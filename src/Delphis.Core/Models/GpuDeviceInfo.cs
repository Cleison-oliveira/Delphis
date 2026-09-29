namespace Delphis.Core.Models;

/// <summary>
/// Information about a detected Vulkan GPU hardware device.
/// </summary>
public record GpuDeviceInfo(
    int DeviceId,
    string DeviceName,
    bool IsDiscrete
)
{
    public override string ToString() =>
        DeviceId == -1
            ? DeviceName
            : $"{DeviceName}{(IsDiscrete ? " (Discrete GPU)" : "")} [ID: {DeviceId}]";
}

/// <summary>
/// Information about an external backend tool/dependency.
/// </summary>
public record DependencyInfo(
    string Key,
    string Name,
    bool IsInstalled,
    string? Path,
    string RequiredFor,
    bool IsOptional
);
