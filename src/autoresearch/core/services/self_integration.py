from __future__ import annotations

import os
import re
from urllib.parse import urlparse

from autoresearch.shared.models import (
    DependencyRequest,
    EvaluationGateRead,
    IntegrationDiscoverRequest,
    IntegrationDiscoveryRead,
    IntegrationPromoteRequest,
    IntegrationPromotionRead,
    IntegrationPrototypeRead,
    IntegrationPrototypeRequest,
    IntegrationSecureFetchRequest,
    JobStatus,
    OfflineSandboxPolicyRead,
    SecureDependencyArtifactRead,
    SecureFetchPlanRead,
    utc_now,
)
from autoresearch.shared.store import Repository, create_resource_id


class SelfIntegrationService:
    """P4 self-integration protocol service (minimal API skeleton)."""

    def __init__(
        self,
        discovery_repository: Repository[IntegrationDiscoveryRead],
        prototype_repository: Repository[IntegrationPrototypeRead],
        promotion_repository: Repository[IntegrationPromotionRead],
    ) -> None:
        self._discovery_repository = discovery_repository
        self._prototype_repository = prototype_repository
        self._promotion_repository = promotion_repository

    def discover(self, request: IntegrationDiscoverRequest) -> IntegrationDiscoveryRead:
        source_url = request.source_url.strip()
        if not source_url:
            raise ValueError("source_url cannot be empty")
        self._validate_source_trust(
            source_url=source_url,
            source_kind=request.source_kind,
            ref=request.ref,
        )

        now = utc_now()
        discovery = IntegrationDiscoveryRead(
            discovery_id=create_resource_id("disc"),
            source_url=source_url,
            source_kind=request.source_kind,
            ref=request.ref,
            status=JobStatus.CREATED,
            candidate_adapter_id=self._candidate_adapter_id(source_url),
            detected_capabilities=self._infer_capabilities(
                source_url=source_url,
                source_kind=request.source_kind,
            ),
            summary=(
                "Discovery accepted. Next step: call "
                "POST /api/v1/integrations/prototype with discovery_id."
            ),
            created_at=now,
            updated_at=now,
            metadata=request.metadata,
            error=None,
        )
        return self._discovery_repository.save(discovery.discovery_id, discovery)

    def get_discovery(self, discovery_id: str) -> IntegrationDiscoveryRead | None:
        return self._discovery_repository.get(discovery_id)

    def prototype(self, request: IntegrationPrototypeRequest) -> IntegrationPrototypeRead:
        discovery = self.get_discovery(request.discovery_id)
        if discovery is None:
            raise KeyError(f"discovery not found: {request.discovery_id}")

        adapter_name = self._normalize_identifier(request.adapter_name)
        if not adapter_name:
            raise ValueError("adapter_name must contain alphanumeric characters")

        trace_id = create_resource_id("trace")
        secure_fetch_plan = self._build_secure_fetch_plan(
            dependencies=request.dependency_requests,
            policy_version=request.policy_version,
            trace_id=trace_id,
        )
        offline_sandbox_policy = OfflineSandboxPolicyRead(
            readonly_mounts=[secure_fetch_plan.readonly_mount_dir],
        )
        evaluation_gate = EvaluationGateRead(
            required_checks=self._default_evaluation_checks(),
            status="pending",
        )

        if secure_fetch_plan.status == "pending":
            summary = (
                "Prototype plan generated. Next step: complete secure fetch on host via "
                "POST /api/v1/integrations/prototype/{prototype_id}/secure-fetch before promotion."
            )
        else:
            summary = (
                "Prototype plan generated. Next step: run offline sandbox regression and "
                "submit evaluation evidence before promotion."
            )

        now = utc_now()
        prototype = IntegrationPrototypeRead(
            prototype_id=create_resource_id("proto"),
            discovery_id=request.discovery_id,
            adapter_name=adapter_name,
            sandbox_backend=request.sandbox_backend,
            dry_run=request.dry_run,
            status=JobStatus.CREATED,
            dependency_requests=request.dependency_requests,
            secure_fetch_plan=secure_fetch_plan,
            offline_sandbox_policy=offline_sandbox_policy,
            evaluation_gate=evaluation_gate,
            trace_id=trace_id,
            planned_files=[
                f"src/autoresearch/adapters/{adapter_name}/__init__.py",
                f"src/autoresearch/adapters/{adapter_name}/adapter_node.py",
                f"tests/integration/{adapter_name}_smoke_test.py",
            ],
            validation_checks=[
                "secure fetch audit completed on host proxy with pip-compile --require-hashes",
                "offline sandbox policy enforced (NETWORK=none + readonly mounts)",
                "contract mapping for upstream inputs/outputs",
                "sandbox smoke test in Docker/Colima",
                "pre-execution cleanup for ._* and .DS_Store",
            ],
            summary=summary,
            created_at=now,
            updated_at=now,
            metadata={
                **request.metadata,
                "source_url": discovery.source_url,
                "source_kind": discovery.source_kind,
                "policy_version": request.policy_version,
            },
            error=None,
        )
        return self._prototype_repository.save(prototype.prototype_id, prototype)

    def get_prototype(self, prototype_id: str) -> IntegrationPrototypeRead | None:
        return self._prototype_repository.get(prototype_id)

    def secure_fetch(
        self,
        prototype_id: str,
        request: IntegrationSecureFetchRequest,
    ) -> IntegrationPrototypeRead:
        prototype = self.get_prototype(prototype_id)
        if prototype is None:
            raise KeyError(f"prototype not found: {prototype_id}")

        expected_packages = {dep.package for dep in prototype.dependency_requests}
        provided_packages = {artifact.package for artifact in request.audited_artifacts}

        if not expected_packages:
            if request.audited_artifacts:
                raise ValueError("prototype has no dependency requests; audited_artifacts must be empty")
            secure_fetch_status = "skipped"
        else:
            if provided_packages != expected_packages:
                missing = sorted(expected_packages - provided_packages)
                unexpected = sorted(provided_packages - expected_packages)
                raise ValueError(
                    "audited artifacts do not match requested dependencies; "
                    f"missing={missing}, unexpected={unexpected}"
                )
            secure_fetch_status = "audited"

        now = utc_now()
        mount_dir = (
            request.mount_dir.strip()
            if request.mount_dir and request.mount_dir.strip()
            else prototype.secure_fetch_plan.readonly_mount_dir
        )
        hash_manifest = self._merge_hash_manifest(
            request_manifest=request.hash_manifest,
            artifacts=request.audited_artifacts,
        )
        sbom = request.sbom or self._build_default_sbom(request.audited_artifacts)
        audit_notes = [
            *prototype.secure_fetch_plan.audit_notes,
            *request.notes,
            (
                "Security_Auditor completed host-side dependency verification "
                f"({request.auditor}) at {now.isoformat()}."
            ),
        ]

        secure_fetch_plan = prototype.secure_fetch_plan.model_copy(
            update={
                "status": secure_fetch_status,
                "readonly_mount_dir": mount_dir,
                "artifacts": request.audited_artifacts,
                "hash_manifest": hash_manifest,
                "sbom": sbom,
                "audit_notes": audit_notes,
                "policy_version": request.policy_version or prototype.secure_fetch_plan.policy_version,
                "audited_at": now if secure_fetch_status == "audited" else prototype.secure_fetch_plan.audited_at,
            }
        )
        offline_sandbox_policy = prototype.offline_sandbox_policy.model_copy(
            update={"readonly_mounts": [mount_dir]}
        )

        updated_prototype = prototype.model_copy(
            update={
                "secure_fetch_plan": secure_fetch_plan,
                "offline_sandbox_policy": offline_sandbox_policy,
                "updated_at": now,
                "summary": (
                    "Secure fetch completed. Next step: run offline integration tests and "
                    "submit evaluation evidence for promotion."
                ),
                "metadata": {
                    **prototype.metadata,
                    "last_secure_fetch_auditor": request.auditor,
                    "secure_fetch_policy_version": request.policy_version,
                },
            }
        )
        return self._prototype_repository.save(updated_prototype.prototype_id, updated_prototype)

    def promote(self, request: IntegrationPromoteRequest) -> IntegrationPromotionRead:
        prototype = self.get_prototype(request.prototype_id)
        if prototype is None:
            raise KeyError(f"prototype not found: {request.prototype_id}")

        if prototype.secure_fetch_plan.status not in {"audited", "skipped"}:
            raise ValueError(
                "secure fetch is incomplete; run host-side audit first and mount audited artifacts"
            )

        gate_status, passed_checks, failed_checks, missing_checks = self._evaluate_gate(
            required_checks=prototype.evaluation_gate.required_checks,
            evaluation_results=request.evaluation_results,
        )
        if request.rollout_mode == "full" and gate_status != "passed":
            raise ValueError(
                "promotion gate failed for full rollout; required checks must be fully passed"
            )
        if request.rollout_mode == "canary" and gate_status == "failed":
            raise ValueError("promotion gate failed; canary rollout blocked by failing checks")

        now = utc_now()
        updated_prototype = prototype.model_copy(
            update={
                "evaluation_gate": prototype.evaluation_gate.model_copy(
                    update={
                        "status": gate_status,
                        "passed_checks": passed_checks,
                        "failed_checks": failed_checks,
                    }
                ),
                "updated_at": now,
            }
        )
        self._prototype_repository.save(updated_prototype.prototype_id, updated_prototype)

        if request.approval_mode == "auto_if_green" and gate_status == "passed":
            decision = "approved"
            promotion_status = JobStatus.COMPLETED
            summary = (
                "Promotion auto-approved because secure fetch is audited and all evaluation "
                "checks passed."
            )
        else:
            decision = "pending"
            promotion_status = JobStatus.CREATED
            summary = (
                "Promotion plan created. Execute side-by-side regression and approve manually "
                "before production cutover."
            )

        promotion = IntegrationPromotionRead(
            promotion_id=create_resource_id("prom"),
            prototype_id=request.prototype_id,
            rollout_mode=request.rollout_mode,
            status=promotion_status,
            decision=decision,
            gate_status=gate_status,
            required_checks=prototype.evaluation_gate.required_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            missing_checks=missing_checks,
            trace_id=prototype.trace_id,
            topology_patch_preview={
                "rollout_mode": request.rollout_mode,
                "graph_changes": [
                    f"register AdapterNode<{prototype.adapter_name}>",
                    "enable shadow comparison with baseline flow",
                    "gate production cutover behind regression score threshold",
                    "enforce audited dependency mount in offline sandbox",
                ],
            },
            rollback_plan=[
                "disable integration feature flag",
                "restore previous graph binding",
                "replay latest stable topology snapshot",
                "revert to previous signed runtime artifact",
            ],
            summary=summary,
            created_at=now,
            updated_at=now,
            metadata={
                **request.metadata,
                "adapter_name": prototype.adapter_name,
                "dry_run": prototype.dry_run,
                "secure_fetch_status": prototype.secure_fetch_plan.status,
                "approval_mode": request.approval_mode,
            },
            error=None,
        )
        return self._promotion_repository.save(promotion.promotion_id, promotion)

    @staticmethod
    def _validate_source_trust(source_url: str, source_kind: str, ref: str | None) -> None:
        parsed = urlparse(source_url)
        scheme = (parsed.scheme or "").lower()
        host = (parsed.hostname or "").lower()

        if scheme != "https":
            raise ValueError("untrusted source: only https source_url is allowed")

        if source_kind in {"repository", "mixed"}:
            # 防止伪造仓库源，默认仅允许 GitHub 主域和 SSH 域。
            allowed_hosts = {"github.com", "www.github.com"}
            if host not in allowed_hosts:
                raise ValueError(
                    f"untrusted repository host: {host or '<empty>'}; allowed hosts: github.com"
                )

            # 默认要求 commit pin，避免分支漂移被投毒。可通过环境变量临时放宽。
            require_pinned_ref = (
                os.getenv("AUTORESEARCH_REQUIRE_PINNED_REPO_REF", "1").strip().lower()
                not in {"0", "false", "no"}
            )
            if require_pinned_ref and not SelfIntegrationService._looks_like_commit_sha(ref):
                raise ValueError(
                    "untrusted repository ref: use full commit SHA (40 hex chars) to pin source"
                )

    @staticmethod
    def _looks_like_commit_sha(ref: str | None) -> bool:
        if ref is None:
            return False
        return bool(re.fullmatch(r"[0-9a-fA-F]{40}", ref.strip()))

    @staticmethod
    def _candidate_adapter_id(source_url: str) -> str:
        parsed = urlparse(source_url)
        path_tail = parsed.path.rstrip("/").split("/")[-1] if parsed.path else ""
        if path_tail.endswith(".git"):
            path_tail = path_tail[: -len(".git")]
        normalized = SelfIntegrationService._normalize_identifier(path_tail)
        return normalized or "external_adapter"

    @staticmethod
    def _normalize_identifier(raw: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9]+", "_", raw.strip().lower())
        normalized = re.sub(r"_+", "_", normalized).strip("_")
        return normalized

    @staticmethod
    def _infer_capabilities(source_url: str, source_kind: str) -> list[str]:
        capabilities: list[str] = []
        if source_kind in {"repository", "mixed"}:
            capabilities.append("repository_structure_discovery")
        if source_kind in {"api_docs", "mixed"}:
            capabilities.append("api_contract_mapping")

        lower_url = source_url.lower()
        if "openclaw" in lower_url:
            capabilities.append("openclaw_compat_adapter")
        if "mcp" in lower_url:
            capabilities.append("mcp_tool_bridge")
        if not capabilities:
            capabilities.append("adapter_scaffold_generation")
        return capabilities

    @staticmethod
    def _default_evaluation_checks() -> list[str]:
        return [
            "unit_test_pass_rate",
            "security_scan_clean",
            "behavior_regression_ok",
            "performance_regression_ok",
            "policy_compliance_ok",
            "reproducible_build_ok",
        ]

    @staticmethod
    def _build_secure_fetch_plan(
        dependencies: list[DependencyRequest],
        policy_version: str,
        trace_id: str,
    ) -> SecureFetchPlanRead:
        request_id = create_resource_id("dep")
        if not dependencies:
            return SecureFetchPlanRead(
                request_id=request_id,
                status="skipped",
                audit_notes=["No third-party dependencies requested; secure fetch skipped."],
                trace_id=trace_id,
                policy_version=policy_version,
            )

        dependency_preview = [
            SelfIntegrationService._dependency_spec(dep)
            for dep in dependencies
        ]
        return SecureFetchPlanRead(
            request_id=request_id,
            status="pending",
            audit_commands=[
                "pip-compile --require-hashes requirements.in",
                "pip download --require-hashes -r requirements.txt --dest /var/secure-wheelhouse",
                "sha256sum /var/secure-wheelhouse/*.whl > hash_manifest.txt",
            ],
            audit_notes=[
                "Sandbox must request dependencies via host proxy only.",
                "Security_Auditor validates hashes before readonly mount into sandbox.",
                f"Requested dependencies: {', '.join(dependency_preview)}",
            ],
            trace_id=trace_id,
            policy_version=policy_version,
        )

    @staticmethod
    def _dependency_spec(dependency: DependencyRequest) -> str:
        if dependency.version_spec:
            return f"{dependency.package}{dependency.version_spec}"
        return dependency.package

    @staticmethod
    def _merge_hash_manifest(
        request_manifest: dict[str, str],
        artifacts: list[SecureDependencyArtifactRead],
    ) -> dict[str, str]:
        manifest = {package: digest for package, digest in request_manifest.items()}
        for artifact in artifacts:
            manifest.setdefault(artifact.package, artifact.sha256)

        for artifact in artifacts:
            manifest_digest = manifest.get(artifact.package, "").strip().lower()
            if manifest_digest != artifact.sha256:
                raise ValueError(
                    "hash_manifest does not match artifact digest for package "
                    f"{artifact.package}"
                )
        return manifest

    @staticmethod
    def _build_default_sbom(artifacts: list[SecureDependencyArtifactRead]) -> dict:
        return {
            "format": "cyclonedx-lite",
            "generated_by": "security_auditor",
            "components": [
                {
                    "type": "library",
                    "name": artifact.package,
                    "version_spec": artifact.version_spec,
                    "artifact": artifact.wheel_filename,
                    "sha256": artifact.sha256,
                }
                for artifact in artifacts
            ],
        }

    @staticmethod
    def _evaluate_gate(
        required_checks: list[str],
        evaluation_results: dict[str, bool],
    ) -> tuple[str, list[str], list[str], list[str]]:
        passed_checks = [check for check in required_checks if evaluation_results.get(check) is True]
        failed_checks = [check for check in required_checks if evaluation_results.get(check) is False]
        missing_checks = [check for check in required_checks if check not in evaluation_results]

        if failed_checks:
            status = "failed"
        elif not required_checks or not missing_checks:
            status = "passed"
        else:
            status = "pending"
        return status, passed_checks, failed_checks, missing_checks
