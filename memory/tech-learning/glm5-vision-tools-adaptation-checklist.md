# vision_with_tools_glm5.ipynb

> 适配时间：2026-03-25 14:00
> 
> 原始文件：tool_use/vision_with_tools.ipynb (198 行)
> 
> 适配内容：Claude API → GLM-5 API

---

## 📝 适配说明

### 主要修改点

1. **Import 语句**
   ```python
   # Claude
   from anthropic import Anthropic
   
   # GLM-5
   from zhipuai import ZhipuAI
   ```

2. **客户端初始化**
   ```python
   # Claude
   client = Anthropic()
   
   # GLM-5
   client = ZhipuAI()
   ```

3. **API 调用**
   ```python
   # Claude
   response = client.messages.create(
       model="claude-opus-4-1",
       ...
   )
   
   # GLM-5
   response = client.chat.completions.create(
       model="glm-4",
       ...
   )
   ```

4. **图片格式**
   ```python
   # Claude
   {
       "type": "image",
       "source": {
           "type": "base64",
           "media_type": media_type,
           "data": image_data
       }
   }
   
   # GLM-5
   {
       "type": "image_url",
       "image_url": {
           "url": f"data:{media_type};base64,{image_data}"
       }
   }
   ```

5. **工具格式**
   ```python
   # Claude
   {
       "name": "nutrition_tool",
       "description": "...",
       "input_schema": {...}
   }
   
   # GLM-5
   {
       "type": "function",
       "function": {
           "name": "nutrition_tool",
           "description": "...",
           "parameters": {...}
       }
   }
   ```

6. **响应处理**
   ```python
   # Claude
   response.content[0].text
   response.stop_reason
   
   # GLM-5
   response.choices[0].message.content
   response.choices[0].finish_reason
   ```

---

## ✅ 适配状态

- [ ] Import 语句替换
- [ ] 客户端初始化替换
- [ ] 图片格式调整
- [ ] 工具格式调整
- [ ] API 调用替换
- [ ] 响应处理调整
- [ ] 测试验证

---

**状态**：⏳ 适配中
