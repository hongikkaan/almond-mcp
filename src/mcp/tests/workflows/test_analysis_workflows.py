import json
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastmcp import FastMCP

from almond_mcp.features.structure.tools import register
from almond_mcp.retrieval_store import AlmondStore


VALIDATE = "analysis_02-validate_structure"
EXPORT = "analysis_04-export_structural_report"
BEAM_ID = str(UUID(int=1))


def analysis_server(database, bridge):
    server = FastMCP("Analysis workflow")
    register(server, SimpleNamespace(retrieval_store=AlmondStore(database), _send_and_receive=bridge))
    return server


def test_cantilever_report(tmp_path, call_tool):
    database = tmp_path / "project.sqlite3"
    length_m, breadth_m, depth_m = 2.0, 0.3, 0.5
    elasticity_kn_m2, tip_load_kn = 33_000_000, 1.0  # C30/37 in kN and m.
    model = {
        "status": "ok", "shells": 0, "tolerance_m": 0.001,
        "max_member_span_m": length_m, "max_span_m": length_m, "anchor_points": [[0, 0, 0]],
        "members": [{"source_guids": [BEAM_ID], "points": [[0, 0, 0], [length_m, 0, 0]],
                     "section": {"shape": "solid_rectangle", "width": breadth_m, "height": depth_m}}],
    }

    def bridge(raw, **_options):
        request = json.loads(raw)
        assert request["type"] == "structure_model" and request["guids"] == [BEAM_ID]
        return json.dumps(model)

    _, result = call_tool(analysis_server(database, bridge), VALIDATE, guids=[BEAM_ID],
                          engine="native", load_kn=tip_load_kn, material="Concrete", self_weight=False,
                          stability="off", structure_type="canopy")
    assert result["status"] == "indicative" and result["passed"] is None
    # Euler–Bernoulli displacement of a fixed cantilever with a tip load, in mm.
    inertia_m4 = breadth_m * depth_m**3 / 12
    expected_mm = 1000 * tip_load_kn * length_m**3 / (3 * elasticity_kn_m2 * inertia_m4)
    assert result["results"]["max_deflection_mm"] == pytest.approx(expected_mm, abs=0.0005)
    assert result["results"]["reactions_kn"] == pytest.approx(tip_load_kn)

    run, = AlmondStore(database).list_validation_runs()
    assert run["result"]["passed"] is None
    assert run["analysis"]["inputs"]["model"] == model
    assert run["request"]["self_weight"] is False

    def unavailable_bridge(*_args, **_options):
        pytest.fail("Persisted analysis must export without asking Rhino for geometry")

    report = tmp_path / "cantilever.md"
    _, output = call_tool(analysis_server(database, unavailable_bridge), EXPORT, path=str(report))
    assert output["status"] == "success" and output["runs"] == 1
    assert "native (INDICATIVE)" in report.read_text(encoding="utf-8")


def test_invalid_model_has_no_run(tmp_path, call_tool):
    database = tmp_path / "project.sqlite3"

    def bridge(raw, **_options):
        assert json.loads(raw)["type"] == "structure_model"
        return json.dumps({"status": "ok", "members": []})

    server = analysis_server(database, bridge)
    _, result = call_tool(server, VALIDATE, guids=[BEAM_ID], engine="native")
    assert result["status"] == "error"
    assert AlmondStore(database).list_validation_runs() == []
    report = tmp_path / "invalid.md"
    assert call_tool(server, EXPORT, path=str(report))[1]["status"] == "error"
    assert not report.exists()
