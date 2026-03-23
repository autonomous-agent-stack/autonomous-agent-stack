# Claude Code 官方文档深度分析 - 第二部分（模型 + API）

**分析时间**: 2026-03-23 16:20  
**状态**: 🔥 慢慢挖，细细分析  
**来源**: 官方文档（Models + Features + Messages + SDKs）

---

## 📖 页面 3: Models Overview（模型概览）

### 核心定位
**Claude模型家族**：Anthropic开发的最先进大型语言模型，不同模型平衡成本、性能和智能。

---

### 最新模型对比表（完整版）

#### 1. Claude Opus 4.6（最强大）
**定位**: The most intelligent model for building agents and coding

**API ID**: 
- Claude API: `claude-opus-4-6`
- AWS Bedrock: `anthropic.claude-opus-4-6-v1`
- GCP Vertex AI: `claude-opus-4-6`

**核心特性**:
- ✅ **Extended thinking**: Yes
- ✅ **Adaptive thinking**: Yes
- ✅ **Priority Tier**: Yes
- ✅ **Comparative latency**: Moderate
- ✅ **Context window**: 1M tokens
- ✅ **Max output**: 128k tokens
- ✅ **Reliable knowledge cutoff**: May 2025
- ✅ **Training data cutoff**: Aug 2025

**价格**:
- Input: **$5 / MTok**（百万token）
- Output: **$25 / MTok**

**适用场景**:
- 🎯 构建AI agents
- 🎯 复杂编码任务
- 🎯 最高智能要求

---

#### 2. Claude Sonnet 4.6（平衡）
**定位**: The best combination of speed and intelligence

**API ID**:
- Claude API: `claude-sonnet-4-6`
- AWS Bedrock: `anthropic.claude-sonnet-4-6`
- GCP Vertex AI: `claude-sonnet-4-6`

**核心特性**:
- ✅ **Extended thinking**: Yes
- ✅ **Adaptive thinking**: Yes
- ✅ **Priority Tier**: Yes
- ✅ **Comparative latency**: Fast
- ✅ **Context window**: 1M tokens
- ✅ **Max output**: 64k tokens
- ✅ **Reliable knowledge cutoff**: Aug 2025
- ✅ **Training data cutoff**: Jan 2026

**价格**:
- Input: **$3 / MTok**
- Output: **$15 / MTok**

**适用场景**:
- ⚖️ 速度与智能平衡
- ⚖️ 大多数生产应用
- ⚖️ 性价比最优

---

#### 3. Claude Haiku 4.5（最快）
**定位**: The fastest model with near-frontier intelligence

**API ID**:
- Claude API: `claude-haiku-4-5`（alias）或 `claude-haiku-4-5-20251001`（完整ID）
- AWS Bedrock: `anthropic.claude-haiku-4-5-20251001-v1:0`
- GCP Vertex AI: `claude-haiku-4-5@20251001`

**核心特性**:
- ✅ **Extended thinking**: Yes
- ❌ **Adaptive thinking**: No
- ✅ **Priority Tier**: Yes
- ✅ **Comparative latency**: Fastest
- ✅ **Context window**: 200k tokens
- ✅ **Max output**: 64k tokens
- ✅ **Reliable knowledge cutoff**: Feb 2025
- ✅ **Training data cutoff**: Jul 2025

**价格**:
- Input: **$1 / MTok**
- Output: **$5 / MTok**

**适用场景**:
- ⚡ 最快响应速度
- ⚡ 简单任务
- ⚡ 高频调用

---

### 模型选择指南

#### 按场景选择

**1. 构建AI Agents**
- ✅ **首选**: Claude Opus 4.6
- 原因：最高智能，最适合复杂推理

**2. 编码任务**
- ✅ **首选**: Claude Opus 4.6
- 原因：编码能力最强

**3. 生产应用**
- ✅ **首选**: Claude Sonnet 4.6
- 原因：平衡速度与智能

**4. 高频调用**
- ✅ **首选**: Claude Haiku 4.5
- 原因：最快响应，最低成本

**5. 长文档处理**
- ✅ **首选**: Claude Opus 4.6 或 Sonnet 4.6
- 原因：1M tokens上下文窗口

**6. 简单任务**
- ✅ **首选**: Claude Haiku 4.5
- 原因：性价比最高

---

### 重要提示

#### 1. 知识截止日期
**Reliable knowledge cutoff**: 最可靠的知识范围
**Training data cutoff**: 训练数据截止日期（更广泛）

**关键点**: 
- Opus 4.6: May 2025（可靠）, Aug 2025（训练）
- Sonnet 4.6: Aug 2025（可靠）, Jan 2026（训练）
- Haiku 4.5: Feb 2025（可靠）, Jul 2025（训练）

#### 2. 平台一致性
- ✅ **相同快照日期的模型**在所有平台完全相同
- ✅ 快照日期确保一致性和稳定性

#### 3. 全球 vs 区域端点
- **Global endpoints**: 动态路由，最大化可用性
- **Regional endpoints**: 保证数据路由通过特定地理区域
- **支持平台**: AWS Bedrock, Google Vertex AI

---

## 📖 页面 4: Features Overview（特性概览）

### API 五大功能区域

#### 1. Model Capabilities（模型能力）
**定义**: 控制Claude如何推理和格式化响应

**核心特性**:
- ✅ Context windows（上下文窗口）
- ✅ Adaptive thinking（自适应思考）
- ✅ Batch processing（批处理）
- ✅ Citations（引用）
- ✅ Data residency（数据驻留）
- ✅ Effort（努力程度）
- ✅ Extended thinking（扩展思考）
- ✅ PDF support（PDF支持）
- ✅ Search results（搜索结果）
- ✅ Structured outputs（结构化输出）

#### 2. Tools（工具）
**定义**: 让Claude在Web或你的环境中执行操作

**Server-side tools**（服务器端工具）:
- ✅ Code execution（代码执行）
- ✅ Web fetch（网页抓取）
- ✅ Web search（网页搜索）

**Client-side tools**（客户端工具）:
- ✅ Bash（命令行）
- ✅ Computer use（计算机控制）
- ✅ Memory（记忆）
- ✅ Text editor（文本编辑器）

#### 3. Tool Infrastructure（工具基础设施）
**定义**: 处理大规模工具发现和编排

**核心特性**:
- ✅ Agent Skills（代理技能）
- ✅ Fine-grained tool streaming（细粒度工具流）
- ✅ MCP connector（MCP连接器）
- ✅ Programmatic tool calling（编程式工具调用）
- ✅ Tool search（工具搜索）

#### 4. Context Management（上下文管理）
**定义**: 保持长时间运行的会话高效

**核心特性**:
- ✅ Context windows（上下文窗口）
- ✅ Compaction（压缩）
- ✅ Context editing（上下文编辑）
- ✅ Prompt caching（提示缓存）
- ✅ Token counting（token计数）

#### 5. Files & Assets（文件和资产）
**定义**: 管理提供给Claude的文档和数据

**核心特性**:
- ✅ Files API（文件API）

---

### Feature Availability（功能可用性）

#### 分类标准

**1. Beta** ⚠️
- **描述**: 预览功能，用于收集反馈
- **特点**:
  - 可用性可能有限（注册要求或等候名单）
  - 可能不会公开宣布
  - 功能可能大幅更改或停止
  - 不保证持续生产使用
  - 可能发生破坏性更改（有通知）
  - 平台特定限制可能适用
  - 有beta header标识

**2. Generally Available (GA)** ✅
- **描述**: 功能稳定，完全支持，推荐生产使用
- **特点**:
  - 不应有beta header或其他预览指示符
  - 受标准API版本保证保护

**3. Deprecated** ⚠️
- **描述**: 功能仍然可用但不再推荐
- **特点**:
  - 提供迁移路径和移除时间表

**4. Retired** ❌
- **描述**: 功能不再可用

---

### 核心特性详解

#### 1. Context Windows（上下文窗口）
**能力**: 最多1M tokens
**用途**: 处理大型文档、广泛代码库和长对话
**可用性**: 
- ✅ Claude API (GA)
- ✅ Amazon Bedrock (GA)
- ✅ Google Cloud Vertex AI (GA)
- ⚠️ Microsoft Foundry (Beta)

#### 2. Adaptive Thinking（自适应思考）
**能力**: 让Claude动态决定何时以及思考多少
**推荐**: Opus 4.6的推荐思考模式
**控制**: 使用effort参数控制思考深度
**可用性**:
- ✅ Claude API (GA)
- ✅ Amazon Bedrock (GA)
- ✅ Google Cloud Vertex AI (GA)
- ⚠️ Microsoft Foundry (Beta)

#### 3. Batch Processing（批处理）
**能力**: 异步处理大量请求以节省成本
**优势**: 批处理API调用比标准API调用便宜50%
**要求**: 每批次大量查询
**可用性**:
- ✅ Claude API (GA)
- ✅ Amazon Bedrock (GA)
- ✅ Google Cloud Vertex AI (GA)

#### 4. Citations（引用）
**能力**: 将Claude的响应基于源文档
**优势**: 提供详细引用到确切的句子和段落
**结果**: 更可验证、更可信的输出
**可用性**:
- ✅ Claude API (GA)
- ✅ Amazon Bedrock (GA)
- ✅ Google Cloud Vertex AI (GA)
- ⚠️ Microsoft Foundry (Beta)

#### 5. Extended Thinking（扩展思考）
**能力**: 复杂任务的增强推理能力
**优势**: 提供Claude分步思考过程的透明度
**用途**: 在给出最终答案之前
**可用性**:
- ✅ Claude API (GA)
- ✅ Amazon Bedrock (GA)
- ✅ Google Cloud Vertex AI (GA)
- ⚠️ Microsoft Foundry (Beta)

#### 6. Structured Outputs（结构化输出）
**能力**: 保证schema符合性
**方法**:
- JSON outputs（结构化数据响应）
- Strict tool use（验证的工具输入）
**可用性**:
- ✅ Claude API (GA)
- ✅ Amazon Bedrock (GA)
- ⚠️ Microsoft Foundry (Beta)

---

## 📖 页面 5: Using the Messages API（Messages API 使用指南）

### 核心定位
**Messages API**: Claude的主要API接口，无状态设计

---

### 基本请求和响应

#### 请求示例（Shell）
```bash
curl https://api.anthropic.com/v1/messages \
  --header "x-api-key: $ANTHROPIC_API_KEY" \
  --header "anthropic-version: 2023-06-01" \
  --header "content-type: application/json" \
  --data '{
    "model": "claude-opus-4-6",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "Hello, Claude"}
    ]
  }'
```

#### 响应示例（JSON）
```json
{
  "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Hello!"
    }
  ],
  "model": "claude-opus-4-6",
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 12,
    "output_tokens": 6
  }
}
```

---

### 多轮对话

#### 关键概念
**无状态API**: 每次请求都发送完整的对话历史

#### 示例
```bash
curl https://api.anthropic.com/v1/messages \
  --header "x-api-key: $ANTHROPIC_API_KEY" \
  --header "anthropic-version: 2023-06-01" \
  --header "content-type: application/json" \
  --data '{
    "model": "claude-opus-4-6",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "Hello, Claude"},
      {"role": "assistant", "content": "Hello!"},
      {"role": "user", "content": "Can you describe LLMs to me?"}
    ]
  }'
```

#### 技巧
- ✅ 可以使用合成的`assistant`消息
- ✅ 不一定要来自Claude的实际响应
- ✅ 用于预设对话上下文

---

### Prefilling（预填充）⚠️

#### 定义
在输入消息列表的最后位置预填Claude的部分响应

#### 示例（获取单选答案）
```bash
curl https://api.anthropic.com/v1/messages \
  --header "x-api-key: $ANTHROPIC_API_KEY" \
  --header "anthropic-version: 2023-06-01" \
  --header "content-type: application/json" \
  --data '{
    "model": "claude-opus-4-6",
    "max_tokens": 1,
    "messages": [
      {
        "role": "user", 
        "content": "What is latin for Ant? (A) Apoidea, (B) Rhopalocera, (C) Formicidae"
      },
      {"role": "assistant", "content": "The answer is ("}
    ]
  }'
```

#### 响应
```json
{
  "id": "msg_01Q8Faay6S7QPTvEUUQARt7h",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "C"
    }
  ],
  "model": "claude-opus-4-6",
  "stop_reason": "max_tokens",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 42,
    "output_tokens": 1
  }
}
```

#### ⚠️ 重要提示
**Prefilling已弃用**，不支持：
- ❌ Claude Opus 4.6
- ❌ Claude Sonnet 4.6
- ❌ Claude Sonnet 4.5

**替代方案**:
- ✅ 使用structured outputs
- ✅ 使用system prompt指令

---

### Vision（视觉）

#### 支持的图像格式
- ✅ `image/jpeg`
- ✅ `image/png`
- ✅ `image/gif`
- ✅ `image/webp`

#### 图像源类型
**1. Base64**
```bash
IMAGE_URL="https://example.com/image.jpg"
IMAGE_MEDIA_TYPE="image/jpeg"
IMAGE_BASE64=$(curl "$IMAGE_URL" | base64 | tr -d '\n')

curl https://api.anthropic.com/v1/messages \
  --header "x-api-key: $ANTHROPIC_API_KEY" \
  --header "anthropic-version: 2023-06-01" \
  --header "content-type: application/json" \
  --data '{
    "model": "claude-opus-4-6",
    "max_tokens": 1024,
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "image",
            "source": {
              "type": "base64",
              "media_type": "'$IMAGE_MEDIA_TYPE'",
              "data": "'$IMAGE_BASE64'"
            }
          },
          {"type": "text", "text": "What is in the above image?"}
        ]
      }
    ]
  }'
```

**2. URL**
```bash
curl https://api.anthropic.com/v1/messages \
  --header "x-api-key: $ANTHROPIC_API_KEY" \
  --header "anthropic-version: 2023-06-01" \
  --header "content-type: application/json" \
  --data '{
    "model": "claude-opus-4-6",
    "max_tokens": 1024,
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "image",
            "source": {
              "type": "url",
              "url": "https://example.com/image.jpg"
            }
          },
          {"type": "text", "text": "What is in the above image?"}
        ]
      }
    ]
  }'
```

**3. File**（通过Files API上传）

---

## 📖 页面 6: Client SDKs（客户端 SDK）

### 官方支持语言

#### 1. Python SDK
**特点**:
- ✅ Sync和async客户端
- ✅ Pydantic模型
- ✅ 类型安全

**安装**:
```bash
pip install anthropic
```

**快速开始**:
```python
import anthropic

client = anthropic.Anthropic()

message = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello, Claude"}],
)

print(message.content)
```

**最低版本**: Python 3.9+

**GitHub**: https://github.com/anthropics/anthropic-sdk-python

---

#### 2. TypeScript SDK
**特点**:
- ✅ Node.js支持
- ✅ Deno支持
- ✅ Bun支持
- ✅ 浏览器支持

**安装**:
```bash
npm install @anthropic-ai/sdk
```

**最低版本**: TypeScript 4.9+ (Node.js 20+)

**GitHub**: https://github.com/anthropics/anthropic-sdk-typescript

---

#### 3. Java SDK
**特点**:
- ✅ Builder模式
- ✅ CompletableFuture异步

**最低版本**: Java 8+

**GitHub**: https://github.com/anthropics/anthropic-sdk-java

---

#### 4. Go SDK
**特点**:
- ✅ Context-based取消
- ✅ Functional选项

**最低版本**: Go 1.23+

**GitHub**: https://github.com/anthropics/anthropic-sdk-go

---

#### 5. Ruby SDK
**特点**:
- ✅ Sorbet类型
- ✅ Streaming helpers

**最低版本**: Ruby 3.2.0+

**GitHub**: https://github.com/anthropics/anthropic-sdk-ruby

---

#### 6. C# SDK
**特点**:
- ✅ .NET Standard 2.0+
- ✅ IChatClient集成

**最低版本**: .NET Standard 2.0

**GitHub**: https://github.com/anthropics/anthropic-sdk-csharp

---

#### 7. PHP SDK
**特点**:
- ✅ Value对象
- ✅ Builder模式

**最低版本**: PHP 8.1.0+

**GitHub**: https://github.com/anthropics/anthropic-sdk-php

---

### 平台支持

所有SDK都支持多种部署选项：

#### 1. Claude API
**描述**: 直接连接Claude API端点

#### 2. Amazon Bedrock
**描述**: 通过AWS使用Claude

#### 3. Google Vertex AI
**描述**: 通过Google Cloud使用Claude

#### 4. Microsoft Foundry
**描述**: 通过Microsoft Azure使用Claude

---

### Beta Features

#### 访问方式
使用`beta`命名空间：

```python
message = client.beta.messages.create(
    model="claude-opus-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}],
    betas=["feature-name"],
)
```

#### 查看可用Beta功能
参考：Beta Headers文档

---

## 🔍 关键发现

### 1. 模型选择策略
**三级选择**:
- **Opus 4.6**: 最高智能（$5/$25 MTok）
- **Sonnet 4.6**: 最佳平衡（$3/$15 MTok）
- **Haiku 4.5**: 最快速度（$1/$5 MTok）

### 2. 功能可用性
**两个层次**:
- **GA（Generally Available）**: 稳定，生产就绪
- **Beta**: 预览，可能变化

### 3. API设计原则
**无状态**: 每次请求发送完整历史
**灵活**: 支持多模态（文本+图像）
**强大**: 内置工具使用能力

### 4. SDK生态
**7种语言**: Python, TypeScript, Java, Go, Ruby, C#, PHP
**4个平台**: Claude API, Bedrock, Vertex AI, Foundry
**类型安全**: 所有SDK都有类型支持

---

## 📊 分析完成度

### Models Overview
- ✅ 模型对比: 100%
- ✅ 选择指南: 100%
- ✅ 价格信息: 100%
- ✅ 平台支持: 100%

### Features Overview
- ✅ 五大区域: 100%
- ✅ 可用性分类: 100%
- ✅ 核心特性: 100%

### Messages API
- ✅ 基本用法: 100%
- ✅ 多轮对话: 100%
- ✅ Vision: 100%
- ✅ Prefilling警告: 100%

### Client SDKs
- ✅ 7种语言: 100%
- ✅ 安装方法: 100%
- ✅ 快速开始: 100%
- ✅ 平台支持: 100%

---

## 🚀 下一步计划

### 1. 深入学习
- 探索具体工具（Tool Use）
- 学习Agent SDK
- 研究MCP集成

### 2. 实践项目
- Python SDK快速开始
- 多轮对话实现
- Vision功能测试

### 3. 进阶主题
- Structured Outputs
- Prompt Caching
- Batch Processing

---

**状态**: ✅ 第二部分分析完成  
**下一步**: 继续探索工具使用、Agent SDK等高级主题  
**Token 消耗**: 🔥 慢工出细活
