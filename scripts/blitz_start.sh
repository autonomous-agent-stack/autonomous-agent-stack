#!/bin/bash
# Blitz Cold Start Script for Autonomous Agent Stack
# Version: v1.2.0-autonomous-genesis
# 用途：一键冷启动与物理对齐

set -e  # 遇到错误立即退出

PROJECT_ROOT="/Volumes/AI_LAB/Github/autonomous-agent-stack"
PORT=8001
LOG_FILE="/tmp/autoresearch_production.log"

echo "═══════════════════════════════════════════════════════════"
echo "🚀 (Blitz Start) Autonomous Agent Stack 冷启动与物理对齐"
echo "═══════════════════════════════════════════════════════════"
echo ""

# 1. 端口冲突清理
echo "📍 [Step 1/5] 端口冲突检查..."
PID=$(lsof -t -i:$PORT 2>/dev/null || true)
if [ -n "$PID" ]; then
    echo "   ⚠️  发现端口 $PORT 被占用 (PID: $PID)"
    echo "   🔨 正在强制释放..."
    kill -9 $PID 2>/dev/null || true
    sleep 1
    echo "   ✅ 端口已释放"
else
    echo "   ✅ 端口 $PORT 可用"
fi

# 2. 环境物理清理（AppleDouble + .DS_Store）
echo ""
echo "🧹 [Step 2/5] 执行环境物理清理..."
echo "   扫描并删除 ._ 文件..."
APPLEDOUBLE_COUNT=$(find "$PROJECT_ROOT" -name "._*" -type f 2>/dev/null | wc -l | xargs)
if [ "$APPLEDOUBLE_COUNT" -gt 0 ]; then
    find "$PROJECT_ROOT" -name "._*" -type f -delete 2>/dev/null || true
    echo "   ✅ 已删除 $APPLEDOUBLE_COUNT 个 AppleDouble 文件"
else
    echo "   ✅ 未发现 AppleDouble 文件"
fi

echo "   扫描并删除 .DS_Store 文件..."
DSSTORE_COUNT=$(find "$PROJECT_ROOT" -name ".DS_Store" -type f 2>/dev/null | wc -l | xargs)
if [ "$DSSTORE_COUNT" -gt 0 ]; then
    find "$PROJECT_ROOT" -name ".DS_Store" -type f -delete 2>/dev/null || true
    echo "   ✅ 已删除 $DSSTORE_COUNT 个 .DS_Store 文件"
else
    echo "   ✅ 未发现 .DS_Store 文件"
fi

# 3. 检查并创建必要的 __init__.py
echo ""
echo "📦 [Step 3/5] 检查模块导入路径..."
for dir in src src/memory src/executors src/opensage src/bridge src/gateway src/security; do
    if [ -d "$PROJECT_ROOT/$dir" ] && [ ! -f "$PROJECT_ROOT/$dir/__init__.py" ]; then
        touch "$PROJECT_ROOT/$dir/__init__.py"
        echo "   ✅ 创建 $dir/__init__.py"
    fi
done
echo "   ✅ 模块导入路径已对齐"

# 4. 清理旧日志
echo ""
echo "📝 [Step 4/5] 清理旧日志文件..."
if [ -f "$LOG_FILE" ]; then
    rm -f "$LOG_FILE"
    echo "   ✅ 旧日志已清理"
else
    echo "   ✅ 无需清理"
fi

# 5. 启动 Uvicorn 生产环境
echo ""
echo "🚀 [Step 5/5] 启动 Uvicorn 生产环境..."
cd "$PROJECT_ROOT"

# 检查 uvicorn 是否安装
if ! command -v uvicorn &> /dev/null; then
    echo "   ❌ 错误：uvicorn 未安装"
    echo "   请运行：pip install uvicorn[standard]"
    exit 1
fi

# 启动服务
uvicorn src.autoresearch.api.main:app \
    --host 127.0.0.1 \
    --port $PORT \
    --log-level info \
    --access-log > "$LOG_FILE" 2>&1 &

SERVER_PID=$!
sleep 2

# 6. 健康检查验证
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
    echo "📍 服务 PID: $SERVER_PID"
    echo "📍 日志文件: $LOG_FILE"
    echo ""
    echo "💡 提示：在 Telegram #General 话题下达指令"
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
