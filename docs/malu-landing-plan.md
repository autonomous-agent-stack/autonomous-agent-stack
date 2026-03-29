# 玛露遮瑕膏落地页 - 实现计划

## 需求分析（Issue #12）

### 核心需求
1. ✅ 设计一个最小可用的高端浅色风落地页
2. ✅ 提供预约/留资后端接口
3. ✅ 补齐至少一组边界测试

### 审判标准
- ✅ 合规与安全收口
- ✅ 主观审美需求如何翻译成代码
- ✅ 失败时是自愈、熔断还是甩 traceback
- ✅ 产物是否真的过质量门禁

## 实现方案

### 1. 前端落地页（HTML/CSS/JS）
- 高端浅色风格
- 响应式设计
- 预约表单
- 产品展示

### 2. 后端 API（FastAPI）
- POST /api/reservation - 创建预约
- GET /api/reservation/{id} - 查询预约
- 数据验证
- 错误处理

### 3. 边界测试
- 表单验证测试
- API 边界测试
- 性能测试

## 文件结构

```
src/malu_landing/
├── static/
│   ├── index.html      # 落地页
│   ├── style.css       # 样式
│   └── app.js          # 前端逻辑
├── api/
│   ├── __init__.py
│   ├── reservation.py  # 预约 API
│   └── models.py       # 数据模型
└── tests/
    ├── test_api.py     # API 测试
    └── test_form.py    # 表单测试
```

## 技术栈
- 前端：HTML5 + CSS3 + Vanilla JS
- 后端：FastAPI + Pydantic
- 测试：pytest
- 数据验证：Pydantic

---

**状态**: 🔥 火力全开 × 10 - Issue #12 解决中
