"""
JSON persistence for GUI settings (channels, LLM, email). No Qt dependency.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field

logger = logging.getLogger(__name__)

_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_CONFIG_DIR)
DEFAULT_SETTINGS_PATH = os.path.join(PROJECT_ROOT, "data", "gui_settings.json")


@dataclass
class GuiSettings:
    """User-editable settings shared by the GUI and optional CLI merge."""

    channels: list[str] = field(default_factory=list)
    use_openai_cloud: bool = False
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_model: str = "llama3.2"
    openai_api_key: str = ""
    dry_run: bool = True
    email_smtp_host: str = "smtp.gmail.com"
    email_smtp_port: int = 587
    email_use_tls: bool = True
    email_from: str = ""
    email_to: str = ""
    email_password: str = ""
    chunk_size: int = 3000
    max_chunk_workers: int = 2
    rss_videos_per_channel: int = 20


def default_gui_settings() -> GuiSettings:
    return GuiSettings(
        channels=["UCk-DG0N8StZ0T9Dv8XpVLZw"],
    )


def gui_settings_path() -> str:
    return os.environ.get("YT_GUI_SETTINGS", DEFAULT_SETTINGS_PATH)


def ensure_data_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)


def load_gui_settings() -> GuiSettings:
    path = gui_settings_path()
    if not os.path.isfile(path):
        s = default_gui_settings()
        try:
            save_gui_settings(s)
        except OSError as e:
            logger.warning("Could not write default settings %s: %s", path, e)
        return s
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Invalid settings file %s: %s; using defaults", path, e)
        return default_gui_settings()

    base = default_gui_settings()
    data = asdict(base)
    for k, v in raw.items():
        if k in data:
            data[k] = v
    return GuiSettings(**data)


def save_gui_settings(settings: GuiSettings) -> None:
    path = gui_settings_path()
    ensure_data_dir(path)
    tmp = f"{path}.tmp"
    payload = asdict(settings)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def channel_list_for_config_merge() -> list[str] | None:
    """Return channels from gui_settings.json if that file exists (may be empty)."""
    path = gui_settings_path()
    if not os.path.isfile(path):
        return None
    try:
        s = load_gui_settings()
    except Exception:
        return None
    return s.channels
