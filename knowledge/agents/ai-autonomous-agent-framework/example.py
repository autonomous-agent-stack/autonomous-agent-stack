#!/usr/bin/env python3
"""
示例：运行完整的自主 Agent

演示如何使用自主 Agent 完成一个复杂任务
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import AutonomousAgent


class SimpleTool:
    """简单工具示例"""
    def execute(self, input_data):
        operation = input_data.get("operation", "")

        if operation == "search":
            query = input_data.get("query", "")
            return f"搜索 '{query}' 的结果..."

        elif operation == "analyze":
            data = input_data.get("data", "")
            return f"分析结果: 处理了 {len(str(data))} 字符"

        elif operation == "generate":
            topic = input_data.get("topic", "")
            return f"生成关于 {topic} 的内容..."

        else:
            return f"执行操作: {operation}"


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🤖 自主 Agent 示例")
    print("="*60)

    # 创建 Agent
    agent = AutonomousAgent(verbose=True)

    # 注册工具
    agent.executor.register_tool("simple_tool", SimpleTool())

    # 运行 Agent
    result = agent.run(
        goal="完成一个简单的任务：搜索信息、分析数据、生成报告",
        tools={},
        constraints={
            "max_time": 5,
            "max_cost": 10
        }
    )

    # 打印结果
    print("\n" + "="*60)
    print("最终结果")
    print("="*60)
    print(f"目标: {result['goal']}")
    print(f"迭代次数: {result['iterations']}")
    print(f"总执行任务数: {result['total_results']}")
    print(f"结果: {result['result']}")
    if result['final_assessment']:
        print(f"最终质量分数: {result['final_assessment']['quality_score']}/10")

    # 导出记忆
    memory_file = "agent_memory.json"
    agent.get_memory().export(memory_file)
    print(f"\n记忆已导出到: {memory_file}")

    # 清理
    if os.path.exists(memory_file):
        os.remove(memory_file)
        print("清理临时文件完成。")


if __name__ == "__main__":
    main()
