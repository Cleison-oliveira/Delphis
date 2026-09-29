using Delphis.Core.Models;

namespace Delphis.Core.Services;

/// <summary>
/// Orchestrates DolphinTextureExtraction-tool (DTE) commands, argument synthesis, and execution.
/// </summary>
public class DteOrchestrator : IDteOrchestrator
{
    private readonly IProcessRunner _processRunner;
    private readonly IEnvironmentDetector _envDetector;

    public DteOrchestrator(IProcessRunner? processRunner = null, IEnvironmentDetector? envDetector = null)
    {
        _processRunner = processRunner ?? new ProcessRunner();
        _envDetector = envDetector ?? new EnvironmentDetector();
    }

    public IReadOnlyList<string> BuildArguments(
        string inputPath,
        string outputPath,
        DteOptions options
    )
    {
        var args = new List<string>();

        // 1. DTE Command Verb
        var verb = options.Mode.ToLowerInvariant() switch
        {
            "merge_rgba" => "CombineRGBA",
            "merge_bgra" => "CombineBGRA",
            "split_tonemaps" => "Finalize",
            "extract" => "Extract",
            "unpack" => "Unpack",
            "custom" => !string.IsNullOrWhiteSpace(options.CustomCommand) ? options.CustomCommand : "Extract",
            _ => "CombineRGBA"
        };
        args.Add(verb);

        // 2. Input and Output Paths
        args.Add(inputPath);
        args.Add(outputPath);

        // 3. Flags and modifiers
        if (options.Tasks > 0)
        {
            args.AddRange(new[] { "-Tasks", options.Tasks.ToString() });
        }

        if (!string.IsNullOrWhiteSpace(options.CleanupMode))
        {
            args.Add($"-Cleanup:{options.CleanupMode}");
        }

        if (options.Recursive)
        {
            args.AddRange(new[] { "-Recursiv", "0" });
        }

        if (options.ExtractMipmaps)
        {
            args.Add("-Mip");
        }

        if (options.DolphinMipDetection)
        {
            args.Add("-Dolphinmipdetection");
        }

        if (options.Mode.Equals("extract", StringComparison.OrdinalIgnoreCase))
        {
            args.Add("-CombinedRGBA");
        }

        if (!string.IsNullOrWhiteSpace(options.ExtraArgs))
        {
            var splits = options.ExtraArgs.Split(' ', StringSplitOptions.RemoveEmptyEntries);
            args.AddRange(splits);
        }

        if (!options.ExtraArgs.Contains("-Log", StringComparison.OrdinalIgnoreCase))
        {
            var hiddenLogDir = Path.Combine(outputPath, ".log");
            args.AddRange(new[] { "-Log", hiddenLogDir });
        }

        return args;
    }

    public async Task<ProcessExecutionResult> ExecuteAsync(
        string inputPath,
        string outputPath,
        DteOptions options,
        IProgress<LogEntry>? logProgress = null,
        CancellationToken cancellationToken = default
    )
    {
        var dte = _envDetector.FindExecutable("dte") ?? _envDetector.FindExecutable("DolphinTextureExtraction.tool");
        if (dte is null)
        {
            throw new FileNotFoundException("DolphinTextureExtraction-tool executable ('dte') was not found in PATH.");
        }

        var hiddenLogDir = Path.Combine(outputPath, ".log");
        try
        {
            Directory.CreateDirectory(hiddenLogDir);
        }
        catch { }

        var args = BuildArguments(inputPath, outputPath, options);
        logProgress?.Report(new LogEntry($"Executing DTE: {dte} {string.Join(" ", args)}", LogLevel.Info));

        var result = await _processRunner.RunAsync(dte, args, null, logProgress, cancellationToken);

        // Process hidden .log directory upon completion
        if (Directory.Exists(hiddenLogDir))
        {
            try
            {
                var logFiles = Directory.GetFiles(hiddenLogDir, "DTE-*.log", SearchOption.AllDirectories);
                if (options.DisableLogFile)
                {
                    // User does not want log file on disk -> remove .log directory completely
                    Directory.Delete(hiddenLogDir, recursive: true);
                }
                else
                {
                    // User wants log file -> move it to the output folder root, then remove .log folder
                    foreach (var logFile in logFiles)
                    {
                        var destFile = Path.Combine(outputPath, Path.GetFileName(logFile));
                        if (File.Exists(destFile))
                        {
                            File.Delete(destFile);
                        }
                        File.Move(logFile, destFile);
                    }

                    try
                    {
                        if (Directory.Exists(hiddenLogDir))
                        {
                            Directory.Delete(hiddenLogDir, recursive: true);
                        }
                    }
                    catch { }
                }
            }
            catch { }
        }

        // Extra safety: if DisableLogFile is requested, ensure no loose DTE-*.log files remain
        if (options.DisableLogFile && Directory.Exists(outputPath))
        {
            try
            {
                var looseLogs = Directory.GetFiles(outputPath, "DTE-*.log", SearchOption.AllDirectories);
                foreach (var logFile in looseLogs)
                {
                    try { File.Delete(logFile); } catch { }
                }
            }
            catch { }
        }

        return result;
    }
}
