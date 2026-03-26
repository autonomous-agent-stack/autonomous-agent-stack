# Cloudflare Tunnel 魔法链接修复脚本

# 问题：PanelAccessService 使用硬编码的 base_url，不读取环境变量

# 修复方法 1：修改 PanelAccessService 源码（推荐）
# 在 src/autoresearch/core/services/panel_access.py 的 __init__ 方法中：

```python
def __init__(
    self,
    *,
    secret: str | None,
    base_url: str = "http://127.0.0.1:8000/api/v1/panel/view",
    # ...
) -> None:
    self._secret = (secret or "").strip()
    
    # ✅ 优先使用环境变量 AUTORESEARCH_BASE_URL
    env_base_url = os.getenv("AUTORESEARCH_BASE_URL", "").strip()
    if env_base_url:
        self._base_url = env_base_url
    else:
        self._base_url = base_url.strip() or "http://127.0.0.1:8000/api/v1/panel/view"
```

# 修复方法 2：使用配置文件（临时方案）
# 创建 ~/.openclaw/config.env

```bash
export AUTORESEARCH_BASE_URL="https://patient-constructed-sake-gsm.trycloudflare.com"
export AUTORESEARCH_BIND_HOST="127.0.0.1"
export AUTORESEARCH_API_PORT=8001
```

# 修复方法 3：修改依赖注入（临时方案）
# 在 src/autoresearch/api/dependencies.py 中修改 get_panel_access_service

```python
def get_panel_access_service() -> PanelAccessService:
    base_url = os.getenv("AUTORESEARCH_BASE_URL", "http://127.0.0.1:8000/api/v1/panel/view")
    
    return PanelAccessService(
        secret=os.getenv("AUTORESEARCH_PANEL_SECRET"),
        base_url=base_url,
        # ...
    )
```

# 当前隧道域名
TUNNEL_URL="https://patient-constructed-sake-gsm.trycloudflare.com"

# 重启服务命令
```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack
pkill -f "uvicorn autoresearch.api.main:app --port 8001"

export AUTORESEARCH_BASE_URL="https://patient-constructed-sake-gsm.trycloudflare.com"
export AUTORESEARCH_BIND_HOST="127.0.0.1"
export AUTORESEARCH_API_PORT=8001

PYTHONPATH=/Volumes/PS1008/Github/autonomous-agent-stack/src:$PYTHONPATH \
nohup .venv/bin/python -m uvicorn autoresearch.api.main:app \
  --host 127.0.0.1 --port 8001 > /tmp/autoresearch_8001.log 2>&1 &
```
