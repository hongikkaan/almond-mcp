# tools.py explain

## upsert_design_room

<!-- instruction:upsert_design_room -->
Creates or updates a legacy room envelope for asset-placement containment checks.
Use upsert_design_component for physical architectural assemblies.
bounds_mm is [min_x, min_y, min_z, max_x, max_y, max_z]. When room_id is
omitted, an existing room with the same name in the scene is updated
instead of creating a duplicate.
<!-- /instruction:upsert_design_room -->

## register_scene_instance

<!-- instruction:register_scene_instance -->
Registers or moves an asset instance in millimetres without retransmitting
its full metadata. Returns a stable instance handle and scene revision.
When z_mm is omitted the instance stands on its room's floor (the room's
min_z), so rooms at storey elevation validate correctly.
<!-- /instruction:register_scene_instance -->

## remove_scene_instance

<!-- instruction:remove_scene_instance -->
Removes an instance from the scene ledger (recorded as a revision delta).
The Rhino geometry, if any, is not touched.
<!-- /instruction:remove_scene_instance -->

## remove_design_room

<!-- instruction:remove_design_room -->
Removes a room from the scene ledger. Instances that referenced it stay
in the scene, orphaned (re-home them with register_scene_instance).
<!-- /instruction:remove_design_room -->

## validate_scene_layout

<!-- instruction:validate_scene_layout -->
Runs cached legacy asset-instance AABB collisions and room-containment checks.
Component/raw-object geometry is reported as unvalidated; inspect it with native probes.
<!-- /instruction:validate_scene_layout -->
