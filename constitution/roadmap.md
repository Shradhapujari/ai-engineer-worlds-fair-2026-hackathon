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
| 4 | Memory / continual learning | PLANNED | M4 Self-Improve | Cache hit = instant fix, no model call |
| 5 | Rollback + circuit breaker | PLANNED | M5 Safe | Regression auto-rolls-back |
| 6 | Demo + video | PLANNED | M6 Ship | Two clean run-throughs |

**Overall:** 4/7 phases done. Next = Phase 4 (memory / continual learning).

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
**Status:** PLANNED · **Milestone:** M4 Self-Improve · **Depends:** P3
**Goal:** the "gets faster as it runs" payoff.
- ☐ SQLite store (`memory/store.py`)
- ☐ Signature normalization + hash (`memory/signature.py`)
- ☐ Exact-match lookup → skip model → hot-swap (quick re-verify)
- ☐ Track + surface `hit_count`
**Exit gate:** cache hit = instant fix, no model call.

## Phase 5 — Rollback + Circuit Breaker + Audit
**Status:** PLANNED · **Milestone:** M5 Safe · **Depends:** P4
**Goal:** containment + polish.
- ☐ Rollback guard (`healer/rollback.py`): re-run input, regression → auto-rollback
- ☐ Circuit breaker: per-window change cap
- ☐ Kill switch (global)
- ☐ Append-only audit log (only observability surface)
- ☐ Polish
**Exit gate:** regression auto-rolls-back.

## Phase 6 — Demo + Video
**Status:** PLANNED · **When:** due Sun 12:00 · **Milestone:** M6 Ship · **Depends:** P5
**Goal:** tight live pitch.
- ☐ Demo script per §8 (work → break vendor live → heal → cache-hit kicker → audit/kill-switch line)
- ☐ 1-min video
- ☐ README: tag event-built work
- ☐ Rehearse 2x
- ☐ Pre-demo compliance check (constitution governance)
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

- 2026-06-27 — **Phase 3 DONE (M3 ✓).** Trust boundary built TDD: `healer/scanner.py` (policy gate: scope/size/self-edit/dangerous-sinks/network-import denylist + best-effort bandit), `healer/sandbox.py` (injectable runner; `local_runner` subprocess-pytest fallback since no Docker), `healer/pipeline.py` (`make_gated_fixer` wires diagnose→patch→scan→sandbox into Guard's Fixer contract; any gate fail → escalate, never deploy). +20 unit tests (53 total) all green. bandit installed; semgrep/Docker deferred (heavy/absent) — local fallbacks keep demo path alive. Next: Phase 4 memory.
- 2026-06-27 — roadmap promoted to living doc; phases + milestones + checklists added.
- 2026-06-27 — Phase 0 IN PROGRESS: scaffold, SQLite init, breakable demo built + verified locally (`run_demo.py` shows agent working then KeyError crash). Pending manual: DO droplet + Gemini key.
- 2026-06-27 — Vertex AI auth wired: ADC via gcloud, gemini-3.5-flash on `global` endpoint verified end-to-end. DO MCP server connected (`@digitalocean/mcp`). Only DO droplet remains for Phase 0.
- 2026-06-27 — **Phases 1 + 2 DONE (M1 ✓, M2 ✓).** Full self-heal loop built TDD: `proxy/{guard,triage,registry,supervisor}.py`, `memory/signature.py`, `healer/{diagnose,patcher}.py`, `models/schemas.py`. 33 unit tests + 2 live tests all green. Live E2E: real Gemini 3.5 Flash catches a KeyError, writes a diff, patcher applies it, hot-swap reloads, call recovers — no human (10s). Tests: `.venv/bin/pytest` (unit) / `-m live` (real model). Next: Phase 3 safety rails.
- 2026-06-27 — **Phase 2 patch generation built TDD.** `healer/diagnose.py` + `models/schemas.py`. 13 unit tests (build_prompt/parse_patch/generate_patch incl. retry+failure paths) + 1 live test against real Gemini 3.5 Flash (global endpoint) all green. Run: `.venv/bin/pytest` (unit) / `-m live` (real model). Fixed `.env` location us-central1→global (3.5-flash 404s regionally). NOTE: Phase 1 still pending — Phase 2 component complete + verified, heal exit gate needs P1 hot-swap.
- 2026-06-27 — **Phase 0 DONE (M0 ✓).** Droplet `omniforge` (id 580786696, sfo3, s-1vcpu-2gb, ubuntu-24-04) provisioned via DO API + cloud-init: Docker 29.1.3, Python 3.12.3, git. SSH key `~/.ssh/omniforge_do` (DO key id 57427027). IP 146.190.45.128. DO MCP re-added at user scope (`droplets,accounts,networking`).
