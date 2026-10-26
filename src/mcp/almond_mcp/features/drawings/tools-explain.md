# tools.py explain

## list_drawing_recipes

<!-- instruction:list_drawing_recipes -->
Lists compact audited layer, lineweight, projection, and export recipes.
<!-- /instruction:list_drawing_recipes -->

## get_drawing_recipe

<!-- instruction:get_drawing_recipe -->
Returns one complete audited drawing recipe.
<!-- /instruction:get_drawing_recipe -->

## apply_drawing_style

<!-- instruction:apply_drawing_style -->
Creates or updates the Rhino layer hierarchy, plot weights, colours, and
linetypes defined by an audited drawing recipe.
<!-- /instruction:apply_drawing_style -->

## import_drawing_hatch_patterns

<!-- instruction:import_drawing_hatch_patterns -->
Imports the AutoCAD-style .pat hatch definitions of an indexed drawing
asset into the active Rhino document's hatch pattern table.

The tool accepts only .pat files resolved from the controlled
asset/drawing/DrawingAssetfiles manifest, mirroring the placement tools' security
boundary.
<!-- /instruction:import_drawing_hatch_patterns -->

## upsert_drawing_sheet

<!-- instruction:upsert_drawing_sheet -->
Register one authored modelspace drawing region with one Rhino Layout tab.

Supply world-XY bounds [minX,minY,minZ,maxX,maxY,maxZ] in mm, positive XY
extents, paper [width,height] in mm, and a positive scale denominator (100 = 1:100).
The native Layout uses a parallel Top detail; the region must fit at that scale.
drawing_type is plan, section, elevation, detail, axonometric, perspective,
schedule or other. These are labels; this tool does not generate drawing geometry.
New sheets create a Layout when layout_id is empty. Existing identities cannot
change model or Layout. Omitted refs preserve existing values; [] clears refs,
plan_id='' unlinks a Plan. List sheets by Plan at wrapup to inspect duplicates.
After an uncertain result, sync_drawing_sheet; do not replay the mutation.
<!-- /instruction:upsert_drawing_sheet -->

## get_drawing_sheet

<!-- instruction:get_drawing_sheet -->
Read a cached sheet title, scale, paper, modelspace bounds, Layout and context refs.
<!-- /instruction:get_drawing_sheet -->

## list_drawing_sheets

<!-- instruction:list_drawing_sheets -->
List named sheets for Plan wrapup or Scene/Component/model review; combine filters with AND.

Returns cached registration data, total and truncation. Review names and locations
before deciding whether drawings are unnecessary; listing never deletes geometry.
<!-- /instruction:list_drawing_sheets -->

## sync_drawing_sheet

<!-- instruction:sync_drawing_sheet -->
Reconcile a sheet from read-only native Layout inspection without replaying a mutation.

Use after a lost response, failed database commit or manual edits. Registered
snapshots can restore a missing ledger row. Verified unregistered retained
Layouts can release an existing ledger row; a missing Layout is not that proof.
<!-- /instruction:sync_drawing_sheet -->

## remove_drawing_sheet

<!-- instruction:remove_drawing_sheet -->
Unregister a sheet while preserving its Rhino Layout, detail and modelspace drawing geometry.
<!-- /instruction:remove_drawing_sheet -->

## response-638

<!-- instruction:response-638 -->
Load a Bridge with drawing_sheets=1 before managing drawing sheets.
<!-- /instruction:response-638 -->

## response-642

<!-- instruction:response-642 -->
Rhino bridge is unavailable. Start RhinoAlmondBridge first.
<!-- /instruction:response-642 -->

## response-645

<!-- instruction:response-645 -->
Rhino bridge is unavailable. Start RhinoAlmondBridge first.
<!-- /instruction:response-645 -->
