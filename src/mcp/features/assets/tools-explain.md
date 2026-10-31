# tools.py explain

## list_drawing_assets

<!-- instruction:list_drawing_assets -->
Lists the common 3DM model and 2D collection, including legacy sources awaiting conversion.

The historical drawing tool names cover imported and generated models. Diagram assets remain separate. source_only/needs_conversion entries require prepare_drawing_asset and 3DM registration before placement; retain their asset_id.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds dimensions, source, paths, drawing, metadata, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:list_drawing_assets -->

## search_drawing_assets

<!-- instruction:search_drawing_assets -->
Searches the common model/2D collection by text, category and measured dimensions.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds dimensions, source, paths, drawing, metadata, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:search_drawing_assets -->

## get_drawing_asset

<!-- instruction:get_drawing_asset -->
Returns one model/2D asset's provenance, representations, availability and conversion or refresh status.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds dimensions, source, paths, drawing, metadata, audit, or all; default is summary.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:get_drawing_asset -->

## prepare_drawing_asset

<!-- instruction:prepare_drawing_asset -->
Prepare a source copy as a 3DM while preserving its assembly, layers, materials and origin.

inspect requires source_file and returns measured top-level parts and images in the working Plan's artifact directory. Mesh interchange files (OBJ/STL/PLY/OFF/GLB/glTF) require input_units. 3DM units are preserved. Limits: 100 MB input, 10,000 top-level objects, 32 preview block levels. Managed paths are project-relative.
normalize is optional: after viewing the images, supply review={vision_reviewed:true,inspected_sha256:...,rotation_degrees_xyz:[...],translation:[...],remove:[{object_id,reason}]}. Omitted transforms are identity; translation uses source document units. Only named top-level objects are removed. Block definitions, layers and object names remain intact.
verify reopens the current prepared 3DM and returns final images. A second verify with review={vision_reviewed:true,final_sha256:...,name:...,asset_id:...} records review of that revision; register_drawing_asset then publishes source_3dm with preparation_job=job_dir. An independently prepared 3DM can be registered directly.
status rereads reports without executing Rhino. field_groups adds parts, previews, provenance or all; offset/limit pages parts, include_ids=true exposes edit handles. Unconfirmed operations require reconciliation rather than replay. Previews describe shape and sample dense meshes; they do not verify textures, PBR channels or the object's intended front.
<!-- /instruction:prepare_drawing_asset -->

## register_drawing_asset

<!-- instruction:register_drawing_asset -->
Register a 3DM model and derive plan/front/right drawings in one versioned publication.

Supply an absolute 3DM path with standard Rhino units. Units, origin, block structure and layers are preserved; dimensions are measured in mm without AABB input. preparation_job optionally attaches hash-bound image review and the original source. Without it, registration does not attest visual review.
Native extraction supports meshes, Breps, extrusions, surfaces, SubD and embedded nested blocks up to 100 MB/250k triangles. External block dependencies require separate verification and are not silently embedded or published.
Copies the source and writes full-size mm DXF, SVG at 1:50/1:100 and A3 sheets where they fit. These are mesh silhouettes, not hidden lines or construction details. Retain existing model IDs when converting sources such as SKP or GLB to 3DM; Diagram IDs remain separate.
Existing registered IDs require replace_existing=true. A replacement retains the canonical source path and can affect linked instances sharing it; prior source bytes, drawings and manifest backups are retained. Source edits to an existing linked asset use refresh_asset. Publication refreshes this MCP's index; other clients reload on reconnect.
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
Choose a registered 3DM asset_id OR an absolute custom source_glb path. Custom interchange files REQUIRE input_units mm or m; up_axis y or z. Scales default to [50,100].
Registered 3DMs use native geometry extraction; custom GLBs require static, uncompressed triangles (max 100 MB/250k triangles). Legacy generated IDs require 3DM conversion first. Use refresh_asset when an edited registered source needs its stored drawings and measurements updated.
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
Places a common model/2D asset; 3DM models use a linked block with active document layers.

x/y/z and returned bounds use active document units; scale is dimensionless. Rhino converts source 3DM units to document units. The source origin is the placement anchor. Edit the library 3DM, then refresh_asset after saving; a changed source with stale metadata returns needs_refresh. Ordinary document blocks are not converted to assets. Legacy non-3DM sources require preparation and registration before placement. Files resolve from the controlled model library.
<!-- /instruction:place_drawing_asset -->

## search_asset_repository

<!-- instruction:search_asset_repository -->
Search the unified model/drawing archive. kind: all, model or element.

Returns stable IDs, file availability, dimensions and MCP resource URIs.
Drawing-ready means the package files verify against the current 3DM. drawing_status distinguishes missing, stale, invalid and source_requires_conversion. Non-3DM models such as SKP and GLB remain source-only until explicitly converted to 3DM; existing 2D files remain usable.
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
Load a Bridge with drawing_asset_extract=2 before registering or refreshing a 3DM asset
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
This asset ID belongs to the separate Diagram collection
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
Inspect the placed geometry and relevant Rhino views before concluding the placement is correct.
<!-- /instruction:response-419 -->

## response-423

<!-- instruction:response-423 -->
Rhino drawing-asset import timed out; inspect the model before retrying.
<!-- /instruction:response-423 -->

## response-424

<!-- instruction:response-424 -->
Rhino bridge is unavailable. Start RhinoAlmondBridge first.
<!-- /instruction:response-424 -->

## refresh_asset

<!-- instruction:refresh_asset -->
Remeasure an edited registered 3DM and regenerate its 2D representations while retaining the linked source path.

Supply asset_id after saving edits to its library 3DM. Publishes dimensions, source hash and a drawing package together; preserves prior packages, manifest backups and a source revision copy. Source units, origin, layers and blocks remain unchanged. The tool does not save or reload Rhino instances; their linked source can then be updated in Rhino. If publication succeeded but index refresh failed, the revision is already applied.
<!-- /instruction:refresh_asset -->
