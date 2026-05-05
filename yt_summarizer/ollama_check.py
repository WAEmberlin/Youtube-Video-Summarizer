"""
Quick connectivity check for Ollama's HTTP API (no extra dependencies).
"""

from __future__ import annotations

import logging
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)


def verify_ollama_compatible_base(http_base: str, timeout: float = 5.0) -> str | None:
    """
    Verify that a server at ``http_base`` responds like Ollama (``/api/tags``).

    Args:
        http_base: Origin only, e.g. ``http://127.0.0.1:11434`` (no ``/v1`` path).

        timeout: Seconds.

    Returns:
        ``None`` if OK, otherwise a short human-readable error message.
    """
    origin = http_base.rstrip("/")
    tags_url = origin + "/api/tags"
    req = urllib.request.Request(tags_url, headers={"User-Agent": "yt_summarizer/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return f"Ollama health check got HTTP {resp.status} from {tags_url}"
    except urllib.error.URLError as e:
        return (
            f"Cannot reach Ollama at {origin} ({e}). "
            "Start the Ollama app (or `ollama serve`) and try again."
        )
    return None


def ollama_origin_from_openai_base(base_url: str) -> str | None:
    """
    Map OpenAI-style base (``.../v1``) to an Ollama origin (scheme://host:port).
    """
    u = base_url.strip()
    if not u:
        return None
    parts = urllib.parse.urlsplit(u)
    if not parts.scheme or not parts.netloc:
        return None
    # Strip trailing /v1 from path
    path = (parts.path or "").rstrip("/")
    if path.endswith("/v1"):
        path = path[: -len("/v1")]
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path or "", "", ""))
