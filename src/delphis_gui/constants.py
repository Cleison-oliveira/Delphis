"""
Delphis Constants and Presets for the Qt6 GUI.
Mirrors and interfaces with Delphis.Core C# definitions.
"""

from pathlib import Path
from typing import Dict, List, Tuple

def _load_app_version() -> str:
    candidates = [
        Path(__file__).resolve().parent / "VERSION",
        Path(__file__).resolve().parents[1] / "VERSION",
        Path(__file__).resolve().parents[2] / "VERSION",
    ]
    for c in candidates:
        if c.is_file():
            try:
                v = c.read_text(encoding="utf-8").strip()
                if v:
                    return v
            except Exception:
                pass
    return "1.0.0"

APP_NAME = "Delphis"
APP_TITLE = "Delphis — Dolphin Texture Manipulation Tool"
APP_VERSION = _load_app_version()

SUPPORTED_IMAGE_EXTENSIONS = {
    ".png", ".webp", ".tga", ".bmp", ".tif", ".tiff", ".jpg", ".jpeg", ".dds"
}

PNG_EXTENSIONS = {".png"}

IMAGE_FILE_FILTER = (
    "All Supported Images (*.png *.webp *.tga *.dds *.bmp *.jpg *.jpeg *.tif *.tiff);;"
    "PNG Images (*.png);;"
    "All Files (*)"
)

GAME_ARCHIVE_FILE_FILTER = (
    "Supported Game & Archive Files (*.iso *.rvz *.gcm *.wbfs *.cso *.wad *.tgc *.wia *.arc *.szs *.szp *.rarc *.u8 *.cpk *.afs *.pak *.bin *.dat *.brres *.bmd *.bdl *.tpl *.bti *.tga *.dds *.png);;"
    "Game Disc Images (*.iso *.rvz *.gcm *.wbfs *.cso *.wad *.tgc *.wia);;"
    "Game Archives (*.arc *.szs *.szp *.rarc *.u8 *.cpk *.afs *.pak *.bin *.dat *.brres);;"
    "All Files (*)"
)

DDS_PRESETS: Dict[str, Dict[str, any]] = {
    "BC7": {
        "name": "BC7 (High Quality RGBA - Recommended)",
        "format": "BC7",
        "description": "State-of-the-art block compression for color & smooth alpha. Best quality for modern HD texture packs in Dolphin.",
        "has_alpha": True,
        "is_default": True
    },
    "BC1": {
        "name": "BC1 / DXT1 (Opaque Textures - High Performance)",
        "format": "BC1",
        "description": "Smallest VRAM size for completely opaque textures without transparency.",
        "has_alpha": False,
        "is_default": False
    },
    "BC1a": {
        "name": "BC1a / DXT1 (1-Bit Punch-through Alpha)",
        "format": "BC1a",
        "description": "Fast 1-bit transparency (binary cutout / decals / foliage).",
        "has_alpha": True,
        "is_default": False
    },
    "BC3": {
        "name": "BC3 / DXT5 (Interpolated Alpha - Classic Compatibility)",
        "format": "BC3",
        "description": "Standard interpolated alpha channel compression with broad legacy compatibility.",
        "has_alpha": True,
        "is_default": False
    },
    "BC5": {
        "name": "BC5 (Two-Channel Normal / Bump Maps)",
        "format": "BC5",
        "description": "High fidelity compression specifically designed for tangent-space Normal Maps.",
        "has_alpha": False,
        "is_default": False
    }
}

AI_MODELS: List[Tuple[str, str]] = [
    ("realesrgan-x4plus-anime", "RealESRGAN x4plus Anime (Optimized for cel-shaded/anime GameCube & Wii textures)"),
    ("realesrgan-x4plus", "RealESRGAN x4plus (General purpose / realistic textures)"),
    ("realesr-animevideov3", "RealESR AnimeVideo v3 (Lightweight anime & cartoon textures)"),
]

SCALE_FACTORS = [2, 3, 4]

ALPHA_UPSCALE_MODES = [
    ("ai", "AI Neural Upscaling (Preserves crisp edges & sub-pixel gradients)"),
    ("lanczos", "Lanczos Mathematical Resampling (Faster processing)")
]

ALPHA_QUICK_PRESETS = [
    (255, "255 (Opaque)"),
    (192, "192 (75%)"),
    (130, "130 (Dolphin Glass/UI)"),
    (64, "64 (25%)"),
    (0, "0 (Transparent)")
]
