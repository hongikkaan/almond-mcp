# tools.py explain

## create_phase

<!-- instruction:create_phase -->
Create an organizational Phase for Plans; this does not edit Rhino geometry.
<!-- /instruction:create_phase -->

## get_phase

<!-- instruction:get_phase -->
Read a Phase's name, description and Plan count.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds description, scope, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:get_phase -->

## list_phases

<!-- instruction:list_phases -->
List organizational Phases with totals and an explicit truncation flag; limit is 1-500.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds description, scope, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:list_phases -->

## update_phase

<!-- instruction:update_phase -->
Update Phase organization; omitted fields retain their values.
<!-- /instruction:update_phase -->

## create_plan

<!-- instruction:create_plan -->
Create a Plan in an optional organizational Phase. Work may pause, switch and
resume in any order; a Plan does not require linear completion.
scope is house, interior, structure, drawing, or component; component uses
inspect_context, design, model, validate. scene_ids are context; component_ids
explicitly bind targets without requiring membership in those Scenes.
Legacy scene_id must match the first scene_ids entry when both are supplied.
Plans record state and evidence, do not execute steps, and do not authorize edits.
depends_on is an array of related Plan or Phase IDs, including tasks in other
Phases. It does not enforce existence, completion, cycles, self-reference or
execution order. Use ["plan_a", "phase_b"], never "plan_a, phase_b".
<!-- /instruction:create_plan -->

## get_plan

<!-- instruction:get_plan -->
Read the current Plan or an immutable saved revision, including legacy baseline 0.
IDs (including Step component_ids) are hidden unless include_ids=true.
The supplied plan_id is not repeated. artifact_dir and artifact_refs locate work files.

Snapshots contain Plan metadata, step state and handles; they are not Rhino
geometry backups. A missing requested revision never falls back to current state.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds steps, references, artifacts, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:get_plan -->

## list_plans

<!-- instruction:list_plans -->
List compact Plan summaries, optionally filtered by Phase, contextual Scene or status.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds references, artifacts, audit, or all; default is summary. For Step detail use get_plan(field_groups=["steps"]).
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:list_plans -->

## update_plan

<!-- instruction:update_plan -->
Update Plan metadata and bindings atomically, recording a new saved revision.

Omitted fields retain prior values; [] clears refs, and phase_id='' detaches
the Phase. expected_revision rejects stale updates without changing the Plan.
References provide context and explicit targets, not permission to edit geometry.
depends_on is a free array of related Plan/Phase IDs, including other Phases.
status may be pending, running, paused, completed, failed or blocked; it imposes
no completion requirement on related work. artifact_refs records work files.
<!-- /instruction:update_plan -->

## list_plan_revisions

<!-- instruction:list_plan_revisions -->
List saved Plan revisions newest first, with operation labels and truncation metadata.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:list_plan_revisions -->

## update_step

<!-- instruction:update_step -->
Record a Step's status, evidence and optional explicit Component targets.
Omitted refs retain prior values; [] clears them. Step component_ids=null in a
returned Plan inherits Plan targets; explicit [] selects none. Scene refs never
expand the selection. Status may be pending, running, paused, completed, failed
or blocked. Dependencies are references, not execution gates. Any Step can be
paused or resumed regardless of other Steps; no forced completion is required.
expected_revision rejects stale updates. No Rhino operation is executed here.
<!-- /instruction:update_step -->

## resolve_targets

<!-- instruction:resolve_targets -->
Resolve registered Step targets, or Plan targets when the Step has no override.

An explicit empty Step selection stays empty. Contextual Scenes never expand
targets. Returned group/document identities have live_verified=false; inspect
current Rhino state and user intent before editing. This does not grant authority.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds references, geometry, scope, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:resolve_targets -->

<!-- instruction:get_selection_references -->
Read the current selection and return its registered Component, Plan and Step IDs
and names in one call. IDs are always included because this is an explicit ID lookup.
Distinguishes direct Step targets from inherited Plan targets and includes ancestor
Components. Scene context never invents targets. Selection is live; relationships
are registered metadata, not a fresh native ownership reconciliation. Unregistered
objects and truncated selection/Plan results are reported explicitly.
field_groups adds steps, references, artifacts, description, scope, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:get_selection_references -->
