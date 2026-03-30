#!/bin/bash

# OpenClaw 一键部署脚本
# 用途: 自动化部署 OpenClaw 到各种环境
# 作者: 持续工作 Agent
# 日期: 2026-03-27

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 配置变量
OPENCLAW_VERSION="2026.3.23-2"
INSTALL_DIR="$HOME/.openclaw"
CONFIG_DIR="$INSTALL_DIR/config"
LOG_DIR="$INSTALL_DIR/logs"

echo -e "${GREEN}=== OpenClaw 一键部署 ===${NC}"
echo "版本: $OPENCLAW_VERSION"
echo "安装目录: $INSTALL_DIR"
echo ""

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macOS"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Linux"
    else
        echo "Unknown"
    fi
}

OS=$(detect_os)
echo -e "${GREEN}检测到操作系统: $OS${NC}"

# 检查依赖
check_dependencies() {
    echo -e "${YELLOW}检查依赖...${NC}"
    
    # 检查 Node.js
    if ! command -v node &> /dev/null; then
        echo -e "${RED}❌ Node.js 未安装${NC}"
        echo "请先安装 Node.js: https://nodejs.org/"
        exit 1
    fi
    
    NODE_VERSION=$(node -v)
    echo -e "${GREEN}✅ Node.js $NODE_VERSION${NC}"
    
    # 检查 npm
    if ! command -v npm &> /dev/null; then
        echo -e "${RED}❌ npm 未安装${NC}"
        exit 1
    fi
    
    NPM_VERSION=$(npm -v)
    echo -e "${GREEN}✅ npm $NPM_VERSION${NC}"
    
    # 检查 Git
    if ! command -v git &> /dev/null; then
        echo -e "${RED}❌ Git 未安装${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Git $(git --version | awk '{print $3}')${NC}"
}

# 创建目录结构
create_directories() {
    echo -e "${YELLOW}创建目录结构...${NC}"
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$INSTALL_DIR/skills"
    mkdir -p "$INSTALL_DIR/workspace"
    
    echo -e "${GREEN}✅ 目录创建完成${NC}"
}

# 安装 OpenClaw
install_openclaw() {
    echo -e "${YELLOW}安装 OpenClaw...${NC}"
    
    # 使用 npm 全局安装
    npm install -g openclaw@$OPENCLAW_VERSION
    
    echo -e "${GREEN}✅ OpenClaw 安装完成${NC}"
}

# 生成配置文件
generate_config() {
    echo -e "${YELLOW}生成配置文件...${NC}"
    
    # 主配置文件
    cat > "$CONFIG_DIR/openclaw.json" << EOF
{
  "version": "$OPENCLAW_VERSION",
  "gateway": {
    "host": "127.0.0.1",
    "port": 443
  },
  "models": {
    "main": {
      "provider": "zhipuai",
      "model": "glm-5",
      "api_key": "\${ZHIPUAI_API_KEY}"
    }
  },
  "agents": {
    "default": {
      "model": "main",
      "temperature": 0.7,
      "max_tokens": 4096
    }
  }
}
EOF
    
    echo -e "${GREEN}✅ 配置文件生成完成${NC}"
}

# 设置环境变量
setup_environment() {
    echo -e "${YELLOW}设置环境变量...${NC}"
    
    # 添加到 shell 配置
    SHELL_CONFIG="$HOME/.zshrc"
    if [ ! -f "$SHELL_CONFIG" ]; then
        SHELL_CONFIG="$HOME/.bashrc"
    fi
    
    # 检查是否已添加
    if ! grep -q "OPENCLAW_HOME" "$SHELL_CONFIG"; then
        cat >> "$SHELL_CONFIG" << EOF

# OpenClaw
export OPENCLAW_HOME="$INSTALL_DIR"
export PATH="\$OPENCLAW_HOME/bin:\$PATH"
EOF
        
        echo -e "${GREEN}✅ 环境变量已添加到 $SHELL_CONFIG${NC}"
        echo -e "${YELLOW}请运行: source $SHELL_CONFIG${NC}"
    else
        echo -e "${GREEN}✅ 环境变量已存在${NC}"
    fi
}

# 验证安装
verify_installation() {
    echo -e "${YELLOW}验证安装...${NC}"
    
    # 检查 openclaw 命令
    if command -v openclaw &> /dev/null; then
        VERSION=$(openclaw --version)
        echo -e "${GREEN}✅ OpenClaw $VERSION 安装成功${NC}"
    else
        echo -e "${RED}❌ OpenClaw 安装失败${NC}"
        exit 1
    fi
}

# 显示后续步骤
show_next_steps() {
    echo ""
    echo -e "${GREEN}=== 安装完成！ ===${NC}"
    echo ""
    echo "📋 后续步骤:"
    echo ""
    echo "1. 设置 API Key:"
    echo "   export ZHIPUAI_API_KEY='your-api-key'"
    echo ""
    echo "2. 启动 Gateway:"
    echo "   openclaw gateway start"
    echo ""
    echo "3. 测试连接:"
    echo "   openclaw status"
    echo ""
    echo "4. 查看日志:"
    echo "   tail -f $LOG_DIR/openclaw.log"
    echo ""
    echo "📚 文档: https://docs.openclaw.ai"
    echo "💬 社区: https://discord.com/invite/clawd"
    echo ""
}

# 主流程
main() {
    check_dependencies
    create_directories
    install_openclaw
    generate_config
    setup_environment
    verify_installation
    show_next_steps
}

# 运行主流程
main
