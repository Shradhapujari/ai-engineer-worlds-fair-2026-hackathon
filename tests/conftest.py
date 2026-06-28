import sys
from pathlib import Path

# Make the testbench root importable so `agent` and `runner` resolve.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
