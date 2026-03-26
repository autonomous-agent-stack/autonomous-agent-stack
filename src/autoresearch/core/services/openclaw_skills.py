from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from autoresearch.shared.models import OpenClawSkillDetailRead, OpenClawSkillRead


@dataclass(frozen=True)
class _LoadedSkill:
    summary: OpenClawSkillRead
    content: str
    aliases: set[str]


@dataclass(frozen=True)
class _SkillIndex:
    skills_by_key: dict[str, _LoadedSkill]
    alias_to_key: dict[str, str]


class OpenClawSkillService:
    """Load OpenClaw-style SKILL.md definitions and expose a minimal compatibility API."""

    def __init__(
        self,
        *,
        repo_root: Path,
        skill_roots: list[Path] | None = None,
        max_skill_file_bytes: int = 256_000,
        max_skills_per_root: int = 300,
    ) -> None:
        self._repo_root = repo_root.resolve()
        self._skill_roots = self._resolve_skill_roots(skill_roots)
        self._max_skill_file_bytes = max(8_192, max_skill_file_bytes)
        self._max_skills_per_root = max(1, max_skills_per_root)

    def list_skills(self) -> list[OpenClawSkillRead]:
        index = self._load_index()
        return [item.summary for item in index.skills_by_key.values()]

    def get_skill(self, skill_name: str) -> OpenClawSkillDetailRead | None:
        normalized = skill_name.strip().lower()
        if not normalized:
            return None
        index = self._load_index()
        key = index.alias_to_key.get(normalized)
        if key is None:
            return None
        loaded = index.skills_by_key[key]
        payload = loaded.summary.model_dump()
        return OpenClawSkillDetailRead(**payload, content=loaded.content)

    def resolve_skill_names(
        self,
        skill_names: list[str],
    ) -> tuple[list[OpenClawSkillRead], list[str]]:
        index = self._load_index()
        resolved: list[OpenClawSkillRead] = []
        missing: list[str] = []
        seen_keys: set[str] = set()

        for raw_name in skill_names:
            candidate = raw_name.strip()
            if not candidate:
                continue
            key = index.alias_to_key.get(candidate.lower())
            if key is None:
                missing.append(candidate)
                continue
            if key in seen_keys:
                continue
            seen_keys.add(key)
            resolved.append(index.skills_by_key[key].summary)
        return resolved, missing

    def build_skills_catalog_prompt(
        self,
        skill_names: list[str],
    ) -> tuple[str, list[OpenClawSkillRead], list[str]]:
        resolved, missing = self.resolve_skill_names(skill_names)
        if not resolved:
            return "", resolved, missing

        lines = [
            "The following OpenClaw skills were loaded for this run.",
            "Use the read tool to inspect a skill file when the task matches its intent.",
            (
                "When a skill file references relative paths, resolve them relative to the skill "
                "directory (the parent of SKILL.md)."
            ),
            "",
            "<available_skills>",
        ]
        for skill in resolved:
            lines.append("  <skill>")
            lines.append(f"    <name>{self._escape_xml(skill.name)}</name>")
            lines.append(f"    <description>{self._escape_xml(skill.description)}</description>")
            lines.append(f"    <location>{self._escape_xml(skill.file_path)}</location>")
            lines.append("  </skill>")
        lines.append("</available_skills>")
        return "\n".join(lines), resolved, missing

    def _load_index(self) -> _SkillIndex:
        skills_by_key: dict[str, _LoadedSkill] = {}
        alias_to_key: dict[str, str] = {}

        for root_dir in self._skill_roots:
            if not root_dir.is_dir():
                continue
            loaded_count = 0
            for skill_dir in sorted(root_dir.iterdir(), key=lambda item: item.name.lower()):
                if loaded_count >= self._max_skills_per_root:
                    break
                if not skill_dir.is_dir():
                    continue
                skill_file = skill_dir / "SKILL.md"
                if not skill_file.is_file():
                    continue
                loaded = self._load_skill(root_dir=root_dir, skill_dir=skill_dir, skill_file=skill_file)
                if loaded is None:
                    continue

                key = loaded.summary.name.strip().lower()
                if not key or key in skills_by_key:
                    continue
                skills_by_key[key] = loaded
                loaded_count += 1

                for alias in loaded.aliases:
                    alias_to_key.setdefault(alias, key)

        sorted_keys = sorted(skills_by_key.keys())
        return _SkillIndex(
            skills_by_key={key: skills_by_key[key] for key in sorted_keys},
            alias_to_key=alias_to_key,
        )

    def _load_skill(
        self,
        *,
        root_dir: Path,
        skill_dir: Path,
        skill_file: Path,
    ) -> _LoadedSkill | None:
        content = self._read_skill_content(skill_file)
        frontmatter = self._parse_frontmatter(content)

        name = self._string_value(frontmatter.get("name")) or skill_dir.name
        name = name.strip()
        if not name:
            return None

        description = self._string_value(frontmatter.get("description")) or ""
        metadata = frontmatter.get("metadata")
        metadata_map = metadata if isinstance(metadata, dict) else {}
        openclaw_metadata = metadata_map.get("openclaw")
        openclaw_map = openclaw_metadata if isinstance(openclaw_metadata, dict) else {}
        skill_key = self._string_value(openclaw_map.get("skillKey")) or name

        summary = OpenClawSkillRead(
            name=name,
            skill_key=skill_key,
            description=description.strip(),
            source=self._resolve_source(root_dir),
            base_dir=str(skill_dir.resolve()),
            file_path=str(skill_file.resolve()),
            metadata=metadata_map,
        )
        aliases = {name.lower(), skill_key.lower()}
        return _LoadedSkill(summary=summary, content=content, aliases=aliases)

    def _read_skill_content(self, path: Path) -> str:
        try:
            raw = path.read_bytes()
        except OSError:
            return ""
        truncated = len(raw) > self._max_skill_file_bytes
        sample = raw[: self._max_skill_file_bytes]
        decoded = sample.decode("utf-8", errors="replace")
        if truncated:
            decoded += "\n...[truncated]"
        return decoded

    def _parse_frontmatter(self, content: str) -> dict[str, Any]:
        if not content.startswith("---"):
            return {}

        lines = content.splitlines()
        if not lines or lines[0].strip() != "---":
            return {}

        end_index = None
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                end_index = index
                break
        if end_index is None:
            return {}

        frontmatter_text = "\n".join(lines[1:end_index])
        name = self._parse_scalar(frontmatter_text, key="name")
        description = self._parse_scalar(frontmatter_text, key="description")
        skill_key = self._parse_skill_key(frontmatter_text)

        metadata: dict[str, Any] = {}
        if skill_key:
            metadata = {"openclaw": {"skillKey": skill_key}}

        parsed: dict[str, Any] = {}
        if name is not None:
            parsed["name"] = name
        if description is not None:
            parsed["description"] = description
        parsed["metadata"] = metadata
        return parsed

    def _resolve_skill_roots(self, skill_roots: list[Path] | None) -> list[Path]:
        if skill_roots is not None:
            return [path.expanduser().resolve() for path in skill_roots]
        return [
            (self._repo_root / "skills").resolve(),
            (self._repo_root.parent / "openclaw" / "skills").resolve(),
        ]

    def _resolve_source(self, root_dir: Path) -> str:
        workspace_skills = (self._repo_root / "skills").resolve()
        sibling_openclaw = (self._repo_root.parent / "openclaw" / "skills").resolve()
        if root_dir.resolve() == workspace_skills:
            return "workspace"
        if root_dir.resolve() == sibling_openclaw:
            return "openclaw"
        return str(root_dir.resolve())

    def _string_value(self, raw: Any) -> str | None:
        if isinstance(raw, str):
            return raw
        return None

    def _parse_scalar(self, text: str, *, key: str) -> str | None:
        pattern = re.compile(rf"(?m)^\s*{re.escape(key)}\s*:\s*(.+?)\s*$")
        matched = pattern.search(text)
        if not matched:
            return None
        return self._strip_wrapping_quotes(matched.group(1).strip())

    def _parse_skill_key(self, text: str) -> str | None:
        json_like = re.search(r'"skillKey"\s*:\s*"([^"]+)"', text)
        if json_like:
            return json_like.group(1).strip()
        yaml_like = re.search(r"(?m)^\s*skillKey\s*:\s*(.+?)\s*$", text)
        if not yaml_like:
            return None
        return self._strip_wrapping_quotes(yaml_like.group(1).strip())

    def _strip_wrapping_quotes(self, value: str) -> str:
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            return value[1:-1]
        return value

    def _escape_xml(self, text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )
