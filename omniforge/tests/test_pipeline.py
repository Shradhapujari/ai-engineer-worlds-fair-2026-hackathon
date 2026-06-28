import json

from omniforge.healer.pipeline import make_gated_fixer
from omniforge.memory import store
from omniforge.memory.signature import signature_hash
from omniforge.models.schemas import IncidentContext

ORIGINAL = 'def answer(d):\n    return d["temp_c"]\n'

CLEAN_DIFF = """--- a/weather.py
+++ b/weather.py
@@ -1,2 +1,2 @@
 def answer(d):
-    return d["temp_c"]
+    return d["temperature_celsius"]
"""

DANGEROUS_DIFF = """--- a/weather.py
+++ b/weather.py
@@ -1,2 +1,2 @@
 def answer(d):
-    return d["temp_c"]
+    return eval(d["temp_c"])
"""

REPRO = 'def test_x():\n    assert True\n'


class FakeClient:
    def __init__(self, diff):
        self._diff = diff
        self.calls = 0

    def generate_text(self, prompt):
        self.calls += 1
        return json.dumps(
            {"root_cause": "rc", "unified_diff": self._diff, "repro_test": REPRO}
        )


class ExplodingClient:
    def generate_text(self, prompt):
        raise AssertionError("model must not be called on a cache hit")


def _ctx(path):
    return IncidentContext(
        id="i1", ts="t", error_type="KeyError", traceback="tb",
        signature_hash=signature_hash("tb"), source_file=path,
        failing_function="answer",
    )


def _write_source(tmp_path):
    p = tmp_path / "weather.py"
    p.write_text(ORIGINAL)
    return str(p)


def test_clean_patch_returns_patched_source(tmp_path):
    path = _write_source(tmp_path)
    escalations = []
    fixer = make_gated_fixer(
        client=FakeClient(CLEAN_DIFF),
        runner=lambda d: (True, "1 passed"),
        on_escalate=lambda ctx, reasons: escalations.append(reasons),
    )
    out = fixer(_ctx(path))
    assert out is not None
    assert 'd["temperature_celsius"]' in out
    assert escalations == []


def test_dangerous_patch_rejected_and_escalated(tmp_path):
    path = _write_source(tmp_path)
    escalations = []
    fixer = make_gated_fixer(
        client=FakeClient(DANGEROUS_DIFF),
        runner=lambda d: (True, "passed"),  # would pass sandbox, but scan blocks first
        on_escalate=lambda ctx, reasons: escalations.append(reasons),
    )
    out = fixer(_ctx(path))
    assert out is None
    assert any("eval()" in r for r in escalations[0])


def test_sandbox_failure_rejected_and_escalated(tmp_path):
    path = _write_source(tmp_path)
    escalations = []
    fixer = make_gated_fixer(
        client=FakeClient(CLEAN_DIFF),
        runner=lambda d: (False, "1 failed: AssertionError"),
        on_escalate=lambda ctx, reasons: escalations.append(reasons),
    )
    out = fixer(_ctx(path))
    assert out is None
    assert any("sandbox" in r for r in escalations[0])


def test_unapplicable_diff_escalates(tmp_path):
    path = _write_source(tmp_path)
    escalations = []
    fixer = make_gated_fixer(
        client=FakeClient("this is not a diff"),
        on_escalate=lambda ctx, reasons: escalations.append(reasons),
    )
    out = fixer(_ctx(path))
    assert out is None
    assert escalations  # escalated with a reason


def _conn(tmp_path):
    db = str(tmp_path / "mem.db")
    store.init_db(db)
    return store.connect(db)


def test_first_heal_calls_model_and_remembers(tmp_path):
    path = _write_source(tmp_path)
    conn = _conn(tmp_path)
    client = FakeClient(CLEAN_DIFF)
    fixer = make_gated_fixer(client=client, runner=lambda d: (True, "passed"),
                             conn=conn)
    ctx = _ctx(path)
    out = fixer(ctx)
    assert 'd["temperature_celsius"]' in out
    assert client.calls == 1
    assert store.lookup(conn, ctx) is not None  # remembered


def test_repeat_error_heals_from_memory_no_model_call(tmp_path):
    path = _write_source(tmp_path)
    conn = _conn(tmp_path)
    ctx = _ctx(path)
    # seed memory via a first heal
    make_gated_fixer(client=FakeClient(CLEAN_DIFF),
                     runner=lambda d: (True, "passed"), conn=conn)(ctx)
    # second occurrence: model must not be called
    fixer = make_gated_fixer(client=ExplodingClient(),
                             runner=lambda d: (True, "passed"), conn=conn)
    out = fixer(ctx)
    assert 'd["temperature_celsius"]' in out
    assert store.hit_count(conn, ctx.signature_hash) >= 1
