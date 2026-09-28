"""
Base Worker and Subprocess Runner for Delphis.
Provides asynchronous execution using QThread with signals for stdout streaming,
progress tracking, cancellation, and error handling.
"""

import sys
import subprocess
import threading
from typing import List, Optional, Tuple, Callable
from PyQt6.QtCore import QObject, QThread, pyqtSignal

class WorkerSignals(QObject):
    """Signals emitted by background worker operations."""
    started = pyqtSignal()
    output_line = pyqtSignal(str, str)  # (message, level: 'info' | 'success' | 'warning' | 'error')
    progress = pyqtSignal(int, int)     # (current, total)
    finished = pyqtSignal(bool, str)    # (success, summary_message)
    cancelled = pyqtSignal()

class BaseWorker(QThread):
    """
    Base worker class for executing background operations without freezing the Qt GUI.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.signals = WorkerSignals()
        self._is_cancelled = False
        self._current_process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    def cancel(self):
        """Request cancellation of the running operation."""
        self._is_cancelled = True
        with self._lock:
            if self._current_process and self._current_process.poll() is None:
                try:
                    self._current_process.terminate()
                    threading.Timer(0.5, self._force_kill_process).start()
                except Exception:
                    pass
        self.signals.cancelled.emit()
        self.signals.output_line.emit("Operation cancelled by user.", "warning")

    def _force_kill_process(self):
        with self._lock:
            if self._current_process and self._current_process.poll() is None:
                try:
                    self._current_process.kill()
                except Exception:
                    pass

    @property
    def is_cancelled(self) -> bool:
        return self._is_cancelled

    def log(self, message: str, level: str = "info"):
        """Emit a log message signal to the GUI console."""
        self.signals.output_line.emit(message, level)

    def set_progress(self, current: int, total: int):
        """Emit a progress update signal."""
        self.signals.progress.emit(current, total)

    def run_cmd(
        self,
        cmd: List[str],
        check: bool = True,
        cwd: Optional[str] = None,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    ) -> subprocess.CompletedProcess:
        """
        Run a subprocess command, register it for instant termination on cancel,
        and raise InterruptedError immediately if cancelled.
        """
        if self._is_cancelled:
            raise InterruptedError("Operation cancelled by user.")

        proc = subprocess.Popen(cmd, cwd=cwd, stdout=stdout, stderr=stderr)
        with self._lock:
            self._current_process = proc

        try:
            out, err = proc.communicate()
            if self._is_cancelled:
                raise InterruptedError("Operation cancelled by user.")
            if check and proc.returncode != 0:
                raise subprocess.CalledProcessError(proc.returncode, cmd, output=out, stderr=err)
            return subprocess.CompletedProcess(cmd, proc.returncode, out, err)
        except Exception:
            if self._is_cancelled:
                raise InterruptedError("Operation cancelled by user.")
            raise
        finally:
            with self._lock:
                if self._current_process is proc:
                    self._current_process = None

    def run_subprocess(self, cmd: List[str], cwd: Optional[str] = None) -> Tuple[int, str]:
        """
        Run a subprocess command, stream output line by line, and handle cancellation.
        """
        if self._is_cancelled:
            return -1, "Cancelled before start"

        cmd_str = " ".join(cmd)
        self.log(f"$ {cmd_str}", "info")

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            with self._lock:
                self._current_process = proc

            output_lines = []
            while True:
                if self._is_cancelled:
                    with self._lock:
                        if self._current_process and self._current_process.poll() is None:
                            self._current_process.terminate()
                    return -1, "Cancelled"

                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    clean_line = line.rstrip()
                    output_lines.append(clean_line)

                    # Highlight logs based on keywords
                    lower = clean_line.lower()
                    if "error" in lower or "fail" in lower or "fatal" in lower:
                        self.log(clean_line, "error")
                    elif "warning" in lower or "[!]" in lower:
                        self.log(clean_line, "warning")
                    elif "success" in lower or "done" in lower or "[ok]" in lower or "[+]" in lower:
                        self.log(clean_line, "success")
                    else:
                        self.log(clean_line, "info")

            rc = proc.wait()
            with self._lock:
                if self._current_process is proc:
                    self._current_process = None
            return rc, "\n".join(output_lines)

        except Exception as e:
            with self._lock:
                self._current_process = None
            self.log(f"Process execution error: {e}", "error")
            return -1, str(e)
