using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;

namespace RhinoAlmondBridge
{
    /// <summary>
    /// Almond's native structural solver, run out of process: one JSON request on stdin of
    /// <c>almond-mcp solve</c>, one JSON reply on stdout. The panel uses it so the Karamba-free
    /// engine (floor and asset loads, EN 1990 combinations, connections, stability) needs no MCP
    /// client. The registered checkout's Python runs its fixed, provenance-checked solver
    /// launcher. Missing or mismatched local files fail without downloading a package.
    /// </summary>
    internal static class NativeSolver
    {
        internal const int Protocol = 1;

        internal sealed class Command
        {
            public string File;
            public string Arguments;
            public string Label;
            public string WorkingDirectory;
        }

        /// <summary>The solver command, or null with a reason when none can be found.</summary>
        internal static Command Resolve(out string reason)
            => ResolveFromRuntime(RhinoTerminal.AlmondHost.RuntimeDirectory, out reason);

        internal static Command ResolveFromRuntime(string runtime, out string reason)
        {
            reason = null;
            try
            {
                string sourceRoot = Path.GetFullPath(Path.Combine(runtime, "..", ".."));
                string python = Path.Combine(sourceRoot, "engine", ".venv", "Scripts", "python.exe");
                string launcher = Path.Combine(runtime, "solve.py");
                if (!File.Exists(python) || !File.Exists(launcher))
                {
                    reason = "The registered Almond checkout needs its Python environment and src/mcp/runtime/solve.py. " +
                             "Restore the checkout and run src/mcp/rebuild_environment.ps1 before using the native solver.";
                    return null;
                }
                string arguments = "-I -B -X utf8 \"" + launcher + "\"";
                return new Command { File = python, Arguments = arguments,
                    Label = "\"" + python + "\" " + arguments, WorkingDirectory = sourceRoot };
            }
            catch (Exception ex) when (ex is ArgumentException || ex is IOException || ex is UnauthorizedAccessException)
            { reason = "Could not locate the registered Almond solver: " + ex.Message; }
            return null;
        }

        /// <summary>Run one request. Never throws: failures come back as {"status":"error","message":...}.</summary>
        internal static async Task<JObject> RunAsync(JObject request, int timeoutMs)
        {
            var command = Resolve(out string reason);
            if (command == null) return Error(reason);
            request["protocol"] = Protocol;
            var info = new ProcessStartInfo(command.File, command.Arguments)
            {
                UseShellExecute = false, CreateNoWindow = true, RedirectStandardInput = true,
                RedirectStandardOutput = true, RedirectStandardError = true,
                StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8,
                WorkingDirectory = command.WorkingDirectory,
            };
            info.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
            info.EnvironmentVariables["PYTHONUTF8"] = "1";
            Process process;
            try { process = Process.Start(info); }
            catch (Exception ex) { return Error("Could not start the native solver (" + command.Label + "): " + ex.Message); }
            using (process)
            {
                var stdout = process.StandardOutput.ReadToEndAsync();
                var stderr = process.StandardError.ReadToEndAsync();
                try
                {
                    byte[] payload = new UTF8Encoding(false).GetBytes(request.ToString(Newtonsoft.Json.Formatting.None));
                    await process.StandardInput.BaseStream.WriteAsync(payload, 0, payload.Length).ConfigureAwait(false);
                    process.StandardInput.Close();
                }
                catch (IOException) { /* the process exited early: its stderr says why */ }
                var done = Task.Run(() => process.WaitForExit(timeoutMs));
                if (!await done.ConfigureAwait(false))
                {
                    try { process.Kill(); } catch { }
                    return Error($"The local native solver did not answer within {timeoutMs / 1000} s ({command.Label}).");
                }
                string output = await stdout.ConfigureAwait(false);
                string errors = await stderr.ConfigureAwait(false);
                JObject reply = null;
                try { reply = JObject.Parse(output); } catch { }
                if (reply == null)
                {
                    string tail = Tail(errors);
                    return Error("The native solver returned no result (" + command.Label + ", exit " + process.ExitCode + ")." +
                                 (tail.Length > 0 ? " " + tail : ""));
                }
                if ((int?)reply["protocol"] != Protocol)
                    return Error($"Solver protocol mismatch: the plugin speaks {Protocol}, the solver {(string)reply["protocol"] ?? "?"}. " +
                                 "Rebuild the Bridge and its Python environment from the same checkout.");
                reply["solver"] = command.Label;
                return reply;
            }
        }

        private static string Tail(string text)
        {
            var lines = (text ?? "").Split('\n').Select(l => l.Trim()).Where(l => l.Length > 0).ToList();
            return string.Join(" ", lines.Skip(Math.Max(0, lines.Count - 3)));
        }

        private static JObject Error(string message) =>
            new JObject { ["protocol"] = Protocol, ["status"] = "error", ["message"] = message };
    }
}
