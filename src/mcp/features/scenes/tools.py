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
        """공유 프로젝트 DB의 Scene 목록 조회. Scene 상세는 scene_04-get tool, 현재 Rhino 구성원은 scene_06-get_objects tool로 조회.

        Args:
            name: 대소문자를 구분하지 않는 부분 검색
            file_name: 확장자를 포함한 정확한 프로젝트 파일명. 생략 시 프로젝트 전체 범위에서 조회
            limit: 1~200
            field_groups: scope, state, geometry, audit, all 중 선택. 생략하거나 빈 배열을 주면 요약 조회
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
        """설계 영역이나 프로그램, 상황을 나타내는 Scene 생성

        Args:
            name: 빈 이름은 Untitled scene으로 저장.
            units: mm, cm, m, in, ft 중 선택.
            file_name: context_04-get_project_info tool의 project.files에 등록된 파일명으로, 폴더 제외
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
        """Scene의 등록 정보와 저장된 Holon·객체 수 조회. 현재 Rhino 구성원은 scene_06-get_objects tool로 조회. include_ids=true일 때도 입력한 scene_id는 생략.

        Args:
            scene_id: scene_07-list tool에서 include_ids=true로 조회하거나 이전에 기록한 Scene ID
            field_groups: scope, state, geometry, audit, all 중 선택. 생략하거나 빈 배열을 주면 요약 조회
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
        """Scene의 프로젝트 파일 연결 변경 또는 해제

        Args:
            scene_id: scene_07-list tool에서 include_ids=true로 조회하거나 이전에 기록한 Scene ID
            file_name: context_04-get_project_info tool의 project.files에 등록된 파일명. 빈 문자열은 연결 해제, 생략하거나 null이면 기존 연결 유지
        """
        try:
            return json.dumps({"status": "success", "scene": compact_ack(context.retrieval_store.update_scene(scene_id, file_name), ACK_FIELDS)})
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))


    def _observe(model_path, ids):
        return observe_objects(context._send_and_receive, model_path, ids)

    @public_tool(mcp, wrapped=True, errors=True)
    def add_scene_objects(scene_id: str, object_ids: list[str], expected_model_path: str = "") -> str:
        """Rhino 객체를 Scene에 추가하거나 해당 Scene에서 제외한 Holon 구성원을 복원

        Args:
            scene_id: scene_07-list tool에서 include_ids=true로 조회한 Scene ID
            object_ids: 일반 형상·클리핑 평면의 Rhino 객체 GUID, 최대 4096개.
            expected_model_path: 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
        """
        try:
            result = context.retrieval_store.change_scene_objects(scene_id, bound_model_path(expected_model_path),
                object_ids, True, observe, _observe)
            return json.dumps({"status": "success", **result})
        except Exception as exc:
            return component_error(exc)

    @public_tool(mcp, wrapped=True, errors=True)
    def remove_scene_objects(scene_id: str, object_ids: list[str], expected_model_path: str = "") -> str:
        """객체를 Scene에서 제외. Rhino 형상과 Holon 그룹은 보존.

        Args:
            scene_id: scene_07-list tool에서 include_ids=true로 조회한 Scene ID
            object_ids: 일반 형상·클리핑 평면의 Rhino 객체 GUID, 최대 4096개.
            expected_model_path: 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
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
        """현재 Rhino 문서에서 Scene의 직접 객체와 Holon 구성원 조회. Scene에서 제외한 구성원은 생략.

        Args:
            scene_id: scene_07-list tool에서 include_ids=true로 조회하거나 이전에 기록한 Scene ID
            field_groups: scope, state, geometry, audit, all 중 선택. 생략하거나 빈 배열을 주면 요약 조회
            limit: 1~200
            expected_model_path: 지정한 경로가 연결 문서와 일치해야 함
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
