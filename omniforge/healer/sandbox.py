"""Sandbox validator (architecture spec §2.7).

Apply the patch in an isolated workspace, run the model's repro_test against
the patched source, and only pass if it goes green. Captures before/after so
the demo can show the failing → fixed transition.

The executor is injected via `runner` so this stays testable. The default
`local_runner` shells out to pytest in a throwaway tempdir (works without
Docker). For full isolation on the droplet, pass a Docker-backed runner with
the same signature — `runner(workdir) -> (passed, output)`.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from typing import Callable, Optional

from omniforge.models.schemas import IncidentContext, Patch, SandboxResult

# runner(workdir) -> (passed, combined_output)
Runner = Callable[[str], tuple]


def local_runner(workdir: str) -> tuple:
    """Run pytest over a workdir in a subprocess. No Docker required.

    The app's package is made importable inside the sandbox (PYTHONPATH =
    current project root) so a repro_test can import prod modules — the local
    stand-in for "the Docker sandbox mirrors prod deps" (spec §2.7).
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = os.getcwd() + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", workdir],
        capture_output=True, text=True, cwd=workdir, env=env,
    )
    return proc.returncode == 0, proc.stdout + proc.stderr


def _run_repro(source: str, module_filename: str, repro_test: str,
               runner: Runner) -> tuple:
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, module_filename), "w") as f:
            f.write(source)
        with open(os.path.join(d, "test_repro.py"), "w") as f:
            f.write(repro_test)
        return runner(d)


def validate(
    patch: Patch,
    ctx: IncidentContext,
    *,
    patched_source: str,
    original_source: Optional[str] = None,
    module_filename: Optional[str] = None,
    runner: Optional[Runner] = None,
) -> SandboxResult:
    """Replay the repro_test against the patched source in isolation.

    passed = repro_test goes green on the patched source. If original_source
    is given, the repro is also run against it first to capture the failing
    'before' output (it is expected to fail there).
    """
    runner = runner or local_runner
    fname = module_filename or (
        os.path.basename(ctx.source_file) if ctx.source_file
        else "module_under_test.py"
    )

    before = ""
    if original_source is not None:
        _, before = _run_repro(original_source, fname, patch.repro_test, runner)

    passed, after = _run_repro(patched_source, fname, patch.repro_test, runner)
    return SandboxResult(passed=passed, before=before, after=after)
