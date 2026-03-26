# macOS M1 单机安全实验环境

这套方案面向 `autonomous-agent-stack` 的本地 AI 探索场景，目标是：

- 让 Agent 能自由写 Python、跑容器、生成日志
- 不碰主账号的家目录和敏感配置
- 把磁盘、CPU、内存和文件系统边界收紧

## 设计原则

1. 主账号与实验账号物理隔离
2. Agent 只看见 `ai_lab` 的工作目录
3. 日志和产物放在独立 APFS 卷，避免把 SSD 写满
4. 容器只给 ARM64、固定 CPU、固定内存
5. 不挂载 `/etc`、`~/.ssh`、主账号家目录

## 推荐拓扑

```text
macOS Host
├── 主账号：your-main-account
└── 标准副账号：ai_lab
    ├── /Users/ai_lab/workspace   <- 唯一可写交换区
    ├── /Users/ai_lab/.cache      <- 可选，独立小缓存
    └── APFS quota volume         <- 硬限制空间上限

Docker (Apple Silicon)
├── platform: linux/arm64
├── python:3.11-slim-bookworm
├── cpus: "4"
├── memory: "2g"
└── volume: /Users/ai_lab/workspace:/workspace:rw
```

## 关键说明

- **标准副账号**：用于降低对主账号的误操作风险，但不是安全边界本身。
- **真正的磁盘硬限制**：macOS 对普通用户目录没有 Linux 式通用 quota；要做硬限制，最好把工作区放到 **独立 APFS 卷**，用 `-quota` 控制容量。
- **双向交换区**：容器只挂载 `/Users/ai_lab/workspace/`，宿主和容器都通过这个目录交换文件。
- **禁挂载敏感目录**：不要把 `/etc`、`~/.ssh`、`~/.zshrc`、`~/Library` 之类目录映射进容器。

## 目录约定

```bash
/Users/ai_lab/
├── workspace/        # 唯一给 Agent 的读写区
├── logs/             # 可选：宿主机审计日志
└── .cache/           # 可选：小缓存，建议单独限制
```

