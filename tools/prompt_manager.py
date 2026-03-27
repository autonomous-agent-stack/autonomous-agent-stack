#!/usr/bin/env python3
"""
Prompt 模板管理器
用于管理和组织 Prompt 模板
"""

from typing import Dict, List, Optional
from string import Template
import json

class PromptTemplate:
    """Prompt 模板"""
    
    def __init__(self, name: str, template: str, description: str = ""):
        """
        初始化 Prompt 模板
        
        Args:
            name: 模板名称
            template: 模板内容
            description: 模板描述
        """
        self.name = name
        self.template = template
        self.description = description
    
    def render(self, **kwargs) -> str:
        """
        渲染模板
        
        Args:
            **kwargs: 模板变量
        
        Returns:
            渲染后的 Prompt
        """
        try:
            return Template(self.template).substitute(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing template variable: {e}")

class PromptManager:
    """Prompt 模板管理器"""
    
    def __init__(self):
        """初始化管理器"""
        self.templates: Dict[str, PromptTemplate] = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """加载默认模板"""
        # ReAct Agent 模板
        self.add_template(
            "react_agent",
            """Answer the following questions as best you can. You have access to the following tools:

$tools_description

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [$tool_names]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: $question

Thought:""",
            "ReAct Agent 提示模板"
        )
        
        # RAG Agent 模板
        self.add_template(
            "rag_agent",
            """Based on the following documents, answer the question. If the information is not in the documents, clearly state that.

Documents:
$context

Question: $question

Answer:""",
            "RAG Agent 提示模板"
        )
        
        # Code Review 模板
        self.add_template(
            "code_review",
            """Review the following code and provide feedback:

Code:
```
$code
```

Please provide:
1. Code quality assessment
2. Potential bugs or issues
3. Performance suggestions
4. Best practices recommendations

Review:""",
            "代码审查提示模板"
        )
        
        # Tool Definition 模板
        self.add_template(
            "tool_definition",
            """{
    "name": "$tool_name",
    "description": "$description",
    "parameters": {
        "type": "object",
        "properties": {
            $parameters
        },
        "required": [$required_params]
    }
}""",
            "工具定义模板"
        )
    
    def add_template(self, name: str, template: str, description: str = ""):
        """
        添加模板
        
        Args:
            name: 模板名称
            template: 模板内容
            description: 模板描述
        """
        self.templates[name] = PromptTemplate(name, template, description)
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """
        获取模板
        
        Args:
            name: 模板名称
        
        Returns:
            Prompt 模板
        """
        return self.templates.get(name)
    
    def render(self, name: str, **kwargs) -> str:
        """
        渲染模板
        
        Args:
            name: 模板名称
            **kwargs: 模板变量
        
        Returns:
            渲染后的 Prompt
        """
        template = self.get_template(name)
        if not template:
            raise ValueError(f"Template not found: {name}")
        
        return template.render(**kwargs)
    
    def list_templates(self) -> List[Dict[str, str]]:
        """
        列出所有模板
        
        Returns:
            模板列表
        """
        return [
            {
                "name": name,
                "description": template.description
            }
            for name, template in self.templates.items()
        ]
    
    def export_templates(self, filename: str):
        """
        导出模板到文件
        
        Args:
            filename: 文件名
        """
        data = {
            name: {
                "template": template.template,
                "description": template.description
            }
            for name, template in self.templates.items()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 模板已导出到 {filename}")
    
    def import_templates(self, filename: str):
        """
        从文件导入模板
        
        Args:
            filename: 文件名
        """
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for name, template_data in data.items():
            self.add_template(
                name,
                template_data["template"],
                template_data.get("description", "")
            )
        
        print(f"✅ 已导入 {len(data)} 个模板")


# 使用示例
if __name__ == "__main__":
    manager = PromptManager()
    
    # 列出所有模板
    print("📋 可用模板:")
    for template in manager.list_templates():
        print(f"  - {template['name']}: {template['description']}")
    
    # 渲染 ReAct Agent 模板
    prompt = manager.render(
        "react_agent",
        tools_description="- search: 搜索互联网\n- calculator: 执行计算",
        tool_names="search, calculator",
        question="北京到上海的距离是多少？"
    )
    
    print("\n📝 渲染后的 Prompt:")
    print(prompt)
    
    # 导出模板
    manager.export_templates("prompt_templates.json")
