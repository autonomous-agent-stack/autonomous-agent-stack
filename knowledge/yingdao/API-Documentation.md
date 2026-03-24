# 影刀 API 完整文档

> **更新时间**: 2026-03-24 19:25
> **状态**: 🔍 探索中（已完成 2/11 模块）

---

## 📋 API 模块概览

影刀开放 API 共包含 11 个模块，提供完整的 RPA 自动化控制能力。

| 模块 | 状态 | API 数量 | 说明 |
|------|------|----------|------|
| **鉴权** | ✅ 完成 | 1 | Token 管理 |
| **RPA企业账号** | ✅ 完成 | 5 | 企业账号 CRUD |
| **工作队列** | ✅ 完成 | 4 | 任务队列管理 |
| 任务运行 | ⏳ 待探索 | - | 任务执行控制 |
| JOB运行 | ⏳ 待探索 | - | JOB 管理 |
| 运行日志 | ⏳ 待探索 | - | 日志查询 |
| 机器人相关 | ⏳ 待探索 | - | 机器人管理 |
| 应用相关 | ⏳ 待探索 | - | 应用管理 |
| 文件 | ⏳ 待探索 | - | 文件操作 |
| 任务 | ⏳ 待探索 | - | 任务管理 |
| 通用说明 | ⏳ 待探索 | - | 错误码、状态码 |

---

## 1. 鉴权（Authentication）

### 获取 Token

**请求**:
```
GET https://api.yingdao.com/oapi/token/v2/token/create
    ?accessKeyId=YOUR_KEY
    &accessKeySecret=YOUR_SECRET
```

**响应**:
```json
{
  "data": {
    "accessToken": "520da9c9-694d-4b40-9332-0c179243c88e",
    "expiresIn": 7199
  },
  "code": 200,
  "success": true
}
```

**Token 使用**:
```
Authorization: Bearer ${accessToken}
```

**详细文档**: [API-Authentication.md](./API-Authentication.md)

---

## 2. RPA 企业账号（RPA Enterprise Account）

### 2.1 查询账号列表

**请求**:
```
GET https://api.yingdao.com/oapi/rpa/user/v1/list
```

**参数**:
- `phone` (可选) - 手机号
- `accountKeyword` (可选) - 账号关键词
- `latestLoginTimeBegin/End` (可选) - 最后登录时间范围
- `expiredTimeBegin/End` (可选) - 过期时间范围
- `accountTypes` (可选) - 账号类型（basic/senior）
- `page` (可选) - 页码
- `size` (可选) - 每页数量（默认 20，最大 100）

**响应示例**:
```json
{
  "data": [
    {
      "userUuid": "xxxuuid",
      "loginAccount": "xxxacc@abbr",
      "name": "xxxname",
      "phone": "13312345678",
      "role": "e_user",
      "roleName": "员工",
      "accountType": "basic",
      "accountTypeName": "基础账号",
      "latestLoginTime": "2024-02-28 15:21:51",
      "expiredTime": "2025-01-19 23:59:59"
    }
  ],
  "page": {
    "total": 1,
    "size": 20,
    "page": 1,
    "pages": 1
  },
  "code": 200,
  "success": true
}
```

### 2.2 其他 API

- **创建账号** - 创建新的 RPA 企业账号
- **修改账号** - 修改账号信息
- **删除账号** - 删除账号
- **重置密码** - 重置账号密码

**权限要求**: 调度管理员权限

---

## 3. 工作队列（Work Queue）

### 3.1 重新排队

**请求**:
```
PATCH https://api.yingdao.com/oapi/tool/queue/v1/queueitems/{itemUuid}/reenqueue
```

**参数**:
- `effectiveTime` (必填) - 生效时间（秒级时间戳）
- `expireTime` (可选) - 过期时间（秒级时间戳）
- `description` (可选) - 描述（0-2000 字符）

**功能**: 将队列项从 `processing` 状态重新变更为 `queued` 状态

### 3.2 队列项状态

| 状态 | 说明 |
|------|------|
| `queued` | 排队中 |
| `processing` | 正在处理 |
| `processed` | 已处理 |
| `exception` | 异常 |
| `on hold` | 挂起 |
| `expired` | 超时过期 |

### 3.3 其他 API

- **修改队列项** - 修改队列项属性
- **出列** - 从队列中取出项目
- **新增队列项** - 向队列添加新项目

---

## 4. 通用说明

### 4.1 请求头

所有 API 请求（除鉴权外）都需要携带以下请求头：

```
Authorization: Bearer {accessToken}
Content-Type: application/json
Accept: */*
```

### 4.2 响应格式

**成功响应**:
```json
{
  "code": 200,
  "success": true,
  "data": { ... },
  "requestId": "xxx",
  "serverIp": "xxx",
  "serverInstName": "xxx"
}
```

**失败响应**:
```json
{
  "code": 400,
  "success": false,
  "msg": "错误描述",
  "requestId": "xxx"
}
```

### 4.3 错误码

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | Token 无效或已过期 |
| 403 | 无权限访问 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

**详细状态码**: 参考 [状态码说明](https://www.yingdao.com/yddoc/language/zh-cn/管理文档/开放api/通用说明/状态码说明.html)

---

## 5. 速率限制

- **默认限制**: 100 次/分钟
- **Token 有效期**: 2 小时
- **建议**: 使用 Token 缓存，避免频繁获取

---

## 6. 最佳实践

### 6.1 Token 管理
- ✅ 缓存 token 直到过期
- ✅ 使用 `expiresIn` 字段计算过期时间
- ✅ 提前 5 分钟刷新 token
- ❌ 不要每次请求都获取新 token

### 6.2 错误处理
- ✅ 捕获 401 错误并自动重新获取 token
- ✅ 记录 `requestId` 用于排查
- ✅ 实现重试机制（最多 3 次）
- ❌ 不要忽略错误响应

### 6.3 性能优化
- ✅ 使用分页获取大量数据
- ✅ 批量操作代替单个操作
- ✅ 启用 HTTP/2
- ✅ 使用连接池

---

## 7. 相关链接

- **官方文档**: https://www.yingdao.com/yddoc/rpa/zh-CN/开放API
- **控制台**: https://console.yingdao.com/user/login
- **社区支持**: https://www.yingdao.com/community/
- **PostMan 模板**: [下载](https://winrobot-pub-a-1302949341.cos.ap-shanghai.myqcloud.com/attachment/20240428162341/3102a4140e13188379f432b78884c4f8.json)

---

## 8. 更新记录

- **2026-03-24 19:25**: 完成鉴权、RPA 企业账号、工作队列模块文档
- **2026-03-24 19:20**: 完成鉴权模块文档
