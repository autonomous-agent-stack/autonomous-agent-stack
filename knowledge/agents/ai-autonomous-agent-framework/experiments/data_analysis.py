# knowledge/agents/ai-autonomous-agent-framework/experiments/data_analysis.py

"""
数据分析实验

演示自主 Agent 如何执行数据分析任务
"""

import os
import sys

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import AutonomousAgent


class DataAnalysisAgent(AutonomousAgent):
    """数据分析专用 Agent"""

    def __init__(self):
        super().__init__(verbose=True)

        # 注册数据分析工具
        self._register_data_tools()

    def _register_data_tools(self):
        """注册数据分析工具"""

        class DataTool:
            """数据分析工具基类"""
            def execute(self, input_data):
                pass

        class LoadCSVTool(DataTool):
            """加载 CSV 工具"""
            def execute(self, input_data):
                filepath = input_data.get("filepath")
                try:
                    # 模拟读取 CSV
                    return {
                        "status": "success",
                        "rows": 100,
                        "columns": 5,
                        "message": f"成功加载 {filepath}"
                    }
                except Exception as e:
                    return {"status": "failed", "error": str(e)}

        class AnalyzeTrendTool(DataTool):
            """分析趋势工具"""
            def execute(self, input_data):
                try:
                    return {
                        "status": "success",
                        "trend": "上升趋势",
                        "growth_rate": 0.15,
                        "message": "数据呈上升趋势，增长率为 15%"
                    }
                except Exception as e:
                    return {"status": "failed", "error": str(e)}

        class VisualizeTool(DataTool):
            """可视化工具"""
            def execute(self, input_data):
                try:
                    return {
                        "status": "success",
                        "output_file": "trend_chart.png",
                        "message": "成功生成趋势图表"
                    }
                except Exception as e:
                    return {"status": "failed", "error": str(e)}

        # 注册工具
        self.executor.register_tool("load_csv", LoadCSVTool())
        self.executor.register_tool("analyze_trend", AnalyzeTrendTool())
        self.executor.register_tool("visualize", VisualizeTool())


def run_data_analysis_experiment():
    """运行数据分析实验"""
    print("\n" + "="*60)
    print("📊 数据分析实验")
    print("="*60)

    # 创建 Agent
    agent = DataAnalysisAgent()

    # 运行 Agent
    result = agent.run(
        goal="分析销售数据并生成趋势可视化",
        tools={},
        constraints={"max_time": 5, "max_cost": 50}
    )

    return result


if __name__ == "__main__":
    result = run_data_analysis_experiment()

    print("\n实验结果:")
    print(f"  - 迭代次数: {result['iterations']}")
    print(f"  - 总执行任务数: {result['total_results']}")
    print(f"  - 最终质量分数: {result['final_assessment']['quality_score']}/10")
