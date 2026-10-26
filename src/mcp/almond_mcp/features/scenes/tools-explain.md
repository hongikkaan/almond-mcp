# tools.py explain

## create_design_scene

<!-- instruction:create_design_scene -->
Creates a persistent scene handle for a house or interior generation.
Scene metadata remains local and is retrieved by ID instead of being
repeated in the model context.
<!-- /instruction:create_design_scene -->

## get_design_scene

<!-- instruction:get_design_scene -->
Returns a token-efficient scene summary by stable handle.
<!-- /instruction:get_design_scene -->

## register_scene_objects

<!-- instruction:register_scene_objects -->
Link top-level objects directly to a Scene without an asset instance or Component.

mode is add, remove or replace for this document's direct links. Other model
links and Component membership are retained. Observe current GUIDs/bounds live;
this updates the local ledger and does not edit Rhino geometry or object names.
<!-- /instruction:register_scene_objects -->

## get_scene_objects

<!-- instruction:get_scene_objects -->
Read cached direct Scene objects and all descendant Component members as one set.
<!-- /instruction:get_scene_objects -->
