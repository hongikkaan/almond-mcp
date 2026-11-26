"""Check the catalogs and startup guide a remote client actually receives."""
import asyncio
from copy import deepcopy
from hashlib import sha256
import json

from jsonschema import Draft202012Validator

from render_tool_declarations import (
    CATALOG_SNAPSHOT, ROOT, SCHEMA_BASELINE, open_stdio, render_catalogs, schema_baseline, stdio_parameters,
)


def test_contract_source_hash():
    source = (ROOT / "TOOL-DECLARATIONS-CURRENT.md").read_text(encoding="utf-8")
    data = json.loads((ROOT / "src/mcp/public_contract_data.json").read_text(encoding="utf-8"))
    recorded_hash = data.get("source_sha256")
    assert recorded_hash == sha256(source.encode("utf-8")).hexdigest(), (
        "Run node tests/integration/compile_tool_contracts.cjs to update the packaged declarations."
    )


CONNECT_TOOLS = {
    "connect_01-list_up", "connect_02-session", "connect_03-start_session",
    "connect_04-disconnect", "connect_05-close_session",
}
UNROUTED_TOOLS = {"context_01-get_policy", "connect_01-list_up", "connect_02-session", "connect_03-start_session"}
POLICY_TOOL = "context_01-get_policy"
CONNECTION_ID = "a" * 32
MODE_FIELDS = {
    "capture_01-conditioning_pass": ("rgb_mode", "edge_mode"),
    "capture_02-inspection": ("display_mode",),
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

    # Hosts can supply examples for the same display mode inputs.
    for field in MODE_FIELDS.get(name, ()):
        for schema in (expected, actual):
            properties = schema["properties"]
            if name == "capture_02-inspection":
                properties = properties["views"]["items"]["properties"]
            properties[field].pop("examples", None)
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
            listed = await client.call_tool("connect_01-list_up", {})
            assert not listed.is_error, listed.content
            assert listed.structured_content == {"targets": []}
            missing = await client.call_tool("context_04-get_project_info", {})
            assert missing.is_error
            assert "connection_id" in missing.content[0].text
        else:
            rejected = await client.call_tool("plan_02-create", {"request": {
                "target": "plan", "title": "Review", "goal": "Review the entrance", "scene_id": "obsolete",
            }})
            assert rejected.is_error
            serialized = rejected.structured_content["result"]
            error = json.loads(serialized)
            assert rejected.content[0].text == serialized
            assert error["status"] == "error" and error["error_code"] == "invalid_arguments"
            missing_rules = await client.call_tool("analysis_05-check_egress", {
                "plate_bounds_mm": [0, 0, 10000, 10000], "exits": [{"x_mm": 0, "y_mm": 0, "width_mm": 900}],
            })
            assert missing_rules.is_error
            assert json.loads(missing_rules.structured_content["result"]) == {
                "message": "egress_rules missing from the construction manifest.",
            }
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
        if routed:
            connection = Draft202012Validator(inputs["properties"]["connection_id"])
            assert connection.is_valid(CONNECTION_ID)
            assert not connection.is_valid(CONNECTION_ID.upper())
            assert not connection.is_valid(CONNECTION_ID[1:])
        if name in terminal:
            assert tool["description"] == terminal[name]["description"], name
            assert tool["outputSchema"] == terminal[name]["outputSchema"], name
            assert tool.get("annotations") == terminal[name].get("annotations"), name
            compare_inputs(name, terminal[name]["inputSchema"], inputs)

    for tool in (*terminal.values(), *beyond.values()):
        Draft202012Validator.check_schema(tool["inputSchema"])
        output = tool["outputSchema"]
        Draft202012Validator.check_schema(output)
        result = output.get("properties", {}).get("result", {})
        if "contentSchema" in result:
            Draft202012Validator.check_schema(result["contentSchema"])

    baseline = json.loads(SCHEMA_BASELINE.read_text(encoding="utf-8"))
    assert schema_baseline(terminal) == baseline
    published = CATALOG_SNAPSHOT.read_text(encoding="utf-8")
    assert published == render_catalogs(beyond, terminal)
