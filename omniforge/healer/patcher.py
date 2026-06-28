"""Apply a model-generated unified diff to source (architecture spec §2.4/§6).

Applies in a throwaway temp dir so a diff that doesn't match the source is
rejected, never silently mangled. `git apply` is tried first (strict context
check); if it refuses — model diffs often carry zero context lines, which it
rejects — fall back to GNU `patch --fuzz`, which tolerates that quirk.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile


class PatchApplyError(Exception):
    """The unified diff could not be applied cleanly to the source."""


def _normalize_paths(diff: str, filename: str) -> str:
    """Rewrite the diff's file headers to the single target basename.

    The model may emit any path depth (`a/buggy_agent.py` or
    `a/omniforge/demo/buggy_agent.py`). We apply against one file written at
    the tempdir root, so pin both headers to `a/<filename>` / `b/<filename>`
    and `git apply -p1` then locates it regardless of the model's choice.
    """
    diff = re.sub(r"^--- .*$", f"--- a/{filename}", diff, count=1, flags=re.M)
    diff = re.sub(r"^\+\+\+ .*$", f"+++ b/{filename}", diff, count=1, flags=re.M)
    return diff


def apply_unified_diff(source: str, diff: str, *, filename: str) -> str:
    diff = _normalize_paths(diff, filename)
    with tempfile.TemporaryDirectory() as d:
        target = os.path.join(d, filename)
        with open(target, "w") as f:
            f.write(source)
        patch_path = os.path.join(d, "change.patch")
        with open(patch_path, "w") as f:
            f.write(diff if diff.endswith("\n") else diff + "\n")

        if not _git_apply(d, patch_path) and not _gnu_patch(d, patch_path):
            raise PatchApplyError(_LAST_ERR[0] or "patch did not apply")

        with open(target) as f:
            return f.read()


_LAST_ERR = [""]  # last apply stderr, for the error message


def _git_apply(d: str, patch_path: str) -> bool:
    for strip in ("-p1", "-p0"):  # model diffs may or may not use a/ b/ prefixes
        proc = subprocess.run(
            ["git", "apply", "--recount", "--unsafe-paths", strip, patch_path],
            cwd=d, capture_output=True, text=True,
        )
        if proc.returncode == 0:
            return True
        _LAST_ERR[0] = proc.stderr.strip()
    return False


def _gnu_patch(d: str, patch_path: str) -> bool:
    # Lenient fallback: tolerates zero-context hunks and small offsets/fuzz.
    for strip in ("-p1", "-p0"):
        proc = subprocess.run(
            ["patch", strip, "--fuzz=2", "--no-backup-if-mismatch", "-f", "-s",
             "-i", patch_path],
            cwd=d, capture_output=True, text=True,
        )
        if proc.returncode == 0:
            return True
        _LAST_ERR[0] = (proc.stderr or proc.stdout).strip()
    return False
