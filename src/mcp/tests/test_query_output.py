"""Public defaults hide identities, explicit requests keep useful nested refs."""
import asyncio
import json
from fastmcp import Client, FastMCP
from almond_mcp.feature_context import FeatureContext
from almond_mcp.features.planning.tools import register
from almond_mcp.features.scenes.tools import register as register_scenes
from almond_mcp.retrieval_store import AlmondStore
from almond_mcp.query_output import query_output


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
            assert "steps" not in plain and "created_at" not in plain
            detailed = (await call("get_plan", plan_id=plan["plan_id"], field_groups=["steps", "references"]))["plan"]
            assert detailed["depends_on_count"] == 2 and detailed["steps"][0]["name"]
            assert all("component_ids" not in step and "step_id" not in step for step in detailed["steps"])
            explicit = (await call("get_plan", plan_id=plan["plan_id"], include_ids=True,
                                   field_groups=["steps", "references"]))["plan"]
            assert "plan_id" not in explicit
            assert explicit["depends_on"] == ["other-phase", "other-plan"]
            assert explicit["scene_ids"] == [scene["scene_id"]]
            assert explicit["steps"][0]["component_ids"] is None
            phases = await call("list_phases", include_ids=True)
            assert phases["phases"][0]["phase_id"] == phase["phase_id"]
            assert "file_name" not in phases["phases"][0]
            assert (await call("list_phases", field_groups=["scope"]))["phases"][0]["file_name"] == ""
            assert (await call("get_design_scene", scene_id=scene["scene_id"], field_groups=["scope"]))["scene"]["file_name"] == ""
            rejected = await client.call_tool("get_plan", {"plan_id": plan["plan_id"], "include_ids": "true"}, raise_on_error=False)
            assert rejected.is_error
    asyncio.run(verify())


def test_same_plan_page_keeps_names_and_counts_while_reducing_bytes(tmp_path):
    """Given many saved Tasks, a first summary read avoids full-reference payloads."""
    store = AlmondStore(tmp_path / "DB")
    for number in range(8):
        plan = store.create_plan(f"Synthetic task {number}")
        store.update_plan(plan["plan_id"], artifact_refs=[f"drawing-{index}.svg" for index in range(20)])
    tools = register(FastMCP("query-cost"), FeatureContext({"retrieval_store": store}))
    summary = tools["list_plans"](limit=5, include_ids=True)
    full = tools["list_plans"](limit=5, include_ids=True, field_groups=["all"])
    small, large = json.loads(summary), json.loads(full)
    assert small["total"] == large["total"] == 8 and len(small["plans"]) == len(large["plans"]) == 5
    assert [item["plan_id"] for item in small["plans"]] == [item["plan_id"] for item in large["plans"]]
    assert [item["goal"] for item in small["plans"]] == [item["goal"] for item in large["plans"]]
    summary_bytes, full_bytes = len(summary.encode("utf-8")), len(full.encode("utf-8"))
    assert summary_bytes < full_bytes / 2
    print(f"Synthetic 5-of-8 Plan page: summary={summary_bytes} bytes; all={full_bytes} bytes; rows=5/5")


def test_agent_outline_summary_hides_guid_paths_while_file_paths_remain_usable():
    """Given a native outline, ID display controls ancestor GUIDs as well as leaf handles."""
    @query_output
    def outline(include_ids: bool = False) -> dict:
        return {"objects": [{"name": "Facade", "path": ["00000000-0000-0000-0000-000000000001"]}],
                "source": {"path": "drawings/facade.svg"}}
    summary = outline()
    assert summary["objects"] == [{"name": "Facade", "path_count": 1}]
    assert summary["source"]["path"] == "drawings/facade.svg"
    assert outline(include_ids=True)["objects"][0]["path"] == ["00000000-0000-0000-0000-000000000001"]
