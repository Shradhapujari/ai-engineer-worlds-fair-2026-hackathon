"""Diagnose + Patch generator (architecture spec §2.4).

Gemini returns strict JSON: root_cause, the COMPLETE fixed file, repro_test.
We compute the unified_diff ourselves with difflib — LLMs emit unreliable diffs
(wrong hunk counts, missing context/headers), but a full-file rewrite is easy
for them and difflib turns it into an always-valid, always-appliable diff.
Pure + testable: the model client is injected.
"""
from __future__ import annotations

import difflib
import json
import os
import time
from typing import Optional, Protocol

from omniforge.config import settings
from omniforge.models.schemas import IncidentContext, Patch

REQUIRED_KEYS = ("root_cause", "fixed_source", "repro_test")


class PatchGenerationError(Exception):
    """Model output was missing or malformed after retries."""


class ModelClient(Protocol):
    def generate_text(self, prompt: str) -> str: ...


def _filename(ctx: IncidentContext) -> str:
    return os.path.basename(ctx.source_file) if ctx.source_file else "module.py"


def make_diff(original: str, fixed: str, filename: str) -> str:
    """Always-valid unified diff from a full-file rewrite."""
    return "".join(difflib.unified_diff(
        original.splitlines(keepends=True),
        fixed.splitlines(keepends=True),
        fromfile=f"a/{filename}", tofile=f"b/{filename}",
    ))


def build_prompt(ctx: IncidentContext, prior: Optional[Patch],
                 original_source: Optional[str] = None) -> str:
    source = original_source if original_source is not None else (
        ctx.source_snapshot or "")
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

Failing function `{ctx.failing_function}` in {ctx.source_file}.
The COMPLETE current contents of {_filename(ctx)}:
{source}

Input that triggered it: {json.dumps(ctx.trigger_input)}
Installed dependency versions: {json.dumps(ctx.dependency_versions)}
{fewshot}
Hard constraints:
- Fix must be minimal and stay within this one file.
- Do NOT add new external network calls.
- Include a repro_test that fails on the old code and passes on the fix.

Respond with ONLY a JSON object, no prose, with exactly these keys:
"root_cause" (string),
"fixed_source" (string — the ENTIRE corrected file content, not a diff),
"repro_test" (string, runnable pytest)."""


def parse_patch(raw: str, *, incident_id: str, model: str, latency_ms: int,
                original_source: str, filename: str) -> Patch:
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
    fixed = data["fixed_source"]
    diff = make_diff(original_source, fixed, filename)
    if not diff.strip():
        raise PatchGenerationError("fixed_source is identical to the original")
    return Patch(
        id=f"patch-{incident_id}",
        incident_id=incident_id,
        root_cause=data["root_cause"],
        unified_diff=diff,
        repro_test=data["repro_test"],
        model_used=model,
        latency_ms=latency_ms,
    )


def generate_patch(
    ctx: IncidentContext,
    prior: Optional[Patch] = None,
    *,
    client: Optional[ModelClient] = None,
    original_source: Optional[str] = None,
) -> Patch:
    """Generate a validated Patch. Retries once with a stricter prompt on
    malformed output; raises PatchGenerationError after the second failure.
    """
    client = client or _default_client()
    original = original_source if original_source is not None else (
        ctx.source_snapshot or "")
    filename = _filename(ctx)
    prompt = build_prompt(ctx, prior, original)
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
                latency_ms=latency_ms, original_source=original, filename=filename,
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
            # Constrained decoding to a strict schema so the diff string — full
            # of quotes and newlines — is always valid, properly-escaped JSON.
            # (mime_type alone leaves the model free to emit unescaped quotes.)
            resp = self._client.models.generate_content(
                model=settings.GEMINI_MODEL, contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": {
                        "type": "object",
                        "properties": {
                            "root_cause": {"type": "string"},
                            "fixed_source": {"type": "string"},
                            "repro_test": {"type": "string"},
                        },
                        "required": ["root_cause", "fixed_source", "repro_test"],
                    },
                },
            )
            return resp.text

    return _VertexClient()
