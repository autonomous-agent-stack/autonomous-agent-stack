#!/bin/bash
# GitHub Issue Metrics Collector
# 收集和分析 GitHub Issue 指标
#
# 用途:
#   - 统计开放/关闭 Issues 数量
#   - 计算平均关闭时间
#   - 标签分布统计
#   - 团队成员工作负载分析
#
# 使用:
#   ./issue-metrics.sh owner/repo [SINCE_DATE]
#
# 示例:
#   ./issue-metrics.sh facebook/react 2024-01-01
#   ./issue-metrics.sh owner/repo $(date -v-1m +%Y-%m-%d)

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."

    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI (gh) 未安装"
        log_info "安装方法: brew install gh 或 apt install gh"
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        log_error "jq 未安装"
        log_info "安装方法: brew install jq 或 apt install jq"
        exit 1
    fi

    log_success "依赖检查通过"
}

# 验证参数
validate_args() {
    if [ -z "$1" ]; then
        log_error "缺少仓库参数"
        echo "使用: $0 owner/repo [SINCE_DATE]"
        echo "示例: $0 facebook/react 2024-01-01"
        exit 1
    fi

    REPO="$1"
    SINCE="${2:-2024-01-01}"

    log_info "仓库: $REPO"
    log_info "起始日期: $SINCE"
}

# 计算两个日期之间的天数
days_between() {
    local d1=$1
    local d2=$2
    echo $(( ( $(date -j -f "%Y-%m-%d" "$d2" +%s) - $(date -j -f "%Y-%m-%d" "$d1" +%s) ) / 86400 ))
}

# 获取 Issue 统计
get_issue_stats() {
    local state=$1
    local query="repo:$REPO created:>$SINCE state:$state"

    log_info "获取 $state Issues..."

    local count=$(gh issue list \
        --repo "$REPO" \
        --search "$query" \
        --limit 1000 \
        --json number \
        --jq 'length' \
        2>/dev/null || echo "0")

    echo "$count"
}

# 获取平均关闭时间
get_avg_close_time() {
    log_info "计算平均关闭时间..."

    local avg_time=$(gh issue list \
        --repo "$REPO" \
        --search "created:>$SINCE state:closed" \
        --limit 1000 \
        --json createdAt,closedAt \
        --jq '
            map(
                ((.closedAt | fromdateiso8601) - (.createdAt | fromdateiso8601)) / 86400
            ) |
            if length > 0 then add / length else 0 end
        ' \
        2>/dev/null || echo "0")

    printf "%.1f" "$avg_time"
}

# 获取标签分布
get_label_distribution() {
    log_info "获取标签分布..."

    gh issue list \
        --repo "$REPO" \
        --search "created:>$SINCE" \
        --limit 1000 \
        --json labels \
        --jq '[.[].labels[].name] | group_by(.) | map({label: .[0], count: length}) | sort_by(.count) | reverse' \
        2>/dev/null || echo "[]"
}

# 获取团队成员工作负载
get_team_workload() {
    log_info "获取团队工作负载..."

    gh issue list \
        --repo "$REPO" \
        --search "created:>$SINCE state:open" \
        --limit 1000 \
        --json assignees \
        --jq '
            map(.assignees[].login) |
            group_by(.) |
            map({member: .[0], open_issues: length}) |
            sort_by(.open_issues) |
            reverse
        ' \
        2>/dev/null || echo "[]"
}

# 获取优先级分布
get_priority_distribution() {
    log_info "获取优先级分布..."

    gh issue list \
        --repo "$REPO" \
        --search "created:>$SINCE" \
        --limit 1000 \
        --json labels \
        --jq '
            [.[].labels[] | select(.name | startswith("priority:")) | .name] |
            group_by(.) |
            map({priority: .[0], count: length})
        ' \
        2>/dev/null || echo "[]"
}

# 格式化 Markdown 表格行
format_table_row() {
    local str="$1"
    local max_len=$2
    local len=${#str}

    if [ $len -gt $max_len ]; then
        echo "${str:0:$((max_len-3))}..."
    else
        printf "%-$((max_len+2))s" "$str"
    fi
}

# 生成报告
generate_report() {
    local total_open=$1
    local total_closed=$2
    local avg_close_time=$3
    local labels_json=$4
    local workload_json=$5
    local priority_json=$6

    echo ""
    echo "# GitHub Issue Metrics Report"
    echo ""
    echo "**Repository**: \`$REPO\`"
    echo "**Period**: \`$SINCE\` to present"
    echo "**Generated**: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    echo "---"
    echo ""

    # 总览
    echo "## 📊 Overview"
    echo ""
    echo "| Metric | Count |"
    echo "|--------|-------|"
    echo "| Total Open Issues | $total_open |"
    echo "| Total Closed Issues | $total_closed |"
    echo "| Total Issues | $((total_open + total_closed)) |"
    echo "| Average Close Time | ${avg_close_time} days |"
    echo "| Close Rate | $(awk "BEGIN {printf \"%.1f\", $total_closed / ($total_open + $total_closed) * 100}")% |"
    echo ""

    # 优先级分布
    echo "## 🎯 Priority Distribution"
    echo ""
    echo "| Priority | Count |"
    echo "|----------|-------|"

    echo "$priority_json" | jq -r '.[] | "| \(.priority) | \(.count) |"'
    echo ""

    # 标签分布 (Top 10)
    echo "## 🏷️ Label Distribution (Top 10)"
    echo ""
    echo "| Label | Count |"
    echo "|-------|-------|"

    echo "$labels_json" | jq -r '.[:10][] | "| `\(.label)` | \(.count) |"'
    echo ""

    # 团队工作负载
    echo "## 👥 Team Workload"
    echo ""
    echo "| Member | Open Issues |"
    echo "|--------|-------------|"

    echo "$workload_json" | jq -r '.[] | "| @\(.member) | \(.open_issues) |"'
    echo ""

    # 趋势分析
    echo "## 📈 Trend Analysis"
    echo ""

    # 计算每日平均创建数
    local days=$(days_between "$SINCE" "$(date +%Y-%m-%d)")
    local daily_created=$(awk "BEGIN {printf \"%.1f\", ($total_open + $total_closed) / $days}")

    echo "- **Daily Average**: $daily_created issues/day"
    echo "- **Days in Period**: $days days"
    echo "- **Project Velocity**: ${avg_close_time} days avg close time"
    echo ""

    # 建议
    echo "## 💡 Recommendations"
    echo ""

    if [ $(echo "$avg_close_time > 7" | bc -l) -eq 1 ]; then
        echo "⚠️ **Close time is high** (> 7 days). Consider:"
        echo "  - Reviewing triage process"
        echo "  - Assigning issues faster"
        echo "  - Adding more team members"
        echo ""
    fi

    if [ $total_open -gt 100 ]; then
        echo "⚠️ **High open issue count** (> 100). Consider:"
        echo "  - Running cleanup for stale issues"
        echo "  - Reviewing and closing resolved issues"
        echo "  - Improving issue templates"
        echo ""
    fi

    local high_priority=$(echo "$priority_json" | jq '[.[] | select(.priority == "priority:high" or .priority == "priority:critical") | .count] | add')
    if [ "$high_priority" -gt 10 ]; then
        echo "⚠️ **Many high-priority issues** ($high_priority). Consider:"
        echo "  - Allocating dedicated resources"
        echo "  - Escalating to management"
        echo "  - Reprioritizing backlog"
        echo ""
    fi

    echo "---"
    echo ""
    echo "*Generated by [issue-metrics.sh](https://github.com/your-org/github-automation-scripts)*"
}

# 主函数
main() {
    echo ""
    log_info "GitHub Issue Metrics Collector"
    echo ""

    # 检查依赖
    check_dependencies

    # 验证参数
    validate_args "$@"

    # 检查认证
    if ! gh auth status &> /dev/null; then
        log_error "GitHub CLI 未认证"
        log_info "运行: gh auth login"
        exit 1
    fi

    log_success "开始收集指标..."

    # 收集数据
    total_open=$(get_issue_stats "open")
    total_closed=$(get_issue_stats "closed")
    avg_close_time=$(get_avg_close_time)
    labels_json=$(get_label_distribution)
    workload_json=$(get_team_workload)
    priority_json=$(get_priority_distribution)

    # 生成报告
    generate_report \
        "$total_open" \
        "$total_closed" \
        "$avg_close_time" \
        "$labels_json" \
        "$workload_json" \
        "$priority_json"

    log_success "报告生成完成！"
}

# 运行主函数
main "$@"
