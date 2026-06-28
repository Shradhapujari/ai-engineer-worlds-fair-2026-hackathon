from omniforge.healer.sandbox import validate, local_runner
from omniforge.models.schemas import IncidentContext, Patch


def _ctx(source_file="weather.py") -> IncidentContext:
    return IncidentContext(
        id="i1", ts="t", error_type="KeyError", traceback="tb",
        signature_hash="h", source_file=source_file, failing_function="answer",
    )


def _patch(repro="def test(): assert True") -> Patch:
    return Patch(id="p1", incident_id="i1", root_cause="rc",
                 unified_diff="diff", repro_test=repro)


def test_validate_passes_with_passing_runner():
    res = validate(_patch(), _ctx(), patched_source="x = 1",
                   runner=lambda d: (True, "1 passed"))
    assert res.passed
    assert res.after == "1 passed"


def test_validate_fails_with_failing_runner():
    res = validate(_patch(), _ctx(), patched_source="x = 1",
                   runner=lambda d: (False, "1 failed"))
    assert not res.passed


def test_before_and_after_captured():
    calls = iter([(False, "before: failed"), (True, "after: passed")])
    res = validate(_patch(), _ctx(), patched_source="patched",
                   original_source="original", runner=lambda d: next(calls))
    assert res.before == "before: failed"
    assert res.after == "after: passed"
    assert res.passed


def test_runner_receives_module_and_test_files():
    import os

    seen = {}

    def runner(workdir):
        seen["files"] = sorted(os.listdir(workdir))
        return True, "ok"

    validate(_patch(), _ctx("vendor.py"), patched_source="x = 1", runner=runner)
    assert seen["files"] == ["test_repro.py", "vendor.py"]


REPRO = """from weather import answer
def test_answer():
    assert answer({"temperature_celsius": 21}) == 21
"""


def test_local_runner_real_pytest_patched_passes_original_fails():
    patched = 'def answer(d):\n    return d["temperature_celsius"]\n'
    original = 'def answer(d):\n    return d["temp_c"]\n'
    res = validate(
        _patch(REPRO), _ctx("weather.py"),
        patched_source=patched, original_source=original,
        runner=local_runner,
    )
    assert res.passed                  # repro green on patched source
    assert "passed" in res.after
    assert "passed" not in res.before  # original (buggy) source failed the repro
