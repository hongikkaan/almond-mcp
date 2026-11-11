"""Give the next useful action with the result that makes it actionable."""
import json
from almond_mcp.public_names import internal_tool_name, tool_references


REVISION_GUIDE = ("expected_revision 검사도 사용할 경우 plan_05-get tool의 request에 같은 target·ID·loop_no를 넣어 "
                  "조회한 최신 revision을 사용합니다. Loop가 바뀌었으면 기록 대상을 먼저 재검토합니다.")
EVIDENCE_LOOP_GUIDE = ("기록할 Step ID가 없으면 먼저 plan_08-list tool의 request에 target='step', 같은 plan_id·loop_no를 넣어 목록에서 Step을 선택합니다. "
                       "근거를 얻은 작업 맥락의 loop_no를 유지해 request.loop_no로 함께 전달합니다. "
                       + REVISION_GUIDE)


# These are successful, single-step suggestions. State/handle checks below take
# precedence; an error never inherits a success suggestion.
SUCCESS_GUIDES = {
    "execute_looping": ("저장된 수행·검증·보고 기록을 확인하고 미완료 Step이 있으면 set_working_plan으로 선택합니다. "
                        "완료한 작업은 반복하지 않고, 수행·검증 결과는 plan_12-update tool의 request에 target='step', plan_id, step_id와 기록할 필드를 넣어 갱신합니다. "
                        + EVIDENCE_LOOP_GUIDE + "\n"
                        "회차가 끝나면 목표·변경 내용·시각적 근거·검증 결과·남은 선택지를 보고합니다."),
    "set_working_plan": ("이 artifact_dir에서 작업하고, plan_12-update tool의 request에 target='step', plan_id, step_id와 "
                         "재사용한 파일은 input_refs.add, 새 산출물은 output_refs.add로 기록합니다. " + EVIDENCE_LOOP_GUIDE),
    "rename_artifact_folder": "이후 산출물 작업에는 갱신된 artifact_dir를 사용합니다.",
    "resolve_targets": "대상의 현재 구성원은 get_ontological_holon으로 확인합니다.",
    "get_selection_references": "관련 Plan은 plan_05-get tool의 request에 target='plan'과 plan_id를 넣어 확인합니다.",
    "analyze_block_reculviely": "블록 편집에 들어간 뒤에는 get_objects로 현재 편집 대상 ID를 다시 조회합니다.",
    "assign_material": "get_objects로 적용된 재료를 확인합니다.",
    "setup_modeling": "객체에 재료를 적용하려면 list_materials에서 선택한 재료를 assign_material에 사용합니다.",
    "edit_planar_face": "get_objects로 변경된 형상과 CRC를 다시 확인합니다.",
    "edit_planar_faces": "get_objects로 변경된 객체의 형상과 CRC를 다시 확인합니다.",
    "add_scene_objects": "get_scene_objects로 Scene의 현재 구성원을 확인합니다.",
    "remove_scene_objects": "get_scene_objects로 Scene의 현재 구성원을 확인합니다.",
    "create_design_scene": "객체를 포함하려면 add_scene_objects에 이 scene_id를 사용합니다.",
    "update_design_scene": "get_design_scene으로 변경된 Scene을 확인할 수 있습니다.",
    "get_design_scene": "현재 Rhino 구성원은 get_scene_objects로 조회합니다.",
    "upsert_ontological_holon": "get_ontological_holon으로 등록 결과와 현재 구성원을 확인합니다.",
    "sync_ontological_holon": "갱신된 구성원은 get_ontological_holon으로 확인할 수 있습니다.",
    "list_ontological_holons": "현재 구성원 확인에는 get_ontological_holon을 사용합니다.",
    "register_drawing_asset": "등록한 자산은 get_drawing_asset으로 확인합니다.",
    "refresh_asset": "갱신된 도면은 get_asset_drawing으로 확인합니다.",
    "place_drawing_asset": "get_objects와 캡처로 배치 위치·축척을 확인합니다.",
    "place_diagram_asset": "get_objects와 캡처로 배치 위치·축척을 확인합니다.",
    "get_drawing_recipe": "선택한 규칙을 문서에 적용하려면 apply_drawing_style을 사용합니다.",
    "list_library": "logic_names에서 선택한 이름을 get_logic_by_id에 입력합니다.",
    "get_logic_by_id": "캡슐 계약과 실행 감사가 확인된 경우 run_gh_definition으로 계산할 수 있습니다.",
    "run_gh_definition": "베이크한 형상이 있으면 get_objects와 캡처로 확인합니다.",
    "get_construction_guidance": "선택한 구법을 객체에 기록하려면 assign_material을 사용합니다.",
    "get_typology_narrative": "관련 구법은 get_construction_guidance로 비교할 수 있습니다.",
    "validate_structure": "문제 부재는 visualize_structure로 검토할 수 있습니다.",
    "visualize_structure": "판정을 검증 이력으로 남기려면 validate_structure를 사용합니다.",
    "get_blender_helper_script": "생성한 코드는 Blender에서 실행합니다. export 실행이 성공하면 얻은 계약을 import_asset_contract에 사용할 수 있습니다.",
    "import_asset_contract": "get_objects와 캡처로 가져온 형상·재료·배치를 확인합니다.",
    "publish_objects_to_chestnut": "Chestnut에서 게시 결과를 확인하고, 갱신할 때는 확인한 자산 ID를 재사용합니다.",
    "publish_to_chestnut": "Chestnut에서 게시 결과를 확인합니다.",
}
LIST_GUIDES = {
    "list_design_scenes": ("scenes", "선택한 scene_id로 get_design_scene을 조회합니다."),
}
ASSET_GUIDES = {
    "list_drawing_assets": "get_drawing_asset", "search_drawing_assets": "get_drawing_asset",
    "search_asset_repository": "get_drawing_asset", "get_drawing_asset": "place_drawing_asset",
    "list_diagram_assets": "get_diagram_asset", "search_diagram_assets": "get_diagram_asset",
    "get_diagram_asset": "place_diagram_asset", "list_drawing_recipes": "get_drawing_recipe",
}
EXECUTIONS = {"execute_rhino_script", "execute_project_python", "get_rhino_execution"}
CAPTURES = {"get_current_viewcapture", "get_defined_viewcapture", "capture_rhino_inspection"}


def next_step(name: str, value: dict, arguments: dict) -> str | None:
    """Choose from observed state, never from a tool's name alone on failure."""
    if name == "close_session":
        if value.get("status") in {"closing", "unconfirmed"}:
            return "같은 request_id로 close_session을 다시 호출해 보관된 결과를 조회합니다. 저장·종료를 다시 실행하지 않습니다. save_request_id가 있으면 get_rhino_execution으로 저장 결과도 확인할 수 있습니다."
        if value.get("status") in {"rejected", "save_failed"}:
            return "reason을 확인합니다. Rhino는 자동으로 다시 종료하지 않습니다. 문제를 해결한 뒤 종료하려는 경우 새 request_id로 close_session을 호출합니다."
        return None
    if name in EXECUTIONS and value.get("completed") is False and value.get("request_id"):
        return "이 request_id로 get_rhino_execution을 조회해 완료 여부를 확인합니다. 같은 코드를 다시 제출하지 않습니다."
    planning_record = name == "get_planning" and value.get("type") in {"phase", "plan", "step"}
    failed_status = value.get("status") in {"error", "failed", "unknown", "uncertain", "incomplete"}
    if (failed_status and not planning_record) or value.get("error"):
        return None
    if (value.get("mutation_state") in {"unknown", "pending", "uncertain"}
            or value.get("requires_reconciliation") or value.get("mutation_applied", False) is None):
        return None
    if name == "disconnect":
        if value.get("released") is not True or value.get("rhino_closed") is not False:
            return None
        return ("연결을 해제했으며 Rhino 창과 문서는 유지됩니다. 저장하고 Rhino까지 종료하려면 "
                "list_connections에서 해당 문서를 확인하고 connect로 다시 연결한 뒤 close_session을 호출합니다.")
    if name == "update_planning":
        if value.get("issues"):
            if arguments.get("target") in {"plan", "step"}:
                return ("issues에서 건너뛴 항목을 확인합니다. 같은 request.target·ID·loop_no를 유지하고 필요한 필드만 수정해 다시 요청합니다. "
                        + REVISION_GUIDE)
            return "issues에서 건너뛴 항목을 확인합니다. 같은 request.target·ID를 유지하고 필요한 필드만 수정해 다시 요청합니다."
        target = arguments.get("target")
        if target == "step":
            return "다음에 수행할 Step을 정했다면 set_working_plan으로 선택합니다."
        if target in {"phase", "plan"}:
            return f"plan_05-get tool의 request에 target='{target}'과 해당 {target}_id를 넣어 변경된 기록을 확인할 수 있습니다."
        return None
    if name == "create_planning":
        if arguments.get("target") == "phase":
            return "Plan을 추가하려면 plan_02-create tool의 request에 target='plan', title, goal과 반환된 phase_id를 입력합니다."
        return "plan_05-get tool의 request에 target='plan', 반환된 plan_id와 include_details=true를 넣어 자동 생성된 Step을 확인합니다."
    if name == "get_planning":
        if value.get("read_only"):
            if not arguments.get("include_details", False):
                return "과거 기록의 상세를 보려면 같은 request.target·ID·loop_no·revision을 유지하고 request.include_details=true로 다시 조회합니다."
            return "이 과거 기록은 읽기 전용입니다. 현재 작업을 조회하려는 경우 request.loop_no와 request.revision을 생략합니다."
        if not arguments.get("include_details", False):
            return "상세 내용이 필요하면 같은 request.target·ID에 request.include_details=true로 다시 조회합니다."
        if value.get("type") == "phase":
            return "plan_08-list tool의 request에 target='plan'과 이 id를 phase_id로 입력해 소속 Plan을 조회합니다."
        if value.get("type") == "plan":
            return "수행할 Step을 정했다면 set_working_plan으로 선택합니다. 새 회차는 execute_looping으로 시작합니다."
        return "이 Step을 수행하려면 plan_id와 id를 set_working_plan의 plan_id·step_id에 입력합니다."
    if name == "list_plan_revisions":
        if not value.get("revisions"):
            return None
        if arguments.get("step_id"):
            return "plan_05-get tool의 request에 target='step', 같은 plan_id·step_id와 선택한 loop_no·revision을 함께 입력합니다."
        return "plan_05-get tool의 request에 target='plan', 같은 plan_id와 선택한 loop_no·revision을 함께 입력합니다."
    if name == "list_planning":
        target = arguments.get("target")
        if target == "phase" and value.get("phases"):
            return "plan_05-get tool의 request에 target='phase'와 phase_id를 넣어 상세를 조회하거나, plan_08-list tool의 request에 target='plan'과 phase_id를 넣어 소속 Plan을 조회합니다."
        if target == "plan" and value.get("plans"):
            return "plan_05-get tool의 request에 target='plan', 선택한 plan_id와 include_details=true를 넣어 Step을 확인합니다."
        if target == "step" and value.get("steps"):
            return "plan_05-get tool의 request에 target='step', 이 plan_id와 선택한 step_id를 입력합니다. 같은 스냅샷을 상세 조회하려면 반환된 loop_no·revision과 include_details=true를 함께 넣습니다."
        return None
    if name == "list_connections":
        available = [t for t in value.get("targets", []) if t.get("model_path") and t.get("state") not in {"in_use", "unavailable", "closing"}]
        if available:
            return "targets에서 연결할 문서를 골라 connect에 host_id와 model_path를 입력합니다."
        if value.get("targets"):
            return "targets의 state와 reason을 확인해 연결할 수 없는 사유를 해소한 뒤 다시 조회합니다."
        return "연결할 Rhino의 저장된 문서에서 almondconnect를 실행한 뒤 목록을 다시 조회합니다."
    if name in {"connect", "start_session"}:
        if value.get("state") == "ready":
            return "연결된 문서가 의도한 문서인지 확인합니다. 프로젝트 정보는 project_info, 기존 작업은 plan_08-list tool의 request에 target='plan'을 넣어 조회합니다."
        if name == "start_session" and value.get("request_id"):
            return "같은 request_id와 model_path로 start_session을 다시 조회합니다."
        return "list_connections로 연결 상태를 확인합니다."
    if name == "list_design_scenes" and value.get("scenes") and not arguments.get("include_ids"):
        return "상세 조회에 쓸 scene_id가 필요하면 include_ids=true로 다시 조회합니다."
    if name == "get_rhino_context" and not any(k in value for k in ("document", "viewport", "named_views", "layouts", "viewports")):
        return None
    if name == "list_ontological_holons" and (not value.get("holons") or not arguments.get("include_ids")):
        return "상세 조회에 쓸 holon_id가 필요하면 include_ids=true로 다시 조회합니다." if value.get("holons") else None
    if name in LIST_GUIDES:
        key, guide = LIST_GUIDES[name]
        return guide if value.get(key) else None
    if name == "get_objects":
        if value.get("next_offset") is not None:
            if value.get("snapshot"):
                return "같은 조회 조건에서 offset=next_offset, expected_snapshot=snapshot으로 다음 페이지를 읽습니다."
            if arguments.get("expected_snapshot"):
                return "기존 expected_snapshot과 조회 조건을 유지하고 offset=next_offset으로 다음 페이지를 읽습니다."
            return None
        if any(row.get("face_page", {}).get("next_offset") is not None for row in value.get("objects", [])):
            return "같은 객체 ID와 geometry_crc를 유지하고 face_offset에 face_page.next_offset을 입력해 다음 면을 조회합니다."
        if value.get("complete") is False or not value.get("objects"):
            return None
        if any(row.get("id") and row.get("geometry_crc") is not None and row.get("faces") for row in value["objects"]):
            return "수정할 면을 선택했다면 같은 관찰의 객체 ID·face_index·geometry_crc를 면 수정 도구에 사용합니다."
        return None
    if value.get("complete") is False:
        return None
    if name == "set_working_plan" and not value.get("step_id"):
        return ("이 artifact_dir에서 작업하고, plan_08-list tool의 request에 target='step', 반환된 plan_id와 loop_no를 넣어 "
                "조회한 목록에서 기록할 Step을 선택합니다.")
    if name in CAPTURES:
        saved = value.get("image_file", {})
        if saved.get("status") == "saved" and saved.get("path") and saved.get("lifetime") == "plan":
            return ("보관할 이미지라면 plan_12-update tool의 request에 target='step', plan_id, step_id와 output_refs={add:[image_file.path]}를 입력합니다. "
                    + EVIDENCE_LOOP_GUIDE)
        return None
    if name in EXECUTIONS:
        page = value.get("result_page", {})
        if any(p.get("next_offset") is not None for p in page.get("pages", {}).values()):
            return "같은 request_id와 반환된 next_offset으로 get_rhino_execution에서 나머지 결과를 읽습니다."
        return None
    if name == "get_plan_section_result":
        return "같은 result_id와 next_offset으로 다음 페이지를 읽습니다." if value.get("next_offset") is not None else None
    if name == "list_capsules":
        if not value.get("capsules"):
            return None
        if not all("input_ports" in row for row in value["capsules"]):
            return "실행할 캡슐의 입력 타입·단위·필수 여부는 include_ids=true, field_groups=['ports']로 조회합니다."
        if any(row.get("capsule_id") and row.get("audited") for row in value["capsules"]):
            return "audited=true인 캡슐의 input_ports에 맞춰 inputs를 구성하고, capsule_id와 함께 run_gh_definition에 입력합니다."
        return None
    if name == "list_library" and not value.get("logic_names"):
        return None
    if name == "visualize_structure" and value.get("status") == "cleared":
        return None
    if name == "list_materials":
        if not value.get("materials"):
            return None
        return ("선택한 material_id를 assign_material에 입력합니다." if arguments.get("include_ids") else
                "재료를 적용하려면 include_ids=true로 재료 ID를 조회해 assign_material에 사용합니다.")
    if name == "capture_conditioning_pass":
        if value.get("errors") or value.get("frames_captured", 0) != value.get("frames_requested"):
            return None
        return ("프레임과 camera_json을 확인하고, plan_12-update tool의 request에 target='step', plan_id, step_id와 output_refs.add에 사용할 산출물 경로를 입력합니다. "
                + EVIDENCE_LOOP_GUIDE)
    if name == "check_egress":
        return "미달 항목의 배치·너비·경로를 수정하고 측정값을 갱신해 다시 검토합니다." if value.get("passed") is False else None
    if name == "apply_drawing_style":
        return "출력 검토에는 review_preparation의 설정을 확인합니다." if value.get("review_preparation") else None
    if name == "list_design_codes":
        if not value.get("profiles"):
            return None
        return ("선택한 기준 ID를 validate_structure 또는 visualize_structure에 사용합니다." if arguments.get("include_ids") else
                "기준을 적용하려면 include_ids=true로 설계 기준 ID를 조회합니다.")
    if name == "get_construction_guidance" and not value.get("systems"):
        return None
    if name == "get_typology_narrative" and not value.get("entries"):
        return None
    if name in ASSET_GUIDES:
        asset = value.get("asset", {})
        if isinstance(asset, dict) and internal_tool_name(asset.get("next_tool", "")) in {"prepare_drawing_asset", "refresh_asset"}:
            return None  # The selected asset already carries its required preparation.
        if isinstance(asset, dict) and asset.get("file_available") is False:
            return None
        # Retained IDs, not display names, are the next tool's inputs.
        data = value.get("results", value.get("assets", value.get("recipes", value.get("asset", value))))
        if not data:
            return None
        if arguments.get("include_ids") is False and not arguments.get("asset_id") and not arguments.get("recipe_id"):
            return "후속 조회에 사용할 ID가 필요하면 같은 조건에 include_ids=true로 다시 조회합니다."
        label = "레시피" if name == "list_drawing_recipes" else "자산"
        return f"선택한 {label}의 ID로 {ASSET_GUIDES[name]}을 호출할 수 있습니다."
    if name == "resolve_targets" and not value.get("holon_ids"):
        return None
    if name == "get_selection_references" and not value.get("plans"):
        return None
    return SUCCESS_GUIDES.get(name)


def guide_payload(name: str, payload: dict, arguments: dict | None = None) -> dict:
    name = internal_tool_name(name)
    arguments = arguments or {}
    if name in {"create_planning", "get_planning", "list_planning", "update_planning"}:
        request = arguments.get("request", {})
        # Pydantic models arrive from registered tools; dictionaries from direct
        # JSON consumers. Read fields without flattening nested patch objects.
        arguments = request if isinstance(request, dict) else vars(request)
    value = dict(payload)
    # Existing state-machine instructions carry exact action tokens and take
    # precedence. Publish one human guidance key instead of two overlapping ones.
    existing = value.pop("next_step", None)
    if existing and name != "list_planning":
        value.setdefault("next_step_guide", existing)
    if "next_step_guide" not in value:
        guide = next_step(name, value, arguments or {})
        if guide:
            value["next_step_guide"] = guide
    if isinstance(value.get("next_step_guide"), str):
        value["next_step_guide"] = tool_references(value["next_step_guide"])
    return value


def guide_result(name: str, result, arguments: dict):
    """Preserve transport, images and errors while adding result-specific prose."""
    if isinstance(result, str):
        try:
            value = json.loads(result)
        except (ValueError, TypeError):
            return result
        return json.dumps(guide_payload(name, value, arguments), ensure_ascii=False) if isinstance(value, dict) else result
    if isinstance(result, dict):
        return guide_payload(name, result, arguments)
    # Image-bearing ToolResult: preserve every binary/text block and metadata.
    from fastmcp.tools import ToolResult
    if not isinstance(result, ToolResult) or result.is_error:
        return result
    value = result.structured_content
    wrapped = isinstance(value, dict) and set(value) == {"result"} and isinstance(value["result"], str)
    if wrapped:
        try:
            payload = json.loads(value["result"])
        except ValueError:
            return result
    else:
        payload = value
    if not isinstance(payload, dict):
        return result
    updated = guide_payload(name, payload, arguments)
    serialized = json.dumps(updated, ensure_ascii=False)
    content = []
    for block in result.content:
        if block.type == "text":
            try:
                matches = json.loads(block.text) == payload
            except (ValueError, TypeError):
                matches = False
            if matches:
                block = block.model_copy(update={"text": serialized})
        content.append(block)
    return result.model_copy(update={"content": content, "structured_content": {"result": serialized} if wrapped else updated})
