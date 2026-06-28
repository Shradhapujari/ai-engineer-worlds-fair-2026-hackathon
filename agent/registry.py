"""Phase 2 — tool registry + dispatch."""
from __future__ import annotations

from agent import tools
from agent.parser import ToolCall

REGISTRY = {
    "calculator": tools.calculator,
    "unit_convert": tools.unit_convert,
    "kv_lookup": tools.kv_lookup,
}


def dispatch(call: ToolCall):
    # BUG (Phase 2): direct lookup -> KeyError on an unregistered tool name.
    fn = REGISTRY[call.name]
    return fn(call.arguments)
