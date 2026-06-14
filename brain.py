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
        """Use a light model to classify the input into a skill."""
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
            user_input=user_input,
        )
        return Skill(result.strip().lower())

    def run(self, user_input: str, skill: Skill | None = None) -> str:
        """
        If skill is provided, use it directly.
        Otherwise classify first with the lightweight model.
        """
        # step 1 — classify
        if skill:
            resolved_skill = skill
            print(f"[{self.name}] skill:  {resolved_skill.value} (manual)")
        else:
            resolved_skill = self._classify(user_input)
            print(f"[{self.name}] skill:  {resolved_skill.value}")

        # step 2 — resolve model + load skill
        model = self.skill_model_map[resolved_skill]
        print(f"[{self.name}] model:  {self.llm.resolve_model(model)}")
        print(f"[{self.name}] running...\n")

        skill_prompt = self.skills.load(resolved_skill)
        system = f"{self.role}\n\n---\n\n{skill_prompt}"

        # step 3 — stream response
        return self.llm.stream(model=model, system=system, user_input=user_input)


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
