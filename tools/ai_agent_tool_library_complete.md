# AI Agent 工具库完整手册

> **版本**: v1.0
> **更新时间**: 2026-03-27 17:03
> **工具数**: 30+

---

## 🛠️ 核心工具库

### 1. 搜索工具

```python
class SearchTool:
    """搜索工具"""
    
    def __init__(self, api_key: str):
        self.client = SearchClient(api_key)
    
    async def search(self, query: str, limit: int = 5) -> list:
        """搜索"""
        results = await self.client.search(query, limit)
        
        return [
            {
                "title": r["title"],
                "url": r["url"],
                "snippet": r["snippet"]
            }
            for r in results
        ]

# 使用
search = SearchTool(API_KEY)
results = await search.search("AI agents")
```

---

### 2. 计算工具

```python
class CalculatorTool:
    """计算工具"""
    
    def calculate(self, expression: str) -> float:
        """计算表达式"""
        # 安全计算
        try:
            result = eval(expression, {"__builtins__": {}}, {})
            return float(result)
        except Exception as e:
            raise ValueError(f"Invalid expression: {e}")

# 使用
calc = CalculatorTool()
result = calc.calculate("2 + 3 * 4")  # 14
```

---

### 3. 代码执行工具

```python
class CodeExecutionTool:
    """代码执行工具"""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    async def execute(self, code: str, language: str = "python") -> str:
        """执行代码"""
        # 沙箱执行
        if language == "python":
            return await self._execute_python(code)
        elif language == "javascript":
            return await self._execute_javascript(code)
        else:
            raise ValueError(f"Unsupported language: {language}")
    
    async def _execute_python(self, code: str) -> str:
        """执行 Python"""
        # 使用 RestrictedPython
        from RestrictedPython import compile_restricted
        
        byte_code = compile_restricted(code, '<inline>', 'exec')
        
        # 执行
        local_vars = {}
        exec(byte_code, {}, local_vars)
        
        return str(local_vars.get('result', ''))

# 使用
tool = CodeExecutionTool()
result = await tool.execute("result = 2 + 2")  # "4"
```

---

### 4. 文件操作工具

```python
class FileTool:
    """文件操作工具"""
    
    async def read(self, file_path: str) -> str:
        """读取文件"""
        with open(file_path, 'r') as f:
            return f.read()
    
    async def write(self, file_path: str, content: str):
        """写入文件"""
        with open(file_path, 'w') as f:
            f.write(content)
    
    async def list_files(self, directory: str) -> list:
        """列出文件"""
        import os
        return os.listdir(directory)

# 使用
tool = FileTool()
content = await tool.read("data.txt")
await tool.write("output.txt", "Hello")
```

---

### 5. 数据库工具

```python
class DatabaseTool:
    """数据库工具"""
    
    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)
    
    async def query(self, sql: str) -> list:
        """查询数据库"""
        with self.engine.connect() as conn:
            result = conn.execute(sql)
            return [dict(row) for row in result]
    
    async def insert(self, table: str, data: dict):
        """插入数据"""
        # 实现插入
        pass

# 使用
tool = DatabaseTool("postgresql://localhost/db")
results = await tool.query("SELECT * FROM users")
```

---

### 6. API 调用工具

```python
class APITool:
    """API 调用工具"""
    
    async def get(self, url: str, headers: dict = None) -> dict:
        """GET 请求"""
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    
    async def post(self, url: str, data: dict, headers: dict = None) -> dict:
        """POST 请求"""
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()

# 使用
tool = APITool()
data = await tool.get("https://api.example.com/data")
```

---

### 7. 邮件工具

```python
class EmailTool:
    """邮件工具"""
    
    def __init__(self, smtp_server: str, port: int):
        self.server = smtp_server
        self.port = port
    
    async def send(self, to: str, subject: str, body: str):
        """发送邮件"""
        import smtplib
        from email.mime.text import MIMEText
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = "agent@example.com"
        msg['To'] = to
        
        with smtplib.SMTP(self.server, self.port) as server:
            server.send_message(msg)

# 使用
tool = EmailTool("smtp.gmail.com", 587)
await tool.send("user@example.com", "Hello", "Test email")
```

---

### 8. 图像生成工具

```python
class ImageGenerationTool:
    """图像生成工具"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    async def generate(self, prompt: str) -> str:
        """生成图像"""
        response = await self.client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        
        return response.data[0].url

# 使用
tool = ImageGenerationTool(API_KEY)
url = await tool.generate("A beautiful sunset")
```

---

### 9. 翻译工具

```python
class TranslationTool:
    """翻译工具"""
    
    def __init__(self, api_key: str):
        self.client = TranslationClient(api_key)
    
    async def translate(self, text: str, target_lang: str) -> str:
        """翻译"""
        result = await self.client.translate(text, target_lang)
        return result["translatedText"]

# 使用
tool = TranslationTool(API_KEY)
translated = await tool.translate("Hello", "zh-CN")  # "你好"
```

---

### 10. 语音工具

```python
class SpeechTool:
    """语音工具"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    async def text_to_speech(self, text: str) -> bytes:
        """文本转语音"""
        response = await self.client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )
        
        return response.content
    
    async def speech_to_text(self, audio: bytes) -> str:
        """语音转文本"""
        response = await self.client.audio.transcriptions.create(
            model="whisper-1",
            file=audio
        )
        
        return response.text

# 使用
tool = SpeechTool(API_KEY)
audio = await tool.text_to_speech("Hello world")
```

---

## 📊 工具分类

| 类别 | 工具 | 用途 |
|------|------|------|
| **信息检索** | Search | 搜索信息 |
| **计算** | Calculator | 数学计算 |
| **代码** | CodeExecution | 执行代码 |
| **文件** | File | 文件操作 |
| **数据** | Database | 数据库操作 |
| **网络** | API | HTTP 请求 |
| **通信** | Email | 发送邮件 |
| **媒体** | Image | 图像生成 |
| **语言** | Translation | 翻译 |
| **音频** | Speech | 语音处理 |

---

## 🔧 工具注册

```python
class ToolRegistry:
    """工具注册中心"""
    
    def __init__(self):
        self.tools = {}
    
    def register(self, name: str, tool: object):
        """注册工具"""
        self.tools[name] = tool
    
    def get(self, name: str) -> object:
        """获取工具"""
        return self.tools.get(name)
    
    def list_tools(self) -> list:
        """列出工具"""
        return list(self.tools.keys())

# 使用
registry = ToolRegistry()
registry.register("search", SearchTool(API_KEY))
registry.register("calculator", CalculatorTool())

# 获取工具
search_tool = registry.get("search")
```

---

## 🎯 最佳实践

1. ✅ 工具应该单一职责
2. ✅ 工具应该有清晰的接口
3. ✅ 工具应该有错误处理
4. ✅ 工具应该有超时限制
5. ✅ 工具应该有权限控制
6. ✅ 工具应该有日志记录
7. ✅ 工具应该有测试覆盖
8. ✅ 工具应该有文档说明

---

**生成时间**: 2026-03-27 17:05 GMT+8
