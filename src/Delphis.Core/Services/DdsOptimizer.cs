using Delphis.Core.Models;

namespace Delphis.Core.Services;

/// <summary>
/// DirectDraw Surface (DDS) Texture Compressor and Optimizer tailored for Dolphin Emulator.
/// </summary>
public class DdsOptimizer : IDdsOptimizer
{
    private readonly IProcessRunner _processRunner;
    private readonly IEnvironmentDetector _envDetector;

    public DdsOptimizer(IProcessRunner? processRunner = null, IEnvironmentDetector? envDetector = null)
    {
        _processRunner = processRunner ?? new ProcessRunner();
        _envDetector = envDetector ?? new EnvironmentDetector();
    }

    public (string EncoderType, string ExecutablePath)? DetectEncoder()
    {
        if (_envDetector.FindExecutable("nvcompress") is { } nv)
            return ("nvcompress", nv);
        if (_envDetector.FindExecutable("texconv") is { } tc)
            return ("texconv", tc);
        if (_envDetector.FindExecutable("compressonatorcli") is { } cmp)
            return ("compressonator", cmp);
        if (_envDetector.FindExecutable("magick") is { } mg)
            return ("magick", mg);
        if (_envDetector.FindExecutable("convert") is { } cv)
            return ("magick", cv);

        return null;
    }

    public static IReadOnlyList<string> BuildEncoderArguments(
        string encoderType,
        string inputPath,
        string outputPath,
        DdsOptions options
    )
    {
        var args = new List<string>();

        switch (encoderType)
        {
            case "nvcompress":
                var nvFlag = options.Preset.ToUpperInvariant() switch
                {
                    "BC1" => "-bc1",
                    "BC1A" => "-bc1a",
                    "BC3" => "-bc3",
                    "BC5" => "-bc5",
                    _ => "-bc7"
                };
                args.Add(nvFlag);
                args.Add(options.GenerateMipmaps ? "-mip" : "-nomip");
                args.Add(inputPath);
                args.Add(outputPath);
                break;

            case "texconv":
                var tcFormat = options.Preset.ToUpperInvariant() switch
                {
                    "BC1" => "BC1_UNORM",
                    "BC3" => "BC3_UNORM",
                    "BC5" => "BC5_UNORM",
                    _ => "BC7_UNORM"
                };
                args.AddRange(new[] { "-y", "-f", tcFormat });
                args.AddRange(options.GenerateMipmaps ? new[] { "-m", "0" } : new[] { "-m", "1" });
                args.AddRange(new[] { "-o", Path.GetDirectoryName(outputPath) ?? ".", inputPath });
                break;

            case "compressonator":
                var cmpFormat = options.Preset.ToUpperInvariant() switch
                {
                    "BC1" => "BC1",
                    "BC3" => "BC3",
                    "BC5" => "BC5",
                    _ => "BC7"
                };
                args.AddRange(new[] { "-fd", cmpFormat });
                if (options.GenerateMipmaps)
                {
                    args.AddRange(new[] { "-miplevels", "0" });
                }
                args.AddRange(new[] { inputPath, outputPath });
                break;

            case "magick":
            default:
                var comp = options.Preset.ToUpperInvariant() switch
                {
                    "BC1" or "BC1A" => "dxt1",
                    "BC3" => "dxt5",
                    _ => "dxt5"
                };
                args.Add(inputPath);
                args.AddRange(new[] { "-define", $"dds:compression={comp}" });
                if (options.GenerateMipmaps)
                {
                    args.AddRange(new[] { "-define", "dds:mipmaps=0" });
                }
                args.Add(outputPath);
                break;
        }

        return args;
    }

    public async Task<bool> ConvertSingleAsync(
        string inputPath,
        string outputPath,
        DdsOptions options,
        CancellationToken cancellationToken = default
    )
    {
        var encoder = DetectEncoder();
        if (encoder is null)
        {
            throw new FileNotFoundException("No supported DDS encoder (nvcompress, texconv, compressonatorcli, magick) was found in PATH.");
        }

        string finalOutput = outputPath;
        if (Directory.Exists(outputPath) || string.IsNullOrEmpty(Path.GetExtension(outputPath)))
        {
            var fileName = Path.ChangeExtension(Path.GetFileName(inputPath), ".dds");
            finalOutput = Path.Combine(outputPath, fileName);
        }

        var outDir = Path.GetDirectoryName(finalOutput);
        if (!string.IsNullOrEmpty(outDir))
        {
            Directory.CreateDirectory(outDir);
        }

        var args = BuildEncoderArguments(encoder.Value.EncoderType, inputPath, finalOutput, options);
        var result = await _processRunner.RunAsync(encoder.Value.ExecutablePath, args, null, null, cancellationToken);

        return result.IsSuccess && (File.Exists(finalOutput) || File.Exists(Path.ChangeExtension(finalOutput, ".DDS")));
    }

    public async Task<int> ConvertBatchAsync(
        string inputDirectory,
        string outputDirectory,
        DdsOptions options,
        IProgress<ProcessingProgress>? progress = null,
        IProgress<LogEntry>? logProgress = null,
        CancellationToken cancellationToken = default
    )
    {
        var encoder = DetectEncoder();
        if (encoder is null)
        {
            logProgress?.Report(new LogEntry("No DDS encoder found (Install 'nvidia-texture-tools', 'texconv', or 'imagemagick').", LogLevel.Error));
            return 0;
        }

        logProgress?.Report(new LogEntry($"Using DDS Encoder: {encoder.Value.EncoderType} ({encoder.Value.ExecutablePath})", LogLevel.Info));

        var searchOption = options.Recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
        var files = File.Exists(inputDirectory)
            ? new[] { inputDirectory }
            : Directory.GetFiles(inputDirectory, "*.*", searchOption)
                .Where(f => DelphisConstants.SupportedImageExtensions.Contains(Path.GetExtension(f)) &&
                            !Path.GetExtension(f).Equals(".dds", StringComparison.OrdinalIgnoreCase))
                .ToArray();

        int total = files.Length;
        if (total == 0)
        {
            logProgress?.Report(new LogEntry($"No eligible images found in '{inputDirectory}'.", LogLevel.Warning));
            return 0;
        }

        logProgress?.Report(new LogEntry($"DDS Optimizer: Converting {total} file(s) [Preset: {options.Preset} | Mipmaps: {options.GenerateMipmaps}]...", LogLevel.Info));

        int successCount = 0;
        for (int i = 0; i < total; i++)
        {
            cancellationToken.ThrowIfCancellationRequested();

            var file = files[i];
            var stem = Path.GetFileNameWithoutExtension(file);

            string dest;
            if (File.Exists(inputDirectory))
            {
                dest = Directory.Exists(outputDirectory)
                    ? Path.Combine(outputDirectory, $"{stem}.dds")
                    : Path.ChangeExtension(outputDirectory, ".dds");
            }
            else
            {
                var rel = Path.GetRelativePath(inputDirectory, file);
                var relDir = Path.GetDirectoryName(rel) ?? string.Empty;
                dest = Path.Combine(outputDirectory, relDir, $"{stem}.dds");
            }

            bool ok = await ConvertSingleAsync(file, dest, options, cancellationToken);
            if (ok)
            {
                successCount++;
                logProgress?.Report(new LogEntry($"[OK] {Path.GetFileName(file)} -> {Path.GetFileName(dest)}", LogLevel.Success));
            }
            else
            {
                logProgress?.Report(new LogEntry($"[ERROR] Failed converting {Path.GetFileName(file)}", LogLevel.Error));
            }

            progress?.Report(new ProcessingProgress(i + 1, total, $"Converted {i + 1}/{total}"));
        }

        logProgress?.Report(new LogEntry(
            $"DDS Optimization complete: {successCount}/{total} files converted to {options.Preset} DDS.",
            successCount == total ? LogLevel.Success : LogLevel.Warning
        ));

        return successCount;
    }
}
