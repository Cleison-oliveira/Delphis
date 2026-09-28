"""
Unit tests for DolphinTextureExtraction-tool (DTE) Backend Worker.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from delphis.core.dte_backend import DTEWorker

def test_dte_worker_command_composition(tmp_path: Path, qapp):
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    out_dir.mkdir()

    # Test CombineRGBA mode
    worker_rgba = DTEWorker(
        input_path=str(in_dir),
        output_path=str(out_dir),
        mode="merge_rgba",
        tasks=2,
        recursive=True,
        cleanup_mode="default",
        extract_mipmaps=False,
        dolphin_mip_detection=True
    )

    with patch("delphis.core.dte_backend.find_executable", return_value="/mock/bin/dte"):
        with patch.object(DTEWorker, "run_subprocess", return_value=(0, "mock success")) as mock_run:
            worker_rgba.run()
            mock_run.assert_called_once()
            called_cmd = mock_run.call_args[0][0]
            assert called_cmd[0] == "/mock/bin/dte"
            assert called_cmd[1] == "CombineRGBA"
            assert called_cmd[2] == str(in_dir)
            assert called_cmd[3] == str(out_dir)
            assert "-Tasks" in called_cmd
            assert "2" in called_cmd
            assert "-Cleanup:default" in called_cmd
            assert "-Recursiv" in called_cmd
            assert "-Dolphinmipdetection" in called_cmd

def test_dte_worker_finalize_and_extract_modes(tmp_path: Path, qapp):
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    out_dir.mkdir()

    # Test Finalize mode
    worker_split = DTEWorker(
        input_path=str(in_dir),
        output_path=str(out_dir),
        mode="split_tonemaps"
    )

    with patch("delphis.core.dte_backend.find_executable", return_value="/mock/bin/dte"):
        with patch.object(DTEWorker, "run_subprocess", return_value=(0, "ok")) as mock_run:
            worker_split.run()
            assert mock_run.call_args[0][0][1] == "Finalize"

    # Test Extract mode
    worker_extract = DTEWorker(
        input_path=str(in_dir),
        output_path=str(out_dir),
        mode="extract"
    )

    with patch("delphis.core.dte_backend.find_executable", return_value="/mock/bin/dte"):
        with patch.object(DTEWorker, "run_subprocess", return_value=(0, "ok")) as mock_run:
            worker_extract.run()
            called_cmd = mock_run.call_args[0][0]
            assert called_cmd[1] == "Extract"
            assert "-CombinedRGBA" in called_cmd
