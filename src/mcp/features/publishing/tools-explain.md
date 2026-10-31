# tools.py explain

## publish_objects_to_chestnut

<!-- instruction:publish_objects_to_chestnut -->
Exports specific Rhino objects as one GLB and publishes them to Chestnut.

Use this after execute_rhino_script (and optionally validate_structure), passing the returned object GUIDs. Reusing asset_id updates the existing Chestnut asset without changing placements that already reference it.

Args:
    guids: Rhino object GUIDs to export. Unrelated document objects are excluded.
    asset_name: Human-readable name shown in Chestnut.
    asset_id: Stable optional ID for linked updates. Generated deterministically
              from the Rhino document and GUIDs when omitted.
    body_type: "static" for architecture, "dynamic" for loose props, or
               "kinematic" for script-driven objects.
    collider: Collider intent: "box", "convex", "compound", or "trimesh".
              Chestnut currently falls back to a box where needed.
    preserve_scale: Keep Rhino's real-world dimensions instead of normalizing
                    the model to a one-metre display prop.
    mass: Physics mass in kilograms. Static bodies always use zero.
Returns:
    JSON containing the stable Chestnut asset ID, URL, metadata, and whether
    the operation created or updated the asset.
<!-- /instruction:publish_objects_to_chestnut -->

## publish_to_chestnut

<!-- instruction:publish_to_chestnut -->
Publishes Rhino objects to Chestnut using safe semantic defaults.

This is the preferred publishing tool for normal use. It hides collider, scale, mass, and rigid-body details. Call it when the user says things such as "publish that to Chestnut".

Args:
    guids: Rhino object GUIDs returned by execute_rhino_script.
    asset_name: Human-readable asset name.
    behavior: Optional semantic preset:
        "auto"         — infer architecture versus movable object from name
        "architecture" — fixed building, terrain, structure, or enclosure
        "object"       — movable physical prop affected by gravity
        "animated"     — script-driven door, lift, platform, or mechanism
    asset_id: Optional stable link ID. Omit for a deterministic Rhino link.
<!-- /instruction:publish_to_chestnut -->

## response-847

<!-- instruction:response-847 -->
Rhino bridge is unavailable. Start RhinoAlmondBridge first.
<!-- /instruction:response-847 -->
