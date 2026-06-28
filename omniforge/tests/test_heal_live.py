"""Live end-to-end heal: Guard catches a real crash, Gemini writes the patch,
the patcher applies it, hot-swap reloads, the call recovers — no human.

Run:  GOOGLE_CLOUD_PROJECT=... GOOGLE_CLOUD_LOCATION=global pytest -m live
Skipped by default.
"""
import importlib
import sys

import pytest

from omniforge.proxy.guard import Guard
from omniforge.proxy import triage
from omniforge.healer.diagnose import generate_patch
from omniforge.healer.patcher import apply_unified_diff

# self-contained target: snapshot == whole file, so the model's diff context
# matches the file the patcher applies against.
ORIG = '''def answer(d):
    return "temp=" + str(d["temp_c"])
'''


@pytest.fixture
def mod(tmp_path):
    f = tmp_path / "weather_handler.py"
    f.write_text(ORIG)
    sys.path.insert(0, str(tmp_path))
    m = importlib.import_module("weather_handler")
    yield m
    sys.path.remove(str(tmp_path))
    sys.modules.pop("weather_handler", None)


@pytest.mark.live
def test_guard_heals_with_real_gemini(mod):
    path = mod.__file__

    def gemini_fixer(ctx):
        ctx.source_file = "weather_handler.py"
        ctx.source_snapshot = open(path).read()
        patch = generate_patch(ctx)
        return apply_unified_diff(open(path).read(), patch.unified_diff,
                                  filename="weather_handler.py")

    g = Guard(mod, "answer", fixer=gemini_fixer)
    # vendor renamed temp_c -> temperature_celsius
    result = g.answer({"temperature_celsius": 21})
    assert "21" in result
    assert g.audit and g.audit[0]["status"] == "healed"
