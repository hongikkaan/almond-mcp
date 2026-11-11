"""Small independent checks for guidance and response/path safety."""
import pytest
from almond_mcp import modeling_guidance
from almond_mcp.instruction_text import read_tool_instruction, tool_instruction
from almond_mcp.managed_paths import project_path
from almond_mcp.query_output import select_fields, validate_field_groups


def test_policy_selection_returns_only_requested_content():
    basic = modeling_guidance.read_policy()
    assert "context_01-get_policy" in basic["tools"]
    assert not {"get_modeling_guide", "get_looping_policy", "get_modeling_policy", "get_retrieval_status"}.intersection(basic["tools"])
    assert basic["text"] == modeling_guidance.BASIC_GUIDE.read_text(encoding="utf-8").strip()
    assert set(basic["available_policies"]) == {"basic", "metadata", "rhino_scripting", "rhinocode"}
    assert modeling_guidance.read_policy("basic") == basic
    scripting = modeling_guidance.read_policy("rhino_scripting")
    assert scripting["guide_version"] == basic["guide_version"]
    assert "text" not in scripting and "policy" not in scripting
    assert scripting["scripting_skill"]["name"] == "rhino3d-scripts"
    assert all(source["text"] and source["sha256"] for source in scripting["scripting_skill"]["sources"])
    metadata = modeling_guidance.read_policy("metadata")
    assert "public_object_keys" in metadata["policy"]
    metadata["policy"].clear()
    assert modeling_guidance.read_policy("metadata")["policy"]
    assert "script_02-run_rhino" in modeling_guidance.read_policy("rhinocode")["text"]
    with pytest.raises(ValueError, match="policy must"):
        modeling_guidance.read_policy("inspect_03-get_document_context")
    with pytest.raises(ValueError):
        modeling_guidance.read_policy(True)


def test_tool_description_loader_preserves_full_prose_and_schema_metadata(tmp_path):
    source = tmp_path / "tools.py"
    explanation = ("First sentence. A second sentence must remain.\n\n"
                   "When to use: Inspect a bounded target.\n"
                   "Limits: Observation is not verification.\n\n"
                   "Args:\n    target: Target from an earlier result.\n\n"
                   "Returns:\n    The complete result.")
    source.with_name("tools-explain.md").write_text(
        "<!-- instruction:example -->\n" + explanation + "\n<!-- /instruction:example -->\n",
        encoding="utf-8")
    assert read_tool_instruction(str(source), "example") == explanation

    @tool_instruction(str(source), "example")
    def example(target: str):
        pass

    assert example.__doc__ == explanation


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
