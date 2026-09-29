"""
Tab 1: Dolphin Texture Extraction & Tonemaps (DTE)
"""

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton,
    QButtonGroup, QCheckBox, QLabel, QLineEdit, QFormLayout, QScrollArea,
    QSpinBox, QComboBox, QMessageBox
)
from delphis_gui.constants import GAME_ARCHIVE_FILE_FILTER, IMAGE_FILE_FILTER
from delphis_gui.gui.widgets.path_picker import PathPicker

class DTETab(QWidget):
    """
    Interface for DolphinTextureExtraction-tool.
    Handles texture extraction, tonemap reconstruction (CombineRGBA / CombineBGRA),
    and splitting high-res textures for Dolphin (Finalize).
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
        paths_group = QGroupBox("Paths & Files", self)
        paths_layout = QFormLayout(paths_group)
        paths_layout.setSpacing(10)

        self.input_picker = PathPicker(
            mode="both",
            file_filter=IMAGE_FILE_FILTER,
            placeholder="Select Game dump/ISO, tonemap pairs (RGBA_*), or folder...",
            parent=self
        )
        paths_layout.addRow("Input Path:", self.input_picker)

        self.output_picker = PathPicker(
            mode="directory",
            placeholder="Select destination folder for extracted/merged textures...",
            parent=self
        )
        paths_layout.addRow("Output Folder:", self.output_picker)
        layout.addWidget(paths_group)

        # 2. Mode of Operation Card
        mode_group = QGroupBox("DTE Operation Mode", self)
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setSpacing(10)

        self.mode_btn_group = QButtonGroup(self)

        self.rb_merge_rgba = QRadioButton("Combine RGBA Tonemaps (Merge grayscale pairs into RGBA PNG)", self)
        self.rb_merge_rgba.setToolTip("Command: CombineRGBA. Finds split grayscale tonemap files (RGBA_*) and combines them into editable RGBA textures.")
        self.rb_merge_rgba.setChecked(True)
        self.mode_btn_group.addButton(self.rb_merge_rgba, 1)
        mode_layout.addWidget(self.rb_merge_rgba)

        self.rb_merge_bgra = QRadioButton("Combine BGRA Tonemaps (Merge grayscale pairs into BGRA PNG)", self)
        self.rb_merge_bgra.setToolTip("Command: CombineBGRA. Finds split grayscale tonemap files (BGRA_*) and combines them into editable BGRA textures.")
        self.mode_btn_group.addButton(self.rb_merge_bgra, 2)
        mode_layout.addWidget(self.rb_merge_bgra)

        self.rb_split = QRadioButton("Finalize & Split (Export High-Res Textures back to Dolphin Tonemaps)", self)
        self.rb_split.setToolTip("Command: Finalize. Takes high-resolution edited textures, splits them into Dolphin tonemap pairs, and optimizes them.")
        self.mode_btn_group.addButton(self.rb_split, 3)
        mode_layout.addWidget(self.rb_split)

        self.rb_extract = QRadioButton("Extract Game Textures (Dump with Dolphin texture hash)", self)
        self.rb_extract.setToolTip("Command: Extract. Dumps all textures from game ISOs/archives formatted with Dolphin texture hashes.")
        self.mode_btn_group.addButton(self.rb_extract, 4)
        mode_layout.addWidget(self.rb_extract)

        self.rb_unpack = QRadioButton("Unpack Raw Archives (Extract files without texture conversion)", self)
        self.rb_unpack.setToolTip("Command: Unpack. Recursively unpacks game files and nested archives.")
        self.mode_btn_group.addButton(self.rb_unpack, 5)
        mode_layout.addWidget(self.rb_unpack)

        self.rb_custom = QRadioButton("Custom DTE Command", self)
        self.mode_btn_group.addButton(self.rb_custom, 6)
        mode_layout.addWidget(self.rb_custom)

        custom_row = QHBoxLayout()
        custom_row.setContentsMargins(20, 0, 0, 0)
        lbl_custom_cmd = QLabel("Command Verb:", self)
        self.txt_custom_cmd = QLineEdit(self)
        self.txt_custom_cmd.setPlaceholderText("e.g. Extract, Unpack, Split, Compress")
        self.txt_custom_cmd.setEnabled(False)
        custom_row.addWidget(lbl_custom_cmd)
        custom_row.addWidget(self.txt_custom_cmd)
        mode_layout.addLayout(custom_row)

        self.rb_custom.toggled.connect(self.txt_custom_cmd.setEnabled)
        self.mode_btn_group.buttonToggled.connect(self._on_mode_changed)
        self._on_mode_changed(None, True)

        layout.addWidget(mode_group)

        # 3. Parameters & Flags Card
        options_group = QGroupBox("DTE Options & Concurrency", self)
        options_layout = QFormLayout(options_group)
        options_layout.setSpacing(10)

        # Tasks / Concurrency
        self.spin_tasks = QSpinBox(self)
        self.spin_tasks.setRange(1, 32)
        self.spin_tasks.setValue(1)
        self.spin_tasks.setToolTip("Maximum concurrent tasks (-Tasks). Setting to 1 prevents concurrent collection crashes in DTE.")
        options_layout.addRow("Max Concurrent Tasks (-Tasks):", self.spin_tasks)

        # Cleanup Mode
        self.combo_cleanup = QComboBox(self)
        self.combo_cleanup.addItem("Retain Original Folder Structure (none)", "none")
        self.combo_cleanup.addItem("Clean / Shorten Unnecessary Folders (default)", "default")
        self.combo_cleanup.addItem("Move All Files to Single Folder (simple)", "simple")
        self.combo_cleanup.addItem("Compact Paths (compact)", "compact")
        options_layout.addRow("Folder Structure (-Cleanup):", self.combo_cleanup)

        # Checkbox Flags Row
        flags_vbox = QVBoxLayout()
        flags_vbox.setSpacing(8)

        self.chk_recursive = QCheckBox("Recursive Archive/Folder Extraction (-Recursiv 0)", self)
        self.chk_recursive.setChecked(True)
        flags_vbox.addWidget(self.chk_recursive)

        self.chk_mips = QCheckBox("Extract Mipmaps (-Mip)", self)
        self.chk_mips.setChecked(False)
        flags_vbox.addWidget(self.chk_mips)

        self.chk_dmd = QCheckBox("Dolphin Mipmap Detection (-Dolphinmipdetection)", self)
        self.chk_dmd.setChecked(True)
        flags_vbox.addWidget(self.chk_dmd)

        self.chk_logfile = QCheckBox("Generate DTE Log File (.log in output folder)", self)
        self.chk_logfile.setChecked(False)
        self.chk_logfile.setToolTip("When checked, saves DTE-*.log file to the output directory. When unchecked, logs appear only in the console drawer without creating a file on disk.")
        flags_vbox.addWidget(self.chk_logfile)

        options_layout.addRow("Detection Flags:", flags_vbox)

        # Extra Flags
        self.txt_extra = QLineEdit(self)
        self.txt_extra.setPlaceholderText("e.g. -Force -Dryrun")
        options_layout.addRow("Extra CLI Flags:", self.txt_extra)

        layout.addWidget(options_group)

        layout.addStretch()
        scroll.setWidget(container)

        main_vbox = QVBoxLayout(self)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.addWidget(scroll)

    def _on_mode_changed(self, button=None, checked=True):
        if not checked:
            return
        mode_id = self.mode_btn_group.checkedId()
        if mode_id in (4, 5):  # 4 = Extract Game Textures, 5 = Unpack Raw Archives
            self.input_picker.setFileFilter(GAME_ARCHIVE_FILE_FILTER)
            self.input_picker.setPlaceholder("Select Game ISO/Disc (.iso, .rvz, .gcm, .wbfs), archive (.arc, .szs, .pak), or folder...")
        else:
            self.input_picker.setFileFilter(IMAGE_FILE_FILTER)
            self.input_picker.setPlaceholder("Select Game dump/ISO, tonemap pairs (RGBA_*), or folder containing textures...")

    def execute_action(self):
        """Execute DTE task from top action bar."""
        in_path = self.input_picker.path()
        out_path = self.output_picker.path()

        if not in_path or not out_path:
            QMessageBox.warning(self, "Missing Paths", "Please specify both Input Path and Output Folder.")
            return

        mode_id = self.mode_btn_group.checkedId()
        mode_map = {
            1: "merge_rgba",
            2: "merge_bgra",
            3: "split_tonemaps",
            4: "extract",
            5: "unpack",
            6: "custom"
        }
        mode_name = mode_map.get(mode_id, "merge_rgba")

        cmd = [
            "dte", mode_name, in_path, out_path,
            "--tasks", str(self.spin_tasks.value()),
            "--cleanup", str(self.combo_cleanup.currentData())
        ]

        if not self.chk_recursive.isChecked():
            cmd.append("--no-recursive")
        if self.chk_mips.isChecked():
            cmd.append("--mips")
        if not self.chk_dmd.isChecked():
            cmd.append("--no-dmd")
        if self.chk_logfile.isChecked():
            cmd.append("--logfile")
        else:
            cmd.append("--no-logfile")

        if mode_name == "custom" and self.txt_custom_cmd.text().strip():
            cmd.extend(["--custom-cmd", self.txt_custom_cmd.text().strip()])

        self.requestWorker.emit(cmd)

    def save_settings(self, settings):
        """Persist DTE tab UI state."""
        settings.beginGroup("dte")
        settings.setValue("input_path", self.input_picker.path())
        settings.setValue("output_path", self.output_picker.path())
        settings.setValue("mode_id", self.mode_btn_group.checkedId())
        settings.setValue("tasks", self.spin_tasks.value())
        settings.setValue("cleanup_index", self.combo_cleanup.currentIndex())
        settings.setValue("recursive", self.chk_recursive.isChecked())
        settings.setValue("mips", self.chk_mips.isChecked())
        settings.setValue("dmd", self.chk_dmd.isChecked())
        settings.setValue("logfile", self.chk_logfile.isChecked())
        settings.setValue("custom_cmd", self.txt_custom_cmd.text())
        settings.setValue("extra", self.txt_extra.text())
        settings.endGroup()

    def load_settings(self, settings):
        """Restore DTE tab UI state from QSettings."""
        settings.beginGroup("dte")
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

        self.spin_tasks.setValue(settings.value("tasks", 1, type=int))
        self.combo_cleanup.setCurrentIndex(settings.value("cleanup_index", 0, type=int))
        self.chk_recursive.setChecked(settings.value("recursive", True, type=bool))
        self.chk_mips.setChecked(settings.value("mips", False, type=bool))
        self.chk_dmd.setChecked(settings.value("dmd", True, type=bool))
        self.chk_logfile.setChecked(settings.value("logfile", False, type=bool))
        self.txt_custom_cmd.setText(settings.value("custom_cmd", ""))
        self.txt_extra.setText(settings.value("extra", ""))
        settings.endGroup()
