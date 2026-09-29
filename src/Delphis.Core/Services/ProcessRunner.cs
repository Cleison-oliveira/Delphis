using System.Diagnostics;
using System.Text;
using Delphis.Core.Models;

namespace Delphis.Core.Services;

/// <summary>
/// High-performance asynchronous process execution service with stdout streaming and process-tree cancellation.
/// </summary>
public class ProcessRunner : IProcessRunner
{
    public async Task<ProcessExecutionResult> RunAsync(
        string executable,
        IReadOnlyList<string> arguments,
        string? workingDirectory = null,
        IProgress<LogEntry>? logProgress = null,
        CancellationToken cancellationToken = default
    )
    {
        var psi = new ProcessStartInfo
        {
            FileName = executable,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
            WorkingDirectory = workingDirectory ?? Directory.GetCurrentDirectory()
        };

        foreach (var arg in arguments)
        {
            psi.ArgumentList.Add(arg);
        }

        var stdoutBuilder = new StringBuilder();
        var stderrBuilder = new StringBuilder();

        using var process = new Process { StartInfo = psi };

        void OnOutputData(object sender, DataReceivedEventArgs e)
        {
            if (e.Data is null) return;
            lock (stdoutBuilder)
            {
                stdoutBuilder.AppendLine(e.Data);
            }

            var level = ClassifyLogLevel(e.Data);
            logProgress?.Report(new LogEntry(e.Data, level));
        }

        void OnErrorData(object sender, DataReceivedEventArgs e)
        {
            if (e.Data is null) return;
            lock (stderrBuilder)
            {
                stderrBuilder.AppendLine(e.Data);
            }

            logProgress?.Report(new LogEntry(e.Data, LogLevel.Warning));
        }

        process.OutputDataReceived += OnOutputData;
        process.ErrorDataReceived += OnErrorData;

        try
        {
            if (!process.Start())
            {
                throw new InvalidOperationException($"Failed to start process '{executable}'.");
            }

            process.BeginOutputReadLine();
            process.BeginErrorReadLine();

            // Wait for completion or cancellation
            await process.WaitForExitAsync(cancellationToken);

            return new ProcessExecutionResult(
                ExitCode: process.ExitCode,
                StandardOutput: stdoutBuilder.ToString().TrimEnd(),
                StandardError: stderrBuilder.ToString().TrimEnd(),
                WasCancelled: false
            );
        }
        catch (OperationCanceledException)
        {
            try
            {
                if (!process.HasExited)
                {
                    process.Kill(entireProcessTree: true);
                }
            }
            catch
            {
                // Process may have already exited
            }

            logProgress?.Report(new LogEntry("Process execution cancelled by user.", LogLevel.Warning));

            return new ProcessExecutionResult(
                ExitCode: -1,
                StandardOutput: stdoutBuilder.ToString().TrimEnd(),
                StandardError: stderrBuilder.ToString().TrimEnd(),
                WasCancelled: true
            );
        }
    }

    private static LogLevel ClassifyLogLevel(string line)
    {
        var lower = line.ToLowerInvariant();
        if (lower.Contains("error") || lower.Contains("fail") || lower.Contains("fatal"))
            return LogLevel.Error;
        if (lower.Contains("warning") || lower.Contains("[!]"))
            return LogLevel.Warning;
        if (lower.Contains("success") || lower.Contains("done") || lower.Contains("[ok]") || lower.Contains("[+]"))
            return LogLevel.Success;

        return LogLevel.Info;
    }
}
