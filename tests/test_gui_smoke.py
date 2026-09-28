"""
Smoke tests for PyQt6 GUI components in headless offscreen mode.
"""

import os
import pytest
from PyQt6.QtWidgets import QApplication
from delphis.gui.main_window import MainWindow

@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_main_window_init(qapp):
    window = MainWindow()
    assert window.windowTitle().startswith("Delphis")

    # Check tabs count
    assert window.tab_widget.count() == 4

    # Check tab instances
    assert window.tab_dte is not None
    assert window.tab_alpha is not None
    assert window.tab_upscale is not None
    assert window.tab_dds is not None

    # Check console drawer and buttons
    assert window.console_drawer is not None
    assert window.btn_top_action.isEnabled() is True
    assert window.btn_top_cancel.isEnabled() is False

    window.close()
