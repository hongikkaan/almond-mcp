# tools.py explain

## list_drawing_assets

<!-- instruction:list_drawing_assets -->
Lists representation-only entourage and graphic proxy assets.

Drawing assets are representation elements and do not participate in room collision checks unless explicitly registered.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds dimensions, source, paths, drawing, metadata, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:list_drawing_assets -->

## search_drawing_assets

<!-- instruction:search_drawing_assets -->
Searches only the controlled architectural drawing-asset library.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds dimensions, source, paths, drawing, metadata, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:search_drawing_assets -->

## get_drawing_asset

<!-- instruction:get_drawing_asset -->
Returns one drawing asset's provenance, scale guidance, and availability.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds dimensions, source, paths, drawing, metadata, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:get_drawing_asset -->

## register_drawing_asset

<!-- instruction:register_drawing_asset -->
Register a reviewed 3DM and automatically derive linked plan/front/right drawings.

Finish cleanup/orientation review with the asset-converter workflow first.
Supply an absolute prepared 3DM path: millimeters, Z up, bottom-center at origin.
Native geometry checks support meshes, Breps, extrusions, surfaces, SubD and nested blocks, up to 100 MB/250k triangles. Unsupported objects reject the whole asset.
Copies the source, measures dimensions and writes DXF at full-size mm, SVG at 1:50/1:100 and A3 sheets where they fit. These are mesh silhouettes, not hidden lines or construction details; visual classification/front are not verified.
Existing IDs require replace_existing=true. Prior files and manifest backups are retained. Refreshes this MCP process's index after atomic publication; other running processes must reconnect. The bundled Rhino panel is a release snapshot; use MCP placement for newly registered local assets.
<!-- /instruction:register_drawing_asset -->

## get_asset_drawing

<!-- instruction:get_asset_drawing -->
Retrieve a registered 3DM's linked drawings and dimensions, or a legacy pilot package.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds dimensions, source, paths, drawing, metadata, audit, or all; the requested manifest/parsed logic/script remains in the default payload.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:get_asset_drawing -->

## generate_asset_drawing_views

<!-- instruction:generate_asset_drawing_views -->
Generate plan/front/right mesh silhouettes with source metadata, full-size DXF, scaled SVG and A3 SVG sheets where they fit. Writes a NEW local drawing-runs folder.
Choose a library asset_id OR an absolute custom source_glb path. Custom files REQUIRE input_units mm or m; up_axis y or z. Scales default to [50,100].
Supports static, uncompressed triangle GLBs only (max 100 MB/250k triangles).
No hidden lines, inferred construction or product-front recognition.
Optional item-level source_references require source_id/title/url/publisher/locator/accessed_on/relationship/used_for/terms_url. They describe references attached to this drawing, never retroactive generation inputs.
<!-- /instruction:generate_asset_drawing_views -->

## audit_asset_drawing

<!-- instruction:audit_asset_drawing -->
Check exported files and whether source geometry changed. Custom packages need the current source_glb to check staleness; library assets resolve automatically.
<!-- /instruction:audit_asset_drawing -->

## asset_catalogue_resource

<!-- instruction:asset_catalogue_resource -->
Compact catalogue; retrieve individual passports/previews on demand.
<!-- /instruction:asset_catalogue_resource -->

## asset_preview_resource

<!-- instruction:asset_preview_resource -->
Existing Blender preview for a known catalogue id.
<!-- /instruction:asset_preview_resource -->

## place_drawing_asset

<!-- instruction:place_drawing_asset -->
Places an indexed representation asset as a reusable Rhino block.

x/y/z and returned bounds use the active document's units; scale is dimensionless.
Prepared 3DM geometry is converted from its stored millimeters by Rhino on import.
Drawing assets are placed on ALMOND-DRAW::ASSETS and remain distinct from generated model blocks. The tool accepts only files resolved from the controlled asset/drawing/DrawingAssetfiles manifest.
<!-- /instruction:place_drawing_asset -->

## search_asset_repository

<!-- instruction:search_asset_repository -->
Search the unified model/drawing archive. kind: all, model or element.

Returns stable IDs, file availability, dimensions and MCP resource URIs.
Drawing-ready means a derived projection package is linked to the object.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds dimensions, source, paths, drawing, metadata, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:search_asset_repository -->

## repository_asset_resource

<!-- instruction:repository_asset_resource -->
Unified object metadata, source evidence, representations and local files.
<!-- /instruction:repository_asset_resource -->

## response-399

<!-- instruction:response-399 -->
Placed geometry deviates from catalogue dimensions beyond tolerance; inspect the source model (see manifest match note).
<!-- /instruction:response-399 -->

## response-400

<!-- instruction:response-400 -->
Load a Bridge with drawing_asset_extract=1 before registering a 3DM asset
<!-- /instruction:response-400 -->

## response-403

<!-- instruction:response-403 -->
Library has no passport; upgrade the asset pack.
<!-- /instruction:response-403 -->

## response-404

<!-- instruction:response-404 -->
Source register missing; update the asset pack
<!-- /instruction:response-404 -->

## response-406

<!-- instruction:response-406 -->
No bundled drawing for this asset; generate views on demand
<!-- /instruction:response-406 -->

## response-409

<!-- instruction:response-409 -->
Choose an asset_id that does not belong to another library
<!-- /instruction:response-409 -->

## response-410

<!-- instruction:response-410 -->
Asset files and manifest were published. Reconnect to refresh the index; do not repeat registration: {0}
<!-- /instruction:response-410 -->

## response-411

<!-- instruction:response-411 -->
Choose exactly one asset_id or source_glb
<!-- /instruction:response-411 -->

## response-417

<!-- instruction:response-417 -->
Model file missing for {0}; run almond-mcp fetch-assets to download it.
<!-- /instruction:response-417 -->

## response-419

<!-- instruction:response-419 -->
register_scene_instance(scene_id, asset_id=..., x, y, rotation) so validate_scene_layout can see this placement.
<!-- /instruction:response-419 -->

## response-423

<!-- instruction:response-423 -->
Rhino drawing-asset import timed out; inspect the model before retrying.
<!-- /instruction:response-423 -->

## response-424

<!-- instruction:response-424 -->
Rhino bridge is unavailable. Start RhinoAlmondBridge first.
<!-- /instruction:response-424 -->
