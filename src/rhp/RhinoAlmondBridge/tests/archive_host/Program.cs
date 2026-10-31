using System;
using System.IO;
using System.Text;
using Newtonsoft.Json;
using RhinoAlmondBridge;

Console.OutputEncoding = new UTF8Encoding(false);
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
