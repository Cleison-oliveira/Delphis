using Delphis.Core.Models;

namespace Delphis.Core.Services;

public record RgbColor(byte R, byte G, byte B);

public record AlphaOptions(
    bool RemoveAlpha = false,
    byte AlphaValue = 255,
    bool ScaleAlpha = true,
    bool SmoothEdges = false,
    double SmoothRadius = 1.0,
    bool Defringe = true,
    RgbColor? BackgroundColor = null,
    bool Recursive = true
);

public interface IAlphaProcessor
{
    /// <summary>
    /// Processes a single image file with 4-channel alpha transparency modifications.
    /// </summary>
    Task<bool> ProcessSingleImageAsync(
        string inputPath,
        string outputPath,
        AlphaOptions options,
        CancellationToken cancellationToken = default
    );

    /// <summary>
    /// Batch processes images in a directory with progress updates and cancellation support.
    /// </summary>
    Task<int> ProcessBatchAsync(
        string inputDirectory,
        string outputDirectory,
        AlphaOptions options,
        IProgress<ProcessingProgress>? progress = null,
        IProgress<LogEntry>? logProgress = null,
        CancellationToken cancellationToken = default
    );
}
