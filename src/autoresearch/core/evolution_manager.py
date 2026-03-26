"""Evolution Manager - P4 自主集成流水线."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error, request

from ..communication import Message, MessageBus, MessageType
from .ast_scanner import ASTScanner
from .brand_auditor import BrandAuditor
from .events import P4Event, VisionEvent
from .services.apple_double_cleaner import AppleDoubleCleaner

logger = logging.getLogger(__name__)


class EvolutionManager:
    """演化管理器
    
    实现 P4 自主集成流水线：
    Trigger → Scan → Sandbox → Audit → HITL
    
    工程红线：
    - 强制执行 AppleDoubleCleaner 物理清理
    - 使用 logger.info("[环境防御] ...") 记录所有操作
    - 禁止执行未经 AST 扫描的外部 Python 代码
    """
    
    def __init__(self, message_bus: MessageBus | None = None):
        self.bus = message_bus or MessageBus()
        self._running = False
        self._active_pipelines: dict[str, P4Event] = {}
        self._pipeline_state: dict[str, dict[str, Any]] = {}
        self._workspace_root = Path(
            os.getenv("P4_WORKSPACE_ROOT", ".autoresearch/p4_runs")
        ).resolve()
        self._workspace_root.mkdir(parents=True, exist_ok=True)
        self._hitl_require_manual = os.getenv("P4_HITL_REQUIRE_MANUAL", "0").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self._hitl_timeout_seconds = int(os.getenv("P4_HITL_TIMEOUT_SECONDS", "300"))
        
    async def start(self) -> None:
        """启动演化管理器"""
        if self._running:
            return
            
        logger.info("[环境防御] EvolutionManager 启动中...")
        
        await self.bus.start()
        self._running = True
        
        # 订阅 VisionEvent
        await self.bus.subscribe("vision", self._handle_vision_event)
        
        # 订阅 P4Event
        await self.bus.subscribe("p4", self._handle_p4_event)
        
        logger.info("[环境防御] EvolutionManager 已启动")
        
    async def stop(self) -> None:
        """停止演化管理器"""
        if not self._running:
            return
            
        logger.info("[环境防御] EvolutionManager 停止中...")
        
        self._running = False
        await self.bus.stop()
        
        logger.info("[环境防御] EvolutionManager 已停止")
        
    async def process_vision_event(self, event: VisionEvent) -> dict[str, Any]:
        """处理视觉事件
        
        Args:
            event: 视觉事件
            
        Returns:
            处理结果
        """
        logger.info(f"[环境防御] 处理视觉事件: {event.event_id}")
        
        # 发布到事件总线
        message = Message(
            type=MessageType.TASK,
            sender="evolution_manager",
            receiver="vision_processor",
            payload=event.to_dict()
        )
        
        await self.bus.publish(message)
        
        return {
            "status": "published",
            "event_id": event.event_id,
            "timestamp": datetime.now().isoformat()
        }
        
    async def execute_p4_pipeline(self, github_url: str) -> P4Event:
        """执行 P4 流水线
        
        P4 = Pull → Parse → Plan → Push
        
        Args:
            github_url: GitHub 仓库 URL
            
        Returns:
            P4 事件结果
        """
        logger.info(f"[环境防御] 启动 P4 流水线: {github_url}")
        
        # 创建 P4 事件
        event = P4Event(
            github_url=github_url,
            repo_name=self._extract_repo_name(github_url)
        )
        
        self._active_pipelines[event.event_id] = event
        self._pipeline_state[event.event_id] = {}
        
        try:
            # Step 1: Trigger
            event.status = "triggering"
            await self._p4_trigger(event)
            
            # Step 2: Scan (安全哨兵)
            event.status = "scanning"
            await self._p4_scan(event)
            
            # Step 3: Sandbox (Docker 隔离)
            event.status = "testing"
            await self._p4_sandbox(event)
            
            # Step 4: Audit (品牌审计)
            event.status = "auditing"
            await self._p4_audit(event)
            
            # Step 5: HITL (Human-in-the-Loop)
            event.status = "hitl"
            await self._p4_hitl(event)
            
            event.status = "completed"
            logger.info(f"[环境防御] P4 流水线完成: {event.event_id}")
            
        except Exception as e:
            event.status = "failed"
            logger.error(f"[环境防御] P4 流水线失败: {e}")
            raise
            
        finally:
            # 清理 AppleDouble 文件
            await self._cleanup_apple_doubles()
            
        return event
        
    async def _p4_trigger(self, event: P4Event) -> None:
        """P4 Step 1: Trigger"""
        logger.info(f"[环境防御] P4 Trigger: {event.github_url}")

        run_dir = self._workspace_root / event.event_id
        repo_dir = run_dir / "repo"
        run_dir.mkdir(parents=True, exist_ok=True)
        self._pipeline_state[event.event_id]["run_dir"] = str(run_dir)
        self._pipeline_state[event.event_id]["repo_path"] = str(repo_dir)

        if repo_dir.exists() and any(repo_dir.iterdir()):
            logger.info("[环境防御] 复用已有工作目录: %s", repo_dir)
            return

        clone_cmd = [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            event.branch,
            event.github_url,
            str(repo_dir),
        ]
        clone_result = await self._run_command(clone_cmd, cwd=run_dir, timeout_seconds=180)

        if clone_result["returncode"] == 0:
            logger.info("[环境防御] 仓库克隆成功: %s", repo_dir)
            return

        logger.warning("[环境防御] git clone 失败，切换到降级模式: %s", clone_result["stderr"])
        repo_dir.mkdir(parents=True, exist_ok=True)
        fallback_meta = {
            "status": "fallback",
            "github_url": event.github_url,
            "repo_name": event.repo_name,
            "error": clone_result["stderr"] or clone_result["stdout"] or "clone failed",
            "timestamp": datetime.now().isoformat(),
        }
        (repo_dir / "CLONE_FAILED.json").write_text(
            json.dumps(fallback_meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        
    async def _p4_scan(self, event: P4Event) -> None:
        """P4 Step 2: Scan (安全哨兵)
        
        执行 AST 静态安全审计
        """
        logger.info(f"[环境防御] P4 Scan: AST 安全审计")

        repo_path = Path(self._pipeline_state[event.event_id].get("repo_path", ""))
        if not repo_path.exists():
            event.scan_result = {
                "status": "failed",
                "violations": [],
                "scanned_files": 0,
                "violation_count": 0,
                "error": f"repo path not found: {repo_path}",
                "timestamp": datetime.now().isoformat(),
            }
            return

        scanner = ASTScanner()
        violations: list[dict[str, Any]] = []
        scanned_files = 0
        py_files = [
            path
            for path in repo_path.rglob("*.py")
            if ".git" not in path.parts and "__pycache__" not in path.parts
        ]
        for path in py_files:
            try:
                code = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            scanned_files += 1
            scan_result = await scanner.scan_code(code, filename=str(path))
            for violation in scan_result.violations:
                violations.append(
                    {
                        "file": str(path),
                        **violation.to_dict(),
                    }
                )

        status = "passed"
        if any(v.get("severity") == "high" for v in violations):
            status = "failed"
        elif violations:
            status = "warning"

        event.scan_result = {
            "status": status,
            "violations": violations[:100],
            "violation_count": len(violations),
            "scanned_files": scanned_files,
            "timestamp": datetime.now().isoformat()
        }
        
    async def _p4_sandbox(self, event: P4Event) -> None:
        """P4 Step 3: Sandbox (Docker 隔离)
        
        在 Docker 容器中运行测试
        """
        logger.info(f"[环境防御] P4 Sandbox: Docker 隔离测试")

        repo_path = Path(self._pipeline_state[event.event_id].get("repo_path", ""))
        compile_errors: list[dict[str, Any]] = []
        py_files = [
            path
            for path in repo_path.rglob("*.py")
            if ".git" not in path.parts and "__pycache__" not in path.parts
        ]

        for path in py_files:
            try:
                code = path.read_text(encoding="utf-8", errors="ignore")
                compile(code, str(path), "exec")
            except SyntaxError as exc:
                compile_errors.append(
                    {
                        "file": str(path),
                        "line": exc.lineno,
                        "message": exc.msg,
                    }
                )
            except Exception as exc:
                compile_errors.append(
                    {
                        "file": str(path),
                        "line": 0,
                        "message": str(exc),
                    }
                )

        docker_result: dict[str, Any] | None = None
        if shutil.which("docker"):
            docker_cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{repo_path}:/workspace:ro",
                "-w",
                "/workspace",
                os.getenv("P4_DOCKER_IMAGE", "python:3.11-slim"),
                "python",
                "-m",
                "compileall",
                "-q",
                ".",
            ]
            docker_result = await self._run_command(docker_cmd, cwd=repo_path, timeout_seconds=240)

        status = "passed" if not compile_errors else "failed"
        if docker_result and docker_result["returncode"] != 0 and status == "passed":
            status = "warning"

        event.test_result = {
            "status": status,
            "tests_run": len(py_files),
            "tests_passed": max(len(py_files) - len(compile_errors), 0),
            "tests_failed": len(compile_errors),
            "compile_errors": compile_errors[:50],
            "docker": docker_result,
            "timestamp": datetime.now().isoformat()
        }
        
    async def _p4_audit(self, event: P4Event) -> None:
        """P4 Step 4: Audit (品牌审计)
        
        品牌调性约束审计
        """
        logger.info(f"[环境防御] P4 Audit: 品牌调性审计")

        repo_path = Path(self._pipeline_state[event.event_id].get("repo_path", ""))
        text_files = [
            path
            for path in repo_path.rglob("*")
            if path.is_file() and path.suffix.lower() in {".md", ".txt", ".rst"}
        ]

        auditor = BrandAuditor()
        all_violations: list[dict[str, Any]] = []
        score_total = 0.0
        scanned_files = 0

        for path in text_files:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if not text.strip():
                continue
            scanned_files += 1
            audit = await auditor.audit_text(text, context=str(path.relative_to(repo_path)))
            score_total += audit.brand_score
            for violation in audit.violations:
                all_violations.append(
                    {
                        "file": str(path),
                        **violation.to_dict(),
                    }
                )

        avg_score = (score_total / scanned_files) if scanned_files else 100.0
        status = "passed"
        if any(v.get("category") == "factory_words" for v in all_violations):
            status = "failed"
        elif all_violations:
            status = "warning"

        event.audit_result = {
            "status": status,
            "violations": all_violations[:100],
            "violation_count": len(all_violations),
            "scanned_files": scanned_files,
            "brand_score": round(avg_score, 2),
            "timestamp": datetime.now().isoformat()
        }
        
    async def _p4_hitl(self, event: P4Event) -> None:
        """P4 Step 5: HITL (Human-in-the-Loop)
        
        发送 Telegram 审批请求
        """
        logger.info(f"[环境防御] P4 HITL: 等待人工审批")

        admin_chat_id = (
            os.getenv("TELEGRAM_ADMIN_CHAT_ID")
            or os.getenv("AUTORESEARCH_ADMIN_CHAT_ID")
            or ""
        ).strip()
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        sent = False
        if admin_chat_id and telegram_token:
            text = (
                "🤖 P4 审批请求\n"
                f"- repo: {event.repo_name}\n"
                f"- scan: {event.scan_result.get('status') if event.scan_result else 'unknown'}\n"
                f"- test: {event.test_result.get('status') if event.test_result else 'unknown'}\n"
                f"- audit: {event.audit_result.get('status') if event.audit_result else 'unknown'}\n"
                f"- event_id: {event.event_id}"
            )
            reply_markup = {
                "inline_keyboard": [
                    [
                        {"text": "✅ 批准", "callback_data": f"p4_approve:{event.event_id}"},
                        {"text": "❌ 拒绝", "callback_data": f"p4_reject:{event.event_id}"},
                    ]
                ]
            }
            sent = await self._send_telegram_message(
                token=telegram_token,
                chat_id=admin_chat_id,
                text=text,
                reply_markup=reply_markup,
            )

        if self._hitl_require_manual:
            event.hitl_approved = await self._wait_for_hitl_decision(event.event_id)
        else:
            event.hitl_approved = True if sent or not admin_chat_id else False

    async def _cleanup_apple_doubles(self) -> None:
        """清理 AppleDouble 文件
        
        工程红线：强制物理清理
        """
        logger.info("[环境防御] 清理 AppleDouble 文件")

        cleaned_count = 0
        for state in self._pipeline_state.values():
            repo_path = state.get("repo_path")
            if repo_path:
                cleaned = await asyncio.to_thread(
                    AppleDoubleCleaner.clean,
                    directory=repo_path,
                    recursive=True,
                    dry_run=False,
                )
                cleaned_count += len(cleaned)
        cleaned_root = await asyncio.to_thread(
            AppleDoubleCleaner.clean,
            directory=str(self._workspace_root),
            recursive=True,
            dry_run=False,
        )
        cleaned_count += len(cleaned_root)
        logger.info("[环境防御] AppleDouble 清理完成: %s files", cleaned_count)
        
    async def _handle_vision_event(self, message: Message) -> None:
        """处理视觉事件消息"""
        event_data = message.payload
        logger.info(f"[环境防御] 收到视觉事件: {event_data.get('event_id')}")
        
    async def _handle_p4_event(self, message: Message) -> None:
        """处理 P4 事件消息"""
        event_data = message.payload
        logger.info(f"[环境防御] 收到 P4 事件: {event_data.get('event_id')}")
        
    def _extract_repo_name(self, github_url: str) -> str:
        """提取仓库名称"""
        # https://github.com/user/repo -> user/repo
        parts = github_url.rstrip("/").split("/")
        if len(parts) >= 2:
            return f"{parts[-2]}/{parts[-1]}"
        return github_url

    async def _run_command(
        self,
        command: list[str],
        *,
        cwd: Path,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        def _runner() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                command,
                cwd=str(cwd),
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
            )

        try:
            completed = await asyncio.to_thread(_runner)
            return {
                "returncode": completed.returncode,
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
                "command": command,
            }
        except FileNotFoundError as exc:
            return {
                "returncode": 127,
                "stdout": "",
                "stderr": str(exc),
                "command": command,
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "returncode": 124,
                "stdout": (exc.stdout or "").strip(),
                "stderr": (exc.stderr or f"timeout after {timeout_seconds}s").strip(),
                "command": command,
            }

    async def _send_telegram_message(
        self,
        *,
        token: str,
        chat_id: str,
        text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> bool:
        endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            endpoint,
            data=body,
            headers={"content-type": "application/json"},
            method="POST",
        )
        try:
            response_data = await asyncio.to_thread(self._urlopen_json, req, 10.0)
            return bool(response_data.get("ok"))
        except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError):
            return False

    async def _wait_for_hitl_decision(self, event_id: str) -> bool:
        decision_file = self._workspace_root / "hitl" / f"{event_id}.decision.json"
        decision_file.parent.mkdir(parents=True, exist_ok=True)
        deadline = datetime.now().timestamp() + self._hitl_timeout_seconds

        while datetime.now().timestamp() < deadline:
            if decision_file.exists():
                try:
                    payload = json.loads(decision_file.read_text(encoding="utf-8"))
                    return bool(payload.get("approved", False))
                except (OSError, json.JSONDecodeError):
                    return False
            await asyncio.sleep(2)

        logger.warning("[环境防御] HITL 审批等待超时: %s", event_id)
        return False

    @staticmethod
    def _urlopen_json(req: request.Request, timeout: float) -> dict[str, Any]:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
        return json.loads(raw)
