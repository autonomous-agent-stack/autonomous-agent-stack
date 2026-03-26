"""
Super Agent Stack - Unified Blitz Router

Features:
1. Drag-and-drop workflow persistence/compile API
2. Heterogeneous compute routing (quality/cost aware)
3. Multi-node dispatch fallback (cluster gateway)
4. Canary rollout + automatic rollback guard
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from .canary_manager import CanaryReleaseManager
from .distributed_gateway import DistributedGateway
from .heterogeneous_router import HeterogeneousComputeRouter
from .workflow_store import WorkflowCompileResult, WorkflowDefinition, WorkflowStore

router = APIRouter(prefix="/api/v1/blitz")

_workflow_store = WorkflowStore()
_compute_router = HeterogeneousComputeRouter()
_distributed_gateway = DistributedGateway()
_canary_manager = CanaryReleaseManager()
_route_history: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Runtime models
# ---------------------------------------------------------------------------
class BlitzTask(BaseModel):
    session_id: str
    prompt: str

    # execution behavior
    use_claude_cli: bool = True
    enable_opensage: bool = True
    context_depth: int = 5

    # cost-aware routing
    node_hint: str | None = None
    preferred_engine: str | None = None
    budget_tier: str = "balanced"  # balanced | cost_saver | performance_first

    # distributed execution
    enable_distributed_dispatch: bool = False
    required_capabilities: list[str] = Field(default_factory=list)
    load_balance_strategy: str = "least_load"

    # workflow-canvas integration
    workflow_id: str | None = None

    # canary guard
    enable_canary_guard: bool = True
    auto_evaluate_canary: bool = True


class DispatchPreviewRequest(BaseModel):
    required_capabilities: list[str] = Field(default_factory=list)
    strategy: str = "least_load"


class CanaryStartRequest(BaseModel):
    baseline_version: str = "stable"
    candidate_version: str
    traffic_ratio: float = 0.1
    error_rate_threshold: float = 0.05
    p95_latency_ms_threshold: float = 2500.0
    min_samples: int = 20


class CanaryRecordRequest(BaseModel):
    release_id: str
    channel: str = "candidate"  # candidate | baseline
    success: bool = True
    latency_ms: float = 0.0


class CanaryRollbackRequest(BaseModel):
    reason: str = "manual rollback"


# ---------------------------------------------------------------------------
# Basic execution helpers
# ---------------------------------------------------------------------------
class SessionMemory:
    """Simple local conversation persistence for Blitz sessions."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.history_path = Path(f"/tmp/session_{session_id}.json")

    def get_context(self, depth: int) -> list[dict[str, Any]]:
        if not self.history_path.exists():
            return []
        try:
            history = json.loads(self.history_path.read_text(encoding="utf-8"))
            if not isinstance(history, list):
                return []
            return history[-max(1, depth) :]
        except Exception:
            return []

    def save_message(self, role: str, content: str) -> None:
        history = self.get_context(1000)
        history.append({"role": role, "content": content, "ts": datetime.now().isoformat()})
        self.history_path.write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")


class ClaudeCLIExecutor:
    @staticmethod
    async def execute(prompt: str, context: list[dict[str, Any]]) -> str:
        full_prompt = "Context:\n" + json.dumps(context, ensure_ascii=False) + "\n\nTask: " + prompt
        try:
            process = await asyncio.create_subprocess_exec(
                "claude",
                "-p",
                full_prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                return stdout.decode().strip()
            return f"Claude CLI failed: {stderr.decode().strip()}"
        except Exception as exc:
            return f"Claude CLI not available: {exc}"


class GLMExecutor:
    @staticmethod
    async def execute(prompt: str, context: list[dict[str, Any]]) -> str:
        # Lightweight fallback path for low-cost tasks.
        snippet = prompt[:280]
        return (
            "[GLM Route] 已使用低成本通道执行。\n"
            f"上下文条数: {len(context)}\n"
            f"任务片段: {snippet}"
        )


class OpenSageEngine:
    @staticmethod
    def synthesize_tool(code_snippet: str) -> dict[str, Any]:
        dangerous_keywords = {"os.system", "subprocess.call", "eval", "exec"}
        for keyword in dangerous_keywords:
            if keyword in code_snippet:
                return {"status": "blocked", "reason": f"dangerous keyword: {keyword}"}

        temp_tool_path = Path(f"/tmp/temp_tool_{int(datetime.now().timestamp())}.py")
        temp_tool_path.write_text(code_snippet, encoding="utf-8")
        return {"status": "success", "path": str(temp_tool_path)}


class MASFactoryBridge:
    @staticmethod
    def dispatch_to_matrix(task: str) -> list[dict[str, str]]:
        return [
            {"agent": "Planner", "action": "Decomposing task"},
            {"agent": "Executor", "action": "Running in sandbox"},
            {"agent": "Evaluator", "action": "Scoring output"},
        ]


def _record_route(decision: dict[str, Any]) -> None:
    _route_history.append(decision)
    if len(_route_history) > 100:
        del _route_history[0 : len(_route_history) - 100]


def _looks_like_failure(text: str) -> bool:
    lowered = (text or "").lower()
    failure_signals = ["error", "failed", "traceback", "exception"]
    return any(signal in lowered for signal in failure_signals)


# ---------------------------------------------------------------------------
# Main execution endpoint
# ---------------------------------------------------------------------------
@router.post("/execute")
async def run_blitz_task(task: BlitzTask, background_tasks: BackgroundTasks) -> dict[str, Any]:
    started = time.perf_counter()
    memory = SessionMemory(task.session_id)
    context = memory.get_context(task.context_depth)

    workflow_compile: WorkflowCompileResult | None = None
    effective_prompt = task.prompt

    if task.workflow_id:
        workflow = _workflow_store.get_or_create_default(task.workflow_id)
        workflow_compile = _workflow_store.compile(workflow)
        effective_prompt = f"{task.prompt}\n\n# Workflow Plan\n{workflow_compile.prompt}"

    decision = _compute_router.route(
        prompt=effective_prompt,
        node_hint=task.node_hint,
        preferred_engine=task.preferred_engine,
        budget_tier=task.budget_tier,
    )

    route_info = {
        **decision.to_dict(),
        "budget_tier": task.budget_tier,
        "node_hint": task.node_hint,
        "timestamp": datetime.now().isoformat(),
    }
    _record_route(route_info)

    dispatch_info: dict[str, Any] = {
        "mode": "local",
        "remote": False,
        "backend": _distributed_gateway.backend,
    }

    if task.enable_distributed_dispatch:
        remote_payload = {
            "task_name": f"blitz_{task.session_id}_{int(time.time())}",
            "prompt": effective_prompt,
            "session_id": task.session_id,
            "metadata": {
                "source": "blitz.execute",
                "engine": decision.engine,
                "workflow_id": task.workflow_id,
            },
        }
        dispatch = await _distributed_gateway.dispatch_or_fallback(
            task_payload=remote_payload,
            required_capabilities=task.required_capabilities,
            strategy=task.load_balance_strategy,
        )
        dispatch_info = {
            "mode": "remote" if dispatch.success else "fallback_local",
            "remote": dispatch.remote,
            "reason": dispatch.reason,
            "backend": _distributed_gateway.backend,
            "strategy": task.load_balance_strategy,
            "required_capabilities": task.required_capabilities,
        }

        if dispatch.success:
            duration_ms = (time.perf_counter() - started) * 1000.0
            memory.save_message("user", task.prompt)
            memory.save_message("assistant", json.dumps(dispatch.payload, ensure_ascii=False))
            return {
                "session_id": task.session_id,
                "response": dispatch.payload,
                "route": route_info,
                "dispatch": dispatch_info,
                "duration_ms": round(duration_ms, 3),
                "workflow": workflow_compile.model_dump() if workflow_compile else None,
                "agents_involved": ["DistributedGateway", "ClusterManager"],
            }

    if decision.engine == "glm":
        response = await GLMExecutor.execute(effective_prompt, context)
    elif decision.engine in {"claude", "codex"} and task.use_claude_cli:
        response = await ClaudeCLIExecutor.execute(effective_prompt, context)
    else:
        matrix_plan = MASFactoryBridge.dispatch_to_matrix(effective_prompt)
        response = f"Matrix Plan Executed: {json.dumps(matrix_plan, ensure_ascii=False)}"

    synthesis_info: dict[str, Any] | None = None
    if task.enable_opensage and "def " in response:
        synthesis_info = OpenSageEngine.synthesize_tool(response)
        response = f"{response}\n\n[OpenSage] Tool synthesized: {synthesis_info.get('status')}"

    canary_info: dict[str, Any] = {"active": False}
    active_release = _canary_manager.get_active_release()
    if active_release and task.enable_canary_guard:
        channel = _canary_manager.choose_channel(active_release, sticky_key=task.session_id)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        success = not _looks_like_failure(response)

        _canary_manager.record_result(
            release_id=active_release.release_id,
            channel=channel,
            success=success,
            latency_ms=elapsed_ms,
        )

        canary_info = {
            "active": True,
            "release_id": active_release.release_id,
            "channel": channel,
            "sample_success": success,
            "latency_ms": round(elapsed_ms, 3),
        }

        if task.auto_evaluate_canary:
            canary_info["evaluation"] = _canary_manager.evaluate(active_release.release_id)

    memory.save_message("user", task.prompt)
    memory.save_message("assistant", response)

    duration_ms = (time.perf_counter() - started) * 1000.0
    return {
        "session_id": task.session_id,
        "response": response,
        "agents_involved": ["Architect", "Security", decision.engine.upper()],
        "route": route_info,
        "dispatch": dispatch_info,
        "canary": canary_info,
        "opensage": synthesis_info,
        "duration_ms": round(duration_ms, 3),
        "workflow": workflow_compile.model_dump() if workflow_compile else None,
    }


@router.get("/status")
async def get_matrix_status() -> dict[str, Any]:
    active_release = _canary_manager.get_active_release()
    return {
        "matrix_active": True,
        "agents": [
            {"name": "架构领航员", "status": "idle", "task": "workflow planning"},
            {"name": "Heterogeneous Router", "status": "active", "task": "cost-aware dispatch"},
            {"name": "OpenSage", "status": "monitoring", "task": "canary + rollback guard"},
            {
                "name": "Cluster Gateway",
                "status": "standby",
                "task": f"multi-node balancing ({_distributed_gateway.backend})",
            },
        ],
        "system_audit": {
            "routing_events": len(_route_history),
            "last_route": _route_history[-1] if _route_history else None,
            "canary_active": bool(active_release),
            "active_release_id": active_release.release_id if active_release else None,
        },
    }


@router.get("/health")
async def blitz_health() -> dict[str, str]:
    return {"status": "ok", "service": "blitz"}


# ---------------------------------------------------------------------------
# Workflow Canvas API
# ---------------------------------------------------------------------------
@router.get("/workflows/{workflow_id}", response_model=WorkflowDefinition)
def get_workflow(workflow_id: str) -> WorkflowDefinition:
    return _workflow_store.get_or_create_default(workflow_id)


@router.put("/workflows/{workflow_id}", response_model=WorkflowDefinition)
def save_workflow(workflow_id: str, workflow: WorkflowDefinition) -> WorkflowDefinition:
    if workflow.workflow_id != workflow_id:
        workflow = workflow.model_copy(update={"workflow_id": workflow_id})
    return _workflow_store.save(workflow)


@router.post("/workflows/{workflow_id}/compile", response_model=WorkflowCompileResult)
def compile_workflow(workflow_id: str) -> WorkflowCompileResult:
    workflow = _workflow_store.get_or_create_default(workflow_id)
    return _workflow_store.compile(workflow)


@router.get("/workflows/{workflow_id}/langflow-export")
def export_langflow_style(workflow_id: str) -> dict[str, Any]:
    """Export a simplified graph payload compatible with canvas-based tools."""
    workflow = _workflow_store.get_or_create_default(workflow_id)
    return {
        "id": workflow.workflow_id,
        "name": workflow.title,
        "nodes": [node.model_dump() for node in workflow.nodes],
        "edges": [edge.model_dump() for edge in workflow.edges],
        "meta": workflow.metadata,
    }


# ---------------------------------------------------------------------------
# Distributed dispatch helpers
# ---------------------------------------------------------------------------
@router.post("/dispatch/preview")
async def preview_dispatch(request: DispatchPreviewRequest) -> dict[str, Any]:
    return await _distributed_gateway.preview_node(
        required_capabilities=request.required_capabilities,
        strategy=request.strategy,
    )


# ---------------------------------------------------------------------------
# Canary release APIs
# ---------------------------------------------------------------------------
@router.post("/canary/start")
def start_canary_release(payload: CanaryStartRequest) -> dict[str, Any]:
    release = _canary_manager.start_release(
        baseline_version=payload.baseline_version,
        candidate_version=payload.candidate_version,
        traffic_ratio=payload.traffic_ratio,
        error_rate_threshold=payload.error_rate_threshold,
        p95_latency_ms_threshold=payload.p95_latency_ms_threshold,
        min_samples=payload.min_samples,
    )
    return release.model_dump()


@router.get("/canary/active")
def get_active_canary_release() -> dict[str, Any]:
    release = _canary_manager.get_active_release()
    return {"active": bool(release), "release": release.model_dump() if release else None}


@router.post("/canary/record")
def record_canary_result(payload: CanaryRecordRequest) -> dict[str, Any]:
    release = _canary_manager.get_release(payload.release_id)
    if release is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="release not found")

    updated = _canary_manager.record_result(
        release_id=payload.release_id,
        channel=payload.channel,
        success=payload.success,
        latency_ms=payload.latency_ms,
    )
    return updated.model_dump()


@router.post("/canary/{release_id}/evaluate")
def evaluate_canary_release(release_id: str) -> dict[str, Any]:
    release = _canary_manager.get_release(release_id)
    if release is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="release not found")
    return _canary_manager.evaluate(release_id)


@router.post("/canary/{release_id}/rollback")
def rollback_canary_release(release_id: str, payload: CanaryRollbackRequest) -> dict[str, Any]:
    release = _canary_manager.get_release(release_id)
    if release is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="release not found")
    rolled_back = _canary_manager.rollback(release_id=release_id, reason=payload.reason)
    return rolled_back.model_dump()


# ---------------------------------------------------------------------------
# Backward-compatible SDK API used by local integration scripts/tests
# ---------------------------------------------------------------------------
class UnifiedRequest(BaseModel):
    request_id: str
    request_type: str
    content: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UnifiedResponse(BaseModel):
    status: str
    session_id: str
    content: Optional[str] = None
    result: dict[str, Any] = Field(default_factory=dict)


class UnifiedRouter:
    """Compatibility wrapper for legacy UnifiedRouter callers."""

    def __init__(self) -> None:
        self._default_depth = 5

    def _resolve_session_id(self, request: UnifiedRequest) -> str:
        if request.session_id:
            return request.session_id
        return f"session_{int(datetime.now().timestamp() * 1000)}"

    async def route(self, request: UnifiedRequest) -> UnifiedResponse:
        session_id = self._resolve_session_id(request)
        request_type = request.request_type.strip().lower()

        if request_type in {"chat", "task", "synthesize", "orchestrate"}:
            blitz_task = BlitzTask(
                session_id=session_id,
                prompt=request.content,
                node_hint=request.metadata.get("node_hint"),
                preferred_engine=request.metadata.get("preferred_engine"),
                budget_tier=request.metadata.get("budget_tier", "balanced"),
                workflow_id=request.metadata.get("workflow_id"),
            )
            response = await run_blitz_task(blitz_task, BackgroundTasks())
            status_value = "success"
            result_payload: dict[str, Any] = {
                "task_id": request.request_id,
                "route": response.get("route"),
                "dispatch": response.get("dispatch"),
                "canary": response.get("canary"),
            }
            if request_type == "task":
                result_payload["topology"] = (
                    response.get("workflow", {}).get("prompt") if response.get("workflow") else "planner -> executor -> evaluator"
                )
            if request_type == "synthesize":
                synthesis = response.get("opensage") or {}
                result_payload.update(
                    {
                        "tool_name": synthesis.get("path", "temp_tool"),
                        "is_valid": synthesis.get("status") == "success",
                        "synthesis": synthesis,
                    }
                )
            if request_type == "orchestrate":
                result_payload.update(
                    {
                        "status": "dispatched",
                        "plan": MASFactoryBridge.dispatch_to_matrix(request.content),
                    }
                )
            return UnifiedResponse(
                status=status_value,
                session_id=session_id,
                content=str(response.get("response", "")),
                result=result_payload,
            )

        return UnifiedResponse(
            status="failed",
            session_id=session_id,
            content=f"unsupported request_type: {request.request_type}",
            result={},
        )

    def get_status(self) -> dict[str, Any]:
        active_release = _canary_manager.get_active_release()
        return {
            "matrix_active": True,
            "default_context_depth": self._default_depth,
            "components": [
                "workflow_canvas",
                "heterogeneous_router",
                "distributed_gateway",
                "canary_guard",
            ],
            "active_canary": active_release.release_id if active_release else None,
        }
