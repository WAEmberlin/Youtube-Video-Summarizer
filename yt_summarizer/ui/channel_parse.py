"""Extract a YouTube channel ID (UC…) from pasted text or URL."""

from __future__ import annotations

import re

# Channel IDs are 24 characters, typically starting with UC.
_UC_CHANNEL_RE = re.compile(r"^UC[A-Za-z0-9_-]{22}$")


def parse_channel_id(text: str) -> str | None:
    """
    Return a channel ID if ``text`` is a bare ID or contains one in a known URL pattern.
    """
    t = (text or "").strip()
    if not t:
        return None
    if _UC_CHANNEL_RE.match(t):
        return t
    m = re.search(r"channel_id=(UC[A-Za-z0-9_-]{22})", t)
    if m:
        return m.group(1)
    m = re.search(r"/channel/(UC[A-Za-z0-9_-]{22})", t)
    if m:
        return m.group(1)
    m = re.search(r"\b(UC[A-Za-z0-9_-]{22})\b", t)
    if m:
        return m.group(1)
    return None
