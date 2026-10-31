"""Guidance factories use isolated live context and retain offline library behavior."""
import asyncio
import base64
import inspect
import json
import struct
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.features.guidance.library import ConstructionLibrary, HistoryLibrary
from almond_mcp.features.guidance.tools import register


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONSTRUCTION_DIR = PROJECT_ROOT / "src/mcp/profiles/construction_system"
HISTORY_DIR = PROJECT_ROOT / "asset/history/Historyfiles"
DRAFTING_DIR = PROJECT_ROOT / "asset/drawing/Draftingfiles"


@pytest.fixture
def context():
    return SimpleNamespace(
        construction_library=ConstructionLibrary(str(CONSTRUCTION_DIR)),
        history_library=HistoryLibrary(str(HISTORY_DIR)),
        DRAFTING_LIBRARY_DIR=str(DRAFTING_DIR),
    )


def test_factory_registers_only_guidance_tools_and_preserves_schema(context):
    mcp = FastMCP("guidance-contract")
    exports = register(mcp, context)
    expected = {
        "get_modeling_guide": {"tool": ("string", "")},
        "get_construction_guidance": {
            "query": ("string", ""), "category": ("string", ""),
            "material": ("string", ""), "structure_type": ("string", ""),
            "span_m": ("number", 0.0), "include_reference_data": ("boolean", False),
        },
        "get_typology_narrative": {
            "query": ("string", ""), "construction_system": ("string", ""),
            "structure_type": ("string", ""), "limit": ("integer", 5),
        },
        "search_detail_sources": {"query": ("string", "")},
    }

    async def run():
        async with Client(mcp) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            assert set(tools) == set(exports) == set(expected)
            for name, fields in expected.items():
                if name != "get_modeling_guide":
                    fields = {**fields, "include_ids": ("boolean", False)}
                schema = tools[name].input_schema
                assert set(schema["properties"]) == set(fields) | ({"field_groups"} if "include_ids" in fields else set())
                if "include_ids" in fields:
                    assert schema["properties"]["field_groups"] == {"anyOf": [{"items": {"type": "string"}, "type": "array"}, {"type": "null"}], "default": None}
                assert not schema.get("required")
                for field, (kind, default) in fields.items():
                    assert schema["properties"][field]["type"] == kind
                    assert schema["properties"][field]["default"] == default
                assert tools[name].description.startswith(inspect.getdoc(exports[name]).split("\n\n")[0])
            assert tools["search_detail_sources"].annotations.read_only_hint is True
            assert tools["search_detail_sources"].annotations.open_world_hint is False
            result = await client.call_tool("search_detail_sources", {"query": "timber", "include_ids": True})
            assert "dataholz" in {source["source_id"] for source in result.structured_content["sources"]}
            construction = await client.call_tool(
                "get_construction_guidance", {"material": "S355", "structure_type": "beam", "span_m": 8.0, "include_ids": True})
            assert "steel-wide-flange-floor" in {system["system_id"] for system in json.loads(construction.content[0].text)["systems"]}
            history = await client.call_tool("get_typology_narrative", {"query": "skyscraper", "limit": 2})
            assert json.loads(history.content[0].text)["total"] >= 1

    asyncio.run(run())


def test_construction_filters_depths_and_reference_data(context):
    tools = register(FastMCP("construction"), context)
    result = json.loads(tools["get_construction_guidance"](
        material="S355", structure_type="beam", span_m=8.0, include_reference_data=True, include_ids=True, field_groups=["all"]))
    assert result["total"] == len(result["systems"]) > 0
    assert all(system["structural_material"] == "Steel" for system in result["systems"])
    floor = next(system for system in result["systems"] if system["system_id"] == "steel-wide-flange-floor")
    assert floor["fits_span"] is True
    assert next(rule for rule in floor["depth_guidance"] if rule["element"] == "beam")["suggested_depth_mm"] == 400
    assert floor["construction_detail"] == floor["name"]
    assert floor["construction_reference"] == {"kind": "construction_system", "id": floor["system_id"]}
    assert result["reference"]["live_loads_kpa"]["office"] > 0
    empty = json.loads(tools["get_construction_guidance"](query="nonexistent-system", include_ids=True, field_groups=["all"]))
    assert empty["total"] == 0 and empty["systems"] == [] and empty["hint"]


def test_construction_assessment_handles_unknown_and_implausible_spans(context):
    library = context.construction_library
    assert library.list(category="floor", query="glulam", material="timber", structure_type="beam")
    fitting = library.assess_span("beam", "S355", 8.0)
    assert fitting["matching_systems"] and not fitting["warnings"]
    outside = library.assess_span("beam", "Wood", 15.0)
    assert outside["warnings"] and not any(item.get("fits_span") for item in outside["matching_systems"])
    unknown = library.assess_span("membrane", "Wood", 10.0)
    assert unknown["matching_systems"] == [] and unknown["warnings"]
    unmeasured = library.assess_span("beam", "Steel", None)
    assert unmeasured["matching_systems"]
    assert all("fits_span" not in item for item in unmeasured["matching_systems"])
    assert library.get("nonexistent-system") is None


def test_typology_filters_keep_total_and_minimum_limit(context):
    library = context.history_library
    towers = library.list(construction_system="steel-column-frame", structure_type="frame")
    assert towers and all("steel-column-frame" in entry["related_construction_systems"] for entry in towers)
    assert any(entry["typology_id"] == "nomadic-lattice-tent" for entry in library.list(structure_type="membrane"))
    tools = register(FastMCP("history"), context)
    result = json.loads(tools["get_typology_narrative"](query="courtyard", limit=0, include_ids=True, field_groups=["all"]))
    assert result["total"] >= 2 and len(result["entries"]) == 1
    assert result["source"] == library.source
    assert library.get(result["entries"][0]["typology_id"])
    assert library.get("nonexistent-typology") is None


def test_factory_reads_replaced_libraries_and_paths_without_cross_server_leak(context, tmp_path):
    first = register(FastMCP("first"), context)
    second_context = SimpleNamespace(**vars(context))
    second = register(FastMCP("second"), second_context)
    context.construction_library = SimpleNamespace(list=lambda **kwargs: [], source="replacement", reference={"test": True})
    context.history_library = SimpleNamespace(list=lambda **kwargs: [], source="replacement history")
    (tmp_path / "sources.json").write_text(json.dumps({"scope": "replacement scope", "sources": []}), encoding="utf-8")
    context.DRAFTING_LIBRARY_DIR = str(tmp_path)
    assert json.loads(first["get_construction_guidance"](include_reference_data=True, include_ids=True, field_groups=["all"]))["reference"] == {"test": True}
    assert json.loads(first["get_construction_guidance"](include_ids=True, field_groups=["all"]))["source"] == "replacement"
    assert json.loads(first["get_typology_narrative"](include_ids=True, field_groups=["all"]))["source"] == "replacement history"
    assert first["search_detail_sources"](include_ids=True, field_groups=["all"])["scope"] == "replacement scope"
    assert json.loads(second["get_construction_guidance"](include_ids=True, field_groups=["all"]))["total"] >= 15
    assert json.loads(second["get_typology_narrative"](include_ids=True, field_groups=["all"]))["total"] >= 12
    assert second["search_detail_sources"](include_ids=True, field_groups=["all"])["sources"]


def test_detail_source_search_ranks_matches_and_breaks_ties_by_id(context, tmp_path):
    data = {"scope": "research candidates", "sources": [
        {"source_id": "z", "title": "Timber", "tags": [], "formats": ["PDF"]},
        {"source_id": "a", "title": "Timber", "tags": [], "formats": ["PDF"]},
        {"source_id": "b", "title": "Concrete", "tags": [], "formats": ["DWG"]},
    ]}
    (tmp_path / "sources.json").write_text(json.dumps(data), encoding="utf-8")
    context.DRAFTING_LIBRARY_DIR = str(tmp_path)
    search = register(FastMCP("sources"), context)["search_detail_sources"]
    assert [source["source_id"] for source in search("PDF concrete", include_ids=True, field_groups=["all"])["sources"]] == ["a", "b", "z"]
    assert search("TIMBER pdf", field_groups=["metadata"])["sources"][0]["matched_terms"] == ["pdf", "timber"]
    assert search("unmatched")["sources"] == []
    assert len(search()["sources"]) == 3


def test_korean_catalogue_query_returns_matching_sources_and_search_evidence(context):
    search = register(FastMCP("korean-sources"), context)["search_detail_sources"]
    result = search("목재 접합", include_ids=True)
    assert result["status"] == "success"
    assert result["query"] == "목재 접합"
    assert set(result["query_terms"]) == {"목재", "접합"}
    assert {"timber", "wood", "junction"} <= set(result["expanded_terms"])
    by_id = {source["source_id"]: source for source in result["sources"]}
    assert "junction" in by_id["dataholz"]["matched_terms"]
    assert "arcat" not in by_id
    assert all(source["matched_terms"] for source in result["sources"])


def test_unicode_source_query_preserves_unmapped_korean_and_mixed_input(context, tmp_path):
    data = {"scope": "source directories", "sources": [
        {"source_id": "korean", "title": "한옥 접합 자료", "tags": [], "formats": ["PDF"]},
        {"source_id": "wood", "title": "Timber junctions", "tags": [], "formats": ["DXF"]},
        {"source_id": "other", "title": "Concrete", "tags": [], "formats": ["DWG"]},
    ]}
    (tmp_path / "sources.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    context.DRAFTING_LIBRARY_DIR = str(tmp_path)
    search = register(FastMCP("unicode-sources"), context)["search_detail_sources"]
    result = search("한옥", include_ids=True)
    assert [source["source_id"] for source in result["sources"]] == ["korean"]
    assert result["sources"][0]["matched_terms"] == ["한옥"]
    assert result["expanded_terms"] == []
    mixed = search("목재 ＤＷＧ", include_ids=True)
    assert {source["source_id"] for source in mixed["sources"]} == {"wood", "other"}
    assert "dwg" in mixed["query_terms"]


@pytest.mark.parametrize("query", ["존재하지않는자료", "🧱!?", "___"])
def test_nonempty_unmatched_or_unsearchable_query_never_returns_all_sources(context, query):
    search = register(FastMCP("query-state"), context)["search_detail_sources"]
    result = search(query)
    assert result["query"] == query
    assert result["sources"] == []
    if query == "존재하지않는자료":
        assert result["status"] == "success" and result["query_terms"]
    else:
        assert result["status"] == "error" and result["error_code"] == "invalid_query"
    assert len(search("  ")["sources"]) == 6


@pytest.mark.parametrize("library_class, collection", [(ConstructionLibrary, "systems"), (HistoryLibrary, "entries")])
def test_libraries_tolerate_missing_malformed_and_incomplete_manifests(library_class, collection, tmp_path, capsys):
    missing = library_class(str(tmp_path))
    assert getattr(missing, collection) == {} and missing.source == ""
    (tmp_path / "manifest.json").write_text("{", encoding="utf-8")
    malformed = library_class(str(tmp_path))
    assert getattr(malformed, collection) == {} and "unreadable" in capsys.readouterr().err
    (tmp_path / "manifest.json").write_text(json.dumps({collection: [{"name": "incomplete"}]}), encoding="utf-8")
    assert getattr(library_class(str(tmp_path)), collection) == {}
