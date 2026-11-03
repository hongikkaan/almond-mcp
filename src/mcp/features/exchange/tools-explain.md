# tools.py explain

## export_asset_contract

<!-- instruction:export_asset_contract -->
When to use: Export specific Rhino objects as a GLB plus an Almond contract for cross-application transfer.
Before calling: Supply current object GUIDs, a stable asset_id and a connected Rhino document; no modeling or validation tool is mandatory. Choose output_dir if the default user-data exchange folder is unsuitable.
Inputs from earlier results: Reuse object GUIDs returned by modeling, selection or prior document operations, not catalogue asset IDs. Retain returned glb_path and contract_path together; import_asset_contract takes contract_path on the receiving side.
Interpretation: The contract records measured dimensions in mm, default bottom-center anchor/floor support, zero clearances and recognized Almond material groups. Material mapping may be incomplete; export success does not prove every object's material identity was captured.
Limits: This writes files and may replace the same asset_id's files in the chosen folder. The contract preserves recorded meaning beyond glTF metadata, not arbitrary Rhino data or automatic Blender/Unreal restoration. Inspect the receiving application's geometry/material result separately.

Args:
    guids: Rhino object GUIDs to export (from execute_rhino_script).
    asset_id: Stable id, e.g. "canopy-pavilion-01" (letters, digits, . _ -).
    name: Human-readable name; defaults to asset_id.
    output_dir: Destination folder. Default: <user data dir>/exchange.
Returns:
    JSON with the glb path, contract path, and recorded dimensions.
<!-- /instruction:export_asset_contract -->

## import_asset_contract

<!-- instruction:import_asset_contract -->
When to use: Import a GLB with its Almond contract into Rhino and restore recognized materials, metadata and anchor placement.
Before calling: Keep the contract and referenced GLB available together and connect the intended active Rhino document. Placement x_mm/y_mm/z_mm is in millimetres regardless of document units, rotation_degrees is about world Z, and the destination layer is created if absent.
Inputs from earlier results: Reuse contract_path returned by export_asset_contract or the path printed after running the Blender export helper. Retain imported_guids from this response for later document edits instead of re-importing to obtain handles.
Interpretation: Read imported_count, metadata_restored, materials_deduplicated and unknown_material_ids separately. dimension_check compares sorted measured extents in mm at 2% tolerance; ok is not visual correctness, while unknown means the comparison lacks usable evidence.
Limits: Canonical PBR/material metadata is restored only for known library materials recognized by name; this does not restore everything glTF omits. Rotation can change measured world-axis extents. A restore/place failure may leave imported_guids in the document; reconcile them before retrying because an error is not rollback.

Args:
    contract_path: Path to a .almond.json contract file.
    x_mm, y_mm, z_mm: Placement point in millimetres (contract anchor).
    rotation_degrees: Rotation about world Z.
    layer: Destination layer, created if absent.
Returns:
    JSON with counts restored/deduplicated and a dimension_check comparing
    what landed against the contract.
<!-- /instruction:import_asset_contract -->

## get_blender_helper_script

<!-- instruction:get_blender_helper_script -->
When to use: Obtain Blender Python for exporting an Almond contract/GLB or assigning canonical Almond materials to named objects.
Before calling: Choose action export or materials; no Rhino call is required. export needs asset_id and a Blender mesh/curve/surface selection when run. materials needs a known material_id and object_names; query the material library only if that ID is unknown.
Inputs from earlier results: Pass the returned script to Blender execution, such as blender-mcp execute_code. For materials, reuse material_id from material discovery with include_ids=true and actual Blender object names. After running export, reuse its printed contract path with import_asset_contract.
Interpretation: Success here means code was generated, not executed or verified in Blender. Export measures evaluated mesh data rather than inflated curve bounding boxes; material code converts sRGB to linear and tags matching materials/objects.
Limits: Only export and materials are supported, not import. Running export writes to output_dir or the default exchange folder; the materials script replaces material slots on matching objects. Generating either script alone changes nothing. The script stays in the default payload; field_groups notes/audit/all and include_ids only affect supplementary output.

Args:
    action: "export" or "materials".
    asset_id, name, output_dir: for "export" (output_dir defaults to the
        Almond exchange folder).
    material_id, object_names: for "materials".
Returns:
    JSON with a "script" field to pass to Blender's execute_code.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
field_groups adds notes, audit, or all; the requested manifest/parsed logic/script remains in the default payload.
include_ids independently enables handles; audit enables timestamps.
<!-- /instruction:get_blender_helper_script -->

## response-672

<!-- instruction:response-672 -->
Open this contract elsewhere with import_asset_contract, or run get_blender_helper_script('import') to load it in Blender.
<!-- /instruction:response-672 -->

## response-677

<!-- instruction:response-677 -->
Run in Blender, then call import_asset_contract with the printed path.
<!-- /instruction:response-677 -->

## response-679

<!-- instruction:response-679 -->
Unknown material_id: {0}. Call list_materials.
<!-- /instruction:response-679 -->
