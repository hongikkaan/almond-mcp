using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;

namespace RhinoAlmondBridge
{
    // A loopback-only server for verified release files and a read-only installed
    // library snapshot. Native process/Rhino concerns are injected by the UI host.
    // TcpListener avoids HttpListener URL reservations/admin rights on Windows.
    // No Rhino dependencies: the exact host can be integration-tested standalone.
    internal sealed class ArchiveHttpServer : IDisposable
    {
        private readonly string _root;
        private readonly Dictionary<string, JObject> _routes = new Dictionary<string, JObject>(StringComparer.Ordinal);
        private TcpListener _listener;
        private volatile bool _running;
        private readonly Func<Task<JObject>> _snapshotProvider;
        private readonly object _overlayGate = new object();
        private Dictionary<string, JObject> _overlayFiles = new Dictionary<string, JObject>(StringComparer.Ordinal);
        private Dictionary<string, byte[]> _overlayJson = new Dictionary<string, byte[]>(StringComparer.Ordinal);
        private Task _refresh;
        private sealed class InstalledFileTooLargeException : Exception { }
        public string Url { get; private set; }

        internal byte[] ReadVerified(string route)
        {
            if (TryReadOverlay(route, out byte[] bytes, out string _)) return bytes;
            return ReadRelease(route);
        }

        private byte[] ReadRelease(string route)
        {
            if (!_routes.TryGetValue(route, out JObject entry)) throw new InvalidDataException("Asset is not in this archive.");
            byte[] data = File.ReadAllBytes(Resolve((string)entry["path"]));
            using (var sha = SHA256.Create())
                if (!string.Equals(BitConverter.ToString(sha.ComputeHash(data)).Replace("-", ""), (string)entry["sha256"], StringComparison.OrdinalIgnoreCase))
                    throw new InvalidDataException("Archive file changed; reinstall this release.");
            return data;
        }

        public ArchiveHttpServer(string directory, Func<Task<JObject>> snapshotProvider = null)
        {
            _snapshotProvider = snapshotProvider;
            _root = Path.GetFullPath(directory).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            var manifest = JObject.Parse(File.ReadAllText(Path.Combine(_root, "bundle.json"), Encoding.UTF8));
            if ((int?)manifest["schema_version"] != 1) throw new InvalidDataException("Unsupported archive bundle.");
            foreach (var route in ((JObject)manifest["routes"]).Properties())
            {
                if (!route.Name.StartsWith("/", StringComparison.Ordinal) || route.Name.Contains(".."))
                    throw new InvalidDataException("Invalid archive route.");
                var entry = (JObject)route.Value;
                Resolve((string)entry["path"]);
                _routes.Add(route.Name, entry);
            }
            if (!_routes.ContainsKey("/api/catalogue") || !_routes.ContainsKey("/"))
                throw new InvalidDataException("Incomplete archive bundle.");
        }

        private Task RefreshInstalledAsync()
        {
            if (_snapshotProvider == null) return Task.CompletedTask;
            lock (_overlayGate)
            {
                if (_refresh == null || _refresh.IsCompleted) _refresh = RefreshInstalledCoreAsync();
                return _refresh;
            }
        }

        private async Task RefreshInstalledCoreAsync()
        {
            var catalogue = JObject.Parse(Encoding.UTF8.GetString(ReadRelease("/api/catalogue")));
            var files = new Dictionary<string, JObject>(StringComparer.Ordinal);
            try
            {
                var snapshot = await _snapshotProvider().ConfigureAwait(false);
                if ((string)snapshot["status"] == "error")
                {
                    catalogue["library_status"] = snapshot;
                }
                else
                {
                    if ((int?)snapshot["schema_version"] != 1 || !(snapshot["catalogue"]?["assets"] is JArray liveAssets) ||
                        !(snapshot["files"] is JObject liveFiles)) throw new InvalidDataException("Invalid installed library snapshot.");
                    foreach (var property in liveFiles.Properties())
                    {
                        if (!property.Name.StartsWith("/files/", StringComparison.Ordinal) || property.Name.Contains("..") || !(property.Value is JObject file))
                            throw new InvalidDataException("Invalid installed library route.");
                        ValidateInstalledFile(file);
                        files.Add(property.Name, (JObject)file.DeepClone());
                    }
                    var byId = new Dictionary<string, JObject>(StringComparer.Ordinal);
                    foreach (var asset in ((JArray)catalogue["assets"]).OfType<JObject>().Concat(liveAssets.OfType<JObject>()))
                    {
                        string id = (string)asset["id"];
                        if (String.IsNullOrWhiteSpace(id)) throw new InvalidDataException("A library record has no asset ID.");
                        byId[id] = (JObject)asset.DeepClone();
                    }
                    var merged = byId.Values.ToArray();
                    catalogue["assets"] = new JArray(merged);
                    catalogue["counts"] = new JObject {
                        ["assets"] = merged.Length, ["models"] = merged.Count(a => (string)a["kind"] == "model"),
                        ["elements"] = merged.Count(a => (string)a["kind"] == "element"),
                        ["drawing_packages"] = merged.Count(a => a["drawing"] is JObject),
                        ["views"] = merged.Sum(a => (a["drawing"]?["views"] as JArray)?.Count ?? 0)
                    };
                    catalogue["library_status"] = new JObject { ["status"] = "ready", ["scope"] = "release_and_installed" };
                }
            }
            catch (Exception)
            {
                files.Clear();
                catalogue["library_status"] = new JObject { ["status"] = "error", ["error_code"] = "library_snapshot_invalid",
                    ["message"] = "Installed library files changed or could not be read. Reload to refresh; release sources remain available." };
            }
            var json = new Dictionary<string, byte[]>(StringComparer.Ordinal) {
                ["/api/catalogue"] = Encoding.UTF8.GetBytes(catalogue.ToString(Newtonsoft.Json.Formatting.None))
            };
            foreach (var asset in ((JArray)catalogue["assets"]).OfType<JObject>())
            {
                string route = (string)asset["record_url"];
                if (String.IsNullOrWhiteSpace(route) || !route.StartsWith("/api/assets/", StringComparison.Ordinal) || route.Contains("..")) continue;
                json[route] = Encoding.UTF8.GetBytes(asset.ToString(Newtonsoft.Json.Formatting.None));
            }
            lock (_overlayGate) { _overlayFiles = files; _overlayJson = json; }
        }

        private static string ValidateInstalledFile(JObject file)
        {
            string source = (string)file["path"], basePath = (string)file["root"];
            if (String.IsNullOrWhiteSpace(source) || String.IsNullOrWhiteSpace(basePath) || !Path.IsPathRooted(source) || !Path.IsPathRooted(basePath))
                throw new InvalidDataException("Invalid installed library path.");
            string root = Path.GetFullPath(basePath).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            string path = Path.GetFullPath(source);
            if (!path.StartsWith(root, StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("Installed library path escapes its root.");
            for (string current = path; current != null && current.Length >= root.TrimEnd(Path.DirectorySeparatorChar).Length; current = Path.GetDirectoryName(current))
                if ((File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0) throw new InvalidDataException("Installed library links are not allowed.");
            var info = new FileInfo(path);
            long? size = (long?)file["size"], modified = (long?)file["mtime_ns"];
            if (!size.HasValue || !modified.HasValue || size.Value < 0 || info.Length != size.Value ||
                info.LastWriteTimeUtc.Ticks != modified.Value / 100 + 621355968000000000L)
                throw new InvalidDataException("Installed library file changed; Reload to refresh.");
            return path;
        }

        private bool TryReadOverlay(string route, out byte[] bytes, out string mime)
        {
            JObject file;
            lock (_overlayGate)
            {
                if (_overlayJson.TryGetValue(route, out bytes)) { mime = "application/json"; return true; }
                _overlayFiles.TryGetValue(route, out file);
            }
            mime = null;
            if (file == null) return false;
            string path = ValidateInstalledFile(file);
            // Large sources remain listed and can be placed through Rhino; keep
            // an individual browser response from allocating unbounded memory.
            if ((long)file["size"] > 268435456) throw new InstalledFileTooLargeException();
            bytes = File.ReadAllBytes(path);
            ValidateInstalledFile(file);
            mime = (string)file["mime"] ?? "application/octet-stream";
            if (mime.Contains("\r") || mime.Contains("\n")) throw new InvalidDataException("Invalid library content type.");
            return true;
        }

        private string Resolve(string relative)
        {
            if (string.IsNullOrWhiteSpace(relative) || Path.IsPathRooted(relative))
                throw new InvalidDataException("Invalid archive file path.");
            string path = Path.GetFullPath(Path.Combine(_root, relative.Replace('/', Path.DirectorySeparatorChar)));
            if (!path.StartsWith(_root, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("Archive file escapes the bundle.");
            // Do not follow links/junctions, including ones changed after startup.
            for (string current = path; current != null && current.Length >= _root.TrimEnd(Path.DirectorySeparatorChar).Length; current = Path.GetDirectoryName(current))
                if ((File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
                    throw new InvalidDataException("Archive links are not allowed.");
            return path;
        }

        public void Start()
        {
            if (_running) return;
            _listener = new TcpListener(IPAddress.Loopback, 0);
            _listener.Start(16);
            Url = "http://127.0.0.1:" + ((IPEndPoint)_listener.LocalEndpoint).Port + "/";
            _running = true;
            Task.Run(() => AcceptLoop());
        }

        private async Task AcceptLoop()
        {
            while (_running)
            {
                try
                {
                    var client = await _listener.AcceptTcpClientAsync().ConfigureAwait(false);
                    _ = Task.Run(() => Respond(client));
                }
                catch (ObjectDisposedException) { break; }
                catch (SocketException) { if (!_running) break; }
            }
        }

        private async Task Respond(TcpClient client)
        {
            using (client)
            {
                try
                {
                    client.ReceiveTimeout = 5000;
                    client.SendTimeout = 5000;
                    using (var stream = client.GetStream())
                    {
                        var header = new List<byte>();
                        while (header.Count < 16384)
                        {
                            int value = stream.ReadByte();
                            if (value < 0) return;
                            header.Add((byte)value);
                            int n = header.Count;
                            if (n >= 4 && header[n-4] == 13 && header[n-3] == 10 && header[n-2] == 13 && header[n-1] == 10) break;
                        }
                        if (header.Count >= 16384) { Send(stream, 431, "Headers too large", null, false); return; }
                        string[] lines = Encoding.ASCII.GetString(header.ToArray()).Split(new[] { "\r\n" }, StringSplitOptions.None);
                        string[] request = lines[0].Split(' ');
                        if (request.Length != 3 || !request[1].StartsWith("/", StringComparison.Ordinal))
                        { Send(stream, 400, "Bad request", null, false); return; }
                        bool head = request[0] == "HEAD";
                        if (request[0] != "GET" && !head) { Send(stream, 405, "Method not allowed", null, false); return; }
                        string host = null;
                        foreach (string line in lines)
                            if (line.StartsWith("Host:", StringComparison.OrdinalIgnoreCase))
                            {
                                if (host != null) { Send(stream, 400, "Bad request", null, head); return; }
                                host = line.Substring(5).Trim();
                            }
                        if (host != new Uri(Url).Authority) { Send(stream, 403, "Forbidden", null, head); return; }
                        string route = request[1].Split('?')[0];
                        if (route == "/api/catalogue") await RefreshInstalledAsync().ConfigureAwait(false);
                        try
                        {
                            if (TryReadOverlay(route, out byte[] installed, out string installedMime))
                            {
                                string filename = request[1].EndsWith("?download=1", StringComparison.Ordinal) ? Path.GetFileName(Uri.UnescapeDataString(route)) : null;
                                Send(stream, 200, "OK", installed, head, installedMime, filename);
                                return;
                            }
                        }
                        catch (InstalledFileTooLargeException)
                        { Send(stream, 413, "Installed file exceeds the browser download limit", null, head); return; }
                        catch (Exception error) when (error is IOException || error is InvalidDataException || error is UnauthorizedAccessException)
                        { Send(stream, 409, "Installed library changed; Reload to refresh", null, head); return; }
                        if (!_routes.TryGetValue(route, out JObject entry)) { Send(stream, 404, "Not found", null, head); return; }
                        byte[] data = File.ReadAllBytes(Resolve((string)entry["path"]));
                        string hash;
                        using (var sha = SHA256.Create()) hash = BitConverter.ToString(sha.ComputeHash(data)).Replace("-", "").ToLowerInvariant();
                        if (hash != (string)entry["sha256"]) { Send(stream, 409, "Archive file changed; reinstall this release", null, head); return; }
                        string download = request[1].EndsWith("?download=1", StringComparison.Ordinal) ? Path.GetFileName((string)entry["path"]) : null;
                        Send(stream, 200, "OK", data, head, (string)entry["mime"], download);
                    }
                }
                catch (IOException) { /* A closing browser may cancel pending transfers. */ }
                catch (SocketException) { }
                catch (InvalidDataException) { }
                catch (UnauthorizedAccessException) { }
            }
        }

        private static void Send(Stream stream, int status, string message, byte[] payload, bool head, string mime = "text/plain; charset=utf-8", string download = null)
        {
            byte[] body = payload ?? Encoding.UTF8.GetBytes(message);
            string headers = "HTTP/1.1 " + status + " " + message + "\r\nContent-Type: " + mime
                + "\r\nContent-Length: " + body.Length + "\r\nConnection: close\r\nCache-Control: no-cache\r\n"
                + "X-Content-Type-Options: nosniff\r\nReferrer-Policy: no-referrer\r\n"
                + "Content-Security-Policy: default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; worker-src 'self' blob:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'\r\n";
            if (download != null) headers += "Content-Disposition: attachment; filename*=UTF-8''" + Uri.EscapeDataString(download) + "\r\n";
            byte[] bytes = Encoding.ASCII.GetBytes(headers + "\r\n");
            stream.Write(bytes, 0, bytes.Length);
            if (!head) stream.Write(body, 0, body.Length);
        }

        public void Dispose()
        {
            _running = false;
            _listener?.Stop();
        }
    }
}
