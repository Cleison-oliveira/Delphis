"""
Unit tests for DDS Texture Optimizer Backend.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess
import pytest
from delphis.core.dds_backend import DDSWorker

def test_dds_worker_nvcompress_conversion(tmp_path: Path, qapp):
    in_file = tmp_path / "texture.png"
    out_file = tmp_path / "texture.dds"
    in_file.write_bytes(b"dummy")

    worker = DDSWorker(
        input_path=str(in_file),
        output_path=str(out_file),
        preset="BC7",
        generate_mipmaps=True
    )

    with patch.object(DDSWorker, "run_cmd") as mock_run_cmd:
        # Create output file to simulate successful conversion
        def side_effect(cmd, check=False):
            out_file.write_bytes(b"dds_data")
            return subprocess.CompletedProcess(cmd, 0)

        mock_run_cmd.side_effect = side_effect

        ok = worker._convert_single(in_file, out_file, "nvcompress", "/mock/nvcompress")
        assert ok is True
        mock_run_cmd.assert_called_once()
        cmd = mock_run_cmd.call_args[0][0]
        assert cmd[0] == "/mock/nvcompress"
        assert "-bc7" in cmd
        assert "-mip" in cmd

def test_dds_worker_presets(tmp_path: Path, qapp):
    in_file = tmp_path / "texture.png"
    out_file = tmp_path / "texture.dds"
    in_file.write_bytes(b"dummy")

    presets = [
        ("BC1", "-bc1"),
        ("BC1a", "-bc1a"),
        ("BC3", "-bc3"),
        ("BC5", "-bc5"),
    ]

    for preset_name, expected_flag in presets:
        worker = DDSWorker(
            input_path=str(in_file),
            output_path=str(out_file),
            preset=preset_name,
            generate_mipmaps=False
        )
        with patch.object(DDSWorker, "run_cmd") as mock_run:
            def side_effect(cmd, check=False):
                out_file.write_bytes(b"dds_data")
                return subprocess.CompletedProcess(cmd, 0)

            mock_run.side_effect = side_effect
            ok = worker._convert_single(in_file, out_file, "nvcompress", "/mock/nvcompress")
            assert ok is True
            cmd = mock_run.call_args[0][0]
            assert expected_flag in cmd
            assert "-nomip" in cmd
