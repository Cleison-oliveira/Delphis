"""
Asynchronous Process Bridge & Worker Subsystem connecting PyQt6 to Delphis C# Engine.
"""

import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import List, Optional, Tuple
from PyQt6.QtCore import QObject, QThread, pyqtSignal

class WorkerSignals(QObject):
    """Signals emitted by asynchronous workers to update the GUI."""
    started = pyqtSignal()
    output_line = pyqtSignal(str, str)  # (message, level: 'info' | 'success' | 'warning' | 'error')
    progress = pyqtSignal(int, int)     # (current, total)
    finished = pyqtSignal(bool, str)    # (success, summary_message)
    cancelled = pyqtSignal()

def detect_vulkan_gpus() -> List[Tuple[int, str]]:
    """Detect available Vulkan GPU devices via vulkaninfo or fallback."""
    gpus: List[Tuple[int, str]] = []
    vulkaninfo = shutil.which("vulkaninfo")
    if vulkaninfo:
        try:
            output = subprocess.check_output([vulkaninfo, "--summary"], text=True, stderr=subprocess.DEVNULL)
            import re
            # Matches lines like: GPU0: ... deviceName = NVIDIA GeForce RTX 3080
            for match in re.finditer(r'GPU(\d+):\s*[\r\n]+(?:\s+.*\n)*?\s+deviceName\s*=\s*(.+)', output):
                dev_id = int(match.group(1))
                dev_name = match.group(2).strip()
                gpus.append((dev_id, f"GPU {dev_id}: {dev_name}"))
        except Exception:
            pass

    if not gpus:
        gpus.append((0, "GPU 0: Default Vulkan Graphics Device"))
    return gpus

def find_delphis_cli() -> str:
    """Finds the delphis-cli binary or dotnet run fallback."""
    # 1. Check system PATH
    cli = shutil.which("delphis-cli")
    if cli:
        return cli

    # 2. Check local publish / bin folder
    repo_root = Path(__file__).resolve().parent.parent.parent
    local_candidates = [
        repo_root / "src" / "Delphis.Cli" / "bin" / "Release" / "net8.0" / "delphis-cli",
        repo_root / "src" / "Delphis.Cli" / "bin" / "Debug" / "net8.0" / "delphis-cli",
        repo_root / "result" / "bin" / "delphis-cli"
    ]
    for c in local_candidates:
        if c.is_file() and os.access(c, os.X_OK):
            return str(c)

    # 3. Default to delphis-cli in PATH
    return "delphis-cli"

class CSharpCommandWorker(QThread):
    """
    Asynchronous QThread executing Delphis C# commands without blocking the Qt event loop.
    """
    def __init__(self, command_args: List[str], quiet: bool = False, parent=None):
        super().__init__(parent)
        self.signals = WorkerSignals()
        self.command_args = list(command_args)
        self.quiet = quiet
        self._is_cancelled = False
        self._current_process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

        if self.quiet and "--quiet" not in self.command_args and "-q" not in self.command_args and "--no-logs" not in self.command_args:
            self.command_args = ["--quiet"] + self.command_args

    def cancel(self):
        """Cancel running subprocess."""
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

    def run(self):
        self.signals.started.emit()

        cli_bin = find_delphis_cli()
        cmd = [cli_bin] + self.command_args

        if not self.quiet:
            cmd_str = " ".join(cmd)
            self.signals.output_line.emit(f"$ {cmd_str}", "info")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            with self._lock:
                self._current_process = proc

            import re
            while True:
                if self._is_cancelled:
                    with self._lock:
                        if self._current_process and self._current_process.poll() is None:
                            self._current_process.terminate()
                    self.signals.finished.emit(False, "Task cancelled by user.")
                    return

                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    clean_line = line.rstrip()

                    # 1. Parse DTE percentage progress bar: e.g. "│█████████████▓ │ 34.76%"
                    pct_match = re.search(r'│.*│\s*(\d+(?:\.\d+)?)%', clean_line)
                    if pct_match:
                        try:
                            pct_val = int(float(pct_match.group(1)))
                            self.signals.progress.emit(pct_val, 100)
                            continue  # Do not dump raw progress bar lines to console log
                        except ValueError:
                            pass

                    # 2. Parse ratio progress: e.g. "(5/20)" or "5/20"
                    match_prog = re.search(r'\(?(\d+)/(\d+)\)?', clean_line)
                    if match_prog:
                        try:
                            cur = int(match_prog.group(1))
                            tot = int(match_prog.group(2))
                            self.signals.progress.emit(cur, tot)
                        except ValueError:
                            pass

                    # 3. Classify log level
                    lower = clean_line.lower()
                    level = "info"
                    if "error" in lower or "fail" in lower or "fatal" in lower:
                        level = "error"
                    elif "warning" in lower or "[!]" in lower:
                        level = "warning"
                    elif "success" in lower or "done" in lower or "[ok]" in lower or "✔" in clean_line:
                        level = "success"

                    # 4. Emit log line unless in quiet mode
                    if not self.quiet or level in ("error", "warning"):
                        self.signals.output_line.emit(clean_line, level)

            rc = proc.wait()
            with self._lock:
                self._current_process = None

            success = (rc == 0) and not self._is_cancelled
            msg = "Operation completed successfully." if success else f"Process exited with code {rc}."
            self.signals.finished.emit(success, msg)

        except Exception as e:
            with self._lock:
                self._current_process = None
            self.signals.output_line.emit(f"[FATAL] Error running command: {e}", "error")
            self.signals.finished.emit(False, str(e))
