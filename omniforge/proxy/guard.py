"""Guard / interceptor (architecture spec §2.1).

Wraps a target function. Clean run = pass-through. On exception: triage →
fixer produces patched source → hot-swap + reload → retry once. If no fix or
the patch still fails, roll back and escalate. Every heal is audited.
"""
from __future__ import annotations

from types import ModuleType
from typing import Callable, Optional

from omniforge.healer.rollback import AuditLog, CircuitBreaker
from omniforge.models.schemas import IncidentContext
from omniforge.proxy import triage
from omniforge.proxy.supervisor import hot_swap, rollback


class Escalated(Exception):
    """No safe fix was applied — handed off to a human."""


# fixer: IncidentContext -> patched module source (str), or None to escalate
Fixer = Callable[[IncidentContext], Optional[str]]
# kill_switch: () -> True to forbid all autonomous changes
KillSwitch = Callable[[], bool]


class Guard:
    def __init__(
        self,
        module: ModuleType,
        func_name: str,
        *,
        fixer: Fixer,
        breaker: Optional[CircuitBreaker] = None,
        kill_switch: Optional[KillSwitch] = None,
        audit_log: Optional[AuditLog] = None,
    ) -> None:
        self.module = module
        self.func_name = func_name
        self.fixer = fixer
        self.breaker = breaker
        self.kill_switch = kill_switch
        self.audit_log = audit_log
        self.audit: list[dict] = []

    def _fn(self) -> Callable:
        return getattr(self.module, self.func_name)

    def call(self, *args, **kwargs):
        try:
            return self._fn()(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — catch before it crashes the process
            ctx = triage.capture(exc, trigger_input={"args": args, "kwargs": kwargs})

        # Containment gates — checked before any autonomous change.
        if self.kill_switch is not None and self.kill_switch():
            self._record(ctx, "kill_switch")
            raise Escalated("kill switch engaged — autonomous healing disabled")
        if self.breaker is not None and not self.breaker.allow():
            self._record(ctx, "circuit_open")
            raise Escalated("circuit breaker open — change cap reached")

        new_source = self.fixer(ctx)
        if new_source is None:
            self._record(ctx, "escalated")
            raise Escalated(f"no fix for {ctx.error_type} in {ctx.failing_function}")

        handle = hot_swap(self.module, new_source)
        if self.breaker is not None:
            self.breaker.record()  # an autonomous change was applied
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
        event = {
            "incident_id": ctx.id,
            "signature": ctx.signature_hash,
            "error_type": ctx.error_type,
            "status": status,
        }
        self.audit.append(event)
        if self.audit_log is not None:
            self.audit_log.record(event)
