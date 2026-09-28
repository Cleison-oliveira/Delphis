"""
Constants, Presets, and Configuration Definitions for Delphis.
"""

from typing import Dict, List, Tuple

APP_NAME = "Delphis"
APP_TITLE = "Delphis — Dolphin Texture Manipulation Tool"
APP_VERSION = "1.0.0"

# Supported Image Formats
SUPPORTED_IMAGE_EXTENSIONS = {
    ".png", ".webp", ".tga", ".bmp", ".tif", ".tiff", ".jpg", ".jpeg", ".dds"
}

PNG_EXTENSIONS = {".png"}

# DDS Compression Presets tailored for Dolphin Emulator
DDS_PRESETS: Dict[str, Dict[str, str]] = {
    "BC7": {
        "name": "BC7 (High Quality RGBA - Recommended)",
        "format": "BC7",
        "description": "State-of-the-art compression for color & smooth alpha. Best quality for modern HD texture packs in Dolphin.",
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
        "description": "Fast 1-bit transparency (binary cutout / decals).",
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

# Real-ESRGAN AI Models
AI_MODELS: List[Tuple[str, str]] = [
    ("realesrgan-x4plus-anime", "RealESRGAN x4plus Anime (Optimized for cel-shaded/anime GameCube & Wii textures)"),
    ("realesrgan-x4plus", "RealESRGAN x4plus (General purpose / realistic textures)"),
    ("realesrnet-x4plus", "RealESRNet x4plus (Alternative sharp reconstruction)"),
]

# Scale Factors
SCALE_FACTORS = [2, 3, 4]

# Alpha Processing Modes for AI Upscaler
ALPHA_UPSCALE_MODES = [
    ("ai", "AI Neural Upscaling (Preserves crisp edges & sub-pixel gradients)"),
    ("lanczos", "Lanczos Mathematical Resampling (Faster processing)")
]

# Quick Alpha Presets
ALPHA_QUICK_PRESETS = [
    (255, "255 (Opaque)"),
    (192, "192 (75%)"),
    (130, "130 (Dolphin Glass/UI)"),
    (64, "64 (25%)"),
    (0, "0 (Transparent)")
]
