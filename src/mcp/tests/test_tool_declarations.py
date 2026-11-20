"""Reviewed declaration syntax cannot execute handlers or metadata expressions."""
import ast
from typing import get_args

import pytest

from almond_mcp.modeling_guidance import PolicyName
from almond_mcp.tool_declarations import checked_stub


def test_reviewed_package_projection_option_is_inert_and_narrow():
    source = '''
@public_tool(mcp, wrapped=False)
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


def test_inert_registration_uses_public_name_and_rejects_executable_metadata():
    source = '''
@public_tool(mcp, wrapped=True, annotations={"readOnlyHint": True})
def get_objects(file_name: str = "") -> str:
    raise RuntimeError("original body")
'''
    node = checked_stub(ast.parse(source).body[0])
    options = {kw.arg: ast.literal_eval(kw.value) for kw in node.decorator_list[0].keywords}
    assert options["name"] == "inspect_02-get_objects"
    assert options["annotations"] == {"readOnlyHint": True}
    assert "original body" not in ast.unparse(node)
    for changed in (
        source.replace("wrapped=True", "wrapped=get_flag()"),
        source.replace('"readOnlyHint": True', '"readOnlyHint": get_flag()'),
        source.replace("public_tool(mcp", "public_tool(unreviewed"),
        source.replace("def get_objects", "@public_tool(mcp, wrapped=False)\ndef get_objects"),
    ):
        with pytest.raises(ValueError):
            checked_stub(ast.parse(changed).body[0])


def test_list_annotation_is_reviewed_without_importing_the_server():
    source = '''
@public_tool(mcp, wrapped=True)
def get_objects(paths: list[str] | None = None) -> str:
    return "not executed"
'''
    node = checked_stub(ast.parse(source).body[0])
    assert "list[str]" in ast.unparse(node.args.args[0].annotation)
    with pytest.raises(ValueError, match="annotation name"):
        checked_stub(ast.parse(source.replace("list[str]", "UnreviewedType")).body[0])


def test_policy_name_annotation_is_reviewed_only_for_the_get_policy_argument():
    source = '''
@public_tool(mcp, wrapped=False)
def get_policy(policy: PolicyName = "") -> ToolResult:
    raise RuntimeError("original body")
'''
    node = checked_stub(ast.parse(source).body[0])
    annotation = node.args.args[0].annotation
    assert ast.unparse(annotation.value) == "Literal"
    assert ast.literal_eval(annotation.slice) == get_args(PolicyName)
    for changed in (
        source.replace("get_policy(", "get_objects("),
        source.replace("policy: PolicyName", "other: PolicyName"),
        source.replace("PolicyName", "list[PolicyName]"),
        source.replace("-> ToolResult", "-> PolicyName"),
    ):
        with pytest.raises(ValueError, match="annotation name"):
            checked_stub(ast.parse(changed).body[0])


@pytest.mark.parametrize("parameters", ["*args: unreviewed()", "**kwargs: unreviewed()"])
def test_inert_declaration_rejects_variadic_annotation_calls(parameters):
    source = f"@public_tool(mcp, wrapped=True)\ndef get_objects({parameters}) -> str:\n    return 'not executed'"
    with pytest.raises(ValueError, match="annotation"):
        checked_stub(ast.parse(source).body[0])


@pytest.mark.parametrize("name", ["get_rhino_context", "get_objects", "get_object_intersections"])
def test_fixed_observations_use_the_public_wrapped_schema(name):
    source = f'''
@public_tool(mcp, wrapped=True)
def {name}() -> str | ToolResult:
    return "not executed"
'''
    node = checked_stub(ast.parse(source).body[0])
    assert isinstance(node.body[-1], ast.Raise)
    options = {kw.arg: ast.literal_eval(kw.value) for kw in node.decorator_list[0].keywords}
    assert options["output_schema"]["x-fastmcp-wrap-result"] is True
    assert "contentSchema" in options["output_schema"]["properties"]["result"]
