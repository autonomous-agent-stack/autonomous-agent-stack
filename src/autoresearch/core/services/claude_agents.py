from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
import threading
import time
from typing import Any

from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_skills import OpenClawSkillService
from autoresearch.core.services.telegram_image_downloader import (
    TelegramImageDownloader,
    parse_telegram_image_url,
)
from autoresearch.core.services.context_manager import ContextManager
from autoresearch.shared.models import (
    ClaudeAgentCancelRequest,
    ClaudeAgentCreateRequest,
    ClaudeAgentRetryRequest,
    ClaudeAgentRunRead,
    ClaudeAgentTreeEdgeRead,
    ClaudeAgentTreeNodeRead,
    ClaudeAgentTreeRead,
    JobStatus,
    OpenClawSkillRead,
    OpenClawSessionCreateRequest,
    OpenClawSessionEventAppendRequest,
    utc_now,
)
from autoresearch.shared.store import Repository, create_resource_id


class ClaudeAgentService:
    """Claude CLI subagent scheduler with depth/concurrency guardrails."""

    ACTIVE_STATUSES = {JobStatus.QUEUED, JobStatus.RUNNING}
    TERMINAL_STATUSES = {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.INTERRUPTED, JobStatus.CANCELLED}
    CANCEL_GRACE_SECONDS = 2.0

    def __init__(
        self,
        repository: Repository[ClaudeAgentRunRead],
        openclaw_service: OpenClawCompatService,
        repo_root: Path | None = None,
        max_agents: int = 20,
        max_depth: int = 3,
        claude_command: list[str] | None = None,
        openclaw_skill_service: OpenClawSkillService | None = None,
        context_manager: ContextManager | None = None,
    ) -> None:
        self._repository = repository
        self._openclaw_service = openclaw_service
        self._openclaw_skill_service = openclaw_skill_service
        self._context_manager = context_manager or ContextManager(openclaw_service)
        self._repo_root = repo_root or Path(__file__).resolve().parents[4]
        self._max_agents = max_agents
        self._max_depth = max_depth
        if claude_command is not None:
            self._claude_command = list(claude_command)
        else:
            self._claude_command = shlex.split(os.getenv("AUTORESEARCH_CLAUDE_COMMAND", "claude"))
        self._runtime_lock = threading.Lock()
        self._running_processes: dict[str, subprocess.Popen[str]] = {}
        self._cancel_requests: set[str] = set()

    @property
    def openclaw_service(self) -> OpenClawCompatService:
        return self._openclaw_service

    def create(self, request: ClaudeAgentCreateRequest) -> ClaudeAgentRunRead:
        if request.generation_depth > self._max_depth:
            raise ValueError(
                f"generation depth {request.generation_depth} exceeds max depth {self._max_depth}"
            )
        if self.active_count() >= self._max_agents:
            raise RuntimeError(f"active agent limit reached ({self._max_agents})")

        session_id = request.session_id
        session_metadata: dict[str, Any] = {}
        if session_id is None:
            session = self._openclaw_service.create_session(
                OpenClawSessionCreateRequest(
                    channel="claude_cli",
                    title=request.task_name,
                    metadata={
                        "source": "claude_agent_scheduler",
                        "parent_agent_id": request.parent_agent_id,
                    },
                )
            )
            session_id = session.session_id
            session_metadata = dict(session.metadata)
        else:
            session = self._openclaw_service.get_session(session_id)
            if session is None:
                raise ValueError(f"session not found: {session_id}")
            session_metadata = dict(session.metadata)

        requested_skill_names = self._resolve_requested_skill_names(
            request=request,
            session_metadata=session_metadata,
        )
        effective_prompt, resolved_skills = self._compose_prompt_with_skills(
            prompt=request.prompt,
            requested_skill_names=requested_skill_names,
        )
        command = self._build_command(request, prompt_override=effective_prompt)
        run_metadata = dict(request.metadata)
        if requested_skill_names:
            run_metadata.update(
                {
                    "requested_skill_names": requested_skill_names,
                    "resolved_skills": [
                        {
                            "name": skill.name,
                            "skill_key": skill.skill_key,
                            "file_path": skill.file_path,
                        }
                        for skill in resolved_skills
                    ],
                    "skills_prompt_injected": bool(resolved_skills),
                }
            )
        now = utc_now()
        run = ClaudeAgentRunRead(
            agent_run_id=create_resource_id("agent"),
            task_name=request.task_name,
            prompt=request.prompt,
            status=JobStatus.QUEUED,
            agent_name=request.agent_name,
            session_id=session_id,
            parent_agent_id=request.parent_agent_id,
            generation_depth=request.generation_depth,
            command=command,
            timeout_seconds=request.timeout_seconds,
            work_dir=str(self._resolve_work_dir(request.work_dir)),
            returncode=None,
            stdout_preview=None,
            stderr_preview=None,
            duration_seconds=None,
            created_at=now,
            updated_at=now,
            metadata=run_metadata,
            error=None,
        )
        saved = self._repository.save(run.agent_run_id, run)
        self._openclaw_service.append_event(
            session_id=session_id,
            request=OpenClawSessionEventAppendRequest(
                role="status",
                content=f"agent queued: {saved.agent_run_id}",
                metadata={
                    "agent_run_id": saved.agent_run_id,
                    "generation_depth": saved.generation_depth,
                    "parent_agent_id": saved.parent_agent_id,
                },
            ),
        )
        self._openclaw_service.set_status(
            session_id=session_id,
            status=JobStatus.QUEUED,
            metadata_updates={"latest_agent_run_id": saved.agent_run_id},
        )
        return saved

    def list(self) -> list[ClaudeAgentRunRead]:
        return self._repository.list()

    def get(self, agent_run_id: str) -> ClaudeAgentRunRead | None:
        return self._repository.get(agent_run_id)

    def active_count(self) -> int:
        return sum(1 for item in self.list() if item.status in self.ACTIVE_STATUSES)

    def execute(self, agent_run_id: str, request: ClaudeAgentCreateRequest) -> None:
        current = self.get(agent_run_id)
        if current is None:
            return
        if current.status in self.TERMINAL_STATUSES:
            self._clear_cancel_requested(agent_run_id)
            return

        # 下载图片（如果有）
        downloaded_images = []
        if request.images:
            bot_token = os.getenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN", "")
            if bot_token:
                downloader = TelegramImageDownloader(bot_token)
                
                for image_url in request.images:
                    file_id = parse_telegram_image_url(image_url)
                    if file_id:
                        local_path = downloader.download_image(file_id)
                        if local_path:
                            downloaded_images.append(local_path)
        
        # 构建带上下文的 Prompt（如果 session_id 存在）
        effective_prompt = request.prompt
        if current.session_id:
            # 获取历史对话
            effective_prompt = self._context_manager.build_context_aware_prompt(
                session_id=current.session_id,
                current_prompt=request.prompt,
                max_turns=10,  # 保留最近 10 轮对话
            )
        
        # 如果有图片，追加到 Prompt
        if downloaded_images:
            image_paths = "\n".join([f"- {path}" for path in downloaded_images])
            effective_prompt = f"{effective_prompt}\n\n请分析以下图片：\n{image_paths}"

        running = current.model_copy(
            update={
                "status": JobStatus.RUNNING,
                "updated_at": utc_now(),
                "error": None,
                "images": downloaded_images,  # 保存下载的图片路径
            }
        )
        self._repository.save(running.agent_run_id, running)

        if running.session_id is not None:
            # 追加用户消息到会话历史
            self._context_manager.append_user_message(
                session_id=running.session_id,
                content=request.prompt,
                metadata={"agent_run_id": running.agent_run_id},
            )
            
            self._openclaw_service.append_event(
                session_id=running.session_id,
                request=OpenClawSessionEventAppendRequest(
                    role="status",
                    content=f"agent running: {running.agent_run_id}",
                    metadata={
                        "agent_run_id": running.agent_run_id,
                        "images_downloaded": len(downloaded_images),
                        "context_aware": True,
                    },
                ),
            )
            self._openclaw_service.set_status(
                session_id=running.session_id,
                status=JobStatus.RUNNING,
            )

        env = os.environ.copy()
        env.update(request.env)
        started = time.perf_counter()
        work_dir = self._resolve_work_dir(request.work_dir)
        command = list(running.command)
        process: subprocess.Popen[str] | None = None

        try:
            process = subprocess.Popen(
                command,
                cwd=work_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self._register_process(agent_run_id, process)
            try:
                stdout_text, stderr_text = process.communicate(timeout=request.timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                process.kill()
                stdout_text, stderr_text = process.communicate()
                if exc.stdout:
                    stdout_text = f"{exc.stdout}{stdout_text}"
                if exc.stderr:
                    stderr_text = f"{exc.stderr}{stderr_text}"
                duration_seconds = time.perf_counter() - started
                timed_out = running.model_copy(
                    update={
                        "status": JobStatus.FAILED,
                        "returncode": -1,
                        "stdout_preview": self._preview_output(stdout_text),
                        "stderr_preview": self._preview_output(stderr_text),
                        "duration_seconds": duration_seconds,
                        "updated_at": utc_now(),
                        "error": f"agent timed out after {request.timeout_seconds}s",
                        "metadata": {
                            **running.metadata,
                            "work_dir": str(work_dir),
                            "env_overrides": request.env,
                            "timeout_failed": True,
                        },
                    }
                )
                self._repository.save(timed_out.agent_run_id, timed_out)
                self._finalize_openclaw_session(timed_out)
                return

            duration_seconds = time.perf_counter() - started
            returncode = int(process.returncode or 0)
            latest = self.get(agent_run_id)
            base_metadata = dict(latest.metadata if latest is not None else running.metadata)
            base_metadata.update(
                {
                    "work_dir": str(work_dir),
                    "env_overrides": request.env,
                }
            )
            cancel_reason = str(base_metadata.get("cancel_reason", "")).strip() or "cancelled by user"
            if self._is_cancel_requested(agent_run_id) or (latest is not None and latest.status is JobStatus.CANCELLED):
                finalized = running.model_copy(
                    update={
                        "status": JobStatus.CANCELLED,
                        "returncode": returncode,
                        "stdout_preview": self._preview_output(stdout_text),
                        "stderr_preview": self._preview_output(stderr_text),
                        "duration_seconds": duration_seconds,
                        "updated_at": utc_now(),
                        "error": cancel_reason,
                        "metadata": base_metadata,
                    }
                )
            else:
                succeeded = returncode == 0
                completed = subprocess.CompletedProcess(
                    args=command,
                    returncode=returncode,
                    stdout=stdout_text,
                    stderr=stderr_text,
                )
                finalized = running.model_copy(
                    update={
                        "status": JobStatus.COMPLETED if succeeded else JobStatus.FAILED,
                        "returncode": returncode,
                        "stdout_preview": self._preview_output(stdout_text),
                        "stderr_preview": self._preview_output(stderr_text),
                        "duration_seconds": duration_seconds,
                        "updated_at": utc_now(),
                        "error": None if succeeded else self._build_error_message(completed),
                        "metadata": base_metadata,
                    }
                )
            self._repository.save(finalized.agent_run_id, finalized)
            self._finalize_openclaw_session(finalized)
        except OSError as exc:
            duration_seconds = time.perf_counter() - started
            missing = running.model_copy(
                update={
                    "status": JobStatus.FAILED,
                    "returncode": -1,
                    "stderr_preview": self._preview_output(str(exc)),
                    "duration_seconds": duration_seconds,
                    "updated_at": utc_now(),
                    "error": str(exc),
                    "metadata": {
                        **running.metadata,
                        "work_dir": str(work_dir),
                        "env_overrides": request.env,
                        "launch_failed": True,
                        "launch_error_type": type(exc).__name__,
                    },
                }
            )
            self._repository.save(missing.agent_run_id, missing)
            self._finalize_openclaw_session(missing)
        except Exception as exc:
            duration_seconds = time.perf_counter() - started
            failed = running.model_copy(
                update={
                    "status": JobStatus.FAILED,
                    "returncode": -1,
                    "stderr_preview": self._preview_output(str(exc)),
                    "duration_seconds": duration_seconds,
                    "updated_at": utc_now(),
                    "error": str(exc),
                    "metadata": {
                        **running.metadata,
                        "work_dir": str(work_dir),
                        "env_overrides": request.env,
                        "internal_failure": True,
                        "internal_error_type": type(exc).__name__,
                    },
                }
            )
            self._repository.save(failed.agent_run_id, failed)
            self._finalize_openclaw_session(failed)
        finally:
            self._clear_cancel_requested(agent_run_id)
            if process is not None:
                self._unregister_process(agent_run_id)

    def fail_preflight(
        self,
        agent_run_id: str,
        request: ClaudeAgentCreateRequest,
        error: str,
    ) -> ClaudeAgentRunRead:
        current = self.get(agent_run_id)
        if current is None:
            raise KeyError(f"agent run not found: {agent_run_id}")
        if current.status in self.TERMINAL_STATUSES:
            return current

        failed = current.model_copy(
            update={
                "status": JobStatus.FAILED,
                "returncode": -1,
                "stdout_preview": None,
                "stderr_preview": self._preview_output(error),
                "duration_seconds": 0.0,
                "updated_at": utc_now(),
                "error": error,
                "metadata": {
                    **current.metadata,
                    "work_dir": str(self._resolve_work_dir(request.work_dir)),
                    "env_overrides": request.env,
                    "preflight_failed": True,
                },
            }
        )
        self._repository.save(failed.agent_run_id, failed)
        self._finalize_openclaw_session(failed)
        self._clear_cancel_requested(agent_run_id)
        return failed

    def cancel(
        self,
        agent_run_id: str,
        request: ClaudeAgentCancelRequest | None = None,
    ) -> ClaudeAgentRunRead:
        cancel_request = request or ClaudeAgentCancelRequest()
        current = self.get(agent_run_id)
        if current is None:
            raise KeyError(f"agent run not found: {agent_run_id}")
        if current.status in self.TERMINAL_STATUSES:
            return current

        reason = cancel_request.reason.strip() or "cancelled by user"
        metadata = dict(current.metadata)
        metadata.update(
            {
                "cancel_reason": reason,
                "cancel_requested_at": utc_now().isoformat(),
            }
        )
        cancelled = current.model_copy(
            update={
                "status": JobStatus.CANCELLED,
                "updated_at": utc_now(),
                "error": reason,
                "metadata": metadata,
            }
        )
        self._repository.save(cancelled.agent_run_id, cancelled)
        self._set_cancel_requested(agent_run_id)

        process = self._get_process(agent_run_id)
        if process is not None:
            try:
                process.terminate()
                try:
                    process.wait(timeout=self.CANCEL_GRACE_SECONDS)
                except subprocess.TimeoutExpired:
                    process.kill()
            except ProcessLookupError:
                pass

        if cancelled.session_id is not None:
            self._openclaw_service.append_event(
                session_id=cancelled.session_id,
                request=OpenClawSessionEventAppendRequest(
                    role="status",
                    content=f"agent cancelled: {cancelled.agent_run_id}",
                    metadata={
                        "agent_run_id": cancelled.agent_run_id,
                        "reason": reason,
                    },
                ),
            )
            self._openclaw_service.set_status(
                session_id=cancelled.session_id,
                status=JobStatus.CANCELLED,
                error=reason,
                metadata_updates={
                    "latest_agent_run_id": cancelled.agent_run_id,
                    "latest_status": JobStatus.CANCELLED.value,
                },
            )
        return cancelled

    def retry(
        self,
        agent_run_id: str,
        request: ClaudeAgentRetryRequest | None = None,
    ) -> tuple[ClaudeAgentRunRead, ClaudeAgentCreateRequest]:
        retry_request = request or ClaudeAgentRetryRequest()
        current = self.get(agent_run_id)
        if current is None:
            raise KeyError(f"agent run not found: {agent_run_id}")
        if current.status not in {JobStatus.FAILED, JobStatus.INTERRUPTED, JobStatus.CANCELLED}:
            raise ValueError("retry is only allowed for failed, interrupted, or cancelled agent runs")

        replay_request = self._build_retry_request(current, retry_request)
        replay_run = self.create(replay_request)

        if replay_run.session_id is not None:
            self._openclaw_service.append_event(
                session_id=replay_run.session_id,
                request=OpenClawSessionEventAppendRequest(
                    role="status",
                    content=f"agent retried: {current.agent_run_id} -> {replay_run.agent_run_id}",
                    metadata={
                        "agent_run_id": replay_run.agent_run_id,
                        "retry_of": current.agent_run_id,
                        "reason": retry_request.reason,
                    },
                ),
            )
        return replay_run, replay_request

    def build_task_tree(self, session_id: str | None = None) -> ClaudeAgentTreeRead:
        runs = self.list()
        if session_id is not None:
            runs = [run for run in runs if run.session_id == session_id]
        runs.sort(key=lambda run: run.created_at)

        run_by_id = {run.agent_run_id: run for run in runs}
        children: dict[str, list[str]] = {run.agent_run_id: [] for run in runs}
        edges: list[ClaudeAgentTreeEdgeRead] = []

        for run in runs:
            parent_id = run.parent_agent_id
            if parent_id and parent_id in run_by_id:
                children[parent_id].append(run.agent_run_id)
                edges.append(
                    ClaudeAgentTreeEdgeRead(
                        parent_agent_run_id=parent_id,
                        child_agent_run_id=run.agent_run_id,
                    )
                )

        roots = [
            run.agent_run_id
            for run in runs
            if run.parent_agent_id is None or run.parent_agent_id not in run_by_id
        ]

        nodes = [
            ClaudeAgentTreeNodeRead(
                agent_run_id=run.agent_run_id,
                parent_agent_id=run.parent_agent_id,
                session_id=run.session_id,
                task_name=run.task_name,
                status=run.status,
                created_at=run.created_at,
                updated_at=run.updated_at,
                children=children.get(run.agent_run_id, []),
                metadata=run.metadata,
            )
            for run in runs
        ]
        return ClaudeAgentTreeRead(
            session_id=session_id,
            root_agent_run_ids=roots,
            nodes=nodes,
            edges=edges,
            mermaid=self._render_mermaid_tree(nodes, edges),
        )

    def _finalize_openclaw_session(self, run: ClaudeAgentRunRead) -> None:
        if run.session_id is None:
            return
        
        # 保存助手响应到会话历史
        assistant_content = run.stdout_preview or run.error or "（无响应）"
        self._context_manager.append_assistant_message(
            session_id=run.session_id,
            content=assistant_content,
            metadata={
                "agent_run_id": run.agent_run_id,
                "returncode": run.returncode,
                "duration_seconds": run.duration_seconds,
            },
        )
        
        if run.status is JobStatus.COMPLETED:
            status_text = "completed"
        elif run.status is JobStatus.CANCELLED:
            status_text = "cancelled"
        elif run.status is JobStatus.INTERRUPTED:
            status_text = "interrupted"
        else:
            status_text = "failed"
        self._openclaw_service.append_event(
            session_id=run.session_id,
            request=OpenClawSessionEventAppendRequest(
                role="status",
                content=f"agent {status_text}: {run.agent_run_id}",
                metadata={
                    "agent_run_id": run.agent_run_id,
                    "returncode": run.returncode,
                    "duration_seconds": run.duration_seconds,
                    "error": run.error,
                    "context_aware": True,
                },
            ),
        )
        self._openclaw_service.set_status(
            session_id=run.session_id,
            status=run.status,
            error=run.error,
            metadata_updates={
                "latest_agent_run_id": run.agent_run_id,
                "latest_status": run.status.value,
            },
        )

    def _build_command(
        self,
        request: ClaudeAgentCreateRequest,
        prompt_override: str | None = None,
    ) -> list[str]:
        if request.command_override:
            command = list(request.command_override)
        else:
            command = list(self._claude_command)
            if request.agent_name:
                command.extend(["--agent", request.agent_name])
            if request.cli_args:
                command.extend(request.cli_args)
            else:
                command.append("--print")

        if request.append_prompt:
            command.append(prompt_override if prompt_override is not None else request.prompt)
        return command

    def _build_retry_request(
        self,
        current: ClaudeAgentRunRead,
        retry_request: ClaudeAgentRetryRequest,
    ) -> ClaudeAgentCreateRequest:
        prompt = retry_request.prompt_override or current.prompt
        timeout_seconds = retry_request.timeout_seconds_override or current.timeout_seconds
        metadata = dict(current.metadata)
        metadata.update(retry_request.metadata_updates)
        metadata.update(
            {
                "retry_of": current.agent_run_id,
                "retry_reason": retry_request.reason,
                "retry_depth": int(metadata.get("retry_depth", 0)) + 1,
            }
        )
        env_overrides = current.metadata.get("env_overrides")
        env: dict[str, str]
        if isinstance(env_overrides, dict):
            env = {str(key): str(value) for key, value in env_overrides.items()}
        else:
            env = {}
        skill_names = self._normalize_skill_name_list(current.metadata.get("requested_skill_names"))

        # Reuse exact previous command by default; when prompt is overridden, rebuild command.
        use_command_override = retry_request.prompt_override is None and bool(current.command)
        return ClaudeAgentCreateRequest(
            task_name=f"{current.task_name}_retry",
            prompt=prompt,
            agent_name=current.agent_name,
            session_id=current.session_id,
            parent_agent_id=current.agent_run_id,
            generation_depth=current.generation_depth,
            timeout_seconds=timeout_seconds,
            work_dir=current.work_dir,
            cli_args=[],
            command_override=list(current.command) if use_command_override else None,
            append_prompt=False if use_command_override else True,
            skill_names=skill_names,
            env=env,
            metadata=metadata,
        )

    def _resolve_requested_skill_names(
        self,
        *,
        request: ClaudeAgentCreateRequest,
        session_metadata: dict[str, Any],
    ) -> list[str]:
        explicit = self._normalize_skill_name_list(request.skill_names)
        if explicit:
            return explicit
        loaded = self._normalize_skill_name_list(session_metadata.get("loaded_skill_names"))
        return loaded

    def _compose_prompt_with_skills(
        self,
        *,
        prompt: str,
        requested_skill_names: list[str],
    ) -> tuple[str, list[OpenClawSkillRead]]:
        if not requested_skill_names:
            return prompt, []
        if self._openclaw_skill_service is None:
            raise ValueError("OpenClaw skill loader is not configured")

        skill_prompt, resolved_skills, missing = self._openclaw_skill_service.build_skills_catalog_prompt(
            requested_skill_names
        )
        if missing:
            raise ValueError(f"OpenClaw skills not found: {', '.join(missing)}")
        if not skill_prompt:
            return prompt, resolved_skills
        return f"{skill_prompt}\n\n{prompt}", resolved_skills

    def _normalize_skill_name_list(self, raw: Any) -> list[str]:
        if not isinstance(raw, list):
            return []
        normalized: list[str] = []
        seen: set[str] = set()
        for item in raw:
            if not isinstance(item, str):
                continue
            name = item.strip()
            if not name:
                continue
            lowered = name.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(name)
        return normalized

    def _build_error_message(self, completed: subprocess.CompletedProcess[str]) -> str:
        stderr = self._preview_output(completed.stderr or "")
        if stderr:
            return stderr
        return f"agent exited with code {completed.returncode}"

    def _resolve_work_dir(self, work_dir: str | None) -> Path:
        if work_dir is None:
            return self._repo_root
        path = Path(work_dir)
        if path.is_absolute():
            return path.resolve()
        return (self._repo_root / path).resolve()

    def _preview_output(self, text: str, limit: int = 1000) -> str | None:
        normalized = text.strip()
        if not normalized:
            return None
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 16] + "\n...[truncated]"

    def _render_mermaid_tree(
        self,
        nodes: list[ClaudeAgentTreeNodeRead],
        edges: list[ClaudeAgentTreeEdgeRead],
    ) -> str:
        if not nodes:
            return "graph TD\n  empty[\"No agent runs\"]"

        lines = [
            "graph TD",
            "classDef completed fill:#d1fae5,stroke:#059669,color:#065f46;",
            "classDef failed fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;",
            "classDef running fill:#dbeafe,stroke:#2563eb,color:#1e3a8a;",
            "classDef queued fill:#fef3c7,stroke:#d97706,color:#78350f;",
            "classDef interrupted fill:#ede9fe,stroke:#7c3aed,color:#4c1d95;",
            "classDef created fill:#e5e7eb,stroke:#6b7280,color:#111827;",
        ]
        for node in nodes:
            node_id = self._mermaid_node_id(node.agent_run_id)
            label = self._escape_mermaid_label(f"{node.task_name}\\n{node.status.value}")
            lines.append(f'  {node_id}["{label}"]')
            lines.append(f"  class {node_id} {self._status_class_name(node.status)};")

        for edge in edges:
            parent_id = self._mermaid_node_id(edge.parent_agent_run_id)
            child_id = self._mermaid_node_id(edge.child_agent_run_id)
            lines.append(f"  {parent_id} --> {child_id}")
        return "\n".join(lines)

    def _status_class_name(self, status: JobStatus) -> str:
        return status.value

    def _mermaid_node_id(self, raw_id: str) -> str:
        return "n_" + "".join(char if char.isalnum() else "_" for char in raw_id)

    def _escape_mermaid_label(self, text: str) -> str:
        return text.replace('"', '\\"')

    def _register_process(self, agent_run_id: str, process: subprocess.Popen[str]) -> None:
        with self._runtime_lock:
            self._running_processes[agent_run_id] = process

    def _get_process(self, agent_run_id: str) -> subprocess.Popen[str] | None:
        with self._runtime_lock:
            return self._running_processes.get(agent_run_id)

    def _unregister_process(self, agent_run_id: str) -> None:
        with self._runtime_lock:
            self._running_processes.pop(agent_run_id, None)

    def _set_cancel_requested(self, agent_run_id: str) -> None:
        with self._runtime_lock:
            self._cancel_requests.add(agent_run_id)

    def _is_cancel_requested(self, agent_run_id: str) -> bool:
        with self._runtime_lock:
            return agent_run_id in self._cancel_requests

    def _clear_cancel_requested(self, agent_run_id: str) -> None:
        with self._runtime_lock:
            self._cancel_requests.discard(agent_run_id)
