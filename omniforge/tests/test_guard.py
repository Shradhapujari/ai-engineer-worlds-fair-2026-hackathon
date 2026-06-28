import importlib
import sys

import pytest

from omniforge.proxy.guard import Guard, Escalated


ORIG = '''def answer(d):
    return "temp=" + str(d["temp_c"])
'''
# vendor renamed temp_c -> temperature_celsius; patched reads new field
FIXED = '''def answer(d):
    return "temp=" + str(d["temperature_celsius"])
'''
STILL_BROKEN = '''def answer(d):
    return "temp=" + str(d["nope"])
'''


@pytest.fixture
def mod(tmp_path):
    f = tmp_path / "guard_target.py"
    f.write_text(ORIG)
    sys.path.insert(0, str(tmp_path))
    m = importlib.import_module("guard_target")
    yield m
    sys.path.remove(str(tmp_path))
    sys.modules.pop("guard_target", None)


def test_clean_call_passes_through(mod):
    g = Guard(mod, "answer", fixer=lambda ctx: None)
    assert g.answer({"temp_c": 14}) == "temp=14"
    assert g.audit == []          # no incident


def test_failing_call_heals_and_returns(mod):
    g = Guard(mod, "answer", fixer=lambda ctx: FIXED)
    result = g.answer({"temperature_celsius": 22})
    assert result == "temp=22"    # healed, correct answer
    assert len(g.audit) == 1
    assert g.audit[0]["status"] == "healed"


def test_no_fix_escalates(mod):
    g = Guard(mod, "answer", fixer=lambda ctx: None)
    with pytest.raises(Escalated):
        g.answer({"temperature_celsius": 22})


def test_bad_patch_rolls_back_and_escalates(mod):
    g = Guard(mod, "answer", fixer=lambda ctx: STILL_BROKEN)
    with pytest.raises(Escalated):
        g.answer({"temperature_celsius": 22})
    # rolled back: original source restored on disk
    assert 'd["temp_c"]' in (mod.__file__ and open(mod.__file__).read())


def test_fixer_receives_incident_context(mod):
    seen = {}
    def fixer(ctx):
        seen["err"] = ctx.error_type
        seen["fn"] = ctx.failing_function
        return FIXED
    Guard(mod, "answer", fixer=fixer).answer({"temperature_celsius": 1})
    assert seen["err"] == "KeyError"
    assert seen["fn"] == "answer"
