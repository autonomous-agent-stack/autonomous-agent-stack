# OpenClaw优化指南

**来源**: https://x.com/qingq77/status/2033574260573180300
**GitHub**: https://github.com/OnlyTerp/openclaw-optimization-guide
**发现日期**: 2026-03-21
**优先级**: ⭐⭐ 中

## 核心思路

把OpenClaw工作区当成"路由层"重做

## 优化方案

### 1. 压缩注入文件
- SOUL.md/AGENTS.md/MEMORY.md/TOOLS.md
- 总量压到 **<8KB**
- 减少每轮token消耗

### 2. 长期信息外置
- 真正的长期信息丢进 `vault/`
- 不每轮注入，按需检索

### 3. 本地向量检索
- 使用Ollama
- 需要时捞相关片段
- 提升检索效率

## 优势

- 降低上下文窗口压力
- 减少token消耗
- 提升响应速度
- 保持关键信息可访问

## 适用场景

- 长期运行的小龙虾
- 大量历史数据
- 需要频繁检索的场景

## 待实践

- [ ] 阅读完整GitHub指南
- [ ] 测试压缩效果
- [ ] 配置Ollama向量检索
- [ ] 对比优化前后token消耗
