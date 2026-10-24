"""Public Sheet schemas, capability gate and reconciliation response envelopes."""
import asyncio
import importlib.util
import json
from pathlib import Path
import uuid

import pytest
from fastmcp import Client

from almond_mcp.retrieval_store import AlmondStore


SHEET_TOOLS = {"upsert_drawing_sheet", "get_drawing_sheet", "list_drawing_sheets",
               "sync_drawing_sheet", "remove_drawing_sheet"}


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    root = tmp_path_factory.mktemp("sheet-tools")
    source = Path(__file__).resolve().parents[3] / "src/mcp/almond_mcp/server.py"
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("RHINO_MCP_STATE_DB", str(root / "state.sqlite3"))
        for suffix in ("LIBRARY", "DRAWING_ASSET", "DIAGRAM_ASSET", "GENERATED_ASSET",
                       "DRAWING_RECIPE", "DRAFTING", "CAPSULE", "MATERIAL", "CONSTRUCTION"):
            patch.setenv(f"RHINO_MCP_{suffix}_DIR", str(root / suffix.lower()))
        spec = importlib.util.spec_from_file_location(f"sheet_server_{uuid.uuid4().hex}", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module


@pytest.fixture
def store(server, tmp_path, monkeypatch):
    result = AlmondStore(tmp_path / "sheets.sqlite3")
    monkeypatch.setattr(server, "retrieval_store", result)
    monkeypatch.setattr(server, "_send_and_receive", lambda *_: pytest.fail("Unexpected native call"))
    return result


@pytest.fixture
def arguments(store, tmp_path):
    return dict(expected_model_path=store._component_model_path(str(tmp_path / "drawings.3dm")),
                title="Level 1 plan", drawing_type="plan", scale_denominator=100.0,
                paper_mm=[420.0, 297.0], model_bounds_mm=[0.0, 0.0, 0.0, 20000.0, 10000.0, 0.0])


def native_sheet(request):
    fields = ("sheet_id", "title", "drawing_type", "scale_denominator", "paper_mm",
              "model_bounds_mm", "scene_ids", "component_ids", "plan_id")
    return dict(status="success", sheet=dict(
        {field: request[field] for field in fields}, complete=True,
        model_path=request["expected_model_path"],
        layout_id=request["layout_id"] or str(uuid.uuid5(uuid.NAMESPACE_URL, request["sheet_id"])),
    ))


@pytest.fixture
def wire(server, monkeypatch):
    def install(handler=native_sheet, capable=True):
        requests = []
        def send(payload):
            request = json.loads(payload)
            requests.append(request)
            if request["type"] == "get_rhino_context":
                return json.dumps(dict(status="success", capabilities={"drawing_sheets": 1} if capable else {}))
            return json.dumps(handler(request))
        monkeypatch.setattr(server, "_send_and_receive", send)
        return requests
    return install


def call(server, name, **arguments):
    tool = getattr(server, name)
    return json.loads(getattr(tool, "fn", tool)(**arguments))


def test_public_sheet_roundtrip_refs_filters_and_preserving_removal(server, store, arguments, wire, monkeypatch):
    scene = store.create_scene("Level 1")["scene_id"]
    plan = store.create_generation_plan("Draw", scope="drawing")
    requests = wire()
    created = call(server, "upsert_drawing_sheet", **arguments, plan_id=plan["plan_id"], scene_ids=[scene])
    assert created["status"] == "success" and created["sheet"]["live_verified"] is True
    sheet = created["sheet"]
    assert [request.get("action") for request in requests] == [None, "upsert"]
    listed = call(server, "list_drawing_sheets", plan_id=plan["plan_id"], scene_id=scene,
                  expected_model_path=arguments["expected_model_path"], limit=1)
    assert listed["total"] == 1 and listed["sheets"][0]["sheet_id"] == sheet["sheet_id"]
    cached = call(server, "get_drawing_sheet", sheet_id=sheet["sheet_id"])
    assert cached["sheet"]["live_verified"] is False
    assert len(requests) == 2
    def unregister(request):
        return dict(status="success", sheet_id=request["sheet_id"],
                    layout_id=request["layout_id"], model_path=request["expected_model_path"])
    requests = wire(unregister)
    removed = call(server, "remove_drawing_sheet", sheet_id=sheet["sheet_id"])
    assert removed["sheet"]["registration_status"] == "unregistered"
    assert [request.get("action") for request in requests] == [None, "unregister"]
    assert store.get_drawing_sheet(sheet["sheet_id"]) is None
    assert store.get_generation_plan(plan["plan_id"], revision=1) == plan


def test_sheet_capability_gate_sends_no_unknown_operation(server, store, arguments, wire):
    requests = wire(capable=False)
    response = call(server, "upsert_drawing_sheet", **arguments)
    assert response["status"] == "error" and "drawing_sheets=1" in response["message"]
    assert "requires_reconciliation" not in response
    assert len(requests) == 1 and requests[0]["type"] == "get_rhino_context"
    assert store.list_drawing_sheets()["total"] == 0


def test_sheet_timeout_returns_recovery_identity_and_inspection_never_replays(server, store, arguments, wire):
    saved = []
    def lost_reply(request):
        saved.append(native_sheet(request))
        raise TimeoutError("Layout response lost")
    requests = wire(lost_reply)
    response = call(server, "upsert_drawing_sheet", **arguments)
    assert response["status"] == "error" and response["requires_reconciliation"] is True
    assert response["error_code"] == "drawing_sheet_reconciliation_required"
    assert response["sheet_id"] == requests[1]["sheet_id"]
    assert response["expected_model_path"] == arguments["expected_model_path"]
    assert [request.get("action") for request in requests] == [None, "upsert"]
    assert store.list_drawing_sheets()["total"] == 0
    inspections = wire(lambda request: saved[0])
    recovered = call(server, "sync_drawing_sheet", expected_model_path=arguments["expected_model_path"],
                     sheet_id=response["sheet_id"])
    assert recovered["status"] == "success" and recovered["sheet"]["live_verified"] is True
    assert [request.get("action") for request in inspections] == [None, "inspect"]


def test_actual_sheet_mcp_schema_and_numeric_guards(server, store, arguments, wire):
    requests = wire()
    async def verify():
        async with Client(server.mcp) as client:
            tools = {tool.name: tool.model_dump(mode="json", by_alias=True, exclude_none=True)
                     for tool in await client.list_tools()}
            assert SHEET_TOOLS <= tools.keys()
            schema = tools["upsert_drawing_sheet"]["inputSchema"]
            assert schema["properties"]["scale_denominator"]["type"] == "number"
            assert schema["properties"]["paper_mm"]["items"]["type"] == "number"
            for name in ("get_drawing_sheet", "list_drawing_sheets"):
                assert tools[name]["annotations"]["readOnlyHint"] is True
            assert tools["remove_drawing_sheet"]["annotations"]["destructiveHint"] is False
            for change in ({"scale_denominator": True}, {"scale_denominator": "100"},
                           {"paper_mm": [True, 297]}, {"model_bounds_mm": ["0", 0, 0, 20000, 10000, 0]}):
                rejected = await client.call_tool("upsert_drawing_sheet", {**arguments, **change}, raise_on_error=False)
                assert rejected.is_error
            assert requests == []
            created = await client.call_tool("upsert_drawing_sheet", arguments)
            sheet = json.loads(created.structured_content["result"])["sheet"]
            read = await client.call_tool("get_drawing_sheet", {"sheet_id": sheet["sheet_id"]})
            assert json.loads(read.structured_content["result"])["sheet"]["live_verified"] is False
    asyncio.run(verify())
    assert [request.get("action") for request in requests] == [None, "upsert"]
