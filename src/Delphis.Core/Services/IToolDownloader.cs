using Delphis.Core.Models;

namespace Delphis.Core.Services;

public interface IToolDownloader
{
    /// <summary>
    /// Downloads and installs missing Real-ESRGAN binary and AI models into the local tool directory.
    /// </summary>
    Task<bool> DownloadRealEsrganAsync(
        IProgress<ProcessingProgress>? progress = null,
        IProgress<LogEntry>? logProgress = null,
        CancellationToken cancellationToken = default
    );
}
