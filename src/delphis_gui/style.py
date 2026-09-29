"""
KDE Plasma 6 / Breeze Native Style Integration for Delphis.
Delegates visual styling directly to KDE Plasma's native QStyle (Breeze)
and system palette without overriding Qt widget delegates with synthetic CSS.
"""

from pathlib import Path
from typing import Optional
from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QStyleFactory

def get_breeze_icon(name: str, fallback_icon: Optional[str] = None) -> QIcon:
    """Retrieve icon from the active system theme (Breeze) with fallback."""
    icon = QIcon.fromTheme(name)
    if not icon.isNull():
        return icon
    if fallback_icon:
        fb = QIcon.fromTheme(fallback_icon)
        if not fb.isNull():
            return fb
    return QIcon()

def get_app_icon() -> QIcon:
    """
    Retrieve the main application icon for Delphis.
    Loads the SVG asset from assets/icons/delphis.svg.
    """
    # 1. Bundled vector SVG asset
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "assets" / "icons" / "delphis.svg",
        Path(__file__).resolve().parent / "assets" / "icons" / "delphis.svg",
        Path("/run/current-system/sw/share/icons/hicolor/scalable/apps/delphis.svg"),
        Path.home() / ".nix-profile/share/icons/hicolor/scalable/apps/delphis.svg"
    ]
    for svg_path in candidates:
        if svg_path.is_file():
            icon = QIcon(str(svg_path))
            if not icon.isNull():
                return icon

    # 2. Installed XDG system theme icon
    theme_icon = QIcon.fromTheme("delphis")
    if not theme_icon.isNull():
        return theme_icon

    # 3. Breeze fallback
    return get_breeze_icon("applications-graphics", "image-x-generic")

NATIVE_SYSTEM_STYLE: Optional[str] = None

def get_native_system_style() -> str:
    """Returns the native system style detected at startup (e.g. Breeze, Fusion)."""
    global NATIVE_SYSTEM_STYLE
    if NATIVE_SYSTEM_STYLE:
        return NATIVE_SYSTEM_STYLE
    if QApplication.style():
        NATIVE_SYSTEM_STYLE = QApplication.style().objectName()
        if NATIVE_SYSTEM_STYLE:
            return NATIVE_SYSTEM_STYLE
    available_styles_lower = {s.lower(): s for s in QStyleFactory.keys()}
    if "breeze" in available_styles_lower:
        return available_styles_lower["breeze"]
    if "fusion" in available_styles_lower:
        return available_styles_lower["fusion"]
    return QStyleFactory.keys()[0] if QStyleFactory.keys() else "Fusion"

def setup_kde_plasma_integration(app: QApplication):
    """
    Connect with desktop environment and restore active/saved visual theme.
    Loads theme from QSettings ("Native" / specific style) without breaking qt6ct/KDE platform themes.
    """
    global NATIVE_SYSTEM_STYLE
    if not NATIVE_SYSTEM_STYLE and app.style():
        NATIVE_SYSTEM_STYLE = app.style().objectName()

    app_icon = get_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    settings = QSettings("Delphis", "Delphis")
    saved_theme = settings.value("ui/theme", "Native")

    available_styles = QStyleFactory.keys()
    if saved_theme and saved_theme.lower() != "native" and saved_theme in available_styles:
        app.setStyle(saved_theme)

    app.setStyleSheet("")
