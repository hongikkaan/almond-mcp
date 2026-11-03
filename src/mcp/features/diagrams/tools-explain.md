# tools.py explain

## list_diagram_assets

<!-- instruction:list_diagram_assets -->
When to use: Browse indexed vector and CAD diagram assets such as people, trees and symbols.
Before calling: No prerequisite; category and offset/limit narrow or page this separate diagram collection.
Inputs from earlier results: None required. Set include_ids=true to obtain asset_id for get_diagram_asset or place_diagram_asset; use field_groups=["drawing"] for roles/LOD or ["paths"] for file details.
Interpretation: The default shortlist identifies catalogue entries and file_available, not whether the drawing looks correct at the intended location or scale.
Limits: This does not place geometry or search common model assets. Other optional groups are dimensions, metadata, source, audit and all; audit exposes timestamps independently of include_ids.
<!-- /instruction:list_diagram_assets -->

## search_diagram_assets

<!-- instruction:search_diagram_assets -->
When to use: Find diagram assets by text, category and maximum recorded dimensions.
Before calling: No prerequisite; dimension filters use millimetres, with zero unbounded. Use category or query only when relevant.
Inputs from earlier results: None required. Set include_ids=true to obtain asset_id for inspection or placement; request field_groups=["dimensions"] to see the dimensions behind a match and ["drawing"] for roles/LOD.
Interpretation: Matches describe indexed diagram metadata and file availability, not scene fit, successful import or visual quality.
Limits: This searches the separate diagram library rather than 3DM models. Other optional groups are metadata, source, paths, audit and all; timestamps require audit and IDs require include_ids.
<!-- /instruction:search_diagram_assets -->

## get_diagram_asset

<!-- instruction:get_diagram_asset -->
When to use: Read metadata for one known diagram asset before deciding how to use it.
Before calling: Supply asset_id; list or search the diagram library only if the ID is unknown.
Inputs from earlier results: Reuse asset_id from diagram discovery with include_ids=true. Request dimensions, drawing, source, paths or metadata through field_groups for details relevant to placement.
Interpretation: file_available reports the indexed source's availability, not an imported or visually checked Rhino object. Retain the supplied asset_id for place_diagram_asset because it is not echoed.
Limits: This neither places nor edits the asset. include_ids independently exposes other unsupplied handles; audit enables timestamps and all requests all available fields.
<!-- /instruction:get_diagram_asset -->

## place_diagram_asset

<!-- instruction:place_diagram_asset -->
When to use: Insert an indexed SVG, DWG or DXF diagram as a Rhino block instance.
Before calling: Supply a known available diagram asset_id in an editable active document; finish any current edit or Undo/Redo. Position and rotation must be finite, and scale finite and positive.
Inputs from earlier results: Reuse asset_id from list_diagram_assets or search_diagram_assets with include_ids=true; discovery is unnecessary when the ID is known. x/y/z use document coordinates, rotation_degrees is about world Z and scale is dimensionless.
Interpretation: Read the placement response and retain returned object_guid for later document operations; inspect the inserted geometry and relevant views rather than treating import success as visual approval.
Limits: Only controlled indexed files are accepted, not arbitrary paths. A timeout does not establish that nothing was inserted; inspect document state before retrying.
<!-- /instruction:place_diagram_asset -->
