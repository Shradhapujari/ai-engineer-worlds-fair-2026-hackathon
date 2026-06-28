"""Sandbox validator (architecture spec §2.7).

Apply the patch in an isolated workspace, run the model's repro_test against
the patched source, and only pass if it goes green. Captures before/after so
the demo can show the failing → fixed transition.

Two isolation modes, chosen automatically:

* **Overlay** (when the failing file is a real file inside the project): copy
  the project into a tempdir, overlay the patched file at its real path, and
  run the repro there with that copy first on PYTHONPATH. Package imports
  (`import omniforge.demo.buggy_agent`) then resolve to the PATCHED copy — the
  real prod modules can't leak in. This is the local stand-in for "the Docker
  sandbox mirrors prod deps".
* **Single-file** (synthetic / out-of-tree sources, e.g. unit tests): write
  just the patched file + the repro into a tempdir.

The executor is injected via `runner` so this stays testable. Default
`local_runner` shells out to pytest (no Docker). For full isolation on the
droplet, pass a Docker-backed runner with the same signature.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from typing import Callable, Optional

from omniforge.models.schemas import IncidentContext, Patch, SandboxResult

REPRO_FILE = "test_repro.py"

# runner(workdir) -> (passed, combined_output)
Runner = Callable[[str], tuple]

# Heavy / irrelevant dirs we never need inside the sandbox copy.
_IGNORE = shutil.ignore_patterns(
    ".git", ".venv", "venv", "__pycache__", "*.pyc", ".pytest_cache",
    "*.db", "*.jsonl", "node_modules",
)


def local_runner(workdir: str) -> tuple:
    """Run the repro test in a subprocess. No Docker required.

    PYTHONPATH puts the sandbox workdir first (so an overlaid patched package
    wins over the installed one), then the project root (so prod deps a
    single-file sandbox doesn't carry still import).
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [workdir, os.getcwd(), env.get("PYTHONPATH", "")]
    )
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", os.path.join(workdir, REPRO_FILE)],
        capture_output=True, text=True, cwd=workdir, env=env,
    )
    return proc.returncode == 0, proc.stdout + proc.stderr


def _overlay_rel(ctx: IncidentContext) -> Optional[str]:
    """Relative path of the failing file inside the project, or None if the
    file isn't a real in-tree file (then single-file mode applies)."""
    if not ctx.source_file or not os.path.isfile(ctx.source_file):
        return None
    root = os.getcwd()
    src = os.path.abspath(ctx.source_file)
    if not src.startswith(root + os.sep):
        return None
    return os.path.relpath(src, root)


def _run_repro(source: str, ctx: IncidentContext, repro_test: str,
               runner: Runner) -> tuple:
    rel = _overlay_rel(ctx)
    with tempfile.TemporaryDirectory() as d:
        if rel is not None:  # overlay mode: copy project, patch in place
            shutil.copytree(os.getcwd(), d, ignore=_IGNORE, dirs_exist_ok=True)
            target = os.path.join(d, rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
        else:                # single-file mode
            fname = (os.path.basename(ctx.source_file) if ctx.source_file
                     else "module_under_test.py")
            target = os.path.join(d, fname)
        with open(target, "w") as f:
            f.write(source)
        with open(os.path.join(d, REPRO_FILE), "w") as f:
            f.write(repro_test)
        return runner(d)


def validate(
    patch: Patch,
    ctx: IncidentContext,
    *,
    patched_source: str,
    original_source: Optional[str] = None,
    runner: Optional[Runner] = None,
) -> SandboxResult:
    """Replay the repro_test against the patched source in isolation.

    passed = repro_test goes green on the patched source. If original_source
    is given, the repro is also run against it first to capture the failing
    'before' output (it is expected to fail there).
    """
    runner = runner or local_runner

    before = ""
    if original_source is not None:
        _, before = _run_repro(original_source, ctx, patch.repro_test, runner)

    passed, after = _run_repro(patched_source, ctx, patch.repro_test, runner)
    return SandboxResult(passed=passed, before=before, after=after)
