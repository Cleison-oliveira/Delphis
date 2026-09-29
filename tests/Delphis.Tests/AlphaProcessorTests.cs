using Delphis.Core.Services;

namespace Delphis.Tests;

public class AlphaProcessorTests
{
    [Fact]
    public void ParseColor_ShouldParseHexAndNamedColors()
    {
        var white = AlphaProcessor.ParseColor("white");
        Assert.NotNull(white);
        Assert.Equal(255, white!.R);
        Assert.Equal(255, white!.G);
        Assert.Equal(255, white!.B);

        var hexRed = AlphaProcessor.ParseColor("#FF0000");
        Assert.NotNull(hexRed);
        Assert.Equal(255, hexRed!.R);
        Assert.Equal(0, hexRed!.G);
        Assert.Equal(0, hexRed!.B);

        Assert.Null(AlphaProcessor.ParseColor(null));
        Assert.Null(AlphaProcessor.ParseColor(""));
        Assert.Null(AlphaProcessor.ParseColor("nonexistent-color-123"));
    }

    [Fact]
    public void DefringeChannel_ShouldUnmultiplySemiTransparentPixels()
    {
        byte[] color = { 100, 100, 50, 100 };
        byte[] alpha = { 255, 128, 64, 0 };

        AlphaProcessor.DefringeChannel(color.AsSpan(), alpha.AsSpan());

        Assert.Equal((byte)100, color[0]);
        Assert.Equal((byte)199, color[1]);
        Assert.Equal((byte)199, color[2]);
        Assert.Equal((byte)100, color[3]);
    }
}
