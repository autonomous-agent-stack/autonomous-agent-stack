# API 接入指南

## 快速开始

### 基础 URL

```
http://localhost:8000
```

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
# 方式一：直接运行
python src/api/main.py

# 方式二：使用 uvicorn（推荐开发环境）
uvicorn src/api/main:app --host 0.0.0.0 --port 8000 --reload
```

### 验证服务

```bash
curl http://localhost:8000/health
```

响应：
```json
{
  "status": "healthy",
  "service": "autonomous-agent-ui-api"
}
```

---

## 认证方式

当前版本为开发环境，**暂无认证要求**。

生产环境建议：
- API Key 认证（Header: `X-API-Key`）
- JWT Token 认证（Header: `Authorization: Bearer <token>`）

---

## API 端点总览

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 服务信息 |
| `/health` | GET | 健康检查 |
| `/api/v1/openclaw/agents/tree` | GET | DAG 节点树 |
| `/api/v1/openclaw/agents/status` | GET | 系统状态 |
| `/api/v1/paperclip/budget` | POST | 预算指令 |
| `/api/v1/paperclip/callback` | POST | 执行回调 |

---

## 错误码说明

| 状态码 | 含义 | 处理建议 |
|--------|------|----------|
| 200 | 成功 | 正常处理响应 |
| 400 | 请求参数错误 | 检查请求体格式 |
| 404 | 资源不存在 | 检查 URL 路径 |
| 422 | 参数验证失败 | 检查字段类型和必填项 |
| 500 | 服务器内部错误 | 联系管理员或重试 |

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

---

## 速率限制

| 环境 | 限制 |
|------|------|
| 开发 | 无限制 |
| 生产 | 100 req/min/IP |

超限响应：
```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 60
}
```

---

## 交互式文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
