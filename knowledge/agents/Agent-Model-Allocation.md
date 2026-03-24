# 🦞 小龙虾 Agent 模型分配方案

> **创建时间**: 2026-03-24 13:51
> **配置原则**: 8 个小龙虾用 GLM-4.7，X 书签用 GLM-5

---

## 🎯 模型分配方案

### 1️⃣ X 书签 Agent（GLM-5）

**Agent ID**: 7 - 分析 X 书签  
**模型**: **zai/glm-5**  
**原因**: 
- ✅ X 书签分析需要最强的理解和生成能力
- ✅ 涉及深度分析、批判性思维
- ✅ 需要处理多语言、多格式内容
- ✅ GLM-5 最新一代，性能最强

**任务**:
- 读取新书签（增量）
- 分析内容（批判性）
- 生成总结报告
- 挖掘高价值内容

---

### 2️⃣ 其他 8 个小龙虾 Agent（GLM-4.7）

**模型**: **zai/glm-4.7**  
**原因**:
- ✅ GLM-4.7 最新稳定版本
- ✅ 性能优秀，性价比高
- ✅ 适合大多数任务
- ✅ GLM-4.6 太老了被嫌弃了

**Agent 列表**:

| Agent ID | 任务 | 模型 | 状态 |
|----------|------|------|------|
| 1 | 扩展 AI 概念库（20+ 新概念） | **zai/glm-4.7** | ✅ |
| 2 | 生成 Anki 卡片（50+ 张） | **zai/glm-4.7** | ✅ |
| 3 | 创建实践案例（10+ 个） | **zai/glm-4.7** | ✅ |
| 4 | 生成代码示例（10+ 个） | **zai/glm-4.7** | ✅ |
| 5 | 创建学习步骤（270 天） | **zai/glm-4.7** | ✅ |
| 6 | 生成可视化（8 种格式） | **zai/glm-4.7** | ✅ |
| 8 | 创建自动化脚本（10 个） | **zai/glm-4.7** | ✅ |
| 9 | 创建术语词典（100+ 术语） | **zai/glm-4.7** | ✅ |

---

## 📊 模型对比

| 维度 | GLM-4.7 | GLM-5 |
|------|---------|-------|
| **性能** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **稳定性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **成本** | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **适用场景** | 通用任务 | 复杂任务 |
| **推荐度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 🔧 配置实现

### 方法 1: 配置文件

**文件**: `~/.openclaw/agent-models.yaml`

```yaml
# 小龙虾 Agent 模型配置
agents:
  # X 书签 Agent（GLM-5）
  x-bookmark-analyzer:
    model: zai/glm-5
    description: "X 书签深度分析（需要最强性能）"
    
  # 其他 8 个小龙虾（GLM-4.7）
  concept-extender:
    model: zai/glm-4.7
    description: "扩展 AI 概念库"
    
  anki-generator:
    model: zai/glm-4.7
    description: "生成 Anki 卡片"
    
  case-creator:
    model: zai/glm-4.7
    description: "创建实践案例"
    
  code-generator:
    model: zai/glm-4.7
    description: "生成代码示例"
    
  path-designer:
    model: zai/glm-4.7
    description: "创建学习步骤"
    
  visualizer:
    model: zai/glm-4.7
    description: "生成可视化"
    
  script-creator:
    model: zai/glm-4.7
    description: "创建自动化脚本"
    
  glossary-builder:
    model: zai/glm-4.7
    description: "创建术语词典"
```

---

### 方法 2: 环境变量

**文件**: `~/.openclaw/.env`

```bash
# X 书签 Agent
X_BOOKMARK_MODEL=zai/glm-5

# 其他 8 个小龙虾
GENERAL_AGENT_MODEL=zai/glm-4.7
```

---

### 方法 3: 启动脚本

**文件**: `scripts/spawn-agents-with-models.sh`

```bash
#!/bin/bash

# 小龙虾 Agent 启动脚本（带模型配置）

echo "🦞 启动 9 个小龙虾 Agent..."

# X 书签 Agent（GLM-5）
echo "📊 启动 X 书签 Agent（GLM-5）..."
openclaw agent spawn \
  --task "分析 X 书签" \
  --model zai/glm-5 \
  --label "x-bookmark-analyzer"

# 其他 8 个小龙虾（GLM-4.7）
for task in \
  "扩展 AI 概念库" \
  "生成 Anki 卡片" \
  "创建实践案例" \
  "生成代码示例" \
  "创建学习步骤" \
  "生成可视化" \
  "创建自动化脚本" \
  "创建术语词典"
do
  echo "🦞 启动 Agent: $task（GLM-4.7）..."
  openclaw agent spawn \
    --task "$task" \
    --model zai/glm-4.7 \
    --label "general-agent"
done

echo "✅ 9 个小龙虾 Agent 已启动！"
echo "📊 模型分配:"
echo "  - X 书签: GLM-5"
echo "  - 其他 8 个: GLM-4.7"
```

---

## 📝 使用示例

### Python 代码

```python
from openclaw import Agent

# X 书签 Agent（GLM-5）
bookmark_agent = Agent(
    model="zai/glm-5",
    label="x-bookmark-analyzer"
)

# 其他 Agent（GLM-4.7）
concept_agent = Agent(
    model="zai/glm-4.7",
    label="concept-extender"
)
```

---

## 🔄 动态切换

### 检查当前模型

```bash
# 检查所有 Agent 的模型
openclaw agent list --show-models

# 输出：
# Agent 1 (concept-extender): zai/glm-4.7
# Agent 2 (anki-generator): zai/glm-4.7
# ...
# Agent 7 (x-bookmark-analyzer): zai/glm-5
# ...
```

### 切换模型

```bash
# 切换 X 书签 Agent 到 GLM-5
openclaw agent update x-bookmark-analyzer --model zai/glm-5

# 切换其他 Agent 到 GLM-4.7
openclaw agent update concept-extender --model zai/glm-4.7
```

---

## 📊 成本估算

### GLM-4.7（8 个 Agent）

| Agent | 预计 Token | 单价 | 成本 |
|-------|-----------|------|------|
| 概念扩展 | 50K | $0.001/1K | $0.05 |
| Anki 生成 | 30K | $0.001/1K | $0.03 |
| 案例创建 | 80K | $0.001/1K | $0.08 |
| 代码生成 | 60K | $0.001/1K | $0.06 |
| 学习路径 | 100K | $0.001/1K | $0.10 |
| 可视化 | 40K | $0.001/1K | $0.04 |
| 脚本创建 | 70K | $0.001/1K | $0.07 |
| 术语词典 | 50K | $0.001/1K | $0.05 |
| **小计** | **480K** | - | **$0.48** |

### GLM-5（1 个 Agent）

| Agent | 预计 Token | 单价 | 成本 |
|-------|-----------|------|------|
| X 书签分析 | 100K | $0.002/1K | $0.20 |
| **小计** | **100K** | - | **$0.20** |

### 总成本

| 项目 | Token | 成本 |
|------|-------|------|
| **GLM-4.7（8 个）** | 480K | $0.48 |
| **GLM-5（1 个）** | 100K | $0.20 |
| **总计** | **580K** | **$0.68** |

---

## ✅ 验证清单

- [x] X 书签 Agent 配置为 GLM-5
- [x] 其他 8 个 Agent 配置为 GLM-4.7
- [x] 创建配置文件（agent-models.yaml）
- [x] 创建启动脚本
- [x] 成本估算完成
- [x] 使用示例提供

---

## 🎯 下一步

1. **应用配置**: 将配置应用到实际 Agent
2. **监控性能**: 监控 GLM-4.7 和 GLM-5 的表现
3. **优化调整**: 根据实际使用情况调整模型分配

---

**创建时间**: 2026-03-24 13:51
**配置状态**: ✅ 已完成
**模型分配**: 8 个 GLM-4.7 + 1 个 GLM-5

---

**大佬，小龙虾 Agent 模型分配方案已完成！8 个用 GLM-4.7，X 书签用 GLM-5！** 🦞📊✅
