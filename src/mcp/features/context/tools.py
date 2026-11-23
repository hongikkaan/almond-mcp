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
        """연결된 Rhino 문서·뷰·편집 상태와 Named View·Layout·레이어 계층·표시 모드 조회. Named View·Layout·표시 모드는 목록별 최대 128개이며 include_ids와 무관하게 ID를 반환. 화면 캡처에는 capture_03-current_view tool 사용.

        Args:
            sections: document, viewport, editor, viewports, named_views, layouts, layer_tree, display_modes 중 선택. 생략 또는 null이면 document, named_views, layouts, layer_tree, display_modes. []이면 항목 조회 생략.
            include_ids: 뷰포트 등 선택적으로 ID를 반환하는 항목에 적용
            include_editor_details: editor 요청 시 공급자·명령·Undo 근거 포함
        """
        from almond_mcp.features.context.context_query import query
        return _observation_result(query(context._send_and_receive, sections, include_ids, include_editor_details))


    @public_tool(mcp, wrapped=True, annotations={'readOnlyHint': True, 'destructiveHint': False}, errors=True)
    @query_output
    def analyze_block_reculviely(mode: str, options: dict, expected_model_path: str = "", include_ids: StrictBool = False) -> str:
        """읽기 전용 중첩 블록 조회. outline은 선택된 루트를 기본으로 구조를 요약하고, resolve-block은 루트부터 대상까지의 경로로 공유 배치와 참조·링크 제한을 확인.

        definition_impact.complete는 영향 범위 계수 완료 여부, occurrences_truncated는 반환 목록의 잘림 여부. 정의 내부 ID는 편집 가능한 문서 객체 ID와 다를 수 있다. 후속 조회에 ID가 필요하면 include_ids=true 사용.

        Args:
            mode: outline 또는 resolve-block
            options: outline: ids 또는 path로 지정. 둘 다 생략하면 scope=selected(기본)·viewport·document 중 사용.
                depth 0..64(기본 64), max_items 1..5000(기본 200), max_bytes 2048..262144(기본 48000).
                field_groups: summary(기본), objects, annotations, transforms. include_geometry와 annotations로 형상·주석 포함, annotation_layer로 TextDot 레이어 필터링. field_groups를 생략하고 include_geometry 또는 annotations를 지정하면 기존 상세 모드.
                resolve-block: path에 최상위부터 대상 블록까지 GUID 1..65개.
            expected_model_path: 생략하면 연결 문서 사용. 지정하면 일치하는 경로에서만 조회.
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
        """Rhino 최상위 모델 객체를 ID·그룹·메타데이터로 조회. current는 표시되고 잠기지 않은 객체(화면 밖 포함), document는 숨김·잠금 객체까지 포함. 그룹은 선택 범위와 구성원의 교집합. 계층 모드는 그룹·블록 배치를 펼쳐 문서 객체와 블록 정의 내부 항목을 구분. 표시 여부는 가림을 고려한 화면 가시성과 별개.

        UserDictionary 조건 예: `{"filters":{"user_dictionary":[{"source":"attributes","key":"brief_probe","any_of":["yes"]}]}}`.

        행 후속 조회에는 같은 조건과 첫 응답의 snapshot·next_offset을 사용. 면 후속 조회에는 document 객체 ID와 geometry_crc 사용. objects·summary의 complete는 전체 행이 첫 응답에 포함되고 편집 상태가 안정적일 때 true. hierarchy는 관계 완전성도 확인하며 깊이 제한을 적용할 수 있다. face_page.complete는 전체 면이 첫 응답에 포함됐을 때 true. 마지막 행 페이지는 next_offset=null.

        Args:
            scope: current 또는 document
            object_ids: scope=document 전용. 서로 다른 최상위 객체 GUID 1..4096개. group_ids와 동시 지정 불가.
            filters: 모든 조건을 함께 적용. layer_paths는 정확한 전체 경로, object_types는 관찰된 Rhino 이름, name_contains는 대소문자 구분 없이 검색. 객체 속성 User Text의 user_text와 UserDictionary의 user_dictionary는 각각 조건 객체 1개도 배열로 지정하며 최대 16개 조건이 모두 일치해야 한다. user_text 예: [{"key":"floor","any_of":["2F"]}]. user_dictionary는 source=attributes(객체 속성) 또는 geometry(형상)와 비어 있지 않은 key 필요. any_of는 user_text에서 문자열 1..64개, user_dictionary에서 문자열·불리언·숫자 1..64개. 키의 값 또는 배열 원소가 any_of 중 하나와 정확히 일치해야 한다.
            include_geometry: fields를 생략한 objects 모드에서 형상 상세를 포함. fields를 명시하면 그 목록 우선.
            offset: 0..100000. 양수이면 expected_snapshot 필요.
            limit: 1..200
            expected_model_path: 생략하면 연결 문서 사용. 지정하면 일치하는 경로에서만 조회.
            result_mode: objects, hierarchy, summary. recursive=true와 summary는 동시 지정 불가.
            fields: 1개 이상 선택: id, name, layer_path, object_type, geometry_kind, geometry_crc, visible, selected, hidden, locked, bounds, groups, user_dictionary, user_text, geometry_valid, solid, manifold, volume, faces, face_count. 형상 상세와 faces는 objects 모드에서만 사용. summary에서는 fields 지정 불가.
            face_offset: 양수이면 scope=document, object_ids 및 객체별 expected_geometry_crcs 필요
            face_limit: 1..128. objects 모드에서 사용.
            expected_geometry_crcs: 객체 GUID별 CRC. 면을 이어서 조회할 때 형상이 바뀌면 거부.
            group_ids: 서로 다른 Rhino 그룹 GUID 1..64개. 모든 scope에서 사용 가능, object_ids와 동시 지정 불가.
            selected: current 전용. 화면 밖에서 선택된 객체도 포함. inside_window와 동시 지정 불가.
            inside_window: current 전용. 활성 뷰포트 경계에 걸친 바운딩 박스 포함. 클리핑 평면과 픽셀 가림은 고려하지 않으며 selected와 동시 지정 불가.
            recursive: true이면 계층 모드 사용
            depth: 1..8, 루트=1. 1 초과 시 recursive=true.
            expected_snapshot: offset > 0이면 첫 페이지의 snapshot 필요
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
        """닫힌 솔리드 중 양의 부피가 겹치는 객체 쌍을 집계. 0건은 검사 범위의 결과이며 간격이나 전체 설계 적합성은 별개. 계산할 수 없는 객체·쌍이 있으면 intersection_count_incomplete와 상세 반환. 면 접촉만으로도 계산이 불완전할 수 있다.

        Args:
            object_ids: 서로 다른 현재 최상위 Rhino 객체 GUID 1..512개. 내부에서 페이지를 나누며 전체를 하나의 범위로 검사.
            include_block: 중첩 블록의 배치 변환을 적용해 구성원까지 검사. false이면 블록 제외.
        """
        return _observation_result(object_queries.intersections(
            context._send_and_receive, ids=object_ids, include_block=include_block))


    @public_tool(mcp, wrapped=False, annotations={'readOnlyHint': False, 'destructiveHint': False})
    def capture_rhino_inspection(views: list[dict], width: StrictInt = 640, height: StrictInt = 480,
                                 columns: StrictInt | None = None, expected_model_path: str = "",
                                 model_view_id: str = "", object_ids: list[str] | None = None) -> ToolResult:
        """작업 화면을 유지하면서 여러 시점과 객체 범위를 한 PNG로 비교. 범위는 문서 표시 상태 기준이며 픽셀 가시성이나 가림은 판정하지 않는다. 그룹 자동 확장과 블록 배치·정의 필터는 지원하지 않는다.

        표시 모드 이름·GUID는 inspect_03-get_document_context tool의 sections=["display_modes"]에서 조회. Wireframe은 곡선·와이어, Shaded는 면과 입체, Technical은 가려진 선을 포함한 선 표현 검토에 적합하다. 사용자 정의 래스터 모드도 선택할 수 있으며 이름이 중복되면 GUID를 사용한다.

        최상위 모델 객체 GUID는 inspect_02-get_objects tool의 include_ids=true로 조회. 공통 object_ids를 지정한 뒤 views=[{"direction":"top","display_mode":"Technical"},{"direction":"iso_ne","display_mode":"Shaded"}]로 같은 대상을 평면과 사시에서 비교한다. 원본 뷰 방향에서 대상에 맞춰 확대하려면 공통 또는 타일별 object_ids와 views=[{"direction":"current","frame_objects":true}]를 사용한다. frame_objects를 생략한 current 타일은 원본 카메라 구도를 유지한다.

        일부 타일이 실패해도 status=success일 수 있으므로 complete와 tiles를 함께 확인한다.

        Args:
            views: 타일 1..16개. direction: current(기본), top, bottom, front, back, left, right, iso_ne, iso_nw, iso_se, iso_sw, below_ne, below_nw, below_se, below_sw. display_mode: 설치된 모드 이름 또는 GUID. label: 최대 120자. object_ids: 블록 인스턴스를 제외한 최상위 객체 GUID 1..512개. 생략하거나 비우면 공통 범위 또는 문서 표시 상태를 사용한다.
            width: 타일당 128..2048픽셀. 결합 이미지 제한도 적용.
            height: 타일당 128..2048픽셀. 결합 이미지 제한도 적용.
            columns: 1..뷰 개수. 생략 시 자동 격자.
            expected_model_path: 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
            model_view_id: 활성화하지 않고 사용할 모델 뷰포트 GUID. Layout·Detail에서 작업 중일 때도 지정 가능.
            object_ids: 모든 타일에 적용할 최상위 객체 GUID 1..4096개. 블록 인스턴스 제외. 타일별 object_ids와 함께 지정할 수 없다.
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
        """저장된 Named View 또는 Layout 용지를 PNG로 캡처. 대상 이름·ID는 inspect_03-get_document_context tool에서 조회한다.

        Named View는 저장된 카메라를 사용하며 표시 모드 선택은 capture_02-inspection tool 참고. Layout은 용지·Detail의 기존 모드와 인쇄 색·선폭으로 출력하고 PrintDisplay는 유지한다. Layout에는 픽셀 크기·display_mode를 지정할 수 없고 Detail 레이블도 지원하지 않는다. 인쇄 대상이 없으면 빈 PNG도 정상이다.

        PNG 전달과 파일 저장은 별개다. 사용량 추정·경고는 별도 text content로 전달한다.

        Args:
            target_kind: named_view 또는 layout.
            target: 기존 이름 또는 ID. 이름은 대소문자 무시 기준으로 하나만 일치해야 한다.
            scale_percent: 1..100 범위의 상한. 전달 용량에 맞춰 더 작아질 수 있다.
            include_usage: 이미지 크기와 픽셀 기준 토큰 추정치 포함.
            display_mode: Named View 전용. 생략 시 Shaded. 설치된 래스터 모드 이름 또는 GUID.
            labels: 최대 200개. 주변 레이블과 겹칠 수 있다.
            depth: 레이블 깊이 1..8.
            width: Named View 전용. 128..2048픽셀. height와 함께 지정하고 scale_percent=100 사용.
            height: Named View 전용. 128..2048픽셀. width와 함께 지정하고 scale_percent=100 사용.
            expected_model_path: 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
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
        """현재 Rhino 모델 뷰포트를 화면 색과 선 표현으로 PNG 캡처. 문서의 PrintDisplay 설정은 유지한다. 대상 지정은 실제 선택과 카메라를 바꾸고 isolate와 display_mode도 작업 화면에 적용된다.

        표시 모드 이름·GUID는 inspect_03-get_document_context tool의 sections=["display_modes"]에서 조회. 작업 화면을 유지하면서 여러 방향이나 모드를 비교하려면 capture_02-inspection tool을 사용한다. 격리는 Rhino Unisolate로 해제할 수 있다. 잠긴 주변 객체는 격리 중에도 보일 수 있으며 선택과 카메라 상태는 별도로 확인한다.

        Args:
            target_ids: 선택·확대할 대상 ID를 하나 이상 지정. 생략 시 현재 구도로 캡처.
            target_kind: object, group, block, holon. block에는 배치 객체 ID 사용. object 이외에는 target_ids 필요.
            isolate: target_ids가 필요하며 확대 전에 격리.
            scale_percent: 1..100.
            include_usage: 이미지 크기와 픽셀 기준 토큰 추정치 포함.
            display_mode: 설치된 래스터 모드 이름 또는 GUID.
            labels: 주변 객체에도 최대 200개 표시하므로 화면을 가릴 수 있다.
            depth: 레이블 확장 깊이 1..8.
            width: 128..2048픽셀. height와 함께 지정하고 scale_percent=100 사용.
            height: 128..2048픽셀. width와 함께 지정하고 scale_percent=100 사용.
            expected_model_path: 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
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
