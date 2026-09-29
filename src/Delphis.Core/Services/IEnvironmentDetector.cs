using Delphis.Core.Models;

namespace Delphis.Core.Services;

public interface IEnvironmentDetector
{
    /// <summary>
    /// Searches for an executable in PATH and standard system locations.
    /// </summary>
    string? FindExecutable(string name);

    /// <summary>
    /// Checks the installation status of all required and optional backend dependencies.
    /// </summary>
    IReadOnlyDictionary<string, DependencyInfo> CheckDependencies();

    /// <summary>
    /// Enumerates all Vulkan-capable graphics adapter devices on the host.
    /// </summary>
    IReadOnlyList<GpuDeviceInfo> DetectVulkanGpus();
}
