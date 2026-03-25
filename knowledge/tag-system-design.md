# 知识库标签系统设计

**设计日期**: 2026-03-25 22:15

---

## 🎯 目标

为 981 个 MD 文件建立统一标签系统，支持：
- 快速分类
- 交叉引用
- 全文搜索

---

## 📋 标签分类

### 1. 主题标签
- `#ai` - 人工智能
- `#agent` - 智能体
- `#research` - 研究
- `#tools` - 工具
- `#learning` - 学习

### 2. 状态标签
- `#active` - 活跃维护
- `#archived` - 已归档
- `#draft` - 草稿
- `#review` - 待审核

### 3. 优先级标签
- `#p0` - 高优先级
- `#p1` - 中优先级
- `#p2` - 低优先级

### 4. 来源标签
- `#youtube` - YouTube 视频
- `#github` - GitHub 项目
- `#twitter` - Twitter/X
- `#arxiv` - arXiv 论文

---

## 🔧 实施方式

### YAML Frontmatter
```yaml
---
title: 文件标题
tags: [ai, agent, research, p0]
created: 2026-03-25
updated: 2026-03-25
status: active
---
```

### 文件命名
```
2026-03-25-msa-research-notes.md
```

---

## 📅 实施计划

| 阶段 | 任务 | 预估 |
|------|------|------|
| 第 1 周 | 设计标签体系 | 1h |
| 第 2 周 | 批量添加标签 | 4h |
| 第 3 周 | 建立搜索脚本 | 2h |

---

**优先级**: 中
