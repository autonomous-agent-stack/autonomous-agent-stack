# AI 编程完全指南 v2

> 100 个实战场景与 Prompt 模板，让你的 AI 编程效率提升 10 倍

---

## 📑 目录

1. [代码生成（20 种场景）](#代码生成)
2. [代码审查（15 种检查）](#代码审查)
3. [代码重构（15 种技巧）](#代码重构)
4. [代码测试（15 种方法）](#代码测试)
5. [代码优化（15 种技巧）](#代码优化)
6. [Debug 技巧（20 种方法）](#debug-技巧)

---

## 🎯 使用指南

### Prompt 通用模板

```
角色：{你希望AI扮演的角色}
任务：{具体要完成的任务}
输入：{输入信息}
输出：{期望的输出格式}
约束：{限制条件和要求}
示例：{示例输入和输出}
```

### 最佳实践

1. **明确需求**：清楚描述问题和期望
2. **提供上下文**：给出完整的信息和示例
3. **迭代改进**：逐步优化和完善
4. **学习最佳实践**：遵循行业标准和规范
5. **持续学习**：跟上技术发展和工具演进

---

## 💻 代码生成（20 种场景）

### 1. 从零生成完整项目

**Prompt**：
```
创建一个 {项目类型} 项目，要求：
- 技术栈：{具体技术栈}
- 核心功能：{功能列表}
- 项目结构：遵循 {架构模式} 最佳实践
- 包含：README.md、配置文件、示例代码、单元测试框架
- 代码规范：遵循 {编码规范}
```

**最佳实践**：明确指定项目类型和技术栈，列出核心功能优先级

---

### 2. 生成 REST API 端点

**Prompt**：
```
生成 {语言/框架} 的 REST API 端点：
- 资源：{资源名称}
- 操作：CRUD（增删改查）
- 数据模型：{字段定义}
- 认证方式：{JWT/OAuth/API Key}
- 验证规则：{输入验证要求}
- 错误处理：标准 HTTP 状态码
```

**示例**：
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class User(BaseModel):
    id: int
    name: str
    email: str

@app.post("/users", response_model=User, status_code=201)
def create_user(user: User):
    # 实现逻辑
    pass
```

---

### 3. 数据库模型生成

**Prompt**：
```
生成 {数据库/ORM} 模型：
- 表名：{表名}
- 字段：{字段列表及类型}
- 关系：{表关系}
- 索引：{索引字段}
- 约束：{主键/外键/唯一约束}
```

---

### 4. 算法实现

**Prompt**：
```
实现 {算法名称}：
- 输入：{输入格式}
- 输出：{输出格式}
- 时间复杂度：O({复杂度})
- 包含：详细注释、测试用例
```

---

### 5-20. 其他生成场景

5. **数据处理脚本** - 数据转换、清洗、验证
6. **正则表达式生成** - 模式匹配、验证
7. **并发/异步代码** - 多线程、协程、异步 I/O
8. **装饰器/中间件** - 日志、认证、缓存、限流
9. **CLI 工具** - 命令行参数解析、子命令
10. **单元测试** - pytest、JUnit、测试用例生成
11. **API 客户端** - REST API、GraphQL、WebSocket
12. **WebSocket 服务** - 实时通信、消息广播
13. **GraphQL 解析器** - Schema、Resolver、关联查询
14. **消息队列消费者** - RabbitMQ、Kafka、Redis
15. **定时任务** - Cron、调度器、任务管理
16. **配置管理** - 多环境配置、热更新
17. **日志系统** - 结构化日志、日志轮转
18. **监控指标** - Prometheus、StatsD、自定义指标
19. **文件上传下载** - 分片上传、断点续传
20. **数据验证** - Pydantic、JSON Schema、自定义验证

---

## 🔍 代码审查（15 种检查）

### 1. 安全漏洞检查

**Prompt**：
```
检查以下代码的安全问题：
- SQL 注入
- XSS 攻击
- CSRF 漏洞
- 敏感信息泄露
- 不安全的随机数
- 依赖漏洞
```

**示例**：
```python
# ❌ 不安全
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ 安全
query = "SELECT * FROM users WHERE id = %s"
db.execute(query, (user_id,))
```

**最佳实践**：
- 使用参数化查询
- 验证和清理输入
- 加密敏感数据
- 定期更新依赖

---

### 2-15. 其他审查检查

2. **性能问题检查** - N+1 查询、内存泄漏、算法复杂度
3. **代码风格一致性** - 命名规范、缩进风格、行长度
4. **错误处理** - 异常捕获、错误消息、错误传播
5. **资源管理** - 文件关闭、连接释放、内存释放
6. **并发安全** - 竞态条件、死锁风险、线程安全
7. **可测试性** - 依赖注入、接口抽象、Mock 友好
8. **可维护性** - 代码复杂度、职责分离、模块化
9. **文档完整性** - 函数文档、注释质量、API 文档
10. **边界条件处理** - 空值处理、极限值、异常输入
11. **异常处理** - 具体异常捕获、异常链保持、finally 使用
12. **日志记录** - 日志级别、敏感信息过滤、结构化日志
13. **配置管理** - 硬编码消除、环境变量、配置保护
14. **API 设计** - RESTful 规范、版本控制、错误响应
15. **数据验证** - 输入验证、类型检查、长度限制

---

## 🔧 代码重构（15 种技巧）

### 1. 提取方法

**Prompt**：
```
重构以下代码：
- 提取独立功能为单独方法
- 每个方法只做一件事
- 方法名清晰表达意图
```

**示例**：
```python
# ❌ 重构前
def process_order(order):
    if not order or not order.get('items'):
        return False
    total = sum(item['price'] * item['quantity'] for item in order['items'])
    order['total'] = total
    order['status'] = 'processed'
    return True

# ✅ 重构后
def process_order(order):
    if not is_valid_order(order):
        return False
    order['total'] = calculate_total(order['items'])
    order['status'] = 'processed'
    return True

def is_valid_order(order):
    return order and order.get('items')

def calculate_total(items):
    return sum(item['price'] * item['quantity'] for item in items)
```

**最佳实践**：
- 保持方法简短（< 20 行）
- 单一职责原则
- 使用有意义的命名
- 减少参数数量

---

### 2. 引入设计模式

**Prompt**：
```
使用 {设计模式} 重构代码：
- 当前问题：{描述问题}
- 模式选择：{设计模式名称}
- 期望改进：{改进目标}
```

**示例（策略模式）**：
```python
from abc import ABC, abstractmethod

class PaymentStrategy(ABC):
    @abstractmethod
    def pay(self, amount):
        pass

class CreditCardPayment(PaymentStrategy):
    def pay(self, amount):
        return f"支付 ¥{amount}（信用卡）"

class PaymentContext:
    def __init__(self, strategy: PaymentStrategy):
        self.strategy = strategy
    
    def execute_payment(self, amount):
        return self.strategy.pay(amount)
```

---

### 3-15. 其他重构技巧

3. **移除重复代码** - 提取公共逻辑、创建共享方法
4. **简化条件表达式** - 提前返回、合并条件、使用三元运算符
5. **引入对象** - 创建数据类、封装相关行为
6. **分解复杂条件** - 提取条件为方法、使用解释性变量
7. **用多态替代条件** - 创建抽象基类、实现具体子类
8. **提取接口/抽象类** - 识别共同行为、定义抽象接口
9. **分离数据和行为** - 数据结构类、行为处理类
10. **封装集合** - 提供访问方法、添加验证逻辑
11. **用工厂方法替代构造函数** - 创建工厂类、封装创建逻辑
12. **用命令模式替代回调** - 创建命令对象、支持撤销/重做
13. **用状态模式替代状态变量** - 定义状态接口、状态转换
14. **用访问者模式替代类型检查** - 分离数据结构和操作
15. **重命名简化** - 使用有意义的名称、避免缩写

---

## 🧪 代码测试（15 种方法）

### 1. 单元测试

**Prompt**：
```
为以下代码生成单元测试：
- 测试框架：{pytest/JUnit}
- 覆盖率目标：{90%+}
- 包含：正常、边界、异常情况
```

**示例**：
```python
import pytest

def add(a, b):
    return a + b

class TestAdd:
    def test_add_positive_numbers(self):
        assert add(2, 3) == 5
    
    def test_add_negative_numbers(self):
        assert add(-2, -3) == -5
    
    @pytest.mark.parametrize("a,b,expected", [
        (1, 2, 3),
        (0, 0, 0),
        (-1, 1, 0),
    ])
    def test_add_multiple_cases(self, a, b, expected):
        assert add(a, b) == expected
```

**最佳实践**：
- 遵循 AAA 模式（Arrange-Act-Assert）
- 使用描述性的测试名称
- 保持测试独立性
- 使用 mocks 和 stubs

---

### 2-15. 其他测试方法

2. **集成测试** - 组件交互、测试数据库、端到端流程
3. **端到端测试** - 用户场景、UI 自动化、完整流程
4. **性能测试** - 响应时间、吞吐量、资源使用
5. **负载测试** - 并发用户、持续压力、资源监控
6. **安全测试** - SQL 注入、XSS、CSRF、认证测试
7. **兼容性测试** - 浏览器、操作系统、设备、API 版本
8. **用户界面测试** - 页面元素、交互流程、响应式布局
9. **A/B 测试** - 变体设计、指标定义、流量分配
10. **混沌测试** - 故障注入、资源限制、恢复验证
11. **契约测试** - API 契约、消费者测试、提供者验证
12. **视觉回归测试** - 页面截图、差异对比、基线管理
13. **API 测试** - 端点覆盖、请求验证、响应断言
14. **数据库测试** - Schema 验证、数据完整性、事务测试
15. **并发测试** - 竞态条件、死锁检测、线程安全

---

## ⚡ 代码优化（15 种技巧）

### 1. 算法优化

**Prompt**：
```
优化以下代码性能：
- 当前复杂度：O({n})
- 目标复杂度：O({log n})
- 优化策略：{具体策略}
```

**示例**：
```python
# ❌ O(n) 查找
def find_item(items, target_id):
    for item in items:
        if item['id'] == target_id:
            return item
    return None

# ✅ O(1) 查找
def find_item(items, target_id):
    item_map = {item['id']: item for item in items}
    return item_map.get(target_id)
```

**最佳实践**：
- 分析时间复杂度
- 使用合适的数据结构
- 避免嵌套循环
- 使用缓存

---

### 2. 内存优化

**Prompt**：
```
优化内存使用：
- 减少对象创建
- 使用生成器替代列表
- 及时释放资源
```

**示例**：
```python
# ❌ 内存密集
def process_large_file(filename):
    with open(filename) as f:
        data = f.readlines()  # 全部加载
    return [line.strip() for line in data]

# ✅ 内存友好
def process_large_file(filename):
    with open(filename) as f:
        for line in f:  # 逐行处理
            yield line.strip()
```

---

### 3-15. 其他优化技巧

3. **数据库查询优化** - 添加索引、避免 N+1、批量操作
4. **缓存策略** - 内存缓存、Redis、失效策略、缓存预热
5. **并发优化** - 连接池、线程池、异步 I/O、批处理
6. **I/O 优化** - 批量读写、异步 I/O、缓冲优化、零拷贝
7. **网络请求优化** - 连接复用、请求合并、压缩传输、CDN
8. **字符串操作优化** - StringBuilder、避免频繁拼接
9. **循环优化** - 减少循环内计算、循环展开、向量化
10. **递归转迭代** - 使用栈模拟、尾递归优化、动态规划
11. **批处理** - 批量大小、超时控制、错误处理
12. **惰性求值** - 生成器、延迟加载、按需计算
13. **对象池化** - 池大小管理、对象复用、泄漏检测
14. **连接池** - 最小/最大连接数、连接超时、健康检查
15. **资源复用** - 单例模式、对象缓存、资源共享

---

## 🐛 Debug 技巧（20 种方法）

### 1. 日志调试

**Prompt**：
```
添加调试日志：
- 记录关键变量
- 记录函数入口/出口
- 记录异常堆栈
- 使用日志级别
```

**示例**：
```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def divide(a, b):
    logger.debug(f"divide called: a={a}, b={b}")
    try:
        result = a / b
        logger.info(f"divide result: {result}")
        return result
    except ZeroDivisionError as e:
        logger.error(f"Division by zero", exc_info=True)
        raise
```

**最佳实践**：
- 使用合适的日志级别
- 包含上下文信息
- 避免记录敏感信息
- 使用结构化日志

---

### 2-20. 其他调试技巧

2. **断点调试** - 条件断点、日志断点、异常断点
3. **异常跟踪** - 捕获完整堆栈、记录上下文、错误报告
4. **内存分析** - 内存泄漏检测、对象引用分析、堆转储
5. **性能分析** - CPU 采样、函数耗时、热路径分析
6. **网络抓包** - Wireshark、请求/响应分析、协议解析
7. **单元测试调试** - 隔离失败测试、查看失败原因
8. **打印调试** - 关键变量输出、执行流程标记、条件打印
9. **二分法定位** - 注释/启用代码、缩小问题范围
10. **增量调试** - 小步提交、每步验证、快速回退
11. **假设验证** - 提出假设、设计验证、收集证据
12. **状态检查** - 变量值、对象状态、系统资源
13. **依赖分析** - 依赖图、版本冲突、循环依赖
14. **版本控制回滚** - Git bisect、历史对比、变更回退
15. **A/B 调试** - 对照实验、变量控制、结果对比
16. **远程调试** - 远程调试器、端口转发、日志收集
17. **生产调试** - 生产环境调试、日志聚合、实时监控
18. **日志聚合** - ELK Stack、Splunk、日志分析
19. **监控告警** - Prometheus、Grafana、自定义告警
20. **错误追踪** - Sentry、Bugsnag、错误报告分析

---

## 📚 附录

### 快速参考清单

#### 代码审查清单

- [ ] 代码符合项目规范
- [ ] 没有安全漏洞
- [ ] 错误处理完善
- [ ] 性能可接受
- [ ] 测试覆盖充分
- [ ] 文档清晰完整
- [ ] 没有硬编码配置
- [ ] 资源正确释放
- [ ] 日志记录合理
- [ ] 可维护性良好

#### 性能优化检查点

- [ ] 数据库查询优化
- [ ] 缓存策略实施
- [ ] 算法复杂度合理
- [ ] 内存使用优化
- [ ] 并发处理正确
- [ ] I/O 操作高效
- [ ] 网络请求优化
- [ ] 资源池化使用
- [ ] 延迟加载实施
- [ ] 批处理策略

#### 常用设计模式

- **创建型**：单例、工厂、建造者、原型
- **结构型**：适配器、桥接、组合、装饰器、外观、代理
- **行为型**：策略、观察者、命令、状态、模板方法、责任链

---

## 🎓 学习资源

### 推荐工具

- **代码生成**：GitHub Copilot、Cursor、ChatGPT
- **代码审查**：SonarQube、CodeClimate、ESLint
- **代码测试**：pytest、JUnit、Jest、Cypress
- **性能分析**：cProfile、py-spy、FlameGraph
- **调试工具**：pdb、Chrome DevTools、Wireshark

### 进阶阅读

- 《代码整洁之道》- Robert C. Martin
- 《重构：改善既有代码的设计》- Martin Fowler
- 《设计模式：可复用面向对象软件的基础》- GoF
- 《单元测试的艺术》- Roy Osherove

---

## 📝 总结

本指南涵盖了 **100 个 AI 编程实战场景**，包括：

- ✅ **代码生成**（20 种场景）：从项目搭建到特定功能实现
- ✅ **代码审查**（15 种检查）：确保代码质量和安全
- ✅ **代码重构**（15 种技巧）：改善代码结构和可维护性
- ✅ **代码测试**（15 种方法）：全面覆盖测试类型
- ✅ **代码优化**（15 种技巧）：提升性能和效率
- ✅ **Debug 技巧**（20 种方法）：快速定位和解决问题

### 使用建议

1. 将本指南作为参考手册，根据具体需求查找对应场景
2. 结合实际项目调整和定制 Prompt 模板
3. 建立自己的 Prompt 库，积累经验
4. 定期回顾和更新，保持内容时效性

---

**版本**：v2.0  
**更新日期**：2026-03-24  
**许可证**：MIT

---

## 🚀 快速开始

```bash
# 1. 选择你需要的场景（如：生成 REST API）
# 2. 复制对应的 Prompt 模板
# 3. 填写你的具体需求
# 4. 发送给 AI 助手
# 5. 根据生成的代码进行调整和优化
```

**祝你编程愉快！🎉**
