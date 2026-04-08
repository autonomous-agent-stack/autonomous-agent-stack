# AAS RFC (Request for Comments)

[**English**](README.en.md) | [简体中文](README.zh-CN.md)

本目录包含 AAS 项目的架构设计文档和 RFC。

## RFC 索引

### 核心架构

| RFC | 状态 | 描述 |
|-----|------|------|
| [distributed-execution.md](./distributed-execution.md) | 📝 Draft | Linux 控制面 + Mac 执行节点的分布式执行架构 |
| [three-machine-architecture.md](./three-machine-architecture.md) | 📝 Draft | Linux + Mac mini + MacBook 异构执行池设计 |
| [federation-protocol.md](./federation-protocol.md) | 📝 Draft | 分层互信联邦协议：L0-L3 信任层级与能力共享 |
| [federation-market-model.md](./federation-market-model.md) | 📝 Draft | 双层协作：联邦（外交）+ 市场（贸易），资源定价与结算机制 |

## RFC 流程

### 1. 提案阶段

```bash
# 创建 RFC 草案
docs/rfc/
├── rfc-001-feature-name.md
└── templates/
    └── rfc-template.md
```

### 2. 讨论阶段

- 在 GitHub Discussions 中创建讨论 thread
- 邀请相关方 review
- 收集反馈并修改

### 3. 审批阶段

- 核心 RFC 需要维护者 approval
- 技术决策需达成共识
- 记录反对意见与解决方案

### 4. 实现阶段

- 创建 implementation issue
- 关联相关 PR
- 更新 RFC 状态

### 5. 完成阶段

- RFC 状态改为 Accepted/Implemented
- 更新 ARCHITECTURE.md
- 归档到 memory/

## RFC 状态

- **📝 Draft**: 草案讨论中
- **👀 Under Review**: 正在 review
- **✅ Accepted**: 已接受，等待实现
- **🚧 In Progress**: 实现中
- **✅ Implemented**: 已实现
- **❌ Rejected**: 已拒绝
- **📦 Superseded**: 已被新 RFC 替代

## RFC 模板

```markdown
# RFC: [标题]

**Status**: Draft | **Author**: ... | **Created**: YYYY-MM-DD
**Depends on**: [相关 RFC]

## 摘要

一句话总结这个 RFC 的核心内容。

## 背景与动机

为什么要做这个改动？解决什么问题？

## 设计

### 核心方案

详细描述设计方案。

### 数据模型

```sql
-- 如有数据模型变更
```

### API 变更

```python
# 如有 API 变更
```

## 实现阶段

- [ ] Phase 1
- [ ] Phase 2
- [ ] Phase 3

## 与现有架构的关系

如何与现有代码兼容？

## 替代方案

考虑过哪些其他方案？为什么不选？

## 风险与缓解

可能的风险和应对措施。

## 参考资料

相关链接。
```

## 贡献指南

欢迎提交新的 RFC！

1. Fork 仓库
2. 创建 `docs/rfc/rfc-XXX-title.md`
3. 填写 RFC 模板
4. 提交 PR 并在 Discussions 中发起讨论

## RFC 阅读顺序

**新加入者推荐阅读顺序**：

1. 先读项目 [ARCHITECTURE.zh-CN.md](../../ARCHITECTURE.zh-CN.md) 了解当前架构
2. 再读 [distributed-execution.md](./distributed-execution.md) 理解分布式基础
3. 然后读 [three-machine-architecture.md](./three-machine-architecture.md) 了解多机扩展
4. 再读 [federation-protocol.md](./federation-protocol.md) 了解联邦愿景
5. 最后读 [federation-market-model.md](./federation-market-model.md) 了解市场机制

**实现者推荐阅读顺序**：

根据当前实现阶段，选择相关 RFC 深入阅读。
