# ai_lab 一键启动器

`scripts/launch_ai_lab.sh` 把常见动作串起来了：

1. 检查 Docker 是否可用
2. 检查 `/Users/ai_lab/workspace` 是否存在
3. 运行守卫检查
4. 启动 Docker Compose
5. 进入交互式容器 shell

## 常用命令

```bash
# 进入交互式 shell
./scripts/launch_ai_lab.sh

# 只启动，不进入 shell
./scripts/launch_ai_lab.sh up

# 查看状态
./scripts/launch_ai_lab.sh status

# 跑一次性命令
./scripts/launch_ai_lab.sh run -- python -V
```

## 设计取舍

- **默认 shell 模式**：适合 Agent 持续探索，降低进场摩擦
- **run 模式**：适合单次验证和 CI 风格动作
- **先守卫后启动**：避免在环境异常时把问题传播到容器里

