from __future__ import annotations

import asyncio
import json
import os
import re
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from autoresearch.core.services.butler_router import ButlerClassification, ButlerIntentRouter, ButlerTaskType


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ButlerRoute(StrEnum):
    DIRECT = "direct"
    WORKER = "worker"
    HERMES = "hermes"
    REJECT = "reject"


class ButlerDispatchSource(StrEnum):
    RULE = "rule"
    MODEL = "model"
    ESCALATION = "escalation"


class ButlerModelBackend(Protocol):
    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs: Any,
    ) -> str: ...


class ButlerModelFillDecision(StrictModel):
    task_type: str = ButlerTaskType.UNKNOWN
    route: ButlerRoute = ButlerRoute.HERMES
    target_agent: str = "butler_orchestrator"
    runtime_id: str = "hermes"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = ""
    action: str = "butler_orchestrator.dispatch"

    @field_validator("task_type")
    @classmethod
    def _validate_task_type(cls, value: str) -> str:
        allowed = {
            ButlerTaskType.EXCEL_AUDIT,
            ButlerTaskType.GITHUB_ADMIN,
            ButlerTaskType.CONTENT_KB,
            ButlerTaskType.BOOKMARK,
            ButlerTaskType.YOUTUBE,
            ButlerTaskType.UNKNOWN,
        }
        normalized = str(value or "").strip().lower()
        if normalized not in allowed:
            raise ValueError(f"unsupported task_type: {value}")
        return normalized

    @field_validator("target_agent")
    @classmethod
    def _validate_target_agent(cls, value: str) -> str:
        allowed = {
            "butler_orchestrator",
            "excel_audit",
            "github_ops_accountA",
            "github_ops_accountB",
            "youtube_ops",
            "content_kb",
        }
        normalized = str(value or "").strip()
        if normalized not in allowed:
            raise ValueError(f"unsupported target_agent: {value}")
        return normalized

    @field_validator("runtime_id")
    @classmethod
    def _validate_runtime_id(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in {"claude", "hermes"}:
            raise ValueError(f"unsupported runtime_id: {value}")
        return normalized


class ButlerDispatchDecision(StrictModel):
    task_type: str = ButlerTaskType.UNKNOWN
    route: ButlerRoute = ButlerRoute.HERMES
    source: ButlerDispatchSource = ButlerDispatchSource.ESCALATION
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str = ""
    target_agent: str = "butler_orchestrator"
    action: str = "butler_orchestrator.dispatch"
    runtime_id: str = "hermes"
    priority: int = Field(default=1, ge=0, le=100)
    max_retries: int = Field(default=2, ge=0, le=20)
    execution_mode: str = "oneshot"
    extracted_params: dict[str, Any] = Field(default_factory=dict)
    model_fill_error: str | None = None


class ButlerDoctorCheck(StrictModel):
    name: str
    status: str
    detail: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ButlerDoctorRead(StrictModel):
    status: str
    checks: list[ButlerDoctorCheck] = Field(default_factory=list)


class ButlerModelFillService:
    def __init__(
        self,
        *,
        backend: ButlerModelBackend | None = None,
        enabled: bool | None = None,
        min_confidence: float = 0.62,
    ) -> None:
        self._backend = backend
        if enabled is None:
            enabled = os.getenv("AUTORESEARCH_BUTLER_MODEL_FILL_ENABLED", "").strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
        self._enabled = bool(enabled)
        self._min_confidence = max(0.0, min(float(min_confidence), 1.0))

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def available(self) -> bool:
        return self._enabled and self._backend is not None

    @property
    def min_confidence(self) -> float:
        return self._min_confidence

    def classify(self, text: str) -> tuple[ButlerModelFillDecision | None, str | None]:
        if not self.available:
            return None, "model fill is disabled or not configured"
        prompt = _build_model_fill_prompt(text)
        try:
            raw = _run_async(
                self._backend.generate(
                    prompt=prompt,
                    system=_MODEL_FILL_SYSTEM_PROMPT,
                    temperature=0.0,
                    max_tokens=512,
                )
            )
            payload = _extract_json_object(raw)
            decision = ButlerModelFillDecision.model_validate(payload)
        except Exception as exc:
            return None, str(exc).strip() or exc.__class__.__name__
        if decision.confidence < self._min_confidence:
            return None, f"model confidence below threshold: {decision.confidence:.2f}"
        return decision, None


class ButlerDispatchCenter:
    def __init__(
        self,
        *,
        rule_router: ButlerIntentRouter | None = None,
        model_fill: ButlerModelFillService | None = None,
    ) -> None:
        self._rule_router = rule_router or ButlerIntentRouter()
        self._model_fill = model_fill or ButlerModelFillService()

    @property
    def rule_router(self) -> ButlerIntentRouter:
        return self._rule_router

    @property
    def model_fill(self) -> ButlerModelFillService:
        return self._model_fill

    def dispatch(
        self,
        text: str,
        *,
        default_runtime_id: str = "claude",
        hermes_execution_mode: str = "oneshot",
    ) -> ButlerDispatchDecision:
        rule = self._rule_router.classify(text)
        runtime_id = _normalize_runtime_id(default_runtime_id)
        execution_mode = _normalize_execution_mode(hermes_execution_mode)
        if rule.task_type != ButlerTaskType.UNKNOWN and rule.confidence > 0:
            return self._decision_from_rule(
                text=text,
                rule=rule,
                default_runtime_id=runtime_id,
                hermes_execution_mode=execution_mode,
            )

        model_decision, error = self._model_fill.classify(text)
        if model_decision is not None:
            return self._decision_from_model(
                text=text,
                model_decision=model_decision,
                hermes_execution_mode=execution_mode,
            )

        return self._escalate_to_hermes(
            text=text,
            rule=rule,
            reason="model_fill_unavailable_or_uncertain",
            model_fill_error=error,
            hermes_execution_mode=execution_mode,
        )

    def doctor_checks(self) -> list[ButlerDoctorCheck]:
        checks = [
            ButlerDoctorCheck(
                name="rule router",
                status="ok",
                detail="keyword rule router is available",
            )
        ]
        if self._model_fill.available:
            checks.append(
                ButlerDoctorCheck(
                    name="model fill",
                    status="ok",
                    detail="model fill routing is configured",
                    metadata={"min_confidence": self._model_fill.min_confidence},
                )
            )
        elif self._model_fill.enabled:
            checks.append(
                ButlerDoctorCheck(
                    name="model fill",
                    status="fail",
                    detail="model fill is enabled but no backend is configured",
                )
            )
        else:
            checks.append(
                ButlerDoctorCheck(
                    name="model fill",
                    status="degraded",
                    detail="model fill is disabled; unknown tasks escalate to Hermes",
                )
            )
        return checks

    def _decision_from_rule(
        self,
        *,
        text: str,
        rule: ButlerClassification,
        default_runtime_id: str,
        hermes_execution_mode: str,
    ) -> ButlerDispatchDecision:
        params = dict(rule.extracted_params)
        repo = _extract_github_repo(text)
        if repo:
            params["repo"] = repo

        task_type = str(rule.task_type)
        route = ButlerRoute.WORKER
        runtime_id = default_runtime_id
        target_agent = "butler_orchestrator"
        action = task_type
        priority = 1
        max_retries = 2
        execution_mode = "oneshot"

        if task_type == ButlerTaskType.EXCEL_AUDIT:
            route = ButlerRoute.DIRECT
            runtime_id = "claude"
            target_agent = "excel_audit"
            action = "excel_audit.run"
            priority = 3
        elif task_type == ButlerTaskType.GITHUB_ADMIN or repo:
            target_agent = _select_github_target_agent(repo)
            action = "github_ops.pr_ops" if "pr" in text.lower() else "github_ops.issue_ops"
            priority = 8
        elif task_type == ButlerTaskType.YOUTUBE:
            target_agent = "youtube_ops"
            action = "youtube_ops.build_digest"
            priority = 5
        elif task_type == ButlerTaskType.CONTENT_KB:
            target_agent = "content_kb"
            action = "content_kb.ingest"
            priority = 4
            if _should_escalate_content_task(text):
                route = ButlerRoute.HERMES
                runtime_id = "hermes"
                execution_mode = hermes_execution_mode
                max_retries = 1 if execution_mode == "interactive" else 2
        elif task_type == ButlerTaskType.BOOKMARK:
            target_agent = "content_kb"
            action = "content_kb.bookmark"
            priority = 4
            route = ButlerRoute.HERMES
            runtime_id = "hermes"
            execution_mode = hermes_execution_mode
            max_retries = 1 if execution_mode == "interactive" else 2

        if route == ButlerRoute.HERMES:
            runtime_id = "hermes"
            execution_mode = hermes_execution_mode

        return ButlerDispatchDecision(
            task_type=task_type,
            route=route,
            source=ButlerDispatchSource.RULE,
            confidence=rule.confidence,
            reason="matched fast rule",
            target_agent=target_agent,
            action=action,
            runtime_id=runtime_id,
            priority=priority,
            max_retries=max_retries,
            execution_mode=execution_mode,
            extracted_params=params,
        )

    def _decision_from_model(
        self,
        *,
        text: str,
        model_decision: ButlerModelFillDecision,
        hermes_execution_mode: str,
    ) -> ButlerDispatchDecision:
        route = model_decision.route
        runtime_id = model_decision.runtime_id
        execution_mode = "oneshot"
        max_retries = 2
        priority = 2
        if route == ButlerRoute.HERMES or runtime_id == "hermes":
            route = ButlerRoute.HERMES
            runtime_id = "hermes"
            execution_mode = hermes_execution_mode
            max_retries = 1 if execution_mode == "interactive" else 2
        if model_decision.task_type == ButlerTaskType.GITHUB_ADMIN:
            priority = 8
        elif model_decision.task_type == ButlerTaskType.YOUTUBE:
            priority = 5
        elif model_decision.task_type in {ButlerTaskType.CONTENT_KB, ButlerTaskType.BOOKMARK}:
            priority = 4

        params: dict[str, Any] = {}
        repo = _extract_github_repo(text)
        if repo:
            params["repo"] = repo
        return ButlerDispatchDecision(
            task_type=model_decision.task_type,
            route=route,
            source=ButlerDispatchSource.MODEL,
            confidence=model_decision.confidence,
            reason=model_decision.reason or "model fill decision",
            target_agent=model_decision.target_agent,
            action=model_decision.action,
            runtime_id=runtime_id,
            priority=priority,
            max_retries=max_retries,
            execution_mode=execution_mode,
            extracted_params=params,
        )

    def _escalate_to_hermes(
        self,
        *,
        text: str,
        rule: ButlerClassification,
        reason: str,
        model_fill_error: str | None,
        hermes_execution_mode: str,
    ) -> ButlerDispatchDecision:
        params = dict(rule.extracted_params)
        repo = _extract_github_repo(text)
        if repo:
            params["repo"] = repo
        return ButlerDispatchDecision(
            task_type=ButlerTaskType.UNKNOWN,
            route=ButlerRoute.HERMES,
            source=ButlerDispatchSource.ESCALATION,
            confidence=0.0,
            reason=reason,
            target_agent="butler_orchestrator",
            action="butler_orchestrator.dispatch",
            runtime_id="hermes",
            priority=1,
            max_retries=1 if hermes_execution_mode == "interactive" else 2,
            execution_mode=hermes_execution_mode,
            extracted_params=params,
            model_fill_error=model_fill_error,
        )


_MODEL_FILL_SYSTEM_PROMPT = """You are a strict router. Return one JSON object only.
Allowed task_type values: excel_audit, github_admin, content_kb, bookmark, youtube, unknown.
Allowed route values: direct, worker, hermes, reject.
Allowed runtime_id values: claude, hermes.
Allowed target_agent values: butler_orchestrator, excel_audit, github_ops_accountA, github_ops_accountB, youtube_ops, content_kb.
Never answer the user's request. Only classify and route."""


def _build_model_fill_prompt(text: str) -> str:
    return (
        "Classify this user request for the AAS butler control plane.\n"
        "Return JSON with keys: task_type, route, target_agent, runtime_id, confidence, reason, action.\n"
        f"User request:\n{text.strip()[:4000]}"
    )


def _extract_json_object(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        raise ValueError("empty model response")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match is None:
            raise ValueError("model response did not contain a JSON object")
        payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("model response must be a JSON object")
    return payload


def _run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError("model fill cannot run inside an active event loop")


_GITHUB_REPO_RE = re.compile(r"https?://github\.com/([^/\s]+)/([^/\s#?]+)", re.IGNORECASE)
_BOOKMARK_KEYWORDS = (
    "书签",
    "bookmark",
    "twitter bookmark",
    "x bookmark",
    "推特书签",
    "x 书签",
)


def _extract_github_repo(text: str) -> str | None:
    match = _GITHUB_REPO_RE.search(text)
    if not match:
        return None
    owner = match.group(1).strip()
    repo = match.group(2).strip().removesuffix(".git")
    return f"{owner}/{repo}" if owner and repo else None


def _select_github_target_agent(repo: str | None) -> str:
    return "github_ops_accountA"


def _should_escalate_content_task(text: str) -> bool:
    normalized = text.strip().lower()
    return any(keyword in normalized for keyword in _BOOKMARK_KEYWORDS)


def _normalize_runtime_id(value: str) -> str:
    normalized = str(value or "claude").strip().lower()
    return normalized if normalized in {"claude", "hermes"} else "claude"


def _normalize_execution_mode(value: str) -> str:
    normalized = str(value or "oneshot").strip().lower()
    return normalized if normalized in {"oneshot", "interactive"} else "oneshot"
