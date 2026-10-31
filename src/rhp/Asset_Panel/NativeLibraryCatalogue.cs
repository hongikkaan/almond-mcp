using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;

namespace RhinoAlmondBridge
{
    // A fixed read-only process on a background task; no Rhino document or MCP
    // connection is created. AssetRepository remains the catalogue policy owner.
    internal static class NativeLibraryCatalogue
    {
        internal static Task<JObject> ReadSnapshotAsync() => Task.Run(ReadSnapshotCoreAsync);

        private static async Task<JObject> ReadSnapshotCoreAsync()
        {
            string runtime = RhinoTerminal.AlmondHost.RuntimeDirectory;
            string sourceRoot = Path.GetFullPath(Path.Combine(runtime, "..", ".."));
            string python = Path.Combine(sourceRoot, "engine", ".venv", "Scripts", "python.exe");
            if (!File.Exists(python))
                return Error("library_python_missing", "Installed library lookup needs the Almond Python environment. Configure it, then Reload.");
            var start = new ProcessStartInfo(python) {
                WorkingDirectory = sourceRoot, UseShellExecute = false, CreateNoWindow = true,
                RedirectStandardOutput = true, RedirectStandardError = true
            };
            start.ArgumentList.Add("-B");
            start.ArgumentList.Add("-m");
            start.ArgumentList.Add("almond_mcp.features.assets.asset_repository");
            start.ArgumentList.Add("--snapshot");
            start.Environment["PYTHONIOENCODING"] = "utf-8";
            start.Environment["PYTHONUTF8"] = "1";
            using (var process = new Process { StartInfo = start })
            using (var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(30)))
            {
                try
                {
                    if (!process.Start()) return Error("library_export_failed", "The installed library reader could not start. Reload after checking the Almond environment.");
                    var output = ReadBounded(process.StandardOutput.BaseStream, 16 * 1024 * 1024, timeout.Token);
                    var errors = ReadBounded(process.StandardError.BaseStream, 65536, timeout.Token);
                    await Task.WhenAll(output, errors, process.WaitForExitAsync(timeout.Token)).ConfigureAwait(false);
                    if (process.ExitCode != 0)
                        return Error("library_export_failed", "Installed library lookup failed. Check its manifest and Almond environment, then Reload.");
                    return JObject.Parse(await output.ConfigureAwait(false));
                }
                catch (OperationCanceledException)
                {
                    return Error("library_export_timeout", "Installed library lookup exceeded 30 seconds. Reload to try again.");
                }
                catch (Exception)
                {
                    return Error("library_export_invalid", "The installed library reader returned an invalid or oversized snapshot. Reload after checking the Almond environment.");
                }
                finally
                {
                    try { if (!process.HasExited) process.Kill(entireProcessTree: true); }
                    catch (InvalidOperationException) { }
                    catch (System.ComponentModel.Win32Exception) { }
                }
            }
        }

        private static async Task<string> ReadBounded(Stream stream, int limit, CancellationToken token)
        {
            using (var memory = new MemoryStream())
            {
                var buffer = new byte[8192];
                while (true)
                {
                    int count = await stream.ReadAsync(buffer.AsMemory(0, buffer.Length), token).ConfigureAwait(false);
                    if (count == 0) break;
                    if (memory.Length + count > limit) throw new InvalidDataException("Library snapshot exceeded its output limit.");
                    memory.Write(buffer, 0, count);
                }
                return Encoding.UTF8.GetString(memory.ToArray());
            }
        }

        private static JObject Error(string code, string message) => new JObject {
            ["status"] = "error", ["error_code"] = code, ["message"] = message
        };
    }
}
