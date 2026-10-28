"""Shared paths and the inspected Almond contract. Never imports Almond."""
from __future__ import annotations

import hashlib
import asyncio
from importlib.metadata import version
import json
from pathlib import Path
import almond_mcp
from almond_mcp.modeling_guidance import content_digest, source_files as guide_files

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT.parent / "mcp" / "runtime"
PACKAGE = Path(almond_mcp.__file__).parent
# Keep the interpreter path used by existing CoS registrations stable.
PYTHON = ROOT.parent / "engine" / ".venv" / "Scripts" / "python.exe"
CATALOG = ROOT / "data" / "tool_catalog.json"
WORKER_STATE_TOOL = "worker_state"
VERSION = "0.2.0"


def digest(path: Path) -> str:
    return content_digest(path)


def source_paths(engine: Path) -> dict[str, Path]:
    package = PACKAGE
    paths = {
        "external_connection_guidance": ROOT / "CONNECTION-INSTRUCTIONS.md",
        "server_description": ROOT / "SERVER-DESCRIPTION.md",
        "model_context_instructions": package / "MODEL-CONTEXT-INSTRUCTIONS.md",
        "project": engine / "project.py",
        "entry": engine / "mcp_server.py",
        "shared_store": engine / "shared_store.py",
        "native_request": engine / "native_request.py",
        "compat_almond": engine / "compat_almond.py",
        "library_paths": engine / "library_paths.py",
        "workspace": engine / "workspace.py",
        "storage_cleanup": engine / "storage_cleanup.py",
        "python_runner": engine / "python_runner.py",
        "server": Path(almond_mcp.__file__).with_name("server.py"),
        "mcp_instructions": package / "FUNDAMENTAL-INSTRUCTIONS.md",
        "retrieval_store": Path(almond_mcp.__file__).with_name("retrieval_store.py"),
        "modeling_policy": package / "features/modeling/modeling_policy.py",
        "modeling_setup": package / "features/modeling/modeling_setup.py",
        "modeling_policy_json": Path(almond_mcp.__file__).with_name("modeling_policy.json"),
        "drawing_assets": package / "features/assets/drawing_assets.py",
        "drafting": package / "features/assets/drafting.py",
        "asset_repository": package / "features/assets/asset_repository.py",
    }
    covered = set(paths.values())
    # The flat source root also contains tests, launchers and build scripts.
    # Fingerprint executable package sources, not transient runtime data/tests.
    package_sources = [*package.glob("*.py"), *(package / "features").rglob("*.py")]
    for path in sorted(package_sources):
        if path not in covered:
            paths["package/" + path.relative_to(package).as_posix()] = path
    notes = [*package.glob("*-explain.md"), *(package / "features").rglob("*-explain.md")]
    for path in sorted(notes):
        paths["package/" + path.relative_to(package).as_posix()] = path
    for path in sorted(engine.glob("*-explain.md")):
        paths["engine/" + path.name] = path
    for path in guide_files():
        paths["package/" + path.relative_to(package).as_posix()] = path
    return paths


def load_catalog() -> dict:
    """Snapshot current source at process startup, without a model runtime import.

    Call before entering the stdio loop. The JSON export is only a developer
    inspection artifact; clients never depend on its freshness or existence.
    """
    from build_catalog import generate
    return asyncio.run(generate())


def check_contract(catalog: dict, engine: Path = ENGINE) -> None:
    for package, expected in catalog["packages"].items():
        actual = version(package)
        if actual != expected:
            raise RuntimeError(f"Almond external MCP expects {package} {expected}; installed: {actual}. Recheck compatibility.")
    paths = source_paths(engine)
    if set(paths) != set(catalog["sources"]):
        raise RuntimeError("Tool source inventory changed after this client started. Start a new client session before connecting.")
    for name, path in paths.items():
        if digest(path) != catalog["sources"][name]:
            raise RuntimeError(f"Tool source {path.name} changed after this client started. Start a new client session before connecting.")


def schema_identity(tool: dict) -> dict:
    return {key: tool.get(key) for key in ("name", "inputSchema", "outputSchema", "annotations")}


def catalog_identity(catalog: dict) -> str:
    snapshot = json.dumps(catalog, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(snapshot.encode("utf-8")).hexdigest()


def validate_worker_tools(catalog: dict, tools: list[dict]) -> None:
    expected = {t["name"]: schema_identity(t) for t in catalog["tools"]}
    actual = {t["name"]: schema_identity(t) for t in tools if t["name"] != WORKER_STATE_TOOL}
    if expected != actual:
        raise RuntimeError("Almond worker tool schemas changed. No modeling request was sent.")
