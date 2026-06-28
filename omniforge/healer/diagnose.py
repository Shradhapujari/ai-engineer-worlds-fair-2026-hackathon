"""Diagnose + Patch generator (architecture spec §2.4).

Gemini produces strict JSON: root_cause, unified_diff, repro_test.
Pure + testable: the model client is injected, so unit tests use a fake and
the live loop passes a real Vertex client.
"""
from __future__ import annotations

import json
import time
from typing import Optional, Protocol

from omniforge.config import settings
from omniforge.models.schemas import IncidentContext, Patch

REQUIRED_KEYS = ("root_cause", "unified_diff", "repro_test")


class PatchGenerationError(Exception):
    """Model output was missing or malformed after retries."""


class ModelClient(Protocol):
    def generate_text(self, prompt: str) -> str: ...


def build_prompt(ctx: IncidentContext, prior: Optional[Patch]) -> str:
    fewshot = ""
    if prior is not None:
        fewshot = (
            "\nA prior validated fix for a related error (use as a guide):\n"
            f"root_cause: {prior.root_cause}\n"
            f"unified_diff:\n{prior.unified_diff}\n"
        )
    return f"""You are OmniForge's patch generator. Fix the crash below.

Exception type: {ctx.error_type}
Traceback:
{ctx.traceback}

Failing function `{ctx.failing_function}` in {ctx.source_file}:
{ctx.source_snapshot}

Input that triggered it: {json.dumps(ctx.trigger_input)}
Installed dependency versions: {json.dumps(ctx.dependency_versions)}
{fewshot}
Hard constraints:
- Patch must be minimal and touch ONLY {ctx.source_file}.
- Do NOT add new external network calls.
- Include a repro_test that fails on the old code and passes on the patch.

Respond with ONLY a JSON object, no prose, with exactly these keys:
"root_cause" (string), "unified_diff" (string, a unified diff),
"repro_test" (string, runnable pytest)."""


def parse_patch(raw: str, *, incident_id: str, model: str, latency_ms: int) -> Patch:
    text = raw.strip()
    if text.startswith("```"):
        # strip ```json ... ``` fences
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError) as e:
        raise PatchGenerationError(f"model output was not valid JSON: {e}") from e
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise PatchGenerationError(f"model output missing keys: {missing}")
    return Patch(
        id=f"patch-{incident_id}",
        incident_id=incident_id,
        root_cause=data["root_cause"],
        unified_diff=data["unified_diff"],
        repro_test=data["repro_test"],
        model_used=model,
        latency_ms=latency_ms,
    )


def generate_patch(
    ctx: IncidentContext,
    prior: Optional[Patch] = None,
    *,
    client: Optional[ModelClient] = None,
) -> Patch:
    """Generate a validated Patch. Retries once with a stricter prompt on
    malformed output; raises PatchGenerationError after the second failure.
    """
    client = client or _default_client()
    prompt = build_prompt(ctx, prior)
    last_error: Optional[Exception] = None

    for attempt in (1, 2):
        if attempt == 2:
            prompt = (
                prompt
                + "\n\nYour previous response was invalid. Return ONLY the JSON "
                "object with the three required keys and nothing else."
            )
        start = time.perf_counter()
        raw = client.generate_text(prompt)
        latency_ms = int((time.perf_counter() - start) * 1000)
        try:
            return parse_patch(
                raw, incident_id=ctx.id, model=settings.GEMINI_MODEL,
                latency_ms=latency_ms,
            )
        except PatchGenerationError as e:
            last_error = e

    raise PatchGenerationError(
        f"patch generation failed after 2 attempts: {last_error}"
    )


def _default_client() -> ModelClient:
    """Real Vertex/Gemini client. Imported lazily so unit tests need no auth."""

    class _VertexClient:
        def __init__(self):
            self._client = settings.genai_client()

        def generate_text(self, prompt: str) -> str:
            resp = self._client.models.generate_content(
                model=settings.GEMINI_MODEL, contents=prompt
            )
            return resp.text

    return _VertexClient()
