#!/bin/bash

# 运行所有自主 Agent 实验

echo "=========================================="
echo "🚀 运行自主 Agent 所有实验"
echo "=========================================="
echo ""

# 进入框架目录
cd "$(dirname "$0")"

# 运行测试
echo ""
echo "1️⃣ 运行基础测试..."
python tests/test_basic.py

# 运行数据分析实验
echo ""
echo "2️⃣ 运行数据分析实验..."
python experiments/data_analysis.py

# 运行代码生成实验
echo ""
echo "3️⃣ 运行代码生成实验..."
python experiments/code_generation.py

# 运行自动研究实验
echo ""
echo "4️⃣ 运行自动研究实验..."
python experiments/research.py

# 运行示例
echo ""
echo "5️⃣ 运行完整示例..."
python example.py

echo ""
echo "=========================================="
echo "✅ 所有实验完成！"
echo "=========================================="
