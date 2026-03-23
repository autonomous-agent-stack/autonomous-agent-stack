# Claude Code 30天训练营 - 练习题库（第1周）

> **版本**: 2.0 | **题目数量**: 30道 | **难度**: ⭐⭐ 入门

---

## 📋 练习题说明

### 使用方法
1. 每天完成3-5道题
2. 先自己思考，再查看答案
3. 理解答案的逻辑
4. 举一反三

### 难度标识
- ⭐ 简单 - 10分钟内完成
- ⭐⭐ 中等 - 20分钟内完成
- ⭐⭐⭐ 较难 - 30分钟内完成

---

## 📝 Day 1-2: 基础语法

### 题目1（⭐） - Hello World变种
**题目**: 编写程序，打印5次"Hello, World!"，每次打印不同的问候语

**答案**:
```python
print("Hello, World!")
print("你好，世界！")
print("Hello, 大家好！")
print("Hello, Python！")
print("Hello, Claude Code！")
```

---

### 题目2（⭐） - 打印个人信息
**题目**: 编写程序，打印你的个人信息（姓名、年龄、职业、爱好）

**答案**:
```python
name = "张三"
age = 25
job = "程序员"
hobby = "编程、阅读、旅行"

print(f"姓名：{name}")
print(f"年龄：{age}岁")
print(f"职业：{job}")
print(f"爱好：{hobby}")
```

---

### 题目3（⭐⭐） - ASCII艺术
**题目**: 编写程序，打印一个简单的房子

**答案**:
```python
print("""
    /\\
   /  \\
  /____\\
  | [] |
  |____|
""")
```

---

### 题目4（⭐⭐） - 交互式问候
**题目**: 编写程序，让用户输入名字，然后打印个性化问候

**答案**:
```python
name = input("请输入你的名字：")
print(f"你好，{name}！欢迎来到Python世界！")
```

---

### 题目5（⭐⭐） - 年龄计算
**题目**: 编写程序，让用户输入出生年份，计算今年的年龄

**答案**:
```python
birth_year = int(input("请输入你的出生年份："))
current_year = 2026
age = current_year - birth_year
print(f"你今年{age}岁")
```

---

### 题目6（⭐⭐） - 温度转换
**题目**: 编写程序，将摄氏度转换为华氏度（公式：F = C × 9/5 + 32）

**答案**:
```python
celsius = float(input("请输入摄氏度："))
fahrenheit = celsius * 9 / 5 + 32
print(f"{celsius}°C = {fahrenheit}°F")
```

---

### 题目7（⭐⭐⭐） - 数字运算
**题目**: 编写程序，让用户输入两个数字，计算它们的和、差、积、商

**答案**:
```python
num1 = float(input("请输入第一个数字："))
num2 = float(input("请输入第二个数字："))

print(f"和：{num1 + num2}")
print(f"差：{num1 - num2}")
print(f"积：{num1 * num2}")
print(f"商：{num1 / num2}")
```

---

### 题目8（⭐⭐⭐） - 圆的面积
**题目**: 编写程序，计算圆的面积（公式：S = πr²）

**答案**:
```python
import math

radius = float(input("请输入圆的半径："))
area = math.pi * radius ** 2
print(f"圆的面积：{area:.2f}")
```

---

### 题目9（⭐） - 字符串长度
**题目**: 编写程序，让用户输入一个字符串，输出它的长度

**答案**:
```python
text = input("请输入一个字符串：")
length = len(text)
print(f"字符串长度：{length}")
```

---

### 题目10（⭐⭐） - 字符串拼接
**题目**: 编写程序，让用户输入名和姓，输出全名

**答案**:
```python
first_name = input("请输入你的名：")
last_name = input("请输入你的姓：")
full_name = first_name + last_name
print(f"全名：{full_name}")
```

---

## 📝 Day 3-4: 数据类型与运算

### 题目11（⭐⭐） - 整除和取余
**题目**: 编写程序，让用户输入两个数字，显示整除和取余结果

**答案**:
```python
num1 = int(input("请输入第一个数字："))
num2 = int(input("请输入第二个数字："))

print(f"整除：{num1 // num2}")
print(f"取余：{num1 % num2}")
```

---

### 题目12（⭐⭐） - 乘方计算
**题目**: 编写程序，计算2的10次方

**答案**:
```python
result = 2 ** 10
print(f"2的10次方 = {result}")
```

---

### 题目13（⭐⭐⭐） - 绝对值
**题目**: 编写程序，让用户输入一个数字，输出它的绝对值

**答案**:
```python
num = float(input("请输入一个数字："))
absolute_value = abs(num)
print(f"绝对值：{absolute_value}")
```

---

### 题目14（⭐⭐） - 浮点数四舍五入
**题目**: 编写程序，将3.14159四舍五入到2位小数

**答案**:
```python
pi = 3.14159
rounded = round(pi, 2)
print(f"四舍五入后：{rounded}")
```

---

### 题目15（⭐⭐） - 字符串重复
**题目**: 编写程序，让用户输入一个字符串和一个数字，输出重复N次的字符串

**答案**:
```python
text = input("请输入一个字符串：")
times = int(input("请输入重复次数："))
result = text * times
print(result)
```

---

### 题目16（⭐⭐） - 字符串分割
**题目**: 编写程序，将"Hello,World!"按逗号分割成两部分

**答案**:
```python
text = "Hello,World!"
parts = text.split(",")
print(f"第一部分：{parts[0]}")
print(f"第二部分：{parts[1]}")
```

---

### 题目17（⭐⭐） - 布尔运算
**题目**: 编写程序，判断以下表达式的结果：
1. True and False
2. True or False
3. not True

**答案**:
```python
print(f"True and False = {True and False}")
print(f"True or False = {True or False}")
print(f"not True = {not True}")
```

---

### 题目18（⭐⭐⭐） - 复杂数学表达式
**题目**: 编写程序，计算 (10 + 20) * 3 - 50 / 2

**答案**:
```python
result = (10 + 20) * 3 - 50 / 2
print(f"结果：{result}")
```

---

### 题目19（⭐⭐） - 类型检测
**题目**: 编写程序，检测以下变量的类型：
- 42
- 3.14
- "Hello"
- True

**答案**:
```python
var1 = 42
var2 = 3.14
var3 = "Hello"
var4 = True

print(f"42的类型：{type(var1)}")
print(f"3.14的类型：{type(var2)}")
print(f"'Hello'的类型：{type(var3)}")
print(f"True的类型：{type(var4)}")
```

---

### 题目20（⭐⭐） - 混合运算
**题目**: 编写程序，计算 "100" + 200 的结果，注意类型转换

**答案**:
```python
result = int("100") + 200
print(f"结果：{result}")
```

---

## 📝 Day 5-7: 列表与字典

### 题目21（⭐） - 列表创建
**题目**: 创建一个包含5个水果的列表，然后打印第3个水果

**答案**:
```python
fruits = ["苹果", "香蕉", "橙子", "葡萄", "草莓"]
print(f"第3个水果：{fruits[2]}")
```

---

### 题目22（⭐⭐） - 列表操作
**题目**: 创建一个列表，添加一个元素，删除一个元素，然后打印

**答案**:
```python
fruits = ["苹果", "香蕉", "橙子"]
fruits.append("葡萄")        # 添加元素
fruits.remove("香蕉")       # 删除元素
print(fruits)
```

---

### 题目23（⭐⭐） - 列表推导式
**题目**: 使用列表推导式，创建一个1-10的平方列表

**答案**:
```python
squares = [x**2 for x in range(1, 11)]
print(squares)
# 输出：[1, 4, 9, 16, 25, 36, 49, 64, 81, 100]
```

---

### 题目24（⭐⭐） - 字典创建
**题目**: 创建一个学生字典，包含姓名、年龄、班级信息，然后打印

**答案**:
```python
student = {
    "name": "张三",
    "age": 18,
    "class": "高三(1)班"
}
print(f"学生姓名：{student['name']}")
print(f"学生年龄：{student['age']}")
print(f"学生班级：{student['class']}")
```

---

### 题目25（⭐⭐） - 字典操作
**题目**: 创建一个字典，添加一个键值对，删除一个键值对，然后打印

**答案**:
```python
student = {
    "name": "张三",
    "age": 18
}
student["gender"] = "男"     # 添加键值对
del student["age"]          # 删除键值对
print(student)
```

---

### 题目26（⭐⭐⭐） - 列表排序
**题目**: 创建一个包含数字的列表，按升序和降序排序

**答案**:
```python
numbers = [5, 2, 8, 1, 9, 3]
numbers.sort()           # 升序排序
print(f"升序：{numbers}")

numbers.sort(reverse=True)  # 降序排序
print(f"降序：{numbers}")
```

---

### 题目27（⭐⭐⭐） - 字典遍历
**题目**: 遍历一个字典，打印所有的键和值

**答案**:
```python
student = {
    "name": "张三",
    "age": 18,
    "class": "高三(1)班"
}

for key, value in student.items():
    print(f"{key}: {value}")
```

---

### 题目28（⭐⭐） - 列表切片
**题目**: 创建一个包含10个数字的列表，获取前3个和后3个

**答案**:
```python
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
print(f"前3个：{numbers[:3]}")
print(f"后3个：{numbers[-3:]}")
```

---

### 题目29（⭐⭐⭐） - 嵌套列表
**题目**: 创建一个二维列表（3x3），打印第2行第3列的元素

**答案**:
```python
matrix = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]
print(f"第2行第3列：{matrix[1][2]}")
```

---

### 题目30（⭐⭐⭐） - 字典推导式
**题目**: 使用字典推导式，创建一个1-5的平方字典

**答案**:
```python
squares = {x: x**2 for x in range(1, 6)}
print(squares)
# 输出：{1: 1, 2: 4, 3: 9, 4: 16, 5: 25}
```

---

## 📊 练习统计

### 难度分布
- ⭐ 简单: 10道
- ⭐⭐ 中等: 15道
- ⭐⭐⭐ 较难: 5道

### 知识点覆盖
- 基础语法: 10道
- 数据类型: 10道
- 列表操作: 5道
- 字典操作: 5道

---

## ✅ 完成检查

### 自我评估
- [ ] 完成所有30道题
- [ ] 理解每道题的答案
- [ ] 能够独立写出代码
- [ ] 记录遇到的错误

### 复习建议
- 重新做一遍错题
- 总结解题技巧
- 整理常用代码片段

---

**创建时间**: 2026-03-23 17:45
**题目数量**: 30道
**难度**: ⭐⭐ 入门
**状态**: 🔥 火力全开完成

🔥 **练习是最好的老师！** 🔥
