using System.Collections.ObjectModel;
using Delphis.Core.Models;

namespace Delphis.Core;

/// <summary>
/// Global Constants, Presets, and Configuration Definitions for Delphis.
/// </summary>
public static class DelphisConstants
{
    public const string AppName = "Delphis";
    public const string AppTitle = "Delphis — Dolphin Texture Manipulation Tool";
    public static readonly string AppVersion = ResolveAppVersion();

    private static string ResolveAppVersion()
    {
        var asm = typeof(DelphisConstants).Assembly;
        var infoVer = asm.GetCustomAttributes(typeof(System.Reflection.AssemblyInformationalVersionAttribute), false)
            .OfType<System.Reflection.AssemblyInformationalVersionAttribute>()
            .FirstOrDefault()?.InformationalVersion;

        if (!string.IsNullOrWhiteSpace(infoVer))
        {
            var cleaned = infoVer.Split('+')[0].Trim();
            if (!string.IsNullOrEmpty(cleaned)) return cleaned;
        }

        var ver = asm.GetName().Version;
        if (ver != null && ver != new Version(0, 0, 0, 0))
        {
            return ver.ToString(3);
        }

        return "1.0.0";
    }

    /// <summary>
    /// Supported image formats for Dolphin texture workflows.
    /// </summary>
    public static readonly IReadOnlySet<string> SupportedImageExtensions = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
    {
        ".png", ".webp", ".tga", ".bmp", ".tif", ".tiff", ".jpg", ".jpeg", ".dds"
    };

    /// <summary>
    /// PNG file extensions.
    /// </summary>
    public static readonly IReadOnlySet<string> PngExtensions = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
    {
        ".png"
    };

    /// <summary>
    /// Community Dolphin DDS Compression Presets.
    /// </summary>
    public static readonly ReadOnlyDictionary<string, DdsPreset> DdsPresets = new(
        new Dictionary<string, DdsPreset>(StringComparer.OrdinalIgnoreCase)
        {
            ["BC7"] = new(
                Format: "BC7",
                Name: "BC7 (High Quality RGBA - Recommended)",
                Description: "State-of-the-art block compression for color & smooth alpha. Best quality for modern HD texture packs in Dolphin.",
                HasAlpha: true,
                IsDefault: true
            ),
            ["BC1"] = new(
                Format: "BC1",
                Name: "BC1 / DXT1 (Opaque Textures - High Performance)",
                Description: "Smallest VRAM size for completely opaque textures without transparency.",
                HasAlpha: false,
                IsDefault: false
            ),
            ["BC1a"] = new(
                Format: "BC1a",
                Name: "BC1a / DXT1 (1-Bit Punch-through Alpha)",
                Description: "Fast 1-bit transparency (binary cutout / decals / foliage).",
                HasAlpha: true,
                IsDefault: false
            ),
            ["BC3"] = new(
                Format: "BC3",
                Name: "BC3 / DXT5 (Interpolated Alpha - Classic Compatibility)",
                Description: "Standard interpolated alpha channel compression with broad legacy compatibility.",
                HasAlpha: true,
                IsDefault: false
            ),
            ["BC5"] = new(
                Format: "BC5",
                Name: "BC5 (Two-Channel Normal / Bump Maps)",
                Description: "High fidelity compression specifically designed for tangent-space Normal Maps.",
                HasAlpha: false,
                IsDefault: false
            )
        }
    );

    /// <summary>
    /// Supported Real-ESRGAN AI Neural Models.
    /// </summary>
    public static readonly ReadOnlyCollection<(string Id, string Description)> AiModels = new(
        new List<(string Id, string Description)>
        {
            ("realesrgan-x4plus-anime", "RealESRGAN x4plus Anime (Optimized for cel-shaded/anime GameCube & Wii textures)"),
            ("realesrgan-x4plus", "RealESRGAN x4plus (General purpose / realistic textures)"),
            ("realesr-animevideov3", "RealESR AnimeVideo v3 (Lightweight anime & cartoon textures)")
        }
    );

    /// <summary>
    /// Resolution scale multipliers.
    /// </summary>
    public static readonly ReadOnlyCollection<int> ScaleFactors = new(new[] { 2, 3, 4 });

    /// <summary>
    /// Quick alpha transparency preset levels.
    /// </summary>
    public static readonly ReadOnlyCollection<(byte Alpha, string Label)> AlphaQuickPresets = new(
        new List<(byte Alpha, string Label)>
        {
            (255, "255 (Opaque)"),
            (192, "192 (75%)"),
            (130, "130 (Dolphin Glass/UI)"),
            (64, "64 (25%)"),
            (0, "0 (Transparent)")
        }
    );
}
