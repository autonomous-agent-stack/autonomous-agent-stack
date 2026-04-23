from __future__ import annotations

import logging
import time
from typing import Callable

from autoresearch.core.runtime_identity import get_runtime_identity
from autoresearch.core.services.claude_runtime_service import ClaudeRuntimeService
from autoresearch.core.services.worker_runtime_dispatch import WorkerRuntimeDispatchService
from autoresearch.core.services.claude_session_records import ClaudeSessionRecordService
from autoresearch.shared.models import (
    ClaudeRuntimeSessionRecordRead,
    JobStatus,
    WorkerClaimRequest,
    WorkerHeartbeatRequest,
    WorkerQueueItemRead,
    WorkerRunReportRequest,
    utc_now,
)
from autoresearch.shared.store import SQLiteModelRepository
from autoresearch.workers.mac.client import MacWorkerApiClient, MacWorkerClient
from autoresearch.workers.mac.config import MacWorkerConfig
from autoresearch.workers.mac.executor import MacWorkerExecutionResult, MacWorkerExecutor


logger = logging.getLogger(__name__)


class MacWorkerDaemon:
    def __init__(
        self,
        *,
        config: MacWorkerConfig,
        client: MacWorkerClient,
        executor: MacWorkerExecutor,
        sleep: Callable[[float], None] = time.sleep,
        content_kb_promotion_bridge=None,
    ) -> None:
        self._config = config
        self._client = client
        self._executor = executor
        self._sleep = sleep
        self._content_kb_bridge = content_kb_promotion_bridge
        self._registered = False
        self._last_heartbeat_at = None
        self._last_claim_at = None
        self._current_run_id: str | None = None

    @classmethod
    def from_env(cls) -> MacWorkerDaemon:
        config = MacWorkerConfig.from_env()
        client = MacWorkerApiClient(config)
        runtime_dispatch = _build_worker_runtime_dispatch(config)
        executor = MacWorkerExecutor(config, runtime_dispatch=runtime_dispatch)
        bridge = _build_content_kb_bridge(config)
        return cls(config=config, client=client, executor=executor, content_kb_promotion_bridge=bridge)

    def run_once(self, *, now=None) -> bool:
        current = now or utc_now()
        if not self._registered:
            self._register(current=current)

        if self._should_heartbeat(current):
            self._heartbeat(current=current)

        if not self._should_claim(current):
            return False

        claim = self._client.claim_run(
            self._config.worker_id,
            WorkerClaimRequest(queue_name=self._config.queue_name),
        )
        self._last_claim_at = current
        if not claim.claimed or claim.run is None:
            return False

        self._process_run(claim.run)
        return True

    def serve_forever(self) -> None:
        sleep_seconds = min(self._config.heartbeat_seconds, self._config.claim_poll_seconds, 1.0)
        while True:
            try:
                self.run_once()
            except KeyboardInterrupt:
                logger.info("Mac worker interrupted, shutting down")
                return
            except Exception:
                logger.exception("Mac worker loop failed")
            self._sleep(sleep_seconds)

    def _register(self, *, current) -> None:
        self._client.register_worker(self._config.build_register_request())
        self._registered = True
        self._last_heartbeat_at = current
        logger.info("Registered worker %s", self._config.worker_id)

    def _heartbeat(self, *, current) -> None:
        queue_depth = 1 if self._current_run_id is not None else 0
        load = 1.0 if self._current_run_id is not None else 0.0
        runtime_identity = get_runtime_identity()
        self._client.heartbeat(
            self._config.worker_id,
            WorkerHeartbeatRequest(
                health="ok",
                load=load,
                queue_depth=queue_depth,
                accepting_work=self._current_run_id is None,
                metadata={
                    **runtime_identity,
                    "active_run_id": self._current_run_id,
                },
            ),
        )
        self._last_heartbeat_at = current
        logger.debug("Heartbeat sent for worker %s", self._config.worker_id)

    def _process_run(self, run: WorkerQueueItemRead) -> None:
        logger.info("Claimed run %s (%s)", run.run_id, run.task_type.value)
        self._current_run_id = run.run_id
        self._client.report_run(
            self._config.worker_id,
            run.run_id,
            WorkerRunReportRequest(
                status=JobStatus.RUNNING,
                message=f"started {run.task_type.value}",
            ),
        )
        try:
            outcome = self._executor.execute(run)
        except Exception as exc:
            logger.exception("Run %s failed", run.run_id)
            self._client.report_run(
                self._config.worker_id,
                run.run_id,
                WorkerRunReportRequest(
                    status=JobStatus.FAILED,
                    message=f"{run.task_type.value} failed",
                    error=str(exc),
                ),
            )
            self._current_run_id = None
            return

        self._report_outcome(run=run, outcome=outcome)
        self._notify_telegram_result(run=run, outcome=outcome)
        self._maybe_promote_content_kb(run=run, outcome=outcome)
        self._current_run_id = None

    def _report_outcome(self, *, run: WorkerQueueItemRead, outcome: MacWorkerExecutionResult) -> None:
        self._client.report_run(
            self._config.worker_id,
            run.run_id,
            WorkerRunReportRequest(
                status=outcome.status,
                message=outcome.message,
                result=outcome.result,
                metrics=outcome.metrics,
                error=outcome.error,
            ),
        )
        logger.info("Run %s %s", run.run_id, outcome.status.value)

    def _notify_telegram_result(
        self, *, run: WorkerQueueItemRead, outcome: MacWorkerExecutionResult,
    ) -> None:
        """Send claude_runtime result back to the Telegram user."""
        if run.task_type.value != "claude_runtime":
            return
        chat_id = run.payload.get("chat_id")
        if not chat_id:
            return
        import json
        import os
        import urllib.request as req

        bot_token = os.getenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            logger.warning("No Telegram bot token found, skipping notification")
            return

        # Build the reply text
        if outcome.status == JobStatus.COMPLETED:
            preview = (outcome.result or {}).get("stdout_preview") or outcome.message
            text = preview[:4000] if preview else "执行完成（无输出）"
        else:
            text = f"执行失败：{(outcome.error or '未知错误')[:500]}"
            hint = (outcome.result or {}).get("telegram_hint")
            if isinstance(hint, str) and hint.strip():
                text = f"{hint.strip()}\n{text}"[:4000]

        payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        thread_id = run.payload.get("message_thread_id")
        if thread_id:
            payload["message_thread_id"] = int(thread_id)

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = json.dumps(payload).encode("utf-8")
        request = req.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with req.urlopen(request, timeout=10) as resp:
                logger.info("Telegram notification sent for run %s (status=%d)", run.run_id, resp.status)
        except Exception:
            logger.warning("Failed to send Telegram notification for run %s", run.run_id, exc_info=True)

    def _maybe_promote_content_kb(
        self, *, run: WorkerQueueItemRead, outcome: MacWorkerExecutionResult,
    ) -> None:
        """After content_kb_ingest, trigger draft PR if requested."""
        if run.task_type.value != "content_kb_ingest":
            return
        if self._content_kb_bridge is None:
            return
        promotion = self._content_kb_bridge.maybe_promote(
            task_type=run.task_type.value,
            result=outcome.result,
        )
        if promotion.pr_requested:
            logger.info(
                "content_kb promotion bridge: pr_requested=%s pr_attempted=%s pr_url=%s failure=%s",
                promotion.pr_requested,
                promotion.pr_attempted,
                promotion.pr_url,
                promotion.failure_reason,
            )

    def _should_heartbeat(self, current) -> bool:
        if self._last_heartbeat_at is None:
            return True
        return (current - self._last_heartbeat_at).total_seconds() >= self._config.heartbeat_seconds

    def _should_claim(self, current) -> bool:
        if self._current_run_id is not None:
            return False
        if self._last_claim_at is None:
            return True
        return (current - self._last_claim_at).total_seconds() >= self._config.claim_poll_seconds


def _build_worker_runtime_dispatch(config: MacWorkerConfig) -> WorkerRuntimeDispatchService | None:
    """Build Telegram / worker runtime dispatch (Claude CLI + optional Hermes adapter)."""
    claude_runtime = _build_claude_runtime(config)
    if claude_runtime is None:
        return None
    try:
        from autoresearch.core.services.runtime_registry_builder import build_runtime_adapter_registry_for_worker

        registry = build_runtime_adapter_registry_for_worker(
            repo_root=config.housekeeping_root,
            claude_runtime=claude_runtime,
        )
        return WorkerRuntimeDispatchService(claude_runtime=claude_runtime, registry=registry)
    except Exception:
        logger.warning(
            "Failed to wire runtime adapter registry on worker; Hermes lane disabled",
            exc_info=True,
        )
        return WorkerRuntimeDispatchService(claude_runtime=claude_runtime, registry=None)


def _build_claude_runtime(config: MacWorkerConfig) -> ClaudeRuntimeService | None:
    """Build ClaudeRuntimeService for the worker process.

    Uses the same SQLite database as the API server so agent runs
    and session records are shared.
    """
    try:
        from autoresearch.core.services.claude_agents import ClaudeAgentService
        from autoresearch.core.services.openclaw_compat import OpenClawCompatService
        from autoresearch.shared.models import ClaudeAgentRunRead, OpenClawSessionRead

        db_path = config.housekeeping_root / "artifacts" / "api" / "evaluations.sqlite3"
        if not db_path.exists():
            logger.warning("Database not found at %s, claude_runtime disabled", db_path)
            return None

        openclaw_service = OpenClawCompatService(
            repository=SQLiteModelRepository(
                db_path=db_path,
                table_name="openclaw_sessions",
                model_cls=OpenClawSessionRead,
            )
        )
        agent_service = ClaudeAgentService(
            repository=SQLiteModelRepository(
                db_path=db_path,
                table_name="claude_agent_runs",
                model_cls=ClaudeAgentRunRead,
            ),
            openclaw_service=openclaw_service,
            repo_root=config.housekeeping_root,
            max_agents=10,
            max_depth=3,
        )
        session_record_service = ClaudeSessionRecordService(
            repository=SQLiteModelRepository(
                db_path=db_path,
                table_name="claude_runtime_session_records",
                model_cls=ClaudeRuntimeSessionRecordRead,
            )
        )
        return ClaudeRuntimeService(
            agent_service=agent_service,
            session_record_service=session_record_service,
        )
    except Exception:
        logger.warning("Failed to build ClaudeRuntimeService, claude_runtime disabled", exc_info=True)
        return None


def _build_content_kb_bridge(config: MacWorkerConfig):
    """Build ContentKBPromotionBridge if environment supports it."""
    try:
        from autoresearch.core.services.content_kb_promotion_bridge import (
            build_content_kb_promotion_bridge,
        )

        repos_root = config.housekeeping_root / "repos"
        return build_content_kb_promotion_bridge(
            repos_root=repos_root,
            base_branch="main",
        )
    except Exception:
        logger.warning("Failed to build content_kb promotion bridge, disabled", exc_info=True)
        return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    MacWorkerDaemon.from_env().serve_forever()


if __name__ == "__main__":
    main()
