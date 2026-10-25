using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;
using System.Reflection.PortableExecutable;

// Read the built assemblies without loading Rhino or invoking any model code.
internal static class RuntimeContract
{
    internal static void Verify(string bridgePath, string connectionPath)
    {
        using var bridgeFile = File.OpenRead(bridgePath);
        using var bridge = new PEReader(bridgeFile);
        using var connectionFile = File.OpenRead(connectionPath);
        using var connection = new PEReader(connectionFile);
        var names = CommandNames(bridge).Concat(CommandNames(connection)).ToArray();
        foreach (string old in new[] { "AlmondCOS", "AlmondCOSDisconnect", "AlmondMCPStart", "AlmondMCPStop", "AlmondMCPStatus" })
            if (names.Contains(old, StringComparer.OrdinalIgnoreCase)) throw new Exception("Legacy command still shipped: " + old);
        if (!CommandNames(connection).Order().SequenceEqual(new[] { "almondconnect", "almonddisconnect" }))
            throw new Exception("Connection RHP does not expose exactly the requested commands.");
        var reader = bridge.GetMetadataReader();
        var type = reader.TypeDefinitions.Select(reader.GetTypeDefinition)
            .Single(t => reader.GetString(t.Name) == "BridgeServer");
        var methods = type.GetMethods().Select(reader.GetMethodDefinition).ToArray();
        if (methods.Any(m => new[] { "Start", "Stop", "ListenLoop", "ReadExact" }.Contains(reader.GetString(m.Name))))
            throw new Exception("Legacy transport is still present in the native handler.");
        var constructor = methods.Single(m => reader.GetString(m.Name) == ".ctor");
        var code = bridge.GetMethodBody(constructor.RelativeVirtualAddress).GetILBytes()!;
        foreach (string fieldName in new[] { "_validator", "_definitionRunner", "_drawingAssetManager", "_drawingStyleManager" }) {
            var handle = type.GetFields().Single(f => reader.GetString(reader.GetFieldDefinition(f).Name) == fieldName);
            var token = BitConverter.GetBytes(MetadataTokens.GetToken(handle));
            // stfld's four-byte operand must identify the existing Engine helper field.
            if (!Enumerable.Range(0, Math.Max(0, code.Length - 4)).Any(i => code[i] == 0x7d && code.Skip(i + 1).Take(4).SequenceEqual(token)))
                throw new Exception("Handler constructor did not initialize " + fieldName);
        }
    }

    static string[] CommandNames(PEReader pe)
    {
        var reader = pe.GetMetadataReader();
        var result = new List<string>();
        foreach (var handle in reader.TypeDefinitions) {
            var type = reader.GetTypeDefinition(handle);
            if (type.BaseType.Kind != HandleKind.TypeReference) continue;
            var parent = reader.GetTypeReference((TypeReferenceHandle)type.BaseType);
            if (reader.GetString(parent.Namespace) != "Rhino.Commands" || reader.GetString(parent.Name) != "Command") continue;
            var getter = type.GetMethods().Select(reader.GetMethodDefinition)
                .Single(m => reader.GetString(m.Name) == "get_EnglishName");
            var code = pe.GetMethodBody(getter.RelativeVirtualAddress).GetILBytes()!;
            // Production command names are compile-time literals: ldstr, ret.
            if (code.Length != 6 || code[0] != 0x72 || code[5] != 0x2a)
                throw new Exception("Command name requires evaluation: " + reader.GetString(type.Name));
            result.Add(reader.GetUserString(MetadataTokens.UserStringHandle(BitConverter.ToInt32(code, 1) & 0x00ffffff)));
        }
        return result.ToArray();
    }
}
