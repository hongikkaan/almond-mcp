"""Offline face-edit dispatch and native preflight tests; no Rhino document is opened."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace
from xml.sax.saxutils import escape

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.features.modeling import face_edit
from almond_mcp.features.modeling.tools import register


ROOT = Path(__file__).resolve().parents[3]
OBJECT = "2fc35662-7448-48a9-ab20-27d3e774734e"
MODEL = r"C:\Fixture\model.3dm"


def arguments(**extra):
    return dict(object_id=OBJECT, face_index=0, expected_geometry_crc=123,
                translation=[0, 0, 10], **extra)


@pytest.fixture
def face_tool(monkeypatch):
    monkeypatch.setenv("ALMOND_MODEL_PATH", MODEL)
    context = SimpleNamespace(_send_and_receive=lambda *a, **k: pytest.fail("Unexpected Rhino request"))
    mcp = FastMCP("offline face editing")
    exported = register(mcp, context)
    tool = exported["edit_planar_face"]
    return context, getattr(tool, "fn", tool), mcp


@pytest.mark.parametrize("key,value", [
    ("object_id", "no-guid"), ("object_id", "00000000-0000-0000-0000-000000000000"),
    ("face_index", -1), ("face_index", True), ("face_index", 2**31), ("expected_geometry_crc", -1),
    ("expected_geometry_crc", 2**32), ("expected_geometry_crc", True),
    ("translation", [0, 0]), ("translation", [0, 0, 0]),
    ("translation", [0, False, 10]), ("translation", [0, 0, float("nan")]),
    ("translation", [0, 0, float("inf")]),
])
def test_planar_face_invalid_input_never_dispatches(face_tool, key, value):
    _, tool, _ = face_tool
    args = arguments()
    args[key] = value
    result = json.loads(tool(**args))
    assert result["error_code"] == "invalid_arguments"
    assert result["mutation_state"] == "not_started"


def test_planar_face_schema_rejects_boolean_coordinates(face_tool):
    _, _, mcp = face_tool
    async def verify():
        async with Client(mcp) as client:
            args = arguments()
            args["translation"] = [False, 0, 10]
            result = await client.call_tool("edit_planar_face", args, raise_on_error=False)
            assert result.is_error
    asyncio.run(verify())


def test_planar_face_capability_gate_precedes_mutation(face_tool):
    context, tool, _ = face_tool
    calls = []
    def send(raw, **kwargs):
        calls.append(json.loads(raw))
        return json.dumps(dict(status="success", capabilities={"modeling_materials": 2}))
    context._send_and_receive = send
    result = json.loads(tool(**arguments()))
    assert result["error_code"] == "unsupported_face_edit"
    assert calls == [{"type": "get_rhino_context", "sections": [], "selection_limit": 0}]


def test_planar_face_preserves_native_receipt_and_uses_fixed_operation(face_tool):
    context, tool, _ = face_tool
    calls = []
    reply = dict(status="success", result=dict(edited=True, object_id=OBJECT,
                 previous_geometry_crc=123, geometry_crc=456), request_id="native-request", undo={"ended": True})
    def send(raw, **kwargs):
        payload = json.loads(raw)
        calls.append(payload)
        if payload["type"] == "get_rhino_context":
            return json.dumps(dict(status="success", capabilities={"face_edit": 1}))
        assert payload == dict(type="edit_planar_face", expected_model_path=MODEL, **arguments())
        assert kwargs == {"timeout": 60.0}
        return json.dumps(reply)
    context._send_and_receive = send
    assert json.loads(tool(**arguments())) == reply
    assert [c["type"] for c in calls] == ["get_rhino_context", "edit_planar_face"]


@pytest.mark.parametrize("reply", [
    dict(status="success"), dict(status="success", result_error="serialization"),
    dict(status="success", result=dict(edited=True, object_id=OBJECT,
         previous_geometry_crc=123, geometry_crc=123)),
])
def test_planar_face_missing_result_is_uncertain_and_never_retried(face_tool, reply):
    context, tool, _ = face_tool
    calls = []
    def send(raw, **kwargs):
        payload = json.loads(raw)
        calls.append(payload)
        return json.dumps(dict(status="success", capabilities={"face_edit": 1})
                          if payload["type"] == "get_rhino_context" else reply)
    context._send_and_receive = send
    result = json.loads(tool(**arguments()))
    assert result["mutation_state"] == "unknown" and result["requires_reconciliation"]
    assert result["error_code"] == "face_edit_result_unconfirmed"
    assert len(calls) == 2


def test_planar_face_timeout_and_native_error_retain_uncertainty(face_tool):
    context, tool, _ = face_tool
    calls = []
    def send(raw, **kwargs):
        calls.append(json.loads(raw))
        if len(calls) == 1:
            return json.dumps(dict(status="success", capabilities={"face_edit": 1}))
        raise TimeoutError("native completion unavailable")
    context._send_and_receive = send
    result = json.loads(tool(**arguments()))
    assert result["mutation_state"] == "unknown" and len(calls) == 2
    rejection = dict(status="error", message="Stale face reference", native_completed=True, undo={"ended": True})
    context._send_and_receive = lambda raw, **k: json.dumps(
        dict(status="success", capabilities={"face_edit": 1})
        if json.loads(raw)["type"] == "get_rhino_context" else rejection)
    assert json.loads(tool(**arguments())) == rejection


@pytest.fixture(scope="module")
def planar_face_native(tmp_path_factory):
    sdk = os.environ.get("ALMOND_TEST_DOTNET") or shutil.which("dotnet")
    assert sdk, "The offline native face-edit fixture requires the .NET 8 SDK."
    directory = tmp_path_factory.mktemp("planar-face-native")
    shutil.copyfile(ROOT / "global.json", directory / "global.json")
    assembly = ROOT / "src/rhp/RhinoAlmondBridge/plugin-runtime/Newtonsoft.Json.dll"
    source = ROOT / "src/mcp/rhino/PlanarFaceEditing.cs"
    assert assembly.is_file()
    (directory / "Fixture.csproj").write_text('''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework></PropertyGroup>
  <ItemGroup><Compile Include="''' + escape(str(source)) + '''" />
  <Reference Include="Newtonsoft.Json"><HintPath>''' + escape(str(assembly)) + '''</HintPath></Reference></ItemGroup>
</Project>''', encoding="utf-8")
    (directory / "NuGet.Config").write_text(
        '<configuration><packageSources><clear /></packageSources></configuration>', encoding="utf-8")
    shutil.copyfile(Path(__file__).with_name("fixtures") / "PlanarFaceEditingStub.cs", directory / "Program.cs")
    # Compile the real bounded conversion path, not Json.NET's broader FromObject
    # conversion. Keep Rhino/Undo as doubles without copying the projector logic.
    executor = (ROOT / "src/rhp/RhinoAlmondBridge/ScriptExecutor.cs").read_text(encoding="utf-8")
    capture_start = executor.index("        private const int MaxResultBytes")
    capture_end = executor.index("        /// <summary>\n        /// Wraps raw C# code", capture_start)
    (directory / "ResultCapture.cs").write_text(
        "using System;\nusing System.Collections;\nusing System.Collections.Generic;\n"
        "using System.Linq;\nusing System.Reflection;\nusing System.Text;\n"
        "using Newtonsoft.Json;\nusing Newtonsoft.Json.Linq;\n"
        "namespace RhinoAlmondBridge { public sealed partial class ScriptExecutor {\n"
        + executor[capture_start:capture_end] + "\n} }\n", encoding="utf-8")
    built = subprocess.run([str(sdk), "build", "Fixture.csproj", "-c", "Release", "--nologo",
                            "-p:UseSharedCompilation=false", "-p:NuGetAudit=false", "-nodeReuse:false"],
                           cwd=directory, capture_output=True, text=True)
    assert built.returncode == 0, built.stdout + built.stderr
    return str(sdk), directory / "bin/Release/net8.0/Fixture.dll"


def native_case(fixture, scenario):
    sdk, binary = fixture
    ran = subprocess.run([sdk, str(binary), scenario], capture_output=True, text=True)
    assert ran.returncode == 0, ran.stdout + ran.stderr
    return json.loads(ran.stdout)


def test_planar_face_native_result_crosses_executor_and_public_boundary(planar_face_native, face_tool):
    native = native_case(planar_face_native, "success")
    assert native["replace_calls"] == 1
    assert native["result_error"] is None, native["result_error"]
    assert native["result"]["translation"] == [0, 0, 10]
    context, tool, _ = face_tool
    context._send_and_receive = lambda raw, **kwargs: json.dumps(
        dict(status="success", capabilities={"face_edit": 1})
        if json.loads(raw)["type"] == "get_rhino_context" else native["response"])
    result = json.loads(tool(**arguments()))
    assert result["status"] == "success" and result["result"]["edited"]
    assert result["result"] == native["result"]
    assert "requires_reconciliation" not in result


@pytest.mark.parametrize("scenario", [
    "wrong_path", "read_only", "editor", "stable_editor", "missing", "reference", "definition", "locked", "page", "extrusion",
    "locked_layer", "locked_parent", "missing_layer", "broken_parent", "cyclic_parent",
    "custom_managed_data", "custom_native_data",
    "stale", "face_index", "curved_face", "curved_neighbour", "tangent", "too_small", "bad_original",
])
def test_planar_face_native_preflight_never_touches_original(planar_face_native, scenario):
    result = native_case(planar_face_native, scenario)
    assert result["error"] and result["replace_calls"] == 0 and result["push_calls"] == 0
    assert result["original_untouched"]
    if scenario in ("wrong_path", "read_only", "editor", "stable_editor"):
        assert result["executor_calls"] == 0 and result["mutation_state"] == "not_started"


@pytest.mark.parametrize("scenario", ["null", "invalid", "open", "nonmanifold", "inward", "zero", "nonfinite",
                                      "nochange", "metadata_only", "strings_failure"])
def test_planar_face_native_invalid_result_preserves_original(planar_face_native, scenario):
    result = native_case(planar_face_native, scenario)
    assert result["error"] and result["replace_calls"] == 0 and result["push_calls"] == 1
    assert result["original_untouched"]


@pytest.mark.parametrize("scenario", ["success", "empty_user_strings"])
def test_planar_face_native_success_preserves_identity_attributes_and_geometry_dictionary(planar_face_native, scenario):
    result = native_case(planar_face_native, scenario)
    assert result["error"] is None and result["replace_calls"] == 1 and result["push_calls"] == 1
    assert result["executor_calls"] == 1
    assert result["original_untouched"] and result["attributes_preserved"] and result["dictionary_preserved"]
    assert result["user_strings_preserved"]
    edit = result["result"]
    assert edit["edited"] and edit["object_id"] == OBJECT
    assert edit["previous_geometry_crc"] == 123 and edit["geometry_crc"] == 456
    assert edit["volume_before"] == 100 and edit["volume_after"] == 150


def test_planar_face_native_replace_failure_is_reported_without_second_mutation(planar_face_native):
    result = native_case(planar_face_native, "replace_failure")
    assert result["error"] and result["replace_calls"] == 1
    assert result["original_untouched"]


@pytest.mark.parametrize("scenario,edits", [("no_dictionary", 1), ("no_dictionary_nochange", 0)])
def test_planar_face_native_absent_dictionary_is_not_attached_to_source(planar_face_native, scenario, edits):
    result = native_case(planar_face_native, scenario)
    assert result["replace_calls"] == edits and result["push_calls"] == 1
    assert result["original_untouched"] and result["dictionary_preserved"]
    assert result["user_strings_preserved"]
