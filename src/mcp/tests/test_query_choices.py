"""Agent situations exercise field choices at the feature API boundary."""
import importlib
import json
from types import SimpleNamespace

import pytest
from fastmcp import FastMCP


@pytest.mark.parametrize("feature,tool,context,collection,detail,group", [
    ("modeling", "list_materials", {"material_library": SimpleNamespace(
        directory="private-materials", list=lambda **_: [{"material_id": "steel", "name": "Steel",
        "category": "metal", "base_color": [150, 170, 120], "created_at": "yesterday"}])},
     "materials", "base_color", "display"),
    ("drawings", "list_drawing_recipes", {"drawing_recipe_indexer": SimpleNamespace(recipes={
        "axon": {"name": "Axon", "description": "Axon view", "projection": {"type": "axon"},
                 "recommended_scales": [50, 100]}})}, "recipes", "recommended_scales", "scales"),
    ("guidance", "get_typology_narrative", {"history_library": SimpleNamespace(source="Narration only",
        list=lambda **_: [{"typology_id": "court", "name": "Courtyard", "era": "historic",
                           "narrative": "A long story", "created_at": "yesterday"}])},
     "entries", "narrative", "narrative"),
    ("grasshopper", "list_capsules", {"CAPSULE_LIBRARY_DIR": "private-capsules",
        "retrieval_store": SimpleNamespace(search_capsules=lambda **_: {"total": 1, "capsules": [
            {"capsule_id": "beam", "title": "Beam", "audited": True, "inputs": [{"name": "span"}],
             "created_at": "yesterday"}]})}, "capsules", "inputs", "ports"),
])
def test_agent_chooses_detail_only_after_reading_a_shortlist(feature, tool, context, collection, detail, group):
    """Given candidate names, detail appears only when the agent selects its purpose."""
    tools = importlib.import_module(f"almond_mcp.features.{feature}.tools").register(
        FastMCP("query-choice"), SimpleNamespace(**context))
    query = tools[tool]
    plain = json.loads(query())
    assert detail not in plain[collection][0] and "created_at" not in plain[collection][0]
    chosen = json.loads(query(field_groups=[group]))
    assert chosen[collection][0][detail]
    assert "created_at" not in chosen[collection][0]
    full = json.loads(query(field_groups=["all"], include_ids=True))
    assert full[collection][0][detail]
    assert json.loads(query(field_groups=["unexpected"]))["error_code"] == "invalid_arguments"


def test_agent_never_loses_uncertainty_or_completion_evidence_to_a_summary():
    """Given uncertain completion, the agent receives the evidence needed to avoid retrying."""
    component = {"component_id": "facade", "name": "Facade", "status": "unknown",
                 "mutation_applied": None, "requires_reconciliation": True,
                 "native_completion": {"request_id": "request-7", "object_ids": ["member-1"]},
                 "objects": [{"rhino_guid": "member-1"}], "warnings": ["Check completion first"]}
    calls = []
    context = SimpleNamespace(retrieval_store=SimpleNamespace(
        get_component=lambda *args, **kwargs: calls.append(args) or component))
    tools = importlib.import_module("almond_mcp.features.components.tools").register(FastMCP("evidence"), context)
    unknown = json.loads(tools["get_design_component"]("facade"))
    assert unknown["component"] == component
    calls.clear()
    rejected = json.loads(tools["get_design_component"]("facade", live=True, field_groups=["unexpected"]))
    assert rejected["error_code"] == "invalid_arguments" and calls == []


def test_scene_write_ack_keeps_proof_and_new_handle_without_echoing_the_snapshot():
    """Given a confirmed write, its handle/count/proof supports continuation without rereading."""
    proof = {"request_id": "request-8", "object_ids": ["member-1"], "observed_at": "verified-time"}
    scene = {"scene_id": "new-scene", "name": "Courtyard", "revision": 2, "objects": 1,
             "direct_objects": 1, "created_at": "yesterday", "native_proof": proof,
             "live_verified": True, "warnings": ["Limited to requested scope"]}
    context = SimpleNamespace(retrieval_store=SimpleNamespace(create_scene=lambda **_: scene))
    tools = importlib.import_module("almond_mcp.features.scenes.tools").register(FastMCP("ack"), context)
    ack = json.loads(tools["create_design_scene"]("Courtyard"))["scene"]
    assert ack["scene_id"] == "new-scene" and ack["revision"] == 2 and ack["direct_objects"] == 1
    assert ack["native_proof"] == proof and ack["warnings"] == ["Limited to requested scope"]
    assert "name" not in ack and "created_at" not in ack
