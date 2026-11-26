import json
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastmcp import FastMCP

from almond_mcp.features.structure.tools import register
from almond_mcp.retrieval_store import AlmondStore


VALIDATE = "analysis_02-validate_structure"
VISUALIZE = "analysis_03-visualize_structure"
EXPORT = "analysis_04-export_structural_report"
BEAM_ID = str(UUID(int=1))
SECOND_MEMBER_ID = str(UUID(int=2))


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
                          stability="off", structure_type="canopy", detail=True)
    assert result["status"] == "indicative" and result["passed"] is None
    # Euler–Bernoulli displacement of a fixed cantilever with a tip load, in mm.
    inertia_m4 = breadth_m * depth_m**3 / 12
    expected_mm = 1000 * tip_load_kn * length_m**3 / (3 * elasticity_kn_m2 * inertia_m4)
    assert result["results"]["max_deflection_mm"] == pytest.approx(expected_mm, abs=0.0005)
    assert result["supports"][0]["sls"]["Fz"] == pytest.approx(tip_load_kn)
    assert result["members"][0]["source_guids"] == [BEAM_ID]

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


@pytest.mark.parametrize(
    ("structure_type", "anchors", "axes", "force", "expected"),
    [
        ("truss", [[-1, 0, 0], [1, 0, 0]], [[[-1, 0, 0], [0, 0, 1]], [[1, 0, 0], [0, 0, 1]]],
         "n_compression_kn", 10.607),
        ("frame", [[0, 0, 0]], [[[0, 0, 0], [2, 0, 0]], [[2, 0, 0], [2, 1, 0]]], "t_max_knm", 7.5),
    ],
)
def test_member_design_forces(tmp_path, call_tool, structure_type, anchors, axes, force, expected):
    guids = [BEAM_ID, SECOND_MEMBER_ID]
    # A symmetric 45° truss splits the factored load over its struts.
    # The offset cantilever transfers half the factored load at a 1 m lever arm.
    members = [{"source_guids": [guid], "points": axis,
                "section": {"shape": "solid_rectangle", "width": 0.3, "height": 0.5}}
               for guid, axis in zip(guids, axes, strict=True)]
    if structure_type == "truss":
        for member in members:
            member["release"] = "pinned"
    model = {"status": "ok", "shells": 0, "anchor_points": anchors, "members": members}
    server = analysis_server(tmp_path / "project.sqlite3", lambda *_args, **_options: json.dumps(model))
    _, result = call_tool(server, VALIDATE, guids=guids, engine="native", load_kn=10, self_weight=False,
                          stability="off", structure_type=structure_type, detail=True)
    member = result["members"][0]
    assert member[force] == pytest.approx(expected, abs=0.001)
    assert member["n_tension_kn"] == 0
    assert member["section"] and member["governing_check"] and member["governing_combination"]


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


def test_display_only_uses_existing_overlay(tmp_path, call_tool):
    def bridge(raw, **_options):
        assert json.loads(raw)["type"] == "structure_draw"
        return json.dumps({"status": "error", "message": "Nothing to display yet: send a result first."})

    server = analysis_server(tmp_path / "project.sqlite3", bridge)
    _, result = call_tool(server, VISUALIZE, guids=[BEAM_ID], reanalyze=False)
    assert result["status"] == "error" and "Nothing to display" in result["message"]
