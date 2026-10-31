# tools.py explain

## list_drawing_recipes

<!-- instruction:list_drawing_recipes -->
Lists compact audited layer, lineweight, projection, and export recipes.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds scales, parameters, source, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:list_drawing_recipes -->

## get_drawing_recipe

<!-- instruction:get_drawing_recipe -->
Returns one audited drawing recipe summary by default. Request field_groups=["parameters"] for layer/style and review-preparation settings.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds scales, parameters, source, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:get_drawing_recipe -->

## apply_drawing_style

<!-- instruction:apply_drawing_style -->
Creates or updates the Rhino layer hierarchy, plot weights, colours, and linetypes defined by an audited drawing recipe.
The A4 plan/section recipe can return an unexecuted rhinocode CLI command template for print-review preparation on the same connected document; this tool does not inspect or change PrintDisplay.
Recipes may specify linetype_segments with positive lengths and explicit is_solid values. Conflicting named patterns or malformed explicit segments are rejected before layer changes; matching named patterns are reused.
Recipes without segments retain their existing name-based behaviour.
<!-- /instruction:apply_drawing_style -->

## import_drawing_hatch_patterns

<!-- instruction:import_drawing_hatch_patterns -->
Imports the AutoCAD-style .pat hatch definitions of an indexed drawing asset into the active Rhino document's hatch pattern table.

The tool accepts only .pat files resolved from the controlled asset/drawing/DrawingAssetfiles manifest, mirroring the placement tools' security boundary.
<!-- /instruction:import_drawing_hatch_patterns -->

## response-642

<!-- instruction:response-642 -->
Rhino bridge is unavailable. Start RhinoAlmondBridge first.
<!-- /instruction:response-642 -->

## response-645

<!-- instruction:response-645 -->
Rhino bridge is unavailable. Start RhinoAlmondBridge first.
<!-- /instruction:response-645 -->
