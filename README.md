# YouTube Video Summarizer (yt_summarizer)

Monitors YouTube channels via RSS, pulls transcripts, summarizes with **Ollama** (default) or OpenAI, and optionally emails HTML digests.

## Desktop UI (recommended)

Double-click **`gui.bat`** or run:

```powershell
pip install -r requirements.txt
python gui.py
```

The app uses a **white and red** PySide6 interface with three tabs:

- **Videos** — Refresh loads recent uploads from your saved channels (RSS). Check the rows you want, then **Summarize & email selected**.
- **Channels** — Add or remove channel IDs (paste a `UC…` id or a URL containing `channel_id=`).
- **Settings** — Ollama base URL and **model name**, optional **OpenAI cloud** mode, **email / SMTP**, **dry-run**, and advanced chunk options.

Settings are saved to **`data/gui_settings.json`** (gitignored). The scheduled CLI (`main.py`) will use the same channel list from that file when present (unless `CHANNEL_IDS` is set in the environment).

## Command-line / scheduler

- **`run.bat` / `run.ps1` / `python main.py`** — unattended cycle: newest unprocessed video per channel (see `.env` / `config.py`).

## Adding channels (without the GUI)

Each channel is a **channel ID** (`UC…`, 24 characters). Find it in the channel URL (`youtube.com/channel/UC…`) or in any RSS link:  
`https://www.youtube.com/feeds/videos.xml?channel_id=PUT_ID_HERE`

1. Use the **Channels** tab in the GUI, or  
2. Edit **`yt_summarizer/config.py`** → `CHANNEL_IDS`, or  
3. Set **`CHANNEL_IDS`** in **`.env`** (comma-separated).

## Easiest run (Windows, Ollama)

1. **Start Ollama** (system tray).
2. **`gui.bat`** for the desktop app, or **`run.bat`** for the automatic CLI.
3. For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833) as the SMTP password. Turn off **Dry-run** in Settings when email is ready.

## OpenAI cloud (instead of Ollama)

In the GUI: choose **OpenAI API (cloud)**, enter the API key and model (e.g. `gpt-4o-mini`).  
Or in `.env`: `OPENAI_BASE_URL=`, `OPENAI_API_KEY=sk-...`, `OPENAI_MODEL=gpt-4o-mini`.

## Re-process a video

Remove its ID from `data/processed.json` (CLI path) or select it again in the GUI (GUI path does not use `processed.json` for your manual selections).
