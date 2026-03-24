#!/bin/bash

# AI 知识图谱 - 自动化脚本集
# 版本: 1.0
# 创建时间: 2026-03-24

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

# 脚本 1: 生成概念摘要
generate_concept_summary() {
    log_info "生成概念摘要..."
    
    local concepts_dir="concepts"
    local output_file="knowledge/summaries/concept-summaries.md"
    
    mkdir -p "$(dirname "$output_file")"
    
    echo "# AI 知识图谱 - 概念摘要" > "$output_file"
    echo "" >> "$output_file"
    echo "> 自动生成时间: $(date '+%Y-%m-%d %H:%M:%S')" >> "$output_file"
    echo "" >> "$output_file"
    
    for file in "$concepts_dir"/*.md; do
        if [ -f "$file" ]; then
            local concept_name=$(basename "$file" .md)
            log_info "处理概念: $concept_name"
            
            echo "## $concept_name" >> "$output_file"
            echo "" >> "$output_file"
            
            # 提取定义（第一段）
            grep -A 3 "^## 定义" "$file" | head -4 >> "$output_file" || echo "无定义" >> "$output_file"
            echo "" >> "$output_file"
        fi
    done
    
    log_success "概念摘要已生成: $output_file"
}

# 脚本 2: 检查双链完整性
check_double_links() {
    log_info "检查双链完整性..."
    
    local concepts_dir="concepts"
    local broken_links=0
    
    for file in "$concepts_dir"/*.md; do
        if [ -f "$file" ]; then
            # 提取所有双链
            grep -o '\[\[.*\]\]' "$file" | while read -r link; do
                # 提取概念名
                concept=$(echo "$link" | sed 's/\[\[\(.*\)\]\]/\1/')
                
                # 检查文件是否存在
                if [ ! -f "$concepts_dir/$concept.md" ]; then
                    log_warning "断链: $link (在 $file)"
                    ((broken_links++))
                fi
            done
        fi
    done
    
    if [ $broken_links -eq 0 ]; then
        log_success "所有双链完整"
    else
        log_error "发现 $broken_links 个断链"
    fi
}

# 脚本 3: 生成知识图谱可视化
generate_knowledge_graph() {
    log_info "生成知识图谱可视化..."
    
    local output_file="knowledge/visualizations/knowledge-graph.html"
    
    mkdir -p "$(dirname "$output_file")"
    
    cat > "$output_file" << 'EOF'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 知识图谱</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
            background: #f0f0f0;
        }
        svg {
            width: 100%;
            height: 100vh;
        }
        .node {
            cursor: pointer;
        }
        .node circle {
            stroke: #fff;
            stroke-width: 2px;
        }
        .node text {
            font-size: 12px;
            pointer-events: none;
        }
        .link {
            stroke: #999;
            stroke-opacity: 0.6;
        }
    </style>
</head>
<body>
    <svg></svg>
    <script>
        // 数据将从 JSON 加载
        const data = {
            nodes: [
                {id: "llm", name: "大语言模型", category: "基础概念"},
                {id: "ai-agent", name: "AI 代理", category: "核心应用"},
                {id: "prompt-engineering", name: "提示词工程", category: "核心应用"},
                {id: "rag", name: "RAG", category: "技术架构"},
                {id: "function-calling", name: "函数调用", category: "核心能力"}
            ],
            links: [
                {source: "llm", target: "ai-agent"},
                {source: "llm", target: "prompt-engineering"},
                {source: "ai-agent", target: "function-calling"},
                {source: "ai-agent", target: "rag"}
            ]
        };
        
        const svg = d3.select("svg");
        const width = +svg.attr("width") || window.innerWidth;
        const height = +svg.attr("height") || window.innerHeight;
        
        const simulation = d3.forceSimulation(data.nodes)
            .force("link", d3.forceLink(data.links).id(d => d.id))
            .force("charge", d3.forceManyBody().strength(-400))
            .force("center", d3.forceCenter(width / 2, height / 2));
        
        const link = svg.append("g")
            .selectAll("line")
            .data(data.links)
            .enter().append("line")
            .attr("class", "link")
            .attr("stroke-width", 2);
        
        const node = svg.append("g")
            .selectAll("g")
            .data(data.nodes)
            .enter().append("g")
            .attr("class", "node")
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));
        
        node.append("circle")
            .attr("r", 20)
            .attr("fill", d => {
                const colors = {
                    "基础概念": "#4A90E2",
                    "核心应用": "#7ED321",
                    "技术架构": "#F5A623",
                    "核心能力": "#D0021B"
                };
                return colors[d.category] || "#999";
            });
        
        node.append("text")
            .attr("dy", 3)
            .attr("text-anchor", "middle")
            .text(d => d.name);
        
        simulation.on("tick", () => {
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
            
            node.attr("transform", d => `translate(${d.x},${d.y})`);
        });
        
        function dragstarted(event) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }
        
        function dragged(event) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }
        
        function dragended(event) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }
    </script>
</body>
</html>
EOF
    
    log_success "知识图谱可视化已生成: $output_file"
}

# 脚本 4: 统计分析
generate_statistics() {
    log_info "生成统计分析..."
    
    local output_file="knowledge/statistics/statistics-report.md"
    
    mkdir -p "$(dirname "$output_file")"
    
    local total_files=$(find concepts -name "*.md" | wc -l | xargs)
    local total_lines=$(find concepts -name "*.md" -exec wc -l {} + | tail -1 | awk '{print $1}')
    local total_size=$(du -sh concepts | awk '{print $1}')
    
    cat > "$output_file" << EOF
# AI 知识图谱 - 统计报告

> 生成时间: $(date '+%Y-%m-%d %H:%M:%S')

## 📊 文件统计

| 维度 | 数值 |
|------|------|
| **概念文件** | $total_files 个 |
| **总行数** | $total_lines 行 |
| **总大小** | $total_size |
| **平均文件** | $((total_lines / total_files)) 行 |

## 📝 内容统计

EOF
    
    # 统计每个文件的行数
    for file in concepts/*.md; do
        if [ -f "$file" ]; then
            local filename=$(basename "$file")
            local lines=$(wc -l < "$file")
            echo "- $filename: $lines 行" >> "$output_file"
        fi
    done
    
    log_success "统计分析已生成: $output_file"
}

# 脚本 5: 备份知识库
backup_knowledge_base() {
    log_info "备份知识库..."
    
    local backup_dir="backups/$(date '+%Y%m%d_%H%M%S')"
    mkdir -p "$backup_dir"
    
    # 备份概念文件
    cp -r concepts "$backup_dir/"
    
    # 备份知识文件
    cp -r knowledge "$backup_dir/" 2>/dev/null || true
    
    # 创建备份清单
    cat > "$backup_dir/BACKUP_MANIFEST.md" << EOF
# 备份清单

- 备份时间: $(date '+%Y-%m-%d %H:%M:%S')
- 备份内容:
  - concepts/ (概念文件)
  - knowledge/ (知识文件)
- 备份大小: $(du -sh "$backup_dir" | awk '{print $1}')
EOF
    
    log_success "知识库已备份: $backup_dir"
}

# 主菜单
show_menu() {
    echo ""
    echo "AI 知识图谱 - 自动化脚本集"
    echo "============================"
    echo ""
    echo "1. 生成概念摘要"
    echo "2. 检查双链完整性"
    echo "3. 生成知识图谱可视化"
    echo "4. 生成统计分析"
    echo "5. 备份知识库"
    echo "6. 运行所有脚本"
    echo "0. 退出"
    echo ""
    read -p "请选择 (0-6): " choice
    
    case $choice in
        1) generate_concept_summary ;;
        2) check_double_links ;;
        3) generate_knowledge_graph ;;
        4) generate_statistics ;;
        5) backup_knowledge_base ;;
        6)
            generate_concept_summary
            check_double_links
            generate_knowledge_graph
            generate_statistics
            backup_knowledge_base
            ;;
        0) exit 0 ;;
        *) log_error "无效选择" ;;
    esac
}

# 主程序
main() {
    if [ $# -eq 0 ]; then
        while true; do
            show_menu
        done
    else
        case $1 in
            summary) generate_concept_summary ;;
            links) check_double_links ;;
            graph) generate_knowledge_graph ;;
            stats) generate_statistics ;;
            backup) backup_knowledge_base ;;
            all)
                generate_concept_summary
                check_double_links
                generate_knowledge_graph
                generate_statistics
                backup_knowledge_base
                ;;
            *)
                log_error "未知命令: $1"
                echo "用法: $0 [summary|links|graph|stats|backup|all]"
                exit 1
                ;;
        esac
    fi
}

main "$@"
