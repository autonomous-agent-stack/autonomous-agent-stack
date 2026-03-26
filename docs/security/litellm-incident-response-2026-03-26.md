# LiteLLM Supply-Chain Incident Response (2026-03-26)

## What We Verified

As of 2026-03-26:

- LiteLLM official issue confirms compromised versions: `1.82.7`, `1.82.8`.
- PyPI currently exposes `1.82.6` as latest stable and no longer lists `1.82.7` / `1.82.8` in the simple index.

Primary references:

- https://github.com/BerriAI/litellm/issues/24512
- https://github.com/BerriAI/litellm/issues/24518
- https://pypi.org/project/litellm/
- https://pypi.org/simple/litellm/

## Local Guardrails Added

- Scanner script: `scripts/security/check_litellm_incident.py`
- Detects:
  - Installed high-risk versions (`1.82.7`, `1.82.8`)
  - Lockfile pins to those versions
  - `litellm_init.pth` in site-packages or `~/.cache/uv`
  - Persistence markers under `~/.config/sysmon/`

Run:

```bash
python3 scripts/security/check_litellm_incident.py
```

Exit code:

- `0`: no high-risk indicators found
- `1`: risk indicators found (immediate incident response required)

## Incident Response Checklist

1. Isolate host from network if high-risk indicators exist.
2. Remove compromised environments and rebuild virtualenv from clean base.
3. Purge package caches (`pip`, `uv`) before reinstalling.
4. Rotate all potentially exposed credentials:
   - Cloud keys (AWS/GCP/Azure)
   - SSH keys
   - API keys in `.env`
   - CI/CD secrets
5. Audit Kubernetes for suspicious pods/secrets access if cluster credentials were present.

## Routing Replacement (No LiteLLM)

- Gateway option: `deployment/oneapi/` (Docker Compose template)
- LAN dispatch option: `BLITZ_DISPATCH_BACKEND=celery` with `examples/celery/`

