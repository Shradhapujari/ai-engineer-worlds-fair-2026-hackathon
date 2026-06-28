# OmniForge Constitution

**Proj:** OmniForge — self-healing proxy. Autonomous runtime debug + patch + hot-swap for prod AI.
**Event:** AI Engineer World's Fair Hackathon 2026 · Theme: Self-Improvement Stack (+ Recursive Intelligence, Continual Learning)
**Ver:** 1.0.0 · **Ratified:** 2026-06-27 · **Truth:** `OmniForge_Architecture.md`

Non-negotiable rules govern all specs/plans/code. Conflict → constitution wins.

---

## Mission

Supervise running AI app. App throws → catch before crash → model writes patch → security scan + Docker sandbox → pass-only hot-swap into live process. Store validated fix in local memory by normalized error signature → next same error fixed instant, no model call. **More it runs, faster + cheaper it heals.** Product = autonomous loop, not dashboard.

---

## Core Principles

**I. Safety Gate Absolute (NON-NEGOTIABLE).** Generated code never hits prod without passing all gates in order: static scan (semgrep+bandit) → policy gate → Docker sandbox w/ passing tests → live verify. Fail → escalate human + log, never silent ship. Containment = whole architecture: scoped diffs, scan-before-exec, sandbox-before-prod, mandatory tests, instant rollback, per-window change cap, kill switch, append-only audit log. *Why: self-modifying code = core risk; gates make it safe + defensible.*

**II. Never Break Demo Path (NON-NEGOTIABLE).** Heal loop always demoable. Phase 1 hardcoded fix stays behind flag → live model hiccup can't kill stage demo. Build working loop first, add intelligence after. Phase 1 alone = still a demo. *Why: Live Demo 20% of judging.*

**III. Stack Lock: Gemini + DO only.** Patch gen = Gemini 3.5 Flash only. Compute = one DigitalOcean droplet (proxy + app + sandbox containers + SQLite). No other vendors/compute. *Why: stack constraint; unlocks Best-DO prize; self-contained.*

**IV. Local-Only Persist + Tooling.** Memory = SQLite local file, 3 tables (`incidents`, `patches`, `fix_memory`, indexed `signature_hash`). semgrep/bandit = local pip. No external net in loop beyond single Gemini call. *Why: zero ext deps = demo reliability + clean security story.*

**V. Continual Learning = Payoff.** Lookup = exact-match signature hash. Validated prior fix skips model → straight to hot-swap (quick sandbox re-verify). Track + surface `hit_count`. *Why: repeat errors ~0ms/$0 = the thesis "it learned."*

**VI. Minimal Scoped Patches.** Model output strict JSON: `root_cause`, `unified_diff` (in-scope files only), `repro_test` (fails old, passes new). Hard constraints: minimal diff, no new ext net calls, no out-of-scope files, no edit to OmniForge own code, must include test. *Why: small scoped diffs = auditable + sandbox-testable + safe swap.*

**VII. Pure Testable Components.** Each component (Guard, Triage, Memory, Diagnose, Scanner, Sandbox, HotSwap, Rollback) honors interface contract, testable isolated. `§5` contracts binding. *Why: robust demo + easy Q&A.*

**VIII. Zero-Dashboard Compliance.** Product = loop. Only observability = minimal append-only audit log, secondary, never dashboard. All work new, built at event, public repo; demo only built features; README tags event-built work. Avoid banned categories (chatbot/RAG/dashboard). *Why: rule compliance = pass/fail.*

---

## Constraints

- **Lang:** Python 3.11+ (runtime reload; matches agent stacks).
- **Latency cache-miss:** Gemini ~1–2s + scan <1s + sandbox+tests ~3–6s + swap <1s → **<~10s**. Cache hit: **<1s, no model call.**
- **Hot-swap:** primary = registry `importlib.reload` + atomic rebind, keep prev callable for rollback; fallback = blue-green worker drain/cutover.
- **Models:** `§4` — `IncidentContext`, `Patch`, `FixMemory` (pydantic).
- **Repo:** `§6` — `proxy/ healer/ memory/ models/ config/ demo/ docker/ tests/ main.py`.

---

## Roadmap (~24h)

| Phase | Goal | Exit gate |
|---|---|---|
| 0 | Setup: repo, DO droplet (Docker+Py), Gemini key, init SQLite, build `buggy_agent`+`fake_vendor_api`. | Droplet runs; app callable. |
| 1 | Loop w/ hardcoded fix: catch→triage→apply→swap→recover. | E2E reload works (**min demo**). |
| 2 | Real Gemini patch gen (diff + repro test). | Generated patch heals live break. |
| 3 | Safety rails: semgrep/bandit + policy gate + Docker sandbox. | Bad patch rejected + escalated. |
| 4 | Memory: SQLite + signature lookup. | Cache hit = instant fix, no model call. |
| 5 | Rollback + circuit breaker + audit log + polish. | Regression auto-rolls-back. |
| 6 | Demo + 1-min video (due Sun 12:00). Rehearse 2x. | Two clean run-throughs. |

---

## Governance

- Constitution supersedes conflicting specs/plans/code.
- Amend = semver bump (MAJOR principle removed/redefined, MINOR added, PATCH clarified) + note what/why.
- Every patch/plan/PR checked vs NON-NEGOTIABLE I+II first; violation blocks merge.
- Audit log = record of every autonomous change. Kill switch + per-window cap always on in any demoed build.

**Pre-demo check:** public repo ✓ · all-new ✓ · only built features ✓ · zero-dashboard ✓ · Gemini+DO only ✓ · gates active ✓ · kill switch + audit log on ✓.
