#!/bin/bash
# Super Agent Stack - 一键冷启动脚本
# 用途：清理端口、启动服务、验证健康

set -e

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="/Volumes/AI_LAB/Github/autonomous-agent-stack"
PORT=8001
LOG_FILE="/tmp/autoresearch_8001.log"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Super Agent Stack - 冷启动序列${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 步骤 1：清理残留进程
echo -e "${YELLOW}[1/5] 清理残留进程...${NC}"
if lsof -i :${PORT} > /dev/null 2>&1; then
    echo -e "  发现端口 ${PORT} 被占用，正在清理..."
    pkill -9 -f "uvicorn.*${PORT}"
    sleep 2
    echo -e "  ${GREEN}✅ 端口已清理${NC}"
else
    echo -e "  ${GREEN}✅ 端口 ${PORT} 空闲${NC}"
fi

# 步骤 2：清理 AppleDouble 文件
echo -e "${YELLOW}[2/5] 物理环境防御（AppleDouble 清理）...${NC}"
find "${PROJECT_ROOT}" -name "._*" -type f -delete 2>/dev/null || true
find "${PROJECT_ROOT}" -name ".DS_Store" -type f -delete 2>/dev/null || true
echo -e "  ${GREEN}✅ 环境清理完成${NC}"

# 步骤 3：启动服务
echo -e "${YELLOW}[3/5] 启动 FastAPI 服务...${NC}"
cd "${PROJECT_ROOT}"

# 设置环境变量
export PYTHONPATH="${PROJECT_ROOT}/src:$PYTHONPATH"

# 启动 uvicorn
nohup .venv/bin/python -m uvicorn autoresearch.api.main:app \
    --host 127.0.0.1 \
    --port ${PORT} \
    > "${LOG_FILE}" 2>&1 &

UVICORN_PID=$!
echo -e "  服务 PID: ${UVICORN_PID}"

# 等待服务启动
sleep 5

# 步骤 4：健康检查
echo -e "${YELLOW}[4/5] 健康检查...${NC}"

# 检查主服务
if curl -s http://127.0.0.1:${PORT}/health > /dev/null; then
    echo -e "  ${GREEN}✅ 主服务健康（/health）${NC}"
else
    echo -e "  ${RED}❌ 主服务启动失败${NC}"
    echo -e "  查看日志: tail -50 ${LOG_FILE}"
    exit 1
fi

# 检查系统健康 API
if curl -s http://127.0.0.1:${PORT}/api/v1/system/health > /dev/null; then
    echo -e "  ${GREEN}✅ 系统健康 API（/api/v1/system/health）${NC}"
else
    echo -e "  ${RED}❌ 系统 API 启动失败${NC}"
    exit 1
fi

# 检查 Blitz API
if curl -s http://127.0.0.1:${PORT}/api/v1/blitz/status > /dev/null; then
    echo -e "  ${GREEN}✅ Blitz API（/api/v1/blitz/status）${NC}"
else
    echo -e "  ${RED}❌ Blitz API 启动失败${NC}"
    exit 1
fi

# 步骤 5：显示状态
echo -e "${YELLOW}[5/5] 系统状态...${NC}"
echo ""

# 获取矩阵状态
MATRIX_STATUS=$(curl -s http://127.0.0.1:${PORT}/api/v1/blitz/status | python3 -m json.tool 2>/dev/null)

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ 启动成功！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "服务地址："
echo -e "  - 主服务:     ${GREEN}http://127.0.0.1:${PORT}${NC}"
echo -e "  - 文档:       ${GREEN}http://127.0.0.1:${PORT}/docs${NC}"
echo -e "  - 系统健康:   ${GREEN}http://127.0.0.1:${PORT}/api/v1/system/health${NC}"
echo -e "  - Blitz 状态: ${GREEN}http://127.0.0.1:${PORT}/api/v1/blitz/status${NC}"
echo ""
echo -e "日志文件: ${YELLOW}${LOG_FILE}${NC}"
echo -e "服务 PID: ${YELLOW}${UVICORN_PID}${NC}"
echo ""

# 显示 Agent 状态
echo -e "${GREEN}Agent 矩阵状态:${NC}"
echo "${MATRIX_STATUS}" | grep -A 10 '"agents"' | head -15

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}准备就绪，等待指令！${NC}"
echo -e "${GREEN}========================================${NC}"
