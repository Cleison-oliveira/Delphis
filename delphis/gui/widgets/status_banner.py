"""
Dependency & Environment Status Banner Widget.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QFrame, QToolTip
)
from delphis.core.env_check import check_dependencies

class StatusBanner(QFrame):
    """
    Status bar component displaying detection badges for backend tools,
    styled dynamically according to KDE Plasma's active color scheme.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border-radius: 4px; padding: 2px;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(10)

        title = QLabel("Tool Status:", self)
        title.setStyleSheet("font-size: 11px; font-weight: bold; opacity: 0.8;")
        layout.addWidget(title)

        self.badge_labels = {}
        self.refresh_status()

    def refresh_status(self):
        deps = check_dependencies()
        layout = self.layout()

        # Clear previous badge widgets except title
        while layout.count() > 1:
            item = layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        for key, info in deps.items():
            installed = info["installed"]
            name = key.upper()
            color = "#2ecc71" if installed else ("#e74c3c" if not info["optional"] else "#f39c12")
            icon = "●"

            badge = QLabel(f"{icon} {name}", self)
            badge.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")
            status_desc = f"{info['name']}: {'INSTALLED' if installed else 'NOT FOUND'}\nPath: {info['path'] or 'N/A'}\nRequired for: {info['required_for']}"
            badge.setToolTip(status_desc)

            layout.addWidget(badge)

        layout.addStretch()
