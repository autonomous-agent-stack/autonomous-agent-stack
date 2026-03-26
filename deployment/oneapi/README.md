# One API Deployment (LiteLLM-free)

This stack is the safer routing replacement path for Blitz:
- Unified provider gateway
- Channel-level routing and fallback
- Works with existing OpenAI-compatible clients

## Quick Start

```bash
cd deployment/oneapi
cp .env.example .env
# edit secrets in .env first
docker compose --env-file .env up -d
```

After startup:
- Gateway UI: `http://127.0.0.1:3000`
- Default login: `root / 123456` (change immediately)

## Security Baseline

- Pin `ONE_API_IMAGE` to a fixed version tag in production.
- Set a long random `ONE_API_SESSION_SECRET`.
- Never expose MySQL/Redis directly to public networks.
- Rotate the default admin password at first login.

## Suggested Routing Groups

Use One API channel groups to map workload tiers:

- `high_reasoning`: Codex / Claude for architecture and critical planning
- `balanced`: medium-cost, high-quality models for general tasks
- `low_cost`: GLM/local endpoints for ETL, extraction, formatting

Then pass group tokens from your app by task class.

