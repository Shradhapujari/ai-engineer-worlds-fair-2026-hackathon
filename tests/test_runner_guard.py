"""Phase 0 exit gate — a valid call runs end-to-end under the OmniForge Guard.

Skips if OmniForge (and its deps) aren't importable in this environment; the
agent itself is fully tested without the proxy.
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def test_guarded_valid_call_passes_through():
    pytest.importorskip("pydantic")  # an OmniForge dependency
    try:
        from runner import guarded_run
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"OmniForge not importable: {exc}")

    from agent.run import run

    call = json.loads((ROOT / "test-data" / "valid_calls.json").read_text())[0]
    assert guarded_run(call) == run(call)
