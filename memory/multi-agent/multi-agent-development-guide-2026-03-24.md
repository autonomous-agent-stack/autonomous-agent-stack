# 🤖 多 Agent 开发指南 - LiteLLM vs One-API

> **创建时间**: 2026-03-24 05:52
> **核心原则**: 轻 Prompt + 重 Skill

---

## 一、 LiteLLM vs One-API：选型对比

### 核心差异

| 维度 | One-API (网关服务派) | LiteLLM (代码原生派) |
|------|---------------------|---------------------|
| **核心定位** | 独立 API 网关与分发系统，Web 管理后台 | Python 开发库（简单代理服务），代码层面抹平差异 |
| **优势** | 统一管理 API Key、调用统计、负载均衡 | 极轻量，`import litellm` 即可调用 100+ 模型 |
| **部署方式** | Docker 部署（M1 芯片丝滑） | `pip install litellm`（Python 虚拟环境） |
| **适用场景** | 本地"模型总闸"，所有项目连接此总闸 | 纯代码开发 Agent，极简依赖，无兼容逻辑 |

### 选型建议

**选择 One-API 如果**:
- ✅ 需要可视化管理界面
- ✅ 需要统一管理多个 API Key
- ✅ 需要查看调用统计和负载均衡
- ✅ 有多个项目需要连接同一个网关

**选择 LiteLLM 如果**:
- ✅ 纯代码开发 Agent
- ✅ 希望代码里没有杂乱兼容逻辑
- ✅ 追求极简依赖
- ✅ 需要快速切换不同模型

---

## 二、 Vibe Coding 多个 Agent：先 Skill 后 Prompt

### 核心结论

**❌ 错误认知**: 只要 Prompt 足够长、足够好，Agent 就能无所不能
**✅ 正确架构**: 轻 Prompt + 重 Skill

### 架构原则

```
┌─────────────────────────────────────┐
│        LLM (文本生成器)              │
│   不会算术、不能联网、读不懂文件      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         Skill (技能/工具)            │
│   - Python 函数                     │
│   - 数据抓取脚本                     │
│   - 正则提取函数                     │
│   - API 调用封装                    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         Prompt (岗位职责)            │
│   - 简洁的任务描述                   │
│   - 调用哪些 Skill                  │
│   - 输出格式要求                    │
└─────────────────────────────────────┘
```

### 实战案例

#### Agent A (资料收集员)

**Skill**:
```python
# skills/web_scraper.py
import requests
from bs4 import BeautifulSoup

def fetch_webpage(url: str) -> str:
    """抓取网页内容"""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup.get_text()

def extract_text(content: str, pattern: str) -> str:
    """提取特定文本"""
    import re
    match = re.search(pattern, content)
    return match.group(1) if match else ""
```

**Prompt**:
```python
prompt = """
你是一个社交媒体分析师。
当用户询问最新趋势时，请：
1. 调用 fetch_webpage(url) 获取数据
2. 调用 extract_text(content, pattern) 提取关键信息
3. 用专业的语气总结
"""
```

#### Agent B (数据分析师)

**Skill**:
```python
# skills/data_analyzer.py
import pandas as pd
import matplotlib.pyplot as plt

def process_table(csv_path: str) -> pd.DataFrame:
    """处理表格数据"""
    return pd.read_csv(csv_path)

def generate_chart(df: pd.DataFrame, x: str, y: str) -> str:
    """生成图表"""
    plt.figure(figsize=(10, 6))
    plt.bar(df[x], df[y])
    plt.savefig('chart.png')
    return 'chart.png'
```

**Prompt**:
```python
prompt = """
你是一个数据分析师。
当用户提供 CSV 文件时，请：
1. 调用 process_table(path) 读取数据
2. 调用 generate_chart(df, x, y) 生成图表
3. 提供数据分析结论
"""
```

---

## 三、多 Agent 协作：技能模块化

### 协作架构

```
┌─────────────────┐
│   用户请求       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Orchestrator   │ ← 调度器 Agent
│  (调度器)       │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌───────┐
│Agent A│ │Agent B│
│(收集) │ │(分析) │
└───┬───┘ └───┬───┘
    │         │
    ▼         ▼
┌───────┐ ┌───────┐
│Skill 1│ │Skill 2│
│(抓取) │ │(处理) │
└───────┘ └───────┘
```

### 实战路径（使用 Cursor）

**步骤 1**: 新建文件，用自然语言描述功能
```
帮我写一个 Python 函数，接收一个关键词，返回对应的搜索结果
```

**步骤 2**: Cursor 瞬间生成 Skill
```python
def search_keyword(keyword: str) -> list:
    """搜索关键词"""
    # Cursor 自动生成代码
    ...
```

**步骤 3**: 挂载到 Agent
```python
from skills.search import search_keyword

agent.add_skill(search_keyword)
```

---

## 四、实战部署

### 方案 A: One-API (推荐用于管理)

#### Docker 部署

```bash
# 拉取镜像
docker pull justsong/one-api:latest

# 启动容器
docker run -d \
  --name one-api \
  -p 3000:3000 \
  -v /path/to/data:/data \
  -e TZ=Asia/Shanghai \
  justsong/one-api:latest

# 访问控制台
open http://localhost:3000
```

#### 配置步骤

1. **登录控制台** (默认账号: root, 密码: 123456)
2. **添加渠道** (OpenAI、Claude、GLM 等)
3. **创建令牌** (统一 API Key)
4. **配置负载均衡** (按需)

---

### 方案 B: LiteLLM (推荐用于开发)

#### 安装

```bash
pip install litellm
```

#### 使用示例

```python
from litellm import completion

# 统一格式调用不同模型
response = completion(
    model="gpt-4",  # 或 "claude-3-5-sonnet-20241022", "glm-5"
    messages=[{"role": "user", "content": "Hello"}]
)

print(response.choices[0].message.content)
```

#### 代理服务

```bash
# 启动代理服务器
litellm --model gpt-4

# 调用代理
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4", "messages": [{"role": "user", "content": "Hello"}]}'
```

---

## 五、完整示例：多 Agent 系统

### 项目结构

```
multi-agent-system/
├── agents/
│   ├── collector/
│   │   ├── SOUL.md
│   │   └── skills/
│   │       ├── web_scraper.py
│   │       └── text_extractor.py
│   ├── analyzer/
│   │   ├── SOUL.md
│   │   └── skills/
│   │       ├── data_processor.py
│   │       └── chart_generator.py
│   └── orchestrator/
│       ├── SOUL.md
│       └── router.py
├── config/
│   ├── litellm_config.yaml
│   └── one_api_config.json
└── main.py
```

### 主程序

```python
# main.py
from agents.collector import CollectorAgent
from agents.analyzer import AnalyzerAgent
from agents.orchestrator import OrchestratorAgent

# 初始化 Agent
collector = CollectorAgent()
analyzer = AnalyzerAgent()
orchestrator = OrchestratorAgent(collector, analyzer)

# 执行任务
result = orchestrator.execute("分析小红书上关于 AI Agent 的最新趋势")
print(result)
```

---

## 六、最佳实践

### 1. Skill 开发原则

- ✅ **单一职责**: 每个 Skill 只做一件事
- ✅ **可测试**: 单元测试覆盖
- ✅ **可复用**: 跨 Agent 共享
- ✅ **文档完整**: 清晰的输入输出说明

### 2. Prompt 编写原则

- ✅ **简洁明了**: 不超过 200 字
- ✅ **明确边界**: 调用哪些 Skill
- ✅ **输出格式**: 指定期望格式
- ✅ **错误处理**: 异常情况处理

### 3. 协作原则

- ✅ **职责分离**: 每个 Agent 专注一个领域
- ✅ **接口清晰**: Agent 间通信标准化
- ✅ **错误隔离**: 单个 Agent 失败不影响全局
- ✅ **可扩展**: 易于添加新 Agent

---

## 七、性能对比

| 方案 | 部署时间 | 学习曲线 | 管理难度 | 开发效率 |
|------|----------|----------|----------|----------|
| **One-API** | 10 分钟 | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **LiteLLM** | 2 分钟 | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **多 Agent 系统** | 1-2 天 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 八、下一步行动

### 立即执行

1. ✅ **启动 One-API** - Docker 部署（5 分钟）
2. ✅ **测试 LiteLLM** - 安装并运行示例（2 分钟）
3. ✅ **创建第一个 Skill** - 使用 Cursor 生成（1 分钟）

### 短期目标

4. ⏳ **开发 3 个核心 Agent** - 收集、分析、调度（1 天）
5. ⏳ **集成到 OpenClaw** - 使用 agent-forge（2 小时）
6. ⏳ **测试多 Agent 协作** - 实际案例验证（4 小时）

---

**大佬，两个方案都准备好了！立即启动 One-API + 创建 LiteLLM 示例？** 🚀
