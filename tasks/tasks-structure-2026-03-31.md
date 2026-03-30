# Tasks 目录结构优化（2026-03-31 00:17）

## 📊 当前结构

### 文件列表（9 个）
1. heartbeat-response-2026-03-31-00-05.md
2. next-phase-plan-2026-03-31.md
3. phase-1-2026-03-30.md
4. phase-2-2026-03-31.md
5. phase-3-2026-03-31.md
6. phase-4-1-2026-03-31.md
7. phase-4-2026-03-31.md
8. scripts-preparation-2026-03-31.md

### 文件分类
- **阶段文档**: 5 个（phase-1 到 phase-4）
- **计划文档**: 1 个（next-phase-plan）
- **脚本文档**: 1 个（scripts-preparation）
- **心跳响应**: 1 个（heartbeat-response）

## 🎯 优化方案

### 方案 A：按日期分类
```
tasks/
├── 2026-03-30/
│   └── phase-1-2026-03-30.md
└── 2026-03-31/
    ├── phase-2-2026-03-31.md
    ├── phase-3-2026-03-31.md
    ├── phase-4-2026-03-31.md
    ├── phase-4-1-2026-03-31.md
    ├── next-phase-plan-2026-03-31.md
    ├── scripts-preparation-2026-03-31.md
    └── heartbeat-response-2026-03-31-00-05.md
```

### 方案 B：按类型分类
```
tasks/
├── phases/
│   ├── phase-1-2026-03-30.md
│   ├── phase-2-2026-03-31.md
│   ├── phase-3-2026-03-31.md
│   └── phase-4-2026-03-31.md
├── plans/
│   └── next-phase-plan-2026-03-31.md
└── scripts/
    └── scripts-preparation-2026-03-31.md
```

### 方案 C：保持扁平结构
- **优点**: 简单直接
- **缺点**: 文件过多时混乱

## 🎯 推荐方案

### 采用方案 A（按日期分类）
- **优点**: 清晰的时间线
- **缺点**: 需要创建子目录

### 执行步骤
1. 创建 2026-03-30/ 和 2026-03-31/ 目录
2. 移动相应文件
3. 更新索引

---

**时间**: 2026-03-31 00:17
**状态**: 🟡 分析完成，待执行
