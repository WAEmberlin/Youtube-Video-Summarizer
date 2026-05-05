"""Main application window: videos, channels, settings."""

from __future__ import annotations

import logging

from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from yt_summarizer.channel_monitor import VideoRef
from yt_summarizer.summarize import FinalSummary
from yt_summarizer.ollama_check import ollama_origin_from_openai_base, verify_ollama_compatible_base
from yt_summarizer.settings_store import GuiSettings, load_gui_settings, save_gui_settings
from yt_summarizer.ui.channel_parse import parse_channel_id
from yt_summarizer.ui.workers import FetchVideosWorker, SummarizeWorker, TestSummaryWorker
from yt_summarizer.video_pipeline import pipeline_from_gui_settings

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main window with Videos / Channels / Settings tabs."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("YouTube Summarizer")
        self.resize(1040, 700)
        self._settings = load_gui_settings()
        self._video_rows: list[VideoRef] = []
        self._fetch_worker: FetchVideosWorker | None = None
        self._sum_worker: SummarizeWorker | None = None
        self._test_worker: TestSummaryWorker | None = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(14)
        root.setContentsMargins(20, 20, 20, 20)

        title = QLabel("YouTube Summarizer")
        title.setObjectName("titleLabel")
        subtitle = QLabel(
            "Pick videos to summarize, manage channels, and tune Ollama or email in Settings."
        )
        subtitle.setObjectName("subtitleLabel")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_videos_tab(), "Videos")
        self._tabs.addTab(self._build_channels_tab(), "Channels")
        self._tabs.addTab(self._build_settings_tab(), "Settings")
        root.addWidget(self._tabs)

        self._apply_settings_to_forms()

    def _build_videos_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        hint = QLabel(
            "Refresh loads the latest uploads from your saved channels. "
            "Check one video and click “Test summary” to preview in a window (no email), "
            "or check videos and use “Summarize & email selected.”"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555;")
        layout.addWidget(hint)

        bar = QHBoxLayout()
        self._btn_refresh = QPushButton("Refresh video list")
        self._btn_refresh.clicked.connect(self._on_refresh_videos)
        self._btn_select_all = QPushButton("Select all")
        self._btn_select_all.setObjectName("secondaryButton")
        self._btn_select_all.clicked.connect(lambda: self._set_all_checks(True))
        self._btn_select_none = QPushButton("Clear selection")
        self._btn_select_none.setObjectName("secondaryButton")
        self._btn_select_none.clicked.connect(lambda: self._set_all_checks(False))
        self._btn_test_summary = QPushButton("Test summary")
        self._btn_test_summary.setObjectName("secondaryButton")
        self._btn_test_summary.setToolTip(
            "Requires a checked video. Shows TL;DR and insights in a dialog (does not send email)."
        )
        self._btn_test_summary.clicked.connect(self._on_test_summary)
        self._btn_run = QPushButton("Summarize & email selected")
        self._btn_run.clicked.connect(self._on_summarize_selected)
        bar.addWidget(self._btn_refresh)
        bar.addWidget(self._btn_select_all)
        bar.addWidget(self._btn_select_none)
        bar.addWidget(self._btn_test_summary)
        bar.addStretch()
        bar.addWidget(self._btn_run)
        layout.addLayout(bar)

        self._video_table = QTableWidget(0, 5)
        self._video_table.setHorizontalHeaderLabels(
            ["Use", "Channel", "Title", "Video ID", "Published"]
        )
        self._video_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._video_table.setColumnWidth(0, 52)
        self._video_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._video_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._video_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._video_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._video_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._video_table.setAlternatingRowColors(True)
        self._video_table.verticalHeader().setVisible(False)
        layout.addWidget(self._video_table)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        self._log = QLabel("")
        self._log.setWordWrap(True)
        self._log.setStyleSheet("color: #444; font-size: 12px;")
        layout.addWidget(self._log)

        return w

    def _build_channels_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        layout.addWidget(
            QLabel("Channels are identified by a UC… ID (from the channel URL or RSS feed).")
        )

        row = QHBoxLayout()
        self._channel_input = QLineEdit()
        self._channel_input.setPlaceholderText(
            "Paste channel ID or URL (e.g. …?channel_id=UC… or /channel/UC…)"
        )
        btn_add = QPushButton("Add channel")
        btn_add.clicked.connect(self._on_add_channel)
        btn_rem = QPushButton("Remove selected")
        btn_rem.setObjectName("secondaryButton")
        btn_rem.clicked.connect(self._on_remove_channel)
        row.addWidget(self._channel_input)
        row.addWidget(btn_add)
        row.addWidget(btn_rem)
        layout.addLayout(row)

        self._channel_list = QListWidget()
        self._channel_list.setAlternatingRowColors(True)
        layout.addWidget(self._channel_list)

        btn_save = QPushButton("Save channels")
        btn_save.clicked.connect(self._save_channels_only)
        layout.addWidget(btn_save)

        return w

    def _build_settings_tab(self) -> QWidget:
        w = QWidget()
        outer = QVBoxLayout(w)

        llm_group = QGroupBox("Language model")
        llm_form = QFormLayout(llm_group)

        mode_row = QHBoxLayout()
        self._radio_ollama = QRadioButton("Ollama (local)")
        self._radio_openai = QRadioButton("OpenAI API (cloud)")
        self._radio_ollama.setChecked(True)
        self._radio_ollama.toggled.connect(self._on_llm_mode_toggle)
        self._radio_openai.toggled.connect(self._on_llm_mode_toggle)
        mode_row.addWidget(self._radio_ollama)
        mode_row.addWidget(self._radio_openai)
        mode_row.addStretch()
        llm_form.addRow("Provider:", mode_row)

        self._ollama_url = QLineEdit()
        self._ollama_url.setPlaceholderText("http://127.0.0.1:11434/v1")
        llm_form.addRow("Ollama base URL:", self._ollama_url)

        self._model_edit = QLineEdit()
        self._model_edit.setPlaceholderText("e.g. llama3.2, mistral, gpt-4o-mini")
        llm_form.addRow("Model name:", self._model_edit)

        self._api_key_edit = QLineEdit()
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_edit.setPlaceholderText("Required only for OpenAI cloud")
        llm_form.addRow("OpenAI API key:", self._api_key_edit)

        btn_test = QPushButton("Test Ollama connection")
        btn_test.setObjectName("secondaryButton")
        btn_test.clicked.connect(self._on_test_ollama)
        llm_form.addRow("", btn_test)

        outer.addWidget(llm_group)

        mail_group = QGroupBox("Email delivery")
        mail_form = QFormLayout(mail_group)

        self._dry_run_check = QCheckBox("Dry-run (log only, do not send email)")
        mail_form.addRow(self._dry_run_check)

        self._smtp_host = QLineEdit()
        self._smtp_port = QSpinBox()
        self._smtp_port.setRange(1, 65535)
        self._smtp_port.setValue(587)
        self._smtp_tls = QCheckBox("Use TLS (STARTTLS)")
        self._smtp_tls.setChecked(True)
        mail_form.addRow("SMTP host:", self._smtp_host)
        mail_form.addRow("SMTP port:", self._smtp_port)
        mail_form.addRow("", self._smtp_tls)

        self._email_from = QLineEdit()
        self._email_to = QLineEdit()
        self._email_pass = QLineEdit()
        self._email_pass.setEchoMode(QLineEdit.EchoMode.Password)
        mail_form.addRow("From:", self._email_from)
        mail_form.addRow("To:", self._email_to)
        mail_form.addRow("SMTP password / app password:", self._email_pass)

        outer.addWidget(mail_group)

        email_help = QGroupBox("How to set up email")
        email_help_layout = QVBoxLayout(email_help)
        help_browser = QTextBrowser()
        help_browser.setReadOnly(True)
        help_browser.setOpenExternalLinks(True)
        help_browser.setMinimumHeight(220)
        help_browser.setHtml(
            "<h3>Gmail (typical setup)</h3>"
            "<ol style='margin-top:8px;'>"
            "<li>Enable <b>2-Step Verification</b> on your Google Account.</li>"
            "<li>Open <a href='https://myaccount.google.com/apppasswords'>App passwords</a> "
            "(Google Account → Security).</li>"
            "<li>Create an app password for <b>Mail</b> — Google shows a "
            "<b>16-character password</b>; copy it.</li>"
            "<li>Here, set <b>SMTP host</b> to <code>smtp.gmail.com</code>, "
            "<b>port</b> <code>587</code>, and keep <b>Use TLS</b> checked.</li>"
            "<li><b>From</b>: your full Gmail address. "
            "<b>To</b>: where summaries should go (can be the same inbox).</li>"
            "<li><b>SMTP password</b>: paste the <b>app password</b>, "
            "not your normal Gmail password.</li>"
            "<li>Leave <b>Dry-run</b> on while testing summaries without sending mail; "
            "turn it off when you want real emails.</li>"
            "</ol>"
            "<p><b>Other providers:</b> use their SMTP documentation "
            "(often port 587 + STARTTLS). Outlook often uses "
            "<code>smtp-mail.outlook.com</code>.</p>"
        )
        email_help_layout.addWidget(help_browser)
        outer.addWidget(email_help)

        adv = QGroupBox("Advanced")
        adv_form = QFormLayout(adv)
        self._chunk_size = QSpinBox()
        self._chunk_size.setRange(500, 20000)
        self._chunk_size.setSingleStep(500)
        self._chunk_size.setValue(3000)
        self._rss_limit = QSpinBox()
        self._rss_limit.setRange(5, 50)
        self._rss_limit.setValue(20)
        self._workers = QSpinBox()
        self._workers.setRange(1, 8)
        self._workers.setValue(2)
        adv_form.addRow("Words per chunk:", self._chunk_size)
        adv_form.addRow("Videos per channel (RSS):", self._rss_limit)
        adv_form.addRow("Parallel chunk workers:", self._workers)
        outer.addWidget(adv)

        save_row = QHBoxLayout()
        btn_save = QPushButton("Save settings")
        btn_save.clicked.connect(self._on_save_settings)
        save_row.addStretch()
        save_row.addWidget(btn_save)
        outer.addLayout(save_row)
        outer.addStretch()

        return w

    def _on_llm_mode_toggle(self) -> None:
        use_cloud = self._radio_openai.isChecked()
        self._ollama_url.setEnabled(not use_cloud)
        self._api_key_edit.setEnabled(use_cloud)

    def _apply_settings_to_forms(self) -> None:
        s = self._settings
        self._channel_list.clear()
        for c in s.channels:
            self._channel_list.addItem(c)

        self._radio_openai.setChecked(s.use_openai_cloud)
        self._radio_ollama.setChecked(not s.use_openai_cloud)
        self._ollama_url.setText(s.llm_base_url)
        self._model_edit.setText(s.llm_model)
        self._api_key_edit.setText(s.openai_api_key)
        self._dry_run_check.setChecked(s.dry_run)
        self._smtp_host.setText(s.email_smtp_host)
        self._smtp_port.setValue(s.email_smtp_port)
        self._smtp_tls.setChecked(s.email_use_tls)
        self._email_from.setText(s.email_from)
        self._email_to.setText(s.email_to)
        self._email_pass.setText(s.email_password)
        self._chunk_size.setValue(s.chunk_size)
        self._rss_limit.setValue(s.rss_videos_per_channel)
        self._workers.setValue(s.max_chunk_workers)
        self._on_llm_mode_toggle()

    def _read_settings_from_forms(self) -> GuiSettings:
        return GuiSettings(
            channels=[self._channel_list.item(i).text() for i in range(self._channel_list.count())],
            use_openai_cloud=self._radio_openai.isChecked(),
            llm_base_url=self._ollama_url.text().strip(),
            llm_model=self._model_edit.text().strip() or "llama3.2",
            openai_api_key=self._api_key_edit.text(),
            dry_run=self._dry_run_check.isChecked(),
            email_smtp_host=self._smtp_host.text().strip() or "smtp.gmail.com",
            email_smtp_port=int(self._smtp_port.value()),
            email_use_tls=self._smtp_tls.isChecked(),
            email_from=self._email_from.text().strip(),
            email_to=self._email_to.text().strip(),
            email_password=self._email_pass.text(),
            chunk_size=int(self._chunk_size.value()),
            max_chunk_workers=int(self._workers.value()),
            rss_videos_per_channel=int(self._rss_limit.value()),
        )

    def _on_save_settings(self) -> None:
        self._settings = self._read_settings_from_forms()
        if not self._settings.use_openai_cloud and not self._settings.llm_base_url:
            QMessageBox.warning(self, "Settings", "Enter the Ollama base URL or switch to OpenAI cloud.")
            return
        if self._settings.use_openai_cloud and not self._settings.openai_api_key.strip():
            QMessageBox.warning(self, "Settings", "Enter your OpenAI API key for cloud mode.")
            return
        if not self._settings.dry_run:
            if not self._settings.email_from or not self._settings.email_to:
                QMessageBox.warning(
                    self,
                    "Settings",
                    "Fill in From / To, enable Dry-run, or email cannot be sent.",
                )
                return
        try:
            save_gui_settings(self._settings)
        except OSError as e:
            QMessageBox.critical(self, "Settings", f"Could not save: {e}")
            return
        QMessageBox.information(self, "Settings", "Saved to data/gui_settings.json")

    def _save_channels_only(self) -> None:
        self._settings = self._read_settings_from_forms()
        try:
            save_gui_settings(self._settings)
        except OSError as e:
            QMessageBox.critical(self, "Channels", f"Could not save: {e}")
            return
        QMessageBox.information(self, "Channels", "Channels saved.")

    def _on_add_channel(self) -> None:
        raw = self._channel_input.text()
        cid = parse_channel_id(raw)
        if not cid:
            QMessageBox.warning(
                self,
                "Channels",
                "Could not find a channel ID. Paste a UC… ID or a URL containing channel_id=…",
            )
            return
        for i in range(self._channel_list.count()):
            if self._channel_list.item(i).text() == cid:
                QMessageBox.information(self, "Channels", "That channel is already in the list.")
                return
        self._channel_list.addItem(cid)
        self._channel_input.clear()

    def _on_remove_channel(self) -> None:
        for item in self._channel_list.selectedItems():
            self._channel_list.takeItem(self._channel_list.row(item))

    def _set_busy(self, busy: bool) -> None:
        self._btn_refresh.setEnabled(not busy)
        self._btn_run.setEnabled(not busy)
        self._btn_test_summary.setEnabled(not busy)
        self._progress.setVisible(busy)

    @staticmethod
    def _format_summary_dialog_text(title: str, video_id: str, summary: FinalSummary) -> str:
        """Plain-text body for the test-summary dialog."""
        url = f"https://www.youtube.com/watch?v={video_id}"
        lines = [
            title,
            url,
            "",
            "── TL;DR ──",
            *[f"• {b}" for b in summary.tldr_bullets],
            "",
            "── Key insights ──",
            *[f"• {x}" for x in summary.all_key_insights],
            "",
            "── Main takeaways ──",
            *[f"• {x}" for x in summary.main_takeaways],
            "",
            "── Timeline ──",
            *[f"• {x}" for x in summary.timeline],
        ]
        return "\n".join(lines)

    def _show_summary_dialog(self, heading: str, body: str) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Test summary")
        dlg.setMinimumSize(580, 520)
        lay = QVBoxLayout(dlg)
        head = QLabel(heading)
        head.setWordWrap(True)
        head.setStyleSheet("font-weight: bold; font-size: 14px; color: #c41230;")
        lay.addWidget(head)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(body)
        text.setStyleSheet("font-family: Consolas, 'Cascadia Mono', monospace; font-size: 12px;")
        lay.addWidget(text)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dlg.accept)
        lay.addWidget(buttons)
        dlg.exec()

    def _first_checked_video(self) -> tuple[str, str] | None:
        """Return (video_id, title) for the first row with the Use checkbox checked."""
        for row in range(self._video_table.rowCount()):
            w = self._video_table.cellWidget(row, 0)
            if isinstance(w, QCheckBox) and w.isChecked():
                vid_item = self._video_table.item(row, 3)
                title_item = self._video_table.item(row, 2)
                if vid_item and title_item:
                    return (vid_item.text(), title_item.text())
        return None

    def _on_test_summary(self) -> None:
        """Summarize first checked video and show results (no email)."""
        first = self._first_checked_video()
        if not first:
            QMessageBox.information(
                self,
                "Test summary",
                "Check the box next to a video in the table, then click Test summary again.",
            )
            return

        video_id, title = first
        self._settings = self._read_settings_from_forms()

        if self._settings.use_openai_cloud:
            if not self._settings.openai_api_key.strip():
                QMessageBox.warning(self, "Test summary", "Enter an OpenAI API key for cloud mode.")
                return
        else:
            if not self._settings.llm_base_url.strip():
                QMessageBox.warning(self, "Test summary", "Enter the Ollama base URL in Settings.")
                return
            if "11434" in self._settings.llm_base_url:
                origin = ollama_origin_from_openai_base(self._settings.llm_base_url)
                if origin:
                    err = verify_ollama_compatible_base(origin)
                    if err:
                        QMessageBox.critical(self, "Ollama", err)
                        return

        try:
            save_gui_settings(self._settings)
        except OSError:
            pass

        pipeline = pipeline_from_gui_settings(self._settings)
        self._set_busy(True)
        self._progress.setRange(0, 0)
        self._progress.setVisible(True)
        self._log.setText("Generating test summary (may take a minute)…")

        self._test_worker = TestSummaryWorker(pipeline, video_id, title)
        self._test_worker.succeeded.connect(self._on_test_summary_succeeded)
        self._test_worker.failed.connect(self._on_test_summary_failed)
        self._test_worker.finished.connect(self._on_test_summary_finished)
        self._test_worker.start()

    def _on_test_summary_succeeded(self, summary: object, title: str, video_id: str) -> None:
        if not isinstance(summary, FinalSummary):
            return
        body = self._format_summary_dialog_text(title, video_id, summary)
        short = title if len(title) < 80 else title[:77] + "…"
        self._show_summary_dialog(short, body)

    def _on_test_summary_failed(self, msg: str) -> None:
        QMessageBox.critical(self, "Test summary", msg)

    def _on_test_summary_finished(self) -> None:
        self._set_busy(False)
        self._progress.setVisible(False)
        self._log.setText("")

    def _on_refresh_videos(self) -> None:
        self._settings = self._read_settings_from_forms()
        ch = [self._channel_list.item(i).text() for i in range(self._channel_list.count())]
        if not ch:
            QMessageBox.warning(self, "Videos", "Add at least one channel on the Channels tab.")
            return
        try:
            save_gui_settings(self._settings)
        except OSError:
            pass

        self._set_busy(True)
        self._log.setText("Loading RSS feeds…")
        self._fetch_worker = FetchVideosWorker(ch, self._settings.rss_videos_per_channel)
        self._fetch_worker.loaded.connect(self._on_videos_loaded)
        self._fetch_worker.failed.connect(self._on_videos_failed)
        self._fetch_worker.finished.connect(lambda: self._set_busy(False))
        self._fetch_worker.start()

    def _on_videos_loaded(self, videos: list) -> None:
        refs = list(videos)
        self._video_rows = refs
        self._video_table.setRowCount(0)
        for row, v in enumerate(refs):
            self._video_table.insertRow(row)
            cb = QCheckBox()
            cb.setChecked(False)
            self._video_table.setCellWidget(row, 0, cb)
            self._video_table.setItem(row, 1, QTableWidgetItem(v.channel_id))
            self._video_table.setItem(row, 2, QTableWidgetItem(v.title))
            self._video_table.setItem(row, 3, QTableWidgetItem(v.video_id))
            self._video_table.setItem(row, 4, QTableWidgetItem(v.published or ""))
        self._log.setText(f"Loaded {len(refs)} video(s) from RSS.")

    def _on_videos_failed(self, msg: str) -> None:
        self._log.setText("")
        QMessageBox.critical(self, "Videos", msg)

    def _set_all_checks(self, checked: bool) -> None:
        for row in range(self._video_table.rowCount()):
            w = self._video_table.cellWidget(row, 0)
            if isinstance(w, QCheckBox):
                w.setChecked(checked)

    def _on_summarize_selected(self) -> None:
        self._settings = self._read_settings_from_forms()
        selected: list[tuple[str, str]] = []
        for row in range(self._video_table.rowCount()):
            w = self._video_table.cellWidget(row, 0)
            if isinstance(w, QCheckBox) and w.isChecked():
                vid_item = self._video_table.item(row, 3)
                title_item = self._video_table.item(row, 2)
                if vid_item and title_item:
                    selected.append((vid_item.text(), title_item.text()))
        if not selected:
            QMessageBox.information(self, "Videos", "Check one or more videos first.")
            return

        if not self._settings.dry_run:
            if not self._settings.email_from or not self._settings.email_to:
                QMessageBox.warning(
                    self,
                    "Email",
                    "Configure From/To in Settings, or enable Dry-run.",
                )
                return

        if self._settings.use_openai_cloud:
            if not self._settings.openai_api_key.strip():
                QMessageBox.warning(self, "LLM", "Enter an OpenAI API key for cloud mode.")
                return
        else:
            if "11434" in self._settings.llm_base_url:
                origin = ollama_origin_from_openai_base(self._settings.llm_base_url)
                if origin:
                    err = verify_ollama_compatible_base(origin)
                    if err:
                        QMessageBox.critical(self, "Ollama", err)
                        return

        try:
            save_gui_settings(self._settings)
        except OSError:
            pass

        pipeline = pipeline_from_gui_settings(self._settings)
        self._set_busy(True)
        self._progress.setRange(0, len(selected))
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._log.setText("Summarizing…")

        self._sum_worker = SummarizeWorker(pipeline, selected)
        self._sum_worker.progress.connect(self._on_sum_progress)
        self._sum_worker.video_finished.connect(self._on_sum_video)
        self._sum_worker.all_finished.connect(self._on_sum_done)
        self._sum_worker.start()

    def _on_sum_progress(self, cur: int, total: int, title: str) -> None:
        self._progress.setMaximum(total)
        self._progress.setValue(cur)
        self._log.setText(f"({cur}/{total}) {title}")

    def _on_sum_video(self, video_id: str, ok: bool, msg: str) -> None:
        level = logging.INFO if ok else logging.WARNING
        logger.log(level, "%s — %s", video_id, msg)

    def _on_sum_done(self) -> None:
        self._set_busy(False)
        self._progress.setVisible(False)
        self._log.setText("Finished. Check your inbox (or logs if dry-run).")

    def _on_test_ollama(self) -> None:
        url = self._ollama_url.text().strip()
        if not url or "11434" not in url:
            QMessageBox.information(
                self,
                "Ollama",
                "Enter an Ollama-style base URL (usually http://127.0.0.1:11434/v1).",
            )
            return
        origin = ollama_origin_from_openai_base(url)
        if not origin:
            QMessageBox.warning(self, "Ollama", "Could not parse that URL.")
            return
        err = verify_ollama_compatible_base(origin)
        if err:
            QMessageBox.critical(self, "Ollama", err)
        else:
            QMessageBox.information(self, "Ollama", "Connected. Models: ensure `ollama pull <model>` has been run.")
