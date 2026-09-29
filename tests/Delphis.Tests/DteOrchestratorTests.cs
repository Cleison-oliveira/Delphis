using Delphis.Core.Models;
using Delphis.Core.Services;

namespace Delphis.Tests;

public class DteOrchestratorTests
{
    [Fact]
    public void BuildArguments_MergeRgba_ShouldSynthesizeCombineRgba()
    {
        var orchestrator = new DteOrchestrator();
        var options = new DteOptions(
            Mode: "merge_rgba",
            Tasks: 4,
            CleanupMode: "default",
            Recursive: true,
            ExtractMipmaps: false,
            DolphinMipDetection: true
        );

        var args = orchestrator.BuildArguments("/path/in", "/path/out", options);

        Assert.Equal("CombineRGBA", args[0]);
        Assert.Equal("/path/in", args[1]);
        Assert.Equal("/path/out", args[2]);
        Assert.Contains("-Tasks", args);
        Assert.Contains("4", args);
        Assert.Contains("-Cleanup:default", args);
        Assert.Contains("-Recursiv", args);
        Assert.Contains("-Dolphinmipdetection", args);
        Assert.Contains("-Log", args);
    }

    [Fact]
    public void BuildArguments_Extract_ShouldIncludeCombinedRgbaFlag()
    {
        var orchestrator = new DteOrchestrator();
        var options = new DteOptions(Mode: "extract");
        var args = orchestrator.BuildArguments("/path/in", "/path/out", options);

        Assert.Equal("Extract", args[0]);
        Assert.Contains("-CombinedRGBA", args);
    }

    [Fact]
    public void BuildArguments_Finalize_ShouldUseFinalizeVerb()
    {
        var orchestrator = new DteOrchestrator();
        var options = new DteOptions(Mode: "split_tonemaps");
        var args = orchestrator.BuildArguments("/path/in", "/path/out", options);

        Assert.Equal("Finalize", args[0]);
    }

    [Fact]
    public void BuildArguments_DisableLogFile_ShouldRetainNormalExecutionArguments()
    {
        var orchestrator = new DteOrchestrator();
        var options = new DteOptions(Mode: "merge_rgba", DisableLogFile: true);
        var args = orchestrator.BuildArguments("/path/in", "/path/out", options);

        Assert.Equal("CombineRGBA", args[0]);
        Assert.Equal("/path/in", args[1]);
        Assert.Equal("/path/out", args[2]);
    }
}
