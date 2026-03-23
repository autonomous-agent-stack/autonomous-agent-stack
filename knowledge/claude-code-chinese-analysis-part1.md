# Claude Code 官方中文文档深度分析 - 第一部分

**整理时间**: 2026-03-23  
**来源**: Claude API 官方中文文档（繁体中文）  
**状态**: 🔥 慢工出细活，系统爬取中

---

## 📋 已爬取页面

### 1. 快速開始（Get Started）✅
**URL**: https://platform.claude.com/docs/zh-TW/get-started  
**内容**: API调用快速入门

### 2. 模型概覽（Models Overview）✅
**URL**: https://platform.claude.com/docs/zh-TW/about-claude/models/overview  
**内容**: 3个模型完整对比

---

## 📖 页面 1: 快速開始

### 核心定位
进行您的第一次 Claude API 呼叫并建立一个简单的网络搜寻助手

---

### 前置条件

#### 必需
1. ✅ **Anthropic Console 帳戶**
   - 网址: https://console.anthropic.com/

2. ✅ **API 金鑰**
   - 获取: https://console.anthropic.com/settings/keys

---

### 呼叫 API

#### 步骤 1: 设定 API 金钥

**环境变量**（推荐）:
```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

**安全提示**:
- ❗ 不要在代码中硬编码 API Key
- ✅ 使用环境变量
- ✅ 定期轮换 API Key

#### 步骤 2: 进行第一次 API 呼叫

**cURL 示例**:
```bash
curl https://api.anthropic.com/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-opus-4-6",
    "max_tokens": 1000,
    "messages": [
      {
        "role": "user",
        "content": "What should I search for to find the latest developments in renewable energy?"
      }
    ]
  }'
```

**示例输出**:
```json
{
  "id": "msg_01HCDu5LRGeP2o7s2xGmxyx8",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Here are some effective search strategies..."
    }
  ],
  "model": "claude-opus-4-6",
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 21,
    "output_tokens": 305
  }
}
```

---

### 其他语言示例

#### Python
```python
import anthropic

client = anthropic.Anthropic()

message = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=1000,
    messages=[
        {"role": "user", "content": "What should I search for to find the latest developments in renewable energy?"}
    ]
)

print(message.content)
```

#### TypeScript
```typescript
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic();

const message = await client.messages.create({
  model: 'claude-opus-4-6',
  max_tokens: 1000,
  messages: [
    {"role": "user", "content": "What should I search for to find the latest developments in renewable energy?"}
  ]
});

console.log(message.content);
```

#### Java
```java
import com.anthropic.client.AnthropicClient;
import com.anthropic.models.Message;

AnthropicClient client = AnthropicClient.builder()
    .apiKey(System.getenv("ANTHROPIC_API_KEY"))
    .build();

Message message = client.messages().create(MessageCreateRequest.builder()
    .model("claude-opus-4-6")
    .maxTokens(1000)
    .messages(List.of(MessageContent.builder()
        .role("user")
        .content("What should I search for to find the latest developments in renewable energy?")
        .build()))
    .build());

System.out.println(message.content());
```

---

### 後續步驟

#### 1. 使用 Messages
**链接**: `/docs/zh-TW/build-with-claude/working-with-messages`
**描述**: 学习 Messages API 的常见模式

#### 2. 功能概覽
**链接**: `/docs/zh-TW/api/overview`
**描述**: 探索 Claude 的进阶功能与能力

#### 3. 客戶端 SDK
**链接**: `/docs/zh-TW/api/client-sdks`
**描述**: 探索 Anthropic 客户端程式库

#### 4. Claude Cookbook
**链接**: https://platform.claude.com/cookbooks
**描述**: 透过互动式 Jupyter 笔记本学习

---

## 📖 页面 2: 模型概覽

### 核心定位
Claude 是由 Anthropic 开发的一系列最先进的大型语言模型。本指南介绍我们的模型并比较其效能。

---

### 选择模型

#### 推荐起点
**如果您不确定该使用哪个模型**:
- ✅ **推荐**: 从 **Claude Opus 4.6** 开始
- **原因**: 最新一代模型，在程式编写和推理方面表现卓越

#### 共同特性
**所有目前的 Claude 模型都支援**:
- ✅ 文字和图片输入
- ✅ 文字输出
- ✅ 多语言功能
- ✅ 视觉能力

#### 可用平台
- ✅ Anthropic API
- ✅ AWS Bedrock
- ✅ Google Vertex AI

---

### 最新模型比较（完整对比表）

#### 1. Claude Opus 4.6（最智慧）

**描述**: 我们最智慧的模型，适用于建构代理和程式编写

**API ID**:
- Claude API: `claude-opus-4-6`
- AWS Bedrock: `anthropic.claude-opus-4-6-v1:0`
- GCP Vertex AI: `claude-opus-4-6`

**定价**:
- 输入: **$5 / MTok**
- 输出: **$25 / MTok**

**核心特性**:
- ✅ **延伸思考**: 是
- ✅ **自适应思考**: 是
- ✅ **优先层级**: 是
- ✅ **相对延迟**: 中等
- ✅ **上下文视窗**: 200K tokens / 1M tokens (beta)
- ✅ **最大输出**: 128K tokens
- ✅ **可靠知识截止日期**: 2025 年 5 月
- ✅ **训练资料截止日期**: 2025 年 8 月

**适用场景**:
- 🎯 构建AI agents
- 🎯 复杂程式编写
- 🎯 最高智慧要求

---

#### 2. Claude Sonnet 4.5（平衡）

**描述**: 速度与智慧的最佳组合

**API ID**:
- Claude API: `claude-sonnet-4-5-20250929` (完整ID) / `claude-sonnet-4-5` (别名)
- AWS Bedrock: `anthropic.claude-sonnet-4-5-20250929-v1:0`
- GCP Vertex AI: `claude-sonnet-4-5@20250929`

**定价**:
- 输入: **$3 / MTok**
- 输出: **$15 / MTok**

**核心特性**:
- ✅ **延伸思考**: 是
- ❌ **自适应思考**: 否
- ✅ **优先层级**: 是
- ✅ **相对延迟**: 快速
- ✅ **上下文视窗**: 200K tokens / 1M tokens (beta)
- ✅ **最大输出**: 64K tokens
- ✅ **可靠知识截止日期**: 2025 年 1 月
- ✅ **训练资料截止日期**: 2025 年 7 月

**适用场景**:
- ⚖️ 速度与智慧平衡
- ⚖️ 大多数生产应用
- ⚖️ 性价比最优

---

#### 3. Claude Haiku 4.5（最快）

**描述**: 我们最快速的模型，具备接近前沿的智慧

**API ID**:
- Claude API: `claude-haiku-4-5-20251001` (完整ID) / `claude-haiku-4-5` (别名)
- AWS Bedrock: `anthropic.claude-haiku-4-5-20251001-v1:0`
- GCP Vertex AI: `claude-haiku-4-5@20251001`

**定价**:
- 输入: **$1 / MTok**
- 输出: **$5 / MTok**

**核心特性**:
- ✅ **延伸思考**: 是
- ❌ **自适应思考**: 否
- ✅ **优先层级**: 是
- ✅ **相对延迟**: 最快
- ✅ **上下文视窗**: 200K tokens
- ✅ **最大输出**: 64K tokens
- ✅ **可靠知识截止日期**: 2025 年 2 月
- ✅ **训练资料截止日期**: 2025 年 7 月

**适用场景**:
- ⚡ 最快响应速度
- ⚡ 简单任务
- ⚡ 高频调用

---

### 重要说明

#### 1. 定价说明
**注释 1**:
- 请参阅定价页面获取完整资讯
- 包括：批次 API 折扣、提示快取费率、延伸思考成本、视觉处理费用

**链接**: `/docs/zh-TW/about-claude/pricing`

#### 2. 知识截止日期
**注释 2**:
- **可靠知识截止日期**: 模型知识最为广泛且可靠的截止日期
- **训练资料截止日期**: 所使用训练资料的更广泛日期范围

**更多信息**: [Anthropic 的透明度中心](https://www.anthropic.com/transparency)

#### 3. 1M Token 上下文视窗
**注释 3**:
- Claude Opus 4.6 和 Sonnet 4.5 在使用 `context-1m-2025-08-07` beta 标头时支援 1M token 上下文视窗
- 超过 200K tokens 的请求适用长上下文定价

**链接**: `/docs/zh-TW/build-with-claude/context-windows#1m-token-context-window`

---

### 平台一致性

#### 快照日期
**具有相同快照日期的模型**:
- ✅ 在所有平台上都是相同的
- ✅ 不会变更
- ✅ 确保一致性
- ✅ 允许开发者在不同环境中依赖稳定的效能

**示例**: 快照日期 20240620

#### 端点类型
**从 Claude Sonnet 4.5 及所有后续模型开始**:

**AWS Bedrock 和 Google Vertex AI 提供两种端点类型**:
1. **全域端点**
   - 动态路由以实现最大可用性

2. **区域端点**
   - 保证资料透过特定地理区域路由

**更多信息**: `/docs/zh-TW/about-claude/pricing#third-party-platform-pricing`

---

### 提示与输出效能

#### Claude 4 模型在以下方面表现卓越

**1. 效能**
- ✅ 推理
- ✅ 程式编写
- ✅ 多语言任务
- ✅ 长上下文处理
- ✅ 诚实度
- ✅ 图片处理

**更多信息**: [Claude 4 部落格文章](http://www.anthropic.com/news/claude-4)

**2. 引人入胜的回应**
**特点**:
- Claude 模型非常适合需要丰富、类人互动的应用程式

**调整方法**:
- ✅ 如果您偏好更简洁的回应，可以调整您的提示来引导模型产生所需的输出长度
- ✅ 参阅提示工程指南获取详情

**参考**:
- 提示工程指南: `/docs/zh-TW/build-with-claude/prompt-engineering`
- 提示最佳实践指南: `/docs/zh-TW/build-with-claude/prompt-engineering/claude-prompting-best-practices`

**3. 输出品質**
- 从先前的模型世代迁移到 Claude 4 时，您可能会注意到整体效能有更大的提升

---

### 遷移到 Claude 4.6

#### 建议
如果您目前正在使用较旧的 Claude 模型:
- ✅ **建议迁移到 Claude Opus 4.6**
- **原因**: 利用改进的智慧和增强的功能

#### 迁移指南
**详细迁移说明**: `/docs/zh-TW/about-claude/models/migration-guide`

---

### 開始使用 Claude

#### 想要与 Claude 聊天？
**访问**: [claude.ai](http://www.claude.ai)

#### 学习资源

**1. Claude 簡介**
- **链接**: `/docs/zh-TW/intro`
- **描述**: 探索 Claude 的功能和开发流程

**2. 快速入門**
- **链接**: `/docs/zh-TW/get-started`
- **描述**: 了解如何在几分钟内进行您的第一次 API 呼叫

**3. Claude Console**
- **链接**: https://console.anthropic.com/
- **描述**: 直接在浏览器中制作和测试强大的提示

---

### 支援

#### 联系方式
如果您有任何问题或需要协助:
- ✅ **支援团队**: https://support.claude.com/
- ✅ **Discord 社群**: https://www.anthropic.com/discord

---

## 🔍 关键发现

### 1. 模型选择策略（中文版）

**三级选择体系**:
```
Opus 4.6  → 最智慧（$5/$25）
Sonnet 4.5 → 最佳平衡（$3/$15）⭐ 推荐
Haiku 4.5 → 最快速（$1/$5）
```

**中文文档特点**:
- 使用"智慧"而非"intelligent"
- 使用"程式编写"而非"coding"
- 使用"建构"而非"build"

### 2. 平台一致性保证

**关键点**:
- ✅ 相同快照日期 = 相同模型
- ✅ 跨平台一致性
- ✅ 稳定的效能

### 3. 新功能：自适应思考

**仅 Opus 4.6 支持**:
- ✅ Opus 4.6: 是
- ❌ Sonnet 4.5: 否
- ❌ Haiku 4.5: 否

**用途**: 让 Claude 动态决定何时以及思考多少

### 4. 1M Token 上下文

**Beta 功能**:
- ✅ Opus 4.6: 支持（需 beta 标头）
- ✅ Sonnet 4.5: 支持（需 beta 标头）
- ❌ Haiku 4.5: 不支持

**Beta 标头**: `context-1m-2025-08-07`

---

## 📊 对比：英文 vs 中文文档

### 术语对比

| 英文 | 繁体中文 | 简体中文 |
|------|---------|---------|
| Intelligent | 智慧 | 智能 |
| Coding | 程式编写 | 编程 |
| Build | 建构 | 构建 |
| Model | 模型 | 模型 |
| Token | Token | Token |
| Context Window | 上下文视窗 | 上下文窗口 |

### 内容差异
- ✅ **内容一致**: 核心信息相同
- ✅ **结构相同**: 页面结构一致
- ✅ **示例相同**: 代码示例一致
- ✅ **链接相同**: 跨页面链接一致

---

## 📈 分析完成度

### 快速開始
- ✅ 前置条件: 100%
- ✅ API 调用: 100%
- ✅ 多语言示例: 100%
- ✅ 后续步骤: 100%

### 模型概覽
- ✅ 模型对比: 100%
- ✅ 选择指南: 100%
- ✅ 定价信息: 100%
- ✅ 平台支持: 100%
- ✅ 重要说明: 100%

---

## 🚀 下一步计划

### 继续爬取（优先级排序）

#### 第一优先级（核心功能）- 13个页面
1. ⏳ **功能概覽** - 5大功能区域
2. ⏳ **使用 Messages API** - API 实战
3. ⏳ **工具概覽** - 工具使用
4. ⏳ **Agent SDK 概覽** - Agent 开发
5. ⏳ **Agent 技能概覽** - 技能系统
6. ⏳ **提示工程概覽** - 提示技巧
7. ⏳ **延伸思考** - 高级推理
8. ⏳ **結構化輸出** - JSON 输出
9. ⏳ **視覺** - 图像处理
10. ⏳ **程式碼執行工具** - 代码执行
11. ⏳ **MCP 連接器** - MCP 集成
12. ⏳ **提示快取** - 性能优化
13. ⏳ **測試與評估** - 测试方法

---

## 💡 学习建议

### 初学者路径
1. ✅ **已完成**: 快速開始
2. ⏳ **下一步**: 使用 Messages API
3. ⏳ **然后**: 功能概覽
4. ⏳ **最后**: 提示工程概覽

### 开发者路径
1. ✅ **已完成**: 模型概覽
2. ⏳ **下一步**: 工具概覽
3. ⏳ **然后**: Agent SDK 概覽
4. ⏳ **最后**: MCP 連接器

### 高级用户路径
1. ⏳ **优先**: 延伸思考
2. ⏳ **然后**: 結構化輸出
3. ⏳ **最后**: 程式碼執行工具

---

**状态**: ✅ 第一部分完成（2个页面）  
**下一步**: 继续爬取核心功能页面  
**Token 消耗**: 🔥 慢工出细活
