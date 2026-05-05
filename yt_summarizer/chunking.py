"""
Split transcripts into word-bounded chunks while preserving start timestamps per chunk.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable


def _word_count(text: str) -> int:
    if not text.strip():
        return 0
    return len(re.findall(r"\S+", text))


def _format_timestamp(seconds: float) -> str:
    """Format seconds as H:MM:SS or M:SS for readability."""
    if seconds < 0:
        seconds = 0.0
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


@dataclass(frozen=True)
class TranscriptChunk:
    """A slice of transcript text with the approximate time where it begins."""

    index: int
    start_seconds: float
    text: str
    word_count: int


def _emit_chunks_from_words(
    words: list[str],
    start_seconds: float,
    chunk_size_words: int,
    chunk_index: int,
) -> tuple[list[TranscriptChunk], list[str], int]:
    """
    Turn a word list into one or more chunks, returning leftover words and next index.
    """
    chunks: list[TranscriptChunk] = []
    i = 0
    while i < len(words):
        take = words[i : i + chunk_size_words]
        i += len(take)
        body = " ".join(take).strip()
        if not body:
            continue
        ts = _format_timestamp(start_seconds)
        labeled = f"[{ts}] {body}"
        chunks.append(
            TranscriptChunk(
                index=chunk_index,
                start_seconds=start_seconds,
                text=labeled,
                word_count=_word_count(labeled),
            )
        )
        chunk_index += 1
    return chunks, [], chunk_index


def chunk_transcript_with_timestamps(
    transcript_items: Iterable[dict[str, Any]],
    chunk_size_words: int = 3000,
) -> list[TranscriptChunk]:
    """
    Split transcript segments into chunks of approximately ``chunk_size_words`` words.

    Chunk boundaries prefer segment boundaries; segments longer than the limit are split
    on whitespace only. Each chunk records the ``start`` timestamp of its first segment.

    Args:
        transcript_items: Items from ``youtube_transcript_api`` (text, start, duration).
        chunk_size_words: Target maximum words per chunk.

    Returns:
        Ordered list of :class:`TranscriptChunk` instances.
    """
    items = list(transcript_items)
    if not items or chunk_size_words <= 0:
        return []

    result: list[TranscriptChunk] = []
    buf_words: list[str] = []
    buf_start: float | None = None
    buf_word_count = 0
    chunk_index = 0

    def flush_buffer() -> None:
        nonlocal buf_words, buf_start, buf_word_count, chunk_index
        if not buf_words or buf_start is None:
            buf_words = []
            buf_start = None
            buf_word_count = 0
            return
        body = " ".join(buf_words).strip()
        if not body:
            buf_words = []
            buf_start = None
            buf_word_count = 0
            return
        ts = _format_timestamp(buf_start)
        labeled = f"[{ts}] {body}"
        result.append(
            TranscriptChunk(
                index=chunk_index,
                start_seconds=buf_start,
                text=labeled,
                word_count=_word_count(labeled),
            )
        )
        chunk_index += 1
        buf_words = []
        buf_start = None
        buf_word_count = 0

    for item in items:
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        try:
            start = float(item.get("start", 0.0))
        except (TypeError, ValueError):
            start = 0.0

        seg_words = text.split()
        if not seg_words:
            continue

        if buf_start is None:
            buf_start = start

        # Adding this whole segment would exceed the budget: flush first (if anything buffered).
        if buf_word_count + len(seg_words) > chunk_size_words and buf_words:
            flush_buffer()
            buf_start = start

        # Segment alone exceeds budget: emit directly in slice-sized pieces.
        if len(seg_words) > chunk_size_words:
            flush_buffer()
            extra, _, chunk_index = _emit_chunks_from_words(
                seg_words, start, chunk_size_words, chunk_index
            )
            result.extend(extra)
            buf_start = None
            buf_word_count = 0
            continue

        buf_words.extend(seg_words)
        buf_word_count += len(seg_words)

        if buf_word_count >= chunk_size_words:
            flush_buffer()

    flush_buffer()
    # Re-index sequentially in case merges produced gaps (should not happen).
    fixed: list[TranscriptChunk] = []
    for i, ch in enumerate(result):
        fixed.append(
            TranscriptChunk(
                index=i,
                start_seconds=ch.start_seconds,
                text=ch.text,
                word_count=ch.word_count,
            )
        )
    return fixed
