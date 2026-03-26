#!/bin/bash
# 快速启动脚本 - autonomous-agent-stack + OpenClaw 记忆
# 使用: bash start_with_memory.sh

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Autonomous Agent Stack - 快速启动（含 OpenClaw 记忆）  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 1. 激活虚拟环境
echo "📍 步骤 1/4: 激活虚拟环境..."
source .venv/bin/activate
echo "✅ Python $(python --version)"

# 2. 检查环境变量
echo ""
echo "📍 步骤 2/4: 检查环境变量..."
if [ -f ".env" ]; then
    echo "✅ .env 文件存在"
    if grep -q "ANTHROPIC_API_KEY" .env; then
        echo "✅ ANTHROPIC_API_KEY 已配置"
    else
        echo "⚠️  ANTHROPIC_API_KEY 未配置，请编辑 .env 文件"
    fi
else
    echo "⚠️  .env 文件不存在，请创建:"
    echo "   cp .env.template .env"
    echo "   nano .env"
fi

# 3. 运行核心测试
echo ""
echo "📍 步骤 3/4: 运行核心测试（验证环境）..."
python -m pytest tests/test_completeness.py -v --tb=short 2>&1 | tail -20

# 4. 启动 API 服务
echo ""
echo "📍 步骤 4/4: 启动 API 服务..."
echo ""
echo "🚀 选择启动方式:"
echo "  1. FastAPI 服务（端口 8000）"
echo "  2. 交互式对话（终端）"
echo "  3. 退出"
echo ""
read -p "请选择 (1/2/3): " choice

case $choice in
    1)
        echo ""
        echo "启动 FastAPI 服务..."
        echo "访问: http://localhost:8000/docs"
        uvicorn src.api.main:app --reload --port 8000
        ;;
    2)
        echo ""
        echo "启动交互式对话..."
        echo "输入 'exit' 退出"
        echo ""
        python -c "
import sys
sys.path.insert(0, '.')
from orchestrator.graph_engine import GraphEngine

print('🤖 Agent 已启动（使用 OpenClaw 记忆）')
print('输入问题开始对话，输入 exit 退出')
print('')

while True:
    user_input = input('你: ')
    if user_input.lower() == 'exit':
        break
    
    # 这里可以调用你的 Agent 逻辑
    print('Agent: 收到！正在处理...')
    print('（这里是演示，实际需要连接到 Agent 引擎）')
    print('')
"
        ;;
    3)
        echo "👋 退出"
        exit 0
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac
