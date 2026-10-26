# tools.py explain

## upsert_design_component

<!-- instruction:upsert_design_component -->
Register direct objects and optional nested child Components in an explicit Rhino group.

object_ids names DIRECT top-level owners (possibly [] when child_component_ids
contains existing children). child_component_ids=None preserves existing children;
[] explicitly detaches them. Each object has exactly one direct Component owner,
and each child at most one parent in the same document without cycles. Parent
group selection includes descendants without rewriting their direct owner IDs.
Every Component needs at least one existing Scene; omitting scene_ids preserves
an existing association. Geometry is not copied or duplicated.
expected_model_path must match the active saved document. After an uncertain
native result, inspect and sync_design_component; do not replay the mutation.
<!-- /instruction:upsert_design_component -->

## get_design_component

<!-- instruction:get_design_component -->
Read cached direct/nested Component members or inspect live Rhino group membership.

live=True reads the actual group, including unowned group-added TextDots as
pending_objects requiring explicit sync; it never changes Rhino or the ledger.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
<!-- /instruction:get_design_component -->

## list_design_components

<!-- instruction:list_design_components -->
List compact cached Components, optionally restricted to one saved model path.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
<!-- /instruction:list_design_components -->

## sync_design_component

<!-- instruction:sync_design_component -->
Reconcile a Component after inspecting live Rhino group membership.

When group editing adds unowned TextDots/objects, one explicit native sync may
adopt their direct ownership under Undo and normalize ancestor memberships.
Unchanged components stay read-only. Conflicting ownership requires explicit
repair. A timed-out mutation is never automatically replayed.
A complete live proof of a previously registered but now unregistered group
also releases its cached registration, after checking Plan/Step/Sheet references.
<!-- /instruction:sync_design_component -->

## remove_design_component

<!-- instruction:remove_design_component -->
Unregister Component ownership while preserving Rhino geometry and the ordinary group.

A root Component may have children; they become roots and keep their object
ownership, registered Rhino groups and Scene links. A Component that still has
its own parent must first be detached. Plan/Step/Sheet references to the
removed Component must be cleared first. No geometry is deleted or copied.
<!-- /instruction:remove_design_component -->

## get_component_intersections

<!-- instruction:get_component_intersections -->
Inspect actual solid overlaps among the current recursive members of 1-32 Components.

The native helper resolves current group members inside the same callback,
tests bounded candidate pairs, and reports unsupported/truncated/unknown work.
A successful call is not proof of no collision unless complete is true.
This helper does not modify Rhino objects or the local Scene ledger.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
<!-- /instruction:get_component_intersections -->

## focus_components

<!-- instruction:focus_components -->
Select, isolate and zoom to current recursive members of 1-32 Components.

Uses Rhino's existing Isolate/Unisolate history; other hidden/locked context
and any existing document state are subject to the native helper's guards.
The operation changes the live selection/visibility/view. An uncertain native
result must be inspected; it is never automatically retried.
<!-- /instruction:focus_components -->

## response-566

<!-- instruction:response-566 -->
Load a Bridge with design_components=1 before registering Components.
<!-- /instruction:response-566 -->

## response-571

<!-- instruction:response-571 -->
Load a Bridge with component_operations=1 before using Component helpers.
<!-- /instruction:response-571 -->
