from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shlex
import shutil
from typing import Any

from autoresearch.github_assistant.models import (
    AssistantConfig,
    AssistantPolicy,
    GitHubAssistantProfileConfig,
    GitHubAssistantProfilesConfig,
    ManagedRepoConfig,
    RepoCatalog,
)

_PROFILES_CATALOG_NAME = "profiles.yaml"
_DEFAULT_PROFILE_ID = "default"
_DEFAULT_GITHUB_HOST = "github.com"
_PROFILE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True, slots=True)
class ResolvedGitHubAssistantProfile:
    id: str
    display_name: str
    root: Path
    github_host: str
    gh_config_dir: Path
    explicit: bool
    is_default: bool


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
        return path.expanduser().resolve()
    return (repo_root / path).resolve()


def load_profile_catalog(repo_root: Path) -> GitHubAssistantProfilesConfig:
    path = repo_root / _PROFILES_CATALOG_NAME
    if not path.exists():
        return GitHubAssistantProfilesConfig(
            default_profile=_DEFAULT_PROFILE_ID,
            profiles=[_implicit_default_profile()],
        )
    catalog = GitHubAssistantProfilesConfig.model_validate(load_yaml_object(path))
    _validate_profile_catalog(catalog)
    return catalog


def list_resolved_profiles(repo_root: Path) -> list[ResolvedGitHubAssistantProfile]:
    explicit = (repo_root / _PROFILES_CATALOG_NAME).exists()
    catalog = load_profile_catalog(repo_root)
    default_profile = catalog.default_profile or (catalog.profiles[0].id if catalog.profiles else _DEFAULT_PROFILE_ID)
    return [
        _resolve_profile_entry(
            repo_root,
            profile,
            explicit=explicit,
            default_profile=default_profile,
        )
        for profile in catalog.profiles
    ]


def resolve_profile(repo_root: Path, profile_id: str | None = None) -> ResolvedGitHubAssistantProfile:
    profiles = list_resolved_profiles(repo_root)
    if not profiles:
        raise FileNotFoundError(f"no github assistant profiles configured under {repo_root}")
    wanted = (profile_id or "").strip()
    if not wanted:
        default_profile = next((profile for profile in profiles if profile.is_default), None)
        return default_profile or profiles[0]
    for profile in profiles:
        if profile.id == wanted:
            return profile
    raise KeyError(f"github assistant profile not found: {wanted}")


def initialize_profile(
    repo_root: Path,
    profile_id: str,
    *,
    display_name: str | None = None,
    source_profile_id: str | None = None,
) -> ResolvedGitHubAssistantProfile:
    normalized_profile_id = profile_id.strip()
    if not normalized_profile_id or not _PROFILE_ID_RE.fullmatch(normalized_profile_id):
        raise ValueError("profile id must match [A-Za-z0-9][A-Za-z0-9._-]*")

    profiles_path = repo_root / _PROFILES_CATALOG_NAME
    explicit = profiles_path.exists()
    catalog = load_profile_catalog(repo_root)
    if any(profile.id == normalized_profile_id for profile in catalog.profiles):
        raise ValueError(f"github assistant profile already exists: {normalized_profile_id}")

    source_profile = resolve_profile(repo_root, source_profile_id)
    profile_root_relative = Path("profiles") / normalized_profile_id
    profile_root = (repo_root / profile_root_relative).resolve()
    if profile_root.exists():
        raise FileExistsError(f"profile root already exists: {profile_root}")
    profile_root.mkdir(parents=True, exist_ok=False)
    _copy_profile_template(source_profile.root, profile_root)

    existing_profiles = list(catalog.profiles)
    if not explicit:
        existing_profiles = [_implicit_default_profile()]
    default_profile = catalog.default_profile or (existing_profiles[0].id if existing_profiles else _DEFAULT_PROFILE_ID)
    existing_profiles.append(
        GitHubAssistantProfileConfig(
            id=normalized_profile_id,
            display_name=(display_name or normalized_profile_id).strip() or normalized_profile_id,
            root=profile_root_relative.as_posix(),
            github_host=source_profile.github_host or _DEFAULT_GITHUB_HOST,
            gh_config_dir=(Path(".gh-profiles") / normalized_profile_id).as_posix(),
        )
    )
    updated_catalog = GitHubAssistantProfilesConfig(
        default_profile=default_profile,
        profiles=existing_profiles,
    )
    _validate_profile_catalog(updated_catalog)
    profiles_path.write_text(
        json.dumps(updated_catalog.model_dump(mode="json", exclude_none=True), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return resolve_profile(repo_root, normalized_profile_id)


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


def _implicit_default_profile() -> GitHubAssistantProfileConfig:
    return GitHubAssistantProfileConfig(
        id=_DEFAULT_PROFILE_ID,
        display_name="Default",
        root=".",
        github_host=_DEFAULT_GITHUB_HOST,
        gh_config_dir=".gh-profiles/default",
    )


def _validate_profile_catalog(catalog: GitHubAssistantProfilesConfig) -> None:
    if not catalog.profiles:
        raise ValueError("profiles.yaml must define at least one profile")
    seen: set[str] = set()
    for profile in catalog.profiles:
        if not _PROFILE_ID_RE.fullmatch(profile.id):
            raise ValueError(f"invalid github assistant profile id: {profile.id}")
        if profile.id in seen:
            raise ValueError(f"duplicate github assistant profile id: {profile.id}")
        seen.add(profile.id)
    if catalog.default_profile and catalog.default_profile not in seen:
        raise ValueError(f"default profile is not defined: {catalog.default_profile}")


def _resolve_profile_entry(
    repo_root: Path,
    profile: GitHubAssistantProfileConfig,
    *,
    explicit: bool,
    default_profile: str,
) -> ResolvedGitHubAssistantProfile:
    return ResolvedGitHubAssistantProfile(
        id=profile.id,
        display_name=profile.display_name or profile.id,
        root=resolve_repo_relative_path(repo_root, profile.root or "."),
        github_host=profile.github_host or _DEFAULT_GITHUB_HOST,
        gh_config_dir=resolve_repo_relative_path(
            repo_root,
            profile.gh_config_dir or (Path(".gh-profiles") / profile.id).as_posix(),
        ),
        explicit=explicit,
        is_default=profile.id == default_profile,
    )


def _copy_profile_template(source_root: Path, destination_root: Path) -> None:
    for filename in ("assistant.yaml", "repos.yaml"):
        source = source_root / filename
        if not source.exists():
            raise FileNotFoundError(f"profile template file not found: {source}")
        shutil.copy2(source, destination_root / filename)
    for dirname in ("prompts", "policies"):
        source = source_root / dirname
        if not source.exists():
            continue
        shutil.copytree(source, destination_root / dirname)
