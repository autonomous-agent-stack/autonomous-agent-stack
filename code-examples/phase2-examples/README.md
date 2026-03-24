# 多智能体系统代码示例（第二阶段）

> **版本**: v0.1
> **日期**: 2026-03-25
> **状态**: 🚧 进行中

---

## 📋 目录

1. [快速开始](#快速开始)
2. [示例列表](#示例列表)
3. [依赖安装](#依赖安装)
4. [运行示例](#运行示例)

---

## 快速开始

### 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### requirements.txt

```
# 核心依赖
asyncio-mqtt==0.16.1
redis==5.0.1
httpx==0.27.0
prometheus-client==0.20.0

# 可视化
matplotlib==3.8.4
networkx==3.2.1

# 工具
python-dotenv==1.0.0
pydantic==2.6.0
```

### 配置环境变量

创建 `.env` 文件：

```bash
# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/agent.log
```

---

## 示例列表

### 1. 基础Agent类

**文件**: `01_basic_agent.py`

**功能**:
- 实现基础Agent类
- 消息收发机制
- 心跳检测

**运行**:
```bash
python 01_basic_agent.py
```

### 2. 层级式协作

**文件**: `02_hierarchical_collaboration.py`

**功能**:
- Orchestrator-Worker架构
- 任务分配与结果汇总
- 支持多个Worker并行

**运行**:
```bash
python 02_hierarchical_collaboration.py
```

### 3. 网状协作

**文件**: `03_mesh_collaboration.py`

**功能**:
- P2P消息传递
- 去中心化决策
- Gossip协议

**运行**:
```bash
python 03_mesh_collaboration.py
```

### 4. 流水线协作

**文件**: `04_pipeline_collaboration.py`

**功能**:
- 顺序任务处理
- 数据流转
- 错误处理

**运行**:
```bash
python 04_pipeline_collaboration.py
```

### 5. 递归协作

**文件**: `05_fractal_collaboration.py`

**功能**:
- 任务递归分解
- 分治算法
- 并行执行子任务

**运行**:
```bash
python 05_fractal_collaboration.py
```

### 6. 粒子群优化

**文件**: `06_pso_optimization.py`

**功能**:
- PSO算法实现
- 多目标优化
- 可视化收敛过程

**运行**:
```bash
python 06_pso_optimization.py
```

### 7. 蚁群优化

**文件**: `07_aco_optimization.py`

**功能**:
- ACO算法实现
- 路径优化
- 信息素更新机制

**运行**:
```bash
python 07_aco_optimization.py
```

### 8. Raft共识

**文件**: `08_raft_consensus.py`

**功能**:
- Raft算法实现
- 选举机制
- 日志复制

**运行**:
```bash
python 08_raft_consensus.py
```

### 9. Gossip协议

**文件**: `09_gossip_protocol.py`

**功能**:
- Gossip传播
- 最终一致性
- 反熵机制

**运行**:
```bash
python 09_gossip_protocol.py
```

### 10. 任务编排引擎

**文件**: `10_workflow_engine.py`

**功能**:
- 工作流定义（JSON）
- DAG执行引擎
- 并行任务调度

**运行**:
```bash
python 10_workflow_engine.py
```

### 11. 分布式锁

**文件**: `11_distributed_lock.py`

**功能**:
- Redis分布式锁
- 锁重试机制
- 死锁预防

**运行**:
```bash
python 11_distributed_lock.py
```

### 12. 消息总线

**文件**: `12_message_bus.py`

**功能**:
- Redis Pub/Sub
- 消息序列化
- 消息确认

**运行**:
```bash
python 12_message_bus.py
```

### 13. 监控系统

**文件**: `13_monitoring_system.py`

**功能**:
- Prometheus指标
- Agent健康检查
- 性能分析

**运行**:
```bash
# 启动Prometheus
prometheus --config.file=prometheus.yml

# 运行示例
python 13_monitoring_system.py

# 访问
# http://localhost:9090
```

### 14. 容错机制

**文件**: `14_fault_tolerance.py`

**功能**:
- 重试策略
- 断路器模式
- 降级机制

**运行**:
```bash
python 14_fault_tolerance.py
```

### 15. 完整案例：数据分析

**文件**: `15_case_data_analysis.py`

**功能**:
- 多Agent协作数据分析
- 实时数据流处理
- 自动报告生成

**运行**:
```bash
python 15_case_data_analysis.py
```

---

## 运行示例

### 单个示例

```bash
# 运行特定示例
python 01_basic_agent.py

# 查看帮助
python 01_basic_agent.py --help
```

### 所有示例

```bash
# 运行所有示例
python run_all_examples.py
```

### 测试

```bash
# 运行单元测试
pytest tests/

# 运行集成测试
pytest tests/integration/

# 生成覆盖率报告
pytest --cov=. --cov-report=html
```

---

## 架构图

### 系统架构

```
┌─────────────────────────────────────────────────┐
│              用户接口层                         │
│  (CLI / Web / API)                          │
└──────────────────┬────────────────────────────┘
                   │
┌──────────────────▼────────────────────────────┐
│              编排层                          │
│  - OrchestratorAgent                         │
│  - WorkflowEngine                            │
│  - TaskScheduler                            │
└──────────────────┬────────────────────────────┘
                   │
┌──────────────────▼────────────────────────────┐
│              协作层                          │
│  - HierarchicalCollaborator                  │
│  - MeshCollaborator                         │
│  - PipelineCollaborator                     │
│  - FractalCollaborator                      │
└──────────────────┬────────────────────────────┘
                   │
┌──────────────────▼────────────────────────────┐
│              通信层                          │
│  - MessageBus (Redis Pub/Sub)               │
│  - DistributedLock                          │
│  - GossipProtocol                          │
└──────────────────┬────────────────────────────┘
                   │
┌──────────────────▼────────────────────────────┐
│              智能层                          │
│  - PSOOptimizer                            │
│  - ACOOptimizer                            │
│  - RaftConsensus                           │
└──────────────────┬────────────────────────────┘
                   │
┌──────────────────▼────────────────────────────┐
│              执行层                          │
│  - WorkerAgents                            │
│  - TaskExecutors                           │
└───────────────────────────────────────────────┘
```

---

## 扩展开发

### 添加新示例

1. 在 `examples/` 目录下创建新文件
2. 实现示例逻辑
3. 添加文档说明
4. 更新本README

### 添加新功能

1. 在 `src/` 目录下创建新模块
2. 编写单元测试
3. 更新文档
4. 提交PR

---

## 常见问题

### Q: 如何选择合适的协作模式？

A: 根据任务特性选择：
- 层级式：专家协作，明确分工
- 网状：实时协作，去中心化
- 流水线：顺序处理，数据流转
- 递归：复杂任务，分治求解

### Q: 如何处理Agent崩溃？

A: 实现以下机制：
1. 心跳检测
2. 任务重分配
3. 断路器模式
4. 降级策略

### Q: 如何优化性能？

A: 参考以下策略：
1. 并行执行可并行任务
2. 使用连接池
3. 实现缓存
4. 优化数据库查询
5. 压缩大消息

---

## 贡献指南

欢迎贡献代码！

1. Fork本仓库
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

---

## 许可证

MIT License

---

## 联系方式

- **Issues**: https://github.com/your-repo/issues
- **Discussions**: https://github.com/your-repo/discussions

---

**版本**: v0.1
**最后更新**: 2026-03-25
**作者**: 小lin 🤖
**状态**: 🚧 进行中
