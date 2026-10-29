# mcp_server.py explain

## project_info

<!-- instruction:project_info -->
Read selected project information. sections defaults to ["project", "document",
"artifacts"]; runtime and instructions are optional. The document section checks
the currently open live document in this same call; do not call get_rhino_context
again merely to verify it. Project root is the one absolute path and is actually
set as ALMOND_PROJECT_ROOT. Other paths are relative to it. Managed tools apply
the root and selected artifact folder automatically; workers supply relative paths.
Reuse known context. Refresh only for first connection/reconnection, evidence of
a document change, missing project/path information, or the user's request.
A new instruction alone is not a refresh trigger.
<!-- /instruction:project_info -->

<!-- instruction:get_rhino_execution -->
Read an official RhinoCode execution without rerunning it. Omit request_id for
the latest execution in this connection, or supply the exact returned request ID.
Completed successful reads return the requested result/logs, page information,
request ID and outcome by default. Set include_diagnostics=true for operation
identity, native/CLI details, Undo, file/hash and runtime-completion evidence.
Pending, uncertain, failed, partial, nonzero CLI exit and result-display-error
responses retain their detailed evidence even when include_diagnostics is false.
Pending and finishing work retains its ownership. Completion requires the exact
final Rhino receipt and the CLI process to have exited; timeout and process exit
alone do not prove completion. native_completed can expose a verified Rhino result
while completed remains false because the CLI lifecycle is still unconfirmed.
A late exact result can reconcile CLI-only
uncertainty. Unrelated native uncertainty remains blocked. include_result controls
result retrieval, result_fields selects top-level fields, and offset/limit page
retained result rows without another Rhino call. include_stdout is false by
default. include_ids defaults true for explicitly authored code results; request
identity always remains, and operation identity is available with diagnostics.
Page information remains on the final page too. Execution files remain available until this
connection is cleaned up. In an external client, connection_id reconciles the
live tracked connection. After the client process restarts, omit connection_id
and provide the exact request_id to read its retained evidence from the recorded
session. This recovery-only path does not reconnect or execute Rhino work.
Retained evidence can still be read after the original model file is renamed or
deleted, while its recorded session storage remains at the original location.
<!-- /instruction:get_rhino_execution -->

<!-- instruction:set_working_plan -->
Select or resume a Plan and optional Step for this connection. Reuse its existing
artifact folder. On first use, artifact_name (one folder name) or the Plan goal
creates a recorded relative path tmp/YYMMDD_name; the directory is created only
when files are needed. Plan/Step status need not be completed or linear. Other
workers discover the same path and refs from the Plan. Use rename_artifact_folder
to change an existing folder name. Managed Python uses this directory as cwd;
Rhino C# uses RhinoAlmondBridge.ManagedFiles.Output("relative-name").
<!-- /instruction:set_working_plan -->

<!-- instruction:rename_artifact_folder -->
Rename a Plan's artifact folder, defaulting to the selected Plan. Supply one name;
a YYMMDD_ prefix is applied automatically. Managed writes are serialized with the
rename. Current Plan/Step file refs are updated together, while immutable revision
history is retained. Existing destinations are never overwritten.
<!-- /instruction:rename_artifact_folder -->

<!-- instruction:execute_project_python -->
Execute Python in the selected Plan artifact folder using relative paths. The
runtime applies project/artifact environment variables and a separate owned scratch
directory. No script file is created. Empty folders and owned scratch are removed
after execution; output artifacts are kept. Record useful outputs in Plan/Step refs.
This does not execute RhinoCommon code or change Rhino's process cwd. Do not start
detached/background writers; they cannot outlive the managed execution scope.
timeout_seconds defaults to 60 (1-600). Partial writes are not automatically retried.
<!-- /instruction:execute_project_python -->

## response-90

<!-- instruction:response-90 -->
This Rhino uses the previous storage protocol. Load the new host and reconnect before sharing a DB.
<!-- /instruction:response-90 -->

## response-92

<!-- instruction:response-92 -->
Do not connect this model to another project database.
<!-- /instruction:response-92 -->

## response-96

<!-- instruction:response-96 -->
Connection changed. Exit Codex and reconnect with almond.
<!-- /instruction:response-96 -->
