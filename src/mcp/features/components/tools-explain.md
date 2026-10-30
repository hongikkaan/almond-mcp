# tools.py explain

## upsert_ontological_component

<!-- instruction:upsert_ontological_component -->
Register an ontological_component meaning unit in a current Rhino group.

object_ids names DIRECT top-level owners (possibly [] when child_component_ids
contains existing children). child_component_ids=None preserves existing children;
[] explicitly detaches them. Each object has exactly one direct Component owner,
and each child at most one parent in the same document without cycles. Current
group members are truth; existing group membership and order are never repaired
from DB records. Ordinary groups/blocks are not automatically meaning units.
Every Component needs at least one existing Scene; omitting scene_ids preserves
an existing association. The document-private registry writes no object management
attributes. A unique exact ordinary group is adopted; ambiguous matches need its
GUID. Geometry is not copied or duplicated. Replies are compact acknowledgements.
For an existing group, name must equal its current Rhino name; this tool refuses
renames because Rhino group-table changes are not Undo-tracked. Registration Undo
restores original object membership and removes meaning; an empty group-table
entry may remain. A new group name collision refuses before mutation rather
than creating an automatically suffixed group. Never repair membership or replay
an undone registration automatically; review the intended Rhino structure first.
expected_model_path must match the active saved document. After an uncertain
native result, inspect and sync_ontological_component; do not replay the mutation.
<!-- /instruction:upsert_ontological_component -->

## get_ontological_component

<!-- instruction:get_ontological_component -->
Read an ontological_component summary or inspect its actual Rhino group.

live=True observes current members/name without changing Rhino or the ledger.
recursive=false is the default; request true only for effective nested geometry.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds references, geometry, scope, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
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

Use one component_id, component_ids, one scene_id, or omit targets for the bound
document (up to 64 registrations including descendants). Geometry, groups,
membership/order, names and object attributes never change. Group/block editing
or unknown isolation refuses alignment. Missing groups retain bindings/history
for Rhino Undo without recreating geometry. Unrelated invalid bindings are
reported individually. The compact reply gives checked/changed/unavailable counts
and actionable problems; complete native snapshots remain internal. Repeated
unchanged alignment creates no revision. Never replay an uncertain mutation.
<!-- /instruction:sync_ontological_component -->

## remove_ontological_component

<!-- instruction:remove_ontological_component -->
Unregister ontological_component meaning while preserving Rhino geometry,
ordinary groups and all existing object attributes. Rhino Undo/Redo restores or
removes the document-private semantic binding.

A root Component may have children; they become roots and keep their object
ownership, registered Rhino groups and Scene links. A Component that still has
its own parent must first be detached. Plan/Step/Sheet references to the
removed Component must be cleared first. No geometry is deleted or copied.
<!-- /instruction:remove_ontological_component -->

## get_component_intersections

<!-- instruction:get_component_intersections -->
Inspect actual solid overlaps among the current recursive members of 1-32 Components.

The native helper resolves current group members inside the same callback,
tests bounded candidate pairs, and reports unsupported/truncated/unknown work.
A successful call is not proof of no collision unless complete is true.
This helper does not modify Rhino objects or the local Scene ledger.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds references, geometry, scope, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:get_component_intersections -->

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
