"""Check the catalogs and startup guide a remote client actually receives."""
import asyncio
from copy import deepcopy
import json

from jsonschema import Draft202012Validator

from render_tool_declarations import ROOT, open_stdio, render_catalogs, stdio_parameters


CONNECT_TOOLS = {
    "connect_01-list_up", "connect_02-session", "connect_03-start_session",
    "connect_04-disconnect", "connect_05-close_session",
}
UNROUTED_TOOLS = {"context_01-get_policy", "connect_01-list_up", "connect_02-session", "connect_03-start_session"}
POLICY_TOOL = "context_01-get_policy"
MODE_FIELDS = {
    "capture_01-conditioning_pass": ("rgb_mode", "edge_mode"),
    "capture_03-current_view": ("display_mode",),
    "capture_04-defined_view": ("display_mode",),
}


def compare_inputs(name, terminal, beyond):
    expected, actual = deepcopy(terminal), deepcopy(beyond)
    if name not in UNROUTED_TOOLS:
        del actual["properties"]["connection_id"]
        actual["required"].remove("connection_id")
        if not actual["required"] and "required" not in expected:
            del actual["required"]

    # An unconnected beyond client has no display-mode menu to advertise.
    for field in MODE_FIELDS.get(name, ()):
        del expected["properties"][field]
    if name == "capture_02-inspection":
        expected["properties"]["views"]["items"].update({
            "additionalProperties": False,
            "properties": {
                "direction": {"type": "string"}, "label": {"type": "string"},
                "frame_objects": {"type": "boolean"}, "object_ids": {"type": "array", "items": {"type": "string"}},
            },
        })
    assert actual == expected, name


async def inspect_route(route, directory):
    async with open_stdio(stdio_parameters(route, directory)) as (client, initialized):
        tools = {tool.name: tool.model_dump(mode="json", by_alias=True, exclude_none=True)
                 for tool in (await client.list_tools()).tools}
        guide = await client.call_tool(POLICY_TOOL, {})
        assert not guide.is_error, guide.content
        policy = guide.structured_content
        Draft202012Validator(tools[POLICY_TOOL]["outputSchema"]).validate(policy)
        assert policy["selected_policy"] == "basic"
        assert POLICY_TOOL in initialized.instructions and "tools/list" in initialized.instructions
        assert f"guide_version={policy['guide_version']}" in initialized.instructions
        assert set(policy["available_policies"]) == {"basic", "metadata", "rhino_scripting", "rhinocode"}
        assert set(policy["tools"]) == set(tools) - CONNECT_TOOLS
        if route == "beyond":
            assert initialized.server_info.name == "beyond"
            missing = await client.call_tool("context_04-get_project_info", {})
            assert missing.is_error
            assert "connection_id" in missing.content[0].text
        return tools, initialized.instructions


def test_public_catalogs_and_guide(tmp_path):
    terminal, terminal_guide = asyncio.run(inspect_route("terminal", tmp_path / "terminal"))
    beyond, beyond_guide = asyncio.run(inspect_route("beyond", tmp_path / "beyond"))

    assert terminal_guide in beyond_guide
    assert set(beyond) - set(terminal) == CONNECT_TOOLS
    assert set(terminal) <= set(beyond)
    for name, tool in beyond.items():
        routed = name not in UNROUTED_TOOLS
        inputs = tool["inputSchema"]
        assert ("connection_id" in inputs["properties"]) == routed, name
        assert ("connection_id" in inputs.get("required", [])) == routed, name
        if name in terminal:
            assert tool["description"] == terminal[name]["description"], name
            assert tool["outputSchema"] == terminal[name]["outputSchema"], name
            compare_inputs(name, terminal[name]["inputSchema"], inputs)

    baseline = json.loads((ROOT / "tests/integration/tool_schemas.json").read_text(encoding="utf-8"))
    fields = ("name", "inputSchema", "outputSchema", "annotations")
    assert {name: {key: tool.get(key) for key in fields} for name, tool in terminal.items()} == baseline
    for tool in (*terminal.values(), *beyond.values()):
        Draft202012Validator.check_schema(tool["inputSchema"])
        Draft202012Validator.check_schema(tool["outputSchema"])

    published = (ROOT / "TOOL-DECLARATIONS-CURRENT.md").read_text(encoding="utf-8")
    assert published == render_catalogs(beyond, terminal)
