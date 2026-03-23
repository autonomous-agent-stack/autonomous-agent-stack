# Day 3: 列表与字典

> **学习时间**: 2小时 | **难度**: ⭐⭐⭐ 入门 | **目标**: 掌握列表和字典

---

## 📋 今日学习目标

- [ ] 理解列表概念
- [ ] 掌握列表操作
- [ ] 理解字典概念
- [ ] 掌握字典操作
- [ ] 完成名片程序

---

## 🎯 学习内容

### 1. 列表（List）

#### 创建列表
```python
# 创建空列表
empty_list = []

# 创建包含元素的列表
fruits = ["苹果", "香蕉", "橙子"]
numbers = [1, 2, 3, 4, 5]
mixed = [1, "hello", 3.14, True]

# 查看列表
print(fruits)      # ['苹果', '香蕉', '橙子']
print(numbers)     # [1, 2, 3, 4, 5]
```

#### 访问列表元素
```python
fruits = ["苹果", "香蕉", "橙子", "葡萄", "草莓"]

# 索引从0开始
print(fruits[0])  # 苹果（第一个）
print(fruits[2])  # 橙子（第三个）
print(fruits[-1]) # 草莓（最后一个）
print(fruits[-2]) # 葡萄（倒数第二个）
```

#### 列表切片
```python
numbers = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

# 获取子列表
print(numbers[2:5])    # [2, 3, 4]（索引2到4）
print(numbers[:5])      # [0, 1, 2, 3, 4]（前5个）
print(numbers[5:])      # [5, 6, 7, 8, 9]（第5个开始）
print(numbers[::2])     # [0, 2, 4, 6, 8]（步长为2）
```

#### 列表操作方法
```python
fruits = ["苹果", "香蕉"]

# 添加元素
fruits.append("橙子")      # ['苹果', '香蕉', '橙子']
fruits.insert(1, "葡萄")   # ['苹果', '葡萄', '香蕉', '橙子']

# 删除元素
fruits.remove("香蕉")      # 删除指定元素
fruits.pop()             # 删除最后一个
fruits.pop(0)            # 删除指定位置
del fruits[0]             # 删除指定位置

# 其他操作
print(len(fruits))         # 2（长度）
print("苹果" in fruits)   # True（是否包含）
fruits.sort()             # 排序
fruits.reverse()           # 反转
```

---

### 2. 字典（Dictionary）

#### 创建字典
```python
# 创建空字典
empty_dict = {}

# 创建包含键值对的字典
person = {
    "name": "张三",
    "age": 25,
    "city": "北京"
}

# 查看字典
print(person)    # {'name': '张三', 'age': 25, 'city': '北京'}
```

#### 访问字典元素
```python
person = {"name": "张三", "age": 25, "city": "北京"}

# 访问键
print(person["name"])    # 张三
print(person["age"])     # 25

# 使用get()方法（推荐）
print(person.get("name"))        # 张三
print(person.get("gender"))       # None（键不存在）
print(person.get("gender", "未知"))  # 未知（提供默认值）
```

#### 字典操作方法
```python
person = {"name": "张三", "age": 25}

# 添加键值对
person["city"] = "北京"
person["gender"] = "男"

# 修改键值对
person["age"] = 26

# 删除键值对
del person["city"]
value = person.pop("age")    # 删除并返回值

# 其他操作
print(len(person))                  # 2（长度）
print("name" in person)           # True（键是否存在）
print(person.keys())              # dict_keys(['name', 'gender'])
print(person.values())            # dict_values(['张三', '男'])
print(person.items())             # dict_items([('name', '张三'), ('gender', '男')])
```

---

### 3. 推导式

#### 列表推导式
```python
# 创建0-9的平方列表
squares = [x**2 for x in range(10)]
print(squares)    # [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]

# 过滤偶数
even_numbers = [x for x in range(10) if x % 2 == 0]
print(even_numbers)    # [0, 2, 4, 6, 8]

# 转换列表
names = ["张三", "李四", "王五"]
upper_names = [name.upper() for name in names]
print(upper_names)    # ['张三', '李四', '王五']
```

#### 字典推导式
```python
# 创建数字平方字典
squares = {x: x**2 for x in range(5)}
print(squares)    # {0: 0, 1: 1, 2: 4, 3: 9, 4: 16}

# 创建名字长度字典
names = ["张三", "李四", "王五"]
name_lengths = {name: len(name) for name in names}
print(name_lengths)    # {'张三': 2, '李四': 2, '王五': 2}
```

---

## 💻 实战项目：个人名片程序

### 项目需求
- 记录个人信息
- 记录联系方式
- 显示完整名片

### 完整代码
```python
# personal_card.py

def create_card():
    """创建个人信息名片"""
    
    # 收集信息
    card = {}
    
    # 基本信息
    card["name"] = input("请输入你的姓名：")
    card["age"] = int(input("请输入你的年龄："))
    card["gender"] = input("请输入你的性别：")
    
    # 联系方式
    card["phone"] = input("请输入你的电话：")
    card["email"] = input("请输入你的邮箱：")
    card["wechat"] = input("请输入你的微信号：")
    
    # 其他信息
    card["city"] = input("请输入你所在城市：")
    card["company"] = input("请输入你的公司：")
    card["position"] = input("请输入你的职位：")
    
    return card

def display_card(card):
    """显示名片"""
    
    print("\n" + "=" * 50)
    print(" " * 20 + "个人名片" + " " * 20)
    print("=" * 50)
    print()
    
    # 基本信息
    print("【基本信息】")
    print(f"  姓名：{card.get('name', '未填写')}")
    print(f"  年龄：{card.get('age', '未填写')}岁")
    print(f"  性别：{card.get('gender', '未填写')}")
    print(f"  城市：{card.get('city', '未填写')}")
    print()
    
    # 联系方式
    print("【联系方式】")
    print(f"  电话：{card.get('phone', '未填写')}")
    print(f"  邮箱：{card.get('email', '未填写')}")
    print(f"  微信：{card.get('wechat', '未填写')}")
    print()
    
    # 职业信息
    print("【职业信息】")
    print(f"  公司：{card.get('company', '未填写')}")
    print(f"  职位：{card.get('position', '未填写')}")
    print()
    
    print("=" * 50)

def main():
    """主函数"""
    print("欢迎使用个人名片生成器！\n")
    
    # 创建名片
    card = create_card()
    
    # 显示名片
    display_card(card)
    
    # 保存到文件（可选）
    save = input("\n是否保存到文件？(y/n): ")
    if save.lower() == 'y':
        with open(f"{card['name']}_card.txt", "w", encoding="utf-8") as f:
            f.write(str(card))
        print(f"已保存到 {card['name']}_card.txt")

if __name__ == "__main__":
    main()
```

### 运行示例
```
欢迎使用个人名片生成器！

请输入你的姓名：张三
请输入你的年龄：25
请输入你的性别：男
请输入你的电话：138-1234-5678
请输入你的邮箱：zhangsan@example.com
请输入你的微信号：zhangsan123
请输入你所在城市：北京
请输入你的公司：某某科技有限公司
请输入你的职位：软件工程师

==================================================
                    个人名片                    
==================================================

【基本信息】
  姓名：张三
  年龄：25岁
  性别：男
  城市：北京

【联系方式】
  电话：138-1234-5678
  邮箱：zhangsan@example.com
  微信：zhangsan123

【职业信息】
  公司：某某科技有限公司
  职位：软件工程师

==================================================
```

---

## 💻 实战练习

### 练习1：购物清单
```python
# shopping_list.py

shopping_list = []

# 添加商品
shopping_list.append("苹果")
shopping_list.append("香蕉")
shopping_list.append("牛奶")

# 显示清单
print("购物清单：")
for i, item in enumerate(shopping_list, 1):
    print(f"{i}. {item}")

print(f"\n总计：{len(shopping_list)}件商品")
```

### 练习2：成绩管理
```python
# grade_manager.py

students = {
    "张三": {"语文": 90, "数学": 85, "英语": 88},
    "李四": {"语文": 78, "数学": 92, "英语": 85},
    "王五": {"语文": 85, "数学": 88, "英语": 90}
}

# 计算平均分
for name, scores in students.items():
    avg = sum(scores.values()) / len(scores)
    print(f"{name}的平均分：{avg:.1f}")
```

### 练习3：通讯录
```python
# contact_book.py

contacts = []

def add_contact():
    name = input("姓名：")
    phone = input("电话：")
    contacts.append({"name": name, "phone": phone})
    print(f"已添加：{name}")

def list_contacts():
    print("\n通讯录：")
    for contact in contacts:
        print(f"{contact['name']}: {contact['phone']}")

def search_contact():
    name = input("搜索姓名：")
    for contact in contacts:
        if contact['name'] == name:
            print(f"{name}: {contact['phone']}")
            return
    print("未找到联系人")

# 主循环
while True:
    print("\n1. 添加联系人")
    print("2. 查看通讯录")
    print("3. 搜索联系人")
    print("4. 退出")
    
    choice = input("请选择：")
    
    if choice == "1":
        add_contact()
    elif choice == "2":
        list_contacts()
    elif choice == "3":
        search_contact()
    elif choice == "4":
        break
```

---

## 🎓 今日作业

### 必做题（3道）
1. **题1**: 创建一个包含10个数字的列表，计算它们的和、平均值
2. **题2**: 创建一个字典，存储5个人的姓名和年龄，按年龄排序
3. **题3**: 使用列表推导式，找出1-100中所有能被3和5整除的数

### 选做题（1道）
4. **题4**: 创建一个嵌套字典，存储班级信息（班级 → 学生 → 成绩）

---

## ✅ 学习检查清单

### 基础知识
- [ ] 理解列表概念
- [ ] 理解字典概念
- [ ] 掌握列表切片
- [ ] 掌握字典访问

### 实践能力
- [ ] 能创建和操作列表
- [ ] 能创建和操作字典
- [ ] 能使用推导式
- [ ] 能完成名片项目

---

## 💡 常见问题

### Q1: 列表和元组的区别？
**A**: 列表可变（可以修改），元组不可变（不能修改）

```python
# 列表
fruits = ["苹果", "香蕉"]
fruits.append("橙子")  # ✅ 可以修改

# 元组
colors = ("红", "绿", "蓝")
colors.append("黄")  # ❌ 不能修改
```

### Q2: 字典的键可以是列表吗？
**A**: 不能，字典的键必须是不可变类型（字符串、数字、元组等）

### Q3: 如何复制列表？
**A**: 使用copy()方法或切片

```python
# 方法1
new_list = old_list.copy()

# 方法2
new_list = old_list[:]
```

---

**创建时间**: 2026-03-23 19:05
**难度**: ⭐⭐⭐ 入门
**学习时间**: 2小时
**状态**: 🔥 火力全开完成

🔥 **恭喜完成Day 3！明天继续！** 🔥
