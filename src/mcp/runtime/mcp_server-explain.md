# mcp_server.py explain

## execute_looping

<!-- instruction:execute_looping -->
Plan의 다음 Loop를 시작하거나 최신 Loop를 재개하여 작업 맥락과 산출물 위치를 준비합니다. Step이나 Rhino 작업을 자동 실행하지 않으며, 에이전트가 다음 기준에 따라 수행·검증·보고합니다.

- 반환된 Step 순서를 기본으로 따르되 실행을 강제하는 조건으로 취급하지 않습니다. 재개 전에는 저장된 기록을 확인하여 이미 수행한 작업, 남은 검증, 아직 전달하지 않은 보고를 구별하고 완료한 Rhino 작업을 반복하지 않습니다.
- Plan과 Step의 상태(pending, running, paused, completed, failed, blocked)는 명시적으로 기록합니다. Step의 수행·검증·보고 진행과 근거는 `update_step`의 상태 및 `input_refs`·`output_refs`로 남기고, Plan의 변경은 `update_plan`으로 기록합니다. 일반 Rhino/Python 호출 자체는 Plan 리비전을 생성하지 않습니다.
- 이전 결과는 현재에도 유효한지 확인한 뒤 재사용합니다. 사용할 이전 파일 경로는 `input_refs`에, 이번 Loop에서 새로 만들거나 수정한 결과 경로는 `output_refs`에 기록합니다.
- Loop에는 별도 업무 상태가 없고, 더 높은 Loop가 시작되면 이전 Loop는 읽기 전용 참고자료입니다. Step 상태는 Plan 상태와 독립적입니다. 모든 Step을 마치거나 회차를 보고했더라도 Plan 완료는 사용자가 결정하며, 그 결정 후에만 Plan 상태를 completed로 기록합니다.
- 회차가 끝나면 목표, 바뀐 내용, 판단을 뒷받침하는 시각 자료, 검증 결과와 남은 선택지를 사용자에게 보고합니다. 질문은 관련 근거와 연결하고 보고는 간결하게 하며, 이미지 수를 고정하지 않습니다.

Args:
    plan_id: 다음 Loop를 시작하거나 최신 Loop를 재개할 기존 Plan ID입니다. create_plan 또는 list_plans에서 얻은 ID를 사용합니다.
    resume: false이면 첫 호출에서 Loop 1을, 이후 호출에서는 다음 Loop를 시작합니다. true이면 이미 시작된 최신 Loop의 번호와 Step 기록을 유지하며, 시작된 Loop가 없거나 이전 Loop를 재개하려는 경우에는 사용할 수 없습니다. 다음 회차를 시작하려면 앞 회차를 보고한 뒤 false로 호출합니다. 시작 결과가 불확실하면 get_phase_plan_step으로 현재 Loop와 기록을 먼저 확인하고, 확인 없이 false로 재호출하지 않습니다. 변경 없는 재개는 리비전을 추가하지 않습니다.
    feedback: 이번 회차에서 반영할 피드백입니다. 새 회차에서는 기본값이 빈 문자열이며, 재개할 때 빈 문자열은 기존 피드백을 유지합니다. 재개 시 기존 값과 다른 비어 있지 않은 피드백을 주면 같은 Loop의 피드백을 갱신하고 리비전을 추가합니다.
    artifact_name: 최초 Plan 산출물 폴더의 이름이며 경로가 아닙니다. 생략하면 목표에서 이름을 정하고, 날짜 접두사가 없으면 YYMMDD_를 붙입니다. 이미 정해진 Plan 폴더를 이 입력으로 바꾸지 않습니다. 이번 Loop의 모든 산출물은 반환된 artifact_dir(Plan 폴더 아래 01, 02, …)에 저장합니다. 같은 Loop 안에서 덮어쓸 수 있지만 중간 결과를 보존하려면 다른 파일명을 사용합니다. 재사용할 이전 파일을 Plan 루트로 옮기거나 과거 산출물을 자동 삭제하지 않습니다. 다음 Loop 폴더가 이미 있으면 기존 파일을 보존하기 위해 시작을 거부합니다. 리비전은 기록과 참조를 보존하며 덮어쓴 파일 내용이나 Rhino 형상을 복원하지 않습니다.
<!-- /instruction:execute_looping -->

## project_info

<!-- instruction:project_info -->
When to use: Read missing project paths, registered file references, live-document identity or selected artifact context on first connection/reconnection, after evidence of a document change or when explicitly requested.
Before calling: No other tool is required. Reuse known context; a new instruction alone is not a reason to refresh. Either project or document requests the live document once, so do not call get_rhino_context merely to repeat that check.
Inputs from earlier results: Select only needed sections: project, document and locations are the defaults; runtime is optional. files_limit (1–500, default 50) and files_offset (nonnegative, default 0) page project.files. Use an earlier set_working_plan selection to interpret locations, not as a prerequisite. With include_ids=true, project.files[].project_file_id feeds Phase/Scene project_file_id inputs and distinguishes duplicate filenames; document.runtime_serial_number and runtime.rhinocode.pipe_id are also opt-in.
Interpretation: project.project_root is the absolute project root; managed paths are relative to it. project.file_name/file_path identify the observed live document once, and is_bound_document is true when it is the bound model, false when it is a different document. project.files is the DB's recorded file list, not a disk scan; files_page retains total/limit/offset/truncated, where truncated means more rows follow this page. document contains units, tolerances, modified state and counts. locations.database is project-wide; artifact_dir belongs to the Plan selected by this connection and is null until selected. runtime exposes requested runtime diagnostics. Use get_policy for basic instructions.
Limits: This does not change the document, select a Plan, save files or validate geometry. Managed tools apply project/artifact paths automatically; workers supply relative paths. A recorded file does not prove disk existence or an open document. A failed live check returns an error without is_bound_document; there is no separate checked/failed flag. Refresh project after a document change or reconnection. locations/runtime alone do not query the live document.

Args:
    sections: Requested sections: project, document, locations, runtime. Omitted defaults to project/document/locations. Project includes registered files; document reads live document properties.
    include_ids: Include identity fields in the requested output; false omits supplementary IDs. Request true when a later tool needs a returned ID; this does not select extra detail groups.
    files_limit: Registered-file page size, 1..500, within the project section.
    files_offset: Zero-based registered-file offset within the project section.
<!-- /instruction:project_info -->

<!-- instruction:get_rhino_execution -->
When to use: Recover an official RhinoCode request's completion evidence, remaining result pages, logs or diagnostics without rerunning its code.
Before calling: Use an existing execute_rhino_script or execute_project_python request when pending, uncertain or missing needed output. A completed response containing the needed result requires no routine follow-up read.
Inputs from earlier results: Pass the exact returned request_id, or omit it for this connection's latest execution. Follow result_page offsets with offset/limit and choose result_fields/include_result/include_stdout as needed; include_stdout defaults false. include_ids defaults true for authored results. Set include_diagnostics=true for operation identity, native/CLI, Undo and file/hash evidence. External client wrappers reconcile a live connection with connection_id; after a client process restart, omit that wrapper connection_id and provide the exact request_id to read retained evidence only, without reconnecting or executing Rhino work.
Interpretation: Read completed, status, mutation_state and result/result_page together. Successful completed reads are compact; pending, uncertain, failed, partial, nonzero-CLI or result-display-error outcomes retain detailed evidence. native_completed can be true while completed remains false until the exact final Rhino receipt and CLI process exit both agree. Page information is retained even on the final page.
Limits: This query never executes or cancels Rhino work, reconnects a lost model or rolls back changes. Timeout/process exit alone is not completion; late exact receipts may reconcile CLI-only uncertainty but unrelated native uncertainty stays blocked. Pending/finishing work keeps ownership. Files/evidence last until connection cleanup and can still be read after a model rename/deletion while their original session storage remains. Request identity is always returned; operation identity is diagnostic.

Args:
    request_id: Previously returned execution request_id; empty selects the most recent request for this session. A timeout requires retrieving the same request, not resubmitting code.
    include_result: Include the saved result when true.
    include_stdout: Include captured stdout when true; this does not run code again.
    result_fields: Optional top-level result field names to retain; omission keeps the result fields.
    offset: Zero-based result page offset (array rows or string characters); stdout uses its byte-stream offset.
    limit: Result page size, 1..1000; stdout is independently bounded by its stream budget.
    include_ids: Include request/execution identity fields; default true.
    include_diagnostics: Include detailed execution diagnostics when true.
<!-- /instruction:get_rhino_execution -->

<!-- instruction:set_working_plan -->
When to use: Select or resume an existing Plan and optional Step as this connection's output workspace before writing Plan-owned artifacts.
Before calling: Reuse a known plan_id or obtain one from create_plan or list_plans; get_phase_plan_step(plan_id=...) supplies Step handles if the step_id is unknown. Plans/Steps need not be completed or followed linearly to select them.
Inputs from earlier results: Pass the existing plan_id and optional matching steps[].step_id. On first selection artifact_name is one folder label; otherwise the Plan goal provides it. Reuse an existing folder instead of selecting a new Plan just to continue work.
Interpretation: The response returns plan_id, step_id, loop_no, revision, plan_artifact_dir and the project-relative artifact_dir. Executed Loops use .almond/produced/YYMMDD_name/01, /02 and later; before execute_looping, loop_no=0 uses the Plan root without a 00 folder. revision is the Plan revision at selection, after any first-folder setup; revision is assigned automatically; if using the optional expected_revision guard, also pass loop_no after Loop execution starts. Selection belongs to this connection; the Plan folder/refs are shared and discoverable by other workers. The directory is created only when files are needed.
Limits: Selection uses the latest Loop only and does not advance it, execute Steps, create geometry or mark work complete. Use execute_looping to begin a new pass or explicitly resume the current one. A selection made stale by another connection advancing the Loop cannot write artifacts until reselected. An existing .almond/produced folder is reused; rename_artifact_folder changes its name. Legacy tmp or .almond/tmp Plan folders must first be migrated with rename_artifact_folder and the explicit plan_id. execute_project_python uses the selected folder as cwd; Rhino C# can write through RhinoAlmondBridge.ManagedFiles.Output("relative-name").

Args:
    plan_id: Existing Plan ID from list_plans.plans[].plan_id or get_phase_plan_step.id.
    step_id: Optional Step ID within the Plan; empty selects the Plan without a Step. Selection does not run or complete it.
    artifact_name: Initial folder name only, never an absolute or relative path; omitted uses the Plan goal. Files go under .almond/produced/YYMMDD_name. Existing folders are reused.
    loop_no: Optional current Loop number guard; older or unknown Loops cannot be selected for writing.
<!-- /instruction:set_working_plan -->

<!-- instruction:rename_artifact_folder -->
When to use: Rename an existing Plan-owned artifact folder without losing current Plan/Step references.
Before calling: Reuse a known plan_id with an artifact folder, or select its workspace through set_working_plan when relying on the default current Plan. There is no need to create a replacement Plan.
Inputs from earlier results: Pass the Plan's existing plan_id when not using the current selection and one new folder name as name; the tool adds the YYMMDD_ prefix. Use the previously returned artifact_dir to recognize which folder is being renamed, not as name.
Interpretation: The response returns the current artifact_dir and, when changed, previous_artifact_dir. The destination is always .almond/produced/YYMMDD_name. Managed writes are serialized and current Plan/Step file refs are rewritten together; continue using the new path. Legacy Plan folders directly under tmp or .almond/tmp can be moved here with the same name and an explicit plan_id. Existing destinations are rejected; folders are never merged or overwritten.
Limits: Renaming is allowed only before the Plan starts execution and only if no past Loop references its files; executed Loop paths must remain unchanged. Existing destinations are never overwritten. This is a folder/ref operation, not a model rename or model save; immutable revision history is intentionally not rewritten. A Plan without an owned artifact folder must be selected first.

Args:
    name: New Plan artifact folder label; the date prefix is managed by the runtime. Moves the owned folder and updates related stored references.
    plan_id: Optional Plan ID; empty uses the currently selected working Plan.
<!-- /instruction:rename_artifact_folder -->

<!-- instruction:execute_project_python -->
When to use: Run synchronous Python 3 in the bound Rhino with the selected Plan artifact folder as cwd when code needs Plan-owned outputs.
Before calling: Select or resume the intended workspace with set_working_plan; reuse an already valid selection. Reuse observed targets/units and the bundled rhino3d-scripts skill/references, currently available via get_policy(policy="rhino_scripting"), when authoring Rhino code.
Inputs from earlier results: Use set_working_plan's artifact_dir as the output context and previously observed GUIDs/measurements in code. Relative writes land in the current Loop folder and may overwrite files in that same Loop; doc and scriptcontext.doc are the bound RhinoDoc. Assign a JSON-safe value to result and record useful output refs in the Plan/Step.
Interpretation: The response includes the RhinoCode outcome, request_id and selected artifact_dir. Use the exact request_id with get_rhino_execution for pending/uncertain completion, missing result pages or needed diagnostics, not after every completed result. project_root is absolute and artifact_dir is relative.
Limits: Do not write to earlier Loop paths; keep them as inputs and write revised outputs in the current Loop. The selected folder and managed path helpers are protections, not an OS sandbox against arbitrary Python or absolute-path file writes. This is Rhino's embedded Python, not the external worker venv; missing packages are not installed automatically. The wrapper temporarily applies project/artifact environment and restores cwd, scriptcontext, Undo and redraw. Timeout limits waiting and does not kill Rhino or roll back partial changes; do not rerun writes merely because the CLI returned/timed out. Do not switch documents or launch detached/background writers.

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
