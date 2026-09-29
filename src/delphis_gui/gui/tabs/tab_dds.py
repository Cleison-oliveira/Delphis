"""
Tab 4: DDS Texture Optimizer for Dolphin
"""

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QComboBox,
    QCheckBox, QLabel, QFormLayout, QScrollArea, QMessageBox, QFrame
)
from delphis_gui.gui.widgets.path_picker import PathPicker
from delphis_gui.constants import DDS_PRESETS

class DDSTab(QWidget):
    """
    Interface for converting textures to optimized .dds format for Dolphin emulator.
    Provides hardware-accelerated block compression (BC7, BC1, BC3, BC5) and automatic Mipmaps.
    """
    requestWorker = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        # 1. Path Selection Card
        paths_group = QGroupBox("Paths & Textures", self)
        paths_layout = QFormLayout(paths_group)
        paths_layout.setSpacing(10)

        self.input_picker = PathPicker(
            mode="both",
            placeholder="Select PNG/TGA/WebP texture file or folder...",
            parent=self
        )
        paths_layout.addRow("Input Image/Folder:", self.input_picker)

        self.output_picker = PathPicker(
            mode="directory",
            placeholder="Select destination folder for optimized .dds textures...",
            parent=self
        )
        paths_layout.addRow("Output Folder:", self.output_picker)
        layout.addWidget(paths_group)

        # 2. Preset Selection Card
        preset_group = QGroupBox("Dolphin Performance Preset", self)
        preset_layout = QVBoxLayout(preset_group)
        preset_layout.setSpacing(8)

        self.combo_preset = QComboBox(self)
        for key, p_data in DDS_PRESETS.items():
            self.combo_preset.addItem(p_data["name"], key)
            if p_data.get("is_default"):
                self.combo_preset.setCurrentIndex(self.combo_preset.count() - 1)

        preset_layout.addWidget(self.combo_preset)

        self.lbl_desc = QLabel(self)
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setFrameShape(QFrame.Shape.StyledPanel)
        self.lbl_desc.setContentsMargins(8, 6, 8, 6)
        preset_layout.addWidget(self.lbl_desc)

        self.combo_preset.currentIndexChanged.connect(self._update_preset_desc)
        self._update_preset_desc()

        layout.addWidget(preset_group)

        # 3. Extra Optimization Settings Card
        options_group = QGroupBox("Optimization Settings", self)
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(10)

        self.chk_mipmaps = QCheckBox("Generate Mipmaps (Essential: Eliminates distant texture shimmering in Dolphin)", self)
        self.chk_mipmaps.setChecked(True)
        options_layout.addWidget(self.chk_mipmaps)

        self.chk_recursive = QCheckBox("Process Subdirectories Recursively", self)
        self.chk_recursive.setChecked(True)
        options_layout.addWidget(self.chk_recursive)

        layout.addWidget(options_group)

        layout.addStretch()
        scroll.setWidget(container)

        main_vbox = QVBoxLayout(self)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.addWidget(scroll)

    def _update_preset_desc(self):
        preset_key = self.combo_preset.currentData()
        preset_data = DDS_PRESETS.get(preset_key, {})
        desc = preset_data.get("description", "")
        self.lbl_desc.setText(desc)

    def execute_action(self):
        """Execute DDS conversion task from top action bar."""
        in_path = self.input_picker.path()
        out_path = self.output_picker.path()

        if not in_path or not out_path:
            QMessageBox.warning(self, "Missing Paths", "Please specify both Input Path and Output Folder.")
            return

        preset_val = self.combo_preset.currentData()

        cmd = [
            "dds", in_path, out_path,
            "--preset", str(preset_val)
        ]

        if not self.chk_mipmaps.isChecked():
            cmd.append("--no-mips")

        self.requestWorker.emit(cmd)

    def save_settings(self, settings):
        """Persist DDS tab UI state."""
        settings.beginGroup("dds")
        settings.setValue("input_path", self.input_picker.path())
        settings.setValue("output_path", self.output_picker.path())
        settings.setValue("preset_index", self.combo_preset.currentIndex())
        settings.setValue("mipmaps", self.chk_mipmaps.isChecked())
        settings.setValue("recursive", self.chk_recursive.isChecked())
        settings.endGroup()

    def load_settings(self, settings):
        """Restore DDS tab UI state from QSettings."""
        settings.beginGroup("dds")
        in_path = settings.value("input_path", "")
        if in_path:
            self.input_picker.setPath(in_path)
        out_path = settings.value("output_path", "")
        if out_path:
            self.output_picker.setPath(out_path)

        preset_idx = settings.value("preset_index", -1, type=int)
        if 0 <= preset_idx < self.combo_preset.count():
            self.combo_preset.setCurrentIndex(preset_idx)

        self.chk_mipmaps.setChecked(settings.value("mipmaps", True, type=bool))
        self.chk_recursive.setChecked(settings.value("recursive", True, type=bool))
        settings.endGroup()
