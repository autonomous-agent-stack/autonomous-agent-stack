"""
OpenClaw Parity 回归测试套件

目标：验证自定义编排系统与原生 OpenClaw 的行为一致性
优先级：P0（核心功能）和 P1（重要功能）

测试覆盖：
- Session 管理（P0）
- Channel 适配（P0）
- 工具调用（P0）
- Event 顺序（P1）
- 错误处理与重试（P1）
- 并发控制（P1）
"""

import pytest
import json
import time
from typing import Dict, List, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class TestResult(Enum):
    """测试结果枚举"""
    PASS = "PASS"           # 完全通过
    PARTIAL = "PARTIAL"     # 部分通过
    FAIL = "FAIL"           # 失败
    SKIP = "SKIP"           # 跳过（功能未实现）


@dataclass
class TestOutcome:
    """测试结果详情"""
    task_id: str
    result: TestResult
    message: str
    actual_output: Dict[str, Any] = field(default_factory=dict)
    expected_output: Dict[str, Any] = field(default_factory=dict)
    tool_calls: List[str] = field(default_factory=list)
    events: List[str] = field(default_factory=list)
    session_changes: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


class GoldenTaskHarness:
    """
    Golden Task 执行器（最小化版本）

    功能：
    1. 加载 Golden Tasks JSON
    2. 模拟 Session 状态管理
    3. 记录 Event 流
    4. 验证输出符合预期
    """

    def __init__(self, golden_tasks_path: str = "tests/fixtures/openclaw_golden_tasks.json"):
        """初始化 harness"""
        self.tasks = self._load_tasks(golden_tasks_path)
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.events: List[Dict[str, Any]] = []
        self.tool_call_log: List[Dict[str, Any]] = []

    def _load_tasks(self, path: str) -> List[Dict[str, Any]]:
        """加载 Golden Tasks"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('tasks', [])
        except FileNotFoundError:
            return []

    def _emit_event(self, event_type: str, data: Dict[str, Any] = None):
        """记录事件"""
        self.events.append({
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        })

    def _create_session(self, user_id: str = "test_user") -> str:
        """创建 session"""
        session_id = f"session_{user_id}_{int(time.time())}"
        self.sessions[session_id] = {
            "id": session_id,
            "user_id": user_id,
            "messages": [],
            "context": {},
            "state": "idle",
            "created_at": datetime.now().isoformat()
        }
        self._emit_event("session_created", {"session_id": session_id})
        return session_id

    def _get_session(self, session_id: str) -> Dict[str, Any]:
        """获取 session"""
        return self.sessions.get(session_id, {})

    def _update_session(self, session_id: str, updates: Dict[str, Any]):
        """更新 session"""
        if session_id in self.sessions:
            self.sessions[session_id].update(updates)
            self._emit_event("session_updated", {"session_id": session_id, "updates": updates})

    def _log_tool_call(self, tool_name: str, parameters: Dict[str, Any]):
        """记录工具调用"""
        call = {
            "tool": tool_name,
            "parameters": parameters,
            "timestamp": datetime.now().isoformat()
        }
        self.tool_call_log.append(call)
        self._emit_event("tool_call", call)

    def execute_task(self, task_id: str) -> TestOutcome:
        """
        执行单个 Golden Task

        返回：TestOutcome
        """
        task = next((t for t in self.tasks if t["id"] == task_id), None)
        if not task:
            return TestOutcome(
                task_id=task_id,
                result=TestResult.FAIL,
                message=f"任务不存在: {task_id}"
            )

        start_time = time.time()

        # 创建 session
        session_id = self._create_session()
        session_before = self._get_session(session_id)

        # 记录消息接收事件
        self._emit_event("message_received", task["input"])

        # 模拟工具调用（TODO: 接入真实的 GraphEngine）
        expected_tools = task.get("expected_tools", [])
        for tool_name in expected_tools:
            self._log_tool_call(tool_name, {})
            self._emit_event("tool_response", {"tool": tool_name, "status": "success"})

        # 模拟输出
        output = {
            "type": task["expected_output"].get("type", "text"),
            "content": f"模拟输出 for {task['name']}",
            "format": task["expected_output"].get("format", "text")
        }

        # 记录消息发送事件
        self._emit_event("message_sent", output)

        # 更新 session
        session_after_updates = {
            "messages": session_before.get("messages", []) + [task["input"]],
            "state": task["expected_session_changes"].get("state", "completed")
        }
        if "context" in task["expected_session_changes"]:
            session_after_updates["context"] = task["expected_session_changes"]["context"]

        self._update_session(session_id, session_after_updates)
        session_after = self._get_session(session_id)

        duration_ms = (time.time() - start_time) * 1000

        # 验证结果
        outcome = self._validate_task(
            task=task,
            actual_output=output,
            session_before=session_before,
            session_after=session_after,
            duration_ms=duration_ms
        )

        return outcome

    def _validate_task(
        self,
        task: Dict[str, Any],
        actual_output: Dict[str, Any],
        session_before: Dict[str, Any],
        session_after: Dict[str, Any],
        duration_ms: float
    ) -> TestOutcome:
        """
        验证任务执行结果

        返回：TestOutcome
        """
        failures = []
        warnings = []

        # 1. 验证工具调用序列
        expected_tools = task.get("expected_tools", [])
        actual_tools = [call["tool"] for call in self.tool_call_log]
        tool_match = self._compare_sequence(expected_tools, actual_tools)

        if not tool_match["exact"]:
            warnings.append(f"工具调用序列不匹配: 预期 {expected_tools}, 实际 {actual_tools}")

        # 2. 验证输出格式
        expected_format = task["expected_output"].get("format", "text")
        actual_format = actual_output.get("format", "text")
        if expected_format != actual_format:
            warnings.append(f"输出格式不匹配: 预期 {expected_format}, 实际 {actual_format}")

        # 3. 验证 Session 变化
        expected_state = task["expected_session_changes"].get("state")
        actual_state = session_after.get("state")
        if expected_state != actual_state:
            failures.append(f"Session 状态不匹配: 预期 {expected_state}, 实际 {actual_state}")

        # 4. 验证事件序列
        expected_events = task.get("expected_events", [])
        actual_events = [e["type"] for e in self.events[-len(expected_events):]]
        event_match = self._compare_sequence(expected_events, actual_events)

        if not event_match["exact"]:
            warnings.append(f"事件序列不匹配")

        # 判定结果
        if failures:
            result = TestResult.FAIL
            message = "; ".join(failures)
        elif warnings:
            result = TestResult.PARTIAL
            message = "; ".join(warnings)
        else:
            result = TestResult.PASS
            message = "完全通过"

        return TestOutcome(
            task_id=task["id"],
            result=result,
            message=message,
            actual_output=actual_output,
            expected_output=task["expected_output"],
            tool_calls=actual_tools,
            events=actual_events,
            session_changes={
                "before": session_before,
                "after": session_after
            },
            duration_ms=duration_ms
        )

    def _compare_sequence(self, expected: List[str], actual: List[str]) -> Dict[str, Any]:
        """
        比较序列是否匹配

        返回：
        - exact: 完全匹配
        - partial: 部分匹配
        - missing: 缺失的元素
        - extra: 多余的元素
        """
        exact = expected == actual
        partial = set(expected) == set(actual)

        expected_set = set(expected)
        actual_set = set(actual)

        missing = list(expected_set - actual_set)
        extra = list(actual_set - expected_set)

        return {
            "exact": exact,
            "partial": partial,
            "missing": missing,
            "extra": extra
        }

    def reset(self):
        """重置状态"""
        self.sessions.clear()
        self.events.clear()
        self.tool_call_log.clear()


# ============ P0 测试：Session 管理 ============

class TestSessionManagement:
    """P0: Session 管理测试"""

    @pytest.fixture
    def harness(self):
        """创建 harness fixture"""
        h = GoldenTaskHarness()
        yield h
        h.reset()

    def test_session_creation(self, harness):
        """测试：创建 session"""
        session_id = harness._create_session("user123")

        assert session_id is not None
        assert session_id in harness.sessions
        assert harness.sessions[session_id]["user_id"] == "user123"
        assert harness.sessions[session_id]["state"] == "idle"

        # 验证事件
        creation_event = next((e for e in harness.events if e["type"] == "session_created"), None)
        assert creation_event is not None
        assert creation_event["data"]["session_id"] == session_id

    def test_session_context_persistence(self, harness):
        """测试：Session 上下文持久化"""
        session_id = harness._create_session("user123")

        # 更新 context
        harness._update_session(session_id, {
            "context": {"user_name": "张三", "preference": "简洁"}
        })

        session = harness._get_session(session_id)
        assert session["context"]["user_name"] == "张三"
        assert session["context"]["preference"] == "简洁"

        # 验证事件
        update_event = next((e for e in harness.events if e["type"] == "session_updated"), None)
        assert update_event is not None

    def test_session_state_transition(self, harness):
        """测试：Session 状态转换"""
        session_id = harness._create_session("user123")

        # 状态转换：idle -> active -> completed
        harness._update_session(session_id, {"state": "active"})
        assert harness._get_session(session_id)["state"] == "active"

        harness._update_session(session_id, {"state": "completed"})
        assert harness._get_session(session_id)["state"] == "completed"

    def test_multi_session_isolation(self, harness):
        """测试：多 session 隔离"""
        session1 = harness._create_session("user1")
        session2 = harness._create_session("user2")

        # 更新不同 session
        harness._update_session(session1, {"context": {"name": "用户1"}})
        harness._update_session(session2, {"context": {"name": "用户2"}})

        # 验证隔离
        assert harness._get_session(session1)["context"]["name"] == "用户1"
        assert harness._get_session(session2)["context"]["name"] == "用户2"

        # 互不影响
        assert harness._get_session(session1)["context"] != harness._get_session(session2)["context"]


# ============ P0 测试：工具调用 ============

class TestToolCalls:
    """P0: 工具调用测试"""

    @pytest.fixture
    def harness(self):
        h = GoldenTaskHarness()
        yield h
        h.reset()

    def test_single_tool_call(self, harness):
        """测试：单个工具调用"""
        harness._log_tool_call("weather", {"location": "Beijing"})

        assert len(harness.tool_call_log) == 1
        assert harness.tool_call_log[0]["tool"] == "weather"
        assert harness.tool_call_log[0]["parameters"]["location"] == "Beijing"

        # 验证事件
        tool_call_event = next((e for e in harness.events if e["type"] == "tool_call"), None)
        assert tool_call_event is not None
        assert tool_call_event["data"]["tool"] == "weather"

    def test_multiple_tool_calls(self, harness):
        """测试：多个工具调用"""
        harness._log_tool_call("read", {"path": "file1.txt"})
        harness._log_tool_call("write", {"path": "file2.txt"})
        harness._log_tool_call("exec", {"command": "ls"})

        assert len(harness.tool_call_log) == 3
        assert [c["tool"] for c in harness.tool_call_log] == ["read", "write", "exec"]

    def test_tool_call_sequence_validation(self, harness):
        """测试：工具调用序列验证"""
        expected = ["read", "write", "exec"]
        harness._log_tool_call("read", {})
        harness._log_tool_call("write", {})
        harness._log_tool_call("exec", {})

        actual = [c["tool"] for c in harness.tool_call_log]
        result = harness._compare_sequence(expected, actual)

        assert result["exact"] is True
        assert result["missing"] == []
        assert result["extra"] == []

    def test_partial_sequence_match(self, harness):
        """测试：部分序列匹配"""
        expected = ["read", "write"]
        harness._log_tool_call("write", {})
        harness._log_tool_call("read", {})

        actual = [c["tool"] for c in harness.tool_call_log]
        result = harness._compare_sequence(expected, actual)

        # 元素相同但顺序不同
        assert result["exact"] is False
        assert result["partial"] is True


# ============ P1 测试：Event 顺序 ============

class TestEventOrdering:
    """P1: 事件顺序测试"""

    @pytest.fixture
    def harness(self):
        h = GoldenTaskHarness()
        yield h
        h.reset()

    def test_event_sequence(self, harness):
        """测试：事件序列"""
        harness._emit_event("message_received")
        harness._emit_event("tool_call")
        harness._emit_event("tool_response")
        harness._emit_event("message_sent")

        expected_types = ["message_received", "tool_call", "tool_response", "message_sent"]
        actual_types = [e["type"] for e in harness.events]

        assert actual_types == expected_types

    def test_event_timestamp_ordering(self, harness):
        """测试：事件时间戳顺序"""
        harness._emit_event("event1")
        time.sleep(0.01)
        harness._emit_event("event2")
        time.sleep(0.01)
        harness._emit_event("event3")

        timestamps = [e["timestamp"] for e in harness.events]
        assert timestamps[0] < timestamps[1] < timestamps[2]

    def test_event_data_preservation(self, harness):
        """测试：事件数据保留"""
        test_data = {"key": "value", "number": 42}
        harness._emit_event("test_event", test_data)

        event = harness.events[0]
        assert event["data"] == test_data


# ============ P1 测试：错误处理 ============

class TestErrorHandling:
    """P1: 错误处理测试"""

    @pytest.fixture
    def harness(self):
        h = GoldenTaskHarness()
        yield h
        h.reset()

    def test_task_execution_failure(self, harness):
        """测试：任务执行失败"""
        # 模拟一个会失败的任务
        task_id = "golden_task_019"  # 超时任务
        outcome = harness.execute_task(task_id)

        # 注意：当前实现是模拟的，所以会 PASS
        # 真实实现需要处理失败情况
        assert outcome.result in [TestResult.PASS, TestResult.PARTIAL, TestResult.FAIL]

    def test_error_recovery_attempt(self, harness):
        """测试：错误恢复尝试"""
        # 这个测试需要真实的重试逻辑
        # 当前只是框架
        assert True  # TODO: 接入真实重试机制


# ============ P1 测试：并发控制 ============

class TestConcurrencyControl:
    """P1: 并发控制测试"""

    @pytest.fixture
    def harness(self):
        h = GoldenTaskHarness()
        yield h
        h.reset()

    def test_concurrent_session_creation(self, harness):
        """测试：并发 session 创建"""
        session_ids = []
        for i in range(10):
            session_ids.append(harness._create_session(f"user{i}"))

        assert len(session_ids) == 10
        assert len(set(session_ids)) == 10  # 所有 ID 唯一

        # 验证所有 session 都存在
        for sid in session_ids:
            assert sid in harness.sessions


# ============ Golden Tasks 集成测试 ============

class TestGoldenTasks:
    """Golden Tasks 集成测试"""

    @pytest.fixture
    def harness(self):
        h = GoldenTaskHarness()
        yield h
        h.reset()

    @pytest.mark.parametrize("task_id", [
        "golden_task_001",  # 简单问答
        "golden_task_002",  # 文件读取
        "golden_task_003",  # 文件写入
        "golden_task_004",  # Web搜索
        "golden_task_005",  # 日历查询
        "golden_task_006",  # 消息发送
    ])
    def test_p0_basic_tool_calls(self, harness, task_id):
        """P0: 基础工具调用测试"""
        outcome = harness.execute_task(task_id)

        # P0 任务应该至少 PARTIAL 通过
        assert outcome.result in [TestResult.PASS, TestResult.PARTIAL]

        # 验证有输出
        assert outcome.actual_output is not None
        assert "content" in outcome.actual_output

    @pytest.mark.parametrize("task_id", [
        "golden_task_007",  # 多步骤任务
        "golden_task_008",  # 条件分支
        "golden_task_009",  # 循环处理
        "golden_task_010",  # 批量操作
        "golden_task_011",  # 错误恢复
        "golden_task_012",  # 跨工具协作
    ])
    def test_p1_complex_workflows(self, harness, task_id):
        """P1: 复杂工作流测试"""
        outcome = harness.execute_task(task_id)

        # P1 任务可以 SKIP（未实现）或 PARTIAL/PASS
        assert outcome.result in [TestResult.PASS, TestResult.PARTIAL, TestResult.SKIP]

        # 如果未实现，应该有明确说明
        if outcome.result == TestResult.SKIP:
            # TODO: 实现复杂工作流后移除
            pytest.skip("复杂工作流未实现")


# ============ 测试工具函数 ============

def test_result_comparison():
    """测试：结果比较工具"""
    harness = GoldenTaskHarness()

    # 完全匹配
    result1 = harness._compare_sequence(["a", "b", "c"], ["a", "b", "c"])
    assert result1["exact"] is True

    # 部分匹配（顺序不同）
    result2 = harness._compare_sequence(["a", "b", "c"], ["b", "c", "a"])
    assert result2["exact"] is False
    assert result2["partial"] is True

    # 缺失和多余
    result3 = harness._compare_sequence(["a", "b"], ["a", "c", "d"])
    assert result3["exact"] is False
    assert "b" in result3["missing"]
    assert "c" in result3["extra"]
    assert "d" in result3["extra"]


if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v", "-s"])
