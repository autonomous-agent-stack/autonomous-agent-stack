# knowledge/agents/ai-autonomous-agent-framework/core/executor.py

"""
执行器

执行具体任务并返回结果
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json
import time


@dataclass
class ExecutionResult:
    """执行结果"""
    task_id: str
    status: str  # success, failed, partial
    output: Any
    error: Optional[str]
    execution_time: float
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "output": self.output,
            "error": self.error,
            "execution_time": self.execution_time,
            "metadata": self.metadata
        }


class Executor:
    """
    执行器

    执行具体任务并返回结果
    """

    def __init__(self, llm_client=None):
        """
        初始化执行器

        Args:
            llm_client: LLM 客户端，用于智能执行
        """
        self.llm_client = llm_client
        self.tools = {}

    def register_tool(self, name: str, tool):
        """
        注册工具

        Args:
            name: 工具名称
            tool: 工具对象
        """
        self.tools[name] = tool

    def execute(
        self,
        task: Dict[str, Any],
        tools: Optional[Dict[str, Any]] = None,
        memory: Optional['MemorySystem'] = None
    ) -> ExecutionResult:
        """
        执行任务

        Args:
            task: 任务字典
            tools: 可用工具
            memory: 记忆系统

        Returns:
            执行结果
        """
        tools = tools or self.tools
        memory = memory or {}

        task_id = task.get("id", "unknown")
        description = task.get("description", "")

        start_time = time.time()

        try:
            # 使用 LLM 决定执行策略
            if self.llm_client:
                result = self._llm_execute(task, tools, memory)
            else:
                result = self._rule_based_execute(task, tools, memory)

            execution_time = time.time() - start_time

            return ExecutionResult(
                task_id=task_id,
                status="success",
                output=result,
                error=None,
                execution_time=execution_time,
                metadata={"description": description}
            )

        except Exception as e:
            execution_time = time.time() - start_time

            return ExecutionResult(
                task_id=task_id,
                status="failed",
                output=None,
                error=str(e),
                execution_time=execution_time,
                metadata={"description": description}
            )

    def _llm_execute(
        self,
        task: Dict[str, Any],
        tools: Dict[str, Any],
        memory: 'MemorySystem'
    ) -> Any:
        """使用 LLM 进行智能执行"""
        prompt = self._build_execution_prompt(task, tools, memory)

        response = self.llm_client.generate(prompt)

        # 解析是否需要调用工具
        action = self._parse_action(response)

        if action and action.get("tool"):
            tool_name = action["tool"]
            if tool_name in tools:
                tool_result = tools[tool_name].execute(action.get("input", {}))
                # 将工具结果反馈给 LLM
                refined_prompt = f"{prompt}\n\n工具结果: {tool_result}\n\n请基于工具结果生成最终答案。"
                response = self.llm_client.generate(refined_prompt)

        return response

    def _rule_based_execute(
        self,
        task: Dict[str, Any],
        tools: Dict[str, Any],
        memory: 'MemorySystem'
    ) -> Any:
        """规则基执行"""
        description = task.get("description", "").lower()

        # 简单的关键词匹配
        if "搜索" in description or "search" in description:
            return self._execute_search(task, tools, memory)
        elif "文件" in description or "file" in description:
            return self._execute_file(task, tools, memory)
        elif "分析" in description or "analyze" in description:
            return self._execute_analysis(task, tools, memory)
        elif "生成" in description or "generate" in description:
            return self._execute_generation(task, tools, memory)
        else:
            return f"执行任务: {task.get('description')}"

    def _execute_search(
        self,
        task: Dict[str, Any],
        tools: Dict[str, Any],
        memory: 'MemorySystem'
    ) -> Any:
        """执行搜索任务"""
        if "web_search" in tools:
            query = task.get("description").replace("搜索", "").strip()
            return tools["web_search"].execute({"query": query})
        return "搜索功能不可用"

    def _execute_file(
        self,
        task: Dict[str, Any],
        tools: Dict[str, Any],
        memory: 'MemorySystem'
    ) -> Any:
        """执行文件操作任务"""
        if "file_io" in tools:
            action = task.get("metadata", {}).get("action", "read")
            path = task.get("metadata", {}).get("path", "")
            return tools["file_io"].execute({"action": action, "path": path})
        return "文件操作功能不可用"

    def _execute_analysis(
        self,
        task: Dict[str, Any],
        tools: Dict[str, Any],
        memory: 'MemorySystem'
    ) -> Any:
        """执行分析任务"""
        # 从记忆中获取相关数据
        dependencies = task.get("dependencies", [])
        if dependencies:
            data = memory.retrieve(dependencies[0])
        else:
            data = None

        if data:
            return f"分析结果: 处理了 {len(str(data))} 字符的数据"

        return "没有可分析的数据"

    def _execute_generation(
        self,
        task: Dict[str, Any],
        tools: Dict[str, Any],
        memory: 'MemorySystem'
    ) -> Any:
        """执行生成任务"""
        description = task.get("description", "")
        return f"生成内容: {description}"

    def _build_execution_prompt(
        self,
        task: Dict[str, Any],
        tools: Dict[str, Any],
        memory: 'MemorySystem'
    ) -> str:
        """构建执行提示"""
        available_tools = list(tools.keys())

        return f"""请执行以下任务：

任务: {task.get('description')}

可用工具: {', '.join(available_tools)}

上下文: {memory.get_context(task.get('id', ''))}

要求:
1. 如果需要使用工具，请指定工具名称和输入
2. 返回执行结果
3. 如果遇到错误，请说明原因

返回格式:
{{
  "tool": "工具名称(可选)",
  "input": {{ "参数": "值" }}(可选),
  "result": "执行结果或答案"
}}
"""

    def _parse_action(self, response: str) -> Optional[Dict[str, Any]]:
        """解析动作"""
        try:
            return json.loads(response)
        except:
            return None


if __name__ == "__main__":
    executor = Executor()

    # 注册模拟工具
    class MockTool:
        def execute(self, input_data):
            return f"工具执行结果: {input_data}"

    executor.register_tool("web_search", MockTool())
    executor.register_tool("file_io", MockTool())

    # 示例任务
    task = {
        "id": "task_1",
        "description": "搜索关于 AI Agent 的最新研究"
    }

    # 执行任务
    result = executor.execute(task)
    print(f"任务 ID: {result.task_id}")
    print(f"状态: {result.status}")
    print(f"输出: {result.output}")
    print(f"执行时间: {result.execution_time:.2f} 秒")
