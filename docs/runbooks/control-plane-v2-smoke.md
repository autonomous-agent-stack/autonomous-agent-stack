# Control Plane v2 Smoke 固化 / Control Plane v2 Smoke Hardening

## 用途 / Purpose

中文：`make smoke-cpv2` 会启动一个使用临时 SQLite 数据库的本地 API，验证 Telegram-like YouTube approval、`/approve`、worker claim/report、v2 task/run projection 与 timeline 事件闭环。

English: `make smoke-cpv2` starts a local API with a temporary SQLite database and validates the full Telegram-like YouTube approval, `/approve`, worker claim/report, v2 task/run projection, and timeline event loop.

## 执行 / Run

中文：默认优先使用 `127.0.0.1:8001`；如果端口已占用，会自动尝试 `127.0.0.1:8011`。

English: By default, the smoke prefers `127.0.0.1:8001`; if that port is occupied, it automatically tries `127.0.0.1:8011`.

```bash
make smoke-cpv2
```

## 成功标准 / Success Criteria

中文：脚本成功时输出一行 compact JSON；失败时以非 0 状态退出，并在 stderr 输出失败原因和 API 日志尾部。

English: On success, the script prints one compact JSON line; on failure, it exits non-zero and writes the failure reason plus the API log tail to stderr.
