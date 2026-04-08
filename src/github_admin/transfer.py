from __future__ import annotations

from github_admin.collaborators import build_cross_collaborator_plan
from github_admin.contracts import (
    GitHubAdminPlanDecisionRead,
    GitHubAdminPostActions,
    GitHubAdminProfileRead,
    GitHubAdminRepositoryRead,
)
from github_admin.invitations import build_invitation_acceptance_plan
from github_admin.profiles import resolve_owner_profile


def build_transfer_decisions(
    *,
    repositories: list[GitHubAdminRepositoryRead],
    source_owners: list[str],
    target_owner: str,
    profiles: list[GitHubAdminProfileRead],
    post_actions: GitHubAdminPostActions,
) -> list[GitHubAdminPlanDecisionRead]:
    target_profile = resolve_owner_profile(profiles, target_owner)
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
            action = "review" if any("heuristic:" in item for item in repository.suggested_exclude_reasons) else "skip"
            reason = "; ".join(repository.suggested_exclude_reasons)

        if repository.source_profile_id is None:
            action = "review"
            reason = "missing source profile for owner"
        elif target_profile is None:
            action = "review"
            reason = "missing target-owner profile; acceptance path cannot be verified"

        if repository.other_collaborators:
            notes.append(f"existing collaborators: {', '.join(repository.other_collaborators)}")
        if repository.collaborator_check == "unavailable":
            notes.append("collaborator check unavailable with current token scope")
        if repository.fork:
            notes.append("confirm fork ownership policy before moving")

        decisions.append(
            GitHubAdminPlanDecisionRead(
                full_name=repository.full_name,
                action=action,
                reason=reason,
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
) -> str:
    planned = [decision for decision in decisions if decision.action == "plan_transfer"]
    not_recommended = [decision for decision in decisions if decision.action != "plan_transfer"]

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
        "",
    ]
    lines.extend(_render_recommended_group(planned))
    lines.extend(_render_not_recommended_group(not_recommended))
    lines.extend(_render_reasons_group(not_recommended))
    return "\n".join(lines).rstrip() + "\n"


def _render_recommended_group(decisions: list[GitHubAdminPlanDecisionRead]) -> list[str]:
    lines = ["## recommended_to_transfer"]
    if not decisions:
        lines.extend(["- None", ""])
        return lines

    for decision in decisions:
        lines.append(f"- `{decision.full_name}`")
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
