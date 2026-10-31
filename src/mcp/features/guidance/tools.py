"""Register construction, typology and detail-source guidance tools."""
from almond_mcp.instruction_text import tool_instruction, read_instruction
from almond_mcp.query_output import query_output, validate_field_groups
from almond_mcp.features.guidance.output import GROUPS, project
from almond_mcp.features.guidance.source_search import search_sources

from pydantic import StrictBool
from fastmcp.tools import ToolResult
from mcp.types import TextContent
from almond_mcp.modeling_guidance import read_guide
import json
from pathlib import Path


def register(mcp, context):
    """Register guidance tools against the calling server's live context."""

    @mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False})
    @tool_instruction(__file__, 'get_modeling_guide')
    def get_modeling_guide(tool: str = "") -> ToolResult:
        return ToolResult(content=[TextContent(type="text", text=json.dumps(read_guide(tool), ensure_ascii=False))])

    @mcp.tool()
    @tool_instruction(__file__, 'get_construction_guidance')
    @query_output
    def get_construction_guidance(
        query: str = "",
        category: str = "",
        material: str = "",
        structure_type: str = "",
        span_m: float = 0.0,
        include_reference_data: bool = False, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        validate_field_groups(field_groups, GROUPS)
        systems = context.construction_library.list(
            category=category, query=query, material=material,
            structure_type=structure_type)
        payload: dict = {
            "total": len(systems),
            "source": context.construction_library.source,
            "systems": [],
        }
        for system in systems:
            card = dict(system)
            card["construction_detail"] = system["name"]
            card["construction_reference"] = {"kind": "construction_system", "id": system["system_id"]}
            if span_m > 0:
                lo, hi = system["span_range_m"]
                if hi > 0:
                    card["fits_span"] = bool(lo <= span_m <= hi)
                    depths = [
                        {"element": rule["element"],
                         "suggested_depth_mm": round(span_m * 1000 / rule["span_ratio"]),
                         "rule": f"span/{rule['span_ratio']}"}
                        for rule in system.get("depth_rules", [])
                        if rule.get("span_ratio")
                    ]
                    if depths:
                        card["depth_guidance"] = depths
            payload["systems"].append(card)
        if include_reference_data:
            payload["reference"] = context.construction_library.reference
        if not systems:
            payload["hint"] = (read_instruction(__file__, 'response-732'))
        return json.dumps(project(payload, field_groups))

    @mcp.tool()
    @tool_instruction(__file__, 'get_typology_narrative')
    @query_output
    def get_typology_narrative(
        query: str = "",
        construction_system: str = "",
        structure_type: str = "",
        limit: int = 5, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        validate_field_groups(field_groups, GROUPS)
        entries = context.history_library.list(query=query,
                                       construction_system=construction_system,
                                       structure_type=structure_type)
        return json.dumps(project({
            "total": len(entries),
            "entries": entries[:max(1, limit)],
            "source": context.history_library.source,
        }, field_groups))

    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
    @tool_instruction(__file__, 'search_detail_sources')
    @query_output
    def search_detail_sources(query: str = "", include_ids: StrictBool = False, field_groups: list[str] | None = None) -> dict:
        validate_field_groups(field_groups, GROUPS)
        data = json.loads((Path(context.DRAFTING_LIBRARY_DIR)/"sources.json").read_text(encoding="utf-8"))
        return project({"scope": data["scope"], **search_sources(data["sources"], query)}, field_groups)

    return {
        "get_modeling_guide": get_modeling_guide,
        "get_construction_guidance": get_construction_guidance,
        "get_typology_narrative": get_typology_narrative,
        "search_detail_sources": search_detail_sources,
    }
