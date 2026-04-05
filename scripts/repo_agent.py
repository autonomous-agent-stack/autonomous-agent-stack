#!/usr/bin/env python3
"""
最小 repo-agent - 导出并提交已完成任务

功能：
    1. 扫描 SQLite 中 completed 且 archive_status != exported 的任务
    2. 调用 archiver 导出
    3. 更新 archive/index.json 和相关 README
    4. 写回：archive_status=exported, archive_path, archived_at
    5. 可选 commit / push

约束：
    - 不改 media-agent 状态机
    - 不实现复杂的 worker/claim 机制
    - 不碰 Telegram 主链
    - 不扩 day/night/scheduler
    - 输出能被后续 repo-agent 复用

Usage:
    # 导出所有待归档任务
    python3 scripts/repo_agent.py export

    # 导出并提交
    python3 scripts/repo_agent.py export --commit

    # 导出、提交并推送
    python3 scripts/repo_agent.py export --commit --push

    # 只处理指定 job
    python3 scripts/repo_agent.py export --job-id 42

    # 查看状态
    python3 scripts/repo_agent.py status
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))

from lib import MediaJobStore, MediaArchiver


class RepoAgent:
    """最小 repo-agent：导出并提交已完成任务"""

    def __init__(
        self,
        store: MediaJobStore = None,
        archiver: MediaArchiver = None,
    ):
        self.store = store or MediaJobStore()
        self.archiver = archiver or MediaArchiver(store=self.store)

    def export(self, job_id: int = None) -> list[int]:
        """
        导出已完成任务

        Args:
            job_id: 指定任务 ID（可选）

        Returns:
            导出的 job ID 列表
        """
        if job_id:
            job = self.store.get(job_id)
            if not job:
                print(f"[repo] Job #{job_id} not found")
                return []
            if job.status.value != "completed":
                print(f"[repo] Job #{job_id} is not completed (status={job.status.value})")
                return []
            jobs = [job]
        else:
            jobs = self.store.get_completed_for_archive(limit=50)

        if not jobs:
            print("[repo] No completed jobs to export")
            return []

        print(f"[repo] Found {len(jobs)} job(s) to export")

        exported = []
        for job in jobs:
            metadata = json.loads(job.metadata_json) if job.metadata_json else {}
            files = metadata.get("files", [])

            try:
                archive_path = self.archiver.export_job(job, files=files)
                self.store.mark_exported(job.id, str(archive_path))
                exported.append(job.id)
                print(f"[repo] Exported job #{job.id} -> {archive_path.relative_to(REPO_ROOT)}")
            except Exception as e:
                print(f"[repo] Failed to export job #{job.id}: {e}")

        if exported:
            self.archiver.update_index()
            print(f"[repo] Updated archive/index.json ({len(exported)} jobs)")

        return exported

    def commit(self, push: bool = False) -> bool:
        """
        提交归档文件

        Args:
            push: 是否推送到远程

        Returns:
            是否有变更被提交
        """
        result = subprocess.run(
            ["git", "status", "--porcelain", "archive/"],
            cwd=REPO_ROOT,
            capture_output=True,
        )

        if not result.stdout.strip():
            print("[repo] No changes to commit")
            return False

        subprocess.run(
            ["git", "add", "archive/"],
            cwd=REPO_ROOT,
            check=True,
        )

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        msg = f"chore(archive): export completed media jobs - {now}"

        subprocess.run(
            ["git", "commit", "-m", msg],
            cwd=REPO_ROOT,
            check=True,
        )

        print(f"[repo] Committed changes")

        if push:
            subprocess.run(
                ["git", "push", "origin", "HEAD"],
                cwd=REPO_ROOT,
                check=True,
            )
            print(f"[repo] Pushed to remote")

        return True

    def status(self):
        """显示归档状态"""
        stats = self.store.stats()
        print("[repo] Queue statistics:")
        for status, count in sorted(stats.items()):
            print(f"  {status}: {count}")

        archive_dir = REPO_ROOT / "archive"
        if archive_dir.exists():
            index_path = archive_dir / "index.json"
            if index_path.exists():
                index = json.loads(index_path.read_text())
                print(f"\n[repo] Archive: {index.get('total', 0)} entries")
                platforms = index.get("platforms", [])
                if platforms:
                    print(f"  Platforms: {', '.join(platforms)}")


def cmd_export(args):
    """导出命令"""
    agent = RepoAgent()
    exported = agent.export(job_id=args.job_id)

    if exported and args.commit:
        agent.commit(push=args.push)

    return 0


def cmd_status(args):
    """状态命令"""
    agent = RepoAgent()
    agent.status()
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Minimal repo-agent for media job archiving",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/repo_agent.py export
  python3 scripts/repo_agent.py export --commit
  python3 scripts/repo_agent.py export --commit --push
  python3 scripts/repo_agent.py export --job-id 42
  python3 scripts/repo_agent.py status
""",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # export
    p_export = subparsers.add_parser("export", help="Export completed jobs to archive")
    p_export.add_argument("--job-id", type=int, help="Specific job ID to export")
    p_export.add_argument("--commit", action="store_true", help="Commit changes after export")
    p_export.add_argument("--push", action="store_true", help="Push to remote (requires --commit)")
    p_export.set_defaults(func=cmd_export)

    # status
    p_status = subparsers.add_parser("status", help="Show archive status")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
