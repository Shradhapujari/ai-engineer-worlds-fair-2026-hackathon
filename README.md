# omniforge-testbench

A deliberately fragile **LLM tool-calling agent** used as the guinea-pig target for the
[OmniForge](../ai-engineer-worlds-fair-2026-hackathon) self-healing proxy.

The agent is built feature by feature. Each feature ships a working happy path **and** one
intentional, deterministic bug of a distinct error class, plus a repro test. OmniForge's job is
to catch each bug at runtime, patch it (Gemini), scan + sandbox the patch, hot-swap it into the
live process, and serve a cache hit on repeat — no human in the loop.

**Embedded by design:** the agent runs in-process under the OmniForge Guard so the real
hot-swap mechanism (`importlib.reload` + rebind) is exercised. Agent modules stay pure; only
`runner.py` imports OmniForge.

## Governing docs (spec-driven)

- [`constitution/mission.md`](constitution/mission.md) — mission + core principles
- [`constitution/tech-stack.md`](constitution/tech-stack.md) — stack lock + layout
- [`constitution/roadmap.md`](constitution/roadmap.md) — 7 phases, one error class each (living doc)

## Test data

`test-data/` — `valid_calls.json`, `kv_data.json`, `buggy/*.json` (one bug-trigger per phase),
and `manifest.json` mapping each fixture → phase → error class → expected post-heal behavior.

## Status

Constitution + test data scaffolded. Phase 0 (code scaffold) not started — see the roadmap.
