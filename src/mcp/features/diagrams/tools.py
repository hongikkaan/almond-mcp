"""Register diagram asset tools using the shared asset catalogue and bridge."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import query_output, validate_field_groups
from almond_mcp.features.diagrams.output import GROUPS, project
from almond_mcp.features.assets.mutation import send_mutation
from almond_mcp.tool_declarations import public_tool

from pydantic import StrictBool
import json


def register(mcp, context):
    """Register diagram tools against the calling server's live context."""

    @public_tool(mcp, wrapped=True)
    @query_output
    def list_diagram_assets(category: str = "", limit: int = 20, offset: int = 0, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        """사람·나무·기호 등 2D 벡터·CAD 다이어그램의 등록 목록을 조회합니다. 목록에 파일이 없는 항목도 포함되며, 자산 ID로 diagram_01-get tool에서 세부 정보와 사용 가능 상태를 확인할 수 있습니다. 키워드·치수 검색은 diagram_04-search tool을 사용합니다.

        Args:
            category: 분류값 전체 일치, 대소문자 무시. 빈 값: 전체.
            limit: 기본 20, 1..50으로 보정.
            offset: 0부터 시작. 음수는 0으로 보정.
            include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
            field_groups: 선택 가능한 세부 그룹은 dimensions, drawing, metadata, source, paths, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다.
        """
        validate_field_groups(field_groups, GROUPS)
        page = context.retrieval_store.search_assets(
            library_id="diagram_assets",
            category=category,
            limit=limit,
            offset=offset,
        )
        return json.dumps(project({
            "library_id": "diagram_assets",
            "purpose": "2D vector diagramming and line-art",
            **page,
        }, field_groups))


    @public_tool(mcp, wrapped=True)
    @query_output
    def search_diagram_assets(
        query: str = "",
        category: str = "",
        max_width_mm: float = 0,
        max_depth_mm: float = 0,
        max_height_mm: float = 0,
        limit: int = 10,
        offset: int = 0, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        """사람·나무 등 등록된 2D 다이어그램을 키워드·분류·최대 치수로 검색합니다. 파일이 없는 자산도 결과에 포함됩니다. 상세 등록 정보와 파일 존재 상태는 diagram_01-get tool에서 조회할 수 있습니다.

        Args:
            query: 여러 검색어는 OR로 결합. 빈 값: 전체.
            category: 분류 전체 일치, 대소문자 무시. 빈 값: 전체.
            max_width_mm: 측정된 자산 너비의 최댓값이며, 밀리미터 단위입니다. 선택 사항이며, 0은 이 크기 필터를 해제합니다.
            max_depth_mm: 등록 치수 상한(mm). 0 이하: 필터 해제. 등록 치수는 추정치일 수 있음.
            max_height_mm: 측정된 자산 높이의 최댓값이며, 밀리미터 단위입니다. 선택 사항이며, 0은 이 크기 필터를 해제합니다.
            limit: 기본 10, 1..50으로 보정.
            offset: 0부터 시작, 음수는 0으로 보정. 다음 페이지에도 같은 필터 사용.
            include_ids: true: 자산 ID 포함.
            field_groups: dimensions, drawing, metadata, source, paths, audit, all. 생략·빈 배열: 요약. 세부 항목은 검색 결과에 나타나지 않을 수 있음.
        """
        validate_field_groups(field_groups, GROUPS)
        return json.dumps(project(context.retrieval_store.search_assets(
            query=query,
            library_id="diagram_assets",
            category=category,
            max_width_mm=max_width_mm,
            max_depth_mm=max_depth_mm,
            max_height_mm=max_height_mm,
            limit=limit,
            offset=offset,
        ), field_groups))


    @public_tool(mcp, wrapped=True)
    @query_output
    def get_diagram_asset(asset_id: str, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        """다이어그램 자산 하나의 등록 정보와 파일 존재 상태를 조회합니다. 목록이나 검색에서 얻은 ID로 조회하며, 파일이 없는 등록 항목도 조회됩니다.

        Args:
            asset_id: 목록·검색에서 얻은 자산 ID. 대소문자·공백까지 정확히 지정.
            include_ids: true: 다른 식별자 포함. 입력 asset_id는 응답에 반복되지 않음.
            field_groups: dimensions, drawing, metadata, source, paths, audit, all. 생략·빈 배열: 요약. all: 다른 그룹 외 등록 필드도 포함.
        """
        validate_field_groups(field_groups, GROUPS)
        asset = context.retrieval_store.get_asset(asset_id, library_id="diagram_assets")
        if not asset:
            return json.dumps(project(error_payload(f"Unknown diagram asset_id: {asset_id}"), field_groups))
        return json.dumps(project({"status": "success", "asset": asset}, field_groups))


    @public_tool(mcp, wrapped=True)
    def place_diagram_asset(
        asset_id: str,
        x: float = 0,
        y: float = 0,
        z: float = 0,
        rotation_degrees: float = 0,
        scale: float = 1,
    ) -> str:
        """SVG·DWG·DXF 다이어그램을 Rhino 문서의 블록 인스턴스로 배치합니다.
        응답 유실 등으로 requires_reconciliation이 true이면 Rhino 문서에서 실제 배치 결과를 확인한 뒤 다음 작업을 결정합니다.

        Args:
            asset_id: include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다.
            x: 현재 Rhino 문서 단위를 사용하는 배치 X 좌표입니다.
            y: 현재 Rhino 문서 단위를 사용하는 배치 Y 좌표입니다.
            z: 현재 Rhino 문서 단위를 사용하는 배치 Z 좌표입니다.
            rotation_degrees: 월드 Z축을 중심으로 한 회전각이며, 단위는 도입니다.
            scale: 양수인 균일 배치 축척입니다. 1이면 단위 변환 후 자산 크기를 유지합니다.
        """
        asset = context.retrieval_store.get_asset(asset_id, library_id="diagram_assets")
        if not asset:
            return json.dumps(error_payload(f"Unknown diagram asset_id: {asset_id}"))
        asset = context.diagram_asset_indexer.resolve_record(asset)
        if not asset or not asset.get("file_available"):
            return json.dumps(error_payload(f"Diagram asset file is missing for {asset_id}."))

        payload = json.dumps({
            "type": "place_drawing_asset",
            "asset_id": asset_id,
            "file_path": asset["_resolved_file"],
            "name": f"{asset.get('product', '')} {asset.get('variant', '')}".strip(),
            "position": [x, y, z],
            "rotation_degrees": rotation_degrees,
            "scale": scale,
            "metadata": {
                "library_id": "diagram_assets",
                "product": asset.get("product"),
                "variant": asset.get("variant"),
                "category": asset.get("category"),
                "dimensions_mm": asset.get("dimensions_mm"),
                "drawing_roles": asset.get("drawing_roles", []),
                "lod": asset.get("lod"),
            },
        }).encode("utf-8")

        return json.dumps(send_mutation(context._send_and_receive, payload, timeout=90.0, action="Diagram asset placement"))

    return {
        "list_diagram_assets": list_diagram_assets,
        "search_diagram_assets": search_diagram_assets,
        "get_diagram_asset": get_diagram_asset,
        "place_diagram_asset": place_diagram_asset,
    }
