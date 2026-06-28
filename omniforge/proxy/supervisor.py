"""Hot-swap engine (architecture spec §2.6, primary strategy).

Write patched source to the module's file, importlib.reload it, and keep the
previous source for instant rollback. No full process restart.
"""
from __future__ import annotations

import importlib
import importlib.util
import os
from dataclasses import dataclass
from types import ModuleType


def _reload(module: ModuleType, path: str) -> None:
    # Delete the cached .pyc so reload always recompiles from source — mtime
    # alone is unreliable when a file is rewritten twice within one second.
    try:
        os.remove(importlib.util.cache_from_source(path))
    except OSError:
        pass
    importlib.invalidate_caches()
    importlib.reload(module)


@dataclass
class SwapHandle:
    module: ModuleType
    old_source: str
    file_path: str


def hot_swap(module: ModuleType, new_source: str) -> SwapHandle:
    path = module.__file__
    assert path is not None, "module has no file to swap"
    with open(path, "r") as f:
        old_source = f.read()
    with open(path, "w") as f:
        f.write(new_source)
    _reload(module, path)
    return SwapHandle(module=module, old_source=old_source, file_path=path)


def rollback(handle: SwapHandle) -> None:
    with open(handle.file_path, "w") as f:
        f.write(handle.old_source)
    _reload(handle.module, handle.file_path)
