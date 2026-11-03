using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json.Linq;

namespace Rhino
{
    public class RhinoDoc { public Rhino.DocObjects.ObjectTable Objects = new Rhino.DocObjects.ObjectTable(); }
}
namespace Rhino.DocObjects
{
    public enum InstanceDefinitionUpdateType { Static, Linked }
    public enum ActiveSpace { ModelSpace, PageSpace }
    public class ObjectAttributes { public ActiveSpace Space; }
    public class RhinoObject { public Guid Id; public bool IsDeleted, IsInstanceDefinitionGeometry; public ObjectAttributes Attributes = new ObjectAttributes(); }
    public class ObjectEnumeratorSettings { public bool NormalObjects, HiddenObjects, LockedObjects, ReferenceObjects, DeletedObjects, IdefObjects; }
    public class ObjectTable { public InstanceObject[] Roots; public RhinoObject[] GetObjectList(ObjectEnumeratorSettings settings) => Roots; }
    public class InstanceObject : RhinoObject { public InstanceDefinition InstanceDefinition; }
    public class InstanceDefinition
    {
        public Guid Id; public string Name; public bool IsDeleted, IsReference;
        public InstanceDefinitionUpdateType UpdateType; public string SourceArchive;
        public RhinoObject[] Members = Array.Empty<RhinoObject>();
        public InstanceDefinition[] Containers = Array.Empty<InstanceDefinition>();
        public int Reads, ExtraMemberCount;
        public int ObjectCount => Members.Length + ExtraMemberCount;
        public RhinoObject[] GetObjects() { Reads++; return Members.Concat(Enumerable.Range(0, ExtraMemberCount).Select(_ => new RhinoObject())).ToArray(); }
        public InstanceDefinition[] GetContainers() => Containers;
    }
}
namespace RhinoAlmondBridge
{
    public static class Program
    {
        public static void Main()
        {
            var input = JObject.Parse(Console.In.ReadToEnd());
            var definitions = input["definitions"].OfType<JObject>().ToDictionary(d => (string)d["id"], d =>
                new Rhino.DocObjects.InstanceDefinition { Id = Guid.Parse((string)d["id"]), Name = (string)d["name"] ?? "Block",
                    IsReference = (bool?)d["reference"] ?? false, SourceArchive = (string)d["source"] ?? "", ExtraMemberCount = (int?)d["extra_members"] ?? 0,
                    UpdateType = (bool?)d["linked"] == true ? Rhino.DocObjects.InstanceDefinitionUpdateType.Linked : Rhino.DocObjects.InstanceDefinitionUpdateType.Static });
            Rhino.DocObjects.InstanceObject Instance(JToken row) => new Rhino.DocObjects.InstanceObject {
                Id = Guid.Parse((string)row["id"]), InstanceDefinition = definitions[(string)row["definition"]],
                Attributes = new Rhino.DocObjects.ObjectAttributes { Space = (bool?)row["page"] == true ? Rhino.DocObjects.ActiveSpace.PageSpace : Rhino.DocObjects.ActiveSpace.ModelSpace } };
            foreach (JObject row in input["definitions"])
            {
                var definition = definitions[(string)row["id"]];
                definition.Members = (row["members"] as JArray ?? new JArray()).Select(Instance).ToArray();
                definition.Containers = (row["containers"] as JArray ?? new JArray()).Select(id => definitions[(string)id]).ToArray();
            }
            var doc = new Rhino.RhinoDoc(); doc.Objects.Roots = input["roots"].Select(Instance).ToArray();
            var result = BlockDefinitionImpact.Observe(doc, definitions[(string)input["target"]], (bool?)input["stable"] ?? true);
            result["fixture_definition_reads"] = JObject.FromObject(definitions.ToDictionary(d => d.Key, d => d.Value.Reads));
            Console.WriteLine(result);
        }
    }
}
