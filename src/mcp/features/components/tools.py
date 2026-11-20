"""Component MCP tools; register explicitly with the current server context."""
from almond_mcp.tool_response import error_payload
from almond_mcp.features.components.public_contract import holon_output
from almond_mcp.query_output import query_output, validate_field_groups
from almond_mcp.features.components.output import GROUPS, project
from almond_mcp.managed_paths import bound_model_path
from almond_mcp.tool_declarations import public_tool
from pydantic import StrictBool, StrictInt
from typing import Literal
import json


from almond_mcp.store_common import ComponentReconciliationError


def send_component_request(send, request: dict) -> dict:
    """Capability-check before one native operation; never retry an uncertain mutation."""
    payload = json.dumps(request, allow_nan=False).encode("utf-8")
    if len(payload) > 2_097_152:
        return {"status": "error", "mutation_applied": False, "message": "Component request exceeds 2 MiB."}
    try:
        rhino_context = json.loads(send(b'{"type":"get_rhino_context","selection_limit":0}'))
        if not isinstance(rhino_context, dict) or rhino_context.get("status") != "success":
            raise ValueError("Could not inspect the bound Rhino document.")
        if rhino_context.get("capabilities", {}).get("design_components") != 1:
            raise ValueError('Load a Bridge with design_components=1 before registering Holons.')
        if rhino_context.get("capabilities", {}).get("component_registry") != 2:
            raise ValueError("Load a Bridge with component_registry=2 before using object-free Component registration.")
        if (request.get("action") == "upsert" and request.get("object_ids") is None
                and rhino_context.get("capabilities", {}).get("component_group_inference") != 1):
            raise ValueError("Load a Bridge with component_group_inference=1 before omitting object_ids.")
    except Exception as exc:
        return {"status": "error", "mutation_applied": False, "message": str(exc)}
    response = send(payload)
    if len(response.encode("utf-8")) > 2_097_152:
        raise ValueError("Component response exceeds 2 MiB.")
    result = json.loads(response)
    if not isinstance(result, dict):
        raise ValueError("Invalid native Component response.")
    return result


def component_error(exc: Exception) -> str:
    result = error_payload(str(exc))
    result.update(getattr(exc, "native_result", {}))
    if isinstance(exc, ComponentReconciliationError):
        result.update(error_code="component_reconciliation_required", requires_reconciliation=True,
                      component_id=exc.component_id, expected_model_path=exc.model_path)
    return json.dumps(result, ensure_ascii=False)


def register(mcp, context):
    from almond_mcp.features.components.intersection_workflow import Workflow
    intersection_workflow = Workflow(context._send_and_receive)

    def observe(request):
        return send_component_request(context._send_and_receive, request)

    def _component_ack(component: dict) -> dict:
        return {key: component[key] for key in (
            "component_id", "rhino_group_id", "status", "availability", "object_count", "live_verified",
        ) if key in component}

    @public_tool(mcp, wrapped=True)
    @holon_output
    def upsert_ontological_holon(
        name: str,
        object_ids: list[str] | None = None,
        expected_model_path: str = "",
        scene_ids: list[str] | None = None,
        holon_id: str = "",
        rhino_group_id: str = "",
        child_holon_ids: list[str] | None = None,
    ) -> str:
        """물리적 요소와 관계를 Holon으로 등록하거나 갱신합니다.

        Args:
            name: 의미적 Holon 이름입니다. 기존 Rhino 그룹에 연결할 때는 해당 그룹의 정확한 이름과 일치해야 합니다.
            object_ids: 등록할 최상위 Rhino 객체 GUID 배열입니다. 각 객체는 하나의 Holon에 속합니다. 생략하면 name과 일치하는 기존 그룹을 사용합니다. []는 child_holon_ids가 있는 부모에만 사용합니다.
            expected_model_path: 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
            scene_ids: Holon이 속할 기존 Scene ID 배열입니다. 새 Holon에는 필수이며, 수정 시 생략하면 유지합니다.
            holon_id: 수정할 기존 Holon ID입니다. 선택 사항이며, 생략하면 등록을 생성합니다.
            rhino_group_id: 기존 Rhino 그룹의 정확한 GUID입니다. 선택 사항이며, 이름의 모호성을 해소하는 데 사용합니다.
            child_holon_ids: 등록된 자식 Holon 목록입니다. 선택 사항이며, []는 기존 자식을 분리하고 생략하면 유지합니다. 자식당 부모는 하나만 허용하고 계층 순환을 금지합니다.
        """
        try:
            component = context.retrieval_store.upsert_component(
                model_path=bound_model_path(expected_model_path), name=name, object_ids=object_ids,
                scene_ids=scene_ids, component_id=holon_id, rhino_group_id=rhino_group_id,
                native_apply=observe, child_component_ids=child_holon_ids,
            )
            return json.dumps({"status": "success", "component": _component_ack(component)}, ensure_ascii=False)
        except Exception as exc:
            return component_error(exc)

    @public_tool(mcp, wrapped=True, annotations={'readOnlyHint': True, 'destructiveHint': False}, errors=True)
    @query_output
    @holon_output
    def get_ontological_holon(holon_id: str, live: bool = False, include_ids: StrictBool = False,
                             recursive: StrictBool = False, field_groups: list[str] | None = None) -> str:
        """Holon의 등록 정보와 구성원을 조회합니다. 기본값은 저장된 정보이며, live=true는 현재 Rhino 그룹·형상을 조회하고 등록 정보와의 차이를 확인합니다. requires_sync는 동기화 필요 여부입니다.

        recursive=true는 자손 Holon을 포함한 유효 구성원을 확장합니다. 이는 Holon 계층이며 Rhino 블록 정의의 내부 확장이 아닙니다. result는 Holon 정보 또는 오류를 담은 JSON 문자열입니다. include_ids=true여도 입력한 holon_id는 요약에 반복 반환되지 않습니다.

        Args:
            holon_id: include_ids=true를 사용한 Holon 조회 또는 이전 등록 결과에서 얻은 등록된 Holon ID입니다.
            live: 기본 false. true: 현재 Rhino 구성원·형상 조회.
            include_ids: 기본 false. true: 요청 그룹에 해당하는 ID 포함.
            recursive: 기본 false. true: 자손 Holon 확장.
            field_groups: references, geometry, scope, audit, all. 생략·빈 배열: 요약.
        """
        validate_field_groups(field_groups, GROUPS)
        try:
            component = context.retrieval_store.get_component(
                holon_id, live=live, native_inspect=observe if live else None,
            )
            if component is None:
                raise KeyError(f"Unknown component_id: {holon_id}")
            if not recursive:
                component = {key: value for key, value in component.items()
                             if key not in {"effective_objects", "effective_object_ids"}}
            return json.dumps(project({"status": "success", "component": component}, field_groups), ensure_ascii=False)
        except Exception as exc:
            return json.dumps(project(json.loads(component_error(exc)), field_groups))

    @public_tool(mcp, wrapped=True, annotations={'readOnlyHint': True, 'destructiveHint': False})
    @query_output
    @holon_output
    def list_ontological_holons(expected_model_path: str = "", include_ids: StrictBool = False,
                               scene_id: str = "", recursive: StrictBool = False,
                               field_groups: list[str] | None = None) -> str:
        """모델에 등록된 Holon 목록을 조회합니다. Scene을 지정하면 연결된 Holon을 조회하며, recursive=true이면 그 자손도 포함합니다. 자손은 해당 Scene에 직접 등록되어 있지 않을 수 있습니다. Scene 미지정 시 기본 목록은 최상위 Holon입니다.

        목록은 저장된 등록 정보이며 현재 Rhino 구성원의 실시간 검증 결과가 아닙니다. 현재 구성원은 scene_05-get_holon tool의 live=true로 조회합니다. result는 목록 또는 오류를 담은 JSON 문자열입니다.

        Args:
            expected_model_path: 관리형 기본: 연결된 모델. 지정 경로에 등록된 Holon이 없으면 빈 목록.
            include_ids: 기본 false. true: 후속 호출용 ID 포함.
            scene_id: 생략·빈 문자열: Scene 필터 없음.
            recursive: 기본 false. true: 자손 포함.
            field_groups: references, geometry, scope, audit, all. 생략·빈 배열: 요약.
        """
        validate_field_groups(field_groups, GROUPS)
        try:
            components = context.retrieval_store.list_components(expected_model_path, scene_id=scene_id, recursive=recursive)
            return json.dumps(project({"status": "success", "components": components, "total": len(components),
                               "live_verified": False}, field_groups), ensure_ascii=False)
        except Exception as exc:
            return json.dumps(project(json.loads(component_error(exc)), field_groups))

    @public_tool(mcp, wrapped=True)
    @holon_output
    def sync_ontological_holon(holon_id: str = "", expected_model_path: str = "", rhino_group_id: str = "",
                              holon_ids: list[str] | None = None, scene_id: str = "") -> str:
        """Rhino의 현재 구성원을 읽어 Holon 등록 정보를 갱신합니다.

        Args:
            holon_id: 단일 대상의 상태 대조 및 정합성 확인에 사용할 등록된 Holon ID입니다. 선택 사항입니다.
            expected_model_path: 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
            rhino_group_id: holon_id와 함께 제공하는 선택 항목으로, 현재 Rhino 그룹 GUID의 일관성을 확인합니다. 이 값만으로 그룹을 선택하거나 연결 대상을 바꾸지 않습니다.
            holon_ids: 명시적 Holon ID 일괄 목록입니다. 선택 사항이며, 단일 Holon/그룹 선택자와 함께 사용하지 않습니다.
            scene_id: 구성원을 갱신할 Scene ID입니다. holon_id, holon_ids, rhino_group_id와 함께 입력하지 않습니다.
        """
        try:
            if holon_id and holon_ids is not None:
                raise ValueError("Use component_id or component_ids, not both.")
            if scene_id and (holon_id or holon_ids is not None):
                raise ValueError("Use a Component target or a Scene scope, not both.")
            if rhino_group_id:
                rhino_group_id = context.retrieval_store._component_guid(rhino_group_id)
                existing = context.retrieval_store.get_component(holon_id)
                if not holon_id or (existing and existing["rhino_group_id"] != rhino_group_id):
                    raise ValueError("The supplied group GUID does not match the existing Component binding.")
            result = context.retrieval_store.align_components(
                model_path=bound_model_path(expected_model_path),
                component_ids=[holon_id] if holon_id else holon_ids,
                scene_id=scene_id, native_inspect=observe,
                expected_groups={holon_id: rhino_group_id} if rhino_group_id else None)
            if holon_id:
                component = context.retrieval_store.get_component(holon_id)
                failed = any(isinstance(problem, dict) and problem.get("component_id") == holon_id
                             for problem in result["problems"])
                if component and not failed:
                    result["component"] = _component_ack(dict(component, live_verified=True))
            return json.dumps(result, ensure_ascii=False)
        except Exception as exc:
            return component_error(exc)

    @public_tool(mcp, wrapped=True, annotations={'destructiveHint': False})
    @holon_output
    def remove_ontological_holon(holon_id: str) -> str:
        """Holon 등록을 해제하고 Rhino 형상과 그룹은 유지합니다.

        Args:
            holon_id: 등록을 해제할 Holon ID입니다. 이 Holon을 참조하는 부모 Holon과 Plan의 관계를 먼저 해제합니다.
        """
        try:
            component = context.retrieval_store.unregister_component(holon_id, native_apply=observe)
            return json.dumps({"status": "success", "component": _component_ack(component)}, ensure_ascii=False)
        except Exception as exc:
            return component_error(exc)

    def _component_operation_bridge(action: str, expected_model_path: str,
                                    component_ids: list[str], max_pairs: int = 64,
                                    include_blocks: bool = False, cursor: str = "") -> str:
        """Verify the advertised native helper before dispatching one bounded request."""
        try:
            model_path = context.retrieval_store._component_model_path(bound_model_path(expected_model_path))
            if (not isinstance(component_ids, list) or not 1 <= len(component_ids) <= 32
                    or any(not isinstance(value, str) or not value.strip() for value in component_ids)
                    or len(set(component_ids)) != len(component_ids)):
                raise ValueError("component_ids must contain 1 to 32 distinct Component handles.")
            if type(max_pairs) is not int or not 1 <= max_pairs <= 64:
                raise ValueError("max_pairs must be an integer between 1 and 64.")
            if type(include_blocks) is not bool or not isinstance(cursor, str) or len(cursor) > 256:
                raise ValueError("include_blocks must be boolean and cursor a string of at most 256 characters.")
            request = {"type": "component_operation", "action": action,
                       "expected_model_path": model_path, "component_ids": component_ids}
            if action == "intersections":
                request["max_pairs"] = max_pairs
                if include_blocks:
                    request["include_blocks"] = True
                if cursor:
                    request["cursor"] = cursor
            payload = json.dumps(request, allow_nan=False).encode("utf-8")
            if len(payload) > 262144:
                raise ValueError("Component operation request exceeds 256 KiB.")
        except (ValueError, TypeError, KeyError) as exc:
            return json.dumps({"status": "error", "error_code": "invalid_arguments",
                               "mutation_applied": False, "message": str(exc)})
        try:
            rhino_context = json.loads(context._send_and_receive(b'{"type":"get_rhino_context","selection_limit":0}'))
            if not isinstance(rhino_context, dict) or rhino_context.get("status") != "success":
                raise ValueError("Could not inspect the bound Rhino document.")
            if rhino_context.get("capabilities", {}).get("component_operations") != 1:
                raise ValueError('Load a Bridge with component_operations=1 before using Holon helpers.')
            if action == "intersections" and rhino_context.get("capabilities", {}).get("intersection_queries") != 1:
                raise ValueError("Load a Bridge with intersection_queries=1 before inspecting Meshes or block occurrences.")
        except Exception as exc:
            return json.dumps({"status": "error", "error_code": "unsupported_component_operations",
                               "mutation_applied": False, "message": str(exc)})
        # After this point a focus timeout cannot certify that Rhino was not changed.
        try:
            response = context._send_and_receive(payload)
            if len(response.encode("utf-8")) > 262144:
                raise ValueError("Component operation response exceeds 256 KiB.")
            result = json.loads(response)
            if not isinstance(result, dict):
                raise ValueError("Native Component helper returned a non-object response.")
            return json.dumps(result, ensure_ascii=False)
        except Exception as exc:
            uncertainty = action == "focus"
            return json.dumps({"status": "error", "error_code": "component_operation_bridge_error",
                               "message": str(exc), "requires_reconciliation": uncertainty,
                               "mutation_applied": None if uncertainty else False})

    @public_tool(mcp, wrapped=False)
    def resolve_object_intersection(object_ids: list[str] | None = None, include_block: StrictBool = False,
                                    review_id: str = "", choice: StrictInt | Literal["skip"] | None = None):
        """겹친 객체 쌍을 이미지로 검토하고 선택한 객체에서 겹친 부분을 제거합니다. 검토 시 실제 카메라와 선택이 바뀝니다.

        choice=1 또는 2는 해당 객체를 잘라내고 skip은 두 객체를 유지합니다. 완료 상태라도 건너뛴 쌍은 남습니다. 수정 후 다음 쌍을 계산하는 과정에서 오류가 나더라도 직전 수정이 적용됐을 수 있습니다. 응답의 previous_result와 실제 형상 상태를 확인합니다.

        Args:
            object_ids: 검토 범위를 시작할 서로 다른 현재 최상위 객체 GUID 1..512개입니다. 선택 사항이며, 현재 범위를 이어서 검토하거나 선택을 제출할 때는 생략합니다.
            include_block: 새 검토 범위에 변환이 적용된 중첩 블록 구성원을 포함합니다. 기본값은 false입니다. 블록 정의 편집은 여전히 지원하지 않습니다.
            review_id: 반환된 결정 핸들로, choice와 함께 사용할 때 필수입니다. 화면에 표시된 연산 대상을 식별합니다. 완료되었거나 새 검토로 대체된 핸들로는 변경을 다시 실행할 수 없습니다.
            choice: 1 또는 2는 해당 번호의 객체에서 겹친 부분을 제거합니다. "skip"은 두 객체를 모두 그대로 둡니다. review_id를 제공하고 object_ids는 생략합니다. 확인/계속 진행하려면 choice를 생략합니다.
        """
        return intersection_workflow.execute(object_ids, include_block, review_id, choice)

    @public_tool(mcp, wrapped=True, annotations={'destructiveHint': False})
    @holon_output
    def focus_holons(holon_ids: list[str], expected_model_path: str = "") -> str:
        """선택한 Holon과 하위 Holon의 현재 유효 구성원을 Rhino에서 선택·격리·확대합니다. 잠긴 주변 객체는 보일 수 있습니다. Unisolate로 격리 전 표시 상태를 복원할 수 있지만, 선택과 카메라는 별도로 변경된 상태로 남을 수 있습니다.

        result는 선택된 객체와 격리·확대 결과 또는 오류를 담은 JSON 문자열입니다.

        Args:
            holon_ids: 서로 다른 Holon ID 1~32개. 유효 최상위 객체 최대 4096개.
            expected_model_path: 생략: 연결된 문서. 지정 시 연결 문서와 일치해야 함.
        """
        return _component_operation_bridge("focus", expected_model_path, holon_ids)

    return {
        "upsert_ontological_holon": upsert_ontological_holon,
        "get_ontological_holon": get_ontological_holon,
        "list_ontological_holons": list_ontological_holons,
        "sync_ontological_holon": sync_ontological_holon,
        "remove_ontological_holon": remove_ontological_holon,
        "_component_operation_bridge": _component_operation_bridge,
        "resolve_object_intersection": resolve_object_intersection,
        "focus_holons": focus_holons,
    }
