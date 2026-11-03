# tools.py explain

## upsert_ontological_holon

<!-- instruction:upsert_ontological_holon -->
When to use: Register or update a semantic Holon bound to a current Rhino group, without copying geometry. A Holon combines physical elements with the shared role, behavior or structure they make possible. Choose its boundary from that relationship, not solely object type, material or proximity; a Holon can belong to several Scenes. Illustrative groupings are not mandatory registration patterns.
Before calling: Use the active saved document; expected_model_path, if supplied, must match it. Supply at least one existing Scene (omitting scene_ids preserves an existing association). Each object has one direct Holon owner; children have at most one same-document parent and no cycles. Use the existing group's exact current name: renaming is refused because group-table changes are not Undo-tracked. Registration requires design_components=1 and component_registry=2; omitted/null object_ids also requires component_group_inference=1.
Inputs from earlier results: Reuse valid Scene handles from Scene creation or list_design_scenes(include_ids=true), and Holon handles from registration acknowledgements or list_ontological_holons(include_ids=true). These semantic IDs are not Rhino GUIDs. object_ids are current top-level object GUIDs for DIRECT owners, not child members; obtain them from an existing valid observation or a live Holon read with include_ids=true and field_groups=["geometry"]. rhino_group_id is a group GUID, not its name/index or a Holon ID. Omit object_ids or pass null to infer direct owners from that existing group or holon_id's binding; native validation reads its actual members and declared children together. child_holon_ids=None preserves children; [] detaches them. Explicit object_ids=[] means no direct owners and requires existing children.
Interpretation: The compact component acknowledgement returns holon_id and rhino_group_id with status, availability, object_count and live_verified when available; retain these handles. The document-private registry records meaning, Scene links and explicit children without object management attributes. Actual group membership/order is truth; child members retain their ownership. One exact ordinary group is adopted; ambiguous matches require its GUID. Only an explicitly requested new group may be created, and name collisions fail before mutation rather than adding a suffix.
Limits: Ordinary groups/blocks are not automatically meaning units. Inference needs an existing group with 1–4096 valid members and never infers name, Scene context or child links, creates a missing group, or repairs membership/order from DB records. No geometry is duplicated. Registration Undo restores original object membership and removes meaning, but an empty non-Undo-tracked group-table entry may remain; review the intended structure rather than repairing or replaying an undone registration. After an uncertain native result, inspect current state and sync_ontological_holon; never replay the mutation automatically.

Args:
    name: Semantic Holon name; must match the exact existing Rhino group name when binding that group.
    object_ids: Current top-level Rhino object GUIDs to register. Omitted may resolve an existing named group; [] is valid only for a parent with child_holon_ids.
    expected_model_path: Usually omitted: managed sessions supply the bound saved Rhino document. An explicit path must match that binding; it does not switch documents.
    scene_ids: Existing Scene memberships; required for a new Holon. Omission preserves an existing registration; this does not create Scenes.
    holon_id: Optional existing Holon ID to revise; omitted creates a registration.
    rhino_group_id: Optional exact existing Rhino group GUID; use it to disambiguate names.
    child_holon_ids: Optional registered child Holons; [] detaches existing children and omission preserves them. Enforces one parent per child and no hierarchy cycles.
<!-- /instruction:upsert_ontological_holon -->

## get_ontological_holon

<!-- instruction:get_ontological_holon -->
When to use: Read a cached Holon summary or observe its current Rhino group without changing Rhino or the ledger.
Before calling: Choose live=true for current members/name; live=false is cached. recursive=false is the default; use true only when effective nested geometry is needed. An existing valid observation can be reused instead of requiring another read.
Inputs from earlier results: Pass a semantic holon_id from a registration acknowledgement or list_ontological_holons(include_ids=true), not a Rhino object/group GUID. For live member GUIDs, request live=true, include_ids=true and field_groups=["geometry"]; add "references" for Scene/parent/child handles and rhino_group_id.
Interpretation: Default output is a summary with IDs/GUIDs omitted; the supplied holon_id is not repeated even with include_ids=true. field_groups selects references, geometry, scope, audit or all; include_ids separately permits IDs within the selected fields, and audit enables timestamps. live_verified identifies a live observation; requires_sync reports ledger disagreement without aligning it.
Limits: Cached geometry_available=false means group-level summaries only, never member IDs or per-object geometry, even when geometry fields are requested. Live observation requires a stable normal model; group/block editing returns an error because persistent group ownership is unverified, not an empty member list or cached live substitute. It validates registration, not design correctness or overlap/topology suitability for editing. Obtain face CRCs through get_objects and intersection review_id through resolve_object_intersection when those operations are needed.

Args:
    holon_id: Registered Holon ID from a Holon query with include_ids=true or a prior registration result.
    live: Read current Rhino group membership and geometry when true; false reads only stored registration.
    include_ids: Include identity fields in the requested output; false omits supplementary IDs. Request true when a later tool needs a returned ID; this does not select extra detail groups.
    recursive: Expand registered child Holons when true; this is the semantic hierarchy, not block-definition expansion.
    field_groups: Optional detail groups: references, geometry, scope, audit or all. Omitted/empty keeps the summary; include_ids controls identities separately.
<!-- /instruction:get_ontological_holon -->

## list_ontological_holons

<!-- instruction:list_ontological_holons -->
When to use: Discover compact cached Holon registrations, optionally filtered by model path or Scene.
Before calling: Choose the intended scope; managed sessions default expected_model_path to the bound model; standalone empty input spans models. recursive=false lists roots in that scope; true includes registered descendants. Scene-scoped roots follow that Scene's canonical links, even when a Holon has a parent in another Scene.
Inputs from earlier results: Use a Scene handle from Scene creation or list_design_scenes(include_ids=true) as scene_id, not a Scene name or Rhino GUID. Request include_ids=true to obtain holon_id handles for later reads, registration updates, alignment, removal or focus; add field_groups=["references"] for Scene/parent/child handles and group GUIDs. For overlaps, first obtain current document object GUIDs with get_ontological_holon(live=true, include_ids=true, field_groups=["geometry"]) or get_objects(scope="document", group_ids=[rhino_group_id], include_ids=true), then pass the verified object IDs to get_object_intersections or resolve_object_intersection. Holon IDs are not accepted as object IDs.
Interpretation: Results report total and live_verified=false. Default output omits IDs/GUIDs; include_ids enables handles only within selected fields. field_groups selects references, geometry, scope, audit or all; default is summary and audit enables timestamps. Returned holon_id is a semantic handle, whereas rhino_group_id is the physical Rhino group GUID.
Limits: This does not inspect or align Rhino. Cached geometry_available=false records contain group summaries, not member GUIDs or per-object geometry; selecting geometry fields cannot turn them into live evidence. Use existing valid live evidence or an explicit live read when current membership matters.

Args:
    expected_model_path: Managed sessions default to the bound model; standalone empty input lists registrations across models. Does not switch the active Rhino document.
    include_ids: Include identity fields in the requested output; false omits supplementary IDs. Request true when a later tool needs a returned ID; this does not select extra detail groups.
    scene_id: Optional registered Scene ID filter; empty does not filter by Scene.
    recursive: Include registered child Holons when true.
    field_groups: Optional detail groups: references, geometry, scope, audit or all. Omitted/empty keeps the summary; include_ids controls identities separately.
<!-- /instruction:list_ontological_holons -->

## sync_ontological_holon

<!-- instruction:sync_ontological_holon -->
When to use: Align the ledger with current Rhino Holon registrations once, without modifying model structure.
Before calling: Use the bound saved document in a stable editing state; a supplied expected_model_path must match. Choose one holon_id, holon_ids, one scene_id, or no targets for the bound document; do not combine target forms. Group/block editing, unknown isolation and other unstable states refuse alignment. No routine pre-query or repeated sync is required when existing evidence remains valid.
Inputs from earlier results: Use semantic Holon handles from registration acknowledgements or list_ontological_holons(include_ids=true), or a Scene handle from Scene creation/listing with IDs enabled. Optional rhino_group_id is a GUID consistency check for an existing single holon_id binding, not a way to rebind it; obtain it from an acknowledgement or a read with include_ids=true and field_groups=["references"].
Interpretation: The compact reply reports checked/changed/unavailable counts, per-item problems and Scene revisions; complete native snapshots stay internal. A successful single target can add a compact component acknowledgement with its Holon and group handles. Valid unrelated registrations can align despite individual problems; repeated unchanged alignment creates no revision.
Limits: Scope is at most 64 registrations including descendants and is response-size bounded; narrow larger scopes. Scene/document discovery may find native registrations missing from the DB, while explicit Holon scope does not broaden that way. Geometry, groups, membership/order, names, selection/view and object attributes are unchanged. Missing groups retain identity/history for Rhino Undo, never recreate geometry. Inspect item-specific recovery instructions; never replay an uncertain mutation as a substitute for reconciliation.

Args:
    holon_id: Optional registered Holon ID for single-target reconciliation.
    expected_model_path: Usually omitted: managed sessions supply the bound saved Rhino document. An explicit path must match that binding; it does not switch documents.
    rhino_group_id: Optional current Rhino group GUID consistency check accompanying holon_id; it does not select or rebind a group by itself.
    holon_ids: Optional explicit Holon ID batch; do not combine with single Holon/group selectors.
    scene_id: Optional Scene scope for batch reconciliation; does not create or infer new Holons.
<!-- /instruction:sync_ontological_holon -->

## remove_ontological_holon

<!-- instruction:remove_ontological_holon -->
When to use: Unregister a Holon's semantic meaning while preserving its Rhino geometry, ordinary group and object attributes.
Before calling: A Holon with its own parent must first be detached, and Plan/Step references to it must be cleared. Confirm the intended semantic removal rather than treating it as geometry deletion.
Inputs from earlier results: Pass the semantic holon_id from a registration acknowledgement or list_ontological_holons(include_ids=true), not a Rhino object/group GUID. Existing valid references can be reused; no fresh read is mandatory solely to obtain an already-known handle.
Interpretation: The compact acknowledgement identifies the removed holon_id and rhino_group_id with unregistered status. Children of a removed root become registered roots and retain direct object ownership, Rhino groups and Scene links. Rhino Undo/Redo restores or removes the document-private semantic binding.
Limits: No geometry is deleted or copied and existing object attributes are preserved. Native semantic changes and DB commits are separate: an uncertain result requires inspecting current registry/groups and alignment, not automatically retrying removal. Undo of meaning does not imply any group-table rename/create/delete rollback.

Args:
    holon_id: Registered Holon ID from a Holon query with include_ids=true or a prior registration result.
<!-- /instruction:remove_ontological_holon -->

## resolve_object_intersection

<!-- instruction:resolve_object_intersection -->
When to use: Review and resolve one overlap at a time through this same tool. The first call shows a comparison; a later numbered choice explicitly authorizes subtraction.
Before calling: Start with 1..512 current top-level Rhino object_ids, optionally include_block=true. A prior count query is optional. Use the bound saved document, a raster model viewport, visible/selectable targets and stable model-editing state. Requires intersection_review=1. Starting with object_ids resets this connection's review scope and skipped pairs.
Inputs from earlier results: After visually inspecting the returned comparison and numbered object metadata, call this tool with review_id and choice=1 or 2 to remove only the overlap from that numbered object; the other object stays unchanged. choice='skip' leaves both objects unchanged. Do not combine a choice with object_ids, supply pair_state, or treat a Holon ID as a Rhino GUID. review_id binds a decision to displayed operand identities, not an old geometry fingerprint. Current geometry is recalculated immediately before replacement.
Interpretation: The tool stops at the first positive pair and returns one side-by-side context/isolated image with object markers 1 and 2, names, layers, containing block names/paths, bounded attributes/UserDictionary, and review_id. Camera and selection move to the targets. Both images share the camera; the temporary native isolation is ended and visibility checked. Whole top-level block instances are displayed; internal member positions are numbered and definitions are unchanged. A choice preserves the target GUID, attributes and groups through the existing per-object Undo boundary, then scans current geometry from the beginning to show the next pending pair. previous_result retains a completed edit/skip even if the next review fails. A no-argument call continues the current scope; completed means no unskipped positive pair remains, not that skipped overlaps disappeared.
Limits: No choice is inferred from geometry or the image. If the design decision is unclear, discuss it with the user or skip. Block/source-file edits, mixed Mesh/Brep edits, textured or vertex-coloured Meshes, unpreservable geometry user data, whole-target deletion and multiple-Brep results remain unsupported. Unknown calculations are errors, not zero overlaps. An uncertain response blocks automatic continuation; inspect the document before explicitly restarting review. Repeated or superseded review_id values cannot replay a modification. Reconnect loses the review session. No model save, source-asset edit or semantic Holon registration is performed.

Args:
    object_ids: Optional 1..512 distinct current top-level object GUIDs to start a review scope. Omit to continue the current scope or submit a choice.
    include_block: Include transformed nested block members in a new review scope; default false. Block definition edits remain unsupported.
    review_id: Returned decision handle required with choice; identifies the displayed operands. Completed/superseded handles cannot replay a change.
    choice: 1 or 2 removes the overlap from that numbered object; "skip" leaves both unchanged. Supply review_id and omit object_ids. Omit choice to inspect/continue.
Returns:
    Comparison PNG, numbered object/block metadata and review_id, or completion/error evidence. previous_result preserves a completed edit even when the next review fails.
<!-- /instruction:resolve_object_intersection -->

## focus_holons

<!-- instruction:focus_holons -->
When to use: Select, isolate and zoom to the current members and registered descendants of Holons.
Before calling: Use 1–32 distinct present Holon handles in the current regular Rhino document with an active model view and no command or Undo/Redo in progress. Targets must be visible/selectable; the resolved set must contain 1–4096 top-level model-space objects. supplied expected_model_path must match the bound saved document.
Inputs from earlier results: Use semantic holon_id handles from registration acknowledgements or list_ontological_holons(include_ids=true), not Rhino object/group GUIDs. The tool resolves current recursive membership itself; no mandatory live read, sync, topology or CRC observation precedes focus.
Interpretation: This changes selection, visibility and camera using Rhino Isolate/Unisolate bookkeeping. The reply identifies selected object GUIDs and viewport, isolation/zoom status and restore_visibility_command=Unisolate. Locked context remains visible; hiding it is not promised.
Limits: This is a viewing operation, not geometry editing or design verification. Existing hidden/locked objects and document state affect native isolation. Unisolate restores visibility through Rhino's bookkeeping, not necessarily the previous selection/camera. Failure or timeout after dispatch can leave partial UI changes: inspect current state instead of automatically retrying.

Args:
    holon_ids: 1..32 registered Holon IDs resolved to their live effective members; at most 4096 resolved top-level objects are supported. Changes actual selection, isolation and camera.
    expected_model_path: Usually omitted: managed sessions supply the bound saved Rhino document. An explicit path must match that binding; it does not switch documents.
<!-- /instruction:focus_holons -->

## response-566

<!-- instruction:response-566 -->
Load a Bridge with design_components=1 before registering Holons.
<!-- /instruction:response-566 -->

## response-571

<!-- instruction:response-571 -->
Load a Bridge with component_operations=1 before using Holon helpers.
<!-- /instruction:response-571 -->
