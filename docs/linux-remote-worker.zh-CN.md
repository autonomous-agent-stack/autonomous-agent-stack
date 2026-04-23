# Linux 远程 Worker 指南

这份指南的目标很单纯：把一台 Linux 机器尽快变成这套仓库的稳定执行节点。

当前最推荐的拓扑不是"Linux 完全复制 Mac/Colima"，而是：

- Mac/Colima：control plane + ai-lab sandbox
- Linux：专用 worker，负责运行 agent 执行任务

## 为什么 Linux 先走 `host`

Linux 上的 `ai-lab` 遇到几个实际问题：

1. **Docker-in-Docker 开销**：Linux worker 本身就在容器里运行 agent，再套一层 ai-lab sandbox 会明显拖慢启动
2. **权限传递复杂性**：DIND 模式下把 host 的 Docker socket 和 volume 映射进 ai-lab 容器，配置和维护都比 host provider 复杂
3. **资源利用率**：直接用 host provider 可以让 agent 更直接地访问宿主机的 Docker 资源

因此，Linux 侧推荐使用 `process` provider，而不是复制 Mac 的 `ai-lab` 沙箱链路。

## 快速配置

### 1. 基础环境

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y git curl wget vim python3 python3-pip python3-venv

# 克隆仓库
git clone https://github.com/srxly888-creator/autonomous-agent-stack.git
cd autonomous-agent-stack

# 设置 Python 环境
make setup
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置必要的变量
vim .env
```

必需配置：

```bash
# LLM 配置
LLM_MODEL=gpt-4
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.openai.com/v1

# 执行模式
AUTORESEARCH_MODE=minimal
```

### 3. 配置 Docker

```bash
# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户添加到 docker 组（避免 sudo）
sudo usermod -aG docker $USER

# 重新登录以使组权限生效
```

### 4. 启动服务

```bash
# 运行健康检查
make doctor

# 启动服务
make start

# 验证服务状态
curl http://127.0.0.1:8001/health
```

## Worker 配置

### 作为 Worker 运行

如果这台 Linux 机器主要作为 worker 执行任务，可以配置为只运行 worker 服务：

```bash
# 只启动 worker
make start-worker

# 或者指定 worker 类型
AEP_WORKER_TYPE=openhands make start-worker
```

### 连接到 Control Plane

如果这台 worker 需要连接到远程 control plane：

```bash
# 在 .env 中配置 control plane 地址
CONTROL_PLANE_URL=http://your-control-plane:8001
WORKER_ID=linux-worker-1
WORKER_SECRET=your_worker_secret

# 启动 worker
make start-worker-remote
```

## 常见问题

### Docker 权限问题

如果遇到 Docker 权限错误：

```bash
# 临时解决（当前会话）
sudo usermod -aG docker $USER
newgrp docker

# 永久解决（重新登录后生效）
sudo usermod -aG docker $USER
```

### Python 环境问题

如果遇到 Python 环境问题：

```bash
# 清理并重新创建虚拟环境
rm -rf .venv
make setup

# 验证 Python 版本
python3 --version  # 应该是 3.11+
```

### 端口冲突

如果默认端口 8001 被占用：

```bash
# 在 .env 中修改端口
PORT=8002

# 或者在启动时指定
PORT=8002 make start
```

## 性能优化

### 1. 减少 Docker 镜像拉取时间

配置 Docker 镜像加速器：

```bash
# 编辑 Docker 配置
sudo vim /etc/docker/daemon.json

# 添加以下内容
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://docker.mirrors.ustc.edu.cn"
  ]
}

# 重启 Docker
sudo systemctl restart docker
```

### 2. 限制 Worker 并发

在 `.env` 中配置：

```bash
# 最大并发任务数
MAX_CONCURRENT_TASKS=2

# 单个任务最大执行时间（秒）
MAX_TASK_TIMEOUT=3600
```

### 3. 清理旧资源

定期清理 Docker 资源：

```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的容器
docker container prune

# 清理未使用的卷
docker volume prune

# 一键清理所有
docker system prune -a --volumes
```

## 监控和日志

### 查看 Worker 日志

```bash
# 查看 worker 日志
tail -f logs/worker.log

# 查看最近的错误
grep ERROR logs/worker.log | tail -20
```

### 查看系统资源

```bash
# 查看 CPU 和内存使用
htop

# 查看 Docker 容器资源使用
docker stats
```

## 安全建议

1. **使用专用用户**：创建专门的用户运行 worker，而不是 root
2. **限制 Docker 权限**：只给 worker 用户必要的 Docker 权限
3. **配置防火墙**：只开放必要的端口
4. **定期更新**：保持系统和 Docker 版本更新
5. **日志审计**：定期检查日志，发现异常行为

## 与 OpenHands 集成

详见 [OpenHands 集成指南](./openhands-cli-integration.zh-CN.md)。
