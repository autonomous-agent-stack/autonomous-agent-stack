#!/bin/bash
# 部署检查脚本 - feature/topic-routing-gateway 合并前检查

set -e

echo "🔍 部署检查开始..."
echo ""

# 1. 物理路径校验
echo "📁 检查工作目录..."
if [[ "$PWD" != "/Volumes/PS1008/Github/autonomous-agent-stack" ]]; then
    echo "❌ 错误：当前不在正确的工作目录"
    echo "   当前：$PWD"
    echo "   应该：/Volumes/PS1008/Github/autonomous-agent-stack"
    exit 1
fi
echo "✅ 工作目录正确"
echo ""

# 2. AppleDouble 文件清理
echo "🧹 检查 AppleDouble 文件..."
APPLEDOUBLE_COUNT=$(find . -name "._*" -o -name ".DS_Store" 2>/dev/null | wc -l | tr -d ' ')
if [[ $APPLEDOUBLE_COUNT -gt 0 ]]; then
    echo "⚠️  发现 $APPLEDOUBLE_COUNT 个 AppleDouble 文件"
    echo "   建议执行：python3 src/security/apple_double_cleaner.py"
else
    echo "✅ 无 AppleDouble 文件"
fi
echo ""

# 3. Git 状态检查
echo "📦 检查 Git 状态..."
CURRENT_BRANCH=$(git branch --show-current)
echo "   当前分支：$CURRENT_BRANCH"

if [[ "$CURRENT_BRANCH" != "main" ]]; then
    echo "⚠️  当前不在 main 分支，需要先切换"
    echo "   执行：git checkout main"
fi
echo ""

# 4. 环境变量检查
echo "🔐 检查环境变量..."
if [[ -f ".env" ]]; then
    echo "✅ .env 文件存在"
    
    # 检查必需的配置
    if grep -q "AUTORESEARCH_TG_CHAT_ID" .env; then
        echo "✅ AUTORESEARCH_TG_CHAT_ID 已配置"
    else
        echo "⚠️  缺少 AUTORESEARCH_TG_CHAT_ID 配置"
    fi
    
    if grep -q "TELEGRAM_BOT_TOKEN" .env; then
        echo "✅ TELEGRAM_BOT_TOKEN 已配置"
    else
        echo "⚠️  缺少 TELEGRAM_BOT_TOKEN 配置"
    fi
else
    echo "⚠️  .env 文件不存在"
    echo "   建议复制：cp .env.topic-routing .env"
fi
echo ""

# 5. Docker 检查
echo "🐳 检查 Docker..."
if docker info &> /dev/null; then
    echo "✅ Docker 运行正常"
else
    echo "⚠️  Docker 未运行"
fi
echo ""

# 6. 分支合并准备
echo "🔀 检查分支状态..."
if git branch -a | grep -q "feature/topic-routing-gateway"; then
    echo "✅ feature/topic-routing-gateway 分支存在"
    
    # 检查未提交的文件
    UNCOMMITTED=$(git status --short | wc -l | tr -d ' ')
    if [[ $UNCOMMITTED -gt 0 ]]; then
        echo "⚠️  有 $UNCOMMITTED 个未提交的文件"
    else
        echo "✅ 工作区干净"
    fi
else
    echo "❌ feature/topic-routing-gateway 分支不存在"
    exit 1
fi
echo ""

# 总结
echo "📊 检查总结："
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 下一步操作："
echo "1. 切换到 main 分支：git checkout main"
echo "2. 配置 .env 文件：cp .env.topic-routing .env"
echo "3. 执行合并：git merge feature/topic-routing-gateway"
echo "4. 运行测试：pytest tests/ -v"
echo "5. 推送到远端：git push origin main"
echo "6. 重启服务"
echo ""
echo "✅ 部署检查完成！"
