"""Heal pipeline: compose diagnose → patch → scan → sandbox into a gated fixer
that plugs into the Guard's existing `Fixer` contract (architecture spec §5).

Every gate is mandatory. A patch that fails generation, application, the
security scan, or the sandbox replay returns None — the Guard then escalates
to a human and never deploys it (spec §2.5/§2.7). The `on_escalate` hook
receives the rejection reasons so the audit log (Phase 5) can record them.
"""
from __future__ import annotations

import os
import sqlite3
from typing import Callable, Optional

from omniforge.healer import sandbox, scanner
from omniforge.healer.diagnose import ModelClient, PatchGenerationError, generate_patch
from omniforge.healer.patcher import PatchApplyError, apply_unified_diff
from omniforge.memory import store
from omniforge.models.schemas import IncidentContext

# on_escalate(ctx, reasons) -> None
EscalateHook = Callable[[IncidentContext, list], None]


def make_gated_fixer(
    *,
    client: Optional[ModelClient] = None,
    scope_files: Optional[set] = None,
    runner: Optional[sandbox.Runner] = None,
    on_escalate: Optional[EscalateHook] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Callable:
    """Build a Guard fixer: ctx -> patched source (str) or None to escalate.

    If `conn` is given, a fix-memory hit on the error signature reuses the
    stored patch — re-verified in the sandbox but with NO model call (the
    continual-learning fast path). A validated fresh fix is remembered.
    """

    def _escalate(ctx: IncidentContext, reasons: list) -> None:
        if on_escalate is not None:
            on_escalate(ctx, reasons)

    def fixer(ctx: IncidentContext) -> Optional[str]:
        if not ctx.source_file:
            _escalate(ctx, ["no source file in incident context"])
            return None
        fname = os.path.basename(ctx.source_file)
        scope = scope_files or {fname}
        with open(ctx.source_file) as f:
            original = f.read()

        # Fast path: known signature -> reuse stored fix, no model call.
        if conn is not None:
            cached = store.lookup(conn, ctx)
            if cached is not None:
                try:
                    patched = apply_unified_diff(
                        original, cached.unified_diff, filename=fname
                    )
                    sb = sandbox.validate(
                        cached, ctx, patched_source=patched,
                        original_source=original, runner=runner,
                    )
                    if sb.passed:
                        return patched  # healed from memory — zero model cost
                except PatchApplyError:
                    pass  # stored fix no longer applies; fall through to regen

        try:
            patch = generate_patch(ctx, client=client)
            patched = apply_unified_diff(original, patch.unified_diff, filename=fname)
        except (PatchGenerationError, PatchApplyError) as e:
            _escalate(ctx, [f"patch generation/apply failed: {e}"])
            return None

        scan_res = scanner.scan(
            patch, scope_files=scope, patched_sources={fname: patched}
        )
        if not scan_res.passed:
            _escalate(ctx, scan_res.reasons)
            return None

        sb = sandbox.validate(
            patch, ctx, patched_source=patched,
            original_source=original, runner=runner,
        )
        if not sb.passed:
            _escalate(ctx, ["sandbox: repro_test failed", sb.after[-500:]])
            return None

        # Validated + about to deploy: remember it so the next occurrence is free.
        if conn is not None:
            patch.deployed = True
            patch.scan_result = scan_res.model_dump()
            patch.sandbox_result = sb.model_dump()
            store.remember(conn, ctx, patch)

        return patched

    return fixer
