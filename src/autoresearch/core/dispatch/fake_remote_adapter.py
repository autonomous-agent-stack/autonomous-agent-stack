from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Callable

from autoresearch.agent_protocol.models import RunSummary
from autoresearch.core.dispatch.failure_classifier import (
    FailureDisposition,
    classify_remote_terminal,
    classify_run_summary,
)
from autoresearch.core.dispatch.remote_adapter import RemoteDispatchAdapter
from autoresearch.shared.models import utc_now
from autoresearch.shared.remote_run_contract import (
    DispatchLane,
    FailureClass,
    RemoteHeartbeat,
    RemoteRunRecord,
    RemoteRunStatus,
    RemoteRunSummary,
    RemoteTaskSpec,
)


@dataclass(slots=True)
class _FakeRunState:
    task_spec: RemoteTaskSpec
    scenario: str
    record: RemoteRunRecord
    poll_count: int = 0
    heartbeats: list[RemoteHeartbeat] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    summary: RemoteRunSummary | None = None


class FakeRemoteAdapter(RemoteDispatchAdapter):
    TERMINAL_STATUSES = {
        RemoteRunStatus.SUCCEEDED,
        RemoteRunStatus.FAILED,
        RemoteRunStatus.STALLED,
        RemoteRunStatus.TIMED_OUT,
    }

    def __init__(
        self,
        *,
        repo_root: Path,
        local_runner: Callable[[Any], RunSummary],
        runtime_root: Path | None = None,
    ) -> None:
        self._repo_root = repo_root.resolve()
        self._runtime_root = self._resolve_runtime_root(runtime_root)
        self._local_runner = local_runner
        self._states: dict[str, _FakeRunState] = {}

    def _resolve_runtime_root(self, runtime_root: Path | None) -> Path:
        candidate = (runtime_root or (self._repo_root / ".masfactory_runtime" / "runs")).resolve()
        try:
            candidate.relative_to(self._repo_root)
        except ValueError as exc:
            raise ValueError(
                "fake remote runtime_root must live under repo_root so artifact_paths remain repo-relative"
            ) from exc
        return candidate

    def dispatch(self, spec: RemoteTaskSpec) -> RemoteRunRecord:
        now = utc_now()
        scenario = self._scenario_for(spec)
        record = RemoteRunRecord(
            run_id=spec.run_id,
            requested_lane=spec.requested_lane,
            lane=spec.lane,
            status=RemoteRunStatus.QUEUED,
            summary=f"dispatch queued for {spec.lane.value} lane",
            updated_at=now,
            fallback_reason=self._fallback_reason_for(spec),
            metadata={
                "runtime_mode": spec.runtime_mode,
                "scenario": scenario,
                "planner_plan_id": spec.planner_plan_id,
                "planner_candidate_id": spec.planner_candidate_id,
            },
        )
        state = _FakeRunState(task_spec=spec, scenario=scenario, record=record)
        state.events.append(
            {
                "type": "queued",
                "recorded_at": now.isoformat(),
                "requested_lane": spec.requested_lane.value,
                "lane": spec.lane.value,
                "scenario": scenario,
            }
        )
        self._states[spec.run_id] = state
        self._persist_state(state)
        return record

    def poll(self, run_id: str) -> RemoteRunRecord:
        state = self._require_state(run_id)
        if state.record.status in self.TERMINAL_STATUSES:
            self._persist_state(state)
            return state.record

        state.poll_count += 1
        scenario = state.scenario
        if scenario in {"local_execute", "fallback_to_local"}:
            if state.poll_count == 1:
                state.record = self._running_record(state, summary="local execution in progress")
                state.heartbeats.append(self._heartbeat(state, sequence=1, summary="local execution heartbeat"))
            else:
                run_summary = self._local_runner(state.task_spec.job)
                state.summary = self._summary_from_run_summary(state, run_summary)
                state.record = self._record_from_summary(state.summary)
        elif scenario == "success":
            if state.poll_count == 1:
                state.record = self._running_record(state, summary="remote execution in progress")
                state.heartbeats.append(self._heartbeat(state, sequence=1, summary="remote execution heartbeat"))
            else:
                state.summary = self._terminal_summary(
                    state=state,
                    status=RemoteRunStatus.SUCCEEDED,
                    summary_text="remote execution completed successfully",
                )
                state.record = self._record_from_summary(state.summary)
        elif scenario == "stalled":
            if state.poll_count == 1:
                state.record = self._running_record(state, summary="remote execution started without progress heartbeat")
            else:
                state.summary = self._terminal_summary(
                    state=state,
                    status=RemoteRunStatus.STALLED,
                    summary_text="remote execution stalled without progress heartbeat",
                )
                state.record = self._record_from_summary(state.summary)
        elif scenario == "timed_out":
            if state.poll_count == 1:
                state.record = self._running_record(state, summary="remote execution running toward timeout")
                state.heartbeats.append(self._heartbeat(state, sequence=1, summary="remote execution heartbeat"))
            else:
                state.summary = self._terminal_summary(
                    state=state,
                    status=RemoteRunStatus.TIMED_OUT,
                    summary_text="remote execution timed out",
                )
                state.record = self._record_from_summary(state.summary)
        elif scenario == "env_missing":
            state.summary = self._terminal_summary(
                state=state,
                status=RemoteRunStatus.FAILED,
                summary_text="remote environment is missing required runtime dependencies",
                error_text="EnvironmentCheckFailed: missing remote runtime dependencies",
            )
            state.record = self._record_from_summary(state.summary)
        elif scenario == "transient_network":
            state.summary = self._terminal_summary(
                state=state,
                status=RemoteRunStatus.FAILED,
                summary_text="remote dispatch failed because the connection was interrupted",
                error_text="ssh: connection reset by peer",
            )
            state.record = self._record_from_summary(state.summary)
        elif scenario == "result_fetch_failure":
            if state.poll_count == 1:
                state.record = self._running_record(state, summary="remote execution in progress")
                state.heartbeats.append(self._heartbeat(state, sequence=1, summary="remote execution heartbeat"))
            else:
                state.record = RemoteRunRecord(
                    run_id=state.task_spec.run_id,
                    requested_lane=state.task_spec.requested_lane,
                    lane=state.task_spec.lane,
                    status=RemoteRunStatus.SUCCEEDED,
                    summary="remote execution completed but summary artifact was lost",
                    started_at=state.record.started_at or utc_now(),
                    updated_at=utc_now(),
                    finished_at=utc_now(),
                    fallback_reason=state.record.fallback_reason,
                    metadata=state.record.metadata,
                )
                state.events.append(
                    {
                        "type": "summary_missing",
                        "recorded_at": utc_now().isoformat(),
                    }
                )
        else:
            state.summary = self._terminal_summary(
                state=state,
                status=RemoteRunStatus.FAILED,
                summary_text=f"unsupported fake remote scenario: {scenario}",
                error_text=f"unsupported fake remote scenario: {scenario}",
            )
            state.record = self._record_from_summary(state.summary)

        self._persist_state(state)
        return state.record

    def heartbeat(self, run_id: str) -> RemoteHeartbeat | None:
        state = self._require_state(run_id)
        return state.heartbeats[-1] if state.heartbeats else None

    def fetch_summary(self, run_id: str) -> RemoteRunSummary:
        state = self._require_state(run_id)
        if state.summary is None:
            raise FileNotFoundError(f"remote summary is not available for run: {run_id}")
        return state.summary

    def _scenario_for(self, spec: RemoteTaskSpec) -> str:
        explicit = str(spec.metadata.get("remote_scenario") or "").strip()
        if explicit:
            return explicit
        if spec.requested_lane is DispatchLane.REMOTE and spec.lane is DispatchLane.LOCAL:
            return "fallback_to_local"
        if spec.lane is DispatchLane.LOCAL:
            return "local_execute"
        return "success"

    @staticmethod
    def _fallback_reason_for(spec: RemoteTaskSpec) -> str | None:
        raw_reason = str(spec.metadata.get("fallback_reason") or "").strip()
        if raw_reason:
            return raw_reason
        if spec.requested_lane is DispatchLane.REMOTE and spec.lane is DispatchLane.LOCAL:
            return "remote lane unavailable; downgraded to local"
        return None

    def _running_record(self, state: _FakeRunState, *, summary: str) -> RemoteRunRecord:
        now = utc_now()
        record = state.record.model_copy(
            update={
                "status": RemoteRunStatus.RUNNING,
                "summary": summary,
                "started_at": state.record.started_at or now,
                "updated_at": now,
            }
        )
        state.events.append(
            {
                "type": "running",
                "recorded_at": now.isoformat(),
                "summary": summary,
            }
        )
        return record

    def _heartbeat(self, state: _FakeRunState, *, sequence: int, summary: str) -> RemoteHeartbeat:
        heartbeat = RemoteHeartbeat(
            run_id=state.task_spec.run_id,
            lane=state.task_spec.lane,
            status=RemoteRunStatus.RUNNING,
            sequence=sequence,
            summary=summary,
            artifact_paths=self._artifact_paths(state, include_summary=False),
        )
        state.events.append(
            {
                "type": "heartbeat",
                "recorded_at": heartbeat.recorded_at.isoformat(),
                "sequence": sequence,
                "summary": summary,
            }
        )
        return heartbeat

    def _summary_from_run_summary(self, state: _FakeRunState, run_summary: RunSummary) -> RemoteRunSummary:
        disposition = classify_run_summary(run_summary)
        final_status = (
            RemoteRunStatus.SUCCEEDED
            if run_summary.final_status in {"ready_for_promotion", "promoted"}
            else RemoteRunStatus.FAILED
        )
        now = utc_now()
        summary = RemoteRunSummary(
            run_id=state.task_spec.run_id,
            requested_lane=state.task_spec.requested_lane,
            lane=state.task_spec.lane,
            status=final_status,
            failure_class=disposition.failure_class,
            recovery_action=disposition.recovery_action,
            artifact_paths=self._artifact_paths(state),
            summary=f"local lane completed with final_status={run_summary.final_status}",
            started_at=state.record.started_at or now,
            updated_at=now,
            finished_at=now,
            fallback_reason=state.record.fallback_reason,
            metadata=state.record.metadata,
            run_summary=run_summary,
        )
        state.events.append(
            {
                "type": "completed",
                "recorded_at": now.isoformat(),
                "status": summary.status.value,
                "final_status": run_summary.final_status,
            }
        )
        return summary

    def _terminal_summary(
        self,
        *,
        state: _FakeRunState,
        status: RemoteRunStatus,
        summary_text: str,
        error_text: str | None = None,
    ) -> RemoteRunSummary:
        now = utc_now()
        disposition = classify_remote_terminal(status=status, error_text=error_text)
        summary = RemoteRunSummary(
            run_id=state.task_spec.run_id,
            requested_lane=state.task_spec.requested_lane,
            lane=state.task_spec.lane,
            status=status,
            failure_class=disposition.failure_class,
            recovery_action=disposition.recovery_action,
            artifact_paths=self._artifact_paths(state),
            summary=summary_text,
            started_at=state.record.started_at or now,
            updated_at=now,
            finished_at=now,
            fallback_reason=state.record.fallback_reason,
            metadata={
                **state.record.metadata,
                **({"error": error_text} if error_text else {}),
            },
        )
        state.events.append(
            {
                "type": "completed",
                "recorded_at": now.isoformat(),
                "status": status.value,
                "summary": summary_text,
                "error": error_text,
            }
        )
        return summary

    @staticmethod
    def _record_from_summary(summary: RemoteRunSummary) -> RemoteRunRecord:
        return RemoteRunRecord.model_validate(summary.model_dump(mode="json", exclude={"run_summary"}))

    def _artifact_paths(self, state: _FakeRunState, *, include_summary: bool = True) -> dict[str, str]:
        run_dir = self._runtime_root / state.task_spec.run_id
        control_dir = run_dir / "remote_control"
        paths = {
            "task_spec": self._relpath(control_dir / "task_spec.json"),
            "record": self._relpath(control_dir / "record.json"),
            "events": self._relpath(control_dir / "events.ndjson"),
        }
        if state.heartbeats:
            paths["heartbeat"] = self._relpath(control_dir / "heartbeat.json")
        if include_summary and state.summary is not None:
            paths["summary"] = self._relpath(control_dir / "summary.json")
        if state.summary is not None and state.summary.run_summary is not None:
            legacy_summary = run_dir / "summary.json"
            if legacy_summary.exists():
                paths["legacy_run_summary"] = self._relpath(legacy_summary)
            patch_uri = str(state.summary.run_summary.promotion_patch_uri or "").strip()
            if patch_uri:
                patch_path = Path(patch_uri)
                if not patch_path.is_absolute():
                    paths["promotion_patch"] = patch_path.as_posix()
        return paths

    def _persist_state(self, state: _FakeRunState) -> None:
        run_dir = self._runtime_root / state.task_spec.run_id
        control_dir = run_dir / "remote_control"
        control_dir.mkdir(parents=True, exist_ok=True)

        task_spec_path = control_dir / "task_spec.json"
        task_spec_path.write_text(
            json.dumps(state.task_spec.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        record = RemoteRunRecord.model_validate(
            {
                **state.record.model_dump(mode="json"),
                "artifact_paths": self._artifact_paths(state),
            }
        )
        state.record = record
        (control_dir / "record.json").write_text(
            json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        (control_dir / "events.ndjson").write_text(
            "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in state.events),
            encoding="utf-8",
        )

        if state.heartbeats:
            heartbeat = RemoteHeartbeat.model_validate(
                {
                    **state.heartbeats[-1].model_dump(mode="json"),
                    "artifact_paths": self._artifact_paths(state, include_summary=False),
                }
            )
            state.heartbeats[-1] = heartbeat
            (control_dir / "heartbeat.json").write_text(
                json.dumps(heartbeat.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        if state.summary is not None:
            summary = RemoteRunSummary.model_validate(
                {
                    **state.summary.model_dump(mode="json"),
                    "artifact_paths": self._artifact_paths(state),
                }
            )
            state.summary = summary
            if state.scenario != "result_fetch_failure":
                (control_dir / "summary.json").write_text(
                    json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

    def _require_state(self, run_id: str) -> _FakeRunState:
        normalized = run_id.strip()
        if normalized not in self._states:
            raise KeyError(f"unknown fake remote run: {normalized}")
        return self._states[normalized]

    def _relpath(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self._repo_root).as_posix()
        except ValueError as exc:
            raise ValueError(
                "fake remote artifact path escaped repo_root; refusing to emit an absolute artifact_paths value"
            ) from exc
