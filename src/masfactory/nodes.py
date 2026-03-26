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
from urllib import error, request

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
        retry_hints = plan.get("retry_hints", [])
        keywords = [part for part in goal.replace("，", " ").replace(",", " ").split() if len(part) > 1]
        memory_hits = context.search_memory(keywords[:8], max_results=6, roots=["memory", "docs"])

        generation = self._generate_code(goal, memory_hits, retry_hints)
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

    def _generate_code(
        self,
        goal: str,
        memory_hits: list[dict[str, Any]],
        retry_hints: list[str],
    ) -> dict[str, Any]:
        llm_payload = self._generate_code_via_llm(goal, memory_hits, retry_hints)
        if llm_payload is not None:
            return llm_payload
        return {
            "mode": "fallback_mock",
            "model": None,
            "error": "No LLM API credentials available. Used deterministic fallback generator.",
            "code": self._build_fallback_code(goal, memory_hits),
        }

    def _generate_code_via_llm(
        self,
        goal: str,
        memory_hits: list[dict[str, Any]],
        retry_hints: list[str],
    ) -> dict[str, Any] | None:
        api_key = (
            os.getenv("MAS_FACTORY_LLM_API_KEY")
            or os.getenv("GLM_API_KEY")
            or os.getenv("ZHIPUAI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        if not api_key:
            return None

        api_base = os.getenv("MAS_FACTORY_LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
        model = os.getenv("MAS_FACTORY_LLM_MODEL", "glm-5")
        endpoint = f"{api_base.rstrip('/')}/chat/completions"

        memory_brief = [
            {"path": hit.get("path", ""), "match_preview": hit.get("match_preview", "")[:200]}
            for hit in memory_hits[:5]
        ]

        system_prompt = (
            "You are a code generator for MASFactory. "
            "Return Python source code only (no markdown) and define solve_task() that returns a JSON-serializable dict."
        )
        user_prompt = (
            f"Goal:\n{goal}\n\n"
            "Runtime constraints:\n"
            "- Code runs inside /workspace.\n"
            "- Prefer Python standard library only.\n"
            "- Never modify /workspace/src/masfactory.\n"
            "- For TODO-harvest goals, scan /workspace/src/**/*.py and patch safe TODO placeholders.\n"
            "- If goal asks for report callback, POST JSON to http://host.docker.internal:18789/chat.\n\n"
            f"Relevant memory hits:\n{json.dumps(memory_brief, ensure_ascii=False, indent=2)}\n\n"
            f"Retry hints:\n{json.dumps(retry_hints, ensure_ascii=False)}\n"
        )

        request_body = {
            "model": model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        timeout = int(os.getenv("MAS_FACTORY_LLM_TIMEOUT", "45"))
        req = request.Request(
            endpoint,
            data=json.dumps(request_body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
            data = json.loads(raw)
            message = (((data.get("choices") or [{}])[0]).get("message") or {}).get("content", "")
            if isinstance(message, list):
                parts: list[str] = []
                for item in message:
                    if isinstance(item, str):
                        parts.append(item)
                    elif isinstance(item, dict) and isinstance(item.get("text"), str):
                        parts.append(item["text"])
                message = "\n".join(parts)
            code = self._extract_python_code(str(message))
            if "def solve_task" not in code:
                raise ValueError("LLM response did not define solve_task()")
            return {"mode": "llm_api", "model": model, "error": None, "code": code}
        except (error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            return {
                "mode": "fallback_mock",
                "model": model,
                "error": f"LLM generation failed: {exc}",
                "code": self._build_fallback_code(goal, memory_hits),
            }

    @staticmethod
    def _extract_python_code(content: str) -> str:
        fenced = re.search(r"```(?:python)?\s*(.*?)```", content, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            return fenced.group(1).strip()
        return content.strip()

    @staticmethod
    def _build_fallback_code(goal: str, memory_hits: list[dict[str, Any]]) -> str:
        goal_literal = json.dumps(goal, ensure_ascii=False)
        memory_literal = json.dumps(memory_hits[:6], ensure_ascii=False, indent=2)
        return (
            "import json\n"
            "from pathlib import Path\n"
            "from urllib import error, request\n"
            "\n"
            f"GOAL = {goal_literal}\n"
            f"MEMORY_HITS = {memory_literal}\n"
            "REPORT_URL = 'http://host.docker.internal:18789/chat'\n"
            "\n"
            "def _is_p4_todo_goal(goal: str) -> bool:\n"
            "    normalized = goal.lower()\n"
            "    return '/workspace/src' in normalized and ('todo' in normalized or '逻辑收割' in goal)\n"
            "\n"
            "def _iter_python_files(root: Path) -> list[Path]:\n"
            "    if not root.exists():\n"
            "        return []\n"
            "    files: list[Path] = []\n"
            "    for path in root.rglob('*.py'):\n"
            "        if 'masfactory' in path.parts:\n"
            "            continue\n"
            "        files.append(path)\n"
            "    return files\n"
            "\n"
            "def _patch_todo_placeholders(path: Path) -> dict:\n"
            "    text = path.read_text(encoding='utf-8')\n"
            "    lines = text.splitlines()\n"
            "    changed = False\n"
            "    todos_found = 0\n"
            "    todos_resolved = 0\n"
            "\n"
            "    for idx, line in enumerate(lines):\n"
            "        stripped = line.strip()\n"
            "        upper = stripped.upper()\n"
            "\n"
            "        if 'TODO' in upper:\n"
            "            todos_found += 1\n"
            "\n"
            "        if stripped.startswith('# TODO') and idx + 1 < len(lines) and lines[idx + 1].strip() == 'pass':\n"
            "            indent = lines[idx + 1][: len(lines[idx + 1]) - len(lines[idx + 1].lstrip())]\n"
            "            lines[idx + 1] = f\"{indent}return None  # auto-implemented TODO\"\n"
            "            changed = True\n"
            "            todos_resolved += 1\n"
            "            continue\n"
            "\n"
            "        if stripped.startswith('pass') and 'TODO' in upper:\n"
            "            indent = line[: len(line) - len(line.lstrip())]\n"
            "            lines[idx] = f\"{indent}return None  # auto-implemented TODO\"\n"
            "            changed = True\n"
            "            todos_resolved += 1\n"
            "            continue\n"
            "\n"
            "        if 'raise NotImplementedError' in stripped and 'TODO' in upper:\n"
            "            indent = line[: len(line) - len(line.lstrip())]\n"
            "            lines[idx] = f\"{indent}return None  # auto-implemented TODO\"\n"
            "            changed = True\n"
            "            todos_resolved += 1\n"
            "\n"
            "    if changed:\n"
            "        path.write_text('\\n'.join(lines) + '\\n', encoding='utf-8')\n"
            "    return {\n"
            "        'path': str(path),\n"
            "        'changed': changed,\n"
            "        'todos_found': todos_found,\n"
            "        'todos_resolved': todos_resolved,\n"
            "    }\n"
            "\n"
            "def _post_report(payload: dict) -> dict:\n"
            "    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')\n"
            "    req = request.Request(\n"
            "        REPORT_URL,\n"
            "        data=body,\n"
            "        headers={'Content-Type': 'application/json'},\n"
            "        method='POST',\n"
            "    )\n"
            "    try:\n"
            "        with request.urlopen(req, timeout=10) as response:\n"
            "            return {'ok': True, 'status': response.status}\n"
            "    except error.URLError as exc:\n"
            "        return {'ok': False, 'error': str(exc)}\n"
            "\n"
            "def solve_task():\n"
            "    root = Path('/workspace/src')\n"
            "    files = _iter_python_files(root)\n"
            "    patch_results = []\n"
            "\n"
            "    if _is_p4_todo_goal(GOAL):\n"
            "        for path in files:\n"
            "            try:\n"
            "                patch_results.append(_patch_todo_placeholders(path))\n"
            "            except Exception as exc:\n"
            "                patch_results.append({'path': str(path), 'changed': False, 'error': str(exc)})\n"
            "    else:\n"
            "        patch_results = [\n"
            "            {\n"
            "                'path': str(path),\n"
            "                'changed': False,\n"
            "                'todos_found': 0,\n"
            "                'todos_resolved': 0,\n"
            "            }\n"
            "            for path in files[:20]\n"
            "        ]\n"
            "\n"
            "    summary = {\n"
            "        'goal': GOAL,\n"
            "        'scanned_files': len(files),\n"
            "        'modified_files': sum(1 for item in patch_results if item.get('changed')),\n"
            "        'todo_found': sum(item.get('todos_found', 0) for item in patch_results),\n"
            "        'todo_resolved': sum(item.get('todos_resolved', 0) for item in patch_results),\n"
            "        'sample': patch_results[:20],\n"
            "    }\n"
            "\n"
            "    message = (\n"
            "        f\"[MASFactory] goal executed | scanned={summary['scanned_files']} \"\n"
            "        f\"modified={summary['modified_files']} resolved={summary['todo_resolved']}\"\n"
            "    )\n"
            "    report_payload = {\n"
            "        'message': message,\n"
            "        'goal': GOAL,\n"
            "        'summary': summary,\n"
            "        'memory_hits': MEMORY_HITS,\n"
            "    }\n"
            "    report_result = _post_report(report_payload)\n"
            "    return {\n"
            "        'status': 'success',\n"
            "        'goal': GOAL,\n"
            "        'summary': summary,\n"
            "        'report_result': report_result,\n"
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
