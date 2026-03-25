# 多语言文档标准

> **标准时间**: 2026-03-22 16:22
> **适用范围**: 所有开源项目文档

---

## 📋 标准

### **必须包含的语言版本**

每个项目必须包含：
1. ✅ **README.md** - 默认中文简体
2. ✅ **README-EN.md** - 英文版
3. ✅ **README-ZH-TW.md** - 中文繁体版

---

## 📝 命名规范

### **文件命名**

```
README.md          # 默认中文简体
README-EN.md       # 英文版
README-ZH-TW.md    # 中文繁体版

LEARNING.md        # 学习笔记（中文简体）
LEARNING-EN.md     # 学习笔记（英文）
LEARNING-ZH-TW.md  # 学习笔记（中文繁体）
```

---

## 🔗 语言切换

### **顶部语言切换**

每个README顶部必须包含：

**中文简体版**:
```markdown
**[English](./README-EN.md)** | **[繁體中文](./README-ZH-TW.md)** | 简体中文
```

**英文版**:
```markdown
**[简体中文](./README.md)** | **[繁體中文](./README-ZH-TW.md)** | English
```

**中文繁体版**:
```markdown
**[简体中文](./README.md)** | **[English](./README-EN.md)** | 繁體中文
```

---

## 📊 翻译优先级

### **高优先级** 🔴

1. ✅ **LEARNING.md** - 学习笔记（教育价值最高）
2. ✅ **Quick Start** - 快速开始
3. ✅ **Installation** - 安装指南

### **中优先级** 🟡

1. ✅ **Core Concepts** - 核心概念
2. ✅ **Examples** - 示例代码
3. ✅ **FAQ** - 常见问题

### **低优先级** 🟢

1. ✅ **Changelog** - 更新日志
2. ✅ **Contributing** - 贡献指南
3. ✅ **License** - 许可证

---

## 🚀 执行计划

### **Phase 1** (立即)

**需要翻译的项目**:
1. ✅ Conductor - 英文README
2. ✅ Pi Mono - 英文README
3. ✅ Agent Orchestrator - 英文README

**任务**:
- [ ] 创建中文简体版
- [ ] 创建中文繁体版
- [ ] 添加语言切换

---

### **Phase 2** (本周)

**已有中文的项目**:
1. ✅ Cherry Studio - 多语言

**任务**:
- [ ] 检查繁体版是否存在
- [ ] 创建繁体版（如不存在）
- [ ] 统一语言切换格式

---

### **Phase 3** (持续)

**新项目标准**:
- [ ] 所有新项目必须有3种语言版本
- [ ] 创建时即包含语言切换
- [ ] 定期检查翻译质量

---

## 💡 翻译工具

### **简体 → 繁体**

**在线工具**:
- https://www.chineseconverter.com/zh-cn/convert
- https://tool.lu/zhconvert/

**命令行**:
```bash
# 使用 opencc
opencc -i README.md -o README-ZH-TW.md -c s2tw.json
```

---

### **简体 → 英文**

**AI 翻译**:
- Claude / GPT-4 翻译
- 人工校对技术术语

**注意事项**:
- ✅ 保留代码块不翻译
- ✅ 保留链接不翻译
- ✅ 技术术语保持英文

---

## 📋 检查清单

### **新项目检查**

- [ ] README.md（中文简体）
- [ ] README-EN.md（英文）
- [ ] README-ZH-TW.md（中文繁体）
- [ ] 语言切换链接正确
- [ ] 翻译质量检查

### **现有项目检查**

- [ ] 是否缺少某种语言版本
- [ ] 语言切换是否完整
- [ ] 翻译是否准确

---

## 🎯 目标

**3个月内**:
- ✅ 所有Fork的项目都有3种语言版本
- ✅ 所有新文档都符合标准
- ✅ 语言切换100%覆盖

**大佬，多语言标准已建立！现在开始执行翻译！** 🚀
