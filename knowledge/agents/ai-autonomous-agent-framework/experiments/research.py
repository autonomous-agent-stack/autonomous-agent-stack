# knowledge/agents/ai-autonomous-agent-framework/experiments/research.py

"""
研究实验

演示自主 Agent 如何执行学术研究任务
"""

import os
import sys

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import AutonomousAgent


class ResearchAgent(AutonomousAgent):
    """研究专用 Agent"""

    def __init__(self):
        super().__init__(verbose=True)

        # 注册研究工具
        self._register_research_tools()

    def _register_research_tools(self):
        """注册研究工具"""

        class ResearchTool:
            """研究工具基类"""
            def execute(self, input_data):
                pass

        class SearchLiteratureTool(ResearchTool):
            """搜索文献工具"""
            def execute(self, input_data):
                query = input_data.get("query", "")
                num_results = input_data.get("num_results", 5)

                try:
                    # 模拟搜索结果
                    results = [
                        {
                            "title": f"Paper {i+1} on {query}",
                            "authors": [f"Author {i}"],
                            "year": 2024 - i,
                            "abstract": f"This paper discusses {query} in detail..."
                        }
                        for i in range(min(num_results, 5))
                    ]

                    return {
                        "status": "success",
                        "query": query,
                        "results_count": len(results),
                        "results": results,
                        "message": f"找到 {len(results)} 篇相关论文"
                    }
                except Exception as e:
                    return {"status": "failed", "error": str(e)}

        class SummarizeFindingsTool(ResearchTool):
            """总结发现工具"""
            def execute(self, input_data):
                findings = input_data.get("findings", [])
                topic = input_data.get("topic", "")

                try:
                    # 简化的总结逻辑
                    summary = f"关于 {topic} 的研究总结:\n\n"
                    for i, finding in enumerate(findings, 1):
                        title = finding.get("title", "Unknown")
                        year = finding.get("year", "Unknown")
                        summary += f"{i}. {title} ({year})\n"

                    return {
                        "status": "success",
                        "summary": summary,
                        "num_findings": len(findings),
                        "message": f"总结 {len(findings)} 篇论文"
                    }
                except Exception as e:
                    return {"status": "failed", "error": str(e)}

        class GenerateReportTool(ResearchTool):
            """生成报告工具"""
            def execute(self, input_data):
                summary = input_data.get("summary", "")
                topic = input_data.get("topic", "")

                try:
                    report = f"""# 研究报告: {topic}

## 执行摘要

本研究对 {topic} 进行了深入分析...

## 关键发现

{summary}

## 结论

基于以上研究发现，我们得出以下结论...

## 参考文献

此处列出相关文献...
"""

                    return {
                        "status": "success",
                        "report": report,
                        "length": len(report),
                        "message": "成功生成研究报告"
                    }
                except Exception as e:
                    return {"status": "failed", "error": str(e)}

        # 注册工具
        self.executor.register_tool("search_literature", SearchLiteratureTool())
        self.executor.register_tool("summarize_findings", SummarizeFindingsTool())
        self.executor.register_tool("generate_report", GenerateReportTool())


def run_research_experiment():
    """运行研究实验"""
    print("\n" + "="*60)
    print("🔬 研究实验")
    print("="*60)

    # 创建 Agent
    agent = ResearchAgent()

    # 运行 Agent
    result = agent.run(
        goal="研究 AI Agent 的最新进展并生成研究报告",
        tools={},
        constraints={"max_time": 4, "max_cost": 40}
    )

    return result


if __name__ == "__main__":
    result = run_research_experiment()

    print("\n实验结果:")
    print(f"  - 迭代次数: {result['iterations']}")
    print(f"  - 总执行任务数: {result['total_results']}")
    print(f"  - 最终质量分数: {result['final_assessment']['quality_score']}/10")
