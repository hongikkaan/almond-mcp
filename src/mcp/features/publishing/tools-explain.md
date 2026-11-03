# tools.py explain

## publish_objects_to_chestnut

<!-- instruction:publish_objects_to_chestnut -->
When to use: Publish specific Rhino objects as one Chestnut GLB with explicit physics, collider and scale settings.
Before calling: Supply current object GUIDs and asset_name with Rhino and the configured Chestnut service available. Use publish_to_chestnut for normal semantic defaults; no modeling or structural validation call is mandatory. Confirm the selected objects and permission to publish their geometry and source metadata.
Inputs from earlier results: Reuse actual object GUIDs from modeling, selection or other document results. Reuse an existing Chestnut asset_id for linked updates; when omitted, the tool derives a stable ID from document path, exported GUIDs and the name slug.
Interpretation: Inspect the service response for created/updated state and retain its stable asset ID for later updates. Reusing asset_id updates that Chestnut asset without changing placements referencing it; success does not validate physics or appearance.
Limits: This uploads geometry plus source document path/GUIDs, bounds and units. Only selected objects are exported. body_type/collider are intent; Chestnut may fall back to box. preserve_scale keeps real-world size; static mass is zero, while a zero mass for non-static bodies becomes 1 kg. Network errors can leave publication uncertain, so check the service before retrying.

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
When to use: Publish selected Rhino objects to Chestnut using simple architecture, object or animated behaviour presets.
Before calling: Supply current object GUIDs and asset_name with Rhino and Chestnut available; no scripting or validation prerequisite exists. Confirm the intended objects and authorization to upload geometry and source document metadata. Choose explicit behavior if name-based auto inference is unsuitable.
Inputs from earlier results: Reuse object GUIDs from modeling, selection or prior document results. Reuse the returned Chestnut asset ID as asset_id for later updates; omit it for a deterministic link based on document path, GUIDs and name slug.
Interpretation: architecture maps to static, object to dynamic and animated to kinematic; all preserve real-world scale and use box colliders. auto uses English words in asset_name, not geometry inspection. Success is a service acknowledgement, not validated appearance or simulated behaviour.
Limits: Animated selects a body type and does not create animation. The underlying publisher normalizes zero non-static mass to 1 kg. This uploads a GLB and metadata including source path/GUIDs; repeated asset_id updates the existing asset while referenced placements remain. Use publish_objects_to_chestnut for low-level controls; reconcile uncertain network results before repeating publication.

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
