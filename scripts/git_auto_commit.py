#!/usr/bin/env python3
"""
Git 自动提交工具

功能：
- 检测文件变化
- 自动生成提交信息
- 批量提交

使用：
    python scripts/git_auto_commit.py
"""

import subprocess
from pathlib import Path
from datetime import datetime

class GitAutoCommit:
    """Git 自动提交工具"""
    
    def __init__(self, repo_dir: str):
        self.repo_dir = Path(repo_dir)
    
    def check_changes(self) -> dict:
        """检查变化"""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.repo_dir,
            capture_output=True,
            text=True
        )
        
        changes = {
            "added": [],
            "modified": [],
            "deleted": []
        }
        
        for line in result.stdout.splitlines():
            status = line[:2]
            file = line[3:]
            
            if "??" in status:
                changes["added"].append(file)
            elif "M" in status:
                changes["modified"].append(file)
            elif "D" in status:
                changes["deleted"].append(file)
        
        return changes
    
    def generate_message(self, changes: dict) -> str:
        """生成提交信息"""
        total = sum(len(v) for v in changes.values())
        
        message = f"🔄 自动提交 - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        message += f"变化文件：{total} 个\n"
        
        if changes["added"]:
            message += f"- 新增：{len(changes['added'])} 个\n"
        
        if changes["modified"]:
            message += f"- 修改：{len(changes['modified'])} 个\n"
        
        if changes["deleted"]:
            message += f"- 删除：{len(changes['deleted'])} 个\n"
        
        return message
    
    def commit(self, message: str):
        """提交"""
        # 添加所有文件
        subprocess.run(
            ["git", "add", "-A"],
            cwd=self.repo_dir,
            check=True
        )
        
        # 提交
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=self.repo_dir,
            check=True
        )
        
        print(f"✅ Committed: {message}")
    
    def push(self):
        """推送"""
        subprocess.run(
            ["git", "push"],
            cwd=self.repo_dir,
            check=True
        )
        
        print("✅ Pushed to remote")
    
    def run(self):
        """运行"""
        print("\n" + "="*60)
        print("  Git Auto Commit Tool")
        print("="*60 + "\n")
        
        # 检查变化
        changes = self.check_changes()
        
        total = sum(len(v) for v in changes.values())
        
        if total == 0:
            print("✅ No changes to commit")
            return
        
        print(f"📋 Found {total} changes:")
        print(f"  Added: {len(changes['added'])}")
        print(f"  Modified: {len(changes['modified'])}")
        print(f"  Deleted: {len(changes['deleted'])}")
        
        # 生成提交信息
        message = self.generate_message(changes)
        
        # 提交
        self.commit(message)
        
        # 推送
        self.push()
        
        print("\n" + "="*60)
        print("  Completed!")
        print("="*60 + "\n")

if __name__ == "__main__":
    repo_dir = "/Users/iCloud_GZ/github_GZ/openclaw-memory"
    auto_commit = GitAutoCommit(repo_dir)
    auto_commit.run()
