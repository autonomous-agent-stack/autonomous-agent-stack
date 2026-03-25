#!/usr/bin/env python3
"""
启动前检查脚本
扫描并清理 AppleDouble 文件
"""

import sys
from pathlib import Path

def check_and_cleanup_appledouble():
    """扫描并清理 AppleDouble 文件"""
    # 获取仓库根目录（基于脚本位置）
    repo_root = Path(__file__).parent.parent
    
    print("🔍 扫描 AppleDouble 文件...")
    print(f"仓库根目录: {repo_root}")
    
    # 扫描 ._ 开头的文件
    appledouble_files = list(repo_root.rglob("._*"))
    
    if not appledouble_files:
        print("✅ 未发现 AppleDouble 文件")
        return 0
    
    print(f"⚠️  发现 {len(appledouble_files)} 个 AppleDouble 文件:")
    
    # 删除文件
    deleted = 0
    for f in appledouble_files:
        try:
            f.unlink()
            print(f"  ✓ {f.relative_to(repo_root)}")
            deleted += 1
        except Exception as e:
            print(f"  ✗ {f.relative_to(repo_root)}: {e}")
    
    print(f"✅ 已清理 {deleted}/{len(appledouble_files)} 个 AppleDouble 文件")
    return deleted

if __name__ == "__main__":
    deleted = check_and_cleanup_appledouble()
    sys.exit(0 if deleted >= 0 else 1)
