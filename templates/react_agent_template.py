"""
ReAct Agent 模板
基于 ReAct (Reasoning + Acting) 模式的 Agent 实现
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import re

class ReActAgent:
    """ReAct Agent 实现"""
    
    def __init__(
        self,
        model: str,
        tools: List[Dict[str, Any]],
        max_iterations: int = 5
    ):
        """
        初始化 ReAct Agent
        
        Args:
            model: LLM 模型名称
            tools: 工具列表
            max_iterations: 最大迭代次数
        """
        self.model = model
        self.tools = {tool["name"]: tool for tool in tools}
        self.max_iterations = max_iterations
        self.history = []
    
    def think(self, question: str) -> Dict[str, str]:
        """
        思考阶段
        
        Args:
            question: 用户问题
        
        Returns:
            思考结果（thought, action, action_input）
        """
        prompt = self._build_think_prompt(question)
        response = self._call_llm(prompt)
        
        # 解析 Thought, Action, Action Input
        thought_match = re.search(r"Thought: (.+)", response)
        action_match = re.search(r"Action: (\w+)", response)
        input_match = re.search(r"Action Input: (.+)", response)
        
        return {
            "thought": thought_match.group(1) if thought_match else "",
            "action": action_match.group(1) if action_match else "",
            "action_input": input_match.group(1) if input_match else ""
        }
    
    def act(self, action: str, action_input: str) -> str:
        """
        行动阶段
        
        Args:
            action: 工具名称
            action_input: 工具输入
        
        Returns:
            工具执行结果
        """
        if action not in self.tools:
            return f"Error: Unknown tool '{action}'"
        
        # 执行工具
        tool = self.tools[action]
        result = self._execute_tool(action, action_input)
        
        return result
    
    def run(self, question: str) -> str:
        """
        运行 Agent
        
        Args:
            question: 用户问题
        
        Returns:
            最终答案
        """
        for iteration in range(self.max_iterations):
            # Think
            thought_result = self.think(question)
            
            # 记录历史
            self.history.append({
                "thought": thought_result["thought"],
                "action": thought_result["action"],
                "action_input": thought_result["action_input"]
            })
            
            # 检查是否完成
            if thought_result["action"] == "Finish":
                return thought_result["action_input"]
            
            # Act
            observation = self.act(
                thought_result["action"],
                thought_result["action_input"]
            )
            
            # 记录观察
            self.history.append({"observation": observation})
        
        return "Error: Max iterations reached"
    
    def _build_think_prompt(self, question: str) -> str:
        """构建思考提示"""
        tools_desc = "\n".join([
            f"- {name}: {tool['description']}"
            for name, tool in self.tools.items()
        ])
        
        history_str = "\n".join([
            f"Thought: {h.get('thought', '')}\n"
            f"Action: {h.get('action', '')}\n"
            f"Action Input: {h.get('action_input', '')}\n"
            f"Observation: {h.get('observation', '')}"
            for h in self.history
        ])
        
        return f"""Answer the following questions as best you can. You have access to the following tools:

{tools_desc}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{', '.join(self.tools.keys())}, Finish]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Action: Finish
Action Input: the final answer to the original input question

Begin!

Question: {question}

{history_str}

Thought:"""
    
    def _call_llm(self, prompt: str) -> str:
        """调用 LLM（需要实现）"""
        # TODO: 实现 LLM 调用
        raise NotImplementedError
    
    def _execute_tool(self, tool_name: str, tool_input: str) -> str:
        """执行工具（需要实现）"""
        # TODO: 实现工具执行
        raise NotImplementedError


# 使用示例
if __name__ == "__main__":
    tools = [
        {
            "name": "search",
            "description": "搜索互联网信息"
        },
        {
            "name": "calculator",
            "description": "执行数学计算"
        }
    ]
    
    agent = ReActAgent(model="gpt-4", tools=tools)
    result = agent.run("北京到上海的距离是多少？")
    print(result)
