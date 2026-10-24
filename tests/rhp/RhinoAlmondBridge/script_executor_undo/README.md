# Native modeling and Undo regression tests

These tests link production sources; they do not install or register a plugin.
`NativeUndoTests` and `ObservationTests` use disposable headless documents.
The modeling, Component, Sheet and asset suites also save and open disposable
regular documents in the supplied test directory. Run those suites in a separate
Rhino 8 process with an empty, unmodified startup document and no user models.
They need the actual Rhino UI process for document events, rendering materials,
Layouts and command behavior. A headless `RhinoCore` host is not equivalent.
Rhino 8 with .NET 8 and a .NET SDK are required.

Build from the repository root:

```powershell
dotnet build src/rhp/RhinoAlmondBridge/RhinoAlmondBridge.csproj -c Release
dotnet build tests/rhp/RhinoAlmondBridge/script_executor_undo/ScriptExecutorUndoTests.csproj -c Release
```

In the isolated Rhino 8 process, run the following Python snippet once. Replace
the DLL path with the full path in your checkout. The queued callback runs after
the launching command returns: running the tests inside a Rhino command could
hide the modeless Undo-record leak this suite checks.

```python
import Rhino
from System import Action
from System.Reflection import Assembly
from Eto.Forms import Application

assembly = Assembly.LoadFrom(
    r"C:\path\to\almond-mcp\tests\rhp\RhinoAlmondBridge\script_executor_undo\bin\Release\net8.0-windows\AlmondScriptUndoTests.dll"
)

def run():
    test_type = assembly.GetType("AlmondScriptUndoTests.NativeUndoTests")
    try:
        report = test_type.GetMethod("RunAll").Invoke(None, None)
        Rhino.RhinoApp.WriteLine(report)
    except Exception as error:
        Rhino.RhinoApp.WriteLine(str(error))

Application.Instance.AsyncInvoke(Action(run))
```

The following suites expose `RunAll(string directory)`. Supply a fresh test
directory under the checkout's ignored `data` folder through reflection, for
example `method.Invoke(None, System.Array[System.Object]([directory]))`.
Call them after the launching command returns, as above. Do not call their
regular-document fixtures from a working Rhino session.

| Suite | Main behavior checked |
| --- | --- |
| `ModelingTests` | Lazy material layers, 101-object shared render material, ordinary Add calls, metadata validation, event routing, Undo/Redo |
| `ComponentHierarchyTests` | Exclusive direct ownership, nested aggregate groups, manual TextDot additions, cycles and competing parents, root removal and reconciliation |
| `DrawingSheetTests` | Real Layout/detail identities, updates, physical scale in mixed model/page units, unregister preservation |
| `ComponentOperationTests` | Exact overlap evidence, incomplete coverage, nested target resolution, Isolate/Unisolate and ZoomSelected |
| `DrawingAssetGeometryTests` | Prepared 3DM extraction, nested block transforms, source/artifact hashes, units/origin/unsupported-geometry rejection |
| `DrawingAssetPlacementTests` | Millimeter and meter documents, source revisions, definition reuse, prevalidation and placement Undo |

Read the full reflected inner exception on failure. Each regular-document
fixture marks only its own disposable document unmodified before closing it.
Close the isolated test process normally before rebuilding the same assembly.

The suite checks successful Undo/Redo, partial creation/deletion/attribute
rollback, both exception paths, empty failures with previous Undo and Redo
history, first-call layer rollback, validation failures, unavailable or
caller-owned recording, lost record ownership, and existing `void Run`
compatibility. It also checks immediate Redo after failed creation, deletion,
attribute edits, and first-call layer initialization, with no intervening edit
that could hide a stale Redo record. Two earlier successful actions must still
support Undo and Redo after a nonempty failure. Every normal exit must leave
Undo, Redo, and recording inactive.
The test's manual Undo/Redo helper checks that condition before doing its own
native bookkeeping, so it cannot hide a leaked executor record.

Rhino discards an empty record synchronously during `EndUndoRecord`, reporting
`Command.UndoRedo` with `IsPurgeRecord` for that record's serial. The executor
observes only that close and skips Undo for discarded records. A custom Undo
marker is deliberately unnecessary: adding one would turn an empty failure into
a history edit and discard an existing Redo chain.

A nonempty failed script is undone and its rollback record is closed before
`ClearRedoRecords` discards the failed script's Redo history. This cleanup runs
only after successful recovery with no active Undo, Redo, or recording operation.
Purged empty records return before this cleanup, preserving the existing Redo
chain; earlier successful Undo records are retained.

The executor suite now includes the original 21 Undo cases plus 19 returned-value
cases. These round-trip the final JSON envelope, check the exact UTF-8 size and
container-depth boundaries, and verify that conversion errors keep successful
edits undoable while runtime/Undo errors cannot expose stale results. Arbitrary
POCO getters must not run during result conversion.

Invoke `AlmondScriptUndoTests.ObservationTests.RunAll()` in the same modeless
callback for nine headless cases. These include a first query on a fresh document,
selection limits and unavailable-view warnings, disabled/caller-owned Undo,
invalid arguments and unchanged document state.

For the four real-view checks, explicitly choose the intended document and call
`ObservationTests.RunViewport(doc)` from a modeless UI callback. It decodes actual
640x480 and 64x64 bounded JPEGs, checks metadata and aspect ratio, and compares
geometry CRC, serialized object attributes, layers, views, clipping, selection,
Modified and Undo state before/after. Arrange any desired page/detail/clipping
fixture explicitly before calling it; the tests do not change the current view
to prepare a capture.

Use a unique output directory and `-p:AssemblyName=...` for a changed fixture if
an earlier test assembly is already loaded. Do not overwrite loaded assemblies.
These linked-source tests and a successful product build are separate from
loading the candidate RHP and receiving an actual image through the MCP client.
