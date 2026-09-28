"""
Environment and Dependency Checker for Delphis.
Detects available backend CLI tools (dte, alphaseal, magick, realesrgan-ncnn-vulkan, DDS tools)
and identifies Vulkan-capable GPUs.
"""

import os
import shutil
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

LOCAL_TOOLS_DIR = Path.home() / ".local" / "share" / "delphis" / "bin"

def find_executable(name: str) -> Optional[str]:
    """Check if an executable is present in PATH, local tools directory, or standard paths."""
    # Check PATH first
    path = shutil.which(name)
    if path:
        return path

    # Check local app data tools directory
    local_path = LOCAL_TOOLS_DIR / name
    if local_path.is_file() and os.access(local_path, os.X_OK):
        return str(local_path)

    # Check common system fallback locations
    common_paths = [
        os.path.expanduser(f"~/.nix-profile/bin/{name}"),
        os.path.expanduser(f"/run/current-system/sw/bin/{name}"),
        f"/usr/local/bin/{name}",
        f"/usr/bin/{name}"
    ]
    for p in common_paths:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None

def check_dependencies() -> Dict[str, Dict[str, any]]:
    """
    Check the status of all core dependencies.
    Returns a dictionary of tool info with 'installed', 'path', and 'description'.
    """
    tools = {
        "dte": {
            "name": "DolphinTextureExtraction-tool (dte)",
            "executables": ["dte", "DolphinTextureExtraction.tool"],
            "required_for": "Tab 1: Dolphin Texture Extraction & Tonemaps",
            "optional": False
        },
        "alphaseal": {
            "name": "AlphaSeal Engine",
            "executables": ["alphaseal"],
            "required_for": "Tab 2: Alpha & Transparency (Built-in Python engine available as primary)",
            "optional": True
        },
        "realesrgan": {
            "name": "Real-ESRGAN NCNN Vulkan",
            "executables": ["realesrgan-ncnn-vulkan", "realesrgan"],
            "required_for": "Tab 3: AI Upscaler",
            "optional": False
        },
        "magick": {
            "name": "ImageMagick",
            "executables": ["magick", "convert"],
            "required_for": "Tab 3: AI Upscaler & Tab 4: DDS Fallback",
            "optional": False
        },
        "dds_tool": {
            "name": "DDS Encoder (nvcompress / texconv / compressonatorcli / magick)",
            "executables": ["nvcompress", "texconv", "compressonatorcli", "magick"],
            "required_for": "Tab 4: DDS Texture Optimizer",
            "optional": False
        }
    }

    results = {}
    for key, info in tools.items():
        found_path = None
        for exe in info["executables"]:
            p = find_executable(exe)
            if p:
                found_path = p
                break

        results[key] = {
            "name": info["name"],
            "installed": found_path is not None,
            "path": found_path,
            "required_for": info["required_for"],
            "optional": info["optional"]
        }

    return results

def detect_vulkan_gpus() -> List[Tuple[int, str]]:
    """
    Detect available Vulkan GPUs for Real-ESRGAN.
    Returns a list of (device_id, device_name).
    """
    gpus: List[Tuple[int, str]] = []

    # 1. Probe via vulkaninfo if available
    vulkaninfo_bin = find_executable("vulkaninfo")
    if vulkaninfo_bin:
        try:
            res = subprocess.run(
                [vulkaninfo_bin, "--summary"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=3
            )
            current_id = None
            current_name = None
            current_type = ""
            for line in res.stdout.splitlines():
                line = line.strip()
                m_gpu = re.match(r'^GPU(\d+):', line)
                if m_gpu:
                    if current_id is not None and current_name:
                        suffix = " (Discrete)" if "DISCRETE" in current_type else (" (Integrated)" if "INTEGRATED" in current_type else (" (CPU)" if "CPU" in current_type else ""))
                        gpus.append((current_id, f"{current_name}{suffix}"))
                    current_id = int(m_gpu.group(1))
                    current_name = None
                    current_type = ""
                elif "deviceName" in line and current_id is not None:
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        current_name = parts[1].strip()
                elif "deviceType" in line and current_id is not None:
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        current_type = parts[1].strip()

            if current_id is not None and current_name:
                suffix = " (Discrete)" if "DISCRETE" in current_type else (" (Integrated)" if "INTEGRATED" in current_type else (" (CPU)" if "CPU" in current_type else ""))
                gpus.append((current_id, f"{current_name}{suffix}"))
        except Exception:
            pass

    # 2. Probe via realesrgan-ncnn-vulkan if vulkaninfo was not found or produced nothing
    if not gpus:
        realesrgan_bin = find_executable("realesrgan-ncnn-vulkan") or find_executable("realesrgan")
        if realesrgan_bin:
            try:
                res = subprocess.run(
                    [realesrgan_bin, "-h"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3
                )
                combined = res.stdout + res.stderr
                matches = re.findall(r'\[(\d+)\s+([^\]]+)\]', combined)
                for dev_id, name in matches:
                    try:
                        gpus.append((int(dev_id), name.strip()))
                    except ValueError:
                        pass
            except Exception:
                pass

    if not gpus:
        gpus = [
            (0, "Default Vulkan Device (Device 0)")
        ]

    gpus.insert(0, (-1, "Auto-detect Best Discrete GPU (Recommended)"))
    return gpus
