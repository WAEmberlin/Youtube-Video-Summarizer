"""Qt application entry."""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from yt_summarizer.ui.main_window import MainWindow
from yt_summarizer.ui.styles import APP_STYLESHEET


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app = QApplication(sys.argv)
    app.setApplicationName("YouTube Summarizer")
    app.setStyleSheet(APP_STYLESHEET)
    win = MainWindow()
    win.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
