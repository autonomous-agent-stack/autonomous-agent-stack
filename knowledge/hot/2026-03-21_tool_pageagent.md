# PageAgent - 阿里开源网页AI化工具

**来源**: https://x.com/btcqzy1/status/2033773816363815019
**GitHub**: https://github.com/alibaba/page-agent
**官方**: 阿里巴巴
**发现日期**: 2026-03-21
**优先级**: ⭐⭐⭐ 高

## 核心创新

一行代码，让任意网页秒变AI Agent可控工具

## 技术突破

### 1. 拒绝截图OCR
- 不靠截图、不耗多余Token
- 直接基于DOM树进行逻辑操作
- 完美适配复杂B2B系统、ERP、Admin后台

### 2. Text-based DOM操作
- 跳过截图，直达底层
- 纯前端JS把网站变成AI Native App
- 像读代码一样读懂网页

### 3. 闭环执行验证
- 操作比人类更快
- 比视觉Agent更准
- 稳如磐石

## 快速开始

### Demo版（一行代码）
```html
<script src="https://cdn.jsdelivr.net/npm/@page-agent/demo"></script>
```

### 生产环境
```bash
npm install @page-agent/core
```

支持：
- OpenAI兼容
- 本地模型
- Ollama
- 自定义LLM

## 核心优势

1. **极简接入**: 无需Browser Extension和Python
2. **无需OCR**: 直接DOM操作，节省Token
3. **稳定可靠**: 不受UI像素级变化影响
4. **速度快**: 操作比人类更快

## 适用场景

- B2B系统自动化
- ERP后台操作
- Admin管理面板
- 数据提取
- 表单填充
- 网页监控

## 热度数据

- GitHub Star: 9.6k+
- Fork: 747次
- GitHub Trending榜第一

## 待实践

- [ ] Demo测试
- [ ] 生产环境集成
- [ ] 自定义LLM配置
- [ ] B2B场景测试
- [ ] 与其他方案对比
