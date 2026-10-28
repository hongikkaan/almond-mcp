"""Exercise the extracted egress factory against the shipped rule tables."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastmcp import FastMCP

from almond_mcp.features.egress.tools import register


MANIFEST = (Path(__file__).resolve().parents[3] / "src" / "mcp" / "profiles"
            / "construction_system" / "manifest.json")


@pytest.fixture
def feature():
    reference = json.loads(MANIFEST.read_text(encoding="utf-8"))["reference"]
    context = SimpleNamespace(construction_library=SimpleNamespace(reference=reference))
    mcp = FastMCP("egress-feature-test")
    exports = register(mcp, context)
    tool = exports["check_egress"]
    fn = getattr(tool, "fn", tool)
    return mcp, context, lambda **kwargs: json.loads(fn(**kwargs))


def exits(width=1120):
    return [{"name": "stair A", "x_mm": 11420, "y_mm": 12600, "width_mm": width},
            {"name": "stair B", "x_mm": 30700, "y_mm": 12600, "width_mm": width}]


def checks(result):
    return {item["check"]: item for item in result["checks"]}


def test_registered_tower_check_uses_original_contract(feature):
    mcp, _, run = feature
    tools = asyncio.run(mcp.list_tools())
    assert [tool.name for tool in tools] == ["check_egress"]
    assert set(tools[0].parameters["properties"]) == {
        "plate_bounds_mm", "exits", "occupancy", "stories", "sprinklered",
        "net_area_m2", "travel_distances_m", "dead_end_m",
    }
    result = run(plate_bounds_mm=[0, 0, 40000, 24000], exits=exits(), stories=6,
                 travel_distances_m=[21.2, 15.1], dead_end_m=11.4)
    assert result["passed"] is True
    assert result["occupant_load"] == 104
    assert result["area_m2"] == result["gross_area_m2"] == 960
    assert len(result["checks"]) == 6
    assert checks(result)["exit_separation_m"]["provided"] == 19.28
    assert result["warnings"] == []
    assert "governing code" in result["source_note"]


def test_single_exit_multistory_and_narrow_close_stairs_fail(feature):
    _, _, run = feature
    single = run(plate_bounds_mm=[0, 0, 24000, 16000], exits=exits()[:1], stories=3)
    assert single["occupant_load"] == 42
    assert checks(single)["exit_count"] == {
        "check": "exit_count", "required": 2, "provided": 1, "passed": False,
        "basis": "occupant-load tiers; multi-story business needs two (IBC-typical)",
    }
    assert "exit_separation_m" not in checks(single)
    close = exits()
    close[1].update(x_mm=14000, width_mm=900)
    result = run(plate_bounds_mm=[0, 0, 40000, 24000], exits=close, stories=6)
    assert result["passed"] is False
    assert checks(result)["exit_separation_m"]["passed"] is False
    assert checks(result)["min_exit_width_mm"]["passed"] is False
    assert result["warnings"] == ["Exits below minimum width: stair B."]


@pytest.mark.parametrize("load,required", [(49, 1), (50, 2), (500, 2), (501, 3),
                                          (1000, 3), (1001, 4)])
def test_occupant_load_tier_boundaries(feature, load, required):
    _, _, run = feature
    # Storage's 46.5 factor keeps these tier boundary areas exactly representable.
    result = run(plate_bounds_mm=[0, 0, 1000, 1000], exits=exits(),
                 occupancy="storage", net_area_m2=load * 46.5)
    assert result["occupant_load"] == load
    assert checks(result)["exit_count"]["required"] == required
    assert checks(result)["exit_count"]["passed"] is (required <= 2)


@pytest.mark.parametrize("load,minimum,passed", [(49, 915, True), (50, 1120, False)])
def test_stair_minimum_changes_at_fifty_occupants(feature, load, minimum, passed):
    _, _, run = feature
    result = run(plate_bounds_mm=[40000, 24000, 0, 0], exits=exits(915),
                 occupancy="storage", stories=2, net_area_m2=load * 46.5)
    assert result["gross_area_m2"] == 960
    assert checks(result)["min_exit_width_mm"]["required"] == minimum
    assert checks(result)["min_exit_width_mm"]["passed"] is passed
    assert checks(result)["total_egress_width_mm"]["required"] == round(load * 7.6)


def test_travel_and_dead_end_limits_include_equality(feature):
    _, _, run = feature
    kwargs = dict(plate_bounds_mm=[0, 0, 40000, 24000], exits=exits(), stories=2,
                  travel_distances_m=[61.0], dead_end_m=6.1)
    at_limit = run(sprinklered=False, **kwargs)
    assert checks(at_limit)["max_travel_distance_m"]["passed"] is True
    assert checks(at_limit)["max_dead_end_m"]["passed"] is True
    kwargs.update(travel_distances_m=[61.01], dead_end_m=6.11)
    above = run(sprinklered=False, **kwargs)
    assert checks(above)["max_travel_distance_m"]["passed"] is False
    assert checks(above)["max_dead_end_m"]["passed"] is False
    sprinklered = run(sprinklered=True, **kwargs)
    assert checks(sprinklered)["max_travel_distance_m"]["passed"] is True
    assert checks(sprinklered)["max_dead_end_m"]["passed"] is True
    nonbusiness = run(occupancy="storage", **kwargs)
    assert "'storage' occupancy" in nonbusiness["warnings"][0]


@pytest.mark.parametrize("kwargs,message", [
    ({"plate_bounds_mm": [0, 0, 1000], "exits": exits()}, "plate_bounds_mm must be"),
    ({"plate_bounds_mm": [0, 0, 1000, 1000], "exits": []}, "exits must not be empty"),
    ({"plate_bounds_mm": [0, 0, 1000, 1000], "exits": exits(),
      "occupancy": "spaceship"}, "Unknown occupancy 'spaceship'"),
])
def test_invalid_input_returns_existing_errors(feature, kwargs, message):
    _, _, run = feature
    result = run(**kwargs)
    assert result["status"] == "error"
    assert message in result["message"]


def test_library_is_resolved_from_context_at_call_time(feature):
    _, context, run = feature
    context.construction_library = SimpleNamespace(reference={})
    assert run(plate_bounds_mm=[0, 0, 1000, 1000], exits=exits()) == {
        "status": "error", "message": "egress_rules missing from the construction manifest.",
    }
