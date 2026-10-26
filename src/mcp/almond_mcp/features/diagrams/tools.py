"""Register diagram asset tools using the shared asset catalogue and bridge."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import query_output
from almond_mcp.instruction_text import tool_instruction

from pydantic import StrictBool
import json
import socket


def register(mcp, context):
    """Register diagram tools against the calling server's live context."""

    @mcp.tool()
    @tool_instruction(__file__, 'list_diagram_assets')
    @query_output
    def list_diagram_assets(category: str = "", limit: int = 20, offset: int = 0, include_ids: StrictBool = False) -> str:
        page = context.retrieval_store.search_assets(
            library_id="diagram_assets",
            category=category,
            limit=limit,
            offset=offset,
        )
        return json.dumps({
            "library_id": "diagram_assets",
            "purpose": "2D vector diagramming and line-art",
            **page,
        })


    @mcp.tool()
    @tool_instruction(__file__, 'search_diagram_assets')
    @query_output
    def search_diagram_assets(
        query: str = "",
        category: str = "",
        max_width_mm: float = 0,
        max_depth_mm: float = 0,
        max_height_mm: float = 0,
        limit: int = 10,
        offset: int = 0, include_ids: StrictBool = False) -> str:
        return json.dumps(context.retrieval_store.search_assets(
            query=query,
            library_id="diagram_assets",
            category=category,
            max_width_mm=max_width_mm,
            max_depth_mm=max_depth_mm,
            max_height_mm=max_height_mm,
            limit=limit,
            offset=offset,
        ))


    @mcp.tool()
    @tool_instruction(__file__, 'get_diagram_asset')
    @query_output
    def get_diagram_asset(asset_id: str, include_ids: StrictBool = False) -> str:
        asset = context.retrieval_store.get_asset(asset_id, library_id="diagram_assets")
        if not asset:
            return json.dumps(error_payload(f"Unknown diagram asset_id: {asset_id}"))
        return json.dumps({"status": "success", "asset": asset})


    @mcp.tool()
    @tool_instruction(__file__, 'place_diagram_asset')
    def place_diagram_asset(
        asset_id: str,
        x: float = 0,
        y: float = 0,
        z: float = 0,
        rotation_degrees: float = 0,
        scale: float = 1,
    ) -> str:
        asset = context.diagram_asset_indexer.get(asset_id)
        if not asset:
            return json.dumps(error_payload(f"Unknown diagram asset_id: {asset_id}"))
        if not asset.get("file_available"):
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

        try:
            return context._send_and_receive(payload, timeout=90.0)
        except socket.timeout:
            return json.dumps(error_payload("Rhino diagram import timed out."))
        except Exception as exc:
            return json.dumps(error_payload(f"Diagram asset placement failed: {exc}"))

    return {
        "list_diagram_assets": list_diagram_assets,
        "search_diagram_assets": search_diagram_assets,
        "get_diagram_asset": get_diagram_asset,
        "place_diagram_asset": place_diagram_asset,
    }
