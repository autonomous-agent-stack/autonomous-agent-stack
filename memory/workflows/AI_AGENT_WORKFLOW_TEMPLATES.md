# AI Agent 完整工作流模板

> **版本**: v1.0
> **更新时间**: 2026-03-27
> **工作流类型**: 5+

---

## 🔄 工作流 1: 客户服务流程

```python
"""
客户服务工作流
完整的客服 Agent 工作流程
"""

from typing import Dict, Any, List
from enum import Enum

class CustomerWorkflowState(Enum):
    """工作流状态"""
    GREETING = "greeting"
    INTENT_CLASSIFICATION = "intent_classification"
    TOOL_EXECUTION = "tool_execution"
    RESPONSE_GENERATION = "response_generation"
    FEEDBACK = "feedback"
    COMPLETED = "completed"

class CustomerServiceWorkflow:
    """客户服务工作流"""
    
    def __init__(self, agent):
        self.agent = agent
        self.state = CustomerWorkflowState.GREETING
        self.context = {}
    
    def run(self, customer_id: str, message: str) -> Dict[str, Any]:
        """运行工作流"""
        # 1. 问候
        if self.state == CustomerWorkflowState.GREETING:
            return self._handle_greeting(customer_id)
        
        # 2. 意图识别
        elif self.state == CustomerWorkflowState.INTENT_CLASSIFICATION:
            return self._classify_intent(message)
        
        # 3. 工具执行
        elif self.state == CustomerWorkflowState.TOOL_EXECUTION:
            return self._execute_tool(message)
        
        # 4. 响应生成
        elif self.state == CustomerWorkflowState.RESPONSE_GENERATION:
            return self._generate_response(message)
        
        # 5. 反馈收集
        elif self.state == CustomerWorkflowState.FEEDBACK:
            return self._collect_feedback(message)
        
        # 6. 完成
        else:
            return {"status": "completed"}
    
    def _handle_greeting(self, customer_id: str) -> Dict[str, Any]:
        """处理问候"""
        self.context["customer_id"] = customer_id
        self.state = CustomerWorkflowState.INTENT_CLASSIFICATION
        
        return {
            "response": "您好！我是智能客服，有什么可以帮您的吗？",
            "next_state": self.state.value
        }
    
    def _classify_intent(self, message: str) -> Dict[str, Any]:
        """识别意图"""
        # 使用 Agent 识别意图
        intent = self.agent.classify_intent(message)
        
        self.context["intent"] = intent
        self.context["message"] = message
        
        # 如果需要工具，跳转到工具执行
        if intent in ["order_query", "refund", "complaint"]:
            self.state = CustomerWorkflowState.TOOL_EXECUTION
        else:
            self.state = CustomerWorkflowState.RESPONSE_GENERATION
        
        return {
            "intent": intent,
            "next_state": self.state.value
        }
    
    def _execute_tool(self, message: str) -> Dict[str, Any]:
        """执行工具"""
        intent = self.context["intent"]
        
        # 根据意图选择工具
        tool_name = self._select_tool(intent)
        
        # 执行工具
        result = self.agent.execute_tool(tool_name, {
            "customer_id": self.context["customer_id"],
            "message": message
        })
        
        self.context["tool_result"] = result
        self.state = CustomerWorkflowState.RESPONSE_GENERATION
        
        return {
            "tool_result": result,
            "next_state": self.state.value
        }
    
    def _generate_response(self, message: str) -> Dict[str, Any]:
        """生成响应"""
        # 使用 Agent 生成响应
        response = self.agent.generate_response(
            message=message,
            context=self.context
        )
        
        self.context["response"] = response
        self.state = CustomerWorkflowState.FEEDBACK
        
        return {
            "response": response,
            "next_state": self.state.value
        }
    
    def _collect_feedback(self, message: str) -> Dict[str, Any]:
        """收集反馈"""
        # 询问满意度
        if "满意度" not in self.context:
            self.context["asked_feedback"] = True
            return {
                "response": "请问您对本次服务满意吗？（1-5 分）",
                "next_state": self.state.value
            }
        else:
            # 记录反馈
            self.context["feedback"] = message
            self.state = CustomerWorkflowState.COMPLETED
            
            return {
                "response": "感谢您的反馈！祝您生活愉快！",
                "next_state": self.state.value
            }
    
    def _select_tool(self, intent: str) -> str:
        """选择工具"""
        tool_map = {
            "order_query": "query_order",
            "refund": "create_refund",
            "complaint": "create_ticket"
        }
        
        return tool_map.get(intent, "default")
```

---

## 🔄 工作流 2: 代码审查流程

```python
"""
代码审查工作流
自动化的代码审查流程
"""

class CodeReviewWorkflow:
    """代码审查工作流"""
    
    def __init__(self, agent):
        self.agent = agent
        self.steps = [
            "static_analysis",
            "llm_review",
            "security_check",
            "performance_check",
            "generate_report"
        ]
        self.current_step = 0
        self.results = {}
    
    def run(self, code: str) -> Dict[str, Any]:
        """运行工作流"""
        for step in self.steps:
            result = self._execute_step(step, code)
            self.results[step] = result
        
        # 生成最终报告
        final_report = self._generate_final_report()
        
        return final_report
    
    def _execute_step(self, step: str, code: str) -> Dict[str, Any]:
        """执行步骤"""
        if step == "static_analysis":
            return self._static_analysis(code)
        elif step == "llm_review":
            return self._llm_review(code)
        elif step == "security_check":
            return self._security_check(code)
        elif step == "performance_check":
            return self._performance_check(code)
        else:
            return {}
    
    def _static_analysis(self, code: str) -> Dict[str, Any]:
        """静态分析"""
        # 使用 flake8
        issues = self.agent.run_static_analysis(code)
        
        return {
            "issues": issues,
            "score": self._calculate_score(issues)
        }
    
    def _llm_review(self, code: str) -> Dict[str, Any]:
        """LLM 审查"""
        suggestions = self.agent.review_with_llm(code)
        
        return {
            "suggestions": suggestions
        }
    
    def _security_check(self, code: str) -> Dict[str, Any]:
        """安全检查"""
        vulnerabilities = self.agent.check_security(code)
        
        return {
            "vulnerabilities": vulnerabilities,
            "risk_level": self._assess_risk(vulnerabilities)
        }
    
    def _performance_check(self, code: str) -> Dict[str, Any]:
        """性能检查"""
        performance_issues = self.agent.check_performance(code)
        
        return {
            "issues": performance_issues
        }
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """生成最终报告"""
        # 计算总分
        total_score = sum(
            result.get("score", 100)
            for result in self.results.values()
        ) / len(self.steps)
        
        # 确定建议
        if total_score >= 80:
            recommendation = "批准合并"
        elif total_score >= 60:
            recommendation = "需要修改"
        else:
            recommendation = "拒绝合并"
        
        return {
            "total_score": total_score,
            "recommendation": recommendation,
            "details": self.results
        }
    
    def _calculate_score(self, issues: List) -> int:
        """计算分数"""
        # 基础分数 100
        score = 100
        
        # 每个问题扣分
        for issue in issues:
            severity = issue.get("severity", "minor")
            if severity == "error":
                score -= 10
            elif severity == "warning":
                score -= 5
            else:
                score -= 2
        
        return max(0, score)
    
    def _assess_risk(self, vulnerabilities: List) -> str:
        """评估风险"""
        if not vulnerabilities:
            return "low"
        elif len(vulnerabilities) <= 3:
            return "medium"
        else:
            return "high"
```

---

**生成时间**: 2026-03-27 13:30 GMT+8
