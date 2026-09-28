"""
KDE Plasma 6 / Breeze Native Style Integration for Delphis.
Delegates all visual styling directly to KDE Plasma 6's native QStyle (Breeze)
and system palette without overriding Qt widget delegates with synthetic CSS.
"""

from pathlib import Path
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QStyleFactory

def get_breeze_icon(name: str, fallback_icon: str = None) -> QIcon:
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
    Loads the editable SVG asset from delphis/assets/icons/delphis.svg.
    Falls back to the system theme 'delphis' or graphics category icon.
    """
    # 1. Bundled editable SVG asset
    svg_path = Path(__file__).resolve().parent.parent / "assets" / "icons" / "delphis.svg"
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

def setup_kde_plasma_integration(app: QApplication):
    """
    Connect with KDE Plasma 6's desktop environment and active theme.
    Ensures the application uses the native Breeze QStyle if available,
    allowing KDE Plasma to globally manage widget drawing, colors,
    dark/light mode, and accent colors.
    """
    # Set default application icon
    app_icon = get_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    # Prefer native Breeze style if available and not already set by platform theme
    available_styles = [s.lower() for s in QStyleFactory.keys()]
    if "breeze" in available_styles:
        app.setStyle("breeze")
    
    # Ensure no global stylesheet overrides break Breeze's native delegates
    app.setStyleSheet("")
