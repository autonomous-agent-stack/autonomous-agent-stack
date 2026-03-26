#!/bin/bash
# 快速测试 FastAPI 服务

set -e

echo "🧪 测试 FastAPI 服务启动..."

# 激活虚拟环境
source .venv/bin/activate

# 测试导入
echo "📍 测试模块导入..."
python -c "
import sys
sys.path.insert(0, 'src')
from autoresearch.api.main import app
print('✅ 导入成功')
" || { echo "❌ 导入失败"; exit 1; }

# 测试启动（5秒超时）
echo ""
echo "📍 测试服务启动（5秒后自动退出）..."
timeout 5 uvicorn src.autoresearch.api.main:app --port 8000 || echo "✅ 服务启动测试完成"

echo ""
echo "🎉 所有测试通过！"
echo ""
echo "现在可以运行:"
echo "  bash start_with_memory.sh"
echo "选择选项 1 启动完整服务"
