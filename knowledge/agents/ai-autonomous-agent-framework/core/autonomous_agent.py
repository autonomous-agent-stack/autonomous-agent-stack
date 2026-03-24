# knowledge/agents/ai-autonomous-agent-framework/core/autonomous_agent.py

"""
自主 AI Agent

能够自主分解任务、规划和执行、评估和修正
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .task_decomposer import TaskDecomposer, Task
from .planning_engine import PlanningEngine, Plan
from .executor import Executor, ExecutionResult
from .reflection_module import ReflectionModule, Assessment
from .memory_system import MemorySystem


@dataclass
class AgentState:
    """Agent 状态"""
    current_goal: str
    iteration: int
    task_tree: Optional[Task]
    plan: Optional[Plan]
    results: List[ExecutionResult]
    assessment: Optional[Assessment]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "current_goal": self.current_goal,
            "iteration": self.iteration,
            "has_task_tree": self.task_tree is not None,
            "has_plan": self.plan is not None,
            "results_count": len(self.results),
            "has_assessment": self.assessment is not None
        }


class AutonomousAgent:
    """
    自主 AI Agent

    能够自主分解任务、规划和执行、评估和修正
    """

    def __init__(
        self,
        llm_client=None,
        max_iterations: int = 10,
        verbose: bool = True
    ):
        """
        初始化自主 Agent

        Args:
            llm_client: LLM 客户端
            max_iterations: 最大迭代次数
            verbose: 是否打印详细信息
        """
        self.llm_client = llm_client
        self.max_iterations = max_iterations
        self.verbose = verbose

        # 初始化核心组件
        self.task_decomposer = TaskDecomposer(llm_client)
        self.planning_engine = PlanningEngine(llm_client)
        self.executor = Executor(llm_client)
        self.reflection = ReflectionModule(llm_client)
        self.memory = MemorySystem()

        # 当前状态
        self.state = None

    def run(
        self,
        goal: str,
        tools: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        运行自主 Agent

        Args:
            goal: 目标
            tools: 可用工具
            constraints: 约束条件

        Returns:
            执行结果字典
        """
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"🤖 自主 Agent 启动")
            print(f"目标: {goal}")
            print(f"{'='*60}\n")

        # 初始化状态
        self.state = AgentState(
            current_goal=goal,
            iteration=0,
            task_tree=None,
            plan=None,
            results=[],
            assessment=None
        )

        # 存储目标到记忆
        self.memory.store("goal", goal, "long_term")

        # 主循环
        while self.state.iteration < self.max_iterations:
            self.state.iteration += 1

            if self.verbose:
                print(f"\n--- 迭代 {self.state.iteration} ---")

            # 1. 任务分解（仅第一次或需要重新规划时）
            if self.state.task_tree is None:
                self._step_decompose()

            # 2. 生成计划
            if self.state.plan is None:
                self._step_plan(constraints)

            # 3. 执行计划
            self._step_execute(tools)

            # 4. 反思评估
            self._step_reflect()

            # 5. 判断是否完成
            if self._check_completion():
                break

            # 6. 修正计划
            if self.state.assessment and self.state.assessment.should_refine:
                self._step_refine()

        # 返回最终结果
        return self._get_final_result()

    def _step_decompose(self):
        """步骤 1: 任务分解"""
        if self.verbose:
            print("📋 分解任务...")

        self.state.task_tree = self.task_decomposer.decompose(
            self.state.current_goal,
            context=self.memory.get_context()
        )

        if self.verbose:
            print(f"  ✓ 任务分解完成")

    def _step_plan(self, constraints: Optional[Dict[str, Any]]):
        """步骤 2: 生成计划"""
        if self.verbose:
            print("📝 生成计划...")

        self.state.plan = self.planning_engine.generate_plan(
            self.state.task_tree,
            constraints=constraints
        )

        if self.verbose:
            print(f"  ✓ 计划生成完成")
            print(f"  预估时间: {self.state.plan.estimated_time:.2f} 小时")
            print(f"  预估成本: ${self.state.plan.estimated_cost:.2f}")

    def _step_execute(self, tools: Optional[Dict[str, Any]]):
        """步骤 3: 执行计划"""
        if self.verbose:
            print("⚙️ 执行计划...")

        iteration_results = []

        for task in self.state.plan.tasks:
            if self.verbose:
                print(f"  - {task.get('description', 'Unknown task')}")

            result = self.executor.execute(
                task=task,
                tools=tools or self.executor.tools,
                memory=self.memory
            )

            # 存储结果到记忆
            self.memory.store(
                result.task_id,
                result.to_dict(),
                "short_term"
            )

            iteration_results.append(result)

            if self.verbose:
                status_icon = "✅" if result.status == "success" else "❌"
                print(f"    {status_icon} {result.status} ({result.execution_time:.2f}s)")

        self.state.results.extend(iteration_results)

    def _step_reflect(self):
        """步骤 4: 反思评估"""
        if self.verbose:
            print("🔍 反思评估...")

        self.state.assessment = self.reflection.assess(
            goal=self.state.current_goal,
            results=self.state.results,
            memory=self.memory
        )

        if self.verbose:
            print(f"  ✓ 目标完成: {self.state.assessment.is_complete}")
            print(f"  ✓ 质量分数: {self.state.assessment.quality_score}/10")
            if self.state.assessment.issues:
                print(f"  ⚠️  问题: {', '.join(self.state.assessment.issues)}")

    def _check_completion(self) -> bool:
        """判断是否完成"""
        if not self.state.assessment:
            return False

        is_complete = self.state.assessment.is_complete
        quality_ok = self.state.assessment.quality_score >= 7

        if is_complete and quality_ok:
            if self.verbose:
                print("\n✨ 目标达成！")
            return True

        return False

    def _step_refine(self):
        """步骤 6: 修正计划"""
        if self.verbose:
            print("🔄 修正计划...")

        # 修正任务树
        self.state.task_tree = self.task_decomposer.refine(
            self.state.task_tree,
            feedback=self.state.assessment.feedback,
            memory=self.memory
        )

        # 修正计划
        self.state.plan = self.planning_engine.refine_plan(
            self.state.plan,
            feedback=self.state.assessment.feedback,
            memory=self.memory
        )

        if self.verbose:
            print(f"  ✓ 计划修正完成")
            if self.state.assessment.suggestions:
                print(f"  💡 建议: {', '.join(self.state.assessment.suggestions)}")

    def _get_final_result(self) -> Dict[str, Any]:
        """获取最终结果"""
        final_result = self.memory.get_final_result(self.state.current_goal)

        return {
            "goal": self.state.current_goal,
            "iterations": self.state.iteration,
            "result": final_result,
            "total_results": len(self.state.results),
            "final_assessment": self.state.assessment.to_dict() if self.state.assessment else None,
            "state": self.state.to_dict()
        }

    def get_memory(self) -> MemorySystem:
        """获取记忆系统"""
        return self.memory

    def get_state(self) -> AgentState:
        """获取当前状态"""
        return self.state

    def reset(self):
        """重置 Agent"""
        self.state = None
        self.memory.clear_working_memory()


if __name__ == "__main__":
    # 创建 Agent
    agent = AutonomousAgent(verbose=True)

    # 定义工具（示例）
    tools = {
        "web_search": lambda x: f"搜索结果: {x}",
        "file_io": lambda x: f"文件操作: {x}",
    }

    # 注册工具到执行器
    for name, tool in tools.items():
        agent.executor.register_tool(name, tool)

    # 运行 Agent
    result = agent.run(
        goal="分析某公司的财务报告并生成投资建议",
        tools=tools,
        constraints={
            "max_time": 10,
            "max_cost": 100
        }
    )

    print(f"\n{'='*60}")
    print("最终结果:")
    print(f"{'='*60}")
    print(f"目标: {result['goal']}")
    print(f"迭代次数: {result['iterations']}")
    print(f"总执行任务数: {result['total_results']}")
    print(f"结果: {result['result']}")
    if result['final_assessment']:
        print(f"最终质量分数: {result['final_assessment']['quality_score']}/10")
