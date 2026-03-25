# 将视觉功能与工具结合使用（GLM-5 适配版）

> 适配时间：2026-03-25 13:58
> 原版：vision_with_tools.ipynb
> 目标：适配为 GLM-5 API

---

## 📋 适配清单

### ✅ 已完成
- [x] 分析原 notebook 结构
- [x] 确定适配点
- [x] 创建适配计划

### ⏳ 待完成
- [ ] 替换 import 语句
- [ ] 替换客户端初始化
- [ ] 替换模型名称
- [ ] 调整工具格式（如需要）
- [ ] 替换 API 调用
- [ ] 测试验证

---

## 🔧 适配详情

### 1. Import 语句

**原版**：
```python
import base64
from anthropic import Anthropic
from IPython.display import Image
```

**适配版**：
```python
import base64
from zhipuai import ZhipuAI
from IPython.display import Image
```

**状态**：✅ 已确认

---

### 2. 客户端初始化

**原版**：
```python
client = Anthropic()
MODEL_NAME = "claude-opus-4-1"
```

**适配版**：
```python
client = ZhipuAI()
MODEL_NAME = "glm-4"
```

**状态**：✅ 已确认

---

### 3. 工具定义

**原版**：
```python
nutrition_tool = {
    "name": "print_nutrition_info",
    "description": "Extracts nutrition information from an image of a nutrition label",
    "input_schema": {
        "type": "object",
        "properties": {
            "calories": {"type": "integer", "description": "The number of calories per serving"},
            "total_fat": {"type": "integer", "description": "The amount of total fat in grams per serving"},
            "cholesterol": {"type": "integer", "description": "The amount of cholesterol in milligrams per serving"},
            "total_carbs": {"type": "integer", "description": "The amount of total carbohydrates in grams per serving"},
            "protein": {"type": "integer", "description": "The amount of protein in grams per serving"}
        },
        "required": ["calories", "total_fat", "cholesterol", "total_carbs", "protein"]
    }
}
```

**GLM-5 格式（OpenAI 兼容）**：
```python
nutrition_tool = {
    "type": "function",
    "function": {
        "name": "print_nutrition_info",
        "description": "Extracts nutrition information from an image of a nutrition label",
        "parameters": {
            "type": "object",
            "properties": {
                "calories": {"type": "integer", "description": "The number of calories per serving"},
                "total_fat": {"type": "integer", "description": "The amount of total fat in grams per serving"},
                "cholesterol": {"type": "integer", "description": "The amount of cholesterol in milligrams per serving"},
                "total_carbs": {"type": "integer", "description": "The amount of total carbohydrates in grams per serving"},
                "protein": {"type": "integer", "description": "The amount of protein in grams per serving"}
            },
            "required": ["calories", "total_fat", "cholesterol", "total_carbs", "protein"]
        }
    }
}
```

**状态**：✅ 已确认

**关键差异**：
- Claude: `input_schema`
- GLM-5: `parameters`（嵌套在 `function` 下）

---

### 4. API 调用

**原版**：
```python
response = client.messages.create(
    model=MODEL_NAME,
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_media_type,
                        "data": image_data
                    }
                },
                {
                    "type": "text",
                    "text": "请使用 print_nutrition_info 工具从此营养标签图像中提取营养信息。"
                }
            ]
        }
    ],
    tools=[nutrition_tool]
)
```

**适配版（GLM-5）**：
```python
response = client.chat.completions.create(
    model=MODEL_NAME,
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{image_media_type};base64,{image_data}"
                    }
                },
                {
                    "type": "text",
                    "text": "请使用 print_nutrition_info 工具从此营养标签图像中提取营养信息。"
                }
            ]
        }
    ],
    tools=[nutrition_tool]
)
```

**状态**：✅ 已确认

**关键差异**：
1. 方法名：`messages.create` → `chat.completions.create`
2. 图片格式：
   - Claude: `{"type": "image", "source": {...}}`
   - GLM-5: `{"type": "image_url", "image_url": {"url": "data:...;base64,..."}}`

---

### 5. 响应处理

**原版**：
```python
print(response.content[0].text)
```

**适配版**：
```python
print(response.choices[0].message.content)
```

**状态**：✅ 已确认

**关键差异**：
- Claude: `response.content[0].text`
- GLM-5: `response.choices[0].message.content`

---

## ⚠️ 注意事项

### 1. 图片格式差异

**Claude**：
```python
{
    "type": "image",
    "source": {
        "type": "base64",
        "media_type": image_media_type,
        "data": image_data
    }
}
```

**GLM-5（OpenAI 兼容）**：
```python
{
    "type": "image_url",
    "image_url": {
        "url": f"data:{image_media_type};base64,{image_data}"
    }
}
```

### 2. 工具调用结果处理

需要验证 GLM-5 的工具调用结果格式是否与 Claude 一致。

---

## 📊 适配进度

| 项目 | 状态 | 备注 |
|------|------|------|
| Import 语句 | ✅ | 已确认 |
| 客户端初始化 | ✅ | 已确认 |
| 工具定义 | ✅ | 已确认 |
| API 调用 | ✅ | 已确认 |
| 响应处理 | ✅ | 已确认 |
| 创建适配文件 | ⏳ | 待完成 |
| 测试验证 | ⏳ | 待完成 |

---

## 🚀 下一步

1. **创建适配文件**（14:00-14:30，50% 火力）
   - 创建 `glm5_adaptation/vision_with_tools_glm5.ipynb`
   - 应用所有适配修改

2. **测试验证**（14:30-15:00，50% 火力）
   - 运行适配后的 notebook
   - 验证功能
   - 记录问题

---

**状态**：🔥🔥 75% 火力阶段
**剩余时间**：2 分钟
**完成度**：80%（分析完成，待创建文件）
