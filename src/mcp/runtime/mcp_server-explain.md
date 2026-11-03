# mcp_server.py explain

## project_info

<!-- instruction:project_info -->
When to use: Read missing project paths, registered file references, live-document identity or selected artifact context on first connection/reconnection, after evidence of a document change or when explicitly requested.
Before calling: No other tool is required. Reuse known context; a new instruction alone is not a reason to refresh. Either project or document requests the live document once, so do not call get_rhino_context merely to repeat that check.
Inputs from earlier results: Select only needed sections: project, document and locations are the defaults; runtime is optional. files_limit (1–500, default 50) and files_offset (nonnegative, default 0) page project.files. Use an earlier set_working_plan selection to interpret locations, not as a prerequisite. With include_ids=true, project.files[].project_file_id feeds Phase/Scene project_file_id inputs and distinguishes duplicate filenames; document.runtime_serial_number and runtime.rhinocode.pipe_id are also opt-in.
Interpretation: project.project_root is the absolute project root; managed paths are relative to it. project.file_name/file_path identify the observed live document once, and is_bound_document is true when it is the bound model, false when it is a different document. project.files is the DB's recorded file list, not a disk scan; files_page retains total/limit/offset/truncated, where truncated means more rows follow this page. document contains units, tolerances, modified state and counts. locations.database is project-wide; artifact_dir belongs to the Plan selected by this connection and is null until selected. runtime exposes requested runtime diagnostics. Use get_modeling_guide for basic instructions.
Limits: This does not change the document, select a Plan, save files or validate geometry. Managed tools apply project/artifact paths automatically; workers supply relative paths. A recorded file does not prove disk existence or an open document. A failed live check returns an error without is_bound_document; there is no separate checked/failed flag. Refresh project after a document change or reconnection. locations/runtime alone do not query the live document.
<!-- /instruction:project_info -->

<!-- instruction:get_rhino_execution -->
When to use: Recover an official RhinoCode request's completion evidence, remaining result pages, logs or diagnostics without rerunning its code.
Before calling: Use an existing execute_rhino_script or execute_project_python request when pending, uncertain or missing needed output. A completed response containing the needed result requires no routine follow-up read.
Inputs from earlier results: Pass the exact returned request_id, or omit it for this connection's latest execution. Follow result_page offsets with offset/limit and choose result_fields/include_result/include_stdout as needed; include_stdout defaults false. include_ids defaults true for authored results. Set include_diagnostics=true for operation identity, native/CLI, Undo and file/hash evidence. External client wrappers reconcile a live connection with connection_id; after a client process restart, omit that wrapper connection_id and provide the exact request_id to read retained evidence only, without reconnecting or executing Rhino work.
Interpretation: Read completed, status, mutation_state and result/result_page together. Successful completed reads are compact; pending, uncertain, failed, partial, nonzero-CLI or result-display-error outcomes retain detailed evidence. native_completed can be true while completed remains false until the exact final Rhino receipt and CLI process exit both agree. Page information is retained even on the final page.
Limits: This query never executes or cancels Rhino work, reconnects a lost model or rolls back changes. Timeout/process exit alone is not completion; late exact receipts may reconcile CLI-only uncertainty but unrelated native uncertainty stays blocked. Pending/finishing work keeps ownership. Files/evidence last until connection cleanup and can still be read after a model rename/deletion while their original session storage remains. Request identity is always returned; operation identity is diagnostic.

<!-- /instruction:get_rhino_execution -->

<!-- instruction:set_working_plan -->
When to use: Select or resume an existing Plan and optional Step as this connection's output workspace before writing Plan-owned artifacts.
Before calling: Reuse a known plan_id or obtain one from create_plan or list_plans; get_phase_plan_step(plan_id=...) supplies Step handles if the step_id is unknown. Plans/Steps need not be completed or followed linearly to select them.
Inputs from earlier results: Pass the existing plan_id and optional matching steps[].step_id. On first selection artifact_name is one folder label; otherwise the Plan goal provides it. Reuse an existing folder instead of selecting a new Plan just to continue work.
Interpretation: The response returns plan_id, step_id, revision and the shared project-relative artifact_dir under tmp/YYMMDD_name. revision is the Plan revision at selection, after any first-folder setup; use it as expected_revision for a subsequent Plan/Step update. Selection belongs to this connection; the Plan folder/refs are shared and discoverable by other workers. The directory is created only when files are needed.
Limits: Selection does not execute steps, create geometry or mark work complete. An existing artifact folder is reused; rename_artifact_folder changes its name. execute_project_python uses the selected folder as cwd; Rhino C# can write through RhinoAlmondBridge.ManagedFiles.Output("relative-name").

<!-- /instruction:set_working_plan -->

<!-- instruction:rename_artifact_folder -->
When to use: Rename an existing Plan-owned artifact folder without losing current Plan/Step references.
Before calling: Reuse a known plan_id with an artifact folder, or select its workspace through set_working_plan when relying on the default current Plan. There is no need to create a replacement Plan.
Inputs from earlier results: Pass the Plan's existing plan_id when not using the current selection and one new folder name as name; the tool adds the YYMMDD_ prefix. Use the previously returned artifact_dir to recognize which folder is being renamed, not as name.
Interpretation: The response returns the current artifact_dir and, when changed, previous_artifact_dir. Managed writes are serialized and current Plan/Step file refs are rewritten together; continue using the new path.
Limits: Existing destinations are never overwritten. This is a folder/ref operation, not a model rename or model save; immutable revision history is intentionally not rewritten. A Plan without an owned artifact folder must be selected first.

<!-- /instruction:rename_artifact_folder -->

<!-- instruction:execute_project_python -->
When to use: Run synchronous Python 3 in the bound Rhino with the selected Plan artifact folder as cwd when code needs Plan-owned outputs.
Before calling: Select or resume the intended workspace with set_working_plan; reuse an already valid selection. Reuse observed targets/units and the bundled rhino3d-scripts skill/references, currently available via get_modeling_guide(include_scripting=True), when authoring Rhino code.
Inputs from earlier results: Use set_working_plan's artifact_dir as the output context and previously observed GUIDs/measurements in code. Relative writes land in that folder; doc and scriptcontext.doc are the bound RhinoDoc. Assign a JSON-safe value to result and record useful output refs in the Plan/Step.
Interpretation: The response includes the RhinoCode outcome, request_id and selected artifact_dir. Use the exact request_id with get_rhino_execution for pending/uncertain completion, missing result pages or needed diagnostics, not after every completed result. project_root is absolute and artifact_dir is relative.
Limits: This is Rhino's embedded Python, not the external worker venv; missing packages are not installed automatically. The wrapper temporarily applies project/artifact environment and restores cwd, scriptcontext, Undo and redraw. Timeout limits waiting and does not kill Rhino or roll back partial changes; do not rerun writes merely because the CLI returned/timed out. Do not switch documents or launch detached/background writers.

Args:
    code: Synchronous Python 3 source; assign a JSON-safe value to result.
    timeout_seconds: Integer 1-600, default 60; waiting limit, not execution cancellation.
Returns:
    RhinoCode outcome, request_id and selected artifact_dir, with late-result recovery.
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
