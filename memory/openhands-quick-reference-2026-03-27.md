# OpenHands 快速参考卡

> 一页纸掌握 OpenHands 核心命令

---

## 🚀 快速开始

### 安装

```bash
# CLI 模式
pip install openhands

# GUI 模式
git clone https://github.com/OpenHands/OpenHands.git
make build && make run

# Cloud 模式
访问 https://app.all-hands.dev
```

### 配置

```bash
# 方式一：环境变量
export ANTHROPIC_API_KEY="sk-ant-xxx"

# 方式二：配置文件
openhands config set api-key sk-ant-xxx

# 方式三：交互式
openhands login
```

---

## 📝 核心命令

### 基础命令

```bash
# 执行任务
openhands run "任务描述"

# 指定模型
openhands run --model claude-3.5-sonnet "任务"

# 指定工作目录
openhands run --directory ./my-project "任务"

# 使用模板
openhands run --template template.yaml "任务"
```

### 高级命令

```bash
# 最大重试次数
openhands run --max-retries 3 "任务"

# 超时设置
openhands run --timeout 300 "任务"

# 输出格式
openhands run --format json "任务"

# 调试模式
openhands run --debug "任务"
```

---

## 🎯 任务描述模板

### Web 开发

```bash
openhands run "创建 FastAPI 项目，包含：
1. 用户认证（JWT）
2. 数据库连接（PostgreSQL）
3. API 文档（OpenAPI）
4. 单元测试（pytest）"
```

### 数据分析

```bash
openhands run "分析 CSV 文件，包含：
1. 数据清洗
2. 统计分析
3. 可视化（matplotlib）
4. 生成报告"
```

### 自动化测试

```bash
openhands run "为 calculator.py 生成单元测试，要求：
1. 测试覆盖率 > 90%
2. 包含边界测试
3. 包含异常测试"
```

---

## 🔧 配置文件

### .openhands.toml

```toml
[agent]
model = "claude-3.5-sonnet"
max_tokens = 4096
temperature = 0.7

[execution]
timeout = 300
max_retries = 3

[logging]
level = "INFO"
file = "~/.openhands/openhands.log"
```

### .openhands/templates/api.yaml

```yaml
name: API 项目模板
description: 创建标准 API 项目
prompt: |
  创建 {framework} API 项目：
  - 框架：{framework}
  - 数据库：{database}
  - 认证：{auth}
  - 文档：OpenAPI
```

---

## 📊 模型选择

| 模型 | 成本 | 质量 | 速度 | 推荐场景 |
|------|------|------|------|---------|
| **Claude 3.5 Sonnet** | $$$ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 复杂任务 |
| **GPT-4o** | $$$ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 通用任务 |
| **GLM-4** | $$ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 中文任务 |
| **Minimax** | Free | ⭐⭐⭐ | ⭐⭐⭐⭐ | 免费试用 |

---

## ⚡ 性能优化

### 1. 使用缓存

```bash
openhands run --cache "任务"
```

### 2. 并行处理

```python
from openhands import Agent
import asyncio

async def parallel_tasks():
    agent = Agent(model="claude-3.5-sonnet")
    
    results = await asyncio.gather(
        agent.run_async("任务1"),
        agent.run_async("任务2"),
        agent.run_async("任务3")
    )
    
    return results
```

### 3. Token 优化

```bash
# 减少 token
openhands run --max-tokens 2048 "任务"

# 启用压缩
openhands run --enable-compression "任务"
```

---

## 🐛 故障排查

### 常见问题

**问题 1**: API Key 无效
```bash
# 检查
echo $ANTHROPIC_API_KEY

# 重新设置
export ANTHROPIC_API_KEY="sk-ant-xxx"
```

**问题 2**: 网络错误
```bash
# 使用代理
export HTTP_PROXY="http://127.0.0.1:7890"
```

**问题 3**: 内存不足
```bash
# 减少并发
openhands run --max-workers 1 "任务"
```

---

## 📚 学习资源

### 官方

- 📖 文档：https://docs.openhands.dev
- 💻 GitHub：https://github.com/OpenHands/OpenHands
- 💬 Discord：https://discord.gg/openhands

### 社区

- 🇨🇳 中文教程：https://github.com/srxly888-creator/openhands-cookbook
- 📺 视频教程：YouTube / B站
- 📝 博客：Medium / 掘金

---

## 💡 最佳实践

### ✅ 好的实践

```bash
# 清晰的任务描述
openhands run "创建 FastAPI 项目，包含用户认证和数据库连接"

# 分步骤执行
openhands run "创建项目结构"
openhands run "实现用户认证"
openhands run "编写单元测试"
```

### ❌ 不好的实践

```bash
# 模糊的任务描述
openhands run "优化代码"

# 一次做太多
openhands run "创建一个完整的电商系统，包含用户管理、商品管理、订单管理、支付集成、物流追踪..."
```

---

## 🎯 快速命令参考

```bash
# 查看帮助
openhands --help

# 查看版本
openhands --version

# 查看配置
openhands config show

# 清理缓存
openhands cache clear

# 查看日志
openhands logs --tail 100

# 更新
pip install --upgrade openhands
```

---

<div align="center">
  <p>📋 打印此页，随时查阅！</p>
</div>
