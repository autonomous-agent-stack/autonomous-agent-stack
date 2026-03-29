#!/usr/bin/env python3
"""
Markdown 检查工具

功能：
- 检查 Markdown 语法
- 检查链接有效性
- 检查标题层级

使用：
    python scripts/md_checker.py
"""

import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

class MarkdownChecker:
    """Markdown 检查工具"""
    
    def __init__(self, memory_dir: str):
        self.memory_dir = Path(memory_dir)
        self.issues = defaultdict(list)
    
    def check_headings(self, file: Path, content: str):
        """检查标题层级"""
        lines = content.splitlines()
        prev_level = 0
        
        for i, line in enumerate(lines, 1):
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                
                # 检查层级跳跃
                if level > prev_level + 1 and prev_level > 0:
                    self.issues[file].append(
                        f"Line {i}: Heading level jumped from {prev_level} to {level}"
                    )
                
                prev_level = level
    
    def check_links(self, file: Path, content: str):
        """检查链接"""
        # 检查空链接
        empty_links = re.findall(r'\[\s*\]\(', content)
        if empty_links:
            self.issues[file].append(f"Found {len(empty_links)} empty links")
        
        # 检查相对链接
        relative_links = re.findall(r'\[.*?\]\((?!http)(.*?)\)', content)
        for link in relative_links:
            if not link.startswith('#'):  # 忽略锚点
                target_file = file.parent / link
                if not target_file.exists():
                    self.issues[file].append(f"Broken link: {link}")
    
    def check_lists(self, file: Path, content: str):
        """检查列表"""
        lines = content.splitlines()
        prev_was_list = False
        
        for i, line in enumerate(lines, 1):
            is_list = line.strip().startswith(('-', '*', '+', '1.', '2.', '3.'))
            
            # 检查列表项之间是否有空行
            if is_list and prev_was_list and line.strip() == '':
                self.issues[file].append(f"Line {i}: Empty line in list")
            
            prev_was_list = is_list
    
    def run(self):
        """运行检查"""
        print("\n" + "="*60)
        print("  Markdown Checker")
        print("="*60 + "\n")
        
        md_files = list(self.memory_dir.rglob("*.md"))
        print(f"📋 Checking {len(md_files)} Markdown files...\n")
        
        for file in md_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.check_headings(file, content)
                self.check_links(file, content)
                self.check_lists(file, content)
            
            except Exception as e:
                self.issues[file].append(f"Error reading file: {e}")
        
        # 输出结果
        if self.issues:
            print(f"❌ Found issues in {len(self.issues)} files:\n")
            
            for file, issues in sorted(self.issues.items()):
                rel_path = file.relative_to(self.memory_dir)
                print(f"📄 {rel_path}:")
                for issue in issues[:5]:  # 只显示前5个问题
                    print(f"  - {issue}")
                print()
        else:
            print("✅ No issues found!")
        
        print("="*60)
        print(f"  Checked {len(md_files)} files, found {sum(len(v) for v in self.issues.values())} issues")
        print("="*60 + "\n")

if __name__ == "__main__":
    memory_dir = "/Users/iCloud_GZ/github_GZ/openclaw-memory/memory"
    checker = MarkdownChecker(memory_dir)
    checker.run()
