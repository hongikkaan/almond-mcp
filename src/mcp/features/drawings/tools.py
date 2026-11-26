"""Drawing recipes and presentation tools without a Sheet database registry."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import query_output, validate_field_groups
from almond_mcp.features.drawings.output import GROUPS, project
from almond_mcp.tool_declarations import public_tool
from almond_mcp.features.drawings.standard import STANDARD_D, STANDARD_D_ID, STANDARD_D_LAYERS, StandardDLayerPath
from pydantic import StrictBool
import json
import socket
from pathlib import Path


_LINETYPE_MANIFEST = Path(__file__).resolve().parents[2] / "profiles" / "linetype" / "manifest.json"
_PRINT_DISPLAY_REVIEW_MACRO = (
    "_PrintDisplay _Scope=_Document _Viewport=_Model _State=_On _Color=_Print "
    "_Viewport=_Layout _State=_On _Color=_Print _DetailBorder=_UsePrintWidth _Enter"
)


def _add_print_review_preparation(response: str) -> str:
    try:
        result = json.loads(response)
    except (TypeError, ValueError):
        return response
    if not isinstance(result, dict) or result.get("status") != "success":
        return response
    result["print_display_review"] = {"macro": _PRINT_DISPLAY_REVIEW_MACRO}
    return json.dumps(result)


def register(mcp, context):
    """Register drawing tools against the assembling server's live services."""
    @public_tool(mcp)
    @query_output
    def list_drawing_recipes(field_groups: list[str] | None = None) -> str:
        validate_field_groups(field_groups, GROUPS)
        recipes = []
        for recipe_id, recipe in sorted(context.drawing_recipe_indexer.recipes.items()):
            recipes.append({
                **context.drawing_recipe_indexer.public_record(recipe),
                "recipe_id": recipe_id,
                "name": recipe.get("name"),
                "description": recipe.get("description"),
                "projection": recipe.get("projection", {}).get("type"),
                "recommended_scales": recipe.get("recommended_scales", []),
            })
        return json.dumps(project({"total": len(recipes), "recipes": recipes}, field_groups))


    @public_tool(mcp)
    @query_output
    def get_drawing_recipe(recipe_id: str, field_groups: list[str] | None = None) -> str:
        validate_field_groups(field_groups, GROUPS)
        recipe = STANDARD_D if recipe_id == STANDARD_D_ID else context.drawing_recipe_indexer.get(recipe_id)
        if not recipe:
            return json.dumps(project(error_payload(f"Unknown drawing recipe_id: {recipe_id}"), field_groups))
        return json.dumps(project({
            "status": "success",
            "recipe": context.drawing_recipe_indexer.public_record(recipe),
        }, field_groups))


    @public_tool(mcp)
    def apply_drawing_style(
        recipe_id: str = "standard_d",
        layer_path: StandardDLayerPath = None,
        overwrite: StrictBool | None = None,
    ) -> str:
        recipe_id = recipe_id or STANDARD_D_ID
        standard_d = recipe_id == STANDARD_D_ID
        if layer_path is not None and not standard_d:
            return json.dumps(error_payload("layer_path is only available for the standard_d recipe."))
        recipe = STANDARD_D if standard_d else context.drawing_recipe_indexer.get(recipe_id)
        if not recipe:
            return json.dumps(error_payload(f"Unknown drawing recipe_id: {recipe_id}"))
        layers = recipe.get("layers", [])
        if layer_path is not None:
            layer = STANDARD_D_LAYERS.get(layer_path)
            if layer is None:
                return json.dumps(error_payload(f"Unknown standard D layer_path: {layer_path}"))
            # A chosen sublayer must not create its standard parent with Rhino defaults.
            layers = [layer, *(
                row for path, row in STANDARD_D_LAYERS.items() if layer_path.startswith(path + "::")
            )]
        preparation = recipe.get("review_preparation")
        prepare_review = isinstance(preparation, dict) and preparation.get("print_display") is True
        includes_standard = recipe.get("_layer_template") == STANDARD_D_ID
        payload = json.dumps({
            "type": "apply_drawing_style",
            **({"include_standard_d": True} if includes_standard else {}),
            "recipe_id": recipe_id,
            "layers": layers,
            "overwrite": (not standard_d) if overwrite is None and not includes_standard else overwrite,
            "linetype_manifest_path": str(_LINETYPE_MANIFEST),
        }).encode("utf-8")
        try:
            if standard_d or includes_standard or overwrite is False:
                observed = json.loads(context._send_and_receive(
                    b'{"type":"get_rhino_context","sections":[],"selection_limit":0}', timeout=60.0))
                capability = observed.get("capabilities", {}).get("drawing_style_protection")
                if observed.get("status") != "success" or type(capability) is not int or capability != 1:
                    return json.dumps(error_payload("Load a Bridge with drawing_style_protection=1."))
            response = context._send_and_receive(payload, timeout=60.0)
            return _add_print_review_preparation(response) if prepare_review else response
        except socket.timeout:
            return json.dumps(error_payload("Applying drawing style timed out."))
        except ConnectionRefusedError:
            return json.dumps(error_payload('Rhino bridge is unavailable. Start RhinoAlmondBridge first.'))
        except Exception as exc:
            return json.dumps(error_payload(f"Drawing style application failed: {exc}"))


    @public_tool(mcp)
    def import_drawing_hatch_patterns(asset_id: str) -> str:
        asset = context.drawing_asset_indexer.get(asset_id)
        if not asset:
            return json.dumps(error_payload(f"Unknown drawing asset_id: {asset_id}"))
        if not asset.get("file_available"):
            return json.dumps(error_payload(f"Drawing asset file is missing for {asset_id}."))
        resolved = asset["_resolved_file"]
        if not resolved.lower().endswith(".pat"):
            return json.dumps(error_payload(f"Asset {asset_id} is not a .pat hatch definition file."))
        payload = json.dumps({
            "type": "import_hatch_patterns",
            "file_path": resolved,
        }).encode("utf-8")
        try:
            return context._send_and_receive(payload, timeout=60.0)
        except socket.timeout:
            return json.dumps(error_payload("Hatch pattern import timed out."))
        except ConnectionRefusedError:
            return json.dumps(error_payload('Rhino bridge is unavailable. Start RhinoAlmondBridge first.'))
        except Exception as exc:
            return json.dumps(error_payload(f"Hatch pattern import failed: {exc}"))


    return {
        "list_drawing_recipes": list_drawing_recipes,
        "get_drawing_recipe": get_drawing_recipe,
        "apply_drawing_style": apply_drawing_style,
        "import_drawing_hatch_patterns": import_drawing_hatch_patterns,
    }
