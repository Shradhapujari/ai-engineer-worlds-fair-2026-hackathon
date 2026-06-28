from omniforge.models.schemas import IncidentContext, Patch


def _ctx(**kw):
    base = dict(
        id="i1", ts="2026-06-27T00:00:00", error_type="KeyError",
        traceback="Traceback...", signature_hash="abc123",
        source_file="demo/buggy_agent.py", failing_function="answer_weather",
        source_snapshot="def answer_weather(city): ...",
        trigger_input={"city": "london"}, dependency_versions={"pydantic": "2.13"},
        log_tail=["line1"], status="open",
    )
    base.update(kw)
    return IncidentContext(**base)


def test_incident_requires_signature_hash():
    import pytest
    with pytest.raises(Exception):
        IncidentContext(id="i1", ts="t", error_type="E", traceback="tb")


def test_incident_holds_trigger_input():
    ctx = _ctx(trigger_input={"city": "tokyo"})
    assert ctx.trigger_input["city"] == "tokyo"
    assert ctx.signature_hash == "abc123"


def test_patch_defaults_not_deployed():
    p = Patch(id="p1", incident_id="i1", root_cause="rc",
              unified_diff="--- a\n+++ b", repro_test="def test(): pass")
    assert p.deployed is False
    assert p.rollback_of is None
    assert p.scan_result == {}
