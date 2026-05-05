"""Application-wide Qt stylesheet (white + red theme)."""

APP_STYLESHEET = """
QWidget {
    background-color: #ffffff;
    color: #1a1a1a;
    font-family: "Segoe UI", "SF Pro Text", Roboto, system-ui, sans-serif;
    font-size: 13px;
}

QMainWindow, QDialog {
    background-color: #fafafa;
}

QLabel#titleLabel {
    font-size: 22px;
    font-weight: 700;
    color: #c41230;
    padding-bottom: 4px;
}

QLabel#subtitleLabel {
    font-size: 12px;
    color: #555555;
}

QTabWidget::pane {
    border: 1px solid #e5e5e5;
    border-radius: 8px;
    top: -1px;
    padding: 12px;
    background: #ffffff;
}

QTabBar::tab {
    background: #f3f3f3;
    color: #333333;
    padding: 10px 22px;
    margin-right: 3px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    min-width: 88px;
}

QTabBar::tab:selected {
    background: #c41230;
    color: #ffffff;
    font-weight: 600;
}

QTabBar::tab:hover:!selected {
    background: #ffe8e8;
    color: #8f0d24;
}

QPushButton {
    background-color: #c41230;
    color: #ffffff;
    border: none;
    padding: 9px 18px;
    border-radius: 6px;
    font-weight: 600;
    min-height: 22px;
}

QPushButton:hover {
    background-color: #a30f28;
}

QPushButton:pressed {
    background-color: #860c21;
}

QPushButton#secondaryButton {
    background-color: #ffffff;
    color: #c41230;
    border: 2px solid #c41230;
}

QPushButton#secondaryButton:hover {
    background-color: #fff5f5;
}

QLineEdit, QSpinBox, QTextEdit {
    background: #ffffff;
    border: 1px solid #d9d9d9;
    border-radius: 6px;
    padding: 8px 10px;
    selection-background-color: #c41230;
    selection-color: #ffffff;
}

QLineEdit:focus, QSpinBox:focus, QTextEdit:focus {
    border: 1px solid #c41230;
}

QListWidget {
    border: 1px solid #e5e5e5;
    border-radius: 8px;
    padding: 6px;
    background: #ffffff;
    alternate-background-color: #fafafa;
}

QListWidget::item:selected {
    background: #c41230;
    color: #ffffff;
}

QListWidget::item:hover:!selected {
    background: #fff0f0;
}

QTableWidget {
    border: 1px solid #e5e5e5;
    border-radius: 8px;
    gridline-color: #eeeeee;
    background: #ffffff;
    alternate-background-color: #fcfcfc;
}

QHeaderView::section {
    background: #fff0f0;
    color: #a30f28;
    padding: 10px;
    font-weight: 700;
    border: none;
    border-bottom: 2px solid #c41230;
}

QProgressBar {
    border: 1px solid #e5e5e5;
    border-radius: 6px;
    text-align: center;
    height: 22px;
    background: #f5f5f5;
}

QProgressBar::chunk {
    background: #c41230;
    border-radius: 5px;
}

QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #c41230;
    background: #ffffff;
}

QCheckBox::indicator:checked {
    background: #c41230;
}

QFrame#cardFrame {
    background: #ffffff;
    border: 1px solid #eeeeee;
    border-radius: 10px;
    padding: 14px;
}

QGroupBox {
    font-weight: 600;
    border: 1px solid #e8e8e8;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #c41230;
}
"""
