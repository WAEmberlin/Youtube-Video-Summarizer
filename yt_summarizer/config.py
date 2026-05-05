"""
Application configuration.

Copy values here or set environment variables for secrets (recommended for production).
"""

from __future__ import annotations

import os

# --- YouTube (RSS feeds; no API key) ---
# Replace with real channel IDs (e.g. UC...).
CHANNEL_IDS: list[str] = [
    "UC_x5XG1OV2P6uZZ5FSM9Ttw",  # example: Google Developers — replace with your channels
]

# --- OpenAI ---
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
# Target ~words per chunk before summarization
CHUNK_SIZE: int = int(os.environ.get("CHUNK_SIZE", "3000"))

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
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
PROCESSED_PATH = os.path.join(DATA_DIR, "processed.json")

# --- Runtime ---
TRANSCRIPT_RETRY_DELAY_SECONDS: float = float(
    os.environ.get("TRANSCRIPT_RETRY_DELAY_SECONDS", "3")
)
MAX_CHUNK_WORKERS: int = int(os.environ.get("MAX_CHUNK_WORKERS", "4"))
