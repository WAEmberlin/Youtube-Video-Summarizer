"""
Entry point: one full monitoring + summarization + email cycle.

Schedule with cron (Linux/macOS) or Task Scheduler (Windows), for example daily:

    0 8 * * * cd /path/to/project && /path/to/python main.py >> /var/log/yt_summarizer.log 2>&1
"""

from __future__ import annotations

import logging
import sys

from yt_summarizer import config
from yt_summarizer.channel_monitor import fetch_newest_video_for_channel
from yt_summarizer.chunking import chunk_transcript_with_timestamps
from yt_summarizer.email_sender import build_summary_email_html, send_html_email
from yt_summarizer.processed_store import load_processed_video_ids, save_processed_video_ids
from yt_summarizer.summarize import consolidate_summaries, summarize_chunks_parallel
from yt_summarizer.transcript import fetch_transcript_items
from openai import OpenAI


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def run_cycle() -> int:
    """
    Poll configured channels, summarize each channel's newest video when new, and email.

    Returns:
        Process exit code (0 success, non-zero on configuration or fatal errors).
    """
    _setup_logging()
    log = logging.getLogger("yt_summarizer.main")

    if not config.OPENAI_API_KEY:
        log.error("OPENAI_API_KEY is not set. Export it or edit config.py.")
        return 1
    if not config.EMAIL_FROM or not config.EMAIL_TO:
        log.error("EMAIL_FROM and EMAIL_TO must be set.")
        return 1
    if not config.CHANNEL_IDS:
        log.error("CHANNEL_IDS is empty. Add at least one channel ID in config.py.")
        return 1

    processed = load_processed_video_ids(config.PROCESSED_PATH)
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    any_work = False
    had_errors = False

    for channel_id in config.CHANNEL_IDS:
        log.info("Checking channel %s", channel_id)
        try:
            ref = fetch_newest_video_for_channel(channel_id)
        except Exception as e:
            log.warning("Channel fetch raised %s; skipping.", e)
            continue

        if ref is None:
            continue
        if ref.video_id in processed:
            log.info("Already processed newest video %s; skipping.", ref.video_id)
            continue

        any_work = True
        log.info("New video: %s — %s", ref.title, ref.video_id)

        items = fetch_transcript_items(
            ref.video_id,
            retry_delay=config.TRANSCRIPT_RETRY_DELAY_SECONDS,
        )
        if not items:
            log.warning("No transcript for %s; marking processed to avoid infinite retries.", ref.video_id)
            processed.add(ref.video_id)
            save_processed_video_ids(config.PROCESSED_PATH, processed)
            continue

        chunks = chunk_transcript_with_timestamps(
            items,
            chunk_size_words=config.CHUNK_SIZE,
        )
        if not chunks:
            log.warning("Chunking produced no output for %s", ref.video_id)
            processed.add(ref.video_id)
            save_processed_video_ids(config.PROCESSED_PATH, processed)
            continue

        log.info("Summarizing %s chunks (parallel up to %s workers)", len(chunks), config.MAX_CHUNK_WORKERS)
        try:
            chunk_sums = summarize_chunks_parallel(
                client,
                config.OPENAI_MODEL,
                chunks,
                max_workers=config.MAX_CHUNK_WORKERS,
            )
            final_summary = consolidate_summaries(
                client,
                config.OPENAI_MODEL,
                ref.title,
                chunk_sums,
            )
        except Exception as e:
            log.exception("OpenAI summarization failed for %s: %s", ref.video_id, e)
            had_errors = True
            continue

        video_url = f"https://www.youtube.com/watch?v={ref.video_id}"
        html = build_summary_email_html(ref.title, video_url, final_summary)
        subject = f"[yt_summarizer] {ref.title}"

        try:
            send_html_email(
                smtp_host=config.EMAIL_SMTP_HOST,
                smtp_port=config.EMAIL_SMTP_PORT,
                use_tls=config.EMAIL_USE_TLS,
                from_addr=config.EMAIL_FROM,
                to_addr=config.EMAIL_TO,
                password=config.EMAIL_PASSWORD,
                subject=subject,
                html_body=html,
            )
        except Exception as e:
            log.exception("Email send failed for %s: %s", ref.video_id, e)
            had_errors = True
            continue

        processed.add(ref.video_id)
        save_processed_video_ids(config.PROCESSED_PATH, processed)
        log.info("Done: emailed summary for %s", ref.video_id)

    if not any_work:
        log.info("No new videos to process.")
    return 1 if had_errors else 0


if __name__ == "__main__":
    raise SystemExit(run_cycle())
