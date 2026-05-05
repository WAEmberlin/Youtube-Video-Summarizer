"""
Run transcript fetch, chunking, summarization, and email for a single video.

Uses explicit parameters so the GUI does not depend on process-wide ``config`` values.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from openai import OpenAI

from yt_summarizer.chunking import chunk_transcript_with_timestamps
from yt_summarizer.email_sender import build_summary_email_html, send_html_email
from yt_summarizer.settings_store import GuiSettings
from yt_summarizer.summarize import (
    FinalSummary,
    consolidate_summaries,
    summarize_chunks_parallel,
)
from yt_summarizer.transcript import fetch_transcript_items

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Per-run LLM and delivery options (from GUI settings)."""

    llm_base_url: str
    llm_model: str
    openai_api_key: str
    dry_run: bool
    email_smtp_host: str
    email_smtp_port: int
    email_use_tls: bool
    email_from: str
    email_to: str
    email_password: str
    chunk_size: int
    max_chunk_workers: int
    transcript_retry_delay: float = 3.0
    use_openai_cloud: bool = False


def build_llm_client(pc: PipelineConfig) -> OpenAI:
    kwargs: dict = {}
    base = "" if pc.use_openai_cloud else (pc.llm_base_url or "").strip()
    if base:
        kwargs["base_url"] = base
    key = (pc.openai_api_key or "").strip() or "local-not-used"
    return OpenAI(api_key=key, **kwargs)


def use_json_object_for_pipeline(pc: PipelineConfig) -> bool:
    """OpenAI cloud JSON mode; local Ollama typically off."""
    if pc.use_openai_cloud:
        return True
    return not bool((pc.llm_base_url or "").strip())


def summarize_video_only(
    pc: PipelineConfig,
    video_id: str,
    title: str,
) -> tuple[FinalSummary | None, str]:
    """
    Fetch transcript, chunk, and summarize only (no email).

    Returns:
        (FinalSummary, "") on success, or (None, error_message).
    """
    if pc.use_openai_cloud:
        if not (pc.openai_api_key or "").strip():
            return None, "OpenAI API key is required for cloud mode."
    elif not (pc.llm_base_url or "").strip():
        return None, "Set the Ollama / OpenAI-compatible base URL."

    client = build_llm_client(pc)
    use_json = use_json_object_for_pipeline(pc)

    items = fetch_transcript_items(video_id, retry_delay=pc.transcript_retry_delay)
    if not items:
        return None, "No transcript available for this video."

    chunks = chunk_transcript_with_timestamps(items, chunk_size_words=pc.chunk_size)
    if not chunks:
        return None, "Transcript produced no chunks."

    try:
        chunk_sums = summarize_chunks_parallel(
            client,
            pc.llm_model,
            chunks,
            max_workers=pc.max_chunk_workers,
            use_json_object=use_json,
        )
        final_summary = consolidate_summaries(
            client,
            pc.llm_model,
            title,
            chunk_sums,
            use_json_object=use_json,
        )
    except Exception as e:
        logger.exception("Summarization failed")
        return None, str(e)

    return final_summary, ""


def summarize_and_deliver_video(
    pc: PipelineConfig,
    video_id: str,
    title: str,
) -> tuple[bool, str]:
    """
    Full pipeline for one video.

    Returns:
        (success, message) where message is error text or a short success note.
    """
    if not pc.dry_run:
        if not pc.email_from.strip() or not pc.email_to.strip():
            return False, "Email From and To are required when not in dry-run mode."

    final_summary, err = summarize_video_only(pc, video_id, title)
    if final_summary is None:
        return False, err

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    html = build_summary_email_html(title, video_url, final_summary)
    subject = f"[yt_summarizer] {title}"

    if pc.dry_run:
        logger.info("Dry-run: %s — %s", title, video_url)
        return True, f"Dry-run OK: {title}"

    try:
        send_html_email(
            smtp_host=pc.email_smtp_host,
            smtp_port=pc.email_smtp_port,
            use_tls=pc.email_use_tls,
            from_addr=pc.email_from.strip(),
            to_addr=pc.email_to.strip(),
            password=pc.email_password,
            subject=subject,
            html_body=html,
        )
    except Exception as e:
        logger.exception("Email failed")
        return False, str(e)

    return True, f"Emailed: {title}"


def pipeline_from_gui_settings(gs: GuiSettings) -> PipelineConfig:
    """Build a pipeline config from persisted GUI settings."""
    return PipelineConfig(
        llm_base_url=gs.llm_base_url.strip(),
        llm_model=gs.llm_model.strip() or "llama3.2",
        openai_api_key=gs.openai_api_key,
        dry_run=gs.dry_run,
        email_smtp_host=gs.email_smtp_host.strip() or "smtp.gmail.com",
        email_smtp_port=gs.email_smtp_port,
        email_use_tls=gs.email_use_tls,
        email_from=gs.email_from,
        email_to=gs.email_to,
        email_password=gs.email_password,
        chunk_size=gs.chunk_size,
        max_chunk_workers=gs.max_chunk_workers,
        use_openai_cloud=gs.use_openai_cloud,
    )
