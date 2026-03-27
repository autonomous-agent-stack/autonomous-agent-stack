# AI Agent API 文档生成器

> **版本**: v1.0
> **更新时间**: 2026-03-27
> **用途**: 自动生成 Agent API 文档

---

## 🚀 快速开始

### 安装

```bash
pip install openapi-spec-generator
```

### 基础用法

```python
from agent_doc_generator import AgentDocGenerator

# 创建文档生成器
generator = AgentDocGenerator(
    title="智能客服 API",
    version="1.0.0",
    description="智能客服 Agent API 文档"
)

# 添加端点
generator.add_endpoint(
    path="/chat",
    method="POST",
    summary="对话接口",
    description="与智能客服进行对话",
    request_body={
        "customer_id": "string",
        "message": "string"
    },
    response={
        "response": "string",
        "intent": "string",
        "confidence": "float"
    }
)

# 生成文档
generator.generate(output_format="openapi")
```

---

## 📝 完整实现

```python
"""
Agent API 文档生成器
自动从代码生成 OpenAPI 文档
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import json
import yaml

@dataclass
class Endpoint:
    """API 端点"""
    path: str
    method: str
    summary: str
    description: str
    request_body: Dict[str, Any]
    response: Dict[str, Any]
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    security: List[str] = field(default_factory=list)

class AgentDocGenerator:
    """Agent API 文档生成器"""
    
    def __init__(
        self,
        title: str,
        version: str,
        description: str = "",
        base_url: str = "http://localhost:8000"
    ):
        self.title = title
        self.version = version
        self.description = description
        self.base_url = base_url
        self.endpoints: List[Endpoint] = []
        self.schemas: Dict[str, Any] = {}
        self.security_schemes: Dict[str, Any] = {}
    
    def add_endpoint(
        self,
        path: str,
        method: str,
        summary: str,
        description: str,
        request_body: Dict[str, Any],
        response: Dict[str, Any],
        parameters: List[Dict[str, Any]] = None,
        tags: List[str] = None,
        security: List[str] = None
    ):
        """添加端点"""
        endpoint = Endpoint(
            path=path,
            method=method.lower(),
            summary=summary,
            description=description,
            request_body=request_body,
            response=response,
            parameters=parameters or [],
            tags=tags or [],
            security=security or []
        )
        
        self.endpoints.append(endpoint)
    
    def add_schema(self, name: str, schema: Dict[str, Any]):
        """添加数据模型"""
        self.schemas[name] = schema
    
    def add_security_scheme(self, name: str, scheme: Dict[str, Any]):
        """添加安全方案"""
        self.security_schemes[name] = scheme
    
    def generate_openapi(self) -> Dict[str, Any]:
        """生成 OpenAPI 文档"""
        openapi = {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": self.description
            },
            "servers": [
                {
                    "url": self.base_url,
                    "description": "API Server"
                }
            ],
            "paths": {},
            "components": {
                "schemas": self.schemas,
                "securitySchemes": self.security_schemes
            }
        }
        
        # 添加端点
        for endpoint in self.endpoints:
            path_item = openapi["paths"].setdefault(endpoint.path, {})
            
            path_item[endpoint.method] = {
                "summary": endpoint.summary,
                "description": endpoint.description,
                "tags": endpoint.tags,
                "requestBody": self._build_request_body(endpoint.request_body),
                "responses": {
                    "200": self._build_response(endpoint.response)
                }
            }
            
            # 添加参数
            if endpoint.parameters:
                path_item[endpoint.method]["parameters"] = endpoint.parameters
            
            # 添加安全
            if endpoint.security:
                path_item[endpoint.method]["security"] = endpoint.security
        
        return openapi
    
    def _build_request_body(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """构建请求体"""
        properties = {}
        required = []
        
        for key, value in body.items():
            if isinstance(value, str):
                properties[key] = {"type": "string"}
            elif isinstance(value, int):
                properties[key] = {"type": "integer"}
            elif isinstance(value, float):
                properties[key] = {"type": "number"}
            elif isinstance(value, bool):
                properties[key] = {"type": "boolean"}
            elif isinstance(value, dict):
                properties[key] = {"type": "object"}
            elif isinstance(value, list):
                properties[key] = {"type": "array"}
            
            required.append(key)
        
        return {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": required,
                        "properties": properties
                    }
                }
            }
        }
    
    def _build_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """构建响应"""
        properties = {}
        
        for key, value in response.items():
            if isinstance(value, str):
                properties[key] = {"type": "string"}
            elif isinstance(value, int):
                properties[key] = {"type": "integer"}
            elif isinstance(value, float):
                properties[key] = {"type": "number"}
            elif isinstance(value, bool):
                properties[key] = {"type": "boolean"}
        
        return {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": properties
                    }
                }
            }
        }
    
    def export_json(self, filename: str):
        """导出为 JSON"""
        openapi = self.generate_openapi()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(openapi, f, ensure_ascii=False, indent=2)
    
    def export_yaml(self, filename: str):
        """导出为 YAML"""
        openapi = self.generate_openapi()
        
        with open(filename, 'w', encoding='utf-8') as f:
            yaml.dump(openapi, f, allow_unicode=True, default_flow_style=False)
    
    def generate_markdown(self) -> str:
        """生成 Markdown 文档"""
        md = f"""# {self.title}

> **版本**: {self.version}
> **Base URL**: {self.base_url}

{self.description}

---

## 📋 目录

"""
        
        # 生成目录
        for endpoint in self.endpoints:
            md += f"- [{endpoint.method.upper()} {endpoint.path}](#{endpoint.method}{endpoint.path.replace('/', '-')})\n"
        
        md += "\n---\n\n"
        
        # 生成端点文档
        for endpoint in self.endpoints:
            md += self._endpoint_to_markdown(endpoint)
        
        return md
    
    def _endpoint_to_markdown(self, endpoint: Endpoint) -> str:
        """端点转 Markdown"""
        md = f"""## {endpoint.method.upper()} {endpoint.path}

**摘要**: {endpoint.summary}

**描述**: {endpoint.description}

### 请求

**方法**: `{endpoint.method.upper()}`

**路径**: `{endpoint.path}`

"""
        
        # 请求体
        if endpoint.request_body:
            md += "**请求体**:\n\n```json\n"
            md += json.dumps(endpoint.request_body, ensure_ascii=False, indent=2)
            md += "\n```\n\n"
        
        # 响应
        if endpoint.response:
            md += "### 响应\n\n```json\n"
            md += json.dumps(endpoint.response, ensure_ascii=False, indent=2)
            md += "\n```\n\n"
        
        md += "---\n\n"
        
        return md


# 使用示例
if __name__ == "__main__":
    # 创建文档生成器
    generator = AgentDocGenerator(
        title="智能客服 API",
        version="1.0.0",
        description="智能客服 Agent API 文档",
        base_url="https://api.example.com"
    )
    
    # 添加安全方案
    generator.add_security_scheme(
        "BearerAuth",
        {
            "type": "http",
            "scheme": "bearer"
        }
    )
    
    # 添加端点
    generator.add_endpoint(
        path="/chat",
        method="POST",
        summary="对话接口",
        description="与智能客服进行对话",
        request_body={
            "customer_id": "string",
            "message": "string"
        },
        response={
            "response": "string",
            "intent": "string",
            "confidence": "float"
        },
        tags=["Chat"],
        security=["BearerAuth"]
    )
    
    generator.add_endpoint(
        path="/history/{customer_id}",
        method="GET",
        summary="获取对话历史",
        description="获取指定客户的对话历史",
        request_body={},
        response={
            "history": [
                {
                    "role": "string",
                    "content": "string",
                    "timestamp": "string"
                }
            ]
        },
        parameters=[
            {
                "name": "customer_id",
                "in": "path",
                "required": True,
                "schema": {"type": "string"}
            }
        ],
        tags=["History"],
        security=["BearerAuth"]
    )
    
    # 导出文档
    generator.export_json("openapi.json")
    generator.export_yaml("openapi.yaml")
    
    # 生成 Markdown
    markdown = generator.generate_markdown()
    with open("API.md", 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    print("✅ 文档生成完成")
```

---

**生成时间**: 2026-03-27 13:05 GMT+8
