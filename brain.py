import json
import yaml
from pathlib import Path
from skill import Skill, SkillCenter


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
            "Reply with only the skill name, nothing else."
        )
        print(f"[{self.name}] classifying task...")
        result = self.llm.complete(
            model=self.classifier_model,
            system=system,
            user_input=classify_input,
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
        self,
        user_message: str,
        agent_reply: str,
        existing_memory: list,
        project: str,
    ) -> list:
        """Condense one exchange into updated memory bullets.

        Uses the cheap classifier model — no need for a heavyweight model here.
        Called *after* the reply is already sent to Slack, so latency doesn't
        matter.

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
            "Given existing memory bullets, a new user message, and the agent's reply, "
            "return ONLY a JSON array of concise bullet strings representing the updated memory. "
            "Merge, update, or drop bullets as needed to keep the list tight and useful. "
            "No preamble, no markdown fences, no explanation — just the JSON array."
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
            cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            bullets = json.loads(cleaned)
            if isinstance(bullets, list):
                return bullets
            raise ValueError("Expected a JSON array")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[{self.name}] memory summarisation parse failed: {e} — keeping existing memory")
            return existing_memory


# ── Example call ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from llm import LLMCenter
    from skill import SkillCenter

    llm = LLMCenter()
    skills = SkillCenter()

    researcher = AgentBrain(llm=llm, skills=skills, config_path="agent/researcher.yaml")

    # Auto-classify — haiku decides the skill, then routes to the right model
    answer = researcher.run("What are the implications of Gödel's theorems?")

    # Or force a skill directly, skipping classifier
    # answer = researcher.run("Summarise this paper...", skill=Skill.SUMMARISE)

    print(answer)