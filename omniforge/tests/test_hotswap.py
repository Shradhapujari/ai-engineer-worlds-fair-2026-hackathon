import importlib
import sys

import pytest

from omniforge.proxy.registry import HandlerRegistry
from omniforge.proxy.supervisor import hot_swap, rollback


# --- registry -------------------------------------------------------------

def test_registry_register_and_get():
    r = HandlerRegistry()
    r.register("greet", lambda: "hi")
    assert r.get("greet")() == "hi"


def test_registry_rebind_swaps_callable():
    r = HandlerRegistry()
    r.register("greet", lambda: "old")
    r.rebind("greet", lambda: "new")
    assert r.get("greet")() == "new"


# --- hot_swap on a real module -------------------------------------------

ORIG = "def value():\n    return 'old'\n"
PATCHED = "def value():\n    return 'new'\n"


@pytest.fixture
def temp_module(tmp_path):
    f = tmp_path / "swap_target.py"
    f.write_text(ORIG)
    sys.path.insert(0, str(tmp_path))
    mod = importlib.import_module("swap_target")
    yield mod
    sys.path.remove(str(tmp_path))
    sys.modules.pop("swap_target", None)


def test_hot_swap_changes_behavior_after_reload(temp_module):
    assert temp_module.value() == "old"
    hot_swap(temp_module, PATCHED)
    assert temp_module.value() == "new"


def test_rollback_restores_original(temp_module):
    handle = hot_swap(temp_module, PATCHED)
    assert temp_module.value() == "new"
    rollback(handle)
    assert temp_module.value() == "old"
