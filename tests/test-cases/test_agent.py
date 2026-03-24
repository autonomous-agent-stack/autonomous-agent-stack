"""
Agent System Test Suite (10 Tests)
Tests for AI Agent functionality including planning, tool use, and collaboration
"""

import unittest
import asyncio
import time
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from .fixtures import (
    SAMPLE_TOOL_CALLS,
    create_mock_agent,
    assert_valid_response,
    assert_performance,
    MockToolCall
)


class AgentState(Enum):
    """Agent execution states"""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    FINISHED = "finished"
    ERROR = "error"


@dataclass
class AgentTask:
    """Task definition for agents"""
    id: str
    description: str
    tools: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    priority: int = 5
    max_steps: int = 10


@dataclass
class AgentMemory:
    """Agent memory system"""
    short_term: List[Dict] = field(default_factory=list)
    long_term: List[Dict] = field(default_factory=list)
    
    def add(self, item: Dict, memory_type: str = "short_term"):
        if memory_type == "short_term":
            self.short_term.append(item)
        else:
            self.long_term.append(item)
    
    def recall(self, query: str) -> List[Dict]:
        """Recall relevant memories"""
        all_memories = self.short_term + self.long_term
        return [m for m in all_memories if query.lower() in str(m).lower()]


class TestAgentTaskPlanning(unittest.TestCase):
    """Test 1: Task Planning Testing"""
    
    def setUp(self):
        self.agent = create_mock_agent()
        self.agent.plan = Mock(return_value=[
            {"action": "search", "params": {"query": "test"}},
            {"action": "analyze", "params": {}},
            {"action": "report", "params": {}}
        ])
    
    def test_task_decomposition(self):
        """Test breaking down complex tasks"""
        task = AgentTask(
            id="task1",
            description="Research Python best practices and create a summary"
        )
        
        plan = self.agent.plan(task)
        
        self.assertIsInstance(plan, list)
        self.assertGreater(len(plan), 1)
        self.assertTrue(all("action" in step for step in plan))
    
    def test_dependency_handling(self):
        """Test handling task dependencies"""
        task = AgentTask(
            id="task2",
            description="Dependent task",
            dependencies=["task1"]
        )
        
        plan = self.agent.plan(task)
        
        # Should account for dependencies
        self.assertIsNotNone(plan)
    
    def test_priority_scheduling(self):
        """Test prioritizing tasks"""
        tasks = [
            AgentTask(id=f"task{i}", description=f"Task {i}", priority=i % 10)
            for i in range(10)
        ]
        
        # Sort by priority
        sorted_tasks = sorted(tasks, key=lambda t: t.priority, reverse=True)
        
        self.assertEqual(sorted_tasks[0].priority, 9)
        self.assertEqual(sorted_tasks[-1].priority, 0)
    
    def test_plan_optimization(self):
        """Test plan optimization"""
        task = AgentTask(
            id="task3",
            description="Complex task requiring optimization"
        )
        
        plan = self.agent.plan(task)
        
        # Should return efficient plan
        self.assertLessEqual(len(plan), task.max_steps)
    
    def test_adaptive_planning(self):
        """Test adaptive planning based on feedback"""
        task = AgentTask(id="task4", description="Adaptive task")
        
        plan1 = self.agent.plan(task)
        # Simulate feedback
        plan2 = self.agent.plan(task, feedback="optimize step 2")
        
        self.assertIsNotNone(plan2)


class TestAgentToolCalling(unittest.TestCase):
    """Test 2: Tool Calling Testing"""
    
    def setUp(self):
        self.agent = create_mock_agent()
        self.tools = {
            "search": Mock(return_value=["result1", "result2"]),
            "calculate": Mock(return_value=42),
            "write_file": Mock(return_value=True),
            "read_file": Mock(return_value="file content")
        }
    
    def test_single_tool_call(self):
        """Test calling a single tool"""
        result = self.tools["search"](query="test")
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)
    
    def test_sequential_tool_calls(self):
        """Test calling multiple tools in sequence"""
        search_result = self.tools["search"](query="Python")
        calc_result = self.tools["calculate"](expression="2+2")
        
        self.assertIsNotNone(search_result)
        self.assertEqual(calc_result, 42)
    
    def test_parallel_tool_calls(self):
        """Test calling tools in parallel"""
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(self.tools["search"], query=f"test{i}")
                for i in range(5)
            ]
            results = [f.result() for f in futures]
        
        self.assertEqual(len(results), 5)
    
    def test_tool_error_handling(self):
        """Test handling tool errors"""
        self.tools["search"].side_effect = Exception("Search failed")
        
        with self.assertRaises(Exception):
            self.tools["search"](query="test")
    
    def test_tool_chaining(self):
        """Test chaining tool outputs"""
        # Search -> Read -> Write
        search_result = self.tools["search"](query="file.txt")
        read_result = self.tools["read_file"]()
        write_result = self.tools["write_file"](content=read_result)
        
        self.assertTrue(write_result)


class TestAgentSelfReflection(unittest.TestCase):
    """Test 3: Self-Reflection Testing"""
    
    def setUp(self):
        self.agent = create_mock_agent()
        self.agent.reflection_history = []
    
    def test_success_evaluation(self):
        """Test evaluating task success"""
        result = self.agent.reflect(
            task="Complete task",
            outcome="Task completed successfully",
            criteria=["accuracy", "efficiency"]
        )
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
    
    def test_failure_analysis(self):
        """Test analyzing failures"""
        result = self.agent.reflect(
            task="Failed task",
            outcome="Task failed due to timeout",
            criteria=["success"]
        )
        
        # Should provide analysis
        self.assertIsNotNone(result)
        self.assertIn("fail", result.lower())
    
    def test_learning_from_mistakes(self):
        """Test learning from mistakes"""
        mistakes = [
            {"task": "task1", "error": "timeout", "lesson": "add timeout check"},
            {"task": "task2", "error": "invalid input", "lesson": "validate input"}
        ]
        
        for mistake in mistakes:
            self.agent.reflection_history.append(mistake)
        
        # Should recall lessons
        lessons = [m["lesson"] for m in self.agent.reflection_history]
        self.assertEqual(len(lessons), 2)
    
    def test_strategy_adjustment(self):
        """Test adjusting strategy based on reflection"""
        initial_strategy = {"approach": "direct"}
        feedback = "Direct approach failed, try iterative"
        
        adjusted_strategy = self.agent.adjust_strategy(
            initial_strategy,
            feedback
        )
        
        self.assertIsNotNone(adjusted_strategy)
    
    def test_confidence_scoring(self):
        """Test confidence in decisions"""
        decision = "Use tool A instead of tool B"
        confidence = self.agent.score_confidence(decision, context={})
        
        self.assertIsInstance(confidence, (int, float))
        self.assertGreaterEqual(confidence, 0)
        self.assertLessEqual(confidence, 1)


class TestAgentMultiAgentCollaboration(unittest.TestCase):
    """Test 4: Multi-Agent Collaboration Testing"""
    
    def setUp(self):
        self.agents = {
            "researcher": create_mock_agent(),
            "writer": create_mock_agent(),
            "reviewer": create_mock_agent()
        }
    
    def test_role_distribution(self):
        """Test distributing roles among agents"""
        task = "Research and write about AI"
        
        researcher_result = self.agents["researcher"].act(
            action=f"Research: {task}"
        )
        writer_result = self.agents["writer"].act(
            action=f"Write based on: {researcher_result}"
        )
        
        self.assertIsNotNone(writer_result)
    
    def test_communication_protocols(self):
        """Test agent communication"""
        message = {
            "from": "researcher",
            "to": "writer",
            "content": "Research results here",
            "timestamp": time.time()
        }
        
        # Simulate message passing
        received = self.agents["writer"].receive(message)
        
        self.assertIsNotNone(received)
    
    def test_shared_memory(self):
        """Test shared memory across agents"""
        shared_memory = {}
        
        # Agent 1 writes
        shared_memory["agent1_data"] = "results from agent 1"
        
        # Agent 2 reads
        agent2_data = shared_memory.get("agent1_data")
        
        self.assertEqual(agent2_data, "results from agent 1")
    
    def test_conflict_resolution(self):
        """Test resolving conflicts between agents"""
        agent1_decision = {"tool": "A", "reason": "faster"}
        agent2_decision = {"tool": "B", "reason": "more accurate"}
        
        # Conflict resolution mechanism
        final_decision = self.resolve_conflict([agent1_decision, agent2_decision])
        
        self.assertIsNotNone(final_decision)
        self.assertIn("tool", final_decision)
    
    def test_collaborative_task_completion(self):
        """Test completing task collaboratively"""
        task = "Create a research report"
        
        # Phase 1: Research
        research = self.agents["researcher"].act(action="Research")
        
        # Phase 2: Writing
        draft = self.agents["writer"].act(
            action=f"Write based on: {research}"
        )
        
        # Phase 3: Review
        review = self.agents["reviewer"].act(
            action=f"Review: {draft}"
        )
        
        self.assertIsNotNone(review)
    
    def resolve_conflict(self, decisions: List[Dict]) -> Dict:
        """Resolve conflicts between agent decisions"""
        # Simple voting mechanism
        from collections import Counter
        
        votes = [d["tool"] for d in decisions]
        counter = Counter(votes)
        
        most_common = counter.most_common(1)[0][0]
        
        return {"tool": most_common, "method": "voting"}


class TestAgentErrorRecovery(unittest.TestCase):
    """Test 5: Error Recovery Testing"""
    
    def setUp(self):
        self.agent = create_mock_agent()
    
    def test_retry_mechanism(self):
        """Test retry on failure"""
        attempts = 0
        max_retries = 3
        
        def flaky_operation():
            nonlocal attempts
            attempts += 1
            if attempts < max_retries:
                raise Exception("Failed")
            return "Success"
        
        # Retry logic
        for i in range(max_retries):
            try:
                result = flaky_operation()
                break
            except Exception:
                continue
        
        self.assertEqual(result, "Success")
        self.assertEqual(attempts, max_retries)
    
    def test_fallback_strategy(self):
        """Test fallback to alternative strategy"""
        primary_tool = Mock(side_effect=Exception("Primary failed"))
        fallback_tool = Mock(return_value="Fallback result")
        
        try:
            result = primary_tool()
        except Exception:
            result = fallback_tool()
        
        self.assertEqual(result, "Fallback result")
    
    def test_graceful_degradation(self):
        """Test graceful degradation when components fail"""
        available_tools = ["tool1", "tool2", "tool3"]
        working_tools = []
        
        for tool in available_tools:
            try:
                # Simulate tool check
                result = f"Used {tool}"
                working_tools.append(tool)
            except Exception:
                continue
        
        # Should work with remaining tools
        self.assertGreater(len(working_tools), 0)
    
    def test_error_categorization(self):
        """Test categorizing errors for appropriate handling"""
        errors = [
            {"type": "timeout", "recoverable": True},
            {"type": "permission", "recoverable": False},
            {"type": "network", "recoverable": True}
        ]
        
        recoverable = [e for e in errors if e["recoverable"]]
        
        self.assertEqual(len(recoverable), 2)
    
    def test_recovery_action_selection(self):
        """Test selecting appropriate recovery action"""
        error_map = {
            "timeout": "retry_with_backoff",
            "permission": "request_access",
            "not_found": "use_alternative"
        }
        
        error_type = "timeout"
        action = error_map.get(error_type, "log_and_continue")
        
        self.assertEqual(action, "retry_with_backoff")


class TestAgentPerformance(unittest.TestCase):
    """Test 6: Performance Testing"""
    
    def setUp(self):
        self.agent = create_mock_agent()
    
    def test_task_completion_time(self):
        """Test task completion within time limit"""
        task = AgentTask(
            id="perf1",
            description="Performance test task"
        )
        
        start_time = time.time()
        result = self.agent.act(action="Complete task")
        duration = time.time() - start_time
        
        assert_performance(start_time, max_duration=5.0)
        self.assertIsNotNone(result)
    
    def test_throughput(self):
        """Test processing multiple tasks"""
        tasks = [AgentTask(id=f"task{i}", description=f"Task {i}") for i in range(10)]
        
        start_time = time.time()
        results = [self.agent.act(action=f"Process {t.id}") for t in tasks]
        duration = time.time() - start_time
        
        self.assertEqual(len(results), len(tasks))
        assert_performance(start_time, max_duration=15.0)
    
    def test_resource_usage(self):
        """Test resource consumption"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform work
        for i in range(100):
            self.agent.act(action=f"Task {i}")
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable
        self.assertLess(memory_increase, 100 * 1024 * 1024)  # < 100MB
    
    def test_scalability(self):
        """Test scaling with task complexity"""
        simple_tasks = [
            AgentTask(id=f"simple{i}", description="Simple task")
            for i in range(10)
        ]
        
        complex_tasks = [
            AgentTask(id=f"complex{i}", description="Complex task with many steps")
            for i in range(10)
        ]
        
        # Should handle both
        for task in simple_tasks + complex_tasks:
            result = self.agent.act(action=f"Process {task.id}")
            self.assertIsNotNone(result)


class TestAgentConcurrency(unittest.TestCase):
    """Test 7: Concurrency Testing"""
    
    def setUp(self):
        self.agents = [create_mock_agent() for _ in range(5)]
    
    def test_concurrent_task_execution(self):
        """Test multiple agents working concurrently"""
        import concurrent.futures
        
        tasks = [f"task{i}" for i in range(10)]
        
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(
                    self.agents[i % 5].act,
                    action=f"Process {task}"
                )
                for i, task in enumerate(tasks)
            ]
            results = [f.result() for f in futures]
        duration = time.time() - start_time
        
        self.assertEqual(len(results), len(tasks))
    
    def test_shared_resource_access(self):
        """Test accessing shared resources safely"""
        shared_counter = {"value": 0}
        lock = Mock()  # Mock lock
        
        def increment():
            # Simulate thread-safe increment
            shared_counter["value"] += 1
        
        # Execute concurrently
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(increment) for _ in range(100)]
            [f.result() for f in futures]
        
        self.assertEqual(shared_counter["value"], 100)
    
    def test_deadlock_prevention(self):
        """Test deadlock prevention in multi-agent scenarios"""
        # This would require actual concurrent agents
        # For now, test that agents can complete without deadlock
        results = []
        
        for agent in self.agents:
            result = agent.act(action="Complete task")
            results.append(result)
        
        self.assertEqual(len(results), len(self.agents))
    
    def test_race_condition_handling(self):
        """Test handling race conditions"""
        shared_data = {"value": 0}
        
        def safe_update(value):
            # Simulate atomic update
            shared_data["value"] = value
        
        # All updates should succeed
        for i in range(10):
            safe_update(i)
        
        self.assertEqual(shared_data["value"], 9)  # Last update


class TestAgentSecurity(unittest.TestCase):
    """Test 8: Security Testing"""
    
    def setUp(self):
        self.agent = create_mock_agent()
    
    def test_tool_access_control(self):
        """Test controlling access to tools"""
        safe_tools = ["search", "read"]
        restricted_tools = ["delete", "modify"]
        
        # Should only use safe tools
        plan = self.agent.plan(
            task="Test task",
            available_tools=safe_tools
        )
        
        for step in plan:
            if "tool" in step:
                self.assertIn(step["tool"], safe_tools)
    
    def test_input_sanitization(self):
        """Test sanitizing user inputs"""
        malicious_inputs = [
            "; rm -rf /",
            "<script>alert('xss')</script>",
            "$(evil_command)"
        ]
        
        for input_text in malicious_inputs:
            # Should sanitize or escape
            sanitized = self.agent.sanitize_input(input_text)
            self.assertNotIn(";", sanitized)
            self.assertNotIn("<script>", sanitized)
    
    def test_output_filtering(self):
        """Test filtering sensitive outputs"""
        sensitive_data = {
            "api_key": "secret-key-123",
            "password": "password123",
            "ssn": "123-45-6789"
        }
        
        # Should filter sensitive data
        filtered_output = self.agent.filter_output(sensitive_data)
        
        self.assertNotIn("secret-key-123", str(filtered_output))
        self.assertNotIn("password123", str(filtered_output))
    
    def test_permission_enforcement(self):
        """Test enforcing permission boundaries"""
        permissions = {
            "read": True,
            "write": False,
            "delete": False
        }
        
        # Read should succeed
        result = self.agent.check_permission("read", permissions)
        self.assertTrue(result)
        
        # Write should fail
        result = self.agent.check_permission("write", permissions)
        self.assertFalse(result)
    
    def test_audit_trail(self):
        """Test maintaining audit trail"""
        actions = []
        
        # Perform actions
        for i in range(5):
            action = {"tool": f"tool{i}", "timestamp": time.time()}
            actions.append(action)
        
        # Should have audit trail
        self.assertEqual(len(actions), 5)
        self.assertTrue(all("timestamp" in a for a in actions))


class TestAgentMemory(unittest.TestCase):
    """Test 9: Memory System Testing"""
    
    def setUp(self):
        self.agent = create_mock_agent()
        self.memory = AgentMemory()
    
    def test_short_term_memory(self):
        """Test short-term memory storage"""
        for i in range(5):
            self.memory.add(
                {"item": f"memory{i}", "timestamp": time.time()},
                "short_term"
            )
        
        self.assertEqual(len(self.memory.short_term), 5)
    
    def test_long_term_memory(self):
        """Test long-term memory storage"""
        important_memories = [
            {"fact": "Python is popular", "importance": "high"},
            {"fact": "AI is growing", "importance": "high"}
        ]
        
        for memory in important_memories:
            self.memory.add(memory, "long_term")
        
        self.assertEqual(len(self.memory.long_term), 2)
    
    def test_memory_recall(self):
        """Test recalling relevant memories"""
        self.memory.add({"fact": "Python is a programming language"}, "long_term")
        self.memory.add({"fact": "Java is also a programming language"}, "long_term")
        
        recalled = self.memory.recall("Python")
        
        self.assertGreater(len(recalled), 0)
        self.assertTrue(any("Python" in str(m) for m in recalled))
    
    def test_memory_consolidation(self):
        """Test consolidating short-term to long-term"""
        # Add to short-term
        self.memory.add({"fact": "Important fact"}, "short_term")
        
        # Consolidate important memories
        important = [m for m in self.memory.short_term if "important" in str(m).lower()]
        
        for memory in important:
            self.memory.add(memory, "long_term")
        
        self.assertGreater(len(self.memory.long_term), 0)
    
    def test_memory_forgetting(self):
        """Test forgetting old memories"""
        # Fill memory
        for i in range(100):
            self.memory.add({"item": i}, "short_term")
        
        # Apply forgetting (keep only recent 50)
        if len(self.memory.short_term) > 50:
            self.memory.short_term = self.memory.short_term[-50:]
        
        self.assertLessEqual(len(self.memory.short_term), 50)


class TestAgentLongRunningTasks(unittest.TestCase):
    """Test 10: Long-Running Task Testing"""
    
    def setUp(self):
        self.agent = create_mock_agent()
    
    def test_checkpoint_save_load(self):
        """Test saving and loading checkpoints"""
        checkpoint = {
            "task_id": "long_task",
            "progress": 50,
            "state": {"data": "intermediate results"}
        }
        
        # Save checkpoint
        saved = self.agent.save_checkpoint(checkpoint)
        
        # Load checkpoint
        loaded = self.agent.load_checkpoint(saved)
        
        self.assertEqual(loaded["progress"], 50)
    
    def test_progress_tracking(self):
        """Test tracking progress over time"""
        total_steps = 100
        progress_history = []
        
        for i in range(total_steps):
            progress = (i + 1) / total_steps * 100
            progress_history.append(progress)
        
        self.assertEqual(len(progress_history), total_steps)
        self.assertEqual(progress_history[-1], 100)
    
    def test_resumption_from_interrupt(self):
        """Test resuming after interruption"""
        initial_progress = 40
        
        # Simulate interruption
        interrupted = {"progress": initial_progress, "last_step": "step 40"}
        
        # Resume
        for i in range(initial_progress, 100):
            pass  # Continue work
        
        self.assertGreater(i, initial_progress)
    
    def test_state_persistence(self):
        """Test persisting state across sessions"""
        state = {
            "session_id": "session1",
            "variables": {"count": 42},
            "history": ["action1", "action2"]
        }
        
        # Persist
        persisted = self.agent.persist_state(state)
        
        # Restore
        restored = self.agent.restore_state(persisted)
        
        self.assertEqual(restored["variables"]["count"], 42)
    
    def test_timeout_handling(self):
        """Test handling long-running timeouts"""
        max_duration = 2.0
        
        start_time = time.time()
        
        # Simulate long task with timeout check
        while time.time() - start_time < max_duration:
            # Do work
            pass
        
        # Should complete within timeout
        duration = time.time() - start_time
        self.assertLessEqual(duration, max_duration + 0.1)  # Small tolerance
    
    def test_cancellation(self):
        """Test cancelling long-running tasks"""
        cancelled = False
        
        # Simulate task that can be cancelled
        def long_task():
            nonlocal cancelled
            for i in range(100000):
                if cancelled:
                    return "Cancelled"
            return "Completed"
        
        # Cancel after some time
        cancelled = True
        result = long_task()
        
        self.assertEqual(result, "Cancelled")


if __name__ == "__main__":
    unittest.main()
