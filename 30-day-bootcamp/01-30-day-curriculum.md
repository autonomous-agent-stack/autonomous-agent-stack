# 30天详细课程大纲 📚

> 每天具体学习目标、知识点、练习题

## 📋 目录

- [第1周：基础入门](#第1周基础入门第1-7天)
- [第2周：进阶技能](#第2周进阶技能第8-14天)
- [第3周：实战强化](#第3周实战强化第15-21天)
- [第4周：综合应用](#第4周综合应用第22-30天)

---

## 第1周：基础入门（第1-7天）

### 🎯 本周目标
理解Claude Code的基本概念，掌握Python基础语法，完成前两个入门项目。

---

### Day 1: 初识Claude Code

#### 📖 学习目标
- 理解什么是Claude Code
- 掌握Claude Code的安装和配置
- 学会基本的交互方式

#### 💡 知识点
1. **Claude Code是什么**
   - AI编程助手的概念
   - 与传统编程的区别
   - 优势和局限性

2. **安装与配置**
   - 环境要求（Python 3.8+）
   - 安装步骤
   - 基本配置

3. **基本使用**
   - 提问的技巧
   - 代码生成流程
   - 最佳实践

#### 📝 练习题
1. 安装Claude Code并完成配置
2. 尝试让Claude Code生成一个简单的问候程序
3. 记录安装过程中遇到的问题

#### 📚 参考资源
- `10-git-tutorial.md` - 基础环境准备
- `08-code-style-guide.md` - 代码规范入门

---

### Day 2: Python基础概念

#### 📖 学习目标
- 理解Python编程的基本概念
- 掌握变量和数据类型
- 学会基本输入输出

#### 💡 知识点
1. **Python简介**
   - 为什么选择Python
   - Python的特点
   - 应用场景

2. **基本语法**
   - 变量的定义和使用
   - 数据类型（字符串、整数、浮点数、布尔值）
   - 输入输出（input/print）

3. **代码注释**
   - 单行注释
   - 多行注释
   - 注释的重要性

#### 📝 练习题
1. 创建程序，询问用户姓名并打印问候语
2. 编写程序计算两个数的和、差、积、商
3. 练习使用不同的数据类型

#### 💻 代码示例
```python
# 练习题1解决方案
name = input("请输入您的姓名：")
print(f"你好，{name}！欢迎来到Python世界！")

# 练习题2解决方案
num1 = float(input("请输入第一个数字："))
num2 = float(input("请输入第二个数字："))
print(f"{num1} + {num2} = {num1 + num2}")
print(f"{num1} - {num2} = {num1 - num2}")
print(f"{num1} × {num2} = {num1 * num2}")
print(f"{num1} ÷ {num2} = {num1 / num2}")
```

---

### Day 3: 条件判断与循环

#### 📖 学习目标
- 掌握if条件语句的使用
- 学会for和while循环
- 理解逻辑运算符

#### 💡 知识点
1. **条件判断**
   - if语句
   - if-else语句
   - if-elif-else语句
   - 逻辑运算符（and, or, not）

2. **循环结构**
   - for循环
   - while循环
   - break和continue
   - 循环嵌套

3. **实际应用**
   - 验证用户输入
   - 批量处理数据
   - 简单的算法实现

#### 📝 练习题
1. 编写程序判断数字是奇数还是偶数
2. 实现1到100的累加
3. 编写猜数字游戏（1-100之间）

#### 💻 代码示例
```python
# 练习题1：判断奇偶数
num = int(input("请输入一个整数："))
if num % 2 == 0:
    print(f"{num} 是偶数")
else:
    print(f"{num} 是奇数")

# 练习题2：1到100累加
total = 0
for i in range(1, 101):
    total += i
print(f"1到100的和是：{total}")

# 练习题3：猜数字游戏
import random
secret = random.randint(1, 100)
while True:
    guess = int(input("请输入你的猜测（1-100）："))
    if guess == secret:
        print("恭喜你猜对了！")
        break
    elif guess < secret:
        print("太小了，再试一次！")
    else:
        print("太大了，再试一次！")
```

---

### Day 4: 列表和字符串

#### 📖 学习目标
- 掌握列表的基本操作
- 学会字符串处理
- 理解索引和切片

#### 💡 知识点
1. **列表**
   - 创建列表
   - 添加、删除、修改元素
   - 列表遍历
   - 列表方法（append, remove, sort等）

2. **字符串**
   - 字符串的创建和拼接
   - 字符串方法（strip, split, join等）
   - 字符串格式化

3. **索引和切片**
   - 正向和反向索引
   - 切片操作
   - 步长

#### 📝 练习题
1. 创建待办事项列表程序
2. 实现字符串逆序功能
3. 统计字符串中各字符的出现次数

#### 💻 代码示例
```python
# 练习题1：待办事项列表
todo_list = []
while True:
    print("\n=== 待办事项 ===")
    for i, item in enumerate(todo_list, 1):
        print(f"{i}. {item}")
    action = input("\n添加(A)/删除(D)/退出(Q)：").upper()
    if action == 'A':
        item = input("输入待办事项：")
        todo_list.append(item)
    elif action == 'D':
        num = int(input("输入要删除的序号："))
        if 1 <= num <= len(todo_list):
            del todo_list[num-1]
    elif action == 'Q':
        break

# 练习题2：字符串逆序
text = input("输入字符串：")
reversed_text = text[::-1]
print(f"逆序后：{reversed_text}")

# 练习题3：统计字符次数
text = input("输入字符串：")
char_count = {}
for char in text:
    char_count[char] = char_count.get(char, 0) + 1
for char, count in sorted(char_count.items()):
    print(f"'{char}': {count}次")
```

---

### Day 5: 实战项目1 - Hello World程序

#### 📖 学习目标
- 完成第一个完整项目
- 掌握项目开发流程
- 学会使用Claude Code辅助开发

#### 🎯 项目说明
创建一个交互式Hello World程序，包含多种问候方式和个性化设置。

#### 💻 项目功能
1. 个性化问候（包含姓名、时间）
2. 多语言问候（中文、英文、日文）
3. 天气查询功能
4. 名言警句展示

#### 📝 开发步骤
1. 查看项目模板 `04-project-templates/project-01-hello-world/`
2. 逐步实现核心功能
3. 添加个性化选项
4. 测试并优化

#### ✅ 完成标准
- [ ] 程序能正常运行
- [ ] 实现所有基础功能
- [ ] 代码有完整注释
- [ ] 有测试用例
- [ ] 代码符合规范

---

### Day 6: 文件操作与字典

#### 📖 学习目标
- 掌握文件读写操作
- 学会字典的使用
- 理解JSON数据格式

#### 💡 知识点
1. **文件操作**
   - 打开和关闭文件
   - 读取文件内容
   - 写入文件
   - 文件路径处理

2. **字典**
   - 创建字典
   - 字典的基本操作
   - 遍历字典
   - 字典方法

3. **JSON数据**
   - JSON格式介绍
   - 读取JSON文件
   - 写入JSON文件
   - 数据序列化和反序列化

#### 📝 练习题
1. 编写程序读取文本文件并统计行数、词数、字符数
2. 创建通讯录程序（使用字典存储）
3. 将数据保存到JSON文件

#### 💻 代码示例
```python
# 练习题1：文本文件统计
filename = input("请输入文件名：")
try:
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')
        words = content.split()
        print(f"行数：{len(lines)}")
        print(f"词数：{len(words)}")
        print(f"字符数：{len(content)}")
except FileNotFoundError:
    print("文件不存在！")

# 练习题2：通讯录程序
import json
contacts = {}
try:
    with open('contacts.json', 'r', encoding='utf-8') as f:
        contacts = json.load(f)
except FileNotFoundError:
    pass

while True:
    name = input("\n输入姓名（或按Q退出）：")
    if name.upper() == 'Q':
        break
    phone = input("输入电话：")
    email = input("输入邮箱：")
    contacts[name] = {'phone': phone, 'email': email}

with open('contacts.json', 'w', encoding='utf-8') as f:
    json.dump(contacts, f, ensure_ascii=False, indent=2)
print("通讯录已保存！")
```

---

### Day 7: 实战项目2 - 文件整理工具

#### 📖 学习目标
- 完成第二个实战项目
- 掌握文件和目录操作
- 学会自动化文件管理

#### 🎯 项目说明
创建一个智能文件整理工具，可以按照文件类型、日期等规则自动整理文件。

#### 💻 项目功能
1. 按文件类型整理（图片、文档、视频等）
2. 按日期整理文件
3. 重命名文件
4. 创建备份

#### 📝 开发步骤
1. 查看项目模板 `04-project-templates/project-02-file-organizer/`
2. 实现文件分类功能
3. 添加日期整理功能
4. 添加文件重命名功能
5. 测试并优化

#### ✅ 完成标准
- [ ] 能自动识别文件类型
- [ ] 能正确移动文件到对应目录
- [ ] 有完善的错误处理
- [ ] 提供操作日志
- [ ] 代码有完整注释

#### 🔗 相关文件
- 模板：`04-project-templates/project-02-file-organizer/`
- 示例：`07-project-examples/project-02-complete.py`

---

## 第2周：进阶技能（第8-14天）

### 🎯 本周目标
掌握Python进阶功能，学习数据处理和Web数据获取，完成数据分析和爬虫项目。

---

### Day 8: 函数与模块

#### 📖 学习目标
- 掌握函数的定义和使用
- 学会参数传递和返回值
- 理解模块和包的概念

#### 💡 知识点
1. **函数**
   - 定义函数
   - 参数（位置参数、关键字参数、默认参数）
   - 返回值
   - 作用域

2. **模块**
   - 导入模块
   - 标准库介绍
   - 第三方库

3. **代码复用**
   - 函数的设计原则
   - 代码组织
   - 模块化编程

#### 📝 练习题
1. 编写计算器程序（使用函数）
2. 实现一个验证用户输入的函数
3. 创建自己的工具模块

#### 💻 代码示例
```python
# 练习题1：计算器函数
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        raise ValueError("除数不能为零")
    return a / b

def calculator():
    print("简单计算器")
    num1 = float(input("第一个数："))
    operator = input("运算符（+ - * /）：")
    num2 = float(input("第二个数："))

    if operator == '+':
        result = add(num1, num2)
    elif operator == '-':
        result = subtract(num1, num2)
    elif operator == '*':
        result = multiply(num1, num2)
    elif operator == '/':
        result = divide(num1, num2)
    else:
        print("无效的运算符")
        return

    print(f"结果：{num1} {operator} {num2} = {result}")

calculator()

# 练习题2：输入验证函数
def get_valid_input(prompt, input_type=float, min_value=None, max_value=None):
    """获取有效的用户输入"""
    while True:
        try:
            value = input_type(input(prompt))
            if min_value is not None and value < min_value:
                print(f"值不能小于{min_value}")
                continue
            if max_value is not None and value > max_value:
                print(f"值不能大于{max_value}")
                continue
            return value
        except ValueError:
            print("请输入有效的数字！")

# 使用示例
age = get_valid_input("请输入年龄（18-120）：", int, 18, 120)
print(f"你的年龄是：{age}岁")
```

---

### Day 9: 异常处理与调试

#### 📖 学习目标
- 掌握异常处理机制
- 学会调试技巧
- 提高代码健壮性

#### 💡 知识点
1. **异常处理**
   - try-except语句
   - 多个except块
   - else和finally
   - 自定义异常

2. **调试技巧**
   - print调试法
   - 使用断言（assert）
   - 日志记录
   - 错误追踪

3. **常见错误**
   - 语法错误
   - 运行时错误
   - 逻辑错误
   - 如何避免

#### 📝 练习题
1. 为之前的程序添加异常处理
2. 实现一个简单的日志系统
3. 练习调试有bug的代码

#### 💻 代码示例
```python
# 练习题1：带异常处理的文件读取
def read_file_safely(filename):
    """安全地读取文件"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            return content
    except FileNotFoundError:
        print(f"错误：文件 '{filename}' 不存在")
        return None
    except PermissionError:
        print(f"错误：没有权限读取文件 '{filename}'")
        return None
    except Exception as e:
        print(f"未知错误：{e}")
        return None

# 练习题2：简单日志系统
import datetime

def log(message, level="INFO"):
    """记录日志"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"

    # 打印到控制台
    print(log_entry)

    # 写入日志文件
    with open('app.log', 'a', encoding='utf-8') as f:
        f.write(log_entry + '\n')

# 使用示例
log("程序启动")
log("正在处理数据...", "INFO")
result = 10 / 0  # 会触发异常
except Exception:
    log("除零错误发生！", "ERROR")
```

---

### Day 10: 数据处理入门

#### 📖 学习目标
- 掌握基础数据处理概念
- 学会使用列表推导式
- 理解排序和过滤

#### 💡 知识点
1. **数据结构**
   - 列表推导式
   - 字典推导式
   - 集合操作

2. **数据处理**
   - 排序（sorted）
   - 过滤（filter）
   - 映射（map）
   - 聚合函数

3. **实际应用**
   - 数据清洗
   - 数据转换
   - 简单统计分析

#### 📝 练习题
1. 实现学生成绩统计程序
2. 处理销售数据，计算总销售额
3. 数据排序和筛选功能

#### 💻 代码示例
```python
# 练习题1：学生成绩统计
students = [
    {'name': '张三', 'math': 85, 'english': 90, 'chinese': 78},
    {'name': '李四', 'math': 92, 'english': 88, 'chinese': 85},
    {'name': '王五', 'math': 78, 'english': 95, 'chinese': 90},
]

# 计算每个学生的平均分
for student in students:
    avg = (student['math'] + student['english'] + student['chinese']) / 3
    student['average'] = round(avg, 1)

# 按平均分排序
students_sorted = sorted(students, key=lambda x: x['average'], reverse=True)

print("班级成绩排名：")
for i, student in enumerate(students_sorted, 1):
    print(f"{i}. {student['name']} - 平均分：{student['average']}")

# 练习题2：销售数据处理
sales_data = [
    {'product': 'A', 'price': 100, 'quantity': 5},
    {'product': 'B', 'price': 200, 'quantity': 3},
    {'product': 'C', 'price': 150, 'quantity': 4},
]

# 计算每个产品的销售额
for sale in sales_data:
    sale['total'] = sale['price'] * sale['quantity']

# 计算总销售额
total_sales = sum(sale['total'] for sale in sales_data)
print(f"总销售额：{total_sales}")

# 使用列表推导式筛选销售额超过500的产品
high_sales = [s for s in sales_data if s['total'] > 500]
print("高销售额产品：", [s['product'] for s in high_sales])
```

---

### Day 11: 网络请求基础

#### 📖 学习目标
- 理解HTTP协议基础
- 学会使用requests库
- 掌握API调用方法

#### 💡 知识点
1. **HTTP基础**
   - GET和POST请求
   - 状态码
   - 请求头和响应头

2. **requests库**
   - 安装和使用
   - 发送GET请求
   - 发送POST请求
   - 处理响应数据

3. **API调用**
   - RESTful API概念
   - JSON数据处理
   - 错误处理

#### 📝 练习题
1. 获取天气API数据
2. 调用免费的公开API
3. 处理网络请求异常

#### 💻 代码示例
```python
# 需要先安装：pip install requests
import requests

# 练习题1：调用天气API
def get_weather(city):
    """获取城市天气"""
    try:
        # 使用免费的天气API（示例）
        url = f"https://api.weatherapi.com/v1/current.json?key=YOUR_API_KEY&q={city}"
        response = requests.get(url)
        response.raise_for_status()  # 检查请求是否成功

        data = response.json()
        location = data['location']['name']
        temp_c = data['current']['temp_c']
        condition = data['current']['condition']['text']

        return f"{location} 的天气：{condition}，温度 {temp_c}°C"

    except requests.exceptions.RequestException as e:
        return f"请求失败：{e}"

# 练习题2：调用免费公开API（JSONPlaceholder）
def get_user_info(user_id):
    """获取用户信息"""
    url = f"https://jsonplaceholder.typicode.com/users/{user_id}"
    response = requests.get(url)

    if response.status_code == 200:
        user = response.json()
        return {
            'name': user['name'],
            'email': user['email'],
            'company': user['company']['name']
        }
    else:
        return None

# 使用示例
user_info = get_user_info(1)
if user_info:
    print(f"用户：{user_info['name']}")
    print(f"邮箱：{user_info['email']}")
    print(f"公司：{user_info['company']}")
```

---

### Day 12: 正则表达式与文本处理

#### 📖 学习目标
- 理解正则表达式基础
- 学会使用re模块
- 掌握文本提取和验证

#### 💡 知识点
1. **正则表达式基础**
   - 元字符和量词
   - 字符类
   - 分组和捕获

2. **re模块**
   - 匹配（match, search, findall）
   - 替换（sub）
   - 分割（split）
   - 编译正则表达式

3. **实际应用**
   - 数据提取
   - 表单验证
   - 日志分析

#### 📝 练习题
1. 验证邮箱地址格式
2. 提取文本中的所有URL
3. 清理和规范化文本数据

#### 💻 代码示例
```python
import re

# 练习题1：邮箱验证
def validate_email(email):
    """验证邮箱地址格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return True
    else:
        return False

# 测试
test_emails = [
    'test@example.com',
    'invalid.email',
    'user@domain.co',
]

for email in test_emails:
    print(f"{email}: {'✓' if validate_email(email) else '✗'}")

# 练习题2：提取URL
def extract_urls(text):
    """从文本中提取所有URL"""
    pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return re.findall(pattern, text)

text = """
访问我们的网站：https://www.example.com
或者查看文档：https://docs.example.com/guide
"""
urls = extract_urls(text)
print("找到的URL：", urls)

# 练习题3：文本规范化
def normalize_text(text):
    """规范化文本"""
    # 移除多余空格
    text = re.sub(r'\s+', ' ', text)
    # 移除特殊字符
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()

dirty_text = "  Hello,   World!!!  "
clean_text = normalize_text(dirty_text)
print(f"原始文本：'{dirty_text}'")
print(f"清理后：'{clean_text}'")
```

---

### Day 13: 实战项目3 - 数据分析器

#### 📖 学习目标
- 完成数据分析项目
- 掌握数据读取、处理、分析
- 学会生成简单报告

#### 🎯 项目说明
创建一个数据分析器，可以读取CSV/JSON文件，进行统计分析，生成可视化报告。

#### 💻 项目功能
1. 读取多种数据格式（CSV、JSON、Excel）
2. 数据清洗和预处理
3. 统计分析（平均值、最大值、最小值等）
4. 数据筛选和排序
5. 生成分析报告

#### 📝 开发步骤
1. 查看项目模板 `04-project-templates/project-03-data-analyzer/`
2. 实现数据读取功能
3. 添加统计分析功能
4. 实现数据筛选
5. 生成报告功能
6. 测试并优化

#### ✅ 完成标准
- [ ] 能读取多种数据格式
- [ ] 提供完整的统计分析
- [ ] 有清晰的数据展示
- [ ] 错误处理完善
- [ ] 代码结构清晰

#### 🔗 相关文件
- 模板：`04-project-templates/project-03-data-analyzer/`
- 示例：`07-project-examples/project-03-complete.py`

---

### Day 14: 实战项目4 - 网页爬虫

#### 📖 学习目标
- 完成网页爬虫项目
- 掌握网络数据获取
- 学会数据提取和存储

#### 🎯 项目说明
创建一个网页爬虫，可以从指定网站抓取数据并保存。

#### 💻 项目功能
1. 发送HTTP请求获取网页
2. 解析HTML内容
3. 提取所需数据
4. 数据清洗和处理
5. 保存到文件/数据库

#### 📝 开发步骤
1. 查看项目模板 `04-project-templates/project-04-web-scraper/`
2. 实现网页获取功能
3. 添加HTML解析功能
4. 实现数据提取
5. 添加数据存储功能
6. 测试并优化

#### ✅ 完成标准
- [ ] 能成功获取网页内容
- [ ] 准确提取目标数据
- [ ] 正确处理异常情况
- [ ] 数据格式规范
- [ ] 遵守robots.txt规则

#### 🔗 相关文件
- 模板：`04-project-templates/project-04-web-scraper/`
- 示例：`07-project-examples/project-04-complete.py`

---

## 第3周：实战强化（第15-21天）

### 🎯 本周目标
掌握自动化编程技能，学习邮件自动化和文档处理，完成两个实战项目。

---

### Day 15: 邮件自动化基础

#### 📖 学习目标
- 理解邮件协议（SMTP/IMAP）
- 学会发送和读取邮件
- 掌握邮件附件处理

#### 💡 知识点
1. **SMTP协议**
   - 发送邮件的基本概念
   - SMTP服务器配置
   - 认证和安全

2. **Python邮件库**
   - smtplib模块
   - email模块
   - MIME类型处理

3. **邮件处理**
   - 发送纯文本邮件
   - 发送HTML邮件
   - 添加附件
   - 处理中文编码

#### 📝 练习题
1. 发送测试邮件到自己的邮箱
2. 发送带附件的邮件
3. 批量发送个性化邮件

#### 💻 代码示例
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# 练习题1：发送简单邮件
def send_email(to_email, subject, body):
    """发送简单邮件"""
    # 配置SMTP服务器（以QQ邮箱为例）
    smtp_server = "smtp.qq.com"
    smtp_port = 587
    sender_email = "your_email@qq.com"
    sender_password = "your_password"  # 需要使用授权码

    try:
        # 创建邮件对象
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # 发送邮件
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # 启用TLS加密
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print(f"邮件已成功发送至 {to_email}")
        return True
    except Exception as e:
        print(f"发送失败：{e}")
        return False

# 练习题2：发送带附件的邮件
def send_email_with_attachment(to_email, subject, body, attachment_path):
    """发送带附件的邮件"""
    msg = MIMEMultipart()
    msg['From'] = "your_email@qq.com"
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    # 添加附件
    with open(attachment_path, 'rb') as f:
        attachment = MIMEApplication(f.read(), _subtype="pdf")
        attachment.add_header('Content-Disposition',
                            'attachment',
                            filename='document.pdf')
        msg.attach(attachment)

    # 发送邮件（同上）
    # ...

# 练习题3：批量发送个性化邮件
recipients = [
    {'name': '张三', 'email': 'zhangsan@example.com'},
    {'name': '李四', 'email': 'lisi@example.com'},
]

for person in recipients:
    subject = f"你好，{person['name']}！"
    body = f"""
    亲爱的{person['name']}：

    这是一封个性化的测试邮件。

    祝好！
    """
    send_email(person['email'], subject, body)
```

---

### Day 16: 定时任务与调度

#### 📖 学习目标
- 理解定时任务概念
- 学会使用schedule库
- 掌握系统定时任务

#### 💡 知识点
1. **Python定时任务**
   - time.sleep
   - schedule库
   - threading模块

2. **系统定时任务**
   - Windows任务计划
   - Linux cron
   - macOS launchd

3. **实际应用**
   - 定期备份数据
   - 定时发送报告
   - 周期性检查更新

#### 📝 练习题
1. 创建每分钟执行的定时任务
2. 实现每天固定时间发送报告
3. 创建定期数据备份程序

#### 💻 代码示例
```python
# 需要先安装：pip install schedule
import schedule
import time
from datetime import datetime

# 练习题1：每分钟执行的任务
def job_every_minute():
    """每分钟执行的任务"""
    print(f"[{datetime.now()}] 每分钟任务执行中...")

schedule.every().minute.do(job_every_minute)

# 练习题2：每天固定时间执行
def morning_report():
    """每天早上9点发送报告"""
    print(f"[{datetime.now()}] 发送晨报...")
    # 这里调用发送邮件的函数
    # send_email(...)

schedule.every().day.at("09:00").do(morning_report)

# 练习题3：周期性备份
def backup_data():
    """每周一凌晨2点备份数据"""
    print(f"[{datetime.now()}] 开始备份数据...")
    # 这里实现备份逻辑
    # shutil.copytree(...)

schedule.every().monday.at("02:00").do(backup_data)

# 主循环
def run_scheduler():
    """运行调度器"""
    print("定时任务调度器启动...")
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    run_scheduler()
```

---

### Day 17: Excel文件处理

#### 📖 学习目标
- 学会使用openpyxl处理Excel
- 掌握数据读取和写入
- 理解Excel文件结构

#### 💡 知识点
1. **openpyxl库**
   - 安装和基础使用
   - 工作簿和工作表
   - 单元格操作

2. **数据操作**
   - 读取Excel数据
   - 写入数据
   - 格式设置
   - 公式计算

3. **实际应用**
   - 数据导入导出
   - 批量处理Excel
   - 生成报表

#### 📝 练习题
1. 读取Excel文件内容
2. 写入数据到Excel
3. 批量处理多个Excel文件

#### 💻 代码示例
```python
# 需要先安装：pip install openpyxl
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill

# 练习题1：创建新的Excel文件
def create_sample_excel():
    """创建示例Excel文件"""
    wb = Workbook()
    ws = wb.active
    ws.title = "学生成绩"

    # 写入表头
    headers = ['姓名', '数学', '英语', '语文', '总分']
    ws.append(headers)

    # 设置表头样式
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="CCCCCC",
                               end_color="CCCCCC",
                               fill_type="solid")

    # 写入数据
    data = [
        ['张三', 85, 90, 78],
        ['李四', 92, 88, 85],
        ['王五', 78, 95, 90],
    ]

    for row in data:
        # 计算总分
        total = sum(row[1:])
        row.append(total)
        ws.append(row)

    # 保存文件
    wb.save('学生成绩.xlsx')
    print("Excel文件创建成功！")

# 练习题2：读取Excel文件
def read_excel(filename):
    """读取Excel文件"""
    wb = load_workbook(filename)
    ws = wb.active

    print(f"工作表名称：{ws.title}")
    print(f"数据行数：{ws.max_row}")
    print(f"数据列数：{ws.max_column}")

    print("\n数据内容：")
    for row in ws.iter_rows(values_only=True):
        print(row)

# 练习题3：批量处理Excel
def process_multiple_excels(file_list):
    """批量处理多个Excel文件"""
    for filename in file_list:
        try:
            wb = load_workbook(filename)
            ws = wb.active

            # 计算每行的总分
            for row in range(2, ws.max_row + 1):
                total = 0
                for col in range(2, ws.max_column + 1):
                    total += ws.cell(row=row, column=col).value or 0
                ws.cell(row=row, column=ws.max_column + 1, value=total)

            wb.save(f"处理_{filename}")
            print(f"{filename} 处理完成")
        except Exception as e:
            print(f"处理 {filename} 时出错：{e}")

# 使用示例
create_sample_excel()
read_excel('学生成绩.xlsx')
```

---

### Day 18: PDF文件处理

#### 📖 学习目标
- 学会使用PyPDF2处理PDF
- 掌握PDF读取和提取
- 了解PDF生成方法

#### 💡 知识点
1. **PDF处理库**
   - PyPDF2
   - pdfplumber
   - reportlab

2. **PDF操作**
   - 读取PDF文本
   - 提取页面
   - 合并PDF
   - 拆分PDF

3. **PDF生成**
   - 创建简单PDF
   - 添加文本和图片
   - 设置格式

#### 📝 练习题
1. 读取PDF文件中的文本
2. 合并多个PDF文件
3. 从PDF提取指定页面

#### 💻 代码示例
```python
# 需要先安装：pip install PyPDF2
from PyPDF2 import PdfReader, PdfWriter, PdfMerger

# 练习题1：读取PDF文本
def extract_pdf_text(pdf_path):
    """提取PDF文本内容"""
    try:
        reader = PdfReader(pdf_path)
        text = ""

        for page in reader.pages:
            text += page.extract_text() + "\n"

        return text
    except Exception as e:
        print(f"读取PDF失败：{e}")
        return None

# 练习题2：合并PDF文件
def merge_pdfs(pdf_files, output_filename):
    """合并多个PDF文件"""
    merger = PdfMerger()

    for pdf in pdf_files:
        try:
            merger.append(pdf)
            print(f"已添加：{pdf}")
        except Exception as e:
            print(f"添加 {pdf} 失败：{e}")

    merger.write(output_filename)
    merger.close()
    print(f"合并完成，保存为：{output_filename}")

# 练习题3：拆分PDF文件
def split_pdf(pdf_path, output_dir):
    """拆分PDF文件，每页保存为一个单独文件"""
    import os

    reader = PdfReader(pdf_path)

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)

        output_path = os.path.join(output_dir, f"page_{i+1}.pdf")
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
        print(f"已保存：{output_path}")

    print(f"拆分完成！共 {len(reader.pages)} 页")

# 使用示例
# text = extract_pdf_text('example.pdf')
# print(text)

# merge_pdfs(['file1.pdf', 'file2.pdf'], 'merged.pdf')

# split_pdf('large_file.pdf', 'split_pages/')
```

---

### Day 19: 实战项目5 - 邮件自动化系统

#### 📖 学习目标
- 完成邮件自动化项目
- 整合多个功能模块
- 实现完整的工作流程

#### 🎯 项目说明
创建一个邮件自动化系统，可以自动发送个性化邮件、定期发送报告、管理邮件模板。

#### 💻 项目功能
1. 邮件模板管理
2. 批量发送个性化邮件
3. 定时任务调度
4. 邮件发送记录
5. 附件管理

#### 📝 开发步骤
1. 查看项目模板 `04-project-templates/project-05-email-automation/`
2. 实现邮件发送功能
3. 添加模板管理功能
4. 实现定时任务
5. 添加日志记录
6. 测试并优化

#### ✅ 完成标准
- [ ] 能成功发送各种类型邮件
- [ ] 模板系统灵活易用
- [ ] 定时任务运行稳定
- [ ] 有完善的错误处理
- [ ] 操作记录完整

#### 🔗 相关文件
- 模板：`04-project-templates/project-05-email-automation/`
- 示例：`07-project-examples/project-05-complete.py`

---

### Day 20: 实战项目6 - PDF处理工具

#### 📖 学习目标
- 完成PDF处理项目
- 掌握文档自动化技能
- 提升编程实践能力

#### 🎯 项目说明
创建一个PDF处理工具集，包含常用的PDF操作功能。

#### 💻 项目功能
1. PDF文本提取
2. PDF合并和拆分
3. PDF页面提取
4. PDF转图片（可选）
5. 批量处理

#### 📝 开发步骤
1. 查看项目模板 `04-project-templates/project-06-pdf-processor/`
2. 实现文本提取功能
3. 添加合并/拆分功能
4. 实现页面操作
5. 添加批量处理
6. 测试并优化

#### ✅ 完成标准
- [ ] 能准确提取PDF文本
- [ ] 合并拆分功能正常
- [ ] 批量处理效率高
- [ ] 支持多种PDF格式
- [ ] 有友好的用户界面

#### 🔗 相关文件
- 模板：`04-project-templates/project-06-pdf-processor/`
- 示例：`07-project-examples/project-06-complete.py`

---

### Day 21: 数据库基础（SQLite）

#### 📖 学习目标
- 理解数据库基本概念
- 学会使用SQLite
- 掌握SQL基础操作

#### 💡 知识点
1. **SQLite基础**
   - 数据库概念
   - SQLite特点
   - Python sqlite3模块

2. **SQL基础**
   - CREATE TABLE
   - INSERT
   - SELECT
   - UPDATE
   - DELETE

3. **实际应用**
   - 数据持久化
   - 数据查询和分析
   - 应用程序开发

#### 📝 练习题
1. 创建数据库和表
2. 插入和查询数据
3. 更新和删除数据

#### 💻 代码示例
```python
import sqlite3

# 练习题1：创建数据库和表
def create_database():
    """创建示例数据库"""
    conn = sqlite3.connect('mydb.db')
    cursor = conn.cursor()

    # 创建用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            age INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print("数据库创建成功！")

# 练习题2：插入数据
def insert_user(name, email, age):
    """插入用户数据"""
    conn = sqlite3.connect('mydb.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO users (name, email, age)
            VALUES (?, ?, ?)
        ''', (name, email, age))

        conn.commit()
        print(f"用户 {name} 添加成功！")
    except sqlite3.IntegrityError:
        print("邮箱已存在！")
    finally:
        conn.close()

# 练习题3：查询数据
def query_users():
    """查询所有用户"""
    conn = sqlite3.connect('mydb.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()

    print("\n所有用户：")
    for user in users:
        print(f"ID: {user[0]}, 姓名: {user[1]}, 邮箱: {user[2]}, 年龄: {user[3]}")

    conn.close()

# 练习题4：更新和删除
def update_user_email(user_id, new_email):
    """更新用户邮箱"""
    conn = sqlite3.connect('mydb.db')
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE users SET email = ? WHERE id = ?
    ''', (new_email, user_id))

    conn.commit()
    conn.close()
    print(f"用户 {user_id} 的邮箱已更新")

def delete_user(user_id):
    """删除用户"""
    conn = sqlite3.connect('mydb.db')
    cursor = conn.cursor()

    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))

    conn.commit()
    conn.close()
    print(f"用户 {user_id} 已删除")

# 使用示例
create_database()
insert_user('张三', 'zhangsan@example.com', 25)
insert_user('李四', 'lisi@example.com', 30)
query_users()
```

---

## 第4周：综合应用（第22-30天）

### 🎯 本周目标
掌握API集成和综合应用，完成股票追踪和个人仪表盘项目，总结提升。

---

### Day 22: API集成进阶

#### 📖 学习目标
- 掌握复杂API调用
- 学会API认证和授权
- 理解API限流和错误处理

#### 💡 知识点
1. **API认证**
   - API Key
   - OAuth
   - JWT

2. **进阶功能**
   - 分页处理
   - 批量请求
   - 异步请求

3. **错误处理**
   - 重试机制
   - 超时设置
   - 错误码处理

#### 📝 练习题
1. 调用需要认证的API
2. 实现自动重试机制
3. 处理API分页数据

#### 💻 代码示例
```python
import requests
import time
from functools import wraps

# 练习题1：带认证的API调用
def call_authenticated_api(api_key, endpoint):
    """调用需要认证的API"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(
            'https://api.example.com/' + endpoint,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API调用失败：{e}")
        return None

# 练习题2：自动重试装饰器
def retry(max_attempts=3, delay=1):
    """自动重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    print(f"第 {attempt + 1} 次尝试失败，{delay}秒后重试...")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

@retry(max_attempts=3, delay=2)
def fetch_data(url):
    """获取数据（带重试）"""
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    return response.json()

# 练习题3：处理分页数据
def fetch_all_data(base_url):
    """获取所有分页数据"""
    all_data = []
    page = 1

    while True:
        url = f"{base_url}?page={page}"
        response = requests.get(url)

        if response.status_code != 200:
            break

        data = response.json()
        items = data.get('items', [])

        if not items:
            break

        all_data.extend(items)
        print(f"已获取第 {page} 页，累计 {len(all_data)} 条数据")

        page += 1

    return all_data

# 使用示例
# data = fetch_all_data('https://api.example.com/data')
# print(f"总共获取 {len(data)} 条数据")
```

---

### Day 23: 数据可视化基础

#### 📖 学习目标
- 了解数据可视化概念
- 学会使用matplotlib
- 掌握基础图表绘制

#### 💡 知识点
1. **matplotlib基础**
   - 安装和导入
   - 基本绘图
   - 图表类型

2. **常用图表**
   - 折线图
   - 柱状图
   - 饼图
   - 散点图

3. **图表美化**
   - 设置标题和标签
   - 调整颜色和样式
   - 添加图例

#### 📝 练习题
1. 绘制简单的折线图
2. 创建柱状图显示数据对比
3. 绘制饼图展示数据占比

#### 💻 代码示例
```python
# 需要先安装：pip install matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 设置中文字体（解决中文显示问题）
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 练习题1：折线图
def draw_line_chart():
    """绘制折线图"""
    months = ['1月', '2月', '3月', '4月', '5月', '6月']
    sales = [120, 150, 180, 200, 190, 220]

    plt.figure(figsize=(10, 6))
    plt.plot(months, sales, marker='o', linewidth=2, markersize=8)
    plt.title('2024年上半年销售趋势', fontsize=16)
    plt.xlabel('月份', fontsize=12)
    plt.ylabel('销售额（万元）', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('line_chart.png', dpi=300)
    plt.show()
    print("折线图已保存为 line_chart.png")

# 练习题2：柱状图
def draw_bar_chart():
    """绘制柱状图"""
    products = ['产品A', '产品B', '产品C', '产品D', '产品E']
    sales = [350, 420, 280, 390, 450]

    plt.figure(figsize=(10, 6))
    bars = plt.bar(products, sales, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8'])
    plt.title('各产品销售量对比', fontsize=16)
    plt.xlabel('产品', fontsize=12)
    plt.ylabel('销售量', fontsize=12)

    # 在柱子上显示数值
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height}',
                ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig('bar_chart.png', dpi=300)
    plt.show()
    print("柱状图已保存为 bar_chart.png")

# 练习题3：饼图
def draw_pie_chart():
    """绘制饼图"""
    categories = ['娱乐', '饮食', '交通', '购物', '其他']
    expenses = [1500, 2000, 800, 1200, 500]

    plt.figure(figsize=(10, 8))
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
    explode = (0.1, 0, 0, 0, 0)  # 突出第一块

    plt.pie(expenses, labels=categories, colors=colors, explode=explode,
            autopct='%1.1f%%', shadow=True, startangle=90)
    plt.title('月度支出分布', fontsize=16)
    plt.axis('equal')
    plt.tight_layout()
    plt.savefig('pie_chart.png', dpi=300)
    plt.show()
    print("饼图已保存为 pie_chart.png")

# 使用示例
draw_line_chart()
draw_bar_chart()
draw_pie_chart()
```

---

### Day 24: Web框架入门（Flask）

#### 📖 学习目标
- 了解Web框架概念
- 学会Flask基础
- 创建简单Web应用

#### 💡 知识点
1. **Flask基础**
   - 安装和快速开始
   - 路由和视图函数
   - 模板渲染

2. **Web概念**
   - HTTP请求和响应
   - GET和POST
   - 表单处理

3. **简单应用**
   - 静态页面
   - 动态内容
   - 数据展示

#### 📝 练习题
1. 创建Hello World应用
2. 实现简单的表单处理
3. 创建数据展示页面

#### 💻 代码示例
```python
# 需要先安装：pip install flask
from flask import Flask, render_template, request

app = Flask(__name__)

# 练习题1：Hello World
@app.route('/')
def hello():
    return '你好，欢迎来到Flask！'

@app.route('/about')
def about():
    return '这是关于页面'

# 练习题2：动态路由
@app.route('/user/<name>')
def user_profile(name):
    return f'你好，{name}！'

@app.route('/add/<int:a>/<int:b>')
def add_numbers(a, b):
    return f'{a} + {b} = {a + b}'

# 练习题3：表单处理
@app.route('/form', methods=['GET', 'POST'])
def form():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        return f'提交成功！姓名：{name}，邮箱：{email}'
    return '''
    <form method="POST">
        <label>姓名：<input type="text" name="name"></label><br>
        <label>邮箱：<input type="email" name="email"></label><br>
        <button type="submit">提交</button>
    </form>
    '''

# 练习题4：返回JSON数据
@app.route('/api/data')
def api_data():
    data = {
        'name': '张三',
        'age': 25,
        'skills': ['Python', 'Flask', 'SQL']
    }
    return data

if __name__ == '__main__':
    app.run(debug=True)
```

---

### Day 25: 实战项目7 - 日程管理器

#### 📖 学习目标
- 完成日程管理项目
- 整合之前学到的技能
- 创建实用的个人工具

#### 🎯 项目说明
创建一个日程管理器，可以管理任务、设置提醒、生成报告。

#### 💻 项目功能
1. 添加、编辑、删除任务
2. 设置任务优先级和截止日期
3. 任务提醒功能
4. 生成任务报告
5. 数据持久化（SQLite）

#### 📝 开发步骤
1. 查看项目模板 `04-project-templates/project-07-schedule-manager/`
2. 设计数据库结构
3. 实现任务管理功能
4. 添加提醒功能
5. 生成报告功能
6. 测试并优化

#### ✅ 完成标准
- [ ] 任务管理功能完整
- [ ] 提醒功能正常运行
- [ ] 报告生成准确
- [ ] 用户界面友好
- [ ] 数据安全可靠

#### 🔗 相关文件
- 模板：`04-project-templates/project-07-schedule-manager/`
- 示例：`07-project-examples/project-07-complete.py`

---

### Day 26: 综合项目设计

#### 📖 学习目标
- 学习项目设计方法
- 掌握需求分析
- 学会架构设计

#### 💡 知识点
1. **项目规划**
   - 需求分析
   - 功能设计
   - 技术选型

2. **架构设计**
   - 模块化设计
   - 代码组织
   - 接口设计

3. **开发流程**
   - 迭代开发
   - 测试策略
   - 文档编写

#### 📝 练习题
1. 设计一个个人博客系统
2. 规划一个在线待办事项应用
3. 设计数据分析工具的架构

#### 💻 设计示例
```markdown
# 个人博客系统设计文档

## 需求分析

### 核心功能
1. 文章管理（增删改查）
2. 分类和标签
3. 评论功能
4. 用户管理（可选）
5. 搜索功能

## 技术选型

### 后端
- 框架：Flask
- 数据库：SQLite
- 认证：Flask-Login（可选）

### 前端
- 模板：Jinja2
- 样式：Bootstrap
- 交互：jQuery（可选）

## 数据库设计

### 表结构
```
posts:
  - id (主键)
  - title (标题)
  - content (内容)
  - created_at (创建时间)
  - updated_at (更新时间)
  - category_id (分类ID)

categories:
  - id (主键)
  - name (名称)

tags:
  - id (主键)
  - name (名称)

comments:
  - id (主键)
  - post_id (文章ID)
  - author (作者)
  - content (内容)
  - created_at (创建时间)
```

## 模块设计

### 核心模块
1. models.py - 数据库模型
2. views.py - 路由和视图
3. forms.py - 表单验证
4. utils.py - 工具函数

### 功能模块
1. auth - 认证模块
2. posts - 文章管理
3. comments - 评论管理
4. search - 搜索功能

## 开发计划

### 阶段1（基础功能）
- 数据库设计
- 基础路由
- 文章列表和详情

### 阶段2（管理功能）
- 文章增删改
- 分类管理
- 标签管理

### 阶段3（进阶功能）
- 评论系统
- 搜索功能
- 用户认证

### 阶段4（优化完善）
- 界面美化
- 性能优化
- 测试和文档
```

---

### Day 27: 实战项目8 - 股票数据追踪器

#### 📖 学习目标
- 完成股票数据追踪项目
- 掌握API集成和数据处理
- 实现实时数据展示

#### 🎯 项目说明
创建一个股票数据追踪器，可以获取实时股票数据，计算收益，生成报告。

#### 💻 项目功能
1. 获取股票实时数据
2. 添加和删除股票
3. 计算盈亏和收益率
4. 生成可视化报告
5. 数据持久化

#### 📝 开发步骤
1. 查看项目模板 `04-project-templates/project-08-stock-tracker/`
2. 集成股票API
3. 实现数据获取和更新
4. 添加计算功能
5. 实现可视化
6. 测试并优化

#### ✅ 完成标准
- [ ] 能准确获取股票数据
- [ ] 计算功能正确
- [ ] 可视化清晰美观
- [ ] 数据更新及时
- [ ] 错误处理完善

#### 🔗 相关文件
- 模板：`04-project-templates/project-08-stock-tracker/`
- 示例：`07-project-examples/project-08-complete.py`

---

### Day 28: 实战项目9 - 个人仪表盘

#### 📖 学习目标
- 完成综合项目
- 整合所有技能
- 创建完整的应用

#### 🎯 项目说明
创建一个个人仪表盘，整合日程、任务、财务、健康等多方面信息。

#### 💻 项目功能
1. 日程管理
2. 任务跟踪
3. 财务记录
4. 健康数据
5. 数据可视化
6. 个人设置

#### 📝 开发步骤
1. 查看项目模板 `04-project-templates/project-09-personal-dashboard/`
2. 设计整体架构
3. 实现各个模块
4. 整合数据展示
5. 优化用户体验
6. 测试并完善

#### ✅ 完成标准
- [ ] 所有功能模块正常运行
- [ ] 数据展示清晰直观
- [ ] 用户操作流畅
- [ ] 性能稳定高效
- [ ] 代码结构清晰

#### 🔗 相关文件
- 模板：`04-project-templates/project-09-personal-dashboard/`
- 示例：`07-project-examples/project-09-complete.py`

---

### Day 29: 总结与回顾

#### 📖 学习目标
- 回顾整个学习过程
- 总结经验和教训
- 制定后续学习计划

#### 💡 回顾内容
1. **基础知识回顾**
   - Python基础语法
   - 数据结构和算法
   - 面向对象编程

2. **项目经验总结**
   - 9个项目的收获
   - 遇到的问题和解决方案
   - 代码质量的提升

3. **技能提升**
   - Claude Code使用技巧
   - 调试和优化方法
   - 项目开发流程

#### 📝 练习题
1. 整理学习笔记
2. 编写学习总结报告
3. 规划进阶学习方向

#### 💻 总结示例
```markdown
# 30天学习总结

## 学习成果

### 完成的项目
✅ Hello World程序
✅ 文件整理工具
✅ 数据分析器
✅ 网页爬虫
✅ 邮件自动化系统
✅ PDF处理工具
✅ 日程管理器
✅ 股票数据追踪器
✅ 个人仪表盘

### 掌握的技能
- Python编程基础
- 文件和数据操作
- 网络编程
- 自动化任务
- 数据库操作
- API集成
- 项目开发流程

## 遇到的挑战

### 主要问题
1. 环境配置问题
2. API调用失败
3. 数据格式不匹配
4. 代码调试困难

### 解决方案
1. 详细记录错误信息
2. 查阅官方文档
3. 使用Claude Code辅助
4. 逐步调试定位

## 经验教训

### 做得好的地方
- 坚持每天学习
- 动手实践项目
- 记录学习笔记

### 需要改进的地方
- 代码规范不够
- 测试覆盖不足
- 文档编写不够详细

## 后续计划

### 短期目标（1-3个月）
1. 深入学习Python高级特性
2. 学习Web框架（Django）
3. 完善现有项目

### 中期目标（3-6个月）
1. 学习前端开发
2. 开发完整Web应用
3. 参与开源项目

### 长期目标（6个月以上）
1. 成为全栈开发者
2. 开发自己的产品
3. 分享学习经验
```

---

### Day 30: 毕业项目与展望

#### 📖 学习目标
- 完成毕业设计
- 展示学习成果
- 规划未来发展

#### 💡 毕业项目
从以下方向中选择一个作为毕业项目：

1. **自动化办公工具集**
   - 文档自动处理
   - 邮件批量发送
   - 数据报表生成

2. **个人知识管理系统**
   - 笔记管理
   - 文档检索
   - 知识图谱

3. **健康生活助手**
   - 运动记录
   - 饮食管理
   - 睡眠追踪

4. **财务管理系统**
   - 收支记录
   - 预算管理
   - 投资分析

5. **创意项目**
   - 自己想做的任何项目

#### 📝 开发要求
1. 项目必须有实用价值
2. 使用至少3个学到的技术点
3. 代码规范，注释完整
4. 有用户界面（CLI或Web）
5. 完成测试和文档

#### 🎉 完成标准
- [ ] 项目功能完整
- [ ] 代码质量良好
- [ ] 有详细文档
- [ ] 有使用演示
- [ ] 总结项目收获

---

## 📊 学习进度追踪

使用下面的表格追踪你的学习进度：

| 天数 | 主题 | 状态 | 完成日期 | 备注 |
|------|------|------|----------|------|
| Day 1 | 初识Claude Code | ⬜ |  |  |
| Day 2 | Python基础概念 | ⬜ |  |  |
| Day 3 | 条件判断与循环 | ⬜ |  |  |
| Day 4 | 列表和字符串 | ⬜ |  |  |
| Day 5 | 实战项目1 | ⬜ |  |  |
| Day 6 | 文件操作与字典 | ⬜ |  |  |
| Day 7 | 实战项目2 | ⬜ |  |  |
| Day 8 | 函数与模块 | ⬜ |  |  |
| Day 9 | 异常处理与调试 | ⬜ |  |  |
| Day 10 | 数据处理入门 | ⬜ |  |  |
| Day 11 | 网络请求基础 | ⬜ |  |  |
| Day 12 | 正则表达式 | ⬜ |  |  |
| Day 13 | 实战项目3 | ⬜ |  |  |
| Day 14 | 实战项目4 | ⬜ |  |  |
| Day 15 | 邮件自动化基础 | ⬜ |  |  |
| Day 16 | 定时任务与调度 | ⬜ |  |  |
| Day 17 | Excel文件处理 | ⬜ |  |  |
| Day 18 | PDF文件处理 | ⬜ |  |  |
| Day 19 | 实战项目5 | ⬜ |  |  |
| Day 20 | 实战项目6 | ⬜ |  |  |
| Day 21 | 数据库基础 | ⬜ |  |  |
| Day 22 | API集成进阶 | ⬜ |  |  |
| Day 23 | 数据可视化基础 | ⬜ |  |  |
| Day 24 | Web框架入门 | ⬜ |  |  |
| Day 25 | 实战项目7 | ⬜ |  |  |
| Day 26 | 综合项目设计 | ⬜ |  |  |
| Day 27 | 实战项目8 | ⬜ |  |  |
| Day 28 | 实战项目9 | ⬜ |  |  |
| Day 29 | 总结与回顾 | ⬜ |  |  |
| Day 30 | 毕业项目 | ⬜ |  |  |

**图例：**
- ⬜ 未开始
- 🟡 进行中
- ✅ 已完成

---

## 🎓 学习建议

### 时间安排
- **第1周**：每天2-3小时，打好基础
- **第2周**：每天2-3小时，提升技能
- **第3周**：每天3-4小时，实战强化
- **第4周**：每天4-5小时，综合应用

### 学习方法
1. **先理解，后实践** - 理论与实践结合
2. **遇到问题先尝试自己解决** - 培养独立思考能力
3. **善用Claude Code** - 让AI成为你的助手
4. **记录学习过程** - 笔记是最好的老师
5. **定期复习** - 避免遗忘

### 常见错误
1. **只看不练** - 编程是实践性技能
2. **遇到困难就放弃** - 坚持是成功的关键
3. **不重视代码质量** - 好习惯从现在开始
4. **不写注释和文档** - 代码需要被理解
5. **不总结学习** - 经验需要提炼

---

## 📞 获取帮助

学习过程中遇到问题：

1. **查看文档**
   - `08-code-style-guide.md` - 代码规范
   - `09-debugging-tips.md` - 调试技巧
   - `05-faq.md` - 常见问题

2. **使用Claude Code**
   - 描述清楚你的问题
   - 提供错误信息
   - 展示相关代码

3. **社区资源**
   - Python官方文档
   - Stack Overflow
   - GitHub开源项目

---

**恭喜你完成30天的学习之旅！以梦为马，不负韶华！** 🎉
