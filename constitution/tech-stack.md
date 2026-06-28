# OmniForge Testbench — Tech Stack

Stack chosen for speed and for faithfulness to the OmniForge heal mechanism (in-process `importlib` hot-swap). Lock per Mission Principles I–III.

| Concern | Choice | Notes |
|---|---|---|
| Language | **Python 3.11+** | Must match OmniForge runtime; enables `importlib.reload` hot-swap. |
| Agent core | **stdlib only** (`json`, `dataclasses`, `typing`) | Dependency-free, fast to build. `pydantic` optional later to mirror OmniForge models — not required. |
| Tool-call input | **Canned JSON fixtures** (`test-data/`) | Deterministic; no live LLM in the loop. Optional real-Gemini input mode can be added later, off by default. |
| Tools | **calculator, unit_convert, kv_lookup** | Pure functions; each is a distinct failure surface. |
| Tests | **pytest** | Repro tests double as OmniForge sandbox-gate inputs. |
| Heal integration | **OmniForge Guard** via `runner.py` | Embedded, in-process; the only seam to the proxy. |
| Persistence | **none** (stateless agent) | OmniForge owns fix-memory (its SQLite); the testbench stores nothing. |

**OmniForge wiring:** `runner.py` adds the OmniForge repo (`../ai-engineer-worlds-fair-2026-hackathon`) to `sys.path`, imports `omniforge.proxy.guard`, and wraps the agent entrypoint. Reuses OmniForge's existing Gemini (Vertex/ADC) + sandbox config — the testbench adds no new vendor or compute.

**Locked:** Python + stdlib agent, OmniForge embedded. No web framework, no database in the testbench, no live LLM by default.

## Layout (target)

```
omniforge-testbench/
  constitution/      mission.md · tech-stack.md · roadmap.md
  agent/             parser.py · registry.py · validate.py · tools.py · format.py · run.py
  runner.py          wraps agent.run with OmniForge Guard  (only file importing omniforge)
  test-data/         valid_calls.json · kv_data.json · buggy/*.json · manifest.json
  tests/             one repro test per phase bug
```
