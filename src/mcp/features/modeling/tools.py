"""Modeling policy, script execution, setup and material tools."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import query_output, validate_field_groups
from almond_mcp.features.modeling.output import GROUPS, project
from almond_mcp.tool_declarations import public_tool
from almond_mcp.managed_paths import bound_model_path
from pydantic import StrictBool, StrictFloat, StrictInt
import json
import uuid
from typing import Literal

from almond_mcp.features.modeling import face_edit, modeling_policy, modeling_setup
from almond_mcp.features.modeling import plan_section as section_operations


def register(mcp, context):
    """Register modeling tools against the current server execution context."""

    @public_tool(mcp, wrapped=True, errors=True)
    def plan_section(operation: Literal["Create", "Update", "Move"], clipping_ids: list[str],
                          points: dict[str, list[StrictFloat | StrictInt]] | None = None,
                          hatch: StrictBool = True, small_details: StrictBool = False,
                          near_width: StrictFloat | StrictInt = 0.09, far_width: StrictFloat | StrictInt = 0.04,
                          near_dark: StrictFloat | StrictInt = 80.0, far_dark: StrictFloat | StrictInt = 45.0,
                          include_attachments: StrictBool | None = None) -> str:
        """활성 모델 또는 현재 Worksession에 첨부된 파일의 클리핑 평면으로 단면선·가시 입면선과 선택적 해치를 활성 모델에 생성합니다. 첨부 형상이 필요하면 먼저 필요한 파일을 Worksession에 첨부한 뒤 include_attachments를 선택합니다. Update는 저장된 위치에서 도면을 다시 계산하므로 기존 도면의 수동 편집이 교체될 수 있습니다. Move는 기존 도면 객체의 GUID와 수동 편집을 유지하며 원점을 옮깁니다.

        응답에는 클리핑별 상태와 도면 객체 GUID, 실제 배치 평면이 포함됩니다. Create·Update에는 실제 계산에 들어간 원본 레이어와 객체 수, 숨김·잠금·첨부 입력의 처리 조건도 포함됩니다. 일부 완료 또는 취소 뒤에는 완료된 도면이 남을 수 있습니다.

        변경 도중 실패하면 각 항목의 recovery.attempts에 객체·속성·레이어의 복구 대상과 성공/실패를 보존합니다. 한 복구가 실패해도 나머지는 계속 시도합니다. tracked_changes_restored는 추적한 변경의 복구 결과이며 원자적 rollback을 보장하지 않습니다. mutation_state가 partial 또는 unknown이고 requires_reconciliation이 true이면 실제 도면을 확인하거나 Undo한 뒤 다음 작업을 결정하고 자동으로 재시도하지 마세요.

        Args:
            operation: Create는 생성 또는 교체, Update는 저장 위치에서 재생성, Move는 기존 도면의 평행이동.
            clipping_ids: 활성 모델 또는 현재 Worksession 첨부 파일의 클리핑 평면 GUID 목록. 비어 있을 수 없으며 중복은 한 번만 처리.
            points: 클리핑 GUID별 절대 도면 원점 [x,y] 또는 [x,y,z], 문서 단위. Create에서 선택, Move에서 모든 GUID에 필수, Update에서 생략.
            hatch: 해치 생성 허용. 원본 단면 스타일의 채움과 형상 조건을 따름. 기본 true.
            small_details: 작은 입면 상세를 보호할지 여부. 기본 false.
            near_width: 가까운 입면선 출력 두께(mm). 기본 0.09, 양수이며 far_width 이상.
            far_width: 먼 입면선 출력 두께(mm). 기본 0.04, 양수이며 near_width 이하.
            near_dark: 가까운 입면선 출력 농도 0..100%. 기본 80, far_dark 이상.
            far_dark: 먼 입면선 출력 농도 0..100%. 기본 45, near_dark 이하.
            include_attachments: true면 활성 모델과 현재 Worksession 첨부 형상을 계산합니다. false면 활성 모델 형상만 계산합니다. Create에서 기본 false, Update에서 생략하면 기존 도면의 설정을 사용합니다. Move는 배치만 변경합니다.
        """
        try:
            payload = section_operations.request(operation, clipping_ids, points, hatch, small_details,
                                                 near_width, far_width, near_dark, far_dark,
                                                 bound_model_path(), include_attachments=include_attachments)
        except (ValueError, TypeError, AttributeError, OverflowError) as exc:
            return json.dumps({**error_payload(str(exc), error_code="invalid_arguments"),
                               "mutation_state": "not_started"})
        return json.dumps(section_operations.dispatch(payload, context._send_and_receive), ensure_ascii=False)

    @public_tool(mcp, wrapped=True)
    def execute_rhino_script(script: str, language: str = "python",
                             timeout_seconds: StrictInt = 60) -> str:
        """연결된 RhinoCode에서 모델링·편집·측정 코드를 실행합니다. 전용 도구로 처리하기 어려운 작업에 사용합니다.

        Args:
            script: 동기식 Python 소스, C# 문장 본문 또는 명령 매크로입니다. Python은 JSON-safe 값을 result에, C#은 결과 JSON을 result_json에 할당합니다. doc은 연결된 문서입니다. command는 !·Pause·대화상자 없이 끝나는 매크로를 입력합니다.
            language: python(기본값 Python 3), python2, csharp, csharp-script 또는 command입니다. 모든 모드는 공식 RhinoCode를 사용합니다.
            timeout_seconds: 1-600의 정수이며 기본값은 60입니다. 실행 종료가 아닌 완료 근거 대기 한도입니다. beyond·CoS는 첫 대기를 최대 60초로 줄여 pending과 request_id를 먼저 반환할 수 있습니다. 미완료 응답은 같은 ID로 script_03-get_execution tool을 조회합니다.
        """
        if not isinstance(script, str) or not script.strip():
            return json.dumps(error_payload("script must be nonempty source or a command.",
                                            error_code="invalid_arguments"))
        if not isinstance(language, str) or language not in {"csharp", "python", "python2", "csharp-script", "command"}:
            return json.dumps(error_payload(
                "language must be csharp, python, python2, csharp-script or command.",
                error_code="invalid_arguments"))
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 600:
            return json.dumps(error_payload("timeout_seconds must be an integer from 1 to 600.",
                                            error_code="invalid_arguments"))
        execute = getattr(context, "_execute_rhinocode", None)
        if execute is None:
            return json.dumps({**error_payload(
                "RhinoCode execution requires a bound Almond runtime and StartScriptServer in its Rhino.",
                error_code="rhinocode_unavailable"), "mutation_state": "not_started"})
        # All public source runs in ScriptEditor. Private native recipes use
        # their own sender and are not callers of this public tool.
        return json.dumps(execute(script, "csharp-script" if language == "csharp" else language,
                                  timeout_seconds), ensure_ascii=False)


    @public_tool(mcp, wrapped=True, errors=True)
    def edit_planar_face(object_id: str, face_index: StrictInt, expected_geometry_crc: StrictInt,
                         translation: list[StrictFloat | StrictInt], expected_model_path: str = "") -> str:
        """닫힌 Brep의 평면 한 면을 PushPull Extend로 이동합니다. 그룹·블록 편집을 종료한 일반 모델에서 사용합니다. 현재 객체의 면 번호와 geometry_crc를 같은 관찰에서 얻어 입력합니다.

        result는 편집 결과 또는 오류를 담은 JSON 문자열입니다. 오류 응답에 mutation_state가 항상 포함되지는 않습니다.

        Args:
            object_id: 연결된 문서의 관찰 결과에서 얻은 현재 잠기지 않은 최상위 닫힌 Brep GUID입니다.
            face_index: expected_geometry_crc와 동일한 형상 관찰 결과에서 얻은 0부터 시작하는 평면 인덱스입니다.
            expected_geometry_crc: 해당 관찰 결과의 형상 CRC입니다. 형상이 변경되었으면 교체 전에 편집을 거부합니다.
            translation: 문서 단위의 유한한 XYZ 숫자 3개입니다. 면 법선 방향 성분이 문서 허용오차를 초과해야 합니다.
            expected_model_path: 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
        """
        try:
            payload = face_edit.request(object_id, face_index, expected_geometry_crc, translation,
                                        bound_model_path(expected_model_path))
        except (ValueError, TypeError, OverflowError) as exc:
            return json.dumps({**error_payload(str(exc), error_code="invalid_arguments"),
                               "mutation_state": "not_started"})
        return json.dumps(face_edit.dispatch(payload, context._send_and_receive), ensure_ascii=False)


    @public_tool(mcp, wrapped=True, errors=True)
    def edit_planar_faces(edits: list[dict], expected_model_path: str = "") -> str:
        """서로 다른 닫힌 Brep의 평면을 한 면씩 단일 Undo 기록으로 이동합니다. 그룹·블록 편집을 종료한 일반 모델에서 사용합니다. 각 객체의 면 번호와 CRC는 같은 형상 관찰에서 얻습니다.

        result는 배치 결과 또는 오류를 담은 JSON 문자열입니다. 준비 단계에서 한 항목이 거부되면 객체 교체를 시작하지 않습니다. 처리 상태와 항목별 결과는 mutation_state와 items에서 확인합니다.

        Args:
            edits: 서로 다른 Brep에 대한 항목 1..32개이며, 각 항목에는 object_id, face_index, expected_geometry_crc 및 translation이 들어갑니다. 단일 면 도구의 적용 대상 조건이 적용됩니다.
            expected_model_path: 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
        """
        try:
            payload = face_edit.batch_request(edits, bound_model_path(expected_model_path))
        except (ValueError, TypeError, OverflowError) as exc:
            return json.dumps({**error_payload(str(exc), error_code="invalid_arguments"),
                               "mutation_state": "not_started"})
        return json.dumps(face_edit.dispatch(payload, context._send_and_receive, batch=True), ensure_ascii=False)


    @public_tool(mcp, wrapped=True, annotations={'destructiveHint': False})
    def save_rhino_document() -> str:
        """연결된 문서 전체를 기존 .3dm 경로에 저장합니다. 사용자에게 영구 저장을 요청받은 경우 사용합니다."""
        try:
            model_path = bound_model_path()
            snapshot = json.loads(context._send_and_receive(json.dumps({
                "type": "get_rhino_context", "sections": [], "selection_limit": 0,
            }).encode("utf-8")))
            if not isinstance(snapshot, dict) or snapshot.get("status") != "success":
                raise ValueError("Could not verify the document-save capability.")
            if snapshot.get("capabilities", {}).get("document_save") != 1:
                return json.dumps({**error_payload(
                    "This Bridge does not support noninteractive document saving.",
                    error_code="unsupported_document_save"), "saved": False})
        except Exception as exc:
            return json.dumps({**error_payload(str(exc), error_code="save_not_started"), "saved": False})
        try:
            result = json.loads(context._send_and_receive(json.dumps({
                "type": "save_rhino_document", "expected_model_path": model_path,
            }).encode("utf-8")))
            if isinstance(result, dict) and result.get("status") == "error":
                return json.dumps(result, ensure_ascii=False)
            if (not isinstance(result, dict) or result.get("status") != "success"
                    or result.get("saved") is not True or type(result.get("modified")) is not bool):
                raise ValueError("The Bridge did not return a confirmed save result.")
            return json.dumps(result, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({**error_payload(str(exc), error_code="save_result_unconfirmed"),
                               "saved": None, "requires_reconciliation": True})


    @public_tool(mcp, wrapped=True)
    def setup_modeling(overwrite: StrictBool) -> str:
        """라이브러리의 표준 재료와 구축 시스템별 레이어를 연결된 Rhino 문서에 설정합니다. 재료를 등록하고 `M` 아래 분류·시스템·부재 역할별 레이어와 색·재료를 구성합니다.

        - **`overwrite=false`**: 없는 항목 생성, 기존 속성 유지 및 차이 보고.
        - **`overwrite=true`**: 없는 항목 생성, 기존 항목의 사전 정의 속성 갱신.

        반환 JSON의 `applied=true`는 기준과의 차이·오류가 없는 상태를 뜻합니다. 차이나 오류가 남으면 `incomplete`이며, 이 경우에도 일부 항목이 이미 생성·변경됐을 수 있습니다.

        객체별 재료 지정에는 `model_04-list_materials` tool과 `model_01-assign_material` tool을 사용합니다.

        Args:
            overwrite: Material과 Layer 모두에 적용되는 필수 불리언입니다. false는 기존 값을 유지하고, 없는 항목을 만들며, 차이를 보고합니다. true는 사전 정의된 속성을 갱신합니다.
        """
        try:
            code = modeling_setup.setup_script(context.material_library, context.construction_library, overwrite)
        except (KeyError, ValueError, IndexError, TypeError) as exc:
            return json.dumps({"status": "error", "mutation_state": "not_started", "message": str(exc)})
        result = modeling_setup.dispatch(code, context._send_and_receive, timeout=600.0, require_setup=True)
        return json.dumps(modeling_setup.setup_result(result), ensure_ascii=False)


    @public_tool(mcp, wrapped=True)
    @query_output
    def list_materials(category: str = "", query: str = "", include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        """라이브러리 재료를 이름·설명·태그 또는 분류로 찾습니다. 결과는 Rhino 문서에 이미 적용된 재료 목록이 아닙니다. 적용에 필요한 material_id는 include_ids=true로 조회합니다. result는 재료 목록 또는 오류를 담은 JSON 문자열입니다.

        Args:
            category: 분류 정확히 일치. 대소문자 구분; 생략 시 전체.
            query: 이름·설명·태그 검색. 대소문자 구분 없음.
            include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
            field_groups: 선택 사항인 상세 그룹: display, physical, metadata, source, paths, audit 또는 all. 생략하거나 비워 두면 요약을 조회합니다.
        """
        validate_field_groups(field_groups, GROUPS)
        materials = context.material_library.list(category=category, query=query)
        return json.dumps(project({
            "total": len(materials),
            "materials": materials,
            "library_dir": str(context.material_library.directory),
        }, field_groups))


    @public_tool(mcp, wrapped=True)
    def assign_material(
        guids: list[str],
        material_id: str,
        apply_render_material: bool = True,
        attach_metadata: bool = False,
        structural_role: str = "",
        construction_system: str = "",
        floor: str = "",
        construction_detail: str = "",
        construction_reference: dict | None = None,
    ) -> str:
        """Rhino 객체에 라이브러리 재료와 선택적인 구축 메타데이터를 적용합니다. 렌더 재료는 객체에 직접 지정되며 레이어는 바뀌지 않습니다. 중복 GUID는 하나로 처리합니다.

        반환 result는 적용 결과 또는 오류를 담은 JSON 문자열입니다. 실제 렌더 재료와 사용자 문자열은 Rhino 객체 속성에서 확인할 수 있습니다. inspect_02의 user_dictionary는 이 사용자 문자열과 같은 항목이 아닙니다.

        Args:
            guids: 할당할 현재 Rhino 객체 GUID입니다. 관찰 결과나 생성 결과를 재사용합니다.
            material_id: model_04-list_materials tool(include_ids=true)에서 얻은 라이브러리의 표준 재료 ID입니다.
            apply_render_material: true이면 지정된 객체에 표준 렌더 재료를 적용합니다.
            attach_metadata: true이면 Almond 재료/구축 메타데이터를 부착합니다. false이면 요청한 렌더 재료만 적용합니다.
            structural_role: 선택 사항인 구조 역할 메타데이터이며, attach_metadata와 함께 사용합니다.
            construction_system: 알려진 구축 시스템 ID입니다. attach_metadata=true일 때 사용합니다. construction_reference를 함께 지정하면 같은 시스템이어야 합니다.
            floor: 선택 사항인 층 레이블 메타데이터이며, attach_metadata와 함께 사용합니다.
            construction_detail: 선택 사항인 구축 상세 설명이며, attach_metadata와 함께 사용합니다.
            construction_reference: {"kind":"construction_system","id":"확인한 system_id"} 형식의 출처 참조입니다. attach_metadata=true일 때 사용합니다. construction_system도 지정하면 같은 시스템이어야 합니다.
        """
        material = context.material_library.get(material_id)
        if not material:
            known = ", ".join(sorted(context.material_library.materials)) or "none loaded"
            return json.dumps(error_payload(f"Unknown material_id: {material_id}. Known: {known}"))
        guid_list = []
        for value in guids:
            try:
                guid = str(uuid.UUID(str(value)))
                if guid not in guid_list:
                    guid_list.append(guid)
            except ValueError:
                return json.dumps(error_payload(f"Invalid Rhino object GUID: {value}"))
        if not guid_list:
            return json.dumps(error_payload("guids must not be empty."))

        warnings = []
        extra_strings: dict[str, str] = {}
        for name, value in (("floor", floor), ("construction_detail", construction_detail),
                            ("structural_role", structural_role), ("construction_system", construction_system)):
            if not isinstance(value, str):
                return json.dumps(error_payload(f"{name} must be a string."))
        if construction_reference is not None:
            if (not isinstance(construction_reference, dict)
                    or set(construction_reference) != {"kind", "id"}
                    or construction_reference.get("kind") != "construction_system"
                    or not isinstance(construction_reference.get("id"), str)
                    or not construction_reference["id"].strip()):
                return json.dumps(error_payload("construction_reference requires kind=construction_system and a known id."))
            if construction_system and construction_system != construction_reference["id"]:
                return json.dumps(error_payload("construction_system and construction_reference identify different sources."))
            construction_system = construction_reference["id"]
        if structural_role:
            extra_strings[modeling_policy.key("structural_role")] = structural_role
        if construction_system:
            system = context.construction_library.get(construction_system)
            if system is None:
                known = ", ".join(sorted(context.construction_library.systems)) or "none loaded"
                return json.dumps(error_payload(f"Unknown construction_system: {construction_system}. "
                               f"Known: {known}"))
            construction_reference = {"kind": "construction_system", "id": construction_system}
            construction_detail = construction_detail or system["name"]
            extra_strings[modeling_policy.key("construction_reference")] = json.dumps(construction_reference, ensure_ascii=True, separators=(",", ":"))
            typical = system.get("render_material_ids", [])
            if typical and material_id not in typical:
                warnings.append(
                    f"Material '{material_id}' is not a typical finish for "
                    f"{construction_system} (typical: {', '.join(typical)}). "
                    f"Applied anyway.")

        if floor:
            extra_strings[modeling_policy.key("floor")] = floor
        if construction_detail:
            extra_strings[modeling_policy.key("construction_detail")] = construction_detail
        script = modeling_setup.material_script(material, guid_list, apply_render_material,
                                  attach_metadata, extra_strings)
        response = modeling_setup.dispatch(script, context._send_and_receive)
        if response.get("status") != "success":
            return json.dumps(response)
        if response.get("result_error"):
            return json.dumps({**response, "material_id": material_id,
                               "message": 'Material assignment ran but its result could not be returned. Inspect Rhino before retrying.'})
        native = response.get("result")
        applied = native.get("applied_guids") if isinstance(native, dict) else None
        if (not isinstance(applied, list) or any(not isinstance(g, str) or g not in guid_list for g in applied)
                or len(applied) != len(set(applied)) or native.get("material_id") != material_id):
            return json.dumps({"status": "error", "error_code": "material_result_unavailable", "mutation_state": "unknown",
                               "message": 'Material assignment returned no valid applied-object result. Inspect Rhino before retrying.'})
        result = {
            "status": "success",
            "material_id": material_id,
            "rhino_material_name": material["name"],
            "ue_material_slot": material["ue_material_slot"],
            "applied_count": len(applied),
            "requested_count": len(guid_list),
            "applied_guids": applied,
            "metadata_attached": native.get("metadata_attached", attach_metadata and (apply_render_material or bool(extra_strings))),
            "material_metadata_attached": attach_metadata and apply_render_material,
            "render_material_applied": apply_render_material,
            "layer_path": native.get("layer_path"),
        }
        changed = native.get("changed_guids")
        if (isinstance(changed, list) and all(isinstance(g, str) and g in applied for g in changed)
                and len(changed) == len(set(changed))):
            result["changed_guids"] = changed
            result["changed_count"] = len(changed)
        if structural_role:
            result["structural_role"] = structural_role
        if construction_system:
            result["construction_system"] = construction_system
        if floor:
            result["floor"] = floor
        if construction_detail:
            result["construction_detail"] = construction_detail
        if construction_reference:
            result["construction_reference"] = construction_reference
        if warnings:
            result["warnings"] = warnings
        return json.dumps(result)


    return {
        "plan_section": plan_section,
        "execute_rhino_script": execute_rhino_script,
        "edit_planar_face": edit_planar_face,
        "edit_planar_faces": edit_planar_faces,
        "save_rhino_document": save_rhino_document,
        "setup_modeling": setup_modeling,
        "list_materials": list_materials,
        "assign_material": assign_material,
    }
