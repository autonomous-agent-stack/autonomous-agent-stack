#!/bin/bash

# AI 代码审查工具选择计算器
# 帮助团队根据需求选择最合适的工具

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 工具列表
tools=("SonarQube" "CodeClimate" "Codacy" "DeepSource" "Semgrep")

# 打印标题
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║    AI 代码审查工具选择计算器                           ║${NC}"
    echo -e "${BLUE}║    AI Code Review Tool Selector Calculator             ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# 提问并获取答案
ask_question() {
    local question=$1
    local options=$2
    local min=$3
    local max=$4

    while true; do
        echo -e "${YELLOW}▶ $question${NC}"
        echo "$options"
        read -p "请选择 [$min-$max]: " answer

        if [[ "$answer" =~ ^[0-9]+$ ]] && [ "$answer" -ge "$min" ] && [ "$answer" -le "$max" ]; then
            echo "$answer"
            break
        else
            echo -e "${RED}❌ 无效选择，请输入 $min 到 $max 之间的数字${NC}"
        fi
    done
}

# 初始化评分
declare -A scores
for tool in "${tools[@]}"; do
    scores[$tool]=0
done

# 问题 1: 团队规模
q1_answer=$(ask_question \
    "1. 您的团队规模是多少？" \
    "  1. 个人或 1-10 人的小团队
  2. 10-50 人的中型团队
  3. 50-100 人的大型团队
  4. 100+ 人的超大型团队" \
    1 4)

case $q1_answer in
    1)
        ((scores[SonarQube]+=1))
        ((scores[CodeClimate]+=2))
        ((scores[Codacy]+=3))
        ((scores[DeepSource]+=3))
        ((scores[Semgrep]+=2))
        ;;
    2)
        ((scores[SonarQube]+=3))
        ((scores[CodeClimate]+=4))
        ((scores[Codacy]+=3))
        ((scores[DeepSource]+=3))
        ((scores[Semgrep]+=3))
        ;;
    3)
        ((scores[SonarQube]+=5))
        ((scores[CodeClimate]+=4))
        ((scores[Codacy]+=3))
        ((scores[DeepSource]+=3))
        ((scores[Semgrep]+=3))
        ;;
    4)
        ((scores[SonarQube]+=5))
        ((scores[CodeClimate]+=4))
        ((scores[Codacy]+=3))
        ((scores[DeepSource]+=3))
        ((scores[Semgrep]+=4))
        ;;
esac

# 问题 2: 主要编程语言
q2_answer=$(ask_question \
    "2. 您主要使用哪种编程语言？" \
    "  1. Java / JVM 语言
  2. Python
  3. JavaScript / TypeScript
  4. Go
  5. Ruby
  6. PHP
  7. C/C++
  8. 多语言混合" \
    1 8)

case $q2_answer in
    1) # Java
        ((scores[SonarQube]+=5))
        ((scores[Semgrep]+=4))
        ((scores[Codacy]+=3))
        ;;
    2) # Python
        ((scores[Semgrep]+=5))
        ((scores[DeepSource]+=4))
        ((scores[Codacy]+=3))
        ((scores[SonarQube]+=3))
        ;;
    3) # JavaScript
        ((scores[DeepSource]+=5))
        ((scores[Codacy]+=4))
        ((scores[Semgrep]+=3))
        ;;
    4) # Go
        ((scores[Semgrep]+=4))
        ((scores[DeepSource]+=4))
        ((scores[Codacy]+=3))
        ;;
    5) # Ruby
        ((scores[CodeClimate]+=5))
        ((scores[DeepSource]+=3))
        ;;
    6) # PHP
        ((scores[SonarQube]+=4))
        ((scores[Codacy]+=3))
        ;;
    7) # C/C++
        ((scores[SonarQube]+=5))
        ((scores[Semgrep]+=4))
        ;;
    8) # 多语言
        ((scores[SonarQube]+=5))
        ((scores[Semgrep]+=4))
        ((scores[DeepSource]+=3))
        ;;
esac

# 问题 3: 最关注的需求
q3_answer=$(ask_question \
    "3. 您最关注什么？（可多选，选择最重要的）" \
    "  1. 代码质量和可维护性
  2. 技术债管理
  3. 安全漏洞检测
  4. 测试覆盖率
  5. 快速反馈和开发体验" \
    1 5)

case $q3_answer in
    1) # 代码质量
        ((scores[SonarQube]+=5))
        ((scores[CodeClimate]+=3))
        ((scores[DeepSource]+=4))
        ;;
    2) # 技术债
        ((scores[CodeClimate]+=5))
        ((scores[SonarQube]+=4))
        ((scores[Codacy]+=2))
        ;;
    3) # 安全
        ((scores[Semgrep]+=5))
        ((scores[SonarQube]+=4))
        ((scores[DeepSource]+=3))
        ;;
    4) # 覆盖率
        ((scores[Codacy]+=5))
        ((scores[SonarQube]+=4))
        ((scores[CodeClimate]+=3))
        ;;
    5) # 快速反馈
        ((scores[DeepSource]+=5))
        ((scores[Semgrep]+=4))
        ((scores[Codacy]+=3))
        ;;
esac

# 问题 4: CI/CD 集成需求
q4_answer=$(ask_question \
    "4. 您是否需要深度 CI/CD 集成？" \
    "  1. 是，需要质量门禁和详细报告
  2. 是，但简单集成即可
  3. 否，主要在本地使用" \
    1 3)

case $q4_answer in
    1)
        ((scores[SonarQube]+=5))
        ((scores[Semgrep]+=5))
        ((scores[CodeClimate]+=3))
        ((scores[Codacy]+=3))
        ((scores[DeepSource]+=3))
        ;;
    2)
        ((scores[Codacy]+=4))
        ((scores[DeepSource]+=4))
        ((scores[CodeClimate]+=3))
        ;;
    3)
        ((scores[Semgrep]+=3))
        ((scores[DeepSource]+=3))
        ;;
esac

# 问题 5: 预算
q5_answer=$(ask_question \
    "5. 您的预算范围是多少？" \
    "  1. 免费或低成本（< $100/月）
  2. 中等预算（$100-500/月）
  3. 充足预算（$500+/月）
  4. 愿意自托管（需要时间维护）" \
    1 4)

case $q5_answer in
    1)
        ((scores[Semgrep]+=5))
        ((scores[SonarQube]+=3)) # 开源版
        ((scores[Codacy]+=2))
        ((scores[DeepSource]+=2))
        ((scores[CodeClimate]+=1))
        ;;
    2)
        ((scores[Codacy]+=4))
        ((scores[DeepSource]+=4))
        ((scores[Semgrep]+=3))
        ;;
    3)
        ((scores[SonarQube]+=5))
        ((scores[CodeClimate]+=4))
        ((scores[Codacy]+=3))
        ((scores[DeepSource]+=3))
        ;;
    4)
        ((scores[SonarQube]+=5))
        ((scores[Semgrep]+=5))
        ;;
esac

# 问题 6: 自定义规则需求
q6_answer=$(ask_question \
    "6. 您是否需要编写自定义规则？" \
    "  1. 是，需要高度自定义
  2. 可能需要，但不是必需的
  3. 否，默认规则足够" \
    1 3)

case $q6_answer in
    1)
        ((scores[Semgrep]+=5))
        ((scores[SonarQube]+=4))
        ((scores[DeepSource]+=3))
        ;;
    2)
        ((scores[SonarQube]+=3))
        ((scores[DeepSource]+=3))
        ((scores[Codacy]+=2))
        ;;
    3)
        ((scores[CodeClimate]+=4))
        ((scores[Codacy]+=4))
        ((scores[DeepSource]+=4))
        ;;
esac

# 问题 7: 部署偏好
q7_answer=$(ask_question \
    "7. 您偏好哪种部署方式？" \
    "  1. SaaS（托管服务，快速上手）
  2. 自托管（完全控制）
  3. 混合（部分 SaaS，部分自托管）" \
    1 3)

case $q7_answer in
    1)
        ((scores[CodeClimate]+=4))
        ((scores[Codacy]+=4))
        ((scores[DeepSource]+=4))
        ((scores[Semgrep]+=3))
        ((scores[SonarQube]+=2))
        ;;
    2)
        ((scores[SonarQube]+=5))
        ((scores[Semgrep]+=5))
        ;;
    3)
        ((scores[SonarQube]+=4))
        ((scores[Semgrep]+=4))
        ((scores[DeepSource]+=3))
        ;;
esac

# 清屏并显示结果
clear
print_header

echo -e "${GREEN}📊 评分结果：${NC}"
echo ""

# 排序并显示结果
sorted_tools=($(for tool in "${!scores[@]}"; do
    echo "${scores[$tool]} $tool"
done | sort -rn | awk '{print $2}'))

# 显示排名
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}║  排名  │  工具名称         │  总分  │  推荐指数          ║${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"

rank=1
for tool in "${sorted_tools[@]}"; do
    score=${scores[$tool]}

    # 计算推荐指数
    if [ $score -ge 30 ]; then
        stars="⭐⭐⭐⭐⭐"
        recommendation="${GREEN}强烈推荐${NC}"
    elif [ $score -ge 25 ]; then
        stars="⭐⭐⭐⭐"
        recommendation="${YELLOW}推荐${NC}"
    elif [ $score -ge 20 ]; then
        stars="⭐⭐⭐"
        recommendation="${YELLOW}可以考虑${NC}"
    else
        stars="⭐⭐"
        recommendation="${RED}不推荐${NC}"
    fi

    printf "║  %2d   │  %-15s │  %2d    │  %-20s ║\n" "$rank" "$tool" "$score" "$stars"
    ((rank++))
done

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""

# 显示前两名推荐
echo -e "${GREEN}🎯 推荐方案：${NC}"
echo ""
echo -e "${YELLOW}方案 1（首选）：${sorted_tools[0]}${NC}"
echo "  推荐理由：评分最高，最符合您的需求"
echo ""

if [ ${#sorted_tools[@]} -gt 1 ]; then
    echo -e "${YELLOW}方案 2（备选）：${sorted_tools[1]}${NC}"
    echo "  推荐理由：评分第二，可以作为补充工具"
    echo ""
fi

echo -e "${BLUE}💡 使用建议：${NC}"
echo "  1. 先试用推荐工具的免费版"
echo "  2. 评估是否满足需求"
echo "  3. 考虑组合使用多个工具（如：SonarQube + Semgrep）"
echo "  4. 参考实战指南文档进行部署"
echo ""

echo -e "${BLUE}📚 相关文档：${NC}"
echo "  • 完整对比指南：ai-code-review-tools-comparison.md"
echo "  • 实战案例：ai-code-review-tools-practical-guide.md"
echo "  • 快速参考：ai-code-review-tools-quick-ref.md"
echo ""

echo -e "${GREEN}✅ 计算完成！感谢使用！${NC}"
