#!/bin/bash
# 优化启动脚本 - AI_LAB 版本

set -e

echo "🚀 启动优化版 API 服务..."

# 激活虚拟环境
source .venv/bin/activate

# 检查依赖
pip check || { echo "❌ 依赖冲突"; exit 1; }

# 启动服务（2 workers，优化配置）
uvicorn src.autoresearch.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \
    --log-level info \
    --access-log \
    --forwarded-allow-ips '*' \
    --proxy-headers

echo "✅ 服务已启动"
