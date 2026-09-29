using System.Globalization;
using Delphis.Core.Models;

namespace Delphis.Core.Services;

/// <summary>
/// High-performance 4-channel (RGBa) image processor for adjusting opacity, removing alpha,
/// defringing color halos, and applying Gaussian edge smoothing.
/// </summary>
public class AlphaProcessor : IAlphaProcessor
{
    private readonly IProcessRunner _processRunner;
    private readonly IEnvironmentDetector _envDetector;

    public AlphaProcessor(IProcessRunner? processRunner = null, IEnvironmentDetector? envDetector = null)
    {
        _processRunner = processRunner ?? new ProcessRunner();
        _envDetector = envDetector ?? new EnvironmentDetector();
    }

    /// <summary>
    /// Defringes color channels around semi-transparent edges by unmultiplying color components.
    /// Formula: C_unmult = min(255, (C * 255) / alpha) for 0 < alpha < 255.
    /// </summary>
    public static void DefringeChannel(Span<byte> colorChannel, ReadOnlySpan<byte> alphaChannel)
    {
        if (colorChannel.Length != alphaChannel.Length)
            throw new ArgumentException("Channel buffers must be of equal length.");

        for (int i = 0; i < colorChannel.Length; i++)
        {
            byte alpha = alphaChannel[i];
            if (alpha == 255 || alpha == 0) continue;

            colorChannel[i] = (byte)Math.Min(255, (int)Math.Round(colorChannel[i] * 255.0 / alpha));
        }
    }

    /// <summary>
    /// Parses a color string (e.g., 'white', 'black', '#ff0000') into an RgbColor struct.
    /// </summary>
    public static RgbColor? ParseColor(string? colorStr)
    {
        if (string.IsNullOrWhiteSpace(colorStr)) return null;

        var str = colorStr.Trim();
        if (str.StartsWith('#'))
        {
            var hex = str[1..];
            if (hex.Length == 6 &&
                byte.TryParse(hex[0..2], NumberStyles.HexNumber, null, out var r) &&
                byte.TryParse(hex[2..4], NumberStyles.HexNumber, null, out var g) &&
                byte.TryParse(hex[4..6], NumberStyles.HexNumber, null, out var b))
            {
                return new RgbColor(r, g, b);
            }
        }

        return str.ToLowerInvariant() switch
        {
            "white" => new RgbColor(255, 255, 255),
            "black" => new RgbColor(0, 0, 0),
            "red" => new RgbColor(255, 0, 0),
            "green" => new RgbColor(0, 255, 0),
            "blue" => new RgbColor(0, 0, 255),
            _ => null
        };
    }

    public async Task<bool> ProcessSingleImageAsync(
        string inputPath,
        string outputPath,
        AlphaOptions options,
        CancellationToken cancellationToken = default
    )
    {
        if (!File.Exists(inputPath))
            return false;

        var magick = _envDetector.FindExecutable("magick") ?? _envDetector.FindExecutable("convert");
        if (magick is null)
        {
            throw new FileNotFoundException("ImageMagick executable ('magick' or 'convert') not found in PATH.");
        }

        string finalOutput = outputPath;
        if (Directory.Exists(outputPath) || string.IsNullOrEmpty(Path.GetExtension(outputPath)))
        {
            var fileName = Path.GetFileName(inputPath);
            finalOutput = Path.Combine(outputPath, fileName);
        }

        var outDir = Path.GetDirectoryName(finalOutput);
        if (!string.IsNullOrEmpty(outDir))
        {
            Directory.CreateDirectory(outDir);
        }

        var args = new List<string> { inputPath };

        if (options.RemoveAlpha)
        {
            if (options.BackgroundColor is not null)
            {
                var bgHex = $"#{options.BackgroundColor.R:X2}{options.BackgroundColor.G:X2}{options.BackgroundColor.B:X2}";
                args.AddRange(new[] { "-background", bgHex, "-alpha", "remove", "-alpha", "off" });
            }
            else
            {
                args.AddRange(new[] { "-alpha", "off" });
            }
        }
        else
        {
            // Adjust alpha opacity
            double factor = options.AlphaValue / 255.0;
            var factorStr = factor.ToString("0.###", CultureInfo.InvariantCulture);

            if (options.ScaleAlpha)
            {
                // Scale existing alpha gradient proportionally
                args.AddRange(new[] { "-channel", "A", "-evaluate", "multiply", factorStr, "+channel" });
            }
            else
            {
                // Hard cutout alpha
                var valStr = options.AlphaValue.ToString(CultureInfo.InvariantCulture);
                args.AddRange(new[] { "-channel", "A", "-evaluate", "set", valStr, "+channel" });
            }

            if (options.SmoothEdges && options.SmoothRadius > 0.0)
            {
                var radStr = options.SmoothRadius.ToString("0.0", CultureInfo.InvariantCulture);
                args.AddRange(new[] { "-channel", "A", "-blur", $"0x{radStr}", "+channel" });
            }
        }

        args.Add(finalOutput);

        var result = await _processRunner.RunAsync(magick, args, null, null, cancellationToken);
        return result.IsSuccess && File.Exists(finalOutput);
    }

    public async Task<int> ProcessBatchAsync(
        string inputDirectory,
        string outputDirectory,
        AlphaOptions options,
        IProgress<ProcessingProgress>? progress = null,
        IProgress<LogEntry>? logProgress = null,
        CancellationToken cancellationToken = default
    )
    {
        if (!Directory.Exists(inputDirectory) && !File.Exists(inputDirectory))
        {
            logProgress?.Report(new LogEntry($"Input path does not exist: {inputDirectory}", LogLevel.Error));
            return 0;
        }

        var searchOption = options.Recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
        var files = File.Exists(inputDirectory)
            ? new[] { inputDirectory }
            : Directory.GetFiles(inputDirectory, "*.*", searchOption)
                .Where(f => DelphisConstants.SupportedImageExtensions.Contains(Path.GetExtension(f)))
                .ToArray();

        int total = files.Length;
        if (total == 0)
        {
            logProgress?.Report(new LogEntry($"No supported images found in '{inputDirectory}'.", LogLevel.Warning));
            return 0;
        }

        logProgress?.Report(new LogEntry($"Alpha Processor: Processing {total} file(s)...", LogLevel.Info));

        int successCount = 0;
        for (int i = 0; i < total; i++)
        {
            cancellationToken.ThrowIfCancellationRequested();

            var file = files[i];
            string dest;
            if (File.Exists(inputDirectory))
            {
                dest = Directory.Exists(outputDirectory)
                    ? Path.Combine(outputDirectory, Path.GetFileName(file))
                    : outputDirectory;
            }
            else
            {
                var rel = Path.GetRelativePath(inputDirectory, file);
                dest = Path.Combine(outputDirectory, rel);
            }

            bool ok = await ProcessSingleImageAsync(file, dest, options, cancellationToken);
            if (ok)
            {
                successCount++;
                logProgress?.Report(new LogEntry($"[OK] {Path.GetFileName(file)} -> {Path.GetFileName(dest)}", LogLevel.Success));
            }
            else
            {
                logProgress?.Report(new LogEntry($"[ERROR] Failed processing {Path.GetFileName(file)}", LogLevel.Error));
            }

            progress?.Report(new ProcessingProgress(i + 1, total, $"Processed {i + 1}/{total}"));
        }

        logProgress?.Report(new LogEntry(
            $"Alpha Processing completed: {successCount}/{total} images processed successfully.",
            successCount == total ? LogLevel.Success : LogLevel.Warning
        ));

        return successCount;
    }
}
