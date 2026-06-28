"""Triage & context capture (architecture spec §2.2).

Turn a caught exception into an IncidentContext: error type, full traceback,
the source file/function that threw, the trigger input, and a stable signature.
"""
from __future__ import annotations

import datetime
import traceback as tb_mod
import uuid
from typing import Optional

from omniforge.memory.signature import signature_hash
from omniforge.models.schemas import IncidentContext


def capture(exc: BaseException, *, trigger_input: Optional[dict] = None,
            log_tail: Optional[list[str]] = None) -> IncidentContext:
    tb = exc.__traceback__
    tb_str = "".join(tb_mod.format_exception(type(exc), exc, tb))

    # last frame = where it actually threw
    last = tb
    while last and last.tb_next:
        last = last.tb_next
    source_file = failing_function = None
    if last is not None:
        code = last.tb_frame.f_code
        source_file = code.co_filename
        failing_function = code.co_name

    return IncidentContext(
        id=str(uuid.uuid4()),
        ts=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        error_type=type(exc).__name__,
        traceback=tb_str,
        signature_hash=signature_hash(tb_str),
        source_file=source_file,
        failing_function=failing_function,
        trigger_input=trigger_input or {},
        log_tail=log_tail or [],
        status="open",
    )
