"""
Tab 2: Alpha & Transparency Adjuster
"""

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton,
    QButtonGroup, QCheckBox, QLabel, QPushButton, QDoubleSpinBox,
    QFormLayout, QColorDialog, QScrollArea, QMessageBox
)
from PyQt6.QtGui import QColor, QPixmap
from delphis_gui.gui.widgets.path_picker import PathPicker
from delphis_gui.gui.widgets.alpha_slider import AlphaSlider
from delphis_gui.style import get_breeze_icon

class AlphaTab(QWidget):
    """
    Interface for Alpha & Transparency manipulation.
    Controls alpha values (0-255) with anti-aliasing preservation,
    edge smoothing, halo defringing, and alpha removal with custom background matte.
    """
    requestWorker = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_bg_color: str = ""

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        # 1. Path Selection Card
        paths_group = QGroupBox("Input & Output Paths", self)
        paths_layout = QFormLayout(paths_group)
        paths_layout.setSpacing(10)

        self.input_picker = PathPicker(
            mode="both",
            placeholder="Select image file or folder to adjust...",
            parent=self
        )
        paths_layout.addRow("Input Image/Folder:", self.input_picker)

        self.output_picker = PathPicker(
            mode="directory",
            placeholder="Select destination folder for processed images...",
            parent=self
        )
        paths_layout.addRow("Output Folder:", self.output_picker)
        layout.addWidget(paths_group)

        # 2. Alpha Mode Card
        mode_group = QGroupBox("Transparency Mode", self)
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setSpacing(10)

        self.mode_btn_group = QButtonGroup(self)

        # Mode A: Adjust Alpha Value
        self.rb_adjust = QRadioButton("Adjust Alpha Opacity (0 = Transparent, 255 = Fully Opaque)", self)
        self.rb_adjust.setChecked(True)
        self.mode_btn_group.addButton(self.rb_adjust, 1)
        mode_layout.addWidget(self.rb_adjust)

        self.alpha_slider = AlphaSlider(default_val=130, parent=self)
        mode_layout.addWidget(self.alpha_slider)

        # Mode B: Remove Alpha
        remove_row = QHBoxLayout()
        self.rb_remove = QRadioButton("Completely Remove Alpha Channel (Convert RGBA -> RGB)", self)
        self.mode_btn_group.addButton(self.rb_remove, 2)
        remove_row.addWidget(self.rb_remove)

        self.btn_bg_color = QPushButton("Matte Background...", self)
        self.btn_bg_color.setIcon(get_breeze_icon("fill-color", "color-picker"))
        self.btn_bg_color.setEnabled(False)
        self.btn_bg_color.clicked.connect(self._pick_bg_color)
        remove_row.addWidget(self.btn_bg_color)

        self.lbl_bg_preview = QLabel("", self)
        self.lbl_bg_preview.setFixedSize(22, 22)
        remove_row.addWidget(self.lbl_bg_preview)
        remove_row.addStretch()

        mode_layout.addLayout(remove_row)
        layout.addWidget(mode_group)

        self.rb_adjust.toggled.connect(self._on_mode_changed)
        self.rb_remove.toggled.connect(self._on_mode_changed)

        # 3. Quality & Edge Refinements Card
        quality_group = QGroupBox("Edge Anti-Aliasing & Halo Removal", self)
        quality_layout = QVBoxLayout(quality_group)
        quality_layout.setSpacing(10)

        self.chk_defringe = QCheckBox("Defringe RGB Channels (Removes dark/light halos around transparent edges)", self)
        self.chk_defringe.setChecked(True)
        quality_layout.addWidget(self.chk_defringe)

        smooth_row = QHBoxLayout()
        self.chk_smooth = QCheckBox("Smooth Edges / Anti-Aliasing Filter (Fixes already pixelated borders)", self)
        self.chk_smooth.setChecked(False)
        smooth_row.addWidget(self.chk_smooth)

        smooth_lbl = QLabel("Radius:", self)
        self.spin_smooth_radius = QDoubleSpinBox(self)
        self.spin_smooth_radius.setRange(0.1, 10.0)
        self.spin_smooth_radius.setSingleStep(0.5)
        self.spin_smooth_radius.setValue(1.0)
        smooth_row.addWidget(smooth_lbl)
        smooth_row.addWidget(self.spin_smooth_radius)
        smooth_row.addStretch()
        quality_layout.addLayout(smooth_row)

        self.chk_hard = QCheckBox("Hard Alpha Cutout (Disable smooth sub-pixel scaling, force constant value)", self)
        quality_layout.addWidget(self.chk_hard)

        self.chk_recursive = QCheckBox("Process Subdirectories Recursively", self)
        self.chk_recursive.setChecked(True)
        quality_layout.addWidget(self.chk_recursive)

        layout.addWidget(quality_group)

        layout.addStretch()
        scroll.setWidget(container)

        main_vbox = QVBoxLayout(self)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.addWidget(scroll)

    def _on_mode_changed(self):
        is_remove = self.rb_remove.isChecked()
        self.btn_bg_color.setEnabled(is_remove)
        self.alpha_slider.setEnabled(not is_remove)

    def _pick_bg_color(self):
        col = QColorDialog.getColor(QColor(255, 255, 255), self, "Select Matte Background Color")
        if col.isValid():
            self.selected_bg_color = col.name()
            pm = QPixmap(20, 20)
            pm.fill(col)
            self.lbl_bg_preview.setPixmap(pm)
            self.lbl_bg_preview.setToolTip(f"Matte Color: {self.selected_bg_color}")

    def execute_action(self):
        """Execute alpha processing from top action bar."""
        in_path = self.input_picker.path()
        out_path = self.output_picker.path()

        if not in_path or not out_path:
            QMessageBox.warning(self, "Missing Paths", "Please specify both Input Path and Output Folder.")
            return

        cmd = ["alpha", in_path, out_path]
        if self.rb_remove.isChecked():
            cmd.append("--remove-alpha")
            if self.selected_bg_color:
                cmd.extend(["--bg", self.selected_bg_color])
        else:
            cmd.extend(["--alpha", str(self.alpha_slider.value())])

        if self.chk_hard.isChecked():
            cmd.append("--hard")

        if self.chk_smooth.isChecked():
            cmd.extend(["--smooth", "--smooth-radius", str(self.spin_smooth_radius.value())])

        if not self.chk_defringe.isChecked():
            cmd.append("--no-defringe")

        self.requestWorker.emit(cmd)

    def save_settings(self, settings):
        """Persist Alpha tab UI state."""
        settings.beginGroup("alpha")
        settings.setValue("input_path", self.input_picker.path())
        settings.setValue("output_path", self.output_picker.path())
        settings.setValue("mode_id", self.mode_btn_group.checkedId())
        settings.setValue("alpha_val", self.alpha_slider.value())
        settings.setValue("bg_color", self.selected_bg_color)
        settings.setValue("defringe", self.chk_defringe.isChecked())
        settings.setValue("smooth", self.chk_smooth.isChecked())
        settings.setValue("smooth_radius", self.spin_smooth_radius.value())
        settings.setValue("hard", self.chk_hard.isChecked())
        settings.setValue("recursive", self.chk_recursive.isChecked())
        settings.endGroup()

    def load_settings(self, settings):
        """Restore Alpha tab UI state from QSettings."""
        settings.beginGroup("alpha")
        in_path = settings.value("input_path", "")
        if in_path:
            self.input_picker.setPath(in_path)
        out_path = settings.value("output_path", "")
        if out_path:
            self.output_picker.setPath(out_path)

        mode_id = settings.value("mode_id", 1, type=int)
        btn = self.mode_btn_group.button(mode_id)
        if btn:
            btn.setChecked(True)

        self.alpha_slider.setValue(settings.value("alpha_val", 130, type=int))
        self.selected_bg_color = settings.value("bg_color", "")
        if self.selected_bg_color:
            pm = QPixmap(20, 20)
            pm.fill(QColor(self.selected_bg_color))
            self.lbl_bg_preview.setPixmap(pm)

        self.chk_defringe.setChecked(settings.value("defringe", True, type=bool))
        self.chk_smooth.setChecked(settings.value("smooth", False, type=bool))
        self.spin_smooth_radius.setValue(settings.value("smooth_radius", 1.0, type=float))
        self.chk_hard.setChecked(settings.value("hard", False, type=bool))
        self.chk_recursive.setChecked(settings.value("recursive", True, type=bool))
        self._on_mode_changed()
        settings.endGroup()
