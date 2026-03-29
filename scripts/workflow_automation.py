#!/usr/bin/env python3
"""
自动化工作流工具

功能：
- 定时执行任务
- 生成工作报告
- 监控项目状态

使用：
    python scripts/workflow_automation.py
"""

import os
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import json

class WorkflowAutomation:
    """自动化工作流工具"""
    
    def __init__(self, repo_dir: str):
        self.repo_dir = Path(repo_dir)
        self.config_file = self.repo_dir / ".workflow_config.json"
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """加载配置"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        
        # 默认配置
        default_config = {
            "tasks": [
                {
                    "name": "Git Status Check",
                    "command": "git status --porcelain",
                    "interval_minutes": 60
                },
                {
                    "name": "File Count",
                    "command": "find . -type f | wc -l",
                    "interval_minutes": 120
                }
            ],
            "last_run": {}
        }
        
        # 保存默认配置
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        return default_config
    
    def run_task(self, task: dict) -> dict:
        """执行任务"""
        print(f"\n🔄 Running: {task['name']}")
        
        try:
            result = subprocess.run(
                task['command'],
                cwd=self.repo_dir,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "name": task['name'],
                "success": result.returncode == 0,
                "output": result.stdout[:500] if result.stdout else "",
                "error": result.stderr[:200] if result.stderr else "",
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            return {
                "name": task['name'],
                "success": False,
                "output": "",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def run_all_tasks(self):
        """运行所有任务"""
        print("\n" + "="*60)
        print("  Workflow Automation")
        print("="*60)
        
        results = []
        
        for task in self.config['tasks']:
            result = self.run_task(task)
            results.append(result)
            
            # 显示结果
            if result['success']:
                print(f"  ✅ {result['name']}")
                if result['output']:
                    print(f"     Output: {result['output'][:100]}")
            else:
                print(f"  ❌ {result['name']}")
                if result['error']:
                    print(f"     Error: {result['error']}")
        
        print("="*60 + "\n")
        
        return results
    
    def generate_report(self, results: list) -> str:
        """生成报告"""
        report = f"""# 工作流自动化报告

> **生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 📊 执行结果

| 任务 | 状态 | 时间 |
|------|------|------|
"""
        
        for result in results:
            status = "✅ 成功" if result['success'] else "❌ 失败"
            timestamp = datetime.fromisoformat(result['timestamp']).strftime("%H:%M:%S")
            report += f"| {result['name']} | {status} | {timestamp} |\n"
        
        return report
    
    def run(self):
        """运行"""
        results = self.run_all_tasks()
        report = self.generate_report(results)
        
        # 保存报告
        report_file = self.repo_dir / f"memory/workflow-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"📄 Report saved: {report_file}")

if __name__ == "__main__":
    repo_dir = "/Users/iCloud_GZ/github_GZ/openclaw-memory"
    automation = WorkflowAutomation(repo_dir)
    automation.run()
