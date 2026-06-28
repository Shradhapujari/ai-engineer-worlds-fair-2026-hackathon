"""Guard / interceptor (architecture spec §2.1).

Wraps a target function. Clean run = pass-through. On exception: triage →
fixer produces patched source → hot-swap + reload → retry once. If no fix or
the patch still fails, roll back and escalate. Every heal is audited.
"""
from __future__ import annotations

from types import ModuleType
from typing import Callable, Optional

from omniforge.models.schemas import IncidentContext
from omniforge.proxy import triage
from omniforge.proxy.supervisor import hot_swap, rollback


class Escalated(Exception):
    """No safe fix was applied — handed off to a human."""


# fixer: IncidentContext -> patched module source (str), or None to escalate
Fixer = Callable[[IncidentContext], Optional[str]]


class Guard:
    def __init__(self, module: ModuleType, func_name: str, *, fixer: Fixer) -> None:
        self.module = module
        self.func_name = func_name
        self.fixer = fixer
        self.audit: list[dict] = []

    def _fn(self) -> Callable:
        return getattr(self.module, self.func_name)

    def call(self, *args, **kwargs):
        try:
            return self._fn()(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — catch before it crashes the process
            ctx = triage.capture(exc, trigger_input={"args": args, "kwargs": kwargs})

        new_source = self.fixer(ctx)
        if new_source is None:
            self._record(ctx, "escalated")
            raise Escalated(f"no fix for {ctx.error_type} in {ctx.failing_function}")

        handle = hot_swap(self.module, new_source)
        try:
            result = self._fn()(*args, **kwargs)
        except Exception as exc:  # patch didn't fix it
            rollback(handle)
            self._record(ctx, "rolled_back")
            raise Escalated(f"patch failed to heal {ctx.error_type}") from exc

        self._record(ctx, "healed")
        return result

    # let g.answer(...) read naturally
    def __getattr__(self, name: str):
        if name == self.func_name:
            return self.call
        raise AttributeError(name)

    def _record(self, ctx: IncidentContext, status: str) -> None:
        self.audit.append({
            "incident_id": ctx.id,
            "signature": ctx.signature_hash,
            "error_type": ctx.error_type,
            "status": status,
        })
