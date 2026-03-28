from __future__ import annotations

import base64
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from autoresearch.core.services.openclaw_skills import OpenClawSkillService
from autoresearch.core.services.writer_lease import WriterLeaseService
from autoresearch.shared.models import (
    ManagedSkillAuditEventRead,
    ManagedSkillCheck,
    ManagedSkillInstallRead,
    ManagedSkillInstallRequest,
    ManagedSkillInstallStatus,
    ManagedSkillManifestRead,
    ManagedSkillRuntimeStateRead,
    utc_now,
)
from autoresearch.shared.store import Repository, create_resource_id


class ManagedSkillRegistryService:
    def __init__(
        self,
        *,
        repo_root: Path,
        repository: Repository[ManagedSkillInstallRead],
        quarantine_root: Path,
        active_root: Path,
        trusted_signers: dict[str, str] | None = None,
        allowed_capabilities: set[str] | None = None,
        writer_lease: WriterLeaseService | None = None,
        manifest_name: str = "managed-skill.json",
        runtime_state_name: str = "managed-skill-state.json",
        max_skill_file_bytes: int = 256_000,
    ) -> None:
        self._repo_root = repo_root.resolve()
        self._repository = repository
        self._quarantine_root = quarantine_root.resolve()
        self._active_root = active_root.resolve()
        self._trusted_signers = {
            key.strip(): value.strip()
            for key, value in (trusted_signers or {}).items()
            if key.strip() and value.strip()
        }
        self._allowed_capabilities = {item.strip() for item in (allowed_capabilities or set()) if item.strip()}
        self._writer_lease = writer_lease or WriterLeaseService()
        self._manifest_name = manifest_name.strip() or "managed-skill.json"
        self._runtime_state_name = runtime_state_name.strip() or "managed-skill-state.json"
        self._max_skill_file_bytes = max(8_192, max_skill_file_bytes)
        self._quarantine_root.mkdir(parents=True, exist_ok=True)
        self._active_root.mkdir(parents=True, exist_ok=True)

    @property
    def quarantine_root(self) -> Path:
        return self._quarantine_root

    @property
    def active_root(self) -> Path:
        return self._active_root

    @property
    def runtime_state_name(self) -> str:
        return self._runtime_state_name

    def list_installs(self) -> list[ManagedSkillInstallRead]:
        return self._repository.list()

    def get_install(self, install_id: str) -> ManagedSkillInstallRead | None:
        return self._repository.get(install_id)

    def get_install_status(self, install_id: str) -> ManagedSkillInstallStatus | None:
        record = self.get_install(install_id)
        return record.status if record is not None else None

    def install_bundle(self, request: ManagedSkillInstallRequest) -> ManagedSkillInstallRead:
        record = self.install_to_quarantine(request)
        if record.status is not ManagedSkillInstallStatus.QUARANTINED:
            return record

        record = self.run_cold_validation(record.install_id)
        if record.status is not ManagedSkillInstallStatus.COLD_VALIDATED:
            return record

        return self.promote_skill(record.install_id)

    def install_to_quarantine(self, request: ManagedSkillInstallRequest) -> ManagedSkillInstallRead:
        bundle_dir = Path(request.bundle_dir).expanduser().resolve()
        manifest = self._load_manifest(bundle_dir)
        install_id = create_resource_id("mskill")
        now = utc_now()
        record = ManagedSkillInstallRead(
            install_id=install_id,
            status=ManagedSkillInstallStatus.PENDING,
            skill_id=manifest.skill_id,
            version=manifest.version,
            requested_by=request.requested_by.strip(),
            manifest=manifest,
            quarantine_dir=None,
            active_dir=None,
            checks=[],
            audit_events=[],
            created_at=now,
            updated_at=now,
            metadata={
                **dict(request.metadata),
                "allow_update": request.allow_update,
            },
            error=None,
        )
        self._repository.save(record.install_id, record)

        audit_events = [
            self._audit_event(
                stage="manifest_load",
                status="ok",
                message=f"loaded {self._manifest_name} for {manifest.skill_id}@{manifest.version}",
            )
        ]
        checks = self._run_preflight_checks(
            bundle_dir=bundle_dir,
            manifest=manifest,
            allow_update=request.allow_update,
        )
        if self._failed(checks):
            audit_events.append(
                self._audit_event(stage="preflight", status="failed", message="preflight checks rejected bundle")
            )
            return self._persist_record(
                record,
                status=ManagedSkillInstallStatus.REJECTED,
                checks=checks,
                audit_events=audit_events,
                error="managed skill preflight failed",
            )

        quarantine_parent = self._quarantine_root / install_id
        quarantine_dir = quarantine_parent / manifest.skill_id
        shutil.copytree(bundle_dir, quarantine_dir)
        self._write_runtime_state(
            bundle_dir=quarantine_dir,
            install_id=install_id,
            manifest=manifest,
            status=ManagedSkillInstallStatus.QUARANTINED,
        )
        audit_events.append(
            self._audit_event(
                stage="quarantine_install",
                status="ok",
                message=f"installed bundle into {quarantine_dir}",
            )
        )
        return self._persist_record(
            record,
            status=ManagedSkillInstallStatus.QUARANTINED,
            checks=checks,
            audit_events=audit_events,
            quarantine_dir=str(quarantine_dir),
        )

    def run_cold_validation(self, install_id: str) -> ManagedSkillInstallRead:
        record = self._require_install(install_id)
        if record.status is not ManagedSkillInstallStatus.QUARANTINED:
            raise ValueError(f"cold validation requires quarantined install: {install_id}")
        if not record.quarantine_dir:
            raise ValueError(f"quarantine_dir is missing for install: {install_id}")

        quarantine_dir = Path(record.quarantine_dir).resolve()
        audit_events = list(record.audit_events)
        contract_checks = self._run_contract_checks(
            manifest=record.manifest,
            quarantine_parent=quarantine_dir.parent,
        )
        checks = [*record.checks, *contract_checks]

        if self._failed(contract_checks):
            audit_events.append(
                self._audit_event(
                    stage="cold_validation",
                    status="failed",
                    message="cold validation or contract tests failed",
                )
            )
            return self._persist_record(
                record,
                status=ManagedSkillInstallStatus.REJECTED,
                checks=checks,
                audit_events=audit_events,
                quarantine_dir=str(quarantine_dir),
                error="managed skill cold validation failed",
            )

        self._write_runtime_state(
            bundle_dir=quarantine_dir,
            install_id=record.install_id,
            manifest=record.manifest,
            status=ManagedSkillInstallStatus.COLD_VALIDATED,
        )
        audit_events.append(
            self._audit_event(
                stage="cold_validation",
                status="ok",
                message=f"cold validation passed for {record.skill_id}@{record.version}",
            )
        )
        return self._persist_record(
            record,
            status=ManagedSkillInstallStatus.COLD_VALIDATED,
            checks=checks,
            audit_events=audit_events,
            quarantine_dir=str(quarantine_dir),
            error=None,
        )

    def promote_skill(self, install_id: str) -> ManagedSkillInstallRead:
        record = self._require_install(install_id)
        if record.status is not ManagedSkillInstallStatus.COLD_VALIDATED:
            raise ValueError(f"promotion requires cold_validated install: {install_id}")
        if not record.quarantine_dir:
            raise ValueError(f"quarantine_dir is missing for install: {install_id}")

        quarantine_dir = Path(record.quarantine_dir).resolve()
        checks = list(record.checks)
        audit_events = list(record.audit_events)
        allow_update = bool(record.metadata.get("allow_update", True))

        promote_check, active_dir = self._promote_bundle(
            record=record,
            quarantine_dir=quarantine_dir,
            allow_update=allow_update,
        )
        checks.append(promote_check)
        if not promote_check.passed:
            audit_events.append(
                self._audit_event(stage="promote", status="failed", message=promote_check.detail)
            )
            return self._persist_record(
                record,
                status=ManagedSkillInstallStatus.COLD_VALIDATED,
                checks=checks,
                audit_events=audit_events,
                quarantine_dir=str(quarantine_dir),
                active_dir=str(active_dir) if active_dir is not None else None,
                error=promote_check.detail,
            )

        audit_events.append(
            self._audit_event(stage="promote", status="ok", message=f"promoted skill into {active_dir}")
        )
        return self._persist_record(
            record,
            status=ManagedSkillInstallStatus.PROMOTED,
            checks=checks,
            audit_events=audit_events,
            quarantine_dir=str(quarantine_dir),
            active_dir=str(active_dir) if active_dir is not None else None,
            error=None,
        )

    def _persist_record(
        self,
        record: ManagedSkillInstallRead,
        *,
        status: ManagedSkillInstallStatus,
        checks: list[ManagedSkillCheck],
        audit_events: list[ManagedSkillAuditEventRead],
        quarantine_dir: str | None = None,
        active_dir: str | None = None,
        error: str | None = None,
    ) -> ManagedSkillInstallRead:
        updated = record.model_copy(
            update={
                "status": status,
                "checks": list(checks),
                "audit_events": list(audit_events),
                "quarantine_dir": quarantine_dir if quarantine_dir is not None else record.quarantine_dir,
                "active_dir": active_dir if active_dir is not None else record.active_dir,
                "error": error,
                "updated_at": utc_now(),
            }
        )
        return self._repository.save(updated.install_id, updated)

    def _run_preflight_checks(
        self,
        *,
        bundle_dir: Path,
        manifest: ManagedSkillManifestRead,
        allow_update: bool,
    ) -> list[ManagedSkillCheck]:
        return [
            self._verify_signer_trusted(manifest),
            self._verify_signature(manifest),
            *self._verify_file_hashes(bundle_dir=bundle_dir, manifest=manifest),
            self._verify_capabilities(manifest),
            self._verify_update_policy(manifest, allow_update=allow_update),
        ]

    def _run_contract_checks(
        self,
        *,
        manifest: ManagedSkillManifestRead,
        quarantine_parent: Path,
    ) -> list[ManagedSkillCheck]:
        entrypoint_path = quarantine_parent / manifest.skill_id / manifest.entrypoint
        load_service = OpenClawSkillService(
            repo_root=self._repo_root,
            skill_roots=[quarantine_parent],
            max_skill_file_bytes=self._max_skill_file_bytes,
            max_skills_per_root=32,
            managed_skill_roots=[],
        )
        detail = load_service.get_skill(manifest.skill_id)
        checks = [
            ManagedSkillCheck(
                id="contract.entrypoint_exists",
                passed=entrypoint_path.is_file(),
                detail=str(entrypoint_path),
            ),
            ManagedSkillCheck(
                id="contract.skill_loadable",
                passed=detail is not None,
                detail="skill was loaded via OpenClawSkillService" if detail is not None else "skill was not loadable",
            ),
        ]
        if detail is not None:
            checks.extend(
                [
                    ManagedSkillCheck(
                        id="contract.skill_name_matches_manifest",
                        passed=detail.name == manifest.name,
                        detail=f"loaded={detail.name} manifest={manifest.name}",
                    ),
                    ManagedSkillCheck(
                        id="contract.skill_key_matches_manifest",
                        passed=detail.skill_key == manifest.skill_id,
                        detail=f"loaded={detail.skill_key} manifest={manifest.skill_id}",
                    ),
                    ManagedSkillCheck(
                        id="contract.skill_content_present",
                        passed=bool(detail.content.strip()),
                        detail="skill content was loaded" if detail.content.strip() else "skill content is empty",
                    ),
                ]
            )
        return checks

    def _promote_bundle(
        self,
        *,
        record: ManagedSkillInstallRead,
        quarantine_dir: Path,
        allow_update: bool,
    ) -> tuple[ManagedSkillCheck, Path | None]:
        manifest = record.manifest
        lease_key = f"skill-promote:{manifest.skill_id}"
        active_dir = self._active_root / manifest.skill_id
        try:
            with self._writer_lease.acquire(lease_key, blocking=False):
                if active_dir.exists() and not allow_update:
                    return (
                        ManagedSkillCheck(
                            id="promote.writer_lease_and_policy",
                            passed=False,
                            detail=f"active skill already exists: {active_dir}",
                        ),
                        None,
                    )

                backup_root = self._active_root / "_backup"
                staging_root = self._active_root / "_staging"
                backup_root.mkdir(parents=True, exist_ok=True)
                staging_root.mkdir(parents=True, exist_ok=True)
                staging_dir = staging_root / f"{manifest.skill_id}-{manifest.version}"
                if staging_dir.exists():
                    shutil.rmtree(staging_dir)
                shutil.copytree(quarantine_dir, staging_dir)
                self._write_runtime_state(
                    bundle_dir=staging_dir,
                    install_id=record.install_id,
                    manifest=manifest,
                    status=ManagedSkillInstallStatus.PROMOTED,
                )

                if active_dir.exists():
                    backup_dir = backup_root / f"{manifest.skill_id}-{utc_now().strftime('%Y%m%d%H%M%S')}"
                    if backup_dir.exists():
                        shutil.rmtree(backup_dir)
                    shutil.move(str(active_dir), str(backup_dir))
                shutil.move(str(staging_dir), str(active_dir))
                return (
                    ManagedSkillCheck(
                        id="promote.writer_lease_and_policy",
                        passed=True,
                        detail=f"promoted to {active_dir}",
                    ),
                    active_dir,
                )
        except TimeoutError:
            return (
                ManagedSkillCheck(
                    id="promote.writer_lease_and_policy",
                    passed=False,
                    detail="writer lease is currently held by another skill promotion",
                ),
                None,
            )

    def _verify_signer_trusted(self, manifest: ManagedSkillManifestRead) -> ManagedSkillCheck:
        trusted = manifest.signer_id in self._trusted_signers
        return ManagedSkillCheck(
            id="preflight.signer_trusted",
            passed=trusted,
            detail="trusted signer configured" if trusted else f"unknown signer_id: {manifest.signer_id}",
        )

    def _verify_signature(self, manifest: ManagedSkillManifestRead) -> ManagedSkillCheck:
        signer_value = self._trusted_signers.get(manifest.signer_id)
        if not signer_value:
            return ManagedSkillCheck(
                id="preflight.signature_valid",
                passed=False,
                detail=f"missing public key for signer_id={manifest.signer_id}",
            )
        try:
            public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(signer_value, validate=True))
            signature = base64.b64decode(manifest.signature, validate=True)
            public_key.verify(signature, self._canonical_manifest_bytes(manifest))
            return ManagedSkillCheck(
                id="preflight.signature_valid",
                passed=True,
                detail="ed25519 signature verified",
            )
        except (ValueError, InvalidSignature):
            return ManagedSkillCheck(
                id="preflight.signature_valid",
                passed=False,
                detail="managed skill signature verification failed",
            )

    def _verify_file_hashes(
        self,
        *,
        bundle_dir: Path,
        manifest: ManagedSkillManifestRead,
    ) -> list[ManagedSkillCheck]:
        declared = {item.path: item.sha256 for item in manifest.files}
        actual_files: dict[str, str] = {}
        symlink_paths: list[str] = []
        for path in sorted(bundle_dir.rglob("*")):
            if path.is_dir():
                continue
            relative = path.relative_to(bundle_dir).as_posix()
            if relative == self._manifest_name:
                continue
            if path.is_symlink():
                symlink_paths.append(relative)
                continue
            actual_files[relative] = self._sha256(path)

        missing = sorted(set(declared) - set(actual_files))
        extra = sorted(set(actual_files) - set(declared))
        mismatched = sorted(
            path for path, digest in declared.items() if path in actual_files and actual_files[path] != digest
        )
        return [
            ManagedSkillCheck(
                id="preflight.no_symlink_files",
                passed=not symlink_paths,
                detail="; ".join(symlink_paths) if symlink_paths else "ok",
            ),
            ManagedSkillCheck(
                id="preflight.files_declared",
                passed=not missing and not extra,
                detail=f"missing={missing or ['-']} extra={extra or ['-']}",
            ),
            ManagedSkillCheck(
                id="preflight.hashes_match",
                passed=not mismatched,
                detail="; ".join(mismatched) if mismatched else "ok",
            ),
        ]

    def _verify_capabilities(self, manifest: ManagedSkillManifestRead) -> ManagedSkillCheck:
        unknown = sorted(
            capability for capability in manifest.capabilities if capability not in self._allowed_capabilities
        )
        return ManagedSkillCheck(
            id="preflight.capabilities_allowed",
            passed=not unknown,
            detail="; ".join(unknown) if unknown else "ok",
        )

    def _verify_update_policy(
        self,
        manifest: ManagedSkillManifestRead,
        *,
        allow_update: bool,
    ) -> ManagedSkillCheck:
        active_dir = self._active_root / manifest.skill_id
        if not active_dir.exists():
            return ManagedSkillCheck(
                id="preflight.update_policy",
                passed=True,
                detail="no active skill installed",
            )
        active_manifest_path = active_dir / self._manifest_name
        if not active_manifest_path.is_file():
            return ManagedSkillCheck(
                id="preflight.update_policy",
                passed=False,
                detail=f"existing active skill is missing {self._manifest_name}",
            )
        active_manifest = ManagedSkillManifestRead.model_validate_json(
            active_manifest_path.read_text(encoding="utf-8")
        )
        if active_manifest.version == manifest.version:
            return ManagedSkillCheck(
                id="preflight.update_policy",
                passed=False,
                detail=f"skill {manifest.skill_id}@{manifest.version} is already active",
            )
        if not allow_update:
            return ManagedSkillCheck(
                id="preflight.update_policy",
                passed=False,
                detail=f"active skill {manifest.skill_id}@{active_manifest.version} already exists",
            )
        return ManagedSkillCheck(
            id="preflight.update_policy",
            passed=True,
            detail=f"update allowed from {active_manifest.version} to {manifest.version}",
        )

    def _load_manifest(self, bundle_dir: Path) -> ManagedSkillManifestRead:
        if not bundle_dir.is_dir():
            raise FileNotFoundError(f"managed skill bundle directory not found: {bundle_dir}")
        manifest_path = bundle_dir / self._manifest_name
        if not manifest_path.is_file():
            raise FileNotFoundError(f"managed skill manifest not found: {manifest_path}")
        return ManagedSkillManifestRead.model_validate_json(manifest_path.read_text(encoding="utf-8"))

    def _write_runtime_state(
        self,
        *,
        bundle_dir: Path,
        install_id: str,
        manifest: ManagedSkillManifestRead,
        status: ManagedSkillInstallStatus,
    ) -> None:
        state = ManagedSkillRuntimeStateRead(
            install_id=install_id,
            skill_id=manifest.skill_id,
            version=manifest.version,
            status=status,
            updated_at=utc_now(),
        )
        (bundle_dir / self._runtime_state_name).write_text(
            json.dumps(state.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _canonical_manifest_bytes(self, manifest: ManagedSkillManifestRead) -> bytes:
        payload: dict[str, Any] = manifest.model_dump(mode="json")
        payload.pop("signature", None)
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def _sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65_536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _audit_event(self, *, stage: str, status: str, message: str) -> ManagedSkillAuditEventRead:
        return ManagedSkillAuditEventRead(
            stage=stage,
            status=status,
            message=message,
            created_at=utc_now(),
        )

    def _require_install(self, install_id: str) -> ManagedSkillInstallRead:
        record = self.get_install(install_id)
        if record is None:
            raise KeyError(f"managed skill install not found: {install_id}")
        return record

    @staticmethod
    def _failed(checks: list[ManagedSkillCheck]) -> bool:
        return any(not item.passed for item in checks)
