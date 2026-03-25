"""
Dynamic Tool Synthesis:
生成 Python 工具代码 -> 沙盒验证 -> 注册到工具池复用。
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
from typing import Any
from uuid import uuid4

# 设置清爽、专业的结构化日志
logger = logging.getLogger("agent_stack.executor")


RUNNER_SNIPPET = """
import importlib.util
import json
import sys

module_path = sys.argv[1]
entrypoint = sys.argv[2]
payload = json.loads(sys.argv[3])

spec = importlib.util.spec_from_file_location("synth_tool", module_path)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load module from {module_path}")

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

func = getattr(module, entrypoint, None)
if func is None or not callable(func):
    raise RuntimeError(f"Entrypoint '{entrypoint}' not found or not callable")

result = func(payload)
print(json.dumps(result, ensure_ascii=False))
"""

RUNNER_SOURCE_SNIPPET = """
import base64
import json
import sys

encoded_source = sys.argv[1]
entrypoint = sys.argv[2]
payload = json.loads(sys.argv[3])

source = base64.b64decode(encoded_source.encode("ascii")).decode("utf-8")
namespace = {}
exec(compile(source, "<synth_tool>", "exec"), namespace)

func = namespace.get(entrypoint)
if func is None or not callable(func):
    raise RuntimeError(f"Entrypoint '{entrypoint}' not found or not callable")

result = func(payload)
print(json.dumps(result, ensure_ascii=False))
"""


class ToolSynthesisError(RuntimeError):
    """Raised when generated tool validation or execution fails."""


@dataclass(frozen=True)
class ToolSynthesisPolicy:
    max_tools: int = 20
    timeout_seconds: int = 10
    max_code_chars: int = 20000
    execution_backend: str = "docker"  # docker | local
    docker_image: str = "python:3.12-alpine"
    docker_cpus: str = "1.0"
    docker_memory: str = "512m"
    docker_pids_limit: int = 128
    blocked_patterns: tuple[str, ...] = (
        r"\bos\.system\(",
        r"\bsubprocess\.",
        r"\bshutil\.rmtree\(",
        r"rm\s+-rf",
        r"\beval\(",
        r"\bexec\(",
    )


@dataclass(frozen=True)
class SynthesizedTool:
    tool_id: str
    tool_name: str
    entrypoint: str
    module_path: str
    status: str
    created_at: str
    updated_at: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "tool_name": self.tool_name,
            "entrypoint": self.entrypoint,
            "module_path": self.module_path,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
        }


class ToolSynthesizer:
    """Generate and run tool code in an isolated working directory."""

    def __init__(self, workspace: Path, policy: ToolSynthesisPolicy | None = None) -> None:
        self.policy = self._resolve_policy(policy)
        self.workspace = workspace.resolve()
        self.tools_dir = self.workspace / "tools"
        self.runtime_dir = self.workspace / "runtime"
        self.db_path = self.workspace / "synthesized_tools.sqlite3"
        self._lock = threading.Lock()

        self.tools_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def synthesize(
        self,
        tool_name: str,
        source_code: str,
        entrypoint: str = "run",
        sample_input: dict[str, Any] | None = None,
    ) -> SynthesizedTool:
        normalized_name = self._normalize_name(tool_name)
        self._validate_source(source_code)
        self._validate_entrypoint(entrypoint)

        tool_id = f"tool_{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        module_path = self.tools_dir / f"{normalized_name}_{tool_id}.py"

        with self._lock:
            if self.count_active_tools() >= self.policy.max_tools:
                raise ToolSynthesisError(
                    f"tool limit reached ({self.policy.max_tools}); reject new tool synthesis"
                )

            module_path.write_text(source_code, encoding="utf-8")

            try:
                self._execute_module(module_path, entrypoint, sample_input or {})
                record = SynthesizedTool(
                    tool_id=tool_id,
                    tool_name=normalized_name,
                    entrypoint=entrypoint,
                    module_path=str(module_path),
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
                self._upsert_record(record)
                return record
            except Exception as exc:
                failed = SynthesizedTool(
                    tool_id=tool_id,
                    tool_name=normalized_name,
                    entrypoint=entrypoint,
                    module_path=str(module_path),
                    status="failed",
                    created_at=now,
                    updated_at=now,
                    error=str(exc),
                )
                self._upsert_record(failed)
                raise ToolSynthesisError(str(exc)) from exc

    def invoke(self, tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        normalized_name = self._normalize_name(tool_name)
        row = self._get_active_tool_row(normalized_name)
        if row is None:
            raise ToolSynthesisError(f"active synthesized tool not found: {normalized_name}")

        module_path = Path(str(row["module_path"]))
        entrypoint = str(row["entrypoint"])
        return self._execute_module(module_path, entrypoint, payload)

    def list_tools(self) -> list[SynthesizedTool]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT tool_id, tool_name, entrypoint, module_path, status, created_at, updated_at, error
                FROM synthesized_tools
                ORDER BY updated_at DESC, tool_id DESC
                """
            ).fetchall()
        return [
            SynthesizedTool(
                tool_id=str(row["tool_id"]),
                tool_name=str(row["tool_name"]),
                entrypoint=str(row["entrypoint"]),
                module_path=str(row["module_path"]),
                status=str(row["status"]),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
                error=str(row["error"]) if row["error"] is not None else None,
            )
            for row in rows
        ]

    def count_active_tools(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(1) AS count
                FROM synthesized_tools
                WHERE status = 'active'
                """
            ).fetchone()
        return int(row["count"]) if row is not None else 0

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS synthesized_tools (
                    tool_id TEXT PRIMARY KEY,
                    tool_name TEXT NOT NULL,
                    entrypoint TEXT NOT NULL,
                    module_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    error TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_synthesized_tools_name_status
                ON synthesized_tools(tool_name, status, updated_at)
                """
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _upsert_record(self, record: SynthesizedTool) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO synthesized_tools (
                    tool_id, tool_name, entrypoint, module_path, status, created_at, updated_at, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tool_id) DO UPDATE SET
                    tool_name = excluded.tool_name,
                    entrypoint = excluded.entrypoint,
                    module_path = excluded.module_path,
                    status = excluded.status,
                    updated_at = excluded.updated_at,
                    error = excluded.error
                """,
                (
                    record.tool_id,
                    record.tool_name,
                    record.entrypoint,
                    record.module_path,
                    record.status,
                    record.created_at,
                    record.updated_at,
                    record.error,
                ),
            )
            connection.commit()

    def _get_active_tool_row(self, tool_name: str) -> sqlite3.Row | None:
        with self._connect() as connection:
            return connection.execute(
                """
                SELECT tool_id, tool_name, entrypoint, module_path, status, created_at, updated_at, error
                FROM synthesized_tools
                WHERE tool_name = ? AND status = 'active'
                ORDER BY updated_at DESC, tool_id DESC
                LIMIT 1
                """,
                (tool_name,),
            ).fetchone()

    def _normalize_name(self, tool_name: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9_]", "_", tool_name.strip().lower())
        normalized = re.sub(r"_+", "_", normalized).strip("_")
        if not normalized:
            raise ToolSynthesisError("tool_name is empty after normalization")
        if not re.match(r"^[a-z][a-z0-9_]*$", normalized):
            raise ToolSynthesisError("tool_name must start with a letter and use [a-z0-9_]")
        return normalized

    def _validate_entrypoint(self, entrypoint: str) -> None:
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", entrypoint):
            raise ToolSynthesisError(f"invalid entrypoint: {entrypoint}")

    def _validate_source(self, source_code: str) -> None:
        if len(source_code) > self.policy.max_code_chars:
            raise ToolSynthesisError(
                f"source code too large: {len(source_code)} > {self.policy.max_code_chars}"
            )
        for pattern in self.policy.blocked_patterns:
            if re.search(pattern, source_code):
                raise ToolSynthesisError(f"blocked unsafe pattern detected: {pattern}")

    def _execute_module(
        self,
        module_path: Path,
        entrypoint: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        safe_payload = json.dumps(payload, ensure_ascii=False)
        backend = self.policy.execution_backend.lower().strip()
        if backend == "docker":
            completed = self._execute_in_docker(module_path, entrypoint, safe_payload)
        elif backend == "local":
            completed = self._execute_local(module_path, entrypoint, safe_payload)
        else:
            raise ToolSynthesisError(
                f"unsupported execution backend: {self.policy.execution_backend}. use docker or local"
            )

        if completed.returncode != 0:
            stderr = completed.stderr.strip() or "unknown synthesis execution failure"
            raise ToolSynthesisError(stderr)

        return self._parse_json_output(completed.stdout)

    def _resolve_policy(self, policy: ToolSynthesisPolicy | None) -> ToolSynthesisPolicy:
        if policy is not None:
            return policy
        return ToolSynthesisPolicy(
            execution_backend=os.getenv("AUTORESEARCH_TOOL_SANDBOX_BACKEND", "docker"),
            docker_image=os.getenv("AUTORESEARCH_TOOL_SANDBOX_IMAGE", "python:3.12-alpine"),
            docker_cpus=os.getenv("AUTORESEARCH_TOOL_SANDBOX_CPUS", "1.0"),
            docker_memory=os.getenv("AUTORESEARCH_TOOL_SANDBOX_MEMORY", "512m"),
            docker_pids_limit=int(os.getenv("AUTORESEARCH_TOOL_SANDBOX_PIDS_LIMIT", "128")),
        )

    def _execute_local(
        self,
        module_path: Path,
        entrypoint: str,
        safe_payload: str,
    ) -> subprocess.CompletedProcess[str]:
        env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONIOENCODING": "utf-8",
        }
        return subprocess.run(
            [
                sys.executable,
                "-c",
                RUNNER_SNIPPET,
                str(module_path),
                entrypoint,
                safe_payload,
            ],
            cwd=self.runtime_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=self.policy.timeout_seconds,
        )

    def _execute_in_docker(
        self,
        module_path: Path,
        entrypoint: str,
        safe_payload: str,
    ) -> subprocess.CompletedProcess[str]:
        if shutil.which("docker") is None:
            raise ToolSynthesisError(
                "docker command not found. install/start Docker or set AUTORESEARCH_TOOL_SANDBOX_BACKEND=local"
            )

        self._cleanup_appledouble(self.workspace)
        source_code = module_path.read_text(encoding="utf-8")
        encoded_source = base64.b64encode(source_code.encode("utf-8")).decode("ascii")
        command = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--cpus",
            self.policy.docker_cpus,
            "--memory",
            self.policy.docker_memory,
            "--pids-limit",
            str(self.policy.docker_pids_limit),
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=16m",
            self.policy.docker_image,
            "python",
            "-c",
            RUNNER_SOURCE_SNIPPET,
            encoded_source,
            entrypoint,
            safe_payload,
        ]
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=self.policy.timeout_seconds,
        )

    def _cleanup_appledouble(self, root: Path) -> int:
        """
        物理切除 Mac 系统产生的 ._ 脏文件并记录拦截日志
        """
        count = 0
        # 查找所有以 ._ 开头的 AppleDouble 文件
        # 这些文件通常是由于 macOS 在非原生文件系统（如挂载的 Docker 卷）上尝试写入元数据产生的
        for path in root.rglob("._*"):
            if path.is_file():
                try:
                    path.unlink(missing_ok=True)
                    count += 1
                    # 这里的日志会被推送到你的浅色监控看板上
                    logger.info(f"[环境防御] 已拦截并物理清理宿主机残留文件: {path.name}")
                except Exception as e:
                    logger.warning(f"[环境防御] 清理文件 {path.name} 失败: {str(e)}")
        
        # 清理 .DS_Store 文件
        for path in root.rglob(".DS_Store"):
            if path.is_file():
                try:
                    path.unlink(missing_ok=True)
                    count += 1
                    logger.info(f"[环境防御] 已拦截并物理清理 .DS_Store 文件: {path.name}")
                except Exception as e:
                    logger.warning(f"[环境防御] 清理 .DS_Store 文件 {path.name} 失败: {str(e)}")
        
        if count > 0:
            logger.info(f"[环境防御] 预检完成：共计阻断 {count} 次潜在的环境污染风险，执行环境已恢复纯净。")
        
        return count

    def _parse_json_output(self, output_text: str) -> dict[str, Any]:
        output = output_text.strip()
        if not output:
            return {}

        for line in reversed(output.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
            return {"result": parsed}

        raise ToolSynthesisError("tool output is not valid JSON")
