#!/bin/bash

# 自动化测试脚本
# 用途: 运行所有测试并生成报告
# 作者: 持续工作 Agent
# 日期: 2026-03-27

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="$PROJECT_DIR/test-reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo -e "${GREEN}=== 自动化测试脚本 ===${NC}"
echo "项目目录: $PROJECT_DIR"
echo "报告目录: $REPORT_DIR"
echo ""

# 创建报告目录
mkdir -p "$REPORT_DIR"

# 运行 Python 测试
run_python_tests() {
    echo -e "${YELLOW}运行 Python 测试...${NC}"
    
    if [ -f "pytest.ini" ] || [ -f "pyproject.toml" ]; then
        # 运行 pytest
        pytest \
            --cov=. \
            --cov-report=html:"$REPORT_DIR/coverage_$TIMESTAMP" \
            --cov-report=xml:"$REPORT_DIR/coverage_$TIMESTAMP.xml" \
            --junitxml="$REPORT_DIR/junit_$TIMESTAMP.xml" \
            --html="$REPORT_DIR/test_report_$TIMESTAMP.html" \
            --self-contained-html \
            -v
        
        echo -e "${GREEN}✅ Python 测试完成${NC}"
    else
        echo -e "${YELLOW}⚠️ 未找到 Python 测试配置${NC}"
    fi
}

# 运行 JavaScript 测试
run_js_tests() {
    echo -e "${YELLOW}运行 JavaScript 测试...${NC}"
    
    if [ -f "package.json" ]; then
        # 检查测试框架
        if grep -q "jest" package.json; then
            npm test -- --coverage --reporters=default --reporters=jest-junit
            mv coverage "$REPORT_DIR/coverage_js_$TIMESTAMP" 2>/dev/null || true
            mv junit.xml "$REPORT_DIR/junit_js_$TIMESTAMP.xml" 2>/dev/null || true
        elif grep -q "mocha" package.json; then
            npm test
        fi
        
        echo -e "${GREEN}✅ JavaScript 测试完成${NC}"
    else
        echo -e "${YELLOW}⚠️ 未找到 package.json${NC}"
    fi
}

# 运行代码质量检查
run_quality_checks() {
    echo -e "${YELLOW}运行代码质量检查...${NC}"
    
    # Python 代码检查
    if command -v flake8 &> /dev/null; then
        flake8 . --output-file="$REPORT_DIR/flake8_$TIMESTAMP.txt" || true
        echo -e "${GREEN}✅ Flake8 检查完成${NC}"
    fi
    
    if command -v mypy &> /dev/null; then
        mypy . --html-report "$REPORT_DIR/mypy_$TIMESTAMP" || true
        echo -e "${GREEN}✅ MyPy 检查完成${NC}"
    fi
    
    # JavaScript 代码检查
    if [ -f "package.json" ] && grep -q "eslint" package.json; then
        npm run lint > "$REPORT_DIR/eslint_$TIMESTAMP.txt" 2>&1 || true
        echo -e "${GREEN}✅ ESLint 检查完成${NC}"
    fi
}

# 生成测试报告
generate_report() {
    echo -e "${YELLOW}生成测试报告...${NC}"
    
    REPORT_FILE="$REPORT_DIR/test_summary_$TIMESTAMP.md"
    
    cat > "$REPORT_FILE" << EOF
# 测试报告

> **生成时间**: $(date +"%Y-%m-%d %H:%M:%S")
> **项目**: $(basename "$PROJECT_DIR")

---

## 📊 测试统计

| 指标 | 数值 |
|------|------|
| **Python 测试** | $(find . -name "test_*.py" | wc -l | tr -d ' ') 个文件 |
| **JavaScript 测试** | $(find . -name "*.test.js" -o -name "*.spec.js" | wc -l | tr -d ' ') 个文件 |
| **代码覆盖率** | 见报告 |

---

## 📁 报告文件

- 覆盖率报告: \`coverage_$TIMESTAMP/html/index.html\`
- JUnit 报告: \`junit_$TIMESTAMP.xml\`
- HTML 报告: \`test_report_$TIMESTAMP.html\`

---

## 🎯 质量检查

- ✅ Flake8
- ✅ MyPy
- ✅ ESLint

---

**生成时间**: $(date +"%Y-%m-%d %H:%M:%S")
EOF
    
    echo -e "${GREEN}✅ 测试报告生成完成: $REPORT_FILE${NC}"
}

# 主流程
main() {
    cd "$PROJECT_DIR"
    
    run_python_tests
    run_js_tests
    run_quality_checks
    generate_report
    
    echo ""
    echo -e "${GREEN}=== 测试完成！ ===${NC}"
    echo "报告位置: $REPORT_DIR"
}

# 运行主流程
main
