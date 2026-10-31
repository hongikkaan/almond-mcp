# tools.py explain

## upsert_ontological_component

<!-- instruction:upsert_ontological_component -->
Register an ontological_component meaning unit in a current Rhino group.

object_ids names DIRECT top-level owners (possibly [] when child_component_ids contains existing children). child_component_ids=None preserves existing children; [] explicitly detaches them. Each object has exactly one direct Component owner, and each child at most one parent in the same document without cycles. Current group members are truth; existing group membership and order are never repaired from DB records. Ordinary groups/blocks are not automatically meaning units.
Every Component needs at least one existing Scene; omitting scene_ids preserves an existing association. The document-private registry writes no object management attributes. A unique exact ordinary group is adopted; ambiguous matches need its GUID. Geometry is not copied or duplicated. Replies are compact acknowledgements.
For an existing group, name must equal its current Rhino name; this tool refuses renames because Rhino group-table changes are not Undo-tracked. Registration Undo restores original object membership and removes meaning; an empty group-table entry may remain. A new group name collision refuses before mutation rather than creating an automatically suffixed group. Never repair membership or replay an undone registration automatically; review the intended Rhino structure first.
expected_model_path must match the active saved document. After an uncertain native result, inspect and sync_ontological_component; do not replay the mutation.
<!-- /instruction:upsert_ontological_component -->

## get_ontological_component

<!-- instruction:get_ontological_component -->
Read an ontological_component summary or inspect its actual Rhino group.

live=True observes current members/name without changing Rhino or the ledger.
Cached reads contain group summaries only (geometry_available=false), never member IDs or per-object geometry.
recursive=false is the default; request true only for effective nested geometry.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds references, geometry, scope, audit, or all; default is summary.
audit enables timestamps.
<!-- /instruction:get_ontological_component -->

## list_ontological_components

<!-- instruction:list_ontological_components -->
List compact cached ontological_components, optionally scoped by scene_id.
recursive=false lists roots in that scope; true also includes registered children.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds references, geometry, scope, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:list_ontological_components -->

## sync_ontological_component

<!-- instruction:sync_ontological_component -->
Align DB records with actual groups in the current stable Rhino document once.

Use one component_id, component_ids, one scene_id, or omit targets for the bound document (up to 64 registrations including descendants). Geometry, groups, membership/order, names and object attributes never change. Group/block editing or unknown isolation refuses alignment. Missing groups retain bindings/history for Rhino Undo without recreating geometry. Unrelated invalid bindings are reported individually. The compact reply gives checked/changed/unavailable counts and actionable problems; complete native snapshots remain internal. Repeated unchanged alignment creates no revision. Never replay an uncertain mutation.
<!-- /instruction:sync_ontological_component -->

## remove_ontological_component

<!-- instruction:remove_ontological_component -->
Unregister ontological_component meaning while preserving Rhino geometry, ordinary groups and all existing object attributes. Rhino Undo/Redo restores or removes the document-private semantic binding.

A root Component may have children; they become roots and keep their object ownership, registered Rhino groups and Scene links. A Component that still has its own parent must first be detached. Plan/Step references to the removed Component must be cleared first. No geometry is deleted or copied.
<!-- /instruction:remove_ontological_component -->

## get_component_intersections

<!-- instruction:get_component_intersections -->
Inspect actual solid overlaps among the current recursive members of 1-32 Components.

Resolves current group members and tests at most max_pairs (1-64) candidate pairs.
Closed Breps, Extrusions and oriented manifold Meshes are supported; include_blocks adds transformed nested occurrences without changing definitions. Disjoint meshes are evaluated as detached geometry; no document split/join is needed. Mixed Brep/Mesh observations report their temporary mesh approximation.
Pass next_cursor with the same scope to continue; geometry/scope changes reject the cursor. Accumulate page results: pagination_complete ends enumeration, while complete describes whether this response alone establishes the whole scope.
Unsupported or unknown work prevents a no-overlap conclusion.
Pair a.handle, b.handle and pair_state connect the result to preview or subtraction.
Pair handles and state are always returned. include_ids=true adds other IDs; supplied target IDs are not repeated.
field_groups adds references, geometry, scope, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:get_component_intersections -->

## show_object_intersection

<!-- instruction:show_object_intersection -->
Preview one inspected overlap in the active model viewport without adding document geometry.

Pass a.handle, b.handle and pair_state from an intersection pair as a, b and pair_state. Names, layers and region measurements accompany the display. Changed geometry rejects stale references and clears an existing preview. Block occurrences can be shown. clear=true removes the preview without requiring handles or state.
An unknown overlap or a positive volume with no returned solid has no fabricated preview.
<!-- /instruction:show_object_intersection -->

## resolve_object_intersection

<!-- instruction:resolve_object_intersection -->
Subtract the selected keep solid from the trim solid, preserving the trim object's ID and attributes.

Pass the returned occurrence handles and pair_state; keep remains unchanged.
Supports document-level Brep/Extrusion pairs and closed Mesh pairs. Disjoint mesh results remain one Mesh object. Block/linked-source members, mixed Mesh/Brep edits, textured meshes, unpreservable geometry user data and results deleting the whole target or creating multiple Breps are reported without editing. A timeout is not rollback: inspect an unconfirmed result before deciding whether to try again.
<!-- /instruction:resolve_object_intersection -->

## focus_components

<!-- instruction:focus_components -->
Select, isolate and zoom to Components. See BASIC-INSTRUCTIONS.md for usage and behavior.
<!-- /instruction:focus_components -->

## response-566

<!-- instruction:response-566 -->
Load a Bridge with design_components=1 before registering Components.
<!-- /instruction:response-566 -->

## response-571

<!-- instruction:response-571 -->
Load a Bridge with component_operations=1 before using Component helpers.
<!-- /instruction:response-571 -->
