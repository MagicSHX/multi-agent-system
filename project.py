from datetime import datetime
from pathlib import Path


class ProjectCenter:
    """
    Project context. Starts with a one pager.
    Agents can add features to the project over time.
    """

    SUPPORTED_EXTENSIONS = {".md"}

    def __init__(self, name: str):
        self.name = name
        self.created_at = datetime.now().isoformat()
        self.features: list[dict] = []

        # paths
        self.project_dir = Path("projects") / name
        self.one_pager_path = self._resolve_one_pager_path()

        # load one pager if exists, else empty
        self.one_pager = self._load_one_pager()

        self.project_summary = None

    # ── One Pager ─────────────────────────────────────────────────────────────

    def _resolve_one_pager_path(self) -> Path | None:
        """Return the first matching one-pager file (.md only)."""
        base_dir = self.project_dir / "one_pager"
        candidate = base_dir / f"{self.name}_one_pager.md"
        return candidate if candidate.exists() else None

    def _load_one_pager(self) -> str:
        if self.one_pager_path and self.one_pager_path.exists():
            return self.one_pager_path.read_text()
        return ""


if __name__ == "__main__":
    project = ProjectCenter("project-test-1")
    print(f"Project name: {project.name}")
    print(f"Created at: {project.created_at}")
    print(f"One pager content:\n{project.one_pager}")