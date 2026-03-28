from __future__ import annotations

import base64
import hashlib
import json
import logging
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from autoresearch.core.services.managed_skill_registry import ManagedSkillRegistryService
from autoresearch.core.services.openclaw_skills import OpenClawSkillService
from autoresearch.core.services.writer_lease import WriterLeaseService
from autoresearch.shared.models import ManagedSkillInstallRequest, ManagedSkillInstallStatus
from autoresearch.shared.store import InMemoryRepository


def _sign_manifest(payload: dict[str, object], private_key: Ed25519PrivateKey) -> str:
    signature = private_key.sign(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    return base64.b64encode(signature).decode("ascii")


def _bundle_file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _build_bundle(
    bundle_root: Path,
    *,
    private_key: Ed25519PrivateKey,
    signer_id: str = "test-signer",
    skill_id: str = "daily_brief",
    version: str = "1.0.0",
    skill_name: str = "Daily Brief",
    capability: str = "prompt",
    frontmatter_name: str | None = None,
    frontmatter_skill_key: str | None = None,
) -> Path:
    bundle_root.mkdir(parents=True, exist_ok=True)
    skill_file = bundle_root / "SKILL.md"
    frontmatter_lines = [
        "---",
        f"name: {frontmatter_name or skill_name}",
        "description: Generate a concise daily brief",
        "metadata:",
        "  openclaw:",
        f"    skillKey: {frontmatter_skill_key or skill_id}",
        "---",
        "# Daily Brief",
        "Use this skill for daily summaries.",
        "",
    ]
    skill_file.write_text("\n".join(frontmatter_lines), encoding="utf-8")
    payload = {
        "schema_version": "managed-skill/v1",
        "skill_id": skill_id,
        "version": version,
        "name": skill_name,
        "description": "Generate a concise daily brief",
        "entrypoint": "SKILL.md",
        "signer_id": signer_id,
        "capabilities": [capability],
        "files": [
            {
                "path": "SKILL.md",
                "sha256": _bundle_file_hash(skill_file),
            }
        ],
        "metadata": {},
    }
    manifest = {**payload, "signature": _sign_manifest(payload, private_key)}
    (bundle_root / "managed-skill.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return bundle_root


def _service(
    tmp_path: Path,
    *,
    trusted_signers: dict[str, str],
    writer_lease: WriterLeaseService | None = None,
) -> ManagedSkillRegistryService:
    return ManagedSkillRegistryService(
        repo_root=tmp_path,
        repository=InMemoryRepository(),
        quarantine_root=tmp_path / "artifacts" / "managed_skills" / "quarantine",
        active_root=tmp_path / "artifacts" / "managed_skills" / "active",
        trusted_signers=trusted_signers,
        allowed_capabilities={"prompt", "filesystem_read", "shell"},
        writer_lease=writer_lease,
    )


def _trusted_keys() -> tuple[Ed25519PrivateKey, str]:
    private_key = Ed25519PrivateKey.generate()
    public_key = base64.b64encode(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode("ascii")
    return private_key, public_key


def test_managed_skill_lifecycle_promotes_only_after_cold_validation(tmp_path: Path) -> None:
    private_key, public_key = _trusted_keys()
    bundle_dir = _build_bundle(tmp_path / "bundle", private_key=private_key)
    service = _service(tmp_path, trusted_signers={"test-signer": public_key})

    quarantined = service.install_to_quarantine(
        ManagedSkillInstallRequest(bundle_dir=str(bundle_dir), requested_by="owner")
    )
    assert quarantined.status is ManagedSkillInstallStatus.QUARANTINED
    assert quarantined.quarantine_dir is not None
    assert quarantined.active_dir is None

    validated = service.run_cold_validation(quarantined.install_id)
    assert validated.status is ManagedSkillInstallStatus.COLD_VALIDATED
    assert validated.quarantine_dir is not None
    assert validated.active_dir is None
    assert any(item.stage == "cold_validation" and item.status == "ok" for item in validated.audit_events)

    promoted = service.promote_skill(validated.install_id)
    assert promoted.status is ManagedSkillInstallStatus.PROMOTED
    assert promoted.active_dir is not None
    assert Path(promoted.active_dir).exists()
    assert any(item.stage == "promote" and item.status == "ok" for item in promoted.audit_events)

    catalog_service = OpenClawSkillService(
        repo_root=tmp_path,
        managed_skill_install_status_resolver=service.get_install_status,
        managed_skill_state_file_name=service.runtime_state_name,
    )
    skill = catalog_service.get_skill("daily_brief")
    assert skill is not None
    assert skill.name == "Daily Brief"
    assert skill.source == "managed"


def test_managed_skill_install_rejects_invalid_signature(tmp_path: Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    trusted_key = Ed25519PrivateKey.generate()
    public_key = base64.b64encode(
        trusted_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode("ascii")
    bundle_dir = _build_bundle(tmp_path / "bundle", private_key=private_key)
    service = _service(tmp_path, trusted_signers={"test-signer": public_key})

    result = service.install_bundle(
        ManagedSkillInstallRequest(bundle_dir=str(bundle_dir), requested_by="owner")
    )

    checks = {item.id: item for item in result.checks}
    assert result.status is ManagedSkillInstallStatus.REJECTED
    assert result.active_dir is None
    assert result.quarantine_dir is None
    assert checks["preflight.signature_valid"].passed is False


def test_managed_skill_install_keeps_quarantine_when_contract_validation_fails(tmp_path: Path) -> None:
    private_key, public_key = _trusted_keys()
    bundle_dir = _build_bundle(
        tmp_path / "bundle",
        private_key=private_key,
        frontmatter_name="Wrong Name",
    )
    service = _service(tmp_path, trusted_signers={"test-signer": public_key})

    result = service.install_bundle(
        ManagedSkillInstallRequest(bundle_dir=str(bundle_dir), requested_by="owner")
    )

    checks = {item.id: item for item in result.checks}
    assert result.status is ManagedSkillInstallStatus.REJECTED
    assert result.quarantine_dir is not None
    assert Path(result.quarantine_dir).exists()
    assert result.active_dir is None
    assert checks["contract.skill_name_matches_manifest"].passed is False


def test_managed_skill_install_rejects_unknown_capabilities(tmp_path: Path) -> None:
    private_key, public_key = _trusted_keys()
    bundle_dir = _build_bundle(
        tmp_path / "bundle",
        private_key=private_key,
        capability="browser_admin",
    )
    service = _service(tmp_path, trusted_signers={"test-signer": public_key})

    result = service.install_bundle(
        ManagedSkillInstallRequest(bundle_dir=str(bundle_dir), requested_by="owner")
    )

    checks = {item.id: item for item in result.checks}
    assert result.status is ManagedSkillInstallStatus.REJECTED
    assert checks["preflight.capabilities_allowed"].passed is False


def test_managed_skill_promotion_stays_cold_validated_when_writer_lease_is_held(tmp_path: Path) -> None:
    private_key, public_key = _trusted_keys()
    writer_lease = WriterLeaseService()
    bundle_dir = _build_bundle(tmp_path / "bundle", private_key=private_key)
    service = _service(tmp_path, trusted_signers={"test-signer": public_key}, writer_lease=writer_lease)

    quarantined = service.install_to_quarantine(
        ManagedSkillInstallRequest(bundle_dir=str(bundle_dir), requested_by="owner")
    )
    validated = service.run_cold_validation(quarantined.install_id)

    with writer_lease.acquire("skill-promote:daily_brief"):
        result = service.promote_skill(validated.install_id)

    checks = {item.id: item for item in result.checks}
    assert result.status is ManagedSkillInstallStatus.COLD_VALIDATED
    assert result.quarantine_dir is not None
    assert result.active_dir is None
    assert checks["promote.writer_lease_and_policy"].passed is False


def test_managed_skill_install_updates_existing_active_version(tmp_path: Path) -> None:
    private_key, public_key = _trusted_keys()
    service = _service(tmp_path, trusted_signers={"test-signer": public_key})

    first_bundle = _build_bundle(tmp_path / "bundle-v1", private_key=private_key, version="1.0.0")
    first_result = service.install_bundle(
        ManagedSkillInstallRequest(bundle_dir=str(first_bundle), requested_by="owner")
    )
    assert first_result.status is ManagedSkillInstallStatus.PROMOTED

    second_bundle = _build_bundle(tmp_path / "bundle-v2", private_key=private_key, version="1.1.0")
    second_result = service.install_bundle(
        ManagedSkillInstallRequest(bundle_dir=str(second_bundle), requested_by="owner")
    )

    assert second_result.status is ManagedSkillInstallStatus.PROMOTED
    active_manifest = json.loads(
        (service.active_root / "daily_brief" / "managed-skill.json").read_text(encoding="utf-8")
    )
    assert active_manifest["version"] == "1.1.0"


def test_openclaw_skill_service_skips_non_promoted_managed_state(tmp_path: Path, caplog) -> None:
    active_dir = tmp_path / "artifacts" / "managed_skills" / "active" / "daily_brief"
    active_dir.mkdir(parents=True, exist_ok=True)
    (active_dir / "SKILL.md").write_text(
        "---\nname: Daily Brief\ndescription: test\nmetadata:\n  openclaw:\n    skillKey: daily_brief\n---\n# Skill\n",
        encoding="utf-8",
    )
    (active_dir / "managed-skill-state.json").write_text(
        json.dumps(
            {
                "install_id": "mskill_1",
                "skill_id": "daily_brief",
                "version": "1.0.0",
                "status": "quarantined",
                "updated_at": "2026-03-28T12:00:00Z",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    caplog.set_level(logging.WARNING)
    service = OpenClawSkillService(repo_root=tmp_path)

    assert service.get_skill("daily_brief") is None
    assert "not promoted" in caplog.text


def test_openclaw_skill_service_skips_when_registry_status_disagrees(tmp_path: Path, caplog) -> None:
    private_key, public_key = _trusted_keys()
    bundle_dir = _build_bundle(tmp_path / "bundle", private_key=private_key)
    service = _service(tmp_path, trusted_signers={"test-signer": public_key})
    promoted = service.install_bundle(
        ManagedSkillInstallRequest(bundle_dir=str(bundle_dir), requested_by="owner")
    )
    assert promoted.status is ManagedSkillInstallStatus.PROMOTED

    caplog.set_level(logging.WARNING)
    catalog_service = OpenClawSkillService(
        repo_root=tmp_path,
        managed_skill_install_status_resolver=lambda install_id: (
            ManagedSkillInstallStatus.COLD_VALIDATED if install_id == promoted.install_id else None
        ),
        managed_skill_state_file_name=service.runtime_state_name,
    )

    assert catalog_service.get_skill("daily_brief") is None
    assert "resolved to status=cold_validated" in caplog.text
