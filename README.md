# OmniForge

**The Self-Healing Proxy** — autonomous runtime debugging, patching, and hot-swapping for production AI systems.

Built at **AI Engineer World's Fair Hackathon 2026** · Theme: *The Self-Improvement Stack*.

🎬 **[Live architecture walkthrough →](https://omniforge-anim.vercel.app)** — animated data-flow showing how OmniForge catches, patches, and hot-swaps itself (new here? start here).

OmniForge supervises a running AI app. On an unhandled error it catches the crash, has Gemini 3.5 Flash write a patch, runs it through a security scanner + Docker sandbox, and — only if it passes — hot-swaps the fix into the live process. Every validated fix is cached in local SQLite by error signature, so repeat errors are fixed instantly with no model call. **The more it runs, the faster and cheaper it heals.**

Governing docs: [`constitution/`](constitution/) — constitution, tech-stack, roadmap.

## Stack
Gemini 3.5 Flash · DigitalOcean droplet · SQLite · Docker · semgrep + bandit · Python 3.11+. (Constitution: Gemini + DO only, all tooling local.)

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env                       # set GOOGLE_CLOUD_PROJECT + location
gcloud auth application-default login      # Vertex AI auth via ADC (no API key)
python -m omniforge.memory.store           # init SQLite
python -m omniforge.demo.run_demo          # smoke test: agent works, then crashes
```

## Tests
```bash
.venv/bin/pytest                 # unit (fast, no network) — run after every change
GOOGLE_CLOUD_PROJECT=ai-hack-sf26sfo-7019 GOOGLE_CLOUD_LOCATION=global \
  .venv/bin/pytest -m live       # live: real Gemini via Vertex/ADC
```
TDD: every functionality has a test under `omniforge/tests/`. Live tests (`@pytest.mark.live`) hit real Gemini and are deselected by default.

## Status
Phases 0–5 done (6/7) — full self-heal loop: catch → Gemini patch → security scan + sandbox → hot-swap → fix-memory (cache hits skip the model) → circuit breaker + kill switch + append-only audit. 72 unit + 2 live tests green. Only Phase 6 (demo + video) remains. See [roadmap](constitution/roadmap.md).

## Built at the event
All code under `omniforge/` was built during the hackathon.
