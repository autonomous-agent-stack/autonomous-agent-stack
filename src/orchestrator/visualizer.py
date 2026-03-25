"""
可视化工具 - 极简监控看板

这个模块提供 MASFactory 的可视化监控功能，
支持实时渲染各个智能体节点的运转状态。
"""

import json
from typing import Dict, Any, List
from datetime import datetime


class Visualizer:
    """
    可视化器
    
    将图结构导出为可视化格式，支持多种渲染引擎。
    """
    
    def __init__(self, theme: str = "light"):
        """
        初始化可视化器
        
        Args:
            theme: 主题（light | dark）
        """
        self.theme = theme
        self.node_colors = {
            "planner": "#4A90E2",
            "generator": "#7B68EE",
            "executor": "#50C878",
            "evaluator": "#FF6B6B"
        }
    
    def export_to_mermaid(self, graph_structure: Dict[str, Any]) -> str:
        """
        导出为 Mermaid 图
        
        Args:
            graph_structure: 图结构（来自 Graph.to_dict()）
        
        Returns:
            Mermaid 代码
        """
        mermaid_code = "graph TD\n"
        
        # 添加节点
        for node in graph_structure["nodes"]:
            node_id = node["id"]
            node_type = node["type"]
            color = self.node_colors.get(node_type, "#FFFFFF")
            
            mermaid_code += f"    {node_id}[{node_id}<br/>{node_type}]:::{node_type}\n"
        
        # 添加边
        for edge in graph_structure["edges"]:
            source = edge["source"]
            target = edge["target"]
            condition = edge.get("condition")
            
            if condition:
                mermaid_code += f"    {source} -->|{condition}| {target}\n"
            else:
                mermaid_code += f"    {source} --> {target}\n"
        
        # 添加样式
        mermaid_code += "\n    classDef planner fill:#4A90E2,stroke:#2E5C8A,color:#FFFFFF\n"
        mermaid_code += "    classDef generator fill:#7B68EE,stroke:#5A4E9E,color:#FFFFFF\n"
        mermaid_code += "    classDef executor fill:#50C878,stroke:#2E8B57,color:#FFFFFF\n"
        mermaid_code += "    classDef evaluator fill:#FF6B6B,stroke:#CC5555,color:#FFFFFF\n"
        
        return mermaid_code
    
    def export_to_json(self, graph_structure: Dict[str, Any]) -> str:
        """
        导出为 JSON（用于前端渲染）
        
        Args:
            graph_structure: 图结构
        
        Returns:
            JSON 字符串
        """
        visual_data = {
            "theme": self.theme,
            "timestamp": datetime.now().isoformat(),
            "graph": graph_structure
        }
        
        return json.dumps(visual_data, indent=2, ensure_ascii=False)
    
    def generate_html_dashboard(
        self,
        graph_structure: Dict[str, Any],
        evaluation_data: Dict[str, Any] = None
    ) -> str:
        """
        生成 HTML 监控看板
        
        Args:
            graph_structure: 图结构
            evaluation_data: 评估数据（可选）
        
        Returns:
            HTML 代码
        """
        # 基础样式（浅色主题）
        bg_color = "#F8F9FA" if self.theme == "light" else "#1A1A1A"
        text_color = "#2C3E50" if self.theme == "light" else "#ECF0F1"
        
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autonomous Agent Stack - 监控看板</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background-color: {bg_color};
            color: {text_color};
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .dashboard {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
        }}
        .graph-panel {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .stats-panel {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .node-status {{
            display: flex;
            align-items: center;
            margin: 10px 0;
            padding: 10px;
            border-radius: 4px;
            background: #F8F9FA;
        }}
        .status-indicator {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 10px;
        }}
        .status-completed {{ background-color: #50C878; }}
        .status-running {{ background-color: #4A90E2; }}
        .status-failed {{ background-color: #FF6B6B; }}
        .status-pending {{ background-color: #95A5A6; }}
        .mermaid {{
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Autonomous Agent Stack</h1>
            <p>实时监控看板 | 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="dashboard">
            <div class="graph-panel">
                <h2>📊 图编排视图</h2>
                <div class="mermaid">
                    {self.export_to_mermaid(graph_structure)}
                </div>
            </div>
            
            <div class="stats-panel">
                <h2>📈 节点状态</h2>
"""
        
        # 添加节点状态
        for node in graph_structure["nodes"]:
            node_id = node["id"]
            node_type = node["type"]
            status = node["status"]
            
            status_class = f"status-{status}"
            html += f"""
                <div class="node-status">
                    <div class="status-indicator {status_class}"></div>
                    <div>
                        <strong>{node_id}</strong><br/>
                        <small>{node_type} | {status}</small>
                    </div>
                </div>
"""
        
        # 添加评估数据（如果有）
        if evaluation_data:
            html += f"""
                <h2>🎯 评估结果</h2>
                <div class="node-status">
                    <div>
                        <strong>分数: {evaluation_data.get('score', 'N/A')}</strong><br/>
                        <small>决策: {evaluation_data.get('decision', 'N/A')}</small>
                    </div>
                </div>
"""
        
        html += """
            </div>
        </div>
    </div>
    
    <script>
        mermaid.initialize({ startOnLoad: true, theme: 'default' });
    </script>
</body>
</html>
"""
        
        return html


# 使用示例
def main():
    """演示可视化工具"""
    print("=" * 60)
    print("🎨 可视化工具演示")
    print("=" * 60)
    
    # 创建示例图结构
    graph_structure = {
        "graph_id": "minimal_loop",
        "nodes": [
            {"id": "planner", "type": "planner", "status": "completed"},
            {"id": "generator", "type": "generator", "status": "completed"},
            {"id": "executor", "type": "executor", "status": "completed"},
            {"id": "evaluator", "type": "evaluator", "status": "completed"}
        ],
        "edges": [
            {"source": "planner", "target": "generator"},
            {"source": "generator", "target": "executor"},
            {"source": "executor", "target": "evaluator"},
            {"source": "evaluator", "target": "generator", "condition": "decision == 'retry'"}
        ]
    }
    
    # 创建可视化器
    visualizer = Visualizer(theme="light")
    
    # 导出为 Mermaid
    mermaid_code = visualizer.export_to_mermaid(graph_structure)
    print("\n📊 Mermaid 图:")
    print(mermaid_code)
    
    # 生成 HTML 看板
    html_dashboard = visualizer.generate_html_dashboard(
        graph_structure,
        evaluation_data={"score": 0.95, "decision": "continue"}
    )
    
    # 保存 HTML
    with open("dashboard.html", "w", encoding="utf-8") as f:
        f.write(html_dashboard)
    
    print("\n✅ HTML 看板已保存到 dashboard.html")


if __name__ == "__main__":
    main()
