# RhinoCode execution integration

This milestone adds the official Rhino 8 ScriptServer route to the existing MCP.
The next development stage evaluates it by doing design work through the public
tools: whether the necessary guidance arrives at the right moment, whether that
guidance improves design decisions, and which tool inputs/outputs obstruct work.
Passing transport tests alone is not evidence of good design behavior.

## Design behavior

A design question can collect related areas, clearances and geometric relationships
in one Python/C# execution and return named fields. Fixed probes are available
when their particular observation fits the question; they are not a mandatory
sequence before every design action. Normal execution replies put the design
answer first. Result fields and pages can be read without recomputing the model.

Preserve the approved 1028-UNIT Drafting guidance. Future BDD cases are discovered
while using the actual tools on the connected Rhino documents, then expressed as
Given/When/Then behaviors before the relevant correction. Basic drafting judgment
should remain autonomous; material design intentions must not be invented.

## Current acceptance state

- Actual Rhino 8.34: Python 3, Python 2, C# statement bodies and command macros
  created geometry and passed one-step Undo/Redo in a disposable saved document.
  C# compilation and partial-runtime-error cases were also exercised. All four
  official modes are enabled; the existing default C# Run contract is retained.
- Source-linked Terminal controls passed the PID-display fixtures. A real Layout
  capture used the new default 75% pixel size; drawing review can request 100%.
- Layout print appearance is an open BDD failure: raster capture still used display
  red despite print black. Do not claim the print-color/width/scale scenario passed.
- Asset preparation source is retained for subsequent BDD work. Its public prepare
  and preparation-job publication paths are disabled with acceptance_pending until
  the import/review/normalize/merge/register behavior is verified end to end.
- Full public-tool design practice, guidance timing and quality are the next stage
  after the user reopens and connects the two Rhino documents.

## Execution boundary

Rhino 8.11 and later ship `rhinocode`; this integration is exercised against the
installed Rhino 8.34.26223.11001. `StartScriptServer` enables discovery.
`rhinocode list --json` supplies an exact `pipeId`, process identity and active
document. `--rhino` selects that pipe, not an Almond A-J slot. Never pick the
first available Rhino or infer a pipe solely from a PID.

The existing `execute_rhino_script(script)` C# `Run(RhinoDoc doc)` contract stays
compatible. Explicit language choices add official Python, Python 2, C# statement
body and command execution after the live gates described above.
The package receives a runtime callback; it does not import the external
connector. The subprocess runs in the external Python worker, never in a Rhino
UI-thread handler. Argument vectors are used without a shell.

## Identity and completion

Before dispatch, validate the bound Rhino PID and process start identity, the
discovered pipe and saved model path. The generated synchronous wrapper validates
the document runtime serial and path again at execution time, then uses that
document explicitly. The wrapper is trusted user-code execution, not a sandbox.
Asynchronous document changes and prompts are outside the completion contract.

Publish a durable per-session RhinoCode execution journal before launching the
CLI. It identifies token, operation, request, nonce, source hash, target process
and document, generated files and child process identity. A matching final
wrapper receipt plus confirmed CLI process exit is required for completion.
CLI exit code or stdout alone is insufficient. The final receipt is independent
of result display limits and reports execution, cleanup, Undo and result errors
separately. Result serialization failure must not erase execution evidence.

RequestBatch tracks official CLI executions separately from native requests;
it must not synthesize a native sequence or native-finally acknowledgement.
ProjectRuntime, native release/drain and retired-session cleanup all consult
the durable external-execution fence. A running, missing or malformed receipt
prevents reuse and cleanup even if the legacy bridge is idle or its worker died.
An inaccessible child process is not evidence of process exit. An exited target
Rhino cannot execute delayed work and permits ordinary retired-session cleanup.

A wait timeout does not kill/replay the CLI or delete its files. Read-only
execution-status retrieval must recover late exact results and expose pending,
finishing, completed and unconfirmed states. Conclusively recovered CLI-only
uncertainty may be released; unrelated native uncertainty must remain blocked.
If the external binding was already invalidated, recovery reports that fact and
requires orderly disconnect/reconnect instead of silently reviving it.

## Language and Undo contracts

Python wrappers provide `doc`, `result` and `artifact_dir`; source compilation
occurs inside error handling. Python 2 is independently tested, not presumed
compatible. The C# script mode is a documented statement body, not an arbitrary
source file or the legacy Run class. It uses explicit JSON result data rather
than implicitly evaluating arbitrary object getters/enumerables.

Only a nonzero Undo record owned by this wrapper may be ended. User-code failure
does not automatically undo preceding work. Partial changes, execution errors
and result errors are distinct outcomes. Commands target the bound document;
their wrapper is enabled only after real Rhino proves synchronous completion.
Do not implement event pumping or fallback to another transport after dispatch.

## Observation and output

Fixed probes remain supported for their nonmutating observation contract. General
questions may use a single targeted Python/C# query. Preserve useful field-group,
ID and pagination controls; output evidence and execution status must survive
projection. Large result data is retrievable without repeating the Rhino work.

`get_rhino_execution` defaults to a compact public response for confirmed successful
reads. It preserves the requested result, page information (including the final
page), explicitly requested logs and their byte paging, and recovery target/status
information. `include_diagnostics=true` returns the full evidence. Pending,
uncertain, failed or partial outcomes, nonzero CLI exit codes and result-display
errors retain details by default. This projection applies after the runtime has
read and reconciled its original evidence, including on retained-file recovery;
it does not alter journal storage, completion/fence decisions, worker checks or
the internal result reader.

Preserve the user-approved Drafting prose from commit 7ba3687. The Layout acceptance
target is print colors and print widths with each Detail's actual scale and the
user's document/view state preserved; the print-color case remains open above.
Live review on 2026-10-29 used the user's connected housing and resident-facility
documents. In the existing A4 resident section Layout (144 PageSpace objects,
no Details), a known line changed from display gray 120 to plot gray 90 after
Document-scoped PrintDisplay On with Print colors. Raster capture therefore
still depends on preview state; this does not pass the independent print-color
acceptance case. RasterMode=false produced blank PNGs in that document. SVG
capture produced data, but Rhino's SVG-to-bitmap conversion returned null.
Do not describe either as a completed raster fix.

The housing document now also contains an actual A4 frame-review Layout with
three model Details at 1:50, 1:1 and 1:2. Stored ratios were checked separately
from image legibility. PrintDisplay DetailBorder=UsePrintWidth suppressed its
No Print borders. Paper-space text bounds must use the view-dependent annotation
scale: this document's parent style scale is 300, while the page scale is 1.
These are working-document observations, not permission to create blank test models.

Image scale_percent controls pixels, defaults
to 75, and may be explicitly 100 for visual review. Terminal shows Rhino PID
persistently next to controls, independently of the changing shell status.

## Asset preparation

The deferred preparation implementation follows the reviewed installed
almond-asset-converter: preserve/import source, inspect parts and previews,
record actual visual decisions, normalize explicit units/orientation/origin,
verify the reopened result and record the actual coplanar-merge command outcome.
Keep stage hashes and truthful review/material limitations. Use the existing
register_drawing_asset atomic publication and linked 3D/2D package audit; do not
introduce the older skill's competing manifest writer.

## Acceptance and delivery

- Offline: exact target selection, stale identities, timeout/late completion,
  worker death, malformed/stale receipt, native release/cleanup fences, result
  selection and real worker/catalog schema agreement.
- User-connected working Rhino files: explicit two-instance routing; Python/C# and command paths;
  syntax/runtime/result failures; grouped Undo/Redo; delayed completion recovery;
  print-color/width/detail-scale captures; imported/generated asset preparation,
  registration and derived drawing audit.
- Exercise public MCP tools in the connected working files; avoid creating or
  launching separate Rhino documents solely for functionality tests. Distinguish live
  native calls from offline/validation-only or unavailable external services.
- Preserve original user models, DBs, skills and unrelated working-tree changes.
  Do not force-close Rhino or replace loaded RHPs. Fixture builds and source tests
  are separate from runtime build, registration, load and live verification.

## Sources

- https://developer.rhino3d.com/guides/scripting/advanced-cli/
- https://developer.rhino3d.com/guides/scripting/advanced-async/
- https://docs.mcneel.com/rhino/8/help/en-us/information/rhinoscripting.htm
- https://developer.rhino3d.com/api/RhinoScriptSyntax/#application-Command
- https://docs.mcneel.com/rhino/8/help/en-us/commands/printdisplay.htm
- https://github.com/github/awesome-copilot/tree/main/skills/rhino3d-scripts
- User requirements: Notion 1028 (407e0a394120801380e7c88a5466b535),
  UNIT feedback (407e0a394120809ab6b0eb256659e18d), and 1028-UNIT session
  01a1803d-c1bf-7093-b203-7f34a5728123.
