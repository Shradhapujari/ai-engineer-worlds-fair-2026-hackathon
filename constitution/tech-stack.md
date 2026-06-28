# OmniForge — Tech Stack

Source: `OmniForge_Architecture.md` §3. Stack lock per Constitution Principle III+IV.

| Concern | Choice | Notes |
|---|---|---|
| Hosting / compute | **DigitalOcean Droplet** (Docker host) | One droplet: proxy + supervised app + sandbox containers + SQLite file. Claim $200 DO credits at DO table. Eligible *Best Usage of DigitalOcean*. |
| Patch generation | **Gemini 3.5 Flash** (via Vertex AI) | Fast + cheap → fits 10s budget. Auth = Application Default Credentials (ADC), no API key. `gcloud auth application-default login`. |
| Fix memory | **SQLite** (local file on droplet) | Signature-hash → validated patch. Zero external deps. |
| Security scan | **semgrep + bandit** (local pip) | No external calls. |
| Sandbox isolation | **Docker** (on droplet) | Ephemeral container per validation. |
| Language | **Python 3.11+** | Enables runtime reload; matches typical agent stacks. |

**Locked:** Gemini + DO only. No other vendors/compute. All persist + tooling local.
