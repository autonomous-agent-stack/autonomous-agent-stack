#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from orchestrator import create_graph_from_prompt
except ModuleNotFoundError:
    from src.orchestrator import create_graph_from_prompt


def _supports_kwarg(func: object, name: str) -> bool:
    try:
        return name in inspect.signature(func).parameters
    except (TypeError, ValueError):
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute prompt-driven orchestration graph for VS/VS Code tasks.",
    )
    parser.add_argument("--prompt", type=str, default=None, help="Inline orchestration prompt string.")
    parser.add_argument(
        "--prompt-file",
        type=str,
        default=None,
        help="Path to a file containing the orchestration prompt.",
    )
    parser.add_argument("--goal", type=str, default=None, help="Fallback goal if prompt has no goal field.")
    parser.add_argument("--graph-id", type=str, default="vscode_prompt_graph")
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument("--max-concurrency", type=int, default=None)
    parser.add_argument(
        "--context-json",
        type=str,
        default="{}",
        help="JSON object merged into runtime context.",
    )
    parser.add_argument("--include-graph", action="store_true", help="Include graph topology in output.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    return parser.parse_args()


def resolve_prompt(prompt: str | None, prompt_file: str | None) -> str:
    if bool(prompt) == bool(prompt_file):
        raise ValueError("Exactly one of --prompt or --prompt-file is required.")
    if prompt_file is not None:
        file_path = Path(prompt_file)
        return file_path.read_text(encoding="utf-8").strip()
    assert prompt is not None
    return prompt.strip()


def parse_context(raw: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("--context-json must be a JSON object.")
    return payload


async def run_orchestration(args: argparse.Namespace) -> dict[str, Any]:
    prompt = resolve_prompt(args.prompt, args.prompt_file)
    context = parse_context(args.context_json)

    create_kwargs: dict[str, Any] = {
        "goal": args.goal,
        "graph_id": args.graph_id,
    }
    if args.max_concurrency is not None and _supports_kwarg(create_graph_from_prompt, "max_concurrency"):
        create_kwargs["max_concurrency"] = args.max_concurrency
    graph = create_graph_from_prompt(prompt, **create_kwargs)
    for key, value in context.items():
        graph.context.set(key, value)

    execute_kwargs: dict[str, Any] = {}
    if args.max_steps is not None:
        execute_kwargs["max_steps"] = args.max_steps
    if args.max_concurrency is not None and _supports_kwarg(graph.execute, "max_concurrency"):
        execute_kwargs["max_concurrency"] = args.max_concurrency
    results = await graph.execute(**execute_kwargs)
    output: dict[str, Any] = {
        "graph_id": graph.graph_id,
        "goal": graph.context.get("goal"),
        "max_steps": graph.context.get("orchestration_max_steps"),
        "max_concurrency": graph.context.get("orchestration_max_concurrency", args.max_concurrency or 1),
        "results": results,
    }
    if args.include_graph:
        output["graph"] = graph.to_dict()
    return output


def main() -> int:
    args = parse_args()
    try:
        payload = asyncio.run(run_orchestration(args))
    except Exception as exc:
        error_payload = {"status": "failed", "error": str(exc)}
        print(json.dumps(error_payload, ensure_ascii=False))
        return 1

    if args.pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
