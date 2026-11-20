"""Drawing recipe workflows through the public MCP tools."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from fastmcp import Client, FastMCP
import pytest

from almond_mcp.features.drawings.library import DrawingRecipeIndexer
from almond_mcp.paths import resolve_dir, user_data_dir
from almond_mcp.runtime.library_paths import bound_library_dirs
from almond_mcp.features.drawings.tools import register


RECIPE_DIR = Path(__file__).resolve().parents[3] / "asset" / "drawing" / "DrawingRecipes"


@pytest.fixture
def bundled_print_recipe():
    recipes = (json.loads(path.read_text(encoding="utf-8")) for path in RECIPE_DIR.glob("*.json"))
    return next(recipe for recipe in recipes if recipe.get("review_preparation", {}).get("print_display") is True)


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


def test_recipe_list_exposes_requested_parameters_and_keeps_default_summary(bundled_print_recipe):
    recipe = bundled_print_recipe

    async def run():
        async with Client(recipe_service(RECIPE_DIR)) as client:
            summary = await call(client, "drawing_05-list_recipes")
            listed = next(row for row in summary["recipes"] if row["name"] == recipe["name"])
            assert listed["projection"] == recipe["projection"]["type"]
            assert {"recipe_id", "layers", "output", "recommended_scales"}.isdisjoint(listed)

            selected = await call(
                client, "drawing_05-list_recipes", include_ids=True,
                field_groups=["scales", "parameters", "source"],
            )
            listed = next(row for row in selected["recipes"] if row["recipe_id"] == recipe["recipe_id"])
            assert listed["projection"] == recipe["projection"]["type"]
            for field in ("recommended_scales", "output", "source"):
                assert listed[field] == recipe[field]
    asyncio.run(run())


def test_recipe_details_supply_the_style_applied_on_both_calls(bundled_print_recipe):
    requests = []
    recipe_id = bundled_print_recipe["recipe_id"]

    def native_reply(payload, *, timeout):
        requests.append(json.loads(payload))
        return json.dumps({"status": "success", "recipe_id": recipe_id, "layers": []})

    async def run():
        async with Client(recipe_service(RECIPE_DIR, native_reply)) as client:
            listed = await call(client, "drawing_05-list_recipes", include_ids=True)
            assert recipe_id in {row["recipe_id"] for row in listed["recipes"]}
            detail = await call(
                client, "drawing_02-get_recipe", recipe_id=recipe_id,
                field_groups=["scales", "parameters"],
            )
            recipe = detail["recipe"]
            assert recipe["output"] == bundled_print_recipe["output"]
            assert recipe["layers"] == bundled_print_recipe["layers"]

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


@pytest.mark.parametrize(("preparation", "native_status", "expect_guide"), [
    ({"print_display": True}, "success", True),
    ({"print_display": False}, "success", False),
    ({"print_display": "true"}, "success", False),
    (None, "success", False),
    ({"print_display": True}, "error", False),
])
def test_print_display_guide_follows_recipe_settings(tmp_path, preparation, native_status, expect_guide):
    recipe = {"recipe_id": "project_plan", "layers": [{"path": "Drawing::Plan"}]}
    if preparation is not None:
        recipe["review_preparation"] = preparation
    (tmp_path / "plan.json").write_text(json.dumps(recipe), encoding="utf-8")

    def native_reply(payload, *, timeout):
        return json.dumps({"status": native_status})

    async def run():
        async with Client(recipe_service(tmp_path, native_reply)) as client:
            result = await call(client, "drawing_01-apply_style", recipe_id="project_plan")
            assert result["status"] == native_status
            if expect_guide:
                assert result["review_preparation"]["status"] == "not_executed"
            else:
                assert "review_preparation" not in result

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
            recipe_id = listed["recipes"][0]["recipe_id"]
            detail = await call(client, "drawing_02-get_recipe", recipe_id=recipe_id)
            assert all(part in detail["next_step_guide"] for part in (
                "drawing_01-apply_style tool", "recipe_id",
            ))
    asyncio.run(run())


def test_omitted_recipe_id_uses_first_loaded_file(tmp_path):
    first = {"recipe_id": "z_style", "layers": [{"path": "Drawing::First"}]}
    second = {"recipe_id": "a_style", "layers": [{"path": "Drawing::Second"}]}
    (tmp_path / "20-second.json").write_text(json.dumps(second), encoding="utf-8")
    (tmp_path / "10-first.json").write_text(json.dumps(first), encoding="utf-8")
    (tmp_path / "00-invalid.json").write_text("{}", encoding="utf-8")
    requests = []

    def native_reply(payload, *, timeout):
        requests.append(json.loads(payload))
        return json.dumps({"status": "success"})

    async def run():
        async with Client(recipe_service(tmp_path, native_reply)) as client:
            assert (await call(client, "drawing_01-apply_style"))["status"] == "success"
            assert (await call(client, "drawing_01-apply_style", recipe_id=second["recipe_id"]))["status"] == "success"
        async with Client(recipe_service(tmp_path / "empty", native_reply)) as client:
            assert (await call(client, "drawing_01-apply_style"))["status"] == "error"

    asyncio.run(run())
    assert [(request["recipe_id"], request["layers"]) for request in requests] == [
        (recipe["recipe_id"], recipe["layers"]) for recipe in (first, second)
    ]


def test_recipe_directory_override_is_indexed_when_the_service_starts(tmp_path, monkeypatch):
    recipe_key = "RHINO_MCP_DRAWING_RECIPE_DIR"
    monkeypatch.delenv(recipe_key, raising=False)
    assert Path(resolve_dir(recipe_key)) == RECIPE_DIR
    assert Path(bound_library_dirs()[recipe_key]) == RECIPE_DIR

    monkeypatch.setenv(recipe_key, str(user_data_dir() / "DrawingRecipes"))
    assert Path(resolve_dir(recipe_key)) == RECIPE_DIR
    assert Path(bound_library_dirs()[recipe_key]) == RECIPE_DIR

    monkeypatch.setenv(recipe_key, str(tmp_path))
    assert Path(bound_library_dirs()[recipe_key]) == tmp_path
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
