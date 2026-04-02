from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def _section(markdown: str, title: str) -> str:
    pattern = re.compile(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)
    match = pattern.search(markdown)
    assert match is not None, f"missing section: {title}"
    return match.group(1)


def test_readme_linux_bringup_points_to_env_linux_and_guide() -> None:
    readme = _read("README.md")
    section = _section(readme, "Linux 主运行面")

    assert "Linux = 主助理 / 主开发执行面 / 主值班面" in section
    assert "Mac = 备用管家 / 备用执行面 / 控制台" in section
    assert "同仓库、同 manifest、不同 runtime 配置" in section
    assert "source .env.linux" in section
    assert "make doctor-linux" in section
    assert "make start" in section
    assert "[Linux Primary Runtime Guide](./docs/linux-remote-worker.md)" in section
    assert "[`.env.linux`](./.env.linux)" in section
    assert "/Volumes/" not in section
    assert "/Users/" not in section


def test_linux_guide_locks_linux_primary_and_mac_backup_contract() -> None:
    guide = _read("docs/linux-remote-worker.md")
    preface = guide.split("## 为什么 Linux 先走 `host`", 1)[0]

    assert guide.startswith("# Linux Primary Runtime Guide")
    assert "Linux = 主助理 / 主开发执行面 / 主值班面" in preface
    assert "Mac = 备用管家 / 备用执行面 / 控制台" in preface
    assert "同仓库、同 manifest、不同 runtime 配置" in preface
    assert "平时 Linux 主跑" in preface
    assert "Mac 只接低到中风险、短时、可人工复核任务" in preface
    assert "不允许分叉成两套实现" in preface
    assert "Mac: 控制面" not in preface


def test_linux_env_files_default_to_host_runtime_and_repo_relative_paths() -> None:
    env_example = _read(".env.example")
    env_linux = _read(".env.linux")

    for content in (env_example, env_linux):
        assert "OPENHANDS_RUNTIME=host" in content
        assert "AUTORESEARCH_RUNTIME_HOST=linux" in content
        assert "AUTORESEARCH_EXECUTION_ROLE=primary" in content
        assert "AUTORESEARCH_TASK_RISK_PROFILE=full" in content
        assert "artifacts/upstream-watch/workspace" in content
        assert "/Volumes/" not in content
        assert "/Users/" not in content
        assert "colima" not in content.lower()
