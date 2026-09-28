"""
XDG Desktop Portal-Compatible Path Selector Widget with Drag & Drop Support.
"""

import os
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QFileDialog, QSizePolicy
)
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from delphis.gui.style import get_breeze_icon

class PathPicker(QWidget):
    """
    Input widget supporting native KDE/XDG portal file and directory pickers,
    drag-and-drop auto-population, and quick clear action.
    """
    pathChanged = pyqtSignal(str)

    def __init__(
        self,
        mode: str = "both",  # "file", "directory", "both", "save_file", "save_dir"
        file_filter: str = "All Supported Images (*.png *.webp *.tga *.dds *.bmp *.jpg);;All Files (*)",
        placeholder: str = "Select or drag & drop file/folder...",
        parent=None
    ):
        super().__init__(parent)
        self.mode = mode
        self.file_filter = file_filter
        self.setAcceptDrops(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.line_edit = QLineEdit(self)
        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.setClearButtonEnabled(True)
        self.line_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.line_edit)

        if self.mode in ("file", "both"):
            self.btn_file = QPushButton("File...", self)
            self.btn_file.setIcon(get_breeze_icon("document-open"))
            self.btn_file.clicked.connect(self._choose_file)
            layout.addWidget(self.btn_file)

        if self.mode in ("directory", "both", "save_dir"):
            self.btn_dir = QPushButton("Folder...", self)
            self.btn_dir.setIcon(get_breeze_icon("folder-open"))
            self.btn_dir.clicked.connect(self._choose_directory)
            layout.addWidget(self.btn_dir)

    def _on_text_changed(self, text: str):
        self.pathChanged.emit(text.strip())

    def path(self) -> str:
        return self.line_edit.text().strip()

    def setPath(self, path_str: str):
        self.line_edit.setText(path_str.strip())

    def _choose_file(self):
        start_dir = self.path() if os.path.exists(self.path()) else os.path.expanduser("~")
        if os.path.isfile(start_dir):
            start_dir = os.path.dirname(start_dir)

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Input Image File",
            start_dir,
            self.file_filter,
            options=QFileDialog.Option(0)  # Native KDE / XDG portal dialog
        )
        if file_path:
            self.setPath(file_path)

    def _choose_directory(self):
        start_dir = self.path() if os.path.exists(self.path()) else os.path.expanduser("~")
        if os.path.isfile(start_dir):
            start_dir = os.path.dirname(start_dir)

        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            start_dir,
            options=QFileDialog.Option(0)  # Native KDE / XDG portal dialog
        )
        if dir_path:
            self.setPath(dir_path)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            local_path = urls[0].toLocalFile()
            if local_path:
                self.setPath(local_path)
                event.acceptProposedAction()
