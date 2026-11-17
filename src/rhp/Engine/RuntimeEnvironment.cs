namespace AlmondEngine;

/// <summary>Fixed installed bundle layout shared by hosts and read-only native library queries.</summary>
public static class RuntimeEnvironment
{
    public static string RuntimeDirectory(string assemblyPath) => Path.GetFullPath(Path.Combine(
        Path.GetDirectoryName(assemblyPath)!, "..", "..", "..", "mcp", "runtime"));

    public static string SourceRoot(string runtime) => Path.GetFullPath(Path.Combine(runtime, "..", ".."));
    public static string PythonExecutable(string runtime) => Path.Combine(SourceRoot(runtime), "engine", ".venv", "Scripts", "python.exe");
}
