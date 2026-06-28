# Running the testbench

This folder is the **guinea-pig agent** that OmniForge heals. It has no venv of
its own — it borrows OmniForge's. `runner.py` is the only file that imports
OmniForge; it adds the sibling repo to `sys.path`, so nothing needs installing here.

```
Ai Engineer World Fair/
├─ ai-engineer-worlds-fair-2026-hackathon/   # OmniForge proxy (has .venv + deps)
└─ omniforge-testbench/                       # <- you are here
```

All commands below are run **from this folder**:

```bash
cd "/Users/shradha/hackathon/Ai Engineer World Fair/omniforge-testbench"
```

The OmniForge venv is referenced by relative path. Every command uses
`../ai-engineer-worlds-fair-2026-hackathon/.venv/bin/...`.

> Tip: `OF="../ai-engineer-worlds-fair-2026-hackathon"` then reuse `$OF`. The
> export and the command that uses it must be in the **same shell**. If
> `echo $OF` prints empty, the export didn't take — use the full path instead.

The agent has **5 intentional bugs**, one error class per phase:

| Fixture | Error | Where |
|---|---|---|
| `missing_name.json` | KeyError | `parser.py` — `obj["name"]` on object with no name |
| `unknown_tool.json` | KeyError | `registry.py` — lookup of unregistered tool |
| `bad_types.json` | TypeError | `tools.py` — `"two" + 3` |
| `divide_zero.json` | ZeroDivisionError | `tools.py` — `a / b`, `b == 0` |
| `none_result.json` | AttributeError | `format.py` — formats a `None` result |

---

# PART A — the agent WITHOUT OmniForge (it crashes)

This is the raw agent — no Guard, no healing. The bugs are real and crash hard.

## A1. Crash one buggy call by hand

```bash
../ai-engineer-worlds-fair-2026-hackathon/.venv/bin/python -c \
  "import json; from agent.run import run; \
   run(json.load(open('test-data/buggy/divide_zero.json')))"
```

Expect a raw traceback ending in:

```
ZeroDivisionError: division by zero
```

Swap `divide_zero.json` for any fixture in the table to see that error class crash.

## A2. Prove all 5 bugs crash (repro tests)

```bash
../ai-engineer-worlds-fair-2026-hackathon/.venv/bin/pytest tests/test_bugs_reproduce.py -v
```

Expect: **5 passed** — each test asserts the agent raises its error class. (Green
here means "the bug reliably crashes," i.e. a valid heal target.)

## A3. The happy path still works (no bug triggered)

```bash
../ai-engineer-worlds-fair-2026-hackathon/.venv/bin/pytest tests/test_happy_path.py -v
```

So the agent isn't broken everywhere — only the 5 bug fixtures crash.

---

# PART B — the agent WITH OmniForge (it heals)

Now wrap the same agent in OmniForge's Guard. On a crash it catches the error,
has Gemini write a patch, scans + sandboxes it, hot-swaps the fix in, and caches
it by error signature so the next identical error is fixed instantly.

Auth once (Vertex AI via ADC, no API key):

```bash
gcloud auth application-default login
```

## B1. Heal a testbench bug — live Gemini

```bash
GOOGLE_CLOUD_PROJECT=ai-hack-sf26sfo-7019 GOOGLE_CLOUD_LOCATION=global \
  ../ai-engineer-worlds-fair-2026-hackathon/.venv/bin/python heal_demo.py divide_zero.json
```

`heal_demo.py` snapshots `agent/` source, runs the buggy call under the real
gated fixer (Gemini → scan → sandbox → hot-swap → fix-memory), runs it again to
show the cache hit, then restores `agent/`.

> **KNOWN LIMITATION — B1 currently escalates, not heals.** OmniForge's Guard
> hot-swaps the *guarded* module (`agent/run.py`), but the testbench's bugs live
> in sibling modules (`parser/registry/tools/format`). The patch lands on the
> wrong file and the heal rolls back. Fixing this needs a Guard change (hot-swap
> `ctx.source_file`'s module + refresh importer bindings). Until then, use B2.

## B2. Proven live heal — OmniForge's own demo

OmniForge's bundled demo agent is a single self-contained module, so it heals
end-to-end today. **This is the working "see it heal" path.**

```bash
cd "../ai-engineer-worlds-fair-2026-hackathon"
GOOGLE_CLOUD_PROJECT=ai-hack-sf26sfo-7019 GOOGLE_CLOUD_LOCATION=global \
  OMNIFORGE_DEMO_LIVE=1 .venv/bin/python -m omniforge.demo.run_demo
```

Shows the full loop:

```
1) agent works:        It's 14°C in london.
2) vendor breaks:      CRASH — KeyError: 'temp_c'      <- the PART A failure
3) OmniForge heals:    It's 14°C in london.   [~14s, no human]
4) repeat same error:  It's 14°C in london.   [~0.4s from SQLite, NO model call]
5) audit log + kill switch + circuit breaker
```

If step 3 already shows ~0.4s (signature cached from a prior run), force a fresh
live heal by clearing the cache first:

```bash
rm omniforge.db && .venv/bin/python -m omniforge.memory.store   # reinit empty db
```

---

## How the seam works (`runner.py`)

```python
Guard(run_module, "run", fixer=...)   # wraps agent.run.run
guard.call(raw)                       # runs agent; on crash -> triage -> fixer -> hot-swap
```

- `agent/` stays pure (never imports omniforge) — that's why PART A crashes raw.
- Phase 0 `runner.py` uses a placeholder escalate-fixer (buggy call just escalates).
- `heal_demo.py` swaps in the **real** `make_gated_fixer(conn=...)` for PART B.
