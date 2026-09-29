"""
Main Application Entry Point for Delphis Qt6 GUI.
"""

import os
import sys
import signal

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication
from delphis_gui.gui.main_window import MainWindow
from delphis_gui.style import setup_kde_plasma_integration
from delphis_gui.constants import APP_NAME, APP_VERSION

def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # 1. Respect user's existing QT_QPA_PLATFORM environment variable
    # Only set a default if completely empty or unset in system
    if "QT_QPA_PLATFORM" in os.environ and not os.environ["QT_QPA_PLATFORM"].strip():
        del os.environ["QT_QPA_PLATFORM"]

    # 2. Application and Organization metadata for QSettings
    QCoreApplication.setOrganizationName("Delphis")
    QCoreApplication.setOrganizationDomain("github.com/Cleison-oliveira/Delphis")
    QCoreApplication.setApplicationName("Delphis")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Delphis")
    app.setOrganizationDomain("github.com/Cleison-oliveira/Delphis")

    setup_kde_plasma_integration(app)

    window = MainWindow()
    window.show()

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
