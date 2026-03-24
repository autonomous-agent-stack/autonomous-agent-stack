# 影刀 API 鉴权文档

## 概述

影刀开放 API 使用 OAuth 2.0 风格的 Token 认证机制，通过 `accessKeyId` 和 `accessKeySecret` 获取临时 `accessToken`，然后在后续请求中使用该 token 进行身份验证。

---

## 前置操作

### 1. 获取 API 密钥

1. 使用**企业管理员账号**登录影刀控制台
   - 控制台地址：https://console.yingdao.com/user/login

2. 进入 **API 配置界面**

3. 创建密钥对：
   - `accessKeyId` - 访问密钥 ID
   - `accessKeySecret` - 访问密钥密码

4. **安全建议**：
   - 为每个对接系统创建独立的密钥对
   - 妥善保管密钥，不要泄露
   - 定期更换密钥

---

## 获取 accessToken

### 请求信息

| 参数 | 值 | 说明 |
|------|-----|------|
| **HTTP URL** | `https://api.yingdao.com/oapi/token/v2/token/create` | 专有云企业请使用专有云地址 |
| **HTTP Method** | `GET` | - |

### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `accessKeyId` | string | 是 | 访问密钥 ID |
| `accessKeySecret` | string | 是 | 访问密钥密码 |

### 请求示例

```
GET https://api.yingdao.com/oapi/token/v2/token/create?accessKeyId=MerC5cKPSa7BTG1A@platform&accessKeySecret=mqTxhk4aK1v7PpDtfQU6dCMgnrR50HFc
```

### 响应体

| 名称 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `code` | int | 是 | 状态码，200 表示成功 |
| `success` | boolean | 是 | 是否成功 |
| `msg` | string | 是 | 消息 |
| `data` | object | 是 | 数据对象 |
| `∟ accessToken` | string | 是 | 访问令牌 |
| `∟ expiresIn` | int | 是 | 有效期（秒） |

### 响应示例

```json
{
  "data": {
    "accessToken": "520da9c9-694d-4b40-9332-0c179243c88e",
    "expiresIn": 7199
  },
  "code": 200,
  "success": true,
  "requestId": "601cf6274032e2cc335c97d2"
}
```

---

## Token 有效期管理

### 有效期规则

- **最大有效期**：2 小时（7200 秒）
- **未过期时**：请求返回老的 `accessToken`
- **已过期时**：请求返回新的 `accessToken`

### 缓存建议

1. **使用 expiresIn 字段**：
   - 不要自定义缓存时间
   - 使用响应中的 `expiresIn` 字段（单位：秒）
   - 避免客户端缓存与服务器不一致

2. **推荐缓存策略**：
   ```python
   # 伪代码
   token = cache.get("yingdao_token")
   if not token or token.expired:
       response = get_new_token()
       token = response.data.accessToken
       expires_at = now() + response.data.expiresIn
       cache.set("yingdao_token", token, expires_at)
   ```

3. **提前刷新**：
   - 建议在 token 过期前 5 分钟刷新
   - 避免在业务高峰期刷新

---

## 使用 accessToken

### 请求头设置

在每次调用 API 时，需要在 HTTP header 中添加 `Authorization` 字段：

```
Authorization: Bearer ${accessToken}
```

**注意事项**：
- `Bearer` 和 `accessToken` 之间必须有一个空格
- `Bearer` 首字母大写
- 每次请求都需要携带此 header

### Python 示例

```python
import requests

# 1. 获取 token
def get_access_token(access_key_id, access_key_secret):
    url = "https://api.yingdao.com/oapi/token/v2/token/create"
    params = {
        "accessKeyId": access_key_id,
        "accessKeySecret": access_key_secret
    }
    response = requests.get(url, params=params)
    data = response.json()
    if data["success"]:
        return data["data"]["accessToken"], data["data"]["expiresIn"]
    else:
        raise Exception(f"获取 token 失败: {data['msg']}")

# 2. 使用 token 调用 API
def call_api(access_token, endpoint, params=None):
    url = f"https://api.yingdao.com/oapi/{endpoint}"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(url, headers=headers, params=params)
    return response.json()

# 使用示例
access_key_id = "your_access_key_id"
access_key_secret = "your_access_key_secret"

token, expires_in = get_access_token(access_key_id, access_key_secret)
result = call_api(token, "task/v2/task/list")
print(result)
```

---

## 错误处理

### 常见错误

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| 401 | Token 无效或已过期 | 重新获取 token |
| 403 | 无权限访问该接口 | 检查账号权限 |
| 404 | 接口不存在 | 检查 URL 是否正确 |
| 500 | 服务器内部错误 | 联系技术支持 |

### 状态码说明

详细状态码说明请参考：
https://www.yingdao.com/yddoc/language/zh-cn/管理文档/开放api/通用说明/状态码说明.html

---

## 模板和工具

### PostMan 模板

下载地址：
https://winrobot-pub-a-1302949341.cos.ap-shanghai.myqcloud.com/attachment/20240428162341/3102a4140e13188379f432b78884c4f8.json

使用方法：
1. 下载 JSON 文件
2. 在 PostMan 中导入
3. 替换 `accessKeyId` 和 `accessKeySecret`
4. 发送请求测试

### Java 模板

暂无官方 Java 模板，可参考以下实现：

```java
import okhttp3.*;

public class YingdaoAPI {
    private static final String BASE_URL = "https://api.yingdao.com/oapi/";
    private String accessToken;
    
    public void login(String accessKeyId, String accessKeySecret) throws Exception {
        OkHttpClient client = new OkHttpClient();
        
        HttpUrl url = HttpUrl.parse(BASE_URL + "token/v2/token/create")
            .newBuilder()
            .addQueryParameter("accessKeyId", accessKeyId)
            .addQueryParameter("accessKeySecret", accessKeySecret)
            .build();
        
        Request request = new Request.Builder()
            .url(url)
            .get()
            .build();
        
        Response response = client.newCall(request).execute();
        String jsonData = response.body().string();
        JSONObject json = new JSONObject(jsonData);
        
        if (json.getBoolean("success")) {
            this.accessToken = json.getJSONObject("data").getString("accessToken");
        } else {
            throw new Exception("登录失败: " + json.getString("msg"));
        }
    }
    
    public String callAPI(String endpoint) throws Exception {
        OkHttpClient client = new OkHttpClient();
        
        Request request = new Request.Builder()
            .url(BASE_URL + endpoint)
            .header("Authorization", "Bearer " + accessToken)
            .get()
            .build();
        
        Response response = client.newCall(request).execute();
        return response.body().string();
    }
}
```

---

## 最佳实践

### 1. 密钥管理

- ✅ 使用环境变量存储密钥
- ✅ 定期更换密钥（建议 90 天）
- ✅ 不同环境使用不同密钥
- ❌ 不要在代码中硬编码密钥
- ❌ 不要在日志中打印密钥

### 2. Token 管理

- ✅ 缓存 token 直到过期
- ✅ 使用 expiresIn 字段计算过期时间
- ✅ 提前 5 分钟刷新 token
- ❌ 不要每次请求都获取新 token

### 3. 错误处理

- ✅ 捕获 401 错误并自动重新获取 token
- ✅ 记录错误日志用于排查
- ✅ 实现重试机制（最多 3 次）
- ❌ 不要忽略错误响应

### 4. 性能优化

- ✅ 使用连接池
- ✅ 启用 HTTP/2
- ✅ 压缩请求和响应
- ✅ 批量操作代替单个操作

---

## 相关链接

- **影刀控制台**: https://console.yingdao.com/user/login
- **官方文档**: https://www.yingdao.com/yddoc/rpa/zh-CN/开放API
- **社区支持**: https://www.yingdao.com/community/
- **状态码说明**: https://www.yingdao.com/yddoc/language/zh-cn/管理文档/开放api/通用说明/状态码说明.html

---

## 更新记录

- **2026-03-24**: 初始版本，完整记录鉴权流程
