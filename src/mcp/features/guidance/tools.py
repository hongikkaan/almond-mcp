"""Register construction, typology and detail-source guidance tools."""
from almond_mcp.tool_declarations import public_tool
from almond_mcp.query_output import query_output, validate_field_groups
from almond_mcp.features.guidance.output import GROUPS, project
from almond_mcp.features.guidance.source_search import search_sources

from pydantic import StrictBool
from fastmcp.tools import ToolResult
from mcp.types import TextContent
from almond_mcp.modeling_guidance import PolicyName, read_policy
import json
from pathlib import Path


def register(mcp, context):
    """Register guidance tools against the calling server's live context."""

    @public_tool(mcp, wrapped=False, annotations={'readOnlyHint': True, 'destructiveHint': False, 'openWorldHint': False})
    def get_policy(policy: PolicyName = "") -> ToolResult:
        """Almond 도구와 기술 참고 자료 조회. policy를 생략하면 공개 도구 목록과 참고 자료 종류를 반환.

        metadata는 User Text 등 객체 메타데이터 키 사전, rhino_scripting은 내장 스크립팅 자료, rhinocode는 코드·명령 실행 지침.

        같은 guide_version에서 이미 읽은 지침은 재사용할 수 있다.

        Args:
            policy: 생략하거나 비워 두면 basic(공개 도구 목록). 참고 자료 종류는 available_policies 참고.
        """
        value = read_policy(policy)
        return ToolResult(content=[TextContent(type="text", text=json.dumps(value, ensure_ascii=False))], structured_content=value)

    @public_tool(mcp, wrapped=True)
    @query_output
    def get_construction_guidance(
        query: str = "",
        category: str = "",
        material: str = "",
        structure_type: str = "",
        span_m: float = 0.0,
        include_reference_data: bool = False, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        """건축 구법 비교·선정을 위한 참고 자료 조회.

        Args:
            query: 예: `glulam`, `longspan`, `bearing wall`.
            category: floor, wall, roof, foundation 중 선택. 빈 값은 전체 분류.
            material: analysis_02-validate_structure tool과 같은 재료명. `Wood`, `Steel`, `Concrete`.
            structure_type: analysis_02-validate_structure tool과 같은 유형. `beam`, `truss`, `shell`, `frame`, `canopy`, `gridshell`, `membrane`, `highrise`.
            span_m: 0보다 크면 시스템별 `fits_span`과 경험칙에 따른 권장 부재 깊이를 계산.
            include_reference_data: `load_kn` 산정에 참고할 용도별 활하중(kPa)과 재료 밀도(kg/m³)를 포함.
            field_groups: `rules`, `narrative`, `source`, `metadata`, `audit`, `all`. 생략하거나 비우면 요약 반환.
        """
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
            payload["hint"] = ('No system matched. Loosen the filters, or call with no arguments to list all systems.')
        return json.dumps(project(payload, field_groups))

    @public_tool(mcp, wrapped=True)
    @query_output
    def get_typology_narrative(
        query: str = "",
        construction_system: str = "",
        structure_type: str = "",
        limit: int = 5, include_ids: StrictBool = False, field_groups: list[str] | None = None) -> str:
        """건축 유형의 서사와 선례 조회.

        Args:
            query: 예: `courtyard`, `skyscraper`, `timber hall`.
            construction_system: 구법 라이브러리의 `system_id` 기준 필터. 예: `steel-column-frame`.
            structure_type: analysis_02-validate_structure tool의 유형으로 필터링. 예: `shell`, `truss`, `frame`, `membrane`.
            field_groups: `rules`, `narrative`, `source`, `metadata`, `audit`, `all`. 생략하거나 비우면 요약 반환.
        """
        validate_field_groups(field_groups, GROUPS)
        entries = context.history_library.list(query=query,
                                       construction_system=construction_system,
                                       structure_type=structure_type)
        return json.dumps(project({
            "total": len(entries),
            "entries": entries[:max(1, limit)],
            "source": context.history_library.source,
        }, field_groups))

    @public_tool(mcp, wrapped=False, annotations={'readOnlyHint': True, 'openWorldHint': False})
    @query_output
    def search_detail_sources(query: str = "", include_ids: StrictBool = False, field_groups: list[str] | None = None) -> dict:
        """건축 자료 디렉터리의 메타데이터 검색.

        Args:
            field_groups: `rules`, `narrative`, `source`, `metadata`, `audit`, `all`. 생략하거나 비우면 요약 반환.
        """
        validate_field_groups(field_groups, GROUPS)
        data = json.loads((Path(context.DRAFTING_LIBRARY_DIR)/"sources.json").read_text(encoding="utf-8"))
        return project({"scope": data["scope"], **search_sources(data["sources"], query)}, field_groups)

    return {
        "get_policy": get_policy,
        "get_construction_guidance": get_construction_guidance,
        "get_typology_narrative": get_typology_narrative,
        "search_detail_sources": search_detail_sources,
    }
