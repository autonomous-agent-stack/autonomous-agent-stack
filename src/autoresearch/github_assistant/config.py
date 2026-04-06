from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
from typing import Any

from autoresearch.github_assistant.models import (
    AssistantConfig,
    AssistantPolicy,
    ManagedRepoConfig,
    RepoCatalog,
)


def load_yaml_object(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
    if not stripped:
        raise ValueError(f"empty config file: {path}")

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise ValueError(f"config {path} requires PyYAML for non-JSON YAML") from exc
        payload = yaml.safe_load(stripped)

    if not isinstance(payload, dict):
        raise ValueError(f"invalid config payload in {path}; expected object")
    return payload


def load_assistant_config(repo_root: Path) -> AssistantConfig:
    path = repo_root / "assistant.yaml"
    if not path.exists():
        raise FileNotFoundError(f"assistant config not found: {path}")
    payload = load_yaml_object(path)
    payload = _apply_assistant_env_overrides(payload)
    return AssistantConfig.model_validate(payload)


def load_repo_catalog(repo_root: Path) -> RepoCatalog:
    path = repo_root / "repos.yaml"
    if not path.exists():
        raise FileNotFoundError(f"repo catalog not found: {path}")
    return RepoCatalog.model_validate(load_yaml_object(path))


def load_policy(repo_root: Path, assistant: AssistantConfig) -> AssistantPolicy:
    path = resolve_repo_relative_path(repo_root, assistant.policy_path)
    if not path.exists():
        raise FileNotFoundError(f"assistant policy not found: {path}")
    return AssistantPolicy.model_validate(load_yaml_object(path))


def resolve_repo(repo_catalog: RepoCatalog, repo_name: str) -> ManagedRepoConfig:
    wanted = repo_name.strip()
    matches = [item for item in repo_catalog.repos if item.repo == wanted]
    if matches:
        return matches[0]

    suffix_matches = [item for item in repo_catalog.repos if item.repo.endswith(f"/{wanted}")]
    if len(suffix_matches) == 1:
        return suffix_matches[0]

    raise KeyError(f"managed repo not found: {repo_name}")


def resolve_repo_relative_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def _apply_assistant_env_overrides(payload: dict[str, Any]) -> dict[str, Any]:
    merged = dict(payload)
    executor = dict(merged.get("executor") or {})

    _maybe_set(merged, "bot_account", os.getenv("GH_ASSISTANT_BOT_ACCOUNT"))
    _maybe_set(merged, "workspace_root", os.getenv("GH_ASSISTANT_WORKSPACE_ROOT"))

    _maybe_set(executor, "adapter", os.getenv("GH_ASSISTANT_EXECUTOR_ADAPTER"))
    _maybe_set(executor, "binary", os.getenv("GH_ASSISTANT_EXECUTOR_BINARY"))

    command_override = os.getenv("GH_ASSISTANT_EXECUTOR")
    if command_override and command_override.strip():
        executor["command"] = shlex.split(command_override)

    if executor:
        merged["executor"] = executor
    return merged


def _maybe_set(payload: dict[str, Any], key: str, value: str | None) -> None:
    if value is None:
        return
    normalized = value.strip()
    if normalized:
        payload[key] = normalized
