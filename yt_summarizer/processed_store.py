"""
Persist processed video IDs to avoid duplicate work.
"""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)


def ensure_parent_dir(path: str) -> None:
    """Create parent directory for a file path if needed."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)


def load_processed_video_ids(path: str) -> set[str]:
    """
    Load the set of already-processed video IDs from JSON storage.

    Args:
        path: Path to ``processed.json``.

    Returns:
        Set of video IDs (empty if file is missing or invalid).
    """
    if not os.path.isfile(path):
        return set()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        ids = data.get("video_ids", [])
        if isinstance(ids, list):
            return {str(x) for x in ids}
    except (json.JSONDecodeError, OSError, TypeError) as e:
        logger.warning("Could not load processed store %s: %s", path, e)
    return set()


def save_processed_video_ids(path: str, video_ids: set[str]) -> None:
    """
    Atomically write the full set of processed video IDs.

    Args:
        path: Path to ``processed.json``.
        video_ids: Complete set to persist.
    """
    ensure_parent_dir(path)
    payload = {"video_ids": sorted(video_ids)}
    tmp_path = f"{path}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, path)
    except OSError as e:
        logger.error("Failed to save processed store %s: %s", path, e)
        raise
