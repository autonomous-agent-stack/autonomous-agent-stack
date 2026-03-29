#!/usr/bin/env python3
"""
GitHub 仓库监控工具

功能：
- 监控仓库状态
- 检查 Stars/Forks
- 生成报告

使用：
    python scripts/github_monitor.py
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime

class GitHubMonitor:
    """GitHub 仓库监控"""
    
    def __init__(self, repo_dir: str):
        self.repo_dir = Path(repo_dir)
    
    def get_repo_info(self, repo: str) -> dict:
        """获取仓库信息"""
        try:
            result = subprocess.run(
                ["gh", "repo", "view", repo, "--json", "name,stargazersCount,forksCount,updatedAt,description"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {"error": result.stderr}
        
        except Exception as e:
            return {"error": str(e)}
    
    def check_multiple_repos(self, repos: list) -> list:
        """检查多个仓库"""
        print(f"\n🔍 Checking {len(repos)} repositories...\n")
        
        results = []
        
        for repo in repos:
            print(f"  Checking: {repo}")
            info = self.get_repo_info(repo)
            
            results.append({
                "repo": repo,
                "info": info,
                "timestamp": datetime.now().isoformat()
            })
        
        return results
    
    def generate_report(self, results: list) -> str:
        """生成报告"""
        report = f"""# GitHub 仓库监控报告

> **生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 📊 仓库状态

| 仓库 | Stars | Forks | 最后更新 |
|------|-------|-------|----------|
"""
        
        for result in results:
            info = result['info']
            
            if 'error' in info:
                report += f"| {result['repo']} | ❌ 错误 | - | - |\n"
            else:
                stars = info.get('stargazersCount', 0)
                forks = info.get('forksCount', 0)
                updated = info.get('updatedAt', 'Unknown')[:10]
                
                report += f"| {result['repo']} | {stars} | {forks} | {updated} |\n"
        
        return report
    
    def run(self):
        """运行"""
        print("\n" + "="*60)
        print("  GitHub Repository Monitor")
        print("="*60 + "\n")
        
        # 监控的仓库列表
        repos = [
            "srxly888-creator/openclaw-memory",
            "srxly888-creator/autonomous-agent-stack",
            "srxly888-creator/openhands-cookbook",
            "srxly888-creator/ai-tools-compendium",
            "EverMind-AI/MSA"
        ]
        
        results = self.check_multiple_repos(repos)
        report = self.generate_report(results)
        
        # 保存报告
        report_file = self.repo_dir / f"memory/github-monitor-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        print("\n" + "="*60)
        print(f"📄 Report saved: {report_file}")
        print("="*60 + "\n")

if __name__ == "__main__":
    repo_dir = "/Users/iCloud_GZ/github_GZ/openclaw-memory"
    monitor = GitHubMonitor(repo_dir)
    monitor.run()
