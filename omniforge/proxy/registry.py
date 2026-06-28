"""Dynamic handler registry (architecture spec §2.6).

Handlers are keyed by name so a single function can be atomically rebound after
a hot-swap without restarting the process.
"""
from __future__ import annotations

from typing import Callable


class HandlerRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, Callable] = {}

    def register(self, name: str, fn: Callable) -> None:
        self._handlers[name] = fn

    def get(self, name: str) -> Callable:
        return self._handlers[name]

    def rebind(self, name: str, fn: Callable) -> None:
        self._handlers[name] = fn
