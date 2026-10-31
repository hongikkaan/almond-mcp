"""Small independent checks for guidance and response/path safety."""
import pytest
from almond_mcp import modeling_guidance
from almond_mcp.managed_paths import project_path
from almond_mcp.query_output import select_fields, validate_field_groups


def test_full_guide_rejects_unknown_tool_and_preserves_original_explanation():
    basic = modeling_guidance.read_guide()
    assert "get_rhino_context" in basic["tools"]
    full = modeling_guidance.read_guide("get_rhino_context")
    assert full["guide_version"] == basic["guide_version"]
    assert full["source_refs"] and len(full["text"].splitlines()) > 1
    with pytest.raises(ValueError, match="Unknown Almond tool"):
        modeling_guidance.read_guide("does_not_exist")


def test_projection_keeps_uncertainty_and_does_not_mutate_source():
    record = {"name": "example", "hidden": "detail", "complete": False, "warnings": ["unverified"]}
    assert select_fields(record, [], {"name"}, {}) == record
    assert record["hidden"] == "detail"
    validate_field_groups(["supported"], {"supported": {"hidden"}})
    with pytest.raises(ValueError, match="Unknown field_groups"):
        validate_field_groups(["unexpected"], {"supported": {"hidden"}})


def test_managed_path_stays_inside_project(tmp_path):
    assert project_path("tmp/report.json", base=tmp_path) == (tmp_path / "tmp/report.json").resolve()
    with pytest.raises(ValueError):
        project_path("../outside", base=tmp_path)
    with pytest.raises(ValueError):
        project_path(str(tmp_path / "absolute"), base=tmp_path)
