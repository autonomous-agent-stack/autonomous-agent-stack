# Adapter 系统 - 快速开始指南

**5分钟上手Adapter系统**

---

## 🎯 目标

完成本指南后，你将：
- ✅ 部署3个Adapter（Codex/GLM-5/Claude）
- ✅ 运行第一个任务
- ✅ 理解自动路由机制

---

## 📋 前置要求

### 必需

- Python 3.9+
- Node.js 18+（Codex需要）
- Git

### API密钥（至少一个）

- OpenAI API Key（Codex）
- 智谱AI API Key（GLM-5）
- Anthropic API Key（Claude）

---

## 🚀 步骤1：部署（2分钟）

### 方式A：自动部署

```bash
# 1. 进入项目目录
cd /Volumes/PS1008/Github/autonomous-agent-stack

# 2. 运行部署脚本
bash /Users/iCloud_GZ/github_GZ/openclaw-memory/memory/deploy-adapters.sh

# 3. 验证部署
make codex-test
```

### 方式B：手动部署

```bash
# 1. 复制文件
cp memory/codex_adapter.sh drivers/
cp memory/configs/agents/codex.yaml configs/agents/
cp memory/tests/test_codex_adapter.py tests/

# 2. 更新Makefile
cat memory/Makefile.codex-addon >> Makefile

# 3. 设置权限
chmod +x drivers/*.sh
```

---

## 🔑 步骤2：配置API密钥（1分钟）

### Codex

```bash
export OPENAI_API_KEY="sk-your-openai-key"
```

### GLM-5

```bash
export ZHIPUAI_API_KEY="your-glm5-key"
```

### Claude

```bash
export ANTHROPIC_API_KEY="your-claude-key"
```

---

## ✅ 步骤3：验证（1分钟）

```bash
# 测试Codex
make codex-test

# 应该看到:
# 8 passed in 2.34s
```

---

## 🎮 步骤4：运行第一个任务（1分钟）

### 使用Codex

```bash
make codex-run TASK="Add docstring to hello function"
```

### 使用GLM-5

```bash
make glm5-run TASK="添加中文文档到hello函数"
```

### 使用Claude

```bash
make claude-run TASK="Review code quality of main.py"
```

---

## 📊 查看结果

```bash
# 查看最新结果
cat .masfactory_runtime/runs/latest/driver_result.json

# 查看日志
tail -f logs/codex_adapter.log
```

---

## 🔄 自动路由（高级）

系统会自动选择最合适的Adapter：

```python
# 中文任务 → GLM-5
make agent-run TASK="添加文档"

# 复杂任务 → Claude
make agent-run TASK="Design architecture"

# 简单任务 → Codex
make agent-run TASK="Fix typo"
```

---

## 💰 成本监控

```bash
# 查看今日成本
make codex-cost-today

# 设置成本上限
export CODEX_MAX_COST_PER_DAY=10.00
```

---

## 🎯 常见任务

### 代码审查

```bash
make codex-run TASK="Review PR #123"
```

### Bug修复

```bash
make codex-run TASK="Fix off-by-one error in loop"
```

### 添加测试

```bash
make codex-run TASK="Add unit tests for utils.py"
```

### 文档编写

```bash
# 英文
make codex-run TASK="Add README"

# 中文
make glm5-run TASK="添加中文README"
```

---

## 🔧 故障排查

### 问题1：API Key未设置

```bash
# 错误: ZHIPUAI_API_KEY not set
# 解决:
export ZHIPUAI_API_KEY="your-key"
```

### 问题2：超时

```bash
# 错误: Execution timed out
# 解决:
export CODEX_TIMEOUT=600  # 增加到10分钟
```

### 问题3：Codex CLI未找到

```bash
# 错误: codex CLI not found
# 解决:
npm install -g @openai/codex
```

---

## 📚 下一步

### 学习资源

- 完整文档: `docs/codex-adapter-integration.md`
- 对比分析: `docs/adapter-comparison-matrix.md`
- 性能基准: `docs/adapter-benchmark-results.md`
- ROI分析: `docs/adapter-roi-analysis.md`

### 高级功能

- 🔧 自动路由配置
- 💰 成本优化
- 📊 性能监控
- 🔄 Fallback机制

---

## ✅ 完成！

你现在已经：

- ✅ 部署了3个Adapter
- ✅ 配置了API密钥
- ✅ 运行了第一个任务
- ✅ 理解了自动路由

**开始你的AI编程之旅吧！** 🚀

---

## 💬 获取帮助

- 文档: `docs/` 目录
- 测试: `tests/` 目录
- 配置: `configs/agents/` 目录
- 问题: 创建GitHub Issue
