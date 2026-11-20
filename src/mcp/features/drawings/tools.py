"""Drawing recipes and presentation tools without a Sheet database registry."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import query_output, validate_field_groups
from almond_mcp.features.drawings.output import GROUPS, project
from almond_mcp.tool_declarations import public_tool
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
    @public_tool(mcp, wrapped=True)
    @query_output
    def list_drawing_recipes(include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        """로드된 도면 스타일 레시피 목록. include_ids=true로 얻은 recipe_id는 drawing_02-get_recipe tool과 drawing_01-apply_style tool에서 사용.

        Args:
            field_groups: scales, parameters, source, audit, all. 생략하거나 비우면 요약.
        """
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


    @public_tool(mcp, wrapped=True)
    @query_output
    def get_drawing_recipe(recipe_id: str, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        """도면 스타일 레시피 조회. field_groups=["scales","parameters"]로 권장 축척·레이어·출력 설정을 확인한 뒤 같은 recipe_id를 drawing_01-apply_style tool에 전달한다.

        Args:
            recipe_id: 이미 확인한 레시피 ID 또는 drawing_05-list_recipes tool에서 include_ids=true로 조회한 ID.
            field_groups: scales, parameters, source, audit, all. 생략하거나 비우면 요약.
        """
        validate_field_groups(field_groups, GROUPS)
        recipe = context.drawing_recipe_indexer.get(recipe_id)
        if not recipe:
            return json.dumps(project(error_payload(f"Unknown drawing recipe_id: {recipe_id}"), field_groups))
        return json.dumps(project({
            "status": "success",
            "recipe": context.drawing_recipe_indexer.public_record(recipe),
        }, field_groups))


    @public_tool(mcp, wrapped=True)
    def apply_drawing_style(recipe_id: str = "") -> str:
        """도면 레시피의 레이어 계층과 색·출력색·출력 선 두께·선종류를 Rhino 문서에 적용. 같은 경로의 기존 레이어도 갱신한다. 같은 이름의 선종류는 기존 정의를 재사용하고 새 선종류는 Almond 선종 매니페스트에서 가져온다. 적용 범위는 레이어와 속성이다.

        변경 전 전용 Undo record를 확보하고 실패 시 해당 record를 복구한다. mutation_state는 none·completed·rolled_back·unknown. requires_reconciliation=true면 재시도 전에 실제 문서 상태를 확인한다.

        레시피의 review_preparation.print_display가 true이면 적용 성공 시 PrintDisplay 설정 명령을 안내한다.

        Args:
            recipe_id: drawing_05-list_recipes tool 또는 drawing_02-get_recipe tool에서 확인. 생략 시 파일명 순으로 처음 로드된 레시피 적용.
        """
        if not recipe_id:
            recipe_id = next(iter(context.drawing_recipe_indexer.recipes), "")
            if not recipe_id:
                return json.dumps(error_payload("No drawing recipes were loaded."))
        recipe = context.drawing_recipe_indexer.get(recipe_id)
        if not recipe:
            return json.dumps(error_payload(f"Unknown drawing recipe_id: {recipe_id}"))
        preparation = recipe.get("review_preparation")
        prepare_review = isinstance(preparation, dict) and preparation.get("print_display") is True
        payload = json.dumps({
            "type": "apply_drawing_style",
            "recipe_id": recipe_id,
            "layers": recipe.get("layers", []),
            "linetype_manifest_path": str(_LINETYPE_MANIFEST),
        }).encode("utf-8")
        try:
            response = context._send_and_receive(payload, timeout=60.0)
            return _add_print_review_preparation(response) if prepare_review else response
        except socket.timeout:
            return json.dumps(error_payload("Applying drawing style timed out."))
        except ConnectionRefusedError:
            return json.dumps(error_payload('Rhino bridge is unavailable. Start RhinoAlmondBridge first.'))
        except Exception as exc:
            return json.dumps(error_payload(f"Drawing style application failed: {exc}"))


    @public_tool(mcp, wrapped=True)
    def import_drawing_hatch_patterns(asset_id: str) -> str:
        """등록된 PAT 자산의 해치 패턴 정의를 Rhino 문서에 가져오기. 같은 이름이 있으면 기존 정의 재사용. 적용 범위는 해치 패턴 정의."""
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
