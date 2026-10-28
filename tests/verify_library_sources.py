"""Verify shared library routing with real MCP queries and disposable model/DB fixtures.

No Rhino is started or contacted. The native bridge fails closed in child probes.
Existing user libraries are read through Almond's native resolver; their hashes are
checked before/after. Explicit-override samples live only in the temporary fixture.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from uuid import uuid4

REPO = Path(__file__).resolve().parents[1]
ENGINE = REPO / "src/mcp/runtime"
COS = REPO / "src/cos"
DATA = REPO / "data/library-verification"
REPORT = DATA / "library-source-verification.json"


def child(mode, metadata, original_args):
    sys.path.insert(0, str(ENGINE))
    sys.path.insert(0, str(COS))
    sys.dont_write_bytecode = True
    attempts = []

    def forbid_native(*args, **kwargs):
        attempts.append("blocked native request")
        raise RuntimeError("Library probe must not contact Rhino.")
    from almond_mcp import paths
    original_resolve = paths.resolve_dir
    observed = {}

    def resolve(variable):
        value = original_resolve(variable)
        observed[variable] = value
        return value

    paths.resolve_dir = resolve
    import mcp_server as entry
    original_configure = entry.configure_project_context

    async def configure(mcp, args, binding, locations, **kwargs):
        await original_configure(mcp, args, binding, locations, **kwargs)
        from almond_mcp import server
        server._send_and_receive = forbid_native
        Path(metadata).write_text(json.dumps({
            "sources": observed, "temp": tempfile.gettempdir(),
            "database": os.environ["RHINO_MCP_STATE_DB"],
            "working_directory": os.getcwd(),
        }, ensure_ascii=False), encoding="utf-8")

    entry.configure_project_context = configure
    try:
        if mode == "cos":
            import external_worker
            sys.argv = [str(COS / "external_worker.py"), *original_args]
            result = external_worker.main()
        else:
            result = entry.main(original_args)
    finally:
        path = Path(metadata)
        if path.exists():
            record = json.loads(path.read_text(encoding="utf-8"))
            record["native_attempts"] = len(attempts)
            path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return result


def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def cli_environment(script_name, task_temp, inherited):
    # Execute only the actual environment-preparation block. No launcher, port,
    # document, lease, process startup, or Codex invocation is executed.
    script = (ENGINE / script_name).read_text(encoding="utf-8-sig")
    start = script.index("    $runtime=@{")
    ending = "    if($CheckOnly){" if script_name == "launch.ps1" else "    Write-Host "
    end = script.index(ending, start)
    runtime = script[start:end]
    codex = (ENGINE / "codex.ps1").read_text(encoding="utf-8-sig")
    match = re.search(r"(?ms)^    \$runtimeEnv = @\(.*?\)\r?\n", codex)
    if match is None:
        raise RuntimeError("Review the changed Codex environment block.")
    command = (
        "$ErrorActionPreference='Stop'\n$previous=@{}\n"
        "[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)\n"
        "$project=[pscustomobject]@{temp=" + ps_quote(task_temp) + ";project_dir=" + ps_quote(Path(task_temp).parent.parent) + "}\n"
        + runtime + "\n" + match.group(0)
        + "\n$captured=@{}\nforeach($name in $runtimeEnv){"
        "$value=[Environment]::GetEnvironmentVariable($name,'Process');"
        "if($null -ne $value){$captured[$name]=$value}}\n"
        "$captured | ConvertTo-Json -Compress\n"
    )
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        env=inherited, capture_output=True, text=True, encoding="utf-8",
        creationflags=subprocess.CREATE_NO_WINDOW, check=True, timeout=15,
    )
    captured = json.loads(completed.stdout)
    if captured.get("LOCALAPPDATA") != inherited.get("LOCALAPPDATA"):
        raise AssertionError("Codex must receive the native Windows data root.")
    result = dict(inherited)
    for key in [k for k in result if k.startswith("RHINO_MCP_") and k.endswith("_DIR")]:
        result.pop(key)
    result.update(captured)
    return result


def unpack(result):
    if result.is_error:
        raise AssertionError(str(result))
    value = result.structured_content
    if value is not None and set(value) == {"result"} and isinstance(value["result"], str):
        return json.loads(value["result"])
    if value is not None:
        return value
    return json.loads(next(block.text for block in result.content if block.type == "text"))


def snapshot(roots):
    result = {}
    for root in roots:
        for directory, _, files in os.walk(root):
            for name in files:
                path = Path(directory) / name
                result[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


async def probe(kind, base, *args, **kwargs):
    try:
        return await _probe(kind, base, *args, **kwargs)
    except Exception as error:
        log = base / (kwargs.get("fixture_name") or kind) / "stderr.txt"
        error.add_note(f"Probe: {kind}\n" + (log.read_text(encoding="utf-8") if log.exists() else "No child log"))
        raise


async def _probe(kind, base, inherited, expected, custom_id=None, *,
                fixture_name=None, seed_scene=False, expected_scene=None):
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    from project import connection_paths, process_start_ticks, ExclusiveFile
    from runtime import load_catalog, catalog_identity, WORKER_STATE_TOOL
    catalog = await asyncio.to_thread(load_catalog)

    folder = base / (fixture_name or kind)
    folder.mkdir(exist_ok=True)
    model = folder / "경로 확인.3dm"
    if not model.exists():
        model.write_bytes(b"LIBRARY ROUTING FIXTURE ONLY; NEVER OPENED IN RHINO")
    token = uuid4().hex
    locations = connection_paths(model, "J", token, create=True)
    storage = Path(locations["storage"])
    mode = "cos" if kind.startswith("cos") else "cli"
    binding = {
        "schema": "almond-project", "attachment": "cos" if mode == "cos" else "terminal",
        **locations, "storage_protocol": 2,
        "label": "J", "port": 5510, "token": token,
        "process_start_ticks": process_start_ticks(os.getpid()),
        "pid": os.getpid(), "valid": True, "model_path": locations["model_path"],
        "storage": locations["storage"],
    }
    ready = Path(locations["ready_path"])
    ready.write_text(json.dumps(binding, ensure_ascii=False), encoding="utf-8")
    metadata = folder / "observed.json"
    environment = dict(inherited, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    if kind.startswith("external"):
        environment = cli_environment("launch.ps1", locations["temp"], environment)
    elif kind.startswith("terminal"):
        environment = cli_environment("terminal_almond.ps1", locations["temp"], environment)
    if mode == "cos":
        environment["ALMONDRHINO_SESSION_TOKEN"] = binding["token"]
        environment["ALMONDRHINO_CATALOG_ID"] = catalog_identity(catalog)
        target_args = ["--session", str(ready), "--port", "5510", "--connection-id", kind]
    else:
        target_args = ["--session", str(ready), "--port", "5510", "--token", binding["token"],
                       "--expected-version", "0.7.0rc2", "--state-db", locations["state_db"]]
    params = StdioServerParameters(
        command=sys.executable,
        args=["-B", "-u", str(Path(__file__).resolve()), "--child", mode, str(metadata), *target_args],
        env=environment, cwd=str(COS if mode == "cos" else ENGINE),
    )
    stderr_path = folder / "stderr.txt"
    with stderr_path.open("w", encoding="utf-8") as errors:
        async with stdio_client(params, errlog=errors) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=45.0) as session:
                await session.initialize()
                tools, cursor = [], None
                from mcp_types import PaginatedRequestParams
                while True:
                    listing = await session.list_tools(
                        params=PaginatedRequestParams(cursor=cursor) if cursor else None)
                    tools.extend(t.name for t in listing.tools)
                    cursor = listing.next_cursor
                    if not cursor:
                        break
                expected_tools = {tool["name"] for tool in catalog["tools"]}
                if mode == "cos":
                    expected_tools.add(WORKER_STATE_TOOL)
                assert set(tools) == expected_tools and len(tools) == len(expected_tools), tools
                info = unpack(await session.call_tool("project_info", {"sections": ["project", "artifacts"]}))
                status = unpack(await session.call_tool("get_retrieval_status", {}))
                library = unpack(await session.call_tool("list_library", {"field_groups": ["paths"]}))
                capsules = unpack(await session.call_tool("list_capsules", {"include_ids": True, "field_groups": ["paths"]}))
                materials = unpack(await session.call_tool("list_materials", {"field_groups": ["paths"]}))
                drawings = unpack(await session.call_tool("list_drawing_assets", {}))
                def relative(value):
                    return os.path.relpath(value, locations["project_dir"]).replace("\\", "/")
                assert info["project"]["project_root"] == locations["project_dir"]
                assert info["project"]["root_variable_set"] is True
                assert info["project"]["database"] == relative(locations["state_db"])
                assert info["artifacts"]["artifact_dir"] == ""
                assert status["database"] == relative(locations["state_db"])
                assert library["library_dir"] == relative(expected["RHINO_MCP_LIBRARY_DIR"])
                assert capsules["capsule_library_dir"] == relative(expected["RHINO_MCP_CAPSULE_DIR"])
                assert materials["library_dir"] == relative(expected["RHINO_MCP_MATERIAL_DIR"])
                if custom_id:
                    asset = unpack(await session.call_tool("get_drawing_asset", {"asset_id": custom_id}))["asset"]
                    assert asset["file_available"] is True, asset
                    assert drawings["total"] == 1, drawings
                    assert drawings["assets"][0]["file_available"] is True, drawings
                scene = None
                if seed_scene:
                    created = unpack(await session.call_tool("create_design_scene", {
                        "name": "Existing fixture scene must survive source reindex", "units": "mm"
                    }))["scene"]
                    # Compare full snapshots, not the compact creation receipt.
                    scene = unpack(await session.call_tool("get_design_scene", {
                        "scene_id": created["scene_id"], "include_ids": True, "field_groups": ["all"]
                    }))["scene"]
                    scene["scene_id"] = created["scene_id"]
                elif expected_scene:
                    scene = unpack(await session.call_tool("get_design_scene", {
                        "scene_id": expected_scene["scene_id"], "include_ids": True, "field_groups": ["all"]
                    }))["scene"]
                    assert scene == {k: v for k, v in expected_scene.items() if k != "scene_id"}, (scene, expected_scene)
    observed = json.loads(metadata.read_text(encoding="utf-8"))
    assert observed["sources"] == expected, (kind, observed["sources"], expected)
    assert Path(observed["temp"]) != Path(locations["temp"])
    assert not Path(locations["temp"]).exists(), "File-free queries created project scratch directories"
    assert observed["database"] == locations["state_db"]
    assert observed["native_attempts"] == 0
    with ExclusiveFile(storage / "mcp.lock"):
        pass
    return {
        "mode": kind, "tool_count": len(tools), "database": locations["state_db"],
        "artifact_dir": locations["call_root"], "source_dirs": observed["sources"],
        "drawing_asset_count": drawings["total"],
        "drawing_available": sum(bool(a["file_available"]) for a in drawings["assets"]),
        "capsule_count": len(capsules["capsules"]),
        "capsule_ids": [c["capsule_id"] for c in capsules["capsules"]],
        "fixture_scene": scene, "existing_scene_preserved": bool(expected_scene),
        "native_requests": 0, "lease_released": True,
    }


async def run():
    sys.path.insert(0, str(ENGINE))
    sys.path.insert(0, str(COS))
    from almond_mcp import paths, __version__
    from runtime import check_contract, load_catalog
    from external_host import exposed_tools

    catalog = await asyncio.to_thread(load_catalog)
    check_contract(catalog)
    public, mapping = exposed_tools(catalog)
    assert set(mapping.values()) == {tool["name"] for tool in catalog["tools"]}
    management = {"list_connections", "connect", "disconnect", "start_session"}
    assert {tool.name for tool in public} == set(mapping) | management
    assert len(public) == len(catalog["tools"]) + len(management)
    inherited = dict(os.environ)
    for variable in paths.LIBRARY_DIRS:
        if inherited.get(variable):
            raise RuntimeError("Review existing explicit library overrides before the default-path probe: " + variable)
    root = Path(inherited["LOCALAPPDATA"]) / "Almond"
    expected = {variable: str(root / name / "releases" / __version__)
                if name in {"GeneratedAssetfiles", "Draftingfiles"} else str(root / name)
                for variable, name in paths.LIBRARY_DIRS.items()}
    before = snapshot([Path(p) for p in expected.values()])
    DATA.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="_library_sources_", dir=DATA) as temporary:
        base = Path(temporary)
        results = await asyncio.gather(*[
            probe(kind, base, inherited, expected) for kind in ("external", "terminal", "cos")
        ], return_exceptions=True)
        failures = [r for r in results if isinstance(r, Exception)]
        if failures:
            raise ExceptionGroup("Default path probes failed", failures)
        custom_root = base / "custom-drawing-library"
        (custom_root / "models").mkdir(parents=True)
        bundle_manifest = REPO / "asset/drawing/DrawingAssetfiles/manifest.json"
        manifest = json.loads(bundle_manifest.read_text(encoding="utf-8"))
        asset = dict(manifest["assets"][0], asset_id="library-routing-fixture", file="models/probe.svg")
        manifest["assets"] = [asset]
        (custom_root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (custom_root / "models/probe.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
        overrides = dict(inherited, RHINO_MCP_DRAWING_ASSET_DIR=str(custom_root))
        expected_override = dict(expected, RHINO_MCP_DRAWING_ASSET_DIR=str(custom_root))
        custom_results = await asyncio.gather(*[
            probe(kind + "-override", base, overrides, expected_override, "library-routing-fixture")
            for kind in ("external", "terminal", "cos")
        ], return_exceptions=True)
        failures = [r for r in custom_results if isinstance(r, Exception)]
        if failures:
            raise ExceptionGroup("Explicit override probes failed", failures)
        results.extend(custom_results)
        bundle = REPO
        old_sources = {variable: str(bundle / paths.REPO_LIBRARY_PATHS.get(name, name))
                       for variable, name in paths.LIBRARY_DIRS.items()}
        old_environment = dict(inherited, **old_sources)
        for kind in ("terminal", "cos"):
            fixture_name = kind + "-existing-database"
            old = await probe(kind + "-old-bundle", base, old_environment, old_sources,
                              fixture_name=fixture_name, seed_scene=True)
            refreshed = await probe(kind + "-after-reconnect", base, inherited, expected,
                                    fixture_name=fixture_name, expected_scene=old["fixture_scene"])
            assert old["database"] == refreshed["database"]
            assert Path(old["artifact_dir"]).parent == Path(refreshed["artifact_dir"]).parent
            assert old["artifact_dir"] != refreshed["artifact_dir"]
            results.extend([old, refreshed])
        after = snapshot([Path(p) for p in expected.values()])
        changed = [p for p, digest in before.items() if after.get(p) != digest]
        added = sorted(set(after) - set(before))
        assert not changed, "Existing user library files changed: " + repr(changed)
        report = {
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "checks_passed": len(results), "cos_public_tools": len(public),
            "existing_user_library_files_checked": len(before),
            "existing_user_library_files_changed": changed,
            "native_scaffold_files_added": added,
            "original_almond_package_modified": False,
            "real_rhino_contacted": False,
            "production_model_or_database_opened": False,
            "lookup_path_cases": 6, "existing_database_reindex_cases": 2,
            "fixture_scene_writes": 2,
            "probes": results,
        }
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: v for k, v in report.items() if k != "probes"}, ensure_ascii=False))
        print(json.dumps({"modes": [r["mode"] for r in results],
                          "capsule_ids": results[0]["capsule_ids"],
                          "sources": expected}, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        raise SystemExit(child(sys.argv[2], sys.argv[3], sys.argv[4:]))
    asyncio.run(run())
