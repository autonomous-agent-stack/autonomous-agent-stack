# Day 3: 列表与字典

> **学习时间**: 2小时 | **难度**: ⭐⭐ 入门 | **目标**: 掌握列表和字典

---

## 📋 今日学习目标

- [ ] 理解列表概念
- [ ] 掌握列表操作
- [ ] 理解字典概念
- [ ] 掌握字典操作
- [ ] 完成个人名片项目

---

## 🎯 学习内容

### 1. 列表（List）

#### 创建列表
```python
# 空列表
empty_list = []

# 包含元素
fruits = ["苹果", "香蕉", "橙子"]
numbers = [1, 2, 3, 4, 5]
mixed = ["张三", 25, True, 3.14]

# 打印列表
print(fruits)    # ['苹果', '香蕉', '橙子']
```

#### 访问元素
```python
fruits = ["苹果", "香蕉", "橙子", "葡萄", "草莓"]

# 索引从0开始
print(fruits[0])    # 苹果（第1个）
print(fruits[1])    # 香蕉（第2个）
print(fruits[4])    # 草莓（第5个）

# 负索引（从后往前）
print(fruits[-1])   # 草莓（最后1个）
print(fruits[-2])   # 葡萄（最后2个）
```

#### 切片操作
```python
fruits = ["苹果", "香蕉", "橙子", "葡萄", "草莓"]

# 切片：[start:end:step]
print(fruits[1:3])    # ['香蕉', '橙子']（第2-3个）
print(fruits[:3])     # ['苹果', '香蕉', '橙子']（前3个）
print(fruits[2:])     # ['橙子', '葡萄', '草莓']（第3个开始）
print(fruits[::2])    # ['苹果', '橙子', '草莓']（每隔1个）
```

#### 常用操作
```python
fruits = ["苹果", "香蕉", "橙子"]

# 添加元素
fruits.append("葡萄")           # 追加到末尾
fruits.insert(1, "草莓")       # 在指定位置插入

# 删除元素
fruits.remove("香蕉")           # 删除指定值
fruits.pop()                   # 删除并返回最后一个元素
del fruits[0]                  # 删除指定位置

# 查找元素
print("苹果" in fruits)         # True（是否存在）
print(fruits.index("橙子"))      # 2（位置）
print(fruits.count("苹果"))      # 1（出现次数）

# 列表长度
print(len(fruits))              # 4

# 排序
fruits.sort()                   # 升序排序
fruits.sort(reverse=True)        # 降序排序
```

---

### 2. 列表推导式

#### 基础语法
```python
# [表达式 for 变量 in 序列]

# 创建平方列表
squares = [x**2 for x in range(1, 11)]
print(squares)
# [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]

# 创建偶数列表
evens = [x for x in range(1, 11) if x % 2 == 0]
print(evens)
# [2, 4, 6, 8, 10]
```

#### 实际应用
```python
# 过滤列表
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
# 大于5的数
greater_than_5 = [x for x in numbers if x > 5]
print(greater_than_5)    # [6, 7, 8, 9, 10]

# 转换列表
names = ["张三", "李四", "王五"]
# 添加"先生"
greetings = [f"{name}先生" for name in names]
print(greetings)    # ['张三先生', '李四先生', '王五先生']

# 嵌套列表推导式
matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
# 展平列表
flattened = [num for row in matrix for num in row]
print(flattened)    # [1, 2, 3, 4, 5, 6, 7, 8, 9]
```

---

### 3. 字典（Dictionary）

#### 创建字典
```python
# 空字典
empty_dict = {}

# 包含键值对
student = {
    "name": "张三",
    "age": 18,
    "class": "高三(1)班"
}

# 打印字典
print(student)
# {'name': '张三', 'age': 18, 'class': '高三(1)班'}
```

#### 访问元素
```python
student = {
    "name": "张三",
    "age": 18,
    "class": "高三(1)班"
}

# 通过键访问值
print(student["name"])        # 张三
print(student["age"])         # 18
print(student["class"])       # 高三(1)班

# 使用get()安全访问（键不存在不报错）
print(student.get("name"))         # 张三
print(student.get("gender"))       # None（不存在）
print(student.get("gender", "未知"))  # 未知（默认值）
```

#### 修改与添加
```python
student = {"name": "张三", "age": 18}

# 修改值
student["age"] = 19
print(student["age"])    # 19

# 添加键值对
student["gender"] = "男"
student["school"] = "第一中学"
print(student)
# {'name': '张三', 'age': 19, 'gender': '男', 'school': '第一中学'}
```

#### 常用操作
```python
student = {
    "name": "张三",
    "age": 18,
    "class": "高三(1)班",
    "grade": 90
}

# 删除键值对
del student["grade"]           # 删除指定键
value = student.pop("class")    # 删除并返回值

# 查看所有键
print(student.keys())          # dict_keys(['name', 'age'])

# 查看所有值
print(student.values())        # dict_values(['张三', 18])

# 查看所有键值对
print(student.items())         # dict_items([('name', '张三'), ('age', 18)])

# 检查键是否存在
print("name" in student)      # True
print("gender" in student)    # False

# 获取长度
print(len(student))            # 2
```

---

### 4. 字典推导式

#### 基础语法
```python
# {键表达式: 值表达式 for 变量 in 序列}

# 创建平方字典
squares = {x: x**2 for x in range(1, 6)}
print(squares)
# {1: 1, 2: 4, 3: 9, 4: 16, 5: 25}

# 创建首字母映射
words = ["apple", "banana", "cherry"]
first_letters = {word: word[0] for word in words}
print(first_letters)
# {'apple': 'a', 'banana': 'b', 'cherry': 'c'}
```

#### 实际应用
```python
# 过滤字典
scores = {"张三": 90, "李四": 85, "王五": 95}
# 优秀成绩（>=90）
excellent = {name: score for name, score in scores.items() if score >= 90}
print(excellent)    # {'张三': 90, '王五': 95}

# 转换字典
fruits = ["apple", "banana", "cherry"]
# 创建水果价格字典
prices = {fruit: 5.0 for fruit in fruits}
print(prices)    # {'apple': 5.0, 'banana': 5.0, 'cherry': 5.0}
```

---

## 💻 实战项目：个人名片

### 项目需求
- 显示姓名、年龄、职业、爱好
- 使用字典存储信息
- 使用列表存储爱好
- 格式化输出

### 完整代码
```python
# personal_card.py

# 创建名片信息
card = {
    "name": "张三",
    "age": 25,
    "gender": "男",
    "profession": "Python开发工程师",
    "location": "北京",
    "phone": "13800138000",
    "email": "zhangsan@example.com",
    "hobbies": ["编程", "阅读", "旅行", "摄影"]
}

# 格式化输出名片
print("=" * 50)
print(" " * 10 + "个人名片" + " " * 10)
print("=" * 50)

print(f"姓名：{card['name']}")
print(f"年龄：{card['age']}岁")
print(f"性别：{card['gender']}")
print(f"职业：{card['profession']}")
print(f"所在地：{card['location']}")
print(f"电话：{card['phone']}")
print(f"邮箱：{card['email']}")

print("\n爱好：")
for i, hobby in enumerate(card['hobbies'], 1):
    print(f"  {i}. {hobby}")

print("=" * 50)
print(f"更新时间：2026-03-23")
print("=" * 50)
```

### 运行示例
```
==================================================
          个人名片
==================================================
姓名：张三
年龄：25岁
性别：男
职业：Python开发工程师
所在地：北京
电话：13800138000
邮箱：zhangsan@example.com

爱好：
  1. 编程
  2. 阅读
  3. 旅行
  4. 摄影
==================================================
更新时间：2026-03-23
==================================================
```

### 交互式版本
```python
# interactive_card.py

def create_card():
    """创建交互式名片"""
    print("===== 创建个人名片 =====")
    
    # 收集信息
    name = input("请输入姓名：")
    age = input("请输入年龄：")
    gender = input("请输入性别：")
    profession = input("请输入职业：")
    location = input("请输入所在地：")
    
    # 收集爱好
    hobbies = []
    print("\n请输入爱好（输入'done'结束）：")
    while True:
        hobby = input(f"  爱好{len(hobbies)+1}: ")
        if hobby.lower() == 'done':
            break
        hobbies.append(hobby)
    
    # 创建名片
    card = {
        "name": name,
        "age": age,
        "gender": gender,
        "profession": profession,
        "location": location,
        "hobbies": hobbies,
        "created_date": "2026-03-23"
    }
    
    # 显示名片
    print("\n" + "=" * 50)
    print(" " * 10 + "个人名片" + " " * 10)
    print("=" * 50)
    print(f"姓名：{card['name']}")
    print(f"年龄：{card['age']}岁")
    print(f"性别：{card['gender']}")
    print(f"职业：{card['profession']}")
    print(f"所在地：{card['location']}")
    
    if card['hobbies']:
        print("\n爱好：")
        for i, hobby in enumerate(card['hobbies'], 1):
            print(f"  {i}. {hobby}")
    else:
        print("\n爱好：暂无")
    
    print("=" * 50)
    print(f"创建时间：{card['created_date']}")
    print("=" * 50)
    
    return card

# 执行
if __name__ == "__main__":
    card = create_card()
```

---

## 💻 实战练习

### 练习1：购物车
```python
# shopping_cart.py

# 购物车列表
cart = ["苹果", "香蕉", "橙子"]

# 添加商品
cart.append("葡萄")
cart.append("草莓")

# 移除已购买商品
cart.remove("香蕉")

# 计算总价
prices = {
    "苹果": 5.0,
    "香蕉": 3.5,
    "橙子": 6.0,
    "葡萄": 8.0,
    "草莓": 10.0
}

total = sum(prices[item] for item in cart)

print("购物车：")
for item in cart:
    print(f"  - {item}：{prices[item]}元")

print(f"\n总价：{total}元")
```

### 练习2：学生成绩管理
```python
# student_scores.py

# 学生成绩字典
students = {
    "张三": {"语文": 85, "数学": 90, "英语": 88},
    "李四": {"语文": 92, "数学": 87, "英语": 90},
    "王五": {"语文": 78, "数学": 95, "英语": 82}
}

# 计算平均分
for name, scores in students.items():
    average = sum(scores.values()) / len(scores)
    print(f"{name}的平均分：{average:.1f}")
```

### 练习3：词频统计
```python
# word_frequency.py

text = "Python is great. Python is easy. Python is powerful."
words = text.lower().replace('.', '').split()

# 统计词频
frequency = {}
for word in words:
    frequency[word] = frequency.get(word, 0) + 1

print("词频统计：")
for word, count in sorted(frequency.items(), key=lambda x: x[1], reverse=True):
    print(f"  {word}: {count}次")
```

---

## 🎓 今日作业

### 必做题（3道）
1. **题1**: 创建一个待办事项列表，支持添加、删除、显示
2. **题2**: 创建一个通讯录字典，支持增删改查
3. **题3**: 统计一段文字中每个字符出现的次数

### 选做题（1道）
4. **题4**: 创建一个简单的库存管理系统（商品、数量、价格）

---

## ✅ 学习检查清单

### 基础知识
- [ ] 理解列表概念
- [ ] 掌握列表操作
- [ ] 理解字典概念
- [ ] 掌握字典操作

### 实践能力
- [ ] 能创建和操作列表
- [ ] 能使用列表推导式
- [ ] 能创建和操作字典
- [ ] 能使用字典推导式

### 项目完成
- [ ] 完成个人名片项目
- [ ] 完成购物车练习
- [ ] 完成成绩管理练习

---

## 💡 常见问题

### Q1: 列表和元组的区别？
**A**: 
- 列表（list）：可变，使用[]
- 元组（tuple）：不可变，使用()

```python
# 列表
fruits = ["苹果", "香蕉"]
fruits.append("橙子")  # ✅ 可以修改

# 元组
coordinates = (10, 20)
coordinates.append(30)  # ❌ 不能修改
```

### Q2: 字典的键有什么限制？
**A**: 
- 必须是不可变类型
- 唯一（不能重复）

```python
# ✅ 可以作为键
d = {
    "name": "张三",      # 字符串
    123: "数字",        # 数字
    (1, 2): "元组"     # 元组
}

# ❌ 不能作为键
d = {
    [1, 2]: "列表",      # 列表（可变）
    {"key": "value"}: "字典"  # 字典（可变）
}
```

### Q3: 如何复制列表和字典？
**A**: 使用copy()或切片

```python
# 列表复制
original = [1, 2, 3]
copy_list = original.copy()
copy_list2 = original[:]

# 字典复制
original = {"a": 1, "b": 2}
copy_dict = original.copy()
copy_dict2 = dict(original)
```

---

## 📝 学习笔记模板

### 今日学习要点
```
1. 列表：可变序列，支持增删改查
2. 字典：键值对存储，快速查找
3. 列表推导式：简洁创建列表
4. 字典推导式：简洁创建字典
```

### 遇到的问题
```
问题1: 列表索引越界
解决: 使用len()检查长度

问题2: 字典键不存在报错
解决: 使用get()方法
```

### 明日计划
```
1. 学习条件判断
2. 学习循环语句
3. 完成评级系统项目
```

---

## 📊 学习时间分配

| 学习内容 | 时间 | 说明 |
|---------|------|------|
| 列表概念与操作 | 35分钟 | 创建、访问、修改 |
| 列表推导式 | 15分钟 | 高级用法 |
| 字典概念与操作 | 35分钟 | 创建、访问、修改 |
| 字典推导式 | 15分钟 | 高级用法 |
| 名片项目 | 15分钟 | 完整实现 |
| 作业完成 | 5分钟 | 3道必做题 |
| **总计** | **120分钟** | **2小时** |

---

## 🎉 今日成就

- ✅ 理解列表和字典
- ✅ 掌握推导式
- ✅ 完成名片项目
- ✅ 完成实战练习
- ✅ 完成今日作业

---

## 📞 明日预告

Day 4: 条件判断与循环
- 学习if/elif/else
- 学习for循环
- 学习while循环
- 实战：猜数字游戏

---

**创建时间**: 2026-03-23 18:40
**难度**: ⭐⭐ 入门
**学习时间**: 2小时
**状态**: 🔥 火力全开完成

🔥 **恭喜完成Day 3！明天继续！** 🔥
