using System;
using System.IO;
using System.Text;
using Newtonsoft.Json;
using RhinoAlmondBridge;
using System.Net;
using System.Net.Http;
using System.Security.Cryptography;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;

Console.OutputEncoding = new UTF8Encoding(false);
if (args.Length == 2 && args[0] == "--overlay")
{
    string root = Path.GetFullPath(args[1]); Directory.CreateDirectory(root);
    string file = Path.Combine(root, "drawing.svg"); File.WriteAllText(file, "<svg>one</svg>");
    string catalogue = Path.Combine(root, "catalogue.json"); File.WriteAllText(catalogue, "{\"assets\":[]}");
    string hash = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(file))).ToLowerInvariant();
    File.WriteAllText(Path.Combine(root, "bundle.json"), new JObject {
        ["schema_version"] = 1, ["routes"] = new JObject {
            ["/"] = new JObject { ["path"] = "drawing.svg", ["sha256"] = hash, ["mime"] = "image/svg+xml" },
            ["/api/catalogue"] = new JObject { ["path"] = "catalogue.json", ["sha256"] = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(catalogue))).ToLowerInvariant(), ["mime"] = "application/json" }
        }
    }.ToString());
    var info = new FileInfo(file); DateTime modified = info.LastWriteTimeUtc;
    var snapshot = new JObject { ["schema_version"] = 1, ["catalogue"] = new JObject { ["assets"] = new JArray() },
        ["files"] = new JObject { ["/files/drawing.svg"] = new JObject { ["path"] = file, ["root"] = root,
            ["size"] = info.Length, ["mtime_ns"] = (modified.Ticks - 621355968000000000L) * 100,
            ["sha256"] = hash, ["mime"] = "image/svg+xml" } } };
    using var server = new ArchiveHttpServer(root, () => Task.FromResult(snapshot)); server.Start();
    using var http = new HttpClient();
    await http.GetStringAsync(server.Url + "api/catalogue");
    if (await http.GetStringAsync(server.Url + "files/drawing.svg") != "<svg>one</svg>") throw new Exception("Verified bytes missing");
    File.WriteAllText(file, "<svg>two</svg>"); File.SetLastWriteTimeUtc(file, modified);
    if ((await http.GetAsync(server.Url + "files/drawing.svg")).StatusCode != HttpStatusCode.Conflict)
        throw new Exception("Same-size same-mtime changed drawing bytes were served");
    Console.WriteLine("PASS: native HTTP overlay rejects drawing bytes changed with preserved size and mtime");
    return 0;
}
if (args.Length != 3 || args[0] != "--mesh")
{
    Console.Error.WriteLine("Usage: ArchiveHost --mesh <glb> <asset-id>");
    return 2;
}
try
{
    Console.WriteLine(JsonConvert.SerializeObject(ArchiveMeshData.Decode(File.ReadAllBytes(args[1]), args[2])));
    return 0;
}
catch (Exception error) { Console.Error.WriteLine(error.Message); return 1; }
