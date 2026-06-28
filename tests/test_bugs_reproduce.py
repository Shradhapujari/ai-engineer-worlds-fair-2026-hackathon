"""Each intentional bug reproduces deterministically — these are OmniForge's heal
targets (one error class per phase, per the roadmap + manifest)."""
import json
from pathlib import Path

import pytest

from agent.run import run

BUGGY = Path(__file__).resolve().parent.parent / "test-data" / "buggy"


def _load(name):
    return json.loads((BUGGY / name).read_text())


@pytest.mark.parametrize(
    "fixture,error",
    [
        ("missing_name.json", KeyError),          # Phase 1
        ("unknown_tool.json", KeyError),          # Phase 2
        ("bad_types.json", TypeError),            # Phase 3
        ("divide_zero.json", ZeroDivisionError),  # Phase 4
        ("none_result.json", AttributeError),     # Phase 5
    ],
)
def test_bug_reproduces(fixture, error):
    with pytest.raises(error):
        run(_load(fixture))
