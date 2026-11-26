"""Register diagram asset tools using the shared asset catalogue and bridge."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import query_output, validate_field_groups
from almond_mcp.features.diagrams.output import GROUPS, project
from almond_mcp.features.assets.mutation import send_placement
from almond_mcp.features.assets.store import AssetResult
from almond_mcp.tool_declarations import public_tool

from pydantic import StrictBool
import json


def register(mcp, context):
    """Register diagram tools against the calling server's live context."""

    def current_card(asset):
        # Resolve under the library root and recheck the file after the index was loaded.
        index = context.diagram_asset_indexer
        resolved = index.resolve_record(asset)
        if resolved is None:
            return {"asset_id": asset["asset_id"], "file_available": False}
        card = index.public_record(resolved)
        if not isinstance(card.get("source"), dict):
            source = {key: card[key] for key in ("geometry_source", "warehouse_title", "warehouse_url", "warehouse_publisher", "license")
                      if card.get(key)}
            if source:
                card["source"] = source
        return card

    def search_catalogue(field_groups, **filters):
        page = context.retrieval_store.search_assets(library_id="diagram_assets", record_format=AssetResult.MANIFEST, **filters)
        page["assets"] = [current_card(asset) for asset in page["assets"]]
        return json.dumps(project(page, field_groups))

    @public_tool(mcp)
    @query_output
    def list_diagram_assets(category: str = "", limit: int = 20, offset: int = 0, field_groups: list[str] | None = None) -> str:
        validate_field_groups(field_groups, GROUPS)
        return search_catalogue(field_groups, category=category, limit=limit, offset=offset)


    @public_tool(mcp)
    @query_output
    def search_diagram_assets(
        query: str = "",
        category: str = "",
        max_width_mm: float = 0,
        max_depth_mm: float = 0,
        max_height_mm: float = 0,
        limit: int = 10,
        offset: int = 0, field_groups: list[str] | None = None) -> str:
        validate_field_groups(field_groups, GROUPS)
        return search_catalogue(
            field_groups,
            query=query,
            category=category,
            max_width_mm=max_width_mm,
            max_depth_mm=max_depth_mm,
            max_height_mm=max_height_mm,
            limit=limit,
            offset=offset,
        )


    @public_tool(mcp)
    @query_output
    def get_diagram_asset(asset_id: str, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        validate_field_groups(field_groups, GROUPS)
        asset = context.retrieval_store.get_asset(asset_id, library_id="diagram_assets")
        if not asset:
            return json.dumps(project(error_payload(f"Unknown diagram asset_id: {asset_id}"), field_groups))
        return json.dumps(project({"status": "success", "asset": current_card(asset)}, field_groups))


    @public_tool(mcp)
    def place_diagram_asset(
        asset_id: str,
        x: float = 0,
        y: float = 0,
        z: float = 0,
        rotation_degrees: float = 0,
        scale: float = 1,
    ) -> str:
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
