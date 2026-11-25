"""Material recipes and Bridge dispatch shared by assignment and archive placement."""
from __future__ import annotations

import json

from almond_mcp.features.modeling import modeling_policy


def literal(value) -> str:
    """A JSON payload inside a C# string literal, with no interpolated code."""
    return json.dumps(json.dumps(value, ensure_ascii=True, separators=(",", ":")), ensure_ascii=True)


def recipe(material: dict) -> dict:
    material = modeling_policy.validate_material(material)
    return {key: material[key] for key in (
        "material_id", "name", "base_color", "metallic", "roughness", "opacity"
    )}


def script(call: str) -> str:
    return "using System;\nusing System.Collections.Generic;\nusing Rhino;\nusing RhinoAlmondBridge;\n" + (
        "public class Script { public static object Run(RhinoDoc doc) { return " + call + "; } }\n"
    )


def material_script(material, guids, apply_render_material, attach_metadata, extra_strings=None):
    metadata = dict(extra_strings or {})
    entries = ", ".join("{ " + json.dumps(key) + ", " + json.dumps(value, ensure_ascii=True) + " }"
                        for key, value in metadata.items())
    ids = ", ".join("new Guid(" + json.dumps(value) + ")" for value in guids)
    payload = recipe(material)
    if apply_render_material:
        payload["layer_settings"] = modeling_policy.material_layer(material)
    return script(f"ModelingMaterials.Apply(doc, {literal(payload)}, new Guid[] {{ {ids} }}, "
                  f"new Dictionary<string, string> {{ {entries} }}, "
                  f"{str(apply_render_material).lower()}, {str(attach_metadata).lower()})")


def dispatch(code, send, timeout=60.0, *, require_material_layer=False):
    """Require the explicit-only Bridge contract before one mutation dispatch."""
    dispatched = False
    try:
        problem = check_bridge(send, require_assignment=True, require_material_layer=require_material_layer)
        if problem:
            return problem
        dispatched = True
        result = json.loads(send(json.dumps({"type": "execute", "script": code}).encode("utf-8"), timeout=timeout))
        if not isinstance(result, dict):
            raise ValueError("Bridge returned an invalid mutation result")
        return result
    except Exception as exc:
        return {"status": "error", "mutation_state": "unknown" if dispatched else "not_started",
                "message": 'Could not confirm modeling operation: {0}. Inspect Rhino before retrying.'.format(exc)}


def check_bridge(send, *, require_assignment=False, require_material_layer=False):
    try:
        context = json.loads(send(b'{"type":"get_rhino_context","selection_limit":0}'))
        if not isinstance(context, dict) or context.get("status") not in ("success", "error"):
            raise ValueError("Bridge returned an invalid context response")
        if context["status"] == "error":
            return context
        if context.get("capabilities", {}).get("modeling_materials") != 2:
            return {"status": "error", "error_code": "unsupported_materials", "mutation_state": "not_started",
                    "message": 'Load the updated Bridge (modeling_materials=2) before editing materials or layers.'}
        if require_assignment and context.get("capabilities", {}).get("material_assignment_metadata") != 2:
            return {"status": "error", "error_code": "unsupported_material_assignment_metadata", "mutation_state": "not_started",
                    "message": "Load a Bridge with material_assignment_metadata=2 before assigning material."}
        if require_material_layer and context.get("capabilities", {}).get("material_layer_assignment") != 1:
            return {"status": "error", "error_code": "unsupported_material_layer_assignment", "mutation_state": "not_started",
                    "message": "Load the updated Bridge (material_layer_assignment=1) before assigning a material layer."}
    except Exception as exc:
        return {"status": "error", "mutation_state": "not_started", "message": str(exc)}
    return None
