"""
Unit tests for Alpha & Transparency Backend Engine.
"""

from pathlib import Path
import pytest
from PIL import Image
from delphis.core.alpha_backend import (
    parse_color,
    defringe_rgb_channels,
    smooth_alpha_channel,
    process_single_image,
    AlphaWorker
)

def test_parse_color():
    assert parse_color("white") == (255, 255, 255)
    assert parse_color("#000000") == (0, 0, 0)
    assert parse_color("#ff0000") == (255, 0, 0)
    assert parse_color("") is None
    assert parse_color("invalid-color-12345") is None

def test_defringe_and_smooth():
    # Create test image with semi-transparent pixel
    img = Image.new("RGBA", (10, 10), (100, 150, 200, 128))
    r, g, b, a = img.split()

    r_out, g_out, b_out = defringe_rgb_channels(r, g, b, a)
    assert r_out.size == (10, 10)
    assert g_out.size == (10, 10)
    assert b_out.size == (10, 10)

    smooth_a = smooth_alpha_channel(a, radius=1.0)
    assert smooth_a.size == (10, 10)

def test_process_single_image_adjust_alpha(tmp_path: Path):
    in_img_path = tmp_path / "input.png"
    out_img_path = tmp_path / "output.png"

    # Create 4x4 test RGBA image with alpha=255
    img = Image.new("RGBA", (4, 4), (200, 100, 50, 255))
    img.save(in_img_path)

    # Adjust alpha to 130
    ok, msg = process_single_image(
        input_path=in_img_path,
        output_path=out_img_path,
        remove_alpha=False,
        alpha_value=130,
        scale_alpha=True,
        smooth=False,
        defringe=False
    )
    assert ok is True
    assert out_img_path.exists()

    with Image.open(out_img_path) as res:
        assert res.mode == "RGBA"
        pixel = res.getpixel((0, 0))
        assert pixel[3] == 130

def test_process_single_image_remove_alpha(tmp_path: Path):
    in_img_path = tmp_path / "input_trans.png"
    out_img_path = tmp_path / "output_opaque.png"

    img = Image.new("RGBA", (4, 4), (255, 0, 0, 128))
    img.save(in_img_path)

    # Remove alpha with white matte background
    ok, msg = process_single_image(
        input_path=in_img_path,
        output_path=out_img_path,
        remove_alpha=True,
        background_color=(255, 255, 255)
    )
    assert ok is True
    assert out_img_path.exists()

    with Image.open(out_img_path) as res:
        assert res.mode == "RGB"

def test_alpha_worker_batch(tmp_path: Path, qapp):
    input_dir = tmp_path / "input_dir"
    output_dir = tmp_path / "output_dir"
    input_dir.mkdir()

    for i in range(3):
        img = Image.new("RGBA", (8, 8), (10 * i, 20 * i, 30 * i, 255))
        img.save(input_dir / f"test_{i}.png")

    worker = AlphaWorker(
        input_path=str(input_dir),
        output_path=str(output_dir),
        remove_alpha=False,
        alpha_value=192,
        scale_alpha=True,
        smooth=True,
        smooth_radius=1.0,
        defringe=True,
        recursive=True
    )

    finished_events = []
    worker.signals.finished.connect(lambda ok, msg: finished_events.append((ok, msg)))

    worker.run()

    assert len(finished_events) == 1
    assert finished_events[0][0] is True
    assert (output_dir / "test_0.png").exists()
    assert (output_dir / "test_1.png").exists()
    assert (output_dir / "test_2.png").exists()
