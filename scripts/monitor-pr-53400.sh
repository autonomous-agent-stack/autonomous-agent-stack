#!/bin/bash
# PR #53400 监控脚本
# Created: 2026-03-25 07:22
# Purpose: 每30分钟检查PR状态，有变化时通知用户

set -e

PR_NUMBER=53400
REPO="openclaw/openclaw"
STATE_FILE="$HOME/.openclaw/workspace/.pr-53400-state.json"
LOG_FILE="$HOME/.openclaw/logs/pr-monitor-53400.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p "$(dirname "$STATE_FILE")"
mkdir -p "$(dirname "$LOG_FILE")"

echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] 检查 PR #$PR_NUMBER...${NC}" | tee -a "$LOG_FILE"

# 获取当前PR状态
CURRENT_STATE=$(gh pr view $PR_NUMBER --repo $REPO --json \
  title,state,updatedAt,author,labels,mergeable,reviewDecision,comments,reviews \
  --jq '{
    title: .title,
    state: .state,
    author: .author.login,
    updated: .updatedAt,
    labels: [.labels[].name],
    mergeable: .mergeable,
    review: .reviewDecision,
    comments: .comments.totalCount,
    reviews: [.reviews[] | {author: .author.login, state: .state}]
  }')

# 保存当前状态
echo "$CURRENT_STATE" > "$STATE_FILE"

# 检查是否有之前的状态
PREV_STATE_FILE="${STATE_FILE}.prev"
if [ -f "$PREV_STATE_FILE" ]; then
  PREV_STATE=$(cat "$PREV_STATE_FILE")
  
  # 比较状态变化
  CURRENT_UPDATE=$(echo "$CURRENT_STATE" | jq -r '.updated')
  PREV_UPDATE=$(echo "$PREV_STATE" | jq -r '.updated')
  
  if [ "$CURRENT_UPDATE" != "$PREV_UPDATE" ]; then
    echo -e "${GREEN}✓ 检测到变化！${NC}" | tee -a "$LOG_FILE"
    echo "更新时间: $CURRENT_UPDATE" | tee -a "$LOG_FILE"
    
    # 通知用户（通过系统消息）
    echo "PR #$PR_NUMBER 有新动态：更新于 $CURRENT_UPDATE" | tee -a "$LOG_FILE"
  else
    echo -e "${YELLOW}无变化${NC}" | tee -a "$LOG_FILE"
  fi
fi

# 保存当前状态为之前状态
cp "$STATE_FILE" "$PREV_STATE_FILE"

echo -e "${GREEN}✓ 检查完成${NC}" | tee -a "$LOG_FILE"
