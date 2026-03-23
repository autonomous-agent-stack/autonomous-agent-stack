# Python代码规范指南 📐

> 良好的代码规范是专业开发者的必备素质

## 目录

- [为什么需要代码规范](#为什么需要代码规范)
- [PEP 8 基础规范](#pep-8-基础规范)
- [命名规范](#命名规范)
- [代码组织](#代码组织)
- [注释规范](#注释规范)
- [文档字符串](#文档字符串)
- [错误处理](#错误处理)
- [最佳实践](#最佳实践)

---

## 为什么需要代码规范

### 🎯 代码规范的重要性

1. **可读性** - 让自己和他人容易理解代码
2. **可维护性** - 方便后续修改和扩展
3. **协作性** - 团队开发时保持一致性
4. **专业性** - 体现开发者的职业素养
5. **减少错误** - 规范的代码通常更安全

### 💡 基本原则

- **代码是写给人看的，顺便能在机器上运行**
- **一致性比个人偏好更重要**
- **清晰优于简洁**
- **简单优于复杂**

---

## PEP 8 基础规范

PEP 8是Python官方的代码风格指南，是Python社区广泛遵循的标准。

### 缩进

**使用4个空格缩进，不要使用Tab**

```python
# ✅ 正确
def function():
    if condition:
        do_something()
        do_another()

# ❌ 错误 - 使用Tab
def function():
	if condition:
		do_something()
		do_another()

# ❌ 错误 - 混用空格和Tab
def function():
    	if condition:
            	do_something()
```

### 行长度

**每行不超过79个字符**

```python
# ✅ 正确 - 适当换行
result = some_function_with_long_name(
    argument1,
    argument2,
    argument3
)

# ✅ 正确 - 使用括号
long_string = (
    "这是一个非常长的字符串，"
    "需要在合适的位置换行"
)

# ❌ 错误 - 行太长
result = some_function_with_long_name(argument1, argument2, argument3, argument4, argument5)
```

### 空格使用

#### 运算符周围

```python
# ✅ 正确 - 二元运算符两侧加空格
x = 1 + 2
y = 3 * 4
z = 5 / 6

# ✅ 正确 - 一元运算符不加空格
x = -1
y = +2
z = ~3

# ❌ 错误
x=1+2
y=3*4
```

#### 逗号后

```python
# ✅ 正确 - 逗号后加空格
my_list = [1, 2, 3, 4, 5]
my_dict = {'a': 1, 'b': 2, 'c': 3}

# ❌ 错误
my_list = [1,2,3,4,5]
my_dict = {'a':1,'b':2,'c':3}
```

#### 括号内

```python
# ✅ 正确 - 括号内不加多余空格
my_list = [1, 2, 3]
my_tuple = (1, 2, 3)
my_dict = {'key': 'value'}
my_func(1, 2, 3)

# ❌ 错误 - 多余空格
my_list = [ 1, 2, 3 ]
my_tuple = ( 1, 2, 3 )
my_func( 1, 2, 3 )
```

#### 冒号使用

```python
# ✅ 正确 - 冒号前不加空格，后加空格（除了切片）
if condition:
    do_something()

for i in range(10):
    print(i)

# 切片：冒号两侧不加空格
my_list[1:5]
my_list[:5]
my_list[5:]

# ❌ 错误
if condition :
    do_something()
my_list[1 : 5]
```

### 空行使用

```python
# ✅ 正确 - 顶层函数/类之间空两行
def function_one():
    pass


def function_two():
    pass


class MyClass:
    def method_one(self):
        pass

    # ✅ 正确 - 类内方法之间空一行
    def method_two(self):
        pass


# ✅ 正确 - 函数内部逻辑块之间可空一行
def complex_function():
    # 第一步：初始化
    data = initialize_data()

    # 第二步：处理数据
    result = process(data)

    # 第三步：返回结果
    return result
```

---

## 命名规范

### 变量命名

#### 基本规则

- 使用小写字母
- 单词之间用下划线连接
- 使用有意义的名称
- 避免使用单字符（除循环变量）

```python
# ✅ 正确
user_name = "张三"
total_amount = 1000
student_age = 20
is_valid = True
item_count = 5

# ❌ 错误
userName = "张三"  # 应使用下划线
x = 1000  # 无意义
n = 20  # 无意义
flag = True  # 应使用 is_valid
cnt = 5  # 应写完整
```

#### 特定前缀

```python
# ✅ 布尔值使用 is_/has_/can_ 前缀
is_active = True
has_permission = False
can_edit = True

# ✅ 私有变量使用单下划线前缀
_internal_data = "内部数据"
_helper_function = "辅助函数"

# ✅ 避免魔法变量
# ❌ 错误
if user_score > 90:
    print("优秀")

# ✅ 正确
EXCELLENT_SCORE = 90
if user_score > EXCELLENT_SCORE:
    print("优秀")
```

### 函数命名

```python
# ✅ 正确 - 小写字母 + 下划线
def get_user_info(user_id):
    pass

def calculate_average(numbers):
    pass

def send_email(to_email, subject):
    pass

# ❌ 错误
def getUserInfo(user_id):  # 应使用小写
def CalculateAverage(numbers):  # 应使用小写
```

### 类命名

```python
# ✅ 正确 - 驼峰命名法
class UserProfile:
    pass

class DataAnalyzer:
    pass

class EmailSender:
    pass

# ❌ 错误
class user_profile:  # 应使用驼峰
class data_analyzer:  # 应使用驼峰
```

### 常量命名

```python
# ✅ 正确 - 全大写 + 下划线
MAX_CONNECTIONS = 100
DEFAULT_TIMEOUT = 30
API_KEY = "your_api_key"
DATABASE_URL = "postgresql://..."

# ❌ 错误
max_connections = 100  # 常量应全大写
MaxConnections = 100  # 类命名方式
```

### 模块和包命名

```python
# ✅ 正确 - 小写字母 + 下划线
# 文件名：user_profile.py
import user_profile

# 文件名：data_processor.py
from data_processor import DataProcessor

# 包名：my_package/
# ✅ 正确 - 短小、小写、避免下划线
# ❌ 错误 - 过长或特殊字符
```

---

## 代码组织

### 导入顺序

按照以下顺序导入，并用空行分隔：

1. 标准库导入
2. 第三方库导入
3. 本地应用/库导入

```python
# ✅ 正确
# 标准库
import os
import sys
from datetime import datetime

# 第三方库
import requests
from flask import Flask, render_template

# 本地导入
from utils import helper_function
from models import User
```

### 文件结构

```python
"""
文件文档字符串
"""

# 1. 导入语句
import os
import sys

# 2. 常量定义
MAX_SIZE = 100
DEFAULT_TIMEOUT = 30

# 3. 异常类定义
class CustomError(Exception):
    pass

# 4. 类定义
class MyClass:
    def __init__(self):
        pass

    def method_one(self):
        pass

# 5. 函数定义
def function_one():
    pass

# 6. 主程序
if __name__ == "__main__":
    main()
```

---

## 注释规范

### 何时使用注释

```python
# ✅ 需要注释的情况：
# 1. 解释"为什么"，而不是"是什么"
# 2. 标记待完成的工作（TODO）
# 3. 说明复杂的算法或逻辑
# 4. 标记已知问题或限制

# ❌ 不需要注释的情况：
# 1. 显而易见的代码
# 2. 注释比代码还难懂
# 3. 过时的注释
```

### 单行注释

```python
# ✅ 正确 - 注释与代码同行，空格分隔
age = 25  # 用户年龄

# ✅ 正确 - 注释在代码上方
# 计算折扣后的价格
discounted_price = original_price * (1 - discount_rate)

# ❌ 错误 - 注释没有空格
age=25 # 用户年龄

# ❌ 错误 - 无意义的注释
age = 25  # 赋值age为25
```

### 多行注释

```python
# ✅ 正确 - 每行都以#开头
# 这是一个复杂的多行注释
# 用于解释某个算法的工作原理
# 需要详细说明每个步骤
result = complex_algorithm()

# ✅ 正确 - 使用三引号作为文档字符串
"""
这个函数实现了快速排序算法
时间复杂度：O(n log n)
空间复杂度：O(log n)
"""
def quick_sort(arr):
    pass
```

### 特殊标记注释

```python
# ✅ 常用特殊标记

# TODO: 需要完成的任务
# FIXME: 需要修复的问题
# HACK: 临时的解决方案
# NOTE: 特别注意事项
# WARNING: 警告信息
# XXX: 问题代码或需要审查

# 示例
def process_data(data):
    # TODO: 添加数据验证
    # FIXME: 这里有个性能问题
    # HACK: 临时使用，需要重构
    return data
```

---

## 文档字符串

文档字符串（docstring）是Python中用于记录函数、类、模块说明的特殊字符串。

### 函数文档字符串

```python
# ✅ 正确 - Google风格
def calculate_rectangle_area(length, width):
    """计算矩形面积。

    Args:
        length (float): 矩形的长度
        width (float): 矩形的宽度

    Returns:
        float: 矩形的面积

    Raises:
        ValueError: 当长度或宽度为负数时

    Examples:
        >>> calculate_rectangle_area(5, 3)
        15
    """
    if length < 0 or width < 0:
        raise ValueError("长度和宽度必须为正数")
    return length * width
```

### 类文档字符串

```python
# ✅ 正确
class User:
    """用户类。

    用于存储和管理用户信息。

    Attributes:
        name (str): 用户姓名
        email (str): 用户邮箱
        age (int): 用户年龄
    """

    def __init__(self, name, email, age):
        """初始化用户对象。

        Args:
            name (str): 用户姓名
            email (str): 用户邮箱
            age (int): 用户年龄
        """
        self.name = name
        self.email = email
        self.age = age
```

### 模块文档字符串

```python
"""
用户管理模块。

提供用户创建、查询、更新、删除等功能。

Typical usage:
    >>> from user_manager import UserManager
    >>> manager = UserManager()
    >>> user = manager.create_user("张三", "zhang@example.com")
"""

import sqlite3
from typing import Optional
```

---

## 错误处理

### 异常捕获

```python
# ✅ 正确 - 捕获特定异常
try:
    result = 10 / 0
except ZeroDivisionError as e:
    print(f"除零错误：{e}")

# ✅ 正确 - 捕获多个异常
try:
    file = open("nonexistent.txt", "r")
    content = file.read()
except (FileNotFoundError, PermissionError) as e:
    print(f"文件操作失败：{e}")

# ❌ 错误 - 捕获所有异常（除非必要）
try:
    some_code()
except Exception:  # 过于宽泛
    pass

# ✅ 正确 - 使用finally清理资源
try:
    file = open("data.txt", "r")
    content = file.read()
except FileNotFoundError:
    print("文件不存在")
finally:
    if 'file' in locals():
        file.close()
```

### 自定义异常

```python
# ✅ 正确 - 定义清晰的异常类
class InvalidEmailError(Exception):
    """无效的邮箱地址异常"""
    pass


class InsufficientFundsError(Exception):
    """余额不足异常"""
    pass


def validate_email(email):
    """验证邮箱格式"""
    if '@' not in email:
        raise InvalidEmailError("邮箱地址必须包含@符号")
    return True
```

---

## 最佳实践

### 使用with语句

```python
# ✅ 正确 - 使用with语句自动管理资源
with open("file.txt", "r", encoding="utf-8") as f:
    content = f.read()
# 文件自动关闭

# ❌ 错误 - 需要手动关闭
f = open("file.txt", "r", encoding="utf-8")
content = f.read()
f.close()  # 可能忘记关闭
```

### 使用列表推导式

```python
# ✅ 正确 - 简洁清晰
numbers = [1, 2, 3, 4, 5]
squares = [x**2 for x in numbers]

# ✅ 正确 - 带条件
even_numbers = [x for x in numbers if x % 2 == 0]

# ❌ 错误 - 过于复杂，可读性差
# result = [x for x in range(100) if x % 2 == 0 and x > 50 and x < 75]
```

### 避免魔法数字

```python
# ❌ 错误
if user_age < 18:
    print("未成年")

# ✅ 正确
ADULT_AGE = 18
if user_age < ADULT_AGE:
    print("未成年")
```

### 函数单一职责

```python
# ❌ 错误 - 函数做太多事情
def process_user_data(data):
    # 读取数据
    # 验证数据
    # 处理数据
    # 保存数据
    # 发送邮件
    pass

# ✅ 正确 - 拆分成多个函数
def validate_user_data(data):
    """验证用户数据"""
    pass


def process_user_data(data):
    """处理用户数据"""
    pass


def save_user_data(data):
    """保存用户数据"""
    pass


def main(data):
    """主流程"""
    if validate_user_data(data):
        processed = process_user_data(data)
        save_user_data(processed)
```

### 使用类型提示

```python
# ✅ 正确 - 使用类型提示提高代码可读性
from typing import List, Optional, Dict


def calculate_average(numbers: List[float]) -> float:
    """计算平均值"""
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)


def find_user(user_id: int) -> Optional[Dict]:
    """查找用户"""
    # 返回用户字典或None
    pass
```

---

## 代码审查清单

在提交代码前，使用这个清单检查：

### ✅ 基本检查
- [ ] 代码符合PEP 8规范
- [ ] 所有函数都有文档字符串
- [ ] 变量和函数命名清晰有意义
- [ ] 没有未使用的导入
- [ ] 没有硬编码的魔法数字

### ✅ 功能检查
- [ ] 代码实现了预期功能
- [ ] 边界情况已处理
- [ ] 错误处理完善
- [ ] 没有明显的性能问题

### ✅ 测试检查
- [ ] 有适当的测试用例
- [ ] 测试覆盖主要功能
- [ ] 所有测试通过

### ✅ 安全检查
- [ ] 没有敏感信息泄露（密码、密钥）
- [ ] 输入数据已验证
- [ ] 没有SQL注入风险
- [ ] 没有XSS风险（Web应用）

---

## 工具推荐

### 代码格式化工具

```bash
# 安装black - Python代码格式化工具
pip install black

# 格式化文件
black your_file.py

# 格式化整个项目
black your_project/

# 检查格式但不修改
black --check your_file.py
```

### 代码检查工具

```bash
# 安装pylint - 代码质量检查工具
pip install pylint

# 检查代码
pylint your_file.py

# 安装flake8 - 另一个代码检查工具
pip install flake8

# 检查代码
flake8 your_file.py
```

### 类型检查工具

```bash
# 安装mypy - 静态类型检查
pip install mypy

# 检查代码
mypy your_file.py
```

---

## 总结

### 🎯 核心要点

1. **遵循PEP 8** - Python官方规范
2. **命名清晰** - 使用有意义的名称
3. **注释适度** - 解释为什么，不是什么
4. **文档完整** - 函数和类都要有文档字符串
5. **单一职责** - 每个函数只做一件事
6. **错误处理** - 捕获并处理可能的异常
7. **使用工具** - black, pylint等工具帮助检查

### 📚 参考资源

- [PEP 8 官方文档](https://www.python.org/dev/peps/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Real Python - Python Code Style](https://realpython.com/python-pep8/)

---

**记住：好的代码规范需要持续练习。从今天开始，养成编写规范代码的习惯！** 💪
