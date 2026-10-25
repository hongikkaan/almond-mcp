"""Real exchange registration and native helpers with isolated, bounded fakes."""
import asyncio
from contextlib import contextmanager
import inspect
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.feature_context import FeatureContext
from almond_mcp.features.exchange import exchange
from almond_mcp.features.exchange.tools import register


G1 = "11111111-1111-1111-1111-111111111111"
G2 = "22222222-2222-2222-2222-222222222222"
MATERIAL = {
    "material_id": "wood-oak", "name": "Oak", "category": "wood",
    "base_color": [200, 170, 130], "metallic": 0.0, "roughness": 0.65,
    "opacity": 1.0, "ue_material_slot": "M_Wood_Oak",
}
REPORT = {"stamped": 2, "deduped": 1, "width": 1200, "depth": 600, "height": 750}
REPORT_EXPRESSIONS = {
    "almond_matgroups.txt": 'Path.Combine(Path.GetTempPath(), "almond_matgroups.txt")',
    "almond_imported.txt": 'Path.Combine(Path.GetTempPath(), "almond_imported.txt")',
    "almond_import_report.json": 'System.IO.Path.Combine(System.IO.Path.GetTempPath(), "almond_import_report.json")',
}
PUBLIC_TOOLS = {"export_asset_contract", "import_asset_contract", "get_blender_helper_script"}
HELPERS = {"_material_groups", "_receive_contract", "_restore_and_place_script"}


@pytest.fixture
def feature():
    materials = {"wood-oak": dict(MATERIAL)}

    def unexpected_sender(*args, **kwargs):
        pytest.fail("A helper used the unscoped sender")

    namespace = dict(exchange=exchange, material_library=SimpleNamespace(
        materials=materials, get=materials.get), tempfile=tempfile,
        _send_and_receive=unexpected_sender)
    context = FeatureContext(namespace)
    mcp = FastMCP("exchange-feature")
    exports = register(mcp, context)
    namespace.update(exports)
    return SimpleNamespace(mcp=mcp, context=context, namespace=namespace, exports=exports)


def contract(tmp_path):
    glb, filename = exchange.contract_paths(tmp_path, "fixture-chair")
    glb.write_bytes(b"glTF-fixture; never imported by Rhino")
    data = exchange.build_contract(
        "fixture-chair", "Fixture Chair", glb.name,
        {"min": [0, 0, 0], "max": [1200, 600, 750]},
        [{"material_id": "wood-oak", "objects": [G1]},
         {"material_id": "unknown", "objects": [G2]}], "blender", object_count=2)
    filename.write_text(json.dumps(data), encoding="utf-8")
    return filename


class NativeFake:
    """Only the expected exchange operations, never sockets or real documents."""

    def __init__(self, folder, *, limit, material_id="wood-oak", failure="", report=REPORT):
        self.folder = folder
        folder.mkdir(parents=True)
        self.limit, self.material_id, self.failure = limit, material_id, failure
        self.report = report
        self.requests, self.reports = [], []

    def __call__(self, payload, **kwargs):
        request = json.loads(payload)
        self.requests.append((request, kwargs))
        assert len(self.requests) <= self.limit, "Unexpected native dispatch or retry"
        if request["type"] == "get_rhino_context":
            assert request == {"type": "get_rhino_context", "selection_limit": 0}
            return json.dumps({"status": "success", "capabilities": {
                "modeling_materials": 1 if self.failure == "bridge" else 2}})
        if request["type"] == "export_glb":
            assert kwargs == {"timeout": 90.0}
            Path(request["output_path"]).write_bytes(b"glTF-fixture")
            return json.dumps({"status": "success", "units": "Meters", "object_guids": [G1, G2],
                               "bounds": {"min": [0, 0, 0], "max": [1.2, 0.6, 0.75]}})
        assert request["type"] == "execute"
        script = request["script"]
        matches = [name for name, expression in REPORT_EXPRESSIONS.items() if expression in script]
        assert len(matches) == 1, "Native helper report expression changed"
        name = matches[0]
        assert script.count(REPORT_EXPRESSIONS[name]) == 1
        self.reports.append(self.folder / name)
        if name == "almond_matgroups.txt":
            assert kwargs == {"timeout": 45.0}
            (self.folder / name).write_text(f"{self.material_id}|{G1}\n", encoding="utf-8")
            return json.dumps({"status": "success"})
        assert kwargs == {"timeout": 120.0}
        stage = "import" if name == "almond_imported.txt" else "restore"
        if self.failure == stage + "_exception":
            raise ConnectionRefusedError("fixture connection lost")
        if self.failure == stage + "_error":
            return json.dumps({"status": "error", "message": stage + " rejected"})
        if stage == "import":
            # The native response is authoritative; the legacy text file differs.
            (self.folder / name).write_text(G2 + "\n", encoding="utf-8")
            return json.dumps({"status": "success", "guids": [] if self.failure == "empty" else [G1, G2]})
        if self.report is not None:
            (self.folder / name).write_text(json.dumps(self.report), encoding="utf-8")
        return json.dumps({"status": "success", "guids": [G1, G2]})

    @contextmanager
    def scope(self, context):
        with context.override(tempfile=SimpleNamespace(gettempdir=lambda: str(self.folder)),
                              _send_and_receive=self):
            yield self


def test_registered_tool_resolves_patched_canonical_exchange(feature, monkeypatch):
    assert feature.context.exchange is exchange
    assert exchange.__name__ == "almond_mcp.features.exchange.exchange"
    monkeypatch.setattr(exchange, "blender_export_script", lambda *args: "replacement")
    result = json.loads(feature.exports["get_blender_helper_script"]("export", asset_id="fixture"))
    assert result["status"] == "success"
    assert result["script"] == "replacement"


def test_factory_registers_exact_public_contract_and_no_helpers(feature):
    assert set(feature.exports) == PUBLIC_TOOLS | HELPERS
    expected = {
        "export_asset_contract": {"guids", "asset_id", "name", "output_dir"},
        "import_asset_contract": {"contract_path", "x_mm", "y_mm", "z_mm", "rotation_degrees", "layer"},
        "get_blender_helper_script": {"action", "asset_id", "name", "output_dir", "material_id", "object_names"},
    }

    async def run():
        async with Client(feature.mcp) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            assert set(tools) == PUBLIC_TOOLS
            for name, fields in expected.items():
                tool = tools[name]
                assert set(tool.input_schema["properties"]) == fields
                signature = inspect.signature(feature.exports[name])
                required = {key for key, value in signature.parameters.items()
                            if value.default is inspect.Parameter.empty}
                assert set(tool.input_schema.get("required", [])) == required
                assert tool.description and inspect.getdoc(feature.exports[name]).startswith(tool.description)
                assert tool.annotations is None
            assert tools["export_asset_contract"].input_schema["properties"]["name"]["default"] == ""
            assert tools["import_asset_contract"].input_schema["properties"]["layer"]["default"] == "ALMOND-EXCHANGE"
            assert tools["get_blender_helper_script"].input_schema["properties"]["object_names"]["default"] is None
            result = await client.call_tool("get_blender_helper_script", {"action": "export", "asset_id": "chair"})
            assert "to_mesh()" in json.loads(result.content[0].text)["script"]

    asyncio.run(run())


def test_export_uses_current_sender_actual_material_helper_and_millimetres(feature, tmp_path):
    native = NativeFake(tmp_path / "reports", limit=2)
    with native.scope(feature.context):
        result = json.loads(feature.exports["export_asset_contract"](
            [G1, G2], "fixture-chair", "Chair", str(tmp_path / "export")))
    assert result["status"] == "success"
    assert len(native.requests) == 2
    exported = exchange.load_contract(result["contract_path"])
    assert exported["dimensions_mm"] == {"width": 1200, "depth": 600, "height": 750}
    assert exported["materials"] == [{"material_id": "wood-oak", "objects": [G1]}]
    assert exported["object_count"] == 2
    assert native.reports == [native.folder / "almond_matgroups.txt"]
    assert feature.context.tempfile is tempfile


def test_import_uses_full_receive_sequence_and_current_exchange_namespace(feature, tmp_path):
    filename = contract(tmp_path / "contract")
    native = NativeFake(tmp_path / "reports", limit=3)
    measured = []
    feature.namespace["exchange"] = SimpleNamespace(
        load_contract=exchange.load_contract, material_name=exchange.material_name,
        dimension_report=lambda data, report: measured.append(report) or {"status": "fixture-match"})
    with native.scope(feature.context):
        result = json.loads(feature.exports["import_asset_contract"](
            str(filename), 100, 200, 0, 90, "FIXTURE"))
    assert result == {
        "status": "success", "asset_id": "fixture-chair", "source_app": "blender",
        "imported_count": 2, "metadata_restored": 2, "materials_deduplicated": 1,
        "unknown_material_ids": ["unknown"], "dimension_check": {"status": "fixture-match"},
        "layer": "FIXTURE", "imported_guids": [G1, G2],
    }
    assert len(native.requests) == 3
    assert measured == [REPORT]
    assert [path.name for path in native.reports] == ["almond_imported.txt", "almond_import_report.json"]
    restore = native.requests[-1][0]["script"]
    assert '"ALMOND::wood-oak"' in restore
    assert "RhinoAlmondBridge.ModelingMaterials.CreateAttributes" in restore
    assert "new Point3d(100 * toDoc, 200 * toDoc, 0 * toDoc)" in restore
    assert "RhinoMath.ToRadians(90)" in restore


def test_material_helper_reads_each_call_override_and_preserves_other_servers(feature, tmp_path):
    isolated_namespace = dict(feature.namespace)
    isolated_context = FeatureContext(isolated_namespace)
    isolated = register(FastMCP("second-exchange"), isolated_context)
    isolated_namespace.update(isolated)
    first = NativeFake(tmp_path / "first", limit=1, material_id="first")
    second = NativeFake(tmp_path / "second", limit=1, material_id="second")
    original_temp = tempfile.gettempdir()
    with first.scope(feature.context):
        with second.scope(isolated_context):
            assert feature.exports["_material_groups"]([G1]) == [{"material_id": "first", "objects": [G1]}]
            assert isolated["_material_groups"]([G1]) == [{"material_id": "second", "objects": [G1]}]
    third = NativeFake(tmp_path / "third", limit=1, material_id="third")
    feature.namespace["tempfile"] = SimpleNamespace(gettempdir=lambda: str(third.folder))
    feature.namespace["_send_and_receive"] = third
    assert feature.exports["_material_groups"]([G1]) == [{"material_id": "third", "objects": [G1]}]
    assert tempfile.gettempdir() == original_temp
    assert isolated_context.tempfile is tempfile


def test_runtime_helper_replacement_is_visible_after_registration(feature, tmp_path):
    feature.namespace["_material_groups"] = lambda guids: [{"material_id": "replaced", "objects": guids}]
    native = NativeFake(tmp_path / "export-reports", limit=1)
    with native.scope(feature.context):
        result = json.loads(feature.exports["export_asset_contract"]([G1], "fixture", output_dir=str(tmp_path)))
    assert result["materials"] == [{"material_id": "replaced", "objects": [G1]}]
    received = []
    feature.namespace["_receive_contract"] = lambda *args: received.append(args) or {"status": "replacement"}
    assert json.loads(feature.exports["import_asset_contract"](result["contract_path"])) == {"status": "replacement"}
    assert received[0][0]["asset_id"] == "fixture"
    restore_calls = []
    original_restore = feature.exports["_restore_and_place_script"]
    feature.namespace["_restore_and_place_script"] = lambda *args: restore_calls.append(args) or original_restore(*args)
    native = NativeFake(tmp_path / "receive-reports", limit=3)
    with native.scope(feature.context):
        feature.exports["_receive_contract"](exchange.load_contract(result["contract_path"]), 0, 0, 0, 0, "TEST")
    assert len(restore_calls) == 1


@pytest.mark.parametrize("failure,count,expected", [
    ("bridge", 1, "updated Bridge"),
    ("import_exception", 2, "Rhino bridge is unavailable"),
    ("import_error", 2, "import rejected"),
    ("empty", 2, "imported no objects"),
    ("restore_exception", 3, "Imported, but restore/place failed"),
    ("restore_error", 3, "restore rejected"),
])
def test_receive_failure_stops_without_retry(feature, tmp_path, failure, count, expected):
    filename = contract(tmp_path / "contract")
    native = NativeFake(tmp_path / "reports", limit=count, failure=failure)
    with native.scope(feature.context):
        result = feature.exports["_receive_contract"](exchange.load_contract(filename), 0, 0, 0, 0, "TEST")
    assert result["status"] == "error"
    assert expected in result["message"]
    assert len(native.requests) == count
    if failure.startswith("restore"):
        assert result["imported_guids"] == [G1, G2]


def test_receive_without_report_retains_unknown_measurement(feature, tmp_path):
    filename = contract(tmp_path / "contract")
    native = NativeFake(tmp_path / "reports", limit=3, report=None)
    with native.scope(feature.context):
        result = feature.exports["_receive_contract"](exchange.load_contract(filename), 0, 0, 0, 0, "TEST")
    assert result["dimension_check"] == {"status": "unknown"}
    assert result["metadata_restored"] == result["materials_deduplicated"] == 0


def test_blender_material_helper_reads_replaced_library(feature):
    materials = {"new-oak": dict(MATERIAL, material_id="new-oak", base_color=[10, 20, 30])}
    feature.namespace["material_library"] = SimpleNamespace(materials=materials, get=materials.get)
    invoke = feature.exports["get_blender_helper_script"]
    assert json.loads(invoke("materials", material_id="wood-oak", object_names=["seat"]))["status"] == "error"
    result = json.loads(invoke("materials", material_id="new-oak", object_names=["seat"]))
    assert result["status"] == "success"
    assert '"new-oak"' in result["script"] and '"seat"' in result["script"]
    assert '"10,20,30"' in result["script"]
