using Delphis.Core.Models;

namespace Delphis.Core.Services;

/// <summary>
/// Result of an executed external process command.
/// </summary>
public record ProcessExecutionResult(
    int ExitCode,
    string StandardOutput,
    string StandardError,
    bool WasCancelled
)
{
    public bool IsSuccess => ExitCode == 0 && !WasCancelled;
}

public interface IProcessRunner
{
    /// <summary>
    /// Executes an external process asynchronously with real-time output streaming and cancellation support.
    /// </summary>
    Task<ProcessExecutionResult> RunAsync(
        string executable,
        IReadOnlyList<string> arguments,
        string? workingDirectory = null,
        IProgress<LogEntry>? logProgress = null,
        CancellationToken cancellationToken = default
    );
}
