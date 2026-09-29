using Delphis.Core.Models;
using Delphis.Core.Services;

namespace Delphis.Tests;

public class UpscalerEngineTests
{
    [Fact]
    public void AutoDetectBestGpu_ShouldPickDiscreteGpuOverIntegrated()
    {
        var mockDetector = new MockEnvDetector(new List<GpuDeviceInfo>
        {
            new GpuDeviceInfo(0, "AMD Radeon 780M Graphics", IsDiscrete: false),
            new GpuDeviceInfo(1, "NVIDIA GeForce RTX 4070 Laptop GPU", IsDiscrete: true)
        });

        var upscaler = new UpscalerEngine(envDetector: mockDetector);
        int chosen = upscaler.AutoDetectBestGpu();

        Assert.Equal(1, chosen);
    }

    [Fact]
    public void AutoDetectBestGpu_WhenSingleIntegratedGpu_ShouldPickIt()
    {
        var mockDetector = new MockEnvDetector(new List<GpuDeviceInfo>
        {
            new GpuDeviceInfo(0, "Intel(R) Iris(R) Xe Graphics", IsDiscrete: false)
        });

        var upscaler = new UpscalerEngine(envDetector: mockDetector);
        int chosen = upscaler.AutoDetectBestGpu();

        Assert.Equal(0, chosen);
    }

    [Fact]
    public void FindModelsDirectory_ShouldFindShareModelsDirectoryIfPresent()
    {
        var tempRoot = Path.Combine(Path.GetTempPath(), $"delphis_test_models_{Guid.NewGuid():N}");
        try
        {
            var binDir = Path.Combine(tempRoot, "bin");
            var shareModels = Path.Combine(tempRoot, "share", "models");
            Directory.CreateDirectory(binDir);
            Directory.CreateDirectory(shareModels);

            var dummyBin = Path.Combine(shareModels, "realesrgan-x4plus-anime.bin");
            File.WriteAllText(dummyBin, "dummy");

            var upscaler = new UpscalerEngine();
            var found = upscaler.FindModelsDirectory(Path.Combine(binDir, "realesrgan-ncnn-vulkan"));

            Assert.Equal(shareModels, found);
        }
        finally
        {
            if (Directory.Exists(tempRoot))
            {
                Directory.Delete(tempRoot, true);
            }
        }
    }
}

internal class MockEnvDetector : IEnvironmentDetector
{
    private readonly IReadOnlyList<GpuDeviceInfo> _gpus;

    public MockEnvDetector(IReadOnlyList<GpuDeviceInfo> gpus)
    {
        _gpus = gpus;
    }

    public string? FindExecutable(string name) => null;
    public IReadOnlyDictionary<string, DependencyInfo> CheckDependencies() => new Dictionary<string, DependencyInfo>();
    public IReadOnlyList<GpuDeviceInfo> DetectVulkanGpus() => _gpus;
}
