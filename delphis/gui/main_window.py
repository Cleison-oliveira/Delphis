"""
Main Application Window for Delphis.
Adheres strictly to the KDE Plasma 6 Breeze Dark design language.
"""

from typing import Optional
from PyQt6.QtCore import Qt, QEvent, QSize
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QStatusBar, QMessageBox, QPushButton, QFrame,
    QDialog, QTextBrowser, QToolButton, QMenu
)
from PyQt6.QtGui import QIcon

from delphis.constants import APP_NAME, APP_TITLE, APP_VERSION
from delphis.gui.style import get_breeze_icon, get_app_icon, setup_kde_plasma_integration
from delphis.gui.widgets.console_drawer import ConsoleDrawer
from delphis.gui.tabs.tab_dte import DTETab
from delphis.gui.tabs.tab_alpha import AlphaTab
from delphis.gui.tabs.tab_upscale import UpscaleTab
from delphis.gui.tabs.tab_dds import DDSTab
from delphis.core.runner import BaseWorker
from delphis.core.downloader import ToolDownloaderWorker
from delphis.core.env_check import find_executable
from delphis.core.upscaler_backend import UpscalerWorker

class MainWindow(QMainWindow):
    """
    Central GUI window for Delphis with native KDE Plasma 6 toolbar,
    segmented tab management, and asynchronous task execution.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(960, 780)
        self.setMinimumSize(800, 620)

        # Set application icon
        self.setWindowIcon(get_app_icon())

        self.current_worker: Optional[BaseWorker] = None
        self.downloader_worker: Optional[ToolDownloaderWorker] = None
        self._pending_upscale_worker: Optional[UpscalerWorker] = None

        self._init_ui()

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # 1. Top Header Toolbar (KDE Plasma style)
        toolbar = QFrame(self)
        toolbar.setFrameShape(QFrame.Shape.StyledPanel)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(6, 4, 6, 4)
        toolbar_layout.setSpacing(6)

        toolbar_layout.addStretch()

        # Action Button in Top Toolbar (Breeze style)
        self.btn_top_action = QPushButton("Execute", self)
        self.btn_top_action.setIcon(get_breeze_icon("media-playback-start", "system-run"))
        self.btn_top_action.setToolTip("Execute Action for Active Tab")
        self.btn_top_action.clicked.connect(self._trigger_active_tab_action)
        toolbar_layout.addWidget(self.btn_top_action)

        # Cancel Button in Top Toolbar (Breeze style)
        self.btn_top_cancel = QPushButton("Cancel", self)
        self.btn_top_cancel.setIcon(get_breeze_icon("process-stop", "dialog-cancel"))
        self.btn_top_cancel.setToolTip("Cancel Active Task")
        self.btn_top_cancel.setEnabled(False)
        self.btn_top_cancel.clicked.connect(self.cancel_active_worker)
        toolbar_layout.addWidget(self.btn_top_cancel)

        # Hamburger / Application Menu Button (KDE Plasma style)
        self.btn_menu = QToolButton(self)
        self.btn_menu.setIcon(get_breeze_icon("open-menu", "application-menu"))
        self.btn_menu.setIconSize(QSize(22, 22))
        self.btn_menu.setFixedSize(32, 32)
        self.btn_menu.setToolTip("Menu")
        self.btn_menu.setAutoRaise(True)
        self.btn_menu.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.btn_menu.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_menu.setStyleSheet("QToolButton::menu-indicator { image: none; width: 0px; }")

        app_menu = QMenu(self)
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

        # Connect tab worker requests
        self.tab_dte.requestWorker.connect(self.start_worker)
        self.tab_alpha.requestWorker.connect(self.start_worker)
        self.tab_upscale.requestWorker.connect(self.start_worker)
        self.tab_dds.requestWorker.connect(self.start_worker)

        main_layout.addWidget(self.tab_widget, stretch=1)

        # 3. Bottom Console Output Drawer
        self.console_drawer = ConsoleDrawer(self)
        main_layout.addWidget(self.console_drawer)

        # 4. Status Bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        self.console_drawer.append_log(f"Delphis v{APP_VERSION} ready.", "info")

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

    def _show_about_dialog(self):
        about_dlg = QDialog(self)
        about_dlg.setWindowTitle(f"About {APP_NAME}")
        about_dlg.resize(460, 300)
        dlg_layout = QVBoxLayout(about_dlg)

        tb = QTextBrowser(about_dlg)
        tb.setOpenExternalLinks(True)
        tb.setHtml(f"""
        <h3>{APP_TITLE}</h3>
        <p><b>Version:</b> {APP_VERSION}</p>
        <p>Unified texture processing suite for the Dolphin GameCube and Wii emulator.</p>
        <hr>
        <p><b>Modules:</b></p>
        <ul>
            <li><b>DTE Extraction & Tonemaps:</b> Dumps textures, merges grayscale tonemaps into RGBA, and exports split formats.</li>
            <li><b>Alpha & Transparency:</b> Proportional anti-aliased transparency tuning, smoothing, and defringing.</li>
            <li><b>AI Upscaler:</b> 4-channel Real-ESRGAN Vulkan NCNN alpha-preserving upscaler.</li>
            <li><b>DDS Texture Optimizer:</b> Hardware block compression (BC7, BC1, BC3, BC5) with Mipmaps for maximum emulator performance.</li>
        </ul>
        """)
        dlg_layout.addWidget(tb)

        btn_close = QPushButton("Close", about_dlg)
        btn_close.setIcon(get_breeze_icon("dialog-close", "window-close"))
        btn_close.clicked.connect(about_dlg.accept)
        dlg_layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

        about_dlg.exec()

    def _show_about_qt_dialog(self):
        about_dlg = QDialog(self)
        about_dlg.setWindowTitle("About Qt")
        about_dlg.resize(480, 240)
        dlg_layout = QVBoxLayout(about_dlg)

        from PyQt6.QtCore import qVersion
        tb = QTextBrowser(about_dlg)
        tb.setOpenExternalLinks(True)
        tb.setHtml(f"""
        <h3>About Qt</h3>
        <p>This program uses <b>Qt version {qVersion()}</b>.</p>
        <p>Qt is a C++ toolkit for cross-platform application development.</p>
        <p>Qt provides single-source portability across all major desktop operating systems.</p>
        <p>For more information, visit <a href="https://www.qt.io/">qt.io</a>.</p>
        """)
        dlg_layout.addWidget(tb)

        btn_close = QPushButton("Close", about_dlg)
        btn_close.setIcon(get_breeze_icon("dialog-close", "window-close"))
        btn_close.clicked.connect(about_dlg.accept)
        dlg_layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

        about_dlg.exec()

    def start_worker(self, worker: BaseWorker):
        """Schedule and run a background worker thread."""
        if self.current_worker and self.current_worker.isRunning():
            QMessageBox.warning(
                self,
                "Task in Progress",
                "Another operation is currently running. Please wait or cancel the active task before starting a new one."
            )
            return

        # Automatic Provisioning: Check if Real-ESRGAN is missing when running upscaler
        if isinstance(worker, UpscalerWorker):
            realesrgan_bin = find_executable("realesrgan-ncnn-vulkan") or find_executable("realesrgan")
            if not realesrgan_bin:
                self.console_drawer.append_log("Real-ESRGAN or AI neural models not found. Auto-downloading in background...", "info")
                self._pending_upscale_worker = worker
                self._run_auto_downloader()
                return

        self._execute_worker(worker)

    def _run_auto_downloader(self):
        """Run background downloader."""
        self.downloader_worker = ToolDownloaderWorker(self)
        self.downloader_worker.output_line.connect(self.console_drawer.append_log)
        self.downloader_worker.progress.connect(lambda cur, tot, msg: self.console_drawer.set_status(msg))
        self.downloader_worker.finished.connect(self._on_auto_download_finished)

        self.console_drawer.set_busy(True)
        self.tab_widget.setEnabled(False)
        self.btn_top_action.setEnabled(False)
        self.btn_top_cancel.setEnabled(True)
        self.downloader_worker.start()

    def _on_auto_download_finished(self, success: bool, msg: str):
        if success and self._pending_upscale_worker:
            self.console_drawer.append_log("Auto-download complete. Proceeding with AI Upscale task...", "success")
            pending = self._pending_upscale_worker
            self._pending_upscale_worker = None
            self._execute_worker(pending)
        else:
            self.console_drawer.set_busy(False)
            self.tab_widget.setEnabled(True)
            self.btn_top_action.setEnabled(True)
            self.btn_top_cancel.setEnabled(False)
            self._pending_upscale_worker = None
            self.console_drawer.set_status("Download failed" if not success else "Ready")

    def _execute_worker(self, worker: BaseWorker):
        self.current_worker = worker

        # Connect worker signals to console drawer
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
        """Cancel the running background worker or downloader."""
        if self.downloader_worker and self.downloader_worker.isRunning():
            self.console_drawer.append_log("Cancelling background tool download...", "warning")
            self.downloader_worker.cancel()
            self._pending_upscale_worker = None

        if self.current_worker and self.current_worker.isRunning():
            self.console_drawer.append_log("Requesting task cancellation...", "warning")
            self.current_worker.cancel()

    def _on_worker_started(self):
        self.console_drawer.set_status("Running task in background...")

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

    def closeEvent(self, event):
        """Ensure running subprocesses are stopped when closing window."""
        if self.downloader_worker and self.downloader_worker.isRunning():
            self.downloader_worker.cancel()
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.cancel()
            self.current_worker.wait(1500)
        event.accept()
