"""Pydantic data models (architecture spec §4). Passive, individually testable."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class IncidentContext(BaseModel):
    id: str
    ts: str
    error_type: str
    traceback: str
    signature_hash: str  # normalized, stable across runs -> the memory key
    source_file: Optional[str] = None
    failing_function: Optional[str] = None
    source_snapshot: Optional[str] = None  # function's code at crash time
    trigger_input: dict = Field(default_factory=dict)  # secrets stripped
    dependency_versions: dict = Field(default_factory=dict)
    log_tail: list[str] = Field(default_factory=list)
    status: Literal["open", "patched", "escalated", "rolled_back"] = "open"


class Patch(BaseModel):
    id: str
    incident_id: str
    root_cause: str
    unified_diff: str
    repro_test: str
    scan_result: dict = Field(default_factory=dict)      # semgrep/bandit + policy
    sandbox_result: dict = Field(default_factory=dict)   # pass/fail, before/after
    deployed: bool = False
    rollback_of: Optional[str] = None
    model_used: Optional[str] = None
    latency_ms: Optional[int] = None
