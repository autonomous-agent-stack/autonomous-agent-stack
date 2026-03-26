from __future__ import annotations

from .celery_app import celery_app


if __name__ == "__main__":
    celery_app.worker_main(["worker", "--loglevel=INFO", "--concurrency=2"])

