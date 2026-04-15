from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from github_admin.contracts import (
    GitHubAdminFailureRead,
    GitHubAdminProfileRead,
    GitHubAdminRepositoryRead,
)


_EXPERIMENT_HINTS = (
    "test",
    "demo",
    "sandbox",
    "playground",
    "scratch",
    "experiment",
    "tmp",
    "temp",
    "practice",
)


class CollaboratorLookupError(RuntimeError):
    pass


class InventoryGateway(Protocol):
    def list_repositories(self, *, owner: str, visibility: str) -> list[dict[str, Any]]: ...

    def list_collaborators(self, *, owner: str, repo: str) -> list[str]: ...


@dataclass(slots=True)
class InventoryCollection:
    repositories: list[GitHubAdminRepositoryRead]
    failures: list[GitHubAdminFailureRead]
    owners_scanned: list[str]


class GitHubApiInventoryGateway:
    def __init__(self, *, github_host: str = "github.com", token: str | None = None, timeout_seconds: float = 15.0) -> None:
        self._github_host = github_host.strip() or "github.com"
        self._token = token.strip() if token else None
        self._timeout_seconds = timeout_seconds

    def list_repositories(self, *, owner: str, visibility: str) -> list[dict[str, Any]]:
        try:
            return self._paged_request(f"/users/{owner}/repos", query={"per_page": "100", "type": visibility})
        except RuntimeError as exc:
            if " 404 " not in f" {exc} ":
                raise
        return self._paged_request(f"/orgs/{owner}/repos", query={"per_page": "100", "type": visibility})

    def list_collaborators(self, *, owner: str, repo: str) -> list[str]:
        try:
            payload = self._paged_request(f"/repos/{owner}/{repo}/collaborators", query={"per_page": "100"})
        except RuntimeError as exc:
            raise CollaboratorLookupError(str(exc)) from exc
        return [
            str(item.get("login", "")).strip()
            for item in payload
            if isinstance(item, dict) and str(item.get("login", "")).strip()
        ]

    def _paged_request(self, path: str, *, query: dict[str, str]) -> list[dict[str, Any]]:
        page = 1
        items: list[dict[str, Any]] = []
        page_size = int(query.get("per_page", "100"))
        while True:
            current_query = dict(query)
            current_query["page"] = str(page)
            payload = self._request_json(path, query=current_query)
            if not isinstance(payload, list):
                raise RuntimeError(f"unexpected GitHub API response for {path}")
            typed = [item for item in payload if isinstance(item, dict)]
            items.extend(typed)
            if len(typed) < page_size:
                return items
            page += 1

    def _request_json(self, path: str, *, query: dict[str, str]) -> Any:
        base_url = f"https://api.{self._github_host}" if self._github_host != "github.com" else "https://api.github.com"
        url = f"{base_url}{path}?{urllib.parse.urlencode(query)}"
        request = urllib.request.Request(url)
        request.add_header("Accept", "application/vnd.github+json")
        request.add_header("User-Agent", "autonomous-agent-stack/github-admin")
        request.add_header("X-GitHub-Api-Version", "2022-11-28")
        if self._token:
            request.add_header("Authorization", f"Bearer {self._token}")
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"GitHub API {exc.code} for {path}: {detail or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"GitHub API request failed for {path}: {exc.reason}") from exc


def collect_inventory(
    *,
    owners: list[str],
    visibility: str,
    include_archived: bool,
    profiles: list[GitHubAdminProfileRead],
    gateway_factory,
) -> InventoryCollection:
    repositories: list[GitHubAdminRepositoryRead] = []
    failures: list[GitHubAdminFailureRead] = []
    owners_scanned: list[str] = []

    for owner in owners:
        profile = _resolve_owner_profile(profiles, owner)
        gateway = gateway_factory(profile)
        try:
            owner_repos = gateway.list_repositories(owner=owner, visibility=visibility)
        except Exception as exc:
            failures.append(
                GitHubAdminFailureRead(
                    scope="owner",
                    owner=owner,
                    action="inventory",
                    detail=str(exc),
                )
            )
            continue

        owners_scanned.append(owner)
        for payload in owner_repos:
            repository = _map_repository(
                payload=payload,
                source_owner=owner,
                include_archived=include_archived,
                source_profile_id=profile.profile_id if profile else None,
            )
            try:
                collaborators = gateway.list_collaborators(owner=owner, repo=repository.name)
            except Exception as exc:
                repository = repository.model_copy(update={"collaborator_check": "unavailable"})
                failures.append(
                    GitHubAdminFailureRead(
                        scope="repo",
                        owner=owner,
                        repo=repository.full_name,
                        action="list_collaborators",
                        detail=str(exc),
                    )
                )
            else:
                other_collaborators = sorted(
                    {
                        login
                        for login in collaborators
                        if login.strip() and login.strip().lower() != owner.strip().lower()
                    },
                    key=str.lower,
                )
                repository = repository.model_copy(
                    update={
                        "other_collaborators": other_collaborators,
                        "collaborator_check": "ok",
                    }
                )
            repositories.append(repository)

    repositories.sort(key=lambda item: item.full_name.lower())
    return InventoryCollection(repositories=repositories, failures=failures, owners_scanned=owners_scanned)


def _resolve_owner_profile(profiles: list[GitHubAdminProfileRead], owner: str) -> GitHubAdminProfileRead | None:
    wanted = owner.strip().lower()
    exact = [profile for profile in profiles if profile.owner.lower() == wanted]
    if exact:
        return sorted(
            exact,
            key=lambda item: (
                item.is_example,
                not item.has_token,
                not item.can_transfer,
                item.profile_id,
            ),
        )[0]
    return None


def _map_repository(
    *,
    payload: dict[str, Any],
    source_owner: str,
    include_archived: bool,
    source_profile_id: str | None,
) -> GitHubAdminRepositoryRead:
    name = str(payload.get("name") or "").strip()
    full_name = str(payload.get("full_name") or f"{source_owner}/{name}").strip()
    archived = bool(payload.get("archived"))
    description = _optional_string(payload.get("description"))
    suggested_reasons = _suggest_exclusion_reasons(
        name=name,
        description=description,
        archived=archived,
        include_archived=include_archived,
        is_fork=bool(payload.get("fork")),
    )
    return GitHubAdminRepositoryRead(
        source_owner=source_owner,
        name=name,
        full_name=full_name,
        visibility=str(payload.get("visibility") or "public"),
        archived=archived,
        fork=bool(payload.get("fork")),
        description=description,
        html_url=_optional_string(payload.get("html_url")),
        default_branch=_optional_string(payload.get("default_branch")),
        language=_optional_string(payload.get("language")),
        stargazers_count=_int_value(payload.get("stargazers_count")),
        forks_count=_int_value(payload.get("forks_count")),
        pushed_at=_optional_string(payload.get("pushed_at")),
        suggested_exclude=bool(suggested_reasons),
        suggested_exclude_reasons=suggested_reasons,
        source_profile_id=source_profile_id,
    )


def _suggest_exclusion_reasons(
    *,
    name: str,
    description: str | None,
    archived: bool,
    include_archived: bool,
    is_fork: bool,
) -> list[str]:
    reasons: list[str] = []
    lowered_name = name.lower()
    lowered_description = (description or "").lower()

    if archived and not include_archived:
        reasons.append("archived repo excluded by request")

    if any(token in lowered_name or token in lowered_description for token in _EXPERIMENT_HINTS):
        reasons.append("heuristic: name or description suggests demo/test/playground usage")

    if is_fork:
        reasons.append("fork repo: confirm whether ownership should move or remain linked upstream")

    return reasons


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _int_value(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if value is None:
        return 0
    try:
        return int(str(value).strip())
    except ValueError:
        return 0

