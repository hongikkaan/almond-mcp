"""Exercise the extracted factory and its existing material safety contracts."""
import asyncio
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.features.modeling import modeling_policy, modeling_setup
from almond_mcp.features.modeling.library import MaterialLibrary
from almond_mcp.features.modeling.tools import register


TOOL_NAMES = {
    "get_modeling_policy", "execute_rhino_script", "setup_modeling",
    "list_materials", "assign_material", "save_rhino_document", "edit_planar_face",
}
PACKAGE = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def original_server(tmp_path_factory):
    # The old server remains the schema baseline until the coordinator cuts over.
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("RHINO_MCP_STATE_DB", str(tmp_path_factory.mktemp("modeling") / "state.sqlite3"))
        spec = importlib.util.spec_from_file_location("almond_modeling_baseline", PACKAGE / "server.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


@pytest.fixture
def feature(original_server):
    context = SimpleNamespace(
        material_library=MaterialLibrary(original_server.MATERIAL_LIBRARY_DIR),
        construction_library=original_server.construction_library,
        _send_and_receive=lambda *a, **k: pytest.fail("Unexpected live Rhino request"),
        MaterialLibrary=MaterialLibrary,
        modeling_policy=modeling_policy,
        modeling_setup=modeling_setup,
    )
    context.mcp = FastMCP("modeling feature test")
    context.__dict__.update(register(context.mcp, context))
    return context


def call(tool, **arguments):
    return json.loads(getattr(tool, "fn", tool)(**arguments))


def test_factory_preserves_public_schema_and_policy_roundtrip(feature, original_server):
    async def verify():
        async with Client(feature.mcp) as client, Client(original_server.mcp) as baseline:
            current = {t.name: t.model_dump(mode="json", by_alias=True, exclude_none=True)
                       for t in await client.list_tools()}
            previous = {t.name: t.model_dump(mode="json", by_alias=True, exclude_none=True)
                        for t in await baseline.list_tools()}
            assert current.keys() == TOOL_NAMES
            assert current == {name: previous[name] for name in TOOL_NAMES}
            result = await client.call_tool("get_modeling_policy", {})
            assert result.structured_content == {"status": "success", "policy": modeling_policy.POLICY}
    asyncio.run(verify())


def test_server_and_recipe_use_canonical_modeling_dependencies(original_server, monkeypatch):
    assert original_server.modeling_policy is modeling_policy
    assert original_server.modeling_setup is modeling_setup
    assert modeling_setup.modeling_policy is modeling_policy
    expected = json.loads((PACKAGE / "modeling_policy.json").read_text(encoding="utf-8"))
    assert modeling_policy.POLICY == expected
    monkeypatch.setattr(modeling_policy, "validate_material", lambda material: {
        "material_id": "patched", "name": "Patched", "base_color": [1, 2, 3],
        "metallic": 0, "roughness": 1, "opacity": 1,
    })
    assert modeling_setup.recipe({})["material_id"] == "patched"


def test_current_library_and_sender_are_resolved_for_each_call(feature):
    assert call(feature.list_materials, category="metal")["materials"]
    replacement = SimpleNamespace(
        directory=Path("replacement-library"),
        materials={},
        list=lambda **kwargs: [],
    )
    feature.material_library = replacement
    assert call(feature.list_materials, field_groups=["paths"]) == {
        "total": 0, "materials": [], "library_dir": str(replacement.directory),
    }
    sent = []
    feature._execute_rhinocode = lambda *args: sent.append(args) or {"status":"success","result":1}
    assert call(feature.execute_rhino_script, script="first")["result"] == 1
    feature._execute_rhinocode = lambda *args: {"status":"success","result":2}
    assert call(feature.execute_rhino_script, script="second")["result"] == 2
    assert sent == [("first", "python", 60)]


def test_separate_registration_has_separate_context(feature, original_server):
    second = SimpleNamespace(
        material_library=MaterialLibrary(original_server.MATERIAL_LIBRARY_DIR),
        construction_library=original_server.construction_library,
        _execute_rhinocode=lambda *args: {"status":"success","result":"second"},
    )
    second.__dict__.update(register(FastMCP("second modeling context"), second))
    feature._execute_rhinocode = lambda *args: {"status":"success","result":"first"}
    assert call(feature.execute_rhino_script, script="test")["result"] == "first"
    assert call(second.execute_rhino_script, script="test")["result"] == "second"


@pytest.mark.parametrize("language, dispatched", [
    ("python", "python"), ("python2", "python2"), ("csharp", "csharp-script"),
    ("csharp-script", "csharp-script"), ("command", "command"),
])
def test_official_execution_is_bound_and_never_falls_back_to_legacy(feature, language, dispatched):
    requests = []
    feature._execute_rhinocode = lambda source, language, timeout: requests.append(
        (source, language, timeout)) or {"status": "running", "request_id": "owned-request"}
    result = call(feature.execute_rhino_script, script="source", language=language, timeout_seconds=5)
    assert result == {"status": "running", "request_id": "owned-request"}
    assert requests == [("source", dispatched, 5)]


def test_missing_official_runtime_is_not_started(feature):
    result = call(feature.execute_rhino_script, script="result = 42", language="python")
    assert result["error_code"] == "rhinocode_unavailable"
    assert result["mutation_state"] == "not_started"


def test_official_failure_is_not_replayed(feature):
    requests = []
    def execute(*args):
        requests.append(args)
        raise RuntimeError("receipt unavailable after dispatch")
    feature._execute_rhinocode = execute
    with pytest.raises(RuntimeError, match="receipt unavailable"):
        call(feature.execute_rhino_script, script="result = 42", language="python")
    assert len(requests) == 1


@pytest.mark.parametrize("arguments", [
    {"script": " "}, {"script": "result = 1", "language": "vbscript"},
    {"script": "result = 1", "language": []},
    {"script": "result = 1", "timeout_seconds": True},
    {"script": "result = 1", "timeout_seconds": 601},
])
def test_execution_validation_precedes_any_dispatch(feature, arguments):
    feature._execute_rhinocode = lambda *args: pytest.fail("Unexpected official execution")
    assert call(feature.execute_rhino_script, **arguments)["error_code"] == "invalid_arguments"


def test_script_timeout_schema_does_not_coerce_boolean(feature):
    async def verify():
        async with Client(feature.mcp) as client:
            result = await client.call_tool("execute_rhino_script", {
                "script": "result = 1", "language": "python", "timeout_seconds": True}, raise_on_error=False)
            assert result.is_error
    asyncio.run(verify())
