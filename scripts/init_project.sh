#!/bin/bash

# 项目初始化脚本
# 用途: 初始化新项目结构
# 作者: 持续工作 Agent
# 日期: 2026-03-27

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_NAME="${1:-my-project}"
PROJECT_TYPE="${2:-python}"  # python | node | fullstack

echo -e "${GREEN}=== 项目初始化 ===${NC}"
echo "项目名称: $PROJECT_NAME"
echo "项目类型: $PROJECT_TYPE"
echo ""

# 创建项目目录
mkdir -p "$PROJECT_NAME"
cd "$PROJECT_NAME"

# 初始化 Git
init_git() {
    echo -e "${YELLOW}初始化 Git...${NC}"
    
    git init
    
    # 创建 .gitignore
    cat > .gitignore << EOF
# Python
__pycache__/
*.py[cod]
*.so
.Python
build/
dist/
*.egg-info/
.venv/
venv/
ENV/

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.npm
.yarn-integrity

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Environment
.env
.env.local
.env.*.local

# Logs
*.log
logs/

# Testing
.coverage
.pytest_cache/
htmlcov/
coverage.xml
*.cover

# Build
dist/
build/
*.spec
EOF
    
    echo -e "${GREEN}✅ Git 初始化完成${NC}"
}

# 初始化 Python 项目
init_python() {
    echo -e "${YELLOW}初始化 Python 项目...${NC}"
    
    # 创建目录结构
    mkdir -p src/"$PROJECT_NAME"
    mkdir -p tests
    mkdir -p docs
    mkdir -p scripts
    
    # 创建 __init__.py
    touch src/"$PROJECT_NAME"/__init__.py
    
    # 创建 pyproject.toml
    cat > pyproject.toml << EOF
[project]
name = "$PROJECT_NAME"
version = "0.1.0"
description = "A Python project"
authors = [{name = "Your Name", email = "your@email.com"}]
requires-python = ">=3.9"

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "flake8>=6.0.0",
    "mypy>=1.0.0",
    "black>=23.0.0"
]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"
addopts = "-v --cov=src --cov-report=html"

[tool.black]
line-length = 100
target-version = ['py39']

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
EOF
    
    # 创建 requirements.txt
    cat > requirements.txt << EOF
# 核心依赖
# fastapi>=0.100.0
# pydantic>=2.0.0

# 开发依赖
# 见 pyproject.toml [project.optional-dependencies]
EOF
    
    # 创建 README.md
    cat > README.md << EOF
# $PROJECT_NAME

> 项目简介

## 安装

\`\`\`bash
pip install -e .
\`\`\`

## 使用

\`\`\`python
from $PROJECT_NAME import main

main.run()
\`\`\`

## 测试

\`\`\`bash
pytest
\`\`\`

## 许可证

MIT
EOF
    
    # 创建示例代码
    cat > src/"$PROJECT_NAME"/main.py << EOF
"""
$PROJECT_NAME 主模块
"""

def run():
    """运行主函数"""
    print("Hello, $PROJECT_NAME!")

if __name__ == "__main__":
    run()
EOF
    
    # 创建测试文件
    cat > tests/test_main.py << EOF
"""
测试主模块
"""
from $PROJECT_NAME.main import run

def test_run():
    """测试 run 函数"""
    # TODO: 添加测试
    pass
EOF
    
    echo -e "${GREEN}✅ Python 项目初始化完成${NC}"
}

# 初始化 Node 项目
init_node() {
    echo -e "${YELLOW}初始化 Node 项目...${NC}"
    
    # 创建 package.json
    cat > package.json << EOF
{
  "name": "$PROJECT_NAME",
  "version": "0.1.0",
  "description": "A Node.js project",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js",
    "test": "jest",
    "lint": "eslint src/"
  },
  "keywords": [],
  "author": "Your Name",
  "license": "MIT",
  "devDependencies": {
    "jest": "^29.0.0",
    "eslint": "^8.0.0"
  }
}
EOF
    
    # 创建目录结构
    mkdir -p src
    mkdir -p tests
    mkdir -p docs
    
    # 创建示例代码
    cat > src/index.js << EOF
/**
 * $PROJECT_NAME 主模块
 */

function main() {
  console.log('Hello, $PROJECT_NAME!');
}

module.exports = { main };

if (require.main === module) {
  main();
}
EOF
    
    # 创建测试文件
    cat > tests/index.test.js << EOF
/**
 * 测试主模块
 */
const { main } = require('../src/index');

describe('Main', () => {
  test('should run main function', () => {
    // TODO: 添加测试
  });
});
EOF
    
    # 创建 README.md
    cat > README.md << EOF
# $PROJECT_NAME

> 项目简介

## 安装

\`\`\`bash
npm install
\`\`\`

## 使用

\`\`\`bash
npm start
\`\`\`

## 测试

\`\`\`bash
npm test
\`\`\`

## 许可证

MIT
EOF
    
    echo -e "${GREEN}✅ Node 项目初始化完成${NC}"
}

# 初始化全栈项目
init_fullstack() {
    echo -e "${YELLOW}初始化全栈项目...${NC}"
    
    # 后端（Python）
    mkdir -p backend
    cd backend
    init_python
    cd ..
    
    # 前端（Node）
    mkdir -p frontend
    cd frontend
    init_node
    cd ..
    
    # 根目录 README
    cat > README.md << EOF
# $PROJECT_NAME

> 全栈项目

## 项目结构

\`\`\`
$PROJECT_NAME/
├── backend/      # Python 后端
├── frontend/     # Node.js 前端
└── README.md
\`\`\`

## 开发

### 后端

\`\`\`bash
cd backend
pip install -e .
python src/$PROJECT_NAME/main.py
\`\`\`

### 前端

\`\`\`bash
cd frontend
npm install
npm start
\`\`\`

## 许可证

MIT
EOF
    
    echo -e "${GREEN}✅ 全栈项目初始化完成${NC}"
}

# 主流程
main() {
    init_git
    
    case "$PROJECT_TYPE" in
        python)
            init_python
            ;;
        node)
            init_node
            ;;
        fullstack)
            init_fullstack
            ;;
        *)
            echo -e "${YELLOW}未知项目类型: $PROJECT_TYPE${NC}"
            echo "支持类型: python, node, fullstack"
            exit 1
            ;;
    esac
    
    # 创建初始提交
    git add .
    git commit -m "feat: 初始化项目结构

项目类型: $PROJECT_TYPE
项目名称: $PROJECT_NAME

Co-authored-by: 项目初始化脚本 <init@openclaw>"
    
    echo ""
    echo -e "${GREEN}=== 项目初始化完成！ ===${NC}"
    echo "项目位置: $(pwd)"
    echo ""
    echo "📋 后续步骤:"
    echo "1. cd $PROJECT_NAME"
    echo "2. 查看项目结构: ls -la"
    echo "3. 开始开发！"
    echo ""
}

# 运行主流程
main
