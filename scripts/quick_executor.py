#!/usr/bin/env python3
"""
快速任务执行器

功能：
- 快速执行常用任务
- 批量操作
- 生成日志

使用：
    python scripts/quick_executor.py
"""

import subprocess
from pathlib import Path
from datetime import datetime

class QuickExecutor:
    """快速任务执行器"""
    
    def __init__(self, repo_dir: str):
        self.repo_dir = Path(repo_dir)
        self.log_file = self.repo_dir / "memory" / "executor.log"
    
    def execute(self, task_name: str, command: str) -> dict:
        """执行任务"""
        print(f"\n🔄 Executing: {task_name}")
        
        start_time = datetime.now()
        
        try:
            result = subprocess.run(
                command,
                cwd=self.repo_dir,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                "name": task_name,
                "success": result.returncode == 0,
                "output": result.stdout[:200] if result.stdout else "",
                "error": result.stderr[:100] if result.stderr else "",
                "duration": f"{duration:.2f}s",
                "timestamp": start_time.isoformat()
            }
        
        except Exception as e:
            return {
                "name": task_name,
                "success": False,
                "output": "",
                "error": str(e),
                "duration": "0s",
                "timestamp": start_time.isoformat()
            }
    
    def run_batch(self, tasks: list):
        """批量执行"""
        print("\n" + "="*60)
        print("  Quick Executor")
        print("="*60)
        
        results = []
        
        for task in tasks:
            result = self.execute(task['name'], task['command'])
            results.append(result)
            
            # 显示结果
            if result['success']:
                print(f"  ✅ {result['name']} ({result['duration']})")
            else:
                print(f"  ❌ {result['name']} - {result['error']}")
        
        print("="*60 + "\n")
        
        return results
    
    def run(self):
        """运行"""
        tasks = [
            {
                "name": "Git Status",
                "command": "git status --short"
            },
            {
                "name": "File Count",
                "command": "find . -name '*.md' | wc -l"
            },
            {
                "name": "Disk Usage",
                "command": "du -sh ."
            }
        ]
        
        results = self.run_batch(tasks)
        
        # 统计
        success = sum(1 for r in results if r['success'])
        total = len(results)
        
        print(f"📊 Results: {success}/{total} successful\n")

if __name__ == "__main__":
    repo_dir = "/Users/iCloud_GZ/github_GZ/openclaw-memory"
    executor = QuickExecutor(repo_dir)
    executor.run()
