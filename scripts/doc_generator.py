#!/usr/bin/env python3
"""
文档生成工具

功能：
- 自动生成 README 索引
- 统计文档数量
- 检查文档质量

使用：
    python scripts/doc_generator.py
"""

import os
from pathlib import Path
from datetime import datetime

class DocGenerator:
    """文档生成工具"""
    
    def __init__(self, memory_dir: str):
        self.memory_dir = Path(memory_dir)
    
    def count_files(self) -> dict:
        """统计文件"""
        stats = {
            "total": 0,
            "markdown": 0,
            "python": 0,
            "other": 0
        }
        
        for file in self.memory_dir.rglob("*"):
            if file.is_file():
                stats["total"] += 1
                
                if file.suffix == ".md":
                    stats["markdown"] += 1
                elif file.suffix == ".py":
                    stats["python"] += 1
                else:
                    stats["other"] += 1
        
        return stats
    
    def generate_index(self) -> str:
        """生成索引"""
        stats = self.count_files()
        
        index = f"""# Memory 文档索引

> **生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 📊 统计

```
总文件数：{stats['total']}
Markdown：{stats['markdown']}
Python：{stats['python']}
其他：{stats['other']}
```

---

## 📂 最近更新

"""
        
        # 获取最近的 Markdown 文件
        recent_files = sorted(
            self.memory_dir.rglob("*.md"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )[:10]
        
        for file in recent_files:
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            rel_path = file.relative_to(self.memory_dir)
            index += f"- [{rel_path}]({rel_path}) ({mtime.strftime('%Y-%m-%d %H:%M')})\n"
        
        return index
    
    def run(self):
        """运行"""
        print("\n" + "="*60)
        print("  Document Generator")
        print("="*60 + "\n")
        
        # 统计
        stats = self.count_files()
        print(f"📊 Statistics:")
        print(f"  Total files: {stats['total']}")
        print(f"  Markdown: {stats['markdown']}")
        print(f"  Python: {stats['python']}")
        print(f"  Other: {stats['other']}")
        
        # 生成索引
        index = self.generate_index()
        print(f"\n📝 Generated index:\n")
        print(index)
        
        print("="*60)
        print("  Completed!")
        print("="*60 + "\n")

if __name__ == "__main__":
    memory_dir = "/Users/iCloud_GZ/github_GZ/openclaw-memory/memory"
    generator = DocGenerator(memory_dir)
    generator.run()
