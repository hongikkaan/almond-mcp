"""Exercise the extracted factory and its existing material safety contracts."""
import asyncio
import importlib.util
import json
import socket
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP

from almond_mcp.features.modeling import modeling_policy, modeling_setup
from almond_mcp.features.modeling.library import MaterialLibrary
from almond_mcp.features.modeling.tools import register
import test_materials as material_contracts


TOOL_NAMES = {
    "get_modeling_policy", "execute_rhino_script", "setup_modeling",
    "list_materials", "assign_material", "save_rhino_document",
}
PACKAGE = Path(__file__).resolve().parents[1] / "almond_mcp"


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
    feature._send_and_receive = lambda payload, **kwargs: sent.append(json.loads(payload)) or '{"status":"success","result":1}'
    assert call(feature.execute_rhino_script, script="first")["result"] == 1
    feature._send_and_receive = lambda payload, **kwargs: '{"status":"success","result":2}'
    assert call(feature.execute_rhino_script, script="second")["result"] == 2
    assert sent == [{"type": "execute", "script": "first"}]


def test_separate_registration_has_separate_context(feature, original_server):
    second = SimpleNamespace(
        material_library=MaterialLibrary(original_server.MATERIAL_LIBRARY_DIR),
        construction_library=original_server.construction_library,
        _send_and_receive=lambda payload, **kwargs: '{"status":"success","result":"second"}',
    )
    second.__dict__.update(register(FastMCP("second modeling context"), second))
    feature._send_and_receive = lambda payload, **kwargs: '{"status":"success","result":"first"}'
    assert call(feature.execute_rhino_script, script="test")["result"] == "first"
    assert call(second.execute_rhino_script, script="test")["result"] == "second"


@pytest.mark.parametrize("exception, message", [
    (socket.timeout(), "Rhino bridge timed out (>60s)."),
    (ConnectionRefusedError(), "Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?"),
    (RuntimeError("wire failed"), "Bridge error: wire failed"),
])
def test_executor_preserves_errors_without_retry(feature, exception, message):
    requests = []
    def send(payload, **kwargs):
        requests.append(payload)
        raise exception
    feature._send_and_receive = send
    assert call(feature.execute_rhino_script, script="test") == {"status": "error", "message": message}
    assert len(requests) == 1


@pytest.mark.parametrize("contract", [
    material_contracts.test_assignment_checks_capability_and_returns_actual_guids_and_metadata,
    material_contracts.test_older_bridge_is_rejected_before_assignment,
    material_contracts.test_metadata_only_assignment_does_not_claim_native_material_change,
    material_contracts.test_assignment_timeout_is_unknown_and_never_retried,
    material_contracts.test_setup_rejects_unsafe_bridge_without_dispatch,
], ids=lambda contract: contract.__name__)
def test_existing_material_safety_contracts_use_extracted_factory(feature, monkeypatch, contract):
    contract(feature, monkeypatch)


@pytest.mark.parametrize("overwrite, encoded", [(None, "null"), (True, "true"), (False, "false")])
def test_extracted_setup_preserves_overwrite_choice(feature, monkeypatch, overwrite, encoded):
    material_contracts.test_material_setup_preserves_overwrite_choice(feature, monkeypatch, overwrite, encoded)


def test_extracted_library_keeps_legacy_manifest_read_only(feature, tmp_path, monkeypatch):
    material_contracts.test_policy_keys_and_legacy_manifest_fallback(feature, tmp_path, monkeypatch)
