import json

import pytest

from omniforge.models.schemas import IncidentContext, Patch
from omniforge.healer.diagnose import (
    build_prompt,
    parse_patch,
    generate_patch,
    PatchGenerationError,
)


def make_ctx():
    return IncidentContext(
        id="inc-1",
        ts="2026-06-27T00:00:00",
        error_type="KeyError",
        traceback="Traceback (most recent call last):\n  KeyError: 'temp_c'",
        signature_hash="sig-abc",
        source_file="demo/buggy_agent.py",
        failing_function="answer_weather",
        source_snapshot='def answer_weather(city):\n    return data["temp_c"]',
        trigger_input={"city": "london"},
        dependency_versions={"pydantic": "2.13"},
        log_tail=["called get_weather"],
        status="open",
    )


VALID_JSON = json.dumps({
    "root_cause": "Vendor renamed temp_c to temperature_celsius",
    "unified_diff": "--- a/buggy_agent.py\n+++ b/buggy_agent.py\n@@\n-    return data[\"temp_c\"]\n+    return data[\"temperature_celsius\"]",
    "repro_test": "def test_weather():\n    assert answer_weather('london')",
})


class FakeClient:
    """Records prompts, returns queued responses in order."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.prompts = []

    def generate_text(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self._responses.pop(0)


# --- build_prompt ---------------------------------------------------------

def test_build_prompt_includes_incident_context():
    p = build_prompt(make_ctx(), prior=None)
    assert "temp_c" in p                 # traceback / source
    assert "answer_weather" in p         # failing function
    assert "london" in p                 # trigger input
    assert "pydantic" in p               # dependency versions


def test_build_prompt_states_hard_constraints():
    p = build_prompt(make_ctx(), prior=None).lower()
    assert "unified_diff" in p and "repro_test" in p and "root_cause" in p
    assert "json" in p                   # strict JSON output demanded


def test_build_prompt_includes_prior_fix_as_fewshot():
    prior = Patch(id="p0", incident_id="old", root_cause="rc-old",
                  unified_diff="OLD_DIFF_MARKER", repro_test="t")
    p = build_prompt(make_ctx(), prior=prior)
    assert "OLD_DIFF_MARKER" in p


# --- parse_patch ----------------------------------------------------------

def test_parse_patch_valid_json():
    patch = parse_patch(VALID_JSON, incident_id="inc-1",
                        model="gemini-3.5-flash", latency_ms=1200)
    assert patch.root_cause.startswith("Vendor renamed")
    assert "temperature_celsius" in patch.unified_diff
    assert patch.repro_test.startswith("def test_weather")
    assert patch.incident_id == "inc-1"
    assert patch.model_used == "gemini-3.5-flash"
    assert patch.latency_ms == 1200


def test_parse_patch_strips_markdown_fences():
    fenced = "```json\n" + VALID_JSON + "\n```"
    patch = parse_patch(fenced, incident_id="inc-1", model="m", latency_ms=1)
    assert "temperature_celsius" in patch.unified_diff


def test_parse_patch_malformed_raises():
    with pytest.raises(PatchGenerationError):
        parse_patch("not json at all", incident_id="i", model="m", latency_ms=1)


def test_parse_patch_missing_key_raises():
    bad = json.dumps({"root_cause": "x"})  # no diff / test
    with pytest.raises(PatchGenerationError):
        parse_patch(bad, incident_id="i", model="m", latency_ms=1)


# --- generate_patch (orchestration) --------------------------------------

def test_generate_patch_success_first_try():
    client = FakeClient([VALID_JSON])
    patch = generate_patch(make_ctx(), client=client)
    assert isinstance(patch, Patch)
    assert patch.incident_id == "inc-1"
    assert patch.model_used
    assert isinstance(patch.latency_ms, int) and patch.latency_ms >= 0
    assert len(client.prompts) == 1


def test_generate_patch_retries_once_then_succeeds():
    client = FakeClient(["garbage", VALID_JSON])
    patch = generate_patch(make_ctx(), client=client)
    assert isinstance(patch, Patch)
    assert len(client.prompts) == 2
    # retry prompt is stricter -> differs from first
    assert client.prompts[1] != client.prompts[0]


def test_generate_patch_raises_after_two_failures():
    client = FakeClient(["garbage", "still garbage"])
    with pytest.raises(PatchGenerationError):
        generate_patch(make_ctx(), client=client)
    assert len(client.prompts) == 2
