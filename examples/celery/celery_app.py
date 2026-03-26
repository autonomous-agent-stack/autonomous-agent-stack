from __future__ import annotations

import os

from celery import Celery


def create_celery_app() -> Celery:
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
    result_backend = os.getenv("CELERY_RESULT_BACKEND", broker_url)
    task_serializer = os.getenv("CELERY_TASK_SERIALIZER", "json")
    result_serializer = os.getenv("CELERY_RESULT_SERIALIZER", "json")

    app = Celery(
        "autonomous_agent_stack",
        broker=broker_url,
        backend=result_backend,
        include=["examples.celery.tasks"],
    )
    app.conf.update(
        task_serializer=task_serializer,
        result_serializer=result_serializer,
        accept_content=["json"],
        timezone=os.getenv("TZ", "Asia/Shanghai"),
        enable_utc=True,
        task_default_queue=os.getenv("CELERY_QUEUE", "blitz"),
        task_track_started=True,
    )
    return app


celery_app = create_celery_app()

