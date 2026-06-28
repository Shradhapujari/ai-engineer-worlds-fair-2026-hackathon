# OmniForge — Roadmap (Living Document)

**Status:** Active · **Last updated:** 2026-06-27 · **Window:** ~24h · **Source:** `OmniForge_Architecture.md` §7
**Owner:** team · **Truth above code:** `constitution.md`

> Living doc. Update status + check boxes as phases land. Sequencing rule: **never break demo path** — keep Phase 1 hardcoded fallback behind flag so live Gemini hiccup can't kill stage demo.

**Legend:** ☐ todo · ◐ in-progress · ☑ done · ⚠ blocked
**Phase status:** `PLANNED` → `IN PROGRESS` → `DONE`

---

## Progress

| Phase | Title | Status | Milestone | Exit gate |
|---|---|---|---|---|
| 0 | Setup | DONE | M0 Foundation ✓ | Droplet runs; demo app callable |
| 1 | Closed loop (hardcoded) | DONE | M1 Min Viable Demo ✓ | E2E reload works |
| 2 | Real patch gen | DONE | M2 Intelligence ✓ | Generated patch heals live break |
| 3 | Safety rails | DONE | M3 Trustworthy ✓ | Bad patch rejected + escalated |
| 4 | Memory / continual learning | DONE | M4 Self-Improve ✓ | Cache hit = instant fix, no model call |
| 5 | Rollback + circuit breaker | DONE | M5 Safe ✓ | Regression auto-rolls-back |
| 6 | Demo + video | PLANNED | M6 Ship | Two clean run-throughs |

**Overall:** 6/7 phases done. Next = Phase 6 (demo + 1-min video) — non-code: rehearse, record, README tag.

---

## Phase 0 — Setup
**Status:** DONE · **When:** Sat ~11:30, ~45min · **Milestone:** M0 Foundation ✓ · **Depends:** —
**Goal:** stand up infra + breakable demo target.
**Droplet:** `omniforge` id 580786696 · sfo3 · s-1vcpu-2gb · ubuntu-24-04 · IP 146.190.45.128 · Docker 29.1.3 + Python 3.12.3 + git · SSH `~/.ssh/omniforge_do`.
- ☑ Repo init (public) — github.com/Shradhapujari/ai-engineer-worlds-fair-2026-hackathon
- ☑ DO droplet: Docker 29.1.3 + Python 3.12.3 — `omniforge` @ 146.190.45.128 (sfo3, s-1vcpu-2gb)
- ☑ Vertex AI auth via ADC — project `ai-hack-sf26sfo-7019`, location `global`, model `gemini-3.5-flash` verified live ("OmniForge online")
- ☑ Init SQLite file (`incidents`, `patches`, `fix_memory`) — `omniforge/memory/store.py`
- ☑ `demo/buggy_agent.py` — `omniforge/demo/buggy_agent.py`
- ☑ `demo/fake_vendor_api.py` (break on demand) — `omniforge/demo/fake_vendor_api.py`
- ☑ Repo scaffold + deps + config + smoke test (`run_demo.py`, verified locally)
**Exit gate:** droplet runs ✓; demo app callable ✓ (local). *(Phase 0 complete — deploy app to droplet in Phase 1.)*

## Phase 1 — Closed Loop (hardcoded fix) — CRITICAL PATH
**Status:** DONE · **Milestone:** M1 Min Viable Demo ✓ · **Depends:** P0
**Goal:** prove reload mechanism E2E before adding intelligence. Phase 1 alone = still a demo.
- ☑ Guard catches crash (`proxy/guard.py`) — try/except, audit log
- ☑ Triage builds IncidentContext (`proxy/triage.py`) + signature (`memory/signature.py`)
- ☑ Apply fix via injected fixer (hardcoded fixer = inject patched source)
- ☑ Hot-swap via reload (`proxy/registry.py`, `proxy/supervisor.py`) — .pyc-safe recompile
- ☑ App recovers; bad patch → rollback + escalate
- ☑ TDD: guard(5) + hotswap(4) + triage(4) + signature(4) tests
**Exit gate:** E2E reload works ✓ (**min viable demo**).

## Phase 2 — Real Patch Generation
**Status:** DONE · **Milestone:** M2 Intelligence ✓ · **Depends:** P1
**Goal:** replace hardcoded patch w/ Gemini 3.5 Flash.
- ☑ `healer/diagnose.py` — `generate_patch(ctx, prior, client)`, injected model client
- ☑ Strict JSON out: `root_cause`, `unified_diff`, `repro_test` (`parse_patch`, fence-stripping)
- ☑ Hard constraints in prompt: minimal diff, no new ext net, in-scope file, include test (`build_prompt`)
- ☑ Retry once w/ stricter prompt on malformed; raise after 2 (`generate_patch`)
- ☑ `models/schemas.py` — `IncidentContext`, `Patch` (pydantic)
- ☑ TDD: 13 unit tests + 1 live test (real Gemini, verified `gemini-3.5-flash`/global)
- ☑ `healer/patcher.py` — apply unified diff via `git apply` (`-p1`/`-p0`), context-verified
- ☑ Live E2E heal test: Guard + real Gemini fixer heals a KeyError (`test_heal_live.py`, 10s)
**Exit gate:** generated patch heals live break ✓ — real Gemini caught crash → patched → hot-swapped → recovered, no human.

## Phase 3 — Safety Rails
**Status:** DONE · **Milestone:** M3 Trustworthy ✓ · **Depends:** P2
**Goal:** trust boundary — generated code never runs prod unscanned.
- ☑ Static scan: bandit, best-effort + injected (`healer/scanner.py`). semgrep deferred (heavy); AST/regex policy gate is the deterministic core.
- ☑ Policy gate: scope, max diff size (200), dangerous-sink + network-import denylist, no self-edit (`_policy_gate`)
- ☑ Sandbox validation (`healer/sandbox.py`): replay repro_test on patched source, before/after capture. Injectable `runner` — `local_runner` (subprocess pytest, no Docker) default; Docker runner drops in with same signature.
- ☑ Reject → escalate (never deploy): `healer/pipeline.py::make_gated_fixer` composes diagnose→patch→scan→sandbox into the Guard `Fixer` contract; any gate fail returns None → Guard escalates + audits.
- ☑ TDD: scanner(11) + sandbox(5, incl. real pytest) + pipeline(4) = 20 new tests, all green.
**Exit gate:** bad patch rejected + escalated ✓ — dangerous diff (eval) blocked by scan, failing repro blocked by sandbox, both escalate.
**Note:** bandit added to venv; `python`→`sys.executable` for subprocess. Docker/semgrep not present locally — sandbox local-runner fallback keeps demo path alive (Constitution II).

## Phase 4 — Memory / Continual Learning
**Status:** DONE · **Milestone:** M4 Self-Improve ✓ · **Depends:** P3
**Goal:** the "gets faster as it runs" payoff.
- ☑ SQLite store (`memory/store.py`): `remember`, `lookup`, `save_incident/patch`, `hit_count`. Dict/list fields JSON-serialized; INSERT OR REPLACE idempotent; re-remember preserves accumulated hits (COALESCE).
- ☑ Signature normalization + hash (`memory/signature.py`) — built P1, reused as memory key.
- ☑ Exact-match lookup → skip model → quick sandbox re-verify (`pipeline.make_gated_fixer(conn=...)`): cache hit reuses stored diff, re-verified in sandbox, NO model call; stale diff falls through to regen.
- ☑ Track + surface `hit_count`: starts 0 on remember, +1 per reuse.
- ☑ TDD: store(6) + pipeline memory-path(2, incl. ExplodingClient proving zero model calls on hit) = 8 new tests, 61 total green.
**Exit gate:** cache hit = instant fix, no model call ✓ — repeat signature heals from SQLite, model client never invoked, hit_count ticks up.

## Phase 5 — Rollback + Circuit Breaker + Audit
**Status:** DONE · **Milestone:** M5 Safe ✓ · **Depends:** P4
**Goal:** containment + polish.
- ☑ Rollback guard: post-swap re-run of the trigger input; regression → `supervisor.rollback` (revert source + reload) + escalate. Lived in `guard.call` since P1; covered by `test_bad_patch_rolls_back_and_escalates`.
- ☑ Circuit breaker (`healer/rollback.py::CircuitBreaker`): rolling-window cap on autonomous changes; injectable clock; Guard records a change on apply, denies + escalates when open.
- ☑ Kill switch (`kill_switch_engaged`): global stop via env `OMNIFORGE_KILL=1` or flag file; Guard escalates without touching source.
- ☑ Append-only audit log (`AuditLog`, JSONL): every outcome recorded (healed/rolled_back/escalated/kill_switch/circuit_open) — the only observability surface.
- ☑ Wired into Guard via optional `breaker`/`kill_switch`/`audit_log` params (back-compatible).
- ☑ TDD: rollback(7) + guard containment(4) = 11 new tests, 72 total green.
**Exit gate:** regression auto-rolls-back ✓; bad patch reverted + escalated; kill switch + breaker block autonomous change; audit log persists every outcome.

## Phase 6 — Demo + Video
**Status:** IN PROGRESS · **When:** due Sun 12:00 · **Milestone:** M6 Ship · **Depends:** P5
**Goal:** tight live pitch.
- ☑ Demo script per §8 (`demo/run_demo.py`): work → break vendor live → heal (patch→scan→sandbox→hot-swap) → cache-hit kicker (no model call, hit_count++) → audit/kill-switch/breaker line. Offline fallback patch keeps demo path alive; `OMNIFORGE_DEMO_LIVE=1` uses real Gemini. Verified offline: heal 0.72s → cache-hit 0.47s, source auto-restored (repeatable).
- ☑ README: tag event-built work (status updated to Phases 0–5 done).
- ☐ 1-min video *(manual — record stage run)*
- ☐ Rehearse 2x *(manual)*
- ☐ Pre-demo compliance check (constitution governance) *(manual)*
**Exit gate:** two clean run-throughs.

---

## Milestones

| ID | Name | Phases | Means |
|---|---|---|---|
| M0 | Foundation | P0 | infra + breakable target live |
| M1 | Min Viable Demo | P1 | something to show no matter what |
| M2 | Intelligence | P2 | real model-written fixes |
| M3 | Trustworthy | P3 | safe to auto-deploy |
| M4 | Self-Improve | P4 | continual-learning thesis proven |
| M5 | Safe | P5 | reckless-proof |
| M6 | Ship | P6 | judged + submitted |

---

## Changelog

- 2026-06-27 — **Phase 6 IN PROGRESS.** Stage-ready demo runner (`demo/run_demo.py`) exercises the full loop end-to-end: work → break vendor → raw crash → heal (patch/scan/sandbox/hot-swap) → same-error cache hit (no model call, hit_count++) → audit/kill-switch/breaker. Offline `FallbackClient` (Constitution II demo-path safety) + real Gemini via `OMNIFORGE_DEMO_LIVE=1`; agent source auto-restored so runs repeat. `sandbox.local_runner` now sets PYTHONPATH so repro_tests can import prod modules (local stand-in for "sandbox mirrors prod deps"). Verified offline (heal 0.72s, cache-hit 0.47s). +1 test (73 total). Remaining (manual): record 1-min video, rehearse 2x, compliance check.
- 2026-06-27 — **Phase 5 DONE (M5 ✓).** Containment built TDD: `healer/rollback.py` — `CircuitBreaker` (rolling-window change cap, injectable clock), `kill_switch_engaged` (env/flag-file global stop), `AuditLog` (append-only JSONL, the only observability surface). Wired into `proxy/guard.py` via optional back-compatible `breaker`/`kill_switch`/`audit_log` params: gates checked before any change, change recorded on apply, every outcome audited. Live rollback-on-regression already in `guard.call` since P1. +11 tests (72 total). **All 6 build phases done — only Phase 6 (demo/video, non-code) remains.**
- 2026-06-27 — **Phase 4 DONE (M4 ✓).** Fix-memory built TDD: `memory/store.py` gains `remember`/`lookup`/`save_incident`/`save_patch`/`hit_count` (JSON-serialized dict fields, idempotent upserts, COALESCE preserves hits on re-remember). `pipeline.make_gated_fixer(conn=...)` short-circuits the model on a signature hit — reuses the stored diff, re-verifies in the sandbox, zero model cost; remembers every fresh validated fix. +8 tests (61 total) incl. ExplodingClient asserting no model call on cache hit. Next: Phase 5 rollback/breaker/audit.
- 2026-06-27 — **Phase 3 DONE (M3 ✓).** Trust boundary built TDD: `healer/scanner.py` (policy gate: scope/size/self-edit/dangerous-sinks/network-import denylist + best-effort bandit), `healer/sandbox.py` (injectable runner; `local_runner` subprocess-pytest fallback since no Docker), `healer/pipeline.py` (`make_gated_fixer` wires diagnose→patch→scan→sandbox into Guard's Fixer contract; any gate fail → escalate, never deploy). +20 unit tests (53 total) all green. bandit installed; semgrep/Docker deferred (heavy/absent) — local fallbacks keep demo path alive. Next: Phase 4 memory.
- 2026-06-27 — roadmap promoted to living doc; phases + milestones + checklists added.
- 2026-06-27 — Phase 0 IN PROGRESS: scaffold, SQLite init, breakable demo built + verified locally (`run_demo.py` shows agent working then KeyError crash). Pending manual: DO droplet + Gemini key.
- 2026-06-27 — Vertex AI auth wired: ADC via gcloud, gemini-3.5-flash on `global` endpoint verified end-to-end. DO MCP server connected (`@digitalocean/mcp`). Only DO droplet remains for Phase 0.
- 2026-06-27 — **Phases 1 + 2 DONE (M1 ✓, M2 ✓).** Full self-heal loop built TDD: `proxy/{guard,triage,registry,supervisor}.py`, `memory/signature.py`, `healer/{diagnose,patcher}.py`, `models/schemas.py`. 33 unit tests + 2 live tests all green. Live E2E: real Gemini 3.5 Flash catches a KeyError, writes a diff, patcher applies it, hot-swap reloads, call recovers — no human (10s). Tests: `.venv/bin/pytest` (unit) / `-m live` (real model). Next: Phase 3 safety rails.
- 2026-06-27 — **Phase 2 patch generation built TDD.** `healer/diagnose.py` + `models/schemas.py`. 13 unit tests (build_prompt/parse_patch/generate_patch incl. retry+failure paths) + 1 live test against real Gemini 3.5 Flash (global endpoint) all green. Run: `.venv/bin/pytest` (unit) / `-m live` (real model). Fixed `.env` location us-central1→global (3.5-flash 404s regionally). NOTE: Phase 1 still pending — Phase 2 component complete + verified, heal exit gate needs P1 hot-swap.
- 2026-06-27 — **Phase 0 DONE (M0 ✓).** Droplet `omniforge` (id 580786696, sfo3, s-1vcpu-2gb, ubuntu-24-04) provisioned via DO API + cloud-init: Docker 29.1.3, Python 3.12.3, git. SSH key `~/.ssh/omniforge_do` (DO key id 57427027). IP 146.190.45.128. DO MCP re-added at user scope (`droplets,accounts,networking`).
