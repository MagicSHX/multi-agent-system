from enum import Enum
from pathlib import Path


class Skill(Enum):
    CODING = "coding"
    SUMMARISE = "summarise"
    REASONING = "reasoning"
    CREATIVE = "creative"
    QUICK = "quick"
    REPLY_NOT_REQUIRED = "reply_not_required"


class SkillCenter:
    """
    Loads skill + context from separate folders.
    Context is optional — skill always loads, context only if file exists.
    """

    def __init__(self, skills_dir: str = "skills", context_dir: str = "context"):
        self.skills_dir = Path(skills_dir)
        self.context_dir = Path(context_dir)
        self._skill_cache: dict[Skill, str] = {}
        self._context_cache: dict[Skill, str] = {}

    def _load_skill(self, skill: Skill) -> str:
        if skill not in self._skill_cache:
            path = self.skills_dir / f"{skill.value}.md"
            self._skill_cache[skill] = path.read_text()
        return self._skill_cache[skill]

    def _load_context(self, skill: Skill) -> str | None:
        if skill not in self._context_cache:
            path = self.context_dir / f"{skill.value}.md"
            self._context_cache[skill] = path.read_text() if path.exists() else None
        return self._context_cache[skill]

    def load(self, skill: Skill) -> str:
        sections = [self._load_skill(skill)]

        context = self._load_context(skill)
        if context:
            sections.append(context)

        return "\n\n---\n\n".join(sections)


skillCenter = SkillCenter(skills_dir="skills", context_dir="context")

# ── Example call ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    prompt = skillCenter.load(Skill.CODING)
    print(prompt)
