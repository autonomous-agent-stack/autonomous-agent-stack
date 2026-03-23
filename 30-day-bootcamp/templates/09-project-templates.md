# 项目模板 - 9个实战项目起始代码

> **版本**: 2.0 | **项目数量**: 9个 | **难度**: ⭐⭐⭐⭐

---

## 📋 项目列表

### 第1周项目（3个）
1. **Hello World程序** - 入门必备
2. **个人名片程序** - 列表与字典
3. **简单计算器** - 条件与循环

### 第2周项目（3个）
4. **成绩计算器** - 函数应用
5. **单位转换器** - 模块化编程
6. **通讯录系统** - 文件操作

### 第3周项目（3个）
7. **个人记账系统** - 数据处理
8. **天气查询工具** - API调用
9. **文件整理工具** - 自动化脚本

### 第4周项目（3个）
10. **个人博客系统** - Web开发
11. **Excel数据分析器** - 数据分析
12. **毕业项目** - 综合应用

---

## 🚀 项目1: Hello World程序

### 模板代码
```python
# hello_world.py

def main():
    """主函数"""
    
    # 打印问候
    print("Hello, World!")
    print("欢迎来到Python世界！")
    
    # 打印个人信息
    print("\n个人信息：")
    print("姓名：张三")
    print("年龄：25")
    print("职业：程序员")
    
    # 打印日期
    from datetime import datetime
    now = datetime.now()
    print(f"\n今天日期：{now.strftime('%Y-%m-%d')}")

if __name__ == "__main__":
    main()
```

### 运行方法
```bash
python3 hello_world.py
```

---

## 🚀 项目2: 个人名片程序

### 模板代码
```python
# personal_card.py

def create_card():
    """创建个人信息名片"""
    card = {}
    
    # 基本信息
    card["name"] = input("姓名：")
    card["age"] = int(input("年龄："))
    card["gender"] = input("性别：")
    
    # 联系方式
    card["phone"] = input("电话：")
    card["email"] = input("邮箱：")
    
    return card

def display_card(card):
    """显示名片"""
    print("\n" + "=" * 50)
    print(" " * 20 + "个人名片" + " " * 20)
    print("=" * 50)
    print(f"\n姓名：{card['name']}")
    print(f"年龄：{card['age']}")
    print(f"性别：{card['gender']}")
    print(f"电话：{card['phone']}")
    print(f"邮箱：{card['email']}")
    print("\n" + "=" * 50)

if __name__ == "__main__":
    card = create_card()
    display_card(card)
```

---

## 🚀 项目3: 简单计算器

### 模板代码
```python
# simple_calculator.py

def add(a, b):
    """加法"""
    return a + b

def subtract(a, b):
    """减法"""
    return a - b

def multiply(a, b):
    """乘法"""
    return a * b

def divide(a, b):
    """除法"""
    if b != 0:
        return a / b
    else:
        return "错误：除数不能为0"

def main():
    """主函数"""
    print("简单计算器\n")
    
    num1 = float(input("请输入第一个数字："))
    operator = input("请输入运算符（+、-、*、/）：")
    num2 = float(input("请输入第二个数字："))
    
    if operator == "+":
        result = add(num1, num2)
    elif operator == "-":
        result = subtract(num1, num2)
    elif operator == "*":
        result = multiply(num1, num2)
    elif operator == "/":
        result = divide(num1, num2)
    else:
        result = "错误：不支持的运算符"
    
    print(f"\n结果：{num1} {operator} {num2} = {result}")

if __name__ == "__main__":
    main()
```

---

## 🚀 项目4: 成绩计算器

### 模板代码
```python
# grade_calculator.py

def calculate_average(grades):
    """计算平均分"""
    return sum(grades) / len(grades)

def get_grade(average):
    """获取等级"""
    if average >= 90:
        return "优秀"
    elif average >= 80:
        return "良好"
    elif average >= 70:
        return "中等"
    elif average >= 60:
        return "及格"
    else:
        return "不及格"

def main():
    """主函数"""
    print("成绩计算器\n")
    
    name = input("请输入学生姓名：")
    subject_count = int(input("请输入科目数量："))
    
    grades = []
    for i in range(subject_count):
        subject = input(f"请输入科目{i+1}名称：")
        score = float(input(f"请输入{subject}成绩："))
        grades.append(score)
    
    # 计算平均分
    average = calculate_average(grades)
    
    # 获取等级
    grade = get_grade(average)
    
    # 显示结果
    print(f"\n学生：{name}")
    print(f"平均分：{average:.1f}")
    print(f"等级：{grade}")

if __name__ == "__main__":
    main()
```

---

## 🚀 项目5: 单位转换器

### 模板代码
```python
# unit_converter.py

# 长度转换
def meters_to_feet(meters):
    """米转英尺"""
    return meters * 3.28084

def feet_to_meters(feet):
    """英尺转米"""
    return feet / 3.28084

# 温度转换
def celsius_to_fahrenheit(celsius):
    """摄氏度转华氏度"""
    return celsius * 9 / 5 + 32

def fahrenheit_to_celsius(fahrenheit):
    """华氏度转摄氏度"""
    return (fahrenheit - 32) * 5 / 9

# 重量转换
def kg_to_pounds(kg):
    """千克转磅"""
    return kg * 2.20462

def pounds_to_kg(pounds):
    """磅转千克"""
    return pounds / 2.20462

def main():
    """主函数"""
    print("单位转换器\n")
    print("1. 长度转换")
    print("2. 温度转换")
    print("3. 重量转换")
    
    choice = input("\n请选择转换类型：")
    
    if choice == "1":
        print("\n1. 米 → 英尺")
        print("2. 英尺 → 米")
        sub_choice = input("请选择转换方向：")
        
        if sub_choice == "1":
            meters = float(input("请输入米数："))
            feet = meters_to_feet(meters)
            print(f"\n{meters}米 = {feet:.2f}英尺")
        elif sub_choice == "2":
            feet = float(input("请输入英尺数："))
            meters = feet_to_meters(feet)
            print(f"\n{feet}英尺 = {meters:.2f}米")
            
    elif choice == "2":
        print("\n1. 摄氏度 → 华氏度")
        print("2. 华氏度 → 摄氏度")
        sub_choice = input("请选择转换方向：")
        
        if sub_choice == "1":
            celsius = float(input("请输入摄氏度："))
            fahrenheit = celsius_to_fahrenheit(celsius)
            print(f"\n{celsius}°C = {fahrenheit:.2f}°F")
        elif sub_choice == "2":
            fahrenheit = float(input("请输入华氏度："))
            celsius = fahrenheit_to_celsius(fahrenheit)
            print(f"\n{fahrenheit}°F = {celsius:.2f}°C")
            
    elif choice == "3":
        print("\n1. 千克 → 磅")
        print("2. 磅 → 千克")
        sub_choice = input("请选择转换方向：")
        
        if sub_choice == "1":
            kg = float(input("请输入千克数："))
            pounds = kg_to_pounds(kg)
            print(f"\n{kg}千克 = {pounds:.2f}磅")
        elif sub_choice == "2":
            pounds = float(input("请输入磅数："))
            kg = pounds_to_kg(pounds)
            print(f"\n{pounds}磅 = {kg:.2f}千克")

if __name__ == "__main__":
    main()
```

---

## 🚀 项目6: 通讯录系统

### 模板代码
```python
# contact_book.py

import json

def load_contacts():
    """加载通讯录"""
    try:
        with open("contacts.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_contacts(contacts):
    """保存通讯录"""
    with open("contacts.json", "w", encoding="utf-8") as f:
        json.dump(contacts, f, ensure_ascii=False, indent=2)

def add_contact(contacts):
    """添加联系人"""
    contact = {
        "name": input("姓名："),
        "phone": input("电话："),
        "email": input("邮箱：")
    }
    contacts.append(contact)
    print(f"已添加：{contact['name']}")
    return contacts

def list_contacts(contacts):
    """列出所有联系人"""
    print("\n通讯录：")
    for i, contact in enumerate(contacts, 1):
        print(f"{i}. {contact['name']} - {contact['phone']}")

def search_contact(contacts):
    """搜索联系人"""
    name = input("请输入要搜索的姓名：")
    found = [c for c in contacts if c['name'] == name]
    
    if found:
        print("\n找到联系人：")
        for contact in found:
            print(f"姓名：{contact['name']}")
            print(f"电话：{contact['phone']}")
            print(f"邮箱：{contact['email']}")
    else:
        print("未找到联系人")

def delete_contact(contacts):
    """删除联系人"""
    name = input("请输入要删除的姓名：")
    index = -1
    
    for i, contact in enumerate(contacts):
        if contact['name'] == name:
            index = i
            break
    
    if index >= 0:
        deleted = contacts.pop(index)
        print(f"已删除：{deleted['name']}")
    else:
        print("未找到联系人")

def main():
    """主函数"""
    contacts = load_contacts()
    
    while True:
        print("\n" + "=" * 40)
        print("通讯录系统")
        print("=" * 40)
        print("1. 添加联系人")
        print("2. 查看通讯录")
        print("3. 搜索联系人")
        print("4. 删除联系人")
        print("5. 退出")
        
        choice = input("\n请选择操作：")
        
        if choice == "1":
            contacts = add_contact(contacts)
            save_contacts(contacts)
        elif choice == "2":
            list_contacts(contacts)
        elif choice == "3":
            search_contact(contacts)
        elif choice == "4":
            contacts = delete_contact(contacts)
            save_contacts(contacts)
        elif choice == "5":
            break
        else:
            print("无效的选择！")

if __name__ == "__main__":
    main()
```

---

## 🚀 项目7: 个人记账系统

### 模板代码
```python
# account_book.py

import json
from datetime import datetime

def load_records():
    """加载记账记录"""
    try:
        with open("account_book.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_records(records):
    """保存记账记录"""
    with open("account_book.json", "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

def add_record(records):
    """添加记录"""
    record = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "type": input("类型（收入/支出）："),
        "category": input("类别："),
        "amount": float(input("金额：")),
        "description": input("备注：")
    }
    records.append(record)
    print(f"已添加：{record['type']} {record['amount']}元")
    return records

def list_records(records):
    """列出所有记录"""
    print("\n记账记录：")
    print(f"{'日期':<12} {'类型':<6} {'类别':<10} {'金额':<10} {'备注':<20}")
    print("-" * 60)
    
    for record in records:
        print(f"{record['date']:<12} {record['type']:<6} {record['category']:<10} {record['amount']:<10.2f} {record['description']:<20}")

def calculate_summary(records):
    """计算汇总"""
    income = sum(r['amount'] for r in records if r['type'] == '收入')
    expense = sum(r['amount'] for r in records if r['type'] == '支出')
    balance = income - expense
    
    print(f"\n收入总计：{income:.2f}元")
    print(f"支出总计：{expense:.2f}元")
    print(f"结余：{balance:.2f}元")

def main():
    """主函数"""
    records = load_records()
    
    while True:
        print("\n" + "=" * 40)
        print("个人记账系统")
        print("=" * 40)
        print("1. 添加记录")
        print("2. 查看记录")
        print("3. 查看汇总")
        print("4. 退出")
        
        choice = input("\n请选择操作：")
        
        if choice == "1":
            records = add_record(records)
            save_records(records)
        elif choice == "2":
            list_records(records)
        elif choice == "3":
            calculate_summary(records)
        elif choice == "4":
            break
        else:
            print("无效的选择！")

if __name__ == "__main__":
    main()
```

---

## 🚀 项目8: 天气查询工具

### 模板代码
```python
# weather_query.py

import requests

def get_weather(city):
    """获取天气信息"""
    # 注意：这里使用的是示例API，实际使用需要申请API密钥
    # 可以使用：和风天气、心知天气等免费API
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid=YOUR_API_KEY"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            return parse_weather(data)
        else:
            return f"查询失败：{response.status_code}"
    except Exception as e:
        return f"发生错误：{e}"

def parse_weather(data):
    """解析天气数据"""
    if data.get('cod') != 200:
        return "城市不存在"
    
    weather = data['weather'][0]['main']
    temp = data['main']['temp'] - 273.15  # Kelvin转摄氏度
    
    return f"""
城市：{data['name']}
天气：{weather}
温度：{temp:.1f}°C
湿度：{data['main']['humidity']}%
风速：{data['wind']['speed']} m/s
"""

def main():
    """主函数"""
    print("天气查询工具\n")
    
    city = input("请输入城市名称（中文或拼音）：")
    
    print("\n正在查询...")
    result = get_weather(city)
    
    print(f"\n{result}")

if __name__ == "__main__":
    main()
```

---

## 🚀 项目9: 文件整理工具

### 模板代码
```python
# file_organizer.py

import os
import shutil
from pathlib import Path

def organize_files(source_dir):
    """整理文件"""
    
    # 文件类型映射
    file_types = {
        '图片': ['.jpg', '.jpeg', '.png', '.gif', '.bmp'],
        '文档': ['.pdf', '.doc', '.docx', '.txt', '.md'],
        '音频': ['.mp3', '.wav', '.flac', '.aac'],
        '视频': ['.mp4', '.avi', '.mkv', '.mov'],
        '压缩包': ['.zip', '.rar', '.7z', '.tar'],
        '代码': ['.py', '.js', '.html', '.css', '.java'],
        '其他': []
    }
    
    # 遍历源目录
    for filename in os.listdir(source_dir):
        filepath = os.path.join(source_dir, filename)
        
        # 跳过目录
        if os.path.isdir(filepath):
            continue
        
        # 获取文件扩展名
        ext = os.path.splitext(filename)[1].lower()
        
        # 确定目标文件夹
        target_folder = '其他'
        for folder, extensions in file_types.items():
            if ext in extensions:
                target_folder = folder
                break
        
        # 创建目标文件夹
        target_dir = os.path.join(source_dir, target_folder)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        
        # 移动文件
        target_path = os.path.join(target_dir, filename)
        print(f"移动：{filename} → {target_folder}/")
        shutil.move(filepath, target_path)
    
    print("\n文件整理完成！")

def main():
    """主函数"""
    print("文件整理工具\n")
    
    source_dir = input("请输入要整理的目录路径：")
    
    # 检查目录是否存在
    if not os.path.exists(source_dir):
        print(f"错误：目录不存在 - {source_dir}")
        return
    
    # 整理文件
    organize_files(source_dir)

if __name__ == "__main__":
    main()
```

---

## 📊 项目统计

### 代码行数统计
- **项目1**: 30行
- **项目2**: 50行
- **项目3**: 60行
- **项目4**: 70行
- **项目5**: 80行
- **项目6**: 120行
- **项目7**: 100行
- **项目8**: 50行
- **项目9**: 80行

### 总计
- **项目数量**: 9个
- **代码行数**: 640+行
- **难度等级**: ⭐⭐⭐⭐

---

## 💡 使用建议

### 如何使用模板
1. **复制模板** - 从本文档复制代码
2. **保存为文件** - 创建对应的.py文件
3. **运行测试** - 执行查看效果
4. **修改完善** - 根据需求添加功能

### 扩展建议
1. **添加错误处理** - try-except
2. **添加日志** - logging模块
3. **添加单元测试** - pytest框架
4. **添加文档** - 文档字符串
5. **代码优化** - PEP 8规范

---

**创建时间**: 2026-03-23 19:10
**项目数量**: 9个
**代码行数**: 640+行
**难度**: ⭐⭐⭐⭐

🔥 **9个项目模板，直接使用！** 🔥
