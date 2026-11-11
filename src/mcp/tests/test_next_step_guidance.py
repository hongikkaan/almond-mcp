"""Follow-up guidance retains usable handles and never advances uncertain work."""
from pathlib import Path
import json
from types import SimpleNamespace

import pytest
from jsonschema import validate
from almond_mcp.output_contracts import public_output_schema

from almond_mcp.features.assets.output import project
from almond_mcp.features.assets import preparation
from almond_mcp.query_output import project_query
from almond_mcp.tool_guidance import guide_payload


def test_source_only_placement_returns_conversion_inputs_without_native_work(monkeypatch):
    from fastmcp import FastMCP
    from almond_mcp.features.assets import model_index
    from almond_mcp.features.assets.tools import register
    monkeypatch.setattr(model_index, "for_context", lambda _: SimpleNamespace(get=lambda _: {"source_only": True}))
    tools = register(FastMCP("source-only"), SimpleNamespace())
    result = json.loads(tools["place_drawing_asset"](asset_id="legacy-model"))
    assert result["mutation_state"] == "not_started"
    assert result["next_tool"] == "asset_07-prepare"
    assert "source_file" in result["next_step_guide"] and "source_file" in result["next_step_guide"]


@pytest.mark.parametrize("identity", ["asset_id", "id"])
@pytest.mark.parametrize("include_ids", [False, True])
def test_conversion_guidance_survives_summary_and_identity_projection(identity, include_ids):
    source = {identity: "example-model", "name": "Example", "next_tool": "prepare_drawing_asset", "source_only": True}
    projected = project_query(project({"assets": [source]}, []), include_ids=include_ids)["assets"][0]
    assert projected["next_tool"] == "asset_07-prepare"
    assert (identity in projected) == include_ids
    assert "stage='inspect'" in projected["next_step_guide"]
    assert "source_file" in projected["next_step_guide"] and "원본 단위" in projected["next_step_guide"]
    assert "프로젝트 기준" in projected["next_step_guide"]
    assert "next_step_guide" not in source  # Projection does not alter the cached index.


def test_refresh_detail_reuses_supplied_id_and_ready_or_empty_results_do_not_invent_work():
    detail = project_query(project({"asset": {"asset_id": "existing", "next_tool": "refresh_asset"}}, None),
                           include_ids=True, supplied={"asset_id": "existing"})["asset"]
    assert "asset_id" not in detail
    assert "조회에 사용한 asset_id" in detail["next_step_guide"] and "asset_08-refresh" in detail["next_step_guide"]
    assert "next_step_guide" not in project({"asset": {"asset_id": "ready", "model_status": "ready"}}, None)["asset"]
    assert project({"assets": [], "total": 0}, None) == {"assets": [], "total": 0}


@pytest.mark.parametrize("state", ["running", "unconfirmed", "failed"])
def test_uncertain_preparation_never_advances_to_mutating_stage(state):
    value = preparation.present(Path("unused-job"), {"state": state, "error": "Unconfirmed", "stages": {}})
    validate(value, public_output_schema('prepare_drawing_asset', wrapped=False))
    assert value["status"] == "error" and value["next_stage"] is None
    assert "stage='status'" in value["next_step_guide"] and "do not replay" in value["next_step_guide"]


@pytest.mark.parametrize("state,stage", [("inspected", "inspect"), ("normalized", "normalize"), ("verified", "verify"), ("ready", "verify")])
def test_preparation_guidance_uses_available_job_and_review_evidence(monkeypatch, state, stage):
    monkeypatch.setattr(preparation, "_report", lambda *args: {"summary": {}, "previews": []})
    value = guide_payload("prepare_drawing_asset", preparation.present(
        Path("unused-job"), {"state": state, "stages": {stage: {"output_sha256": "hash"}}}, field_groups=[]))
    assert "job_dir" in value and "job_dir" in value["next_step_guide"]
    if state == "verified":
        assert value["review_targets"]["final_sha256"] == "hash"
        assert "Review the final preview images" in value["next_step_guide"]
        assert "field_groups=['previews']" in value["next_step_guide"] and "asset_09-register" not in value["next_step_guide"]
    elif state == "ready":
        assert value["ready_for_registration"] is True and value["source_3dm"].endswith("final.3dm")
        assert "asset_09-register" in value["next_step_guide"] and "preparation_job=job_dir" in value["next_step_guide"]
    else:
        assert "stage='verify'" in value["next_step_guide"] and not value["ready_for_registration"]
