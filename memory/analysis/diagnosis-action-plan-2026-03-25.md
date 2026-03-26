# 项目诊断与行动计划（2026-03-25）

## 📊 项目评估总览

### 🥇 一线项目（主攻方向）

#### 1. claude_cli - 最成熟项目
- **状态**: ✅ 成品级
- **定位**: 教程/模板产品
- **优势**:
  - 文档优先的工作流
  - 清晰的学习路径和分层
  - 40 ahead / 2 behind（有二次重组）
  - locale 检查脚本可运行
- **问题**:
  - ._*/Git 污染
- **下一步**:
  - 添加自动化验证（link check、markdown lint）
  - 建立官方文档同步节奏
  - **不做**: 继续扩写章节

#### 2. autoresearch - 最有潜力
- **状态**: 🚀 高潜力，需重构
- **定位**: 原创产品线（主攻方向）
- **优势**:
  - 任务拆分清晰（problem.md / task.json / run_task.py / evaluate.py）
  - 最小闭环成立（本地测试通过）
  - API-first 设计
- **问题**:
  - pyproject.toml 还是 "train-first"（强绑 CUDA Torch）
  - README 和实际依赖不一致
- **下一步**:
  - **立即**: 拆分 core 和 train
  - **立即**: 改成真正的 API-first packaging
  - 清理错误依赖

### 🥈 二线项目（稳定维护）

#### 3. claude_cli-private - 内部发行版
- **状态**: ✅ 有价值
- **定位**: 中文内部版/学习发行版
- **优势**:
  - 明确维护策略（只保留中文）
  - 52 ahead / 0 behind
  - README 链接通
- **问题**:
  - ._*/Git 污染
  - 维护逻辑过于强硬（-X ours + 自动删文件）
- **下一步**:
  - ✅ 已修复：去掉 -X ours，添加冲突中止逻辑
  - 定位收窄为"中文内部版"

### 🥉 三线项目（暂停扩张）

#### 4. ai-tools-compendium - 产量高但不可信
- **状态**: ⚠️ 需重构
- **定位**: 研究冲刺档案馆
- **优势**:
  - 内容量大
  - 样文质量不错（结构化对比）
- **问题**:
  - README 描述目录不存在
  - 19 个坏链接（README）+ 104 个坏链接（INDEX.md）
  - 索引和来源体系失控
- **下一步**:
  - **暂停**: 继续扩写
  - **立即**: 修索引和来源体系
  - **选择**: 降级为"档案馆"或重做为"元数据驱动资料库"

#### 5. openclaw-memory - 基础设施需重构
- **状态**: ⚠️ 需拆仓
- **定位**: 私有知识湖 + 运行记忆 + 字幕语料 + 工作区杂物
- **优势**:
  - 知识分层设计（hot/warm/cold）
- **问题**:
  - 混合体（1060 路径，805 个 .vtt）
  - knowledge/warm/ 和 cold/ 各只有 1 条（分层未跑起来）
  - ._*/Git 污染
- **下一步**:
  - ✅ 已有拆仓方案（OPENCLAW_MEMORY_MIGRATION_PLAN.md）
  - **立即**: 拆分为三层（agent-memory-core、knowledge-corpus、media-subtitles）

### 🎬 字幕/知识库项目 - 素材仓阶段

#### 6. finance-knowledge-base - 早期雏形
- **状态**: 🏗️ 雏形
- **定位**: 语料仓 + 处理流水线
- **优势**:
  - 有结构设计（books/ articles/ research/ xiao_lin_shuo）
- **问题**:
  - 数据核对链路未闭合（HeVuAKDtWX8 不在下载清单）
  - 只有 5 个字幕文件
- **下一步**:
  - **重命名**: "语料仓 + 处理流水线"（别叫知识图谱）
  - **建立**: ingestion pipeline、manifest、语言轨道规范

#### 7. ai-knowledge-graph - 野心大执行粗
- **状态**: ⚠️ 需重构
- **定位**: 语料仓
- **问题**:
  - 统计错误（346+39+14=399，写 393）
  - 目录树名和仓库名不一致
  - README 有重复段落
- **下一步**:
  - **立即**: README、统计、目录全部改成自动生成

---

## 🚨 紧急问题：._*/Git 污染

### 影响范围
- autoresearch
- ai-tools-compendium
- finance-knowledge-base
- claude_cli-private
- openclaw-memory

### 问题表现
- badRefName
- bad sha1 file
- non-monotonic index
- 会直接拖垮 Git 可靠性

### 清理方案
```bash
# 1. 查找所有 ._ 文件
find . -name "._*" -type f

# 2. 删除所有 ._ 文件
find . -name "._*" -type f -delete

# 3. 清理 Git 元数据
git fsck --full
git gc --prune=now

# 4. 添加到 .gitignore
echo "._*" >> .gitignore
echo ".DS_Store" >> .gitignore

# 5. 提交清理
git add .gitignore
git commit -m "chore: 清理 AppleDouble 文件污染"
git push
```

---

## 🎯 优先级行动计划

### P0（立即执行）
1. ✅ **清理 ._*/Git 污染**（所有仓库）
2. ✅ **重构 autoresearch**（改成 API-first）
3. ⏳ **修 ai-tools-compendium 索引**

### P1（本周完成）
1. ⏳ **拆分 openclaw-memory**（三层架构）
2. ⏳ **添加 claude_cli 自动化验证**
3. ⏳ **重命名字幕项目**（语料仓定位）

### P2（本月完成）
1. ⏳ **建立 claude_cli 官方文档同步**
2. ⏳ **完善 autoresearch 文档**
3. ⏳ **建立字幕项目 ingestion pipeline**

---

## 📋 项目定位总结

### 主产品线
1. **autoresearch** - 原创产品（API-first）
2. **claude_cli** - 方法论资产（教程/模板）

### 内部资产
3. **claude_cli-private** - 中文内部版

### 基础设施
4. **openclaw-memory** - 待拆仓（三层架构）

### 素材仓
5. **ai-tools-compendium** - 研究冲刺档案馆
6. **finance-knowledge-base** - 语料仓 + 处理流水线
7. **ai-knowledge-graph** - 语料仓

---

## 🚀 下一步行动

### 立即执行（今天）
1. ✅ 确认诊断和建议
2. ⏳ 清理 ._*/Git 污染（所有仓库）
3. ⏳ 重构 autoresearch（API-first）

### 本周重点
1. ⏳ 修 ai-tools-compendium 索引
2. ⏳ 拆分 openclaw-memory
3. ⏳ 添加 claude_cli 自动化验证

### 长期目标
1. ⏳ 建立可持续的维护流程
2. ⏳ 完善项目文档和自动化
3. ⏳ 建立社区反馈机制

---

**诊断时间**: 2026-03-25 15:27
**诊断者**: 大佬
**状态**: ✅ 确认
**下一步**: 清理污染 + 重构 autoresearch
