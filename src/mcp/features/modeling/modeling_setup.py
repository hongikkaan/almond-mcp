"""MCP-owned recipes and construction-layer setup, shared by the public tools."""
from __future__ import annotations
from almond_mcp.instruction_text import read_instruction

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
    return script(f"ModelingMaterials.Apply(doc, {literal(recipe(material))}, new Guid[] {{ {ids} }}, "
                  f"new Dictionary<string, string> {{ {entries} }}, "
                  f"{str(apply_render_material).lower()}, {str(attach_metadata).lower()})")


def construction_layers(systems, materials):
    root = modeling_policy.POLICY["construction_layer_root"]
    layers = {root: {"path": root, "color": [128, 128, 128]}}

    def add(path, material_id=None):
        modeling_policy.validate_layer_path(path)
        material = materials[material_id] if material_id else None
        layers[path] = {"path": path, "color": material["base_color"] if material else [128, 128, 128]}
        if material:
            layers[path]["material"] = recipe(material)

    for system in systems:
        category = f'{root}::{system["category"]}'
        branch = f'{category}::{system["name"]}'
        default = system["render_material_ids"][0]
        add(category)
        add(branch, default)
        for element in system["elements"]:
            role = element["role"]
            material_id = default
            # Current project defaults; the manifest does not define role-level recipes.
            if role in ("connection", "reinforcement", "decking"):
                material_id = "steel-galvanized"
            if system["structural_material"] == "Wood" and role in ("subfloor", "sheathing"):
                material_id = "wood-birch-ply"
            add(f"{branch}::{role}", material_id)
    return list(layers.values())


def setup_script(material_library, construction_library, overwrite):
    if type(overwrite) is not bool:
        raise ValueError("overwrite must be true or false")
    recipes = [recipe(m) for m in material_library.materials.values()]
    if not recipes or not construction_library.systems:
        raise ValueError("Material and construction libraries must be available before setup")
    if len({r["name"] for r in recipes}) != len(recipes):
        raise ValueError("Duplicate material names in manifest")
    layers = construction_layers(construction_library.systems.values(), material_library.materials)
    return script(f"ModelingMaterials.Setup(doc, {literal(recipes)}, {literal(layers)}, {str(overwrite).lower()})")


def dispatch(code, send, timeout=60.0, *, require_setup=False):
    """Require the explicit-only Bridge contract before one mutation dispatch."""
    dispatched = False
    try:
        problem = check_bridge(send, require_setup=require_setup)
        if problem:
            return problem
        dispatched = True
        result = json.loads(send(json.dumps({"type": "execute", "script": code}).encode("utf-8"), timeout=timeout))
        if not isinstance(result, dict):
            raise ValueError("Bridge returned an invalid mutation result")
        return result
    except Exception as exc:
        return {"status": "error", "mutation_state": "unknown" if dispatched else "not_started",
                "message": read_instruction(__file__, 'response-744').format(exc)}


def check_bridge(send, *, require_setup=False):
    try:
        context = json.loads(send(b'{"type":"get_rhino_context","selection_limit":0}'))
        if not isinstance(context, dict) or context.get("status") not in ("success", "error"):
            raise ValueError("Bridge returned an invalid context response")
        if context["status"] == "error":
            return context
        if context.get("capabilities", {}).get("modeling_materials") != 2:
            return {"status": "error", "error_code": "unsupported_materials", "mutation_state": "not_started",
                    "message": read_instruction(__file__, 'response-746')}
        if require_setup and context.get("capabilities", {}).get("modeling_setup") != 1:
            return {"status": "error", "error_code": "unsupported_modeling_setup", "mutation_state": "not_started",
                    "message": "Load the updated Bridge (modeling_setup=1) before combined Material/Layer setup."}
    except Exception as exc:
        return {"status": "error", "mutation_state": "not_started", "message": str(exc)}
    return None


def setup_result(response):
    if response.get("status") != "success":
        return response
    result = response.get("result")
    if (response.get("result_error") or not isinstance(result, dict)
            or type(result.get("applied")) is not bool
            or not isinstance(result.get("differences"), list)
            or not isinstance(result.get("errors"), list)
            or result["applied"] != (not result["differences"] and not result["errors"])):
        return {"status": "error", "error_code": "setup_result_unconfirmed", "mutation_state": "unknown",
                "message": "Could not confirm setup results. Inspect Rhino before retrying."}
    if result["applied"]:
        return {"status": "success", "applied": True}
    return {"status": "incomplete", "applied": False,
            "differences": result["differences"], "errors": result["errors"]}
