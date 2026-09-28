"""
4-Channel AI Upscaler Backend for Delphis.
Preserves alpha channel transparency by splitting into RGB + Alpha,
upscaling channels independently with Real-ESRGAN Vulkan NCNN, and cleanly recomposing.
"""

import os
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import List, Optional
from delphis.core.runner import BaseWorker
from delphis.core.env_check import find_executable
from delphis.core.downloader import LOCAL_TOOLS_DIR
from delphis.constants import PNG_EXTENSIONS

class UpscalerWorker(BaseWorker):
    """
    Worker for orchestrating 4-channel alpha-preserving Real-ESRGAN AI upscaling.
    """
    def __init__(
        self,
        input_path: str,
        output_path: str,
        scale: int = 4,
        model: str = "realesrgan-x4plus-anime",
        alpha_mode: str = "ai",  # 'ai' or 'lanczos'
        gpu_id: int = -1,         # -1 for auto-detect
        recursive: bool = True,
        parent=None
    ):
        super().__init__(parent)
        self.input_path = input_path
        self.output_path = output_path
        self.scale = scale
        self.model = model
        self.alpha_mode = alpha_mode
        self.gpu_id = gpu_id
        self.recursive = recursive

    def _auto_detect_gpu(self, realesrgan_bin: str, magick_bin: str, tmp_dir: Path, models_dir: Optional[str]) -> Tuple[int, str]:
        """Auto-detect the best discrete GPU device ID and name."""
        from delphis.core.env_check import detect_vulkan_gpus
        detected = [g for g in detect_vulkan_gpus() if g[0] >= 0]

        best_gpu = 0
        best_name = "Default Vulkan Device"
        best_score = -1

        for dev_id, name in detected:
            score = 10
            lower = name.lower()
            if "nvidia" in lower or "geforce" in lower or "rtx" in lower or "gtx" in lower:
                score = 100
            elif ("radeon" in lower or "amd" in lower) and "discrete" in lower:
                score = 85
            elif "discrete" in lower:
                score = 80
            elif "radeon" in lower or "amd" in lower:
                score = 50
            elif "intel" in lower:
                score = 30
            elif "llvmpipe" in lower or "cpu" in lower:
                score = 1

            if score > best_score:
                best_score = score
                best_gpu = dev_id
                best_name = name

        return best_gpu, best_name

    def _find_models_dir(self, realesrgan_bin: str) -> Optional[str]:
        """Locate the models directory for Real-ESRGAN."""
        bin_dir = Path(realesrgan_bin).parent
        candidates = [
            bin_dir / "models",
            bin_dir.parent / "share" / "realesrgan-ncnn-vulkan" / "models",
            bin_dir.parent / "share" / "Real-ESRGAN-ncnn-vulkan" / "models",
            LOCAL_TOOLS_DIR / "models"
        ]
        for c in candidates:
            if c.is_dir() and any(c.glob("*.bin")):
                return str(c)
        return None

    def run(self):
        self.signals.started.emit()
        in_p = Path(self.input_path)
        out_p = Path(self.output_path)

        realesrgan_bin = find_executable("realesrgan-ncnn-vulkan") or find_executable("realesrgan")
        magick_bin = find_executable("magick") or find_executable("convert")

        if not realesrgan_bin:
            msg = "Real-ESRGAN executable ('realesrgan-ncnn-vulkan') not found in PATH or local directory. Click 'Download Missing Tools' in the top bar."
            self.log(f"[ERROR] {msg}", "error")
            self.signals.finished.emit(False, msg)
            return

        if not magick_bin:
            msg = "ImageMagick executable ('magick' or 'convert') not found in PATH."
            self.log(f"[ERROR] {msg}", "error")
            self.signals.finished.emit(False, msg)
            return

        if not in_p.exists():
            msg = f"Input path does not exist: {self.input_path}"
            self.log(f"[ERROR] {msg}", "error")
            self.signals.finished.emit(False, msg)
            return

        # Locate models directory if needed
        models_dir = self._find_models_dir(realesrgan_bin)
        if models_dir:
            self.log(f"Using Real-ESRGAN models directory: {models_dir}", "info")

        # Collect images
        if in_p.is_file():
            images = [in_p]
        else:
            pattern = "**/*" if self.recursive else "*"
            images = [
                p for p in in_p.glob(pattern)
                if p.is_file() and p.suffix.lower() in PNG_EXTENSIONS
            ]

        total = len(images)
        if total == 0:
            msg = f"No PNG images found in '{self.input_path}'."
            self.log(f"[WARNING] {msg}", "warning")
            self.signals.finished.emit(False, msg)
            return

        tmp_dir = Path(tempfile.mkdtemp(prefix="delphis_upscale_"))
        try:
            active_gpu = self.gpu_id
            gpu_name = ""
            if active_gpu < 0:
                self.log("Detecting best Vulkan GPU device...", "info")
                active_gpu, gpu_name = self._auto_detect_gpu(realesrgan_bin, magick_bin, tmp_dir, models_dir)
                self.log(f"Selected GPU: {gpu_name} (Device ID: {active_gpu})", "info")
            else:
                from delphis.core.env_check import detect_vulkan_gpus
                gpu_dict = {d_id: d_name for d_id, d_name in detect_vulkan_gpus() if d_id >= 0}
                gpu_name = gpu_dict.get(active_gpu, f"GPU Device {active_gpu}")
                self.log(f"Selected GPU: {gpu_name} (Device ID: {active_gpu})", "info")

            self.log(f"AI Upscaler: Processing {total} file(s) [Scale: {self.scale}x | Model: {self.model} | Alpha: {self.alpha_mode}]...", "info")

            is_single_file_mode = in_p.is_file() and (not out_p.exists() or out_p.is_file()) and (out_p.suffix != "")

            success_count = 0
            for idx, img_path in enumerate(images, 1):
                if self.is_cancelled:
                    self.signals.finished.emit(False, "Operation cancelled by user.")
                    return

                stem = img_path.stem
                if is_single_file_mode:
                    dest = out_p
                elif in_p.is_file():
                    dest = out_p / f"{stem}.png"
                else:
                    rel = img_path.relative_to(in_p)
                    dest = out_p / rel.parent / f"{stem}.png"

                dest.parent.mkdir(parents=True, exist_ok=True)

                self.log(f"Upscaling ({idx}/{total}): {img_path.name} -> {dest.name}", "info")

                rgb_in = tmp_dir / f"{stem}_rgb_in.png"
                rgb_out = tmp_dir / f"{stem}_rgb_out.png"
                alpha_in = tmp_dir / f"{stem}_alpha_in.png"
                alpha_out = tmp_dir / f"{stem}_alpha_out.png"

                try:
                    # 1. Split RGB and Alpha without background blending
                    self.run_cmd([
                        magick_bin, str(img_path), "-alpha", "off", "-colorspace", "sRGB", "-depth", "8", f"PNG24:{rgb_in}"
                    ], check=True)

                    self.run_cmd([
                        magick_bin, str(img_path), "-alpha", "extract", "-colorspace", "gray", "-depth", "8", str(alpha_in)
                    ], check=True)

                    if self.is_cancelled:
                        self.signals.finished.emit(False, "Operation cancelled by user.")
                        return

                    # Build AI upscale command
                    ai_cmd_rgb = [realesrgan_bin, "-i", str(rgb_in), "-o", str(rgb_out), "-n", self.model, "-s", str(self.scale), "-g", str(active_gpu)]
                    if models_dir:
                        ai_cmd_rgb.extend(["-m", models_dir])

                    # 2. Upscale RGB with AI model (fallback to Lanczos if AI fails)
                    res_rgb = self.run_cmd(ai_cmd_rgb, check=False)
                    if self.is_cancelled:
                        self.signals.finished.emit(False, "Operation cancelled by user.")
                        return

                    if res_rgb.returncode != 0 or not rgb_out.exists():
                        self.log(f"  [!] AI upscale failed for RGB on {img_path.name}, falling back to Lanczos", "warning")
                        self.run_cmd([
                            magick_bin, str(rgb_in), "-filter", "Lanczos", "-resize", f"{self.scale}00%", str(rgb_out)
                        ], check=True)

                    if self.is_cancelled:
                        self.signals.finished.emit(False, "Operation cancelled by user.")
                        return

                    # 3. Upscale Alpha channel
                    if self.alpha_mode == "ai":
                        alpha_rgb_in = tmp_dir / f"{stem}_alpha_rgb_in.png"
                        alpha_rgb_out = tmp_dir / f"{stem}_alpha_rgb_out.png"
                        self.run_cmd([
                            magick_bin, str(alpha_in), "-type", "TrueColor", str(alpha_rgb_in)
                        ], check=True)

                        ai_cmd_alpha = [realesrgan_bin, "-i", str(alpha_rgb_in), "-o", str(alpha_rgb_out), "-n", self.model, "-s", str(self.scale), "-g", str(active_gpu)]
                        if models_dir:
                            ai_cmd_alpha.extend(["-m", models_dir])

                        res_alpha = self.run_cmd(ai_cmd_alpha, check=False)
                        if self.is_cancelled:
                            self.signals.finished.emit(False, "Operation cancelled by user.")
                            return

                        if res_alpha.returncode == 0 and alpha_rgb_out.exists():
                            self.run_cmd([
                                magick_bin, str(alpha_rgb_out), "-colorspace", "Gray", str(alpha_out)
                            ], check=True)
                        else:
                            self.log(f"  [!] AI upscale failed for Alpha on {img_path.name}, falling back to Lanczos", "warning")
                            self.run_cmd([
                                magick_bin, str(alpha_in), "-filter", "Lanczos", "-resize", f"{self.scale}00%", str(alpha_out)
                            ], check=True)
                    else:
                        self.run_cmd([
                            magick_bin, str(alpha_in), "-filter", "Lanczos", "-resize", f"{self.scale}00%", str(alpha_out)
                        ], check=True)

                    if self.is_cancelled:
                        self.signals.finished.emit(False, "Operation cancelled by user.")
                        return

                    # 4. Recomposite upscaled RGB and Alpha
                    self.run_cmd([
                        magick_bin, str(rgb_out), str(alpha_out), "-alpha", "off", "-compose", "CopyOpacity", "-composite", str(dest)
                    ], check=True)

                    success_count += 1
                    self.log(f"[OK] Upscaled: {dest.name}", "success")

                except InterruptedError:
                    self.signals.finished.emit(False, "Operation cancelled by user.")
                    return
                except Exception as ex:
                    if self.is_cancelled:
                        self.signals.finished.emit(False, "Operation cancelled by user.")
                        return
                    self.log(f"[ERROR] Failed upscaling {img_path.name}: {ex}", "error")
                finally:
                    for f in [rgb_in, rgb_out, alpha_in, alpha_out]:
                        if f.exists():
                            try:
                                f.unlink()
                            except Exception:
                                pass

                self.set_progress(idx, total)

            summary = f"AI Upscaling completed: {success_count}/{total} files successfully processed."
            self.log(summary, "success" if success_count == total else "warning")
            self.signals.finished.emit(success_count == total, summary)

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
