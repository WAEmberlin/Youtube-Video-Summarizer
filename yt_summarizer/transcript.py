"""
YouTube transcript retrieval with retry and Whisper placeholder.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger(__name__)


def transcribe_with_whisper(video_id: str) -> str | None:
    """
    Placeholder for future local Whisper / speech-to-text integration.

    Implement this to download audio and run Whisper when transcripts are unavailable.

    Args:
        video_id: YouTube video ID.

    Returns:
        Full transcript text, or None if not implemented or failed.
    """
    logger.debug("Whisper stub called for video_id=%s (not implemented)", video_id)
    return None


def fetch_transcript_items(video_id: str, retry_delay: float = 3.0) -> list[dict[str, Any]]:
    """
    Fetch transcript segments as a list of dicts with text, start, and duration.

    Retries once after ``retry_delay`` seconds if the first attempt fails.
    On persistent failure, attempts the Whisper stub and returns an empty list
    if no text is produced.

    Args:
        video_id: YouTube video ID.
        retry_delay: Seconds to wait before one retry.

    Returns:
        List of segments compatible with ``youtube_transcript_api`` format.
    """
    last_error: BaseException | None = None
    for attempt in range(2):
        try:
            raw = YouTubeTranscriptApi.get_transcript(video_id)
            return list(raw)
        except BaseException as e:
            last_error = e
            logger.warning(
                "Transcript fetch failed for %s (attempt %s): %s",
                video_id,
                attempt + 1,
                e,
            )

        if attempt == 0:
            time.sleep(retry_delay)

    whisper_text = transcribe_with_whisper(video_id)
    if whisper_text:
        return [{"text": whisper_text, "start": 0.0, "duration": 0.0}]

    if last_error:
        logger.error("Giving up on transcript for %s: %s", video_id, last_error)
    return []


def items_to_plain_text(items: list[dict[str, Any]]) -> str:
    """Join transcript segments into plain text without timestamps."""
    parts = [str(i.get("text", "")).strip() for i in items]
    return " ".join(p for p in parts if p)
