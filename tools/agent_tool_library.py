# AI Agent 工具库完整指南

> **版本**: v1.0
> **更新时间**: 2026-03-27 14:00
> **工具数**: 30+

---

## 🛠️ 核心工具

### 1. 搜索工具

```python
class SearchTool:
    """互联网搜索工具"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def search(self, query: str, limit: int = 5) -> List[dict]:
        """搜索互联网"""
        # 调用搜索 API
        results = google_search(query, limit)
        
        return [
            {
                "title": r["title"],
                "url": r["link"],
                "snippet": r["snippet"]
            }
            for r in results
        ]
    
    def get_schema(self):
        """返回工具 schema"""
        return {
            "name": "search",
            "description": "搜索互联网获取信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回结果数量",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
```

---

### 2. 计算工具

```python
class CalculatorTool:
    """数学计算工具"""
    
    def calculate(self, expression: str) -> float:
        """计算数学表达式"""
        try:
            # 安全计算
            result = eval(expression, {"__builtins__": None}, {})
            return float(result)
        except Exception as e:
            raise ValueError(f"计算错误: {e}")
    
    def get_schema(self):
        return {
            "name": "calculator",
            "description": "计算数学表达式",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，如 '2 + 2'"
                    }
                },
                "required": ["expression"]
            }
        }
```

---

### 3. 代码执行工具

```python
class CodeExecutionTool:
    """代码执行工具"""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    def execute(self, code: str, language: str = "python") -> dict:
        """执行代码"""
        if language == "python":
            return self._execute_python(code)
        else:
            raise ValueError(f"不支持的语言: {language}")
    
    def _execute_python(self, code: str) -> dict:
        """执行 Python 代码"""
        try:
            # 创建沙箱环境
            local_vars = {}
            
            # 执行代码
            exec(code, {"__builtins__": safe_builtins}, local_vars)
            
            # 获取结果
            result = local_vars.get("result", None)
            
            return {
                "success": True,
                "result": str(result),
                "variables": list(local_vars.keys())
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_schema(self):
        return {
            "name": "code_execute",
            "description": "执行代码",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "要执行的代码"
                    },
                    "language": {
                        "type": "string",
                        "description": "编程语言",
                        "enum": ["python"],
                        "default": "python"
                    }
                },
                "required": ["code"]
            }
        }
```

---

### 4. 文件操作工具

```python
class FileTool:
    """文件操作工具"""
    
    def read(self, file_path: str) -> str:
        """读取文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise IOError(f"读取文件失败: {e}")
    
    def write(self, file_path: str, content: str) -> bool:
        """写入文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            raise IOError(f"写入文件失败: {e}")
    
    def list_files(self, directory: str) -> List[str]:
        """列出文件"""
        try:
            return os.listdir(directory)
        except Exception as e:
            raise IOError(f"列出文件失败: {e}")
    
    def get_schema(self):
        return {
            "name": "file_operations",
            "description": "文件操作",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["read", "write", "list"]
                    },
                    "file_path": {
                        "type": "string",
                        "description": "文件路径"
                    },
                    "content": {
                        "type": "string",
                        "description": "写入内容（仅 write 操作）"
                    }
                },
                "required": ["operation", "file_path"]
            }
        }
```

---

### 5. 数据库工具

```python
class DatabaseTool:
    """数据库操作工具"""
    
    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)
    
    def query(self, sql: str) -> List[dict]:
        """执行查询"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql))
                
                return [
                    dict(row._mapping)
                    for row in result
                ]
        except Exception as e:
            raise DatabaseError(f"查询失败: {e}")
    
    def execute(self, sql: str) -> int:
        """执行更新"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql))
                conn.commit()
                
                return result.rowcount
        except Exception as e:
            raise DatabaseError(f"执行失败: {e}")
    
    def get_schema(self):
        return {
            "name": "database",
            "description": "数据库操作",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["query", "execute"]
                    },
                    "sql": {
                        "type": "string",
                        "description": "SQL 语句"
                    }
                },
                "required": ["operation", "sql"]
            }
        }
```

---

### 6. API 调用工具

```python
class APITool:
    """API 调用工具"""
    
    def call(
        self,
        url: str,
        method: str = "GET",
        headers: dict = None,
        body: dict = None
    ) -> dict:
        """调用 API"""
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=body,
                timeout=10
            )
            
            response.raise_for_status()
            
            return response.json()
        
        except Exception as e:
            raise APIError(f"API 调用失败: {e}")
    
    def get_schema(self):
        return {
            "name": "api_call",
            "description": "调用外部 API",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "API URL"
                    },
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "DELETE"],
                        "default": "GET"
                    },
                    "headers": {
                        "type": "object",
                        "description": "请求头"
                    },
                    "body": {
                        "type": "object",
                        "description": "请求体"
                    }
                },
                "required": ["url"]
            }
        }
```

---

### 7. 邮件发送工具

```python
class EmailTool:
    """邮件发送工具"""
    
    def __init__(self, smtp_server: str, port: int, username: str, password: str):
        self.smtp_server = smtp_server
        self.port = port
        self.username = username
        self.password = password
    
    def send(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool = False
    ) -> bool:
        """发送邮件"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = to
            msg['Subject'] = subject
            
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_server, self.port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            return True
        
        except Exception as e:
            raise EmailError(f"发送邮件失败: {e}")
    
    def get_schema(self):
        return {
            "name": "send_email",
            "description": "发送邮件",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "收件人邮箱"
                    },
                    "subject": {
                        "type": "string",
                        "description": "邮件主题"
                    },
                    "body": {
                        "type": "string",
                        "description": "邮件内容"
                    },
                    "html": {
                        "type": "boolean",
                        "description": "是否为 HTML 格式",
                        "default": false
                    }
                },
                "required": ["to", "subject", "body"]
            }
        }
```

---

## 📊 工具对比

| 工具 | 用途 | 复杂度 | 安全性 |
|------|------|--------|--------|
| **搜索** | 信息检索 | ⭐ | ⭐⭐⭐ |
| **计算** | 数学运算 | ⭐ | ⭐⭐⭐⭐ |
| **代码执行** | 运行代码 | ⭐⭐⭐ | ⭐⭐ |
| **文件操作** | 读写文件 | ⭐⭐ | ⭐⭐ |
| **数据库** | 数据操作 | ⭐⭐⭐ | ⭐⭐ |
| **API 调用** | 外部服务 | ⭐⭐ | ⭐⭐⭐ |
| **邮件** | 通信 | ⭐⭐ | ⭐⭐⭐ |

---

## 🔧 工具注册

```python
class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self.tools = {}
    
    def register(self, tool):
        """注册工具"""
        schema = tool.get_schema()
        self.tools[schema["name"]] = tool
    
    def get(self, name: str):
        """获取工具"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[dict]:
        """列出所有工具"""
        return [
            tool.get_schema()
            for tool in self.tools.values()
        ]

# 使用
registry = ToolRegistry()
registry.register(SearchTool(api_key="..."))
registry.register(CalculatorTool())
registry.register(FileTool())

# 获取工具
search = registry.get("search")
```

---

**生成时间**: 2026-03-27 14:05 GMT+8
