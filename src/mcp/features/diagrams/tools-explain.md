# tools.py explain

## list_diagram_assets

<!-- instruction:list_diagram_assets -->
Lists available vector and CAD diagram assets (people, trees, symbols).
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds dimensions, drawing, metadata, source, paths, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:list_diagram_assets -->

## search_diagram_assets

<!-- instruction:search_diagram_assets -->
Searches the diagram asset library.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds dimensions, drawing, metadata, source, paths, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:search_diagram_assets -->

## get_diagram_asset

<!-- instruction:get_diagram_asset -->
Returns one diagram asset's metadata.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds dimensions, drawing, metadata, source, paths, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:get_diagram_asset -->

## place_diagram_asset

<!-- instruction:place_diagram_asset -->
Places an indexed diagram asset (SVG, DWG, DXF).
<!-- /instruction:place_diagram_asset -->
