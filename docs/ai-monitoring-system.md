# AI 系统监控体系

> **版本**: 1.0  
> **创建日期**: 2026-03-24  
> **适用范围**: LLM、RAG、Agent、系统资源

## 概述

本监控体系覆盖 AI 系统的核心组件，包含 40+ 个关键监控指标，提供全方位的可观测性和告警能力。

---

## 一、LLM 监控（15 个指标）

### 1. 请求量（Request Volume）

**指标定义**：单位时间内 LLM API 调用次数

**采集方法**：
- 在 API 网关层记录每次调用
- 使用 Prometheus Counter 指标：`llm_requests_total{model, endpoint}`
- 采样周期：1 分钟

**告警阈值**：
- 警告：请求量 > 10,000/min
- 严重：请求量 > 50,000/min

**可视化方案**：
- 时间序列折线图（1小时、24小时、7天）
- 按模型分组的堆叠图
- 热力图显示高峰时段

**分析建议**：
- 监控请求量趋势，识别流量波动
- 对比不同模型的使用占比
- 为容量规划和成本预估提供依据

---

### 2. 响应时间（Response Time）

**指标定义**：从请求发起到完全接收响应的时间

**采集方法**：
- 记录每个请求的 timestamps：start_time, end_time
- 使用 Histogram 指标：`llm_response_time_seconds{model}`
- 分桶配置：[0.1, 0.5, 1, 2, 5, 10, 30, 60]

**告警阈值**：
- P50 警告：> 2s
- P95 警告：> 5s
- P99 严重：> 10s

**可视化方案**：
- 时间序列折线图（P50/P95/P99）
- 箱线图显示分布
- 热力图：模型 × 时间段

**分析建议**：
- 识别慢查询和性能瓶颈
- 对比不同模型的响应时间
- 优化超时设置和重试策略

---

### 3. Token 使用量（Token Usage）

**指标定义**：输入 Token 和输出 Token 的累计量

**采集方法**：
- 从 API 响应中提取 `usage.prompt_tokens` 和 `usage.completion_tokens`
- 使用 Counter 指标：
  - `llm_tokens_input_total{model}`
  - `llm_tokens_output_total{model}`
- 采样周期：1 分钟

**告警阈值**：
- 日使用量警告：> 1M tokens
- 异常突增：环比增长 > 50%

**可视化方案**：
- 双轴折线图（输入 vs 输出）
- 按模型分组的堆叠面积图
- 成本估算仪表盘

**分析建议**：
- 追踪成本趋势
- 优化提示词长度
- 识别高消耗场景

---

### 4. 错误率（Error Rate）

**指标定义**：失败请求数占总请求数的比例

**采集方法**：
- 记录 HTTP 状态码和错误类型
- 使用 Counter 指标：
  - `llm_requests_total{status="success"}`
  - `llm_requests_total{status="error"}`
- 计算公式：错误率 = error_requests / total_requests

**告警阈值**：
- 警告：错误率 > 5%
- 严重：错误率 > 10%
- 紧急：错误率 > 20%

**可视化方案**：
- 百分比折线图
- 错误类型分布饼图
- 时间轴上的错误标记

**分析建议**：
- 分类错误类型（超时、限流、服务异常）
- 关联特定模型或时间段
- 优化重试和降级策略

---

### 5. 成本（Cost）

**指标定义**：基于 Token 使用的预估成本

**采集方法**：
- 根据模型定价计算：
  - 成本 = (input_tokens × input_price + output_tokens × output_price)
- 使用 Gauge 指标：`llm_cost_dollars{model}`
- 采样周期：1 小时

**告警阈值**：
- 小时成本警告：> $10
- 日成本警告：> $100
- 异常增长：环比 > 50%

**可视化方案**：
- 累计成本柱状图
- 按模型分组的饼图
- 成本趋势折线图

**分析建议**：
- 追踪预算消耗
- 识别高成本模型
- 优化提示词和模型选择

---

### 6. 并发数（Concurrency）

**指标定义**：当前正在处理的请求数量

**采集方法**：
- 在请求处理前后记录计数
- 使用 Gauge 指标：`llm_concurrent_requests{model}`
- 实时采样

**告警阈值**：
- 警告：并发数 > 50
- 严重：并发数 > 100
- 接近限流：> 配置上限的 80%

**可视化方案**：
- 实时仪表盘
- 时间序列热力图
- 按模型分组的柱状图

**分析建议**：
- 监控系统负载
- 识别高峰时段
- 优化并发控制策略

---

### 7. 队列长度（Queue Length）

**指标定义**：等待处理的请求数量

**采集方法**：
- 记录消息队列长度
- 使用 Gauge 指标：`llm_queue_length`
- 实时采样

**告警阈值**：
- 警告：队列长度 > 100
- 严重：队列长度 > 500
- 紧急：队列长度 > 1000

**可视化方案**：
- 实时队列监控仪表盘
- 时间序列折线图
- 排队时间分布直方图

**分析建议**：
- 监控系统积压情况
- 优化队列配置和扩容策略
- 预警处理延迟风险

---

### 8. 缓存命中率（Cache Hit Rate）

**指标定义**：缓存命中次数占总查询次数的比例

**采集方法**：
- 记录 cache_hit 和 cache_miss
- 使用 Counter 指标：
  - `llm_cache_hits_total`
  - `llm_cache_misses_total`
- 计算公式：命中率 = cache_hits / (cache_hits + cache_misses)

**告警阈值**：
- 命中率过低：< 30%
- 目标值：> 50%

**可视化方案**：
- 百分比仪表盘
- 时间序列折线图
- 命中/未命中对比图

**分析建议**：
- 优化缓存策略和键设计
- 识别高频重复查询
- 调整缓存过期时间

---

### 9. 模型分布（Model Distribution）

**指标定义**：各模型使用占比

**采集方法**：
- 按模型标签统计请求量
- 使用 Counter 指标：`llm_requests_total{model}`
- 采样周期：1 小时

**告警阈值**：
- 模型使用异常（单模型占比 > 90%）

**可视化方案**：
- 饼图/环形图
- 堆叠面积图
- 模型对比表

**分析建议**：
- 了解模型使用偏好
- 识别过度依赖的模型
- 为模型升级和淘汰提供依据

---

### 10. 用户分布（User Distribution）

**指标定义**：按用户或租户的请求分布

**采集方法**：
- 从请求上下文提取 user_id 或 tenant_id
- 使用 Counter 指标：`llm_requests_total{user_id}`
- 采样周期：1 小时

**告警阈值**：
- 单用户异常高流量：> 平均 10 倍
- 未授权用户访问

**可视化方案**：
- Top 10 用户柱状图
- 用户请求量热力图
- 用户画像仪表盘

**分析建议**：
- 识别高频用户
- 发现异常使用模式
- 优化资源分配和计费

---

### 11. 时间分布（Time Distribution）

**指标定义**：按时间段（小时/天/周）的请求分布

**采集方法**：
- 记录请求时间戳
- 使用 Histogram 指标：`llm_requests_time_bucket`
- 采样周期：1 小时

**告警阈值**：
- 异常时段流量（如凌晨 2-5 点）

**可视化方案**：
- 24 小时热力图
- 7 天折线图
- 时段对比图

**分析建议**：
- 识别业务高峰
- 优化资源调度
- 预测容量需求

---

### 12. 质量评分（Quality Score）

**指标定义**：LLM 输出的质量评估（基于用户反馈或自动化评估）

**采集方法**：
- 收集用户评分（1-5 分）
- 使用 Histogram 指标：`llm_quality_score_bucket{model}`
- 采样周期：1 小时

**告警阈值**：
- 平均评分 < 3.5
- 低评分比例 > 30%

**可视化方案**：
- 评分分布直方图
- 时间序列趋势图
- 模型对比雷达图

**分析建议**：
- 识别低质量输出场景
- 优化提示词和模型选择
- 持续改进系统

---

### 13. 内容过滤（Content Filtering）

**指标定义**：被安全策略拦截的请求数量

**采集方法**：
- 记录被过滤的请求
- 使用 Counter 指标：
  - `llm_content_filtered_total{reason}`
- 采样周期：1 小时

**告警阈值**：
- 过滤率异常：> 10%
- 特定类型过滤激增

**可视化方案**：
- 过滤原因分布饼图
- 时间序列折线图
- 过滤类型对比表

**分析建议**：
- 监控安全策略效果
- 识别误杀和漏杀
- 优化过滤规则

---

### 14. 降级次数（Degradation Count）

**指标定义**：启用降级策略（如切换到小模型）的次数

**采集方法**：
- 记录降级事件
- 使用 Counter 指标：`llm_degradations_total{reason}`
- 实时记录

**告警阈值**：
- 降级率 > 5%
- 持续降级 > 10 分钟

**可视化方案**：
- 降级原因分布图
- 时间轴标记
- 降级时长仪表盘

**分析建议**：
- 评估系统稳定性
- 识别降级触发条件
- 优化降级策略

---

### 15. 重试次数（Retry Count）

**指标定义**：请求重试的次数

**采集方法**：
- 记录重试事件和次数
- 使用 Counter 指标：`llm_retries_total{reason}`
- 实时记录

**告警阈值**：
- 重试率 > 10%
- 单请求重试 > 3 次

**可视化方案**：
- 重试原因分布图
- 时间序列折线图
- 重试成功率仪表盘

**分析建议**：
- 识别不稳定的接口
- 优化重试策略
- 改善错误处理

---

## 二、RAG 监控（10 个指标）

### 1. 文档数量（Document Count）

**指标定义**：向量数据库中的文档总数

**采集方法**：
- 查询向量数据库统计
- 使用 Gauge 指标：`rag_documents_total`
- 采样周期：5 分钟

**告警阈值**：
- 文档数量异常下降：> 10%
- 增长停滞：> 24 小时无新增

**可视化方案**：
- 累计数量折线图
- 分类堆叠图
- 数据库状态仪表盘

**分析建议**：
- 监控数据完整性
- 评估数据更新频率
- 规划存储容量

---

### 2. 向量化速度（Vectorization Speed）

**指标定义**：文档向量化的平均速度

**采集方法**：
- 记录每个文档向量化时长
- 使用 Histogram 指标：`rag_vectorization_duration_seconds`
- 实时采样

**告警阈值**：
- P95 > 10s
- 平均速度 > 5s

**可视化方案**：
- 时间序列折线图（P50/P95/P99）
- 分布直方图
- 性能趋势图

**分析建议**：
- 优化向量化性能
- 识别性能瓶颈
- 评估扩容需求

---

### 3. 检索延迟（Retrieval Latency）

**指标定义**：向量检索的平均响应时间

**采集方法**：
- 记录每次检索时长
- 使用 Histogram 指标：`rag_retrieval_latency_seconds`
- 实时采样

**告警阈值**：
- P50 警告：> 500ms
- P95 警告：> 1s
- P99 严重：> 2s

**可视化方案**：
- 时间序列折线图
- 箱线图
- 热力图：查询类型 × 时段

**分析建议**：
- 优化索引和检索算法
- 识别慢查询
- 改善缓存策略

---

### 4. 检索准确率（Retrieval Accuracy）

**指标定义**：检索结果的相关性评分

**采集方法**：
- 记录人工评分或自动化评分
- 使用 Histogram 指标：`rag_retrieval_score_bucket`
- 采样周期：1 小时

**告警阈值**：
- 平均准确率 < 0.7
- 准确率下降 > 20%

**可视化方案**：
- 准确率趋势折线图
- 评分分布直方图
- Top-K 准确率对比图

**分析建议**：
- 优化检索算法
- 调整向量维度和相似度阈值
- 改进文档质量和切分策略

---

### 5. 缓存命中率（Cache Hit Rate）

**指标定义**：向量检索缓存的命中比例

**采集方法**：
- 记录 cache_hit 和 cache_miss
- 使用 Counter 指标：
  - `rag_cache_hits_total`
  - `rag_cache_misses_total`
- 计算公式：命中率 = cache_hits / (cache_hits + cache_misses)

**告警阈值**：
- 命中率过低：< 20%
- 目标值：> 40%

**可视化方案**：
- 百分比仪表盘
- 时间序列折线图
- 缓存效果对比图

**分析建议**：
- 优化缓存策略
- 识别高频重复查询
- 调整缓存容量和过期时间

---

### 6. 存储使用量（Storage Usage）

**指标定义**：向量数据库的存储空间占用

**采集方法**：
- 查询数据库存储统计
- 使用 Gauge 指标：`rag_storage_bytes{type}`
- 采样周期：5 分钟

**告警阈值**：
- 存储使用率 > 80%
- 增长过快：日增长 > 10%

**可视化方案**：
- 存储使用量仪表盘
- 时间序列折线图
- 分类堆叠图（向量/元数据）

**分析建议**：
- 监控存储容量
- 识别存储增长趋势
- 规划扩容和清理策略

---

### 7. 查询量（Query Volume）

**指标定义**：单位时间内的检索查询次数

**采集方法**：
- 记录每次查询
- 使用 Counter 指标：`rag_queries_total{type}`
- 采样周期：1 分钟

**告警阈值**：
- 查询量异常增长：> 50%
- 单用户异常查询

**可视化方案**：
- 时间序列折线图
- 按类型分组的堆叠图
- 热力图：查询类型 × 时段

**分析建议**：
- 识别查询高峰
- 评估系统负载
- 优化容量规划

---

### 8. 错误率（Error Rate）

**指标定义**：检索失败请求的比例

**采集方法**：
- 记录成功和失败的查询
- 使用 Counter 指标：
  - `rag_queries_total{status="success"}`
  - `rag_queries_total{status="error"}`
- 计算公式：错误率 = error_queries / total_queries

**告警阈值**：
- 警告：错误率 > 5%
- 严重：错误率 > 10%
- 紧急：错误率 > 20%

**可视化方案**：
- 百分比折线图
- 错误类型分布饼图
- 时间轴上的错误标记

**分析建议**：
- 分类错误原因
- 关联特定查询模式
- 优化错误处理和重试策略

---

### 9. 索引大小（Index Size）

**指标定义**：向量索引的内存或磁盘占用

**采集方法**：
- 查询索引统计
- 使用 Gauge 指标：`rag_index_bytes`
- 采样周期：5 分钟

**告警阈值**：
- 索引增长异常：> 20%
- 内存使用率 > 80%

**可视化方案**：
- 索引大小仪表盘
- 时间序列折线图
- 索引类型对比图

**分析建议**：
- 监控索引健康度
- 评估内存需求
- 优化索引配置

---

### 10. 更新频率（Update Frequency）

**指标定义**：文档向量化更新的频率

**采集方法**：
- 记录新增、更新、删除操作
- 使用 Counter 指标：
  - `rag_documents_created_total`
  - `rag_documents_updated_total`
  - `rag_documents_deleted_total`
- 采样周期：5 分钟

**告警阈值**：
- 更新异常：> 1000/min
- 更新停滞：> 1 小时无更新

**可视化方案**：
- 操作类型堆叠图
- 时间序列折线图
- 更新统计表

**分析建议**：
- 监控数据新鲜度
- 识别更新异常
- 优化增量更新策略

---

## 三、Agent 监控（10 个指标）

### 1. 任务数量（Task Count）

**指标定义**：单位时间内 Agent 接收的任务数量

**采集方法**：
- 在任务入口记录
- 使用 Counter 指标：`agent_tasks_total{agent_name}`
- 采样周期：1 分钟

**告警阈值**：
- 任务量异常增长：> 50%
- 任务积压：队列 > 100

**可视化方案**：
- 时间序列折线图
- 按任务类型分组
- 任务积压仪表盘

**分析建议**：
- 识别业务高峰
- 评估系统负载
- 规划资源扩容

---

### 2. 完成率（Completion Rate）

**指标定义**：任务成功完成的比例

**采集方法**：
- 记录任务状态（success/failed/cancelled）
- 使用 Counter 指标：
  - `agent_tasks_total{status="success"}`
  - `agent_tasks_total{status="failed"}`
- 计算公式：完成率 = success_tasks / total_tasks

**告警阈值**：
- 警告：完成率 < 90%
- 严重：完成率 < 80%
- 紧急：完成率 < 70%

**可视化方案**：
- 百分比仪表盘
- 状态分布饼图
- 时间序列趋势图

**分析建议**：
- 识别失败模式
- 优化任务处理逻辑
- 改善错误处理

---

### 3. 执行时间（Execution Time）

**指标定义**：任务从开始到完成的耗时

**采集方法**：
- 记录任务开始和结束时间
- 使用 Histogram 指标：`agent_task_duration_seconds{agent_name, task_type}`
- 分桶配置：[1, 5, 10, 30, 60, 300, 600, 1800]

**告警阈值**：
- P50 警告：> 30s
- P95 警告：> 2min
- P99 严重：> 5min

**可视化方案**：
- 时间序列折线图（P50/P95/P99）
- 箱线图
- 任务类型对比图

**分析建议**：
- 识别慢任务和瓶颈
- 优化工作流
- 调整超时设置

---

### 4. 工具调用次数（Tool Call Count）

**指标定义**：任务执行过程中调用工具的次数

**采集方法**：
- 记录每次工具调用
- 使用 Counter 指标：`agent_tool_calls_total{tool_name}`
- 实时记录

**告警阈值**：
- 单任务工具调用 > 20 次
- 工具调用失败率高

**可视化方案**：
- 工具使用分布饼图
- 时间序列折线图
- Top 工具柱状图

**分析建议**：
- 识别高频工具
- 优化工具选择策略
- 发现异常调用模式

---

### 5. 错误率（Error Rate）

**指标定义**：任务执行失败的比例

**采集方法**：
- 记录任务错误类型
- 使用 Counter 指标：`agent_errors_total{error_type}`
- 计算公式：错误率 = error_tasks / total_tasks

**告警阈值**：
- 警告：错误率 > 10%
- 严重：错误率 > 20%
- 紧急：错误率 > 30%

**可视化方案**：
- 百分比折线图
- 错误类型分布图
- 时间轴上的错误标记

**分析建议**：
- 分类错误原因
- 识别故障模式
- 优化容错机制

---

### 6. 重试次数（Retry Count）

**指标定义**：任务执行过程中的重试次数

**采集方法**：
- 记录重试事件
- 使用 Counter 指标：`agent_retries_total{reason}`
- 实时记录

**告警阈值**：
- 重试率 > 20%
- 单任务重试 > 5 次

**可视化方案**：
- 重试原因分布图
- 时间序列折线图
- 重试成功率仪表盘

**分析建议**：
- 识别不稳定的操作
- 优化重试策略
- 改善错误处理

---

### 7. 资源使用（Resource Usage）

**指标定义**：Agent 执行过程中的 CPU、内存等资源占用

**采集方法**：
- 通过进程监控工具采集
- 使用 Gauge 指标：
  - `agent_cpu_usage_percent{agent_name}`
  - `agent_memory_usage_bytes{agent_name}`
- 采样周期：10 秒

**告警阈值**：
- CPU 使用率 > 80%
- 内存使用率 > 80%
- 内存泄漏：持续增长

**可视化方案**：
- 资源使用仪表盘
- 时间序列折线图
- Agent 对比图

**分析建议**：
- 监控资源瓶颈
- 识别资源泄漏
- 优化资源分配

---

### 8. 并发数（Concurrency）

**指标定义**：同时执行的任务数量

**采集方法**：
- 记录活跃任务数
- 使用 Gauge 指标：`agent_concurrent_tasks{agent_name}`
- 实时采样

**告警阈值**：
- 并发数 > 10
- 接近配置上限的 80%

**可视化方案**：
- 实时仪表盘
- 时间序列热力图
- Agent 负载对比图

**分析建议**：
- 监控系统负载
- 识别峰值需求
- 优化并发控制

---

### 9. 队列长度（Queue Length）

**指标定义**：等待处理的任务队列长度

**采集方法**：
- 记录任务队列长度
- 使用 Gauge 指标：`agent_queue_length`
- 实时采样

**告警阈值**：
- 警告：队列长度 > 50
- 严重：队列长度 > 100
- 紧急：队列长度 > 200

**可视化方案**：
- 实时队列监控
- 时间序列折线图
- 排队时间分布

**分析建议**：
- 监控任务积压
- 优化调度策略
- 预警延迟风险

---

### 10. 超时次数（Timeout Count）

**指标定义**：任务执行超时的次数

**采集方法**：
- 记录超时事件
- 使用 Counter 指标：`agent_timeouts_total{task_type}`
- 实时记录

**告警阈值**：
- 超时率 > 5%
- 连续超时 > 3 次

**可视化方案**：
- 超时原因分布图
- 时间序列折线图
- 超时任务类型对比

**分析建议**：
- 识别慢任务
- 优化超时设置
- 改善任务拆分策略

---

## 四、系统监控（5 个指标）

### 1. CPU 使用率（CPU Usage）

**指标定义**：系统 CPU 占用百分比

**采集方法**：
- 使用 Node Exporter 或系统监控工具
- 使用 Gauge 指标：`system_cpu_usage_percent{mode}`
- 采样周期：10 秒

**告警阈值**：
- 警告：使用率 > 70%
- 严重：使用率 > 85%
- 紧急：使用率 > 95%

**可视化方案**：
- 使用率仪表盘
- 时间序列折线图
- 多核对比图

**分析建议**：
- 监控系统负载
- 识别 CPU 密集型进程
- 规划扩容需求

---

### 2. 内存使用率（Memory Usage）

**指标定义**：系统内存占用百分比

**采集方法**：
- 使用系统监控工具
- 使用 Gauge 指标：
  - `system_memory_usage_percent`
  - `system_memory_available_bytes`
- 采样周期：10 秒

**告警阈值**：
- 警告：使用率 > 75%
- 严重：使用率 > 85%
- 紧急：使用率 > 95%

**可视化方案**：
- 内存使用仪表盘
- 时间序列折线图
- 内存分类堆叠图

**分析建议**：
- 监控内存压力
- 识别内存泄漏
- 优化内存使用

---

### 3. 磁盘使用率（Disk Usage）

**指标定义**：磁盘空间占用百分比

**采集方法**：
- 使用系统监控工具
- 使用 Gauge 指标：`system_disk_usage_percent{device}`
- 采样周期：1 分钟

**告警阈值**：
- 警告：使用率 > 70%
- 严重：使用率 > 85%
- 紧急：使用率 > 95%

**可视化方案**：
- 磁盘使用仪表盘
- 多磁盘对比图
- 增长趋势图

**分析建议**：
- 监控磁盘容量
- 识别快速增长
- 规划清理和扩容

---

### 4. 网络流量（Network Traffic）

**指标定义**：网络带宽使用量

**采集方法**：
- 使用网络监控工具
- 使用 Counter 指标：
  - `system_network_bytes_in{interface}`
  - `system_network_bytes_out{interface}`
- 采样周期：10 秒

**告警阈值**：
- 带宽使用率 > 70%
- 异常流量增长：> 200%

**可视化方案**：
- 流量仪表盘（入/出）
- 时间序列折线图
- 接口对比图

**分析建议**：
- 监控网络负载
- 识别流量异常
- 规划带宽需求

---

### 5. 系统负载（System Load）

**指标定义**：系统平均负载（1/5/15 分钟）

**采集方法**：
- 读取系统 load average
- 使用 Gauge 指标：`system_load_average{period}`
- 采样周期：10 秒

**告警阈值**：
- 警告：1 分钟负载 > CPU 核心数 × 0.7
- 严重：1 分钟负载 > CPU 核心数 × 0.9
- 紧急：1 分钟负载 > CPU 核心数 × 1.2

**可视化方案**：
- 负载仪表盘
- 时间序列折线图（1/5/15 分钟）
- 负载趋势图

**分析建议**：
- 监控系统压力
- 预警性能问题
- 优化进程调度

---

## 五、监控面板配置

### Grafana Dashboard JSON

```json
{
  "dashboard": {
    "title": "AI System Monitoring Dashboard",
    "tags": ["ai", "llm", "rag", "agent"],
    "timezone": "browser",
    "schemaVersion": 36,
    "version": 1,
    "refresh": "30s",
    "panels": [
      {
        "id": 1,
        "title": "LLM Request Volume",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(llm_requests_total[5m])) by (model)"
          }
        ]
      },
      {
        "id": 2,
        "title": "LLM Response Time (P95)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(llm_response_time_seconds_bucket[5m])) by (le, model))"
          }
        ]
      },
      {
        "id": 3,
        "title": "LLM Token Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(llm_tokens_input_total[5m])) by (model)"
          },
          {
            "expr": "sum(rate(llm_tokens_output_total[5m])) by (model)"
          }
        ]
      },
      {
        "id": 4,
        "title": "LLM Error Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(llm_requests_total{status=\"error\"}[5m])) / sum(rate(llm_requests_total[5m])) * 100"
          }
        ]
      },
      {
        "id": 5,
        "title": "RAG Retrieval Latency (P95)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(rag_retrieval_latency_seconds_bucket[5m])) by (le))"
          }
        ]
      },
      {
        "id": 6,
        "title": "RAG Document Count",
        "type": "stat",
        "targets": [
          {
            "expr": "rag_documents_total"
          }
        ]
      },
      {
        "id": 7,
        "title": "Agent Task Completion Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(agent_tasks_total{status=\"success\"}[5m])) / sum(rate(agent_tasks_total[5m])) * 100"
          }
        ]
      },
      {
        "id": 8,
        "title": "Agent Task Duration (P95)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(agent_task_duration_seconds_bucket[5m])) by (le))"
          }
        ]
      },
      {
        "id": 9,
        "title": "System CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "system_cpu_usage_percent"
          }
        ]
      },
      {
        "id": 10,
        "title": "System Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "system_memory_usage_percent"
          }
        ]
      }
    ]
  }
}
```

### Prometheus Alert Rules

```yaml
groups:
  - name: ai_system_alerts
    interval: 30s
    rules:
      # LLM Alerts
      - alert: HighLLMErrorRate
        expr: sum(rate(llm_requests_total{status="error"}[5m])) / sum(rate(llm_requests_total[5m])) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "LLM error rate is high"
          description: "Error rate is {{ $value | humanizePercentage }} for 5 minutes"

      - alert: SlowLLMResponse
        expr: histogram_quantile(0.95, sum(rate(llm_response_time_seconds_bucket[5m])) by (le, model)) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "LLM response time is slow"
          description: "P95 response time is {{ $value }}s"

      # RAG Alerts
      - alert: HighRAGRetrievalLatency
        expr: histogram_quantile(0.95, sum(rate(rag_retrieval_latency_seconds_bucket[5m])) by (le)) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "RAG retrieval latency is high"
          description: "P95 retrieval time is {{ $value }}s"

      # Agent Alerts
      - alert: LowAgentCompletionRate
        expr: sum(rate(agent_tasks_total{status="success"}[5m])) / sum(rate(agent_tasks_total[5m])) < 0.8
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Agent completion rate is low"
          description: "Completion rate is {{ $value | humanizePercentage }}"

      # System Alerts
      - alert: HighCPUUsage
        expr: system_cpu_usage_percent > 85
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High CPU usage"
          description: "CPU usage is {{ $value }}%"

      - alert: HighMemoryUsage
        expr: system_memory_usage_percent > 85
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value }}%"
```

### 数据采集架构

```
┌─────────────────┐
│   Applications  │
│  (LLM/RAG/Agent)│
└────────┬────────┘
         │
         ├───► Metrics Exporter (Prometheus format)
         │
┌────────▼────────┐
│   Prometheus    │
│   (TSDB)        │
└────────┬────────┘
         │
         ├───► AlertManager
         │
┌────────▼────────┐
│    Grafana      │
│   (Dashboard)   │
└─────────────────┘
```

### 推荐技术栈

| 组件 | 推荐工具 |
|------|----------|
| 指标采集 | Prometheus Exporter, OpenTelemetry |
| 时序数据库 | Prometheus, InfluxDB, TimescaleDB |
| 可视化 | Grafana, Kibana |
| 告警 | AlertManager, PagerDuty |
| 日志 | ELK Stack, Loki |
| 追踪 | Jaeger, Zipkin |

### 部署清单

- [ ] 安装 Prometheus
- [ ] 配置数据采集 Exporter
- [ ] 部署 Grafana
- [ ] 导入 Dashboard 配置
- [ ] 配置 AlertManager
- [ ] 设置告警通知渠道
- [ ] 配置告警规则
- [ ] 验证指标采集
- [ ] 测试告警触发
- [ ] 文档化运维流程

---

## 附录

### 告警等级定义

- **INFO**: 信息通知，无需立即处理
- **WARNING**: 警告级别，需要关注
- **CRITICAL**: 严重级别，需要立即处理
- **EMERGENCY**: 紧急级别，需要快速响应

### 常用命令

```bash
# 查询 Prometheus 指标
curl http://localhost:9090/api/v1/query?query=llm_requests_total

# 查看当前告警
curl http://localhost:9090/api/v1/alerts

# 重载 Prometheus 配置
curl -X POST http://localhost:9090/-/reload

# 导入 Grafana Dashboard
curl -X POST http://localhost:3000/api/dashboards/db -H "Content-Type: application/json" -d @dashboard.json
```

### 参考资源

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [OpenTelemetry Specification](https://opentelemetry.io/docs/reference/specification/)
- [Observability Best Practices](https://sre.google/sre-book/monitoring-distributed-systems/)

---

**文档维护者**: 小lin  
**最后更新**: 2026-03-24
