#!/bin/bash
# 健康检查脚本

API_URL="http://127.0.0.1:8000"

echo "🔍 检查 API 健康..."

# 系统健康
SYSTEM_HEALTH=$(curl -s "$API_URL/api/v1/system/health")
if echo "$SYSTEM_HEALTH" | grep -q '"status":"online"'; then
    echo "✅ 系统健康"
else
    echo "❌ 系统异常"
fi

# Admin 健康
ADMIN_HEALTH=$(curl -s "$API_URL/api/v1/admin/health")
if echo "$ADMIN_HEALTH" | grep -q '"status":"ok"'; then
    echo "✅ Admin 健康"
else
    echo "❌ Admin 异常"
fi

# 端点统计
ENDPOINTS=$(curl -s "$API_URL/openapi.json" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['paths']))")
echo "📊 端点数: $ENDPOINTS"

echo "✅ 健康检查完成"
