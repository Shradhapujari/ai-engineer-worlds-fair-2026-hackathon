"""Live end-to-end: real Gemini 3.5 Flash via Vertex/ADC.
Run explicitly:  pytest -m live   (needs GOOGLE_CLOUD_PROJECT + ADC).
Skipped by default (pytest.ini addopts = -m "not live").
"""
import pytest

from omniforge.healer.diagnose import generate_patch, PatchGenerationError
from omniforge.tests.test_diagnose import make_ctx


@pytest.mark.live
def test_generate_patch_live_against_real_gemini():
    try:
        patch = generate_patch(make_ctx())  # default real Vertex client
    except PatchGenerationError as e:
        pytest.fail(f"live model returned unparseable output: {e}")
    assert patch.root_cause.strip()
    assert patch.unified_diff.strip()
    assert patch.repro_test.strip()
    assert patch.model_used == "gemini-3.5-flash"
    assert patch.latency_ms is not None and patch.latency_ms > 0
