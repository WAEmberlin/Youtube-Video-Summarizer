"""
YouTube transcript retrieval with retry and Whisper placeholder.

Uses youtube-transcript-api 1.x (instance API: ``fetch`` / ``list``).
"""

from __future__ import annotations

import logging
import time
from typing import Any

from youtube_transcript_api import FetchedTranscript, YouTubeTranscriptApi

logger = logging.getLogger(__name__)

# Priority language codes for ``fetch()`` — tries manually created, then generated per lib behavior.
_LANGUAGE_PRIORITY: tuple[str, ...] = (
    "en",
    "en-US",
    "en-GB",
    "es",
    "es-419",
    "fr",
    "fr-FR",
    "de",
    "de-DE",
    "pt",
    "pt-BR",
    "ja",
    "ko",
    "hi",
    "zh",
    "zh-CN",
    "zh-TW",
    "ru",
    "it",
    "nl",
    "pl",
    "tr",
    "sv",
    "da",
    "fi",
    "no",
    "nb",
    "cs",
    "el",
    "he",
    "hu",
    "id",
    "ms",
    "ro",
    "sk",
    "uk",
    "vi",
    "th",
    "ar",
    "bn",
    "ta",
    "te",
    "mr",
    "gu",
    "kn",
    "ml",
    "pa",
)


def _fetched_to_items(fetched: FetchedTranscript) -> list[dict[str, Any]]:
    """Convert v1 ``FetchedTranscript`` to legacy list-of-dicts shape."""
    return [
        {"text": s.text, "start": s.start, "duration": s.duration}
        for s in fetched.snippets
    ]


def _fetch_any_available_track(api: YouTubeTranscriptApi, video_id: str) -> list[dict[str, Any]]:
    """Try every transcript track until one downloads successfully."""
    last_err: BaseException | None = None
    try:
        transcript_list = api.list(video_id)
    except Exception as e:
        raise e

    for transcript in transcript_list:
        try:
            fetched = transcript.fetch()
            return _fetched_to_items(fetched)
        except Exception as e:
            last_err = e
            logger.debug(
                "Track %s failed for %s: %s",
                getattr(transcript, "language_code", "?"),
                video_id,
                e,
            )
            continue

    if last_err is not None:
        raise last_err
    raise RuntimeError(f"No transcript tracks listed for video {video_id}")


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
        List of segments compatible with downstream chunking (legacy dict shape).
    """
    api = YouTubeTranscriptApi()
    last_error: BaseException | None = None

    # Strategy 1: youtube-transcript-api 1.x instance ``fetch`` with language priority.
    try:
        fetched = api.fetch(video_id, languages=_LANGUAGE_PRIORITY)
        return _fetched_to_items(fetched)
    except Exception as e:
        last_error = e
        logger.warning(
            "Transcript fetch failed for %s (attempt 1): %s",
            video_id,
            e,
        )

    time.sleep(retry_delay)

    # Strategy 2: walk every transcript track YouTube lists (covers uncommon language codes).
    try:
        return _fetch_any_available_track(api, video_id)
    except Exception as e:
        last_error = e
        logger.warning("Transcript fetch failed for %s (attempt 2): %s", video_id, e)

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
