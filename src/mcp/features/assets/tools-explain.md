# tools.py explain

## list_drawing_assets

<!-- instruction:list_drawing_assets -->
When to use: Browse the common model and 2D asset collection, including legacy sources awaiting conversion.
Before calling: No prerequisite; use category and offset/limit to narrow or page the catalogue. Diagram assets are a separate collection.
Inputs from earlier results: None required. Set include_ids=true to obtain asset_id for get_drawing_asset or placement; request field_groups=["paths"] if source paths are needed.
Interpretation: Read file_available, model_status, source_only and drawing_status separately. A source_only or needs_conversion model must be prepared and registered as 3DM while retaining its asset_id.
Limits: Catalogue readiness is file evidence, not visual or placement validation. Optional groups are dimensions, source, paths, drawing, metadata, audit or all; audit exposes timestamps and include_ids independently exposes handles.
<!-- /instruction:list_drawing_assets -->

## search_drawing_assets

<!-- instruction:search_drawing_assets -->
When to use: Find common model or 2D assets by text, category and maximum measured dimensions.
Before calling: No prerequisite; provide only relevant filters, with dimension limits in millimetres and zero meaning unbounded.
Inputs from earlier results: None required. Set include_ids=true to retain asset_id for inspection, preparation/registration or placement; request dimensions or paths through field_groups when needed.
Interpretation: Compare returned dimensions and readiness before choosing a model. Legacy source_only models are not placement-ready even when their original source is available.
Limits: Dimension matching is not a scene fit or clearance check. Diagram assets are separate. Optional groups are dimensions, source, paths, drawing, metadata, audit or all; IDs and timestamps require include_ids and audit respectively.
<!-- /instruction:search_drawing_assets -->

## get_drawing_asset

<!-- instruction:get_drawing_asset -->
When to use: Inspect one known model or 2D asset's availability, provenance and conversion or refresh status.
Before calling: Supply a known asset_id; list or search only if the ID is unknown.
Inputs from earlier results: Reuse asset_id from list_drawing_assets or search_drawing_assets with include_ids=true. Request field_groups=["paths"] for source_path/model_path and dimensions, source or drawing for the corresponding details.
Interpretation: model_status and drawing_status distinguish an available file from a current registered model or drawing package; needs_refresh directs saved source edits to refresh_asset.
Limits: This query neither imports nor visually validates geometry. The supplied asset_id is not echoed even with include_ids=true; retain it yourself. Other optional groups are metadata, audit and all; audit enables timestamps.
<!-- /instruction:get_drawing_asset -->

## prepare_drawing_asset

<!-- instruction:prepare_drawing_asset -->
When to use: Inspect and optionally normalize a source copy into a reviewed 3DM without changing its assembly, layers, materials or origin by default.
Before calling: Select a working Plan artifact directory. inspect needs an existing absolute source_file; OBJ/STL/PLY/OFF/GLB/glTF also need input_units. Later stages reuse job_dir and omit source_file/input_units. An independently prepared 3DM can instead be registered directly.
Inputs from earlier results: Reuse job_dir and review_targets hashes exactly. Request field_groups=["parts","previews"] with include_ids=true to obtain object_id removal handles and images; offset/limit page parts. Optional normalize needs actual image review with review={vision_reviewed:true,inspected_sha256:...,rotation_degrees_xyz:[...],translation:[...],remove:[{object_id,reason}]}; omitted transforms are identity and translation uses source document units. Skip normalize if no edits are needed. verify produces final images; after reviewing them, a second verify with review={vision_reviewed:true,final_sha256:...,name:...,asset_id:...} makes source_3dm available for register_drawing_asset with preparation_job=job_dir.
Interpretation: ready_for_registration records hash-bound caller review attestations, not automated visual approval. status rereads durable reports without running Rhino; reconcile unconfirmed work rather than replaying it.
Limits: Managed output paths are project-relative. Inputs are limited to 100 MB, 10,000 top-level objects and 32 preview block levels; 3DM units are preserved. Only explicitly named top-level objects are removed; definitions, layers and object names remain intact. Previews sample dense meshes and do not verify textures, PBR channels or intended front.
<!-- /instruction:prepare_drawing_asset -->

## register_drawing_asset

<!-- instruction:register_drawing_asset -->
When to use: Publish a 3DM model with measured dimensions and linked plan/front/right drawings as one versioned library asset.
Before calling: Supply an absolute source_3dm with standard Rhino units and a Bridge supporting drawing_asset_extract=2. No preparation prerequisite exists for an independently prepared 3DM; preparation_job optionally attaches hash-bound review and original-source evidence. Existing registered IDs require replace_existing=true.
Inputs from earlier results: Reuse a legacy model's asset_id when converting it; Diagram IDs cannot be reused. For reviewed preparation, pass returned source_3dm and job_dir as preparation_job, with the reviewed name and asset_id. Retain the published ID for placement or refresh_asset.
Interpretation: registration_applied=true means publication happened even if live_index_refreshed=false; reconnect to refresh the index, not repeat registration. requires_reconciliation or an unknown application state needs investigation before retrying. Registration without preparation_job does not attest visual review.
Limits: Source units, origin, layers and blocks are preserved; dimensions and full-size DXF are in mm, SVG defaults to 1:50/1:100 with A3 sheets where they fit. Native extraction covers meshes, Breps, extrusions, surfaces, SubD and embedded nested blocks up to 100 MB/250k triangles; external dependencies are not silently embedded or published. Drawings are silhouettes, not hidden lines or construction details. Replacement retains the canonical source path and may affect linked instances; prior source bytes, drawings and manifest backups are retained. Use refresh_asset for saved edits to an existing linked source; other clients reload on reconnect.
<!-- /instruction:register_drawing_asset -->

## get_asset_drawing

<!-- instruction:get_asset_drawing -->
When to use: Retrieve a registered model's drawing manifest and view URI, or an available legacy pilot drawing package.
Before calling: Supply a known asset_id; discovery is optional when the ID is already known.
Inputs from earlier results: Reuse asset_id from model discovery with include_ids=true. Request field_groups=["paths"] to obtain package_dir and available dimensions_path for file access or audit_asset_drawing; retain the supplied ID because it is not echoed.
Interpretation: The default result retains manifest and plan_svg_uri. A returned package describes stored outputs, not proof that they still match the current source; use audit_asset_drawing when that evidence is needed.
Limits: This retrieves existing drawings and does not generate or refresh them. Optional groups are dimensions, source, paths, drawing, metadata, audit or all; include_ids exposes unsupplied handles independently, and audit enables timestamps.
<!-- /instruction:get_asset_drawing -->

## generate_asset_drawing_views

<!-- instruction:generate_asset_drawing_views -->
When to use: Generate a new local package of plan/front/right mesh silhouettes without replacing a registered asset's stored drawings.
Before calling: Choose exactly one registered 3DM asset_id or absolute custom source_glb. Custom GLB input requires input_units mm or m and up_axis y or z; scales default to [50,100]. Registered 3DM extraction needs the capable Rhino Bridge; custom GLB processing is local.
Inputs from earlier results: Reuse a registered asset_id obtained with include_ids=true, or a known GLB file path. Retain returned package_dir for audit_asset_drawing. Optional source_references need source_id/title/url/publisher/locator/accessed_on/relationship/used_for/terms_url.
Interpretation: The new drawing-runs folder contains full-size mm DXF, scaled SVG and A3 sheets where they fit. Reference records describe evidence attached to this drawing, not retroactive generation inputs.
Limits: No hidden lines, inferred construction or product-front recognition. Custom GLBs must contain static uncompressed triangles, at most 100 MB/250k triangles. Legacy generated IDs need 3DM conversion first. For a changed registered source, use refresh_asset to update stored drawings and measurements instead.
<!-- /instruction:generate_asset_drawing_views -->

## audit_asset_drawing

<!-- instruction:audit_asset_drawing -->
When to use: Check a drawing package's exported file hashes and, when a source is available, its staleness.
Before calling: Supply an absolute package_dir. A known library source resolves automatically; custom packages need the current absolute source_glb to check source geometry.
Inputs from earlier results: Reuse package_dir from generate_asset_drawing_views or get_asset_drawing with field_groups=["paths"]. Keep the original custom GLB path for source comparison.
Interpretation: Read source_geometry as well as status: not_checked means no source comparison was made, even if status is success; stale means the source changed. The checked_files count reports audit coverage, not visual review.
Limits: This is a read-only file/geometry audit, not visual, drawing-quality or construction validation, and it does not regenerate files.
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
When to use: Place a common model or 2D library asset into the active Rhino document, linking 3DM models to their registered source.
Before calling: Use an available known asset_id in an editable document; finish any active edit or Undo/Redo. Standard document/source units and drawing_asset_linked=1 are required for 3DM. Legacy non-3DM models require preparation and registration first. scale must be finite, greater than zero and at most 100.
Inputs from earlier results: Reuse asset_id from list/search results requested with include_ids=true; no lookup is needed if already known. x/y/z and returned bounds use active document units, rotation_degrees is about world Z, scale is dimensionless, and the source origin is the anchor.
Interpretation: Rhino converts 3DM units to document units; linked blocks use active document layers. Inspect returned placement evidence and relevant views before concluding correctness; needs_refresh means save the edited library 3DM and call refresh_asset. Retain returned object_guid for later document operations.
Limits: Files resolve only from the controlled library; ordinary document blocks are not converted into assets. Placement can refresh a shared linked definition and affect existing instances. A timeout may leave a mutation applied: inspect/reconcile before retrying.
<!-- /instruction:place_drawing_asset -->

## search_asset_repository

<!-- instruction:search_asset_repository -->
When to use: Search the unified model/drawing archive and optionally restrict results to current drawing-ready packages.
Before calling: No prerequisite; choose kind all, model or element and drawing_ready=true only when that filter matches the task.
Inputs from earlier results: None required. Set include_ids=true to obtain each record's id for the corresponding asset tools; this search does not return an asset_id field. Request field_groups=["dimensions"] or ["source"] for dimensions or license details, or ["all"] to retain uri for the individual repository resource.
Interpretation: drawing_ready means package files verify against the current 3DM; drawing_status distinguishes missing, stale, invalid and source_requires_conversion. source_available and source_only can identify a convertible source even when it is not ready for placement.
Limits: Non-3DM models such as SKP/GLB need explicit conversion and registration; existing 2D files remain usable. Search does not import or certify appearance. Optional groups are dimensions, source, paths, drawing, metadata, audit or all, but groups cannot add fields absent from this search's shortlist; use individual repository resources for full files/representations.
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
When to use: Remeasure a saved, edited registered 3DM and regenerate its stored drawings while retaining the linked source path.
Before calling: Save edits to the asset's library 3DM and supply its known asset_id; do not use this to convert a legacy source or save an open document. Native extraction requires a Bridge supporting drawing_asset_extract=2.
Inputs from earlier results: Reuse the registered asset_id from registration or discovery with include_ids=true; a needs_refresh result identifies this operation when the source hash changed.
Interpretation: Publication updates dimensions, source hash and drawing package together, preserving prior packages, manifest backups and a source revision copy. If publication succeeded but live index refresh failed, the revision is already applied; reconnect instead of blindly repeating it.
Limits: Source units, origin, layers and blocks stay unchanged. This neither saves Rhino nor reloads existing linked instances; update their linked source in Rhino afterward. Publication does not establish visual correctness, and an error alone is not proof that no file publication occurred.
<!-- /instruction:refresh_asset -->
