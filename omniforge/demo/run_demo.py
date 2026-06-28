"""End-to-end self-heal demo (architecture spec §8).

Stages:
  1. Agent works against the stable vendor.
  2. Break the vendor live (schema rename) -> the agent crashes (the 2am page).
  3. OmniForge catches it -> Gemini patch -> security scan -> sandbox -> hot-swap.
     The agent answers correctly again. No human touched it.
  4. Same error again -> healed instantly from SQLite fix-memory, NO model call
     (hit_count ticks up). "It learned. Faster + cheaper every time."
  5. One line on the audit log + kill switch: safe, not reckless.

Run:
  python -m omniforge.demo.run_demo              # offline, hardcoded fallback patch
  OMNIFORGE_DEMO_LIVE=1 \
  GOOGLE_CLOUD_PROJECT=... python -m omniforge.demo.run_demo   # real Gemini

The fallback keeps the demo path alive if live Gemini hiccups (Constitution II).
"""
from __future__ import annotations

import json
import os
import time

from omniforge.config import settings
from omniforge.healer.pipeline import make_gated_fixer
from omniforge.healer.rollback import AuditLog, CircuitBreaker, kill_switch_engaged
from omniforge.healer.sandbox import local_runner
from omniforge.memory import store
from omniforge.proxy.guard import Escalated, Guard
from omniforge.proxy.supervisor import hot_swap

AGENT_FILE = os.path.join(os.path.dirname(__file__), "buggy_agent.py")
BUGGY_LINE = '    temp = data["temp_c"]  # breaks when vendor renames the field\n'
FIXED_LINE = ('    temp = data.get("temp_c", data.get("temperature_celsius"))'
              "  # tolerate vendor rename\n")

# The sandbox runs in overlay mode (patched file at its real package path),
# so import the module under test via its package path.
REPRO = """from omniforge.demo import buggy_agent, fake_vendor_api

def test_heals_broken_vendor():
    fake_vendor_api.BROKEN = True
    assert "°C" in buggy_agent.answer_weather("london")
"""


class FallbackClient:
    """Offline stand-in for Gemini: returns the known-good full file as JSON
    (same contract as the real model — diagnose computes the diff itself)."""

    def __init__(self, patched: str) -> None:
        self._json = json.dumps({
            "root_cause": "vendor renamed temp_c -> temperature_celsius",
            "fixed_source": patched,
            "repro_test": REPRO,
        })

    def generate_text(self, prompt: str) -> str:
        return self._json


def _build_client(patched: str):
    live = os.environ.get("OMNIFORGE_DEMO_LIVE") == "1" and settings.GCP_PROJECT
    if live:
        print("   [using real Gemini via Vertex]")
        return None  # make_gated_fixer falls back to the real Vertex client
    print("   [using offline fallback patch — set OMNIFORGE_DEMO_LIVE=1 for Gemini]")
    return FallbackClient(patched)


def main() -> None:
    from omniforge.demo import buggy_agent, fake_vendor_api

    with open(AGENT_FILE) as f:
        original = f.read()
    patched = original.replace(BUGGY_LINE, FIXED_LINE)
    assert patched != original, "demo fixture drifted: BUGGY_LINE not found"

    db = "omniforge_demo.db"
    store.init_db(db)
    conn = store.connect(db)
    audit = AuditLog("omniforge_demo_audit.jsonl")
    breaker = CircuitBreaker(settings.MAX_CHANGES_PER_WINDOW,
                             settings.CHANGE_WINDOW_SECONDS)

    fixer = make_gated_fixer(
        client=_build_client(patched),
        conn=conn,
        runner=local_runner,
        on_escalate=lambda ctx, reasons: print(f"   ESCALATED: {reasons}"),
    )
    guard = Guard(buggy_agent, "answer_weather", fixer=fixer,
                  breaker=breaker, kill_switch=kill_switch_engaged,
                  audit_log=audit)

    try:
        print("\n1) Agent working (stable vendor):")
        print("  ", guard.answer_weather("london"))

        print("\n2) Break the vendor live (rename field) — raw agent crashes:")
        fake_vendor_api.BROKEN = True
        try:
            buggy_agent.answer_weather("london")
        except KeyError as e:
            print(f"   CRASH — KeyError: {e}   (would page someone at 2am)")

        print("\n3) OmniForge heals it (patch -> scan -> sandbox -> hot-swap):")
        t0 = time.perf_counter()
        answer = guard.answer_weather("london")
        dt = time.perf_counter() - t0
        print(f"   {answer}   [healed in {dt:.2f}s, no human]")

        print("\n4) Same error again -> healed from memory, NO model call:")
        hot_swap(buggy_agent, original)  # simulate a fresh deploy of the buggy code
        t0 = time.perf_counter()
        answer = guard.answer_weather("london")
        dt = time.perf_counter() - t0
        sig = guard.audit[-1]["signature"]
        print(f"   {answer}   [healed in {dt:.2f}s from SQLite, "
              f"hit_count={store.hit_count(conn, sig)}]")

        print("\n5) Safe, not reckless — audit log (last 3 events):")
        for e in audit.entries()[-3:]:
            print(f"   {e['ts']}  {e['status']:11}  {e['error_type']}")
        print("   Kill switch: OMNIFORGE_KILL=1 halts all autonomous healing.")
        print(f"   Circuit breaker: max {settings.MAX_CHANGES_PER_WINDOW} "
              f"changes / {settings.CHANGE_WINDOW_SECONDS:.0f}s.")
    except Escalated as e:
        print(f"\n   Demo escalated (no safe fix applied): {e}")
    finally:
        # Restore the demo agent + vendor so the run is repeatable.
        hot_swap(buggy_agent, original)
        fake_vendor_api.BROKEN = False
        conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
