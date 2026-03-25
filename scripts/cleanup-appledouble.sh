#!/bin/bash
# AppleDouble 文件清理脚本
# 基于仓库根目录，不写死路径

set -e

# 获取仓库根目录（基于脚本位置）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🧹 清理 AppleDouble 文件..."
echo "仓库根目录: $REPO_ROOT"

# 统计数量
COUNT=$(find "$REPO_ROOT" -name "._*" -type f | wc -l | tr -d ' ')

if [ "$COUNT" -eq 0 ]; then
    echo "✅ 未发现 AppleDouble 文件"
    exit 0
fi

echo "发现 $COUNT 个 AppleDouble 文件，正在清理..."

# 删除文件
find "$REPO_ROOT" -name "._*" -type f -delete

echo "✅ 已清理 $COUNT 个 AppleDouble 文件"
