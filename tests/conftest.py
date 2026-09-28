"""
Pytest configuration and global fixtures.
"""

import os
import sys
from pathlib import Path
import pytest
from PyQt6.QtWidgets import QApplication

# Ensure repository root is in Python path for test discovery
REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

@pytest.fixture(scope="session")
def qapp():
    """Ensure a headless QApplication instance is active for tests."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
