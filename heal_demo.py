"""Watch OmniForge heal this testbench live.

Picks a buggy fixture, runs the agent under the OmniForge Guard with the REAL
gated fixer (Gemini -> scan -> sandbox -> hot-swap + fix-memory), then runs the
same call again to show the cache hit (no model call). Agent source is snapshot
before and restored after, so the demo repeats.

Run (live Gemini, from the testbench dir):
    GOOGLE_CLOUD_PROJECT=ai-hack-sf26sfo-7019 GOOGLE_CLOUD_LOCATION=global \
      ../ai-engineer-worlds-fair-2026-hackathon/.venv/bin/python heal_demo.py

Optional first arg = fixture name (default missing_name.json):
    ... heal_demo.py divide_zero.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import runner  # adds the OmniForge repo to sys.path as a side effect

from omniforge.healer.pipeline import make_gated_fixer
from omniforge.memory import store
from omniforge.proxy.guard import Guard

ROOT = Path(__file__).resolve().parent
OMNIFORGE_REPO = ROOT.parent / "ai-engineer-worlds-fair-2026-hackathon"
AGENT_DIR = ROOT / "agent"


def _snapshot() -> dict[Path, str]:
    return {p: p.read_text() for p in AGENT_DIR.glob("*.py")}


def _restore(snap: dict[Path, str]) -> None:
    for p, text in snap.items():
        p.write_text(text)


def main() -> None:
    fixture = sys.argv[1] if len(sys.argv) > 1 else "missing_name.json"
    raw = json.loads((ROOT / "test-data" / "buggy" / fixture).read_text())

    def _on_escalate(ctx, reasons):
        print(f"    [escalate] {ctx.error_type}: {reasons}")

    conn = store.connect(str(OMNIFORGE_REPO / "omniforge.db"))  # sets row_factory
    fixer = make_gated_fixer(conn=conn, on_escalate=_on_escalate)  # default scope = file that threw
    guard = Guard(runner.run_module, "run", fixer=fixer)

    snap = _snapshot()
    try:
        print(f"== fixture: {fixture} ==")

        print("\n[1] first call -> crash caught, OmniForge heals live...")
        out1 = guard.call(raw)
        print(f"    healed result: {out1!r}")

        print("\n[2] same call again -> fix-memory cache hit (no model call)...")
        out2 = guard.call(raw)
        print(f"    result: {out2!r}")
    finally:
        _restore(snap)
        conn.close()
        print("\nagent/ source restored. done.")


if __name__ == "__main__":
    main()
