#!/bin/bash
# OpenClaw Skill 快速安装脚本
# 基于 OpenClaw Master Skills 项目

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 技能目录
SKILLS_DIR="$HOME/.openclaw/workspace/skills"
MASTER_SKILLS_REPO="https://github.com/LeoYeAI/openclaw-master-skills.git"

# 打印帮助
print_help() {
    echo -e "${BLUE}OpenClaw Skill 安装器${NC}"
    echo ""
    echo "用法:"
    echo "  $0 list              # 列出所有可用 skills"
    echo "  $0 search <关键词>    # 搜索 skills"
    echo "  $0 install <skill>   # 安装 skill"
    echo "  $0 update            # 更新 skill 仓库"
    echo ""
    echo "示例:"
    echo "  $0 list"
    echo "  $0 search browser"
    echo "  $0 install agent-browser"
}

# 检查依赖
check_dependencies() {
    if ! command -v git &> /dev/null; then
        echo -e "${YELLOW}错误: 未安装 git${NC}"
        exit 1
    fi
}

# 初始化仓库
init_repo() {
    if [ ! -d "/tmp/openclaw-master-skills" ]; then
        echo -e "${BLUE}正在克隆 OpenClaw Master Skills 仓库...${NC}"
        git clone "$MASTER_SKILLS_REPO" /tmp/openclaw-master-skills
    else
        echo -e "${BLUE}仓库已存在，正在更新...${NC}"
        cd /tmp/openclaw-master-skills && git pull
    fi
}

# 列出所有 skills
list_skills() {
    init_repo
    echo -e "${GREEN}可用的 Skills:${NC}"
    echo ""
    cd /tmp/openclaw-master-skills/skills
    ls -1 | head -50
    echo ""
    echo -e "${YELLOW}提示: 共 $(ls -1 | wc -l) 个 skills${NC}"
}

# 搜索 skills
search_skills() {
    local keyword="$1"
    init_repo
    echo -e "${GREEN}搜索结果 (关键词: $keyword):${NC}"
    echo ""
    cd /tmp/openclaw-master-skills/skills
    ls -1 | grep -i "$keyword" || echo "未找到匹配的 skills"
}

# 安装 skill
install_skill() {
    local skill_name="$1"
    
    # 创建 skills 目录
    mkdir -p "$SKILLS_DIR"
    
    # 检查 skill 是否存在
    if [ ! -d "/tmp/openclaw-master-skills/skills/$skill_name" ]; then
        echo -e "${YELLOW}错误: Skill '$skill_name' 不存在${NC}"
        echo "使用 '$0 list' 查看所有可用 skills"
        exit 1
    fi
    
    # 复制 skill
    echo -e "${BLUE}正在安装 $skill_name...${NC}"
    cp -r "/tmp/openclaw-master-skills/skills/$skill_name" "$SKILLS_DIR/"
    
    echo -e "${GREEN}✅ $skill_name 安装成功！${NC}"
    echo -e "位置: $SKILLS_DIR/$skill_name"
}

# 主函数
main() {
    check_dependencies
    
    case "${1:-help}" in
        list)
            list_skills
            ;;
        search)
            if [ -z "$2" ]; then
                echo "错误: 请提供搜索关键词"
                exit 1
            fi
            search_skills "$2"
            ;;
        install)
            if [ -z "$2" ]; then
                echo "错误: 请指定要安装的 skill"
                exit 1
            fi
            install_skill "$2"
            ;;
        update)
            init_repo
            echo -e "${GREEN}✅ 仓库已更新${NC}"
            ;;
        help|--help|-h)
            print_help
            ;;
        *)
            echo "错误: 未知命令 '$1'"
            print_help
            exit 1
            ;;
    esac
}

main "$@"
