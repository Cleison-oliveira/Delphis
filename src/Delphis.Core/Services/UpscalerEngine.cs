using Delphis.Core.Models;

namespace Delphis.Core.Services;

/// <summary>
/// 4-Channel AI Upscaler Engine for Delphis.
/// Preserves transparency by separating RGB and Alpha channels, processing with Real-ESRGAN Vulkan NCNN,
/// and cleanly recomposing without edge artifacts or halo color bleeding.
/// </summary>
public class UpscalerEngine : IUpscalerEngine
{
    private readonly IProcessRunner _processRunner;
    private readonly IEnvironmentDetector _envDetector;

    public UpscalerEngine(IProcessRunner? processRunner = null, IEnvironmentDetector? envDetector = null)
    {
        _processRunner = processRunner ?? new ProcessRunner();
        _envDetector = envDetector ?? new EnvironmentDetector();
    }

    public string? FindModelsDirectory(string realesrganExecutable)
    {
        var binDir = Path.GetDirectoryName(realesrganExecutable);
        if (binDir is null) return null;

        var parentDir = Path.GetDirectoryName(binDir) ?? binDir;
        var candidates = new[]
        {
            Path.Combine(binDir, "models"),
            Path.Combine(parentDir, "share", "models"),
            Path.Combine(parentDir, "share", "realesrgan-ncnn-vulkan", "models"),
            Path.Combine(parentDir, "share", "Real-ESRGAN-ncnn-vulkan", "models"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".local", "share", "delphis", "bin", "models"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".local", "share", "delphis", "models")
        };

        foreach (var c in candidates)
        {
            if (Directory.Exists(c) && Directory.GetFiles(c, "*.bin").Length > 0)
            {
                return c;
            }
        }

        return null;
    }

    public int AutoDetectBestGpu()
    {
        var detected = _envDetector.DetectVulkanGpus().Where(g => g.DeviceId >= 0).ToList();
        if (detected.Count == 0) return 0;

        int bestGpu = 0;
        int bestScore = -1;

        foreach (var gpu in detected)
        {
            int score = 10;
            var lower = gpu.DeviceName.ToLowerInvariant();

            if (lower.Contains("nvidia") || lower.Contains("geforce") || lower.Contains("rtx") || lower.Contains("gtx"))
                score = 100;
            else if ((lower.Contains("radeon") || lower.Contains("amd")) && gpu.IsDiscrete)
                score = 85;
            else if (gpu.IsDiscrete)
                score = 80;
            else if (lower.Contains("radeon") || lower.Contains("amd"))
                score = 50;
            else if (lower.Contains("intel"))
                score = 30;
            else if (lower.Contains("llvmpipe") || lower.Contains("cpu"))
                score = 1;

            if (score > bestScore)
            {
                bestScore = score;
                bestGpu = gpu.DeviceId;
            }
        }

        return bestGpu;
    }

    private static bool IsProcessOutputFailed(ProcessExecutionResult result, string outputFile)
    {
        if (!result.IsSuccess) return true;
        if (!File.Exists(outputFile)) return true;
        try
        {
            if (new FileInfo(outputFile).Length == 0) return true;
        }
        catch
        {
            return true;
        }

        var err = result.StandardError ?? string.Empty;
        var outText = result.StandardOutput ?? string.Empty;
        if (err.Contains("fopen", StringComparison.OrdinalIgnoreCase) ||
            err.Contains("find_blob_index_by_name", StringComparison.OrdinalIgnoreCase) ||
            outText.Contains("find_blob_index_by_name", StringComparison.OrdinalIgnoreCase))
        {
            return true;
        }

        return false;
    }

    private async Task<(int Width, int Height, bool HasAlpha)> ProbeImageAsync(string magickExecutable, string imagePath, CancellationToken cancellationToken)
    {
        try
        {
            var identifyExe = _envDetector.FindExecutable("magick") ?? _envDetector.FindExecutable("identify") ?? magickExecutable;
            var args = Path.GetFileName(identifyExe).StartsWith("magick", StringComparison.OrdinalIgnoreCase)
                ? new[] { "identify", "-format", "%w %h %[channels]", imagePath }
                : new[] { "-format", "%w %h %[channels]", imagePath };

            var res = await _processRunner.RunAsync(identifyExe, args, null, null, cancellationToken);
            if (res.IsSuccess && !string.IsNullOrWhiteSpace(res.StandardOutput))
            {
                var parts = res.StandardOutput.Trim().Split(' ', StringSplitOptions.RemoveEmptyEntries);
                if (parts.Length >= 2 && int.TryParse(parts[0], out var w) && int.TryParse(parts[1], out var h))
                {
                    bool hasAlpha = parts.Length >= 3 && (parts[2].Contains('a', StringComparison.OrdinalIgnoreCase) || parts[2].Contains("alpha", StringComparison.OrdinalIgnoreCase));
                    return (w, h, hasAlpha);
                }
            }
        }
        catch { }

        return (0, 0, true);
    }

    public async Task<bool> UpscaleSingleAsync(
        string inputPath,
        string outputPath,
        UpscalerOptions options,
        string? modelsDirectory = null,
        CancellationToken cancellationToken = default
    )
    {
        var realesrgan = _envDetector.FindExecutable("realesrgan-ncnn-vulkan") ?? _envDetector.FindExecutable("realesrgan");
        var magick = _envDetector.FindExecutable("magick") ?? _envDetector.FindExecutable("convert");

        if (realesrgan is null)
            throw new FileNotFoundException("Real-ESRGAN executable ('realesrgan-ncnn-vulkan') not found in PATH.");
        if (magick is null)
            throw new FileNotFoundException("ImageMagick executable ('magick') not found in PATH.");

        var modelsDir = modelsDirectory ?? FindModelsDirectory(realesrgan);
        if (!string.IsNullOrEmpty(modelsDir) && Directory.Exists(modelsDir))
        {
            var modelPrefix = options.Model;
            var matches = Directory.GetFiles(modelsDir, $"{modelPrefix}*.bin");
            if (matches.Length == 0)
            {
                var available = Directory.GetFiles(modelsDir, "*.bin")
                    .Select(Path.GetFileNameWithoutExtension)
                    .Distinct();
                throw new FileNotFoundException(
                    $"Neural model '{options.Model}' files (.bin/.param) not found in '{modelsDir}'. Available models: {string.Join(", ", available)}"
                );
            }
        }

        int activeGpu = options.GpuId < 0 ? AutoDetectBestGpu() : options.GpuId;

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

        // 1. Probe input image dimensions to guarantee pixel-perfect alignment for 2x, 3x, 4x
        var (origW, origH, hasAlpha) = await ProbeImageAsync(magick, inputPath, cancellationToken);
        int targetW = origW > 0 ? origW * options.Scale : 0;
        int targetH = origH > 0 ? origH * options.Scale : 0;

        // Model native scale: Real-ESRGAN x4 models MUST run at -s 4; animevideov3 runs at specified scale
        int nativeModelScale = options.Model.Contains("animevideov3", StringComparison.OrdinalIgnoreCase)
            ? options.Scale
            : (options.Model.Contains("x2", StringComparison.OrdinalIgnoreCase) ? 2 : 4);

        var tempDir = Path.Combine(Path.GetTempPath(), $"delphis_cs_upscale_{Guid.NewGuid():N}");
        Directory.CreateDirectory(tempDir);

        var stem = Path.GetFileNameWithoutExtension(inputPath);
        var rgbIn = Path.Combine(tempDir, $"{stem}_rgb_in.png");
        var rgbOut = Path.Combine(tempDir, $"{stem}_rgb_out.png");
        var alphaIn = Path.Combine(tempDir, $"{stem}_alpha_in.png");
        var alphaOut = Path.Combine(tempDir, $"{stem}_alpha_out.png");

        try
        {
            // Case A: Image has NO alpha channel (opaque) -> 1-pass direct RGB upscale (Maximum performance)
            if (!hasAlpha)
            {
                await _processRunner.RunAsync(magick, new[] { inputPath, "-colorspace", "sRGB", "-depth", "8", $"PNG24:{rgbIn}" }, null, null, cancellationToken);
                cancellationToken.ThrowIfCancellationRequested();

                var aiArgs = new List<string> { "-i", rgbIn, "-o", rgbOut, "-n", options.Model, "-s", nativeModelScale.ToString(), "-g", activeGpu.ToString() };
                if (!string.IsNullOrEmpty(modelsDir)) aiArgs.AddRange(new[] { "-m", modelsDir });

                var resAi = await _processRunner.RunAsync(realesrgan, aiArgs, null, null, cancellationToken);
                if (IsProcessOutputFailed(resAi, rgbOut))
                {
                    await _processRunner.RunAsync(magick, new[] { rgbIn, "-filter", "Lanczos", "-resize", $"{options.Scale}00%", rgbOut }, null, null, cancellationToken);
                }

                // Ensure exact pixel alignment geometry for 2x, 3x, 4x without seam or checkerboard artifacts
                if (targetW > 0 && targetH > 0)
                {
                    await _processRunner.RunAsync(magick, new[] { rgbOut, "-filter", "Lanczos", "-resize", $"{targetW}x{targetH}!", "-depth", "8", finalOutput }, null, null, cancellationToken);
                }
                else
                {
                    File.Copy(rgbOut, finalOutput, overwrite: true);
                }

                return File.Exists(finalOutput) && new FileInfo(finalOutput).Length > 0;
            }

            // Case B: Image HAS alpha channel -> Optimized 2-layer separation (RGB Color + Alpha Transparency)
            // 2. Separate into only TWO layers: RGB color layer and Alpha transparency layer
            await _processRunner.RunAsync(magick, new[] { inputPath, "-alpha", "off", "-colorspace", "sRGB", "-depth", "8", $"PNG24:{rgbIn}" }, null, null, cancellationToken);
            await _processRunner.RunAsync(magick, new[] { inputPath, "-alpha", "extract", "-colorspace", "gray", "-depth", "8", alphaIn }, null, null, cancellationToken);

            cancellationToken.ThrowIfCancellationRequested();

            // 3. Upscale RGB Color Layer with AI model at native neural scale
            var aiArgsRgb = new List<string> { "-i", rgbIn, "-o", rgbOut, "-n", options.Model, "-s", nativeModelScale.ToString(), "-g", activeGpu.ToString() };
            if (!string.IsNullOrEmpty(modelsDir))
            {
                aiArgsRgb.AddRange(new[] { "-m", modelsDir });
            }

            var resRgb = await _processRunner.RunAsync(realesrgan, aiArgsRgb, null, null, cancellationToken);
            if (IsProcessOutputFailed(resRgb, rgbOut))
            {
                await _processRunner.RunAsync(magick, new[] { rgbIn, "-filter", "Lanczos", "-resize", $"{options.Scale}00%", rgbOut }, null, null, cancellationToken);
            }

            // Enforce exact target geometry on RGB layer for seamless connection without checkerboard artifacts
            if (targetW > 0 && targetH > 0)
            {
                await _processRunner.RunAsync(magick, new[] { rgbOut, "-filter", "Lanczos", "-resize", $"{targetW}x{targetH}!", rgbOut }, null, null, cancellationToken);
            }

            cancellationToken.ThrowIfCancellationRequested();

            // 4. Upscale Alpha Transparency Layer
            if (options.AlphaMode.Equals("ai", StringComparison.OrdinalIgnoreCase))
            {
                var alphaRgbIn = Path.Combine(tempDir, $"{stem}_alpha_rgb_in.png");
                var alphaRgbOut = Path.Combine(tempDir, $"{stem}_alpha_rgb_out.png");

                await _processRunner.RunAsync(magick, new[] { alphaIn, "-type", "TrueColor", alphaRgbIn }, null, null, cancellationToken);

                var aiArgsAlpha = new List<string> { "-i", alphaRgbIn, "-o", alphaRgbOut, "-n", options.Model, "-s", nativeModelScale.ToString(), "-g", activeGpu.ToString() };
                if (!string.IsNullOrEmpty(modelsDir))
                {
                    aiArgsAlpha.AddRange(new[] { "-m", modelsDir });
                }

                var resAlpha = await _processRunner.RunAsync(realesrgan, aiArgsAlpha, null, null, cancellationToken);
                if (!IsProcessOutputFailed(resAlpha, alphaRgbOut))
                {
                    await _processRunner.RunAsync(magick, new[] { alphaRgbOut, "-colorspace", "Gray", alphaOut }, null, null, cancellationToken);
                }
                else
                {
                    await _processRunner.RunAsync(magick, new[] { alphaIn, "-filter", "Lanczos", "-resize", $"{options.Scale}00%", alphaOut }, null, null, cancellationToken);
                }
            }
            else
            {
                await _processRunner.RunAsync(magick, new[] { alphaIn, "-filter", "Lanczos", "-resize", $"{options.Scale}00%", alphaOut }, null, null, cancellationToken);
            }

            // Enforce exact target geometry on Alpha layer for seamless connection without checkerboard artifacts
            if (targetW > 0 && targetH > 0)
            {
                await _processRunner.RunAsync(magick, new[] { alphaOut, "-filter", "Lanczos", "-resize", $"{targetW}x{targetH}!", alphaOut }, null, null, cancellationToken);
            }

            cancellationToken.ThrowIfCancellationRequested();

            // 5. Recompose upscaled RGB color and Alpha transparency layers into final RGBA image
            var recomposeRes = await _processRunner.RunAsync(
                magick,
                new[] { rgbOut, alphaOut, "-alpha", "off", "-compose", "CopyOpacity", "-composite", "-depth", "8", finalOutput },
                null,
                null,
                cancellationToken
            );

            return recomposeRes.IsSuccess && File.Exists(finalOutput) && new FileInfo(finalOutput).Length > 0;
        }
        finally
        {
            try { Directory.Delete(tempDir, true); } catch { /* Ignore cleanup errors */ }
        }
    }

    public async Task<int> UpscaleBatchAsync(
        string inputDirectory,
        string outputDirectory,
        UpscalerOptions options,
        IProgress<ProcessingProgress>? progress = null,
        IProgress<LogEntry>? logProgress = null,
        CancellationToken cancellationToken = default
    )
    {
        var realesrgan = _envDetector.FindExecutable("realesrgan-ncnn-vulkan") ?? _envDetector.FindExecutable("realesrgan");
        if (realesrgan is null)
        {
            logProgress?.Report(new LogEntry("Real-ESRGAN executable ('realesrgan-ncnn-vulkan') not found in PATH.", LogLevel.Error));
            return 0;
        }

        var searchOption = options.Recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
        var files = File.Exists(inputDirectory)
            ? new[] { inputDirectory }
            : Directory.GetFiles(inputDirectory, "*.png", searchOption);

        int total = files.Length;
        if (total == 0)
        {
            logProgress?.Report(new LogEntry($"No PNG images found in '{inputDirectory}'.", LogLevel.Warning));
            return 0;
        }

        logProgress?.Report(new LogEntry($"AI Upscaler: Processing {total} file(s) [Scale: {options.Scale}x | Model: {options.Model}]...", LogLevel.Info));

        int successCount = 0;
        for (int i = 0; i < total; i++)
        {
            cancellationToken.ThrowIfCancellationRequested();

            var file = files[i];
            var stem = Path.GetFileName(file);

            string dest;
            if (File.Exists(inputDirectory))
            {
                dest = Directory.Exists(outputDirectory)
                    ? Path.Combine(outputDirectory, stem)
                    : outputDirectory;
            }
            else
            {
                var rel = Path.GetRelativePath(inputDirectory, file);
                dest = Path.Combine(outputDirectory, rel);
            }

            logProgress?.Report(new LogEntry($"Upscaling ({i + 1}/{total}): {Path.GetFileName(file)} -> {Path.GetFileName(dest)}", LogLevel.Info));

            bool ok = await UpscaleSingleAsync(file, dest, options, null, cancellationToken);
            if (ok)
            {
                successCount++;
                logProgress?.Report(new LogEntry($"[OK] {Path.GetFileName(dest)}", LogLevel.Success));
            }
            else
            {
                logProgress?.Report(new LogEntry($"[ERROR] Failed upscaling {Path.GetFileName(file)}", LogLevel.Error));
            }

            progress?.Report(new ProcessingProgress(i + 1, total, $"Upscaled {i + 1}/{total}"));
        }

        logProgress?.Report(new LogEntry(
            $"AI Upscaling completed: {successCount}/{total} files successfully processed.",
            successCount == total ? LogLevel.Success : LogLevel.Warning
        ));

        return successCount;
    }
}
