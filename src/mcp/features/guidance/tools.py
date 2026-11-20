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
        """Almond 작업의 기본 지침과 활동별 지침을 조회합니다. policy를 생략하면 기본 지침, 공통 도구 이름과 available_policies를 반환하며, 작업에 필요한 지침을 policy로 선택해 읽습니다.

        basic 또는 빈 값은 기본 지침과 공통 도구 이름을 반환합니다. metadata는 User Text·UserDictionary를 편집하기 전 확인하는 지침(text)과 객체 키 사전(policy)을 함께 반환합니다. rhino_scripting은 내장 Rhino 스크립팅 참고자료, rhinocode는 코드·명령 실행 지침입니다. spatial_modeling, observation, drawing, feedback_reporting은 각 활동의 판단 기준입니다.

        선택에 따라 본문은 text, policy 또는 scripting_skill에 담깁니다. source_refs에서 출처와 해시를 확인하고 같은 guide_version에서 이미 읽은 지침은 재사용할 수 있습니다. 개별 도구의 호출법은 해당 도구의 공개 설명과 스키마를 확인합니다.

        Args:
            policy: 생략 또는 빈 문자열은 basic. 선택값의 용도는 available_policies 참고.
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
        """건축 구법을 비교하고 선택할 참고 자료를 조회합니다.

        Args:
            query: 자유 텍스트 필터입니다(예: "glulam", "longspan", "bearing wall").
            category: "floor", "wall", "roof", "foundation" 중 하나입니다. 비워 두면 모두 포함합니다.
            material: analysis_04-validate_structure tool에서 사용하는 이름: "Wood", "Steel", "Concrete".
            structure_type: analysis_04-validate_structure tool의 유형입니다("beam", "truss", "shell", "frame", "canopy", "gridshell", "membrane", "highrise").
            span_m: 0보다 크면 반환되는 각 시스템이 fits_span과 경간 비율 규칙에 따른 권장 부재 깊이를 보고합니다.
            include_reference_data: load_kn 입력을 정하는 데 사용할 용도별 활하중(kPa)과 재료 밀도(kg/m3)도 반환합니다.
            include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
            field_groups: 상세 그룹: rules, narrative, source, metadata, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
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
        """건축 유형의 서사와 선례를 조회합니다.

        Args:
            query: 자유 텍스트입니다(예: "courtyard", "skyscraper", "timber hall").
            construction_system: 구법 라이브러리의 system_id와 관련된 항목으로 필터링합니다(예: "steel-column-frame").
            structure_type: analysis_04-validate_structure tool의 유형으로 필터링합니다("shell", "truss", "frame", "membrane" 등).
            limit: 반환할 최대 항목 수입니다. 기본값은 5입니다.
            include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
            field_groups: 상세 그룹: rules, narrative, source, metadata, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
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
        """건축 자료 디렉터리의 metadata를 검색합니다.

        Args:
            query: 자유 텍스트 검색어입니다. 비워 두면 텍스트 필터를 적용하지 않습니다.
            include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
            field_groups: 상세 그룹: rules, narrative, source, metadata, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
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
