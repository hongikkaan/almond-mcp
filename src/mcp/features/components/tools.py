"""Component MCP tools; register explicitly with the current server context."""
from almond_mcp.tool_response import error_payload
from almond_mcp.features.components.public_contract import holon_output
from almond_mcp.features.context.object_inputs import DictionaryFilter
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
        """물리적 요소와 관계를 Holon으로 등록하거나 갱신

        Args:
            name: 기존 Rhino 그룹을 연결할 때는 그룹의 정확한 이름과 일치해야 함
            object_ids: 최상위 Rhino 객체만 지정 가능하며 객체당 Holon 한 개. 생략하면 name과 일치하는 기존 그룹을 사용하고 빈 배열은 child_holon_ids가 있는 부모에만 허용
            expected_model_path: 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
            scene_ids: 새 Holon은 필수. 수정 시 생략하면 기존 Scene 연결 유지
            holon_id: 생략하면 새 Holon 등록
            rhino_group_id: 동명 Rhino 그룹을 구분할 때 사용
            child_holon_ids: 빈 배열은 기존 자식 분리, 생략은 유지. 자식당 부모 한 개만 허용하며 순환 금지
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
        """Holon의 등록 정보와 구성원 조회. live=true로 현재 Rhino 상태를 등록 정보와 대조하고 requires_sync로 동기화 필요 여부를 확인. recursive=true는 Rhino 블록 정의 경계는 유지하며 자손 Holon을 확장. include_ids=true일 때도 입력한 holon_id는 요약에서 생략.

        Args:
            holon_id: include_ids=true로 조회하거나 이전 등록 결과에서 확인한 Holon ID
            include_ids: 요청한 필드 그룹에 해당하는 ID만 포함
            field_groups: references, geometry, scope, audit, all 중 선택. 생략하거나 빈 배열을 주면 요약 조회
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
        """모델에서 저장된 Holon 등록 목록 조회. Scene을 지정하면 연결된 Holon을, 생략하면 기본으로 최상위 Holon을 조회. recursive=true는 자손을 포함하며 이 자손은 Scene에 직접 등록되지 않았을 수 있다. 현재 Rhino 구성원은 scene_05-get_holon tool에서 live=true로 조회.

        Args:
            expected_model_path: 관리형 세션에서 생략하면 연결된 모델 기준
            field_groups: references, geometry, scope, audit, all 중 선택. 생략하거나 빈 배열을 주면 요약 조회
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
        """현재 Rhino 구성원으로 Holon 등록 정보 갱신

        Args:
            expected_model_path: 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
            rhino_group_id: holon_id와 함께 지정해 현재 Rhino 그룹 GUID가 일치하는지 확인하는 용도
            holon_ids: holon_id 또는 rhino_group_id와 동시 지정 불가
            scene_id: holon_id, holon_ids, rhino_group_id와 동시 지정 불가
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
        """Holon 등록 해제. Rhino 형상과 그룹은 보존.

        Args:
            holon_id: 이 Holon을 참조하는 부모 Holon과 Plan의 관계를 먼저 해제
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
                                    review_id: str = "", choice: StrictInt | Literal["skip"] | None = None,
                                    user_text: list[dict] | None = None,
                                    user_dictionary: DictionaryFilter | None = None):
        """겹친 객체 쌍을 캡처해 비교하고 지정한 객체에서 겹친 부분을 제거. 검토 시 실제 카메라와 선택이 바뀐다. 완료 후에도 건너뛴 쌍은 남는다. 다음 쌍의 검사 미판정(assessment=incomplete)에는 대상·이유와 해당 검사에서 확인한 모델 공차·단위를 반환하며 null은 확인 불가를 뜻한다. 직전 수정이 이미 적용됐을 수 있으므로 previous_result와 실제 형상을 확인.

        Args:
            object_ids: 새 검토를 시작할 현재 최상위 객체의 서로 다른 GUID 1..512개. 이어서 검토하거나 선택을 제출할 때는 생략.
            include_block: 새 검토에 배치 변환을 적용한 중첩 블록 구성원 포함. 블록 정의 편집은 지원하지 않음.
            user_text: 새 검토 범위의 객체 속성 User Text 조건 배열. 예: [{"key":"floor","any_of":["2F"]}]. 한 객체가 모든 조건과 일치하는 쌍을 표시. 양쪽 값은 objects[].attributes.user_strings.values에서 확인. 중첩 블록에는 정의 구성원의 속성 적용.
            review_id: 비교 화면의 대상을 식별하는 반환 ID. choice 제출 시 필수. 완료됐거나 새 검토로 대체된 ID는 재사용 불가.
            user_dictionary: 새 검수에서 속성(attributes) 또는 형상(geometry)의 UserDictionary를 source, key, any_of 조건으로 필터링. 배열 값은 원소 하나라도 일치하면 통과. User Text도 지정하면 같은 객체가 두 필터를 모두 통과해야 쌍을 표시. 값은 objects[].user_dictionary에서 확인.
            choice: 1 또는 2: 해당 번호 객체에서 겹친 부분 제거. skip: 두 객체 유지. 선택 제출 시 review_id를 지정하고 object_ids는 생략. 검토만 하거나 이어갈 때는 choice 생략.
        """
        return intersection_workflow.execute(object_ids, include_block, review_id, choice, user_text, user_dictionary)

    @public_tool(mcp, wrapped=True, annotations={'destructiveHint': False})
    @holon_output
    def focus_holons(holon_ids: list[str], expected_model_path: str = "") -> str:
        """선택한 Holon과 하위 Holon의 유효 구성원을 Rhino에서 선택·격리·확대. 잠긴 주변 객체는 계속 보일 수 있다. Unisolate는 격리 전 표시 상태를 복원하며, 선택과 카메라 상태는 별도로 복원해야 할 수 있다.

        Args:
            holon_ids: 서로 다른 ID 1~32개. 유효 최상위 객체는 최대 4096개
            expected_model_path: 지정한 경로가 연결 문서와 일치해야 함
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
