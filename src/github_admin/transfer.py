from __future__ import annotations

from github_admin.collaborators import build_cross_collaborator_plan
from github_admin.contracts import (
    GitHubAdminPlanDecisionRead,
    GitHubAdminPostActions,
    GitHubAdminPreflightCheckRead,
    GitHubAdminPreflightRead,
    GitHubAdminProfileIsolationRead,
    GitHubAdminProfileRead,
    GitHubAdminReadiness,
    GitHubAdminRepoPreflightRead,
    GitHubAdminRepositoryRead,
    GitHubAdminTargetOwnerProbeRead,
)
from github_admin.invitations import build_invitation_acceptance_plan
from github_admin.profiles import resolve_owner_profile


def build_preflight_report(
    *,
    repositories: list[GitHubAdminRepositoryRead],
    source_owners: list[str],
    target_owner: str,
    profiles: list[GitHubAdminProfileRead],
    post_actions: GitHubAdminPostActions,
    gateway_factory,
) -> GitHubAdminPreflightRead:
    profile_isolation = [
        _evaluate_profile_isolation(owner=owner, role="source", profiles=profiles, require_transfer=True)
        for owner in source_owners
    ]
    target_profile = resolve_owner_profile(profiles, target_owner)
    target_profile_check = _evaluate_profile_isolation(
        owner=target_owner,
        role="target",
        profiles=profiles,
        require_transfer=False,
    )
    profile_isolation.append(target_profile_check)

    target_probe = _probe_target_owner(
        target_owner=target_owner,
        target_profile=target_profile,
        target_profile_check=target_profile_check,
        gateway_factory=gateway_factory,
    )
    source_check_index = {(item.owner.lower(), item.role): item for item in profile_isolation}
    repo_preflight = [
        _build_repo_preflight(
            repository=repository,
            source_profile_check=source_check_index.get((repository.source_owner.lower(), "source")),
            target_probe=target_probe,
            target_profile=target_profile,
            post_actions=post_actions,
        )
        for repository in repositories
    ]
    repo_preflight.sort(key=lambda item: item.full_name.lower())
    return GitHubAdminPreflightRead(
        profile_isolation=profile_isolation,
        target_owner_probe=target_probe,
        repositories=repo_preflight,
    )


def build_transfer_decisions(
    *,
    repositories: list[GitHubAdminRepositoryRead],
    source_owners: list[str],
    target_owner: str,
    profiles: list[GitHubAdminProfileRead],
    post_actions: GitHubAdminPostActions,
    preflight: GitHubAdminPreflightRead | None = None,
) -> list[GitHubAdminPlanDecisionRead]:
    target_profile = resolve_owner_profile(profiles, target_owner)
    preflight_index = {
        item.full_name: item for item in (preflight.repositories if preflight is not None else [])
    }
    decisions: list[GitHubAdminPlanDecisionRead] = []

    for repository in repositories:
        notes: list[str] = []
        planned_collaborators = (
            build_cross_collaborator_plan(repository.source_owner, source_owners)
            if post_actions.add_cross_collaborators
            else []
        )
        invitation_profiles = build_invitation_acceptance_plan(
            enabled=post_actions.request_invitation_acceptance,
            confirmation_profile_id=target_profile.profile_id if target_profile else None,
        )

        action = "plan_transfer"
        reason = "eligible for dry-run transfer"
        if repository.suggested_exclude_reasons:
            action = "review" if any("heuristic:" in item or item.startswith("fork repo:") for item in repository.suggested_exclude_reasons) else "skip"
            reason = "; ".join(repository.suggested_exclude_reasons)

        if repository.source_profile_id is None:
            action = "review"
            reason = "missing source profile for owner"
        elif target_profile is None:
            action = "review"
            reason = "missing target-owner profile; acceptance path cannot be verified"

        repo_preflight = preflight_index.get(repository.full_name)
        readiness = repo_preflight.readiness if repo_preflight else GitHubAdminReadiness.UNKNOWN
        if repo_preflight and action == "plan_transfer" and repo_preflight.readiness != GitHubAdminReadiness.READY:
            action = "review"
            reason = repo_preflight.reason

        if repository.other_collaborators:
            notes.append(f"existing collaborators: {', '.join(repository.other_collaborators)}")
        if repository.collaborator_check == "unavailable":
            notes.append("collaborator check unavailable with current token scope")
        if repository.fork:
            notes.append("confirm fork ownership policy before moving")
        if repo_preflight and repo_preflight.notes:
            notes.extend(repo_preflight.notes)

        decisions.append(
            GitHubAdminPlanDecisionRead(
                full_name=repository.full_name,
                action=action,
                reason=reason,
                readiness=readiness,
                source_profile_id=repository.source_profile_id,
                confirmation_profile_id=target_profile.profile_id if target_profile else None,
                planned_collaborators=planned_collaborators,
                invitation_acceptance_profiles=invitation_profiles,
                notes=notes,
            )
        )

    return sorted(decisions, key=lambda item: item.full_name.lower())


def render_transfer_plan_markdown(
    *,
    run_id: str,
    source_owners: list[str],
    target_owner: str,
    decisions: list[GitHubAdminPlanDecisionRead],
    preflight: GitHubAdminPreflightRead | None = None,
) -> str:
    planned = [decision for decision in decisions if decision.action == "plan_transfer"]
    not_recommended = [decision for decision in decisions if decision.action != "plan_transfer"]
    ready = [item for item in (preflight.repositories if preflight else []) if item.readiness == GitHubAdminReadiness.READY]
    blocked = [item for item in (preflight.repositories if preflight else []) if item.readiness == GitHubAdminReadiness.BLOCKED]
    unknown = [item for item in (preflight.repositories if preflight else []) if item.readiness == GitHubAdminReadiness.UNKNOWN]

    lines = [
        "# GitHub Admin Dry-Run Transfer Plan",
        "",
        f"- Run ID: `{run_id}`",
        f"- Source owners: {', '.join(source_owners)}",
        f"- Target owner: `{target_owner}`",
        f"- Dry run: `true`",
        "",
        "## Summary",
        f"- recommended_to_transfer: {len(planned)}",
        f"- not_recommended_to_transfer: {len(not_recommended)}",
        f"- ready_to_execute: {len(ready)}",
        f"- blocked: {len(blocked)}",
        f"- unknown: {len(unknown)}",
        "",
    ]
    lines.extend(_render_profile_isolation(preflight))
    lines.extend(_render_target_probe(preflight))
    lines.extend(_render_recommended_group(planned))
    lines.extend(_render_not_recommended_group(not_recommended))
    lines.extend(_render_reasons_group(not_recommended))
    lines.extend(_render_preflight_group("ready_to_execute", ready))
    lines.extend(_render_preflight_group("blocked", blocked))
    lines.extend(_render_preflight_group("unknown", unknown))
    return "\n".join(lines).rstrip() + "\n"


def _evaluate_profile_isolation(
    *,
    owner: str,
    role: str,
    profiles: list[GitHubAdminProfileRead],
    require_transfer: bool,
) -> GitHubAdminProfileIsolationRead:
    profile = resolve_owner_profile(profiles, owner)
    if profile is None:
        return GitHubAdminProfileIsolationRead(
            owner=owner,
            role=role,
            readiness=GitHubAdminReadiness.BLOCKED,
            reason=f"missing {role}-owner profile",
        )
    if profile.is_example:
        return GitHubAdminProfileIsolationRead(
            owner=owner,
            role=role,
            profile_id=profile.profile_id,
            readiness=GitHubAdminReadiness.BLOCKED,
            reason=f"{role}-owner profile is example-only",
            github_host=profile.github_host,
            has_token=profile.has_token,
            can_transfer=profile.can_transfer,
        )
    if not profile.has_token:
        return GitHubAdminProfileIsolationRead(
            owner=owner,
            role=role,
            profile_id=profile.profile_id,
            readiness=GitHubAdminReadiness.BLOCKED,
            reason=f"{role}-owner profile has no usable token",
            github_host=profile.github_host,
            has_token=profile.has_token,
            can_transfer=profile.can_transfer,
        )
    if require_transfer and not profile.can_transfer:
        return GitHubAdminProfileIsolationRead(
            owner=owner,
            role=role,
            profile_id=profile.profile_id,
            readiness=GitHubAdminReadiness.BLOCKED,
            reason=f"{role}-owner profile is not transfer-capable",
            github_host=profile.github_host,
            has_token=profile.has_token,
            can_transfer=profile.can_transfer,
        )
    return GitHubAdminProfileIsolationRead(
        owner=owner,
        role=role,
        profile_id=profile.profile_id,
        readiness=GitHubAdminReadiness.READY,
        reason=f"{role}-owner profile isolation validated",
        github_host=profile.github_host,
        has_token=profile.has_token,
        can_transfer=profile.can_transfer,
    )


def _probe_target_owner(
    *,
    target_owner: str,
    target_profile: GitHubAdminProfileRead | None,
    target_profile_check: GitHubAdminProfileIsolationRead,
    gateway_factory,
) -> GitHubAdminTargetOwnerProbeRead:
    if target_profile_check.readiness == GitHubAdminReadiness.BLOCKED:
        return GitHubAdminTargetOwnerProbeRead(
            target_owner=target_owner,
            confirmation_profile_id=target_profile_check.profile_id,
            readiness=GitHubAdminReadiness.BLOCKED,
            reason=target_profile_check.reason,
        )

    try:
        gateway = gateway_factory(target_profile)
        gateway.list_repositories(owner=target_owner, visibility="all")
    except Exception as exc:
        detail = str(exc)
        lower = detail.lower()
        readiness = GitHubAdminReadiness.BLOCKED if "404" in lower or "not found" in lower else GitHubAdminReadiness.UNKNOWN
        return GitHubAdminTargetOwnerProbeRead(
            target_owner=target_owner,
            confirmation_profile_id=target_profile.profile_id if target_profile else None,
            readiness=readiness,
            reason=f"target owner probe failed: {detail}",
        )

    return GitHubAdminTargetOwnerProbeRead(
        target_owner=target_owner,
        confirmation_profile_id=target_profile.profile_id if target_profile else None,
        readiness=GitHubAdminReadiness.READY,
        reason="target owner reachable via repository listing probe",
    )


def _build_repo_preflight(
    *,
    repository: GitHubAdminRepositoryRead,
    source_profile_check: GitHubAdminProfileIsolationRead | None,
    target_probe: GitHubAdminTargetOwnerProbeRead,
    target_profile: GitHubAdminProfileRead | None,
    post_actions: GitHubAdminPostActions,
) -> GitHubAdminRepoPreflightRead:
    profile_status = GitHubAdminPreflightCheckRead(
        status=source_profile_check.readiness if source_profile_check else GitHubAdminReadiness.BLOCKED,
        reason=(source_profile_check.reason if source_profile_check else "missing source-owner profile check"),
    )
    target_status = GitHubAdminPreflightCheckRead(status=target_probe.readiness, reason=target_probe.reason)
    collaborator_status = _build_collaborator_readiness(repository=repository, enabled=post_actions.add_cross_collaborators)
    invitation_status = _build_invitation_readiness(
        enabled=post_actions.request_invitation_acceptance,
        target_probe=target_probe,
        confirmation_profile_id=target_profile.profile_id if target_profile else None,
    )

    blocked_reasons: list[str] = []
    unknown_reasons: list[str] = []
    notes: list[str] = []

    _collect_check_reason(profile_status, blocked_reasons, unknown_reasons)
    _collect_check_reason(target_status, blocked_reasons, unknown_reasons)
    _collect_check_reason(collaborator_status, blocked_reasons, unknown_reasons)
    _collect_check_reason(invitation_status, blocked_reasons, unknown_reasons)

    for item in repository.suggested_exclude_reasons:
        if item.startswith("heuristic:") or item.startswith("fork repo:"):
            unknown_reasons.append(item)
        else:
            blocked_reasons.append(item)

    if repository.other_collaborators:
        notes.append(f"existing collaborators: {', '.join(repository.other_collaborators)}")

    if blocked_reasons:
        readiness = GitHubAdminReadiness.BLOCKED
        reason = blocked_reasons[0]
        reasons = blocked_reasons + [item for item in unknown_reasons if item not in blocked_reasons]
    elif unknown_reasons:
        readiness = GitHubAdminReadiness.UNKNOWN
        reason = unknown_reasons[0]
        reasons = unknown_reasons
    else:
        readiness = GitHubAdminReadiness.READY
        reason = "preflight checks passed"
        reasons = ["preflight checks passed"]

    return GitHubAdminRepoPreflightRead(
        full_name=repository.full_name,
        readiness=readiness,
        reason=reason,
        source_profile_id=repository.source_profile_id,
        confirmation_profile_id=target_probe.confirmation_profile_id,
        profile_isolation=profile_status,
        target_owner_probe=target_status,
        collaborator_sync=collaborator_status,
        invitation_acceptance=invitation_status,
        reasons=reasons,
        notes=notes,
    )


def _build_collaborator_readiness(
    *,
    repository: GitHubAdminRepositoryRead,
    enabled: bool,
) -> GitHubAdminPreflightCheckRead:
    if not enabled:
        return GitHubAdminPreflightCheckRead(
            status=GitHubAdminReadiness.READY,
            reason="collaborator sync disabled by request",
        )
    if repository.collaborator_check == "ok":
        return GitHubAdminPreflightCheckRead(
            status=GitHubAdminReadiness.READY,
            reason="collaborator readiness inspected",
        )
    return GitHubAdminPreflightCheckRead(
        status=GitHubAdminReadiness.UNKNOWN,
        reason="collaborator readiness unavailable with current token scope",
    )


def _build_invitation_readiness(
    *,
    enabled: bool,
    target_probe: GitHubAdminTargetOwnerProbeRead,
    confirmation_profile_id: str | None,
) -> GitHubAdminPreflightCheckRead:
    if not enabled:
        return GitHubAdminPreflightCheckRead(
            status=GitHubAdminReadiness.READY,
            reason="invitation acceptance check disabled by request",
        )
    if not confirmation_profile_id:
        return GitHubAdminPreflightCheckRead(
            status=GitHubAdminReadiness.BLOCKED,
            reason="missing confirmation profile for invitation acceptance",
        )
    if target_probe.readiness == GitHubAdminReadiness.READY:
        return GitHubAdminPreflightCheckRead(
            status=GitHubAdminReadiness.READY,
            reason="invitation acceptance profile is ready for dry-run verification",
        )
    if target_probe.readiness == GitHubAdminReadiness.BLOCKED:
        return GitHubAdminPreflightCheckRead(
            status=GitHubAdminReadiness.BLOCKED,
            reason=target_probe.reason,
        )
    return GitHubAdminPreflightCheckRead(
        status=GitHubAdminReadiness.UNKNOWN,
        reason=target_probe.reason,
    )


def _collect_check_reason(
    check: GitHubAdminPreflightCheckRead,
    blocked_reasons: list[str],
    unknown_reasons: list[str],
) -> None:
    if not check.reason:
        return
    if check.status == GitHubAdminReadiness.BLOCKED:
        blocked_reasons.append(check.reason)
    elif check.status == GitHubAdminReadiness.UNKNOWN:
        unknown_reasons.append(check.reason)


def _render_profile_isolation(preflight: GitHubAdminPreflightRead | None) -> list[str]:
    lines = ["## preflight"]
    if not preflight:
        lines.extend(["- None", ""])
        return lines
    lines.append("### profile_isolation")
    if not preflight.profile_isolation:
        lines.append("- None")
    else:
        for item in preflight.profile_isolation:
            lines.append(
                f"- `{item.owner}` ({item.role}) -> `{item.readiness.value}`"
                + (f" via `{item.profile_id}`" if item.profile_id else "")
            )
            if item.reason:
                lines.append(f"  reason: {item.reason}")
    lines.append("")
    return lines


def _render_target_probe(preflight: GitHubAdminPreflightRead | None) -> list[str]:
    lines = ["### target_owner_probe"]
    probe = preflight.target_owner_probe if preflight else None
    if probe is None:
        lines.extend(["- None", ""])
        return lines
    lines.append(f"- `{probe.target_owner}` -> `{probe.readiness.value}`")
    if probe.confirmation_profile_id:
        lines.append(f"  confirmation profile: `{probe.confirmation_profile_id}`")
    if probe.reason:
        lines.append(f"  reason: {probe.reason}")
    lines.append("")
    return lines


def _render_recommended_group(decisions: list[GitHubAdminPlanDecisionRead]) -> list[str]:
    lines = ["## recommended_to_transfer"]
    if not decisions:
        lines.extend(["- None", ""])
        return lines

    for decision in decisions:
        lines.append(f"- `{decision.full_name}`")
        lines.append(f"  readiness: `{decision.readiness.value}`")
        if decision.source_profile_id:
            lines.append(f"  source profile: `{decision.source_profile_id}`")
        if decision.confirmation_profile_id:
            lines.append(f"  confirmation profile: `{decision.confirmation_profile_id}`")
        if decision.planned_collaborators:
            lines.append(f"  planned collaborators: {', '.join(decision.planned_collaborators)}")
        if decision.invitation_acceptance_profiles:
            lines.append(
                "  invitation acceptance checks: "
                + ", ".join(f"`{profile}`" for profile in decision.invitation_acceptance_profiles)
            )
        for note in decision.notes:
            lines.append(f"  note: {note}")
    lines.append("")
    return lines


def _render_not_recommended_group(decisions: list[GitHubAdminPlanDecisionRead]) -> list[str]:
    lines = ["## not_recommended_to_transfer"]
    if not decisions:
        lines.extend(["- None", ""])
        return lines

    for decision in decisions:
        lines.append(f"- `{decision.full_name}` (`{decision.action}`)")
        lines.append(f"  readiness: `{decision.readiness.value}`")
        if decision.source_profile_id:
            lines.append(f"  source profile: `{decision.source_profile_id}`")
        if decision.confirmation_profile_id:
            lines.append(f"  confirmation profile: `{decision.confirmation_profile_id}`")
        for note in decision.notes:
            lines.append(f"  note: {note}")
    lines.append("")
    return lines


def _render_reasons_group(decisions: list[GitHubAdminPlanDecisionRead]) -> list[str]:
    lines = ["## reasons"]
    if not decisions:
        lines.extend(["- None", ""])
        return lines

    for decision in decisions:
        lines.append(f"- `{decision.full_name}`: {decision.reason}")
    lines.append("")
    return lines


def _render_preflight_group(title: str, items: list[GitHubAdminRepoPreflightRead]) -> list[str]:
    lines = [f"## {title}"]
    if not items:
        lines.extend(["- None", ""])
        return lines

    for item in items:
        lines.append(f"- `{item.full_name}`")
        if item.source_profile_id:
            lines.append(f"  source profile: `{item.source_profile_id}`")
        if item.confirmation_profile_id:
            lines.append(f"  confirmation profile: `{item.confirmation_profile_id}`")
        lines.append(f"  reason: {item.reason}")
        for reason in item.reasons[1:]:
            lines.append(f"  detail: {reason}")
        for note in item.notes:
            lines.append(f"  note: {note}")
    lines.append("")
    return lines

