using System;
using System.IO;
using System.Text;
using Newtonsoft.Json;
using RhinoAlmondBridge;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;

Console.OutputEncoding = new UTF8Encoding(false);
if (args.Length == 3 && args[0] == "--serve")
{
    var snapshot = JObject.Parse(File.ReadAllText(args[2]));
    using var server = new ArchiveHttpServer(args[1], () => Task.FromResult(snapshot));
    server.Start();
    Console.WriteLine(server.Url);
    Console.ReadLine(); // The test controls the lifetime through its stdin pipe.
    return 0;
}
if (args.Length != 3 || args[0] != "--mesh")
{
    Console.Error.WriteLine("Usage: ArchiveHost --mesh <glb> <asset-id> | --serve <bundle-dir> <snapshot.json>");
    return 2;
}
try
{
    Console.WriteLine(JsonConvert.SerializeObject(ArchiveMeshData.Decode(File.ReadAllBytes(args[1]), args[2])));
    return 0;
}
catch (Exception error) { Console.Error.WriteLine(error.Message); return 1; }
