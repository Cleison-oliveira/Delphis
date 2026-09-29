namespace Delphis.Core.Models;

public enum LogLevel
{
    Info,
    Success,
    Warning,
    Error
}

/// <summary>
/// Progress reporting payload for long-running batch operations.
/// </summary>
public record ProcessingProgress(
    int Current,
    int Total,
    string Message
)
{
    public int Percentage => Total > 0 ? (int)((double)Current / Total * 100) : 0;
}

/// <summary>
/// Structured log entry emitted during task execution.
/// </summary>
public record LogEntry(
    string Message,
    LogLevel Level = LogLevel.Info,
    DateTime Timestamp = default
)
{
    public DateTime Timestamp { get; init; } = Timestamp == default ? DateTime.UtcNow : Timestamp;
}
