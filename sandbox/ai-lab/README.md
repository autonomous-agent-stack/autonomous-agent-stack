# ai_lab 安全实验环境

这套配置把 Agent 限在一个很小的边界里：

- 只允许读写 `/Users/ai_lab/workspace`
- 容器使用 `python:3.11-slim-bookworm`
- 架构固定为 `linux/arm64`
- CPU 限制为 4 核，内存限制为 2GB

## 启动顺序

1. 先创建 `ai_lab` 用户和 APFS 限额卷
2. 再确认 `/Users/ai_lab/workspace` 已挂载
3. 最后启动 Docker Compose

## 启动

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack/sandbox/ai-lab
docker compose up
```

## 验证

```bash
./scripts/check_ai_lab_guardrails.sh
```

