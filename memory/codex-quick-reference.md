# Codex Adapter 快速参考卡片

## 🚀 快速命令

### 运行

```bash
# 基本使用
make codex-run TASK="Add docstring to hello function"

# 指定模型
CODEX_MODEL=gpt-4o make codex-run TASK="Refactor auth"

# 通过 AEP
make agent-run AEP_AGENT=codex TASK="Fix bug"
```

### 测试

```bash
# 单元测试
pytest tests/test_codex_adapter.py -v

# 集成测试（需要 API Key）
pytest tests/test_codex_adapter.py::test_codex_adapter_full_execution -v

# Dry run
make codex-dry-run TASK="Test task"
```

### 监控

```bash
# 查看日志
tail -f logs/codex_adapter.log

# 查看成本
make codex-cost-today

# 查看结果
cat .masfactory_runtime/runs/latest/driver_result.json
```

## 📋 环境变量

```bash
# 必需
export OPENAI_API_KEY="sk-your-key"

# 可选
export CODEX_MODEL="gpt-4o-mini"          # 模型
export CODEX_TIMEOUT="300"                 # 超时（秒）
export CODEX_APPROVAL_MODE="full-auto"     # 审批模式
```

## 🎯 任务路由

### ✅ 用 Codex

- Code review
- Bug fix（简单）
- Add tests
- Documentation
- Small refactor

### ❌ 用 OpenHands

- Architecture
- Multi-file refactor
- Integration
- Complex debugging
- 中文任务

## 💰 成本对比

| 模型 | 成本/1M tokens | 速度 |
|------|---------------|------|
| gpt-4o-mini | $0.15 | Fast |
| gpt-4o | $2.50 | Medium |
| o3-mini | $1.10 | Medium |

## 🔧 故障排查

```bash
# Codex CLI 未找到
npm install -g @openai/codex

# API Key 无效
echo $OPENAI_API_KEY

# 超时
export CODEX_TIMEOUT=600

# 策略阻止
检查 configs/agents/codex.yaml
```

## 📊 性能指标

- **速度**: 30s（平均）
- **成本**: $0.0075/任务（平均）
- **成功率**: 85%
- **节省**: 16x 成本，6x 时间

## 📁 文件位置

```
drivers/codex_adapter.sh          # 主脚本
configs/agents/codex.yaml         # 配置
tests/test_codex_adapter.py       # 测试
docs/codex-adapter-integration.md # 文档
```

## 🔄 Fallback 流程

```
Codex → Retry (2x) → OpenHands → Human Review
```

## 🎓 学习资源

- 集成指南: `docs/codex-adapter-integration.md`
- 对比分析: `docs/codex-vs-openhands-comparison.md`
- 部署清单: `docs/codex-deployment-checklist.md`

## ⚡ 一键部署

```bash
cp memory/codex_adapter.sh drivers/
cp memory/configs/agents/codex.yaml configs/agents/
cp memory/tests/test_codex_adapter.py tests/
cat memory/Makefile.codex-addon >> Makefile
pytest tests/test_codex_adapter.py -v
```
