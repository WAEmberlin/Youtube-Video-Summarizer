"""
OpenAI-based chunk summarization and a second-pass consolidation.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from yt_summarizer.chunking import TranscriptChunk

logger = logging.getLogger(__name__)


@dataclass
class ChunkSummary:
    """Structured summary for one transcript chunk."""

    chunk_index: int
    bullet_summary: list[str]
    key_insights: list[str]


@dataclass
class FinalSummary:
    """Combined output after the second pass."""

    tldr_bullets: list[str]
    main_takeaways: list[str]
    timeline: list[str]
    all_key_insights: list[str]


def _extract_json_object(content: str) -> str:
    """Trim optional Markdown fences around a JSON object."""
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _parse_chunk_json(content: str) -> tuple[list[str], list[str]]:
    data = json.loads(_extract_json_object(content))
    bullets = data.get("bullet_summary") or data.get("bullets") or []
    insights = data.get("key_insights") or data.get("insights") or []
    if not isinstance(bullets, list):
        bullets = [str(bullets)]
    if not isinstance(insights, list):
        insights = [str(insights)]
    return [str(b) for b in bullets], [str(i) for i in insights]


def summarize_chunk(
    client: OpenAI,
    model: str,
    chunk: TranscriptChunk,
) -> ChunkSummary:
    """
    Summarize a single transcript chunk using the chat completions API.

    Returns bullet points and key insights as structured JSON.
    """
    system = (
        "You summarize video transcript excerpts. Reply with compact, accurate notes. "
        "Output must be valid JSON only."
    )
    user = (
        "Summarize this transcript chunk. Return JSON with exactly these keys:\n"
        '- "bullet_summary": array of short bullet strings (the section summary)\n'
        '- "key_insights": array of distinct insights or claims\n\n'
        f"Chunk:\n{chunk.text}"
    )
    resp = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
    )
    raw = (resp.choices[0].message.content or "").strip()
    bullets, insights = _parse_chunk_json(raw)
    return ChunkSummary(
        chunk_index=chunk.index,
        bullet_summary=bullets,
        key_insights=insights,
    )


def summarize_chunks_parallel(
    client: OpenAI,
    model: str,
    chunks: list[TranscriptChunk],
    max_workers: int = 4,
) -> list[ChunkSummary]:
    """
    Summarize all chunks, optionally in parallel.

    Results are sorted by chunk index.
    """
    if not chunks:
        return []
    max_workers = max(1, min(max_workers, len(chunks)))
    out: list[ChunkSummary] = []

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut_map = {
            ex.submit(summarize_chunk, client, model, ch): ch.index for ch in chunks
        }
        for fut in as_completed(fut_map):
            try:
                out.append(fut.result())
            except Exception as e:
                idx = fut_map[fut]
                logger.exception("Chunk %s summarization failed: %s", idx, e)
                out.append(
                    ChunkSummary(
                        chunk_index=idx,
                        bullet_summary=[f"(summarization failed for chunk {idx})"],
                        key_insights=[],
                    )
                )

    out.sort(key=lambda x: x.chunk_index)
    return out


def consolidate_summaries(
    client: OpenAI,
    model: str,
    video_title: str,
    chunk_summaries: list[ChunkSummary],
) -> FinalSummary:
    """
    Second pass: merge chunk-level summaries into TL;DR, takeaways, and a timeline.
    """
    parts: list[str] = []
    all_insights: list[str] = []
    for cs in chunk_summaries:
        parts.append(
            f"--- Chunk {cs.chunk_index} ---\n"
            f"Bullets: {json.dumps(cs.bullet_summary, ensure_ascii=False)}\n"
            f"Insights: {json.dumps(cs.key_insights, ensure_ascii=False)}"
        )
        all_insights.extend(cs.key_insights)

    system = (
        "You combine partial summaries of one video into a coherent whole. "
        "Use only the provided chunk summaries. Output valid JSON only."
    )
    user = (
        f'Video title: "{video_title}"\n\n'
        "Here are per-chunk summaries:\n\n"
        + "\n\n".join(parts)
        + "\n\nReturn JSON with exactly these keys:\n"
        '- "tldr_bullets": 3 to 5 short bullet strings for the whole video\n'
        '- "main_takeaways": array of important takeaways (strings)\n'
        '- "timeline": array of strings describing the flow over time '
        '(use coarse timing hints like early/mid/late or minute ranges if present)\n'
    )
    resp = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
    )
    raw = (resp.choices[0].message.content or "").strip()
    data = json.loads(_extract_json_object(raw))
    tldr = data.get("tldr_bullets") or data.get("tldr") or []
    takeaways = data.get("main_takeaways") or []
    timeline = data.get("timeline") or []
    if isinstance(tldr, str):
        tldr = [tldr]
    if not isinstance(takeaways, list):
        takeaways = [str(takeaways)]
    if not isinstance(timeline, list):
        timeline = [str(timeline)]
    return FinalSummary(
        tldr_bullets=[str(x) for x in tldr],
        main_takeaways=[str(x) for x in takeaways],
        timeline=[str(x) for x in timeline],
        all_key_insights=all_insights,
    )
