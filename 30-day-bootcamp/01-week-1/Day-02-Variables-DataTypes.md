# Day 2: 变量与数据类型

> **学习时间**: 2小时 | **难度**: ⭐⭐ 入门 | **目标**: 理解变量和数据类型

---

## 📋 今日学习目标

- [ ] 理解变量概念
- [ ] 掌握基本数据类型
- [ ] 学会类型转换
- [ ] 完成计算器项目

---

## 🎯 学习内容

### 1. 变量

#### 什么是变量？
变量就像一个盒子，可以存储数据。

```python
# 变量赋值
name = "张三"
age = 25
height = 1.75

# 使用变量
print(name)      # 输出：张三
print(age)       # 输出：25
print(height)    # 输出：1.75
```

#### 变量命名规则
```python
# ✅ 正确的命名
my_name = "张三"
age = 25
user_age = 25
userName = "李四"

# ❌ 错误的命名
2name = "错误"      # 不能以数字开头
my-name = "错误"     # 不能包含连字符
class = "错误"      # 不能使用关键字
```

#### 变量命名建议
- 使用有意义的名称
- 使用小写字母和下划线
- 避免使用拼音

---

### 2. 基本数据类型

#### 整数（int）
```python
# 整数运算
a = 10
b = 20

print(a + b)    # 30 加法
print(a - b)    # -10 减法
print(a * b)    # 200 乘法
print(a / b)    # 0.5 除法
print(a // b)   # 0 整除
print(a % b)    # 10 取余
print(a ** b)   # 100000000000000000000000 乘方
```

#### 浮点数（float）
```python
# 浮点数运算
x = 3.14
y = 2.71

print(x + y)    # 5.85
print(x * y)    # 8.5094
print(round(x, 2))    # 3.14 四舍五入
```

#### 字符串（str）
```python
# 字符串定义
name = "张三"
greeting = '你好！'
message = """这是
多行
字符串"""

# 字符串拼接
full_name = name + greeting
print(full_name)    # 张三你好！

# 字符串重复
stars = "*" * 10
print(stars)    # **********

# 字符串长度
print(len(name))    # 2
```

#### 布尔值（bool）
```python
# 布尔值
is_student = True
is_teacher = False

print(is_student)    # True
print(not is_student)    # False
```

---

### 3. 类型转换

#### 自动类型转换
```python
# 整数 + 浮点数 = 浮点数
result = 10 + 3.14
print(result)    # 13.14
print(type(result))    # <class 'float'>
```

#### 手动类型转换
```python
# 转整数
num = int("123")
print(num)    # 123
print(type(num))    # <class 'int'>

# 转浮点数
height = float("1.75")
print(height)    # 1.75
print(type(height))    # <class 'float'>

# 转字符串
age = str(25)
print(age)    # '25'
print(type(age))    # <class 'str'>
```

---

### 4. 输入输出

#### 输入（input）
```python
# 获取用户输入
name = input("请输入你的名字：")
print(f"你好，{name}！")

# input总是返回字符串
age = input("请输入你的年龄：")
# age的类型是str，不是int
```

#### 格式化输出
```python
name = "张三"
age = 25
height = 1.75

# 方法1：f-string（推荐）
print(f"姓名：{name}")
print(f"年龄：{age}岁")
print(f"身高：{height}米")

# 方法2：format()
print("姓名：{}".format(name))
print("年龄：{}岁".format(age))

# 方法3：%格式化（旧版）
print("姓名：%s" % name)
print("年龄：%d岁" % age)
```

---

## 💻 实战项目：简单计算器

### 项目需求
- 可以进行加减乘除运算
- 支持两个数字输入
- 显示计算结果

### 完整代码
```python
# simple_calculator.py

# 获取用户输入
num1 = float(input("请输入第一个数字："))
operator = input("请输入运算符（+、-、*、/）：")
num2 = float(input("请输入第二个数字："))

# 根据运算符计算
if operator == "+":
    result = num1 + num2
    print(f"结果：{num1} + {num2} = {result}")
elif operator == "-":
    result = num1 - num2
    print(f"结果：{num1} - {num2} = {result}")
elif operator == "*":
    result = num1 * num2
    print(f"结果：{num1} × {num2} = {result}")
elif operator == "/":
    if num2 != 0:
        result = num1 / num2
        print(f"结果：{num1} ÷ {num2} = {result}")
    else:
        print("错误：除数不能为零！")
else:
    print("错误：不支持的运算符！")
```

### 运行示例
```
请输入第一个数字：10
请输入运算符（+、-、*、/）：*
请输入第二个数字：5
结果：10 × 5 = 50.0
```

---

## 💻 实战练习

### 练习1：个人信息卡片
```python
# personal_card.py

name = input("请输入你的名字：")
age = int(input("请输入你的年龄："))
height = float(input("请输入你的身高（米）："))
hobby = input("请输入你的爱好：")

print("\n===== 个人信息卡片 =====")
print(f"姓名：{name}")
print(f"年龄：{age}岁")
print(f"身高：{height}米")
print(f"爱好：{hobby}")
print("=" * 25)
```

### 练习2：温度转换器
```python
# temperature.py

# 摄氏度转华氏度
celsius = float(input("请输入摄氏度："))
fahrenheit = celsius * 9 / 5 + 32

print(f"\n{celsius}°C = {fahrenheit}°F")
```

### 练习3：面积计算器
```python
# area_calculator.py

import math

radius = float(input("请输入圆的半径（米）："))
area = math.pi * radius ** 2

print(f"\n圆的面积：{area:.2f} 平方米")
```

---

## 🎓 今日作业

### 必做题（3道）
1. **题1**: 编写程序，计算两个数的和、差、积、商
2. **题2**: 编写程序，将华氏度转换为摄氏度
3. **题3**: 编写程序，计算圆的周长和面积

### 选做题（1道）
4. **题4**: 编写程序，计算长方体的体积

---

## ✅ 学习检查清单

### 基础知识
- [ ] 理解变量概念
- [ ] 掌握基本数据类型
- [ ] 理解类型转换
- [ ] 知道输入输出方法

### 实践能力
- [ ] 能正确定义变量
- [ ] 能进行基本运算
- [ ] 能获取用户输入
- [ ] 能格式化输出

### 项目完成
- [ ] 完成简单计算器
- [ ] 完成个人信息卡片
- [ ] 完成温度转换器

---

## 💡 常见问题

### Q1: input()返回什么类型？
**A**: input()总是返回字符串类型，需要手动转换

### Q2: 如何查看变量类型？
**A**: 使用type()函数
```python
age = 25
print(type(age))    # <class 'int'>
```

### Q3: 字符串和数字能相加吗？
**A**: 不能，需要先转换类型
```python
# 错误
result = "10" + 20    # TypeError

# 正确
result = int("10") + 20    # 30
```

---

## 📝 学习笔记模板

### 今日学习要点
```
1. 变量命名规则：小写+下划线
2. 基本数据类型：int、float、str、bool
3. 类型转换：int()、float()、str()
4. 输入输出：input()、print()
```

### 遇到的问题
```
问题1: 字符串和数字不能相加
解决: 使用int()或float()转换

问题2: 浮点数精度问题
解决: 使用round()四舍五入
```

### 明日计划
```
1. 学习列表操作
2. 学习字典操作
3. 完成名片程序
```

---

## 📊 学习时间分配

| 学习内容 | 时间 | 说明 |
|---------|------|------|
| 变量概念 | 20分钟 | 理解和练习 |
| 数据类型 | 30分钟 | 四种基本类型 |
| 类型转换 | 15分钟 | 转换方法 |
| 计算器项目 | 35分钟 | 完整实现 |
| 作业完成 | 10分钟 | 3道必做题 |
| 复习总结 | 10分钟 | 整理笔记 |
| **总计** | **120分钟** | **2小时** |

---

## 🎉 今日成就

- ✅ 理解变量概念
- ✅ 掌握基本数据类型
- ✅ 学会类型转换
- ✅ 完成计算器项目
- ✅ 完成实战练习

---

## 📞 明日预告

Day 3: 列表与字典
- 学习列表创建与操作
- 学习字典创建与操作
- 学习推导式
- 实战：个人名片程序

---

**创建时间**: 2026-03-23 17:40
**难度**: ⭐⭐ 入门
**学习时间**: 2小时
**状态**: 🔥 火力全开完成

🔥 **恭喜完成Day 2！明天继续！** 🔥
