from __future__ import annotations

import errno
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable
from urllib import error as urllib_error
import urllib.request as urllib_req

from autoresearch.build_label import get_build_label
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

_WORKER_TELEGRAM_TEXT_LIMIT = 3900


def _worker_telegram_escape_cell(value: str) -> str:
    return str(value).replace("|", "/").replace("\n", " ").strip()


def _worker_telegram_kv_table(rows: list[tuple[str, str]]) -> str:
    lines = ["| 项 | 值 |", "| --- | --- |"]
    for key, val in rows:
        lines.append(f"| {_worker_telegram_escape_cell(key)[:40]} | {_worker_telegram_escape_cell(val)[:900]} |")
    return "\n".join(lines)


def _strip_hermes_noise_lines(text: str) -> str:
    """Drop leading Hermes ``Warning:`` / ``[INFO]`` chatter so the body shows real content.

    Examples that should collapse to empty (so caller falls back to summary or
    a "no output" template):
        "Warning: Unknown toolsets: shell, git\n"
        "Warning: ...\n[INFO] ..."

    Returns the cleaned text (may still be empty).
    """
    if not text:
        return ""
    lines = text.splitlines()
    skip_prefixes = ("warning:", "[warn", "[info", "[debug")
    while lines:
        head = lines[0].strip().lower()
        if head and any(head.startswith(prefix) for prefix in skip_prefixes):
            lines.pop(0)
            continue
        break
    return "\n".join(lines).strip()


def _first_nonempty_line(text: str, *, limit: int = 600) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s:
            return s[:limit]
    return ""


def _is_vacuous_hermes_summary(summary: str) -> bool:
    """True when Hermes adapter left only a generic completion stub (no real line)."""
    t = summary.strip().lower()
    if not t:
        return True
    if t in {"hermes completed.", "hermes completed successfully."}:
        return True
    if t == "hermes completed":
        return True
    if t.startswith("hermes completed:"):
        rest = t.split(":", 1)[1].strip()
        return rest in {"", "successfully."}
    return False


def _strip_hermes_summary_noise(summary: str) -> str:
    """Same as ``_strip_hermes_noise_lines`` but unwraps the Hermes one-liner.

    Hermes adapter emits ``"Hermes completed: <first stdout line>"``. When that
    first line is a Warning, we pop the warning prefix so the summary cell
    surfaces something useful instead of a duplicated noise line.
    """
    if not summary:
        return ""
    cleaned = summary.strip()
    if cleaned.lower().startswith("hermes completed:"):
        body = cleaned.split(":", 1)[1].strip()
        body = _strip_hermes_noise_lines(body)
        if body:
            return f"Hermes completed: {body}"
        return "Hermes completed."
    return _strip_hermes_noise_lines(cleaned) or cleaned


def _truncate_worker_telegram_body(text: str, limit: int = _WORKER_TELEGRAM_TEXT_LIMIT) -> str:
    normalized = text.strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(1, limit - 24)] + "\n...[已截断]"


def _is_fd_exhaustion(exc: BaseException) -> bool:
    """True when errno 24 / EMFILE appears on this exception or its chain."""
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if isinstance(cur, OSError) and getattr(cur, "errno", None) == errno.EMFILE:
            return True
        if isinstance(cur, urllib_error.URLError):
            reason = cur.reason
            if isinstance(reason, OSError) and getattr(reason, "errno", None) == errno.EMFILE:
                return True
        text = str(cur).lower()
        if "too many open files" in text or "[errno 24]" in text:
            return True
        cur = cur.__cause__ or cur.__context__
    return False


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
        base_sleep = min(self._config.heartbeat_seconds, self._config.claim_poll_seconds, 1.0)
        backoff = base_sleep
        while True:
            try:
                self.run_once()
                backoff = base_sleep
            except KeyboardInterrupt:
                logger.info("Mac worker interrupted, shutting down")
                return
            except Exception as exc:
                logger.exception("Mac worker loop failed")
                if _is_fd_exhaustion(exc):
                    backoff = min(max(backoff, 2.0) * 2.0, 120.0)
                    logger.error(
                        "Resource exhaustion (likely too many open files); sleeping %.1fs before retry",
                        backoff,
                    )
                else:
                    backoff = base_sleep
            self._sleep(backoff)

    def _register(self, *, current) -> None:
        self._client.register_worker(self._config.build_register_request())
        self._registered = True
        self._last_heartbeat_at = current
        logger.info(
            "Registered worker %s [build=%s]",
            self._config.worker_id,
            get_build_label(),
        )

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

        delivery = self._notify_telegram_result(run=run, outcome=outcome)
        if delivery:
            outcome.metrics = {**outcome.metrics, **delivery}
        self._report_outcome(run=run, outcome=outcome)
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
    ) -> dict[str, Any]:
        """Send claude_runtime result back to the Telegram user.

        When the control plane stored ``telegram_queue_ack_message_id`` on the queue item
        (from the synchronous queue ack), we **edit** that message so the chat stays a
        single updating card (similar to Hermes-style UX). Otherwise we send a new message.

        Returns a delivery dict (always non-empty for ``claude_runtime``) so the caller
        can persist it via ``report_run`` for control-plane-side observability and the
        butler-fallback path:

            {
                "telegram_notify_status": "edited" | "sent" | "failed"
                                          | "skipped_no_token" | "skipped_no_chat",
                "telegram_notify_attempts": int,
                "telegram_notify_error": str | None,
            }

        Non-``claude_runtime`` runs return ``{}`` (no delivery work attempted).
        """
        if run.task_type.value != "claude_runtime":
            return {}
        chat_id = run.payload.get("chat_id")
        if not chat_id:
            return {
                "telegram_notify_status": "skipped_no_chat",
                "telegram_notify_attempts": 0,
                "telegram_notify_error": None,
            }

        bot_token = os.getenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            label = (self._config.telegram_reply_brand or "初代worker").strip() or "初代worker"
            msg = (
                f"[{label}] skip telegram: no bot token "
                "(set AUTORESEARCH_TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN for this worker process)"
            )
            logger.warning(msg)
            print(msg, file=sys.stderr, flush=True)
            return {
                "telegram_notify_status": "skipped_no_token",
                "telegram_notify_attempts": 0,
                "telegram_notify_error": "missing AUTORESEARCH_TELEGRAM_BOT_TOKEN/TELEGRAM_BOT_TOKEN in worker env",
            }

        brand = (self._config.telegram_reply_brand or "").strip()
        payload = run.payload
        task_name = str(payload.get("task_name") or run.task_name or "").strip() or "(unnamed)"
        res: dict[str, Any] = dict(outcome.result or {})
        summary_raw = str(res.get("summary") or "").strip()
        stdout_raw = str(res.get("stdout_preview") or "").strip()
        stdout_clean = _strip_hermes_noise_lines(stdout_raw)
        summary_clean = _strip_hermes_summary_noise(summary_raw)

        if outcome.status == JobStatus.COMPLETED:
            # Prefer cleaned variants. If cleaning swallowed everything (i.e. the
            # whole stdout was just `Warning:` noise), do NOT fall back to the
            # raw noise — surface the explicit "no output" template instead so
            # the user gets a meaningful card with run_id to inspect.
            had_raw_content = bool(stdout_raw or summary_raw)
            cleaned_main = stdout_clean or summary_clean
            if cleaned_main:
                main_body = cleaned_main
            elif not had_raw_content:
                main_body = (
                    str(outcome.message or "").strip()
                    or f"（运行结束：无文本输出；请对照 run_id 与面板/日志）\nrun_id: {run.run_id}"
                )
            else:
                main_body = (
                    "（运行结束：仅有警告输出，无业务结果；请查面板或日志）"
                    f"\nrun_id: {run.run_id}"
                )
            status_label = "completed"
        else:
            err = (outcome.error or "未知错误").strip()
            main_body = f"执行失败：{err[:1200]}"
            hint = res.get("telegram_hint")
            if isinstance(hint, str) and hint.strip():
                main_body = f"{hint.strip()}\n{main_body}"
            status_label = outcome.status.value

        table_rows: list[tuple[str, str]] = [
            ("任务", task_name),
            ("run_id", str(run.run_id)),
            ("状态", status_label),
        ]
        summary_for_cell = (summary_clean or summary_raw).strip()
        # Hermes often leaves summary as the generic ``Hermes completed.`` while
        # stdout carries the user-visible line — avoid a useless 摘要 row.
        if _is_vacuous_hermes_summary(summary_for_cell) and stdout_clean:
            fl = _first_nonempty_line(stdout_clean, limit=600)
            if fl:
                summary_for_cell = fl
        first_main_line = _first_nonempty_line(main_body, limit=600)
        if (
            summary_for_cell
            and summary_for_cell != stdout_clean
            and summary_for_cell != stdout_raw
            and summary_for_cell.strip() != first_main_line.strip()
        ):
            table_rows.append(("摘要", summary_for_cell[:600]))

        parts: list[str] = []
        if brand:
            parts.append(f"【{brand}】")
        parts.append("任务已结束。")
        parts.append("")
        parts.append(_worker_telegram_kv_table(table_rows))
        parts.append("")
        parts.append(main_body)
        text = _truncate_worker_telegram_body("\n".join(parts))

        thread_raw = run.payload.get("message_thread_id")
        thread_id: int | None = None
        if thread_raw is not None and str(thread_raw).strip() != "":
            try:
                thread_id = int(thread_raw)
            except (TypeError, ValueError):
                thread_id = None

        ack_raw = (run.metadata or {}).get("telegram_queue_ack_message_id")
        ack_message_id: int | None = None
        if ack_raw is not None and str(ack_raw).strip() != "":
            try:
                ack_message_id = int(ack_raw)
            except (TypeError, ValueError):
                ack_message_id = None

        if ack_message_id is not None and self._worker_telegram_edit_or_send(
            bot_token=bot_token,
            chat_id=str(chat_id),
            message_id=ack_message_id,
            text=text,
            message_thread_id=thread_id,
        ):
            logger.info(
                "Telegram completion edited in-place run=%s chat_id=%s message_id=%s",
                run.run_id,
                chat_id,
                ack_message_id,
            )
            return {
                "telegram_notify_status": "edited",
                "telegram_notify_attempts": 1,
                "telegram_notify_error": None,
            }

        send_outcome = self._worker_telegram_send_message_with_retries(
            bot_token=bot_token,
            chat_id=str(chat_id),
            text=text,
            message_thread_id=thread_id,
            run_id=str(run.run_id),
        )
        delivered, attempts, last_error = send_outcome
        return {
            "telegram_notify_status": "sent" if delivered else "failed",
            "telegram_notify_attempts": attempts,
            "telegram_notify_error": last_error,
        }

    def _worker_telegram_edit_or_send(
        self,
        *,
        bot_token: str,
        chat_id: str,
        message_id: int,
        text: str,
        message_thread_id: int | None,
    ) -> bool:
        """Try editMessageText; on failure return False so caller can sendMessage."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        for attempt in range(1, 4):
            req = urllib_req.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib_req.urlopen(req, timeout=15) as resp:
                    raw = resp.read().decode("utf-8")
                parsed = json.loads(raw or "{}")
                if not parsed.get("ok"):
                    desc = str(parsed.get("description") or parsed)
                    if "message is not modified" in desc.lower():
                        return True
                    logger.warning(
                        "Telegram editMessageText not ok chat_id=%s message_id=%s: %s",
                        chat_id,
                        message_id,
                        desc,
                    )
                    return False
                return True
            except urllib_error.HTTPError as exc:
                try:
                    err_body = exc.read().decode("utf-8", errors="replace")
                except Exception:
                    err_body = ""
                if "message is not modified" in err_body.lower():
                    return True
                logger.warning(
                    "Telegram editMessageText HTTPError attempt %s/3 chat_id=%s message_id=%s: %s",
                    attempt,
                    chat_id,
                    message_id,
                    exc,
                )
                if attempt < 3:
                    self._sleep(0.4 * attempt)
            except Exception as exc:
                logger.warning(
                    "Telegram editMessageText attempt %s/3 failed chat_id=%s message_id=%s: %s",
                    attempt,
                    chat_id,
                    message_id,
                    exc,
                )
                if attempt < 3:
                    self._sleep(0.4 * attempt)
        return False

    def _worker_telegram_send_message_with_retries(
        self,
        *,
        bot_token: str,
        chat_id: str,
        text: str,
        message_thread_id: int | None,
        run_id: str,
    ) -> tuple[bool, int, str | None]:
        """Send a fresh Telegram message with up to 3 retries.

        Returns ``(delivered, attempts, last_error_str)`` so callers can record
        delivery quality on the run report (used by rca-notify for control-plane
        observability and butler-fallback dedup).
        """
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        last_exc: BaseException | None = None
        for attempt in range(1, 4):
            req = urllib_req.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib_req.urlopen(req, timeout=15) as resp:
                    logger.info(
                        "Telegram sendMessage ok run=%s chat_id=%s status=%d attempt=%s",
                        run_id,
                        chat_id,
                        resp.status,
                        attempt,
                    )
                return True, attempt, None
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "Telegram sendMessage attempt %s/3 failed run=%s chat_id=%s: %s",
                    attempt,
                    run_id,
                    chat_id,
                    exc,
                )
                if attempt < 3:
                    self._sleep(0.5 * attempt)
        logger.error(
            "Telegram sendMessage exhausted for run=%s chat_id=%s: %s",
            run_id,
            chat_id,
            last_exc,
            exc_info=last_exc is not None,
        )
        return False, 3, str(last_exc) if last_exc is not None else "unknown error"

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


def _resolve_worker_api_db_path(config: MacWorkerConfig) -> Path:
    """Same DB file the API uses (`AUTORESEARCH_API_DB_PATH` or repo default)."""
    raw = (os.environ.get("AUTORESEARCH_API_DB_PATH") or "").strip()
    if raw:
        db_path = Path(raw).expanduser()
    else:
        db_path = config.housekeeping_root / "artifacts" / "api" / "evaluations.sqlite3"
    db_path = db_path.resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def _build_claude_runtime(config: MacWorkerConfig) -> ClaudeRuntimeService | None:
    """Build ClaudeRuntimeService for the worker process.

    Uses the same SQLite database as the API server so agent runs
    and session records are shared.
    """
    try:
        from autoresearch.core.services.claude_agents import ClaudeAgentService
        from autoresearch.core.services.openclaw_compat import OpenClawCompatService
        from autoresearch.shared.models import ClaudeAgentRunRead, OpenClawSessionRead

        db_path = _resolve_worker_api_db_path(config)
        logger.info("Mac worker SQLite control-plane DB: %s", db_path)
        if not db_path.exists():
            logger.warning(
                "SQLite file not present yet at %s (API will create on first write); worker will open/create WAL sidecars here",
                db_path,
            )

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
