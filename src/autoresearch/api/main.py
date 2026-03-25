from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI

from autoresearch import __version__
from autoresearch.api.routers import evaluations, experiments, optimizations, reports, variants


app = FastAPI(
    title="autoresearch API",
    version=__version__,
    description=(
        "API-first orchestration layer for evaluation, reporting, variant generation, "
        "optimization, and experiment management."
    ),
)

app.include_router(evaluations.router)
app.include_router(reports.router)
app.include_router(variants.router)
app.include_router(optimizations.router)
app.include_router(experiments.router)


@app.get("/", tags=["meta"])
def read_root() -> dict[str, Any]:
    return {
        "name": app.title,
        "version": app.version,
        "status": "ok",
        "docs_url": app.docs_url,
    }


@app.get("/healthz", tags=["meta"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


def run() -> None:
    import uvicorn

    host = os.getenv("AUTORESEARCH_API_HOST", "127.0.0.1")
    port = int(os.getenv("AUTORESEARCH_API_PORT", "8000"))
    uvicorn.run("autoresearch.api.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()
