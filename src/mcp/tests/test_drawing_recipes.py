"""Drawing recipe workflows through the public MCP tools."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from fastmcp import Client, FastMCP

from almond_mcp.features.drawings.library import DrawingRecipeIndexer
from almond_mcp.paths import resolve_dir
from almond_mcp.features.drawings.tools import register


A4_ID = "architectural_plan_section_a4_v1"
RECIPE_DIR = Path(__file__).resolve().parents[3] / "asset" / "drawing" / "DrawingRecipes"


def recipe_service(recipe_dir, send=None):
    server = FastMCP("drawing-recipes")
    register(server, SimpleNamespace(
        drawing_recipe_indexer=DrawingRecipeIndexer(recipe_dir),
        _send_and_receive=send,
    ))
    return server


async def call(client, name, **arguments):
    response = await client.call_tool(name, arguments)
    return json.loads(response.content[0].text)


def test_recipe_list_exposes_requested_a4_parameters_and_keeps_default_summary():
    async def run():
        async with Client(recipe_service(RECIPE_DIR)) as client:
            summary = await call(client, "drawing_05-list_recipes")
            a4 = next(row for row in summary["recipes"] if row["name"] == "Architectural Plan and Section A4")
            assert a4["projection"] == "parallel"
            assert {"recipe_id", "layers", "output", "recommended_scales"}.isdisjoint(a4)

            selected = await call(
                client, "drawing_05-list_recipes", include_ids=True,
                field_groups=["scales", "parameters", "source"],
            )
            a4 = next(row for row in selected["recipes"] if row["recipe_id"] == A4_ID)
            assert a4["projection"] == "parallel"
            assert a4["recommended_scales"] == ["1:50", "1:100", "1:200"]
            assert a4["output"]["paper"] == "A4"
            assert a4["source"]["type"] == "live_drawing_review"
    asyncio.run(run())


def test_a4_recipe_details_supply_the_style_applied_on_both_calls():
    requests = []

    def native_reply(payload, *, timeout):
        requests.append(json.loads(payload))
        return json.dumps({"status": "success", "recipe_id": A4_ID, "layers": []})

    async def run():
        async with Client(recipe_service(RECIPE_DIR, native_reply)) as client:
            listed = await call(client, "drawing_05-list_recipes", include_ids=True)
            recipe_id = next(row["recipe_id"] for row in listed["recipes"]
                             if row["name"] == "Architectural Plan and Section A4")
            assert recipe_id == A4_ID
            detail = await call(
                client, "drawing_02-get_recipe", recipe_id=recipe_id,
                field_groups=["scales", "parameters"],
            )
            recipe = detail["recipe"]
            assert recipe["output"]["orientation"] == "landscape"
            section_cut = next(layer for layer in recipe["layers"] if layer["role"] == "section_cut")
            assert section_cut["path"] == "ALMOND-DRAW::SECTION-CUT"
            assert section_cut["plot_weight_mm"] == 0.35

            for _ in range(2):
                outcome = await call(client, "drawing_01-apply_style", recipe_id=recipe_id)
                assert outcome["status"] == "success"
                assert outcome["review_preparation"]["status"] == "not_executed"
            assert len(requests) == 2
            for request in requests:
                assert request["type"] == "apply_drawing_style"
                assert request["recipe_id"] == recipe_id
                assert request["layers"] == recipe["layers"]
                manifest = Path(request["linetype_manifest_path"])
                assert manifest == Path(__file__).resolve().parents[1] / "profiles" / "linetype" / "manifest.json"
                assert json.loads(manifest.read_text(encoding="utf-8"))["ALMOND A4 Hidden"] == [
                    {"length": 3, "is_solid": True},
                    {"length": 1.5, "is_solid": False},
                ]
    asyncio.run(run())


def test_recipe_layer_only_supplies_the_linetype_name(tmp_path):
    recipe = {
        "recipe_id": "project_style",
        "name": "Project style",
        "layers": [{
            "path": "Drawing::Hidden",
            "linetype": "Project Hidden",
            "linetype_segments": [{"length": 999, "is_solid": True}],
        }],
    }
    (tmp_path / "style.json").write_text(json.dumps(recipe), encoding="utf-8")
    requests = []

    def native_reply(payload, *, timeout):
        requests.append(json.loads(payload))
        return json.dumps({"status": "success", "layers": []})

    async def run():
        async with Client(recipe_service(tmp_path, native_reply)) as client:
            detail = await call(
                client, "drawing_02-get_recipe", recipe_id="project_style",
                field_groups=["parameters"],
            )
            result = await call(client, "drawing_01-apply_style", recipe_id="project_style")
            assert result["status"] == "success"
            layers = [{"path": "Drawing::Hidden", "linetype": "Project Hidden"}]
            assert detail["recipe"]["layers"] == layers
            assert requests[0]["layers"] == layers
    asyncio.run(run())


def test_recipe_guidance_names_the_arguments_to_continue_from_each_result():
    async def run():
        async with Client(recipe_service(RECIPE_DIR)) as client:
            summary = await call(client, "drawing_05-list_recipes")
            assert all(part in summary["next_step_guide"] for part in (
                "drawing_05-list_recipes tool", "include_ids=true",
            ))
            listed = await call(client, "drawing_05-list_recipes", include_ids=True)
            assert all(part in listed["next_step_guide"] for part in (
                "drawing_02-get_recipe tool", "recipe_id", "scales", "parameters",
            ))
            detail = await call(client, "drawing_02-get_recipe", recipe_id=A4_ID)
            assert all(part in detail["next_step_guide"] for part in (
                "drawing_01-apply_style tool", "recipe_id",
            ))
    asyncio.run(run())


def test_recipe_directory_override_is_indexed_when_the_service_starts(tmp_path, monkeypatch):
    recipe_key = "RHINO_MCP_DRAWING_RECIPE_DIR"
    monkeypatch.delenv(recipe_key, raising=False)
    assert Path(resolve_dir(recipe_key)) == RECIPE_DIR

    monkeypatch.setenv(recipe_key, str(tmp_path))
    file = tmp_path / "custom.json"
    recipe = {"recipe_id": "custom_plan", "name": "Custom Plan", "projection": {"type": "parallel"}}
    file.write_text(json.dumps(recipe), encoding="utf-8")
    running_service = recipe_service(resolve_dir(recipe_key))
    recipe["name"] = "Updated Custom Plan"
    file.write_text(json.dumps(recipe), encoding="utf-8")

    async def run():
        async with Client(running_service) as client:
            listed = await call(client, "drawing_05-list_recipes", include_ids=True)
            assert [(row["recipe_id"], row["name"]) for row in listed["recipes"]] == [
                ("custom_plan", "Custom Plan")]
        async with Client(recipe_service(resolve_dir(recipe_key))) as client:
            listed = await call(client, "drawing_05-list_recipes", include_ids=True)
            assert [(row["recipe_id"], row["name"]) for row in listed["recipes"]] == [
                ("custom_plan", "Updated Custom Plan")]
    asyncio.run(run())
