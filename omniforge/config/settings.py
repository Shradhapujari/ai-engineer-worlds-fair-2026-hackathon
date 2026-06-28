"""Central config. Reads env, no external services beyond Gemini (Constitution III/IV).

Auth: Vertex AI via Application Default Credentials (ADC). No API key.
Set up ADC once on the droplet:
    gcloud auth application-default login        # interactive, or
    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json   # service account
"""
import os

# Patch generation — Gemini via Vertex AI (ADC auth)
USE_VERTEXAI = True
GCP_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
# gemini-3.5-flash is served on the `global` endpoint (404s in regional ones).
GCP_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
GEMINI_MODEL = os.environ.get("OMNIFORGE_MODEL", "gemini-3.5-flash")

# Fix memory — local SQLite file on the droplet
DB_PATH = os.environ.get("OMNIFORGE_DB", "omniforge.db")

# Safety (Phase 1): keep hardcoded-fix fallback available so a live model
# hiccup can't kill the demo (Constitution II).
USE_HARDCODED_FALLBACK = os.environ.get("OMNIFORGE_FALLBACK", "1") == "1"


def genai_client():
    """Build a google-genai client in Vertex mode. Credentials come from ADC.
    Imported lazily so Phase 0 (no SDK installed yet) still runs.
    """
    from google import genai

    if not GCP_PROJECT:
        raise RuntimeError(
            "GOOGLE_CLOUD_PROJECT unset. Set it and run "
            "`gcloud auth application-default login`."
        )
    return genai.Client(
        vertexai=True, project=GCP_PROJECT, location=GCP_LOCATION
    )
