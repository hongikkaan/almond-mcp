"""Small independent checks for guidance and response/path safety."""
import ast
import pytest
from almond_mcp import modeling_guidance
from almond_mcp.tool_declarations import checked_stub
from almond_mcp.managed_paths import project_path
from almond_mcp.query_output import select_fields, validate_field_groups
from almond_mcp.output_contracts import public_output_schema
from schema_assertions import assert_described_payload


def test_policy_selection_returns_only_requested_content():
    basic = modeling_guidance.read_policy()
    schema = public_output_schema("get_policy", wrapped=False)
    for name in ("", *basic["available_policies"]):
        assert_described_payload(modeling_guidance.read_policy(name), schema)
    assert "context_01-get_policy" in basic["tools"]
    assert not {"get_modeling_guide", "get_looping_policy", "get_modeling_policy", "get_retrieval_status"}.intersection(basic["tools"])
    assert basic["text"] == modeling_guidance.BASIC_SUMMARY
    assert set(basic["available_policies"]) == {"basic", "metadata", "rhino_scripting", "rhinocode"}
    assert modeling_guidance.read_policy("basic") == basic
    for retired in ("spatial_modeling", "observation", "drawing", "feedback_reporting"):
        with pytest.raises(ValueError):
            modeling_guidance.read_policy(retired)
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


def test_bundled_policy_content_changes_guide_version(monkeypatch):
    policy = "rhinocode"
    original = modeling_guidance.read_policy(policy)
    path = modeling_guidance.RHINOCODE_POLICY
    read_content = modeling_guidance._read_content

    def changed_content(source):
        content = read_content(source)
        return content + b"\n\nObservation test.\n" if source == path else content

    with monkeypatch.context() as patch:
        patch.setattr(modeling_guidance, "_read_content", changed_content)
        modeling_guidance._snapshot.cache_clear()
        try:
            updated = modeling_guidance.read_policy(policy)
        finally:
            modeling_guidance._snapshot.cache_clear()
    assert updated["text"].endswith("Observation test.")
    assert updated["source_refs"][0]["sha256"] != original["source_refs"][0]["sha256"]
    assert updated["guide_version"] != original["guide_version"]


def test_inert_catalog_uses_full_docstring_from_the_registration():
    declaration = ast.parse('''@public_tool(mcp, wrapped=True)
def get_objects(target: str):
    """First sentence. A second sentence must remain.

    Args:
        target: Target from an earlier result.

    Returns:
        The complete result.
    """
    raise RuntimeError("Only the handler should execute this.")
''').body[0]
    stub = checked_stub(declaration)
    assert ast.get_docstring(stub) == ast.get_docstring(declaration)
    assert "Only the handler" not in ast.unparse(stub)


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
