# Planning tools

## create_phase

<!-- instruction:create_phase -->
When to use: Create an organizational Phase for related Plans without editing Rhino geometry.
Before calling: Supply a nonempty name. status accepts pending, running, paused, completed, failed or blocked. file_name is a filename without folders; depends_on contains only phase_ IDs.
Inputs from earlier results: project_info(sections=["project"], include_ids=true).project.files[].project_file_id selects an existing file and distinguishes duplicate filenames. list_phases.phases[].phase_id supplies Phase dependency references.
Interpretation: phase.phase_id feeds list_plans.phase_id, get_phase_plan_step.phase_id or update_phase.phase_id. Dependencies are recorded relationships; [] means none.
Limits: Same-kind references may be uncreated, self-referential or cyclic; they do not force execution or completion. This creates no model or Plan and does not verify a file on disk.
<!-- /instruction:create_phase -->

## list_phases

<!-- instruction:list_phases -->
When to use: Begin Phase → Plan → Step discovery or inspect the project's organizational Phases.
Before calling: Choose limit from 1–500. Optional field_groups are description, scope, audit or all; no earlier lookup is required.
Inputs from earlier results: None required. Every phases[].phase_id is visible and feeds list_plans(phase_id=...) or get_phase_plan_step(phase_id=...).
Interpretation: Rows contain phase_id, name, status, plan_count and Phase depends_on IDs. next_step explains how to read the selected Phase's details or list its Plans. total and truncated describe the bounded list; description adds prose, scope adds file references and audit adds stored timestamps.
Limits: This is recorded organization, not evidence of live geometry or completed design. IDs are always returned; there is no include_ids argument. There is no offset argument.
<!-- /instruction:list_phases -->

## update_phase

<!-- instruction:update_phase -->
When to use: Revise a Phase's name, description, status, file association or Phase dependency references.
Before calling: Supply phase_id and only intended changes. depends_on accepts {add: string[], remove: string[]}; omit either array for no operation. Omitted/null fields and an empty patch stay unchanged. Use only phase_ IDs. file_name='' clears the file association when project_file_id is omitted.
Inputs from earlier results: list_phases.phases[].phase_id or get_phase_plan_step(phase_id=...).id feeds phase_id. project_info(..., include_ids=true).project.files[].project_file_id selects an existing project file.
Interpretation: The acknowledgment returns phase.phase_id/status, changed and issues for skipped input items. status is success with no skips, partial_success with applied changes and skips, or no_change with skips but no actual change. A repeated scalar value is a no-op. Each issue identifies field, add/remove operation, zero-based index, original value and reason.
Limits: Conflicting add/remove values are skipped on both sides; duplicates, already-present additions, absent removals and invalid string values affect only those items. Invalid general fields or input types/structure reject the entire request. This does not rename/move a model, propagate status or enforce dependency order. Same-kind dependencies need not exist and may contain cycles or self-references.
<!-- /instruction:update_phase -->

## create_plan

<!-- instruction:create_plan -->
When to use: Record a titled Plan with template Steps, optional Phase organization, contextual Scenes and explicit Holon targets.
Before calling: Supply nonempty title and goal. title is the short list label; goal preserves the full objective. scope defaults to house; existing house/interior/structure/drawing/component templates remain. Choose spatial_development, plan_editing, construction_detail, model_revision or inspection for task-oriented work. phase_id is optional; depends_on accepts only plan_ IDs.
Inputs from earlier results: list_phases.phases[].phase_id feeds phase_id. Scene and Holon discovery provide scene_ids and holon_ids. The legacy scene_id, when supplied with scene_ids, must equal its first item. list_plans.plans[].plan_id provides dependency references.
Interpretation: plan.plan_id and revision feed get_phase_plan_step, set_working_plan and subsequent updates. The selected scope creates its ordered template Steps; Holon targets belong to the Plan only.
Limits: Creating a Plan does not select its artifact folder, edit Rhino or force Step execution. construction_detail is a template, not an enabling flag: detailed construction modeling still needs the user's request for that Task. inspection has no modeling Step. Existing custom scope mappings are preserved. Dependencies may be uncreated, self-referential or cyclic and do not enforce completion.
<!-- /instruction:create_plan -->

## get_phase_plan_step

<!-- instruction:get_phase_plan_step -->
When to use: Read one Phase, Plan or specific Step in detail, including a saved Plan/Step revision when needed.
Before calling: Supply exactly one of phase_id or plan_id. A step_id requires plan_id and selects only that Step. revision is valid only for a Plan or Step; include_holons=true is valid only for a Plan. No include_ids or field_groups argument is accepted.
Inputs from earlier results: list_phases.phases[].phase_id selects a Phase; list_plans.plans[].plan_id selects a Plan. A Plan result's plan.steps[].step_id selects one Step under the same plan_id. list_plan_revisions.revisions[].revision selects saved state.
Interpretation: Common id, type and status identify the selected item and its workflow state. phase contains name, description, file_name/project_file_id, Phase depends_on and plan_titles. plan contains title, goal, scope, revision, phase (phase_id/name or null), Plan depends_on, scene_ids, artifact_dir/artifact_refs, created_at/updated_at in KST YYYY-MM-DD-HH:mm and Step ID/name/status summaries. Plan holon_ids appear only with include_holons=true; available_details lists an unrequested include_holons option. step contains its plan_id, Plan revision, name and only that Step's input_refs/output_refs. IDs are always returned. Plan next_step explains specific-Step detail and set_working_plan; Step next_step explains selecting that work context and artifact location. Selection is not execution or a status change.
Limits: This does not select a working Plan, execute a Step or verify geometry. status is the item's pending/running/paused/completed/failed/blocked state; status=error reports a failed query. Step records have no Holon assignment. Old snapshots stay immutable; missing legacy titles are derived from their goals, and an unavailable historical Phase name is null. Revisions are metadata history, not Rhino backups. Historical next_step keeps the revision for Step discovery and directs a fresh query without revision before selecting current work; set_working_plan never restores history.
<!-- /instruction:get_phase_plan_step -->

## list_plans

<!-- instruction:list_plans -->
When to use: List concise Plan titles within a Phase, or use existing scene/status filters to inspect recorded work.
Before calling: Prefer phase_id from list_phases. scene_id and status are optional existing filters; omitted filters span the project. limit is 1–500. There are no field_groups or include_ids arguments.
Inputs from earlier results: list_phases.phases[].phase_id feeds phase_id; Scene discovery can supply scene_id. Every returned plans[].plan_id feeds get_phase_plan_step(plan_id=...).
Interpretation: Each row contains plan_id, title, scope, status and revision. goal and repeated Phase membership are omitted. total/limit/truncated describe the list; next_step explains Plan detail and specific-Step discovery.
Limits: This reads stored metadata and does not prove design completion. The current filters remain available; no new cross-Phase progress mode or multi-Plan detail batch is implied.
<!-- /instruction:list_plans -->

## update_plan

<!-- instruction:update_plan -->
When to use: Change a Plan's title, full goal, Phase, Scene context, Plan Holon targets, dependency references, status or artifact references.
Before calling: Supply plan_id and intended fields. depends_on accepts {add: string[], remove: string[]} with plan_ IDs; omitted/null/empty patches retain it. Other arrays retain their replacement contract: omission/null preserves and [] clears. phase_id='' detaches the Phase. title and goal must be nonempty when supplied. expected_revision remains optional.
Inputs from earlier results: list_plans.plans[].plan_id or get_phase_plan_step(plan_id=...).id identifies the Plan. The detail's plan.revision feeds expected_revision; Phase/Scene/Holon discovery provides relationship IDs.
Interpretation: plan.plan_id/status/revision, changed and issues acknowledge the result. success means no skips, partial_success means changes plus skipped items, and no_change means skips without actual change. Issues identify field, operation, index, value and reason. Actual changes create one revision; unchanged values create none. Explicit Plan status remains until a real Step status change recalculates it.
Limits: Invalid general fields, unknown targets, stale expected_revision or malformed input reject the entire request. Dependency string item problems are reported individually; same-value add/remove skips both. References are recorded, not executed or verified. Same-kind dependencies allow uncreated IDs, self-references and cycles. This does not select a folder or edit geometry; update_step remains separate.
<!-- /instruction:update_plan -->

## list_plan_revisions

<!-- instruction:list_plan_revisions -->
When to use: Discover which metadata operations created a Plan's saved revisions before reading an earlier state.
Before calling: Supply plan_id and limit from 1–500. Optional field_groups accepts audit or all to include stored revision timestamps.
Inputs from earlier results: A Plan's id or list_plans.plans[].plan_id feeds plan_id. Each revisions[].revision feeds get_phase_plan_step(plan_id=..., revision=...), optionally with step_id.
Interpretation: plan_id is always returned; rows expose revision and operation, with created_at when audit/all is selected. total/limit/truncated describe available history. There is no include_ids argument.
Limits: Revisions preserve Plan metadata and Step records, not Rhino geometry. Artifact folder setup can create a revision. Reading history neither restores it nor changes current state.
<!-- /instruction:list_plan_revisions -->

## update_step

<!-- instruction:update_step -->
When to use: Track a Step's status or revise its input/output evidence under its Plan.
Before calling: Supply plan_id and step_id. status is optional (pending, running, paused, completed, failed or blocked); omission/null keeps it. input_refs/output_refs accept {add: string[], remove: string[]}; omission/null/{} and empty add/remove retain existing records. Remove observed values to clear them. Bare replacement arrays are not accepted. Holon assignment belongs to update_plan.
Inputs from earlier results: get_phase_plan_step(plan_id=...).plan.steps[].step_id identifies a Step; add step_id to that query to read its current input_refs/output_refs. plan.revision or step.revision feeds expected_revision.
Interpretation: The response acknowledges plan.plan_id/status/revision and step.step_id/status, with changed and issues. success has no skips; partial_success has changes and skipped items; no_change has skips but no actual change. Each issue identifies field, add/remove operation, zero-based index, original value and reason. Any combination of valid status/refs edits creates one Plan revision if changed. Reference-only edits preserve the current Step and paused/completed Plan; a real Step status change recalculates Plan status.
Limits: Same-value add/remove skips both; duplicate_input, already_present, not_found and invalid_value skip only the affected string item. Invalid status, unknown target, stale expected_revision or malformed input/type rejects the entire request. Evidence strings are stored, not verified; partial application may leave a requested record replacement unfinished. Dependencies do not gate execution and this call grants no authority to edit geometry. No actual change creates no revision.
<!-- /instruction:update_step -->

## resolve_targets

<!-- instruction:resolve_targets -->
When to use: Identify a Plan's registered Holon target set before deciding how to inspect or act on it.
Before calling: Supply plan_id; an optional step_id validates the Step context but never overrides Plan targets. field_groups accepts references, geometry, scope, audit or all.
Inputs from earlier results: list_plans.plans[].plan_id or unified detail id supplies plan_id. Plan detail supplies step IDs when needed. Returned holon_ids feed focus_holons or Holon detail queries; revision can feed expected_revision.
Interpretation: source is plan. A Plan's explicit empty target set stays empty. IDs are always returned, including plan_id and a supplied step_id; there is no include_ids argument. Optional groups add available hierarchy, model/group identity or timestamp fields.
Limits: Scene context never expands targets. This returns stored identities with live_verified=false, not verified group membership, live geometry or edit authorization. Steps own no separate Holon targets.
<!-- /instruction:resolve_targets -->

## get_selection_references

<!-- instruction:get_selection_references -->
When to use: Discover which recorded Plans refer to the current Rhino selection, including ancestor Holons.
Before calling: A live saved document is needed. selection_limit is 1–200 and the matching-Plan limit is 1–500. field_groups selects steps, references, geometry, artifacts, description, scope, audit or all.
Inputs from earlier results: No IDs are required. Returned plans[].plan_id feeds get_phase_plan_step or resolve_targets. The steps group adds Step summaries belonging to the matched Plan. Holon and object handles are always visible for separately authorized follow-up work.
Interpretation: Target references belong to Plans. Optional Step summaries have source=plan and do not imply Step assignments. ownership_live_verified concerns native selected-object ownership; references_live_verified=false concerns stored ancestry and Plan relationships. Selection counts, total_plans and truncated remain explicit.
Limits: There is no include_ids argument. Scene context invents no targets; this query does not reconcile registrations or authorize edits. Obtain the current Plan revision before relying on an expected_revision guard.
<!-- /instruction:get_selection_references -->
