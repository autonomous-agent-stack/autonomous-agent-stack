from __future__ import annotations

from autoresearch.core.runtime_identity import get_runtime_identity
from autoresearch.shared.models import OpenClawSessionCreateRequest

from .router import router, compat_router
from ._guard import (  # re-exported for test access
    _CHAT_RATE_WINDOWS,
    _validate_secret_token,
    _guard_webhook_replay_and_rate,
)
from ._messages import (  # re-exported for test access
    _status_diag_value,
    _telegram_queue_ack_message,
    _telegram_two_column_table,
)

__all__ = ["router", "compat_router"]
