"""
Automatic Downloader & Tool Provisioner for Delphis.
Automatically fetches and sets up backend tools and AI neural models
(realesrgan-ncnn-vulkan + models) if not found on the host system.
"""

import os
import sys
import shutil
import zipfile
import tarfile
import urllib.request
from pathlib import Path
from typing import Optional, Callable
from PyQt6.QtCore import QThread, pyqtSignal

# Local user app data directory for storing downloaded tools and models
LOCAL_TOOLS_DIR = Path.home() / ".local" / "share" / "delphis" / "bin"
REALESRGAN_RELEASE_URL = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip"

def get_local_tools_dir() -> Path:
    """Ensure and return the local tools directory."""
    LOCAL_TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    return LOCAL_TOOLS_DIR

def is_tool_locally_available(tool_name: str) -> bool:
    """Check if the tool executable exists in the local tools directory."""
    target = LOCAL_TOOLS_DIR / tool_name
    return target.is_file() and os.access(target, os.X_OK)

class ToolDownloaderWorker(QThread):
    """
    Background worker for downloading and extracting required tools and AI models.
    """
    progress = pyqtSignal(int, int, str)  # (downloaded_bytes, total_bytes, message)
    output_line = pyqtSignal(str, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        tools_dir = get_local_tools_dir()
        zip_path = tools_dir / "realesrgan_bundle.zip"

        self.output_line.emit(f"Starting download of Real-ESRGAN and AI models to {tools_dir}...", "info")

        try:
            # Download file with progress report
            req = urllib.request.Request(
                REALESRGAN_RELEASE_URL,
                headers={"User-Agent": "Delphis/1.0"}
            )

            with urllib.request.urlopen(req, timeout=30) as response, open(zip_path, "wb") as out_file:
                total_size = int(response.info().get("Content-Length", 0))
                downloaded = 0
                block_size = 1024 * 64

                while True:
                    if self._is_cancelled:
                        self.finished.emit(False, "Download cancelled by user.")
                        return

                    buffer = response.read(block_size)
                    if not buffer:
                        break

                    downloaded += len(buffer)
                    out_file.write(buffer)

                    pct = int((downloaded / total_size) * 100) if total_size > 0 else 0
                    msg = f"Downloading AI models: {downloaded // 1024 // 1024}MB / {total_size // 1024 // 1024}MB ({pct}%)"
                    self.progress.emit(downloaded, total_size, msg)

            self.output_line.emit("Extracting Real-ESRGAN executable and AI neural models...", "info")

            # Extract zip
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tools_dir)

            # Make binary executable
            binary_path = tools_dir / "realesrgan-ncnn-vulkan"
            if binary_path.exists():
                binary_path.chmod(0o755)

            # Clean zip archive
            if zip_path.exists():
                zip_path.unlink()

            success_msg = f"Real-ESRGAN and models installed successfully into {tools_dir}."
            self.output_line.emit(f"[SUCCESS] {success_msg}", "success")
            self.finished.emit(True, success_msg)

        except Exception as e:
            err_msg = f"Failed to download tools: {e}"
            self.output_line.emit(f"[ERROR] {err_msg}", "error")
            self.finished.emit(False, err_msg)
