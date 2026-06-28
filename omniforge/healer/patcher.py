"""Apply a model-generated unified diff to source (architecture spec §2.4/§6).

Uses `git apply` in a throwaway temp dir so context lines are verified — a diff
that doesn't match the source is rejected, never silently mangled.
"""
from __future__ import annotations

import os
import subprocess
import tempfile


class PatchApplyError(Exception):
    """The unified diff could not be applied cleanly to the source."""


def apply_unified_diff(source: str, diff: str, *, filename: str) -> str:
    with tempfile.TemporaryDirectory() as d:
        target = os.path.join(d, filename)
        with open(target, "w") as f:
            f.write(source)
        patch_path = os.path.join(d, "change.patch")
        with open(patch_path, "w") as f:
            f.write(diff if diff.endswith("\n") else diff + "\n")

        last_err = ""
        for strip in ("-p1", "-p0"):  # model diffs may or may not use a/ b/ prefixes
            proc = subprocess.run(
                ["git", "apply", "--recount", "--unsafe-paths", strip, patch_path],
                cwd=d, capture_output=True, text=True,
            )
            if proc.returncode == 0:
                break
            last_err = proc.stderr.strip()
        else:
            raise PatchApplyError(last_err or "git apply failed")

        with open(target) as f:
            return f.read()
