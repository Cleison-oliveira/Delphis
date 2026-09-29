using Delphis.Core.Models;

namespace Delphis.Core.Services;

public record DteOptions(
    string Mode = "merge_rgba", // "merge_rgba", "merge_bgra", "split_tonemaps", "extract", "unpack", "custom"
    int Tasks = 1,
    bool Recursive = true,
    bool ExtractMipmaps = false,
    bool DolphinMipDetection = true,
    string CleanupMode = "none", // "none", "default", "simple", "compact"
    string CustomCommand = "Extract",
    string ExtraArgs = "",
    bool DisableLogFile = false
);

public interface IDteOrchestrator
{
    /// <summary>
    /// Builds the CLI argument list for a given DTE operation.
    /// </summary>
    IReadOnlyList<string> BuildArguments(
        string inputPath,
        string outputPath,
        DteOptions options
    );

    /// <summary>
    /// Executes a DTE extraction or tonemap merge/split operation asynchronously.
    /// </summary>
    Task<ProcessExecutionResult> ExecuteAsync(
        string inputPath,
        string outputPath,
        DteOptions options,
        IProgress<LogEntry>? logProgress = null,
        CancellationToken cancellationToken = default
    );
}
