"""
DolphinTextureExtraction-tool (DTE) Backend Worker for Delphis.
Handles texture extraction, tonemap reconstruction (CombineRGBA / CombineBGRA),
and splitting high-res textures back into Dolphin-compatible tonemaps (Finalize).
"""

import os
import shlex
from pathlib import Path
from typing import List, Optional
from delphis.core.runner import BaseWorker
from delphis.core.env_check import find_executable

class DTEWorker(BaseWorker):
    """
    Worker for orchestrating DolphinTextureExtraction-tool commands with correct verb syntax.
    """
    def __init__(
        self,
        input_path: str,
        output_path: str,
        mode: str = "merge_rgba",  # "merge_rgba", "merge_bgra", "split_tonemaps", "extract", "unpack", "custom"
        tasks: int = 1,
        recursive: bool = True,
        extract_mipmaps: bool = False,
        dolphin_mip_detection: bool = True,
        cleanup_mode: str = "none",  # "none", "simple", "default", "compact"
        custom_command: str = "Extract",
        extra_args: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.input_path = input_path
        self.output_path = output_path
        self.mode = mode
        self.tasks = tasks
        self.recursive = recursive
        self.extract_mipmaps = extract_mipmaps
        self.dolphin_mip_detection = dolphin_mip_detection
        self.cleanup_mode = cleanup_mode
        self.custom_command = custom_command
        self.extra_args = extra_args

    def run(self):
        self.signals.started.emit()
        self.log(f"Starting DTE Task: Mode = {self.mode}", "info")

        dte_bin = find_executable("dte") or find_executable("DolphinTextureExtraction.tool")
        if not dte_bin:
            msg = "DolphinTextureExtraction-tool executable ('dte' or 'DolphinTextureExtraction.tool') was not found in PATH."
            self.log(f"[ERROR] {msg}", "error")
            self.signals.finished.emit(False, msg)
            return

        in_p = Path(self.input_path)
        out_p = Path(self.output_path)

        if not in_p.exists():
            msg = f"Input path does not exist: {self.input_path}"
            self.log(f"[ERROR] {msg}", "error")
            self.signals.finished.emit(False, msg)
            return

        out_p.mkdir(parents=True, exist_ok=True)

        cmd = [dte_bin]

        # 1. First argument must be the DTE Command Verb
        if self.mode == "merge_rgba":
            cmd.append("CombineRGBA")
            self.log("Action: CombineRGBA (Searching texture pairs and merging into RGBA)...", "info")
        elif self.mode == "merge_bgra":
            cmd.append("CombineBGRA")
            self.log("Action: CombineBGRA (Searching texture pairs and merging into BGRA)...", "info")
        elif self.mode == "split_tonemaps":
            cmd.append("Finalize")
            self.log("Action: Finalize (Separating combined textures & optimizing for Dolphin)...", "info")
        elif self.mode == "extract":
            cmd.append("Extract")
            self.log("Action: Extract (Dumping textures with Dolphin texture hash)...", "info")
        elif self.mode == "unpack":
            cmd.append("Unpack")
            self.log("Action: Unpack (Unpacking game files/archives)...", "info")
        elif self.mode == "custom":
            cmd.append(self.custom_command if self.custom_command else "Extract")
            self.log(f"Action: Custom ({self.custom_command})...", "info")
        else:
            cmd.append("CombineRGBA")

        # 2. Input and Output Paths
        cmd.append(str(in_p))
        cmd.append(str(out_p))

        # 3. Standard Options and Flags
        if self.tasks > 0:
            cmd.extend(["-Tasks", str(self.tasks)])

        if self.cleanup_mode:
            cmd.append(f"-Cleanup:{self.cleanup_mode}")

        if self.recursive:
            cmd.extend(["-Recursiv", "0"])

        if self.extract_mipmaps:
            cmd.append("-Mip")

        if self.dolphin_mip_detection:
            cmd.append("-Dolphinmipdetection")

        if self.mode == "extract":
            cmd.append("-CombinedRGBA")

        # Extra flags
        if self.extra_args.strip():
            cmd.extend(shlex.split(self.extra_args.strip()))

        rc, output = self.run_subprocess(cmd)

        if self.is_cancelled:
            self.signals.finished.emit(False, "Task was cancelled.")
            return

        if rc == 0:
            msg = f"DTE operation finished successfully. Output saved to: {self.output_path}"
            self.log(f"[SUCCESS] {msg}", "success")
            self.signals.finished.emit(True, msg)
        else:
            msg = f"DTE failed with exit code {rc}."
            self.log(f"[ERROR] {msg}", "error")
            self.signals.finished.emit(False, msg)
