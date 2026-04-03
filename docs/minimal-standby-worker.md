# Minimal Standby Worker

这版不是完整 scheduler。

它的准确定性是：

- `manual lease-based standby worker`
- `file-backed queue`
- `single-active execution helper`

不要把它叫成：

- automatic failover
- host scheduler
- production standby cluster
- high availability control plane

它只做两件事：

1. 用一个共享 `lease.json` 指定唯一 active host
2. 让多个 worker 盯同一个 `JobSpec` inbox，但只有 lease owner 会真正执行

这正对应最小“备用组”思路：

- Linux 正常时，lease 指向 Linux，Mac worker 常驻但空转
- Linux 挂掉时，手动切 lease 到 Mac
- Mac 看到 lease 归自己，马上开始处理 pending job

## Scope

这版只覆盖：

- file-backed `pending/running/completed/failed` inbox
- lease-gated single-active worker
- manual enqueue / worker scripts
- macOS `launchd` 模板

这版不覆盖：

- routing 变更
- builder host selection
- automatic failover
- heartbeat-based lease transfer
- fencing token
- shared queue integration
- scheduler semantics
- manager / planner integration

## 目录结构

默认运行态路径：

```text
artifacts/runtime/standby/
  lease.json
  jobs/
    pending/
    running/
    completed/
    failed/
```

`lease.json` 最小格式：

```json
{
  "owner": "linux-1",
  "version": 1
}
```

## 为什么这版不改 routing / builder

这套最小版故意把边界卡死：

- `routing` 只负责“选 agent / mode / policy overlay”
- `builder` 只负责把 request materialize 成 `JobSpec`
- standby 只负责“当前这台 host 有没有资格消费 pending job”

也就是说：

- 不在 routing 里判断 host 存活
- 不在 builder 里切 host
- 不让 backup worker 自作主张自动接管

唯一决策就是 `lease.json`。

## 先跑起来

### 1. 初始化 lease

```bash
mkdir -p artifacts/runtime/standby/jobs/{pending,running,completed,failed}
cat > artifacts/runtime/standby/lease.json <<'EOF'
{
  "owner": "linux-1",
  "version": 1
}
EOF
```

### 2. 入队一个 job

```bash
PYTHONPATH=src .venv/bin/python scripts/standby_enqueue_job.py \
  --agent openhands \
  --task "Create src/demo_math.py with add(a, b) and tests."
```

### 3. 启动 Mac standby worker

```bash
PYTHONPATH=src .venv/bin/python scripts/standby_host_worker.py \
  --host-id mac-1 \
  --poll-seconds 5
```

如果当前 lease owner 不是 `mac-1`，worker 会保持 standby。

### 4. 手动切换接管

Linux 挂掉后，手动改 lease：

```bash
cat > artifacts/runtime/standby/lease.json <<'EOF'
{
  "owner": "mac-1",
  "version": 2
}
EOF
```

Mac worker 下一轮轮询会开始消费 `pending/` 里的 job。

## 结果文件

- 领取中的 job 会进入 `jobs/running/`
- 成功 job 会进入 `jobs/completed/`
- 失败或 `human_review` 会进入 `jobs/failed/`

文件里会包含：

- 原始 `JobSpec`
- `claimed_by` / `claimed_at`
- `run_summary`
- `error`

## launchd 常驻

模板文件：

- `deployment/launchd/com.autoresearch.standby-host-worker.plist.template`

把其中的占位符替换成你的实际路径后，放到：

```text
~/Library/LaunchAgents/com.autoresearch.standby-host-worker.plist
```

然后：

```bash
launchctl unload ~/Library/LaunchAgents/com.autoresearch.standby-host-worker.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.autoresearch.standby-host-worker.plist
launchctl start com.autoresearch.standby-host-worker
```

## 当前边界

这版是最小可运行版，不包含：

- fencing
- 自动心跳切换
- 自动 failover
- shared queue
- 现有 manager/planner SQLite 队列接入

如果要继续升级，下一步再补：

- lease compare-and-swap
- worker heartbeat
- active host fencing token
- 把 `manager_agent_dispatches` 或 `autoresearch_plans` 接到同一个 single-active worker
