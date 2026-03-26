#!/bin/bash

# ========================================================================
# Autonomous Agent Stack - Universal Production Launch (v2.0)
# 架构：零容器依赖 / SQLite 状态机 / 4x 异步 Workers
# ========================================================================

PROJECT_ROOT="/Volumes/AI_LAB/Github/autonomous-agent-stack"
PORT=8001
DB_DIR="$PROJECT_ROOT/data"

echo "🌐 (System) 正在执行 v2.0 生产环境点火序列..."

# 1. 物理目录预检
if [ ! -d "$DB_DIR" ]; then
    mkdir -p "$DB_DIR"
    echo "✅ [Storage] 已创建持久化数据目录: $DB_DIR"
fi

# 2. 环境变量加载与校验
cd "$PROJECT_ROOT" || exit
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✅ [Config] 生产环境变量已加载"
else
    echo "❌ [Error] 缺失 .env 文件，请配置 ANTHROPIC_API_KEY"
    exit 1
fi

export AUTORESEARCH_ENV="production"
export LOG_LEVEL="INFO"
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

# 3. 端口强制清理
PID=$(lsof -t -i:$PORT)
if [ -n "$PID" ]; then
    echo "⚠️ [Defense] 释放被占用的端口 $PORT (PID: $PID)..."
    kill -9 $PID
    sleep 1
fi

# 4. 启动 Uvicorn (生产模式: 多 Worker, 无 reload)
echo "🚀 [Launch] 拉起 FastAPI 生产集群 (4 Workers)..."
nohup .venv/bin/uvicorn src.autoresearch.api.main:app \
    --host 0.0.0.0 \
    --port $PORT \
    --workers 4 \
    --log-level info > "$DB_DIR/production_$(date +%Y%m%d).log" 2>&1 &

sleep 3

# 5. 生产状态回检
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$PORT/health)
if [ "$STATUS" -eq 200 ]; then
    echo "========================================"
    echo "🎉 [Success] 生产环境部署完成并已上线！"
    echo "========================================"
    echo "• 主控 API: http://127.0.0.1:$PORT"
    echo "• 视觉看板: http://127.0.0.1:$PORT/panel"
    echo "• 状态机DB: $DB_DIR/event_bus.sqlite"
    echo "• 运行日志: $DB_DIR/production_$(date +%Y%m%d).log"
else
    echo "❌ [Error] 服务拉起失败，请检查日志。"
fi
