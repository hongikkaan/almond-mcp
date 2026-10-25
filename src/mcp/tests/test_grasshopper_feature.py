"""Exercise extracted Grasshopper tools, parser, and registry without Rhino."""
import asyncio
import json
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from fastmcp import FastMCP

from almond_mcp.feature_context import FeatureContext
from almond_mcp.features.grasshopper import ghx_parser, tools
from almond_mcp.features.grasshopper.library import LibraryIndexer, _sync_capsule_library
from almond_mcp.features.grasshopper.store import GrasshopperStore
from almond_mcp.retrieval_store import AlmondStore

# Reuse the behavioral capsule contracts against the extracted factory below.
from test_capsules import (
    AUDITED_MANIFEST, REAL_CAPSULE_DIR, BridgeMock, _call, capsule_dir,
    test_sync_skips_invalid_manifests_and_lists_capsules,
    test_list_capsules_filters,
    test_run_rejects_unknown_capsule,
    test_run_refuses_unaudited_capsule,
    test_run_rejects_missing_required_input,
    test_run_rejects_wrong_typed_inputs,
    test_run_rejects_unknown_input_name,
    test_run_happy_path_sends_contract_payload_verbatim_response,
    test_run_omitted_seed_is_sent_as_null,
    test_run_returns_error_json_when_bridge_down,
)


# The mixin comes first so these tests execute extracted SQL before facade cutover.
# After cutover AlmondStore itself already supplies the same mixin.
if issubclass(AlmondStore, GrasshopperStore):
    CapsuleStore = AlmondStore
else:
    class CapsuleStore(GrasshopperStore, AlmondStore):
        pass


def _load_feature(tmp_path, capsule_dir):
    namespace = ModuleType("grasshopper_feature_fixture")
    namespace.retrieval_store = CapsuleStore(tmp_path / "state.sqlite3")
    namespace.CAPSULE_LIBRARY_DIR = str(capsule_dir)
    namespace.LIBRARY_DIR = str(tmp_path / "logic")
    namespace.indexer = LibraryIndexer(namespace.LIBRARY_DIR)
    namespace.capsule_sync_report = _sync_capsule_library(
        namespace.retrieval_store, namespace.CAPSULE_LIBRARY_DIR,
    )
    namespace._send_and_receive = lambda *_args, **_kwargs: pytest.fail(
        "A test must explicitly replace the bridge sender."
    )
    namespace.mcp = FastMCP("Grasshopper fixture")
    namespace.context = FeatureContext(vars(namespace))
    vars(namespace).update(tools.register(namespace.mcp, namespace.context))
    return namespace


@pytest.fixture()
def server(tmp_path, capsule_dir):
    return _load_feature(tmp_path, capsule_dir)


def test_real_capsule_library_syncs_cleanly(tmp_path):
    feature = _load_feature(tmp_path, REAL_CAPSULE_DIR)
    assert feature.capsule_sync_report["skipped"] == []
    payload = json.loads(_call(feature.list_capsules))
    assert payload["total"] == 8
    assert all(card["capability"] == "analyze" for card in payload["capsules"])


def test_factory_registers_existing_public_signatures(server):
    registered = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}
    assert set(registered) == {
        "list_library", "get_logic_by_id", "list_capsules", "run_gh_definition",
    }
    assert registered["list_library"].parameters["properties"] == {}
    assert registered["get_logic_by_id"].parameters["required"] == ["logic_id"]
    assert set(registered["list_capsules"].parameters["properties"]) == {
        "capability", "audited_only",
    }
    run_schema = registered["run_gh_definition"].parameters
    assert set(run_schema["properties"]) == {"capsule_id", "inputs", "seed", "timeout_s"}
    assert run_schema["required"] == ["capsule_id", "inputs"]
    assert run_schema["properties"]["timeout_s"]["default"] == 60.0


def test_factory_reads_rebound_context_services_and_keeps_instances_independent(
    server, tmp_path, capsule_dir, monkeypatch,
):
    second = _load_feature(tmp_path / "second", capsule_dir)
    replacement_page = {"total": 0, "capsules": []}
    monkeypatch.setattr(server, "retrieval_store", SimpleNamespace(
        search_capsules=lambda **_kwargs: replacement_page,
    ))
    monkeypatch.setattr(server, "CAPSULE_LIBRARY_DIR", "rebound-capsules")
    listing = json.loads(_call(server.list_capsules))
    assert listing == {"capsule_library_dir": "rebound-capsules", **replacement_page}
    assert json.loads(_call(second.list_capsules))["total"] == 2
    with second.context.override(retrieval_store=server.retrieval_store):
        assert json.loads(_call(second.list_capsules))["total"] == 0
    assert json.loads(_call(second.list_capsules))["total"] == 2


def test_logic_tools_use_current_indexer_and_parse_ghx_before_gh(server, tmp_path, monkeypatch):
    library = tmp_path / "logic-files"
    library.mkdir()
    (library / "Beam.ghx").write_bytes(b"<Archive>Karamba Assemble Model</Archive>")
    (library / "Beam.gh").write_bytes(b"not compressed")
    (library / "notes.json").write_text(json.dumps({"title": "Only metadata"}), encoding="utf-8")
    monkeypatch.setattr(server, "LIBRARY_DIR", str(library))
    monkeypatch.setattr(server, "indexer", LibraryIndexer(str(library)))
    listing = json.loads(_call(server.list_library))
    assert listing == {
        "library_dir": str(library), "total_entries": 2, "logic_ids": ["beam", "notes"],
    }
    parsed = json.loads(_call(server.get_logic_by_id, logic_id="BEAM"))
    assert parsed["file_name"] == "Beam.ghx"
    assert parsed["components"]
    metadata = json.loads(_call(server.get_logic_by_id, logic_id="notes"))
    assert metadata["metadata"] == {"title": "Only metadata"}
    assert "not found" in json.loads(_call(server.get_logic_by_id, logic_id="missing"))["error"]


def test_old_parser_path_is_same_module_and_keeps_manifest_lookup(tmp_path, monkeypatch):
    from almond_mcp import ghx_parser as compatibility

    assert compatibility is ghx_parser
    capsule_dir = tmp_path / "capsules"
    capsule_dir.mkdir()
    definition = tmp_path / "TestBeam.ghx"
    definition.write_bytes(b"<Archive>Karamba Assemble Model</Archive>")
    library_manifest = capsule_dir / "test_beam_v1.capsule.json"
    library_manifest.write_text(json.dumps(AUDITED_MANIFEST), encoding="utf-8")
    monkeypatch.setattr(compatibility, "CAPSULES_DIR", str(capsule_dir))
    parsed = ghx_parser.GHParser(str(definition)).parse()
    assert parsed.metadata["capsule"]["capsule_id"] == "test_beam_v1"
    assert parsed.metadata["capsule_manifest_path"] == str(library_manifest)
    adjacent = definition.with_suffix(".capsule.json")
    adjacent.write_text(json.dumps({**AUDITED_MANIFEST, "capsule_id": "adjacent"}), encoding="utf-8")
    assert ghx_parser.GHParser(str(definition)).parse().metadata["capsule"]["capsule_id"] == "adjacent"


def test_registry_transaction_rollback_pruning_and_query_pagination(tmp_path):
    store = CapsuleStore(tmp_path / "capsules.sqlite3")
    first = {**AUDITED_MANIFEST, "_manifest_path": "preserved/local/path"}
    second = {**AUDITED_MANIFEST, "capsule_id": "second", "audited": False, "title": "Second beam"}
    assert store.sync_capsules([first, second]) == 2
    assert store.get_capsule(" test_beam_v1 ") == first
    page = store.search_capsules(query="beam", capability=" ANALYZE ", limit=1)
    assert page["total"] == 2
    assert page["next_offset"] == 1
    assert page["capsules"][0]["capsule_id"] == "test_beam_v1"
    assert "_manifest_path" not in page["capsules"][0]
    next_page = store.search_capsules(query="beam", limit=1, offset=page["next_offset"])
    assert next_page["capsules"][0]["capsule_id"] == "second"
    assert next_page["next_offset"] is None
    with pytest.raises(ValueError, match="missing keys"):
        store.sync_capsules([{**first, "title": "must roll back"}, {"capsule_id": "invalid"}])
    assert store.get_capsule("test_beam_v1") == first
    assert store.search_capsules()["total"] == 2
    assert store.sync_capsules([second]) == 1
    assert store.get_capsule("test_beam_v1") is None
    assert store.sync_capsules([]) == 0
    assert store.search_capsules()["total"] == 0


def test_run_resolves_rebound_capsule_directory_and_timeout_response(server, monkeypatch):
    manifest = {**AUDITED_MANIFEST}
    monkeypatch.setattr(server, "retrieval_store", SimpleNamespace(get_capsule=lambda _id: manifest))
    monkeypatch.setattr(server, "CAPSULE_LIBRARY_DIR", "rebound-dir")
    mock = BridgeMock('{"status":"ok"}')
    monkeypatch.setattr(server, "_send_and_receive", mock)
    assert _call(server.run_gh_definition, capsule_id="test_beam_v1", inputs={
        "ALMOND_IN_LINES": {"guids": ["guid"]},
    }) == '{"status":"ok"}'
    assert mock.payloads[0][0]["manifest_path"] == str(Path("rebound-dir") / "test_beam_v1.capsule.json")
    import socket

    def timeout(*_args, **_kwargs):
        raise socket.timeout()

    monkeypatch.setattr(server, "_send_and_receive", timeout)
    response = json.loads(_call(server.run_gh_definition, capsule_id="test_beam_v1", inputs={
        "ALMOND_IN_LINES": {"guids": ["guid"]},
    }))
    assert "timed out" in response["message"]


def test_legacy_parser_module_command_still_parses_a_definition(tmp_path):
    import subprocess
    import sys

    definition = tmp_path / "CommandBeam.ghx"
    definition.write_bytes(b"<Archive>Karamba Assemble Model</Archive>")
    run = subprocess.run(
        [sys.executable, "-B", "-X", "utf8", "-m", "almond_mcp.ghx_parser", str(definition)],
        capture_output=True, text=True, encoding="utf-8", timeout=30, check=True,
    )
    parsed = json.loads(run.stdout)
    assert parsed["file_name"] == "CommandBeam.ghx"
    assert parsed["components"]
