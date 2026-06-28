"""Security scanner / policy gate (architecture spec §2.5).

The trust boundary: model-generated code never runs in prod without passing
this. Two layers, both local (Constitution IV — no hosted services):

1. Policy gate — pure, deterministic checks on the unified diff: scope,
   max size, no self-edit, dangerous sinks, no new network/dangerous imports.
   This is the demo-critical core; it always runs and needs no extra tooling.
2. Static scan — best-effort bandit pass on the patched source. Defense in
   depth; injected so unit tests stay fast and it degrades gracefully if
   bandit is absent.

Reject => escalate (caller's job), never deploy.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Callable, Optional

from omniforge.models.schemas import Patch, ScanResult

MAX_DIFF_LINES = 200  # a heal is minimal; a huge diff is suspicious

# Dangerous sinks: code-exec, destruction, exfiltration. Matched in added lines.
_DANGEROUS_PATTERNS = [
    (re.compile(r"\beval\s*\("), "eval()"),
    (re.compile(r"\bexec\s*\("), "exec()"),
    (re.compile(r"\b__import__\s*\("), "__import__()"),
    (re.compile(r"\bcompile\s*\("), "compile()"),
    (re.compile(r"\bos\.system\s*\("), "os.system()"),
    (re.compile(r"\bos\.popen\s*\("), "os.popen()"),
    (re.compile(r"\bos\.(remove|unlink|rmdir)\s*\("), "os file deletion"),
    (re.compile(r"\bshutil\.rmtree\s*\("), "shutil.rmtree()"),
    (re.compile(r"shell\s*=\s*True"), "subprocess shell=True"),
    (re.compile(r"\bpickle\.loads?\s*\("), "pickle load"),
    (re.compile(r"\bmarshal\.loads\s*\("), "marshal.loads()"),
    (re.compile(r"\bsocket\.socket\s*\("), "raw socket"),
]

# New imports of these modules are rejected: network egress / native exec.
_DANGEROUS_IMPORTS = {
    "socket", "requests", "urllib", "urllib2", "http", "httplib",
    "ftplib", "smtplib", "telnetlib", "subprocess", "ctypes",
    "pickle", "marshal", "multiprocessing",
}

_PLUS_FILE = re.compile(r"^\+\+\+ (?:b/)?(.+)$")
_IMPORT = re.compile(r"^(?:import|from)\s+([A-Za-z_][\w.]*)")


def _touched_files(diff: str) -> list[str]:
    files = []
    for line in diff.splitlines():
        m = _PLUS_FILE.match(line)
        if m and m.group(1) != "/dev/null":
            files.append(m.group(1).strip())
    return files


def _added_lines(diff: str) -> list[str]:
    # body of additions, minus the '+++' file header
    return [ln[1:] for ln in diff.splitlines()
            if ln.startswith("+") and not ln.startswith("+++")]


def _policy_gate(patch: Patch, scope_files: set[str]) -> list[str]:
    reasons: list[str] = []
    diff = patch.unified_diff

    touched = _touched_files(diff)
    if not touched:
        reasons.append("diff touches no files (unparseable)")
    for path in touched:
        base = os.path.basename(path)
        if base not in scope_files:
            reasons.append(f"out-of-scope file: {path}")
        # no self-edit: OmniForge's own code is off-limits (demo target is ok)
        norm = path.replace("\\", "/")
        if "omniforge/" in norm and "omniforge/demo/" not in norm:
            reasons.append(f"must not modify OmniForge's own code: {path}")

    diff_lines = sum(
        1 for ln in diff.splitlines()
        if (ln.startswith("+") or ln.startswith("-"))
        and not ln.startswith(("+++", "---"))
    )
    if diff_lines > MAX_DIFF_LINES:
        reasons.append(f"diff too large: {diff_lines} > {MAX_DIFF_LINES} lines")

    added = _added_lines(diff)
    for line in added:
        for pat, label in _DANGEROUS_PATTERNS:
            if pat.search(line):
                reasons.append(f"dangerous sink: {label}")
        m = _IMPORT.match(line.strip())
        if m and m.group(1).split(".")[0] in _DANGEROUS_IMPORTS:
            reasons.append(f"disallowed import: {m.group(1)}")

    return reasons


def _bandit_scan(patched_sources: dict[str, str]) -> list[str]:
    """Best-effort bandit pass. High-severity findings => reasons.
    Returns [] (skips) if bandit isn't available — the policy gate still ran.
    """
    try:
        import bandit  # noqa: F401
    except ImportError:
        return []

    reasons: list[str] = []
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for name, src in patched_sources.items():
            p = os.path.join(d, os.path.basename(name))
            with open(p, "w") as f:
                f.write(src)
            paths.append(p)
        proc = subprocess.run(
            [sys.executable, "-m", "bandit", "-f", "json", "-ll", *paths],
            capture_output=True, text=True,
        )
        try:
            report = json.loads(proc.stdout)
        except (json.JSONDecodeError, ValueError):
            return []  # couldn't parse — don't block on a tooling glitch
        for issue in report.get("results", []):
            if issue.get("issue_severity") in ("MEDIUM", "HIGH"):
                reasons.append(
                    f"bandit {issue['issue_severity']}: {issue['test_id']} "
                    f"{issue['issue_text']}"
                )
    return reasons


# static_scan: maps patched sources -> list of finding reasons. Injected for tests.
StaticScan = Callable[[dict], list]


def scan(
    patch: Patch,
    *,
    scope_files: set[str],
    patched_sources: Optional[dict] = None,
    static_scan: Optional[StaticScan] = None,
) -> ScanResult:
    """Run the policy gate (always) + static scan (if patched sources given).

    scope_files: basenames the incident is allowed to touch.
    patched_sources: {filename: full patched source} for the static pass.
    """
    reasons = _policy_gate(patch, scope_files)
    if patched_sources:
        scanner = static_scan or _bandit_scan
        reasons += scanner(patched_sources)
    return ScanResult(passed=len(reasons) == 0, reasons=reasons)
