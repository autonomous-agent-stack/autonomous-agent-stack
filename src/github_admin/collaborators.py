from __future__ import annotations


def build_cross_collaborator_plan(source_owner: str, owners: list[str]) -> list[str]:
    wanted = source_owner.strip().lower()
    collaborators = [owner for owner in owners if owner.strip() and owner.strip().lower() != wanted]
    return sorted(dict.fromkeys(collaborators), key=str.lower)
