"""Modeling policy, script execution and material tools."""
from almond_mcp.tool_response import error_payload, script_result
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
                          include_attachments: StrictBool | None = None,
                          section_width_source: Literal["source", "output_layer"] = "source") -> str:
        """활성 모델이나 Worksession 첨부 파일의 클리핑 평면에서 단면선·가시 입면선·해치를 생성. Update는 저장 위치에서 다시 계산해 수동 편집을 교체할 수 있고, Move는 GUID와 수동 편집을 유지한 채 원점만 이동.

        Rhino는 작업 시작 120초에 취소를 요청한다. 안전한 지점에서 중단하고 Undo와 정리를 마치면 timeout 및 클리핑별 결과를 반환한다. 완료된 도면은 남는다. SDK 호출 또는 정리 중 클라이언트 대기가 끝나면 중단 여부는 미확인이다. 변경 실패 시 객체·속성·레이어 복구 시도는 recovery.attempts에 기록하며 tracked_changes_restored는 추적한 변경의 복구 결과다. requires_reconciliation=true이면 실제 도면과 Undo 상태를 확인하고 자동 재시도하지 않는다.

        Args:
            operation: Create: 생성 또는 교체. Update: 저장 위치에서 재생성. Move: 기존 도면의 평행이동.
            clipping_ids: 활성 모델 또는 Worksession 첨부 파일의 클리핑 평면 GUID. 최소 1개, 중복은 한 번만 처리.
            points: 클리핑 GUID별 절대 도면 원점 [x,y] 또는 [x,y,z], 문서 단위. Create에서 선택, Move에서 모든 GUID에 필수, Update에서 생략.
            hatch: 원본 단면 스타일의 채움과 형상 조건에 따라 해치 생성
            small_details: 입면 투영에서 작은 상세 보호
            near_width: 가까운 입면선 두께(mm). 양수, far_width 이상.
            far_width: 먼 입면선 두께(mm). 양수, near_width 이하.
            near_dark: 가까운 입면선 농도(%). 0..100, far_dark 이상.
            far_dark: 먼 입면선 농도(%). 0..100, near_dark 이하.
            section_width_source: 단면선의 인쇄 선폭 기준. source는 원본의 유효 선폭, output_layer는 D::PlanSection::Section 레이어의 선폭. Move에는 적용되지 않음.
            include_attachments: Worksession 첨부 형상 포함. Create에서 생략하면 활성 모델만, Update에서 생략하면 저장된 설정 사용. Move에는 적용되지 않음.
        """
        try:
            payload = section_operations.request(operation, clipping_ids, points, hatch, small_details,
                                                 near_width, far_width, near_dark, far_dark,
                                                 bound_model_path(), include_attachments=include_attachments,
                                                 section_width_source=section_width_source)
        except (ValueError, TypeError, AttributeError, OverflowError) as exc:
            return json.dumps({**error_payload(str(exc), error_code="invalid_arguments"),
                               "mutation_state": "not_started"})
        return json.dumps(section_operations.dispatch(payload, context._send_and_receive), ensure_ascii=False)

    @public_tool(mcp, wrapped=True)
    def execute_rhino_script(script: str, language: str = "python",
                             timeout_seconds: StrictInt = 60) -> str:
        """연결된 RhinoCode에서 모델링·편집·측정 코드 또는 명령 매크로 실행. 실행 완료만 기록할 때는 출력 또는 반환값에 executed를 사용하고, 작업 결과는 result와 mutation_state에서 확인한다. 완료가 불확실하면 반환된 request_id로 script_03-get_execution tool을 조회하고, 같은 변경을 다시 실행하기 전에 문서 상태를 확인한다.

        Args:
            script: 동기식 Python 소스, C# 문장 본문 또는 명령 매크로. Python은 JSON 호환 값을 result에, C#은 JSON을 result_json에 할당. doc은 연결된 문서. command는 !·Pause·대화상자 없이 종료되는 매크로
            language: python(Python 3), python2, csharp, csharp-script, command 중 선택.
            timeout_seconds: 완료 근거 대기 한도 1~600초. beyond·CoS는 첫 대기 최대 60초 후 pending과 request_id를 반환할 수 있음.
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
        """닫힌 Brep의 평면 한 면을 PushPull Extend로 이동. 그룹·블록 편집을 종료한 일반 모델에서 사용. 현재 객체의 면 번호와 geometry_crc를 같은 관찰에서 가져온다. 일부 오류 응답에는 mutation_state가 없을 수 있다.

        Args:
            object_id: 연결 문서에서 관찰한 잠기지 않은 최상위 닫힌 Brep의 GUID
            face_index: 같은 형상 관찰에서 얻은 평면 인덱스. 0부터 시작.
            expected_geometry_crc: 면 번호와 같은 관찰에서 얻은 형상 CRC. 형상이 바뀌면 객체 교체 전에 거부.
            translation: 문서 단위의 유한한 XYZ 값 3개. 면 법선 방향 성분의 절댓값은 문서 허용오차를 넘어야 한다.
            expected_model_path: 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
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
        """서로 다른 닫힌 Brep의 평면을 한 면씩 단일 Undo 기록으로 이동. 그룹·블록 편집을 종료한 일반 모델에서 사용. 객체별 면 번호와 CRC는 같은 관찰에서 가져온다. 준비 단계에서 한 항목이 거부되면 객체 교체를 시작하지 않는다.

        Args:
            edits: 서로 다른 Brep에 대한 항목 1..32개. 각 항목에 object_id, face_index, expected_geometry_crc, translation을 지정하며 model_02-edit_planar_face tool과 동일한 조건 적용.
            expected_model_path: 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
        """
        try:
            payload = face_edit.batch_request(edits, bound_model_path(expected_model_path))
        except (ValueError, TypeError, OverflowError) as exc:
            return json.dumps({**error_payload(str(exc), error_code="invalid_arguments"),
                               "mutation_state": "not_started"})
        return json.dumps(face_edit.dispatch(payload, context._send_and_receive, batch=True), ensure_ascii=False)


    @public_tool(mcp, wrapped=True, annotations={'destructiveHint': False})
    def save_rhino_document() -> str:
        """사용자의 영구 저장 요청에 따라 연결된 문서 전체를 기존 .3dm 경로에 저장"""
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
    @query_output
    def list_materials(category: str = "", query: str = "", include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        """라이브러리에서 이름·설명·태그나 분류로 재료 검색. model_01-assign_material tool에 사용할 material_id는 include_ids=true로 조회.

        Args:
            category: 분류와 정확히 일치, 대소문자 구분. 생략하면 전체 분류.
            query: 이름·설명·태그 검색. 대소문자 구분 없음.
            field_groups: display, physical, metadata, source, paths, audit, all. 생략·빈 배열이면 요약.
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
        """Rhino 객체에 라이브러리 렌더 재료와 선택적 구축 메타데이터 지정. 렌더 재료를 적용하면 지정한 객체를 해당 재료의 레이어로 옮겨 ByLayer로 지정한다. 중복 GUID는 한 번만 처리. 메타데이터는 inspect_02-get_objects tool에서 fields=["user_text"]로 읽거나 filters.user_text로 검색.

        success는 전체 처리, partial은 일부 처리. executed는 적용한 객체가 없거나 적용 결과를 읽지 못한 상태. 결과 확인이 안 된 경우 재시도 전에 Rhino에서 대상 객체 확인.

        Args:
            guids: 현재 Rhino 객체의 GUID. 관찰 또는 생성 결과에서 가져온 값.
            material_id: model_04-list_materials tool에서 include_ids=true로 조회한 표준 재료 ID
            apply_render_material: true면 재료 전용 레이어(기본 M::<category>::<material_id>)에 배치한다. layer_settings는 새 레이어에만 적용한다. false면 객체 레이어와 재료를 유지한다.
            attach_metadata: Almond 재료·구축 메타데이터를 객체 속성에 기록
            structural_role: attach_metadata=true일 때 기록할 구조 역할
            construction_system: 라이브러리에서 확인한 구축 시스템 ID. attach_metadata=true일 때 기록하며 construction_reference와 함께 지정하면 동일한 시스템 필요.
            floor: attach_metadata=true일 때 기록할 층 레이블
            construction_detail: attach_metadata=true일 때 기록할 구축 상세
            construction_reference: {"kind":"construction_system","id":"확인한 system_id"} 형식. attach_metadata=true일 때 기록하며 construction_system을 함께 지정하면 동일한 시스템 필요.
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
            extra_strings["structural_role"] = structural_role
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
                    f"{construction_system} (typical: {', '.join(typical)}).")

        if floor:
            extra_strings[modeling_policy.key("floor")] = floor
        if construction_detail:
            extra_strings[modeling_policy.key("construction_detail")] = construction_detail
        try:
            script = modeling_setup.material_script(material, guid_list, apply_render_material,
                                                   attach_metadata, extra_strings)
        except ValueError as exc:
            return json.dumps(error_payload(str(exc)))
        response = modeling_setup.dispatch(script, context._send_and_receive,
                                           require_material_layer=apply_render_material)
        if response.get("status") != "success":
            return json.dumps(response)
        if response.get("result_error"):
            return json.dumps({**script_result(response), "material_id": material_id,
                               "message": 'Material assignment ran but its result could not be returned. Inspect Rhino before retrying.'})
        native = response.get("result")
        applied = native.get("applied_guids") if isinstance(native, dict) else None
        if (not isinstance(applied, list) or any(not isinstance(g, str) or g not in guid_list for g in applied)
                or len(applied) != len(set(applied)) or native.get("material_id") != material_id):
            return json.dumps({"status": "error", "error_code": "material_result_unavailable", "mutation_state": "unknown",
                               "message": 'Material assignment returned no valid applied-object result. Inspect Rhino before retrying.'})
        layer_path, layer_action, layer_changed = None, "not_applied", []
        if apply_render_material:
            layer_path = native.get("layer_path")
            layer_action = native.get("layer_action")
            layer_changed = native.get("layer_changed_guids")
            expected_path = modeling_policy.material_layer(material)["path"]
            changed = native.get("changed_guids")
            actual = layer_path.casefold().split("::") if isinstance(layer_path, str) else []
            expected = expected_path.casefold().split("::")
            if (len(actual) != 3 or not actual[-1] or actual[:2] != expected[:2]
                    or layer_action not in ("created", "reused")
                    or (layer_action == "created" and actual != expected)
                    or native.get("render_material_applied") is not True
                    or not isinstance(layer_changed, list) or not isinstance(changed, list)
                    or any(not isinstance(g, str) or g not in applied or g not in changed for g in layer_changed)
                    or len(layer_changed) != len(set(layer_changed))):
                return json.dumps({"status": "error", "error_code": "material_layer_result_unavailable",
                                   "mutation_state": "unknown",
                                   "message": "Could not confirm material layer assignment. Inspect Rhino before retrying."})
        status = "success"
        if not applied:
            status = "executed"
        elif len(applied) < len(guid_list):
            status = "partial"
        result = {
            "status": status,
            "material_id": material_id,
            "rhino_material_name": material["name"],
            "ue_material_slot": material["ue_material_slot"],
            "applied_count": len(applied),
            "requested_count": len(guid_list),
            "applied_guids": applied,
            "metadata_attached": native.get("metadata_attached", attach_metadata and (apply_render_material or bool(extra_strings))),
            "material_metadata_attached": attach_metadata and apply_render_material,
            "render_material_applied": apply_render_material,
            "layer_path": layer_path,
            "layer_action": layer_action,
            "layer_changed_guids": layer_changed,
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
        "list_materials": list_materials,
        "assign_material": assign_material,
    }
