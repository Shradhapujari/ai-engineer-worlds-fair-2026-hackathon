"""Phase 4 — tool implementations. Each tool takes a single `args` dict."""
from __future__ import annotations

import json
from pathlib import Path

_KV_PATH = Path(__file__).resolve().parent.parent / "test-data" / "kv_data.json"


def calculator(args) -> dict:
    op, a, b = args["op"], args["a"], args["b"]
    if op == "add":
        return {"value": a + b}
    if op == "sub":
        return {"value": a - b}
    if op == "mul":
        return {"value": a * b}
    if op == "divide":
        # BUG (Phase 4): no zero guard -> ZeroDivisionError when b == 0.
        return {"value": a / b}
    raise ValueError(f"unknown op: {op}")


_FACTORS = {"cm": 0.01, "m": 1.0, "km": 1000.0}


def unit_convert(args) -> dict:
    meters = args["value"] * _FACTORS[args["from"]]
    return {"value": meters / _FACTORS[args["to"]], "unit": args["to"]}


def kv_lookup(args):
    data = json.loads(_KV_PATH.read_text())
    val = data.get(args["key"])
    if val is None:
        # BUG surface (Phase 5): a miss returns None, but the formatter assumes
        # a dict result -> AttributeError downstream.
        return None
    return {"value": val}
