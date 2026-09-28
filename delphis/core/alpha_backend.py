"""
Alpha & Transparency Backend Engine for Delphis.
High-performance 4-channel (RGBa) image processor for adjusting and removing alpha transparency,
preserving anti-aliased sub-pixel gradients, defringing color halos, and batch processing.
"""

from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image, ImageColor, ImageFilter
from delphis.core.runner import BaseWorker
from delphis.constants import SUPPORTED_IMAGE_EXTENSIONS

def parse_color(color_str: str) -> Optional[Tuple[int, int, int]]:
    """Parse color string into RGB tuple (e.g. 'white', 'black', '#ffffff')."""
    if not color_str:
        return None
    try:
        return ImageColor.getrgb(color_str)[:3]
    except Exception:
        return None

def defringe_rgb_channels(
    r: Image.Image,
    g: Image.Image,
    b: Image.Image,
    a: Image.Image
) -> Tuple[Image.Image, Image.Image, Image.Image]:
    """
    Defringe RGB channels around semi-transparent edges to eliminate dark/light halos.
    Unmultiplies color channels using alpha weight.
    """
    def unmultiply_channel(c_img: Image.Image, a_img: Image.Image) -> Image.Image:
        c_bytes = c_img.tobytes()
        a_bytes = a_img.tobytes()
        out = bytearray(len(c_bytes))
        for i in range(len(c_bytes)):
            alpha = a_bytes[i]
            if alpha == 255:
                out[i] = c_bytes[i]
            elif alpha > 0:
                out[i] = min(255, int(round((c_bytes[i] * 255.0) / alpha)))
            else:
                out[i] = c_bytes[i]
        return Image.frombytes("L", c_img.size, bytes(out))

    return (
        unmultiply_channel(r, a),
        unmultiply_channel(g, a),
        unmultiply_channel(b, a)
    )

def smooth_alpha_channel(a: Image.Image, radius: float = 1.0) -> Image.Image:
    """Apply edge anti-aliasing / smoothing filter to alpha channel."""
    return a.filter(ImageFilter.GaussianBlur(radius=radius))

def process_single_image(
    input_path: Path,
    output_path: Path,
    remove_alpha: bool = False,
    alpha_value: Optional[int] = None,
    scale_alpha: bool = True,
    smooth: bool = False,
    smooth_radius: float = 1.0,
    defringe: bool = False,
    background_color: Optional[Tuple[int, int, int]] = None
) -> Tuple[bool, str]:
    """Process a single image file with 4-channel separation and recombining."""
    try:
        with Image.open(input_path) as img:
            img_rgba = img.convert("RGBA")
            r, g, b, a = img_rgba.split()

            if remove_alpha:
                if background_color is not None:
                    bg = Image.new("RGB", img.size, background_color)
                    bg.paste(img_rgba, mask=a)
                    result = bg
                else:
                    result = img.convert("RGB")
            elif alpha_value is not None:
                if defringe:
                    r, g, b = defringe_rgb_channels(r, g, b, a)

                factor = alpha_value / 255.0
                if scale_alpha:
                    new_a = a.point(lambda p: int(round(p * factor)))
                else:
                    new_a = a.point(lambda p: alpha_value if p > 0 else 0)

                if smooth:
                    new_a = smooth_alpha_channel(new_a, radius=smooth_radius)

                result = Image.merge("RGBA", (r, g, b, new_a))
            else:
                result = img

            output_path.parent.mkdir(parents=True, exist_ok=True)
            save_kwargs = {}
            if output_path.suffix.lower() == ".png":
                save_kwargs["optimize"] = True

            result.save(output_path, **save_kwargs)
            return True, f"Saved: {output_path.name}"
    except Exception as e:
        return False, f"Failed: {input_path.name} -> {e}"

class AlphaWorker(BaseWorker):
    """
    Worker for batch or single image alpha transparency processing.
    """
    def __init__(
        self,
        input_path: str,
        output_path: str,
        remove_alpha: bool = False,
        alpha_value: int = 255,
        scale_alpha: bool = True,
        smooth: bool = False,
        smooth_radius: float = 1.0,
        defringe: bool = False,
        background_color: Optional[str] = None,
        recursive: bool = True,
        parent=None
    ):
        super().__init__(parent)
        self.input_path = input_path
        self.output_path = output_path
        self.remove_alpha = remove_alpha
        self.alpha_value = alpha_value
        self.scale_alpha = scale_alpha
        self.smooth = smooth
        self.smooth_radius = smooth_radius
        self.defringe = defringe
        self.background_color = parse_color(background_color) if background_color else None
        self.recursive = recursive

    def run(self):
        self.signals.started.emit()
        in_p = Path(self.input_path)
        out_p = Path(self.output_path)

        if not in_p.exists():
            msg = f"Input path does not exist: {self.input_path}"
            self.log(f"[ERROR] {msg}", "error")
            self.signals.finished.emit(False, msg)
            return

        # Collect target images
        if in_p.is_file():
            images = [in_p]
        else:
            pattern = "**/*" if self.recursive else "*"
            images = [
                p for p in in_p.glob(pattern)
                if p.is_file() and p.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
            ]

        total = len(images)
        if total == 0:
            msg = f"No supported images found in '{self.input_path}'."
            self.log(f"[WARNING] {msg}", "warning")
            self.signals.finished.emit(False, msg)
            return

        action_desc = "Removing Alpha (RGBA -> RGB)" if self.remove_alpha else f"Adjusting Alpha to {self.alpha_value}/255"
        self.log(f"Alpha Engine: Processing {total} file(s) [{action_desc}]...", "info")

        is_single_file_mode = in_p.is_file() and (not out_p.exists() or out_p.is_file()) and (out_p.suffix != "")

        success_count = 0
        for idx, img_path in enumerate(images, 1):
            if self.is_cancelled:
                self.signals.finished.emit(False, "Operation cancelled by user.")
                return

            if is_single_file_mode:
                dest = out_p
            elif in_p.is_file():
                dest = out_p / img_path.name
            else:
                rel = img_path.relative_to(in_p)
                dest = out_p / rel

            ok, info = process_single_image(
                input_path=img_path,
                output_path=dest,
                remove_alpha=self.remove_alpha,
                alpha_value=self.alpha_value if not self.remove_alpha else None,
                scale_alpha=self.scale_alpha,
                smooth=self.smooth,
                smooth_radius=self.smooth_radius,
                defringe=self.defringe,
                background_color=self.background_color
            )

            if ok:
                success_count += 1
                self.log(f"[OK] {img_path.name} -> {dest.name}", "success")
            else:
                self.log(f"[ERROR] {info}", "error")

            self.set_progress(idx, total)

        summary = f"Alpha Processing complete: {success_count}/{total} images processed successfully."
        self.log(summary, "success" if success_count == total else "warning")
        self.signals.finished.emit(success_count == total, summary)
