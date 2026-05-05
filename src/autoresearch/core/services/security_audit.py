from __future__ import annotations

import asyncio
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import ApprovalStatus, JobStatus, StrictModel, utc_now


SecurityAuditStatus = Literal["pass", "warn", "fail"]


class SecurityAuditFindingRead(StrictModel):
    category: str
    severity: Literal["info", "warning", "high", "critical"]
    message: str
    path: str | None = None
    line: int | None = None
    evidence: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecurityAuditQuickScanRequest(StrictModel):
    diff: str | None = None
    files: list[str] = Field(default_factory=list)
    rule_candidate: dict[str, Any] | None = None
    mode: Literal["diff", "files", "rule_candidate", "mixed"] = "mixed"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecurityAuditQuickScanRead(StrictModel):
    status: SecurityAuditStatus
    generated_at: datetime = Field(default_factory=utc_now)
    summary: str
    findings: list[SecurityAuditFindingRead] = Field(default_factory=list)
    risk_tags: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecurityAuditDailyReportRead(StrictModel):
    status: SecurityAuditStatus
    generated_at: datetime = Field(default_factory=utc_now)
    window: str = "daily"
    counts: dict[str, int] = Field(default_factory=dict)
    findings: list[SecurityAuditFindingRead] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    artifact_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecurityAuditService:
    """Lightweight governance audit service for Butler/worker workflows."""

    def __init__(
        self,
        *,
        repo_root: Path | None = None,
        artifact_root: Path | None = None,
        control_plane: Any | None = None,
        worker_scheduler: WorkerSchedulerService | None = None,
        approval_store: ApprovalStoreService | None = None,
    ) -> None:
        self._repo_root = (repo_root or Path(__file__).resolve().parents[4]).resolve()
        self._artifact_root = artifact_root or self._repo_root / "artifacts" / "security_audit"
        self._control_plane = control_plane
        self._worker_scheduler = worker_scheduler
        self._approval_store = approval_store

    def quick_scan(self, request: SecurityAuditQuickScanRequest) -> SecurityAuditQuickScanRead:
        findings: list[SecurityAuditFindingRead] = []
        risk_tags: set[str] = set()
        if request.diff and request.diff.strip():
            findings.extend(self._scan_diff(request.diff))
        for file_path in request.files:
            findings.extend(self._scan_file(file_path))
        if request.rule_candidate:
            rule_findings, rule_risks = self._audit_rule_candidate(request.rule_candidate)
            findings.extend(rule_findings)
            risk_tags.update(rule_risks)

        for finding in findings:
            if finding.severity in {"high", "critical"}:
                risk_tags.add("security_high")
            elif finding.severity == "warning":
                risk_tags.add("security_warning")

        status = self._status_from_findings(findings)
        return SecurityAuditQuickScanRead(
            status=status,
            summary=self._summary_for_status(status, findings),
            findings=findings,
            risk_tags=sorted(risk_tags),
            metadata={"scanner": "security_audit", "strategy": "quick_scan"},
        )

    def generate_daily_report(self, *, write_artifact: bool = True) -> SecurityAuditDailyReportRead:
        counts: Counter[str] = Counter()
        findings: list[SecurityAuditFindingRead] = []
        recommendations: list[str] = []

        tasks = self._safe_list(lambda: self._control_plane.list_tasks())
        approvals = self._safe_list(lambda: self._control_plane.list_approvals())
        worker_runs = self._safe_list(lambda: self._worker_scheduler.list_queue())
        legacy_approvals = self._safe_list(
            lambda: self._approval_store.list_requests(status=ApprovalStatus.PENDING, limit=200)
        )

        counts["control_plane_tasks"] = len(tasks)
        counts["control_plane_approvals"] = len(approvals)
        counts["pending_legacy_approvals"] = len(legacy_approvals)
        counts["worker_runs"] = len(worker_runs)
        counts["failed_worker_runs"] = sum(
            1 for run in worker_runs if getattr(run, "status", None) == JobStatus.FAILED
        )
        counts["hermes_fallback_tasks"] = sum(
            1
            for task in tasks
            if getattr(task, "capability_id", "") == "hermes_openclaw"
            or (getattr(task, "metadata", {}) or {}).get("butler_source") == "escalation"
        )
        counts["external_risk_tasks"] = sum(
            1 for task in tasks if "external_api" in set(getattr(task, "risk_tags", []) or [])
        )

        if counts["failed_worker_runs"]:
            findings.append(
                SecurityAuditFindingRead(
                    category="worker_health",
                    severity="warning",
                    message=f"{counts['failed_worker_runs']} worker runs are failed.",
                )
            )
            recommendations.append("Review failed worker runs before promoting new Butler rules.")
        if counts["pending_legacy_approvals"]:
            findings.append(
                SecurityAuditFindingRead(
                    category="approval_backlog",
                    severity="warning",
                    message=f"{counts['pending_legacy_approvals']} legacy approvals are still pending.",
                )
            )
        if counts["hermes_fallback_tasks"] >= 5:
            findings.append(
                SecurityAuditFindingRead(
                    category="hermes_fallback_drift",
                    severity="warning",
                    message="Hermes fallback volume is high; consider promoting stable routing rules.",
                    metadata={"hermes_fallback_tasks": counts["hermes_fallback_tasks"]},
                )
            )
            recommendations.append("Review Hermes fallback tasks and promote mature rules after quick scan.")

        status = self._status_from_findings(findings)
        artifact_path = None
        report = SecurityAuditDailyReportRead(
            status=status,
            counts=dict(counts),
            findings=findings,
            recommendations=recommendations,
            artifact_path=None,
            metadata={
                "strategy": "light_scan_plus_daily_digest",
                "generated_by": "security_audit",
            },
        )
        if write_artifact:
            artifact_path = self._write_daily_artifact(report)
            report = report.model_copy(update={"artifact_path": str(artifact_path)})
        return report

    def run_prompt_hygiene(self) -> SecurityAuditQuickScanRead:
        script = self._repo_root / "scripts" / "check_prompt_hygiene.py"
        if not script.exists():
            return SecurityAuditQuickScanRead(
                status="fail",
                summary="prompt hygiene script is missing",
                findings=[
                    SecurityAuditFindingRead(
                        category="prompt_hygiene",
                        severity="critical",
                        message=f"Missing script: {script}",
                    )
                ],
                risk_tags=["security_high"],
            )
        completed = subprocess.run(
            [sys.executable, str(script), "--root", "src"],
            cwd=self._repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        severity: Literal["info", "warning", "high", "critical"] = (
            "warning" if completed.returncode == 0 else "high"
        )
        return SecurityAuditQuickScanRead(
            status="warn" if completed.returncode == 0 else "fail",
            summary="prompt hygiene completed",
            findings=[
                SecurityAuditFindingRead(
                    category="prompt_hygiene",
                    severity=severity,
                    message=(completed.stdout or completed.stderr or "prompt hygiene completed").strip()[:1000],
                )
            ],
            risk_tags=["security_warning"] if completed.returncode == 0 else ["security_high"],
            metadata={"returncode": completed.returncode},
        )

    def _scan_diff(self, diff: str) -> list[SecurityAuditFindingRead]:
        findings: list[SecurityAuditFindingRead] = []
        try:
            from gatekeeper.static_analyzer import PR_Static_Analyzer

            result = _run_sync(PR_Static_Analyzer().analyze_pr(diff))
            for item in result.get("violations", []):
                findings.append(
                    SecurityAuditFindingRead(
                        category=str(item.get("type") or "static_analyzer"),
                        severity="high",
                        message=str(item.get("description") or "static analyzer violation"),
                        line=int(item.get("line_number") or 0) or None,
                        evidence=str(item)[:1000],
                    )
                )
        except Exception as exc:
            findings.append(
                SecurityAuditFindingRead(
                    category="static_analyzer",
                    severity="warning",
                    message=f"PR static analyzer unavailable: {exc}",
                )
            )

        added_code = "\n".join(
            line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")
        )
        if added_code.strip():
            findings.extend(self._scan_code(added_code, filename="<diff>"))
        return findings

    def _scan_file(self, file_path: str) -> list[SecurityAuditFindingRead]:
        path = Path(file_path)
        if not path.is_absolute():
            path = self._repo_root / path
        if not path.exists() or not path.is_file():
            return [
                SecurityAuditFindingRead(
                    category="file_scan",
                    severity="warning",
                    message=f"file not found: {file_path}",
                    path=str(path),
                )
            ]
        try:
            return self._scan_code(path.read_text(encoding="utf-8"), filename=str(path))
        except Exception as exc:
            return [
                SecurityAuditFindingRead(
                    category="file_scan",
                    severity="warning",
                    message=f"file scan failed: {exc}",
                    path=str(path),
                )
            ]

    @staticmethod
    def _scan_code(code: str, *, filename: str) -> list[SecurityAuditFindingRead]:
        try:
            from security.ast_auditor import ASTAuditor

            result = ASTAuditor(strict_mode=True).scan_code(code, filename=filename)
        except Exception as exc:
            return [
                SecurityAuditFindingRead(
                    category="ast_audit",
                    severity="warning",
                    message=f"AST auditor unavailable: {exc}",
                    path=filename,
                )
            ]
        findings: list[SecurityAuditFindingRead] = []
        for issue in result.get("issues", []):
            severity = _normalize_ast_severity(str(issue.get("severity") or "warning"))
            findings.append(
                SecurityAuditFindingRead(
                    category="ast_audit",
                    severity=severity,
                    message=str(issue.get("message") or issue.get("function") or "AST issue"),
                    path=filename,
                    line=int(issue.get("line") or 0) or None,
                    evidence=str(issue.get("code_snippet") or issue.get("function") or "")[:500],
                )
            )
        return findings

    @staticmethod
    def _audit_rule_candidate(
        candidate: dict[str, Any],
    ) -> tuple[list[SecurityAuditFindingRead], set[str]]:
        findings: list[SecurityAuditFindingRead] = []
        risk_tags: set[str] = set()
        writes = candidate.get("writes") or candidate.get("target_paths") or []
        if isinstance(writes, str):
            writes = [writes]
        tool_requirements = candidate.get("tool_requirements") or []
        if isinstance(tool_requirements, str):
            tool_requirements = [tool_requirements]

        if any(str(path).startswith("configs/butler/") for path in writes):
            findings.append(
                SecurityAuditFindingRead(
                    category="rule_candidate",
                    severity="warning",
                    message="Rule candidate modifies Butler routing configuration.",
                    metadata={"candidate_id": candidate.get("id") or candidate.get("rule_id")},
                )
            )
            risk_tags.add("rule_promotion")
        if any("github.repo.push" in str(item) or "github.pr.create" in str(item) for item in tool_requirements):
            findings.append(
                SecurityAuditFindingRead(
                    category="rule_candidate",
                    severity="high",
                    message="Rule candidate requests external GitHub write tools.",
                    metadata={"tool_requirements": tool_requirements},
                )
            )
            risk_tags.update({"external_api", "external_write", "security_high"})
        return findings, risk_tags

    def _write_daily_artifact(self, report: SecurityAuditDailyReportRead) -> Path:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_dir = self._artifact_root / "daily"
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = out_dir / f"{day}.json"
        md_path = out_dir / f"{day}.md"
        json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        md_path.write_text(_render_daily_markdown(report), encoding="utf-8")
        return md_path

    @staticmethod
    def _safe_list(factory) -> list[Any]:
        try:
            result = factory()
        except Exception:
            return []
        return list(result or [])

    @staticmethod
    def _status_from_findings(findings: list[SecurityAuditFindingRead]) -> SecurityAuditStatus:
        if any(item.severity in {"critical", "high"} for item in findings):
            return "fail"
        if any(item.severity == "warning" for item in findings):
            return "warn"
        return "pass"

    @staticmethod
    def _summary_for_status(status: SecurityAuditStatus, findings: list[SecurityAuditFindingRead]) -> str:
        if status == "pass":
            return "security quick scan passed"
        if status == "warn":
            return f"security quick scan found {len(findings)} warning(s)"
        return f"security quick scan found {len(findings)} high-risk finding(s)"


def build_default_security_audit_service(*, repo_root: Path | None = None) -> SecurityAuditService:
    return SecurityAuditService(repo_root=repo_root)


def _run_sync(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError("security audit cannot run an async scanner inside an active event loop")


def _normalize_ast_severity(value: str) -> Literal["info", "warning", "high", "critical"]:
    normalized = value.strip().lower()
    if normalized == "critical":
        return "critical"
    if normalized == "high":
        return "high"
    if normalized in {"medium", "warning"}:
        return "warning"
    return "info"


def _render_daily_markdown(report: SecurityAuditDailyReportRead) -> str:
    lines = [
        "# 安全审计日报 / Security Audit Daily Report",
        "",
        f"- 状态 / Status: {report.status}",
        f"- 生成时间 / Generated at: {report.generated_at.isoformat()}",
        "",
        "## 统计 / Counts",
    ]
    for key, value in sorted(report.counts.items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## 发现 / Findings"])
    if report.findings:
        for finding in report.findings:
            lines.append(f"- [{finding.severity}] {finding.category}: {finding.message}")
    else:
        lines.append("- 无高风险发现 / No high-risk findings.")
    lines.extend(["", "## 建议 / Recommendations"])
    if report.recommendations:
        for item in report.recommendations:
            lines.append(f"- {item}")
    else:
        lines.append("- 继续保持轻扫 + 日报节奏 / Keep the light-scan plus daily cadence.")
    return "\n".join(lines) + "\n"
