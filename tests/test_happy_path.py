"""Phase 0 — the agent works on valid tool calls (no proxy)."""
import json
from pathlib import Path

import pytest

from agent.run import run

VALID = json.loads(
    (Path(__file__).resolve().parent.parent / "test-data" / "valid_calls.json").read_text()
)


@pytest.mark.parametrize(
    "call,expected",
    [
        (VALID[0], "5"),       # calculator add 2 + 3
        (VALID[1], "2.5"),     # calculator divide 10 / 4
        (VALID[2], "1.0"),     # unit_convert 100 cm -> m
        (VALID[3], "Paris"),   # kv_lookup capital_of_france
    ],
)
def test_valid_calls(call, expected):
    assert run(call) == expected
