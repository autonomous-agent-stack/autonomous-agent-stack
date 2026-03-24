"""
简单测试脚本

测试自主 Agent 的核心功能
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import (
    TaskDecomposer,
    PlanningEngine,
    Executor,
    ReflectionModule,
    MemorySystem,
    AutonomousAgent,
    Task,
)


def test_task_decomposer():
    """测试任务分解器"""
    print("\n测试任务分解器...")

    decomposer = TaskDecomposer()
    task_tree = decomposer.decompose("分析数据")

    assert task_tree.description == "分析数据"
    assert len(task_tree.metadata.get("subtasks", [])) > 0

    print("✓ 任务分解器测试通过")


def test_planning_engine():
    """测试规划引擎"""
    print("\n测试规划引擎...")

    planner = PlanningEngine()
    task_tree = Task(id="root", description="测试任务", dependencies=[])

    task_tree.metadata = {
        "subtasks": [
            Task(id="task_1", description="步骤1", dependencies=[]),
            Task(id="task_2", description="步骤2", dependencies=["task_1"]),
        ]
    }

    plan = planner.generate_plan(task_tree)
    assert len(plan.tasks) > 0

    print("✓ 规划引擎测试通过")


def test_executor():
    """测试执行器"""
    print("\n测试执行器...")

    executor = Executor()

    class MockTool:
        def execute(self, input_data):
            return "success"

    executor.register_tool("mock", MockTool())

    task = {"id": "test", "description": "测试任务"}
    result = executor.execute(task, tools={"mock": MockTool()})

    assert result.status == "success"
    assert result.task_id == "test"

    print("✓ 执行器测试通过")


def test_memory_system():
    """测试记忆系统"""
    print("\n测试记忆系统...")

    memory = MemorySystem()

    # 存储记忆
    memory.store("key1", "value1", "short_term")
    memory.store("key2", "value2", "long_term")

    # 检索记忆
    item1 = memory.retrieve("key1")
    assert item1 is not None
    assert item1.value == "value1"

    # 搜索记忆
    results = memory.search("key", limit=10)
    assert len(results) > 0

    print("✓ 记忆系统测试通过")


def test_reflection_module():
    """测试反思模块"""
    print("\n测试反思模块...")

    from core import ExecutionResult

    reflection = ReflectionModule()

    results = [
        ExecutionResult(
            task_id="task_1",
            status="success",
            output="完成",
            error=None,
            execution_time=1.0,
            metadata={}
        ),
    ]

    assessment = reflection.assess(
        goal="测试目标",
        results=results,
        memory=MemorySystem()
    )

    assert assessment is not None
    assert isinstance(assessment.quality_score, float)

    print("✓ 反思模块测试通过")


def test_autonomous_agent():
    """测试自主 Agent"""
    print("\n测试自主 Agent...")

    agent = AutonomousAgent(verbose=False)

    # 注册简单工具
    class SimpleTool:
        def execute(self, input_data):
            return "done"

    agent.executor.register_tool("simple", SimpleTool())

    # 运行 Agent
    result = agent.run(
        goal="执行简单任务",
        tools={},
        constraints={"max_time": 1}
    )

    assert result is not None
    assert "goal" in result
    assert "iterations" in result

    print("✓ 自主 Agent 测试通过")


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🧪 运行自主 Agent 测试")
    print("="*60)

    try:
        test_task_decomposer()
        test_planning_engine()
        test_executor()
        test_memory_system()
        test_reflection_module()
        test_autonomous_agent()

        print("\n" + "="*60)
        print("✅ 所有测试通过！")
        print("="*60)

        return 0

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
