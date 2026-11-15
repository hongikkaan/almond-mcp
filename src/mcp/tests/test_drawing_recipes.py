"""Recipe discovery/loading and production style preservation without live Rhino or user data."""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP

from almond_mcp import paths
from almond_mcp.features.drawings import linetypes
from almond_mcp.features.drawings.library import DrawingRecipeIndexer
from almond_mcp.features.drawings.tools import register


REPO = Path(__file__).resolve().parents[3]
RECIPES = REPO / "asset/drawing/DrawingRecipes"
A4 = "architectural_plan_section_a4_v1"


def context(directory):
    requests = []
    def send(payload, **kwargs):
        requests.append(json.loads(payload))
        return json.dumps({"status": "success", "layers": []})
    return SimpleNamespace(drawing_recipe_indexer=DrawingRecipeIndexer(str(directory)),
                           _send_and_receive=send, requests=requests)


@pytest.mark.parametrize("include_ids", [False, True])
@pytest.mark.parametrize("groups", [None, [], ["parameters"], ["all"]])
def test_a4_discovery_detail_guidance_and_repeat_payload(include_ids, groups):
    ctx = context(RECIPES)
    tools = register(FastMCP("recipes"), ctx)
    summary = json.loads(tools["list_drawing_recipes"](include_ids=include_ids, field_groups=groups))
    assert summary["total"] == 2
    assert "drawing_01-apply_style tool" in summary["next_step_guide"]
    assert all(("recipe_id" in recipe) == include_ids for recipe in summary["recipes"])
    detail = json.loads(tools["get_drawing_recipe"](A4, include_ids=include_ids, field_groups=groups))
    assert "drawing_01-apply_style tool" in detail["next_step_guide"]
    assert "조회에 사용한 recipe_id" in detail["next_step_guide"]
    assert "recipe_id" not in detail["recipe"]  # Known input is not echoed.
    assert ("layers" in detail["recipe"]) == bool(groups)
    original = deepcopy(ctx.drawing_recipe_indexer.recipes)
    for _ in range(2):
        assert json.loads(tools["apply_drawing_style"](A4))["status"] == "success"
    assert ctx.requests[0] == ctx.requests[1]
    layers = {layer["role"]: layer for layer in ctx.requests[0]["layers"]}
    assert layers["hidden"]["linetype_segments"] == [{"length": 3, "is_solid": True}, {"length": 1.5, "is_solid": False}]
    assert layers["overhead"]["linetype_segments"][2] == {"length": 0.5, "is_solid": True}
    assert ctx.drawing_recipe_indexer.recipes == original


def test_fresh_shared_snapshot_sample_exclusion_and_failed_edit_preserves_index(tmp_path):
    source = json.loads((RECIPES / "technical_axon.json").read_text(encoding="utf-8"))
    recipe_file = tmp_path / "working.json"
    recipe_file.write_text(json.dumps(source), encoding="utf-8")
    # Authoring files are excluded before parsing, including an unfinished edit.
    (tmp_path / "sample.json").write_text("unfinished authoring sample", encoding="utf-8")
    (tmp_path / "template.json").write_text(json.dumps({"is_sample": True}), encoding="utf-8")
    ctx = context(tmp_path)
    tools = register(FastMCP("refresh"), ctx)
    assert json.loads(tools["list_drawing_recipes"]())["total"] == 1
    source["name"] = "Changed while connected"
    source["layers"][0]["plot_weight_mm"] = 0.22
    recipe_file.write_text(json.dumps(source), encoding="utf-8")
    assert json.loads(tools["list_drawing_recipes"]())["recipes"][0]["name"] == source["name"]
    assert json.loads(tools["get_drawing_recipe"](source["recipe_id"]))["recipe"]["name"] == source["name"]
    tools["apply_drawing_style"](source["recipe_id"])
    assert ctx.requests[-1]["layers"][0]["plot_weight_mm"] == 0.22
    good = deepcopy(ctx.drawing_recipe_indexer.recipes)
    recipe_file.write_text("{", encoding="utf-8")
    for name, args in (("list_drawing_recipes", ()), ("get_drawing_recipe", (source["recipe_id"],)),
                       ("apply_drawing_style", (source["recipe_id"],))):
        result = json.loads(tools[name](*args))
        assert result["status"] == "error" and "working.json" in result["message"]
    assert len(ctx.requests) == 1 and ctx.drawing_recipe_indexer.recipes == good
    recipe_file.write_text(json.dumps(source), encoding="utf-8")
    assert json.loads(tools["get_drawing_recipe"](source["recipe_id"]))["status"] == "success"
    recipe_file.unlink()
    assert json.loads(tools["list_drawing_recipes"]())["total"] == 0


def test_duplicate_id_rejects_without_replacing_good_snapshot(tmp_path):
    (tmp_path / "first.json").write_text('{"recipe_id":"one"}', encoding="utf-8")
    index = DrawingRecipeIndexer(str(tmp_path))
    (tmp_path / "duplicate.json").write_text('{"recipe_id":"one"}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate recipe_id"):
        index.refresh()
    assert set(index.recipes) == {"one"}


def test_recipe_paths_keep_explicit_repo_and_appdata_resolution(tmp_path, monkeypatch):
    explicit = tmp_path / "explicit"
    monkeypatch.setenv("RHINO_MCP_DRAWING_RECIPE_DIR", str(explicit))
    assert paths.resolve_dir("RHINO_MCP_DRAWING_RECIPE_DIR") == str(explicit)
    monkeypatch.delenv("RHINO_MCP_DRAWING_RECIPE_DIR")
    assert Path(paths.resolve_dir("RHINO_MCP_DRAWING_RECIPE_DIR")) == RECIPES
    monkeypatch.setattr(paths, "_repo_dir", lambda _: None)
    monkeypatch.setattr(paths, "user_data_dir", lambda: tmp_path / "AppData")
    selected = Path(paths.resolve_dir("RHINO_MCP_DRAWING_RECIPE_DIR"))
    assert selected == tmp_path / "AppData/DrawingRecipes"
    assert selected.is_dir()


def test_profile_is_source_relative_and_keeps_legacy_patterns_and_inline_compatibility(monkeypatch):
    monkeypatch.setenv("RHINO_MCP_DRAWING_RECIPE_DIR", "unused")
    assert linetypes.PROFILE_FILE == REPO / "src/mcp/profiles/linetype/manifest.json"
    recipe = {"layers": [{"path": "a", "linetype": "User DashDot"}, {"path": "b", "linetype": "User custom"},
                         {"path": "c", "linetype": "User explicit", "linetype_segments": [{"length": 99, "is_solid": True}]},
                         {"path": "d", "linetype": "ALMOND A4 Hidden", "linetype_segments": [{"length": 99, "is_solid": True}]}]}
    before = deepcopy(recipe)
    layers = linetypes.style_layers(recipe)
    assert [v["length"] for v in layers[0]["linetype_segments"]] == [8, 3, 1, 3]
    assert [v["length"] for v in layers[1]["linetype_segments"]] == [6, 3]
    assert layers[2]["linetype_segments"][0]["length"] == 99
    assert layers[3]["linetype_segments"][0]["length"] == 3  # A4 source profile owns an old inline copy.
    assert recipe == before


@pytest.mark.parametrize("name", ["Continuous", "ByLayer", "ByParent", " bylayer ", " byparent ", " "])
def test_reserved_layer_patterns_do_not_receive_custom_segments(name):
    recipe = {"layers": [{"path": "Reserved", "linetype": name}]}
    assert linetypes.style_layers(recipe) == recipe["layers"]


@pytest.mark.parametrize("invalid", [[], [{"length": 0, "is_solid": True}], [{"length": True, "is_solid": True}],
                                     [{"length": 1, "is_solid": "true"}], [{"length": 1, "is_solid": False}],
                                     [{"length": float("nan"), "is_solid": True}]])
def test_invalid_profile_fails_before_transport(tmp_path, monkeypatch, invalid):
    profile = json.loads(linetypes.PROFILE_FILE.read_text(encoding="utf-8"))
    profile["linetypes"][0]["segments"] = invalid
    target = tmp_path / "manifest.json"
    target.write_text(json.dumps(profile), encoding="utf-8")
    monkeypatch.setattr(linetypes, "PROFILE_FILE", target)
    ctx = context(RECIPES)
    tools = register(FastMCP("invalid-profile"), ctx)
    assert json.loads(tools["apply_drawing_style"](A4))["status"] == "error"
    assert not ctx.requests


def test_unknown_recipe_has_no_success_guidance_or_transport():
    ctx = context(RECIPES)
    tools = register(FastMCP("unknown"), ctx)
    for name in ("get_drawing_recipe", "apply_drawing_style"):
        result = json.loads(tools[name]("not-registered"))
        assert result["status"] == "error" and "next_step_guide" not in result
    assert not ctx.requests


@pytest.mark.parametrize("invalid", [[], {"schema_version": True},
    {"schema_version": 1, "linetypes": {}, "legacy_name_rules": []},
    {"schema_version": 1, "linetypes": [1], "legacy_name_rules": []}])
def test_invalid_profile_structure_returns_error_before_transport(tmp_path, monkeypatch, invalid):
    target = tmp_path / "manifest.json"
    target.write_text(json.dumps(invalid), encoding="utf-8")
    monkeypatch.setattr(linetypes, "PROFILE_FILE", target)
    ctx = context(RECIPES)
    tools = register(FastMCP("invalid-profile-structure"), ctx)
    assert json.loads(tools["apply_drawing_style"](A4))["status"] == "error"
    assert not ctx.requests


def test_registered_recipe_call_guidance_is_executable():
    async def run():
        ctx = context(RECIPES)
        mcp = FastMCP("recipe-call")
        register(mcp, ctx)
        async with Client(mcp) as client:
            listing = await client.call_tool("drawing_05-list_recipes", {"include_ids": True})
            records = json.loads(listing.content[0].text)
            selected = next(recipe["recipe_id"] for recipe in records["recipes"] if recipe["recipe_id"] == A4)
            detail = await client.call_tool("drawing_02-get_recipe", {"recipe_id": selected})
            assert "drawing_01-apply_style tool" in json.loads(detail.content[0].text)["next_step_guide"]
            applied = await client.call_tool("drawing_01-apply_style", {"recipe_id": selected})
            assert not applied.is_error and json.loads(applied.content[0].text)["status"] == "success"
        assert len(ctx.requests) == 1 and ctx.requests[0]["recipe_id"] == A4
    asyncio.run(run())


def test_native_style_manager_preserves_named_definitions_and_references():
    sdk = os.environ.get("ALMOND_TEST_DOTNET")
    assert sdk, "Run through run_tests.ps1 to select .NET 8 SDK."
    project = Path(__file__).with_name("drawing_style_host") / "DrawingStyleHost.csproj"
    built = subprocess.run([sdk, "build", str(project), "-c", "Release", "--nologo", "-p:UseSharedCompilation=false",
                            "-p:NuGetAudit=false", "-nodeReuse:false"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert built.returncode == 0, built.stdout + built.stderr
    result = subprocess.run([sdk, str(project.parent / "bin/Release/net8.0/DrawingStyleHost.dll")],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS:" in result.stdout
