# OmniForge Testbench — Mission

**Project:** `omniforge-testbench` — a deliberately fragile LLM tool-calling agent that serves as the guinea-pig target for the OmniForge self-healing proxy.
**Relationship:** Embedded (in-process). The agent runs under the OmniForge Guard; a single thin `runner.py` is the only file that imports OmniForge. The agent modules themselves stay pure and proxy-agnostic.
**Version:** 1.0.0 · **Ratified:** 2026-06-28 · **Truth:** this file; conflicts resolve in favor of the constitution.

---

## Mission

Build a small LLM tool-calling agent — *parse tool call → validate args → dispatch → execute → format result* — feature by feature. Each feature ships with three things:

1. a working **happy path**,
2. exactly **one intentional, deterministic bug** of a distinct error class, and
3. a **repro test** that fails on the bug and passes once healed.

The testbench is not judged by its own features. It is judged by **OmniForge's heal coverage across them**: every intentional bug must be caught → patched (Gemini) → scanned → sandboxed → hot-swapped → recovered, with no human, then served as an instant **cache hit** on repeat.

---

## Core Principles

**I. Faithful target (NON-NEGOTIABLE).** The agent must be real Python modules, hot-swappable via `importlib.reload`, running in the **same process** as the Guard — one shared module object. No separate process, no network shim. *Why: OmniForge heals by reload-and-rebind in-process; anything else tests nothing real.*

**II. Pure app, thin seam (NON-NEGOTIABLE).** Agent modules never `import omniforge`. Only `runner.py` wires the Guard around entrypoints. The agent is fully buildable and unit-testable without the proxy present. *Why: clean decoupling — build/test the target alone, prove the heal loop through one seam.*

**III. Deterministic failures.** No live LLM in the loop by default. Tool calls come from fixed test-data fixtures. Every bug reproduces 100% from a known input. *Why: repeatable demo + valid sandbox repro tests; flaky targets can't prove healing.*

**IV. One error class per phase.** Each phase introduces exactly one distinct failure mode (KeyError, unknown-tool, TypeError/coercion, ZeroDivisionError, None/AttributeError, …). *Why: maximize OmniForge's error-class coverage; keep each heal diff small and scoped.*

**V. Repro test per bug.** Every intentional bug has a pytest that fails on the old code and passes on the fixed code — this feeds OmniForge's sandbox gate directly. *Why: the sandbox needs a fail-old/pass-new test to validate any candidate patch.*

**VI. Heal-provable exit gates.** A phase is *done* only when OmniForge heals its bug end-to-end (recovers) **and** a repeat of the same error signature is a cache hit (no model call). *Why: closing the loop is the whole point.*

**VII. Minimal scope.** The smallest agent that produces these failures. No features, abstractions, or config beyond the heal-coverage goal. *Why: scoped target = scoped, auditable heals.*

---

## Success Criteria

- All phase fixtures run through OmniForge and heal end-to-end (recover).
- Every error class is covered at least once (Phase 6 coverage matrix all green).
- Each healed signature, on repeat, is a cache hit with zero model calls.
- One injected regression auto-rolls-back via OmniForge's containment.
