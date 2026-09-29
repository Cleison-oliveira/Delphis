using Delphis.Core.Models;
using Delphis.Core.Services;

namespace Delphis.Tests;

public class EnvironmentDetectorTests
{
    [Fact]
    public void ParseVulkanInfoSummary_ShouldExtractDiscreteAndIntegratedGpus()
    {
        var sampleSummary = """
        GPU0:
            deviceName = NVIDIA GeForce RTX 4090
            deviceType = PHYSICAL_DEVICE_TYPE_DISCRETE_GPU
        GPU1:
            deviceName = AMD Radeon 780M Graphics
            deviceType = PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU
        """;

        var list = new List<GpuDeviceInfo>();
        EnvironmentDetector.ParseVulkanInfoSummary(sampleSummary, list);

        Assert.Equal(2, list.Count);
        Assert.Equal(0, list[0].DeviceId);
        Assert.Equal("NVIDIA GeForce RTX 4090", list[0].DeviceName);
        Assert.True(list[0].IsDiscrete);

        Assert.Equal(1, list[1].DeviceId);
        Assert.Equal("AMD Radeon 780M Graphics", list[1].DeviceName);
        Assert.False(list[1].IsDiscrete);
    }
}
