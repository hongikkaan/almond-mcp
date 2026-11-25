"""Register diagram asset tools using the shared asset catalogue and bridge."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import query_output, validate_field_groups
from almond_mcp.features.diagrams.output import GROUPS, project
from almond_mcp.features.assets.mutation import send_placement
from almond_mcp.tool_declarations import public_tool

from pydantic import StrictBool
import json


def register(mcp, context):
    """Register diagram tools against the calling server's live context."""

    @public_tool(mcp, wrapped=True)
    @query_output
    def list_diagram_assets(category: str = "", limit: int = 20, offset: int = 0, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        """사람·나무·기호 등 등록된 2D 벡터·CAD 다이어그램 조회. 파일이 없는 항목도 포함한다. 상세 정보는 diagram_01-get tool, 키워드·치수 검색은 diagram_04-search tool.

        Args:
            category: 분류값 전체 일치. 대소문자 무시. 비워 두면 전체 조회.
            limit: 1..50으로 보정.
            offset: 음수는 0으로 보정.
            field_groups: dimensions, drawing, metadata, source, paths, audit, all. 생략하거나 비우면 요약.
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
        """등록된 2D 다이어그램을 키워드·분류·최대 치수로 검색. 파일이 없는 자산도 포함한다. 상세 정보와 파일 상태는 diagram_01-get tool에서 조회한다.

        Args:
            query: 여러 검색어는 OR로 결합. 비워 두면 키워드 조건 없이 검색.
            category: 분류값 전체 일치. 대소문자 무시. 비워 두면 전체 검색.
            max_width_mm: 0 이하이면 치수 필터 해제.
            max_depth_mm: 0 이하이면 치수 필터 해제. 등록 치수는 추정치일 수 있다.
            max_height_mm: 0 이하이면 치수 필터 해제.
            limit: 1..50으로 보정.
            offset: 음수는 0으로 보정. 다음 페이지에도 같은 필터 사용.
            field_groups: dimensions, drawing, metadata, source, paths, audit, all. 생략하거나 비우면 요약. 일부 세부 값은 포함되지 않을 수 있다.
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
        """다이어그램 자산의 등록 정보와 원본 파일 상태 조회. 파일이 없는 항목도 조회 가능.

        Args:
            asset_id: diagram_02-list tool 또는 diagram_04-search tool에서 얻은 ID. 대소문자와 공백까지 그대로 사용.
            include_ids: true면 추가 식별자 포함. 입력 asset_id는 응답에 반복하지 않는다.
            field_groups: dimensions, drawing, metadata, source, paths, audit, all. 생략하거나 비우면 요약. all은 다른 그룹 밖의 등록 필드도 포함.
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
        """SVG·DWG·DXF 다이어그램을 Rhino 문서에 블록 인스턴스로 배치. requires_reconciliation=true면 문서에서 실제 배치를 확인한 뒤 다음 작업을 결정한다.

        Args:
            asset_id: 기존 라이브러리 자산 ID. 모르는 경우 include_ids=true로 목록·검색 결과에서 확인.
            x: 현재 Rhino 문서 단위.
            y: 현재 Rhino 문서 단위.
            z: 현재 Rhino 문서 단위.
            rotation_degrees: 월드 Z축 기준.
            scale: 양수인 균일 축척. 1은 문서 단위로 변환한 자산의 원래 크기.
        """
        asset = context.retrieval_store.get_asset(asset_id, library_id="diagram_assets")
        if not asset:
            return json.dumps(error_payload(f"Unknown diagram asset_id: {asset_id}"))
        asset = context.diagram_asset_indexer.resolve_record(asset)
        if not asset or not asset.get("file_available"):
            return json.dumps(error_payload(f"Diagram asset file is missing for {asset_id}."))

        return json.dumps(send_placement(
            context._send_and_receive, asset_id=asset_id, asset=asset, position=(x, y, z),
            rotation_degrees=rotation_degrees, scale=scale, library_id="diagram_assets",
            action="Diagram asset placement",
        ))

    return {
        "list_diagram_assets": list_diagram_assets,
        "search_diagram_assets": search_diagram_assets,
        "get_diagram_asset": get_diagram_asset,
        "place_diagram_asset": place_diagram_asset,
    }
