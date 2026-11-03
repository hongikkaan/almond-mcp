# tools.py explain

## upsert_ontological_holon

<!-- instruction:upsert_ontological_holon -->
When to use: Register or update a semantic Holon bound to a current Rhino group, without copying geometry.
Before calling: Use the active saved document; expected_model_path, if supplied, must match it. Supply at least one existing Scene (omitting scene_ids preserves an existing association). Each object has one direct Holon owner; children have at most one same-document parent and no cycles. Use the existing group's exact current name: renaming is refused because group-table changes are not Undo-tracked. Registration requires design_components=1 and component_registry=2; omitted/null object_ids also requires component_group_inference=1.
Inputs from earlier results: Reuse valid Scene handles from Scene creation or list_design_scenes(include_ids=true), and Holon handles from registration acknowledgements or list_ontological_holons(include_ids=true). These semantic IDs are not Rhino GUIDs. object_ids are current top-level object GUIDs for DIRECT owners, not child members; obtain them from an existing valid observation or a live Holon read with include_ids=true and field_groups=["geometry"]. rhino_group_id is a group GUID, not its name/index or a Holon ID. Omit object_ids or pass null to infer direct owners from that existing group or holon_id's binding; native validation reads its actual members and declared children together. child_holon_ids=None preserves children; [] detaches them. Explicit object_ids=[] means no direct owners and requires existing children.
Interpretation: The compact component acknowledgement returns holon_id and rhino_group_id with status, availability, object_count and live_verified when available; retain these handles. The document-private registry records meaning, Scene links and explicit children without object management attributes. Actual group membership/order is truth; child members retain their ownership. One exact ordinary group is adopted; ambiguous matches require its GUID. Only an explicitly requested new group may be created, and name collisions fail before mutation rather than adding a suffix.
Limits: Ordinary groups/blocks are not automatically meaning units. Inference needs an existing group with 1–4096 valid members and never infers name, Scene context or child links, creates a missing group, or repairs membership/order from DB records. No geometry is duplicated. Registration Undo restores original object membership and removes meaning, but an empty non-Undo-tracked group-table entry may remain; review the intended structure rather than repairing or replaying an undone registration. After an uncertain native result, inspect current state and sync_ontological_holon; never replay the mutation automatically.
<!-- /instruction:upsert_ontological_holon -->

## get_ontological_holon

<!-- instruction:get_ontological_holon -->
When to use: Read a cached Holon summary or observe its current Rhino group without changing Rhino or the ledger.
Before calling: Choose live=true for current members/name; live=false is cached. recursive=false is the default; use true only when effective nested geometry is needed. An existing valid observation can be reused instead of requiring another read.
Inputs from earlier results: Pass a semantic holon_id from a registration acknowledgement or list_ontological_holons(include_ids=true), not a Rhino object/group GUID. For live member GUIDs, request live=true, include_ids=true and field_groups=["geometry"]; add "references" for Scene/parent/child handles and rhino_group_id.
Interpretation: Default output is a summary with IDs/GUIDs omitted; the supplied holon_id is not repeated even with include_ids=true. field_groups selects references, geometry, scope, audit or all; include_ids separately permits IDs within the selected fields, and audit enables timestamps. live_verified identifies a live observation; requires_sync reports ledger disagreement without aligning it.
Limits: Cached geometry_available=false means group-level summaries only, never member IDs or per-object geometry, even when geometry fields are requested. Live observation validates the registration snapshot, not design correctness or overlap/topology suitability for editing. Geometry CRCs or pair_state needed by another operation must come from that operation's relevant observation, not from a summary.
<!-- /instruction:get_ontological_holon -->

## list_ontological_holons

<!-- instruction:list_ontological_holons -->
When to use: Discover compact cached Holon registrations, optionally filtered by model path or Scene.
Before calling: Choose the intended scope; an omitted expected_model_path does not restrict this cached list to the active document. recursive=false lists roots in that scope; true includes registered descendants. Scene-scoped roots follow that Scene's canonical links, even when a Holon has a parent in another Scene.
Inputs from earlier results: Use a Scene handle from Scene creation or list_design_scenes(include_ids=true) as scene_id, not a Scene name or Rhino GUID. Request include_ids=true to obtain holon_id handles for later reads, registration updates, alignment, removal, focus or intersection queries; add field_groups=["references"] for Scene/parent/child handles and group GUIDs.
Interpretation: Results report total and live_verified=false. Default output omits IDs/GUIDs; include_ids enables handles only within selected fields. field_groups selects references, geometry, scope, audit or all; default is summary and audit enables timestamps. Returned holon_id is a semantic handle, whereas rhino_group_id is the physical Rhino group GUID.
Limits: This does not inspect or align Rhino. Cached geometry_available=false records contain group summaries, not member GUIDs or per-object geometry; selecting geometry fields cannot turn them into live evidence. Use existing valid live evidence or an explicit live read when current membership matters.
<!-- /instruction:list_ontological_holons -->

## sync_ontological_holon

<!-- instruction:sync_ontological_holon -->
When to use: Align the ledger with current Rhino Holon registrations once, without modifying model structure.
Before calling: Use the bound saved document in a stable editing state; a supplied expected_model_path must match. Choose one holon_id, holon_ids, one scene_id, or no targets for the bound document; do not combine target forms. Group/block editing, unknown isolation and other unstable states refuse alignment. No routine pre-query or repeated sync is required when existing evidence remains valid.
Inputs from earlier results: Use semantic Holon handles from registration acknowledgements or list_ontological_holons(include_ids=true), or a Scene handle from Scene creation/listing with IDs enabled. Optional rhino_group_id is a GUID consistency check for an existing single holon_id binding, not a way to rebind it; obtain it from an acknowledgement or a read with include_ids=true and field_groups=["references"].
Interpretation: The compact reply reports checked/changed/unavailable counts, per-item problems and Scene revisions; complete native snapshots stay internal. A successful single target can add a compact component acknowledgement with its Holon and group handles. Valid unrelated registrations can align despite individual problems; repeated unchanged alignment creates no revision.
Limits: Scope is at most 64 registrations including descendants and is response-size bounded; narrow larger scopes. Scene/document discovery may find native registrations missing from the DB, while explicit Holon scope does not broaden that way. Geometry, groups, membership/order, names, selection/view and object attributes are unchanged. Missing groups retain identity/history for Rhino Undo, never recreate geometry. Inspect item-specific recovery instructions; never replay an uncertain mutation as a substitute for reconciliation.
<!-- /instruction:sync_ontological_holon -->

## remove_ontological_holon

<!-- instruction:remove_ontological_holon -->
When to use: Unregister a Holon's semantic meaning while preserving its Rhino geometry, ordinary group and object attributes.
Before calling: A Holon with its own parent must first be detached, and Plan/Step references to it must be cleared. Confirm the intended semantic removal rather than treating it as geometry deletion.
Inputs from earlier results: Pass the semantic holon_id from a registration acknowledgement or list_ontological_holons(include_ids=true), not a Rhino object/group GUID. Existing valid references can be reused; no fresh read is mandatory solely to obtain an already-known handle.
Interpretation: The compact acknowledgement identifies the removed holon_id and rhino_group_id with unregistered status. Children of a removed root become registered roots and retain direct object ownership, Rhino groups and Scene links. Rhino Undo/Redo restores or removes the document-private semantic binding.
Limits: No geometry is deleted or copied and existing object attributes are preserved. Native semantic changes and DB commits are separate: an uncertain result requires inspecting current registry/groups and alignment, not automatically retrying removal. Undo of meaning does not imply any group-table rename/create/delete rollback.
<!-- /instruction:remove_ontological_holon -->

## show_object_intersection

<!-- instruction:show_object_intersection -->
When to use: Preview one observed solid overlap in the active model viewport without adding document geometry.
Before calling: Use the current regular Rhino model view and bound saved document; supplied expected_model_path must match. Reuse an existing pair observation while its state remains valid; clear=true removes the preview without handles or state.
Inputs from earlier results: Pass a.handle and b.handle from a Holon or object intersection result as a and b, plus that pair's unchanged pair_state. Handles contain the top-level object GUID in object_id and optional nested member GUIDs in path, not Holon IDs or full pair records. Pair receipts are returned regardless of intersection ID/display options; no separate topology, face-index or raw-CRC input substitutes for pair_state.
Interpretation: Native code resolves both occurrences, validates the receipt and recomputes the overlap. Names, layers and region measurements accompany displayed geometry; displayed=false can report no confirmed solid even with a positive volume. Block occurrences can be shown without changing definitions.
Limits: Unknown overlap or positive volume with no returned solid never produces a fabricated preview. Geometry/attribute/definition changes invalidate the transient display and stale receipts are rejected; inspect again when invalidated. A preview is viewport/document-scoped visual evidence only, not an edit, semantic registration or design validation.
<!-- /instruction:show_object_intersection -->

## resolve_object_intersection

<!-- instruction:resolve_object_intersection -->
When to use: Subtract a selected keep solid from a trim solid while preserving the trim object's GUID and document attributes.
Before calling: Confirm the intended keep/trim direction in the bound writable saved document and stable model-editing state; supplied expected_model_path must match. A confirmed positive overlap is required and recomputed before editing. A preview is optional, not a mandatory step.
Inputs from earlier results: Pass the two returned occurrence handles from a still-valid Holon or object intersection observation as keep and trim, with that pair's pair_state. Handles use object_id and path, not semantic Holon IDs; the receipt validates current geometry CRCs/occurrence state. Do not construct it from a summary, raw CRC or topology/face index. Either pair direction can be chosen explicitly; keep remains unchanged.
Interpretation: One validated object replacement runs through the existing executor/Undo boundary, preserving the trim GUID, attributes and group membership. The result must confirm edited=true, matching keep_id/trim_id and a changed geometry_crc relative to previous_geometry_crc; those receipts establish the checked replacement, not design suitability. Closed Mesh pairs and document-level Brep/Extrusion pairs are supported; disjoint Mesh results remain one Mesh object.
Limits: Block/linked-source members, mixed Mesh/Brep edits, textured or vertex-coloured meshes, unpreservable geometry user data, whole-target deletion and multiple-Brep results are rejected without editing. Geometry is validated and its reduced volume checked against the observed overlap within numeric uncertainty before replacement; this is not comprehensive topology/design validation. A timeout, result_error or unconfirmed receipt is not rollback: inspect the target before deciding on any retry. No source asset or semantic Holon registration is automatically changed.
<!-- /instruction:resolve_object_intersection -->

## focus_holons

<!-- instruction:focus_holons -->
When to use: Select, isolate and zoom to the current members and registered descendants of Holons.
Before calling: Use 1–32 distinct present Holon handles in the current regular Rhino document with an active model view and no command or Undo/Redo in progress. Targets must be visible/selectable; the resolved set must contain 1–4096 top-level model-space objects. supplied expected_model_path must match the bound saved document.
Inputs from earlier results: Use semantic holon_id handles from registration acknowledgements or list_ontological_holons(include_ids=true), not Rhino object/group GUIDs. The tool resolves current recursive membership itself; no mandatory live read, sync, topology or CRC observation precedes focus.
Interpretation: This changes selection, visibility and camera using Rhino Isolate/Unisolate bookkeeping. The reply identifies selected object GUIDs and viewport, isolation/zoom status and restore_visibility_command=Unisolate. Locked context remains visible; hiding it is not promised.
Limits: This is a viewing operation, not geometry editing or design verification. Existing hidden/locked objects and document state affect native isolation. Unisolate restores visibility through Rhino's bookkeeping, not necessarily the previous selection/camera. Failure or timeout after dispatch can leave partial UI changes: inspect current state instead of automatically retrying. See BASIC-INSTRUCTIONS.md for usage and behavior.
<!-- /instruction:focus_holons -->

## response-566

<!-- instruction:response-566 -->
Load a Bridge with design_components=1 before registering Holons.
<!-- /instruction:response-566 -->

## response-571

<!-- instruction:response-571 -->
Load a Bridge with component_operations=1 before using Holon helpers.
<!-- /instruction:response-571 -->
