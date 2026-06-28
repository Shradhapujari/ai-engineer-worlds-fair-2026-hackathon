"""Containment: circuit breaker, kill switch, append-only audit log
(architecture spec §2.8).

These bound the blast radius of autonomous code changes. The Guard consults
them before applying a fix and records every outcome. The audit log is the
only observability surface — deliberately minimal, not a dashboard.

Live rollback itself lives in `proxy.supervisor.rollback` (revert source +
reload); the Guard already retries the original input post-swap and rolls back
on a regression. This module governs *whether* a change is allowed and *records*
that it happened.
"""
from __future__ import annotations

import datetime
import json
import os
import time
from typing import Callable, Optional

from omniforge.config import settings


class CircuitBreaker:
    """Cap autonomous changes per rolling time window. Over the cap => deny."""

    def __init__(self, max_changes: int, window_seconds: float,
                 *, clock: Callable[[], float] = time.monotonic) -> None:
        self.max_changes = max_changes
        self.window_seconds = window_seconds
        self._clock = clock
        self._stamps: list[float] = []

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_seconds
        self._stamps = [t for t in self._stamps if t > cutoff]

    def allow(self) -> bool:
        """True if another change is permitted right now (does not record it)."""
        now = self._clock()
        self._prune(now)
        return len(self._stamps) < self.max_changes

    def record(self) -> None:
        """Register that a change was applied."""
        now = self._clock()
        self._prune(now)
        self._stamps.append(now)


def kill_switch_engaged() -> bool:
    """Global stop. Engaged via env OMNIFORGE_KILL=1 or a flag file.
    When engaged, no autonomous change is applied — everything escalates.
    """
    if os.environ.get("OMNIFORGE_KILL", "0") == "1":
        return True
    flag = os.environ.get("OMNIFORGE_KILL_FILE", "")
    return bool(flag) and os.path.exists(flag)


class AuditLog:
    """Append-only JSONL record of every autonomous change. Never rewritten."""

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path or settings.AUDIT_LOG

    def record(self, event: dict) -> dict:
        entry = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 **event}
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def entries(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        with open(self.path) as f:
            return [json.loads(line) for line in f if line.strip()]
