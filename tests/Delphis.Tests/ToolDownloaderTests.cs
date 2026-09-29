using Delphis.Core.Services;

namespace Delphis.Tests;

public class ToolDownloaderTests
{
    [Fact]
    public void ToolDownloader_InstantiatesSuccessfully()
    {
        var downloader = new ToolDownloader();
        Assert.NotNull(downloader);
    }
}
