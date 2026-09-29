using System.IO.Compression;
using Delphis.Core.Models;

namespace Delphis.Core.Services;

/// <summary>
/// Downloads and sets up Real-ESRGAN and AI neural models on demand.
/// </summary>
public class ToolDownloader : IToolDownloader
{
    private const string DownloadUrl = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip";
    
    private static readonly string ToolsDir = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
        ".local", "share", "delphis", "bin"
    );

    private readonly HttpClient _httpClient;

    public ToolDownloader(HttpClient? httpClient = null)
    {
        _httpClient = httpClient ?? new HttpClient();
    }

    public async Task<bool> DownloadRealEsrganAsync(
        IProgress<ProcessingProgress>? progress = null,
        IProgress<LogEntry>? logProgress = null,
        CancellationToken cancellationToken = default
    )
    {
        Directory.CreateDirectory(ToolsDir);
        var zipPath = Path.Combine(ToolsDir, "realesrgan_temp.zip");

        try
        {
            logProgress?.Report(new LogEntry($"Downloading Real-ESRGAN from {DownloadUrl}...", LogLevel.Info));

            using (var response = await _httpClient.GetAsync(DownloadUrl, HttpCompletionOption.ResponseHeadersRead, cancellationToken))
            {
                response.EnsureSuccessStatusCode();

                var totalBytes = response.Content.Headers.ContentLength ?? -1L;
                await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
                await using var fileStream = new FileStream(zipPath, FileMode.Create, FileAccess.Write, FileShare.None, 81920, true);

                var buffer = new byte[81920];
                long totalRead = 0;
                int read;

                while ((read = await stream.ReadAsync(buffer, 0, buffer.Length, cancellationToken)) > 0)
                {
                    await fileStream.WriteAsync(buffer.AsMemory(0, read), cancellationToken);
                    totalRead += read;

                    if (totalBytes > 0)
                    {
                        var pct = (int)((double)totalRead / totalBytes * 100);
                        progress?.Report(new ProcessingProgress((int)(totalRead / 1024 / 1024), (int)(totalBytes / 1024 / 1024), $"Downloading: {totalRead / 1024 / 1024}MB / {totalBytes / 1024 / 1024}MB ({pct}%)"));
                    }
                }
            }

            logProgress?.Report(new LogEntry("Extracting Real-ESRGAN and neural models...", LogLevel.Info));
            ZipFile.ExtractToDirectory(zipPath, ToolsDir, overwriteFiles: true);

            var binPath = Path.Combine(ToolsDir, "realesrgan-ncnn-vulkan");
            if (File.Exists(binPath) && !OperatingSystem.IsWindows())
            {
                File.SetUnixFileMode(binPath, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute |
                                              UnixFileMode.GroupRead | UnixFileMode.GroupExecute |
                                              UnixFileMode.OtherRead | UnixFileMode.OtherExecute);
            }

            if (File.Exists(zipPath))
            {
                File.Delete(zipPath);
            }

            logProgress?.Report(new LogEntry($"[SUCCESS] Real-ESRGAN installed successfully in {ToolsDir}", LogLevel.Success));
            return true;
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            logProgress?.Report(new LogEntry($"Failed to download Real-ESRGAN: {ex.Message}", LogLevel.Error));
            return false;
        }
        finally
        {
            if (File.Exists(zipPath))
            {
                try { File.Delete(zipPath); } catch { /* Ignore */ }
            }
        }
    }
}
