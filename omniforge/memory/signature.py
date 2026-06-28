"""Normalized error signature (architecture spec §2.2).

Strip run-specific noise (line numbers, hex addresses, file paths) so the same
logical error hashes to a stable key across runs — the fix-memory lookup key.
"""
from __future__ import annotations

import hashlib
import re

_LINE_NO = re.compile(r"line \d+")
_HEX_ADDR = re.compile(r"0x[0-9a-fA-F]+")
_PATH = re.compile(r'File "[^"]*/([^/"]+)"')  # keep basename, drop directories


def normalize(traceback: str) -> str:
    t = _PATH.sub(r'File "\1"', traceback)
    t = _LINE_NO.sub("line N", t)
    t = _HEX_ADDR.sub("0xADDR", t)
    return t.strip()


def signature_hash(traceback: str) -> str:
    return hashlib.sha256(normalize(traceback).encode()).hexdigest()
