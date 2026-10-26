"""Drawing recipes and presentation tools without a Sheet database registry."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import query_output
from almond_mcp.instruction_text import tool_instruction, read_instruction
from pydantic import StrictBool
import json
import socket




def register(mcp, context):
    """Register drawing tools against the assembling server's live services."""
    @mcp.tool()
    @tool_instruction(__file__, 'list_drawing_recipes')
    @query_output
    def list_drawing_recipes(include_ids: StrictBool = False) -> str:
        recipes = []
        for recipe_id, recipe in sorted(context.drawing_recipe_indexer.recipes.items()):
            recipes.append({
                "recipe_id": recipe_id,
                "name": recipe.get("name"),
                "description": recipe.get("description"),
                "projection": recipe.get("projection", {}).get("type"),
                "recommended_scales": recipe.get("recommended_scales", []),
            })
        return json.dumps({"total": len(recipes), "recipes": recipes})


    @mcp.tool()
    @tool_instruction(__file__, 'get_drawing_recipe')
    @query_output
    def get_drawing_recipe(recipe_id: str, include_ids: StrictBool = False) -> str:
        recipe = context.drawing_recipe_indexer.get(recipe_id)
        if not recipe:
            return json.dumps(error_payload(f"Unknown drawing recipe_id: {recipe_id}"))
        return json.dumps({
            "status": "success",
            "recipe": context.drawing_recipe_indexer.public_record(recipe),
        })


    @mcp.tool()
    @tool_instruction(__file__, 'apply_drawing_style')
    def apply_drawing_style(recipe_id: str = "technical_axon_v1") -> str:
        recipe = context.drawing_recipe_indexer.get(recipe_id)
        if not recipe:
            return json.dumps(error_payload(f"Unknown drawing recipe_id: {recipe_id}"))
        payload = json.dumps({
            "type": "apply_drawing_style",
            "recipe_id": recipe_id,
            "layers": recipe.get("layers", []),
        }).encode("utf-8")
        try:
            return context._send_and_receive(payload, timeout=60.0)
        except socket.timeout:
            return json.dumps(error_payload("Applying drawing style timed out."))
        except ConnectionRefusedError:
            return json.dumps(error_payload(read_instruction(__file__, 'response-642')))
        except Exception as exc:
            return json.dumps(error_payload(f"Drawing style application failed: {exc}"))


    @mcp.tool()
    @tool_instruction(__file__, 'import_drawing_hatch_patterns')
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
            return json.dumps(error_payload(read_instruction(__file__, 'response-645')))
        except Exception as exc:
            return json.dumps(error_payload(f"Hatch pattern import failed: {exc}"))


    return {
        "list_drawing_recipes": list_drawing_recipes,
        "get_drawing_recipe": get_drawing_recipe,
        "apply_drawing_style": apply_drawing_style,
        "import_drawing_hatch_patterns": import_drawing_hatch_patterns,
    }
