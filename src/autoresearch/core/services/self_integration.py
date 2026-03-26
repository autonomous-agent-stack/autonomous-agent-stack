from __future__ import annotations

import os
import re
from urllib.parse import urlparse

from autoresearch.shared.models import (
    IntegrationDiscoverRequest,
    IntegrationDiscoveryRead,
    IntegrationPromoteRequest,
    IntegrationPromotionRead,
    IntegrationPrototypeRead,
    IntegrationPrototypeRequest,
    JobStatus,
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

        now = utc_now()
        prototype = IntegrationPrototypeRead(
            prototype_id=create_resource_id("proto"),
            discovery_id=request.discovery_id,
            adapter_name=adapter_name,
            sandbox_backend=request.sandbox_backend,
            dry_run=request.dry_run,
            status=JobStatus.CREATED,
            planned_files=[
                f"src/autoresearch/adapters/{adapter_name}/__init__.py",
                f"src/autoresearch/adapters/{adapter_name}/adapter_node.py",
                f"tests/integration/{adapter_name}_smoke_test.py",
            ],
            validation_checks=[
                "contract mapping for upstream inputs/outputs",
                "sandbox smoke test in Docker/Colima",
                "pre-execution cleanup for ._* and .DS_Store",
            ],
            summary=(
                "Prototype plan generated. Next step: implement adapter in sandbox and "
                "run regression before promotion."
            ),
            created_at=now,
            updated_at=now,
            metadata={
                **request.metadata,
                "source_url": discovery.source_url,
                "source_kind": discovery.source_kind,
            },
            error=None,
        )
        return self._prototype_repository.save(prototype.prototype_id, prototype)

    def get_prototype(self, prototype_id: str) -> IntegrationPrototypeRead | None:
        return self._prototype_repository.get(prototype_id)

    def promote(self, request: IntegrationPromoteRequest) -> IntegrationPromotionRead:
        prototype = self.get_prototype(request.prototype_id)
        if prototype is None:
            raise KeyError(f"prototype not found: {request.prototype_id}")

        now = utc_now()
        promotion = IntegrationPromotionRead(
            promotion_id=create_resource_id("prom"),
            prototype_id=request.prototype_id,
            rollout_mode=request.rollout_mode,
            status=JobStatus.CREATED,
            decision="pending",
            topology_patch_preview={
                "rollout_mode": request.rollout_mode,
                "graph_changes": [
                    f"register AdapterNode<{prototype.adapter_name}>",
                    "enable shadow comparison with baseline flow",
                    "gate production cutover behind regression score threshold",
                ],
            },
            rollback_plan=[
                "disable integration feature flag",
                "restore previous graph binding",
                "replay latest stable topology snapshot",
            ],
            summary=(
                "Promotion plan created. Execute side-by-side regression and approve "
                "manually before production cutover."
            ),
            created_at=now,
            updated_at=now,
            metadata={
                **request.metadata,
                "adapter_name": prototype.adapter_name,
                "dry_run": prototype.dry_run,
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
