"""Material library manifest validity + assign_material script generation."""
import importlib.util
import json
import sys
import tempfile
import uuid
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = PROJECT_ROOT / "src" / "mcp" / "profiles" / "material" / "manifest.json"

PACKAGE_ROOT = PROJECT_ROOT / "src" / "mcp"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))


def load_server():
    import os
    spec = importlib.util.spec_from_file_location(
        f"almond_server_materials_{uuid.uuid4().hex}",
        PACKAGE_ROOT / "server.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def server():
    return load_server()


def call(tool, **arguments):
    return json.loads(getattr(tool, "fn", tool)(**arguments))


def test_manifest_is_valid():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    materials = manifest["materials"]
    assert len(materials) >= 10
    seen = set()
    for material in materials:
        for key in ("material_id", "name", "category", "base_color",
                    "metallic", "roughness", "opacity", "ue_material_slot"):
            assert key in material, f"{material.get('material_id')} missing {key}"
        assert material["material_id"] not in seen
        seen.add(material["material_id"])
        r, g, b = material["base_color"]
        assert all(0 <= v <= 255 for v in (r, g, b))
        for channel in ("metallic", "roughness", "opacity"):
            assert 0.0 <= material[channel] <= 1.0, material["material_id"]
        assert material["ue_material_slot"].startswith("M_")
        assert "layer_path" not in material


def test_library_loads_and_filters(server):
    assert len(server.material_library.materials) >= 10
    metals = server.material_library.list(category="metal")
    assert metals and all(m["category"] == "metal" for m in metals)
    hits = server.material_library.list(query="polycarbonate")
    assert hits and all("polycarbonate" in m["material_id"] for m in hits)


def test_material_assignment_uses_shared_native_helper_without_dimension_return(server):
    material = server.material_library.get("steel-painted-sage")
    guid = str(uuid.uuid4())
    label = '1F "north"\\entry\n중층'
    script = server._material_script(material, [guid], True, True, {"almond:floor": label})
    assert "ModelingMaterials.Apply(doc," in script
    assert server.modeling_setup.literal(server.modeling_setup.recipe(material)) in script
    assert guid in script
    assert json.dumps(label, ensure_ascii=True) in script
    assert "public static object Run" in script and "List<Guid>" not in script
    assert "doc.Materials.Add" not in script and "doc.Layers.Add" not in script
    assert "false, false" in server._material_script(material, [guid], False, False)


def test_policy_keys_and_legacy_manifest_fallback(server, tmp_path, monkeypatch):
    policy = server.modeling_policy
    assert set(policy.POLICY["public_object_keys"]) == {"component_id", "floor", "construction_detail"}
    assert policy.key("construction_reference") == "almond:construction_reference"
    assert policy.key("component_record") == "almond:component_record"
    with pytest.raises(KeyError):
        policy.key("scene_ids")
    record = dict(server.material_library.get("steel-painted-sage"))
    record["layer_path"] = "M::metal::steel-painted-sage"
    manifest = tmp_path / "manifest.json"
    original = json.dumps({"materials": [record]})
    manifest.write_text(original, encoding="utf-8")
    library = server.MaterialLibrary(str(tmp_path))
    assert "layer_path" not in library.get(record["material_id"])
    assert manifest.read_text(encoding="utf-8") == original
    monkeypatch.setattr(server, "_send_and_receive", lambda *a, **k: pytest.fail("A library query must not contact Rhino"))
    assert "layer_path" not in call(server.list_materials, query="steel-painted-sage")["materials"][0]


@pytest.mark.parametrize("bad_path", ["A::metal", "M::", "M::::steel", "M::bad:name", "M:: bad", "M::a\nb", 12])
def test_material_layers_reject_invalid_hierarchy(server, bad_path):
    record = dict(server.material_library.get("steel-painted-sage"), layer_path=bad_path)
    with pytest.raises(ValueError):
        server.modeling_policy.validate_layer_path(bad_path)


@pytest.mark.parametrize("bad", [{"base_color": [True, 0, 0]}, {"roughness": float("nan")},
                                {"opacity": 2}, {"metallic": "0.2"}])
def test_invalid_material_channels_are_rejected(server, bad):
    with pytest.raises(ValueError):
        server.modeling_policy.validate_material({**server.material_library.get("steel-painted-sage"), **bad})


def test_assignment_checks_capability_and_returns_actual_guids_and_metadata(server, monkeypatch):
    guid = str(uuid.uuid4())
    sent = []

    def send(payload, **kwargs):
        request = json.loads(payload)
        sent.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"modeling_materials": 2}})
        return json.dumps({"status": "success", "result": {"material_id": "steel-painted-sage",
                           "applied_guids": [guid], "layer_path": None}})

    monkeypatch.setattr(server, "_send_and_receive", send)
    result = call(server.assign_material, guids=[guid.upper(), guid], material_id="steel-painted-sage", floor="2F",
                  construction_system="steel-wide-flange-floor", attach_metadata=True)
    assert result["status"] == "success"
    assert result["requested_count"] == result["applied_count"] == 1
    assert result["applied_guids"] == [guid]
    assert result["layer_path"] is None
    assert result["rhino_material_name"] == server.material_library.get("steel-painted-sage")["name"]
    assert result["construction_reference"] == {"kind": "construction_system", "id": "steel-wide-flange-floor"}
    assert result["construction_detail"] == server.construction_library.get("steel-wide-flange-floor")["name"]
    assert [request["type"] for request in sent] == ["get_rhino_context", "execute"]
    assert '"almond:floor", "2F"' in sent[-1]["script"]
    assert '"almond:construction_system"' not in sent[-1]["script"]
    assert '"almond:structural_material"' not in sent[-1]["script"]


@pytest.mark.parametrize("extra", [
    {"construction_reference": {"kind": "directory", "id": "dataholz"}},
    {"construction_reference": {"kind": "construction_system", "id": "missing"}},
    {"construction_reference": {"kind": "construction_system", "id": "steel-wide-flange-floor", "verified": True}},
    {"construction_system": "wood-joist-floor", "construction_reference": {"kind": "construction_system", "id": "steel-wide-flange-floor"}},
])
def test_unknown_or_conflicting_construction_reference_never_reaches_rhino(server, monkeypatch, extra):
    monkeypatch.setattr(server, "_send_and_receive", lambda *a, **k: pytest.fail("Invalid metadata reached Rhino"))
    result = call(server.assign_material, guids=[str(uuid.uuid4())], material_id="steel-painted-sage", **extra)
    assert result["status"] == "error"


def test_older_bridge_is_rejected_before_assignment(server, monkeypatch):
    requests = []

    def send(payload, **kwargs):
        requests.append(json.loads(payload))
        return json.dumps({"status": "success", "capabilities": {"block_analysis": 1, "modeling_materials": 1}})

    monkeypatch.setattr(server, "_send_and_receive", send)
    result = call(server.assign_material, guids=[str(uuid.uuid4())], material_id="steel-painted-sage")
    assert result["error_code"] == "unsupported_materials"
    assert [request["type"] for request in requests] == ["get_rhino_context"]


@pytest.mark.parametrize("native_result", [{"status": "success"}, {"status": "success", "result_error": "too_large"}])
def test_missing_assignment_result_does_not_report_zero_or_retry(server, monkeypatch, native_result):
    requests = []

    def send(payload, **kwargs):
        request = json.loads(payload)
        requests.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"modeling_materials": 2}})
        return json.dumps(native_result)

    monkeypatch.setattr(server, "_send_and_receive", send)
    result = call(server.assign_material, guids=[str(uuid.uuid4())], material_id="steel-painted-sage")
    assert "applied_count" not in result
    assert len(requests) == 2
    assert "before retrying" in result["message"]


def test_metadata_only_assignment_does_not_claim_native_material_change(server, monkeypatch):
    guid = str(uuid.uuid4())

    def send(payload, **kwargs):
        request = json.loads(payload)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"modeling_materials": 2}})
        assert "false, true" in request["script"]
        assert '"almond:material_id"' not in request["script"]
        return json.dumps({"status": "success", "result": {"material_id": "steel-painted-sage",
                           "applied_guids": [guid], "changed_guids": [], "layer_path": None}})

    monkeypatch.setattr(server, "_send_and_receive", send)
    result = call(server.assign_material, guids=[guid], material_id="steel-painted-sage", floor="1F", apply_render_material=False, attach_metadata=True)
    assert result["render_material_applied"] is False
    assert result["material_metadata_attached"] is False
    assert result["layer_path"] is None and result["changed_count"] == 0


def test_assignment_timeout_is_unknown_and_never_retried(server, monkeypatch):
    requests = []

    def send(payload, **kwargs):
        request = json.loads(payload)
        requests.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"modeling_materials": 2}})
        raise TimeoutError("test timeout after dispatch")

    monkeypatch.setattr(server, "_send_and_receive", send)
    result = call(server.assign_material, guids=[str(uuid.uuid4())], material_id="steel-painted-sage")
    assert result["mutation_state"] == "unknown" and len(requests) == 2


def test_given_routine_material_assignment_then_no_management_userstrings_by_default(server, monkeypatch):
    guid = str(uuid.uuid4())
    def send(payload, **kwargs):
        request = json.loads(payload)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"modeling_materials": 2}})
        assert "true, false)" in request["script"]
        return json.dumps({"status": "success", "result": {
            "material_id": "steel-painted-sage", "applied_guids": [guid],
            "metadata_attached": False, "layer_path": None}})
    monkeypatch.setattr(server, "_send_and_receive", send)
    result = call(server.assign_material, guids=[guid], material_id="steel-painted-sage")
    assert result["status"] == "success"
    assert result["render_material_applied"] is True
    assert result["metadata_attached"] is False
    assert result["material_metadata_attached"] is False


def test_construction_setup_resolves_layers_and_role_materials(server):
    layers = server.modeling_setup.construction_layers(
        server.construction_library.systems.values(), server.material_library.materials)
    by_path = {row["path"]: row for row in layers}
    assert len(by_path) == len(layers)
    assert by_path["M"] == {"path": "M", "color": [128, 128, 128]}
    for system in server.construction_library.systems.values():
        branch = f'M::{system["category"]}::{system["name"]}'
        assert by_path[branch]["material"]["material_id"] == system["render_material_ids"][0]
        for element in system["elements"]:
            row = by_path[f'{branch}::{element["role"]}']
            assert row["color"] == row["material"]["base_color"]
            if element["role"] in ("connection", "reinforcement", "decking"):
                assert row["material"]["material_id"] == "steel-galvanized"


def test_setup_rejects_unsafe_bridge_without_dispatch(server, monkeypatch):
    requests = []
    def send(payload, **kwargs):
        requests.append(json.loads(payload))
        return json.dumps({"status": "success", "capabilities": {"modeling_materials": 1}})
    monkeypatch.setattr(server, "_send_and_receive", send)
    result = call(server.setup_modeling, operation="layers")
    assert result["error_code"] == "unsupported_materials"
    assert [r["type"] for r in requests] == ["get_rhino_context"]


@pytest.mark.parametrize("overwrite, encoded", [(None, "null"), (True, "true"), (False, "false")])
def test_material_setup_preserves_overwrite_choice(server, monkeypatch, overwrite, encoded):
    requests = []
    def send(payload, **kwargs):
        request = json.loads(payload)
        requests.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"modeling_materials": 2}})
        assert "ModelingMaterials.Register(doc," in request["script"]
        assert f", {encoded});" in request["script"]
        return json.dumps({"status": "success", "result": {"updated_materials": 27, "skipped_materials": 0}})
    monkeypatch.setattr(server, "_send_and_receive", send)
    result = call(server.setup_modeling, operation="materials", overwrite=overwrite)
    assert result["result"]["updated_materials"] == 27 and len(requests) == 2


@pytest.fixture(autouse=True)
def isolated_server_database(tmp_path, monkeypatch):
    monkeypatch.setenv("RHINO_MCP_STATE_DB", str(tmp_path / "DB"))
