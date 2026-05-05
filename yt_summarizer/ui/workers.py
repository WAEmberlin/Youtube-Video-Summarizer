"""Background threads for RSS fetch and summarization jobs."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from yt_summarizer.channel_monitor import VideoRef, fetch_recent_videos_for_channel
from yt_summarizer.video_pipeline import PipelineConfig, summarize_and_deliver_video


class FetchVideosWorker(QThread):
    """Load recent videos from RSS for all configured channels."""

    loaded = Signal(list)  # list[VideoRef]
    failed = Signal(str)

    def __init__(self, channels: list[str], per_channel: int, parent=None) -> None:
        super().__init__(parent)
        self._channels = list(channels)
        self._per = per_channel

    def run(self) -> None:  # noqa: D102
        try:
            out: list[VideoRef] = []
            for cid in self._channels:
                if not cid.strip():
                    continue
                out.extend(fetch_recent_videos_for_channel(cid.strip(), limit=self._per))
            self.loaded.emit(out)
        except Exception as e:
            self.failed.emit(str(e))


class SummarizeWorker(QThread):
    """Summarize and email (or dry-run) each selected video sequentially."""

    progress = Signal(int, int, str)  # index 1-based, total, current title
    video_finished = Signal(str, bool, str)  # video_id, ok, message
    all_finished = Signal()

    def __init__(
        self,
        pipeline: PipelineConfig,
        videos: list[tuple[str, str]],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._pipeline = pipeline
        self._videos = list(videos)

    def run(self) -> None:  # noqa: D102
        total = len(self._videos)
        for i, (vid, title) in enumerate(self._videos):
            self.progress.emit(i + 1, total, title)
            ok, msg = summarize_and_deliver_video(self._pipeline, vid, title)
            self.video_finished.emit(vid, ok, msg)
        self.all_finished.emit()
