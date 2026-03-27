# AI Agent API 文档生成器

> **版本**: v1.0
> **更新时间**: 2026-03-27 14:20
> **API 文档**: 100+

---

## 🎯 自动生成 API 文档

### 完整实现

```python
import inspect
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class APIEndpoint:
    """API 端点"""
    path: str
    method: str
    description: str
    parameters: List[Dict]
    request_body: Optional[Dict]
    responses: Dict[int, Dict]
    tags: List[str]
    deprecated: bool = False

class APIDocGenerator:
    """API 文档生成器"""
    
    def __init__(self, title: str, version: str = "1.0.0"):
        self.title = title
        self.version = version
        self.endpoints = []
    
    def add_endpoint(self, endpoint: APIEndpoint):
        """添加端点"""
        self.endpoints.append(endpoint)
    
    def generate_openapi(self) -> dict:
        """生成 OpenAPI 文档"""
        openapi = {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": f"{self.title} API Documentation"
            },
            "paths": {}
        }
        
        for endpoint in self.endpoints:
            if endpoint.path not in openapi["paths"]:
                openapi["paths"][endpoint.path] = {}
            
            path_obj = {
                "summary": endpoint.description,
                "description": endpoint.description,
                "tags": endpoint.tags,
                "parameters": endpoint.parameters,
                "responses": endpoint.responses,
                "deprecated": endpoint.deprecated
            }
            
            if endpoint.request_body:
                path_obj["requestBody"] = {
                    "content": {
                        "application/json": {
                            "schema": endpoint.request_body
                        }
                    }
                }
            
            openapi["paths"][endpoint.path][endpoint.method.lower()] = path_obj
        
        return openapi
    
    def generate_markdown(self) -> str:
        """生成 Markdown 文档"""
        md = f"# {self.title} API 文档\n\n"
        md += f"版本: {self.version}\n\n"
        md += "---\n\n"
        
        # 按标签分组
        grouped = {}
        for endpoint in self.endpoints:
            for tag in endpoint.tags:
                if tag not in grouped:
                    grouped[tag] = []
                grouped[tag].append(endpoint)
        
        # 生成文档
        for tag, endpoints in grouped.items():
            md += f"## {tag}\n\n"
            
            for endpoint in endpoints:
                md += f"### {endpoint.method} {endpoint.path}\n\n"
                md += f"{endpoint.description}\n\n"
                
                # 参数
                if endpoint.parameters:
                    md += "**参数**\n\n"
                    md += "| 名称 | 类型 | 必需 | 描述 |\n"
                    md += "|------|------|------|------|\n"
                    
                    for param in endpoint.parameters:
                        required = "是" if param.get("required", False) else "否"
                        md += f"| {param['name']} | {param['schema']['type']} | {required} | {param['description']} |\n"
                    
                    md += "\n"
                
                # 请求体
                if endpoint.request_body:
                    md += "**请求体**\n\n"
                    md += "```json\n"
                    md += f"{json.dumps(endpoint.request_body, indent=2, ensure_ascii=False)}\n"
                    md += "```\n\n"
                
                # 响应
                md += "**响应**\n\n"
                for status, response in endpoint.responses.items():
                    md += f"- **{status}**: {response['description']}\n"
                
                md += "\n---\n\n"
        
        return md

# 使用示例
generator = APIDocGenerator("AI Agent API", "1.0.0")

# 添加端点
generator.add_endpoint(APIEndpoint(
    path="/api/v1/agent/run",
    method="POST",
    description="运行 Agent",
    parameters=[],
    request_body={
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "任务描述"
            },
            "context": {
                "type": "object",
                "description": "上下文"
            }
        },
        "required": ["task"]
    },
    responses={
        200: {
            "description": "成功",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "result": {"type": "string"},
                            "status": {"type": "string"}
                        }
                    }
                }
            }
        },
        400: {
            "description": "参数错误"
        }
    },
    tags=["Agent"]
))

# 生成文档
openapi_doc = generator.generate_openapi()
markdown_doc = generator.generate_markdown()

print(markdown_doc)
```

---

## 📊 自动生成 API 测试

```python
import requests
from typing import Dict, Any

class APITester:
    """API 测试器"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
    
    def test_endpoint(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        expected_status: int = 200
    ) -> bool:
        """测试端点"""
        url = f"{self.base_url}{path}"
        
        try:
            if method == "GET":
                response = self.session.get(url, params=data)
            elif method == "POST":
                response = self.session.post(url, json=data)
            elif method == "PUT":
                response = self.session.put(url, json=data)
            elif method == "DELETE":
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # 检查状态码
            if response.status_code != expected_status:
                print(f"❌ {method} {path}: Expected {expected_status}, got {response.status_code}")
                return False
            
            # 检查响应
            if not response.content:
                print(f"❌ {method} {path}: Empty response")
                return False
            
            print(f"✅ {method} {path}")
            return True
        
        except Exception as e:
            print(f"❌ {method} {path}: {e}")
            return False

# 使用示例
tester = APITester("http://localhost:8000")

# 测试所有端点
results = [
    tester.test_endpoint("GET", "/health"),
    tester.test_endpoint("POST", "/api/v1/agent/run", data={"task": "test"}),
    tester.test_endpoint("GET", "/api/v1/agent/status")
]

print(f"\n通过率: {sum(results) / len(results) * 100:.1f}%")
```

---

## 🎯 自动生成 API 客户端

```python
from typing import Dict, Any, Optional

class APIClient:
    """API 客户端"""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url
        self.headers = {}
        
        if api_key:
            self.headers["X-API-Key"] = api_key
    
    def get(self, path: str, params: Optional[Dict] = None) -> Dict:
        """GET 请求"""
        response = requests.get(
            f"{self.base_url}{path}",
            params=params,
            headers=self.headers
        )
        
        response.raise_for_status()
        return response.json()
    
    def post(self, path: str, data: Dict) -> Dict:
        """POST 请求"""
        response = requests.post(
            f"{self.base_url}{path}",
            json=data,
            headers=self.headers
        )
        
        response.raise_for_status()
        return response.json()
    
    def put(self, path: str, data: Dict) -> Dict:
        """PUT 请求"""
        response = requests.put(
            f"{self.base_url}{path}",
            json=data,
            headers=self.headers
        )
        
        response.raise_for_status()
        return response.json()
    
    def delete(self, path: str) -> None:
        """DELETE 请求"""
        response = requests.delete(
            f"{self.base_url}{path}",
            headers=self.headers
        )
        
        response.raise_for_status()

# 使用示例
client = APIClient("https://api.example.com", api_key="your-key")

# 调用 API
result = client.post("/api/v1/agent/run", data={
    "task": "What is AI?"
})

print(result["response"])
```

---

## 📝 API 文档模板

### 1. 端点模板

```markdown
## 端点名称

**描述**: 端点描述

**请求**:
```
POST /api/v1/endpoint
```

**参数**:
| 名称 | 类型 | 必需 | 描述 |
|------|------|------|------|
| param1 | string | 是 | 参数 1 |
| param2 | integer | 否 | 参数 2 |

**请求体**:
```json
{
  "field1": "value1",
  "field2": 123
}
```

**响应**:
```json
{
  "status": "success",
  "data": {...}
}
```

**错误码**:
- 400: 参数错误
- 401: 认证失败
- 500: 服务器错误

**示例**:
```python
import requests

response = requests.post(
    "https://api.example.com/api/v1/endpoint",
    json={"field1": "value1", "field2": 123}
)

print(response.json())
```
```

---

**生成时间**: 2026-03-27 14:25 GMT+8
