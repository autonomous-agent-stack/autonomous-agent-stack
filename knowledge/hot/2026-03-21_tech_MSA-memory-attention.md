# MSA (Memory Sparse Attention)

**来源**: https://x.com/elliotchen100/status/2034479369855590660
**补充**: https://x.com/alchainhust/status/2033584179351547952
**GitHub**: https://github.com/EverMind-AI/MSA
**发现日期**: 2026-03-21
**优先级**: ⭐⭐⭐ 高

## 幕后故事 ⭐

- **一作**: 17岁Kimi实习生 @nathancgy4
- **灵感来源**: 考场草稿纸上想出来的
- **马斯克评价**: "Impressive work from Kimi"

## 核心创新

**问题**: 传统方案（RAG、暴力扩窗口、压缩）各有缺陷
**方案**: 把「记忆」直接长进注意力机制，端到端训练

## 性能数据

- **参数**: 4B小模型
- **扩展**: 16K → 1亿 token
- **精度衰减**: < 9%
- **推理**: 仅需2张A800
- **对比**: 干翻235B级别RAG方案

## 技术特点

1. 不检索（无需RAG）
2. 不压缩（无信息损失）
3. 端到端训练
4. 原生长记忆

## 应用场景

- Agent长记忆
- 超长文档理解
- 多轮对话历史
- 代码仓库理解

## 待研究

- [ ] 论文精读
- [ ] 代码实现细节
- [ ] 与RAG对比实验
- [ ] 部署成本分析
- [ ] 与OpenClaw集成可能性

## 相关链接

- 论文: 待补充
- 代码: https://github.com/EverMind-AI/MSA
- 推文: https://x.com/bozhou_ai/status/2035033044831400166
