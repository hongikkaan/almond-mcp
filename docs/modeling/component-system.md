# Scene, Component, planning and material layers

Scene은 공간 맥락, Component는 명시적으로 등록한 Rhino group이며 Phase·Plan·Step은 수동 계획 기록이다. Room과 asset instance는 기존 충돌·containment·하중 경로에 남는다.

## Native Component hierarchy

### Identity and structure

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

### Upsert, inspect and explicit sync

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

### Unregister and uncertain completion

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

## Room and structural target limits

**Current Room contract.** `retrieval_store.upsert_room` accepts only six finite
`bounds_mm` values; the `rooms` table has no curve/Brep identity. An assigned
`instance` uses `room.min_z` as its default floor elevation. The
`validate_scene_layout` query runs R-tree instance-AABB collision preflight and
compares each assigned instance AABB with the Room AABB, reporting
`passed_scope=legacy_asset_instances`,
`registered_object_collisions_checked=false` and `live_verified=false`.
An enclosing box or a curved Room reference stored only in metadata does not
support exact curved-boundary containment.

**Current structural analysis contract.** `validate_structure(guids, ...)`
and `visualize_structure(guids, ...)` take explicit Rhino GUIDs, not Component
IDs. `StructureModelExport.Handle` runs `ModelConditioner.Condition`: Points
become support anchors, Curves become member axes, slender Extrusions and
prismatic Breps can heuristically become members, and Mesh/surface/plate-like
geometry becomes shells; other solids can be skipped with warnings. The
native frame solver requires line members and rejects shells. The Karamba
fallback is not automatically equivalent EN 1990 / Eurocode verification.
Passing all architectural Component geometry directly as structural members
would overstate both coverage and analysis validity.

Generated-asset gravity loads are **loads**, not automatically members.
Preserve `AssetPlacementExport.Handle` (including old/new asset-ID tags),
`retrieval_store.scene_instances`, `asset_loads.placements_from_scene`,
`LoadTable.lookup`, `asset_loads.apply`, `structure_study.asset_catalogue`,
`server._structural_loads_path`, `_asset_load_spec`,
`get_generated_asset_passport`, `structural-loads.json`, and generated manifest
`category`, `spatial.support_plane`, `nominal_dimensions_mm`, and stable asset
IDs. This existing path assigns estimated G/Q product/occupancy loads to
frame members while reporting skipped ground-only, wall-mounted and
structural elements. `test_asset_load_tools.py` and `test_asset_loads.py`
cover these consumers. Asset conversion must not drop those identities/loads.

## Phase, Plan and Step

Phase is an organizational parent. A Plan can reference Scenes and Components;
a Step can explicitly reference Components. This does not impose a permanent
rule that Scene belongs only at Phase or Component only at Plan. Explicit
component references need not be restricted to the Plan's contextual Scenes.

```mermaid
erDiagram
    PHASE o|--o{ PLAN : organizes
    PLAN ||--|{ STEP : orders
    PLAN }o--o{ SCENE : contextualizes
    PLAN }o--o{ COMPONENT : targets
    STEP }o--o{ COMPONENT : targets
    PLAN ||--|{ PLAN_REVISION : archives_state
```

The legacy `scene_id` remains compatible with the first entry of `scene_ids`.
The existing scope templates remain; a minimal Component scope supports
inspection, design, modeling and validation without requiring a furniture loop.
There is no new automatic scheduler or arbitrary DAG editor.

Omitted reference arguments preserve prior values; an explicit empty list clears
them. A Step's explicit empty component selection must not silently expand to
the Plan or every object in a Scene. Target resolution is registration context,
not authorization to edit all returned geometry.

Each committed Plan mutation creates an immutable full Plan-state snapshot.
Revision numbers identify these saved states, not design attempts. Existing
Plans receive a clearly labeled migration baseline; earlier history is not
invented. `expected_revision` permits stale-client rejection. These snapshots
archive plan metadata, dependencies, statuses and handles, not Rhino geometry.

```mermaid
stateDiagram-v2
    [*] --> pending
    pending --> running: prerequisites completed
    running --> completed: evidence recorded
    running --> failed: execution failed
    pending --> blocked: blocked explicitly
    blocked --> running: prerequisites completed
    failed --> running: explicit retry after inspection
```

A completed prerequisite cannot regress while a dependent remains running or
completed. The caller must explicitly invalidate dependent work first. Updates,
dependency checks, revision checks and archival snapshots share one transaction.

## Drawing Sheets

A Sheet is one named record bound to one real Rhino Layout and a registered
detail viewport. Its drawing remains authored geometry in a world-XY region of
model space. `model_bounds_mm` records six bounds, `paper_mm` records physical
paper width/height and `scale_denominator` records the paper ratio (100 means
1:100). The native path uses a parallel Top detail with a 10 mm inset and checks
that the region fits at the requested scale, including when model and page units
differ. A section/elevation/axonometric `drawing_type` is a label for the authored
region; registration itself does not project 3D geometry.

Scene, Component and Plan references support `list_drawing_sheets` at Plan
wrapup. Listing is read-only; `remove_drawing_sheet` releases registration while
preserving the Layout, detail and model geometry. Uncertain native completion
requires `sync_drawing_sheet` to inspect the existing Layout, not a second create.
Layout view changes do not reliably participate in Rhino Undo; responses expose
`layout_undo_supported=false`, and failed updates attempt explicit compensation.

## Prepared drawing assets

The canonical new asset is a reviewed, prepared 3DM. Cleanup, orientation and
visual review stay with the external Almond Asset Converter. Registration verifies
millimeters, Z-up coordinates and a bottom-center origin; it does not rotate the
source, claim that a front direction is visually correct, or alter the user's file.
The native extractor reads a copied File3dm, resolves nested block transforms,
meshes supported geometry, and acknowledges source/artifact hashes and measured
bounds. Unsupported geometry or an incomplete extraction prevents publication.

`register_drawing_asset` stages the copied model, plan/front/right DXF and SVG,
and `dimensions.json` under one stable asset ID. It uses the existing GLB drafting
projection code with verified native triangles, preserving the custom GLB path.
An OS lock serializes library writes; all files are checked before an atomic
manifest replacement. Explicit replacement retains old version folders and a
manifest backup. Failures before publication leave the old entry intact. An index
refresh failure after publication is reported as `registration_applied=true`;
reconnect instead of repeating registration.

`get_asset_drawing`, drawing resources, audit and `place_drawing_asset` resolve the
same entry. Placement verifies the 3DM hash, accounts for document units, and
caches block definitions by source revision and units. It preserves old placed
instances when a new source revision is registered. A missing acknowledgement is
not permission to repeat placement.

The public generated/Meshy list/search/recommend/fit/place tools are retired.
Existing generated manifests, resource readers, load consumers and GLB package
derivation remain compatible. Diagram assets, construction and Eurocode analysis
remain available. The native docked Asset Panel reads its installed archive
snapshot; newly registered local assets are immediately visible to the registering
MCP process and its repository UI, not automatically to that bundled panel.
Other running MCP processes must reconnect to reload their cached library.

## Material-driven layers and small metadata

The material manifest currently contains a flat material list with categories,
not an undocumented deeper hierarchy. Each entry gains an explicit `layer_path`.
Existing user manifests without that field derive the same category/material-ID
path without rewriting AppData. Library identity remains `material_id`; a
display-name change must not silently produce a different library material.

The chosen implementation supports direct RhinoCommon batch scripts without
requiring geometry-specific wrappers. `ModelingMaterials.CreateAttributes`
prepares attributes for standard `doc.Objects.Add*` methods, and `assign_material`
uses the same native material/layer helper. Only the required `M::...` ancestors and leaf are
created, on demand. Reading a catalog or starting the plugin creates no material
layers. Existing layers are reused. Generic `A-WALL`, `A-STRC` and `A-GLAZ`
initialization is removed from the script executor; Undo recovery remains.

```mermaid
flowchart TD
    A[MCP script starts] --> B[Observe additions and direct material changes]
    B --> C{Script succeeds and still owns Undo?}
    C -->|No| D[Skip routing and report failure]
    C -->|Yes| E[Unsubscribe and inspect final live objects]
    E --> F{Direct object material?}
    F -->|No| G[Keep current layer]
    F -->|Yes| H[Resolve and lazily apply material layer]
    H --> I[Finish same Undo record]
```

`ByLayer` and `ByParent` are not guessed or converted: changing their layer can
change their effective material and cause a feedback loop. Unmaterialed objects
remain until a direct material is assigned. Custom document materials use a
readable name and stable identity under a policy-defined custom root. Notifications
only collect IDs during an MCP script; they never mutate geometry in an event
callback. Routing starts after unsubscribing, while the same Undo record is still
owned. Failed scripts, startup, file loading and unrelated manual UI changes do
not trigger routing. External Python/C# scripts use the attribute factory explicitly.
Shared block definitions must not be rewritten by an occurrence-level routing
operation. Automatic routing and explicit material assignment use the same
path resolver and lazy layer helper.

`modeling_policy.json` defines supported keys. Public modeling metadata is
Component ID, floor and construction-detail label; names remain optional/free.
The Component's group-GUID-keyed internal record map on existing objects carries
name, Scene references and direct children. Necessary stable material
IDs, asset provenance and licensing fields are retained where real consumers
need them. New assignments stop duplicating material name/category, UE slot and
PBR channels onto object user strings: native materials hold the visual values.
Existing unrelated user strings are preserved. Legacy key names remain documented
for reading existing files, not as a list of required new stamps.

The existing construction catalog contains preliminary construction systems,
not verified detail drawings. A human-readable construction label and a typed
stable source reference are stored separately. A system ID is not relabeled
as a certified detail ID. Floor values are supplied, not inferred from names or
layer strings. Metadata updates do not erase unrelated user keys.

## Skill tool integration

All five existing helper capabilities already have fixed MCP routing:
`outline`, `resolve-block`, `sections`, `vertical-probe` and `joint-pairs` through
`get_rhino_probe`. Their implementation moves into Bridge's `Probes` source
directory, with tests and documentation updated; no duplicate tool wrappers or
arbitrary script execution endpoint is added. Usage guidance remains in the
skill and points to public MCP inputs and outputs.
