# Celery LAN Dispatch Example

This example shows how to fan out Blitz tasks from an M1 host to LAN workers.

## Install

```bash
python3 -m pip install "celery>=5.3" "redis>=5.0"
```

## Start Redis

```bash
docker run --rm -p 6379:6379 redis:7-alpine
```

## Start Worker (any machine in LAN)

```bash
export CELERY_BROKER_URL=redis://<redis-host>:6379/0
export CELERY_RESULT_BACKEND=redis://<redis-host>:6379/1
export PYTHONPATH=$(pwd)
python3 -m examples.celery.worker_entry
```

## Enable Blitz to use Celery dispatch

```bash
export BLITZ_DISPATCH_BACKEND=celery
export CELERY_BROKER_URL=redis://<redis-host>:6379/0
export CELERY_RESULT_BACKEND=redis://<redis-host>:6379/1
export CELERY_QUEUE=blitz
export CELERY_TASK_NAME=autonomous_agent_stack.execute_task
```

Then call `/api/v1/blitz/execute` with `enable_distributed_dispatch=true`.

## Notes

- `DistributedGateway` returns a Celery task id immediately.
- Your worker can be replaced with real agent-runtime code in `tasks.py`.

