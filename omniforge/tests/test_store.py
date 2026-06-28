import pytest

from omniforge.memory import store
from omniforge.models.schemas import IncidentContext, Patch


@pytest.fixture
def conn(tmp_path):
    db = str(tmp_path / "test.db")
    store.init_db(db)
    c = store.connect(db)
    yield c
    c.close()


def _ctx(sig="sig-abc"):
    return IncidentContext(
        id=f"i-{sig}", ts="2026-06-27T00:00:00Z", error_type="KeyError",
        traceback="tb", signature_hash=sig, source_file="weather.py",
        failing_function="answer", trigger_input={"k": "v"},
    )


def _patch(sig="sig-abc"):
    return Patch(
        id=f"p-{sig}", incident_id=f"i-{sig}", root_cause="rc",
        unified_diff="diff", repro_test="def t(): pass",
        scan_result={"passed": True}, sandbox_result={"passed": True, "after": "ok"},
        deployed=True, model_used="gemini-3.5-flash", latency_ms=1200,
    )


def test_lookup_miss_returns_none(conn):
    assert store.lookup(conn, _ctx()) is None


def test_remember_then_lookup_hit(conn):
    ctx, patch = _ctx(), _patch()
    store.remember(conn, ctx, patch)
    found = store.lookup(conn, ctx)
    assert found is not None
    assert found.id == patch.id
    assert found.unified_diff == "diff"


def test_dict_fields_round_trip(conn):
    ctx, patch = _ctx(), _patch()
    store.remember(conn, ctx, patch)
    found = store.lookup(conn, ctx)
    assert found.scan_result == {"passed": True}
    assert found.sandbox_result == {"passed": True, "after": "ok"}
    assert found.deployed is True
    assert found.latency_ms == 1200


def test_hit_count_starts_zero_and_increments_on_lookup(conn):
    ctx, patch = _ctx(), _patch()
    store.remember(conn, ctx, patch)
    assert store.hit_count(conn, ctx.signature_hash) == 0  # remembered, not yet reused
    store.lookup(conn, ctx)
    assert store.hit_count(conn, ctx.signature_hash) == 1
    store.lookup(conn, ctx)
    store.lookup(conn, ctx)
    assert store.hit_count(conn, ctx.signature_hash) == 3


def test_re_remember_preserves_accumulated_hits(conn):
    ctx, patch = _ctx(), _patch()
    store.remember(conn, ctx, patch)
    store.lookup(conn, ctx)
    store.lookup(conn, ctx)               # hit_count = 2
    store.remember(conn, ctx, patch)      # re-store same signature
    assert store.hit_count(conn, ctx.signature_hash) == 2  # not reset to 0


def test_distinct_signatures_are_independent(conn):
    store.remember(conn, _ctx("sig-a"), _patch("sig-a"))
    store.remember(conn, _ctx("sig-b"), _patch("sig-b"))
    store.lookup(conn, _ctx("sig-a"))
    assert store.hit_count(conn, "sig-a") == 1
    assert store.hit_count(conn, "sig-b") == 0
    assert store.lookup(conn, _ctx("sig-b")).id == "p-sig-b"
