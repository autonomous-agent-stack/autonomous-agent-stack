#!/bin/bash

# 批量推送脚本
# 用途: 推送所有未推送的提交到 GitHub
# 作者: 火力全开 Agent
# 日期: 2026-03-27

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PROJECTS_DIR="$HOME/github_GZ"

echo -e "${GREEN}=== 批量推送脚本 ===${NC}"
echo "扫描目录: $PROJECTS_DIR"
echo ""

# 计数器
total_projects=0
pushed_projects=0
failed_projects=0

cd "$PROJECTS_DIR"

for dir in */; do
  if [ -d "$dir/.git" ]; then
    project_name="${dir%/}"
    ((total_projects++))

    cd "$dir"

    # 检查是否有未推送的提交
    current_branch=$(git branch --show-current)
    unpushed=$(git log "origin/$current_branch"..HEAD --oneline 2>/dev/null | wc -l | tr -d ' ')

    if [ "$unpushed" -gt 0 ]; then
      echo -e "${YELLOW}📤 $project_name ($unpushed 个未推送)${NC}"

      # 尝试推送
      if git push origin "$current_branch" 2>&1 | grep -q "rejected"; then
        echo -e "${RED}  ❌ 推送失败（可能需要先 pull）${NC}"
        ((failed_projects++))
      else
        echo -e "${GREEN}  ✅ 推送成功${NC}"
        ((pushed_projects++))
      fi
    fi

    cd "$PROJECTS_DIR"
  fi
done

echo ""
echo -e "${GREEN}=== 推送完成 ===${NC}"
echo "总项目数: $total_projects"
echo "推送成功: $pushed_projects"
echo "推送失败: $failed_projects"

if [ "$failed_projects" -gt 0 ]; then
  echo ""
  echo -e "${YELLOW}⚠️ 失败的项目需要手动处理（可能需要先 pull）${NC}"
fi
