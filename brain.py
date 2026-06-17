import json
import yaml
from pathlib import Path
from skill import Skill, SkillCenter
import traceback

# Deliverable convention: skill prompts (layered onto `role` in run()) are
# expected to wrap any finished deliverable — a report, draft, doc, etc. that
# the agent is producing as output rather than just discussing — in
#   <deliverable name="...">...full text...</deliverable>
# This is the "lead plan" signal that tells summarise_for_memory() a document's
# full latest content should be captured. run() does not need to special-case
# skills; it only needs to know the tag exists so it can pass the raw reply
# (which still contains the tag) through to summarise_for_memory() untouched.


class AgentBrain:
    """
    Built from a yaml config file.
    Classifier model auto-routes incoming input to the right skill.
    Agent role is fixed — skill prompt is layered on top.
    """

    def __init__(self, llm, skills: SkillCenter, config_path: str):
        config = yaml.safe_load(Path(config_path).read_text())
        config_general = yaml.safe_load(Path("agents/general/general.yaml").read_text())

        self.llm = llm
        self.skills = skills
        self.name = config["name"]
        self.role = config["role"]
        self.role = f"{self.role}\n\n---\n\n{config_general['operation-principle']}"
        self.classifier_model = config["classifier_model"]
        self.skill_model_map = {
            Skill(skill_name): skill_cfg["model"]
            for skill_name, skill_cfg in config["skills"].items()
        }

    def _classify(self, user_input: str) -> Skill:
        """Use a light model to classify the input into a skill.

        Only the raw user message is sent — project context and memory are
        stripped (everything after the first semicolon) to keep token cost low.
        """
        classify_input = user_input.split(";")[0].strip()

        skill_names = ", ".join(s.value for s in self.skill_model_map)
        system = (
            "You are a task classifier. "
            f"Classify the user input into exactly one of these skills: {skill_names}. "
            "Reply with only the skill name, nothing else. And if the received msg doesn't require any action item or taks or reply, return reply_not_required."
        )
        print(f"[{self.name}] classifying task...")
        result = self.llm.complete(
            model=self.classifier_model, system=system, user_input=classify_input,
        )
        return Skill(result.strip().lower())

    def run(self, user_input: str, skill: Skill | None = None) -> str:
        """
        Classify the input (or use the provided skill), then stream a plain
        string reply. Memory summarisation is handled separately via
        summarise_for_memory() so the reply path is always clean.

        Args:
            user_input: Full input string, may include project context / memory.
            skill: Optional override — skips classification entirely.

        Returns:
            Plain string reply ready to post to Slack.
        """
        # step 1 — classify (never send full context to the cheap classifier)
        if skill:
            resolved_skill = skill
            print(f"[{self.name}] skill:  {resolved_skill.value} (manual)")
        else:
            resolved_skill = self._classify(user_input)
            print(f"[{self.name}] skill:  {resolved_skill.value}")

        # step 2 — resolve model + load skill prompt
        model = self.skill_model_map[resolved_skill]
        print(f"[{self.name}] model:  {self.llm.resolve_model(model)}")
        print(f"[{self.name}] running...\n")

        skill_prompt = self.skills.load(resolved_skill)
        system = f"{self.role}\n\n---\n\n{skill_prompt}"

        # step 3 — stream plain reply
        return self.llm.stream(model=model, system=system, user_input=user_input)

    def summarise_for_memory(
        self, user_message: str, agent_reply: str, existing_memory: list, project: str,
    ) -> list:
        """Condense one exchange into updated memory bullets.

        Uses the cheap classifier model — no need for a heavyweight model here.
        Called *after* the reply is already sent to Slack, so latency doesn't
        matter.

        If agent_reply contains <deliverable name="...">...</deliverable> tags
        (see module docstring), the matching documents entry's `content` field
        is overwritten with that deliverable's full latest text, copied
        verbatim by the cheap model. Note: relying on a cheap model to
        reproduce long text losslessly inside JSON carries real risk of
        truncation, escaping issues, or unintended paraphrasing — this is a
        known tradeoff of this approach and worth monitoring in practice.

        Args:
            user_message: Raw user message text (no context appended).
            agent_reply:  The reply that was just sent to Slack.
            existing_memory: Current bullet list for this project.
            project: Project identifier (used for logging only).

        Returns:
            Updated list of concise memory bullet strings, or the existing
            memory unchanged if parsing fails.
        """
        system = (
            "You are a memory summariser for an AI agent. "
            "Given the existing memory JSON, a new user message, and the agent's reply, "
            "return ONLY an updated JSON object with this shape:\n\n"
            "{\n"
            '  "project_info": {"name": "", "goal": "", "constraints": []},\n'
            '  "documents": [{"name": "", "status": "", "notes": null, "content": null}],\n'
            '  "action_items": [{"task": "", "owner": null, "status": ""}],\n'
            '  "decisions": [],\n'
            '  "info": []\n'
            "}\n\n"
            "Rules:\n"
            "1. documents: NEVER drop an entry once added. If a document is referenced again, update "
            "its existing entry (status, notes) in place rather than duplicating it. Keep names exact "
            "as referenced — never paraphrase or shorten a document's name.\n"
            "2. action_items: NEVER silently delete. Update status as it changes. Only remove an item "
            "if it's clearly done and no longer relevant to future steps.\n"
            "3. decisions: append-only list of locked-in choices, scope, and constraints. Add new "
            "entries; don't reword or remove existing ones unless explicitly reversed or contradicted.\n"
            "4. info: the only section you should freely merge, reword, or prune for brevity.\n"
            "5. project_info: update fields in place as new information arrives; don't lose prior "
            "constraints unless contradicted by new info.\n"
            "6. If unsure which category something belongs to, prefer documents or decisions over "
            "info — when in doubt, don't compress it away.\n"
            "7. content field: if the agent reply contains one or more "
            '<deliverable name="...">...</deliverable> tags, find or create the documents entry '
            "whose name matches the tag's name attribute, and set its content field to the exact, "
            "complete text inside that tag — copied verbatim, with no paraphrasing, summarising, "
            "reformatting, or truncation. This OVERWRITES any previous content for that name (the "
            "field always holds only the latest version). If a documents entry has no deliverable "
            "tag associated with it in this turn, leave its existing content field untouched. If a "
            "document has never had a deliverable tag, content stays null. Do not invent a "
            "deliverable tag or content that was not present in the agent reply.\n"
            "No preamble, no markdown fences, no explanation — just the JSON object."
        )
        user_input = (
            f"Existing memory: {json.dumps(existing_memory)}\n"
            f"User message: {user_message}\n"
            f"Agent reply: {agent_reply}"
        )

        print(f"[{self.name}] summarising memory for {project}...")
        raw = self.llm.complete(
            model=self.classifier_model,  # cheap model is sufficient
            system=system,
            user_input=user_input,
        )

        try:
            cleaned = (
                raw.strip()
                .removeprefix("```json")
                .removeprefix("```")
                .removesuffix("```")
                .strip()
            )
            memory = json.loads(cleaned)
            if isinstance(memory, dict) and {
                "project_info", "documents", "action_items", "decisions", "info"
            }.issubset(memory.keys()):
                return memory
            raise ValueError("Expected a JSON object with the memory schema keys")
        except (json.JSONDecodeError, ValueError) as e:
            print(
                f"[{self.name}] memory summarisation parse failed: {traceback.format_exc()} — keeping existing memory"
            )
            return existing_memory


# ── Example call ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from llm import LLMCenter
    from skill import SkillCenter

    llm = LLMCenter()
    skills = SkillCenter()

    researcher = AgentBrain(
        llm=llm, skills=skills, config_path="agent/research-agent.yaml"
    )

    # Auto-classify — haiku decides the skill, then routes to the right model
    answer = researcher.run("What are the implications of Gödel's theorems?")

    # Or force a skill directly, skipping classifier
    # answer = researcher.run("Summarise this paper...", skill=Skill.SUMMARISE)

    print(answer)