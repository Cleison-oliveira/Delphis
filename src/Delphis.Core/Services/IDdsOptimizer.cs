using Delphis.Core.Models;

namespace Delphis.Core.Services;

public record DdsOptions(
    string Preset = "BC7",
    bool GenerateMipmaps = true,
    bool Recursive = true
);

public interface IDdsOptimizer
{
    /// <summary>
    /// Converts and compresses an image into DirectDraw Surface (DDS) format using community presets.
    /// </summary>
    Task<bool> ConvertSingleAsync(
        string inputPath,
        string outputPath,
        DdsOptions options,
        CancellationToken cancellationToken = default
    );

    /// <summary>
    /// Batch converts textures in a folder to hardware-accelerated DDS format.
    /// </summary>
    Task<int> ConvertBatchAsync(
        string inputDirectory,
        string outputDirectory,
        DdsOptions options,
        IProgress<ProcessingProgress>? progress = null,
        IProgress<LogEntry>? logProgress = null,
        CancellationToken cancellationToken = default
    );
}
