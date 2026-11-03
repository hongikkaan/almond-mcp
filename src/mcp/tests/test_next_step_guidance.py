"""Follow-up guidance retains usable handles and never advances uncertain work."""
from pathlib import Path
import json
from types import SimpleNamespace

import pytest

from almond_mcp.features.assets.output import project
from almond_mcp.features.assets import preparation
from almond_mcp.query_output import project_query


def test_source_only_placement_returns_conversion_inputs_without_native_work(monkeypatch):
    from fastmcp import FastMCP
    from almond_mcp.features.assets import model_index
    from almond_mcp.features.assets.tools import register
    monkeypatch.setattr(model_index, "for_context", lambda _: SimpleNamespace(get=lambda _: {"source_only": True}))
    tools = register(FastMCP("source-only"), SimpleNamespace())
    result = json.loads(tools["place_drawing_asset"](asset_id="legacy-model"))
    assert result["mutation_state"] == "not_started"
    assert result["next_tool"] == "prepare_drawing_asset"
    assert "source_file" in result["next_step"] and "retain the ID supplied" in result["next_step"]


@pytest.mark.parametrize("identity", ["asset_id", "id"])
@pytest.mark.parametrize("include_ids", [False, True])
def test_conversion_guidance_survives_summary_and_identity_projection(identity, include_ids):
    source = {identity: "example-model", "name": "Example", "next_tool": "prepare_drawing_asset", "source_only": True}
    projected = project_query(project({"assets": [source]}, []), include_ids=include_ids)["assets"][0]
    assert projected["next_tool"] == "prepare_drawing_asset"
    assert (identity in projected) == include_ids
    assert "stage='inspect'" in projected["next_step"]
    assert "source_file" in projected["next_step"] and "include_ids=true" in projected["next_step"]
    assert "project-relative" in projected["next_step"]
    assert "next_step" not in source  # Projection does not alter the cached index.


def test_refresh_detail_reuses_supplied_id_and_ready_or_empty_results_do_not_invent_work():
    detail = project_query(project({"asset": {"asset_id": "existing", "next_tool": "refresh_asset"}}, None),
                           include_ids=True, supplied={"asset_id": "existing"})["asset"]
    assert "asset_id" not in detail
    assert "ID supplied" in detail["next_step"] and "refresh_asset(asset_id=" in detail["next_step"]
    assert "next_step" not in project({"asset": {"asset_id": "ready", "model_status": "ready"}}, None)["asset"]
    assert project({"assets": [], "total": 0}, None) == {"assets": [], "total": 0}


@pytest.mark.parametrize("state", ["running", "unconfirmed", "failed"])
def test_uncertain_preparation_never_advances_to_mutating_stage(state):
    value = preparation.present(Path("unused-job"), {"state": state, "error": "Unconfirmed", "stages": {}})
    assert value["status"] == "error" and value["next_stage"] is None
    assert "stage='status'" in value["next_step"] and "do not replay" in value["next_step"]


@pytest.mark.parametrize("state,stage", [("inspected", "inspect"), ("normalized", "normalize"), ("verified", "verify"), ("ready", "verify")])
def test_preparation_guidance_uses_available_job_and_review_evidence(monkeypatch, state, stage):
    monkeypatch.setattr(preparation, "_report", lambda *args: {"summary": {}, "previews": []})
    value = preparation.present(Path("unused-job"), {"state": state, "stages": {stage: {"output_sha256": "hash"}}}, field_groups=[])
    assert "job_dir" in value and "job_dir" in value["next_step"]
    if state == "verified":
        assert value["review_targets"]["final_sha256"] == "hash"
        assert "Review the final preview images" in value["next_step"]
        assert "field_groups=['previews']" in value["next_step"] and "register_drawing_asset" not in value["next_step"]
    elif state == "ready":
        assert value["ready_for_registration"] is True and value["source_3dm"].endswith("final.3dm")
        assert "register_drawing_asset" in value["next_step"] and "preparation_job=job_dir" in value["next_step"]
    else:
        assert "stage='verify'" in value["next_step"] and not value["ready_for_registration"]
