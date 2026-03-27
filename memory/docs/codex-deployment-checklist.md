# Codex Adapter 部署清单

## 前置条件检查

### ✅ 必需

- [ ] Python 3.9+ 已安装
- [ ] Node.js 18+ 已安装
- [ ] Git 已安装
- [ ] OpenAI API Key（或 LiteLLM Proxy）

### 🔧 可选

- [ ] Docker（用于 OpenHands）
- [ ] LiteLLM Proxy（用于 GLM-5）
- [ ] Make（用于简化命令）

## 部署步骤

### 1. 克隆仓库

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack
git checkout codex/openhands-controlled-backend
git pull
```

### 2. 安装 Codex CLI

```bash
# 使用 npm
npm install -g @openai/codex

# 验证安装
codex --version
# 输出: 0.x.x
```

### 3. 配置环境变量

```bash
# 方案 A：直接使用 OpenAI
export OPENAI_API_KEY="sk-your-openai-key"

# 方案 B：使用 GLM-5（推荐，成本更低）
# 先启动 LiteLLM Proxy
export ZHIPUAI_API_KEY="your-glm5-key"
litellm --model zhipu/glm-5 --port 4000 &

# 然后配置 Codex
export CODEX_MODEL="zhipu/glm-5"
export LLM_BASE_URL="http://localhost:4000"
```

### 4. 安装依赖

```bash
make setup
# 或
pip install -r requirements.txt
```

### 5. 验证安装

```bash
# 运行诊断
make doctor

# 应该看到:
# ✅ Python 3.x
# ✅ Codex CLI 0.x
# ✅ OpenAI API Key (或 LiteLLM Proxy)
```

### 6. 运行测试

```bash
# 单元测试
pytest tests/test_codex_adapter.py -v

# 应该看到:
# test_read_job_field_basic PASSED
# test_missing_required_env_vars PASSED
# ...
# 8 passed
```

### 7. 试运行

```bash
# Dry run（不实际执行）
make codex-dry-run TASK="Test task"

# 应该看到:
# [aep][codex] starting run_id=...
# [aep][codex] DRY RUN - skipping execution
# ✅ driver_result.json generated
```

## 配置文件

### 1. 创建 codex.yaml

```bash
# 复制模板
cp configs/agents/openhands.yaml configs/agents/codex.yaml

# 编辑配置
nano configs/agents/codex.yaml
```

### 2. 关键配置项

```yaml
# configs/agents/codex.yaml
adapter:
  id: codex
  version: "1.0.0"

model:
  default: "gpt-4o-mini"  # 或 "zhipu/glm-5"

execution:
  approval_mode: "full-auto"
  timeout_sec: 300

policy:
  max_changed_files: 20
  allowed_paths:
    - "src/**"
    - "tests/**"
```

### 3. 环境变量文件

```bash
# 创建 .env（不要提交到 Git）
cat > .env <<EOF
OPENAI_API_KEY=sk-your-key
CODEX_MODEL=gpt-4o-mini
CODEX_TIMEOUT=300
EOF

# 添加到 .gitignore
echo ".env" >> .gitignore
```

## 集成到 Makefile

### 1. 添加 Codex 目标

```bash
# 追加到 Makefile
cat Makefile.codex-addon >> Makefile
```

### 2. 验证 Makefile

```bash
make help | grep codex

# 应该看到:
# codex-run          - Run Codex adapter
# codex-test         - Run tests
# codex-dry-run      - Test without execution
```

## 工作流集成

### 1. Telegram Bot

```python
# src/gateway/telegram_webhook.py
# 添加 Codex 路由

@router.post("/telegram/codex")
async def codex_webhook(update: dict):
    task = update["message"]["text"]
    result = await run_agent(
        agent="codex",
        task=task,
    )
    return {"status": "ok", "result": result}
```

### 2. GitHub Actions

```yaml
# .github/workflows/codex-review.yml
name: Codex Code Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Codex Review
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          make codex-run TASK="Review this PR for bugs"
```

### 3. Git Hooks

```bash
# .git/hooks/pre-commit
#!/bin/bash
# 自动运行 Codex 审查

changed_files=$(git diff --cached --name-only | grep '\.py$')
if [ -n "$changed_files" ]; then
    make codex-run TASK="Review: $changed_files"
fi
```

## 监控和日志

### 1. 日志配置

```yaml
# configs/agents/codex.yaml
logging:
  level: "info"
  file: "logs/codex_adapter.log"
  to_aep_events: true
```

### 2. 查看日志

```bash
# 实时日志
tail -f logs/codex_adapter.log

# AEP 事件日志
cat .masfactory_runtime/runs/<run_id>/events.ndjson
```

### 3. 成本追踪

```bash
# 查看今日成本
make codex-cost-today

# 重置计数器
make codex-cost-reset
```

## 性能优化

### 1. 并发执行

```python
# scripts/concurrent_codex.py
import asyncio
from autoresearch.agent_protocol import run_agent_async

async def run_batch(tasks: list[str]):
    results = await asyncio.gather(*[
        run_agent_async(agent="codex", task=task)
        for task in tasks
    ])
    return results
```

### 2. 缓存机制

```yaml
# configs/agents/codex.yaml
cache:
  enabled: true
  ttl: 3600  # 1 hour
  max_size: 100
```

### 3. 模型预热

```bash
# 启动时预热（减少首次延迟）
codex --model gpt-4o-mini "ping" > /dev/null 2>&1
```

## 故障排查

### 问题 1：Codex CLI 未找到

```bash
# 症状
[aep][codex] codex CLI not found in PATH

# 解决
which codex  # 检查路径
npm install -g @openai/codex  # 重新安装
```

### 问题 2：API Key 无效

```bash
# 症状
[aep][codex] Invalid API key

# 解决
echo $OPENAI_API_KEY  # 检查是否设置
# 重新设置
export OPENAI_API_KEY="sk-your-key"
```

### 问题 3：超时

```bash
# 症状
[aep][codex] timed out after 300s

# 解决
export CODEX_TIMEOUT=600  # 增加到 10 分钟
```

### 问题 4：策略阻止

```bash
# 症状
status: policy_blocked

# 解决
# 检查 configs/agents/codex.yaml
# 确保文件在 allowed_paths 中
# 确保不在 forbidden_paths 中
```

## 安全检查

### ✅ 必须确认

- [ ] `.env` 已添加到 `.gitignore`
- [ ] API Key 未硬编码在代码中
- [ ] `forbidden_paths` 包含 `.git/**`, `**/*.key`
- [ ] `max_changed_files` 设置合理（< 50）
- [ ] 网络访问已禁用（除非必要）

### 🔒 生产环境

```yaml
# configs/agents/codex.prod.yaml
policy:
  network: "disabled"
  max_changed_files: 10
  forbidden_paths:
    - ".git/**"
    - "**/*.key"
    - "**/*.pem"
    - "**/.env*"
    - "logs/**"
  cleanup_on_success: true
  retain_workspace_on_failure: true
```

## 回滚计划

### 如果 Codex 出问题

```bash
# 1. 切换回 OpenHands
make agent-run AEP_AGENT=openhands TASK="..."

# 2. 禁用 Codex
mv drivers/codex_adapter.sh drivers/codex_adapter.sh.disabled

# 3. 回滚配置
git checkout configs/agents/codex.yaml
```

## 验收测试

### 完整流程测试

```bash
# 1. 单元测试
make codex-test

# 2. 集成测试
pytest tests/test_codex_adapter.py -m integration

# 3. 端到端测试
make codex-run TASK="Add docstring to hello function"

# 4. 检查结果
cat .masfactory_runtime/runs/latest/driver_result.json

# 5. 验证变更
git diff
```

### 成功标准

- ✅ 所有单元测试通过（8/8）
- ✅ Dry run 生成 driver_result.json
- ✅ 真实执行修改文件
- ✅ 日志正常记录
- ✅ 成本追踪工作
- ✅ Fallback 到 OpenHands 成功

## 部署后检查

### 第 1 天

```bash
# 检查日志
tail -f logs/codex_adapter.log

# 检查成本
make codex-cost-today

# 检查成功率
grep "status" .masfactory_runtime/runs/*/driver_result.json | jq -r '.status' | sort | uniq -c
```

### 第 1 周

```bash
# 检查性能
cat .masfactory_runtime/runs/*/driver_result.json | \
  jq -r '.metrics.duration_ms' | \
  awk '{sum+=$1; count++} END {print "Avg:", sum/count, "ms"}'

# 检查成本趋势
# 手动记录每日成本
```

### 第 1 月

```bash
# 生成月度报告
python scripts/monthly_report.py --agent codex

# 调整策略
# 根据数据调整 routing rules
```

## 下一步

1. ✅ 部署 Codex Adapter
2. 🔜 监控 1 周
3. 🔜 调整路由规则
4. 🔜 添加 GLM-5 Adapter
5. 🔜 优化成本

## 支持

- 文档：`docs/codex-adapter-integration.md`
- 测试：`tests/test_codex_adapter.py`
- 配置：`configs/agents/codex.yaml`
- 问题：创建 GitHub Issue
