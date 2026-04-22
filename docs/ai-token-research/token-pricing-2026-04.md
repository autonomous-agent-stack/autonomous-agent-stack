# 全球 AI 厂商 Token 定价表（2026 年 4 月）
# Global AI Provider Token Pricing Table (April 2026)

> 数据采集日期：2026-04-22 | 价格单位：每百万 Token（USD 或 CNY）
> Data collected: 2026-04-22 | Unit: per million tokens (USD or CNY)

---

## 一、国际厂商 / International Providers

### Anthropic Claude

| 模型 | 输入价格 | 输出价格 | 备注 |
|------|---------|---------|------|
| Claude Opus 4.7 | $5.00 | $25.00 | 旗舰模型 |
| Claude Sonnet 4.6 | $3.00 | $15.00 | 性价比主力 |
| Claude Haiku 4.5 | $1.00 | $5.00 | 轻量快速 |

来源：https://docs.anthropic.com/en/docs/about-claude/models

### Google Gemini

| 模型 | 输入价格 | 输出价格 | 备注 |
|------|---------|---------|------|
| Gemini 3.1 Pro Preview | $2.00 | $12.00 | ≤200K 上下文 |
| Gemini 3.1 Flash-Lite | $0.25 | $1.50 | 超低成本 |
| Gemini 3 Flash | $0.50 | $3.00 | 平衡性能 |

来源：https://ai.google.dev/pricing

### OpenAI（via Artificial Analysis）

| 模型 | 输入价格 | 输出价格 | 备注 |
|------|---------|---------|------|
| GPT-5.4 (xhigh) | ~$2.50 | ~$10.00 | 旗舰 |
| GPT-5.4 mini (xhigh) | ~$0.75 | ~$4.50 | 轻量版 |

来源：https://artificialanalysis.ai/models（OpenAI 官方定价页被 Cloudflare 拦截）

### DeepSeek

| 模型 | 输入价格 | 输出价格 | 缓存命中 | 备注 |
|------|---------|---------|---------|------|
| deepseek-chat (V3.2) | $0.28 | $0.42 | $0.028 | 性价比极高 |
| deepseek-reasoner | $0.28 | $0.42 | $0.028 | 推理增强 |

来源：https://platform.deepseek.com/api-docs/pricing

---

## 二、国内厂商 / Domestic (Chinese) Providers

### 阿里云百炼（通义千问）

| 模型 | 输入价格 | 输出价格 | 备注 |
|------|---------|---------|------|
| Qwen3.6-Max-Preview | ¥9.00 | ¥54.00 | 最新旗舰 |
| Qwen3-Max (≤32K) | ¥2.50 | ¥10.00 | 主力模型 |
| Qwen3-Max (>32K) | ¥4.00 | ¥16.00 | 长上下文 |

来源：https://help.aliyun.com/zh/model-studio/model-pricing

### 智谱 AI（GLM）

| 模型 | 输入价格 | 输出价格 | 备注 |
|------|---------|---------|------|
| GLM-5.1 | ¥6-8 | ¥24-28 | 旗舰 |
| GLM-4.7 | ¥2-4 | ¥8-16 | 主力 |
| GLM-4.7-Flash | 免费 | 免费 | 入门推广 |
| GLM-4.5-Air | ¥0.80 | ¥2-6 | 轻量 |

来源：https://open.bigmodel.cn/pricing

### Kimi K2.6（月之暗面）

| 模型 | 输入价格 | 输出价格 | 缓存命中 | 备注 |
|------|---------|---------|---------|------|
| Kimi K2.6 | ¥6.50 | ¥27.00 | ¥1.10 | 262K 上下文 |

来源：https://platform.kimi.com/docs/pricing/chat-k26

---

## 三、价格对比概览 / Price Comparison Overview

### 美元计价（统一为 USD/MTok）

| 厂商 | 最低输入 | 最低输出 | 性价比代表 |
|------|---------|---------|-----------|
| DeepSeek | $0.28 | $0.42 | deepseek-chat |
| Google | $0.25 | $1.50 | Gemini 3.1 Flash-Lite |
| Anthropic | $1.00 | $5.00 | Claude Haiku 4.5 |
| OpenAI | ~$0.75 | ~$4.50 | GPT-5.4 mini |

### 人民币计价（CNY/MTok）

| 厂商 | 最低输入 | 最低输出 | 备注 |
|------|---------|---------|------|
| 智谱 | 免费 | 免费 | GLM-4.7-Flash（限时） |
| 智谱 | ¥0.80 | ¥2 | GLM-4.5-Air |
| DeepSeek | ≈¥2.03 | ≈¥3.04 | deepseek-chat |
| 通义千问 | ¥2.50 | ¥10 | Qwen3-Max |
| Kimi | ¥6.50 | ¥27 | K2.6 |

---

## 四、关键发现 / Key Findings

1. **价格差距巨大**：从 DeepSeek 的 $0.28 到 Anthropic Opus 的 $5.00，输入价格相差 18 倍
2. **国内厂商更便宜**：智谱 Flash 免费策略、DeepSeek 超低价，竞争激烈
3. **缓存机制**：DeepSeek 和 Kimi 提供缓存命中价格（原价的 1/10-1/6），大幅降低重复调用成本
4. **输出价格远高于输入**：普遍为输入的 3-6 倍，这影响商业模式设计
5. **汇率换算**：DeepSeek 按 ¥7.25/USD 粗算，国内厂商定价普遍低于国际厂商
