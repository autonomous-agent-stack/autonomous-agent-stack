# AI 编程完全指南 - 代码示例库

> 配套代码示例，演示 AI 编程指南中的各种场景

---

## 目录

1. [代码生成示例](#代码生成示例)
2. [代码审查示例](#代码审查示例)
3. [代码重构示例](#代码重构示例)
4. [代码测试示例](#代码测试示例)
5. [代码优化示例](#代码优化示例)
6. [Debug 示例](#debug-示例)

---

## 代码生成示例

### 1. REST API 端点（FastAPI）

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import uvicorn

app = FastAPI(title="用户管理 API", version="1.0.0")

# 数据模型
class UserBase(BaseModel):
    name: str
    email: EmailStr
    age: Optional[int] = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    
    class Config:
        orm_mode = True

# 内存数据库（示例）
users_db: List[User] = []
user_id_counter = 1

# API 端点
@app.post("/users", response_model=User, status_code=201, tags=["用户"])
async def create_user(user: UserCreate):
    """创建新用户"""
    global user_id_counter
    user_dict = user.dict()
    user_dict["id"] = user_id_counter
    user_id_counter += 1
    users_db.append(User(**user_dict))
    return User(**user_dict)

@app.get("/users", response_model=List[User], tags=["用户"])
async def list_users(skip: int = 0, limit: int = 10):
    """获取用户列表"""
    return users_db[skip:skip + limit]

@app.get("/users/{user_id}", response_model=User, tags=["用户"])
async def get_user(user_id: int):
    """获取单个用户"""
    for user in users_db:
        if user.id == user_id:
            return user
    raise HTTPException(status_code=404, detail="用户不存在")

@app.put("/users/{user_id}", response_model=User, tags=["用户"])
async def update_user(user_id: int, user_update: UserCreate):
    """更新用户"""
    for i, user in enumerate(users_db):
        if user.id == user_id:
            users_db[i] = User(id=user_id, **user_update.dict())
            return users_db[i]
    raise HTTPException(status_code=404, detail="用户不存在")

@app.delete("/users/{user_id}", status_code=204, tags=["用户"])
async def delete_user(user_id: int):
    """删除用户"""
    for i, user in enumerate(users_db):
        if user.id == user_id:
            users_db.pop(i)
            return
    raise HTTPException(status_code=404, detail="用户不存在")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

### 2. 数据库模型（SQLAlchemy）

```python
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

# 创建基类
Base = declarative_base()

# 用户模型
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    bio = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")

# 文章模型
class Post(Base):
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    author = relationship("User", back_populates="posts")

# 初始化数据库
engine = create_engine('sqlite:///blog.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
```

---

### 3. 异步代码（aiohttp）

```python
import asyncio
import aiohttp
from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime

@dataclass
class FetchResult:
    url: str
    success: bool
    status_code: int = None
    content: str = None
    error: str = None
    duration: float = None

class AsyncFetcher:
    """异步并发请求处理器"""
    
    def __init__(self, max_concurrent: int = 10, timeout: int = 30):
        self.max_concurrent = max_concurrent
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fetch_single(self, session: aiohttp.ClientSession, url: str) -> FetchResult:
        """获取单个 URL"""
        start_time = datetime.now()
        result = FetchResult(url=url)
        
        try:
            async with self.semaphore:
                async with session.get(url, timeout=self.timeout) as response:
                    result.status_code = response.status
                    result.success = 200 <= response.status < 300
                    
                    if result.success:
                        result.content = await response.text()
                    else:
                        result.error = f"HTTP {response.status}"
        
        except asyncio.TimeoutError:
            result.error = "请求超时"
            result.success = False
        
        except Exception as e:
            result.error = str(e)
            result.success = False
        
        finally:
            result.duration = (datetime.now() - start_time).total_seconds()
        
        return result
    
    async def fetch_batch(self, urls: List[str]) -> List[FetchResult]:
        """批量获取多个 URL"""
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_single(session, url) for url in urls]
            return await asyncio.gather(*tasks)

# 使用示例
async def main():
    urls = [
        "https://api.github.com/users/github",
        "https://api.github.com/users/microsoft",
        "https://api.github.com/users/google",
    ]
    
    fetcher = AsyncFetcher(max_concurrent=3)
    results = await fetcher.fetch_batch(urls)
    
    for result in results:
        status = "✓" if result.success else "✗"
        print(f"{status} {result.url}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 4. 装饰器

```python
import functools
import time
from typing import Callable, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_execution(func: Callable) -> Callable:
    """记录函数执行的装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        start_time = time.time()
        
        logger.info(f"[调用] {func_name}")
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            logger.info(
                f"[成功] {func_name} - "
                f"执行时间: {execution_time:.4f}s"
            )
            return result
        
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"[失败] {func_name} - "
                f"执行时间: {execution_time:.4f}s, "
                f"异常: {str(e)}"
            )
            raise
    
    return wrapper

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """重试装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                
                except Exception as e:
                    if attempt == max_attempts:
                        logger.error(f"[重试失败] {func.__name__}")
                        raise
                    
                    logger.warning(f"[重试] {func.__name__} - 尝试 {attempt}/{max_attempts}")
                    time.sleep(current_delay)
                    current_delay *= backoff
        
        return wrapper
    return decorator

def cache(ttl: int = 300):
    """内存缓存装饰器"""
    cache_store = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = (func.__name__, args, frozenset(kwargs.items()))
            current_time = time.time()
            
            if key in cache_store:
                cached_value, cached_time = cache_store[key]
                if current_time - cached_time < ttl:
                    return cached_value
            
            result = func(*args, **kwargs)
            cache_store[key] = (result, current_time)
            return result
        
        wrapper.cache_clear = lambda: cache_store.clear()
        return wrapper
    
    return decorator

# 使用示例
@log_execution
@retry(max_attempts=3, delay=1.0)
@cache(ttl=60)
def fetch_data(url: str) -> dict:
    """模拟获取数据"""
    import random
    if random.random() < 0.3:
        raise ConnectionError("网络连接失败")
    
    return {"url": url, "data": "示例数据"}
```

---

### 5. CLI 工具

```python
#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

def setup_parser() -> argparse.ArgumentParser:
    """设置命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="mytool",
        description="一个强大的命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 全局参数
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="增加输出详细程度 (-v, -vv, -vvv)"
    )
    
    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="可用子命令")
    
    # process 子命令
    process_parser = subparsers.add_parser("process", help="处理数据文件")
    process_parser.add_argument("--input", type=str, required=True, help="输入文件路径")
    process_parser.add_argument("--output", type=str, required=True, help="输出文件路径")
    process_parser.add_argument("--format", choices=["json", "csv"], default="json")
    
    # analyze 子命令
    analyze_parser = subparsers.add_parser("analyze", help="分析数据文件")
    analyze_parser.add_argument("files", nargs="+", help="要分析的文件")
    analyze_parser.add_argument("--stats", action="store_true", help="显示统计信息")
    
    return parser

def process_file(input_path: str, output_path: str, format: str):
    """处理文件"""
    print(f"处理文件: {input_path}")
    
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"错误: 文件不存在: {input_path}", file=sys.stderr)
        sys.exit(1)
    
    # 处理逻辑...
    print(f"✓ 处理完成: {output_path}")

def analyze_files(files, stats: bool = False):
    """分析文件"""
    print(f"分析 {len(files)} 个文件")
    
    total_size = 0
    for file_path in files:
        path = Path(file_path)
        if path.exists():
            size = path.stat().st_size
            total_size += size
            if stats:
                print(f"  {file_path}: {size:,} bytes")
    
    print(f"\n总计: {total_size:,} bytes")

def main():
    """主函数"""
    parser = setup_parser()
    args = parser.parse_args()
    
    if args.command == "process":
        process_file(args.input, args.output, args.format)
    elif args.command == "analyze":
        analyze_files(args.files, args.stats)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## 代码审查示例

### 1. 安全漏洞对比

#### ❌ 不安全代码

```python
# SQL 注入漏洞
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)

# XSS 漏洞
def render_comment(comment):
    return f"<div>{comment}</div>"

# 硬编码敏感信息
API_KEY = "sk-1234567890abcdef"
PASSWORD = "admin123"
```

#### ✅ 安全代码

```python
# 使用参数化查询
def get_user(user_id):
    query = "SELECT * FROM users WHERE id = %s"
    return db.execute(query, (user_id,))

# 转义 HTML
from html import escape

def render_comment(comment):
    return f"<div>{escape(comment)}</div>"

# 使用环境变量
import os
API_KEY = os.getenv("API_KEY")
PASSWORD = os.getenv("PASSWORD")
```

---

### 2. 性能问题对比

#### ❌ 性能问题

```python
# N+1 查询
def get_users_with_posts():
    users = db.query("SELECT * FROM users")
    for user in users:
        user['posts'] = db.query(f"SELECT * FROM posts WHERE user_id = {user['id']}")
    return users

# 不必要的循环
def has_item(items, target):
    for item in items:
        if item == target:
            return True
    return False

# O(n) 查找
users = [{'id': 1, 'name': 'Alice'}, {'id': 2, 'name': 'Bob'}]
def find_user(user_id):
    for user in users:
        if user['id'] == user_id:
            return user
    return None
```

#### ✅ 优化后

```python
# 使用 JOIN
def get_users_with_posts():
    return db.query("""
        SELECT u.*, p.*
        FROM users u
        LEFT JOIN posts p ON u.id = p.user_id
    """)

# 使用内置函数
def has_item(items, target):
    return target in items

# O(1) 查找
users_map = {user['id']: user for user in users}
def find_user(user_id):
    return users_map.get(user_id)
```

---

## 代码重构示例

### 1. 提取方法

#### ❌ 重构前

```python
def process_order(order):
    if not order:
        return False
    if not order.get('items'):
        return False
    total = 0
    for item in order['items']:
        if item.get('price') and item.get('quantity'):
            total += item['price'] * item['quantity']
    if total <= 0:
        return False
    order['total'] = total
    order['status'] = 'processed'
    return True
```

#### ✅ 重构后

```python
def process_order(order):
    if not is_valid_order(order):
        return False
    
    order['total'] = calculate_total(order['items'])
    order['status'] = 'processed'
    return True

def is_valid_order(order):
    return order and order.get('items')

def calculate_total(items):
    return sum(
        item['price'] * item['quantity']
        for item in items
        if item.get('price') and item.get('quantity')
    )
```

---

### 2. 策略模式

#### ❌ 使用条件

```python
def process_payment(payment_type, amount):
    if payment_type == 'credit_card':
        # 信用卡逻辑
        return f"支付 ¥{amount}（信用卡）"
    elif payment_type == 'alipay':
        # 支付宝逻辑
        return f"支付 ¥{amount}（支付宝）"
    elif payment_type == 'wechat':
        # 微信逻辑
        return f"支付 ¥{amount}（微信）"
    else:
        raise ValueError("不支持的支付方式")
```

#### ✅ 策略模式

```python
from abc import ABC, abstractmethod

class PaymentStrategy(ABC):
    @abstractmethod
    def pay(self, amount: float) -> str:
        pass

class CreditCardPayment(PaymentStrategy):
    def pay(self, amount: float) -> str:
        return f"支付 ¥{amount}（信用卡）"

class AlipayPayment(PaymentStrategy):
    def pay(self, amount: float) -> str:
        return f"支付 ¥{amount}（支付宝）"

class WechatPayment(PaymentStrategy):
    def pay(self, amount: float) -> str:
        return f"支付 ¥{amount}（微信）"

class PaymentContext:
    def __init__(self, strategy: PaymentStrategy):
        self.strategy = strategy
    
    def execute_payment(self, amount: float) -> str:
        return self.strategy.pay(amount)

# 使用
context = PaymentContext(AlipayPayment())
result = context.execute_payment(100)
```

---

## 代码测试示例

### 1. 单元测试（pytest）

```python
import pytest

class Calculator:
    def add(self, a, b):
        return a + b
    
    def divide(self, a, b):
        if b == 0:
            raise ZeroDivisionError("除数不能为零")
        return a / b

class TestCalculator:
    @pytest.fixture
    def calc(self):
        return Calculator()
    
    def test_add_positive_numbers(self, calc):
        assert calc.add(2, 3) == 5
    
    def test_add_negative_numbers(self, calc):
        assert calc.add(-2, -3) == -5
    
    def test_add_zero(self, calc):
        assert calc.add(5, 0) == 5
        assert calc.add(0, 5) == 5
    
    @pytest.mark.parametrize("a,b,expected", [
        (1, 2, 3),
        (0, 0, 0),
        (-1, 1, 0),
        (100, 200, 300),
    ])
    def test_add_multiple_cases(self, calc, a, b, expected):
        assert calc.add(a, b) == expected
    
    def test_divide_positive_numbers(self, calc):
        assert calc.divide(10, 2) == 5
    
    def test_divide_by_zero_raises_error(self, calc):
        with pytest.raises(ZeroDivisionError):
            calc.divide(10, 0)
    
    def test_divide_negative_numbers(self, calc):
        assert calc.divide(-10, -2) == 5
```

---

## 代码优化示例

### 1. 算法优化

#### ❌ O(n) 查找

```python
def find_user(users, user_id):
    for user in users:
        if user['id'] == user_id:
            return user
    return None
```

#### ✅ O(1) 查找

```python
def create_user_map(users):
    return {user['id']: user for user in users}

# 使用
user_map = create_user_map(users)
user = user_map.get(user_id)
```

---

### 2. 内存优化

#### ❌ 内存密集

```python
def process_large_file(filename):
    with open(filename) as f:
        data = f.readlines()
    
    results = []
    for line in data:
        processed = line.strip().upper()
        results.append(processed)
    
    return results
```

#### ✅ 内存友好

```python
def process_large_file(filename):
    with open(filename) as f:
        for line in f:
            yield line.strip().upper()

# 使用
for result in process_large_file('large_file.txt'):
    # 逐行处理
    pass
```

---

## Debug 示例

### 1. 日志调试

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def divide(a, b):
    logger.debug(f"divide called: a={a}, b={b}")
    
    try:
        result = a / b
        logger.info(f"divide result: {result}")
        return result
    
    except ZeroDivisionError as e:
        logger.error(f"Division by zero: a={a}, b={b}", exc_info=True)
        raise
    
    except Exception as e:
        logger.critical(f"Unexpected error: {str(e)}", exc_info=True)
        raise
```

---

### 2. 异常跟踪

```python
import traceback

def risky_operation():
    try:
        # 可能失败的代码
        result = 1 / 0
        return result
    
    except ZeroDivisionError as e:
        # 记录完整的堆栈跟踪
        error_info = {
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc()
        }
        
        logger.error(f"Error occurred: {error_info}")
        raise
```

---

## 总结

本代码示例库涵盖了：

- ✅ **代码生成**（5 个示例）：REST API、数据库模型、异步代码、装饰器、CLI 工具
- ✅ **代码审查**（2 个示例）：安全漏洞对比、性能问题对比
- ✅ **代码重构**（2 个示例）：提取方法、策略模式
- ✅ **代码测试**（1 个示例）：单元测试
- ✅ **代码优化**（2 个示例）：算法优化、内存优化
- ✅ **Debug**（2 个示例）：日志调试、异常跟踪

所有示例都可以直接运行和测试！

---

**快速开始**：
```bash
# 1. 复制需要的代码示例
# 2. 根据你的需求进行调整
# 3. 运行和测试
# 4. 结合 AI 编程指南使用
```
