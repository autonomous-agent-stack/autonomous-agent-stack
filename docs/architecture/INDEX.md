# 架构设计文档快速索引

## 📚 文档列表

### 1. [单体架构](./01-monolithic-architecture.md)
**适合场景**：初创企业、MVP 产品、小型项目

**核心内容**：
- 架构图（Mermaid）
- 优势劣势对比
- 实现方案（代码示例）
- 部署方案（Docker/Kubernetes）
- 性能优化建议
- 何时演进到微服务

**关键字**：
```
#单体 #MVP #快速开发 #部署简单 #性能优异
```

---

### 2. [微服务架构](./02-microservices-architecture.md)
**适合场景**：大型系统、多团队协作、需要独立扩展

**核心内容**：
- 服务拆分策略（DDD 驱动）
- 通信机制（REST/gRPC/消息队列）
- 服务发现（Consul/Nacos/Eureka）
- 负载均衡策略
- 分布式事务（Saga/TCC）
- 部署策略（Kubernetes/灰度发布）
- 监控与可观测性

**关键字**：
```
#微服务 #服务拆分 #服务发现 #分布式事务 #Kubernetes #Consul #Saga #CQRS
```

---

### 3. [事件驱动架构](./03-event-driven-architecture.md)
**适合场景**：高并发系统、异步处理、多系统集成

**核心内容**：
- 事件核心概念
- 事件总线（Kafka/RabbitMQ）
- 事件溯源（Event Sourcing）
- CQRS 模式
- 三种事件模式
- 消息队列方案对比
- 可靠性保证

**关键字**：
```
#事件驱动 #事件溯源 #CQRS #Kafka #RabbitMQ #异步 #解耦 #最终一致性
```

---

### 4. [分层架构](./04-layered-architecture.md)
**适合场景**：大多数业务系统、长期维护项目

**核心内容**：
- 四层架构（表现/应用/领域/基础设施）
- 依赖倒置原则（DIP）
- 领域驱动设计（DDD）
- 实体、值对象、领域服务
- 领域事件
- 测试策略

**关键字**：
```
#分层架构 #DDD #领域驱动 #依赖倒置 #实体 #值对象 #领域服务 #CQRS
```

---

### 5. [管道架构](./05-pipeline-architecture.md)
**适合场景**：数据处理、CI/CD、机器学习推理

**核心内容**：
- 三种管道模式（数据/处理/部署）
- ETL/ELT 实现
- 图像处理管道
- CI/CD Pipeline
- 并行处理
- 状态持久化
- 监控与可观测性

**关键字**：
```
#管道架构 #ETL #数据处理 #CI/CD #Jenkins #Kubernetes #并行处理
```

---

## 🎯 按场景快速查找

### 初创企业 / MVP 产品
→ [单体架构](./01-monolithic-architecture.md)

### 大型电商平台（日活千万级）
→ [微服务架构](./02-microservices-architecture.md) + [事件驱动架构](./03-event-driven-architecture.md)

### 金融系统（需要完整审计）
→ [事件驱动架构](./03-event-driven-architecture.md)（事件溯源）

### 企业管理系统（ERP/CRM）
→ [分层架构](./04-layered-architecture.md)

### 数据分析平台
→ [管道架构](./05-pipeline-architecture.md)（数据管道）

### AI/ML 推理系统
→ [管道架构](./05-pipeline-architecture.md)（处理管道）

### 自动化部署系统
→ [管道架构](./05-pipeline-architecture.md)（CI/CD 管道）

### 高并发秒杀系统
→ [微服务架构](./02-microservices-architecture.md) + [事件驱动架构](./03-event-driven-architecture.md)

### 多租户 SaaS 平台
→ [微服务架构](./02-microservices-architecture.md) + [分层架构](./04-layered-architecture.md)

---

## 📊 架构对比速查表

| 维度 | 单体 | 微服务 | 事件驱动 | 分层 | 管道 |
|------|------|--------|----------|------|------|
| **复杂度** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **可扩展性** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **学习曲线** | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **适用规模** | 小型 | 大型 | 中大型 | 中型 | 中型 |
| **开发效率** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **部署难度** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **运维成本** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |

---

## 🔍 按技术栈查找

### Java Spring 技术栈
- [单体架构](./01-monolithic-architecture.md)：Spring Boot 单体应用
- [微服务架构](./02-microservices-architecture.md)：Spring Cloud 微服务
- [分层架构](./04-layered-architecture.md)：Spring MVC + Spring Data

### Python 技术栈
- [单体架构](./01-monolithic-architecture.md)：Django/Flask 单体应用
- [管道架构](./05-pipeline-architecture.md)：数据科学管道

### Go 技术栈
- [微服务架构](./02-microservices-architecture.md)：gRPC 微服务
- [事件驱动架构](./03-event-driven-architecture.md)：高性能事件处理

### 云原生技术栈
- [微服务架构](./02-microservices-architecture.md)：Kubernetes + Istio
- [管道架构](./05-pipeline-architecture.md)：Jenkins/GitLab CI

---

## 💡 常见问题快速定位

### Q: 什么时候应该从单体迁移到微服务？
**A**: 参见 [单体架构 - 何时演进到微服务](./01-monolithic-architecture.md#何时演进到微服务)

**触发条件**（满足 3+ 项）：
- ✅ 团队规模 > 20 人
- ✅ 用户规模 > 100 万
- ✅ 代码量 > 10 万行
- ✅ 部署频率 > 每周 2 次
- ✅ 单个模块需要独立扩展

---

### Q: 如何选择消息队列？
**A**: 参见 [事件驱动架构 - 消息队列方案](./03-event-driven-architecture.md#消息队列方案)

**快速选择**：
- 日志收集、实时分析 → **Kafka**
- 工作流、任务队列 → **RabbitMQ**
- 金融、电商订单 → **RocketMQ**
- 大规模多租户 → **Pulsar**

---

### Q: 如何拆分微服务？
**A**: 参见 [微服务架构 - 服务拆分策略](./02-microservices-architecture.md#服务拆分策略)

**拆分原则**：
1. 按业务能力拆分（DDD 驱动）
2. 高内聚、低耦合
3. 单一职责
4. 可以被一个小团队独立维护

---

### Q: 什么是 CQRS？什么时候使用？
**A**: 参见 [事件驱动架构 - CQRS](./03-event-driven-architecture.md#4-cqrs)

**适用场景**：
- 高并发读写
- 复杂查询场景
- 读多写少系统
- 需要查询性能优化

---

### Q: 如何设计 ETL 管道？
**A**: 参见 [管道架构 - 数据管道](./05-pipeline-architecture.md#1-数据管道-data-pipeline)

**关键步骤**：
1. Extract（提取）
2. Clean（清洗）
3. Transform（转换）
4. Validate（验证）
5. Load（加载）

---

## 🛠️ 工具与技术索引

### API 网关
- Kong
- Spring Cloud Gateway
- Nginx
- Traefik

### 服务注册与发现
- Consul
- Eureka
- Nacos
- Zookeeper

### 消息队列
- Kafka
- RabbitMQ
- RocketMQ
- ActiveMQ

### 容器编排
- Kubernetes
- Docker Swarm
- ECS (AWS)

### 链路追踪
- Jaeger
- Zipkin
- SkyWalking

### CI/CD 工具
- Jenkins
- GitLab CI
- GitHub Actions
- CircleCI

---

## 📖 学习路径建议

### 初级（1-3 个月）
1. 学习 [单体架构](./01-monolithic-architecture.md)
2. 掌握基础开发技能
3. 了解基本的部署流程

### 中级（3-6 个月）
1. 学习 [分层架构](./04-layered-architecture.md)
2. 掌握 DDD 基础
3. 学习单元测试和集成测试

### 高级（6-12 个月）
1. 学习 [微服务架构](./02-microservices-architecture.md)
2. 学习 [事件驱动架构](./03-event-driven-architecture.md)
3. 掌握分布式系统设计
4. 学习容器化和编排

### 专家（1 年+）
1. 深入学习所有架构模式
2. 掌握架构演进方法
3. 学习架构决策方法
4. 培养系统设计能力

---

## 🔗 外部资源推荐

### 经典书籍
- 《软件架构模式》- Mark Richards
- 《微服务设计》- Sam Newman
- 《领域驱动设计》- Eric Evans
- 《Building Microservices》- Sam Newman

### 在线资源
- Martin Fowler's Blog
- The AWS Architecture Center
- Microsoft Azure Architecture Center
- Google Cloud Architecture Center

### 开源项目
- Spring Cloud (微服务)
- Apache Kafka (消息队列)
- Kubernetes (容器编排)
- Apache Airflow (数据管道)

---

## 📝 文档使用建议

1. **初次阅读**：从 [总结报告](./README.md) 开始，了解各架构的适用场景
2. **深入学习**：按顺序阅读 5 个架构文档，每个文档都包含详细实现
3. **实践应用**：根据项目需求选择合适的架构，参考实现方案
4. **持续迭代**：架构是演进的，随着业务发展不断调整优化

---

**索引最后更新**：2026-03-24
**维护者**：AI 系统架构团队

如有问题或建议，请查阅具体架构文档或联系架构团队。
