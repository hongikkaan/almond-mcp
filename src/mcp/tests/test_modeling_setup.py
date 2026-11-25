"""Material assignment through isolated transport and the production native layer policy."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.features.modeling import modeling_setup
from almond_mcp.features.modeling.library import MaterialLibrary
from almond_mcp.features.modeling.tools import register


PROFILE = Path(__file__).resolve().parents[1] / "profiles/material"


def context(reply=None, *, material_layer=True, assignment=2):
    material = {"material_id": "oak", "name": "Oak", "category": "Wood", "ue_material_slot": "Oak",
                "base_color": [10, 20, 30], "metallic": 0.0, "roughness": 0.5, "opacity": 1.0}
    requests = []

    def send(payload, **kwargs):
        request = json.loads(payload)
        requests.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {
                "modeling_materials": 2,
                **({"material_assignment_metadata": assignment} if assignment else {}),
                **({"material_layer_assignment": 1} if material_layer else {})}})
        if isinstance(reply, Exception):
            raise reply
        return json.dumps(reply)

    materials = {"oak": material}
    systems = {"timber": {"name": "Timber system", "render_material_ids": ["oak"]}}
    return SimpleNamespace(construction_library=SimpleNamespace(systems=systems, get=systems.get),
                           material_library=SimpleNamespace(materials=materials, get=materials.get),
                           _send_and_receive=send, requests=requests)


def test_material_script_execution_does_not_claim_assignment_after_result_error():
    ctx = context({"status": "success", "result_error": "serialization failed"})
    tools = register(FastMCP("material-result-error"), ctx)
    result = json.loads(tools["assign_material"](["00000000-0000-0000-0000-000000000001"], "oak", floor="1F", structural_role="slab"))
    assert result["status"] == "executed"
    assert result["material_id"] == "oak"
    assert result["result_error"] == "serialization failed"
    assert "applied_count" not in result
    assert [request["type"] for request in ctx.requests] == ["get_rhino_context", "execute"]


@pytest.mark.parametrize("applied_count, status", [(0, "executed"), (1, "partial"), (2, "success")])
def test_material_result_distinguishes_assignment_coverage(applied_count, status):
    guids = ["00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000002"]
    applied = guids[:applied_count]
    ctx = context({"status": "success", "result": {
        "material_id": "oak", "applied_guids": applied, "changed_guids": applied, "metadata_attached": bool(applied),
        "layer_path": "M::Wood::oak", "layer_action": "created",
        "layer_changed_guids": applied[:1], "render_material_applied": True,
    }})
    tools = register(FastMCP("material-result-coverage"), ctx)
    result = json.loads(tools["assign_material"](guids, "oak", "1F", "slab", apply_render_material=bool(applied_count)))
    assert result["status"] == status
    assert result["applied_count"] == applied_count
    assert result["requested_count"] == len(guids)
    assert result["layer_path"] == ("M::Wood::oak" if applied else None)
    assert result["layer_action"] == ("created" if applied else "not_applied")
    assert result["layer_changed_guids"] == applied[:1]


def test_layer_settings_use_material_category_and_are_sent_only_for_render_assignment():
    from almond_mcp.features.modeling.modeling_policy import material_layer, validate_material

    material = context().material_library.get("oak")
    assert material_layer(material) == {"path": "M::Wood::oak"}
    style = {"path": "M::Wood::Oak custom", "color": [40, 50, 60],
             "plot_color": [0, 0, 0], "plot_weight_mm": 0.25, "linetype": "Continuous"}
    assert material_layer(validate_material({**material, "layer_settings": style})) == style
    for invalid in ({"path": "D::Wood::oak"}, {"path": "M::Metal::oak"},
                    {"path": "M::Wood::oak::child"}, {"color": [256, 1, 2]}, {"plot_weight_mm": True}):
        with pytest.raises(ValueError):
            material_layer(validate_material({**material, "layer_settings": invalid}))
    material["layer_settings"] = style
    code = modeling_setup.material_script(material, [], True, False)
    assert "M::Wood::Oak custom" in code and "plot_weight_mm" in code
    assert "layer_settings" not in modeling_setup.material_script(material, [], False, True)


def test_bundled_layer_colors_reach_the_public_assignment():
    guid = "00000000-0000-0000-0000-000000000001"
    native = {"metadata_attached": True, "applied_guids": [guid], "changed_guids": [guid], "layer_action": "created",
              "layer_changed_guids": [guid], "render_material_applied": True}
    ctx = context({"status": "success", "result": native})
    ctx.material_library = MaterialLibrary(PROFILE)
    assign = register(FastMCP("bundled-materials"), ctx)["assign_material"]
    materials = json.loads((PROFILE / "manifest.json").read_text(encoding="utf-8"))["materials"]
    assert materials and len(materials) == len(ctx.material_library.materials)
    for material in materials:
        colors = {"color": material["base_color"], "plot_color": material["base_color"]}
        assert material["layer_settings"] == colors
        path = f"M::{material['category']}::{material['material_id']}"
        native.update(material_id=material["material_id"], layer_path=path)
        assert json.loads(assign([guid], material["material_id"], floor="1F", structural_role="slab"))["status"] == "success"
        context_request, execute_request = ctx.requests
        assert [context_request["type"], execute_request["type"]] == ["get_rhino_context", "execute"]
        argument = execute_request["script"].split("ModelingMaterials.Apply(doc, ", 1)[1]
        encoded, _ = json.JSONDecoder().raw_decode(argument)
        payload = json.loads(encoded)
        assert payload["layer_settings"] == {"path": path, **colors}
        ctx.requests.clear()


def test_existing_default_installation_uses_only_unchanged_bundled_records(tmp_path, monkeypatch):
    from almond_mcp import paths

    monkeypatch.setattr(paths, "user_data_dir", lambda: tmp_path)
    current = json.loads((PROFILE / "manifest.json").read_text(encoding="utf-8"))["materials"]
    original, edited, styled = current[:3]
    records = [{k: v for k, v in record.items() if k != "layer_settings"} for record in current[:3]]
    records[1]["base_color"] = [1, 2, 3]
    records[2]["layer_settings"] = {}
    content = json.dumps({"materials": records})
    for folder in ("Materialfiles", "custom"):
        directory = tmp_path / folder
        directory.mkdir()
        manifest = directory / "manifest.json"
        manifest.write_text(content, encoding="utf-8")
        library = MaterialLibrary(directory)
        expected = original if folder == "Materialfiles" else records[0]
        assert library.get(original["material_id"]) == expected
        assert library.get(edited["material_id"]) == records[1]
        assert library.get(styled["material_id"]) == records[2]
        assert manifest.read_text(encoding="utf-8") == content
    monkeypatch.setattr("almond_mcp.features.modeling.library.__file__",
                        str(tmp_path / "unbundled/features/modeling/library.py"))
    assert MaterialLibrary(tmp_path / "Materialfiles").get(original["material_id"]) == records[0]


def test_material_layer_rules_only_apply_to_render_assignment(tmp_path):
    from almond_mcp.features.modeling.modeling_policy import POLICY

    guid = "00000000-0000-0000-0000-000000000001"
    ctx = context({"status": "success", "result": {"material_id": "oak", "applied_guids": [guid], "metadata_attached": True}})
    material = {**ctx.material_library.get("oak"), "category": "paint:interior"}
    (tmp_path / "manifest.json").write_text(json.dumps({"materials": [material]}))
    ctx.material_library = MaterialLibrary(tmp_path)
    assert ctx.material_library.get("oak") == material
    assign = register(FastMCP("legacy-material"), ctx)["assign_material"]
    assert json.loads(assign([guid], "oak", floor="1F", structural_role="slab"))["status"] == "error"
    assert ctx.requests == []
    assert json.loads(assign([guid], "oak", "1F", "slab", apply_render_material=False))["status"] == "success"
    assert set(POLICY["material_assignment_keys"]) == {"Floor", "construction_detail", "construction_reference", "structural_role"}


def test_old_bridge_rejects_render_assignment_but_can_still_attach_metadata():
    guid = "00000000-0000-0000-0000-000000000001"
    ctx = context({"status": "success", "result": {
        "material_id": "oak", "applied_guids": [guid], "metadata_attached": True,
    }}, material_layer=False)
    tools = register(FastMCP("material-capability"), ctx)
    failed = json.loads(tools["assign_material"]([guid], "oak", floor="1F", structural_role="slab"))
    assert failed["error_code"] == "unsupported_material_layer_assignment"
    assert failed["mutation_state"] == "not_started"
    assert [r["type"] for r in ctx.requests] == ["get_rhino_context"]
    result = json.loads(tools["assign_material"]([guid], "oak", "1F", "slab", apply_render_material=False))
    assert result["status"] == "success" and result["metadata_attached"] is True
    assert result["layer_action"] == "not_applied" and result["layer_changed_guids"] == []
    assert result["layer_path"] is None and result["render_material_applied"] is False
    assert result["structural_role"] == "slab" and "structural_role" in ctx.requests[-1]["script"]


def test_material_result_does_not_confirm_a_move_without_bridge_evidence():
    guid = "00000000-0000-0000-0000-000000000001"
    ctx = context({"status": "success", "result": {
        "material_id": "oak", "applied_guids": [guid], "changed_guids": [], "metadata_attached": True,
        "layer_path": "M::Wood::oak", "layer_action": "reused",
        "layer_changed_guids": [guid], "render_material_applied": True,
    }})
    result = json.loads(register(FastMCP("material-unconfirmed"), ctx)["assign_material"]([guid], "oak", floor="1F", structural_role="slab"))
    assert result["error_code"] == "material_layer_result_unavailable"
    assert result["mutation_state"] == "unknown"


def test_public_tool_requires_floor_and_role_even_when_render_and_tagging_are_disabled():
    guid = "00000000-0000-0000-0000-000000000001"
    ctx = context({"status": "success", "result": {"material_id": "oak", "applied_guids": [guid], "metadata_attached": True}})
    server = FastMCP("assignment-schema")
    register(server, ctx)

    async def invoke():
        args = dict(guids=[guid], material_id="oak", floor="2F", structural_role="joist",
                    apply_render_material=False, attach_metadata=False)
        async with Client(server) as client:
            for key in ("floor", "structural_role"):
                missing = {k: v for k, v in args.items() if k != key}
                response = await client.call_tool("model_01-assign_material", missing, raise_on_error=False)
                assert response.is_error
            assert not ctx.requests
            response = await client.call_tool("model_01-assign_material", args)
            result = json.loads(response.structured_content["result"])
            assert result["status"] == "success" and result["floor"] == "2F" and result["structural_role"] == "joist"
            assert "construction_detail" not in result and "construction_reference" not in result

    asyncio.run(invoke())


@pytest.mark.parametrize("floor, role", [("", "joist"), ("1F", "  ")])
def test_assignment_rejects_blank_required_fields_before_dispatch(floor, role):
    ctx = context()
    assign = register(FastMCP("required"), ctx)["assign_material"]
    result = json.loads(assign(["00000000-0000-0000-0000-000000000001"], "oak", floor, role))
    assert result["status"] == "error" and not ctx.requests


@pytest.mark.parametrize("render", [True, False])
@pytest.mark.parametrize("version", [None, 1])
def test_old_bridge_cannot_skip_required_metadata(render, version):
    ctx = context(assignment=version)
    assign = register(FastMCP("old-metadata"), ctx)["assign_material"]
    result = json.loads(assign(["00000000-0000-0000-0000-000000000001"], "oak", "2F", "joist",
                               apply_render_material=render, attach_metadata=False))
    assert result["error_code"] == "unsupported_material_assignment_metadata" and result["mutation_state"] == "not_started"
    assert [r["type"] for r in ctx.requests] == ["get_rhino_context"]


@pytest.mark.parametrize("options, detail, reference", [
    ({}, "", None),
    ({"construction_detail": "  ", "construction_system": ""}, "", None),
    ({"construction_detail": "Finish"}, "Finish", None),
    ({"construction_reference": {"kind": "construction_system", "id": "timber"}}, "", "timber"),
    ({"construction_system": "timber"}, "", "timber"),
    ({"construction_detail": "Finish", "construction_system": "timber"}, "Finish", "timber"),
])
def test_assignment_optional_fields_are_independent(options, detail, reference):
    guid = "00000000-0000-0000-0000-000000000001"
    ctx = context({"status": "success", "result": {"material_id": "oak", "applied_guids": [guid], "metadata_attached": True}})
    assign = register(FastMCP("fields"), ctx)["assign_material"]
    result = json.loads(assign([guid], "oak", "2F", "joist", apply_render_material=False, attach_metadata=False, **options))
    assert result["status"] == "success" and result["metadata_attached"] and not result["material_metadata_attached"]
    assert (result["floor"], result["structural_role"]) == ("2F", "joist")
    expected = {"kind": "construction_system", "id": reference} if reference else None
    script = ctx.requests[-1]["script"]
    for key, value in {"construction_detail": detail, "construction_reference": expected}.items():
        if value:
            assert result[key] == value
            encoded = value if isinstance(value, str) else json.dumps(value, separators=(",", ":"))
            assert "{ " + json.dumps(key) + ", " + json.dumps(encoded) + " }" in script
        else:
            assert key not in result and json.dumps(key) not in script
    assert '{ "Floor", "2F" }' in script and '{ "structural_role", "joist" }' in script
    assert 'layer_settings' not in script and '"floor"' not in script


def test_conflicting_reference_and_unverified_metadata_cannot_report_success():
    guid = "00000000-0000-0000-0000-000000000001"
    ctx = context({"status": "success", "result": {"material_id": "oak", "applied_guids": [guid]}})
    assign = register(FastMCP("unverified-fields"), ctx)["assign_material"]
    result = json.loads(assign([guid], "oak", "2F", "joist", construction_system="other",
                               construction_reference={"kind": "construction_system", "id": "timber"}))
    assert result["status"] == "error" and not ctx.requests
    result = json.loads(assign([guid], "oak", "2F", "joist", apply_render_material=False))
    assert result["error_code"] == "material_metadata_unconfirmed" and result["mutation_state"] == "unknown"


def test_native_material_layer_selection_and_metadata(tmp_path):
    sdk = os.environ.get("ALMOND_TEST_DOTNET")
    assert sdk, "Run through run_tests.ps1 to select the .NET 8 SDK."
    project = Path(__file__).with_name("modeling_setup_host") / "ModelingSetupHost.csproj"
    result = subprocess.run([sdk, "build", str(project), "-c", "Release", "--nologo", "-p:UseSharedCompilation=false",
                             "-p:NuGetAudit=false", "-nodeReuse:false"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert result.returncode == 0, result.stdout + result.stderr
    host = project.parent / "bin/Release/net8.0-windows/ModelingSetupHost.dll"
    result = subprocess.run([sdk, str(host)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS:" in result.stdout
