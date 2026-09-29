"""
Real-time Console Output Drawer Widget for Delphis.
"""

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QProgressBar, QPlainTextEdit, QFrame, QApplication
)
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QColor, QFontDatabase
from delphis_gui.style import get_breeze_icon

class ConsoleDrawer(QWidget):
    """
    Expandable bottom drawer showing live stdout execution logs,
    colored status tags, percentage progress bar, and copy/clear buttons.
    """
    toggleExpandRequested = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_expanded = True
        self.logs_enabled = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Header Control Bar
        header_bar = QFrame(self)
        header_bar.setFrameShape(QFrame.Shape.StyledPanel)
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(6, 2, 6, 2)
        header_layout.setSpacing(6)

        self.btn_toggle = QPushButton("Console Output", self)
        self.btn_toggle.setIcon(get_breeze_icon("utilities-terminal", "terminal"))
        self.btn_toggle.setFlat(True)
        self.btn_toggle.clicked.connect(self._toggle_expand)
        header_layout.addWidget(self.btn_toggle)

        self.lbl_status = QLabel("Ready", self)
        header_layout.addWidget(self.lbl_status, stretch=1)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedWidth(180)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        header_layout.addWidget(self.progress_bar)

        self.btn_copy = QPushButton("Copy", self)
        self.btn_copy.setIcon(get_breeze_icon("edit-copy"))
        self.btn_copy.clicked.connect(self._copy_log)
        header_layout.addWidget(self.btn_copy)

        self.btn_clear = QPushButton("Clear", self)
        self.btn_clear.setIcon(get_breeze_icon("edit-clear"))
        self.btn_clear.clicked.connect(self.clear)
        header_layout.addWidget(self.btn_clear)

        layout.addWidget(header_bar)

        # Terminal Log Area
        self.log_edit = QPlainTextEdit(self)
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumBlockCount(2000)
        self.log_edit.setFixedHeight(130)
        self.log_edit.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        layout.addWidget(self.log_edit)

    def _toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self.log_edit.setVisible(self.is_expanded)
        self.toggleExpandRequested.emit(self.is_expanded)

    def append_log(self, text: str, level: str = "info", force: bool = False):
        if not self.logs_enabled and not force and level not in ("error", "fatal"):
            return

        palette = self.palette()
        default_color = palette.color(palette.ColorRole.Text).name()

        colors = {
            "info": default_color,
            "success": "#2ecc71",
            "warning": "#f67400",
            "error": "#da4453"
        }
        color_hex = colors.get(level, default_color)

        cursor = self.log_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color_hex))
        cursor.insertText(f"{text}\n", fmt)

        self.log_edit.setTextCursor(cursor)
        self.log_edit.ensureCursorVisible()

    def set_status(self, text: str):
        self.lbl_status.setText(text)

    def set_progress(self, current: int, total: int):
        if total > 0:
            pct = int((current / total) * 100)
            self.progress_bar.setValue(pct)
            self.progress_bar.setVisible(True)
            self.set_status(f"Processing ({current}/{total} - {pct}%)")
        else:
            self.progress_bar.setVisible(False)

    def set_busy(self, is_busy: bool):
        if not is_busy:
            self.progress_bar.setVisible(False)

    def clear(self):
        self.log_edit.clear()
        self.set_status("Logs cleared")

    def _copy_log(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.log_edit.toPlainText())
        self.set_status("Log copied to clipboard")
