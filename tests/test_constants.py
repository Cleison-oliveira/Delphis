"""
Tests for constants and configuration presets.
"""

import pytest
from delphis.constants import (
    APP_NAME,
    APP_VERSION,
    SUPPORTED_IMAGE_EXTENSIONS,
    PNG_EXTENSIONS,
    DDS_PRESETS,
    AI_MODELS,
    SCALE_FACTORS,
    ALPHA_UPSCALE_MODES,
    ALPHA_QUICK_PRESETS,
)

def test_app_metadata():
    assert APP_NAME == "Delphis"
    assert isinstance(APP_VERSION, str)
    assert len(APP_VERSION) > 0

def test_supported_extensions():
    assert ".png" in SUPPORTED_IMAGE_EXTENSIONS
    assert ".dds" in SUPPORTED_IMAGE_EXTENSIONS
    assert ".webp" in SUPPORTED_IMAGE_EXTENSIONS
    assert ".png" in PNG_EXTENSIONS

def test_dds_presets():
    required_presets = ["BC7", "BC1", "BC1a", "BC3", "BC5"]
    for p in required_presets:
        assert p in DDS_PRESETS
        preset = DDS_PRESETS[p]
        assert "name" in preset
        assert "format" in preset
        assert "description" in preset
        assert "has_alpha" in preset

    # BC7 should be default
    assert DDS_PRESETS["BC7"]["is_default"] is True

def test_ai_models():
    assert len(AI_MODELS) >= 3
    model_ids = [m[0] for m in AI_MODELS]
    assert "realesrgan-x4plus-anime" in model_ids
    assert "realesrgan-x4plus" in model_ids
    assert "realesrnet-x4plus" in model_ids

def test_scale_factors():
    assert SCALE_FACTORS == [2, 3, 4]

def test_alpha_quick_presets():
    values = [p[0] for p in ALPHA_QUICK_PRESETS]
    assert 255 in values
    assert 192 in values
    assert 130 in values
    assert 64 in values
    assert 0 in values
