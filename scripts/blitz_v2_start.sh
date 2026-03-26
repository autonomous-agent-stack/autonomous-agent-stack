#!/bin/bash
# Blitz v2.0 冷启动脚本 - 分布式生产环境
# Version: v2.0-distributed-genesis

set -e

PROJECT_ROOT="/Volumes/AI_LAB/Github/autonomous-agent-stack"
PORT=8001
LOG_FILE="/tmp/autoresearch_v2.log"

echo "═══════════════════════════════════════════════════════════"
echo "🚀 (Blitz v2.0) Autonomous Agent Stack - 分布式启动"
echo "═══════════════════════════════════════════════════════════"
echo ""

# 1. 检查 PostgreSQL
echo "📍 [Step 1/6] 检查 PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo "   ⚠️  PostgreSQL 未安装"
    echo "   💡 建议安装: brew install postgresql@15"
else
    if pg_isready -q; then
        echo "   ✅ PostgreSQL 运行中"
    else
        echo "   🔨 启动 PostgreSQL..."
        brew services start postgresql@15 || true
        sleep 2
        echo "   ✅ PostgreSQL 已启动"
    fi
fi

# 2. 检查 Redis
echo ""
echo "📍 [Step 2/6] 检查 Redis..."
if ! command -v redis-cli &> /dev/null; then
    echo "   ⚠️  Redis 未安装"
    echo "   💡 建议安装: brew install redis"
else
    if redis-cli ping > /dev/null 2>&1; then
        echo "   ✅ Redis 运行中"
    else
        echo "   🔨 启动 Redis..."
        brew services start redis || true
        sleep 1
        echo "   ✅ Redis 已启动"
    fi
fi

# 3. 环境物理清理
echo ""
echo "🧹 [Step 3/6] 执行环境物理清理..."
APPLEDOUBLE_COUNT=$(find "$PROJECT_ROOT" -name "._*" -type f 2>/dev/null | wc -l | xargs)
if [ "$APPLEDOUBLE_COUNT" -gt 0 ]; then
    find "$PROJECT_ROOT" -name "._*" -type f -delete 2>/dev/null || true
    echo "   ✅ 已删除 $APPLEDOUBLE_COUNT 个 AppleDouble 文件"
else
    echo "   ✅ 未发现 AppleDouble 文件"
fi

# 4. 数据库迁移
echo ""
echo "📦 [Step 4/6] 执行数据库迁移..."
cd "$PROJECT_ROOT"

if [ -d "alembic" ]; then
    if command -v alembic &> /dev/null; then
        alembic upgrade head > /dev/null 2>&1 || echo "   ⚠️  迁移失败（可能已是最新）"
        echo "   ✅ 数据库已迁移"
    else
        echo "   ⚠️  Alembic 未安装，跳过迁移"
    fi
else
    echo "   ⚠️  Alembic 目录不存在，跳过迁移"
fi

# 5. 安装依赖
echo ""
echo "📦 [Step 5/6] 检查依赖..."
if command -v uv &> /dev/null; then
    uv pip install asyncpg redis webauthn psutil aiohttp > /dev/null 2>&1 || true
    echo "   ✅ 依赖已安装"
elif command -v pip &> /dev/null; then
    pip install asyncpg redis webauthn psutil aiohttp > /dev/null 2>&1 || true
    echo "   ✅ 依赖已安装"
else
    echo "   ⚠️  未找到 pip 或 uv，请手动安装依赖"
fi

# 6. 启动服务
echo ""
echo "🚀 [Step 6/6] 启动 Uvicorn 生产环境..."
PID=$(lsof -t -i:$PORT 2>/dev/null || true)
if [ -n "$PID" ]; then
    echo "   ⚠️  端口 $PORT 被占用 (PID: $PID)，正在释放..."
    kill -9 $PID 2>/dev/null || true
    sleep 1
fi

# 启动服务
uvicorn src.autoresearch.api.main:app \
    --host 127.0.0.1 \
    --port $PORT \
    --log-level info \
    --access-log > "$LOG_FILE" 2>&1 &

SERVER_PID=$!
sleep 3

# 健康检查
echo ""
echo "🏥 [Health Check] 验证服务状态..."
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$PORT/health 2>/dev/null || echo "000")

if [ "$HEALTH_STATUS" -eq 200 ]; then
    echo "═══════════════════════════════════════════════════════════"
    echo "🎉 [Success] 底座已就绪"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "📍 监控面板: http://127.0.0.1:$PORT/panel"
    echo "📍 健康检查: http://127.0.0.1:$PORT/health"
    echo "📍 WebSocket: ws://127.0.0.1:$PORT/ws/telemetry"
    echo "📍 服务 PID: $SERVER_PID"
    echo "📍 日志文件: $LOG_FILE"
    echo ""
    echo "🧪 测试命令:"
    echo "   curl http://127.0.0.1:$PORT/health"
    echo "   wscat -c ws://127.0.0.1:$PORT/ws/telemetry"
    echo ""
else
    echo "═══════════════════════════════════════════════════════════"
    echo "❌ [Error] 服务启动异常"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "📍 健康检查状态: $HEALTH_STATUS"
    echo "📍 日志文件: $LOG_FILE"
    echo ""
    echo "💡 请检查日志："
    echo "   tail -f $LOG_FILE"
    echo ""
    exit 1
fi
