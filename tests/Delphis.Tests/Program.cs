using System.Reflection;

namespace Delphis.Tests;

public class Program
{
    public static int Main(string[] args)
    {
        Console.OutputEncoding = System.Text.Encoding.UTF8;
        Console.WriteLine("🧪 Delphis Automated C# (.NET 8) Test Suite");
        Console.WriteLine("===========================================");

        var assembly = Assembly.GetExecutingAssembly();
        var testTypes = assembly.GetTypes()
            .Where(t => t.IsClass && !t.IsAbstract && t.Name.EndsWith("Tests"))
            .ToList();

        int passed = 0;
        int failed = 0;

        foreach (var type in testTypes)
        {
            var instance = Activator.CreateInstance(type);
            var methods = type.GetMethods(BindingFlags.Public | BindingFlags.Instance)
                .Where(m => m.GetCustomAttribute<FactAttribute>() != null)
                .ToList();

            foreach (var method in methods)
            {
                var testName = $"{type.Name}.{method.Name}";
                try
                {
                    method.Invoke(instance, null);
                    Console.ForegroundColor = ConsoleColor.Green;
                    Console.WriteLine($"  [PASS] {testName}");
                    Console.ResetColor();
                    passed++;
                }
                catch (Exception ex)
                {
                    Console.ForegroundColor = ConsoleColor.Red;
                    var inner = ex.InnerException ?? ex;
                    Console.WriteLine($"  [FAIL] {testName}: {inner.Message}");
                    Console.ResetColor();
                    failed++;
                }
            }
        }

        Console.WriteLine();
        Console.WriteLine("-------------------------------------------");
        if (failed == 0)
        {
            Console.ForegroundColor = ConsoleColor.Green;
            Console.WriteLine($"✔ All {passed} tests passed successfully!");
            Console.ResetColor();
            return 0;
        }
        else
        {
            Console.ForegroundColor = ConsoleColor.Red;
            Console.WriteLine($"✘ Test run failed: {passed} passed, {failed} failed.");
            Console.ResetColor();
            return 1;
        }
    }
}
