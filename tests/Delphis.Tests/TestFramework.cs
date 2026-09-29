using System.Diagnostics.CodeAnalysis;
using System.Runtime.CompilerServices;

namespace Delphis.Tests;

[AttributeUsage(AttributeTargets.Method)]
public class FactAttribute : Attribute { }

public static class Assert
{
    public static void True(bool condition, [CallerArgumentExpression(nameof(condition))] string? expr = null)
    {
        if (!condition)
            throw new Exception($"Assert.True failed for: {expr}");
    }

    public static void False(bool condition, [CallerArgumentExpression(nameof(condition))] string? expr = null)
    {
        if (condition)
            throw new Exception($"Assert.False failed for: {expr}");
    }

    public static void Equal<T>(T expected, T actual)
    {
        if (!EqualityComparer<T>.Default.Equals(expected, actual))
            throw new Exception($"Assert.Equal failed. Expected: '{expected}', Actual: '{actual}'");
    }

    public static void NotNull([NotNull] object? obj, [CallerArgumentExpression(nameof(obj))] string? expr = null)
    {
        if (obj is null)
            throw new Exception($"Assert.NotNull failed for: {expr}");
    }

    public static void Null(object? obj, [CallerArgumentExpression(nameof(obj))] string? expr = null)
    {
        if (obj is not null)
            throw new Exception($"Assert.Null failed for: {expr}");
    }

    public static void Contains<T>(T item, IEnumerable<T> collection)
    {
        if (!collection.Contains(item))
            throw new Exception($"Assert.Contains failed. Item '{item}' not found in collection.");
    }
}
