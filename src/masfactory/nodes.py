"""MASFactory core node skeletons.

These nodes stay intentionally explicit and lightweight so the execution path
is easy to debug.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from .context import MASContext


@dataclass
class MASNode:
    node_id: str
    node_type: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    async def execute(self, context: MASContext) -> dict[str, Any]:
        raise NotImplementedError


@dataclass
class PlannerNode(MASNode):
    def __init__(self, node_id: str = "planner") -> None:
        super().__init__(node_id=node_id, node_type="planner", description="plan the next move")

    async def execute(self, context: MASContext) -> dict[str, Any]:
        plan = {
            "goal": context.goal,
            "next_steps": [
                "inspect workspace",
                "generate runnable code",
                "run in sandbox",
                "evaluate result",
            ],
        }
        previous_evaluation = context.load_memory("last_evaluation") or context.get("last_evaluation")
        if isinstance(previous_evaluation, dict):
            retry_hints = previous_evaluation.get("retry_hints") or []
            if previous_evaluation.get("decision") == "retry" and retry_hints:
                plan["retry_hints"] = list(retry_hints)
        context.set("plan", plan)
        context.save_memory("last_plan", plan)
        return plan


@dataclass
class GeneratorNode(MASNode):
    def __init__(self, node_id: str = "generator") -> None:
        super().__init__(node_id=node_id, node_type="generator", description="generate task code")

    async def execute(self, context: MASContext) -> dict[str, Any]:
        plan = context.get("plan", {})
        goal = self._resolve_goal(context, plan)
        retry_hints = self._normalize_retry_hints(plan.get("retry_hints", []))
        memory_hits = self._resolve_memory_hits(context, goal)

        generation = await self._generate_code(goal, memory_hits, retry_hints)
        code = generation["code"]

        payload = {
            "code": code,
            "goal": goal,
            "memory_hits": memory_hits,
            "generation_mode": generation["mode"],
        }
        if generation.get("model"):
            payload["model"] = generation["model"]
        if generation.get("error"):
            payload["generation_error"] = generation["error"]

        context.set("generated_code", code)
        context.set("memory_hits", memory_hits)
        context.set("generation_mode", generation["mode"])
        context.save_artifact("generated_code", code)
        context.save_artifact("memory_hits", memory_hits)
        context.save_artifact("generation_meta", {k: v for k, v in generation.items() if k != "code"})
        return payload

    @staticmethod
    def _resolve_goal(context: MASContext, plan: dict[str, Any]) -> str:
        goal = str(plan.get("goal") or context.goal or "").strip()
        if not goal:
            goal = "explore and learn"
        context.goal = goal
        return goal

    @staticmethod
    def _normalize_retry_hints(retry_hints: Any) -> list[str]:
        if isinstance(retry_hints, list):
            return [str(item).strip() for item in retry_hints if str(item).strip()]
        if isinstance(retry_hints, str) and retry_hints.strip():
            return [retry_hints.strip()]
        return []

    @staticmethod
    def _resolve_memory_hits(context: MASContext, goal: str) -> list[dict[str, Any]]:
        cached_hits = context.get("memory_hits")
        if isinstance(cached_hits, list):
            return [item for item in cached_hits if isinstance(item, dict)]

        keywords = [part for part in goal.replace("，", " ").replace(",", " ").split() if len(part) > 1]
        return context.search_memory(keywords[:8], max_results=6, roots=["memory", "docs"])

    async def _generate_code(
        self,
        goal: str,
        memory_hits: list[dict[str, Any]],
        retry_hints: list[str],
    ) -> dict[str, Any]:
        llm_payload = await self._generate_code_via_llm(goal, memory_hits, retry_hints)
        if llm_payload is not None:
            return llm_payload
        fallback_reason = "No LLM API credentials available. Used fallback generator."
        return {
            "mode": "fallback_mock",
            "model": None,
            "error": fallback_reason,
            "code": self._build_fallback_code(goal, fallback_reason, memory_hits),
        }

    async def _generate_code_via_llm(
        self,
        goal: str,
        memory_hits: list[dict[str, Any]],
        retry_hints: list[str],
    ) -> dict[str, Any] | None:
        llm_config = self._resolve_llm_config()
        if llm_config is None:
            return None

        endpoint = f"{llm_config['base_url'].rstrip('/')}/chat/completions"
        system_prompt, user_prompt = self._build_generation_prompt(goal, memory_hits, retry_hints)

        request_body = {
            "model": llm_config["model"],
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=llm_config["timeout"]) as client:
                response = await client.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {llm_config['api_key']}",
                        "Content-Type": "application/json",
                    },
                    json=request_body,
                )
                response.raise_for_status()
            data = response.json()
            message = self._extract_message_content(data)
            code = self._extract_python_code(str(message))
            if not code:
                raise ValueError("LLM response contained no code")
            if not re.search(r"^\s*def\s+solve_task\s*\(", code, flags=re.MULTILINE):
                raise ValueError("LLM response did not define solve_task()")
            return {"mode": "llm_api", "model": llm_config["model"], "error": None, "code": code}
        except (httpx.HTTPError, json.JSONDecodeError, ValueError) as exc:
            fallback_reason = f"LLM generation failed: {exc}"
            return {
                "mode": "fallback_mock",
                "model": llm_config["model"],
                "error": fallback_reason,
                "code": self._build_fallback_code(goal, fallback_reason, memory_hits),
            }

    @staticmethod
    def _resolve_llm_config() -> dict[str, Any] | None:
        explicit_key = os.getenv("MAS_FACTORY_LLM_API_KEY", "").strip()
        glm_key = os.getenv("GLM_API_KEY", "").strip() or os.getenv("ZHIPUAI_API_KEY", "").strip()
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()

        if explicit_key:
            api_key = explicit_key
            provider = "glm"
        elif glm_key:
            api_key = glm_key
            provider = "glm"
        elif openai_key:
            api_key = openai_key
            provider = "openai"
        else:
            return None

        configured_base = os.getenv("MAS_FACTORY_LLM_BASE_URL", "").strip()
        if configured_base:
            base_url = configured_base.rstrip("/")
        elif provider == "glm":
            base_url = os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4").rstrip("/")
        else:
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

        model_override = os.getenv("MAS_FACTORY_LLM_MODEL", "").strip()
        if model_override:
            model = model_override
        elif provider == "glm":
            model = "glm-5"
        else:
            model = "gpt-4o-mini"

        timeout = float(os.getenv("MAS_FACTORY_LLM_TIMEOUT", "45"))
        return {
            "api_key": api_key,
            "provider": provider,
            "base_url": base_url,
            "model": model,
            "timeout": timeout,
        }

    @staticmethod
    def _build_generation_prompt(
        goal: str,
        memory_hits: list[dict[str, Any]],
        retry_hints: list[str],
    ) -> tuple[str, str]:
        memory_brief = [
            {"path": hit.get("path", ""), "match_preview": str(hit.get("match_preview", ""))[:200]}
            for hit in memory_hits[:6]
        ]
        system_prompt = (
            "You are a MASFactory code generation agent. "
            "Write a self-contained Python script that can run immediately in /workspace. "
            "Return Python code only with a top-level solve_task() function. "
            "solve_task() must return a JSON-serializable dict."
        )
        user_prompt = (
            f"Goal:\n{goal}\n\n"
            f"Memory hits:\n{json.dumps(memory_brief, ensure_ascii=False, indent=2)}\n\n"
            f"Retry hints:\n{json.dumps(retry_hints, ensure_ascii=False, indent=2)}\n\n"
            "Requirements:\n"
            "- Produce execution-ready Python.\n"
            "- Prefer standard library.\n"
            "- Do not modify /workspace/src/masfactory.\n"
            "- Return code only, no markdown explanations."
        )
        return system_prompt, user_prompt

    @staticmethod
    def _extract_message_content(data: dict[str, Any]) -> str:
        content = (((data.get("choices") or [{}])[0]).get("message") or {}).get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                    continue
                if isinstance(item, dict):
                    if isinstance(item.get("text"), str):
                        parts.append(item["text"])
                    elif isinstance(item.get("content"), str):
                        parts.append(item["content"])
            return "\n".join(part for part in parts if part).strip()
        return str(content).strip()

    @staticmethod
    def _extract_python_code(content: str) -> str:
        python_fenced = re.search(r"```python\s*(.*?)```", content, flags=re.DOTALL | re.IGNORECASE)
        if python_fenced:
            return python_fenced.group(1).strip()

        generic_fenced = re.search(r"```\s*(.*?)```", content, flags=re.DOTALL)
        if generic_fenced:
            candidate = generic_fenced.group(1).strip()
            if "\n" in candidate:
                first_line, rest = candidate.split("\n", 1)
                if re.fullmatch(r"[a-zA-Z0-9_+-]+", first_line.strip()):
                    candidate = rest.strip()
            return candidate

        return content.strip()

    @staticmethod
    def _build_fallback_code(goal: str, reason: str, memory_hits: list[dict[str, Any]]) -> str:
        goal_literal = json.dumps(goal, ensure_ascii=False)
        reason_literal = json.dumps(reason, ensure_ascii=False)
        memory_paths = [str(hit.get("path", "")) for hit in memory_hits[:6]]
        memory_literal = json.dumps(memory_paths, ensure_ascii=False)
        return (
            f"GOAL = {goal_literal}\n"
            f"REASON = {reason_literal}\n"
            f"MEMORY_HIT_PATHS = {memory_literal}\n"
            "\n"
            "def solve_task():\n"
            "    return {\n"
            "        'status': 'fallback',\n"
            "        'goal': GOAL,\n"
            "        'reason': REASON,\n"
            "        'memory_hit_paths': MEMORY_HIT_PATHS,\n"
            "    }\n"
        )


@dataclass
class ExecutorNode(MASNode):
    def __init__(self, node_id: str = "executor") -> None:
        super().__init__(node_id=node_id, node_type="executor", description="execute generated code in sandbox")

    def pre_execute(self, context: MASContext) -> dict[str, Any]:
        workspace = Path(context.workspace)
        return {
            "workspace": str(workspace),
            "read_only_inputs": ["/etc", str(Path.home() / ".ssh")],
            "cleanup": ["._*", ".DS_Store"],
        }

    async def execute(self, context: MASContext) -> dict[str, Any]:
        code = context.get("generated_code", "")
        result = self._run_in_ai_lab(code)
        context.set("execution_result", result)
        context.save_artifact("execution_result", result)
        return result

    def _run_in_ai_lab(self, code: str) -> dict[str, Any]:
        repo_root = Path(__file__).resolve().parents[2]
        runtime_dir = repo_root / ".masfactory_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        script_path = runtime_dir / "first_flight.py"

        script_path.write_text(
            "\n".join(
                [
                    "import json",
                    "import traceback",
                    "from pathlib import Path",
                    "",
                    "payload = {'status': 'failed', 'workspace': '/workspace'}",
                    "try:",
                    "    code = Path('/workspace/.masfactory_runtime/generated_code.py').read_text(encoding='utf-8')",
                    "    namespace = {}",
                    "    exec(code, namespace)",
                    "    solve_task = namespace.get('solve_task')",
                    "    if not callable(solve_task):",
                    "        raise RuntimeError('generated code must define solve_task()')",
                    "    result = solve_task()",
                    "    payload = {'status': 'success', 'result': result, 'workspace': '/workspace'}",
                    "except Exception as exc:",
                    "    payload = {",
                    "        'status': 'failed',",
                    "        'error': str(exc),",
                    "        'traceback': traceback.format_exc(),",
                    "        'workspace': '/workspace',",
                    "    }",
                    "",
                    "print(json.dumps(payload, ensure_ascii=False))",
                ]
            ),
            encoding="utf-8",
        )

        (runtime_dir / "generated_code.py").write_text(code, encoding="utf-8")

        command = [
            str(repo_root / "scripts" / "launch_ai_lab.sh"),
            "run",
            "python",
            "/workspace/.masfactory_runtime/first_flight.py",
        ]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=repo_root,
                env={
                    **os.environ,
                    "PYTHONUNBUFFERED": "1",
                    "EXTRA_VOLUME": f"{runtime_dir}:/workspace/.masfactory_runtime:rw",
                    "AUTO_OPEN_DOCKER": "0",
                },
            )
        except FileNotFoundError:
            return self._run_locally(code, repo_root, "docker command not found")

        if completed.returncode != 0:
            return self._run_locally(
                code,
                repo_root,
                completed.stderr.strip() or completed.stdout.strip() or "sandbox execution failed",
            )

        payload = self._parse_json_from_output(completed.stdout)
        payload.update({"mode": "sandbox", "code": code})
        return payload

    @staticmethod
    def _parse_json_from_output(stdout: str) -> dict[str, Any]:
        lines = [line for line in stdout.splitlines() if line.strip()]
        if not lines:
            return {"status": "failed", "error": "empty sandbox output"}
        for line in reversed(lines):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
        return {"status": "failed", "raw_output": stdout.strip() or "<empty>"}

    @staticmethod
    def _run_locally(code: str, repo_root: Path, reason: str) -> dict[str, Any]:
        namespace: dict[str, Any] = {}
        try:
            exec(code, namespace)
            solve_task = namespace.get("solve_task")
            if not callable(solve_task):
                raise RuntimeError("generated code must define solve_task()")
            result = solve_task()
            return {
                "status": "success",
                "mode": "local_fallback",
                "workspace": str(repo_root),
                "result": result,
                "sandbox_error": reason,
                "code": code,
            }
        except Exception as exc:
            return {
                "status": "failed",
                "mode": "local_fallback",
                "workspace": str(repo_root),
                "error": f"{reason}; local fallback failed: {exc}",
                "code": code,
            }


@dataclass
class EvaluatorNode(MASNode):
    def __init__(self, node_id: str = "evaluator") -> None:
        super().__init__(node_id=node_id, node_type="evaluator", description="evaluate outcomes")

    async def execute(self, context: MASContext) -> dict[str, Any]:
        execution = context.get("execution_result", {})
        memory_hits = context.get("memory_hits", [])
        resource_hints = {
            "workspace": execution.get("workspace"),
            "mode": execution.get("mode"),
        }
        success = execution.get("status") == "success"
        failure_category = None
        retry_hints: list[str] = []
        if not success:
            failure_category = self._classify_failure(str(execution.get("error", "")))
            retry_hints = self._retry_hints_for_failure(failure_category)
        if success and execution.get("mode") == "local_fallback" and not retry_hints:
            retry_hints = ["Task completed locally because the sandbox was unavailable."]
        evaluation = {
            "score": 0.95 if success else 0.25,
            "decision": "continue" if success else "retry",
            "notes": "skeleton evaluation",
            "memory_hits": memory_hits,
            "resource_hints": resource_hints,
            "failure_category": failure_category,
            "retry_hints": retry_hints,
        }
        context.set("evaluation", evaluation)
        context.set("retry_hints", retry_hints)
        context.save_memory("last_evaluation", evaluation)
        context.save_memory("last_retry_hints", retry_hints)
        return evaluation

    @staticmethod
    def _classify_failure(error_message: str) -> str:
        normalized = error_message.lower()
        if any(token in normalized for token in ("oom", "out of memory", "killed", "exit code 137")):
            return "resource_overflow"
        if any(token in normalized for token in ("syntaxerror", "invalid syntax", "nameerror", "indentationerror")):
            return "logic_error"
        if any(token in normalized for token in ("docker", "compose", "daemon", "runc", "oci runtime")):
            return "sandbox_error"
        return "runtime_error"

    @staticmethod
    def _retry_hints_for_failure(category: str | None) -> list[str]:
        hints: dict[str, list[str]] = {
            "logic_error": [
                "Run a syntax/indentation check before the next generation pass.",
                "Reduce the code path to a smaller, testable function.",
                "Add or tighten a unit test around the failing branch.",
            ],
            "resource_overflow": [
                "Lower peak memory usage by streaming or chunking the input.",
                "Avoid loading the full workspace or large datasets at once.",
                "Retry with a smaller problem slice and re-measure.",
            ],
            "sandbox_error": [
                "Run `make ai-lab-check` before retrying the flight.",
                "Verify Docker Desktop is running and the daemon is reachable.",
                "Confirm `/Users/ai_lab/workspace` is mounted and writable.",
            ],
            "runtime_error": [
                "Inspect stderr and stdout with WATCH=1 enabled.",
                "Retry the same goal after capturing the exact failure text.",
            ],
        }
        if category is None:
            return []
        return hints.get(category, ["Review the failure details and regenerate a narrower plan."])
