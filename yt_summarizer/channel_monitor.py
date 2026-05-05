"""
Fetch newest videos per channel using YouTube RSS feeds (no API key).
"""

from __future__ import annotations

import logging
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

logger = logging.getLogger(__name__)

ATOM_NS = "http://www.w3.org/2005/Atom"
YT_NS = "http://www.youtube.com/xml/schemas/v2015"


def _tag(ns: str, local: str) -> str:
    return f"{{{ns}}}{local}"


@dataclass(frozen=True)
class VideoRef:
    """Minimal reference to a video from the RSS feed."""

    video_id: str
    title: str
    channel_id: str


def _parse_video_id_from_entry_id(entry_id_text: str | None) -> str | None:
    if not entry_id_text:
        return None
    # Format: yt:video:VIDEO_ID
    m = re.search(r"yt:video:([A-Za-z0-9_-]{11})", entry_id_text)
    if m:
        return m.group(1)
    m = re.search(r"[?&]v=([A-Za-z0-9_-]{11})", entry_id_text)
    return m.group(1) if m else None


def fetch_newest_video_for_channel(channel_id: str, timeout: float = 30.0) -> VideoRef | None:
    """
    Return the newest video for a channel from its official Atom feed.

    The feed orders entries with the most recent first.

    Args:
        channel_id: YouTube channel ID (UC...).
        timeout: HTTP timeout in seconds.

    Returns:
        VideoRef for the latest entry, or None if the feed is empty or invalid.
    """
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "yt_summarizer/1.0 (+https://github.com)"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
    except urllib.error.URLError as e:
        logger.warning("RSS fetch failed for channel %s: %s", channel_id, e)
        return None

    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        logger.warning("RSS parse failed for channel %s: %s", channel_id, e)
        return None

    entry_tag = _tag(ATOM_NS, "entry")
    title_tag = _tag(ATOM_NS, "title")
    id_tag = _tag(ATOM_NS, "id")

    link_tag = _tag(ATOM_NS, "link")
    for entry in root.findall(f".//{entry_tag}"):
        title_el = entry.find(title_tag)
        id_el = entry.find(id_tag)
        title = (title_el.text or "").strip() if title_el is not None else ""
        entry_id = id_el.text.strip() if id_el is not None and id_el.text else None
        video_id = _parse_video_id_from_entry_id(entry_id)
        if not video_id:
            vid_el = entry.find(_tag(YT_NS, "videoId"))
            if vid_el is not None and vid_el.text:
                video_id = vid_el.text.strip()
        if not video_id:
            for link in entry.findall(link_tag):
                href = link.get("href") or ""
                video_id = _parse_video_id_from_entry_id(href)
                if video_id:
                    break
        if video_id:
            return VideoRef(video_id=video_id, title=title, channel_id=channel_id)

    logger.info("No entries found in RSS for channel %s", channel_id)
    return None
