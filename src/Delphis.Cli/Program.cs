using System.Globalization;
using Delphis.Core;
using Delphis.Core.Models;
using Delphis.Core.Services;

namespace Delphis.Cli;

public class Program
{
    public static async Task<int> Main(string[] args)
    {
        Console.OutputEncoding = System.Text.Encoding.UTF8;

        bool quiet = args.Contains("-q") || args.Contains("--quiet") || args.Contains("--no-logs");
        var filteredArgs = args.Where(a => a is not "-q" and not "--quiet" and not "--no-logs").ToArray();

        if (filteredArgs.Length == 0 || filteredArgs[0] is "-h" or "--help" or "help")
        {
            PrintUsage();
            return 0;
        }

        if (filteredArgs[0] is "-v" or "--version" or "version")
        {
            Console.WriteLine($"{DelphisConstants.AppName} v{DelphisConstants.AppVersion}");
            return 0;
        }

        var command = filteredArgs[0].ToLowerInvariant();
        var cmdArgs = filteredArgs.Skip(1).ToArray();

        var env = new EnvironmentDetector();
        var runner = new ProcessRunner();
        IProgress<LogEntry>? progressLog = quiet ? null : new Progress<LogEntry>(e =>
        {
            var color = e.Level switch
            {
                LogLevel.Success => ConsoleColor.Green,
                LogLevel.Warning => ConsoleColor.Yellow,
                LogLevel.Error => ConsoleColor.Red,
                _ => ConsoleColor.Gray
            };
            Console.ForegroundColor = color;
            Console.WriteLine($"[{e.Timestamp:HH:mm:ss}] {e.Message}");
            Console.ResetColor();
        });

        try
        {
            return command switch
            {
                "doctor" => RunDoctor(env),
                "alpha" => await RunAlphaAsync(cmdArgs, env, runner, progressLog),
                "dds" => await RunDdsAsync(cmdArgs, env, runner, progressLog),
                "upscale" => await RunUpscaleAsync(cmdArgs, env, runner, progressLog),
                "dte" => await RunDteAsync(cmdArgs, env, runner, progressLog),
                _ => HandleUnknownCommand(command)
            };
        }
        catch (Exception ex)
        {
            Console.ForegroundColor = ConsoleColor.Red;
            Console.WriteLine($"[FATAL ERROR] {ex.Message}");
            Console.ResetColor();
            return 1;
        }
    }

    private static void PrintUsage()
    {
        Console.WriteLine($"🐬 {DelphisConstants.AppTitle} (CLI v{DelphisConstants.AppVersion})");
        Console.WriteLine("===============================================================");
        Console.WriteLine("Usage: delphis-cli <command> [options]");
        Console.WriteLine();
        Console.WriteLine("Commands:");
        Console.WriteLine("  doctor                                   Check status of backend dependencies and Vulkan GPUs");
        Console.WriteLine("  alpha <in> <out> [options]               Adjust or remove alpha transparency with anti-aliasing");
        Console.WriteLine("  dds <in> <out> [options]                 Convert textures to Dolphin-optimized DDS format");
        Console.WriteLine("  upscale <in> <out> [options]             4-channel alpha-preserving Real-ESRGAN AI upscaler");
        Console.WriteLine("  dte <mode> <in> <out> [options]          Extract, unpack, finalize or combine tonemaps via DTE");
        Console.WriteLine();
        Console.WriteLine("Global Options:");
        Console.WriteLine("  --quiet, -q, --no-logs                   Disable real-time execution logs");
        Console.WriteLine();
        Console.WriteLine("Alpha Options: --alpha <0-255>, --remove-alpha, --smooth, --smooth-radius <float>, --hard, --no-defringe, --bg <color>, --no-recursive");
        Console.WriteLine("DDS Options:   --preset <BC7|BC1|BC1a|BC3|BC5>, --no-mips, --no-recursive");
        Console.WriteLine("Upscale Flags: --scale <2|3|4>, --model <name>, --alpha-mode <ai|lanczos|none>, --gpu <id>, --no-recursive");
        Console.WriteLine("DTE Modes:     merge_rgba, merge_bgra, split_tonemaps, extract, unpack, custom");
        Console.WriteLine("DTE Flags:     --tasks <n>, --cleanup <mode>, --no-recursive, --mips, --no-dmd, --custom-cmd <verb>, --extra <flags>");
    }

    private static int RunDoctor(IEnvironmentDetector env)
    {
        Console.WriteLine("🔍 Delphis System & Dependency Doctor");
        Console.WriteLine("====================================");

        var deps = env.CheckDependencies();
        foreach (var (k, info) in deps)
        {
            Console.ForegroundColor = info.IsInstalled ? ConsoleColor.Green : (info.IsOptional ? ConsoleColor.Yellow : ConsoleColor.Red);
            var mark = info.IsInstalled ? "✔" : "✘";
            Console.WriteLine($"  {mark} {info.Name,-50} : {(info.IsInstalled ? info.Path : "NOT FOUND")}");
            Console.ResetColor();
        }

        Console.WriteLine();
        Console.WriteLine("🎮 Vulkan Graphics Adapters:");
        var gpus = env.DetectVulkanGpus();
        foreach (var gpu in gpus)
        {
            Console.WriteLine($"  • Device {gpu.DeviceId}: {gpu.DeviceName} {(gpu.IsDiscrete ? "(Discrete)" : "")}");
        }

        return 0;
    }

    private static async Task<int> RunAlphaAsync(string[] args, IEnvironmentDetector env, IProcessRunner runner, IProgress<LogEntry>? log)
    {
        if (args.Length < 2)
        {
            Console.WriteLine("Usage: delphis-cli alpha <inputPath> <outputPath> [--alpha <val>] [--remove-alpha] [--smooth] [--smooth-radius <r>] [--hard] [--no-defringe] [--bg <color>] [--no-recursive]");
            return 1;
        }

        var input = args[0];
        var output = args[1];
        byte alpha = 255;
        bool remove = false;
        bool smooth = false;
        double smoothRadius = 1.0;
        bool scaleAlpha = true;
        bool defringe = true;
        RgbColor? bgColor = null;
        bool recursive = true;

        for (int i = 2; i < args.Length; i++)
        {
            if (args[i] == "--alpha" && i + 1 < args.Length && byte.TryParse(args[i + 1], out var val)) alpha = val;
            if (args[i] == "--remove-alpha") remove = true;
            if (args[i] == "--smooth") smooth = true;
            if (args[i] == "--smooth-radius" && i + 1 < args.Length && double.TryParse(args[i + 1], NumberStyles.Any, CultureInfo.InvariantCulture, out var rad)) smoothRadius = rad;
            if (args[i] == "--hard") scaleAlpha = false;
            if (args[i] == "--no-defringe") defringe = false;
            if (args[i] == "--bg" && i + 1 < args.Length) bgColor = AlphaProcessor.ParseColor(args[i + 1]);
            if (args[i] == "--no-recursive") recursive = false;
        }

        var processor = new AlphaProcessor(runner, env);
        var options = new AlphaOptions(
            RemoveAlpha: remove,
            AlphaValue: alpha,
            ScaleAlpha: scaleAlpha,
            SmoothEdges: smooth,
            SmoothRadius: smoothRadius,
            Defringe: defringe,
            BackgroundColor: bgColor,
            Recursive: recursive
        );

        if (File.Exists(input))
        {
            log?.Report(new LogEntry($"Alpha Processor: Processing single image '{Path.GetFileName(input)}'...", LogLevel.Info));
            var ok = await processor.ProcessSingleImageAsync(input, output, options);
            if (ok) log?.Report(new LogEntry($"[OK] Processed {Path.GetFileName(input)}", LogLevel.Success));
            else log?.Report(new LogEntry($"[ERROR] Failed processing {Path.GetFileName(input)}", LogLevel.Error));
            return ok ? 0 : 1;
        }

        var count = await processor.ProcessBatchAsync(input, output, options, null, log);
        return count > 0 ? 0 : 1;
    }

    private static async Task<int> RunDdsAsync(string[] args, IEnvironmentDetector env, IProcessRunner runner, IProgress<LogEntry>? log)
    {
        if (args.Length < 2)
        {
            Console.WriteLine("Usage: delphis-cli dds <inputPath> <outputPath> [--preset <BC7|BC1|BC1a|BC3|BC5>] [--no-mips] [--no-recursive]");
            return 1;
        }

        var input = args[0];
        var output = args[1];
        string preset = "BC7";
        bool mips = true;
        bool recursive = true;

        for (int i = 2; i < args.Length; i++)
        {
            if (args[i] == "--preset" && i + 1 < args.Length) preset = args[i + 1];
            if (args[i] == "--no-mips") mips = false;
            if (args[i] == "--no-recursive") recursive = false;
        }

        var optimizer = new DdsOptimizer(runner, env);
        var options = new DdsOptions(Preset: preset, GenerateMipmaps: mips, Recursive: recursive);

        if (File.Exists(input))
        {
            log?.Report(new LogEntry($"DDS Optimizer: Converting single image '{Path.GetFileName(input)}' [Preset: {preset}]...", LogLevel.Info));
            var ok = await optimizer.ConvertSingleAsync(input, output, options);
            if (ok) log?.Report(new LogEntry($"[OK] Converted {Path.GetFileName(input)}", LogLevel.Success));
            else log?.Report(new LogEntry($"[ERROR] Failed converting {Path.GetFileName(input)}", LogLevel.Error));
            return ok ? 0 : 1;
        }

        var count = await optimizer.ConvertBatchAsync(input, output, options, null, log);
        return count > 0 ? 0 : 1;
    }

    private static async Task<int> RunUpscaleAsync(string[] args, IEnvironmentDetector env, IProcessRunner runner, IProgress<LogEntry>? log)
    {
        if (args.Length < 2)
        {
            Console.WriteLine("Usage: delphis-cli upscale <inputPath> <outputPath> [--scale <2|3|4>] [--model <name>] [--alpha-mode <ai|lanczos|none>] [--gpu <id>] [--no-recursive]");
            return 1;
        }

        var input = args[0];
        var output = args[1];
        int scale = 4;
        string model = "realesrgan-x4plus-anime";
        string alphaMode = "ai";
        int? gpuId = null;
        bool recursive = true;

        for (int i = 2; i < args.Length; i++)
        {
            if (args[i] == "--scale" && i + 1 < args.Length && int.TryParse(args[i + 1], out var s)) scale = s;
            if (args[i] == "--model" && i + 1 < args.Length) model = args[i + 1];
            if (args[i] == "--alpha-mode" && i + 1 < args.Length) alphaMode = args[i + 1];
            if (args[i] == "--gpu" && i + 1 < args.Length && int.TryParse(args[i + 1], out var g)) gpuId = g;
            if (args[i] == "--no-recursive") recursive = false;
        }

        var upscaler = new UpscalerEngine(runner, env);
        var options = new UpscalerOptions(
            Scale: scale,
            Model: model,
            AlphaMode: alphaMode,
            GpuId: gpuId ?? -1,
            Recursive: recursive
        );

        if (File.Exists(input))
        {
            log?.Report(new LogEntry($"AI Upscaler: Upscaling single file '{Path.GetFileName(input)}' [Scale: {scale}x | Model: {model}]...", LogLevel.Info));
            var ok = await upscaler.UpscaleSingleAsync(input, output, options);
            if (ok) log?.Report(new LogEntry($"[OK] Upscaled {Path.GetFileName(input)}", LogLevel.Success));
            else log?.Report(new LogEntry($"[ERROR] Failed upscaling {Path.GetFileName(input)}", LogLevel.Error));
            return ok ? 0 : 1;
        }

        var count = await upscaler.UpscaleBatchAsync(input, output, options, null, log);
        return count > 0 ? 0 : 1;
    }

    private static async Task<int> RunDteAsync(string[] args, IEnvironmentDetector env, IProcessRunner runner, IProgress<LogEntry>? log)
    {
        if (args.Length < 3)
        {
            Console.WriteLine("Usage: delphis-cli dte <merge_rgba|merge_bgra|split_tonemaps|extract|unpack|custom> <in> <out> [--tasks <n>] [--cleanup <mode>] [--no-recursive] [--mips] [--no-dmd] [--custom-cmd <verb>] [--extra <flags>]");
            return 1;
        }

        var mode = args[0];
        var input = args[1];
        var output = args[2];
        int tasks = 1;
        string cleanup = "none";
        bool recursive = true;
        bool mips = false;
        bool dmd = true;
        string? customCmd = null;
        string? extra = null;

        bool disableLogFile = false;

        for (int i = 3; i < args.Length; i++)
        {
            if (args[i] is "--no-logfile" or "--no-log" or "--no-logs") disableLogFile = true;
            if (args[i] is "--logfile" or "--keep-logfile" or "--with-logfile") disableLogFile = false;
            if ((args[i] == "--tasks" || args[i] == "-Tasks") && i + 1 < args.Length && int.TryParse(args[i + 1], out var t)) tasks = t;
            if (args[i] == "--cleanup" && i + 1 < args.Length) cleanup = args[i + 1];
            if (args[i] == "--no-recursive") recursive = false;
            if (args[i] == "--mips" || args[i] == "-Mip") mips = true;
            if (args[i] == "--no-dmd") dmd = false;
            if (args[i] == "--custom-cmd" && i + 1 < args.Length) customCmd = args[i + 1];
            if (args[i] == "--extra" && i + 1 < args.Length) extra = args[i + 1];
        }

        var orchestrator = new DteOrchestrator(runner, env);
        var options = new DteOptions(
            Mode: mode,
            Tasks: tasks,
            CleanupMode: cleanup,
            Recursive: recursive,
            ExtractMipmaps: mips,
            DolphinMipDetection: dmd,
            CustomCommand: customCmd ?? "Extract",
            ExtraArgs: extra ?? string.Empty,
            DisableLogFile: disableLogFile
        );

        var res = await orchestrator.ExecuteAsync(input, output, options, log);
        return res.IsSuccess ? 0 : res.ExitCode;
    }

    private static int HandleUnknownCommand(string cmd)
    {
        Console.ForegroundColor = ConsoleColor.Red;
        Console.WriteLine($"Unknown command: '{cmd}'. Run 'delphis-cli --help' for usage.");
        Console.ResetColor();
        return 1;
    }
}
