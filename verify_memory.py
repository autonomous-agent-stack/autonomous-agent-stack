#!/usr/bin/env python3
"""
验证 OpenClaw 记忆迁移是否成功
运行: python verify_memory.py
"""

import os
import sys
from pathlib import Path

def verify_memory_files():
    """验证记忆文件是否存在"""
    print("=== 验证 OpenClaw 记忆迁移 ===\n")
    
    required_files = [
        "MEMORY.md",
        "AGENTS.md",
        "SOUL.md",
        "USER.md",
        "HEARTBEAT.md"
    ]
    
    missing_files = []
    
    for file in required_files:
        if os.path.exists(file):
            size = os.path.getsize(file)
            lines = len(open(file, 'r', encoding='utf-8').readlines())
            print(f"✅ {file:20} {lines:4} 行, {size:6} 字节")
        else:
            print(f"❌ {file:20} 不存在")
            missing_files.append(file)
    
    print("\n=== 检查 memory 目录 ===\n")
    
    memory_dir = Path("memory")
    if memory_dir.exists():
        md_files = list(memory_dir.glob("**/*.md"))
        print(f"✅ memory/ 目录存在")
        print(f"✅ 共 {len(md_files)} 个 Markdown 文件")
        
        # 统计子目录
        subdirs = [d for d in memory_dir.iterdir() if d.is_dir()]
        print(f"✅ {len(subdirs)} 个子目录")
        
        # 显示前 10 个子目录
        print("\n子目录列表:")
        for i, subdir in enumerate(subdirs[:10], 1):
            file_count = len(list(subdir.glob("*.md")))
            print(f"  {i:2}. {subdir.name:30} ({file_count} 文件)")
        
        if len(subdirs) > 10:
            print(f"  ... 还有 {len(subdirs) - 10} 个子目录")
    else:
        print(f"❌ memory/ 目录不存在")
        missing_files.append("memory/")
    
    print("\n=== 总结 ===\n")
    
    if missing_files:
        print(f"❌ 迁移不完整，缺少 {len(missing_files)} 个文件/目录:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    else:
        print("✅ 迁移完整！所有记忆文件都已就绪")
        print("\n🚀 下一步:")
        print("   1. 配置 .env 文件（添加 API Keys）")
        print("   2. 运行: bash start_with_memory.sh")
        print("   3. 或手动启动: uvicorn src.api.main:app --reload --port 8000")
        return True

if __name__ == "__main__":
    success = verify_memory_files()
    sys.exit(0 if success else 1)
