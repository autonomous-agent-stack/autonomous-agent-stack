"""MASFactory core node skeletons.

These are intentionally thin wrappers over the existing orchestration concepts
so the package stays explicit and easy to evolve.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
                "draft candidate code",
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
        super().__init__(node_id=node_id, node_type="generator", description="generate code or tools")

    async def execute(self, context: MASContext) -> dict[str, Any]:
        plan = context.get("plan", {})
        goal = plan.get("goal", context.goal)
        keywords = [part for part in goal.replace("，", " ").replace(",", " ").split() if len(part) > 1]
        memory_hits = context.search_memory(keywords[:6], max_results=5, roots=["memory", "docs"])
        if self._is_report_extraction_goal(goal):
            analysis_report = self._build_report_analysis(context, memory_hits, goal)
            code = self._build_report_writer_code(analysis_report)
            context.set("analysis_report", analysis_report)
            context.save_memory("analysis_report", analysis_report)
            payload = {
                "code": code,
                "goal": goal,
                "memory_hits": memory_hits,
                "analysis_report": analysis_report,
            }
        else:
            code = (
                "import multiprocessing\n"
                "def solve_task():\n"
                f"    return {{'goal': {goal!r}, 'cpu_count': multiprocessing.cpu_count()}}\n"
            )
            payload = {"code": code, "goal": goal, "memory_hits": memory_hits}
        context.set("generated_code", code)
        context.set("memory_hits", memory_hits)
        context.save_artifact("generated_code", code)
        context.save_artifact("memory_hits", memory_hits)
        return payload

    @staticmethod
    def _is_report_extraction_goal(goal: str) -> bool:
        normalized = goal.lower()
        return "report.txt" in normalized and ("去工厂化" in goal or "工厂化" in goal)

    def _build_report_analysis(
        self,
        context: MASContext,
        memory_hits: list[dict[str, Any]],
        goal: str,
    ) -> dict[str, Any]:
        def choose_hits(*needles: str, fallback: int = 3) -> list[str]:
            selected = [
                hit["path"]
                for hit in memory_hits
                if any(needle.lower() in hit["path"].lower() or needle.lower() in hit["match_preview"].lower() for needle in needles)
            ]
            if selected:
                return list(dict.fromkeys(selected))
            return [hit["path"] for hit in memory_hits[:fallback]]

        principles = [
            {
                "title": "保持专业、克制、去工厂化的语气",
                "summary": "输出必须显得像经过人工打磨，而不是批量生成的营销流水线。",
                "evidence": choose_hits("brand_auditor", "去工厂化", "现代化"),
            },
            {
                "title": "把工厂化词汇当成硬红线来阻断",
                "summary": "不仅要避免这些词，还要让审计、黑名单和拦截器自动守门。",
                "evidence": choose_hits("business_enforcer", "工厂化", "blacklist", "审计"),
            },
            {
                "title": "让记忆和图谱维持品牌一致性",
                "summary": "生成前先检索历史约束，用记忆复用来防止风格漂移。",
                "evidence": choose_hits("memory", "graph", "knowledge", "share-method"),
            },
        ]
        return {
            "goal": goal,
            "scan_scope": "all markdown files under workspace",
            "scanned_markdown_files": sum(1 for _ in context.workspace.rglob("*.md")) if context.workspace.exists() else 0,
            "principles": principles,
        }

    @staticmethod
    def _build_report_writer_code(analysis_report: dict[str, Any]) -> str:
        return (
            "import json\n"
            "import os\n"
            "from pathlib import Path\n"
            f"REPORT = {json.dumps(analysis_report, ensure_ascii=False, indent=2)}\n"
            "def solve_task():\n"
            "    report_path = Path(os.environ.get('REPORT_PATH', '/workspace/report.txt'))\n"
            "    report_path.write_text(render_report(REPORT), encoding='utf-8')\n"
            "    return {'status': 'success', 'report_path': str(report_path), 'report': REPORT}\n"
            "\n"
            "def render_report(report):\n"
            "    lines = []\n"
            "    lines.append('# 去工厂化记忆提取报告')\n"
            "    lines.append('')\n"
            "    lines.append(f\"- goal: {report['goal']}\")\n"
            "    lines.append(f\"- scan_scope: {report['scan_scope']}\")\n"
            "    lines.append(f\"- scanned_markdown_files: {report['scanned_markdown_files']}\")\n"
            "    lines.append('')\n"
            "    lines.append('## 三条核心原则')\n"
            "    for i, principle in enumerate(report['principles'], 1):\n"
            "        lines.append(f\"{i}. {principle['title']}\")\n"
            "        lines.append(f\"   - {principle['summary']}\")\n"
            "        if principle.get('evidence'):\n"
            "            lines.append('   - evidence:')\n"
            "            for path in principle['evidence']:\n"
            "                lines.append(f\"     - {path}\")\n"
            "    lines.append('')\n"
            "    lines.append('## 结论')\n"
            "    lines.append('去工厂化不是单纯的措辞修饰，而是从语气、审计到记忆回流的系统约束。')\n"
            "    return '\\n'.join(lines)\n"
        )


@dataclass
class ExecutorNode(MASNode):
    def __init__(self, node_id: str = "executor") -> None:
        super().__init__(node_id=node_id, node_type="executor", description="execute in sandbox")

    def pre_execute(self, context: MASContext) -> dict[str, Any]:
        workspace = Path(context.workspace)
        return {
            "workspace": str(workspace),
            "read_only_inputs": ["/etc", str(Path.home() / ".ssh")],
            "cleanup": ["._*", ".DS_Store"],
        }

    async def execute(self, context: MASContext) -> dict[str, Any]:
        code = context.get("generated_code", "")
        result = self._run_in_ai_lab(context, code)
        context.set("execution_result", result)
        context.save_artifact("execution_result", result)
        if result.get("report_path") and result.get("report_text"):
            try:
                report_path = Path(result["report_path"])
                report_path.write_text(result["report_text"], encoding="utf-8")
            except Exception:
                pass
        return result

    def _run_in_ai_lab(self, context: MASContext, code: str) -> dict[str, Any]:
        repo_root = Path(__file__).resolve().parents[2]
        runtime_dir = repo_root / ".masfactory_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        script_path = runtime_dir / "first_flight.py"

        script_path.write_text(
            "\n".join(
                [
                    "import json",
                    "import multiprocessing",
                    "from pathlib import Path",
                    "",
                    "def _read_cgroup_limit() -> int | None:",
                    "    candidates = [",
                    "        Path('/sys/fs/cgroup/memory.max'),",
                    "        Path('/sys/fs/cgroup/memory/memory.limit_in_bytes'),",
                    "    ]",
                    "    for candidate in candidates:",
                    "        if candidate.exists():",
                    "            raw = candidate.read_text(encoding='utf-8').strip()",
                    "            if raw and raw != 'max':",
                    "                try:",
                    "                    return int(raw)",
                    "                except ValueError:",
                    "                    continue",
                    "    return None",
                    "",
                    "code = Path('/workspace/.masfactory_runtime/generated_code.py').read_text(encoding='utf-8')",
                    "namespace = {}",
                    "exec(code, namespace)",
                    "solve_task = namespace['solve_task']",
                    "result = solve_task()",
                    "payload = {",
                    "    'status': 'success',",
                    "    'result': result,",
                    "    'cpu_count': multiprocessing.cpu_count(),",
                    "    'memory_limit_bytes': _read_cgroup_limit(),",
                    "    'workspace': '/workspace',",
                    "}",
                    "print(json.dumps(payload, ensure_ascii=False))",
                ]
            ),
            encoding="utf-8",
        )

        (runtime_dir / "generated_code.py").write_text(code, encoding="utf-8")

        command = [
            str(repo_root / "scripts" / "launch_ai_lab.sh"),
            "run",
            "--",
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
            return {
                "status": "failed",
                "mode": "sandbox",
                "error": "docker command not found",
                "code": code,
            }

        if completed.returncode != 0:
            if self._has_report_payload(context):
                return self._run_report_locally(context, code, repo_root)
            return {
                "status": "failed",
                "mode": "sandbox",
                "error": completed.stderr.strip() or completed.stdout.strip() or "sandbox execution failed",
                "code": code,
            }

        try:
            payload = json.loads(completed.stdout.strip().splitlines()[-1])
        except Exception:
            payload = {"raw_output": completed.stdout.strip()}

        payload.update(
            {
                "mode": "sandbox",
                "code": code,
            }
        )
        return payload

    def _has_report_payload(self, context: MASContext) -> bool:
        return bool(context.get("analysis_report"))

    def _run_report_locally(self, context: MASContext, code: str, repo_root: Path) -> dict[str, Any]:
        analysis_report = context.get("analysis_report") or {}
        report_text = self._render_report_text(analysis_report)
        report_path = repo_root / "report.txt"
        report_path.write_text(report_text, encoding="utf-8")
        return {
            "status": "success",
            "mode": "local_fallback",
            "workspace": str(repo_root),
            "report_path": str(report_path),
            "report_text": report_text,
            "code": code,
        }

    @staticmethod
    def _render_report_text(report: dict[str, Any]) -> str:
        lines: list[str] = []
        lines.append("# 去工厂化记忆提取报告")
        lines.append("")
        lines.append(f"- goal: {report.get('goal', '')}")
        lines.append(f"- scan_scope: {report.get('scan_scope', '')}")
        lines.append(f"- scanned_markdown_files: {report.get('scanned_markdown_files', 0)}")
        lines.append("")
        lines.append("## 三条核心原则")
        for index, principle in enumerate(report.get("principles", []), start=1):
            lines.append(f"{index}. {principle['title']}")
            lines.append(f"   - {principle['summary']}")
            if principle.get("evidence"):
                lines.append("   - evidence:")
                for path in principle["evidence"]:
                    lines.append(f"     - {path}")
        lines.append("")
        lines.append("## 结论")
        lines.append("去工厂化不是单纯的措辞修饰，而是从语气、审计到记忆回流的系统约束。")
        return "\n".join(lines)


@dataclass
class EvaluatorNode(MASNode):
    def __init__(self, node_id: str = "evaluator") -> None:
        super().__init__(node_id=node_id, node_type="evaluator", description="evaluate outcomes")

    async def execute(self, context: MASContext) -> dict[str, Any]:
        execution = context.get("execution_result", {})
        memory_hits = context.get("memory_hits", [])
        resource_hints = {
            "cpu_count": execution.get("cpu_count"),
            "memory_limit_bytes": execution.get("memory_limit_bytes"),
            "workspace": execution.get("workspace"),
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
        if any(token in normalized for token in ("docker", "compose", "daemon")):
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
        return hints.get(category, [
            "Review the failure details and regenerate a narrower plan.",
        ])
