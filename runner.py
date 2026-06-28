"""The only seam to OmniForge. Wraps the pure agent entrypoint with the Guard.

Adds the sibling OmniForge repo to sys.path, then guards `agent.run.run`.
Phase 0 uses a placeholder escalate-fixer (no autonomous fix yet); the real
gated fixer (Gemini -> scan -> sandbox) gets wired in from Phase 1 onward.
"""
from __future__ import annotations

import sys
from pathlib import Path

_OMNIFORGE_REPO = (
    Path(__file__).resolve().parent.parent / "ai-engineer-worlds-fair-2026-hackathon"
)
if str(_OMNIFORGE_REPO) not in sys.path:
    sys.path.insert(0, str(_OMNIFORGE_REPO))

from omniforge.proxy.guard import Guard  # noqa: E402

from agent import run as run_module  # noqa: E402


def _escalate_fixer(ctx):
    # Phase 0 placeholder. Valid calls never reach this; a buggy call escalates
    # until the real fixer is wired in.
    return None


def build_guard(fixer=_escalate_fixer) -> Guard:
    return Guard(run_module, "run", fixer=fixer)


def guarded_run(raw, fixer=_escalate_fixer):
    return build_guard(fixer).call(raw)
