#!/bin/bash

# 多项目健康度检查脚本
# 用途: 扫描所有 Git 项目，生成健康度报告
# 作者: 火力全开 Agent
# 日期: 2026-03-27

set -e

# 配置
PROJECTS_DIR="$HOME/github_GZ"
REPORT_DIR="$HOME/github_GZ/openclaw-memory/memory"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M")
REPORT_FILE="$REPORT_DIR/health-check-$TIMESTAMP.md"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== 多项目健康度检查 ===${NC}"
echo "扫描目录: $PROJECTS_DIR"
echo "报告输出: $REPORT_FILE"
echo ""

# 初始化计数器
total_projects=0
clean_projects=0
dirty_projects=0
total_commits=0
large_projects=0
stale_projects=0

# 创建报告文件
cat > "$REPORT_FILE" << EOF
# 项目健康度检查报告

> **执行时间**: $(date +"%Y-%m-%d %H:%M GMT+8")
> **扫描目录**: $PROJECTS_DIR

---

## 📊 总体统计

| 指标 | 数值 |
|------|------|
| **总项目数** | 0 |
| **干净项目** | 0 (0%) |
| **需清理项目** | 0 (0%) |
| **总提交数** | 0 |
| **大项目** | 0 (>100 提交) |
| **长期未更新** | 0 (>60 天) |

---

EOF

# 扫描项目
echo "## ✅ 干净项目" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "| 项目 | 分支 | 提交数 | 最后更新 | 状态 |" >> "$REPORT_FILE"
echo "|------|------|--------|----------|------|" >> "$REPORT_FILE"

cd "$PROJECTS_DIR"

for dir in */; do
  if [ -d "$dir/.git" ]; then
    project_name="${dir%/}"
    ((total_projects++))

    cd "$dir"

    # 获取项目信息
    branch=$(git branch --show-current)
    commits=$(git rev-list --count HEAD)
    last_update=$(git log -1 --format='%ar')
    uncommitted=$(git status --short | wc -l | tr -d ' ')

    ((total_commits+=commits))

    # 判断项目状态
    if [ "$uncommitted" -eq 0 ]; then
      ((clean_projects++))
      status="✅ 干净"
      echo "| **$project_name** | $branch | $commits | $last_update | $status |" >> "$REPORT_FILE"
    else
      ((dirty_projects++))
      status="⚠️ $uncommitted 未提交"
      echo -e "${YELLOW}⚠️ $project_name ($uncommitted 未提交)${NC}"
    fi

    # 判断是否是大项目
    if [ "$commits" -gt 100 ]; then
      ((large_projects++))
      echo -e "${GREEN}🔥 $project_name ($commits 提交)${NC}"
    fi

    # 判断是否长期未更新
    if [[ "$last_update" == *"weeks"* ]] || [[ "$last_update" == *"months"* ]]; then
      ((stale_projects++))
      echo -e "${RED}⏰ $project_name ($last_update)${NC}"
    fi

    cd "$PROJECTS_DIR"
  fi
done

# 更新报告统计数据
sed -i '' "s/| \*\*总项目数\*\* | 0 |/| **总项目数** | $total_projects |/" "$REPORT_FILE"
sed -i '' "s/| \*\*干净项目\*\* | 0 (0%)/| **干净项目** | $clean_projects ($(( clean_projects * 100 / total_projects ))%) |/" "$REPORT_FILE"
sed -i '' "s/| \*\*需清理项目\*\* | 0 (0%)/| **需清理项目** | $dirty_projects ($(( dirty_projects * 100 / total_projects ))%) |/" "$REPORT_FILE"
sed -i '' "s/| \*\*总提交数\*\* | 0 |/| **总提交数** | $total_commits |/" "$REPORT_FILE"
sed -i '' "s/| \*\*大项目\*\* | 0 (>100 提交)/| **大项目** | $large_projects (>100 提交) |/" "$REPORT_FILE"
sed -i '' "s/| \*\*长期未更新\*\* | 0 (>60 天)/| **长期未更新** | $stale_projects (>60 天) |/" "$REPORT_FILE"

# 添加行动建议
cat >> "$REPORT_FILE" << EOF

---

## 🚀 行动建议

### P0 紧急
- [ ] 提交所有未提交的文件
- [ ] 检查长期未更新的项目

### P1 高优先级
- [ ] 为大项目补充文档
- [ ] 整理项目结构

### P2 中优先级
- [ ] 评估是否归档不活跃项目
- [ ] 自动化健康检查（cron job）

---

**生成时间**: $(date +"%Y-%m-%d %H:%M GMT+8")
**下次检查**: $(date -v+7d +"%Y-%m-%d %H:%M GMT+8")
EOF

echo ""
echo -e "${GREEN}=== 检查完成 ===${NC}"
echo "总项目数: $total_projects"
echo "干净项目: $clean_projects ($(( clean_projects * 100 / total_projects ))%)"
echo "需清理: $dirty_projects"
echo "大项目: $large_projects"
echo "长期未更新: $stale_projects"
echo ""
echo "报告已生成: $REPORT_FILE"
