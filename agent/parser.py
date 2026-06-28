"""Phase 1 — tool-call parser. Raw model output (JSON) -> ToolCall."""
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class ToolCall:
    name: str
    arguments: dict


def parse_call(raw) -> ToolCall:
    obj = json.loads(raw) if isinstance(raw, str) else raw
    # BUG (Phase 1): direct key access -> KeyError when 'name' is absent.
    return ToolCall(name=obj["name"], arguments=obj["arguments"])
