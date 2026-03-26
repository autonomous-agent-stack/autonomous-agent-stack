from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_prompt_hygiene.py"


def run_hygiene(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_hygiene_check_reports_findings_and_writes_outputs(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "clean.py").write_text("def clean():\n    return 42\n", encoding="utf-8")
    (src / "noisy.py").write_text(
        "# TODO: 实现真实的 API 调用\n"
        "# TODO: 实现真实的 API 调用\n"
        "# TODO: 实现真实的 API 调用\n"
        "def build():\n"
        '    """工厂化流程说明 placeholder"""\n'
        '    return "这里有一个工厂化提示"\n',
        encoding="utf-8",
    )

    output_dir = tmp_path / "audit"
    result = run_hygiene("--root", str(src), "--output-dir", str(output_dir))

    assert result.returncode == 0
    assert "[hygiene] status=WARN" in result.stdout

    text_report = (output_dir / "report.txt").read_text(encoding="utf-8")
    json_report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))

    assert "# Prompt Hygiene Report" in text_report
    assert json_report["files_scanned"] == 2
    assert json_report["score"] < 100
    assert any(finding["category"] == "forbidden_term" for finding in json_report["findings"])
    assert any(finding["category"] == "placeholder_token" for finding in json_report["findings"])
    assert json_report["repeated_phrases"]
    assert json_report["repeated_phrases"][0]["count"] == 3


def test_hygiene_check_fail_on_findings_when_strict(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "noisy.py").write_text("# TODO: repeated\n# TODO: repeated\n# TODO: repeated\n", encoding="utf-8")

    output_dir = tmp_path / "audit"
    result = run_hygiene(
        "--root",
        str(src),
        "--output-dir",
        str(output_dir),
        "--fail-on-findings",
    )

    assert result.returncode == 1
    assert (output_dir / "report.txt").exists()
    assert (output_dir / "report.json").exists()


def test_hygiene_check_passes_on_clean_tree(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "clean.py").write_text("def answer():\n    return 42\n", encoding="utf-8")

    output_dir = tmp_path / "audit"
    result = run_hygiene("--root", str(src), "--output-dir", str(output_dir))

    assert result.returncode == 0
    json_report = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
    assert json_report["findings"] == []
    assert json_report["repeated_phrases"] == []
    assert json_report["score"] == 100
