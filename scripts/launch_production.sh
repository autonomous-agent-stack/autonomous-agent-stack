#!/bin/bash
# Production Launch Script for Autonomous Agent Stack
# Version: v1.2.0-autonomous-genesis

PROJECT_ROOT="/Volumes/PS1008/Github/autonomous-agent-stack"
PORT=8001

echo "🌐 (System) 启动通用版自主智能体底座..."

# 1. 端口冲突检查
PID=$(lsof -t -i:$PORT)
if [ -n "$PID" ]; then
    echo "⚠️ [Defense] 发现端口 $PORT 被占用 (PID: $PID)，正在强制释放..."
    kill -9 $PID
    sleep 1
fi

# 2. 环境物理清理
echo "🧹 [Defense] 执行环境物理清理..."
find "$PROJECT_ROOT" -name "._*" -type f -delete 2>/dev/null
find "$PROJECT_ROOT" -name ".DS_Store" -type f -delete 2>/dev/null
echo "✅ [Defense] 环境清理完成"

# 3. 切换到项目目录
cd "$PROJECT_ROOT"

# 4. 启动 Uvicorn 生产环境
echo "🚀 [Launch] 启动 Uvicorn 生产环境..."
uvicorn src.autoresearch.api.main:app \
    --host 127.0.0.1 \
    --port $PORT \
    --log-level info > /tmp/autoresearch_production.log 2>&1 &

sleep 2

# 5. 健康检查验证
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$PORT/health 2>/dev/null)
if [ "$STATUS" -eq 200 ]; then
    echo "🎉 [Success] 底座已就绪。监控面板: http://127.0.0.1:$PORT/panel"
else
    echo "❌ [Error] 服务启动异常，请检查日志: tail -f /tmp/autoresearch_production.log"
fi
