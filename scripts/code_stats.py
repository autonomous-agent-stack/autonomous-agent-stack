#!/usr/bin/env python3
"""
代码统计工具

功能：
- 统计代码行数
- 分析代码质量
- 生成报告

使用：
    python scripts/code_stats.py
"""

import os
from pathlib import Path
from collections import defaultdict
from datetime import datetime

class CodeStats:
    """代码统计工具"""
    
    def __init__(self, memory_dir: str):
        self.memory_dir = Path(memory_dir)
    
    def analyze_files(self) -> dict:
        """分析文件"""
        stats = defaultdict(lambda: {
            "files": 0,
            "lines": 0,
            "size": 0
        })
        
        extensions = {
            ".md": "Markdown",
            ".py": "Python",
            ".js": "JavaScript",
            ".html": "HTML",
            ".css": "CSS",
            ".json": "JSON",
            ".sh": "Shell"
        }
        
        for file in self.memory_dir.rglob("*"):
            if file.is_file():
                ext = file.suffix
                if ext in extensions:
                    lang = extensions[ext]
                    stats[lang]["files"] += 1
                    
                    # 统计行数
                    try:
                        with open(file, 'r', encoding='utf-8') as f:
                            lines = len(f.readlines())
                            stats[lang]["lines"] += lines
                    except:
                        pass
                    
                    # 统计大小
                    stats[lang]["size"] += file.stat().st_size
        
        return dict(stats)
    
    def generate_report(self) -> str:
        """生成报告"""
        stats = self.analyze_files()
        
        report = f"""# 代码统计报告

> **生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 📊 统计概览

| 语言 | 文件数 | 代码行数 | 大小 |
|------|--------|----------|------|
"""
        
        total_files = 0
        total_lines = 0
        total_size = 0
        
        for lang, data in sorted(stats.items(), key=lambda x: x[1]["lines"], reverse=True):
            files = data["files"]
            lines = data["lines"]
            size_kb = data["size"] / 1024
            
            report += f"| {lang} | {files} | {lines} | {size_kb:.2f} KB |\n"
            
            total_files += files
            total_lines += lines
            total_size += data["size"]
        
        total_size_mb = total_size / (1024 * 1024)
        
        report += f"| **总计** | **{total_files}** | **{total_lines}** | **{total_size_mb:.2f} MB** |\n"
        
        return report
    
    def run(self):
        """运行"""
        print("\n" + "="*60)
        print("  Code Statistics Tool")
        print("="*60 + "\n")
        
        # 分析
        stats = self.analyze_files()
        
        print("📊 Statistics:\n")
        
        total_files = 0
        total_lines = 0
        total_size = 0
        
        for lang, data in sorted(stats.items(), key=lambda x: x[1]["lines"], reverse=True):
            files = data["files"]
            lines = data["lines"]
            size_kb = data["size"] / 1024
            
            print(f"  {lang}:")
            print(f"    Files: {files}")
            print(f"    Lines: {lines}")
            print(f"    Size: {size_kb:.2f} KB")
            print()
            
            total_files += files
            total_lines += lines
            total_size += data["size"]
        
        total_size_mb = total_size / (1024 * 1024)
        
        print("="*60)
        print(f"  Total: {total_files} files, {total_lines} lines, {total_size_mb:.2f} MB")
        print("="*60 + "\n")

if __name__ == "__main__":
    memory_dir = "/Users/iCloud_GZ/github_GZ/openclaw-memory/memory"
    stats = CodeStats(memory_dir)
    stats.run()
