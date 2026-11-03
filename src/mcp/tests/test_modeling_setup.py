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


def context(reply=None, *, capability=True):
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
                "modeling_materials": 2, **({"modeling_setup": 1} if capability else {})}})
        if isinstance(reply, Exception):
            raise reply
        return json.dumps(reply or {"status": "success", "result": {"applied": True, "differences": [], "errors": []}})

    return SimpleNamespace(material_library=SimpleNamespace(materials={"oak": material}),
                           construction_library=SimpleNamespace(systems={"floor": system}),
                           _send_and_receive=send, requests=requests)


@pytest.mark.parametrize("overwrite", [False, True])
def test_single_dispatch_and_compact_confirmation(overwrite):
    ctx = context()
    tools = register(FastMCP("setup-test"), ctx)
    assert json.loads(tools["setup_modeling"](overwrite)) == {"status": "success", "applied": True}
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


async def check_required_strict_boolean_and_no_operation_argument():
    ctx = context()
    mcp = FastMCP("setup-schema")
    register(mcp, ctx)
    async with Client(mcp) as client:
        tool = next(t for t in await client.list_tools() if t.name == "setup_modeling")
        assert tool.input_schema["required"] == ["overwrite"]
        assert set(tool.input_schema["properties"]) == {"overwrite"}
        baseline = Path(__file__).resolve().parents[3] / "tests/integration/tool_schemas.json"
        assert tool.input_schema == json.loads(baseline.read_text(encoding="utf-8"))["setup_modeling"]["inputSchema"]
        for args in ({}, {"overwrite": None}, {"overwrite": "false"}, {"overwrite": 1}, {"overwrite": False, "operation": "layers"}):
            result = await client.call_tool("setup_modeling", args, raise_on_error=False)
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
