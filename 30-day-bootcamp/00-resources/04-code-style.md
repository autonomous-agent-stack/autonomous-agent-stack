# 代码规范指南（PEP 8）- Python代码风格

> **版本**: 2.0 | **标准**: PEP 8 | **重要性**: ⭐⭐⭐ 必读

---

## 📋 为什么需要代码规范？

### 好代码的特征
- ✅ **可读性强** - 一目了然
- ✅ **易于维护** - 修改方便
- ✅ **团队协作** - 风格统一
- ✅ **减少错误** - 规避陷阱

### 代码规范的好处
1. **提高代码质量** - 避免常见错误
2. **提升开发效率** - 减少思考成本
3. **便于团队协作** - 统一风格
4. **方便代码审查** - 快速定位问题

---

## 📏 基础规范

### 1. 缩进

#### 规则：使用4个空格
```python
# ✅ 正确（4个空格）
def function():
    if condition:
        do_something()

# ❌ 错误（2个空格）
def function():
  if condition:
    do_something()

# ❌ 错误（Tab）
def function():
	if condition:
		do_something()
```

#### VS Code设置
```json
// settings.json
{
  "editor.tabSize": 4,
  "editor.insertSpaces": true,
  "editor.detectIndentation": false
}
```

---

### 2. 行长度

#### 规则：每行不超过79个字符
```python
# ✅ 正确（79字符以内）
result = calculate_distance(point1, point2, method="euclidean")

# ❌ 错误（超过79字符）
result = calculate_distance(point1, point2, method="euclidean", unit="meters", precision=2)

# ✅ 使用换行符（\）
result = calculate_distance(
    point1, point2,
    method="euclidean",
    unit="meters",
    precision=2
)
```

---

### 3. 空行

#### 规则：空行分隔代码块
```python
# ✅ 正确
import os
import sys

def function1():
    pass

def function2():
    pass

if __name__ == "__main__":
    function1()
    function2()
```

#### 空行数量
- **函数之间**: 2行
- **类之间**: 2行
- **函数内部**: 1行（分隔逻辑块）

---

### 4. 空格使用

#### 运算符两侧加空格
```python
# ✅ 正确
x = 1 + 2
y = x * 3 - 4
z = x / y

# ❌ 错误
x = 1+2
y = x*3-4
z = x/y
```

#### 逗号后加空格
```python
# ✅ 正确
numbers = [1, 2, 3, 4, 5]
result = function(a, b, c)

# ❌ 错误
numbers = [1,2,3,4,5]
result = function(a,b,c)
```

#### 括号内不加空格
```python
# ✅ 正确
result = (1 + 2) * 3
numbers = [1, 2, 3]

# ❌ 错误
result = ( 1 + 2 ) * 3
numbers = [ 1, 2, 3 ]
```

---

## 📝 命名规范

### 1. 变量和函数

#### 规则：小写字母 + 下划线
```python
# ✅ 正确
user_name = "张三"
user_age = 25

def calculate_sum():
    pass

# ❌ 错误
UserName = "张三"      # 驼峰命名
user_age = 25
CalculateSum()           # 大写开头
```

#### 有意义的命名
```python
# ✅ 正确
student_name = "张三"
student_age = 25
is_active = True

# ❌ 错误
n = "张三"
a = 25
flag = True
```

---

### 2. 常量

#### 规则：全大写 + 下划线
```python
# ✅ 正确
MAX_CONNECTIONS = 100
DEFAULT_TIMEOUT = 30
API_KEY = "secret_key"

# ❌ 错误
max_connections = 100
default_timeout = 30
apiKey = "secret_key"
```

---

### 3. 类名

#### 规则：首字母大写 + 驼峰命名
```python
# ✅ 正确
class UserService:
    pass

class DataProcessor:
    pass

# ❌ 错误
class user_service:     # 小写
class data_processor:   # 小写
class User_Service:     # 下划线
```

---

### 4. 私有变量

#### 规则：前缀下划线
```python
# ✅ 正确
class User:
    def __init__(self, name):
        self._name = name        # 私有变量
        self.__age = None        # 强私有

# ❌ 错误
class User:
    def __init__(self, name):
        self.name = name       # 应该私有
```

---

## 📚 注释规范

### 1. 单行注释

#### 规则：# 后加1个空格
```python
# ✅ 正确
# 计算用户年龄
age = current_year - birth_year

# ❌ 错误
#计算用户年龄
age = current_year - birth_year
```

#### 注释位置
```python
# ✅ 正确（注释在代码上方）
# 计算面积
area = radius ** 2 * pi

# ✅ 正确（注释在代码同行，简单情况）
area = radius ** 2 * pi  # 计算面积
```

---

### 2. 多行注释

#### 规则：三引号
```python
# ✅ 正确
"""
这是一个多行注释
可以写多行内容
用于解释复杂逻辑
"""

def complex_function():
    pass
```

---

### 3. 文档字符串（Docstring）

#### 规则：函数/类的第一行使用三引号
```python
# ✅ 正确
def calculate_area(radius):
    """
    计算圆的面积

    Args:
        radius (float): 圆的半径

    Returns:
        float: 圆的面积
    """
    return 3.14 * radius ** 2

# ✅ 一行文档字符串
def hello():
    """打印问候语"""
    print("Hello!")
```

---

## 🏗️ 结构规范

### 1. 导入语句

#### 规则：标准库 → 第三方库 → 本地模块
```python
# ✅ 正确

# 1. 标准库
import os
import sys
from datetime import datetime

# 2. 第三方库
import requests
from flask import Flask

# 3. 本地模块
from myapp.utils import helper
from myapp.config import settings

# ❌ 错误（混在一起）
import os
import requests
from flask import Flask
import sys
from myapp.utils import helper
```

---

### 2. 类的结构

#### 规则：顺序固定
```python
# ✅ 正确的顺序
class User:
    """用户类"""
    
    # 1. 类变量
    DEFAULT_ROLE = "guest"
    
    def __init__(self, name, age):
        # 2. 初始化方法
        self.name = name
        self.age = age
    
    @property
    def is_adult(self):
        # 3. 属性方法
        return self.age >= 18
    
    def update_info(self, name=None, age=None):
        # 4. 公共方法
        if name:
            self.name = name
        if age:
            self.age = age
    
    def _validate_age(self):
        # 5. 私有方法
        return self.age >= 0
    
    @staticmethod
    def from_dict(data):
        # 6. 静态方法
        return User(data["name"], data["age"])
```

---

### 3. 文件结构

#### 规则：顺序固定
```python
# ✅ 正确的顺序

# 1. 模块文档字符串
"""用户管理模块"""

# 2. 导入语句
import os
from typing import List

# 3. 常量
MAX_USERS = 100
DEFAULT_PAGE_SIZE = 20

# 4. 异常类
class UserError(Exception):
    pass

# 5. 工具函数
def validate_email(email: str) -> bool:
    pass

# 6. 类
class User:
    pass

# 7. 主程序
if __name__ == "__main__":
    pass
```

---

## 🎯 类型提示

### 规则：使用类型注解
```python
# ✅ 正确（带类型提示）
def calculate_sum(a: int, b: int) -> int:
    """计算两个整数的和"""
    return a + b

def get_user(user_id: int) -> dict:
    """获取用户信息"""
    return {"id": user_id, "name": "张三"}

# ❌ 错误（无类型提示）
def calculate_sum(a, b):
    return a + b
```

### 类型提示的好处
1. **IDE支持** - 自动补全和检查
2. **文档化** - 参数类型一目了然
3. **类型检查** - 使用mypy检查类型

---

## 🚫 常见错误

### 1. 混用Tab和空格
```python
# ❌ 错误
def function():
    if condition:        # Tab
        do_something()   # 空格

# ✅ 正确（统一使用空格）
def function():
    if condition:
        do_something()
```

---

### 2. 行过长不换行
```python
# ❌ 错误（超过79字符）
result = very_long_function_name(parameter1, parameter2, parameter3, parameter4)

# ✅ 正确（换行）
result = very_long_function_name(
    parameter1,
    parameter2,
    parameter3,
    parameter4
)
```

---

### 3. 无意义的注释
```python
# ❌ 错误（无意义）
x = x + 1  # x加1

# ✅ 正确（解释为什么）
x = x + 1  # 计数器递增，准备下一次迭代
```

---

## 🔍 自动检查工具

### 1. pylint

#### 安装
```bash
pip3 install pylint
```

#### 使用
```bash
# 检查单个文件
pylint my_file.py

# 检查整个目录
pylint my_project/

# 评分（10分制）
# 10.0: 优秀
# 9.0-9.9: 良好
# 8.0-8.9: 及格
# <8.0: 需要改进
```

---

### 2. flake8

#### 安装
```bash
pip3 install flake8
```

#### 使用
```bash
# 检查代码
flake8 my_file.py

# 常见错误代码
# E501: 行太长
# E302: 空行数量不对
# W293: 行尾有空格
```

---

### 3. black（自动格式化）

#### 安装
```bash
pip3 install black
```

#### 使用
```bash
# 自动格式化
black my_file.py

# 查看差异（不修改）
black --diff my_file.py

# 格式化整个目录
black my_project/
```

---

### 4. isort（导入排序）

#### 安装
```bash
pip3 install isort
```

#### 使用
```bash
# 自动排序导入
isort my_file.py

# 格式化整个目录
isort my_project/
```

---

## 📊 代码质量检查清单

### 提交前检查
- [ ] 代码符合PEP 8规范
- [ ] 所有函数都有文档字符串
- [ ] 所有变量都有有意义的名称
- [ ] 没有超过79字符的行
- [ ] 没有无用的导入
- [ ] 没有注释掉的代码
- [ ] 所有魔法数字都定义为常量
- [ ] 使用类型提示

### 项目级检查
- [ ] 统一的代码风格
- [ ] 完整的文档
- [ ] 单元测试覆盖
- [ ] 代码审查通过

---

## 💡 最佳实践

### 1. 保持简单
```python
# ✅ 简单明了
def calculate_area(radius):
    return 3.14 * radius ** 2

# ❌ 过于复杂
def calculate_area(radius):
    """
    计算圆的面积，使用数学常数π，
    通过半径的平方乘以π得到面积值。
    注意：这里使用3.14作为π的近似值。
    """
    pi = 3.14
    radius_squared = radius ** 2
    area = pi * radius_squared
    return area
```

---

### 2. DRY原则（Don't Repeat Yourself）
```python
# ❌ 重复代码
def process_users():
    for user in users:
        if user.age >= 18:
            user.can_vote = True
        else:
            user.can_vote = False

def process_students():
    for student in students:
        if student.age >= 18:
            student.can_vote = True
        else:
            student.can_vote = False

# ✅ 提取公共逻辑
def set_can_vote(person):
    person.can_vote = person.age >= 18

def process_users():
    for user in users:
        set_can_vote(user)

def process_students():
    for student in students:
        set_can_vote(student)
```

---

### 3. 单一职责原则
```python
# ❌ 一个函数做太多事
def process_user(data):
    # 验证数据
    if not data.get("name"):
        return False
    # 保存到数据库
    save_to_db(data)
    # 发送邮件
    send_email(data["email"])
    # 更新缓存
    update_cache(data)
    return True

# ✅ 拆分成多个函数
def validate_user(data):
    return bool(data.get("name"))

def save_user(data):
    save_to_db(data)
    send_email(data["email"])
    update_cache(data)

def process_user(data):
    if not validate_user(data):
        return False
    save_user(data)
    return True
```

---

## 📚 参考资料

### 官方资源
- PEP 8官方文档: https://www.python.org/dev/peps/pep-0008/
- PEP 257（文档字符串）: https://www.python.org/dev/peps/pep-0257/

### 工具文档
- pylint: https://pylint.pycqa.org/
- flake8: https://flake8.pycqa.org/
- black: https://black.readthedocs.io/
- isort: https://pycqa.github.io/isort/

---

**创建时间**: 2026-03-23 18:55
**版本**: 2.0
**标准**: PEP 8
**重要性**: ⭐⭐⭐ 必读

🔥 **代码规范，从现在开始！** 🔥
