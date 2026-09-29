namespace Delphis.Core.Models;

/// <summary>
/// DirectDraw Surface (DDS) compression preset profile.
/// </summary>
public record DdsPreset(
    string Format,
    string Name,
    string Description,
    bool HasAlpha,
    bool IsDefault
);
