# QUICK START

This guide is optimized for first-time users. If you only do three things, do these:

```bash
cd /Volumes/PS1008/Github/autonomous-agent-stack
make setup
make doctor
make start
```

## What each command does

- `make setup`: create `.venv`, install dependencies, and create `.env` from template if needed
- `make doctor`: run environment checks and print fix hints
- `make start`: run doctor then start API on `127.0.0.1:8001`

After start succeeds:

- API health: `http://127.0.0.1:8001/health`
- Swagger docs: `http://127.0.0.1:8001/docs`
- Panel: `http://127.0.0.1:8001/panel`

## Common tasks

```bash
make help
make test-quick
PORT=8010 make start
```

## Manual mode (without Makefile)

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/doctor.py --port 8001
PYTHONPATH=src .venv/bin/python -m uvicorn autoresearch.api.main:app --host 127.0.0.1 --port 8001 --reload
```

## Troubleshooting

- If doctor shows `FAIL` on dependencies, run `make setup` again.
- If port `8001` is occupied, use `PORT=8010 make start`.
- If import errors appear, always start with `make start` so `PYTHONPATH=src` is set automatically.
