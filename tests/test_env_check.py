"""
Unit tests for Environment and Dependency Checker.
"""

from unittest.mock import patch, MagicMock
import subprocess
import pytest
from delphis.core.env_check import (
    find_executable,
    check_dependencies,
    detect_vulkan_gpus
)

def test_find_executable():
    with patch("shutil.which", return_value="/usr/bin/echo"):
        assert find_executable("echo") == "/usr/bin/echo"

def test_check_dependencies():
    with patch("delphis.core.env_check.find_executable", return_value="/usr/bin/mock_tool"):
        deps = check_dependencies()
        assert "dte" in deps
        assert "realesrgan" in deps
        assert "magick" in deps
        assert "dds_tool" in deps
        assert deps["dte"]["installed"] is True
        assert deps["dte"]["path"] == "/usr/bin/mock_tool"

def test_detect_vulkan_gpus():
    mock_vulkaninfo_output = """
GPU0:
    deviceName = NVIDIA GeForce RTX 3080
    deviceType = PHYSICAL_DEVICE_TYPE_DISCRETE_GPU
GPU1:
    deviceName = AMD Radeon Graphics
    deviceType = PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU
"""
    with patch("delphis.core.env_check.find_executable", return_value="/usr/bin/vulkaninfo"):
        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value = subprocess.CompletedProcess(
                ["vulkaninfo", "--summary"], 0, stdout=mock_vulkaninfo_output, stderr=""
            )
            gpus = detect_vulkan_gpus()
            assert len(gpus) >= 3  # Auto-detect + GPU0 + GPU1
            assert gpus[0][0] == -1  # Auto-detect option
            assert "NVIDIA GeForce RTX 3080 (Discrete)" in gpus[1][1]
            assert "AMD Radeon Graphics (Integrated)" in gpus[2][1]
