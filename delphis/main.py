"""
Main Application Entry Point for Delphis.
"""

import sys
import os
import signal

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from delphis.gui.main_window import MainWindow
from delphis.gui.style import setup_kde_plasma_integration
from delphis.constants import APP_NAME, APP_VERSION

def main():
    # Allow Ctrl+C in terminal to terminate the Qt application cleanly
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("DolphinEmu")

    # Connect with KDE Plasma's global platform theme and color scheme
    setup_kde_plasma_integration(app)

    window = MainWindow()
    window.show()

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
