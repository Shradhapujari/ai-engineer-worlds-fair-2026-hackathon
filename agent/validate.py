"""Phase 3 — argument validation / coercion."""
from __future__ import annotations

from agent.parser import ToolCall


def validate(call: ToolCall) -> ToolCall:
    # BUG (Phase 3): no coercion/validation — wrong-typed args flow straight to
    # the tools (e.g. a string where a number is expected -> TypeError downstream).
    return call
