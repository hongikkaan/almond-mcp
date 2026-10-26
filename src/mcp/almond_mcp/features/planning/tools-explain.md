# tools.py explain

## create_generation_phase

<!-- instruction:create_generation_phase -->
Create an organizational Phase for Plans; this does not edit Rhino geometry.
<!-- /instruction:create_generation_phase -->

## get_generation_phase

<!-- instruction:get_generation_phase -->
Read a Phase's name, description and Plan count.
<!-- /instruction:get_generation_phase -->

## list_generation_phases

<!-- instruction:list_generation_phases -->
List organizational Phases with totals and an explicit truncation flag; limit is 1-500.
<!-- /instruction:list_generation_phases -->

## update_generation_phase

<!-- instruction:update_generation_phase -->
Update Phase organization; omitted fields retain their values.
<!-- /instruction:update_generation_phase -->

## create_generation_plan

<!-- instruction:create_generation_plan -->
Create a dependency-ordered Plan in an optional organizational Phase.
scope is house, interior, structure, drawing, or component; component uses
inspect_context, design, model, validate. scene_ids are context; component_ids
explicitly bind targets without requiring membership in those Scenes.
Legacy scene_id must match the first scene_ids entry when both are supplied.
Plans record state and evidence, do not execute steps, and do not authorize edits.
<!-- /instruction:create_generation_plan -->

## get_generation_plan

<!-- instruction:get_generation_plan -->
Read the current Plan or an immutable saved revision, including legacy baseline 0.

Snapshots contain Plan metadata, step state and handles; they are not Rhino
geometry backups. A missing requested revision never falls back to current state.
<!-- /instruction:get_generation_plan -->

## list_generation_plans

<!-- instruction:list_generation_plans -->
List compact Plan summaries, optionally filtered by Phase, contextual Scene or status.
<!-- /instruction:list_generation_plans -->

## update_generation_plan

<!-- instruction:update_generation_plan -->
Update Plan metadata and bindings atomically, recording a new saved revision.

Omitted fields retain prior values; [] clears refs, and phase_id='' detaches
the Phase. expected_revision rejects stale updates without changing the Plan.
References provide context and explicit targets, not permission to edit geometry.
<!-- /instruction:update_generation_plan -->

## list_generation_plan_revisions

<!-- instruction:list_generation_plan_revisions -->
List saved Plan revisions newest first, with operation labels and truncation metadata.
<!-- /instruction:list_generation_plan_revisions -->

## update_generation_step

<!-- instruction:update_generation_step -->
Record a Step's status, evidence and optional explicit Component targets.
Omitted refs retain prior values; [] clears them. Step component_ids=null in a
returned Plan inherits Plan targets; explicit [] selects none. Scene refs never
expand the selection. running/completed require completed prerequisites, and a
prerequisite cannot regress while descendants run or remain completed.
expected_revision rejects stale updates. No Rhino operation is executed here.
<!-- /instruction:update_generation_step -->

## resolve_generation_targets

<!-- instruction:resolve_generation_targets -->
Resolve registered Step targets, or Plan targets when the Step has no override.

An explicit empty Step selection stays empty. Contextual Scenes never expand
targets. Returned group/document identities have live_verified=false; inspect
current Rhino state and user intent before editing. This does not grant authority.
<!-- /instruction:resolve_generation_targets -->
