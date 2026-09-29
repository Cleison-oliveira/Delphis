"""
Synchronized Alpha Slider + SpinBox + Preset Selector Widget.
"""

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSlider, QSpinBox, QLabel, QPushButton
)
from delphis_gui.constants import ALPHA_QUICK_PRESETS

class AlphaSlider(QWidget):
    """
    Control for selecting transparency / alpha values (0 to 255) with synchronized
    horizontal slider, numeric spinbox, increment/decrement buttons, and quick preset badges.
    """
    valueChanged = pyqtSignal(int)

    def __init__(self, default_val: int = 255, parent=None):
        super().__init__(parent)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        # Primary Slider & Spinbox Row
        slider_row = QHBoxLayout()
        slider_row.setSpacing(10)

        self.slider = QSlider(Qt.Orientation.Horizontal, self)
        self.slider.setRange(0, 255)
        self.slider.setValue(default_val)
        slider_row.addWidget(self.slider, stretch=1)

        self.spinbox = QSpinBox(self)
        self.spinbox.setRange(0, 255)
        self.spinbox.setValue(default_val)
        self.spinbox.setFixedWidth(75)
        slider_row.addWidget(self.spinbox)

        main_layout.addLayout(slider_row)

        # Quick Presets Row
        presets_row = QHBoxLayout()
        presets_row.setSpacing(6)
        presets_label = QLabel("Quick Presets:", self)
        presets_row.addWidget(presets_label)

        for val, label in ALPHA_QUICK_PRESETS:
            btn = QPushButton(label.split()[0], self)
            btn.setToolTip(f"Set alpha to {label}")
            btn.clicked.connect(lambda checked, v=val: self.setValue(v))
            presets_row.addWidget(btn)

        presets_row.addStretch()
        main_layout.addLayout(presets_row)

        # Connect signals
        self.slider.valueChanged.connect(self._on_slider_changed)
        self.spinbox.valueChanged.connect(self._on_spinbox_changed)

    def _on_slider_changed(self, val: int):
        self.spinbox.blockSignals(True)
        self.spinbox.setValue(val)
        self.spinbox.blockSignals(False)
        self.valueChanged.emit(val)

    def _on_spinbox_changed(self, val: int):
        self.slider.blockSignals(True)
        self.slider.setValue(val)
        self.slider.blockSignals(False)
        self.valueChanged.emit(val)

    def value(self) -> int:
        return self.spinbox.value()

    def setValue(self, val: int):
        self.slider.setValue(max(0, min(255, val)))
