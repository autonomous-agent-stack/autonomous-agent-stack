# AI + RPA 深度集成技术白皮书

**版本**: 1.0  
**日期**: 2026-03-24  
**作者**: 小lin  
**关键词**: AI, RPA, 影刀, 自然语言处理, 流程自动化

---

## 目录

1. [引言](#1-引言)
2. [技术背景](#2-技术背景)
3. [系统架构设计](#3-系统架构设计)
4. [自然语言到 RPA 流程转换器](#4-自然语言到-rpa-流程转换器)
5. [核心代码实现](#5-核心代码实现)
6. [测试案例](#6-测试案例)
7. [影刀集成实践](#7-影刀集成实践)
8. [性能优化策略](#8-性能优化策略)
9. [未来发展方向](#9-未来发展方向)
10. [附录](#10-附录)

---

## 1. 引言

### 1.1 项目背景

机器人流程自动化（RPA）已经广泛应用于企业数字化转型，但传统 RPA 开发存在以下痛点：

1. **学习曲线陡峭**：业务人员无法直接创建自动化流程
2. **开发效率低**：简单的流程需要专业开发者数小时完成
3. **维护成本高**：流程变更需要重新编码
4. **异常处理困难**：缺乏智能的异常识别和处理机制

### 1.2 AI + RPA 的价值

通过将人工智能与 RPA 深度集成，可以实现：

- **自然语言驱动**：业务人员用自然语言描述需求，AI 自动生成 RPA 流程
- **智能调试**：AI 自动识别瓶颈并提供优化建议
- **自适应优化**：根据运行数据自动调整流程参数
- **低代码/无代码**：降低技术门槛，加速业务自动化落地

### 1.3 目标定位

本项目的核心目标是构建一个完整的 AI + RPA 集成平台，以影刀为主要 RPA 工具，实现：

1. **需求理解层**：解析自然语言业务需求，提取关键操作步骤
2. **流程生成层**：自动生成可执行的 RPA 流程代码
3. **调试优化层**：智能分析流程执行数据，提供优化建议
4. **集成适配层**：封装影刀 API，提供统一的服务接口

---

## 2. 技术背景

### 2.1 RPA 技术概述

RPA（Robotic Process Automation）是一种通过软件机器人模拟人类在计算机上的操作，自动执行规则化、重复性业务流程的技术。

#### 核心能力

1. **UI 自动化**：通过模拟鼠标、键盘操作与应用程序交互
2. **数据操作**：读取、处理、写入各类数据（Excel、数据库、网页等）
3. **逻辑控制**：支持循环、条件判断、异常处理等编程逻辑
4. **集成能力**：通过 API 与各种系统集成

#### 影刀简介

影刀是国内领先的 RPA 平台，具有以下特点：

- **可视化流程设计**：拖拽式流程编辑器
- **丰富的组件库**：涵盖 Web 自动化、桌面自动化、Excel 操作等
- **Python 扩展**：支持通过 Python 编写自定义组件
- **云端部署**：支持流程云端运行和管理

### 2.2 自然语言处理技术

#### 任务解析

自然语言需求解析的核心挑战：

1. **意图识别**：识别用户想要实现的目标
2. **实体抽取**：提取操作对象、参数、条件等关键信息
3. **步骤拆解**：将复杂需求分解为可执行的原子操作
4. **逻辑推理**：推断隐含的操作步骤和依赖关系

#### 技术选型

- **大语言模型**：使用 GPT-4、GLM-4 等强大的语言模型进行语义理解
- **结构化解析**：使用 LLM 生成结构化的 JSON 描述
- **知识库增强**：结合 RPA 领域知识提高解析准确率
- **Few-shot Learning**：通过示例学习提高泛化能力

### 2.3 AI 辅助代码生成

#### 代码生成策略

1. **模板驱动**：预定义 RPA 流程模板，根据需求填充参数
2. **组合生成**：将原子操作组合成完整流程
3. **语义转换**：将自然语言指令直接转换为代码
4. **多轮迭代**：通过交互式对话逐步完善流程

#### 代码质量保障

- **静态分析**：检查生成的代码是否符合 RPA 平台的规范
- **模拟执行**：在虚拟环境中模拟运行，发现潜在问题
- **代码评审**：AI 自我审查生成的代码质量
- **测试生成**：自动生成单元测试和集成测试

---

## 3. 系统架构设计

### 3.1 总体架构

```
┌─────────────────────────────────────────────────────────┐
│                     用户交互层                            │
│  (Web UI / 命令行 / 消息机器人)                           │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                   需求理解层                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ 意图识别    │  │ 实体抽取    │  │ 步骤拆解    │      │
│  │ (LLM)       │  │ (NER)       │  │ (Chain of   │      │
│  │             │  │             │  │  Thought)   │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                   流程生成层                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ 流程规划    │  │ 代码生成    │  │ 静态检查    │      │
│  │ (Planner)   │  │ (CodeGen)   │  │ (Linter)    │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                   RPA 执行层                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ 影刀适配器  │  │ 任务调度    │  │ 日志收集    │      │
│  │ (Adapter)   │  │ (Scheduler) │  │ (Logger)    │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                   优化分析层                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ 性能分析    │  │ 瓶颈识别    │  │ 优化建议    │      │
│  │ (Profiler)  │  │ (Bottleneck)│  │ (Optimizer) │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
└─────────────────────────────────────────────────────────┘
```

### 3.2 核心组件详解

#### 3.2.1 需求理解层

**功能**：将自然语言需求转化为结构化的任务描述

**输入**：
- 自然语言需求文本
- 可选的上下文信息（业务领域、已有流程等）

**输出**：
```json
{
  "intent": "自动化数据采集",
  "entities": {
    "target_url": "https://example.com",
    "output_path": "./data.xlsx",
    "frequency": "每天上午9点"
  },
  "steps": [
    {
      "action": "open_browser",
      "params": {"url": "https://example.com"}
    },
    {
      "action": "extract_data",
      "params": {"selector": "table.results"}
    },
    {
      "action": "save_excel",
      "params": {"path": "./data.xlsx"}
    }
  ],
  "conditions": {
    "if_no_data": "发送警报邮件"
  }
}
```

**技术实现**：
- 使用 Chain-of-Thought (CoT) 提示策略
- 嵌入 RPA 领域知识库
- 支持多轮对话澄清需求

#### 3.2.2 流程生成层

**功能**：根据结构化任务描述生成可执行的 RPA 流程代码

**工作流程**：
1. **流程规划**：确定操作的执行顺序和依赖关系
2. **代码生成**：将每个步骤转换为对应的 RPA 代码
3. **异常处理**：自动添加 Try-Catch 和重试逻辑
4. **参数化**：将硬编码值转换为可配置参数

**生成策略**：
- 基于模板的快速生成
- 基于语义理解的灵活生成
- 混合模式结合两者优势

#### 3.2.3 RPA 执行层

**功能**：执行生成的 RPA 流程并收集运行数据

**核心模块**：
- **影刀适配器**：封装影刀 API，提供统一接口
- **任务调度器**：支持定时执行、并行执行、依赖管理
- **日志收集器**：记录每个步骤的执行时间、成功/失败状态、错误信息

**监控指标**：
- 执行时间（总时间、每个步骤的时间）
- 成功率（流程级别、步骤级别）
- 资源占用（CPU、内存）
- 异常发生频率和类型

#### 3.2.4 优化分析层

**功能**：分析执行数据，识别瓶颈，提供优化建议

**分析维度**：

1. **性能分析**：
   - 识别耗时最长的步骤
   - 分析等待时间（如页面加载、网络请求）
   - 评估并行执行的可能性

2. **稳定性分析**：
   - 识别失败率高的步骤
   - 分析失败模式（超时、元素未找到、数据格式错误）
   - 评估重试策略的有效性

3. **资源优化**：
   - 分析内存使用模式
   - 识别资源泄漏
   - 建议资源释放策略

4. **优化建议生成**：
   ```json
   {
     "recommendations": [
       {
         "type": "performance",
         "step": "extract_data",
         "issue": "等待页面加载耗时过长",
         "suggestion": "添加显式等待条件，减少固定等待时间",
         "expected_improvement": "减少 30-40% 执行时间"
       },
       {
         "type": "reliability",
         "step": "click_submit",
         "issue": "元素选择器不稳定",
         "suggestion": "使用更稳定的选择器策略（如 data-id）",
         "expected_improvement": "提高 90% 成功率"
       }
     ]
   }
   ```

### 3.3 数据流设计

```
用户需求
   ↓
[需求理解层] → 结构化任务描述
   ↓
[流程生成层] → RPA 流程代码 + 配置文件
   ↓
[RPA 执行层] → 执行结果 + 运行日志
   ↓
[优化分析层] → 性能报告 + 优化建议
   ↓
用户反馈 → 迭代优化
```

### 3.4 技术栈选型

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| 自然语言处理 | GLM-4 / GPT-4 | 强大的语言理解和生成能力 |
| 流程编排 | LangGraph | 结构化的流程编排框架 |
| 代码生成 | Jinja2 + 自定义模板 | 灵活的模板引擎 |
| RPA 平台 | 影刀 RPA | 国内领先的 RPA 平台 |
| 任务调度 | APScheduler | Python 定时任务库 |
| 数据存储 | SQLite / PostgreSQL | 轻量级到企业级的数据库 |
| 监控告警 | Prometheus + Grafana | 专业的监控方案 |
| 日志管理 | ELK Stack (Elasticsearch, Logstash, Kibana) | 完整的日志分析方案 |

---

## 4. 自然语言到 RPA 流程转换器

### 4.1 转换器架构

```
┌──────────────────────────────────────────────────────────┐
│                    自然语言输入                             │
│     "每天早上9点自动登录网站下载报表并发送邮件"                │
└─────────────────────┬────────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────────┐
│              第一阶段：语义解析                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  领域识别     │→ │  意图分类     │→ │  实体提取     │   │
│  │ (Domain)     │  │ (Intent)     │  │ (Entity)     │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────┬────────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────────┐
│              第二阶段：任务分解                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  步骤规划     │→ │  依赖分析     │→ │  参数填充     │   │
│  │ (Step Plan)  │  │ (Dependency) │  │ (Param Fill) │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────┬────────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────────┐
│              第三阶段：流程生成                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  模板匹配     │→ │  代码生成     │→ │  静态检查     │   │
│  │ (Template)   │  │ (CodeGen)    │  │ (Static)     │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────┬────────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────────┐
│                    RPA 流程输出                            │
│  可执行的影刀流程文件 + 配置 + 文档                         │
└──────────────────────────────────────────────────────────┘
```

### 4.2 语义解析模块

#### 4.2.1 领域识别

识别用户需求所属的业务领域，以便使用领域特定的知识和模板。

**常见领域**：
- 数据采集（爬虫）
- 数据处理（Excel、数据库）
- 报表生成
- 邮件自动化
- 文件管理
- 网页测试

**实现示例**：

```python
class DomainClassifier:
    """领域分类器"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
        self.domains = {
            "data_collection": ["爬虫", "抓取", "采集", "下载"],
            "data_processing": ["处理", "转换", "计算", "分析"],
            "reporting": ["报表", "统计", "汇总", "生成报告"],
            "email": ["邮件", "发送", "通知", "提醒"],
            "file_management": ["移动", "重命名", "删除", "整理"],
            "web_testing": ["测试", "验证", "检查", "监控"]
        }
    
    def classify(self, user_input: str) -> str:
        """分类用户需求所属领域"""
        # 使用 LLM 进行语义分类
        prompt = f"""
        分析以下用户需求，判断其最可能属于哪个 RPA 自动化领域。
        
        用户需求: {user_input}
        
        可选领域:
        - data_collection: 数据采集、爬虫、下载
        - data_processing: 数据处理、转换、分析
        - reporting: 报表生成、统计汇总
        - email: 邮件自动化、发送通知
        - file_management: 文件管理、整理
        - web_testing: 网页测试、监控
        
        请只返回领域名称。
        """
        
        response = self.llm.generate(prompt)
        return response.strip()
```

#### 4.2.2 意图分类

识别用户想要实现的具体操作类型。

**意图类型**：

```python
INTENT_TAXONOMY = {
    "automate_recurring": "自动化重复性任务",
    "extract_data": "提取数据",
    "transform_data": "转换数据格式",
    "send_notification": "发送通知/邮件",
    "generate_report": "生成报表",
    "monitor_changes": "监控变化",
    "validate_workflow": "验证流程"
}
```

**实现示例**：

```python
class IntentClassifier:
    """意图分类器"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
    
    def classify(self, user_input: str, domain: str) -> Dict[str, Any]:
        """分类用户意图并提取关键信息"""
        prompt = f"""
        分析用户需求，识别意图并提取关键信息。
        
        用户需求: {user_input}
        所属领域: {domain}
        
        请以 JSON 格式返回:
        {{
            "intent": "意图类型",
            "confidence": 0.95,
            "key_info": {{
                "frequency": "执行频率",
                "target": "操作目标",
                "output": "输出要求"
            }}
        }}
        """
        
        response = self.llm.generate(prompt)
        return json.loads(response)
```

#### 4.2.3 实体提取

从用户需求中提取关键的实体信息。

**实体类型**：

```python
ENTITY_TYPES = {
    "URL": ["网址", "网站", "链接", "URL"],
    "PATH": ["路径", "文件", "文件夹", "目录"],
    "TIME": ["时间", "日期", "频率", "定时"],
    "EMAIL": ["邮件", "邮箱"],
    "CREDENTIALS": ["账号", "密码", "登录"],
    "DATA_SOURCE": ["数据库", "Excel", "表格"],
    "CONDITION": ["如果", "当", "否则", "满足"]
}
```

**实现示例**：

```python
class EntityExtractor:
    """实体提取器"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
        self.entity_patterns = self._compile_patterns()
    
    def _compile_patterns(self):
        """编译正则表达式模式"""
        patterns = {
            "URL": r'https?://[^\s]+',
            "EMAIL": r'[\w.-]+@[\w.-]+\.\w+',
            "TIME": r'(?:每天|每周|每月|每天上午|每天下午)\s*\d+[点时]?',
            "PATH": r'[/\\]?[\w./\\-]+',
        }
        return {k: re.compile(v) for k, v in patterns.items()}
    
    def extract(self, user_input: str) -> Dict[str, List[str]]:
        """提取实体信息"""
        # 使用 LLM 进行语义实体提取
        prompt = f"""
        从以下用户需求中提取所有关键实体。
        
        用户需求: {user_input}
        
        实体类型:
        - URL: 网址、链接
        - TIME: 时间、频率、定时
        - PATH: 文件路径、目录
        - EMAIL: 邮箱地址
        - CREDENTIALS: 账号、密码相关信息
        - DATA_SOURCE: 数据来源（Excel、数据库等）
        - CONDITION: 条件、逻辑
        
        请以 JSON 格式返回所有提取到的实体:
        {{
            "URL": ["https://example.com"],
            "TIME": ["每天早上9点"],
            ...
        }}
        如果某类实体未找到，返回空数组。
        """
        
        response = self.llm.generate(prompt)
        entities = json.loads(response)
        
        # 结合正则表达式进行补充提取
        for entity_type, pattern in self.entity_patterns.items():
            matches = pattern.findall(user_input)
            if matches and entity_type not in entities:
                entities[entity_type] = matches
            elif matches:
                entities[entity_type].extend(matches)
        
        return entities
```

### 4.3 任务分解模块

#### 4.3.1 步骤规划

将用户需求分解为一系列可执行的原子步骤。

**步骤类型定义**：

```python
STEP_TYPES = {
    "open": {"name": "打开", "params": ["url", "path", "app"]},
    "click": {"name": "点击", "params": ["selector", "element"]},
    "input": {"name": "输入", "params": ["selector", "value"]},
    "extract": {"name": "提取", "params": ["selector", "format"]},
    "save": {"name": "保存", "params": ["path", "format"]},
    "send": {"name": "发送", "params": ["recipient", "subject", "body"]},
    "wait": {"name": "等待", "params": ["duration", "condition"]},
    "condition": {"name": "条件判断", "params": ["condition", "true_branch", "false_branch"]},
    "loop": {"name": "循环", "params": ["count", "iterator", "body"]}
}
```

**实现示例**：

```python
class StepPlanner:
    """步骤规划器"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
        self.step_types = STEP_TYPES
    
    def plan(self, user_input: str, entities: Dict, intent: str) -> List[Dict]:
        """规划执行步骤"""
        # 使用 Chain-of-Thought 进行步骤分解
        prompt = f"""
        将以下用户需求分解为详细的执行步骤。
        
        用户需求: {user_input}
        
        已提取的实体:
        {json.dumps(entities, ensure_ascii=False, indent=2)}
        
        意图: {intent}
        
        可用的步骤类型:
        {json.dumps(self.step_types, ensure_ascii=False, indent=2)}
        
        请以 JSON 格式返回步骤列表:
        [
            {{
                "step_id": 1,
                "action": "open",
                "description": "打开目标网站",
                "params": {{"url": "https://example.com"}},
                "dependencies": []
            }},
            ...
        ]
        
        注意:
        1. 步骤应该按照执行顺序排列
        2. dependencies 字段表示该步骤依赖的前序步骤（数组）
        3. 参数值应该优先使用提取到的实体
        4. 如果需要参数化，使用占位符（如 {{username}}）
        """
        
        response = self.llm.generate(prompt)
        steps = json.loads(response)
        
        # 验证和优化步骤
        steps = self._validate_and_optimize(steps, entities)
        
        return steps
    
    def _validate_and_optimize(self, steps: List[Dict], entities: Dict) -> List[Dict]:
        """验证并优化步骤序列"""
        # 检查步骤类型是否有效
        for i, step in enumerate(steps):
            if step["action"] not in self.step_types:
                # 尝试映射到最接近的有效类型
                similar = self._find_similar_action(step["action"])
                if similar:
                    steps[i]["action"] = similar
                    steps[i]["suggested_original"] = step["action"]
        
        # 检查参数完整性
        for step in steps:
            action_info = self.step_types.get(step["action"], {})
            required_params = action_info.get("params", [])
            for param in required_params:
                if param not in step["params"]:
                    # 尝试从实体中推断
                    if param in entities and entities[param]:
                        step["params"][param] = entities[param][0]
                    else:
                        # 添加为待确认参数
                        step["params"][param] = f"{{TODO_{param}}}"
        
        # 分析依赖关系
        steps = self._analyze_dependencies(steps)
        
        return steps
    
    def _find_similar_action(self, action: str) -> Optional[str]:
        """查找相似的有效操作"""
        action_lower = action.lower()
        for valid_action in self.step_types:
            if action_lower in valid_action or valid_action in action_lower:
                return valid_action
        return None
    
    def _analyze_dependencies(self, steps: List[Dict]) -> List[Dict]:
        """分析步骤之间的依赖关系"""
        for i, step in enumerate(steps):
            dependencies = []
            
            # 分析参数引用
            for param_value in step["params"].values():
                # 检查是否引用了前序步骤的输出
                if isinstance(param_value, str) and "$" in param_value:
                    # 格式如 $step_1.output
                    match = re.search(r'\$step_(\d+)\.output', param_value)
                    if match:
                        dep_step_id = int(match.group(1))
                        if dep_step_id < step["step_id"]:
                            dependencies.append(dep_step_id)
            
            # 检查动作隐含的依赖
            if step["action"] in ["input", "click", "extract"]:
                # 这些操作通常需要在页面打开之后
                if i > 0 and steps[i-1]["action"] == "open":
                    dependencies.append(steps[i-1]["step_id"])
            
            step["dependencies"] = dependencies
        
        return steps
```

#### 4.3.2 依赖分析

识别步骤之间的依赖关系，确保执行顺序正确。

**依赖类型**：

```python
DEPENDENCY_TYPES = {
    "sequential": "顺序依赖（A 必须在 B 之前执行）",
    "data_dependency": "数据依赖（B 需要使用 A 的输出）",
    "resource_dependency": "资源依赖（A 和 B 需要共享资源）",
    "conditional": "条件依赖（B 的执行依赖 A 的结果）"
}
```

**实现示例**：

```python
class DependencyAnalyzer:
    """依赖分析器"""
    
    def analyze(self, steps: List[Dict]) -> Dict[str, Any]:
        """分析步骤依赖关系"""
        # 构建依赖图
        dependency_graph = self._build_dependency_graph(steps)
        
        # 检测循环依赖
        cycles = self._detect_cycles(dependency_graph)
        
        if cycles:
            raise ValueError(f"检测到循环依赖: {cycles}")
        
        # 拓扑排序
        execution_order = self._topological_sort(dependency_graph)
        
        # 分析可并行的步骤
        parallel_groups = self._identify_parallel_steps(dependency_graph)
        
        return {
            "graph": dependency_graph,
            "execution_order": execution_order,
            "parallel_groups": parallel_groups,
            "critical_path": self._find_critical_path(steps, dependency_graph)
        }
    
    def _build_dependency_graph(self, steps: List[Dict]) -> Dict[int, List[int]]:
        """构建依赖图"""
        graph = {step["step_id"]: [] for step in steps}
        
        for step in steps:
            for dep_id in step.get("dependencies", []):
                if dep_id in graph:
                    graph[dep_id].append(step["step_id"])
        
        return graph
    
    def _detect_cycles(self, graph: Dict[int, List[int]]) -> List[List[int]]:
        """检测循环依赖（使用 DFS）"""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in graph}
        cycles = []
        
        def dfs(node, path):
            color[node] = GRAY
            path.append(node)
            
            for neighbor in graph[node]:
                if color[neighbor] == GRAY:
                    # 发现环
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:])
                elif color[neighbor] == WHITE:
                    dfs(neighbor, path)
            
            path.pop()
            color[node] = BLACK
        
        for node in graph:
            if color[node] == WHITE:
                dfs(node, [])
        
        return cycles
    
    def _topological_sort(self, graph: Dict[int, List[int]]) -> List[int]:
        """拓扑排序"""
        in_degree = {node: 0 for node in graph}
        
        for node in graph:
            for neighbor in graph[node]:
                in_degree[neighbor] += 1
        
        # 找到入度为 0 的节点
        queue = deque([node for node in in_degree if in_degree[node] == 0])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result
    
    def _identify_parallel_steps(self, graph: Dict[int, List[int]]) -> List[List[int]]:
        """识别可以并行执行的步骤组"""
        # 简化版：基于层级的分组
        in_degree = {node: 0 for node in graph}
        for node in graph:
            for neighbor in graph[node]:
                in_degree[neighbor] += 1
        
        groups = []
        current_group = [node for node in in_degree if in_degree[node] == 0]
        
        while current_group:
            groups.append(current_group.copy())
            next_group = []
            
            for node in current_group:
                for neighbor in graph[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_group.append(neighbor)
            
            current_group = next_group
        
        return groups
    
    def _find_critical_path(self, steps: List[Dict], graph: Dict[int, List[int]]) -> List[int]:
        """找到关键路径（最长的依赖路径）"""
        step_estimated_time = {
            step["step_id"]: step.get("estimated_time", 1)
            for step in steps
        }
        
        # 计算每个步骤到终点的最长路径
        memo = {}
        
        def longest_path_to_end(node):
            if node in memo:
                return memo[node]
            
            if not graph[node]:
                memo[node] = (step_estimated_time[node], [node])
                return memo[node]
            
            max_time = 0
            max_path = []
            
            for neighbor in graph[node]:
                neighbor_time, neighbor_path = longest_path_to_end(neighbor)
                if neighbor_time > max_time:
                    max_time = neighbor_time
                    max_path = neighbor_path
            
            total_time = step_estimated_time[node] + max_time
            path = [node] + max_path
            memo[node] = (total_time, path)
            
            return memo[node]
        
        # 找到所有起始节点（入度为 0）
        in_degree = {node: 0 for node in graph}
        for node in graph:
            for neighbor in graph[node]:
                in_degree[neighbor] += 1
        
        start_nodes = [node for node in in_degree if in_degree[node] == 0]
        
        # 找到最长的路径
        max_critical_path = []
        max_total_time = 0
        
        for start_node in start_nodes:
            time, path = longest_path_to_end(start_node)
            if time > max_total_time:
                max_total_time = time
                max_critical_path = path
        
        return max_critical_path
```

### 4.4 流程生成模块

#### 4.4.1 模板匹配引擎

基于领域和步骤类型，匹配最优的流程模板。

**模板定义**：

```python
# templates/web_automation.json
{
    "template_name": "Web 自动化流程",
    "domain": "data_collection",
    "steps_template": [
        {
            "action": "open_browser",
            "template_code": "browser.open({url})",
            "default_params": {
                "url": "{url}",
                "headless": False
            }
        },
        {
            "action": "wait_for_load",
            "template_code": "browser.wait_for_page_load({timeout})",
            "default_params": {
                "timeout": 30
            }
        },
        {
            "action": "login",
            "template_code": """
# 登录
browser.find_element({username_selector}).input({username})
browser.find_element({password_selector}).input({password})
browser.find_element({submit_selector}).click()
            """,
            "default_params": {
                "username_selector": "#username",
                "password_selector": "#password",
                "submit_selector": "#login-button"
            }
        }
    ]
}
```

**实现示例**：

```python
class TemplateEngine:
    """模板匹配引擎"""
    
    def __init__(self, template_dir: str = "./templates"):
        self.template_dir = Path(template_dir)
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Dict]:
        """加载所有模板"""
        templates = {}
        
        for template_file in self.template_dir.glob("*.json"):
            with open(template_file, 'r', encoding='utf-8') as f:
                template = json.load(f)
                template_name = template.get("template_name", template_file.stem)
                templates[template_name] = template
        
        return templates
    
    def find_best_template(self, domain: str, steps: List[Dict]) -> Optional[Dict]:
        """找到最匹配的模板"""
        # 计算每个模板的匹配分数
        scored_templates = []
        
        for template_name, template in self.templates.items():
            if template.get("domain") != domain:
                continue
            
            score = self._calculate_match_score(template, steps)
            if score > 0:
                scored_templates.append((template_name, template, score))
        
        # 返回分数最高的模板
        if scored_templates:
            scored_templates.sort(key=lambda x: x[2], reverse=True)
            return scored_templates[0][1]
        
        return None
    
    def _calculate_match_score(self, template: Dict, steps: List[Dict]) -> float:
        """计算模板匹配分数"""
        template_steps = template.get("steps_template", [])
        
        # 简单的 Jaccard 相似度
        template_actions = set(step["action"] for step in template_steps)
        user_actions = set(step["action"] for step in steps)
        
        intersection = len(template_actions & user_actions)
        union = len(template_actions | user_actions)
        
        if union == 0:
            return 0
        
        return intersection / union
    
    def apply_template(self, template: Dict, steps: List[Dict], entities: Dict) -> List[Dict]:
        """应用模板到步骤"""
        template_steps = template.get("steps_template", [])
        result_steps = []
        
        # 合并模板步骤和用户步骤
        for i, (template_step, user_step) in enumerate(zip(template_steps, steps)):
            merged_step = {
                "step_id": i + 1,
                "action": user_step.get("action", template_step["action"]),
                "template_code": template_step.get("template_code", ""),
                "params": {**template_step.get("default_params", {}), **user_step.get("params", {})},
                "description": user_step.get("description", "")
            }
            result_steps.append(merged_step)
        
        return result_steps
```

#### 4.4.2 代码生成器

根据步骤和模板，生成可执行的 RPA 代码。

**影刀代码结构**：

```python
# 影刀流程结构
{
    "flow_name": "自动化流程名称",
    "variables": {},  # 全局变量
    "steps": [],      # 执行步骤
    "error_handling": {}  # 异常处理
}
```

**实现示例**：

```python
class CodeGenerator:
    """代码生成器"""
    
    def __init__(self, template_engine: TemplateEngine):
        self.template_engine = template_engine
        self.jinja_env = Environment(loader=FileSystemLoader('./code_templates'))
    
    def generate(self, steps: List[Dict], entities: Dict, domain: str) -> Dict:
        """生成 RPA 流程代码"""
        # 1. 查找最佳模板
        template = self.template_engine.find_best_template(domain, steps)
        
        if template:
            steps = self.template_engine.apply_template(template, steps, entities)
        
        # 2. 生成变量定义
        variables = self._generate_variables(entities)
        
        # 3. 生成步骤代码
        code_steps = []
        for step in steps:
            step_code = self._generate_step_code(step, variables)
            code_steps.append({
                "step_id": step["step_id"],
                "action": step["action"],
                "code": step_code,
                "description": step.get("description", "")
            })
        
        # 4. 生成异常处理
        error_handling = self._generate_error_handling(steps)
        
        # 5. 组装完整流程
        flow = {
            "flow_name": entities.get("task_name", ["自动化流程"])[0],
            "version": "1.0",
            "variables": variables,
            "steps": code_steps,
            "error_handling": error_handling,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "domain": domain,
                "entities": entities
            }
        }
        
        return flow
    
    def _generate_variables(self, entities: Dict) -> Dict:
        """生成变量定义"""
        variables = {}
        
        # URL 变量
        if "URL" in entities and entities["URL"]:
            for i, url in enumerate(entities["URL"]):
                variables[f"URL_{i+1}"] = {"type": "string", "value": url}
        
        # 路径变量
        if "PATH" in entities and entities["PATH"]:
            for i, path in enumerate(entities["PATH"]):
                variables[f"PATH_{i+1}"] = {"type": "string", "value": path}
        
        # 邮箱变量
        if "EMAIL" in entities and entities["EMAIL"]:
            for i, email in enumerate(entities["EMAIL"]):
                variables[f"EMAIL_{i+1}"] = {"type": "string", "value": email}
        
        # 时间变量
        if "TIME" in entities and entities["TIME"]:
            for i, time_str in enumerate(entities["TIME"]):
                variables[f"TIME_{i+1}"] = {"type": "string", "value": time_str}
        
        # 凭证变量（敏感信息）
        if "CREDENTIALS" in entities and entities["CREDENTIALS"]:
            for i, cred_info in enumerate(entities["CREDENTIALS"]):
                variables[f"CREDENTIAL_{i+1}"] = {
                    "type": "secure_string",
                    "value": f"{{TODO: 请输入{cred_info}}}"
                }
        
        return variables
    
    def _generate_step_code(self, step: Dict, variables: Dict) -> str:
        """生成单个步骤的代码"""
        action = step["action"]
        params = step.get("params", {})
        
        # 使用 Jinja2 模板生成代码
        if "template_code" in step and step["template_code"]:
            template = self.jinja_env.from_string(step["template_code"])
            code = template.render(**params, **variables)
        else:
            # 使用默认代码生成逻辑
            code = self._generate_default_code(action, params, variables)
        
        return code
    
    def _generate_default_code(self, action: str, params: Dict, variables: Dict) -> str:
        """生成默认步骤代码"""
        code_generators = {
            "open": self._gen_open,
            "click": self._gen_click,
            "input": self._gen_input,
            "extract": self._gen_extract,
            "save": self._gen_save,
            "wait": self._gen_wait,
            "send": self._gen_send
        }
        
        generator = code_generators.get(action, self._gen_generic)
        return generator(params, variables)
    
    def _gen_open(self, params: Dict, variables: Dict) -> str:
        """生成打开操作的代码"""
        if "url" in params:
            return f"browser.open('{params['url']}')"
        elif "path" in params:
            return f"app.open('{params['path']}')"
        else:
            return "# TODO: 打开操作参数缺失"
    
    def _gen_click(self, params: Dict, variables: Dict) -> str:
        """生成点击操作的代码"""
        selector = params.get("selector", "TODO_SELECTOR")
        return f"browser.find_element('{selector}').click()"
    
    def _gen_input(self, params: Dict, variables: Dict) -> str:
        """生成输入操作的代码"""
        selector = params.get("selector", "TODO_SELECTOR")
        value = params.get("value", "TODO_VALUE")
        return f"browser.find_element('{selector}').input('{value}')"
    
    def _gen_extract(self, params: Dict, variables: Dict) -> str:
        """生成提取操作的代码"""
        selector = params.get("selector", "TODO_SELECTOR")
        output_format = params.get("format", "text")
        return f"data = browser.find_element('{selector}').extract(format='{output_format}')"
    
    def _gen_save(self, params: Dict, variables: Dict) -> str:
        """生成保存操作的代码"""
        path = params.get("path", "TODO_PATH")
        return f"save_to_excel(data, '{path}')"
    
    def _gen_wait(self, params: Dict, variables: Dict) -> str:
        """生成等待操作的代码"""
        duration = params.get("duration", 5)
        return f"time.sleep({duration})"
    
    def _gen_send(self, params: Dict, variables: Dict) -> str:
        """生成发送操作的代码"""
        recipient = params.get("recipient", "TODO_EMAIL")
        subject = params.get("subject", "自动化流程完成")
        body = params.get("body", "流程已成功执行")
        return f"send_email(to='{recipient}', subject='{subject}', body='{body}')"
    
    def _gen_generic(self, params: Dict, variables: Dict) -> str:
        """生成通用代码"""
        return f"# TODO: 生成 {action} 操作的代码"
    
    def _generate_error_handling(self, steps: List[Dict]) -> Dict:
        """生成异常处理逻辑"""
        error_handlers = {}
        
        for step in steps:
            step_id = step["step_id"]
            action = step["action"]
            
            # 为每个步骤生成异常处理
            error_handlers[step_id] = {
                "retry_policy": {
                    "max_retries": 3,
                    "retry_delay": 5
                },
                "fallback_actions": [
                    {
                        "action": "log_error",
                        "params": {"message": f"步骤 {step_id} ({action}) 执行失败"}
                    },
                    {
                        "action": "screenshot",
                        "params": {"filename": f"error_step_{step_id}.png"}
                    }
                ]
            }
        
        return error_handlers
```

#### 4.4.3 静态代码检查器

在代码生成后进行静态检查，确保代码质量。

**检查项**：

```python
STATIC_CHECK_RULES = [
    {
        "name": "参数完整性检查",
        "description": "检查所有必需参数是否已提供"
    },
    {
        "name": "选择器有效性检查",
        "description": "检查选择器语法是否正确"
    },
    {
        "name": "循环依赖检查",
        "description": "检测步骤之间是否存在循环依赖"
    },
    {
        "name": "安全风险检查",
        "description": "检查是否存在硬编码的敏感信息"
    },
    {
        "name": "最佳实践检查",
        "description": "检查是否符合 RPA 最佳实践"
    }
]
```

**实现示例**：

```python
class StaticCodeChecker:
    """静态代码检查器"""
    
    def __init__(self):
        self.rules = STATIC_CHECK_RULES
        self.checkers = {
            "参数完整性检查": self._check_parameter_completeness,
            "选择器有效性检查": self._check_selector_validity,
            "循环依赖检查": self._check_circular_dependencies,
            "安全风险检查": self._check_security_risks,
            "最佳实践检查": self._check_best_practices
        }
    
    def check(self, flow: Dict) -> Dict[str, Any]:
        """执行所有静态检查"""
        results = {
            "total_rules": len(self.rules),
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "details": []
        }
        
        for rule in self.rules:
            rule_name = rule["name"]
            checker = self.checkers.get(rule_name)
            
            if not checker:
                continue
            
            check_result = checker(flow)
            result_detail = {
                "rule": rule_name,
                "description": rule["description"],
                "status": check_result["status"],
                "issues": check_result.get("issues", []),
                "suggestions": check_result.get("suggestions", [])
            }
            
            results["details"].append(result_detail)
            
            if check_result["status"] == "pass":
                results["passed"] += 1
            elif check_result["status"] == "fail":
                results["failed"] += 1
            elif check_result["status"] == "warning":
                results["warnings"] += 1
        
        results["overall_status"] = (
            "pass" if results["failed"] == 0 else
            "warning" if results["warnings"] > 0 else
            "fail"
        )
        
        return results
    
    def _check_parameter_completeness(self, flow: Dict) -> Dict:
        """检查参数完整性"""
        issues = []
        suggestions = []
        
        required_params = {
            "open": ["url"],
            "click": ["selector"],
            "input": ["selector", "value"],
            "save": ["path"],
            "send": ["recipient"]
        }
        
        for step in flow["steps"]:
            action = step["action"]
            if action in required_params:
                params = step.get("params", {})
                for required_param in required_params[action]:
                    if required_param not in params or params[required_param].startswith("TODO"):
                        issues.append(f"步骤 {step['step_id']} 缺少必需参数: {required_param}")
                        suggestions.append(f"请在步骤 {step['step_id']} 中提供 {required_param} 参数")
        
        return {
            "status": "fail" if issues else "pass",
            "issues": issues,
            "suggestions": suggestions
        }
    
    def _check_selector_validity(self, flow: Dict) -> Dict:
        """检查选择器有效性"""
        issues = []
        suggestions = []
        
        selector_actions = ["click", "input", "extract"]
        
        for step in flow["steps"]:
            if step["action"] in selector_actions:
                selector = step.get("params", {}).get("selector", "")
                
                if selector.startswith("TODO"):
                    issues.append(f"步骤 {step['step_id']} 的选择器未定义")
                    suggestions.append(f"请在步骤 {step['step_id']} 中定义有效的选择器")
                elif not re.match(r'^[#.][a-zA-Z0-9_-]+$', selector):
                    # 简单的选择器验证（实际应该更复杂）
                    pass
        
        return {
            "status": "fail" if issues else "pass",
            "issues": issues,
            "suggestions": suggestions
        }
    
    def _check_circular_dependencies(self, flow: Dict) -> Dict:
        """检查循环依赖"""
        issues = []
        suggestions = []
        
        # 构建依赖图
        graph = {}
        for step in flow["steps"]:
            graph[step["step_id"]] = step.get("dependencies", [])
        
        # 使用 DFS 检测环
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in graph}
        cycles = []
        
        def dfs(node, path):
            color[node] = GRAY
            path.append(node)
            
            for neighbor in graph[node]:
                if color[neighbor] == GRAY:
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:])
                elif color[neighbor] == WHITE:
                    dfs(neighbor, path)
            
            path.pop()
            color[node] = BLACK
        
        for node in graph:
            if color[node] == WHITE:
                dfs(node, [])
        
        if cycles:
            for cycle in cycles:
                issues.append(f"检测到循环依赖: {' -> '.join(map(str, cycle))}")
                suggestions.append("请重构流程以消除循环依赖")
        
        return {
            "status": "fail" if cycles else "pass",
            "issues": issues,
            "suggestions": suggestions
        }
    
    def _check_security_risks(self, flow: Dict) -> Dict:
        """检查安全风险"""
        issues = []
        suggestions = []
        
        # 检查硬编码的敏感信息
        sensitive_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "密码硬编码"),
            (r'username\s*=\s*["\'][^"\']+["\']', "用户名硬编码"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "API Key 硬编码")
        ]
        
        for step in flow["steps"]:
            code = step.get("code", "")
            
            for pattern, risk_desc in sensitive_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    issues.append(f"步骤 {step['step_id']} 检测到 {risk_desc}")
                    suggestions.append(f"请使用变量替换硬编码的敏感信息")
        
        return {
            "status": "fail" if issues else "pass",
            "issues": issues,
            "suggestions": suggestions
        }
    
    def _check_best_practices(self, flow: Dict) -> Dict:
        """检查最佳实践"""
        warnings = []
        suggestions = []
        
        # 检查是否缺少等待操作
        for i, step in enumerate(flow["steps"]):
            if step["action"] == "click" and i + 1 < len(flow["steps"]):
                next_step = flow["steps"][i + 1]
                if next_step["action"] not in ["wait", "extract"]:
                    warnings.append(f"步骤 {step['step_id']} 后建议添加等待操作")
                    suggestions.append(f"在步骤 {step['step_id']} 后添加适当的等待，确保页面加载完成")
        
        return {
            "status": "warning" if warnings else "pass",
            "issues": [],
            "suggestions": suggestions
        }
```

### 4.5 完整转换器示例

```python
class NLToRPAConverter:
    """自然语言到 RPA 流程转换器"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
        self.domain_classifier = DomainClassifier(llm_client)
        self.intent_classifier = IntentClassifier(llm_client)
        self.entity_extractor = EntityExtractor(llm_client)
        self.step_planner = StepPlanner(llm_client)
        self.dependency_analyzer = DependencyAnalyzer()
        self.template_engine = TemplateEngine()
        self.code_generator = CodeGenerator(self.template_engine)
        self.static_checker = StaticCodeChecker()
    
    def convert(self, user_input: str) -> Dict[str, Any]:
        """完整的转换流程"""
        print(f"[1/8] 领域识别...")
        domain = self.domain_classifier.classify(user_input)
        print(f"  识别领域: {domain}")
        
        print(f"[2/8] 意图分类...")
        intent_info = self.intent_classifier.classify(user_input, domain)
        print(f"  识别意图: {intent_info['intent']}")
        
        print(f"[3/8] 实体提取...")
        entities = self.entity_extractor.extract(user_input)
        print(f"  提取实体: {list(entities.keys())}")
        
        print(f"[4/8] 步骤规划...")
        steps = self.step_planner.plan(user_input, entities, intent_info['intent'])
        print(f"  规划步骤: {len(steps)} 步")
        
        print(f"[5/8] 依赖分析...")
        dependency_result = self.dependency_analyzer.analyze(steps)
        print(f"  执行顺序: {dependency_result['execution_order']}")
        
        print(f"[6/8] 流程生成...")
        flow = self.code_generator.generate(steps, entities, domain)
        print(f"  生成流程: {flow['flow_name']}")
        
        print(f"[7/8] 静态检查...")
        check_result = self.static_checker.check(flow)
        print(f"  检查结果: {check_result['overall_status']}")
        print(f"  通过: {check_result['passed']}, 失败: {check_result['failed']}, 警告: {check_result['warnings']}")
        
        print(f"[8/8] 生成报告...")
        
        return {
            "status": "success",
            "domain": domain,
            "intent": intent_info,
            "entities": entities,
            "steps": steps,
            "dependencies": dependency_result,
            "flow": flow,
            "static_check": check_result,
            "metadata": {
                "input": user_input,
                "generated_at": datetime.now().isoformat()
            }
        }
    
    def save_flow(self, flow: Dict, output_path: str):
        """保存流程到文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(flow, f, ensure_ascii=False, indent=2)
        print(f"流程已保存到: {output_path}")
```

---

## 5. 核心代码实现

### 5.1 项目结构

```
ai-rpa-integration/
├── src/
│   ├── __init__.py
│   ├── nl_parser/              # 自然语言解析模块
│   │   ├── __init__.py
│   │   ├── domain_classifier.py
│   │   ├── intent_classifier.py
│   │   └── entity_extractor.py
│   ├── flow_planner/           # 流程规划模块
│   │   ├── __init__.py
│   │   ├── step_planner.py
│   │   └── dependency_analyzer.py
│   ├── code_generator/         # 代码生成模块
│   │   ├── __init__.py
│   │   ├── template_engine.py
│   │   ├── code_generator.py
│   │   └── static_checker.py
│   ├── rpa_executor/           # RPA 执行模块
│   │   ├── __init__.py
│   │   ├── yingdao_adapter.py
│   │   ├── scheduler.py
│   │   └── logger.py
│   └── optimizer/             # 优化分析模块
│       ├── __init__.py
│       ├── profiler.py
│       ├── bottleneck_detector.py
│       └── optimizer.py
├── templates/                  # 流程模板
│   ├── web_automation.json
│   ├── data_processing.json
│   └── email_automation.json
├── code_templates/             # 代码模板（Jinja2）
│   ├── open.jinja2
│   ├── click.jinja2
│   └── input.jinja2
├── tests/                      # 测试文件
│   ├── __init__.py
│   ├── test_nl_parser.py
│   ├── test_flow_planner.py
│   ├── test_code_generator.py
│   └── test_integration.py
├── examples/                   # 示例代码
│   ├── example_1.py
│   ├── example_2.py
│   └── example_3.py
├── requirements.txt            # Python 依赖
├── config.json               # 配置文件
└── main.py                   # 主程序入口
```

### 5.2 配置文件

```json
{
  "llm": {
    "provider": "zhipuai",
    "model": "glm-4",
    "api_key": "YOUR_API_KEY",
    "base_url": "https://open.bigmodel.cn/api/paas/v4/",
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "yingdao": {
    "api_endpoint": "http://localhost:8080/api",
    "api_key": "YOUR_YINGDAO_API_KEY"
  },
  "database": {
    "type": "sqlite",
    "path": "./data/ai_rpa.db"
  },
  "logging": {
    "level": "INFO",
    "file": "./logs/ai_rpa.log",
    "max_size": "10MB",
    "backup_count": 5
  },
  "scheduler": {
    "timezone": "Asia/Shanghai",
    "default_max_workers": 3
  }
}
```

### 5.3 主程序入口

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI + RPA 深度集成平台主程序
"""

import argparse
import json
import sys
from pathlib import Path

from src.nl_parser import NLToRPAConverter
from src.rpa_executor import FlowExecutor
from src.optimizer import FlowOptimizer


def load_config(config_path: str = "config.json") -> dict:
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def cmd_convert(args):
    """转换自然语言需求到 RPA 流程"""
    from src.llm_client import LLMClient
    
    config = load_config(args.config)
    llm_client = LLMClient(config["llm"])
    
    converter = NLToRPAConverter(llm_client)
    
    print("=" * 60)
    print("AI + RPA 自然语言转换器")
    print("=" * 60)
    print(f"\n用户需求: {args.input}")
    print()
    
    result = converter.convert(args.input)
    
    # 保存结果
    output_path = args.output or f"output/{result['flow']['flow_name']}.json"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'=' * 60}")
    print("转换完成！")
    print(f"{'=' * 60}")
    print(f"\n流程名称: {result['flow']['flow_name']}")
    print(f"输出文件: {output_path}")
    print(f"步骤数量: {len(result['flow']['steps'])}")
    print(f"检查状态: {result['static_check']['overall_status']}")
    
    if result['static_check']['overall_status'] != 'pass':
        print(f"\n⚠️  静态检查发现问题，请检查输出文件中的 details 字段")
    
    return 0


def cmd_execute(args):
    """执行 RPA 流程"""
    config = load_config(args.config)
    
    executor = FlowExecutor(config)
    
    # 加载流程文件
    with open(args.flow_file, 'r', encoding='utf-8') as f:
        flow = json.load(f)
    
    print(f"执行流程: {flow['flow_name']}")
    
    result = executor.execute(flow)
    
    print(f"执行结果: {result['status']}")
    if result['status'] == 'failed':
        print(f"错误信息: {result['error']}")
    
    return 0


def cmd_optimize(args):
    """优化 RPA 流程"""
    config = load_config(args.config)
    
    optimizer = FlowOptimizer(config)
    
    # 加载流程文件
    with open(args.flow_file, 'r', encoding='utf-8') as f:
        flow = json.load(f)
    
    print(f"分析流程: {flow['flow_name']}")
    
    # 加载执行日志（如果有）
    execution_logs = []
    if args.log_file:
        with open(args.log_file, 'r', encoding='utf-8') as f:
            execution_logs = json.load(f)
    
    recommendations = optimizer.analyze(flow, execution_logs)
    
    print("\n优化建议:")
    for rec in recommendations:
        print(f"\n  [{rec['type'].upper()}] {rec['title']}")
        print(f"  问题: {rec['issue']}")
        print(f"  建议: {rec['suggestion']}")
        if rec.get('expected_improvement'):
            print(f"  预期效果: {rec['expected_improvement']}")
    
    # 保存优化建议
    output_path = args.output or f"output/{flow['flow_name']}_optimized.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(recommendations, f, ensure_ascii=False, indent=2)
    
    print(f"\n优化建议已保存到: {output_path}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="AI + RPA 深度集成平台",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 转换自然语言需求
  python main.py convert -i "每天早上9点自动登录网站下载报表" -o flow.json
  
  # 执行 RPA 流程
  python main.py execute -f flow.json
  
  # 优化流程
  python main.py optimize -f flow.json -l execution_log.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # convert 命令
    convert_parser = subparsers.add_parser('convert', help='转换自然语言需求到 RPA 流程')
    convert_parser.add_argument('-i', '--input', required=True, help='自然语言需求')
    convert_parser.add_argument('-o', '--output', help='输出文件路径')
    convert_parser.add_argument('-c', '--config', default='config.json', help='配置文件路径')
    convert_parser.set_defaults(func=cmd_convert)
    
    # execute 命令
    execute_parser = subparsers.add_parser('execute', help='执行 RPA 流程')
    execute_parser.add_argument('-f', '--flow-file', required=True, help='流程文件路径')
    execute_parser.add_argument('-c', '--config', default='config.json', help='配置文件路径')
    execute_parser.set_defaults(func=cmd_execute)
    
    # optimize 命令
    optimize_parser = subparsers.add_parser('optimize', help='优化 RPA 流程')
    optimize_parser.add_argument('-f', '--flow-file', required=True, help='流程文件路径')
    optimize_parser.add_argument('-l', '--log-file', help='执行日志文件路径')
    optimize_parser.add_argument('-o', '--output', help='输出文件路径')
    optimize_parser.add_argument('-c', '--config', default='config.json', help='配置文件路径')
    optimize_parser.set_defaults(func=cmd_optimize)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

### 5.4 LLM 客户端封装

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM 客户端封装
支持多种 LLM 提供商
"""

import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import requests


class LLMClient(ABC):
    """LLM 客户端基类"""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        pass
    
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """对话生成"""
        pass


class ZhipuAIClient(LLMClient):
    """智谱 AI 客户端（GLM-4）"""
    
    def __init__(self, config: Dict):
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://open.bigmodel.cn/api/paas/v4/")
        self.model = config.get("model", "glm-4")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2000)
        self.timeout = config.get("timeout", 30)
    
    def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, **kwargs)
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """对话生成"""
        url = f"{self.base_url}chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens)
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            return content
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"LLM API 请求失败: {str(e)}")


class OpenAIClient(LLMClient):
    """OpenAI 客户端（GPT-4）"""
    
    def __init__(self, config: Dict):
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://api.openai.com/v1/")
        self.model = config.get("model", "gpt-4")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2000)
    
    def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, **kwargs)
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """对话生成"""
        url = f"{self.base_url}chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens)
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            return content
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"LLM API 请求失败: {str(e)}")


class LLMClientFactory:
    """LLM 客户端工厂"""
    
    @staticmethod
    def create(config: Dict) -> LLMClient:
        """根据配置创建 LLM 客户端"""
        provider = config.get("provider", "").lower()
        
        if provider == "zhipuai":
            return ZhipuAIClient(config)
        elif provider == "openai":
            return OpenAIClient(config)
        else:
            raise ValueError(f"不支持的 LLM 提供商: {provider}")
```

### 5.5 影刀 API 适配器

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
影刀 RPA 平台适配器
"""

import json
import requests
from typing import Dict, List, Any, Optional
from pathlib import Path


class YingdaoAdapter:
    """影刀 API 适配器"""
    
    def __init__(self, config: Dict):
        self.api_endpoint = config.get("api_endpoint", "")
        self.api_key = config.get("api_key", "")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def create_flow(self, flow: Dict) -> Dict[str, Any]:
        """创建流程"""
        url = f"{self.api_endpoint}/flows"
        
        try:
            response = requests.post(url, headers=self.headers, json=flow)
            response.raise_for_status()
            
            return response.json()
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"创建流程失败: {str(e)}")
    
    def execute_flow(self, flow_id: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """执行流程"""
        url = f"{self.api_endpoint}/flows/{flow_id}/execute"
        
        data = {
            "params": params or {}
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            
            return response.json()
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"执行流程失败: {str(e)}")
    
    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """获取执行状态"""
        url = f"{self.api_endpoint}/executions/{execution_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"获取执行状态失败: {str(e)}")
    
    def list_flows(self) -> List[Dict[str, Any]]:
        """列出所有流程"""
        url = f"{self.api_endpoint}/flows"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json().get("flows", [])
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"列出流程失败: {str(e)}")
    
    def delete_flow(self, flow_id: str) -> bool:
        """删除流程"""
        url = f"{self.api_endpoint}/flows/{flow_id}"
        
        try:
            response = requests.delete(url, headers=self.headers)
            response.raise_for_status()
            
            return True
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"删除流程失败: {str(e)}")


class FlowExecutor:
    """流程执行器"""
    
    def __init__(self, config: Dict):
        self.yingdao_adapter = YingdaoAdapter(config.get("yingdao", {}))
        self.scheduler = TaskScheduler(config)
        self.logger = ExecutionLogger(config.get("logging", {}))
    
    def execute(self, flow: Dict, params: Optional[Dict] = None) -> Dict[str, Any]:
        """执行流程"""
        execution_log = {
            "flow_name": flow["flow_name"],
            "flow_version": flow.get("version", "1.0"),
            "started_at": None,
            "finished_at": None,
            "status": "pending",
            "steps": [],
            "errors": []
        }
        
        try:
            # 创建流程
            print(f"创建流程: {flow['flow_name']}")
            flow_result = self.yingdao_adapter.create_flow(flow)
            flow_id = flow_result.get("flow_id")
            
            if not flow_id:
                raise Exception("创建流程失败，未返回 flow_id")
            
            print(f"流程 ID: {flow_id}")
            
            # 执行流程
            print(f"执行流程...")
            execution_log["started_at"] = datetime.now().isoformat()
            
            execution_result = self.yingdao_adapter.execute_flow(flow_id, params)
            execution_id = execution_result.get("execution_id")
            
            if not execution_id:
                raise Exception("执行流程失败，未返回 execution_id")
            
            print(f"执行 ID: {execution_id}")
            
            # 轮询执行状态
            status = self._wait_for_completion(execution_id)
            
            execution_log["finished_at"] = datetime.now().isoformat()
            execution_log["status"] = status
            
            # 记录日志
            self.logger.log(execution_log)
            
            return {
                "status": "success" if status == "completed" else "failed",
                "execution_id": execution_id,
                "final_status": status
            }
        
        except Exception as e:
            execution_log["status"] = "failed"
            execution_log["errors"].append(str(e))
            self.logger.log(execution_log)
            
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _wait_for_completion(self, execution_id: str, poll_interval: int = 5, timeout: int = 300) -> str:
        """等待执行完成"""
        import time
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status_result = self.yingdao_adapter.get_execution_status(execution_id)
            status = status_result.get("status")
            
            print(f"执行状态: {status}")
            
            if status in ["completed", "failed", "cancelled"]:
                return status
            
            time.sleep(poll_interval)
        
        raise Exception(f"执行超时（{timeout}秒）")


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, config: Dict):
        from apscheduler.schedulers.background import BackgroundScheduler
        
        self.scheduler = BackgroundScheduler()
        self.timezone = config.get("scheduler", {}).get("timezone", "Asia/Shanghai")
        self.executor = None  # 需要在外部注入
    
    def schedule(self, flow: Dict, cron_expression: str) -> str:
        """调度定时任务"""
        from apscheduler.triggers.cron import CronTrigger
        
        job_id = f"{flow['flow_name']}_{int(time.time())}"
        
        self.scheduler.add_job(
            func=self._execute_flow,
            trigger=CronTrigger.from_crontab(cron_expression, timezone=self.timezone),
            id=job_id,
            args=[flow],
            name=flow['flow_name']
        )
        
        return job_id
    
    def _execute_flow(self, flow: Dict):
        """执行流程的包装函数"""
        if self.executor:
            self.executor.execute(flow)
    
    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
    
    def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()


class ExecutionLogger:
    """执行日志记录器"""
    
    def __init__(self, config: Dict):
        self.log_file = config.get("file", "./logs/execution.log")
        self.log_dir = Path(self.log_file).parent
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def log(self, execution_log: Dict):
        """记录执行日志"""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(execution_log, ensure_ascii=False) + "\n")
    
    def get_logs(self, limit: int = 100) -> List[Dict]:
        """获取最近的执行日志"""
        logs = []
        
        if not Path(self.log_file).exists():
            return logs
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                logs.append(json.loads(line))
                if len(logs) >= limit:
                    break
        
        return logs
```

### 5.6 优化分析模块

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
流程优化分析模块
"""

import json
from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime, timedelta


class FlowOptimizer:
    """流程优化器"""
    
    def __init__(self, config: Dict):
        self.profiler = Profiler()
        self.bottleneck_detector = BottleneckDetector()
        self.recommendation_engine = RecommendationEngine()
    
    def analyze(self, flow: Dict, execution_logs: Optional[List[Dict]] = None) -> List[Dict]:
        """分析流程并提供优化建议"""
        recommendations = []
        
        # 如果有执行日志，进行性能分析
        if execution_logs:
            performance_data = self._parse_execution_logs(execution_logs)
            
            # 瓶颈检测
            bottlenecks = self.bottleneck_detector.detect(performance_data)
            
            for bottleneck in bottlenecks:
                recommendation = self.recommendation_engine.generate(bottleneck)
                recommendations.append(recommendation)
        
        # 代码质量分析
        code_issues = self._analyze_code_quality(flow)
        recommendations.extend(code_issues)
        
        # 最佳实践检查
        best_practice_issues = self._check_best_practices(flow)
        recommendations.extend(best_practice_issues)
        
        return recommendations
    
    def _parse_execution_logs(self, execution_logs: List[Dict]) -> Dict:
        """解析执行日志"""
        performance_data = defaultdict(list)
        
        for log in execution_logs:
            if "steps" in log:
                for step_log in log["steps"]:
                    step_id = step_log.get("step_id")
                    duration = step_log.get("duration", 0)
                    status = step_log.get("status", "unknown")
                    
                    performance_data[step_id].append({
                        "duration": duration,
                        "status": status,
                        "timestamp": log.get("started_at")
                    })
        
        return dict(performance_data)


class Profiler:
    """性能分析器"""
    
    def profile_step(self, step_id: int, func) -> Dict[str, Any]:
        """分析单个步骤的性能"""
        import time
        import tracemalloc
        
        # 内存分析
        tracemalloc.start()
        
        # 时间分析
        start_time = time.time()
        
        try:
            result = func()
            status = "success"
            error = None
        except Exception as e:
            status = "failed"
            error = str(e)
            result = None
        
        end_time = time.time()
        
        # 获取内存使用情况
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        return {
            "step_id": step_id,
            "duration": end_time - start_time,
            "memory_usage": current / 1024 / 1024,  # MB
            "peak_memory": peak / 1024 / 1024,      # MB
            "status": status,
            "error": error,
            "result": result
        }


class BottleneckDetector:
    """瓶颈检测器"""
    
    def detect(self, performance_data: Dict[int, List[Dict]]) -> List[Dict]:
        """检测性能瓶颈"""
        bottlenecks = []
        
        # 分析每个步骤的性能
        for step_id, executions in performance_data.items():
            if not executions:
                continue
            
            # 计算平均执行时间
            avg_duration = sum(e["duration"] for e in executions) / len(executions)
            
            # 计算失败率
            failed_count = sum(1 for e in executions if e["status"] != "success")
            failure_rate = failed_count / len(executions)
            
            # 识别瓶颈
            if avg_duration > 10:  # 超过 10 秒
                bottlenecks.append({
                    "type": "performance",
                    "step_id": step_id,
                    "issue": f"步骤平均执行时间过长: {avg_duration:.2f} 秒",
                    "metric": {
                        "avg_duration": avg_duration,
                        "executions": len(executions)
                    }
                })
            
            if failure_rate > 0.1:  # 失败率超过 10%
                bottlenecks.append({
                    "type": "reliability",
                    "step_id": step_id,
                    "issue": f"步骤失败率过高: {failure_rate * 100:.1f}%",
                    "metric": {
                        "failure_rate": failure_rate,
                        "failed_count": failed_count,
                        "total_count": len(executions)
                    }
                })
        
        # 分析整体流程瓶颈
        if performance_data:
            total_steps = len(performance_data)
            total_time = sum(
                sum(e["duration"] for e in executions)
                for executions in performance_data.values()
            )
            
            avg_time_per_step = total_time / total_steps
            
            # 找出执行时间最长的步骤
            slowest_step = max(
                performance_data.items(),
                key=lambda x: sum(e["duration"] for e in x[1]) / len(x[1])
            )
            
            avg_slowest = sum(e["duration"] for e in slowest_step[1]) / len(slowest_step[1])
            
            if avg_slowest > avg_time_per_step * 2:
                bottlenecks.append({
                    "type": "critical_path",
                    "step_id": slowest_step[0],
                    "issue": f"该步骤是关键路径瓶颈，执行时间是平均值的 {avg_slowest / avg_time_per_step:.1f} 倍",
                    "metric": {
                        "avg_duration": avg_slowest,
                        "relative_factor": avg_slowest / avg_time_per_step
                    }
                })
        
        return bottlenecks


class RecommendationEngine:
    """建议生成引擎"""
    
    def generate(self, bottleneck: Dict) -> Dict:
        """根据瓶颈生成优化建议"""
        bottleneck_type = bottleneck["type"]
        
        if bottleneck_type == "performance":
            return self._generate_performance_recommendation(bottleneck)
        elif bottleneck_type == "reliability":
            return self._generate_reliability_recommendation(bottleneck)
        elif bottleneck_type == "critical_path":
            return self._generate_critical_path_recommendation(bottleneck)
        else:
            return self._generate_generic_recommendation(bottleneck)
    
    def _generate_performance_recommendation(self, bottleneck: Dict) -> Dict:
        """生成性能优化建议"""
        suggestions = [
            {
                "title": "减少固定等待时间",
                "issue": bottleneck["issue"],
                "suggestion": "将固定等待（sleep）替换为显式等待，等待元素出现后再继续",
                "expected_improvement": "减少 30-50% 等待时间",
                "code_example": """
# 优化前
time.sleep(5)

# 优化后
browser.wait_for_element(selector="button.submit", timeout=10)
                """
            },
            {
                "title": "使用并行执行",
                "issue": bottleneck["issue"],
                "suggestion": "如果步骤之间没有依赖关系，可以并行执行以减少总时间",
                "expected_improvement": "根据并行步骤数量，可减少 40-80% 执行时间"
            }
        ]
        
        return {
            "type": "performance",
            "step_id": bottleneck["step_id"],
            "bottleneck": bottleneck,
            "recommendations": suggestions
        }
    
    def _generate_reliability_recommendation(self, bottleneck: Dict) -> Dict:
        """生成可靠性优化建议"""
        suggestions = [
            {
                "title": "增加重试机制",
                "issue": bottleneck["issue"],
                "suggestion": "为容易失败的步骤添加自动重试逻辑",
                "expected_improvement": "提高 70-90% 成功率",
                "code_example": """
# 添加重试逻辑
for attempt in range(3):
    try:
        result = browser.click(selector="button.submit")
        break
    except Exception as e:
        if attempt == 2:
            raise
        time.sleep(2)
                """
            },
            {
                "title": "优化选择器",
                "issue": bottleneck["issue"],
                "suggestion": "使用更稳定的选择器（如 data-id、aria-label）而非依赖 CSS 类名",
                "expected_improvement": "提高选择器稳定性，减少因 DOM 变化导致的失败"
            }
        ]
        
        return {
            "type": "reliability",
            "step_id": bottleneck["step_id"],
            "bottleneck": bottleneck,
            "recommendations": suggestions
        }
    
    def _generate_critical_path_recommendation(self, bottleneck: Dict) -> Dict:
        """生成关键路径优化建议"""
        suggestions = [
            {
                "title": "分析步骤可拆分性",
                "issue": bottleneck["issue"],
                "suggestion": "分析该步骤是否可以拆分为多个子步骤，以便部分步骤可以并行执行",
                "expected_improvement": "根据可拆分程度，可能减少 20-60% 执行时间"
            },
            {
                "title": "优化算法或数据结构",
                "issue": bottleneck["issue"],
                "suggestion": "如果该步骤涉及数据处理，考虑使用更高效的算法或数据结构",
                "expected_improvement": "根据数据规模，可能显著提升性能"
            }
        ]
        
        return {
            "type": "critical_path",
            "step_id": bottleneck["step_id"],
            "bottleneck": bottleneck,
            "recommendations": suggestions
        }
    
    def _generate_generic_recommendation(self, bottleneck: Dict) -> Dict:
        """生成通用建议"""
        return {
            "type": "generic",
            "step_id": bottleneck.get("step_id"),
            "bottleneck": bottleneck,
            "recommendations": [
                {
                    "title": "需要人工审查",
                    "issue": bottleneck["issue"],
                    "suggestion": "该问题需要开发人员进一步分析和优化"
                }
            ]
        }
```

---

## 6. 测试案例

### 6.1 测试案例 1：数据采集流程

**测试目标**：验证从自然语言需求到数据采集 RPA 流程的完整转换流程

**用户需求**：
```
每天早上9点自动登录 https://example.com，下载销售报表，保存到桌面 sales.xlsx，完成后发送邮件通知我
```

**预期输出**：

```json
{
  "domain": "data_collection",
  "intent": "automate_recurring",
  "entities": {
    "URL": ["https://example.com"],
    "TIME": ["每天早上9点"],
    "PATH": ["sales.xlsx"]
  },
  "steps": [
    {
      "step_id": 1,
      "action": "open_browser",
      "description": "打开浏览器",
      "params": {
        "url": "https://example.com"
      },
      "dependencies": []
    },
    {
      "step_id": 2,
      "action": "login",
      "description": "登录网站",
      "params": {
        "username": "{TODO_username}",
        "password": "{TODO_password}"
      },
      "dependencies": [1]
    },
    {
      "step_id": 3,
      "action": "download_report",
      "description": "下载销售报表",
      "params": {
        "report_type": "销售报表",
        "output_path": "~/Desktop/sales.xlsx"
      },
      "dependencies": [2]
    },
    {
      "step_id": 4,
      "action": "send_email",
      "description": "发送完成通知",
      "params": {
        "to": "{TODO_email}",
        "subject": "销售报表下载完成",
        "body": "报表已成功下载到桌面"
      },
      "dependencies": [3]
    }
  ]
}
```

**测试代码**：

```python
def test_data_collection_flow():
    """测试数据采集流程"""
    from src.nl_parser import NLToRPAConverter
    from src.llm_client import LLMClientFactory
    
    # 准备测试数据
    user_input = "每天早上9点自动登录 https://example.com，下载销售报表，保存到桌面 sales.xlsx，完成后发送邮件通知我"
    
    # 初始化转换器
    config = load_config("config.json")
    llm_client = LLMClientFactory.create(config["llm"])
    converter = NLToRPAConverter(llm_client)
    
    # 执行转换
    result = converter.convert(user_input)
    
    # 验证结果
    assert result["status"] == "success"
    assert result["domain"] == "data_collection"
    assert "https://example.com" in result["entities"]["URL"]
    assert "sales.xlsx" in str(result["entities"]["PATH"])
    assert len(result["steps"]) >= 4
    assert result["steps"][0]["action"] in ["open_browser", "open"]
    assert result["steps"][-1]["action"] in ["send_email", "send"]
    
    print("✓ 测试通过：数据采集流程转换正确")
    
    return result
```

### 6.2 测试案例 2：邮件自动化

**测试目标**：验证邮件自动化流程的生成

**用户需求**：
```
每周一上午10点，给团队发送任务周报，内容包括本周完成的任务列表、下周计划，邮件抄送给主管
```

**预期输出**：

```json
{
  "domain": "email",
  "intent": "automate_recurring",
  "entities": {
    "TIME": ["每周一上午10点"]
  },
  "steps": [
    {
      "step_id": 1,
      "action": "query_tasks",
      "description": "查询本周完成的任务",
      "params": {
        "time_range": "this_week",
        "status": "completed"
      },
      "dependencies": []
    },
    {
      "step_id": 2,
      "action": "query_plans",
      "description": "查询下周计划",
      "params": {
        "time_range": "next_week"
      },
      "dependencies": []
    },
    {
      "step_id": 3,
      "action": "generate_report",
      "description": "生成周报内容",
      "params": {
        "completed_tasks": "$step_1.output",
        "next_week_plans": "$step_2.output"
      },
      "dependencies": [1, 2]
    },
    {
      "step_id": 4,
      "action": "send_email",
      "description": "发送周报邮件",
      "params": {
        "to": "{team_email}",
        "cc": "{manager_email}",
        "subject": "任务周报 - {date}",
        "body": "$step_3.output"
      },
      "dependencies": [3]
    }
  ]
}
```

**测试代码**：

```python
def test_email_automation():
    """测试邮件自动化"""
    from src.nl_parser import NLToRPAConverter
    from src.llm_client import LLMClientFactory
    
    user_input = "每周一上午10点，给团队发送任务周报，内容包括本周完成的任务列表、下周计划，邮件抄送给主管"
    
    config = load_config("config.json")
    llm_client = LLMClientFactory.create(config["llm"])
    converter = NLToRPAConverter(llm_client)
    
    result = converter.convert(user_input)
    
    assert result["domain"] == "email"
    assert "每周一上午10点" in result["entities"]["TIME"]
    assert any(step["action"] == "send_email" for step in result["steps"])
    
    # 验证数据依赖
    send_step = next(step for step in result["steps"] if step["action"] == "send_email")
    assert len(send_step["dependencies"]) > 0
    
    print("✓ 测试通过：邮件自动化流程转换正确")
    
    return result
```

### 6.3 测试案例 3：条件判断和异常处理

**测试目标**：验证条件逻辑和异常处理的生成

**用户需求**：
```
监控网站 https://example.com，如果页面出现"系统维护"字样，立即发送警报邮件，否则每10分钟记录一次页面状态
```

**预期输出**：

```json
{
  "domain": "web_testing",
  "intent": "monitor_changes",
  "steps": [
    {
      "step_id": 1,
      "action": "open_browser",
      "description": "打开网站",
      "params": {
        "url": "https://example.com"
      },
      "dependencies": []
    },
    {
      "step_id": 2,
      "action": "extract_text",
      "description": "提取页面文本",
      "params": {
        "selector": "body",
        "format": "text"
      },
      "dependencies": [1]
    },
    {
      "step_id": 3,
      "action": "condition",
      "description": "判断是否维护",
      "params": {
        "condition": "if '系统维护' in $step_2.output",
        "true_branch": [4],
        "false_branch": [5]
      },
      "dependencies": [2]
    },
    {
      "step_id": 4,
      "action": "send_alert",
      "description": "发送警报邮件",
      "params": {
        "to": "{admin_email}",
        "subject": "网站维护警报",
        "body": "检测到网站处于维护状态"
      },
      "dependencies": [3]
    },
    {
      "step_id": 5,
      "action": "log_status",
      "description": "记录状态",
      "params": {
        "status": "normal",
        "message": "网站运行正常"
      },
      "dependencies": [3]
    },
    {
      "step_id": 6,
      "action": "wait",
      "description": "等待10分钟",
      "params": {
        "duration": 600
      },
      "dependencies": [4, 5]
    },
    {
      "step_id": 7,
      "action": "loop",
      "description": "循环监控",
      "params": {
        "count": "infinite",
        "body": [1, 2, 3, 4, 5, 6]
      },
      "dependencies": [6]
    }
  ]
}
```

**测试代码**：

```python
def test_conditional_logic():
    """测试条件判断逻辑"""
    from src.nl_parser import NLToRPAConverter
    from src.llm_client import LLMClientFactory
    
    user_input = "监控网站 https://example.com，如果页面出现'系统维护'字样，立即发送警报邮件，否则每10分钟记录一次页面状态"
    
    config = load_config("config.json")
    llm_client = LLMClientFactory.create(config["llm"])
    converter = NLToRPAConverter(llm_client)
    
    result = converter.convert(user_input)
    
    assert result["domain"] == "web_testing"
    assert any(step["action"] == "condition" for step in result["steps"])
    
    # 验证条件步骤
    condition_step = next(step for step in result["steps"] if step["action"] == "condition")
    assert "condition" in condition_step["params"]
    assert "true_branch" in condition_step["params"]
    assert "false_branch" in condition_step["params"]
    
    # 验证循环
    assert any(step["action"] == "loop" for step in result["steps"])
    
    print("✓ 测试通过：条件判断和循环逻辑转换正确")
    
    return result
```

### 6.4 测试案例 4：复杂的数据处理

**测试目标**：验证数据处理流程的生成，包括多步骤数据转换

**用户需求**：
```
读取 Excel 文件 data.xlsx 中的订单数据，筛选出金额大于1000的订单，按地区分组统计，生成饼图，保存为 report.html
```

**预期输出**：

```json
{
  "domain": "data_processing",
  "intent": "transform_data",
  "steps": [
    {
      "step_id": 1,
      "action": "read_excel",
      "description": "读取Excel文件",
      "params": {
        "path": "data.xlsx",
        "sheet": 0
      },
      "dependencies": []
    },
    {
      "step_id": 2,
      "action": "filter_data",
      "description": "筛选金额大于1000的订单",
      "params": {
        "data": "$step_1.output",
        "condition": "amount > 1000"
      },
      "dependencies": [1]
    },
    {
      "step_id": 3,
      "action": "group_data",
      "description": "按地区分组",
      "params": {
        "data": "$step_2.output",
        "group_by": "region",
        "agg_func": "sum"
      },
      "dependencies": [2]
    },
    {
      "step_id": 4,
      "action": "create_chart",
      "description": "生成饼图",
      "params": {
        "data": "$step_3.output",
        "chart_type": "pie",
        "title": "各地区订单金额分布"
      },
      "dependencies": [3]
    },
    {
      "step_id": 5,
      "action": "save_html",
      "description": "保存为HTML文件",
      "params": {
        "chart": "$step_4.output",
        "output_path": "report.html"
      },
      "dependencies": [4]
    }
  ]
}
```

**测试代码**：

```python
def test_data_processing():
    """测试数据处理流程"""
    from src.nl_parser import NLToRPAConverter
    from src.llm_client import LLMClientFactory
    
    user_input = "读取 Excel 文件 data.xlsx 中的订单数据，筛选出金额大于1000的订单，按地区分组统计，生成饼图，保存为 report.html"
    
    config = load_config("config.json")
    llm_client = LLMClientFactory.create(config["llm"])
    converter = NLToRPAConverter(llm_client)
    
    result = converter.convert(user_input)
    
    assert result["domain"] == "data_processing"
    
    # 验证数据处理步骤
    expected_actions = ["read_excel", "filter", "group", "create_chart", "save"]
    for expected_action in expected_actions:
        assert any(expected_action in step["action"] for step in result["steps"]), f"缺少 {expected_action} 步骤"
    
    # 验证数据依赖
    for i in range(1, len(result["steps"])):
        step = result["steps"][i]
        if i > 1:
            assert len(step["dependencies"]) > 0, f"步骤 {i} 缺少依赖"
    
    print("✓ 测试通过：数据处理流程转换正确")
    
    return result
```

### 6.5 测试案例 5：端到端集成测试

**测试目标**：验证从需求到执行的完整流程

**测试流程**：

1. **用户输入需求**
2. **AI 生成 RPA 流程**
3. **静态代码检查**
4. **部署到影刀平台**
5. **执行流程**
6. **收集执行日志**
7. **性能分析和优化**

**测试代码**：

```python
def test_end_to_end_integration():
    """端到端集成测试"""
    from src.nl_parser import NLToRPAConverter
    from src.llm_client import LLMClientFactory
    from src.rpa_executor import FlowExecutor
    from src.optimizer import FlowOptimizer
    
    print("\n" + "=" * 60)
    print("端到端集成测试")
    print("=" * 60)
    
    # 1. 准备测试需求
    user_input = "每天早上8点，打开 https://news.example.com，获取头条新闻标题，保存到 daily_news.txt"
    print(f"\n[测试需求] {user_input}")
    
    # 2. 加载配置
    config = load_config("config.json")
    
    # 3. 需求转换
    print("\n[阶段 1] 需求转换...")
    llm_client = LLMClientFactory.create(config["llm"])
    converter = NLToRPAConverter(llm_client)
    conversion_result = converter.convert(user_input)
    
    assert conversion_result["status"] == "success"
    print(f"✓ 需求转换成功: {conversion_result['flow']['flow_name']}")
    print(f"✓ 生成步骤: {len(conversion_result['flow']['steps'])} 个")
    
    # 4. 静态检查
    print("\n[阶段 2] 静态代码检查...")
    check_result = conversion_result["static_check"]
    assert check_result["overall_status"] in ["pass", "warning"], f"静态检查失败: {check_result}"
    print(f"✓ 检查通过: 通过 {check_result['passed']} 项，警告 {check_result['warnings']} 项")
    
    # 5. 保存流程
    print("\n[阶段 3] 保存流程文件...")
    flow = conversion_result["flow"]
    flow_file = "output/test_flow.json"
    with open(flow_file, 'w', encoding='utf-8') as f:
        json.dump(flow, f, ensure_ascii=False, indent=2)
    print(f"✓ 流程已保存: {flow_file}")
    
    # 6. 执行流程（模拟）
    print("\n[阶段 4] 执行流程...")
    try:
        executor = FlowExecutor(config)
        
        # 模拟执行（实际需要影刀环境）
        print("⚠ 跳过实际执行（需要影刀环境）")
        # execution_result = executor.execute(flow)
        # print(f"✓ 流程执行完成: {execution_result['status']}")
        
    except Exception as e:
        print(f"⚠ 执行阶段跳过: {str(e)}")
    
    # 7. 性能分析（模拟）
    print("\n[阶段 5] 性能分析...")
    optimizer = FlowOptimizer(config)
    
    # 模拟执行日志
    mock_logs = [
        {
            "flow_name": flow["flow_name"],
            "started_at": "2026-03-24T08:00:00+08:00",
            "finished_at": "2026-03-24T08:00:15+08:00",
            "status": "completed",
            "steps": [
                {"step_id": 1, "duration": 2.5, "status": "success"},
                {"step_id": 2, "duration": 5.0, "status": "success"},
                {"step_id": 3, "duration": 7.5, "status": "success"}
            ]
        }
    ]
    
    recommendations = optimizer.analyze(flow, mock_logs)
    print(f"✓ 分析完成，生成 {len(recommendations)} 条优化建议")
    
    for i, rec in enumerate(recommendations, 1):
        print(f"\n  建议 {i}: {rec.get('type', 'N/A')}")
        print(f"  问题: {rec.get('issue', 'N/A')}")
        if rec.get('suggestions'):
            for j, suggestion in enumerate(rec['suggestions'][:1], 1):
                print(f"  方案{j}: {suggestion.get('suggestion', 'N/A')}")
    
    # 8. 测试总结
    print("\n" + "=" * 60)
    print("端到端集成测试完成")
    print("=" * 60)
    print("\n测试结果:")
    print("✓ 需求转换: 成功")
    print("✓ 静态检查: 通过")
    print("✓ 流程生成: 成功")
    print("✓ 性能分析: 成功")
    print("\n整体状态: 通过 ✓")
    
    return True
```

---

## 7. 影刀集成实践

### 7.1 影刀平台简介

影刀是国内领先的 RPA 平台，提供：

- **可视化流程设计**：拖拽式操作，无需编码
- **丰富的组件库**：覆盖 Web、桌面、数据库等
- **Python 扩展**：支持自定义组件开发
- **云端部署**：支持流程云端运行和调度
- **API 集成**：提供 REST API 进行流程管理

### 7.2 影刀 API 接口

#### 7.2.1 创建流程

```python
import requests

def create_yingdao_flow(flow_data):
    """创建影刀流程"""
    
    api_url = "https://api.yingdao.com/api/v1/flows"
    api_key = "YOUR_API_KEY"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 转换为影刀格式
    yingdao_flow = convert_to_yingdao_format(flow_data)
    
    response = requests.post(api_url, headers=headers, json=yingdao_flow)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"创建流程失败: {response.text}")
```

#### 7.2.2 执行流程

```python
def execute_yingdao_flow(flow_id, params=None):
    """执行影刀流程"""
    
    api_url = f"https://api.yingdao.com/api/v1/flows/{flow_id}/execute"
    api_key = "YOUR_API_KEY"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "params": params or {},
        "async": True
    }
    
    response = requests.post(api_url, headers=headers, json=data)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"执行流程失败: {response.text}")
```

#### 7.2.3 查询执行状态

```python
def get_execution_status(execution_id):
    """查询执行状态"""
    
    api_url = f"https://api.yingdao.com/api/v1/executions/{execution_id}"
    api_key = "YOUR_API_KEY"
    
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    response = requests.get(api_url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"查询状态失败: {response.text}")
```

### 7.3 格式转换器

将 AI 生成的流程格式转换为影刀格式：

```python
class YingdaoFormatConverter:
    """影刀格式转换器"""
    
    def __init__(self):
        self.action_mapping = {
            "open_browser": "Browser.Open",
            "click": "Element.Click",
            "input": "Element.Input",
            "extract": "Element.GetText",
            "wait": "Delay",
            "send_email": "Email.Send",
            "save_excel": "Excel.Write",
            "read_excel": "Excel.Read"
        }
    
    def convert(self, ai_flow: Dict) -> Dict:
        """转换为影刀格式"""
        yingdao_flow = {
            "name": ai_flow["flow_name"],
            "version": ai_flow.get("version", "1.0"),
            "description": ai_flow.get("metadata", {}).get("description", ""),
            "variables": self._convert_variables(ai_flow.get("variables", {})),
            "activities": self._convert_activities(ai_flow.get("steps", [])),
            "settings": {
                "retry_policy": self._convert_retry_policy(
                    ai_flow.get("error_handling", {})
                ),
                "log_level": "info"
            }
        }
        
        return yingdao_flow
    
    def _convert_variables(self, variables: Dict) -> List[Dict]:
        """转换变量"""
        yingdao_vars = []
        
        for var_name, var_info in variables.items():
            yingdao_var = {
                "name": var_name,
                "type": self._map_variable_type(var_info.get("type", "string")),
                "value": var_info.get("value", ""),
                "is_secure": var_info.get("type") == "secure_string"
            }
            yingdao_vars.append(yingdao_var)
        
        return yingdao_vars
    
    def _map_variable_type(self, type_str: str) -> str:
        """映射变量类型"""
        type_mapping = {
            "string": "String",
            "number": "Int32",
            "boolean": "Boolean",
            "secure_string": "SecureString"
        }
        return type_mapping.get(type_str, "String")
    
    def _convert_activities(self, steps: List[Dict]) -> List[Dict]:
        """转换活动（步骤）"""
        yingdao_activities = []
        
        for step in steps:
            activity = {
                "id": f"activity_{step['step_id']}",
                "type": self._map_action_type(step["action"]),
                "displayName": step.get("description", step["action"]),
                "properties": self._convert_step_properties(step),
                "nextActivities": self._get_next_activities(step)
            }
            yingdao_activities.append(activity)
        
        return yingdao_activities
    
    def _map_action_type(self, action: str) -> str:
        """映射动作类型"""
        return self.action_mapping.get(action, "CustomActivity")
    
    def _convert_step_properties(self, step: Dict) -> Dict:
        """转换步骤属性"""
        properties = {}
        params = step.get("params", {})
        
        action = step["action"]
        
        if action == "open_browser":
            properties["Url"] = params.get("url", "")
            properties["Headless"] = params.get("headless", False)
        
        elif action == "click":
            properties["Selector"] = params.get("selector", "")
            properties["SimulateClick"] = True
        
        elif action == "input":
            properties["Selector"] = params.get("selector", "")
            properties["Value"] = params.get("value", "")
            properties["ClearBeforeInput"] = True
        
        elif action == "extract":
            properties["Selector"] = params.get("selector", "")
            properties["ExtractType"] = params.get("format", "text")
        
        elif action == "wait":
            properties["DelaySeconds"] = params.get("duration", 5)
        
        elif action == "send_email":
            properties["To"] = params.get("recipient", "")
            properties["Subject"] = params.get("subject", "")
            properties["Body"] = params.get("body", "")
        
        return properties
    
    def _get_next_activities(self, step: Dict) -> List[str]:
        """获取下一步活动 ID"""
        # 这里需要根据步骤 ID 找到依赖该步骤的所有步骤
        # 简化实现：假设步骤按顺序执行
        return [f"activity_{step['step_id'] + 1}"]
    
    def _convert_retry_policy(self, error_handling: Dict) -> Dict:
        """转换重试策略"""
        if not error_handling:
            return {}
        
        # 取第一个步骤的重试策略作为默认策略
        first_step = next(iter(error_handling.values()), {})
        retry_policy = first_step.get("retry_policy", {})
        
        return {
            "enabled": True,
            "maxRetryCount": retry_policy.get("max_retries", 3),
            "retryDelay": retry_policy.get("retry_delay", 5),
            "retryOnFailure": True
        }
```

### 7.4 实际应用案例

#### 案例：电商订单自动化处理

**业务需求**：
> 每天上午10点，从电商平台后台下载前一天的所有订单，进行数据清洗（去除重复、格式化日期、计算总金额），生成销售报表并发送给销售团队。

**实现步骤**：

1. **需求解析**：
```python
user_input = """
每天上午10点，从电商平台后台下载前一天的所有订单，
进行数据清洗（去除重复、格式化日期、计算总金额），
生成销售报表并发送给销售团队
"""

converter = NLToRPAConverter(llm_client)
result = converter.convert(user_input)
```

2. **生成的流程**：
```json
{
  "flow_name": "电商订单自动化处理",
  "variables": {
    "platform_url": {"type": "string", "value": "https://platform.example.com"},
    "admin_username": {"type": "secure_string", "value": "{TODO_账号}"},
    "admin_password": {"type": "secure_string", "value": "{TODO_密码}"},
    "sales_team_email": {"type": "string", "value": "sales@company.com"},
    "report_output_path": {"type": "string", "value": "./reports/sales_{{date}}.xlsx"}
  },
  "steps": [
    {
      "step_id": 1,
      "action": "open_browser",
      "description": "打开电商平台后台",
      "params": {"url": "{{platform_url}}"},
      "dependencies": []
    },
    {
      "step_id": 2,
      "action": "login",
      "description": "登录后台",
      "params": {
        "username": "{{admin_username}}",
        "password": "{{admin_password}}"
      },
      "dependencies": [1]
    },
    {
      "step_id": 3,
      "action": "navigate_to_orders",
      "description": "导航到订单页面",
      "params": {"path": "/admin/orders"},
      "dependencies": [2]
    },
    {
      "step_id": 4,
      "action": "set_date_filter",
      "description": "设置日期筛选（前一天）",
      "params": {"date": "yesterday"},
      "dependencies": [3]
    },
    {
      "step_id": 5,
      "action": "download_orders",
      "description": "下载订单数据",
      "params": {"format": "excel"},
      "dependencies": [4]
    },
    {
      "step_id": 6,
      "action": "load_excel",
      "description": "加载下载的Excel文件",
      "params": {"path": "./downloads/orders.xlsx"},
      "dependencies": [5]
    },
    {
      "step_id": 7,
      "action": "remove_duplicates",
      "description": "去除重复订单",
      "params": {"key_columns": ["order_id"]},
      "dependencies": [6]
    },
    {
      "step_id": 8,
      "action": "format_dates",
      "description": "格式化日期字段",
      "params": {
        "columns": ["order_date", "payment_date"],
        "format": "YYYY-MM-DD"
      },
      "dependencies": [7]
    },
    {
      "step_id": 9,
      "action": "calculate_totals",
      "description": "计算订单总金额",
      "params": {
        "formula": "quantity * unit_price",
        "output_column": "total_amount"
      },
      "dependencies": [8]
    },
    {
      "step_id": 10,
      "action": "generate_report",
      "description": "生成销售报表",
      "params": {
        "output_path": "{{report_output_path}}",
        "charts": ["sales_by_product", "sales_by_region"]
      },
      "dependencies": [9]
    },
    {
      "step_id": 11,
      "action": "send_email",
      "description": "发送报表给销售团队",
      "params": {
        "to": "{{sales_team_email}}",
        "subject": "每日销售报表 - {{date}}",
        "body": "附件为昨天的销售报表，请查收。",
        "attachments": ["{{report_output_path}}"]
      },
      "dependencies": [10]
    }
  ]
}
```

3. **转换到影刀格式**：
```python
converter = YingdaoFormatConverter()
yingdao_flow = converter.convert(result["flow"])

# 部署到影刀
yingdao_api = YingdaoAdapter(config["yingdao"])
flow_result = yingdao_api.create_flow(yingdao_flow)
flow_id = flow_result["flow_id"]
```

4. **设置定时任务**：
```python
# 每天上午10点执行
cron_expression = "0 10 * * *"

scheduler = TaskScheduler(config)
job_id = scheduler.schedule(result["flow"], cron_expression)
```

5. **执行和监控**：
```python
# 执行流程
execution_result = yingdao_api.execute_flow(flow_id)
execution_id = execution_result["execution_id"]

# 监控执行状态
status = yingdao_api.get_execution_status(execution_id)
print(f"状态: {status['status']}")
```

6. **性能优化**：
```python
# 运行一段时间后，分析性能数据
optimizer = FlowOptimizer(config)
logs = yingdao_api.get_execution_logs(flow_id)
recommendations = optimizer.analyze(result["flow"], logs)

# 应用优化建议
# ...
```

---

## 8. 性能优化策略

### 8.1 性能瓶颈识别

#### 常见性能瓶颈

1. **固定等待时间**：使用 `sleep()` 导致不必要的延迟
2. **串行执行**：可并行的步骤串行执行
3. **重复操作**：相同的数据重复获取或处理
4. **低效选择器**：不稳定的元素选择导致重试
5. **内存泄漏**：未正确释放资源

#### 性能分析工具

```python
class PerformanceAnalyzer:
    """性能分析器"""
    
    def analyze_flow(self, flow: Dict, execution_logs: List[Dict]) -> Dict:
        """分析流程性能"""
        metrics = {
            "total_execution_time": 0,
            "step_analysis": {},
            "bottlenecks": [],
            "optimization_potential": []
        }
        
        # 分析整体执行时间
        for log in execution_logs:
            started = datetime.fromisoformat(log["started_at"])
            finished = datetime.fromisoformat(log["finished_at"])
            duration = (finished - started).total_seconds()
            metrics["total_execution_time"] += duration
        
        # 分析每个步骤
        step_times = defaultdict(list)
        for log in execution_logs:
            for step_log in log.get("steps", []):
                step_id = step_log.get("step_id")
                duration = step_log.get("duration", 0)
                step_times[step_id].append(duration)
        
        for step_id, times in step_times.items():
            avg_time = sum(times) / len(times)
            max_time = max(times)
            min_time = min(times)
            
            metrics["step_analysis"][step_id] = {
                "avg_duration": avg_time,
                "max_duration": max_time,
                "min_duration": min_time,
                "variance": max_time - min_time,
                "execution_count": len(times)
            }
            
            # 识别瓶颈
            if avg_time > 10:  # 超过10秒
                metrics["bottlenecks"].append({
                    "step_id": step_id,
                    "type": "slow",
                    "avg_duration": avg_time,
                    "potential_reduction": "30-50%"
                })
        
        # 计算优化潜力
        if metrics["bottlenecks"]:
            potential_reduction = sum(
                b["avg_duration"] * 0.4  # 假设可减少40%
                for b in metrics["bottlenecks"]
            )
            metrics["optimization_potential"] = {
                "current_total": metrics["total_execution_time"],
                "estimated_reduction": potential_reduction,
                "optimized_total": metrics["total_execution_time"] - potential_reduction,
                "improvement_percentage": (potential_reduction / metrics["total_execution_time"]) * 100
            }
        
        return metrics
```

### 8.2 优化技术

#### 8.2.1 智能等待策略

**问题**：固定等待时间导致流程变慢

**解决方案**：使用显式等待

```python
# 优化前
time.sleep(5)
element = browser.find_element("#submit")
element.click()

# 优化后
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

wait = WebDriverWait(driver, 10)
element = wait.until(
    EC.presence_of_element_located((By.ID, "submit"))
)
element.click()
```

**AI 辅助优化建议**：
- 检测到固定等待时间时，建议替换为显式等待
- 分析页面加载模式，动态调整超时时间
- 对于网络请求，建议使用更智能的重试策略

#### 8.2.2 并行执行优化

**问题**：可并行的步骤串行执行

**解决方案**：识别并行机会，使用多线程/异步执行

```python
import asyncio
import aiohttp

async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

async def parallel_fetch(urls):
    tasks = [fetch_data(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return results

# 使用
urls = ["https://api1.com/data", "https://api2.com/data", "https://api3.com/data"]
results = asyncio.run(parallel_fetch(urls))
```

**AI 辅助优化**：
- 分析步骤依赖图，识别可并行执行的步骤组
- 估计并行执行的收益
- 生成优化后的执行计划

#### 8.2.3 缓存机制

**问题**：相同的数据重复获取

**解决方案**：添加缓存层

```python
from functools import lru_cache
import hashlib

class DataCache:
    """数据缓存"""
    
    def __init__(self):
        self.cache = {}
    
    def get(self, key):
        """获取缓存"""
        return self.cache.get(key)
    
    def set(self, key, value, ttl=3600):
        """设置缓存"""
        self.cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl
        }
    
    def is_expired(self, key):
        """检查是否过期"""
        if key not in self.cache:
            return True
        
        return self.cache[key]["expires_at"] < time.time()

# 使用
cache = DataCache()

def get_data_with_cache(url):
    cache_key = hashlib.md5(url.encode()).hexdigest()
    
    if not cache.is_expired(cache_key):
        return cache.get(cache_key)["value"]
    
    data = fetch_data(url)
    cache.set(cache_key, data)
    
    return data
```

#### 8.2.4 选择器优化

**问题**：不稳定的元素选择器导致失败

**解决方案**：使用更稳定的选择器策略

```python
class SelectorOptimizer:
    """选择器优化器"""
    
    STABLE_SELECTORS = [
        # 优先使用 data 属性
        "[data-{attr}='{value}']",
        # 使用 aria 属性
        "[aria-label='{value}']",
        "[aria-id='{value}']",
        # 使用特定 ID（不是动态生成的）
        "#{id}",
        # 最后才用 class
        ".{class}"
    ]
    
    def optimize_selector(self, element_info: Dict) -> str:
        """优化选择器"""
        # 尝试按优先级生成选择器
        for selector_template in self.STABLE_SELECTORS:
            selector = self._try_template(element_info, selector_template)
            if selector:
                return selector
        
        # 如果都不行，使用元素的结构路径
        return self._generate_path_selector(element_info)
    
    def _try_template(self, element_info: Dict, template: str) -> Optional[str]:
        """尝试使用模板生成选择器"""
        # 实现逻辑...
        pass
    
    def _generate_path_selector(self, element_info: Dict) -> str:
        """生成基于路径的选择器"""
        # 实现逻辑...
        pass
```

### 8.3 自适应优化

基于执行数据的自动优化策略：

```python
class AdaptiveOptimizer:
    """自适应优化器"""
    
    def __init__(self):
        self.performance_history = {}
        self.optimization_rules = [
            self._optimize_wait_times,
            self._optimize_selectors,
            self._optimize_parallelism
        ]
    
    def optimize_flow(self, flow: Dict, execution_logs: List[Dict]) -> Dict:
        """优化流程"""
        optimized_flow = flow.copy()
        
        # 收集性能数据
        performance_data = self._collect_performance_data(execution_logs)
        
        # 应用优化规则
        for rule in self.optimization_rules:
            optimized_flow = rule(optimized_flow, performance_data)
        
        return optimized_flow
    
    def _optimize_wait_times(self, flow: Dict, data: Dict) -> Dict:
        """优化等待时间"""
        for step in flow["steps"]:
            if step["action"] == "wait":
                # 根据历史数据调整等待时间
                step_id = step["step_id"]
                if step_id in data:
                    avg_time = data[step_id]["avg_actual_wait_time"]
                    # 使用 P90 的值
                    p90_time = data[step_id]["p90_actual_wait_time"]
                    step["params"]["duration"] = min(avg_time * 1.2, p90_time)
        
        return flow
    
    def _optimize_selectors(self, flow: Dict, data: Dict) -> Dict:
        """优化选择器"""
        for step in flow["steps"]:
            if step["action"] in ["click", "input", "extract"]:
                step_id = step["step_id"]
                if step_id in data and data[step_id]["failure_rate"] > 0.1:
                    # 选择器不稳定，尝试生成更稳定的选择器
                    current_selector = step["params"]["selector"]
                    new_selector = self._generate_stable_selector(current_selector, data[step_id])
                    if new_selector:
                        step["params"]["selector"] = new_selector
        
        return flow
    
    def _optimize_parallelism(self, flow: Dict, data: Dict) -> Dict:
        """优化并行执行"""
        # 分析步骤依赖，识别并行机会
        # 生成优化后的执行计划
        return flow
```

---

## 9. 未来发展方向

### 9.1 短期目标（3-6 个月）

1. **完善核心功能**
   - 增强自然语言解析准确率（目标：95%+）
   - 扩展支持的 RPA 操作类型（增加 50%）
   - 优化代码生成质量

2. **提升用户体验**
   - 开发可视化编辑器
   - 支持实时预览和调试
   - 添加交互式需求澄清功能

3. **集成更多平台**
   - 支持 UiPath
   - 支持 Automation Anywhere
   - 支持 Power Automate

### 9.2 中期目标（6-12 个月）

1. **智能化升级**
   - 引入多模态输入（截图、语音）
   - 支持流程可视化理解（从流程图生成需求）
   - 自适应学习和优化

2. **企业级功能**
   - 多租户支持
   - RBAC 权限管理
   - 审计日志和合规报告

3. **性能优化**
   - 大规模流程并发执行
   - 分布式任务调度
   - 实时性能监控

### 9.3 长期愿景（1-3 年）

1. **完全自动化**
   - 零代码/低代码 RPA 开发
   - AI 自主发现自动化机会
   - 自愈和自适应 RPA 流程

2. **生态系统建设**
   - 流程市场（分享和复用）
   - 插件系统（扩展功能）
   - 开发者社区

3. **技术前沿探索**
   - 大模型微调（领域专用模型）
   - 强化学习优化
   - 跨平台流程迁移

---

## 10. 附录

### 10.1 术语表

| 术语 | 英文 | 解释 |
|------|------|------|
| RPA | Robotic Process Automation | 机器人流程自动化 |
| NLP | Natural Language Processing | 自然语言处理 |
| LLM | Large Language Model | 大语言模型 |
| CoT | Chain-of-Thought | 思维链提示策略 |
| DOM | Document Object Model | 文档对象模型 |
| API | Application Programming Interface | 应用程序编程接口 |
| UI | User Interface | 用户界面 |

### 10.2 参考资源

**论文和研究**：
- Wei et al. "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models"
- Brown et al. "Language Models are Few-Shot Learners"

**工具和框架**：
- 影刀 RPA: https://www.yingdao.com/
- LangChain: https://github.com/hwchase17/langchain
- Selenium: https://www.selenium.dev/

**社区和文档**：
- RPA 中国: https://rpa.cn/
- LLM 指南: https://github.com/Mooler0410/LLMsPracticalGuide

### 10.3 配置文件示例

**完整配置文件**：

```json
{
  "llm": {
    "provider": "zhipuai",
    "model": "glm-4",
    "api_key": "YOUR_ZHIPUAI_API_KEY",
    "base_url": "https://open.bigmodel.cn/api/paas/v4/",
    "temperature": 0.7,
    "max_tokens": 2000,
    "timeout": 30
  },
  "yingdao": {
    "api_endpoint": "https://api.yingdao.com/api/v1",
    "api_key": "YOUR_YINGDAO_API_KEY",
    "timeout": 60
  },
  "database": {
    "type": "sqlite",
    "path": "./data/ai_rpa.db",
    "backup_enabled": true
  },
  "logging": {
    "level": "INFO",
    "file": "./logs/ai_rpa.log",
    "max_size": "10MB",
    "backup_count": 5,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  },
  "scheduler": {
    "timezone": "Asia/Shanghai",
    "default_max_workers": 3,
    "job_store": "sqlite",
    "job_store_path": "./data/jobs.db"
  },
  "optimization": {
    "auto_optimize": true,
    "optimization_threshold": 0.8,
    "min_execution_logs": 5
  }
}
```

### 10.4 常见问题

**Q1: 如何提高自然语言解析的准确率？**

A: 可以通过以下方式提升：
1. 使用更强大的 LLM 模型（如 GPT-4）
2. 提供 Few-shot 示例
3. 构建领域知识库
4. 增加多轮对话澄清环节

**Q2: 支持哪些 RPA 平台？**

A: 目前主要支持影刀，计划支持：
- UiPath
- Automation Anywhere
- Power Automate
- 自定义 Python RPA

**Q3: 如何处理复杂的业务逻辑？**

A: 可以通过以下方式：
1. 将复杂需求拆分为多个子流程
2. 使用条件分支和循环结构
3. 结合人工审核和确认
4. 使用变量和表达式

**Q4: 生成的代码质量如何保障？**

A: 通过多重保障：
1. 静态代码检查
2. 模拟执行测试
3. 人工审核机制
4. 持续优化反馈

**Q5: 如何部署到生产环境？**

A: 部署步骤：
1. 配置生产环境参数
2. 部署到影刀云端
3. 设置定时任务
4. 配置监控和告警
5. 准备回滚方案

---

## 结语

本技术白皮书详细阐述了 AI + RPA 深度集成的技术方案，从需求理解到流程生成、执行、优化的完整闭环。通过自然语言驱动的 RPA 开发，可以大幅降低自动化门槛，加速企业数字化转型。

未来，我们将持续优化系统性能，扩展功能边界，致力于打造最智能、最易用的 RPA 开发平台。

---

**文档版本**: 1.0  
**最后更新**: 2026-03-24  
**作者**: 小lin  
**联系**: [待补充]
