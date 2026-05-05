"""
Application configuration.

**Easiest path (Ollama):** install Ollama, copy ``.env.example`` to ``.env``, set ``DRY_RUN=1``
to try without email, then run ``run.ps1`` (Windows) or ``python main.py``.

For OpenAI cloud, set ``OPENAI_API_KEY`` and clear ``OPENAI_BASE_URL`` in ``.env`` (empty value).
"""

from __future__ import annotations

import os

_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_CONFIG_DIR)


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


_load_dotenv()

from openai import OpenAI

# --- YouTube (RSS feeds; no API key) ---
# Priority: CHANNEL_IDS env → data/gui_settings.json (from GUI) → fallback list below.
_ch_env = os.environ.get("CHANNEL_IDS", "").strip()
_gui_channels: list[str] | None = None
try:
    from yt_summarizer.settings_store import channel_list_for_config_merge

    _gui_channels = channel_list_for_config_merge()
except Exception:
    pass

if _ch_env:
    CHANNEL_IDS: list[str] = [x.strip() for x in _ch_env.split(",") if x.strip()]
elif _gui_channels is not None:
    CHANNEL_IDS = _gui_channels
else:
    CHANNEL_IDS = [
        "UCk-DG0N8StZ0T9Dv8XpVLZw",
    ]

# --- LLM defaults: Ollama local first; OpenAI cloud if only API key is set ---
if "OPENAI_BASE_URL" in os.environ:
    OPENAI_BASE_URL: str = os.environ.get("OPENAI_BASE_URL", "").strip()
elif os.environ.get("OPENAI_API_KEY", "").strip():
    OPENAI_BASE_URL = ""
else:
    OPENAI_BASE_URL = "http://127.0.0.1:11434/v1"

if "OPENAI_MODEL" in os.environ:
    _model_raw = os.environ.get("OPENAI_MODEL", "").strip()
    OPENAI_MODEL: str = _model_raw or (
        "llama3.2" if OPENAI_BASE_URL else "gpt-4o-mini"
    )
else:
    OPENAI_MODEL = "llama3.2" if OPENAI_BASE_URL else "gpt-4o-mini"

OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
CHUNK_SIZE: int = int(os.environ.get("CHUNK_SIZE", "3000"))

# Skip SMTP; print summary to logs only.
# If ``DRY_RUN`` is unset in the environment, default to dry-run when email is incomplete.
_dry_raw = os.environ.get("DRY_RUN", "").strip()
if _dry_raw:
    DRY_RUN: bool = _dry_raw.lower() in ("1", "true", "yes")
else:
    _has_mail = bool(os.environ.get("EMAIL_FROM", "").strip()) and bool(
        os.environ.get("EMAIL_TO", "").strip()
    )
    DRY_RUN = not _has_mail

# --- Email (smtplib) ---
EMAIL_SMTP_HOST: str = os.environ.get("EMAIL_SMTP_HOST", "smtp.gmail.com")
EMAIL_SMTP_PORT: int = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
EMAIL_USE_TLS: bool = os.environ.get("EMAIL_USE_TLS", "true").lower() in (
    "1",
    "true",
    "yes",
)
EMAIL_FROM: str = os.environ.get("EMAIL_FROM", "")
EMAIL_TO: str = os.environ.get("EMAIL_TO", "")
EMAIL_PASSWORD: str = os.environ.get("EMAIL_PASSWORD", "")

# --- Paths ---
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
PROCESSED_PATH = os.path.join(DATA_DIR, "processed.json")

# --- Runtime ---
TRANSCRIPT_RETRY_DELAY_SECONDS: float = float(
    os.environ.get("TRANSCRIPT_RETRY_DELAY_SECONDS", "3")
)
MAX_CHUNK_WORKERS: int = int(os.environ.get("MAX_CHUNK_WORKERS", "2"))

_OPENAI_JSON_ENV = os.environ.get("OPENAI_JSON_RESPONSE", "").strip().lower()


def use_json_object_response() -> bool:
    """Whether to request JSON-only responses from the chat API."""
    if _OPENAI_JSON_ENV in ("1", "true", "yes"):
        return True
    if _OPENAI_JSON_ENV in ("0", "false", "no"):
        return False
    return not bool(OPENAI_BASE_URL)


def build_openai_client() -> OpenAI:
    """
    Build an OpenAI SDK client for cloud or a compatible local endpoint.

    Local servers often ignore the API key; a placeholder is sent if none is set.
    """
    kwargs: dict = {}
    if OPENAI_BASE_URL:
        kwargs["base_url"] = OPENAI_BASE_URL
    key = OPENAI_API_KEY or "local-not-used"
    return OpenAI(api_key=key, **kwargs)


def llm_config_ok() -> bool:
    """True if we have credentials for cloud API or a local base URL."""
    if OPENAI_BASE_URL:
        return True
    return bool(OPENAI_API_KEY)
