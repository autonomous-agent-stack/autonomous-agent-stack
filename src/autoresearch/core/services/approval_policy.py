from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from autoresearch.github_assistant.config import load_yaml_object
from autoresearch.shared.models import ApprovalRisk


ApprovalPolicyDecisionValue = Literal["auto", "approval_required", "blocked"]


@dataclass(frozen=True, slots=True)
class ApprovalPolicyDecision:
    decision: ApprovalPolicyDecisionValue
    risk: ApprovalRisk
    reason: str
    required_role: str | None = None
    policy_id: str = "default"


class ApprovalPolicyService:
    """Resolve action-level approval policy from repo-local YAML config."""

    def __init__(self, *, policy_path: Path | None = None) -> None:
        repo_root = Path(__file__).resolve().parents[4]
        self._policy_path = policy_path or repo_root / "configs" / "approval_policy.yaml"
        self._payload = self._load_payload()

    @property
    def policy_path(self) -> Path:
        return self._policy_path

    def decide(
        self,
        *,
        task_type: str,
        action: str,
        metadata: dict[str, Any] | None = None,
    ) -> ApprovalPolicyDecision:
        metadata = metadata or {}
        key = self._action_key(task_type=task_type, action=action)
        actions = self._actions()
        policy = actions.get(key) or actions.get(action.strip().lower())
        if policy is None:
            policy = self._default_policy_for(action)
        return self._decision_from_policy(key=key, policy=policy, metadata=metadata)

    def doctor(self) -> dict[str, Any]:
        return {
            "policy_path": str(self._policy_path),
            "loaded": self._policy_path.exists(),
            "actions": sorted(self._actions()),
        }

    def _load_payload(self) -> dict[str, Any]:
        if not self._policy_path.exists():
            return {"actions": {}}
        return load_yaml_object(self._policy_path)

    def _actions(self) -> dict[str, dict[str, Any]]:
        raw = self._payload.get("actions")
        if not isinstance(raw, dict):
            return {}
        out: dict[str, dict[str, Any]] = {}
        for key, value in raw.items():
            if not isinstance(value, dict):
                continue
            normalized_key = str(key or "").strip().lower()
            if normalized_key:
                out[normalized_key] = dict(value)
        return out

    @staticmethod
    def _action_key(*, task_type: str, action: str) -> str:
        normalized_task = str(task_type or "").strip().lower()
        normalized_action = str(action or "").strip().lower()
        return f"{normalized_task}:{normalized_action}" if normalized_task else normalized_action

    @staticmethod
    def _default_policy_for(action: str) -> dict[str, Any]:
        normalized = str(action or "").strip().lower()
        if any(token in normalized for token in ("merge", "push", "delete", "settings", "close_issue", "release")):
            return {
                "decision": "blocked",
                "risk": "destructive",
                "reason": "action is outside the Mac single-machine MVP safety envelope",
            }
        if any(token in normalized for token in ("comment", "label")):
            return {
                "decision": "approval_required",
                "risk": "external",
                "required_role": "supervisor",
                "reason": "GitHub write action requires approval",
            }
        return {
            "decision": "auto",
            "risk": "read",
            "reason": "read-only or local action",
        }

    @staticmethod
    def _decision_from_policy(
        *,
        key: str,
        policy: dict[str, Any],
        metadata: dict[str, Any],
    ) -> ApprovalPolicyDecision:
        raw_decision = str(policy.get("decision") or policy.get("mode") or "blocked").strip().lower()
        if raw_decision not in {"auto", "approval_required", "blocked"}:
            raw_decision = "blocked"
        raw_risk = str(policy.get("risk") or ("read" if raw_decision == "auto" else "external")).strip().lower()
        try:
            risk = ApprovalRisk(raw_risk)
        except ValueError:
            risk = ApprovalRisk.EXTERNAL
        reason = str(policy.get("reason") or metadata.get("approval_reason") or key).strip()
        return ApprovalPolicyDecision(
            decision=raw_decision,  # type: ignore[arg-type]
            risk=risk,
            reason=reason,
            required_role=(str(policy.get("required_role")).strip() if policy.get("required_role") else None),
            policy_id=str(policy.get("policy_id") or key or "default"),
        )
