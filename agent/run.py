"""Agent entrypoint — the callable OmniForge's Guard wraps.

Pipeline: parse -> validate -> dispatch (execute) -> format.
Pure: this module never imports omniforge. The Guard seam lives in runner.py.
"""
from __future__ import annotations

from agent.format import format_result
from agent.parser import parse_call
from agent.registry import dispatch
from agent.validate import validate


def run(raw) -> str:
    call = parse_call(raw)
    validate(call)
    result = dispatch(call)
    return format_result(call, result)
