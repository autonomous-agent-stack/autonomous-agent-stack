"""
Agent 错误类单元测试
"""

import unittest

from lib.error_handling.agent_errors import (
    TaskPlanningError,
    ToolCallError,
    SelfReflectionError,
    MemoryError,
    CollaborationError,
    TimeoutError as AgentTimeoutError,
)


class TestTaskPlanningError(unittest.TestCase):
    """测试 TaskPlanningError"""

    def test_initialization(self):
        """测试初始化"""
        error = TaskPlanningError(
            agent_name="CodeAgent",
            reason="无法生成有效的执行计划",
            task_description="编写一个 Python 函数",
            available_tools=["code_editor", "test_runner"],
        )

        self.assertEqual(error.details["agent_name"], "CodeAgent")
        self.assertEqual(error.details["reason"], "无法生成有效的执行计划")
        self.assertEqual(error.details["task_description"], "编写一个 Python 函数")
        self.assertEqual(error.details["available_tools"], ["code_editor", "test_runner"])

    def test_task_description_truncation(self):
        """测试任务描述截断"""
        long_task = "x" * 1000
        error = TaskPlanningError(agent_name="Agent", reason="测试", task_description=long_task)

        self.assertLess(len(error.details["task_description"]), 300)

    def test_action_history_truncation(self):
        """测试动作历史截断"""
        action_history = [f"action_{i}" for i in range(100)]
        error = TaskPlanningError(
            agent_name="Agent", reason="测试", available_tools=action_history
        )

        # available_tools 应该完整保留（不是 action_history）
        self.assertEqual(len(error.details["available_tools"]), 100)


class TestToolCallError(unittest.TestCase):
    """测试 ToolCallError"""

    def test_initialization(self):
        """测试初始化"""
        error = ToolCallError(
            tool_name="code_editor",
            reason="文件不存在",
            tool_args={"file": "test.py", "content": "print('hello')"},
            tool_output="Error: File not found",
        )

        self.assertEqual(error.details["tool_name"], "code_editor")
        self.assertEqual(error.details["reason"], "文件不存在")
        self.assertIn("tool_args", error.details)
        self.assertIn("tool_output", error.details)

    def test_tool_args_truncation(self):
        """测试工具参数截断"""
        long_args = {"data": "x" * 1000}
        error = ToolCallError(tool_name="test", reason="测试", tool_args=long_args)

        self.assertLess(len(error.details["tool_args"]), 300)

    def test_tool_output_truncation(self):
        """测试工具输出截断"""
        long_output = "x" * 1000
        error = ToolCallError(tool_name="test", reason="测试", tool_output=long_output)

        self.assertLess(len(error.details["tool_output"]), 500)


class TestSelfReflectionError(unittest.TestCase):
    """测试 SelfReflectionError"""

    def test_initialization(self):
        """测试初始化"""
        error = SelfReflectionError(
            agent_name="CodeAgent",
            reason="无法评估代码质量",
            action_history=["write_code", "run_tests"],
            outcome="测试通过但代码不规范",
        )

        self.assertEqual(error.details["agent_name"], "CodeAgent")
        self.assertEqual(error.details["reason"], "无法评估代码质量")
        self.assertEqual(error.details["action_history"], ["write_code", "run_tests"])
        self.assertEqual(error.details["outcome"], "测试通过但代码不规范")

    def test_action_history_limit(self):
        """测试动作历史限制"""
        action_history = [f"action_{i}" for i in range(100)]
        error = SelfReflectionError(
            agent_name="Agent", reason="测试", action_history=action_history
        )

        # 只保留最近 5 个动作
        self.assertEqual(len(error.details["action_history"]), 5)


class TestMemoryError(unittest.TestCase):
    """测试 MemoryError"""

    def test_initialization(self):
        """测试初始化"""
        error = MemoryError(
            memory_type="long_term",
            operation="write",
            reason="存储空间不足",
            memory_key="agent_123:conversation",
            memory_size=1024000,
        )

        self.assertEqual(error.details["memory_type"], "long_term")
        self.assertEqual(error.details["operation"], "write")
        self.assertEqual(error.details["reason"], "存储空间不足")
        self.assertEqual(error.details["memory_key"], "agent_123:conversation")
        self.assertEqual(error.details["memory_size"], 1024000)


class TestCollaborationError(unittest.TestCase):
    """测试 CollaborationError"""

    def test_initialization(self):
        """测试初始化"""
        error = CollaborationError(
            agent_1="CodeAgent",
            agent_2="TestAgent",
            reason="协议不兼容",
            protocol="REST",
            message="Failed to serialize result",
        )

        self.assertEqual(error.details["agent_1"], "CodeAgent")
        self.assertEqual(error.details["agent_2"], "TestAgent")
        self.assertEqual(error.details["reason"], "协议不兼容")
        self.assertEqual(error.details["protocol"], "REST")
        self.assertEqual(error.details["message"], "Failed to serialize result")

    def test_message_truncation(self):
        """测试消息截断"""
        long_message = "x" * 1000
        error = CollaborationError(
            agent_1="A", agent_2="B", reason="测试", message=long_message
        )

        self.assertLess(len(error.details["message"]), 500)


class TestAgentTimeoutError(unittest.TestCase):
    """测试 AgentTimeoutError"""

    def test_initialization(self):
        """测试初始化"""
        error = AgentTimeoutError(
            agent_name="CodeAgent",
            elapsed=120.0,
            timeout=60.0,
            task_description="编写复杂算法",
            current_step="优化代码",
        )

        self.assertEqual(error.details["agent_name"], "CodeAgent")
        self.assertEqual(error.details["elapsed"], 120.0)
        self.assertEqual(error.details["timeout"], 60.0)
        self.assertEqual(error.details["task_description"], "编写复杂算法")
        self.assertEqual(error.details["current_step"], "优化代码")

    def test_no_retry_config(self):
        """测试无重试配置"""
        error = AgentTimeoutError(agent_name="Agent", elapsed=120.0, timeout=60.0)

        self.assertIsNone(error.retry_config)

    def test_abort_strategy(self):
        """测试终止策略"""
        error = AgentTimeoutError(agent_name="Agent", elapsed=120.0, timeout=60.0)

        self.assertEqual(error.recovery_strategy.value, "abort")


class TestAllAgentErrors(unittest.TestCase):
    """测试所有 Agent 错误的共同属性"""

    def test_all_errors_have_error_codes(self):
        """测试所有错误都有错误代码"""
        errors = [
            TaskPlanningError("Agent", "测试"),
            ToolCallError("tool", "测试"),
            SelfReflectionError("Agent", "测试"),
            MemoryError("short_term", "read", "测试"),
            CollaborationError("A", "B", "测试"),
            AgentTimeoutError("Agent", 120.0, 60.0),
        ]

        for error in errors:
            self.assertIsNotNone(error.error_code)
            self.assertIsInstance(error.error_code, str)
            self.assertTrue(error.error_code.startswith("AGENT_"))

    def test_all_errors_can_convert_to_dict(self):
        """测试所有错误都可以转换为字典"""
        errors = [
            TaskPlanningError("Agent", "测试"),
            ToolCallError("tool", "测试"),
            SelfReflectionError("Agent", "测试"),
            MemoryError("short_term", "read", "测试"),
            CollaborationError("A", "B", "测试"),
            AgentTimeoutError("Agent", 120.0, 60.0),
        ]

        for error in errors:
            error_dict = error.to_dict()
            self.assertIn("error_code", error_dict)
            self.assertIn("message", error_dict)
            self.assertIn("severity", error_dict)
            self.assertIn("recovery_strategy", error_dict)

    def test_severity_levels(self):
        """测试严重程度分布"""
        # TimeoutError 应该是 MEDIUM
        timeout_error = AgentTimeoutError("Agent", 120.0, 60.0)
        self.assertEqual(timeout_error.severity.value, "medium")

        # 其他错误通常是 HIGH
        other_errors = [
            TaskPlanningError("Agent", "测试"),
            ToolCallError("tool", "测试"),
            SelfReflectionError("Agent", "测试"),
            MemoryError("short_term", "read", "测试"),
            CollaborationError("A", "B", "测试"),
        ]

        for error in other_errors:
            self.assertIn(error.severity.value, ["medium", "high"])


if __name__ == "__main__":
    unittest.main()
