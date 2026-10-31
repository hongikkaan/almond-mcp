# tools.py explain

<!-- instruction:list_design_scenes -->
List Scene names across the whole project, without a Plan or live document lookup.
name is a case-insensitive substring; file_name is an exact optional filter.
Results are bounded by limit (1–200) and offset, with total and truncated.
The default is names only; field_groups adds scope (file_name, units), audit (created_at, updated_at), state (revision), or all. include_ids independently enables Scene handles.
<!-- /instruction:list_design_scenes -->

## create_design_scene

<!-- instruction:create_design_scene -->
Creates a persistent scene handle for a house or interior generation.
file_name resolves a project_files reference; project_file_id selects an existing entry.
Scene metadata remains local and is retrieved by ID instead of being repeated in the model context.
<!-- /instruction:create_design_scene -->

## get_design_scene

<!-- instruction:get_design_scene -->
Returns a scene summary; scope adds file_name (empty when not recorded). IDs are hidden unless include_ids=true; the supplied scene_id is not repeated.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds scope (file_name/units/model_path), state (revision), geometry (bounds/component), audit (timestamps), or all.
<!-- /instruction:get_design_scene -->

<!-- instruction:update_design_scene -->
Set the Scene’s project_files reference by file_name or project_file_id; file_name='' clears it.
A filename must have no folders. Duplicate names require project_file_id from list_project_files. This changes metadata only; it does not rename or move the Rhino document.
<!-- /instruction:update_design_scene -->

## get_scene_objects

<!-- instruction:get_scene_objects -->
Read current Rhino members of the Scene’s registered semantic groups as one set.
Requires a live saved document, stable editing state and at most 64 registered groups.
expected_model_path optionally verifies the bound model. Individual objects are never registered in the DB.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds scope (file_name/units/model_path), state (revision), geometry (bounds/component), audit (timestamps), or all.
limit (1–200), offset and truncated bound the live object page.
<!-- /instruction:get_scene_objects -->
