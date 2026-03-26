#!/bin/bash

# 快速提交脚本
# 用途: 一键提交所有未提交的文件
# 作者: 火力全开 Agent
# 日期: 2026-03-27

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 检查是否在 Git 仓库中
if [ ! -d ".git" ]; then
  echo -e "${RED}❌ 不在 Git 仓库中${NC}"
  exit 1
fi

# 获取未提交文件数
uncommitted=$(git status --short | wc -l | tr -d ' ')

if [ "$uncommitted" -eq 0 ]; then
  echo -e "${GREEN}✅ 没有未提交的文件${NC}"
  exit 0
fi

echo -e "${YELLOW}📋 发现 $uncommitted 个未提交文件${NC}"
git status --short

# 提示输入提交信息
echo ""
echo -e "${YELLOW}请输入提交信息（留空使用默认）:${NC}"
read -r commit_msg

if [ -z "$commit_msg" ]; then
  commit_msg="chore: 快速提交 $uncommitted 个文件"
fi

# 执行提交
echo ""
echo -e "${GREEN}🚀 正在提交...${NC}"
git add .
git commit -m "$commit_msg

Co-authored-by: 火力全开 Agent <fire-mode@openclaw>"

echo ""
echo -e "${GREEN}✅ 提交成功！${NC}"

# 询问是否推送
echo ""
echo -e "${YELLOW}是否推送到远程仓库？(y/n)${NC}"
read -r push_answer

if [ "$push_answer" = "y" ] || [ "$push_answer" = "Y" ]; then
  echo -e "${GREEN}🚀 正在推送...${NC}"
  git push origin "$(git branch --show-current)"
  echo -e "${GREEN}✅ 推送成功！${NC}"
fi

echo ""
echo -e "${GREEN}完成！${NC}"
