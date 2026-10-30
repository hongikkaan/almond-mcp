# Rhino code and command execution

Almond can use Rhino's official ScriptServer from an external process. Rhino 8.11+
ships rhinocode; StartScriptServer enables it. The integrated runtime still binds
each operation to a particular process and saved document. Its execution status,
Undo information and returned data are separate from architectural correctness.

## Choosing a path

| Need | Call or language | Result contract |
|---|---|---|
| A supported document, selection or geometric observation | context/probe tools | Tested nonmutating observation, selectable fields |
| A custom query or ordinary geometry script | execute_rhino_script, language="python" | Python 3; set result to JSON data |
| C# source | execute_rhino_script, language="csharp" | Official C# statement body; doc and result_json, no Run class |
| Python with the selected Plan folder as cwd | execute_project_python | Official Rhino Python 3; same execution receipt and recovery |
| A verified official C# statement body | language="csharp-script" | doc and result_json; explicit JSON text, no Run class |
| Existing Python 2 code | language="python2" | Only when this runtime reports the language verified |
| A complete Rhino command | language="command" | Only when a synchronous script-runner context is verified |
| A previously dispatched operation | get_rhino_execution | State/result lookup; never dispatches the code again |

Capabilities and actual installed versions decide which official modes are ready.
An unavailable mode is rejected before execution. Python 3 is the default;
csharp and csharp-script select the same official statement-body mode.
Private native recipes retain their Bridge path; public code has no fallback.
A general script is not automatically read-only.

## Python

The runtime provides doc (the verified bound RhinoDoc), result and artifact_dir.
Use that document throughout the operation. Use the document's units and tolerance,
and convert GUID strings to System.Guid when calling RhinoCommon APIs.

```python
import Rhino
from System import Guid

target_ids = ["an-object-guid-from-a-prior-result"]
rows = []
for target in target_ids:
    obj = doc.Objects.FindId(Guid(target))
    if obj is None:
        rows.append({"id": target, "missing": True})
        continue
    box = obj.Geometry.GetBoundingBox(True)
    rows.append({"id": target, "name": obj.Name,
                 "type": str(obj.ObjectType),
                 "layer": doc.Layers[obj.Attributes.LayerIndex].FullPath,
                 "size": [box.Max.X-box.Min.X, box.Max.Y-box.Min.Y, box.Max.Z-box.Min.Z]})
result = {"units": str(doc.ModelUnitSystem),
          "tolerance": doc.ModelAbsoluteTolerance, "objects": rows}
```

Return dimensions, relationships or selected attributes needed for the decision.
Do not serialize Rhino geometry objects or return every object property by default.
For large results, retrieve selected fields/pages from get_rhino_execution instead
of rerunning the query. include_ids controls data handles; request/operation IDs
remain visible because they identify the execution being inspected.

Build and validate replacement geometry before deleting originals. Check operation
results for empty/invalid geometry and document-unit mistakes. Use try/finally to
restore redraw or other temporary state changed by your code. User input prompts,
background tasks, async:true and delayed document changes are outside this
synchronous execution contract.

## Commands and languages

A command macro is input for Rhino's command interpreter. Supply every required
argument and use English-prefixed command/option names. Do not add a leading !:
it can cancel a different operation. RhinoScriptSyntax rs.Command accepts one
command per call and does not support the !-space combination. A macro with loops
or conditions should become a Python script.

RhinoApp.RunScript called from a modeless callback may return before its command
runs. Only use command mode, or command calls inside a runtime-verified script-runner
context, when command completion is part of the operation. An accepted CLI request
or process exit is not sufficient evidence. Do not add event pumps to wait.

Rhino's unified ScriptEditor supports Python and C#. Legacy VBScript uses the
separate LoadScript/RunScript surface; it is not a claimed native ScriptEditor
language. External CLI script arguments are file paths, not a general script-argv
protocol. Use explicit data files or values in the submitted source.

The rhino3d-scripts skill and its four references are bundled with the tools.
get_modeling_guide(tool="execute_rhino_script") returns this pinned material and
INTEGRATION.md, whose automated execution rules take precedence over interactive
examples, VB/ScriptEditor claims, forced-cancel macros and manual Undo scaffolds.
Its personal installed files are not a dependency of the MCP server.

## Results, errors and Undo

An execution receipt records the exact request and document identity independently
of stdout and result size. A result serialization error can occur after code ran;
that does not reverse edits. A user exception may leave partial edits. The runtime
only ends an Undo record it owns; it must not automatically undo preceding work.
Read the returned execution and Undo fields before deciding the next action.

A timeout ends waiting, not the Rhino operation. Keep the request_id and query
get_rhino_execution. A matching final receipt and stopped CLI process allow late
results to be recovered; a missing or invalid receipt remains explicitly unresolved.
Do not resend the script, switch transport, or delete its temporary files to make
the connection appear idle. Existing native-transport uncertainty is not cleared
by an unrelated successful CLI result.

## Sources

- [Official RhinoCode CLI](https://developer.rhino3d.com/guides/scripting/advanced-cli/)
- [ScriptEditor macros](https://developer.rhino3d.com/guides/scripting/advanced-scripteditor-macros/)
- [RhinoScriptSyntax Command](https://developer.rhino3d.com/api/RhinoScriptSyntax/#application-Command)
- [Rhino scripting surfaces](https://docs.mcneel.com/rhino/8/help/en-us/information/rhinoscripting.htm)
- [Source skill](https://github.com/github/awesome-copilot/tree/main/skills/rhino3d-scripts)
