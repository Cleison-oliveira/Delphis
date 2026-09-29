using Delphis.Core;

namespace Delphis.Tests;

public class ConstantsTests
{
    [Fact]
    public void AppMetadata_ShouldBeValid()
    {
        Assert.Equal("Delphis", DelphisConstants.AppName);
        Assert.False(string.IsNullOrWhiteSpace(DelphisConstants.AppVersion));
        Assert.False(string.IsNullOrWhiteSpace(DelphisConstants.AppTitle));
    }

    [Fact]
    public void SupportedImageExtensions_ShouldContainStandardFormats()
    {
        Assert.Contains(".png", DelphisConstants.SupportedImageExtensions);
        Assert.Contains(".dds", DelphisConstants.SupportedImageExtensions);
        Assert.Contains(".webp", DelphisConstants.SupportedImageExtensions);
        Assert.Contains(".tga", DelphisConstants.SupportedImageExtensions);
    }

    [Fact]
    public void DdsPresets_ShouldContainStandardDolphinPresets()
    {
        var expectedPresets = new[] { "BC7", "BC1", "BC1a", "BC3", "BC5" };
        foreach (var p in expectedPresets)
        {
            Assert.True(DelphisConstants.DdsPresets.ContainsKey(p));
            var preset = DelphisConstants.DdsPresets[p];
            Assert.False(string.IsNullOrWhiteSpace(preset.Name));
            Assert.False(string.IsNullOrWhiteSpace(preset.Description));
        }

        Assert.True(DelphisConstants.DdsPresets["BC7"].IsDefault);
        Assert.True(DelphisConstants.DdsPresets["BC7"].HasAlpha);
        Assert.False(DelphisConstants.DdsPresets["BC1"].HasAlpha);
    }

    [Fact]
    public void AiModels_ShouldContainAnimeAndRealisticModels()
    {
        Assert.True(DelphisConstants.AiModels.Count >= 3);
        var ids = DelphisConstants.AiModels.Select(m => m.Id).ToList();
        Assert.Contains("realesrgan-x4plus-anime", ids);
        Assert.Contains("realesrgan-x4plus", ids);
        Assert.Contains("realesr-animevideov3", ids);
    }

    [Fact]
    public void AlphaQuickPresets_ShouldContainDolphinPresetLevels()
    {
        var levels = DelphisConstants.AlphaQuickPresets.Select(p => p.Alpha).ToList();
        Assert.Contains((byte)255, levels);
        Assert.Contains((byte)192, levels);
        Assert.Contains((byte)130, levels);
        Assert.Contains((byte)64, levels);
        Assert.Contains((byte)0, levels);
    }
}
