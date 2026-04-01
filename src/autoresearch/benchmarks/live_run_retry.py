from __future__ import annotations

from typing import Any

LIVE_RUN_RETRY_RESULT_VALUES = (
    "not_requested",
    "not_needed",
    "not_attempted",
    "recovered",
    "exhausted",
)


def build_live_run_retry_result_counts() -> dict[str, int]:
    return {value: 0 for value in LIVE_RUN_RETRY_RESULT_VALUES}


def resolve_live_run_retry_result(
    *,
    explicit: Any,
    succeeded: bool,
    retry_budget: int,
    retry_attempts_used: int,
) -> str:
    normalized = normalize_live_run_retry_result(
        explicit,
        succeeded=succeeded,
        retry_budget=retry_budget,
        retry_attempts_used=retry_attempts_used,
    )
    if normalized is not None:
        return normalized
    if retry_budget <= 0:
        return "not_requested"
    if retry_attempts_used <= 0:
        return "not_needed" if succeeded else "not_attempted"
    return "recovered" if succeeded else "exhausted"


def normalize_live_run_retry_result(
    value: Any,
    *,
    succeeded: bool,
    retry_budget: int,
    retry_attempts_used: int,
) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text in LIVE_RUN_RETRY_RESULT_VALUES:
        return text
    if text == "retried":
        if retry_budget <= 0:
            return "not_requested"
        if retry_attempts_used <= 0:
            return "not_needed" if succeeded else "not_attempted"
        return "recovered" if succeeded else "exhausted"
    return None
