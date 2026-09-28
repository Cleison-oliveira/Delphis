"""
DDS Texture Optimizer Backend for Delphis.
Converts textures to hardware-accelerated .dds (DirectDraw Surface) format using
community-recommended Dolphin emulator compression presets (BC7, BC1, BC1a, BC3, BC5)
and automatic Mipmap generation to maximize emulator performance and reduce VRAM footprint.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple
from delphis.core.runner import BaseWorker
from delphis.core.env_check import find_executable
from delphis.constants import SUPPORTED_IMAGE_EXTENSIONS

class DDSWorker(BaseWorker):
    """
    Worker for batch converting and optimizing images into DDS format.
    """
    def __init__(
        self,
        input_path: str,
        output_path: str,
        preset: str = "BC7",
        generate_mipmaps: bool = True,
        recursive: bool = True,
        parent=None
    ):
        super().__init__(parent)
        self.input_path = input_path
        self.output_path = output_path
        self.preset = preset
        self.generate_mipmaps = generate_mipmaps
        self.recursive = recursive

    def _convert_single(
        self,
        src: Path,
        dest: Path,
        encoder_type: str,
        encoder_bin: str
    ) -> bool:
        """Convert a single image to DDS using the detected encoder."""
        dest.parent.mkdir(parents=True, exist_ok=True)

        if encoder_type == "nvcompress":
            cmd = [encoder_bin]
            if self.preset == "BC7":
                cmd.append("-bc7")
            elif self.preset == "BC1":
                cmd.append("-bc1")
            elif self.preset == "BC1a":
                cmd.append("-bc1a")
            elif self.preset == "BC3":
                cmd.append("-bc3")
            elif self.preset == "BC5":
                cmd.append("-bc5")
            else:
                cmd.append("-bc7")

            if self.generate_mipmaps:
                cmd.append("-mip")
            else:
                cmd.append("-nomip")

            cmd.extend([str(src), str(dest)])
            res = self.run_cmd(cmd, check=False)
            return res.returncode == 0 and dest.exists()

        elif encoder_type == "texconv":
            # texconv accepts -f format -m mipmaps -o outdir src
            fmt = "BC7_UNORM"
            if self.preset == "BC1":
                fmt = "BC1_UNORM"
            elif self.preset == "BC3":
                fmt = "BC3_UNORM"
            elif self.preset == "BC5":
                fmt = "BC5_UNORM"

            cmd = [encoder_bin, "-y", "-f", fmt]
            if self.generate_mipmaps:
                cmd.extend(["-m", "0"])
            else:
                cmd.extend(["-m", "1"])
            cmd.extend(["-o", str(dest.parent), str(src)])

            res = self.run_cmd(cmd, check=False)
            # texconv names output same as input but with .dds
            expected = dest.parent / f"{src.stem}.DDS"
            if not dest.exists() and expected.exists():
                expected.rename(dest)
            return dest.exists()

        elif encoder_type == "compressonator":
            fmt = "BC7" if self.preset not in ["BC1", "BC3", "BC5"] else self.preset
            cmd = [encoder_bin, "-fd", fmt]
            if self.generate_mipmaps:
                cmd.extend(["-miplevels", "0"])
            cmd.extend([str(src), str(dest)])
            res = self.run_cmd(cmd, check=False)
            return res.returncode == 0 and dest.exists()

        elif encoder_type == "magick":
            # ImageMagick fallback
            compression = "dxt5"
            if self.preset in ["BC1", "BC1a"]:
                compression = "dxt1"
            elif self.preset == "BC3":
                compression = "dxt5"
            elif self.preset == "BC7":
                compression = "none"

            cmd = [encoder_bin, str(src), "-define", f"dds:compression={compression}"]
            if self.generate_mipmaps:
                cmd.extend(["-define", "dds:mipmaps=0"])
            cmd.append(str(dest))

            res = self.run_cmd(cmd, check=False)
            return res.returncode == 0 and dest.exists()

        return False

    def run(self):
        self.signals.started.emit()
        in_p = Path(self.input_path)
        out_p = Path(self.output_path)

        # Detect best available encoder
        encoder_type = None
        encoder_bin = None

        if find_executable("nvcompress"):
            encoder_type = "nvcompress"
            encoder_bin = find_executable("nvcompress")
        elif find_executable("texconv"):
            encoder_type = "texconv"
            encoder_bin = find_executable("texconv")
        elif find_executable("compressonatorcli"):
            encoder_type = "compressonator"
            encoder_bin = find_executable("compressonatorcli")
        elif find_executable("magick"):
            encoder_type = "magick"
            encoder_bin = find_executable("magick")
        elif find_executable("convert"):
            encoder_type = "magick"
            encoder_bin = find_executable("convert")

        if not encoder_bin:
            msg = "No DDS encoder found (Install 'nvidia-texture-tools', 'texconv', 'compressonator', or 'imagemagick')."
            self.log(f"[ERROR] {msg}", "error")
            self.signals.finished.emit(False, msg)
            return

        self.log(f"Using DDS Encoder: {encoder_type} ({encoder_bin})", "info")

        if not in_p.exists():
            msg = f"Input path does not exist: {self.input_path}"
            self.log(f"[ERROR] {msg}", "error")
            self.signals.finished.emit(False, msg)
            return

        # Collect images
        if in_p.is_file():
            images = [in_p]
        else:
            pattern = "**/*" if self.recursive else "*"
            images = [
                p for p in in_p.glob(pattern)
                if p.is_file() and p.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS and p.suffix.lower() != ".dds"
            ]

        total = len(images)
        if total == 0:
            msg = f"No eligible image files found in '{self.input_path}'."
            self.log(f"[WARNING] {msg}", "warning")
            self.signals.finished.emit(False, msg)
            return

        self.log(f"DDS Optimizer: Converting {total} file(s) [Preset: {self.preset} | Mipmaps: {self.generate_mipmaps}]...", "info")

        is_single_file_mode = in_p.is_file() and (not out_p.exists() or out_p.is_file()) and (out_p.suffix != "")

        success_count = 0
        for idx, img_path in enumerate(images, 1):
            if self.is_cancelled:
                self.signals.finished.emit(False, "Operation cancelled by user.")
                return

            stem = img_path.stem
            if is_single_file_mode:
                dest = out_p.with_suffix(".dds")
            elif in_p.is_file():
                dest = out_p / f"{stem}.dds"
            else:
                rel = img_path.relative_to(in_p)
                dest = out_p / rel.parent / f"{stem}.dds"

            ok = self._convert_single(img_path, dest, encoder_type, encoder_bin)
            if ok:
                success_count += 1
                self.log(f"[OK] {img_path.name} -> {dest.name}", "success")
            else:
                self.log(f"[ERROR] Failed converting {img_path.name}", "error")

            self.set_progress(idx, total)

        summary = f"DDS Optimization complete: {success_count}/{total} files converted to {self.preset} DDS."
        self.log(summary, "success" if success_count == total else "warning")
        self.signals.finished.emit(success_count == total, summary)
