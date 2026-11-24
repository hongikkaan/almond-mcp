"""Combined setup contract; isolated transport and production native policy, no live Rhino."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.features.modeling import modeling_setup
from almond_mcp.features.modeling.tools import register


def context(reply=None, *, capability=True, material_layer=True):
    material = {"material_id": "oak", "name": "Oak", "category": "Wood", "ue_material_slot": "Oak",
                "base_color": [10, 20, 30], "metallic": 0.0, "roughness": 0.5, "opacity": 1.0}
    system = {"category": "floor", "name": "Oak floor", "render_material_ids": ["oak"],
              "structural_material": "Other", "elements": [{"role": "surface"}]}
    requests = []

    def send(payload, **kwargs):
        request = json.loads(payload)
        requests.append(request)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {
                "modeling_materials": 2, **({"modeling_setup": 1} if capability else {}),
                **({"material_layer_assignment": 1} if material_layer else {})}})
        if isinstance(reply, Exception):
            raise reply
        return json.dumps(reply or {"status": "success", "result": {"applied": True, "differences": [], "errors": []}})

    materials = {"oak": material}
    return SimpleNamespace(material_library=SimpleNamespace(materials=materials, get=materials.get),
                           construction_library=SimpleNamespace(systems={"floor": system}),
                           _send_and_receive=send, requests=requests)


@pytest.mark.parametrize("overwrite", [False, True])
def test_single_dispatch_and_compact_confirmation(overwrite):
    ctx = context()
    tools = register(FastMCP("setup-test"), ctx)
    result = json.loads(tools["setup_modeling"](overwrite))
    assert "model_01-assign_material" in result.pop("next_step_guide")
    assert result == {"status": "success", "applied": True}
    assert [r["type"] for r in ctx.requests] == ["get_rhino_context", "execute"]
    code = ctx.requests[-1]["script"]
    assert "ModelingMaterials.Setup(doc," in code and f", {str(overwrite).lower()})" in code
    assert "ApplyLayers(" not in code and "Register(" not in code


def test_old_loaded_bridge_rejected_before_mutation_and_assignment_still_supported():
    ctx = context(capability=False)
    result = json.loads(register(FastMCP("old-setup"), ctx)["setup_modeling"](False))
    assert result["mutation_state"] == "not_started" and result["error_code"] == "unsupported_modeling_setup"
    assert len(ctx.requests) == 1
    assert modeling_setup.check_bridge(ctx._send_and_receive) is None


def test_differences_and_item_errors_remain_actionable():
    details = {"applied": False,
               "differences": [{"kind": "layer", "name": "M::floor", "property": "color", "current": [1, 2, 3], "expected": [128]*3}],
               "errors": [{"kind": "material", "name": "Oak", "message": "conflicting material_id"}]}
    ctx = context({"status": "success", "result": details})
    result = json.loads(register(FastMCP("incomplete-setup"), ctx)["setup_modeling"](False))
    assert result == {"status": "incomplete", **details}


@pytest.mark.parametrize("reply", [
    TimeoutError("disconnected"), {"status": "success", "result_error": "serialization failed"},
    {"status": "success", "result": {"applied": True, "differences": [{}], "errors": []}},
    {"status": "success", "result": {"applied": False}},
])
def test_unknown_mutation_never_retried(reply):
    ctx = context(reply)
    result = json.loads(register(FastMCP("unknown-setup"), ctx)["setup_modeling"](False))
    assert result["status"] == "error" and result["mutation_state"] == "unknown"
    assert len([r for r in ctx.requests if r["type"] == "execute"]) == 1


def test_material_script_execution_does_not_claim_assignment_after_result_error():
    ctx = context({"status": "success", "result_error": "serialization failed"})
    tools = register(FastMCP("material-result-error"), ctx)
    result = json.loads(tools["assign_material"](["00000000-0000-0000-0000-000000000001"], "oak"))
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
        "material_id": "oak", "applied_guids": applied, "changed_guids": applied,
        "layer_path": "M::Wood::oak", "layer_action": "created",
        "layer_changed_guids": applied[:1], "render_material_applied": True,
    }})
    tools = register(FastMCP("material-result-coverage"), ctx)
    result = json.loads(tools["assign_material"](guids, "oak", apply_render_material=bool(applied_count)))
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


def test_material_layer_rules_only_apply_to_render_assignment(tmp_path):
    from almond_mcp.features.modeling.library import MaterialLibrary
    from almond_mcp.features.modeling.modeling_policy import POLICY

    guid = "00000000-0000-0000-0000-000000000001"
    ctx = context({"status": "success", "result": {"material_id": "oak", "applied_guids": [guid], "metadata_attached": True}})
    material = {**ctx.material_library.get("oak"), "category": "paint:interior"}
    (tmp_path / "manifest.json").write_text(json.dumps({"materials": [material]}))
    ctx.material_library = MaterialLibrary(tmp_path)
    assert ctx.material_library.get("oak") == material
    assign = register(FastMCP("legacy-material"), ctx)["assign_material"]
    assert json.loads(assign([guid], "oak"))["status"] == "error"
    assert ctx.requests == []
    assert json.loads(assign([guid], "oak", False, True, floor="1F"))["status"] == "success"
    assert set(POLICY["material_assignment_keys"]) == {"floor", "construction_detail", "construction_reference", "structural_role"}


def test_old_bridge_rejects_render_assignment_but_can_still_attach_metadata():
    guid = "00000000-0000-0000-0000-000000000001"
    ctx = context({"status": "success", "result": {
        "material_id": "oak", "applied_guids": [guid], "metadata_attached": True,
    }}, material_layer=False)
    tools = register(FastMCP("material-capability"), ctx)
    failed = json.loads(tools["assign_material"]([guid], "oak"))
    assert failed["error_code"] == "unsupported_material_layer_assignment"
    assert failed["mutation_state"] == "not_started"
    assert [r["type"] for r in ctx.requests] == ["get_rhino_context"]
    result = json.loads(tools["assign_material"]([guid], "oak", False, True, floor="1F", structural_role="slab"))
    assert result["status"] == "success" and result["metadata_attached"] is True
    assert result["layer_action"] == "not_applied" and result["layer_changed_guids"] == []
    assert result["layer_path"] is None and result["render_material_applied"] is False
    assert result["structural_role"] == "slab" and "structural_role" in ctx.requests[-1]["script"]


def test_material_result_does_not_confirm_a_move_without_bridge_evidence():
    guid = "00000000-0000-0000-0000-000000000001"
    ctx = context({"status": "success", "result": {
        "material_id": "oak", "applied_guids": [guid], "changed_guids": [],
        "layer_path": "M::Wood::oak", "layer_action": "reused",
        "layer_changed_guids": [guid], "render_material_applied": True,
    }})
    result = json.loads(register(FastMCP("material-unconfirmed"), ctx)["assign_material"]([guid], "oak"))
    assert result["error_code"] == "material_layer_result_unavailable"
    assert result["mutation_state"] == "unknown"


async def check_required_strict_boolean_and_no_operation_argument():
    ctx = context()
    mcp = FastMCP("setup-schema")
    register(mcp, ctx)
    async with Client(mcp) as client:
        tool = next(t for t in await client.list_tools() if t.name == "model_05-setup")
        assert tool.input_schema["required"] == ["overwrite"]
        assert set(tool.input_schema["properties"]) == {"overwrite"}
        baseline = Path(__file__).resolve().parents[3] / "tests/integration/tool_schemas.json"
        assert tool.input_schema == json.loads(baseline.read_text(encoding="utf-8"))["model_05-setup"]["inputSchema"]
        for args in ({}, {"overwrite": None}, {"overwrite": "false"}, {"overwrite": 1}, {"overwrite": False, "operation": "layers"}):
            result = await client.call_tool("model_05-setup", args, raise_on_error=False)
            assert result.is_error
        assert ctx.requests == []


def test_required_strict_boolean_and_no_operation_argument():
    asyncio.run(check_required_strict_boolean_and_no_operation_argument())


def test_unavailable_library_rejected_before_mutation():
    ctx = context()
    ctx.material_library.materials.clear()
    result = json.loads(register(FastMCP("empty-setup"), ctx)["setup_modeling"](False))
    assert result["mutation_state"] == "not_started"
    assert not ctx.requests


def test_native_setup_preservation_and_failure_policy(tmp_path):
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
