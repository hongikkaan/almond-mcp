"""Extract current production Undo methods for the offline host; no Rhino runtime.

Run with this checkout's Python before building StepCompletionHost.csproj.
Results.cs is linked directly by the project; Rhino document/Undo APIs are fakes.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
source_path = HERE.parents[2] / "rhp/RhinoAlmondBridge/ScriptExecutor.cs"
source = source_path.read_text(encoding="utf-8")
start = source.index("        internal ScriptResult ExecuteAction(RhinoDoc doc, Func<object> action)")
stop = source.index("        /// <summary>\n        /// Wraps raw C# code", start)
prefix = """using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Rhino;
using Rhino.Commands;
namespace RhinoAlmondBridge { public partial class ScriptExecutor {
"""
suffix = """
private void AddScaleDimensions(RhinoDoc doc, List<Guid> guids) { throw new NotSupportedException("Cleanup returns counts, never a GUID list."); }
} }
"""
output = HERE / "obj/ActualExecutor.g.cs"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(prefix + source[start:stop] + suffix, encoding="utf-8")
print(json.dumps({"executor_source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
                  "generated": str(output), "actual_rhino_loaded": False}))
