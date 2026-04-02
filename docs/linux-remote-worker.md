# Linux Primary Runtime Guide

这份指南的目标很单纯：把一台 Linux 机器尽快收口成这套仓库的默认运行面，而不是把它当成 Mac 的 worker。

固定拓扑：

- `Linux = 主助理 / 主开发执行面 / 主值班面`
- `Mac = 备用管家 / 备用执行面 / 控制台`
- `同仓库、同 manifest、不同 runtime 配置`
- 不允许分叉成两套实现

默认分工：

- Linux 跑 `OpenHands`、长任务、benchmark、`Telegram` 主值班
- Linux 负责主执行链、主 `/task` 路径、主 agent 宿主
- Mac 保留备用执行能力，但默认不常驻、不接主执行链

故障切换：

- 平时 Linux 主跑
- Mac 先检查 Linux 管家在线性：`health / heartbeat / 可达性`
- Linux 在线就转交 Linux
- Linux 掉线时，Mac 只接低到中风险、短时、可人工复核任务
- Linux 不在线、超时未响应或明确拒绝时，Mac 备用接管
- Linux 恢复后切回 Linux

## 为什么 Linux 先走 `host`

这个仓库在 Mac 上对 `ai-lab + Colima + 外置盘` 做过加固，但 Linux 主运行面的默认起步路径更简单：

- 避开 Colima / Mac socket 差异
- 先验证真实 OpenHands 能写代码、跑测试、产 patch
- 先把 Linux 主 `/task` 和主值班跑稳
- 等业务链稳定后，再考虑把 Linux 执行面容器化

所以第一阶段建议固定：

```bash
export OPENHANDS_RUNTIME=host
```

## 最小准备

要求：

- Python `3.11+`
- `git`
- `curl`
- 建议安装 `gh`
- 建议安装 `tmux`

初始化：

```bash
git clone <your-repo-url>
cd autonomous-agent-stack

python3.11 -m venv .venv
source .venv/bin/activate

make setup
set -a
source .env.linux
set +a
make doctor-linux
```

`make doctor-linux` 会额外检查几件对 Linux 主运行面最关键的事：

- 当前是否真在 Linux 上
- `OPENHANDS_RUNTIME` 是否设成 `host`
- `DOCKER_HOST` 是否错误继承了 Mac / Colima 路径
- `.masfactory_runtime`、`artifacts`、`logs` 是否可写
- `gh` 和 `tmux` 是否可用

## 推荐环境变量

最低限度：

```bash
export AUTORESEARCH_RUNTIME_HOST=linux
export AUTORESEARCH_EXECUTION_ROLE=primary
export AUTORESEARCH_TASK_RISK_PROFILE=full
export OPENHANDS_RUNTIME=host
export AUTORESEARCH_API_HOST=0.0.0.0
export AUTORESEARCH_API_PORT=8001
```

Mac 备用机只在本地覆盖 runtime 身份，不改单仓库实现：

```bash
export AUTORESEARCH_RUNTIME_HOST=macos
export AUTORESEARCH_EXECUTION_ROLE=backup
export AUTORESEARCH_TASK_RISK_PROFILE=low_medium
```

如果 Linux 节点上已经准备好了独立 OpenHands CLI，可再补：

```bash
export OPENHANDS_LOCAL_BIN=/absolute/path/to/openhands
```

如果由 Linux 节点直接访问模型：

```bash
export LLM_MODEL=openai/glm-5
export LLM_API_KEY=...
export LLM_BASE_URL=...
```

## 启动方式

API：

```bash
OPENHANDS_RUNTIME=host make start
```

真实 OpenHands worker 冒烟：

```bash
OPENHANDS_RUNTIME=host make openhands OH_TASK="Create apps/demo/lead_capture.py with tests."
```

AEP runner：

```bash
OPENHANDS_RUNTIME=host make agent-run \
  AEP_AGENT=openhands \
  AEP_TASK="Create apps/demo/lead_capture.py with tests."
```

promotion：

```bash
PYTHONPATH=src .venv/bin/python scripts/promote_run.py \
  --run-id <run-id> \
  --push \
  --open-draft-pr
```

## Linux 主运行面怎么用最值钱

最实用的用法不是“把 Linux 也当第二控制台”，而是把默认运行面真正放到 Linux。

### 模式 1: Linux 主运行 + Mac 备用控制台

最推荐。

- Linux 继续收 Telegram
- Linux 负责 OpenHands / pytest / promotion / benchmark
- Mac 平时只做观察、调试、紧急接管

### 模式 2: Linux 长任务箱

适合长任务。

- SSH 到 Linux
- 用 `tmux` 起会话
- 在 tmux 里跑真实 OpenHands 和全量测试

示例：

```bash
tmux new -s aas-worker
cd /path/to/autonomous-agent-stack
source .venv/bin/activate
OPENHANDS_RUNTIME=host make start
```

### 模式 3: Mac 故障接管窗口

只在 Linux 掉线时启用。

- Mac 只接低到中风险、短时、可人工复核任务
- 不在 Mac 上恢复主值班常驻
- Linux 恢复后，主动切回 Linux

## 最佳实践

### 1. 先 `host`，后容器

Linux 第一阶段先固定：

```bash
export OPENHANDS_RUNTIME=host
```

先证明这 4 件事都稳定，再考虑容器化：

- OpenHands 能写入业务目录
- pytest 能跑通
- patch 能产出
- promotion 能完成

### 2. 把 Linux 当主运行面，不当备用 worker

最优分工是：

- Linux 收 Telegram 和主 `/task`
- Linux 跑重任务和长测试
- Mac 只做备用控制台和备用执行面

这样能把“默认运行面”故障和“备用控制台”故障拆开。

### 3. 永远先跑 `make doctor-linux`

每次新节点上线、重装 Python、迁移目录、换用户后，先跑：

```bash
OPENHANDS_RUNTIME=host make doctor-linux
```

不要先跑长任务，再回头找 `DOCKER_HOST` 或目录权限问题。

### 4. 用 `tmux` 托管长任务

不要把真实 OpenHands 长跑直接挂在脆弱 SSH 会话上。

最小建议：

```bash
tmux new -s aas-worker
```

### 5. 不要把 Mac 备用机扩成第二套实现

- 同一套仓库
- 同一套 manifest
- 同一套 agent 定义
- 只通过本地 runtime 配置区分 Linux / Mac

### 6. 不要把 Mac 的运行态变量原样 rsync 过去

尤其是：

- `DOCKER_HOST`
- `COLIMA_*`
- `/Users/...`
- `/Volumes/...`

Linux 节点要有自己的本地路径和本地执行假设。

### 7. 业务任务优先落 `apps/`

Linux 节点最适合跑边界清晰的业务任务，例如：

- `apps/<surface>/...`
- `tests/apps/...`

不要一上来拿它做模糊的大范围框架重构。

## 常见坑

### 1. 继承了 Mac 的 `DOCKER_HOST`

现象：

- `make doctor-linux` 提示 `DOCKER_HOST` 指向 `/Users/.../.colima/...`

处理：

```bash
unset DOCKER_HOST
```

### 2. 运行目录不可写

现象：

- `.masfactory_runtime`
- `artifacts`
- `logs`

处理：

```bash
mkdir -p .masfactory_runtime artifacts logs
chmod -R u+rwX .masfactory_runtime artifacts logs
```

### 3. 想一上来复制 `ai-lab`

不建议。

Linux 远端第一阶段先用 `host` runtime 打通：

- Manager
- Worker
- Validator
- Promotion

把这条链跑稳后，再考虑容器化隔离。

## 一句话建议

Linux 节点现在最有价值的角色是“干净、稳定、能长跑的执行机”，不是去复刻 Mac 的 Colima 环境。
