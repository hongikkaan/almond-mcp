"""Scene MCP tools registered against a per-server feature context."""
from almond_mcp.tool_response import error_payload
from almond_mcp.features.components.public_contract import holon_output
from almond_mcp.features.components.tools import component_error, send_component_request
from almond_mcp.query_output import compact_ack, query_output, select_fields, validate_field_groups
from almond_mcp.managed_paths import bound_model_path
from almond_mcp.tool_declarations import public_tool
import json
from pydantic import StrictBool, StrictInt
from almond_mcp.features.scenes.observation import observe_objects


ACK_FIELDS = {"scene_id", "revision", "scene_revisions"}
SCENE_GROUPS = {
    "scope": {"file_name", "units", "model_path"},
    "state": {"revision"},
    "geometry": {"bounds_mm", "component_id"},
    "audit": {"created_at", "updated_at", "observed_at"},
}


def register(mcp, context):
    def observe(request):
        return send_component_request(context._send_and_receive, request)

    @public_tool(mcp, wrapped=True, annotations={'readOnlyHint': True, 'destructiveHint': False})
    @query_output
    @holon_output
    def list_design_scenes(name: str = "", file_name: str = "", limit: StrictInt = 50,
                           offset: StrictInt = 0, include_ids: StrictBool = False,
                           field_groups: list[str] | None = None) -> str:
        """공유 프로젝트 DB에 등록된 Scene 목록을 조회합니다. 파일명을 생략하면 연결된 파일뿐 아니라 프로젝트의 모든 파일을 포함합니다.

        result는 scenes, total, limit, offset, truncated를 담은 JSON 문자열입니다. truncated=true이면 같은 필터에서 offset을 limit만큼 늘려 다음 페이지를 조회합니다. Scene 상세는 scene_04-get tool, 현재 Rhino 구성원은 scene_06-get_objects tool로 확인합니다.

        Args:
            name: Scene 이름 부분 검색. 대소문자 무관.
            file_name: 확장자를 포함한 정확한 프로젝트 파일명. 생략: 전체 파일.
            limit: 1~200, 기본 50.
            offset: 0부터 시작. 기본 0.
            include_ids: 기본 false. true: scene_id 등 포함.
            field_groups: scope, state, geometry, audit, all. 생략·빈 배열: 요약.
        """
        validate_field_groups(field_groups, SCENE_GROUPS)
        try:
            result = context.retrieval_store.list_scenes(name, file_name, limit, offset)
            result["scenes"] = [select_fields(scene, field_groups, {"scene_id", "name"}, SCENE_GROUPS)
                                for scene in result["scenes"]]
            return json.dumps({"status": "success", **result}, ensure_ascii=False)
        except ValueError as exc:
            return json.dumps(error_payload(str(exc), error_code="invalid_arguments"))

    @public_tool(mcp, wrapped=True)
    @holon_output
    def create_design_scene(name: str, units: str = "mm", file_name: str = "") -> str:
        """설계 영역·프로그램·상황을 나타내는 Scene을 생성합니다.

        Args:
            name: 설계 영역 또는 행위/프로그램 맥락을 설명하는 Scene 이름입니다. 비어 있으면 Untitled가 됩니다.
            units: Scene에 기록할 단위입니다. mm, cm, m, in, ft 중 하나를 선택합니다.
            file_name: context_04-get_project_info tool의 project.files에 등록된 파일명입니다. 폴더는 제외하며, 비어 있으면 파일에 연결하지 않습니다.
        """
        try:
            return json.dumps({
                "status": "success",
                "scene": compact_ack(context.retrieval_store.create_scene(name=name, units=units, file_name=file_name), ACK_FIELDS),
            })
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    @public_tool(mcp, wrapped=True)
    @query_output
    @holon_output
    def get_design_scene(scene_id: str, include_ids: StrictBool = False,
                         field_groups: list[str] | None = None) -> str:
        """Scene의 등록 정보와 Holon·객체 수를 조회합니다. 저장된 요약이며 현재 Rhino 구성원을 실시간 검증하지 않습니다. 객체 수가 null이면 수를 확정할 수 없는 상태입니다. 현재 구성원은 scene_06-get_objects tool로 조회합니다.

        result는 scene 또는 오류를 담은 JSON 문자열입니다. include_ids=true여도 입력한 scene_id는 반복 반환하지 않습니다.

        Args:
            scene_id: scene_07-list tool(include_ids=true) 또는 기록된 Scene 참조에서 얻은 기존 Scene ID입니다.
            include_ids: 기본 false. 결과에 포함된 식별자를 표시합니다.
            field_groups: scope, state, geometry, audit, all. 생략·빈 배열: 요약.
        """
        validate_field_groups(field_groups, SCENE_GROUPS)
        scene = context.retrieval_store.get_scene(scene_id)
        if not scene:
            return json.dumps(error_payload(f"Unknown scene_id: {scene_id}"))
        return json.dumps({"status": "success", "scene": select_fields(scene, field_groups,
            {"scene_id", "name", "units", "revision", "components", "objects", "direct_objects"}, SCENE_GROUPS)})

    @public_tool(mcp, wrapped=True)
    @holon_output
    def update_design_scene(scene_id: str, file_name: str | None = None) -> str:
        """Scene의 프로젝트 파일 연결을 변경하거나 해제합니다.

        Args:
            scene_id: scene_07-list tool(include_ids=true) 또는 기록된 Scene 참조에서 얻은 기존 Scene ID입니다.
            file_name: context_04-get_project_info tool의 project.files에 등록된 교체 파일명입니다. 빈 문자열은 연결 해제, 생략/null은 유지입니다.
        """
        try:
            return json.dumps({"status": "success", "scene": compact_ack(context.retrieval_store.update_scene(scene_id, file_name), ACK_FIELDS)})
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    def _observe(model_path, ids):
        return observe_objects(context._send_and_receive, model_path, ids)

    @public_tool(mcp, wrapped=True, errors=True)
    def add_scene_objects(scene_id: str, object_ids: list[str], expected_model_path: str = "") -> str:
        """Rhino 객체를 Scene에 포함하거나 해당 Scene에서 제외했던 Holon 구성원을 복원합니다.

        Args:
            scene_id: scene_07-list tool(include_ids=true)에서 얻은 기존 Scene ID입니다.
            object_ids: 일반 형상이나 클리핑 평면을 포함하는 객체 GUID 배열로, 최대 4096개 항목을 허용합니다.
            expected_model_path: 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
        """
        try:
            result = context.retrieval_store.change_scene_objects(scene_id, bound_model_path(expected_model_path),
                object_ids, True, observe, _observe)
            return json.dumps({"status": "success", **result})
        except Exception as exc:
            return component_error(exc)

    @public_tool(mcp, wrapped=True, errors=True)
    def remove_scene_objects(scene_id: str, object_ids: list[str], expected_model_path: str = "") -> str:
        """객체를 Scene에서 제외합니다. Rhino 형상과 Holon 그룹은 유지됩니다.

        Args:
            scene_id: scene_07-list tool(include_ids=true)에서 얻은 기존 Scene ID입니다.
            object_ids: 일반 형상 또는 클리핑 평면을 포함하는 객체 GUID 배열이며, 최대 4096개 항목을 받습니다.
            expected_model_path: 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
        """
        try:
            result = context.retrieval_store.change_scene_objects(scene_id, bound_model_path(expected_model_path),
                object_ids, False, observe, _observe)
            return json.dumps({"status": "success", **result})
        except Exception as exc:
            return component_error(exc)

    @public_tool(mcp, wrapped=True, annotations={'readOnlyHint': True, 'destructiveHint': False}, errors=True)
    @query_output
    @holon_output
    def get_scene_objects(scene_id: str, include_ids: StrictBool = False,
                          field_groups: list[str] | None = None, limit: StrictInt = 50,
                          offset: StrictInt = 0, expected_model_path: str = "") -> str:
        """Scene의 직접 객체와 Holon 구성원을 현재 Rhino 문서에서 조회합니다. Scene에서 제외한 구성원은 목록에 포함되지 않습니다.

        result는 objects, total, limit, offset, truncated 및 live_verified 또는 오류를 담은 JSON 문자열입니다. truncated=true이면 같은 조건에서 offset을 limit만큼 늘려 다음 페이지를 조회합니다.

        Args:
            scene_id: scene_07-list tool(include_ids=true) 또는 기록된 Scene 참조에서 얻은 기존 Scene ID입니다.
            include_ids: 기본 false. true: 객체 GUID 포함.
            field_groups: scope, state, geometry, audit, all. 생략·빈 배열: 요약.
            limit: 1~200, 기본 50.
            offset: 0부터 시작. 기본 0.
            expected_model_path: 생략: 연결된 문서. 지정 시 연결 문서와 일치해야 함.
        """
        validate_field_groups(field_groups, SCENE_GROUPS)
        try:
            if type(limit) is not int or not 1 <= limit <= 200 or type(offset) is not int or offset < 0:
                return json.dumps(error_payload("limit must be 1–200 and offset non-negative.", error_code="invalid_arguments"))
            model_path = bound_model_path(expected_model_path)
            objects = context.retrieval_store.scene_objects(scene_id, model_path, observe, _observe)
            selected = [select_fields(obj, field_groups,
                {"rhino_guid", "name", "object_type"}, SCENE_GROUPS) for obj in objects[offset:offset + limit]]
            return json.dumps({"status": "success", "scene_id": scene_id, "objects": selected,
                               "total": len(objects), "limit": limit, "offset": offset,
                               "truncated": offset + len(selected) < len(objects), "live_verified": True, "model_path": model_path}, ensure_ascii=False)
        except Exception as exc:
            return component_error(exc)


    return {
        "list_design_scenes": list_design_scenes,
        "create_design_scene": create_design_scene,
        "get_design_scene": get_design_scene,
        "update_design_scene": update_design_scene,
        "get_scene_objects": get_scene_objects,
        "add_scene_objects": add_scene_objects,
        "remove_scene_objects": remove_scene_objects,
    }
