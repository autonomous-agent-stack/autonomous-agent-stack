# 娱乐策划服务

AAS 的 Telegram-only 独立 bounded service，用来生成合法娱乐、音乐和学习资料整理计划。

它根据心情、可用时间、兴趣、专注度和同行场景输出结构化 JSON。默认路径不需要账号。可选 YouTube OAuth profile 只读授权，不自动登录 YouTube Music 或 NotebookLM 网页会话。

## 账号利用

- `youtube_music`：YouTube Premium/Music 账号画像，用于音乐、放松、陪伴场景。
- `youtube_learning`：另一个 Google/YouTube + NotebookLM 账号画像，用于学习、AI、商业、纪录片和资料整理场景。
- NotebookLM：作为学习资料整理流程，生成可手动收集的来源、提问框架和整理步骤。

两个 YouTube profile 共用同一个 Google OAuth Client，但 refresh token 分开存。唯一允许的 scope 是：

```text
https://www.googleapis.com/auth/youtube.readonly
```

## Telegram 授权命令

```text
/youtube-auth youtube_music
/youtube-auth youtube_learning
/youtube-auth-status
/youtube-auth-revoke youtube_music
```

本机环境变量放在 `.env.local` 等非提交文件里：

```text
AUTORESEARCH_GOOGLE_OAUTH_CLIENT_ID=...
AUTORESEARCH_GOOGLE_OAUTH_CLIENT_SECRET=...
AUTORESEARCH_YOUTUBE_OAUTH_REDIRECT_URI=http://127.0.0.1:8001/api/v1/auth/youtube/oauth/callback
```

token 默认保存在 `~/.config/autoresearch/google/youtube_profiles/`，不会回显到 Telegram，也不会写入仓库。

## 版权边界

服务只推荐合法、官方、公开、免费或正常付费账号权益内的内容。禁止输出盗版、破解或绕过付费平台的建议。YouTube Music 只使用官方 YouTube 可授权数据；NotebookLM 仍是手动导入和整理流程。

## 本地调用

```python
from packages.entertainment_curator.service import EntertainmentCuratorTelegramService

service = EntertainmentCuratorTelegramService()
result = service.handle_telegram_message("今晚 1小时 想听音乐放松")
```

AAS 集成层只从 Telegram 进入。Control Plane 记录任务和审计事件，然后本地 immediate result 返回，不进入 worker queue。
