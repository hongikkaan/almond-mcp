# Native Component hierarchy

Implementation: src/rhp/RhinoAlmondBridge/ComponentRegistry.cs. It uses the
existing native UI-thread dispatch, object attributes and owned Rhino Undo
record. The root agent owns live verification and packaged RHP delivery.

## Identity and structure

- A Component is an explicitly registered Rhino group identified by its
  persistent group GUID. Names, material layers and group indices are not IDs.
- Each editable top-level object has at most one direct owner, recorded in the
  almond:component_id attribute. Nested block occurrences remain top-level
  atomic objects; shared definition members and BlockEdit clones are excluded.
- child_component_ids gives direct children and parent_component_id is derived.
  One child has at most one parent; cycles, duplicate parent links and
  cross-document references are prohibited. Reparent by detaching the old
  parent first.
- A parent Rhino group physically contains direct members plus all descendant
  members. objects/object_ids describe direct ownership; effective_objects
  and effective_object_ids contain the set-deduplicated subtree. The ancestor
  group never replaces child ownership stamps.
- Each Component has at least one Scene and a nonempty subtree. A parent can
  own zero objects if it has a child. Parent Scene context includes descendant
  geometry without modifying any child's own Scene list.

Rhino 8.34 tests showed that Group.UserStrings cannot provide correct
Undo/Redo. Instead, each Component registration lives in the
almond:component_record attribute of an **existing member**. The JSON value
is a map keyed by persistent group GUID; each entry has exactly five fields:
component_id, rhino_group_id, name, scene_ids, child_component_ids.
One existing member can host direct-owner and several ancestor records.
Edits preserve unrelated map entries and never create an artificial anchor
object. The old singleton record remains readable and is migrated on edit.
The allowed record fields are listed in modeling_policy.json.

## Upsert, inspect and explicit sync

Native upsert receives the complete list of DIRECT object_ids and the optional
child_component_ids. Omitting children preserves them, while an explicit empty
list detaches all children if the resulting subtree is nonempty.
expected_object_ids refers to cached DIRECT owners, not the whole physical
group. expected_child_component_ids, expected_parent_component_id and
expected_effective_object_ids are supported stale-state guards.

Read-only inspect (get_design_component with live=True) returns a complete
group/owner snapshot. User-added TextDots or other unowned group members appear
in pending_objects and set requires_sync=true; TextDots carry bounded text and
world-millimetre positions. effective_object_ids also exposes these IDs for
the existing get_rhino_probe outline annotation path. Inspection does not
stamp or claim ownership.

Native sync is an explicitly requested reconciliation. It adopts only
previously unowned objects whose deepest registered group is unambiguous and
normalizes ancestor physical group memberships inside one owned Undo record.
Incomparable group memberships, detached stamped objects, foreign ownership
and copied records fail without automatically reassigning or silently
discarding data. A consistent sync performs no native mutation. Upsert/sync
respond with the primary component and affected_components full snapshots;
read-only inspect also returns related ancestor/descendant and supplied prior
relationship peer snapshots to support ledger reconciliation after Undo.

Snapshots distinguish direct and effective members, pending objects,
parent/children, and requires_sync. Native result validation and response
size bounding finish inside the owned Undo record. SQLite validates the
entire returned set before committing. Native Undo and a SQLite transaction
are separate mechanisms: failed DB commit, socket timeout or lost response
must never trigger automatic replay.

## Unregister and uncertain completion

Unregistering a Component still attached to a parent is rejected; detach it
explicitly first. A ROOT Component may unregister with children, including
a root that has no directly owned objects. Its group remains an ordinary
group; its own direct owner stamps and one group-keyed record are cleared,
while descendants, their group records, geometry and ownership are retained.
Children become roots.

The native top-level acknowledgement contains component_id, model_path,
rhino_group_id, detached_child_component_ids and full affected_components
child snapshots. If a database commit is lost after native success, read-only
inspect can prove removal using former expected_object_ids (DIRECT),
expected_child_component_ids and expected_effective_object_ids from the
ledger. It confirms the original group still exists with the same complete
effective membership, all former direct objects are unowned, the former
Component record is absent, and each former child remains registered as a
root with intact ownership. Missing or modified groups are not success proof.

Plan/Step/Sheet references must be removed before unregistering; the Python
store checks them before native mutation. A parent-only Component with exactly
one child cannot detach the child while remaining a nonempty Component.
When removing that container is intended, unregister the root parent instead.

Native tests: ModelingTests.cs preserves previous single-level behavior and
ComponentHierarchyTests.cs covers aggregation, annotation discovery, explicit
sync, multi-parent/cycle rejection, legacy records, Undo/Redo and root removal
reconciliation. Passing disposable native fixtures is not proof that a user's
running Rhino process loaded the updated binary.
