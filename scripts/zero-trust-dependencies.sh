#!/bin/bash
# 零信任加固脚本 - 依赖哈希锁死

set -e

echo "🔐 零信任加固开始..."
echo ""

# Step 1: 生成哈希锁定的依赖清单
echo "📦 Step 1: 生成依赖哈希清单..."

if [[ -f "requirements.in" ]]; then
    pip-compile --generate-hashes requirements.in --output-file requirements.txt.locked
    echo "✅ requirements.txt.locked 已生成"
else
    echo "⚠️  requirements.in 不存在，从当前环境生成"
    pip freeze | grep -v "^\-e" > requirements.in
    pip-compile --generate-hashes requirements.in --output-file requirements.txt.locked
    echo "✅ requirements.txt.locked 已生成（从当前环境）"
fi

# Step 2: 验证哈希
echo ""
echo "🔍 Step 2: 验证哈希完整性..."

if pip install --dry-run -r requirements.txt.locked &> /dev/null; then
    echo "✅ 哈希验证通过"
else
    echo "❌ 哈希验证失败，可能存在篡改"
    exit 1
fi

# Step 3: 生成 SHA-256 校验和
echo ""
echo "🔐 Step 3: 生成 SHA-256 校验和..."

sha256sum requirements.txt.locked > requirements.txt.locked.sha256
echo "✅ SHA-256 校验和已生成"

# Step 4: 审计日志
echo ""
echo "📝 Step 4: 记录审计日志..."

AUDIT_LOG="logs/dependency-audit.log"
mkdir -p logs

echo "[$(date -Iseconds)] 零信任加固完成" >> $AUDIT_LOG
echo "  - 依赖数量: $(wc -l < requirements.txt.locked)" >> $AUDIT_LOG
echo "  - SHA-256: $(cut -d' ' -f1 requirements.txt.locked.sha256)" >> $AUDIT_LOG

echo "✅ 审计日志已记录"

echo ""
echo "🎉 零信任加固完成！"
echo ""
echo "📊 统计："
echo "  - 依赖数量: $(wc -l < requirements.txt.locked)"
echo "  - 校验和: $(cut -d' ' -f1 requirements.txt.locked.sha256)"
