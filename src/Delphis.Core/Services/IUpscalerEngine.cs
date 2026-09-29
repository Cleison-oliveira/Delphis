using Delphis.Core.Models;

namespace Delphis.Core.Services;

public record UpscalerOptions(
    int Scale = 4,
    string Model = "realesrgan-x4plus-anime",
    string AlphaMode = "ai", // "ai" or "lanczos"
    int GpuId = -1, // -1 for auto-detect
    bool Recursive = true
);

public interface IUpscalerEngine
{
    /// <summary>
    /// Upscales a single texture using an alpha-preserving 4-channel Real-ESRGAN neural pipeline.
    /// </summary>
    Task<bool> UpscaleSingleAsync(
        string inputPath,
        string outputPath,
        UpscalerOptions options,
        string? modelsDirectory = null,
        CancellationToken cancellationToken = default
    );

    /// <summary>
    /// Batch upscales images in a folder with real-time progress and cancellation.
    /// </summary>
    Task<int> UpscaleBatchAsync(
        string inputDirectory,
        string outputDirectory,
        UpscalerOptions options,
        IProgress<ProcessingProgress>? progress = null,
        IProgress<LogEntry>? logProgress = null,
        CancellationToken cancellationToken = default
    );
}
