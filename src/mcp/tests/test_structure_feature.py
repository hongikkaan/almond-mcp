"""Contracts for extracted structural tools, history and compatibility imports.

Bridge replies are test data; these tests never contact or modify Rhino.
"""
import asyncio
import importlib
import inspect
import json
from pathlib import Path

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.feature_context import FeatureContext
from almond_mcp.features.structure import tools
from almond_mcp.features.structure.store import StructureStore
from almond_mcp.retrieval_store import AlmondStore
from test_capsules import _load_server
import test_asset_load_tools as asset_regressions
import test_retrieval_store as store_regressions
import test_structure_view as view_regressions


if issubclass(AlmondStore, StructureStore):
    ExtractedStore = AlmondStore
else:
    class ExtractedStore(StructureStore, AlmondStore):
        """Use moved methods with the existing shared schema/connection lifecycle."""


class StructureContext(FeatureContext):
    if not hasattr(FeatureContext, "set_state"):
        def set_state(self, name, value):
            # Pre-cutover fallback; integrated tests use the shared implementation.
            self._namespace[name] = value


@pytest.fixture
def extracted_server(monkeypatch, tmp_path):
    capsule_dir = tmp_path / "capsules"
    capsule_dir.mkdir()
    server = _load_server(monkeypatch, tmp_path, capsule_dir)
    server.retrieval_store = ExtractedStore(server.retrieval_store.database_path)
    server.mcp = FastMCP("Extracted structure")
    server.__dict__.update(tools.register(server.mcp, StructureContext(server.__dict__)))
    return server


@pytest.mark.parametrize("regression", [
    view_regressions.test_sends_structure_view_request,
    view_regressions.test_display_only_update_and_reveal_clamp,
    view_regressions.test_clear_needs_no_guids,
    view_regressions.test_rejects_missing_guids_and_bad_colour,
    asset_regressions.test_validate_with_rhino_asset_loads,
    asset_regressions.test_validate_with_scene_ledger_placements,
    asset_regressions.test_asset_loads_need_native_and_a_capable_bridge,
    asset_regressions.test_visualize_with_asset_loads_draws_load_points,
])
def test_existing_tool_regressions_on_extracted_factory(regression, extracted_server, monkeypatch):
    regression(extracted_server, monkeypatch)


def test_existing_history_roundtrip_on_extracted_store(monkeypatch):
    monkeypatch.setattr(store_regressions, "AlmondStore", ExtractedStore)
    case = store_regressions.ValidationHistoryTests("test_record_and_list_validation_runs")
    result = case.run()
    assert result.wasSuccessful(), (result.failures, result.errors)


def test_tool_schemas_and_documentation_are_preserved(monkeypatch, tmp_path):
    capsule_dir = tmp_path / "capsules"
    capsule_dir.mkdir()
    original = _load_server(monkeypatch, tmp_path, capsule_dir)
    mcp = FastMCP("Extracted schemas")
    exports = tools.register(mcp, StructureContext(original.__dict__))
    public = {name for name in exports if not name.startswith("_")}

    async def schemas(server):
        async with Client(server) as client:
            return {tool.name: tool.model_dump() for tool in await client.list_tools()
                    if tool.name in public}

    assert asyncio.run(schemas(mcp)) == asyncio.run(schemas(original.mcp))
    for name, extracted in exports.items():
        before = getattr(original, name)
        assert inspect.signature(extracted) == inspect.signature(before)
        assert inspect.getdoc(extracted) == inspect.getdoc(before)


def test_rebinding_and_overlay_state_remain_per_server(extracted_server, monkeypatch, tmp_path):
    first = extracted_server
    capsule_dir = tmp_path / "other-capsules"
    capsule_dir.mkdir()
    second = _load_server(monkeypatch, tmp_path / "other", capsule_dir)
    second.__dict__.update(tools.register(FastMCP("Other structure"), StructureContext(second.__dict__)))
    calls = []

    def sender(label):
        def send(payload, timeout=60.0):
            calls.append((label, json.loads(payload)))
            return json.dumps({"status": "pass", "results": {"analysis_method": "api"}})
        return send

    monkeypatch.setattr(first, "_send_and_receive", sender("first"))
    monkeypatch.setattr(second, "_send_and_receive", sender("second"))
    first.visualize_structure(guids=["beam"], engine="karamba")
    assert first._VIEW_ENGINE == "api"
    assert second._VIEW_ENGINE is None
    second.visualize_structure(guids=["beam"], engine="karamba")
    monkeypatch.setattr(first, "_send_and_receive", sender("rebound"))
    first.visualize_structure(clear=True)
    assert [label for label, _ in calls] == ["first", "second", "rebound"]
    assert first._VIEW_ENGINE is None and second._VIEW_ENGINE == "api"

    # Replacing the public server field still controls the next display-only route.
    monkeypatch.setattr(first, "_VIEW_ENGINE", "native")
    first.visualize_structure(guids=["beam"], reanalyze=False)
    assert calls[-1][1]["type"] == "structure_draw"


def test_native_validation_history_report_and_service_replacement(extracted_server, monkeypatch, tmp_path):
    server = extracted_server
    asset_regressions.bridge(server, monkeypatch)
    verdict = json.loads(server.validate_structure(["beam"], engine="native", load_kn=0.001))
    assert verdict["status"] in ("pass", "fail")
    assert server.retrieval_store.list_validation_runs()[0]["analysis_method"] == "native"
    target = tmp_path / "reports" / "structure.md"
    report = json.loads(server.export_structural_report(str(target)))
    assert report["runs"] == 1 and report["latest_method"] == "native"
    assert "Structural validation report" in target.read_text(encoding="utf-8")

    # A factory must resolve the current store/helper, including call-local overrides.
    monkeypatch.setattr(server, "retrieval_store", ExtractedStore(tmp_path / "replacement.sqlite3"))
    assert "No validation runs" in json.loads(server.export_structural_report(str(target)))["message"]
    monkeypatch.setattr(server, "GENERATED_LIBRARY_DIR", str(tmp_path / "replacement-library"))
    assert server._structural_loads_path() == tmp_path / "replacement-library" / "structural-loads.json"
    context = StructureContext(server.__dict__)
    with context.override(_send_and_receive=lambda *_args, **_kwargs: '{"status":"overridden"}'):
        overridden = tools.register(FastMCP("Override"), context)
        assert json.loads(overridden["_bridge_call"]({}, 1))["status"] == "overridden"


@pytest.mark.parametrize("name", [
    "native_structure", "frame_solver", "ec3", "floor_loads", "asset_loads", "design_codes", "structure_study",
])
def test_old_imports_share_feature_module_identity(name, monkeypatch):
    old = importlib.import_module(f"almond_mcp.{name}")
    moved = importlib.import_module(f"almond_mcp.features.structure.{name}")
    assert old is moved
    marker = object()
    monkeypatch.setattr(old, "_identity_probe", marker, raising=False)
    assert moved._identity_probe is marker


def test_builtin_design_code_resource_stays_at_package_path():
    from almond_mcp.features.structure import design_codes
    from almond_mcp import paths

    assert design_codes.BUILT_IN == Path(paths.__file__).resolve().parent / "code_profiles"
    assert design_codes.load("eurocode").id == "eurocode"
