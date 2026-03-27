#!/usr/bin/env python3
"""
Agent 性能监控器
用于监控 Agent 的性能指标
"""

import time
import json
from typing import Dict, List, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import statistics

@dataclass
class AgentMetrics:
    """Agent 性能指标"""
    agent_name: str
    start_time: float
    end_time: float = 0.0
    duration: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    tool_calls: int = 0
    errors: int = 0
    success: bool = True

class AgentMonitor:
    """Agent 监控器"""
    
    def __init__(self):
        """初始化监控器"""
        self.metrics: List[AgentMetrics] = []
        self.current_agent: Dict[str, Any] = {}
    
    def start_agent(self, agent_name: str):
        """
        开始监控 Agent
        
        Args:
            agent_name: Agent 名称
        """
        self.current_agent = {
            "name": agent_name,
            "start_time": time.time(),
            "tool_calls": 0,
            "errors": 0
        }
    
    def record_tool_call(self):
        """记录工具调用"""
        if self.current_agent:
            self.current_agent["tool_calls"] += 1
    
    def record_error(self):
        """记录错误"""
        if self.current_agent:
            self.current_agent["errors"] += 1
    
    def record_tokens(self, input_tokens: int, output_tokens: int):
        """
        记录 token 使用
        
        Args:
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
        """
        if self.current_agent:
            self.current_agent["input_tokens"] = input_tokens
            self.current_agent["output_tokens"] = output_tokens
    
    def end_agent(self, success: bool = True) -> AgentMetrics:
        """
        结束监控 Agent
        
        Args:
            success: 是否成功
        
        Returns:
            性能指标
        """
        end_time = time.time()
        duration = end_time - self.current_agent["start_time"]
        
        metrics = AgentMetrics(
            agent_name=self.current_agent["name"],
            start_time=self.current_agent["start_time"],
            end_time=end_time,
            duration=duration,
            input_tokens=self.current_agent.get("input_tokens", 0),
            output_tokens=self.current_agent.get("output_tokens", 0),
            total_tokens=self.current_agent.get("input_tokens", 0) + self.current_agent.get("output_tokens", 0),
            tool_calls=self.current_agent["tool_calls"],
            errors=self.current_agent["errors"],
            success=success
        )
        
        self.metrics.append(metrics)
        self.current_agent = {}
        
        return metrics
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取性能摘要
        
        Returns:
            性能摘要
        """
        if not self.metrics:
            return {"message": "No metrics collected"}
        
        total_runs = len(self.metrics)
        successful_runs = sum(1 for m in self.metrics if m.success)
        failed_runs = total_runs - successful_runs
        
        durations = [m.duration for m in self.metrics]
        tokens = [m.total_tokens for m in self.metrics]
        tool_calls = [m.tool_calls for m in self.metrics]
        
        return {
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "success_rate": f"{(successful_runs / total_runs * 100):.1f}%",
            "avg_duration": f"{statistics.mean(durations):.2f}s",
            "min_duration": f"{min(durations):.2f}s",
            "max_duration": f"{max(durations):.2f}s",
            "avg_tokens": int(statistics.mean(tokens)),
            "total_tokens": sum(tokens),
            "avg_tool_calls": f"{statistics.mean(tool_calls):.1f}",
            "total_errors": sum(m.errors for m in self.metrics)
        }
    
    def export_metrics(self, filename: str):
        """
        导出指标到文件
        
        Args:
            filename: 文件名
        """
        data = {
            "summary": self.get_summary(),
            "metrics": [asdict(m) for m in self.metrics],
            "exported_at": datetime.now().isoformat()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 指标已导出到 {filename}")
    
    def print_report(self):
        """打印性能报告"""
        summary = self.get_summary()
        
        print("\n📊 Agent 性能报告")
        print("=" * 60)
        
        print(f"\n总运行次数: {summary['total_runs']}")
        print(f"成功次数: {summary['successful_runs']}")
        print(f"失败次数: {summary['failed_runs']}")
        print(f"成功率: {summary['success_rate']}")
        
        print(f"\n平均耗时: {summary['avg_duration']}")
        print(f"最快: {summary['min_duration']}")
        print(f"最慢: {summary['max_duration']}")
        
        print(f"\n平均 Token: {summary['avg_tokens']:,}")
        print(f"总 Token: {summary['total_tokens']:,}")
        
        print(f"\n平均工具调用: {summary['avg_tool_calls']}")
        print(f"总错误数: {summary['total_errors']}")
        
        print("\n" + "=" * 60)


# 使用示例
if __name__ == "__main__":
    monitor = AgentMonitor()
    
    # 模拟 Agent 运行
    for i in range(5):
        monitor.start_agent(f"TestAgent-{i+1}")
        
        # 模拟工作
        time.sleep(0.1 * (i + 1))
        
        # 记录指标
        monitor.record_tokens(100 * (i + 1), 50 * (i + 1))
        monitor.record_tool_call()
        monitor.record_tool_call()
        
        if i == 3:
            monitor.record_error()
            monitor.end_agent(success=False)
        else:
            monitor.end_agent(success=True)
    
    # 打印报告
    monitor.print_report()
    
    # 导出指标
    monitor.export_metrics("agent_metrics.json")
