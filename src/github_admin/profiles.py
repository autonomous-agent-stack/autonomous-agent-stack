from __future__ import annotations

from pathlib import Path

from github_admin.contracts import GitHubAdminProfileRead


def load_profiles(config_dir: Path) -> list[GitHubAdminProfileRead]:
    candidates = sorted(config_dir.glob("*.env")) + sorted(config_dir.glob("*.env.example"))
    resolved: dict[str, GitHubAdminProfileRead] = {}

    for path in candidates:
        values = _parse_env_file(path)
        profile_id = values.get("PROFILE_ID") or _default_profile_id(path)
        profile = GitHubAdminProfileRead(
            profile_id=profile_id,
            owner=(values.get("OWNER") or values.get("GITHUB_USERNAME") or _default_owner(path)).strip(),
            github_host=(values.get("GH_HOST") or values.get("GITHUB_HOST") or "github.com").strip() or "github.com",
            can_transfer=_parse_bool(values.get("CAN_TRANSFER"), default=False),
            has_token=_has_usable_token(values.get("GH_TOKEN") or values.get("GITHUB_TOKEN")),
            token=_normalize_token(values.get("GH_TOKEN") or values.get("GITHUB_TOKEN")),
            source_path=str(path.resolve()),
            is_example=path.name.endswith(".example"),
        )
        existing = resolved.get(profile.profile_id)
        if existing is None or (existing.is_example and not profile.is_example):
            resolved[profile.profile_id] = profile

    return sorted(resolved.values(), key=lambda item: item.profile_id)


def resolve_owner_profile(profiles: list[GitHubAdminProfileRead], owner: str) -> GitHubAdminProfileRead | None:
    wanted = owner.strip().lower()
    exact = [profile for profile in profiles if profile.owner.lower() == wanted]
    if exact:
        return _prefer_real_profile(exact)

    hinted = [
        profile
        for profile in profiles
        if wanted in profile.profile_id.lower() or profile.profile_id.lower() in {wanted, f"github_{wanted}"}
    ]
    if hinted:
        return _prefer_real_profile(hinted)
    return None


def _prefer_real_profile(profiles: list[GitHubAdminProfileRead]) -> GitHubAdminProfileRead:
    return sorted(
        profiles,
        key=lambda item: (
            item.is_example,
            not item.has_token,
            not item.can_transfer,
            item.profile_id,
        ),
    )[0]


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def _default_profile_id(path: Path) -> str:
    stem = path.name.removesuffix(".env.example").removesuffix(".env")
    return stem if stem.startswith("github_") else f"github_{stem}"


def _default_owner(path: Path) -> str:
    stem = path.name.removesuffix(".env.example").removesuffix(".env")
    return stem.removeprefix("github_")


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _normalize_token(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _has_usable_token(value: str | None) -> bool:
    token = _normalize_token(value)
    if token is None:
        return False
    placeholders = {
        "your_token_here",
        "your_project_token_here",
        "changeme",
        "<token>",
    }
    return token.lower() not in placeholders
