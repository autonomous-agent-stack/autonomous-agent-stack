from __future__ import annotations

import argparse
import json
from pathlib import Path

from autoresearch.shared.remote_run_contract import RemoteRunSummary, RemoteTaskSpec


def export_schemas(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = {
        "task_run.schema.json": RemoteTaskSpec.model_json_schema(),
        "run_summary.schema.json": RemoteRunSummary.model_json_schema(),
    }
    written: list[Path] = []
    for name, payload in targets.items():
        path = output_dir / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Export remote-run JSON schemas.")
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parents[1] / "schemas"),
        help="directory to receive exported schema files",
    )
    args = parser.parse_args()
    export_schemas(Path(args.output_dir).expanduser().resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
