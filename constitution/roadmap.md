# OmniForge Testbench — Roadmap (Living Document)

**Status:** Active · **Last updated:** 2026-06-28 · **Source of truth:** `mission.md`

> Living doc. Update status + check boxes as phases land.
> **Build rule:** each phase adds one feature with exactly one intentional, deterministic bug (one error class). A phase is DONE only when OmniForge heals that bug end-to-end **and** a repeat is a cache hit (Mission Principle VI).

**Legend:** ☐ todo · ◐ in-progress · ☑ done · ⚠ blocked
**Phase status:** `PLANNED` → `IN PROGRESS` → `DONE`

---

## Progress

| Phase | Title | Feature | Error class | Status | Exit gate |
|---|---|---|---|---|---|
| 0 | Scaffold | dirs + runner + fixtures | — | PLANNED | valid call runs E2E under Guard |
| 1 | Tool-call parser | parse JSON → ToolCall | `KeyError` / JSON `ValueError` | PLANNED | bug healed + cache hit |
| 2 | Registry + dispatch | name → callable | unknown-tool `KeyError` | PLANNED | bug healed + cache hit |
| 3 | Arg validation | coerce args to signature | `TypeError` / `ValueError` | PLANNED | bug healed + cache hit |
| 4 | Tool execution | calculator / convert / lookup | `ZeroDivisionError` / `IndexError` | PLANNED | bug healed + cache hit |
| 5 | Result formatting | format + 2-step chain | `AttributeError` (None) / `KeyError` | PLANNED | bug healed + cache hit |
| 6 | Heal-coverage matrix | run all fixtures + harden | all of the above | PLANNED | matrix all green; regression auto-rolls-back |

**Overall:** 0/7 phases done.

---

## Phase 0 — Scaffold
**Status:** PLANNED · **Depends:** —
**Goal:** stand up the agent skeleton and the OmniForge seam.
- ☐ Dirs: `agent/`, `tests/`, `test-data/`
- ☐ `runner.py` — adds OmniForge repo to `sys.path`, imports `omniforge.proxy.guard`, wraps `agent.run.run(call)` with the Guard
- ☐ Load fixtures from `test-data/` (valid + kv data)
- ☐ Happy-path smoke: a valid tool call returns the correct result with the agent alone (no proxy)
**Exit gate:** a valid call runs end-to-end under the Guard; agent runs standalone too.

## Phase 1 — Tool-call Parser  (error class: `KeyError` / JSON `ValueError`)
**Status:** PLANNED · **Depends:** P0
**Feature:** parse raw model output (JSON string) into `ToolCall{name, arguments}`.
**Intentional bug:** parser does `obj["name"]` / `obj["arguments"]` directly → `KeyError` when a key is missing (and unguarded `json.loads` on malformed input).
**Fixture:** `test-data/buggy/missing_name.json` · **Repro:** `tests/test_p1_parser.py` (fails old, passes healed).
**Exit gate:** OmniForge catches the `KeyError` → patches parser → hot-swaps → recovers; repeat of same signature = cache hit (no model call).

## Phase 2 — Registry + Dispatch  (error class: unknown-tool `KeyError`)
**Status:** PLANNED · **Depends:** P1
**Feature:** registry maps tool name → callable; `dispatch(call)` routes to it.
**Intentional bug:** `registry[name]` direct lookup → `KeyError` on an unknown tool name (no membership check / no fallback).
**Fixture:** `test-data/buggy/unknown_tool.json` · **Repro:** `tests/test_p2_dispatch.py`.
**Exit gate:** healed E2E + cache hit.

## Phase 3 — Arg Validation  (error class: `TypeError` / `ValueError`)
**Status:** PLANNED · **Depends:** P2
**Feature:** validate and coerce arguments to each tool's expected types before calling.
**Intentional bug:** no coercion — a string `"two"` flows into integer arithmetic → `TypeError`; or `int(value)` on a non-numeric string → `ValueError`.
**Fixture:** `test-data/buggy/bad_types.json` · **Repro:** `tests/test_p3_validate.py`.
**Exit gate:** healed E2E + cache hit.

## Phase 4 — Tool Execution  (error class: `ZeroDivisionError` / `IndexError`)
**Status:** PLANNED · **Depends:** P3
**Feature:** implement the tools — `calculator` (add/sub/mul/divide), `unit_convert`, `kv_lookup` over `kv_data.json`.
**Intentional bug:** `divide` does `a / b` with no zero guard → `ZeroDivisionError` (and/or `kv_lookup` indexing a result list out of range → `IndexError`).
**Fixture:** `test-data/buggy/divide_zero.json` · **Repro:** `tests/test_p4_tools.py`.
**Exit gate:** healed E2E + cache hit.

## Phase 5 — Result Formatting  (error class: `AttributeError` (None) / `KeyError`)
**Status:** PLANNED · **Depends:** P4
**Feature:** format a tool result into the final answer string; support a simple 2-step chain (output of tool A feeds tool B).
**Intentional bug:** formatter assumes the result is a non-None dict with a given key → `AttributeError` on `None` or `KeyError` in the template when a tool returns nothing.
**Fixture:** `test-data/buggy/none_result.json` · **Repro:** `tests/test_p5_format.py`.
**Exit gate:** healed E2E + cache hit.

## Phase 6 — Heal-Coverage Matrix + Harden
**Status:** PLANNED · **Depends:** P5
**Goal:** prove coverage and containment across the whole testbench.
- ☐ Run every fixture in `manifest.json` through OmniForge; assert each heals (recovers) and is then a cache hit
- ☐ Emit a coverage table: phase → error class → healed? → cache hit? → heal latency
- ☐ Inject one regression (a patch that breaks a passing case) and confirm OmniForge auto-rolls-back + escalates
- ☐ Kill-switch sanity: with kill switch on, no autonomous change is applied
**Exit gate:** matrix all green — every phase bug healed E2E + cache hit; regression auto-rolls-back.

---

## Milestones

| ID | Name | Phases | Means |
|---|---|---|---|
| M0 | Skeleton | P0 | agent runs under Guard |
| M1 | First heal | P1 | one real bug healed E2E |
| M2 | Breadth | P2–P5 | five distinct error classes healed |
| M3 | Proven | P6 | coverage matrix green + rollback verified |

---

## Changelog

- 2026-06-28 — Roadmap created. Concept: embedded LLM tool-calling agent as OmniForge heal target; 7 phases, one error class each.
