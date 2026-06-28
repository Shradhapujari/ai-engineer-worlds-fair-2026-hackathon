from omniforge.proxy.triage import capture
from omniforge.models.schemas import IncidentContext


def _boom(d):
    return d["temp_c"]          # raises KeyError


def _raise_key_error():
    try:
        _boom({"temperature_celsius": 14})
    except KeyError as e:
        return e


def test_capture_returns_incident_context():
    exc = _raise_key_error()
    ctx = capture(exc, trigger_input={"city": "london"})
    assert isinstance(ctx, IncidentContext)
    assert ctx.error_type == "KeyError"
    assert "KeyError" in ctx.traceback
    assert ctx.failing_function == "_boom"
    assert ctx.trigger_input == {"city": "london"}
    assert ctx.status == "open"


def test_capture_signature_is_64_hex():
    ctx = capture(_raise_key_error())
    assert len(ctx.signature_hash) == 64


def test_capture_same_error_same_signature():
    a = capture(_raise_key_error())
    b = capture(_raise_key_error())
    assert a.signature_hash == b.signature_hash
    assert a.id != b.id          # but each incident is unique


def test_capture_records_source_file():
    ctx = capture(_raise_key_error())
    assert ctx.source_file and ctx.source_file.endswith("test_triage.py")
