using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;
using RhinoAlmondBridge;

internal static class Program
{
    static readonly List<object> Results = new();
    static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }
    static void Test(string name, Action action)
    {
        action();
        Results.Add(new { name, status = "passed" });
    }
    static int Main(string[] args)
    {
        string sandbox = Path.GetFullPath(args[0]);
        Directory.CreateDirectory(sandbox);
        string root = Path.Combine(sandbox, "checkout with spaces 한글");
        string runtime = Path.Combine(root, "src", "mcp", "runtime");
        string python = Path.Combine(root, "src", "engine", ".venv", "Scripts", "python.exe");
        string launcher = Path.Combine(runtime, "solve.py");
        Directory.CreateDirectory(runtime);
        Directory.CreateDirectory(Path.GetDirectoryName(python));
        File.WriteAllText(python, "resolver-only fixture; never execute");
        File.WriteAllText(launcher, "# resolver-only fixture; never execute\n");
        string oldOverride = Environment.GetEnvironmentVariable("ALMOND_SOLVER_COMMAND");
        string oldPath = Environment.GetEnvironmentVariable("PATH");
        try
        {
            Test("absolute checkout with spaces and Korean characters", () => {
                var command = NativeSolver.ResolveFromRuntime(runtime, out string reason);
                Check(command != null && reason == null, "Local command was not selected: " + reason);
                Check(command.File == python, "Wrong Python selected");
                Check(command.WorkingDirectory == Path.Combine(root, "src"), "Wrong working directory");
                Check(command.Arguments == "-I -B -X utf8 \"" + launcher + "\"", "Wrong isolated bootstrap arguments");
                Check(!command.Label.Contains("uvx"), "Remote command leaked into local label");
            });
            Test("loaded-assembly runtime seam", () => {
                RhinoTerminal.AlmondHost.RuntimeDirectory = runtime;
                var command = NativeSolver.Resolve(out string reason);
                Check(command != null && command.File == python && reason == null, "Public resolver did not use registered runtime");
            });
            Test("legacy environment override and PATH are ignored", () => {
                string fakeBin = Path.Combine(sandbox, "fake uvx bin");
                Directory.CreateDirectory(fakeBin);
                File.WriteAllText(Path.Combine(fakeBin, "uvx.exe"), "must not execute");
                Environment.SetEnvironmentVariable("ALMOND_SOLVER_COMMAND", "uvx almond-mcp@0.7.0rc2");
                Environment.SetEnvironmentVariable("PATH", fakeBin);
                var command = NativeSolver.ResolveFromRuntime(runtime, out string reason);
                Check(command != null && command.File == python && reason == null, "Legacy remote override influenced selection");
            });
            Test("missing Python fails even when uvx is present", () => {
                File.Move(python, python + ".held");
                try {
                    var command = NativeSolver.ResolveFromRuntime(runtime, out string reason);
                    Check(command == null && !string.IsNullOrWhiteSpace(reason), "Missing Python did not fail closed");
                    Check(reason.Contains("rebuild_environment.ps1"), "Failure omitted repair instruction");
                } finally { File.Move(python + ".held", python); }
            });
            Test("missing bootstrap fails", () => {
                File.Move(launcher, launcher + ".held");
                try {
                    var command = NativeSolver.ResolveFromRuntime(runtime, out string reason);
                    Check(command == null && !string.IsNullOrWhiteSpace(reason), "Missing bootstrap did not fail closed");
                } finally { File.Move(launcher + ".held", launcher); }
            });
            Test("absent or invalid runtime fails without fallback", () => {
                foreach (string invalid in new[] { Path.Combine(sandbox, "missing", "runtime"), "bad\0runtime", null }) {
                    var command = NativeSolver.ResolveFromRuntime(invalid, out string reason);
                    Check(command == null && !string.IsNullOrWhiteSpace(reason), "Invalid runtime was accepted");
                }
            });
            Test("ProcessStartInfo preserves exact argument boundaries", () => {
                // Execute only a controlled Python argument recorder, never NativeSolver.RunAsync/Rhino.
                string recorder = Path.Combine(sandbox, "record args 한글.py");
                File.WriteAllText(recorder, "import json,sys; print(json.dumps(sys.argv[1:]))\n");
                var command = NativeSolver.ResolveFromRuntime(runtime, out string reason);
                var start = new ProcessStartInfo(args[1], "-I -B \"" + recorder + "\" " + command.Arguments) {
                    UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true,
                    WorkingDirectory = command.WorkingDirectory
                };
                using var child = Process.Start(start);
                string stdout = child.StandardOutput.ReadToEnd();
                string stderr = child.StandardError.ReadToEnd();
                Check(child.WaitForExit(10000) && child.ExitCode == 0, "Argument recorder failed: " + stderr);
                var argv = JsonSerializer.Deserialize<string[]>(stdout);
                Check(argv.SequenceEqual(new[] { "-I", "-B", "-X", "utf8", launcher }), "Argument boundaries changed");
            });
            Console.WriteLine(JsonSerializer.Serialize(new {
                status = "passed", runtime = System.Runtime.InteropServices.RuntimeInformation.FrameworkDescription,
                source = "src/mcp/features/structure/native/NativeSolver.cs",
                tests = Results, actualRhinoLoaded = false, actualSolverProcessStarted = false
            }, new JsonSerializerOptions { WriteIndented = true }));
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex);
            return 1;
        }
        finally
        {
            Environment.SetEnvironmentVariable("ALMOND_SOLVER_COMMAND", oldOverride);
            Environment.SetEnvironmentVariable("PATH", oldPath);
        }
    }
}

namespace RhinoTerminal
{
    internal static class AlmondHost
    {
        internal static string RuntimeDirectory { get; set; }
    }
}
