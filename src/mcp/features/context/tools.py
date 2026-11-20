"""Live Rhino observations and local retrieval diagnostics."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import query_output
from almond_mcp.managed_paths import bound_model_path
from almond_mcp.tool_declarations import public_tool
from almond_mcp.features.context import object_queries
from almond_mcp.features.context.capture_artifacts import save_png

import base64
import io
import json
import math

from fastmcp.tools import ToolResult
from mcp.types import ImageContent, TextContent
from PIL import Image as PillowImage
from pydantic import StrictBool, StrictInt


def _observation_result(serialized: str) -> str | ToolResult:
    """Keep the wrapped-string schema while marking explicit observation errors."""
    value = json.loads(serialized)
    if isinstance(value, dict) and value.get("status") == "error":
        return ToolResult(content=[TextContent(type="text", text=serialized)],
                          structured_content={"result": serialized}, is_error=True)
    return serialized


def register(mcp, context):
    """Register observation tools using the server's current connection and state."""


    @public_tool(mcp, wrapped=True, annotations={'readOnlyHint': True, 'destructiveHint': False})
    def get_rhino_context(sections: list[str] | None = None, include_ids: StrictBool = False,
                          include_editor_details: StrictBool = False) -> str | ToolResult:
        """연결된 Rhino 문서·뷰·편집 상태와 저장된 Named View·Layout·레이어 계층·표시 모드를 조회합니다.

        - `document`: 단위·공차·변경 여부·객체와 레이어 수
        - `viewport` / `viewports`: 활성 화면의 카메라·투영·표시 모드 / 뷰포트 목록
        - `editor`: 편집 모드와 안정성
        - `named_views` / `layouts` / `display_modes`: 저장된 뷰·용지·표시 모드 목록. 목록마다 최대 128개이며 일부만 반환하면 warnings에 표시합니다.
        - `layer_tree`: 삭제되지 않은 모든 레이어의 이름과 계층. 깊이당 공백 두 칸으로 들여쓰며 레이어가 없으면 빈 문자열, 조회 실패 시 null입니다.

        **Named View·Layout·표시 모드 목록의 ID**는 `include_ids`와 무관하게 반환됩니다. 화면 이미지 캡처는 `capture_03-current_view` tool을 사용합니다.

        Args:
            sections: document, viewport, editor, viewports, named_views, layouts, layer_tree, display_modes 중 선택.
                생략 또는 null은 document, named_views, layouts, layer_tree, display_modes. []는 status와 warnings만.
            include_ids: viewport 등에서 ID 포함. 기본 false.
            include_editor_details: editor 요청 시 공급자·명령·Undo 근거 포함. 기본 false.
        """
        from almond_mcp.features.context.context_query import query
        return _observation_result(query(context._send_and_receive, sections, include_ids, include_editor_details))


    @public_tool(mcp, wrapped=True, annotations={'readOnlyHint': True, 'destructiveHint': False}, errors=True)
    @query_output
    def analyze_block_reculviely(mode: str, options: dict, expected_model_path: str = "", include_ids: StrictBool = False) -> str:
        """중첩 블록 구조와 특정 배치 경로의 공유 정의 영향을 조회합니다. 읽기 전용입니다.

        - outline: 기본적으로 선택된 루트의 요약. ids·path·scope로 대상을 정하고 field_groups로 상세를 선택합니다.
        - resolve-block: 루트부터 대상 블록까지의 path로 정의의 공유 배치와 참조·링크 제한을 확인합니다.
        - truncated·depth_limited: 조회 범위의 제한. definition_impact의 complete는 영향 범위 계수 완료 여부, occurrences_truncated는 반환 목록의 잘림 여부입니다.
        - 정의 내부 ID는 현재 편집 가능한 문서 객체 ID와 다를 수 있습니다. 후속 호출에 ID가 필요하면 include_ids=true를 사용합니다.

        Args:
            mode: outline | resolve-block
            options: outline: ids 또는 path. 생략 시 scope=selected(기본)|viewport|document.
                depth 0..64(기본 64), max_items 1..5000(기본 200), max_bytes 2048..262144(기본 48000).
                field_groups: summary(기본), objects, annotations, transforms 중 선택.
                include_geometry, annotations, annotation_layer: 형상·주석 출력 및 TextDot 레이어 필터.
                field_groups 생략 + include_geometry 또는 annotations 지정: legacy 상세 모드.
                resolve-block: path에 최상위부터 목표 블록까지 GUID 1..65개.
            expected_model_path: 생략: 연결 문서. 지정 시 경로 일치 검사.
            include_ids: 기본 false.
        """
        try:
            expected_model_path = bound_model_path(expected_model_path)
        except ValueError as exc:
            return json.dumps(error_payload(str(exc), error_code="invalid_arguments"))
        if (mode not in ("outline", "resolve-block")
                or not isinstance(options, dict) or not isinstance(expected_model_path, str)
                or not expected_model_path.strip()):
            return json.dumps(error_payload(
                "outline or resolve-block, an options object and expected_model_path are required.",
                error_code="invalid_arguments",
            ))
        fields = options.get("field_groups")
        if mode == "outline" and "field_groups" in options and (
                not isinstance(fields, list) or not fields or
                any(not isinstance(group, str) or group not in ("summary", "objects", "annotations", "transforms") for group in fields)):
            return json.dumps(error_payload(
                "outline field_groups must be a nonempty array of summary, objects, annotations or transforms.",
                error_code="invalid_arguments"))
        try:
            payload = json.dumps({"type": "analyze_block_reculviely", "mode": mode, "options": options,
                                  "expected_model_path": expected_model_path}, allow_nan=False).encode("utf-8")
            if len(payload) > 262144:
                raise ValueError("Block analysis request exceeds 256 KiB; narrow the request.")
        except (TypeError, ValueError) as exc:
            return json.dumps(error_payload(
                str(exc),
                error_code="invalid_arguments",
            ))
        try:
            # Older observation-capable Bridges route unknown request types into ScriptExecutor.
            context_response = context._send_and_receive(b'{"type":"get_rhino_context","selection_limit":0}')
            snapshot = json.loads(context_response)
            if not isinstance(snapshot, dict) or snapshot.get("status") not in ("success", "error"):
                raise ValueError("Bridge returned an invalid context response.")
            if snapshot["status"] == "error":
                return context_response
            if snapshot.get("capabilities", {}).get("block_analysis") != 1:
                return json.dumps(error_payload(
                    'Load a Bridge with block_analysis=1 before analyzing blocks.',
                    error_code="unsupported_block_analysis",
                ))
            return context._send_and_receive(payload)
        except Exception as exc:
            return json.dumps(error_payload(
                f"Could not analyze the live Rhino block: {exc}",
                error_code="bridge_error",
            ))


    @public_tool(mcp, wrapped=True, annotations={'readOnlyHint': True, 'destructiveHint': False})
    def get_objects(scope: str = "current", object_ids: list[str] | None = None,
                          filters: dict | None = None, include_geometry: StrictBool = False,
                          offset: StrictInt = 0, limit: StrictInt = 50,
                          expected_model_path: str = "", include_ids: StrictBool = False,
                          result_mode: str = "objects", fields: list[str] | None = None,
                          face_offset: StrictInt = 0, face_limit: StrictInt = 128,
                          expected_geometry_crcs: dict[str, StrictInt] | None = None,
                          group_ids: list[str] | None = None, selected: StrictBool = False,
                          inside_window: StrictBool = False, recursive: StrictBool = False,
                          depth: StrictInt = 1, expected_snapshot: str = "") -> str | ToolResult:
        """Rhino 문서의 최상위 모델 객체를 조회합니다. `current`는 표시되고 잠기지 않은 객체(화면 밖 포함), `document`는 숨김·잠금 객체도 포함합니다. 객체·그룹 ID와 메타데이터로 범위를 좁히고 객체, 요약 또는 계층으로 관찰합니다. 그룹은 선택한 범위와 구성원의 교집합입니다. 계층 조회는 그룹·블록 배치를 펼치며 문서 객체와 블록 정의 내부 항목을 구분합니다.

        조건 하나로 객체의 UserDictionary를 조회하는 호출 예시는 `{"filters":{"user_dictionary":[{"source":"attributes","key":"brief_probe","any_of":["yes"]}]}}`입니다.

        행과 면은 각각 페이지를 나눕니다. 행 후속 조회에는 같은 조건과 첫 응답의 snapshot·next_offset을, 면 후속 조회에는 document 객체 ID와 geometry_crc를 사용합니다. objects/summary의 complete는 전체 행이 첫 단일 응답에 포함되고 편집 상태가 안정적일 때 true입니다. 마지막 페이지는 next_offset=null로 확인합니다. hierarchy의 complete에는 관계 완전성도 반영되며 깊이 제한이 있을 수 있습니다. face_page.complete는 전체 면이 첫 단일 응답에 있을 때 true입니다.

        표시 여부는 픽셀 가시성이나 가림 여부를 뜻하지 않습니다.

        Args:
            scope: current(기본), document.
            object_ids: document 범위에서만 사용할 수 있는 선택 사항인 서로 다른 최상위 객체 GUID입니다(1..4096개). group_ids와 함께 사용하지 않습니다.
            filters: layer_paths(정확한 전체 경로), object_types(관찰된 Rhino 이름), name_contains(대소문자 구분 없음), user_dictionary, user_text 조건을 모두 적용합니다. user_text는 객체 속성 User Text를 대상으로 하며 예시는 [{"key":"floor","any_of":["2F"]}]입니다. 최대 16개 조건이 모두 일치해야 하며, 조건마다 문자열 1~64개 중 하나와 정확히 일치해야 합니다. user_dictionary는 조건 하나도 조건 객체의 JSON 배열에 담으며 최대 16개 조건이 모두 일치해야 합니다. 각 조건의 source는 attributes(객체 속성) 또는 geometry(형상), key는 비어 있지 않은 키입니다. any_of는 문자열·불리언·숫자를 1~64개 담은 배열이며, 해당 키의 값 또는 배열 원소가 그중 하나와 일치하면 조건을 충족합니다.
            include_geometry: fields를 생략했을 때 objects 모드에서 형상 상세 정보를 포함합니다. 명시적인 fields가 우선합니다.
            offset: 0..100000. 양수: expected_snapshot 필수.
            limit: 1..200, 기본 50.
            expected_model_path: 생략: 연결 문서. 지정 시 경로 일치 검사.
            include_ids: 기본 false. true: ID 포함.
            result_mode: objects(기본), hierarchy, summary. recursive=true와 summary는 배타.
            fields: 선택 사항인 비어 있지 않은 필드 목록입니다. id, name, layer_path, object_type, geometry_kind, geometry_crc, visible, selected, hidden, locked, bounds, groups, user_dictionary, user_text, geometry_valid, solid, manifold, volume, faces, face_count를 사용할 수 있습니다. 형상 상세 정보와 faces에는 objects 모드가 필요합니다. user_text는 요청 시 객체 속성 문자열을 values, total_keys, truncated로 반환합니다. summary는 fields를 거부합니다.
            face_offset: 기본 0. 양수: document object_ids와 각 객체의 expected_geometry_crcs 필수.
            face_limit: 1..128, 기본 128. objects 모드.
            expected_geometry_crcs: 객체 GUID별 CRC. 면 연속 조회 중 형상 변경 시 거부.
            group_ids: 어느 scope에서든 사용할 수 있는 선택 사항인 서로 다른 Rhino 그룹 GUID입니다(1..64개). 구성원과 선택한 범위의 교집합을 사용합니다. object_ids와 함께 사용하지 않습니다.
            selected: current에서만 사용하며 기본값은 false입니다. 화면 밖의 선택도 포함하여 적격한 선택 객체로 필터링합니다. inside_window와 함께 사용할 수 없습니다.
            inside_window: current에서만 사용하며 기본값은 false입니다. 활성 뷰포트 경계에 걸친 바운딩 박스를 포함합니다. 클리핑 평면이나 픽셀 가림 검사는 수행하지 않습니다. selected와 함께 사용할 수 없습니다.
            recursive: 기본 false. true: hierarchy 모드.
            depth: 1..8, 루트=1. 1 초과 시 recursive=true.
            expected_snapshot: 첫 페이지 snapshot. offset > 0에서 필수.
        """
        return _observation_result(object_queries.query(context._send_and_receive, scope=scope,
                                    ids=[] if object_ids is None else object_ids,
                                    filters={} if filters is None else filters,
                                    include_geometry=include_geometry, offset=offset, limit=limit,
                                    expected_model_path=expected_model_path, result_mode=result_mode,
                                    fields=fields, face_offset=face_offset, face_limit=face_limit,
                                    expected_geometry_crcs=expected_geometry_crcs, include_ids=include_ids,
                                    group_ids=group_ids, selected=selected, inside_window=inside_window,
                                    recursive=recursive, depth=depth, expected_snapshot=expected_snapshot))


    @public_tool(mcp, wrapped=True, annotations={'readOnlyHint': True, 'destructiveHint': False})
    def get_object_intersections(object_ids: list[str], include_block: StrictBool = False) -> str | ToolResult:
        """닫힌 솔리드 사이에서 양의 부피가 겹치는 객체 쌍의 수를 찾습니다. include_block=false면 블록을 검사 범위에서 제외합니다. 0건은 선택된 검사 범위에서의 결과이며 전체 설계 적합성이나 간격을 보장하지 않습니다.

        계산할 수 없는 객체·쌍이 있으면 intersection_count_incomplete 오류와 상세를 반환합니다. 접촉만 하는 면도 계산 불완전으로 반환될 수 있습니다. result는 결과 또는 오류를 담은 JSON 문자열입니다.

        Args:
            object_ids: 서로 다른 현재 최상위 Rhino 객체 GUID 1..512개입니다. 내부 페이지 처리를 통해 하나의 범위로 검사합니다.
            include_block: true이면 변환이 적용된 중첩 블록 구성원까지 펼칩니다. 기본값 false는 범위에서 블록을 제외합니다.
        """
        return _observation_result(object_queries.intersections(
            context._send_and_receive, ids=object_ids, include_block=include_block))


    @public_tool(mcp, wrapped=False, annotations={'readOnlyHint': False, 'destructiveHint': False})
    def capture_rhino_inspection(views: list[dict], width: StrictInt = 640, height: StrictInt = 480,
                                 columns: StrictInt | None = None, expected_model_path: str = "",
                                 model_view_id: str = "", object_ids: list[str] | None = None) -> ToolResult:
        """작업 화면을 유지하면서 여러 시점과 객체 범위를 하나의 PNG로 비교합니다. 객체 범위는 문서 표시 상태를 기준으로 하며 픽셀 가시성이나 가림을 보장하지 않습니다. 그룹 자동 확장과 블록 배치·정의 필터는 지원하지 않습니다.

        설치된 표시 모드의 이름과 GUID는 inspect_03-get_document_context tool에서 sections=["display_modes"]로 조회합니다. Wireframe은 와이어와 곡선 검토, Shaded는 면과 입체 형태 검토, Technical은 가려진 선을 포함한 선 표현 검토에 적합합니다. 사용자 정의 래스터 모드도 설치된 이름이나 GUID로 선택할 수 있습니다. 이름이 중복되면 GUID를 사용합니다.

        inspect_02-get_objects tool에서 include_ids=true로 최상위 모델 객체의 GUID를 확인합니다. 모든 타일을 같은 대상에 맞추려면 공통 object_ids에 GUID 배열을 넣고 views에서 각 방향과 모드를 선택합니다. 예를 들어 views=[{"direction":"top","display_mode":"Technical"},{"direction":"iso_ne","display_mode":"Shaded"}]는 같은 대상을 평면과 사시 방향으로 비교합니다. 원본 뷰 방향에서 지정 객체에 맞춰 확대하려면 공통 또는 타일별 object_ids와 함께 views=[{"direction":"current","frame_objects":true}]를 사용합니다. frame_objects를 생략한 current 타일은 원본 카메라 구도를 사용합니다.

        일부 타일이 실패해도 status=success일 수 있습니다. 전체 성공 여부는 complete에서, 개별 결과와 적용된 모드의 이름·GUID는 tiles에서 확인합니다. PNG 전달과 image_file 저장은 별개입니다.

        Args:
            views: 타일 1..16개. direction: current(기본), top, bottom, front, back, left, right, iso_ne, iso_nw, iso_se, iso_sw, below_ne, below_nw, below_se, below_sw.\\n  // display_mode: 설치된 이름/GUID, label: 최대 120자. object_ids: 최상위 GUID 1..512개; 생략·빈 배열은 공통 범위 또는 문서 표시 상태.
            width: 타일의 픽셀 너비로, 범위는 128..2048이며 기본값은 640입니다. 결합 이미지 제한도 적용됩니다.
            height: 타일의 픽셀 높이로, 범위는 128..2048이며 기본값은 480입니다. 결합 이미지 제한도 적용됩니다.
            columns: 선택 사항인 열 개수이며, 범위는 1..뷰 개수입니다. 생략하면 자동 격자를 사용합니다.
            expected_model_path: 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
            model_view_id: 선택 사항인, 목록에 있는 모델 뷰포트 GUID입니다. Layout/Detail이 활성화된 경우를 포함하여 해당 뷰포트를 활성화하지 않고 사용합니다.
            object_ids: 공통 최상위 객체 GUID 1..4096개. 빈 배열 불가; 타일별 object_ids와 배타.
        """
        from almond_mcp.features.context.inspection_capture import execute
        try:
            path = bound_model_path(expected_model_path)
        except ValueError as exc:
            return _viewport_result(error_payload(str(exc), error_code="invalid_arguments"))
        payload = {"views": views, "width": width, "height": height}
        if columns is not None:
            payload["columns"] = columns
        if model_view_id != "":
            payload["model_view_id"] = model_view_id
        if object_ids is not None:
            payload["object_ids"] = object_ids
        return execute(context._send_and_receive, payload, path)


    def _viewport_result(metadata: dict) -> ToolResult:
        content = [TextContent(type="text", text=json.dumps(metadata, ensure_ascii=False))]
        return ToolResult(content=content, structured_content=metadata,
                          is_error=metadata.get("status") != "success")


    @public_tool(mcp, wrapped=False, annotations={'readOnlyHint': False, 'destructiveHint': False})
    def get_defined_viewcapture(target_kind: str, target: str, scale_percent: StrictInt = 75,
                                include_usage: StrictBool = False, display_mode: str = "",
                                labels: StrictBool = False, depth: StrictInt = 1,
                                width: StrictInt | None = None, height: StrictInt | None = None,
                                expected_model_path: str = "") -> ToolResult:
        """저장된 Named View 또는 Layout 용지를 PNG로 캡처합니다. 이름·ID는 inspect_03-get_document_context tool에서 조회합니다.

        Named View는 저장된 카메라를 사용하고, Layout은 용지와 Detail의 기존 표시 모드를 사용합니다. Named View에 사용할 설치 모드와 용도는 capture_02-inspection tool의 설명을 참고합니다. Layout에는 픽셀 크기와 display_mode를 지정할 수 없습니다. 이미지와 image_file 저장 결과는 별개이며, 사용량 추정·경고는 별도 text content로 반환됩니다. Layout은 인쇄 색과 선폭으로 출력하며 문서의 PrintDisplay 설정을 바꾸지 않습니다. 용지와 Detail에 보이는 인쇄 대상이 없으면 빈 PNG도 정상 결과입니다. Layout Detail 레이블은 지원하지 않습니다.

        Args:
            target_kind: named_view | layout.
            target: 기존 이름 또는 ID입니다. 대소문자를 구분하지 않는 이름 일치는 유일해야 합니다.
            scale_percent: 범위는 1..100이며 기본값은 75입니다. 원하는 상한이며, 백분율 캡처는 전달 용량 제한에 맞게 축소될 수 있습니다.
            include_usage: true이면 이미지 크기와 픽셀 기준 토큰 추정치를 포함합니다.
            display_mode: Named View 전용. 기본 Shaded; 설치된 래스터 모드 이름 또는 ID.
            labels: 기본 false. 최대 200개; 주변 레이블이 겹칠 수 있음.
            depth: 레이블 깊이: 1..8, 기본 1.
            width: 선택 사항인 Named View의 픽셀 너비로, 범위는 128..2048입니다. height도 제공하고 scale_percent=100으로 설정합니다. Layout에는 사용하지 않습니다.
            height: 선택 사항인 Named View의 픽셀 높이로, 범위는 128..2048입니다. width도 제공하고 scale_percent=100으로 설정합니다. Layout에는 사용하지 않습니다.
            expected_model_path: 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
        """
        from almond_mcp.features.context.view_capture import execute
        result = execute(context._send_and_receive, "get_defined_viewcapture", target_kind=target_kind, target=target,
                         scale_percent=scale_percent, include_usage=include_usage, display_mode=display_mode,
                         labels=labels, depth=depth, width=width, height=height, expected_model_path=expected_model_path)
        return _capture_result(result, scale_percent, include_usage,
                               requested_size=(width, height) if width is not None and height is not None else None)


    @public_tool(mcp, wrapped=False, annotations={'readOnlyHint': False, 'destructiveHint': False})
    def get_current_viewcapture(target_ids: list[str] | None = None, target_kind: str = "object",
                                isolate: StrictBool = False, scale_percent: StrictInt = 75,
                                include_usage: StrictBool = False, display_mode: str = "",
                                labels: StrictBool = False, depth: StrictInt = 1,
                                width: StrictInt | None = None, height: StrictInt | None = None,
                                expected_model_path: str = "") -> ToolResult:
        """현재 Rhino 모델 뷰포트를 일반 화면 색과 선 표현으로 PNG에 캡처합니다. 캡처 중 문서의 PrintDisplay 설정은 유지됩니다. 대상 지정 시 실제 선택과 카메라가 바뀌며, isolate와 display_mode도 실제 화면 상태를 변경합니다. 설치된 모드의 이름과 GUID는 inspect_03-get_document_context tool에서 sections=["display_modes"]로 조회합니다. 작업 화면을 유지하면서 선택한 객체를 여러 방향이나 모드로 비교하려면 capture_02-inspection tool을 사용합니다. 격리 해제는 Rhino Unisolate를 사용합니다. 잠긴 주변 객체는 보일 수 있고, 선택·카메라는 별도로 확인해야 합니다.

        PNG 이미지 전달과 image_file 저장은 별개입니다. include_usage의 토큰 수는 픽셀 기준 추정치입니다. labels는 주변 객체에도 표시되어 화면을 가릴 수 있습니다.

        Args:
            target_ids: 화면에서 선택·확대할 객체, 그룹 또는 Holon의 ID 배열입니다. 생략하면 현재 화면을 사용하며, 입력할 때는 하나 이상의 ID를 지정합니다.
            target_kind: object(기본), group, block, holon. block은 배치 객체 ID; 비기본값은 target_ids 필요.
            isolate: 기본 false. true: target_ids 필수, 확대 전 Isolate.
            scale_percent: 이미지 해상도의 백분율입니다. 1..100 범위이며 기본값은 75입니다.
            include_usage: true이면 이미지 크기와 픽셀 기준 토큰 추정치를 포함합니다.
            display_mode: 선택 사항인 설치된 래스터 모드 이름/ID입니다. 제공하면 실제 모델 뷰포트를 변경합니다.
            labels: 기본 false. 주변 객체에도 최대 200개 표시 가능.
            depth: 레이블 확장 깊이: 1..8, 기본 1.
            width: 이미지의 픽셀 너비입니다. 128..2048 범위이며 height도 입력하고 scale_percent=100으로 지정합니다.
            height: 이미지의 픽셀 높이입니다. 128..2048 범위이며 width도 입력하고 scale_percent=100으로 지정합니다.
            expected_model_path: 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
        """
        from almond_mcp.features.context.view_capture import execute
        result = execute(context._send_and_receive, "get_current_viewcapture", target_kind=target_kind, target_ids=target_ids,
                         isolate=isolate, scale_percent=scale_percent, include_usage=include_usage, display_mode=display_mode,
                         labels=labels, depth=depth, width=width, height=height, expected_model_path=expected_model_path)
        return _capture_result(result, scale_percent, include_usage,
                               requested_size=(width, height) if width is not None and height is not None else None)

    def _capture_result(response: dict, scale_percent: int, include_usage: bool,
                        *, kind: str = "viewport", requested_size: tuple[int, int] | None = None) -> ToolResult:
        if response.get("status") != "success":
            response.pop("image", None)
            return _viewport_result(response)
        try:
            scale_percent = response.get("scale_percent", scale_percent)
            if type(scale_percent) is not int or not 1 <= scale_percent <= 100:
                raise ValueError("Invalid actual capture scale.")
            captured = response["image"]
            encoded = captured["data"]
            byte_limit = 4 * 1024 * 1024
            if captured["mime_type"] != "image/png" or not isinstance(encoded, str):
                raise ValueError("Expected base64 PNG image data. Load the matching Bridge runtime if it still returns JPEG.")
            if len(encoded) > 4 * ((byte_limit + 2) // 3):
                raise ValueError("The captured PNG exceeds 4 MiB; use a lower scale_percent.")
            raw = base64.b64decode(encoded, validate=True)
            if not raw or len(raw) > byte_limit:
                raise ValueError("The captured PNG is empty or exceeds 4 MiB.")
            dimensions = (captured["width"], captured["height"])
            source = (captured["source_width"], captured["source_height"])
            if requested_size is not None and (dimensions != requested_size or source != requested_size):
                raise ValueError("Captured dimensions do not match the explicit requested pixels.")
            if (any(type(value) is not int or value < 1 for value in (*dimensions, *source)) or
                    dimensions[0] * dimensions[1] > 16 * 1024 * 1024 or
                    dimensions != tuple(max(1, value * scale_percent // 100) for value in source)):
                raise ValueError("Captured dimensions do not match the requested percentage or exceed 16 megapixels.")
            with PillowImage.open(io.BytesIO(raw)) as picture:
                if picture.format != "PNG" or picture.size != dimensions:
                    raise ValueError("PNG dimensions or format do not match the capture metadata.")
                picture.load()
        except Exception as exc:
            error = error_payload(f"Invalid viewport image: {exc}", error_code="invalid_capture_response")
            error.update({key: response[key] for key in ("view_change", "mutation_applied", "requires_reconciliation", "warnings") if key in response})
            return _viewport_result(error)
        image_file = save_png(raw, kind)
        metadata = {"image_file": image_file}
        metadata.update({key: response[key] for key in ("view_change", "mutation_applied", "requires_reconciliation") if key in response})
        content = [ImageContent(type="image", data=encoded, mimeType="image/png"),
                   TextContent(type="text", text=json.dumps(metadata, ensure_ascii=False))]
        if response.get("warnings"):
            content.append(TextContent(type="text", text=json.dumps({"warnings": response["warnings"]}, ensure_ascii=False)))
        if include_usage:
            # Pixel patches, not compressed PNG bytes, drive this example estimate.
            # The client model/detail is not supplied by MCP; never call it actual usage.
            patches = ((dimensions[0] + 31) // 32) * ((dimensions[1] + 31) // 32)
            usage = {"width": dimensions[0], "height": dimensions[1], "scale_percent": scale_percent,
                     "patches_32px": patches, "estimated_image_tokens": math.ceil(patches * 1.2),
                     "assumption": "32px patches x 1.2, no provider resizing; actual model/detail may differ"}
            content.append(TextContent(type="text", text=json.dumps(usage)))
        return ToolResult(content=content, structured_content=metadata)


    return {
        "get_rhino_context": get_rhino_context,
        "analyze_block_reculviely": analyze_block_reculviely,
        "_viewport_result": _viewport_result,
        "get_defined_viewcapture": get_defined_viewcapture,
        "get_current_viewcapture": get_current_viewcapture,
        "get_objects": get_objects,
        "get_object_intersections": get_object_intersections,
        "capture_rhino_inspection": capture_rhino_inspection,
    }
