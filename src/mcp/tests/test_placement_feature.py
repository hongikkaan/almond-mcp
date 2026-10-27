"""Extracted placement factories and SQL, with disposable SQLite regressions."""
import asyncio
import json

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.feature_context import FeatureContext
from almond_mcp.features.placement.store import PlacementStore
from almond_mcp.features.placement.tools import register
from almond_mcp.retrieval_store import AlmondStore
import test_components as component_regressions
import test_retrieval_store as ledger_regressions


# Before facade cutover, the extracted methods must win over the old definitions.
if issubclass(AlmondStore, PlacementStore):
    ExtractedPlacementStore = AlmondStore
else:
    class ExtractedPlacementStore(PlacementStore, AlmondStore):
        pass


@pytest.fixture
def store(tmp_path):
    result = ExtractedPlacementStore(tmp_path / "placement.sqlite3")
    result.sync_assets([
        {"asset_id": "cube", "dimensions_mm": {"width": 100, "depth": 100, "height": 100}},
        {"asset_id": "rectangle", "dimensions_mm": {"width": 200, "depth": 100, "height": 50}},
    ], library_id="fixture")
    return result


@pytest.mark.parametrize("regression", [
    "test_scene_revisions_and_rtree_collisions",
    "test_upsert_room_by_name_updates_instead_of_duplicating",
    "test_instance_z_defaults_to_room_floor",
    "test_remove_instance_and_room",
])
def test_existing_placement_regressions_use_extracted_methods(monkeypatch, regression):
    monkeypatch.setattr(ledger_regressions, "AlmondStore", ExtractedPlacementStore)
    case = ledger_regressions.SceneLedgerFixesTests(regression)
    case.setUp()
    try:
        getattr(case, regression)()
    finally:
        case.tearDown()


@pytest.mark.parametrize("regression", [
    "test_additive_component_schema_preserves_legacy_rooms_instances_and_revisions",
    "test_direct_store_legacy_ids_cannot_cross_scenes_and_instance_delete_cleans_rtree",
])
def test_existing_scene_boundaries_use_extracted_methods(store, monkeypatch, regression):
    monkeypatch.setattr(component_regressions, "AlmondStore", ExtractedPlacementStore)
    getattr(component_regressions, regression)(store)


def test_touching_faces_rotation_and_containment_use_cached_world_bounds(store):
    scene = store.create_scene("Boundary checks")["scene_id"]
    room = store.upsert_room(scene, "Room", [0, 0, 0, 400, 300, 100])["room_id"]
    first = store.upsert_instance(scene, "cube", 50, 50, room_id=room)
    second = store.upsert_instance(scene, "cube", 150, 50, room_id=room)
    report = store.validate_scene(scene)
    assert report["passed"] is True  # Equal faces touch without positive-volume overlap.
    assert report["coverage"]["room_containment"] == "instances_with_assigned_room"
    assert report["passed_scope"] == "legacy_asset_instances" and report["live_verified"] is False
    moved = store.upsert_instance(scene, "rectangle", 51, 101, rotation_degrees=90,
                                  room_id=room, instance_id=second["instance_id"])
    assert moved["world_aabb_mm"]["min"] == pytest.approx([1, 1, 0], abs=1e-12)
    assert moved["world_aabb_mm"]["max"] == pytest.approx([101, 201, 50])
    report = store.validate_scene(scene)
    assert report["collision_count"] == 1 and report["outside_room_count"] == 0
    assert set(report["collisions"][0]["instances"]) == {first["instance_id"], second["instance_id"]}
    store.upsert_instance(scene, "cube", 390, 290, room_id=room, instance_id=second["instance_id"])
    assert store.validate_scene(scene)["outside_room"][0]["failing_axes"] == ["x", "y"]


def test_revision_failure_rolls_back_placement_and_rtree(store, monkeypatch):
    scene = store.create_scene("Transaction checks")["scene_id"]
    room = store.upsert_room(scene, "Room", [0, 0, 0, 1000, 1000, 1000])["room_id"]
    placed = store.upsert_instance(scene, "cube", 500, 500, room_id=room)
    before = component_regressions.snapshot(store)

    def fail_revision(*args, **kwargs):
        raise RuntimeError("revision write failed")

    monkeypatch.setattr(store, "_record_revision", fail_revision)
    operations = [
        lambda: store.upsert_room(scene, "Room", [0, 0, 0, 2000, 2000, 2000], room_id=room),
        lambda: store.upsert_instance(scene, "cube", 700, 700, instance_id=placed["instance_id"]),
        lambda: store.remove_instance(scene, placed["instance_id"]),
        lambda: store.remove_room(scene, room),
    ]
    for operation in operations:
        with pytest.raises(RuntimeError, match="revision write failed"):
            operation()
        assert component_regressions.snapshot(store) == before


def call(exports, tool_name, **arguments):
    function = exports[tool_name]
    return json.loads(getattr(function, "fn", function)(**arguments))


def test_factory_reads_rebound_store_and_preserves_all_five_tool_responses(store, tmp_path):
    original = store.create_scene("Original")["scene_id"]
    namespace = {"retrieval_store": store}
    exports = register(FastMCP("Placement fixture"), FeatureContext(namespace))
    replacement = ExtractedPlacementStore(tmp_path / "replacement.sqlite3")
    replacement.sync_assets([
        {"asset_id": "cube", "dimensions_mm": {"width": 100, "depth": 100, "height": 100}},
    ], library_id="fixture")
    scene = replacement.create_scene("Replacement")["scene_id"]
    namespace["retrieval_store"] = replacement
    room = call(exports, "upsert_design_room", scene_id=scene, name="Upper floor",
                bounds_mm=[0, 0, 18000, 1000, 1000, 21000])
    assert room["status"] == "success"
    instance = call(exports, "register_scene_instance", scene_id=scene, asset_id="cube",
                    x_mm=500, y_mm=500, room_id=room["room_id"])
    assert instance["status"] == "success" and "world_aabb_mm" not in instance
    assert replacement.scene_instances(scene)[0]["min_z"] == 18000
    report = call(exports, "validate_scene_layout", scene_id=scene, detail_limit=1)
    assert report["status"] == "success" and report["passed"] is True
    removed = call(exports, "remove_scene_instance", scene_id=scene, instance_id=instance["instance_id"])
    assert removed["status"] == "success" and removed["revision"] > instance["revision"]
    removed_room = call(exports, "remove_design_room", scene_id=scene, room_id=room["room_id"])
    assert removed_room["status"] == "success" and removed_room["orphaned_instances"] == 0
    assert store.get_scene(original)["revision"] == 0
    assert replacement.scene_instances(scene) == []


@pytest.mark.parametrize("name,arguments", [
    ("upsert_design_room", {"name": "Room", "bounds_mm": [0, 0, 0, 1, 1, 1]}),
    ("register_scene_instance", {"asset_id": "cube", "x_mm": 0, "y_mm": 0}),
    ("remove_scene_instance", {"instance_id": "missing"}),
    ("remove_design_room", {"room_id": "missing"}),
    ("validate_scene_layout", {}),
])
def test_factory_retains_json_error_envelopes(store, name, arguments):
    exports = register(FastMCP("Placement errors"), FeatureContext({"retrieval_store": store}))
    result = call(exports, name, scene_id="unknown-scene", **arguments)
    assert result["status"] == "error" and "unknown-scene" in result["message"]


def test_factory_registers_public_schema_and_protocol_call(store):
    mcp = FastMCP("Placement protocol")
    exports = register(mcp, FeatureContext({"retrieval_store": store}))
    scene = store.create_scene("Protocol")["scene_id"]

    async def verify():
        async with Client(mcp) as client:
            tools = {tool.name: tool.model_dump(mode="json", by_alias=True)
                     for tool in await client.list_tools()}
            assert set(tools) == set(exports) == {
                "upsert_design_room", "register_scene_instance", "remove_scene_instance",
                "remove_design_room", "validate_scene_layout",
            }
            room = tools["upsert_design_room"]["inputSchema"]
            assert room["required"] == ["scene_id", "name", "bounds_mm"]
            assert room["properties"]["room_id"]["default"] == ""
            instance = tools["register_scene_instance"]["inputSchema"]
            assert instance["required"] == ["scene_id", "asset_id", "x_mm", "y_mm"]
            for key, value in {"z_mm": None, "rotation_degrees": 0, "scale": 1,
                               "room_id": "", "instance_id": "", "locked": False, "rhino_guid": ""}.items():
                assert instance["properties"][key]["default"] == value
            layout = tools["validate_scene_layout"]["inputSchema"]
            assert layout["properties"]["detail_limit"]["default"] == 50
            assert all("context" not in tool["inputSchema"]["properties"] for tool in tools.values())
            result = await client.call_tool("validate_scene_layout", {"scene_id": scene})
            assert result.is_error is False
            payload = json.loads(result.content[0].text)
            assert payload["status"] == "success" and payload["passed_scope"] == "legacy_asset_instances"

    asyncio.run(verify())
