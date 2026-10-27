using System.Runtime.InteropServices;
using Rhino;
using Rhino.FileIO;
using Rhino.PlugIns;
using RhinoAlmondBridge;

// Test-only identity. This assembly must never replace or register as the Bridge.
[assembly: Guid("fcf793c0-6937-4c4f-9d2b-c3c65f4df8e1")]

namespace AlmondScriptUndoTests
{
    /// <summary>Tests production archive helpers through Rhino's real 3dm plugin hooks.</summary>
    public sealed class SemanticRegistryFixturePlugin : PlugIn
    {
        protected override bool ShouldCallWriteDocument(FileWriteOptions options) => true;

        protected override void WriteDocument(RhinoDoc doc, BinaryArchiveWriter archive, FileWriteOptions options)
        {
            ComponentSemanticRegistry.Write(doc, archive);
        }

        protected override void ReadDocument(RhinoDoc doc, BinaryArchiveReader archive, FileReadOptions options)
        {
            ComponentSemanticRegistry.Read(doc, archive, options);
        }
    }
}
