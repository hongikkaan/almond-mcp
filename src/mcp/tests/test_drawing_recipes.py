"""Drawing recipe workflows through the public MCP tools."""
import asyncio
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

from fastmcp import Client, FastMCP
import pytest

from almond_mcp.features.drawings.library import DrawingRecipeIndexer
from almond_mcp.paths import resolve_dir, user_data_dir
from almond_mcp.runtime.library_paths import bound_library_dirs
from almond_mcp.features.drawings.standard import STANDARD_D
from almond_mcp.features.drawings.tools import register
from almond_mcp.tool_declarations import declaration_sources, inspect_declarations, register_inert_tools


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
        if json.loads(payload)["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"drawing_style_protection": 1}})
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
            assert recipe["layers"] == bundled_print_recipe["layers"] + STANDARD_D["layers"]

            for _ in range(2):
                outcome = await call(client, "drawing_01-apply_style", recipe_id=recipe_id)
                assert outcome["status"] == "success"
                assert outcome["review_preparation"]["status"] == "not_executed"
            assert len(requests) == 2
            for request in requests:
                assert request["type"] == "apply_drawing_style"
                assert request["recipe_id"] == recipe_id
                assert request["include_standard_d"] is True and request["overwrite"] is None
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


def test_bundled_recipes_list_read_and_apply_their_own_manual_d_layers(tmp_path):
    extensions = {}
    for filename, path in (("architectural_plan_section_a4.json", "D::Line::SiteBoundary"),
                           ("technical_axon.json", "D::PlanSectionNotes::AxoGuide")):
        recipe = json.loads((RECIPE_DIR / filename).read_text(encoding="utf-8"))
        layer = {"path": path, "plot_weight_mm": 0.22, "linetype": "Continuous"}
        recipe["layers"].append(layer)
        (tmp_path / filename).write_text(json.dumps(recipe), encoding="utf-8")
        extensions[recipe["recipe_id"]] = layer

    sdk = os.environ["ALMOND_TEST_DOTNET"]
    project = RECIPE_DIR.parents[2] / "src/rhp/RhinoAlmondBridge/tests/drawing_style/DrawingStyleFixture.csproj"
    subprocess.run([sdk, "build", str(project), "-c", "Release", "--nologo", "-p:NuGetAudit=false",
                    "-p:UseSharedCompilation=false", "-nodeReuse:false"], check=True)
    fixture = project.parent / "bin/Release/net8.0/DrawingStyleFixture.dll"

    def native_reply(payload, *, timeout):
        if json.loads(payload)["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"drawing_style_protection": 1}})
        return subprocess.run([sdk, str(fixture), "--apply"], input=payload, capture_output=True,
                              check=True, timeout=timeout).stdout.decode("utf-8")

    async def run():
        async with Client(recipe_service(tmp_path, native_reply)) as client:
            listed = await call(client, "drawing_05-list_recipes", include_ids=True)
            assert {row["recipe_id"] for row in listed["recipes"]} == set(extensions)
            for recipe_id, layer in extensions.items():
                detail = await call(client, "drawing_02-get_recipe", recipe_id=recipe_id, field_groups=["parameters"])
                assert layer in detail["recipe"]["layers"]
                applied = await call(client, "drawing_01-apply_style", recipe_id=recipe_id)
                assert applied["status"] == "success", applied
                actual = {row["path"]: row for row in applied["layers"]}
                assert set(actual) == {row["path"] for row in detail["recipe"]["layers"]}
                assert actual[layer["path"]]["plot_weight_mm"] == layer["plot_weight_mm"]
                assert actual[layer["path"]]["linetype"] == layer["linetype"]
                fixed_choice = await client.call_tool("drawing_01-apply_style", {"layer_path": layer["path"]},
                                                      raise_on_error=False)
                assert fixed_choice.is_error
    asyncio.run(run())


@pytest.mark.parametrize("path", ["D", "d::line", "D::LINE::hidden", "d::plansection", "D::PlanSection::Section"])
def test_composed_recipe_rejects_reserved_layer_paths(tmp_path, path):
    recipe = {"recipe_id": "unsafe", "layer_template": "standard_d", "layers": [{"path": path}]}
    (tmp_path / "unsafe.json").write_text(json.dumps(recipe), encoding="utf-8")
    assert DrawingRecipeIndexer(tmp_path).get("unsafe") is None


def test_standard_template_works_without_configured_recipes_and_resolves_a_selected_layer(tmp_path):
    requests = []

    def native_reply(payload, *, timeout):
        request = json.loads(payload)
        if request["type"] == "get_rhino_context":
            return json.dumps({"status": "success", "capabilities": {"drawing_style_protection": 1}})
        requests.append(request)
        return json.dumps({"status": "success", "layers": request["layers"]})

    async def run():
        async with Client(recipe_service(tmp_path / "empty", native_reply)) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            schema = tools["drawing_01-apply_style"].input_schema
            paths = [layer["path"] for layer in STANDARD_D["layers"]]
            inert_server = FastMCP("drawing-recipe-declarations")
            declarations = inspect_declarations(declaration_sources())
            declaration = next(item for item in declarations if item.name == "drawing_01-apply_style")
            register_inert_tools(inert_server, (declaration,))
            async with Client(inert_server) as inert_client:
                inert_tool, = await inert_client.list_tools()
                assert inert_tool.input_schema == schema
            layer_schema = schema["properties"]["layer_path"]
            assert any(option.get("enum") == paths for option in layer_schema["anyOf"])
            assert all(f'{row["path"]}: {row["role"]}' in layer_schema["description"] for row in STANDARD_D["layers"])
            assert (await call(client, "drawing_01-apply_style"))["layers"] == STANDARD_D["layers"]
            selected = await call(client, "drawing_01-apply_style", layer_path="D::Line::Hidden", overwrite=True)
            assert [layer["path"] for layer in selected["layers"]] == ["D::Line::Hidden", "D::Line"]

    asyncio.run(run())
    assert [request["overwrite"] for request in requests] == [False, True]
    assert all(request["recipe_id"] == "standard_d" for request in requests)
    assert all(not layer["path"].startswith("D::PlanSection") for layer in requests[0]["layers"])


def test_explicit_legacy_recipe_preserves_default_overwrite_but_has_no_standard_path_selector(tmp_path):
    legacy = {"recipe_id": "example_style", "layers": [{"path": "Drawing::Example"}]}
    (tmp_path / "recipe.json").write_text(json.dumps(legacy), encoding="utf-8")
    requests = []

    def native_reply(payload, *, timeout):
        requests.append(json.loads(payload))
        return json.dumps({"status": "success"})

    async def run():
        async with Client(recipe_service(tmp_path, native_reply)) as client:
            assert (await call(client, "drawing_01-apply_style", recipe_id=legacy["recipe_id"]))["status"] == "success"
            assert (await call(client, "drawing_01-apply_style", recipe_id=legacy["recipe_id"], layer_path="D::Section"))["status"] == "error"

    asyncio.run(run())
    assert len(requests) == 1
    assert requests[0]["overwrite"] is True
    assert requests[0]["layers"] == legacy["layers"]


@pytest.mark.parametrize("capability", [None, True, 0, "1"])
def test_old_bridge_never_receives_a_protected_mutation(tmp_path, capability):
    (tmp_path / "legacy.json").write_text(json.dumps({"recipe_id": "legacy", "layers": [{"path": "X"}]}))
    seen = []
    def send(payload, *, timeout):
        seen.append(json.loads(payload)["type"])
        return json.dumps({"status": "success", "capabilities": {"drawing_style_protection": capability}})

    async def run():
        async with Client(recipe_service(tmp_path, send)) as client:
            for args in ({}, {"overwrite": True}, {"recipe_id": "legacy", "overwrite": False}):
                assert (await call(client, "drawing_01-apply_style", **args))["status"] == "error"
        async with Client(recipe_service(RECIPE_DIR, send)) as client:
            for path in RECIPE_DIR.glob("*.json"):
                recipe = json.loads(path.read_text(encoding="utf-8"))
                assert (await call(client, "drawing_01-apply_style", recipe_id=recipe["recipe_id"]))["status"] == "error"
    asyncio.run(run())
    assert seen == ["get_rhino_context"] * 5


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
