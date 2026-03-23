# Day 1: 环境搭建与基础

> **学习时间**: 2小时 | **难度**: ⭐ 极简 | **目标**: 完成第一个程序

---

## 📋 今日学习目标

- [ ] 安装Python 3.x
- [ ] 安装Claude Code
- [ ] 配置开发环境
- [ ] 编写Hello World程序
- [ ] 理解Python基础概念

---

## 🎯 学习内容

### 1. 安装Python

#### macOS
```bash
# 使用Homebrew安装
brew install python3

# 验证安装
python3 --version
# 输出：Python 3.x.x
```

#### Windows
```bash
# 访问官网下载
https://www.python.org/downloads/

# 下载并安装
# 勾选 "Add Python to PATH"
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3

# 验证安装
python3 --version
```

---

### 2. 安装Claude Code

#### 通过npm安装
```bash
# 安装Node.js（如果未安装）
brew install node

# 安装Claude Code
npm install -g @anthropic/claude-code

# 验证安装
claude --version
```

#### 配置Claude Code
```bash
# 登录
claude auth login

# 选择浏览器方式
# 扫描二维码完成认证
```

---

### 3. 配置开发环境

#### 创建工作目录
```bash
# 创建学习目录
mkdir ~/claude-code-bootcamp
cd ~/claude-code-bootcamp

# 创建Day 1目录
mkdir day-01
cd day-01
```

#### 安装代码编辑器
```bash
# 推荐使用VS Code
brew install --cask visual-studio-code

# 安装Python扩展
# 打开VS Code
# Extensions → 搜索"Python" → 安装
```

---

### 4. 第一个Python程序

#### Hello World程序
```python
# 创建文件 hello.py

# 这是我的第一个Python程序
print("Hello, World!")

# 打印欢迎信息
print("欢迎来到Claude Code训练营！")

# 打印当前日期
print("开始时间：2026-03-23")
```

#### 运行程序
```bash
# 方法1：使用python命令
python3 hello.py

# 方法2：使用Claude Code
claude run hello.py
```

---

### 5. Python基础概念

#### 什么是Python？
- **解释型语言** - 不需要编译，直接运行
- **动态类型** - 不需要声明变量类型
- **高级语言** - 语法简单，接近自然语言

#### 为什么选择Python？
- **易学易用** - 语法简洁
- **功能强大** - 丰富的库
- **应用广泛** - Web、AI、数据分析等
- **社区活跃** - 大量资源

#### Python能做什么？
- **Web开发** - Django、Flask
- **数据分析** - pandas、numpy
- **人工智能** - TensorFlow、PyTorch
- **自动化脚本** - 文件处理、系统管理
- **爬虫开发** - requests、BeautifulSoup

---

## 💻 实战练习

### 练习1：打印个人信息
```python
# 创建文件 profile.py

# 打印个人信息
print("姓名：张三")
print("年龄：25")
print("职业：程序员")
print("爱好：编程、阅读")
```

### 练习2：打印ASCII艺术
```python
# 创建文件 art.py

print("""
  /\\_/\\  
 ( o.o ) 
  > ^ <
""")

print("这是一个可爱的猫咪！")
```

### 练习3：打印日历
```python
# 创建文件 calendar.py

print("2026年3月")
print("日 一 二 三 四 五 六")
print("1  2  3  4  5  6")
print("7  8  9  10 11 12 13")
print("14 15 16 17 18 19 20")
print("21 22 23 24 25 26 27")
print("28 29 30 31")
```

---

## 🎓 今日作业

### 必做题（3道）
1. **题1**: 编写程序，打印5次"Hello World"
2. **题2**: 编写程序，打印一个简单的图形（三角形、正方形等）
3. **题3**: 编写程序，打印你喜欢的名言

### 选做题（1道）
4. **题4**: 编写程序，打印一个复杂的ASCII艺术（如房子、汽车等）

---

## ✅ 学习检查清单

### 环境检查
- [ ] Python 3.x已安装
- [ ] Claude Code已安装
- [ ] 工作目录已创建
- [ ] VS Code已安装并配置

### 基础知识
- [ ] 理解Python是解释型语言
- [ ] 知道Python的应用领域
- [ ] 能运行Python程序
- [ ] 理解print()函数的作用

### 实践能力
- [ ] 能编写简单的print语句
- [ ] 能添加注释
- [ ] 能运行程序
- [ ] 能解决简单的错误

---

## 💡 常见问题

### Q1: python命令找不到？
**A**: 使用`python3`命令代替`python`

### Q2: 安装很慢怎么办？
**A**: 使用国内镜像源
```bash
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple 包名
```

### Q3: Claude Code认证失败？
**A**: 
1. 确保网络连接正常
2. 检查API密钥是否正确
3. 尝试重新认证

### Q4: 中文乱码怎么办？
**A**: 在文件开头添加编码声明
```python
# -*- coding: utf-8 -*-
```

---

## 📝 学习笔记模板

### 今日学习要点
```
1. 安装了Python 3.x
2. 安装了Claude Code
3. 学会了print()函数
4. 理解了Python基础概念
```

### 遇到的问题
```
问题1: python命令找不到
解决: 使用python3命令

问题2: 中文乱码
解决: 添加编码声明
```

### 明日计划
```
1. 学习变量定义
2. 学习数据类型
3. 完成计算器项目
```

---

## 🚀 进阶挑战

### 挑战1：交互式输入
```python
# 创建文件 input.py

name = input("请输入你的名字：")
print(f"你好，{name}！")
```

### 挑战2：计算器雏形
```python
# 创建文件 calculator.py

num1 = float(input("请输入第一个数字："))
num2 = float(input("请输入第二个数字："))

print(f"相加：{num1 + num2}")
print(f"相减：{num1 - num2}")
```

### 挑战3：猜数字游戏（简化版）
```python
# 创建文件 guess.py

import random

secret = random.randint(1, 100)
guess = int(input("猜一个1-100的数字："))

if guess == secret:
    print("恭喜你，猜对了！")
else:
    print(f"猜错了，正确答案是{secret}")
```

---

## 📊 学习时间分配

| 学习内容 | 时间 | 说明 |
|---------|------|------|
| 环境安装 | 30分钟 | Python + Claude Code |
| 基础概念 | 20分钟 | Python介绍 |
| 实战练习 | 40分钟 | 编写程序 |
| 作业完成 | 20分钟 | 3道必做题 |
| 复习总结 | 10分钟 | 整理笔记 |
| **总计** | **120分钟** | **2小时** |

---

## 🎉 今日成就

- ✅ 完成环境搭建
- ✅ 编写第一个程序
- ✅ 理解Python基础
- ✅ 完成实战练习
- ✅ 完成今日作业

---

## 📞 获取帮助

### 遇到问题？
1. 查看FAQ: `../00-resources/06-FAQ.md`
2. 查看调试指南: `../00-resources/05-debug-guide.md`
3. 提问到学习群

### 明日预告
Day 2: 变量与数据类型
- 学习变量定义
- 学习基本数据类型
- 学习类型转换
- 实战：简单计算器

---

**创建时间**: 2026-03-23 17:35
**难度**: ⭐ 极简
**学习时间**: 2小时
**状态**: 🔥 火力全开完成

🔥 **恭喜完成Day 1！明天继续！** 🔥
