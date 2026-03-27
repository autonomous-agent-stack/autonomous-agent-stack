"""Integrations package with lazy submodule loading."""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "google_workspace",
    "apple_bridge",
    "hitl_approval",
]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return import_module(f".{name}", __name__)
