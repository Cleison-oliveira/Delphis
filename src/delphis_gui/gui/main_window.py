"""
Main Application Window for Delphis Qt6 GUI.
Adheres strictly to the KDE Plasma 6 Breeze design language.
"""

from typing import Optional, List
from PyQt6.QtCore import Qt, QSize, QSettings
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QMessageBox, QPushButton, QFrame, QDialog, QTextBrowser,
    QToolButton, QMenu, QStatusBar, QApplication, QStyleFactory
)
from delphis_gui.constants import APP_NAME, APP_TITLE, APP_VERSION
from delphis_gui.style import get_breeze_icon, get_app_icon, get_native_system_style
from delphis_gui.gui.widgets.console_drawer import ConsoleDrawer
from delphis_gui.gui.tabs.tab_dte import DTETab
from delphis_gui.gui.tabs.tab_alpha import AlphaTab
from delphis_gui.gui.tabs.tab_upscale import UpscaleTab
from delphis_gui.gui.tabs.tab_dds import DDSTab
from delphis_gui.core.bridge import CSharpCommandWorker

class MainWindow(QMainWindow):
    """
    Central GUI window for Delphis with native KDE Plasma 6 toolbar,
    segmented tab management, theme selection, and state persistence.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(960, 780)
        self.setMinimumSize(800, 620)
        self.setWindowIcon(get_app_icon())

        self.current_worker: Optional[CSharpCommandWorker] = None
        self._init_ui()
        self.load_settings()

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # 1. Top Header Toolbar
        toolbar = QFrame(self)
        toolbar.setFrameShape(QFrame.Shape.StyledPanel)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(6, 4, 6, 4)
        toolbar_layout.setSpacing(6)

        toolbar_layout.addStretch()

        # Action Button in Top Toolbar
        self.btn_top_action = QPushButton("Execute", self)
        self.btn_top_action.setIcon(get_breeze_icon("media-playback-start", "system-run"))
        self.btn_top_action.setToolTip("Execute Action for Active Tab")
        self.btn_top_action.clicked.connect(self._trigger_active_tab_action)
        toolbar_layout.addWidget(self.btn_top_action)

        # Cancel Button in Top Toolbar
        self.btn_top_cancel = QPushButton("Cancel", self)
        self.btn_top_cancel.setIcon(get_breeze_icon("process-stop", "dialog-cancel"))
        self.btn_top_cancel.setToolTip("Cancel Active Task")
        self.btn_top_cancel.setEnabled(False)
        self.btn_top_cancel.clicked.connect(self.cancel_active_worker)
        toolbar_layout.addWidget(self.btn_top_cancel)

        # Hamburger Menu Button
        self.btn_menu = QToolButton(self)
        self.btn_menu.setIcon(get_breeze_icon("open-menu", "application-menu"))
        self.btn_menu.setIconSize(QSize(22, 22))
        self.btn_menu.setFixedSize(32, 32)
        self.btn_menu.setToolTip("Menu")
        self.btn_menu.setAutoRaise(True)
        self.btn_menu.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        app_menu = QMenu(self)

        # Theme Submenu (Kdenlive / Krita style)
        self.theme_menu = app_menu.addMenu(get_breeze_icon("preferences-desktop-theme", "style"), "Theme")
        self.theme_action_group = QActionGroup(self)
        self.theme_action_group.setExclusive(True)

        settings = QSettings("Delphis", "Delphis")
        saved_theme = settings.value("ui/theme", "Native")

        # 1. Native / System Theme Option
        act_native = QAction("Native (System Default)", self.theme_menu)
        act_native.setCheckable(True)
        if not saved_theme or saved_theme.lower() == "native":
            act_native.setChecked(True)
        act_native.triggered.connect(lambda checked: self._change_theme("Native"))
        self.theme_action_group.addAction(act_native)
        self.theme_menu.addAction(act_native)

        self.theme_menu.addSeparator()

        # 2. Available QStyleFactory styles
        available_styles = QStyleFactory.keys()
        for style_name in available_styles:
            act = QAction(style_name, self.theme_menu)
            act.setCheckable(True)
            if saved_theme and saved_theme.lower() != "native" and style_name.lower() == saved_theme.lower():
                act.setChecked(True)
            act.triggered.connect(lambda checked, s=style_name: self._change_theme(s))
            self.theme_action_group.addAction(act)
            self.theme_menu.addAction(act)

        app_menu.addSeparator()

        act_doctor = app_menu.addAction(get_breeze_icon("system-help", "help-contents"), "Run System Doctor")
        act_doctor.triggered.connect(self._run_doctor)

        act_about = app_menu.addAction(get_breeze_icon("help-about", "dialog-information"), f"About {APP_NAME}")
        act_about.triggered.connect(self._show_about_dialog)

        act_about_qt = app_menu.addAction(get_breeze_icon("help-about", "dialog-information"), "About Qt")
        act_about_qt.triggered.connect(self._show_about_qt_dialog)

        app_menu.addSeparator()
        act_quit = app_menu.addAction(get_breeze_icon("application-exit", "window-close"), "Quit")
        act_quit.triggered.connect(self.close)

        self.btn_menu.setMenu(app_menu)
        toolbar_layout.addWidget(self.btn_menu)

        main_layout.addWidget(toolbar)

        # 2. Main Tabbed Content Area
        self.tab_widget = QTabWidget(self)

        self.tab_dte = DTETab(self)
        self.tab_alpha = AlphaTab(self)
        self.tab_upscale = UpscaleTab(self)
        self.tab_dds = DDSTab(self)

        icon_dte = get_breeze_icon("archive-extract", "archive-extract-symbolic")
        icon_alpha = get_breeze_icon("edit-opacity", "draw-brush-symbolic")
        icon_upscale = get_breeze_icon("transform-scale", "zoom-in-symbolic")
        icon_dds = get_breeze_icon("speedometer", "flash-symbolic")

        self.tab_widget.addTab(self.tab_dte, icon_dte, "Extraction (DTE)")
        self.tab_widget.addTab(self.tab_alpha, icon_alpha, "Alpha & Transparency")
        self.tab_widget.addTab(self.tab_upscale, icon_upscale, "AI Upscaler (4-Channel)")
        self.tab_widget.addTab(self.tab_dds, icon_dds, "DDS Texture Optimizer")

        self.tab_dte.requestWorker.connect(self.start_worker_with_args)
        self.tab_alpha.requestWorker.connect(self.start_worker_with_args)
        self.tab_upscale.requestWorker.connect(self.start_worker_with_args)
        self.tab_dds.requestWorker.connect(self.start_worker_with_args)

        main_layout.addWidget(self.tab_widget, stretch=1)

        # 3. Bottom Console Output Drawer
        self.console_drawer = ConsoleDrawer(self)
        main_layout.addWidget(self.console_drawer)

        # 4. Status Bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        self.console_drawer.append_log("Ready for use.", "info")

    def _trigger_active_tab_action(self):
        current_idx = self.tab_widget.currentIndex()
        tab_map = {
            0: self.tab_dte,
            1: self.tab_alpha,
            2: self.tab_upscale,
            3: self.tab_dds
        }
        tab = tab_map.get(current_idx)
        if tab and hasattr(tab, "execute_action"):
            tab.execute_action()

    def _run_doctor(self):
        self.start_worker_with_args(["doctor"])

    def _show_about_dialog(self):
        about_dlg = QDialog(self)
        about_dlg.setWindowTitle(f"About {APP_NAME}")
        about_dlg.resize(480, 300)
        dlg_layout = QVBoxLayout(about_dlg)

        tb = QTextBrowser(about_dlg)
        tb.setOpenExternalLinks(True)
        tb.setHtml(f"""
        <h3>{APP_TITLE}</h3>
        <p><b>Version:</b> {APP_VERSION}</p>
        <p>Unified texture processing suite for the Dolphin GameCube and Wii emulator.</p>
        <p><b>Engine:</b> Modern C# (.NET 8) Core with Qt6 Desktop Interface.</p>
        <hr>
        <p><b>Modules:</b></p>
        <ul>
            <li><b>DTE Extraction & Tonemaps:</b> Dumps textures, merges grayscale tonemaps into RGBA, and exports split formats.</li>
            <li><b>Alpha & Transparency:</b> Proportional anti-aliased transparency tuning, smoothing, and defringing.</li>
            <li><b>AI Upscaler:</b> 4-channel Real-ESRGAN Vulkan NCNN alpha-preserving upscaler.</li>
            <li><b>DDS Texture Optimizer:</b> Hardware block compression (BC7, BC1, BC3, BC5) with Mipmaps.</li>
        </ul>
        """)
        dlg_layout.addWidget(tb)

        btn_close = QPushButton("Close", about_dlg)
        btn_close.setIcon(get_breeze_icon("dialog-close", "window-close"))
        btn_close.clicked.connect(about_dlg.accept)
        dlg_layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)
        about_dlg.exec()

    def _show_about_qt_dialog(self):
        """Displays native About Qt dialog."""
        QApplication.aboutQt()

    def start_worker_with_args(self, cmd_args: List[str]):
        """Schedule and run a background worker thread calling Delphis C# Engine."""
        if self.current_worker and self.current_worker.isRunning():
            QMessageBox.warning(
                self,
                "Task in Progress",
                "Another operation is currently running. Please wait or cancel the active task before starting a new one."
            )
            return

        is_quiet = ("--no-logs" in cmd_args or "--quiet" in cmd_args or "-q" in cmd_args)
        worker = CSharpCommandWorker(cmd_args, quiet=is_quiet, parent=self)
        self.current_worker = worker

        worker.signals.started.connect(self._on_worker_started)
        worker.signals.output_line.connect(self.console_drawer.append_log)
        worker.signals.progress.connect(self.console_drawer.set_progress)
        worker.signals.finished.connect(self._on_worker_finished)
        worker.signals.cancelled.connect(self._on_worker_cancelled)

        self.console_drawer.set_busy(True)
        self.tab_widget.setEnabled(False)
        self.btn_top_action.setEnabled(False)
        self.btn_top_cancel.setEnabled(True)
        worker.start()

    def cancel_active_worker(self):
        if self.current_worker and self.current_worker.isRunning():
            self.console_drawer.append_log("Requesting task cancellation...", "warning")
            self.current_worker.cancel()

    def _on_worker_started(self):
        self.console_drawer.set_status("Running C# task in background...")

    def _on_worker_finished(self, success: bool, msg: str):
        self.console_drawer.set_busy(False)
        self.tab_widget.setEnabled(True)
        self.btn_top_action.setEnabled(True)
        self.btn_top_cancel.setEnabled(False)
        self.console_drawer.set_status("Finished" if success else "Failed")
        self.current_worker = None

    def _on_worker_cancelled(self):
        self.console_drawer.set_busy(False)
        self.tab_widget.setEnabled(True)
        self.btn_top_action.setEnabled(True)
        self.btn_top_cancel.setEnabled(False)
        self.console_drawer.set_status("Cancelled")
        self.current_worker = None

    def _change_theme(self, theme_name: str):
        """Applies chosen QStyle or resets to native desktop platform style, persisting it to QSettings."""
        if theme_name.lower() == "native":
            native_style = get_native_system_style()
            created = QStyleFactory.create(native_style) if native_style in QStyleFactory.keys() else None
            if created:
                QApplication.setStyle(created)
            else:
                QApplication.setStyle(native_style)
            self.console_drawer.append_log(f"Theme changed to: Native ({native_style})", "info")
        else:
            created = QStyleFactory.create(theme_name)
            if created:
                QApplication.setStyle(created)
            else:
                QApplication.setStyle(theme_name)
            self.console_drawer.append_log(f"Theme changed to: {theme_name}", "info")

        # Repolish all widgets immediately for live update without restart
        for widget in QApplication.allWidgets():
            try:
                widget.style().unpolish(widget)
                widget.style().polish(widget)
                widget.update()
            except Exception:
                pass

        settings = QSettings("Delphis", "Delphis")
        settings.setValue("ui/theme", theme_name)

    def save_settings(self):
        """Persists window geometry, active tab, and all tab settings to QSettings."""
        settings = QSettings("Delphis", "Delphis")
        settings.beginGroup("main_window")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("window_state", self.saveState())
        settings.setValue("active_tab", self.tab_widget.currentIndex())
        settings.endGroup()

        self.tab_dte.save_settings(settings)
        self.tab_alpha.save_settings(settings)
        self.tab_upscale.save_settings(settings)
        self.tab_dds.save_settings(settings)

    def load_settings(self):
        """Restores window geometry, active tab, and all tab settings from QSettings."""
        settings = QSettings("Delphis", "Delphis")
        settings.beginGroup("main_window")
        geo = settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        state = settings.value("window_state")
        if state:
            self.restoreState(state)
        active_tab = settings.value("active_tab", 0, type=int)
        if 0 <= active_tab < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(active_tab)
        settings.endGroup()

        self.tab_dte.load_settings(settings)
        self.tab_alpha.load_settings(settings)
        self.tab_upscale.load_settings(settings)
        self.tab_dds.load_settings(settings)

    def closeEvent(self, event):
        self.save_settings()
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.cancel()
            self.current_worker.wait(1500)
        event.accept()
