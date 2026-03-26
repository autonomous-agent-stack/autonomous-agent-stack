# 🔄 Function Calling 完整闭环流程

> **创建时间**: 2026-03-24 05:58
> **演示状态**: ✅ 成功

---

## 📊 完整闭环流程

```
1️⃣ 用户提问
   ↓
2️⃣ 大模型思考 → 决定调用工具
   ↓
3️⃣ 本地执行工具（Claude 写好的脚本）
   ↓
4️⃣ 结果返回大模型
   ↓
5️⃣ 大模型生成最终回复
```

---

## 🎯 核心机制

### 大模型的角色
- **只负责**：理解意图、提取参数、组织回复
- **不负责**：实际执行（由本地脚本完成）

### 本地脚本的角色
- **负责**：稳定、可靠的执行
- **优势**：可控、低成本、可调试

---

## 📝 实际代码示例

### 1. 定义工具说明书

```python
tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "generate_maru_pitch",
            "description": "当需要介绍玛露遮瑕膏时调用此工具",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "目标发布平台"
                    }
                },
                "required": ["platform"]
            }
        }
    }
]
```

### 2. 本地工具执行器

```python
class ToolExecutor:
    def execute(self, tool_name: str, arguments: dict) -> str:
        # 调用 Claude 写好的脚本
        if tool_name == "generate_maru_pitch":
            return generate_maru_pitch(**arguments)
```

### 3. 完整调用流程

```python
from litellm import completion

# 第一步：用户提问
messages = [{"role": "user", "content": "帮我生成小红书文案"}]

# 第二步：大模型决定调用工具
response = completion(
    model="deepseek/deepseek-chat",
    messages=messages,
    tools=tools_schema,
    tool_choice="auto"
)

# 第三步：执行工具
if response.choices[0].message.tool_calls:
    tool_call = response.choices[0].message.tool_calls[0]
    result = executor.execute(
        tool_call.function.name,
        json.loads(tool_call.function.arguments)
    )

    # 第四步：结果返回大模型
    messages.append({
        "role": "tool",
        "content": result
    })

    # 第五步：大模型生成最终回复
    final = completion(
        model="deepseek/deepseek-chat",
        messages=messages
    )

    print(final.choices[0].message.content)
```

---

## 💡 关键优势

### 1. 极低成本
- 大模型仅调用 2 次（决策 + 生成）
- 本地脚本执行（几乎零成本）
- 可使用廉价模型（DeepSeek、GLM-4-Air）

### 2. 高度可控
- 工具输入输出严格定义
- 本地脚本可调试
- 错误处理完善

### 3. 灵活扩展
- 添加新工具只需：
  1. 写 Python 函数
  2. 添加工具说明书
  3. 注册到执行器

---

## 🚀 最佳实践

### 第一步：用 Claude CLI 写 Skill
```bash
claude "帮我写一个抓取小红书数据的爬虫"
```

### 第二步：包装成标准函数
```python
def scrape_xiaohongshu(keyword: str) -> dict:
    """抓取小红书数据"""
    # Claude 生成的代码
    ...
    return {"status": "success", "data": result}
```

### 第三步：注册到 Agent
```python
executor.register("scrape_xiaohongshu", scrape_xiaohongshu)
```

---

## 📊 成本对比

| 方案 | API 调用次数 | 成本（每 100 次） |
|------|-------------|-----------------|
| **纯 Claude CLI** | 10-50 次 | $5-25 |
| **LiteLLM + Skill** | 2 次 | $0.02 |

**节省**: 99.9%

---

## 🎯 适用场景

### ✅ 适合
- 长期运行的自动化服务
- 需要稳定输出的生产环境
- 成本敏感的项目
- 多端接入（微信、飞书等）

### ❌ 不适合
- 快速原型验证
- 一次性数据处理
- 探索性任务

---

## 📚 参考资源

- **演示代码**: `/tmp/claude-to-skill-demo/complete_loop_demo.py`
- **LiteLLM 文档**: https://docs.litellm.ai
- **Function Calling 规范**: OpenAI API Reference

---

**大佬，完整闭环演示成功！核心流程已掌握！** 🚀
