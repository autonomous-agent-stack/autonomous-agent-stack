from __future__ import annotations


def build_invitation_acceptance_plan(*, enabled: bool, confirmation_profile_id: str | None) -> list[str]:
    if not enabled or not confirmation_profile_id:
        return []
    return [confirmation_profile_id]

