using System.Diagnostics;
using System.Text.RegularExpressions;
using Delphis.Core.Models;

namespace Delphis.Core.Services;

/// <summary>
/// Probes system environment, PATH directories, dependencies, and Vulkan GPU hardware.
/// </summary>
public class EnvironmentDetector : IEnvironmentDetector
{
    private static readonly string LocalToolsDir = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
        ".local", "share", "delphis", "bin"
    );

    public string? FindExecutable(string name)
    {
        // 1. Check system PATH
        var pathEnv = Environment.GetEnvironmentVariable("PATH") ?? string.Empty;
        var searchPaths = pathEnv.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries);

        foreach (var path in searchPaths)
        {
            var fullPath = Path.Combine(path, name);
            if (File.Exists(fullPath))
            {
                return fullPath;
            }
        }

        // 2. Check user local app data dir
        var localToolPath = Path.Combine(LocalToolsDir, name);
        if (File.Exists(localToolPath))
        {
            return localToolPath;
        }

        // 3. Check common Linux & Nix fallback locations
        var userHome = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        var fallbackLocations = new[]
        {
            Path.Combine(userHome, ".nix-profile", "bin", name),
            Path.Combine("/run/current-system/sw/bin", name),
            Path.Combine("/usr/local/bin", name),
            Path.Combine("/usr/bin", name)
        };

        foreach (var location in fallbackLocations)
        {
            if (File.Exists(location))
            {
                return location;
            }
        }

        return null;
    }

    public IReadOnlyDictionary<string, DependencyInfo> CheckDependencies()
    {
        var definitions = new[]
        {
            (Key: "dte", Name: "DolphinTextureExtraction-tool (dte)", Executables: new[] { "dte", "DolphinTextureExtraction.tool" }, RequiredFor: "Tab 1: Dolphin Texture Extraction & Tonemaps", Optional: false),
            (Key: "realesrgan", Name: "Real-ESRGAN NCNN Vulkan", Executables: new[] { "realesrgan-ncnn-vulkan", "realesrgan" }, RequiredFor: "Tab 3: AI Upscaler", Optional: false),
            (Key: "magick", Name: "ImageMagick", Executables: new[] { "magick", "convert" }, RequiredFor: "Tab 3: AI Upscaler & Tab 4: DDS Fallback", Optional: false),
            (Key: "dds_tool", Name: "DDS Encoder (nvcompress / texconv / compressonatorcli / magick)", Executables: new[] { "nvcompress", "texconv", "compressonatorcli", "magick" }, RequiredFor: "Tab 4: DDS Texture Optimizer", Optional: false)
        };

        var results = new Dictionary<string, DependencyInfo>(StringComparer.OrdinalIgnoreCase);

        foreach (var def in definitions)
        {
            string? foundPath = null;
            foreach (var exe in def.Executables)
            {
                var p = FindExecutable(exe);
                if (p is not null)
                {
                    foundPath = p;
                    break;
                }
            }

            results[def.Key] = new DependencyInfo(
                Key: def.Key,
                Name: def.Name,
                IsInstalled: foundPath is not null,
                Path: foundPath,
                RequiredFor: def.RequiredFor,
                IsOptional: def.Optional
            );
        }

        return results;
    }

    public IReadOnlyList<GpuDeviceInfo> DetectVulkanGpus()
    {
        var gpus = new List<GpuDeviceInfo>();

        // 1. Probe via vulkaninfo
        var vulkanInfo = FindExecutable("vulkaninfo");
        if (vulkanInfo is not null)
        {
            try
            {
                using var proc = Process.Start(new ProcessStartInfo
                {
                    FileName = vulkanInfo,
                    Arguments = "--summary",
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                });

                if (proc is not null && proc.WaitForExit(3000))
                {
                    var stdout = proc.StandardOutput.ReadToEnd();
                    ParseVulkanInfoSummary(stdout, gpus);
                }
            }
            catch
            {
                // vulkaninfo probe failed; fall through
            }
        }

        // 2. Probe via Real-ESRGAN CLI help output if needed
        if (gpus.Count == 0)
        {
            var realesrgan = FindExecutable("realesrgan-ncnn-vulkan") ?? FindExecutable("realesrgan");
            if (realesrgan is not null)
            {
                try
                {
                    using var proc = Process.Start(new ProcessStartInfo
                    {
                        FileName = realesrgan,
                        Arguments = "-h",
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        UseShellExecute = false,
                        CreateNoWindow = true
                    });

                    if (proc is not null && proc.WaitForExit(3000))
                    {
                        var combined = proc.StandardOutput.ReadToEnd() + proc.StandardError.ReadToEnd();
                        var matches = Regex.Matches(combined, @"\[(\d+)\s+([^\]]+)\]");
                        foreach (Match match in matches)
                        {
                            if (int.TryParse(match.Groups[1].Value, out var devId))
                            {
                                var name = match.Groups[2].Value.Trim();
                                var isDiscrete = name.Contains("NVIDIA", StringComparison.OrdinalIgnoreCase) ||
                                                 name.Contains("GeForce", StringComparison.OrdinalIgnoreCase) ||
                                                 (name.Contains("Radeon", StringComparison.OrdinalIgnoreCase) && !name.Contains("Graphics", StringComparison.OrdinalIgnoreCase));
                                gpus.Add(new GpuDeviceInfo(devId, name, isDiscrete));
                            }
                        }
                    }
                }
                catch
                {
                    // Fallback below
                }
            }
        }

        if (gpus.Count == 0)
        {
            gpus.Add(new GpuDeviceInfo(0, "Default Vulkan Device (Device 0)", false));
        }

        gpus.Insert(0, new GpuDeviceInfo(-1, "Auto-detect Best Discrete GPU (Recommended)", true));
        return gpus;
    }

    public static void ParseVulkanInfoSummary(string output, List<GpuDeviceInfo> destination)
    {
        int? currentId = null;
        string? currentName = null;
        string currentType = string.Empty;

        var lines = output.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
        foreach (var rawLine in lines)
        {
            var line = rawLine.Trim();
            var matchGpu = Regex.Match(line, @"^GPU(\d+):");
            if (matchGpu.Success)
            {
                if (currentId.HasValue && !string.IsNullOrEmpty(currentName))
                {
                    destination.Add(new GpuDeviceInfo(
                        currentId.Value,
                        currentName,
                        currentType.Contains("DISCRETE", StringComparison.OrdinalIgnoreCase)
                    ));
                }

                currentId = int.Parse(matchGpu.Groups[1].Value);
                currentName = null;
                currentType = string.Empty;
            }
            else if (line.StartsWith("deviceName", StringComparison.OrdinalIgnoreCase) && currentId.HasValue)
            {
                var parts = line.Split('=', 2);
                if (parts.Length == 2) currentName = parts[1].Trim();
            }
            else if (line.StartsWith("deviceType", StringComparison.OrdinalIgnoreCase) && currentId.HasValue)
            {
                var parts = line.Split('=', 2);
                if (parts.Length == 2) currentType = parts[1].Trim();
            }
        }

        if (currentId.HasValue && !string.IsNullOrEmpty(currentName))
        {
            destination.Add(new GpuDeviceInfo(
                currentId.Value,
                currentName,
                currentType.Contains("DISCRETE", StringComparison.OrdinalIgnoreCase)
            ));
        }
    }
}
