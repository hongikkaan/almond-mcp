"""The external adapter must reject stale worker schemas and source snapshots."""
import ast
import copy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src/cos"))
from runtime import check_contract, schema_identity, validate_worker_tools
from build_catalog import checked_stub


def test_reviewed_package_projection_option_is_inert_and_narrow():
    source = '''
@mcp.tool()
@query_output(preserve_cross_drive_fields={"package_dir"})
def get_asset_drawing(asset_id: str) -> dict:
    raise RuntimeError("Bodies are inert")
'''
    checked = checked_stub(ast.parse(source).body[0])
    assert len(checked.decorator_list) == 1
    for changed in (
        source.replace('{"package_dir"}', 'get_fields()'),
        source.replace('{"package_dir"}', '{"model_path"}'),
        source.replace('preserve_cross_drive_fields=', 'unknown='),
        source.replace('get_asset_drawing(', 'unreviewed_tool('),
    ):
        with pytest.raises(ValueError):
            checked_stub(ast.parse(changed).body[0])


def test_literal_public_tool_alias_survives_inert_catalog_generation():
    source = '@mcp.tool(name="get_phase_plan_step", title="get_phase·plan·step")\ndef get_details(plan_id: str = "") -> str:\n    raise RuntimeError("original body")'
    node = checked_stub(ast.parse(source).body[0])
    assert ast.literal_eval(node.decorator_list[0].keywords[0].value) == "get_phase_plan_step"
    assert ast.literal_eval(node.decorator_list[0].keywords[1].value) == "get_phase·plan·step"
    assert "original body" not in ast.unparse(node)
    with pytest.raises(ValueError):
        checked_stub(ast.parse(source.replace('"get_phase_plan_step"', 'get_name()')).body[0])
    with pytest.raises(ValueError):
        checked_stub(ast.parse(source.replace('"get_phase·plan·step"', 'get_title()')).body[0])


def test_list_patch_annotation_is_reviewed_without_importing_the_server():
    node = checked_stub(ast.parse('''
@mcp.tool()
def update_step(output_refs: StringListPatch | None = None) -> str:
    return "not executed"
''').body[0])
    assert "StringListPatch" in ast.unparse(node.args.args[0].annotation)
    with pytest.raises(ValueError, match="annotation name"):
        checked_stub(ast.parse(ast.unparse(node).replace("StringListPatch", "UnreviewedType")).body[0])


def test_worker_schema_and_name_mismatch_are_rejected():
    tool = {"name": "sample", "inputSchema": {"type": "object", "properties": {"x": {"type": "string"}}},
            "outputSchema": {"type": "object"}, "annotations": {"readOnlyHint": True}}
    catalog = {"tools": [tool]}
    validate_worker_tools(catalog, [copy.deepcopy(tool)])
    for field in ("name", "inputSchema", "outputSchema", "annotations"):
        altered = copy.deepcopy(tool)
        altered[field] = "other" if field == "name" else {}
        with pytest.raises(RuntimeError, match="schemas changed"):
            validate_worker_tools(catalog, [altered])
    assert schema_identity({**tool, "description": "new wording"}) == schema_identity(tool)


def test_stale_fingerprint_and_package_version_are_rejected(monkeypatch, tmp_path):
    import runtime
    source = tmp_path / "source.py"
    source.write_text("one", encoding="utf-8")
    monkeypatch.setattr(runtime, "source_paths", lambda engine: {"source": source})
    monkeypatch.setattr(runtime, "version", lambda package: "1")
    catalog = {"packages": {"sdk": "1"}, "sources": {"source": runtime.digest(source)}}
    check_contract(catalog)
    source.write_text("two", encoding="utf-8")
    with pytest.raises(RuntimeError, match="changed"):
        check_contract(catalog)
    catalog["sources"]["source"] = runtime.digest(source)
    catalog["packages"]["sdk"] = "2"
    with pytest.raises(RuntimeError, match="expects"):
        check_contract(catalog)


@pytest.mark.parametrize("name", ["get_rhino_context", "get_objects", "get_object_intersections"])
def test_fixed_observations_keep_the_reviewed_wrapped_string_schema(name):
    source = '''
@mcp.tool(output_schema={"type": "object", "properties": {"result": {"type": "string"}},
                        "required": ["result"], "x-fastmcp-wrap-result": True})
def TOOL() -> str | ToolResult:
    return "not executed"
'''.replace("TOOL", name)
    node = checked_stub(ast.parse(source).body[0])
    assert isinstance(node.body[-1], ast.Raise)
    for changed in (source.replace(name, "unreviewed_tool"), source.replace('"type": "string"', '"type": "integer"')):
        with pytest.raises(ValueError, match="output schema"):
            checked_stub(ast.parse(changed).body[0])
