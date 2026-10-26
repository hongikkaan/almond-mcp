"""Public defaults hide identities, explicit requests keep useful nested refs."""
import asyncio
import json
from fastmcp import Client, FastMCP
from almond_mcp.feature_context import FeatureContext
from almond_mcp.features.planning.tools import register
from almond_mcp.features.scenes.tools import register as register_scenes
from almond_mcp.retrieval_store import AlmondStore


def test_query_defaults_ids_echo_omission_and_empty_file_names(tmp_path):
    store = AlmondStore(tmp_path / "DB")
    phase = store.create_phase("Phase")
    scene = store.create_scene("Scene")
    plan = store.create_plan("Task", phase_id=phase["phase_id"], scene_ids=[scene["scene_id"]],
                             depends_on=["other-phase", "other-plan"])
    mcp = FastMCP("public-query-contract")
    context = FeatureContext({"retrieval_store": store})
    register(mcp, context)
    register_scenes(mcp, context)

    async def verify():
        async with Client(mcp) as client:
            async def call(name, **args):
                response = await client.call_tool(name, args)
                return json.loads(response.content[0].text)
            plain = (await call("get_plan", plan_id=plan["plan_id"]))["plan"]
            assert "plan_id" not in plain and "component_ids" not in plain and "phase_id" not in plain
            assert "scene_ids" not in plain and "depends_on" not in plain
            assert plain["depends_on_count"] == 2 and plain["steps"][0]["name"]
            assert all("component_ids" not in step and "step_id" not in step for step in plain["steps"])
            explicit = (await call("get_plan", plan_id=plan["plan_id"], include_ids=True))["plan"]
            assert "plan_id" not in explicit
            assert explicit["depends_on"] == ["other-phase", "other-plan"]
            assert explicit["scene_ids"] == [scene["scene_id"]]
            assert explicit["steps"][0]["component_ids"] is None
            phases = await call("list_phases", include_ids=True)
            assert phases["phases"][0]["phase_id"] == phase["phase_id"]
            assert phases["phases"][0]["file_name"] == ""
            assert (await call("get_design_scene", scene_id=scene["scene_id"]))["scene"]["file_name"] == ""
            rejected = await client.call_tool("get_plan", {"plan_id": plan["plan_id"], "include_ids": "true"}, raise_on_error=False)
            assert rejected.is_error
    asyncio.run(verify())
