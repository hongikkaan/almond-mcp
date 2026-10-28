# tools.py explain

<!-- instruction:list_design_scenes -->
List Scene names across the whole project, without a Plan or live document lookup.
name is a case-insensitive substring; file_name is an exact optional filter.
Results are bounded by limit (1–200) and offset, with total and truncated.
The default is names only; field_groups adds scope (file_name, units), audit
(created_at, updated_at), state (revision), or all. include_ids independently enables Scene handles.
<!-- /instruction:list_design_scenes -->

## create_design_scene

<!-- instruction:create_design_scene -->
Creates a persistent scene handle for a house or interior generation.
Scene metadata remains local and is retrieved by ID instead of being
repeated in the model context.
<!-- /instruction:create_design_scene -->

## get_design_scene

<!-- instruction:get_design_scene -->
Returns a scene summary; scope adds file_name (empty when not recorded). IDs are
hidden unless include_ids=true; the supplied scene_id is not repeated.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds scope (file_name/units/model_path), state (revision), geometry (bounds/component), audit (timestamps), or all.
<!-- /instruction:get_design_scene -->

<!-- instruction:update_design_scene -->
Record a Scene's file_name, including an empty string to clear it. This changes
metadata only; it does not rename or move the Rhino document.
<!-- /instruction:update_design_scene -->

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
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds scope (file_name/units/model_path), state (revision), geometry (bounds/component), audit (timestamps), or all.
limit (1–200), offset and truncated bound the cached object page.
<!-- /instruction:get_scene_objects -->
