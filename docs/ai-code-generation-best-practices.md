# AI 代码生成最佳实践

> 涵盖代码补全、重构建议、安全审计、性能优化和多语言支持的全面指南

## 📋 目录

- [代码补全](#代码补全)
- [重构建议](#重构建议)
- [安全审计](#安全审计)
- [性能优化](#性能优化)
- [多语言支持](#多语言支持)
- [通用原则](#通用原则)

---

## 代码补全

### 核心原则

1. **上下文感知**
   - 提供足够的代码上下文（至少 50-100 行）
   - 包含相关导入、类型定义和函数签名
   - 展示项目的编码风格和模式

2. **精确提示词**
   ```markdown
   ❌ 差："帮我写个函数"
   ✅ 好："实现一个快速排序函数，接受 int[] 并返回排序后的数组，
        时间复杂度 O(n log n)，使用原地排序"
   ```

3. **指定约束条件**
   - 语言版本（Python 3.10+，ES2022，Go 1.21）
   - 性能要求（时间/空间复杂度）
   - 依赖限制（仅使用标准库）
   - 代码风格（遵循 PEP8/Google Style）

### 实践技巧

#### 渐进式生成
```python
# 第一步：生成函数框架
def process_data(data: List[Dict]) -> List[Dict]:
    """处理输入数据，返回清洗后的结果"""
    # TODO: 实现数据清洗逻辑
    pass

# 第二步：逐步填充逻辑
# 第三步：添加错误处理
# 第四步：优化性能
```

#### 测试驱动补全
```javascript
// 先写测试
describe('calculateDiscount', () => {
  it('should apply 10% discount for members', () => {
    expect(calculateDiscount(100, true)).toBe(90);
  });
});

// 再让 AI 生成实现代码
```

### 质量检查清单

- [ ] 代码可编译/运行
- [ ] 符合项目编码规范
- [ ] 包含必要的错误处理
- [ ] 添加了适当的注释和文档
- [ ] 通过了静态代码检查（linting）

---

## 重构建议

### 识别重构时机

**代码异味（Code Smells）：**

1. **长函数**
   ```python
   # ❌ 200 行的函数
   def process_order(order):
       # ... 200 行逻辑
       pass

   # ✅ 拆分为多个小函数
   def process_order(order):
       validate_order(order)
       calculate_totals(order)
       apply_discounts(order)
       save_order(order)
   ```

2. **重复代码**
   ```javascript
   // ❌ 重复逻辑
   function calculateA(x, y) {
     return x * y * 1.1 + 10;
   }
   function calculateB(x, y) {
     return x * y * 1.1 + 20;
   }

   // ✅ 提取公共逻辑
   function calculateWithBase(x, y, base) {
     return x * y * 1.1 + base;
   }
   ```

3. **深层嵌套**
   ```java
   // ❌ 5 层嵌套
   if (condition1) {
       if (condition2) {
           if (condition3) {
               if (condition4) {
                   doSomething();
               }
           }
       }
   }

   // ✅ 提前返回
   if (!condition1) return;
   if (!condition2) return;
   if (!condition3) return;
   if (!condition4) return;
   doSomething();
   ```

### 重构策略

#### 1. 提取方法/函数
```python
# 重构前
def generate_report(data):
    # 50 行数据处理逻辑
    # 30 行格式化逻辑
    # 20 行输出逻辑
    pass

# 重构后
def generate_report(data):
    processed = process_data(data)
    formatted = format_data(processed)
    output_report(formatted)
```

#### 2. 引入参数对象
```javascript
// 重构前
function createOrder(customerId, productId, quantity,
                    shippingAddress, billingAddress, paymentMethod) {
  // ...
}

// 重构后
function createOrder(orderDetails) {
  const { customer, product, quantity, shipping, billing, payment } = orderDetails;
  // ...
}
```

#### 3. 策略模式替代条件分支
```typescript
// 重构前
function calculateBonus(employee) {
  if (employee.level === 'junior') {
    return employee.salary * 0.05;
  } else if (employee.level === 'senior') {
    return employee.salary * 0.1;
  } else if (employee.level === 'lead') {
    return employee.salary * 0.15;
  }
}

// 重构后
const bonusStrategies = {
  junior: (salary) => salary * 0.05,
  senior: (salary) => salary * 0.1,
  lead: (salary) => salary * 0.15
};

function calculateBonus(employee) {
  const strategy = bonusStrategies[employee.level];
  return strategy(employee.salary);
}
```

### AI 辅助重构提示词

```markdown
请重构以下代码，重点关注：
1. 提高可读性
2. 降低复杂度
3. 消除重复
4. 改善错误处理
5. 保持现有功能不变

原始代码：
[粘贴代码]

项目约束：
- Python 3.10+
- 遵循 PEP8
- 不使用外部依赖
```

---

## 安全审计

### 常见安全问题

#### 1. SQL 注入
```python
# ❌ 不安全
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ 安全（使用参数化查询）
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))
```

#### 2. XSS 攻击
```javascript
// ❌ 不安全
element.innerHTML = userInput;

// ✅ 安全
element.textContent = userInput;
// 或使用 DOMPurify
element.innerHTML = DOMPurify.sanitize(userInput);
```

#### 3. 命令注入
```bash
# ❌ 不安全
system("rm -rf " + user_input)

# ✅ 安全
使用白名单验证
使用专门的库代替 shell 命令
```

#### 4. 敏感信息泄露
```python
# ❌ 不安全：硬编码密钥
API_KEY = "sk-1234567890abcdef"

# ✅ 安全：使用环境变量
import os
API_KEY = os.getenv("API_KEY")
```

### 安全检查清单

```markdown
### 输入验证
- [ ] 所有用户输入都经过验证和清理
- [ ] 使用白名单而非黑名单
- [ ] 限制输入长度和格式
- [ ] 对上传文件进行类型检查

### 输出编码
- [ ] HTML 内容转义
- [ ] JSON 输出使用安全的序列化器
- [ ] SQL 使用参数化查询
- [ ] Shell 命令使用参数列表

### 认证和授权
- [ ] 密码使用 bcrypt/Argon2 加密
- [ ] 实现速率限制
- [ ] 使用 HTTPS/TLS
- [ ] 实施最小权限原则

### 依赖管理
- [ ] 定期更新依赖
- [ ] 使用工具扫描漏洞（npm audit, pip-audit）
- [ ] 锁定依赖版本
- [ ] 审查第三方库的安全性
```

### AI 安全审计提示词

```markdown
请对以下代码进行安全审计：

[粘贴代码]

检查重点：
1. SQL 注入风险
2. XSS/CSRF 漏洞
3. 命令注入风险
4. 认证/授权问题
5. 敏感信息泄露
6. 依赖安全问题

请提供：
- 风险等级（高/中/低）
- 具体问题说明
- 修复建议
- 修复后的代码示例
```

---

## 性能优化

### 性能分析流程

1. **测量先于优化**
   ```python
   import timeit

   def measure_performance():
       setup = "from module import function"
       stmt = "function(data)"
       time = timeit.timeit(stmt, setup, number=1000)
       print(f"Execution time: {time:.4f}s")
   ```

2. **识别瓶颈**
   - 使用 profiler（cProfile, Py-Spy, pprof）
   - 检查数据库查询次数
   - 分析内存使用情况

3. **优化热点**

### 常见优化技术

#### 1. 算法优化
```python
# ❌ O(n²)
def find_duplicates_naive(items):
    duplicates = []
    for i, item1 in enumerate(items):
        for item2 in items[i+1:]:
            if item1 == item2:
                duplicates.append(item1)
    return duplicates

# ✅ O(n)
def find_duplicates_optimized(items):
    seen = set()
    duplicates = set()
    for item in items:
        if item in seen:
            duplicates.add(item)
        else:
            seen.add(item)
    return list(duplicates)
```

#### 2. 缓存
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_calculation(n):
    # 耗时计算
    return result
```

#### 3. 批量操作
```javascript
// ❌ N+1 查询
for (const user of users) {
  const posts = await db.query('SELECT * FROM posts WHERE user_id = ?', [user.id]);
  user.posts = posts;
}

// ✅ 批量查询
const userIds = users.map(u => u.id);
const posts = await db.query('SELECT * FROM posts WHERE user_id IN (?)', [userIds]);
const postsByUser = groupBy(posts, 'user_id');
users.forEach(user => user.posts = postsByUser[user.id] || []);
```

#### 4. 并发处理
```go
// 并发下载
func downloadFiles(urls []string) ([]byte, error) {
    var wg sync.WaitGroup
    results := make(chan []byte, len(urls))
    
    for _, url := range urls {
        wg.Add(1)
        go func(u string) {
            defer wg.Done()
            data, _ := http.Get(u)
            results <- data
        }(url)
    }
    
    go func() {
        wg.Wait()
        close(results)
    }()
    
    // 收集结果
    var allData [][]byte
    for data := range results {
        allData = append(allData, data)
    }
    
    return bytes.Join(allData, nil), nil
}
```

### 性能优化检查清单

- [ ] 数据库查询已优化（索引、批量查询、避免 N+1）
- [ ] 缓存策略合理（内存、Redis、CDN）
- [ ] 算法复杂度合适（大数据量避免 O(n²)）
- [ ] 并发/并行处理正确使用
- [ ] 资源释放正确（连接、文件句柄、内存）
- [ ] 避免过早优化

### AI 性能优化提示词

```markdown
请优化以下代码的性能：

[粘贴代码]

当前性能问题：
- 执行时间：5.2s
- 处理数据量：100,000 条记录
- 瓶颈：数据库查询

优化目标：
- 执行时间 < 1s
- 保持功能不变
- 不增加系统复杂度

请提供：
1. 性能瓶颈分析
2. 优化方案（多种选择）
3. 优化后的代码
4. 预期性能提升
```

---

## 多语言支持

### 语言特性理解

#### Python
- 强调可读性（PEP 8）
- 使用类型注解（Python 3.6+）
- 利用列表推导、生成器
- 使用 dataclass 简化类定义

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class User:
    id: int
    name: str
    email: Optional[str] = None

def filter_active_users(users: List[User]) -> List[User]:
    return [u for u in users if u.email is not None]
```

#### JavaScript/TypeScript
- 使用现代 ES6+ 特性
- TypeScript 提供类型安全
- async/await 处理异步
- 函数式编程（map, filter, reduce）

```typescript
interface User {
  id: number;
  name: string;
  email?: string;
}

const filterActiveUsers = (users: User[]): User[] => 
  users.filter(user => user.email !== undefined);
```

#### Go
- 显式错误处理
- 使用 goroutine 实现并发
- 接口优于继承
- 避免过度设计

```go
type User struct {
    ID    int
    Name  string
    Email *string
}

func FilterActiveUsers(users []User) []User {
    var active []User
    for _, u := range users {
        if u.Email != nil {
            active = append(active, u)
        }
    }
    return active
}
```

#### Rust
- 所有权和借用
- 模式匹配
- 零成本抽象
- 无 GC 的内存安全

```rust
struct User {
    id: i32,
    name: String,
    email: Option<String>,
}

fn filter_active_users(users: Vec<User>) -> Vec<User> {
    users.into_iter()
        .filter(|u| u.email.is_some())
        .collect()
}
```

### 跨语言模式映射

| 模式 | Python | JavaScript | Go | Rust |
|------|--------|------------|-----|------|
| 可空类型 | Optional[Type] | Type \| null | \*Type | Option<Type> |
| 错误处理 | try/except | try/catch | error | Result<T, E> |
| 异步 | async/await | async/await | goroutine | async/await |
| 列表推导 | [x for x in seq] | seq.map(x => x) | for loop | iter.map() |
| 装饰器 | @decorator | 高阶函数 | 中间件 | 特征 |

### 多语言项目最佳实践

#### 1. 共享数据格式
- 使用 JSON/Protocol Buffers/Thrift
- 定义统一的 schema
- 生成各语言的类型定义

#### 2. API 规范
- OpenAPI/Swagger
- GraphQL schema
- 版本化管理

#### 3. CI/CD
- 统一的代码检查工具
- 多语言测试
- 容器化部署

### AI 多语言提示词

```markdown
请将以下 Python 代码转换为 [目标语言]：

[粘贴 Python 代码]

转换要求：
1. 保持功能不变
2. 使用目标语言的惯用写法（idiomatic）
3. 添加必要的类型定义
4. 包含错误处理
5. 添加代码注释

目标语言：[JavaScript/TypeScript/Go/Rust]
语言版本：[例如：ES2022, Go 1.21]
```

---

## 通用原则

### 1. 可读性 > 聪明代码

```python
# ❌ 过于 clever
def calculate(a, b, c):
    return (a * b) >> 2 if c else (a | b) ^ 0xFF

# ✅ 清晰明确
def calculate_discount(price, quantity, is_member):
    if is_member:
        return price * quantity * 0.75  # 25% 折扣
    else:
        return price * quantity * 0.95  # 5% 折扣
```

### 2. 测试优先

- 为生成的代码编写测试
- 测试覆盖边界情况
- 使用 TDD 或 BDD 方法

### 3. 文档完善

```python
def process_user_data(user: User) -> ProcessedUser:
    """
    处理用户数据，生成标准化输出。
    
    Args:
        user: 原始用户对象
        
    Returns:
        ProcessedUser: 处理后的用户数据
        
    Raises:
        ValueError: 当用户数据无效时
        UserNotFoundError: 当用户不存在时
        
    Examples:
        >>> user = User(id=1, name="Alice")
        >>> process_user_data(user)
        ProcessedUser(id=1, name="Alice", status="active")
    """
    pass
```

### 4. 持续改进

- 代码审查（Code Review）
- 定期重构
- 收集反馈并迭代
- 关注性能和安全更新

---

## 工具推荐

### 代码质量
- **Python**: pylint, mypy, black
- **JavaScript/TS**: ESLint, Prettier, TypeScript
- **Go**: gofmt, golint, staticcheck
- **Rust**: clippy, rustfmt

### 安全扫描
- **通用**: Snyk, Dependabot, OWASP Dependency Check
- **语言特定**: pip-audit (Python), npm audit (JavaScript)

### 性能分析
- **Python**: cProfile, Py-Spy
- **Node**: Clinic.js, 0x
- **Go**: pprof, go tool trace
- **Rust**: flamegraph, criterion

### 测试
- **Python**: pytest, unittest
- **JavaScript**: Jest, Mocha
- **Go**: testing package
- **Rust**: cargo test

---

## 总结

AI 辅助代码生成是强大的生产力工具，但需要遵循以下原则：

1. **人工审查不可或缺** - AI 生成的代码必须经过人工检查
2. **测试先行** - 为生成的代码编写充分的测试
3. **上下文关键** - 提供清晰、详细的提示词和上下文
4. **渐进式使用** - 从简单任务开始，逐步增加复杂度
5. **持续学习** - 了解最佳实践，提升提示词质量

记住：AI 是助手，不是替代品。最终的代码质量取决于工程师的专业素养和判断。

---

## 参考资源

- [Clean Code](https://www.amazon.com/Clean-Code-Handbook-Software-Craftsmanship/dp/0132350882) - Robert C. Martin
- [Refactoring](https://refactoring.com/) - Martin Fowler
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [The Pragmatic Programmer](https://pragprog.com/titles/tpp20/) - David Thomas, Andrew Hunt
- 各语言官方文档和最佳实践指南
