# tools.py explain

## export_asset_contract

<!-- instruction:export_asset_contract -->
Exports Rhino objects as a portable Almond asset: a GLB plus an asset
contract (.almond.json) carrying what the file cannot.

The contract records real dimensions in mm, the anchor and support plane,
clearances, and the Almond material_id of every object - so another
application (Blender, Unreal, another Rhino) can restore full meaning
even though glTF drops per-object metadata. Pair with
import_asset_contract on the receiving side.

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
Imports an Almond asset contract (from Blender, Unreal, or another Rhino)
into the open Rhino document, restoring everything the file format drops.

Runs the full receive sequence: import the GLB, collapse the duplicate
materials glTF creates, restore canonical PBR values from the Almond
material library (glTF round trips shift base colours), re-attach the
almond:* metadata keyed off the surviving material name, place the asset
at the requested point using the contract's anchor, and verify the
measured size against the contract's recorded dimensions.

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
Returns Python to run inside Blender (via blender-mcp's execute_code) so
Blender participates in the Almond workflow without a dedicated bridge.

Actions:
    "export"    - export the current Blender selection as an Almond asset
                  contract + GLB (measured from evaluated mesh data,
                  because Blender inflates curve bounding boxes).
    "materials" - create Almond library materials in Blender (sRGB values
                  converted to linear) and assign them to named objects,
                  tagging both with almond:* properties.

Args:
    action: "export" or "materials".
    asset_id, name, output_dir: for "export" (output_dir defaults to the
        Almond exchange folder).
    material_id, object_names: for "materials".
Returns:
    JSON with a "script" field to pass to Blender's execute_code.
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
