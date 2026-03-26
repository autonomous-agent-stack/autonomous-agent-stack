"""Lightweight context object for MASFactory skeleton nodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MASContext:
    """Shared execution context for the MASFactory skeleton."""

    workspace: Path = Path("/workspace")
    goal: str = "explore and learn"
    state: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    memory: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.state[key] = value

    def save_artifact(self, key: str, value: Any) -> None:
        self.artifacts[key] = value

    def save_memory(self, key: str, value: Any) -> None:
        self.memory[key] = value

    def load_memory(self, key: str, default: Any = None) -> Any:
        return self.memory.get(key, default)

    def search_memory(
        self,
        keywords: list[str],
        *,
        max_results: int = 5,
        roots: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Search markdown notes under the workspace for simple keyword matches."""
        root = self.workspace
        if not root.exists():
            return []

        results: list[dict[str, Any]] = []
        seen: set[Path] = set()
        lowered = [keyword.lower() for keyword in keywords if keyword.strip()]
        if not lowered:
            return []

        candidate_roots = roots or ["memory", "docs"]
        candidates: list[Path] = []
        for relative_root in candidate_roots:
            current_root = root / relative_root
            if current_root.exists():
                candidates.extend(current_root.rglob("*.md"))
        if not candidates:
            candidates = list(root.rglob("*.md"))

        for path in candidates:
            if path in seen or not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            haystack = text.lower()
            if any(keyword in haystack for keyword in lowered):
                results.append(
                    {
                        "path": str(path),
                        "match_preview": text[:240].replace("\n", " "),
                    }
                )
                seen.add(path)
                if len(results) >= max_results:
                    return results
        return results
