"""Drawing recipes and presentation tools without a Sheet database registry."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import query_output, validate_field_groups
from almond_mcp.features.drawings.output import GROUPS, project
from almond_mcp.instruction_text import tool_instruction, read_instruction
from pydantic import StrictBool
import json
import socket


_A4_RECIPE_ID = "architectural_plan_section_a4_v1"
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
    result["review_preparation"] = {
        "status": "not_executed",
        "message": (
            "PrintDisplay was not inspected or changed. Reuse a discovered pipe matching "
            "this connection's Rhino PID and saved document path; discover it only if unconfirmed. "
            "Skip this step if Document-scoped Model/Layout PrintDisplay On with Print colors "
            "is already confirmed."
        ),
        "cli": {
            "program": "rhinocode",
            "discovery_arguments": ["list", "--json"],
            "arguments_template": ["--rhino", "{matched_pipeId}", "command", _PRINT_DISPLAY_REVIEW_MACRO],
        },
    }
    return json.dumps(result)


def register(mcp, context):
    """Register drawing tools against the assembling server's live services."""
    @mcp.tool()
    @tool_instruction(__file__, 'list_drawing_recipes')
    @query_output
    def list_drawing_recipes(include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        validate_field_groups(field_groups, GROUPS)
        recipes = []
        for recipe_id, recipe in sorted(context.drawing_recipe_indexer.recipes.items()):
            recipes.append({
                "recipe_id": recipe_id,
                "name": recipe.get("name"),
                "description": recipe.get("description"),
                "projection": recipe.get("projection", {}).get("type"),
                "recommended_scales": recipe.get("recommended_scales", []),
            })
        return json.dumps(project({"total": len(recipes), "recipes": recipes}, field_groups))


    @mcp.tool()
    @tool_instruction(__file__, 'get_drawing_recipe')
    @query_output
    def get_drawing_recipe(recipe_id: str, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        validate_field_groups(field_groups, GROUPS)
        recipe = context.drawing_recipe_indexer.get(recipe_id)
        if not recipe:
            return json.dumps(project(error_payload(f"Unknown drawing recipe_id: {recipe_id}"), field_groups))
        return json.dumps(project({
            "status": "success",
            "recipe": context.drawing_recipe_indexer.public_record(recipe),
        }, field_groups))


    @mcp.tool()
    @tool_instruction(__file__, 'apply_drawing_style')
    def apply_drawing_style(recipe_id: str = "technical_axon_v1") -> str:
        recipe = context.drawing_recipe_indexer.get(recipe_id)
        if not recipe:
            return json.dumps(error_payload(f"Unknown drawing recipe_id: {recipe_id}"))
        preparation = recipe.get("review_preparation")
        prepare_review = (recipe_id == _A4_RECIPE_ID and isinstance(preparation, dict)
                          and preparation.get("print_display") is True)
        payload = json.dumps({
            "type": "apply_drawing_style",
            "recipe_id": recipe_id,
            "layers": recipe.get("layers", []),
        }).encode("utf-8")
        try:
            response = context._send_and_receive(payload, timeout=60.0)
            return _add_print_review_preparation(response) if prepare_review else response
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
