#!/bin/bash

# 项目统计报告生成器
# 用途: 生成项目统计信息报告
# 作者: 火力全开 Agent
# 日期: 2026-03-27

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECTS_DIR="$HOME/github_GZ"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M")
REPORT_FILE="$HOME/github_GZ/openclaw-memory/memory/project-stats-$TIMESTAMP.md"

echo -e "${GREEN}=== 项目统计报告生成器 ===${NC}"
echo "扫描目录: $PROJECTS_DIR"
echo "报告输出: $REPORT_FILE"
echo ""

# 初始化计数器
total_projects=0
total_commits=0
total_files=0
total_lines=0

# 创建报告文件
cat > "$REPORT_FILE" << EOF
# 项目统计报告

> **生成时间**: $(date +"%Y-%m-%d %H:%M GMT+8")
> **扫描目录**: $PROJECTS_DIR

---

## 📊 总体统计

| 指标 | 数值 |
|------|------|
| **总项目数** | 0 |
| **总提交数** | 0 |
| **总文件数** | 0 |
| **总代码行数** | 0 |

---

## 📈 项目详情

| 项目 | 提交数 | 文件数 | 代码行数 | 最后更新 |
|------|--------|--------|----------|----------|
EOF

cd "$PROJECTS_DIR"

for dir in */; do
  if [ -d "$dir/.git" ]; then
    project_name="${dir%/}"
    ((total_projects++))

    cd "$dir"

    # 获取项目统计
    commits=$(git rev-list --count HEAD)
    files=$(find . -type f -not -path "./.git/*" | wc -l | tr -d ' ')
    lines=$(find . -type f -not -path "./.git/*" -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}')
    last_update=$(git log -1 --format='%ar')

    # 处理空值
    if [ -z "$lines" ]; then
      lines=0
    fi

    ((total_commits+=commits))
    ((total_files+=files))
    ((total_lines+=lines))

    echo "| **$project_name** | $commits | $files | $lines | $last_update |" >> "$REPORT_FILE"

    cd "$PROJECTS_DIR"
  fi
done

# 更新报告统计数据
sed -i '' "s/| \*\*总项目数\*\* | 0 |/| **总项目数** | $total_projects |/" "$REPORT_FILE"
sed -i '' "s/| \*\*总提交数\*\* | 0 |/| **总提交数** | $total_commits |/" "$REPORT_FILE"
sed -i '' "s/| \*\*总文件数\*\* | 0 |/| **总文件数** | $total_files |/" "$REPORT_FILE"
sed -i '' "s/| \*\*总代码行数\*\* | 0 |/| **总代码行数** | $total_lines |/" "$REPORT_FILE"

# 添加尾部
cat >> "$REPORT_FILE" << EOF

---

## 💡 分析建议

### 大项目（>100 提交）
- 需要重点关注代码质量
- 建议补充测试和文档
- 考虑模块化重构

### 中等项目（10-100 提交）
- 功能相对完善
- 建议优化性能
- 补充使用示例

### 小项目（<10 提交）
- 处于初期阶段
- 建议快速迭代
- 收集用户反馈

---

**生成时间**: $(date +"%Y-%m-%d %H:%M GMT+8")
EOF

echo ""
echo -e "${GREEN}=== 统计完成 ===${NC}"
echo "总项目数: $total_projects"
echo "总提交数: $total_commits"
echo "总文件数: $total_files"
echo "总代码行数: $total_lines"
echo ""
echo "报告已生成: $REPORT_FILE"
