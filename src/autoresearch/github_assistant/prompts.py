from __future__ import annotations

from pathlib import Path
from string import Template


class PromptCatalog:
    def __init__(self, prompts_root: Path) -> None:
        self._prompts_root = prompts_root

    def require(self, filename: str) -> Path:
        path = self._prompts_root / filename
        if not path.exists():
            raise FileNotFoundError(f"prompt file not found: {path}")
        return path

    def render(self, filename: str, values: dict[str, object]) -> str:
        path = self.require(filename)
        template = Template(path.read_text(encoding="utf-8"))
        text_values = {key: self._to_text(value) for key, value in values.items()}
        return template.safe_substitute(text_values).strip() + "\n"

    @staticmethod
    def _to_text(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return "\n".join(str(item) for item in value)
        return str(value)
