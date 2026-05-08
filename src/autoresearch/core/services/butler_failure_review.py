from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from autoresearch.github_assistant.config import load_yaml_object
from autoresearch.core.services.session_events import SessionEventService
from autoresearch.shared.models import SessionEventCreateRequest, StrictModel, utc_now
from autoresearch.shared.store import create_resource_id


ButlerFailureKind = Literal[
    "route_mismatch",
    "dependency_missing",
    "auth_required",
    "quota_exceeded",
    "permission_denied",
    "permission_required",
    "worker_contract_error",
    "contract_error",
    "runtime_unavailable",
    "needs_user_decision",
    "unknown_complex",
]


class ButlerFailureReviewRequest(StrictModel):
    message: str = ""
    task_id: str | None = None
    run_id: str | None = None
    capability_id: str | None = None
    route_decision: dict[str, Any] | None = None
    worker_error: str | None = None
    worker_message: str | None = None
    worker_result: dict[str, Any] | None = None
    worker_metrics: dict[str, Any] | None = None
    session_id: str | None = None
    usage_entry_id: str | None = None
    doctor_snapshot: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ButlerFailureReviewRead(StrictModel):
    review_id: str
    failure_kind: ButlerFailureKind
    diagnosis: str
    suggested_route: str | None = None
    candidate_skill_summary: str | None = None
    rule_candidate: dict[str, Any] | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    task_id: str | None = None
    run_id: str | None = None
    capability_id: str | None = None
    usage_entry_id: str | None = None
    hermes_review_run_id: str | None = None
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class ButlerFailureReviewService:
    """Local Butler failure review and rule-candidate capture."""

    def __init__(
        self,
        *,
        session_events: SessionEventService | None = None,
        rule_candidates_path: Path | None = None,
    ) -> None:
        self._session_events = session_events
        self._rule_candidates_path = rule_candidates_path

    def review(self, request: ButlerFailureReviewRequest) -> ButlerFailureReviewRead:
        failure_kind = classify_butler_failure(request)
        review_id = create_resource_id("failure_review")
        diagnosis, suggested_route, skill_summary, confidence = _review_text_for(
            failure_kind=failure_kind,
            request=request,
        )
        rule_candidate = _rule_candidate_for(
            review_id=review_id,
            failure_kind=failure_kind,
            request=request,
            suggested_route=suggested_route,
            candidate_skill_summary=skill_summary,
            confidence=confidence,
        )
        if rule_candidate is not None:
            rule_candidate = self._persist_rule_candidate(rule_candidate)

        review = ButlerFailureReviewRead(
            review_id=review_id,
            failure_kind=failure_kind,
            diagnosis=diagnosis,
            suggested_route=suggested_route,
            candidate_skill_summary=skill_summary,
            rule_candidate=rule_candidate,
            confidence=confidence,
            task_id=request.task_id,
            run_id=request.run_id,
            capability_id=request.capability_id,
            usage_entry_id=request.usage_entry_id,
            created_at=utc_now(),
            metadata={
                "source": "butler_failure_review",
                "review_action": "hermes.failure_review",
                "hermes_review_status": "not_invoked",
                "doctor_snapshot": request.doctor_snapshot or {},
                **dict(request.metadata),
            },
        )
        self._record_review_event(review, request)
        return review

    def _record_review_event(
        self,
        review: ButlerFailureReviewRead,
        request: ButlerFailureReviewRequest,
    ) -> None:
        if self._session_events is None or not request.session_id:
            return
        self._session_events.append(
            SessionEventCreateRequest(
                session_id=request.session_id,
                source="butler_failure_review",
                event_type="butler.failure_reviewed",
                role="status",
                content=f"Butler failure reviewed: {review.failure_kind}",
                status=review.failure_kind,
                runtime_id="local",
                run_id=request.run_id,
                idempotency_key=f"butler-failure-review:{review.review_id}",
                metadata=review.model_dump(mode="json"),
            )
        )

    def _persist_rule_candidate(self, candidate: dict[str, Any]) -> dict[str, Any]:
        path = self._rule_candidates_path
        if path is None:
            return candidate
        current = _load_rule_candidates(path)
        candidates = list(current.get("rule_candidates") or [])
        if not any(item.get("candidate_id") == candidate.get("candidate_id") for item in candidates if isinstance(item, dict)):
            candidates.append(candidate)
        current["rule_candidates"] = candidates
        try:
            import yaml  # type: ignore

            text = yaml.safe_dump(current, sort_keys=False, allow_unicode=True)
        except Exception:
            text = json.dumps(current, ensure_ascii=False, indent=2) + "\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return {**candidate, "candidate_path": str(path)}


def classify_butler_failure(request: ButlerFailureReviewRequest) -> ButlerFailureKind:
    evidence = _evidence_text(request)
    metadata = request.metadata if isinstance(request.metadata, dict) else {}
    if metadata.get("route_mismatch") or metadata.get("expected_capability_id"):
        return "route_mismatch"
    if any(
        token in evidence
        for token in (
            "binary_missing",
            "collector_missing",
            "executable not found",
            "executable path not found",
            "hermes executable",
            "command not found",
            "not on path",
        )
    ):
        return "dependency_missing"
    if any(token in evidence for token in ("collector_auth_failed", "auth_required", "login required", "not authenticated")):
        return "auth_required"
    if "quota exceeded" in evidence or "over quota" in evidence or "quota exhausted" in evidence:
        return "quota_exceeded"
    if any(token in evidence for token in ("permission_denied", "permission denied", "not allowed", "blocked by policy", "approval_required")):
        return "permission_denied"
    if any(
        token in evidence
        for token in (
            "worker_contract_error",
            "validationerror",
            "field required",
            "missing field",
            "payload missing",
            "contract",
            "model_validate",
            "pydantic",
        )
    ):
        return "worker_contract_error"
    if any(
        token in evidence
        for token in (
            "runtime_unavailable",
            "adapter_missing",
            "runtime adapter",
            "not configured on this worker",
            "interactive_bridge_unavailable",
        )
    ):
        return "runtime_unavailable"
    if any(token in evidence for token in ("needs_user_decision", "ambiguous", "ask user")):
        return "needs_user_decision"
    return "unknown_complex"


def _review_text_for(
    *,
    failure_kind: ButlerFailureKind,
    request: ButlerFailureReviewRequest,
) -> tuple[str, str | None, str | None, float]:
    if failure_kind == "dependency_missing":
        return (
            "Hermes 或本地运行时依赖缺失，任务不应继续重试同一 worker 路径。 / "
            "Hermes or a local runtime dependency is missing, so the same worker path should not be retried.",
            "Return a local diagnostic and surface doctor readiness before retry.",
            "Summarize missing runtime dependencies and route to local diagnostics first.",
            0.92,
        )
    if failure_kind == "worker_contract_error":
        return (
            "Worker payload 与执行契约不匹配，需要修正 capability adapter 或 worker contract。 / "
            "The worker payload does not match the execution contract; fix the capability adapter or worker contract.",
            "Repair the capability payload contract before requeueing.",
            "Capture required payload fields and validate before worker dispatch.",
            0.88,
        )
    if failure_kind == "contract_error":
        return (
            "执行输入与能力契约不匹配，需要修正 adapter 或请求参数。 / "
            "The execution input does not match the capability contract; fix the adapter or request parameters.",
            "Repair the capability contract before retrying.",
            "Validate required request fields before worker dispatch.",
            0.88,
        )
    if failure_kind == "auth_required":
        return (
            "本机登录态或凭据需要恢复，任务应暂停并给用户可继续的恢复动作。 / "
            "Local auth or credentials need recovery; pause the task and show resumable actions.",
            "Pause for auth recovery and requeue after the user confirms.",
            "Explain auth recovery steps and preserve the original run evidence.",
            0.9,
        )
    if failure_kind == "quota_exceeded":
        return (
            "请求被额度治理拒绝，不能交给 Hermes 执行业务绕过治理。 / "
            "The request was rejected by quota governance and must not be handed to Hermes for execution.",
            "Return quota denial with usage entry details.",
            "Explain quota denial and next eligible retry window.",
            0.9,
        )
    if failure_kind == "permission_denied":
        return (
            "请求被权限或审批策略阻断，应保留治理结果而非降级执行业务。 / "
            "The request was blocked by permission or approval policy; preserve the governance result instead of fallback execution.",
            "Return permission denial or approval-required state.",
            "Explain permission denial and required approval path.",
            0.9,
        )
    if failure_kind == "permission_required":
        return (
            "任务需要额外权限或审批，不能由 Hermes 直接绕过。 / "
            "The task needs additional permission or approval; Hermes must not bypass it.",
            "Return an approval-required state.",
            "Explain the permission or approval path.",
            0.9,
        )
    if failure_kind == "runtime_unavailable":
        return (
            "目标 runtime 未配置或不可用，需要暴露 readiness 而不是静默失败。 / "
            "The target runtime is not configured or unavailable; expose readiness instead of failing opaquely.",
            "Route to local readiness diagnosis.",
            "Summarize runtime readiness checks and operator action.",
            0.84,
        )
    if failure_kind == "route_mismatch":
        return (
            "规则路由与用户意图不匹配，可生成候选规则等待安全审计。 / "
            "The rule route did not match the user intent; create a candidate rule for security audit.",
            str(request.metadata.get("suggested_route") or "review rule candidate"),
            "Derive a narrow routing rule from the failed message and observed correction.",
            0.78,
        )
    if failure_kind == "needs_user_decision":
        return (
            "当前证据显示存在产品或权限选择，需要向用户确认后再继续。 / "
            "The evidence indicates a product or permission choice; ask the user before continuing.",
            "Ask a concise user question and keep the run resumable.",
            "State the smallest decision needed to continue.",
            0.82,
        )
    return (
        "失败证据不足以安全自动修复，保留本地复盘摘要供人工判断。 / "
        "The evidence is insufficient for safe automatic repair; keep a local review summary for human judgment.",
        "Keep local diagnosis and avoid automatic business fallback.",
        None,
        0.45,
    )


def _rule_candidate_for(
    *,
    review_id: str,
    failure_kind: ButlerFailureKind,
    request: ButlerFailureReviewRequest,
    suggested_route: str | None,
    candidate_skill_summary: str | None,
    confidence: float,
) -> dict[str, Any] | None:
    if failure_kind != "route_mismatch":
        return None
    message = str(request.message or request.worker_message or "").strip()
    if not message:
        return None
    return {
        "candidate_id": create_resource_id("rule_candidate"),
        "source": "butler_failure_review",
        "status": "proposed",
        "review_id": review_id,
        "match": {"message_example": message[:500]},
        "suggested_route": suggested_route,
        "candidate_skill_summary": candidate_skill_summary,
        "confidence": confidence,
        "created_at": utc_now().isoformat(),
        "metadata": {
            "failure_kind": failure_kind,
            "task_id": request.task_id,
            "run_id": request.run_id,
            "capability_id": request.capability_id,
        },
    }


def _evidence_text(request: ButlerFailureReviewRequest) -> str:
    payload = {
        "message": request.message,
        "worker_error": request.worker_error,
        "worker_message": request.worker_message,
        "worker_result": request.worker_result,
        "worker_metrics": request.worker_metrics,
        "route_decision": request.route_decision,
        "doctor_snapshot": request.doctor_snapshot,
        "metadata": request.metadata,
        "capability_id": request.capability_id,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).lower()


def _load_rule_candidates(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "version": "1",
            "description": "管家候选规则登记表 / Butler rule candidate registry",
            "rule_candidates": [],
        }
    try:
        payload = load_yaml_object(path)
    except Exception:
        return {
            "version": "1",
            "description": "管家候选规则登记表 / Butler rule candidate registry",
            "rule_candidates": [],
        }
    if not isinstance(payload.get("rule_candidates"), list):
        payload["rule_candidates"] = []
    payload.setdefault("version", "1")
    payload.setdefault("description", "管家候选规则登记表 / Butler rule candidate registry")
    return payload
