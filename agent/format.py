"""Phase 5 — result formatting."""
from __future__ import annotations

from agent.parser import ToolCall


def format_result(call: ToolCall, result) -> str:
    # BUG (Phase 5): assumes result is a non-None dict; a None result
    # (e.g. a lookup miss) -> AttributeError on .get().
    return str(result.get("value"))
