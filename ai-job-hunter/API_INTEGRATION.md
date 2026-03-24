# API 集成指南

本文档详细说明如何集成各个求职平台的 API。

## 📋 目录

- [LinkedIn](#linkedin)
- [Indeed](#indeed)
- [Glassdoor](#glassdoor)
- [Hired](#hired)
- [AngelList (Wellfound)](#angellist)

---

## LinkedIn

### API 概述

LinkedIn 提供了多种 API，求职功能主要通过 **LinkedIn Jobs API** 实现。

### 申请步骤

1. **创建开发者账户**

   访问 [LinkedIn Developer Portal](https://developer.linkedin.com/)，使用 LinkedIn 账号登录。

2. **创建应用**

   - 点击 "Create App"
   - 填写应用信息：
     - App Name: `AI Job Hunter`
     - App Description: `Job search and application tracking tool`
     - Website URL: `http://localhost:8000`
     - Privacy Policy URL: `http://localhost:8000/privacy`
   - 同意服务条款并提交

3. **申请 API 权限**

   - 进入应用详情页
   - 在 "Products" 标签页申请以下产品：
     - **Member Permissions**: `r_liteprofile`, `r_emailaddress`
     - **Job Permissions**: `r_jobs`, `rw_jobs`（如果需要）

4. **获取凭证**

   - 进入 "Auth" 标签页
   - 记录以下信息：
     - `Client ID`
     - `Client Secret`

### API 使用示例

```python
import requests
import json

class LinkedInAPI:
    """LinkedIn API 封装"""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.base_url = "https://api.linkedin.com/v2"

    def authenticate(self) -> str:
        """OAuth 2.0 认证"""
        auth_url = "https://www.linkedin.com/oauth/v2/accessToken"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        response = requests.post(auth_url, params=params)
        data = response.json()
        self.access_token = data.get("access_token")
        return self.access_token

    def search_jobs(self, keywords: str, location: str = "") -> dict:
        """搜索职位"""
        if not self.access_token:
            self.authenticate()

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        # LinkedIn 的 Jobs API 需要特殊权限
        # 以下是示例结构，实际使用需要申请访问权限
        url = f"{self.base_url}/jobs"
        params = {
            "keywords": keywords,
            "location": location
        }

        response = requests.get(url, headers=headers, params=params)
        return response.json()

# 使用示例
linkedin = LinkedInAPI(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET"
)

jobs = linkedin.search_jobs("AI Engineer", "San Francisco")
```

### 注意事项

- LinkedIn API 有严格的速率限制（Rate Limits）
- 某些功能需要申请企业级访问权限
- 个人开发者账户可能无法访问完整的 Jobs API
- 建议使用 LinkedIn 的 RSS Feed 或爬虫作为替代方案

---

## Indeed

### API 概述

Indeed 提供 **Indeed Publisher API**，可以用于搜索职位。

### 申请步骤

1. **注册 Publisher 账户**

   访问 [Indeed Publisher Program](https://www.indeed.com/publisher) 注册。

2. **创建 API 密钥**

   - 登录 Publisher Dashboard
   - 进入 API 部分
   - 创建新的 API 密钥（Publisher ID）

3. **获取凭证**

   - `publisher_id`: 你的 Publisher ID
   - `api_key`: API 密钥（如果提供）

### API 使用示例

```python
import requests
from urllib.parse import quote

class IndeedAPI:
    """Indeed API 封装"""

    def __init__(self, publisher_id: str):
        self.publisher_id = publisher_id
        self.base_url = "https://api.indeed.com/v1"

    def search_jobs(
        self,
        query: str,
        location: str = "",
        radius: int = 25,
        job_type: str = "fulltime"
    ) -> dict:
        """搜索职位"""
        params = {
            "publisher": self.publisher_id,
            "q": quote(query),
            "l": quote(location) if location else "",
            "radius": radius,
            "jt": job_type,
            "v": "2",  # API version
            "format": "json",
            "limit": 25,
            "userip": "1.2.3.4",  # 替换为你的 IP
            "useragent": "Mozilla/5.0"
        }

        url = f"{self.base_url}/jobs"
        response = requests.get(url, params=params)
        return response.json()

# 使用示例
indeed = IndeedAPI(publisher_id="YOUR_PUBLISHER_ID")

jobs = indeed.search_jobs(
    query="Python Developer",
    location="San Francisco",
    job_type="fulltime"
)

# 处理结果
for job in jobs.get("results", []):
    print(f"{job['jobtitle']} - {job['company']}")
```

### 注意事项

- Indeed API 是免费的，但有请求限制（通常每月 100,000 次）
- 需要提供 `userip` 和 `useragent` 参数
- 某些字段可能需要特殊权限才能访问

---

## Glassdoor

### API 概述

Glassdoor 提供 **API Partner Program**，可以访问公司评价、薪资和职位信息。

### 申请步骤

1. **申请 Partner 计划**

   访问 [Glassdoor API Partner](https://www.glassdoor.com/developer/apiOverview.htm) 提交申请。

2. **等待审核**

   - Glassdoor 会审核你的申请
   - 审核通过后会发送凭证

3. **获取凭证**

   - `partner_id`: 你的 Partner ID
   - `api_key`: API 密钥

### API 使用示例

```python
import requests

class GlassdoorAPI:
    """Glassdoor API 封装"""

    def __init__(self, partner_id: str, api_key: str):
        self.partner_id = partner_id
        self.api_key = api_key
        self.base_url = "https://api.glassdoor.com/api/api.htm"

    def search_jobs(self, query: str, location: str = "") -> dict:
        """搜索职位"""
        params = {
            "t.p": self.partner_id,
            "t.k": self.api_key,
            "format": "json",
            "v": "1",
            "action": "jobs-progression",
            "q": query,
            "l": location
        }

        response = requests.get(self.base_url, params=params)
        return response.json()

    def get_company_reviews(self, company: str) -> dict:
        """获取公司评价"""
        params = {
            "t.p": self.partner_id,
            "t.k": self.api_key,
            "format": "json",
            "v": "1",
            "action": "employers",
            "q": company
        }

        response = requests.get(self.base_url, params=params)
        return response.json()

# 使用示例
glassdoor = GlassdoorAPI(
    partner_id="YOUR_PARTNER_ID",
    api_key="YOUR_API_KEY"
)

jobs = glassdoor.search_jobs("Data Scientist", "New York")
```

### 注意事项

- Glassdoor API 需要付费订阅
- 免费版本功能受限
- 建议申请试用版本评估

---

## Hired

### API 概述

Hired 提供 API 访问，但主要面向企业和招聘机构。

### 申请步骤

1. **联系 Hired**

   - 访问 [Hired API Documentation](https://hired.com/api)
   - 发送邮件至 api@hired.com 申请访问

2. **提供信息**

   - 说明使用目的
   - 提供公司信息
   - 解释预期使用量

3. **获取凭证**

   - 等待审核通过
   - 获取 API 密钥

### API 使用示例

```python
import requests

class HiredAPI:
    """Hired API 封装"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://hired.com/api/v1"

    def search_jobs(self, keywords: str, location: str = "") -> dict:
        """搜索职位"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        params = {
            "q": keywords,
            "location": location
        }

        response = requests.get(
            f"{self.base_url}/jobs",
            headers=headers,
            params=params
        )
        return response.json()

# 使用示例
hired = HiredAPI(api_key="YOUR_API_KEY")
jobs = hired.search_jobs("Software Engineer", "Remote")
```

### 注意事项

- Hired API 主要面向企业用户
- 个人开发者可能难以获得访问权限
- 建议直接使用 Hired 网站进行职位搜索

---

## AngelList (Wellfound)

### API 概述

AngelList (现已更名为 Wellfound) 提供 API 访问，用于搜索创业公司和职位。

### 申请步骤

1. **创建 AngelList 账户**

   访问 [AngelList](https://angel.co) 注册账户。

2. **申请 API 访问**

   - 访问 [AngelList API](https://angel.co/api)
   - 注册应用
   - 获取 API 密钥

3. **获取凭证**

   - `client_id`: 应用 Client ID
   - `client_secret`: 应用 Client Secret
   - `access_token`: OAuth 访问令牌

### API 使用示例

```python
import requests

class AngelListAPI:
    """AngelList API 封装"""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.base_url = "https://api.angel.co/1"

    def authenticate(self) -> str:
        """OAuth 2.0 认证"""
        # 需要用户授权流程
        # 这里是简化示例
        auth_url = f"{self.base_url}/oauth/token"
        params = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": "AUTHORIZATION_CODE"  # 从授权回调获取
        }

        response = requests.post(auth_url, params=params)
        data = response.json()
        self.access_token = data.get("access_token")
        return self.access_token

    def search_jobs(self, keywords: str, location: str = "") -> dict:
        """搜索职位"""
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        params = {
            "q": keywords,
            "location": location
        }

        response = requests.get(
            f"{self.base_url}/jobs",
            headers=headers,
            params=params
        )
        return response.json()

# 使用示例
angellist = AngelListAPI(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET"
)
angellist.authenticate()

jobs = angellist.search_jobs("Full Stack Developer", "Remote")
```

### 注意事项

- AngelList API 有访问频率限制
- 某些功能需要付费订阅
- 建议查看最新的 API 文档，因为 API 可能有更新

---

## 🔐 安全建议

1. **不要在代码中硬编码 API 密钥**
   - 使用环境变量
   - 使用配置文件
   - 使用密钥管理服务

2. **使用环境变量**

   ```bash
   export LINKEDIN_CLIENT_ID="your_client_id"
   export LINKEDIN_CLIENT_SECRET="your_client_secret"
   ```

   ```python
   import os

   client_id = os.getenv("LINKEDIN_CLIENT_ID")
   client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
   ```

3. **实施速率限制**

   ```python
   import time
   from functools import wraps

   def rate_limit(calls_per_second=1):
       def decorator(func):
           @wraps(func)
           def wrapper(*args, **kwargs):
               time.sleep(1.0 / calls_per_second)
               return func(*args, **kwargs)
           return wrapper
       return decorator
   ```

4. **错误处理**

   ```python
   try:
       jobs = api.search_jobs("Python Developer")
   except requests.exceptions.RequestException as e:
       print(f"API 请求失败: {e}")
   except Exception as e:
       print(f"未知错误: {e}")
   ```

---

## 📚 参考资源

- [LinkedIn API Documentation](https://learn.microsoft.com/en-us/linkedin/shared/references/v2/job-search/)
- [Indeed Publisher API](https://www.indeed.com/publisher/api-documentation)
- [Glassdoor API](https://www.glassdoor.com/developer/apiOverview.htm)
- [AngelList API](https://angel.co/api)

---

## 🆘 常见问题

### Q: 为什么某些平台 API 无法访问？

A: 许多平台的 API 需要企业级访问权限或付费订阅。作为个人开发者，可能需要使用爬虫或网站 RSS Feed 作为替代方案。

### Q: 如何处理 API 速率限制？

A: 实施请求队列、缓存结果、使用代理 IP 分发请求。

### Q: 可以免费使用这些 API 吗？

A: Indeed API 是免费的，其他平台（LinkedIn、Glassdoor、Hired）通常需要付费或特殊权限。

### Q: 如果无法获取 API 访问权限怎么办？

A: 可以使用网页爬虫技术（如 Selenium、BeautifulSoup）抓取公开的职位信息，但要注意遵守网站的 robots.txt 和使用条款。

---

祝你集成顺利！ 🚀
