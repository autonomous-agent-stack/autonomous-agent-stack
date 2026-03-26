from __future__ import annotations

from typing import Any

from .celery_app import celery_app


@celery_app.task(name="autonomous_agent_stack.execute_task")
def execute_task(task_payload: dict[str, Any]) -> dict[str, Any]:
    """Minimal LAN worker task for Blitz dispatch demo.

    Replace this function body with your real agent execution logic.
    """
    metadata = task_payload.get("metadata", {})
    return {
        "status": "accepted",
        "message": "task enqueued and handled by celery worker",
        "task_name": task_payload.get("task_name"),
        "session_id": task_payload.get("session_id"),
        "metadata": metadata,
    }

