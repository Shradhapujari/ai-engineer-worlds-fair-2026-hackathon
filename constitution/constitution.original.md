# OmniForge Constitution

**Project:** OmniForge — The Self-Healing Proxy: autonomous runtime debugging, patching, and hot-swapping for production AI systems.
**Event:** AI Engineer World's Fair Hackathon 2026 · Theme: *The Self-Improvement Stack* (+ Recursive Intelligence & Continual Learning)
**Version:** 1.0.0 · **Ratified:** 2026-06-27 · **Source of truth:** `OmniForge_Architecture.md`

This document holds the non-negotiable principles that govern every plan, spec, and line of code in OmniForge. Where a downstream artifact conflicts with the constitution, the constitution wins.

---

## Mission

OmniForge supervises a running AI app. When the app throws an unhandled error, OmniForge catches it before it crashes the process, asks the model to write a patch, runs that patch through a security scanner and an isolated Docker sandbox, and — only if it passes — hot-swaps the fixed code into the live process. Every validated fix is stored in local memory keyed by a normalized error signature, so the next occurrence of the same error is fixed instantly without calling the model. **The more it runs, the faster and cheaper it heals.** The product *is* the autonomous loop — not a dashboard.

---

## Core Principles

### I. Safety Gate Is Absolute (NON-NEGOTIABLE)
Generated code NEVER runs in production without passing every gate, in order: static security scan (semgrep + bandit) → policy gate → Docker sandbox validation with passing tests → live verify. Any gate failure escalates to a human and is logged; it is never silently shipped. Containment is the whole architecture: scope-limited diffs, scan-before-execute, sandbox-before-prod, mandatory passing tests, instant rollback, per-window change cap, kill switch, append-only audit log.
*Rationale: autonomous self-modifying code is the core risk; the gates are what make it defensible to judges and safe in reality.*

### II. Never Break the Demo Path (NON-NEGOTIABLE)
The end-to-end heal loop must always be demoable. Phase 1's hardcoded-fix fallback stays behind a flag so a live model hiccup cannot kill the stage demo. Sequencing rule: build a working end-to-end loop first, add intelligence after. If only Phase 1 works, there is still a demo.
*Rationale: Live Demo is 20% of judging; a broken demo is a zero regardless of code quality.*

### III. Stack Lock: Gemini + DigitalOcean Only
Patch generation uses **Gemini 3.5 Flash** only. Hosting/compute is a single **DigitalOcean droplet** running the proxy, supervised app, sandbox containers, and the SQLite file. No other model vendors, no other hosted compute.
*Rationale: hackathon stack constraint; also unlocks "Best Usage of DigitalOcean" and keeps the system self-contained.*

### IV. Local-Only Persistence & Tooling
Fix memory is **SQLite, a local file on the droplet** — three tables (`incidents`, `patches`, `fix_memory`, indexed on `signature_hash`). Security tooling (semgrep, bandit) is local pip, no hosted services. No external network dependency in the heal loop beyond the single Gemini call.
*Rationale: zero external deps = reliability under demo conditions and a clean security story.*

### V. Continual Learning Is the Payoff
Memory lookup is exact-match on the normalized signature hash. A validated, previously deployed fix skips the model and goes straight to hot-swap (after a quick sandbox re-verify). `hit_count` is tracked and surfaced to prove the system gets faster and cheaper over time.
*Rationale: repeat errors at ~0ms and $0 is the thesis — "it learned."*

### VI. Minimal, Scoped Patches
Model output is strict JSON: `root_cause`, `unified_diff` touching only in-scope files, and a `repro_test` that fails on old code and passes on patched code. Hard prompt constraints: minimal diff, no new external network calls, no files outside incident scope, no changes to OmniForge's own code, must include the verifying test.
*Rationale: small scoped diffs are auditable, sandbox-testable, and safe to hot-swap.*

### VII. Pure, Independently Testable Components
Each component (Guard, Triage, Memory, Diagnose, Scanner, Sandbox, HotSwap, Rollback) honors its interface contract and is testable in isolation. Contracts in `§5` of the architecture spec are binding.
*Rationale: makes the demo robust and the judging Q&A easy.*

### VIII. Zero-Dashboard Compliance
The product is the autonomous loop. The only observability surface is a minimal append-only audit log — deliberately secondary, never a dashboard product. All work is new, built at the event, public repo; demo only built features; tag in the README what was built during the event. Avoid every banned category (chatbot/RAG/dashboard).
*Rationale: rule compliance is pass/fail; a banned-category build is disqualified.*

---

## Constraints

- **Language:** Python 3.11+ (enables runtime reload; matches typical agent stacks).
- **Latency budget — cache miss:** Gemini ~1–2s + scan <1s + sandbox+tests ~3–6s + hot-swap <1s → **under ~10s**. Cache hit: **<1s, no model call.**
- **Hot-swap:** primary = function-registry `importlib.reload` + atomic rebind, keep previous callable for rollback; fallback = blue-green worker with drain/cutover.
- **Data models:** per `§4` — `IncidentContext`, `Patch`, `FixMemory` (pydantic).
- **Repo structure:** per `§6` — `proxy/ healer/ memory/ models/ config/ demo/ docker/ tests/ main.py`.

---

## Roadmap (build phases, ~24h window)

| Phase | Goal | Gate before moving on |
|---|---|---|
| 0 | Setup: repo, DO droplet (Docker+Python), Gemini key, init SQLite, build `buggy_agent` + `fake_vendor_api`. | Droplet runs; demo app callable. |
| 1 | Close loop with hardcoded fix: catch → triage → apply → hot-swap → recover. | End-to-end reload works (**minimum viable demo**). |
| 2 | Real patch generation via Gemini (diff + repro test). | Generated patch heals a live break. |
| 3 | Safety rails: semgrep/bandit + policy gate + Docker sandbox. | Bad patches rejected & escalated. |
| 4 | Memory / continual learning: SQLite store + signature lookup. | Cache hit = instant fix, no model call. |
| 5 | Rollback + circuit breaker + audit log + polish. | Regression auto-rolls-back. |
| 6 | Demo + 1-min video (due Sun 12:00). Rehearse twice. | Two clean run-throughs. |

---

## Governance

- This constitution supersedes any conflicting decision in specs, plans, or code. Resolve conflicts in favor of the constitution.
- Amendments require a version bump (semver: MAJOR = principle removed/redefined, MINOR = principle added, PATCH = clarification) and a note of what changed and why.
- Every patch, plan, and PR is checked against the **NON-NEGOTIABLE** principles (I, II) first; a violation blocks merge.
- The append-only audit log is the record of every autonomous change; the kill switch and per-window change cap are always enabled in any demoed build.

**Compliance check (run before any demo):** public repo ✓ · all-new work ✓ · demo only built features ✓ · zero-dashboard ✓ · Gemini+DO only ✓ · safety gates active ✓ · kill switch + audit log on ✓.
