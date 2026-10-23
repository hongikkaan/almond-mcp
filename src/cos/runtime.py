"""Shared paths and the inspected Almond contract. Never imports Almond."""
from __future__ import annotations

import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import almond_mcp

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT.parent / "engine"
CATALOG = ROOT / "tool_catalog.json"
PREFIX = "almond_cos_"
WORKER_STATE_TOOL = "almond_cos_worker_state"
VERSION = "0.1.1"


def digest(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def source_paths(engine: Path) -> dict[str, Path]:
    return {
        "project": engine / "project.py",
        "entry": engine / "mcp_server.py",
        "shared_store": engine / "shared_store.py",
        "native_request": engine / "native_request.py",
        "compat_almond": engine / "compat_almond.py",
        "library_paths": engine / "library_paths.py",
        "server": Path(almond_mcp.__file__).with_name("server.py"),
        "retrieval_store": Path(almond_mcp.__file__).with_name("retrieval_store.py"),
        "modeling_policy": Path(almond_mcp.__file__).with_name("modeling_policy.py"),
        "modeling_policy_json": Path(almond_mcp.__file__).with_name("modeling_policy.json"),
        "drawing_assets": Path(almond_mcp.__file__).with_name("drawing_assets.py"),
        "drafting": Path(almond_mcp.__file__).with_name("drafting.py"),
        "asset_repository": Path(almond_mcp.__file__).with_name("asset_repository.py"),
    }


def load_catalog(path: Path = CATALOG) -> dict:
    catalog = json.loads(path.read_text(encoding="utf-8"))
    if catalog.get("format") != 1 or not catalog.get("tools"):
        raise RuntimeError("AlmondCOS tool catalog is missing or unsupported. Run build_catalog.py.")
    return catalog


def check_contract(catalog: dict, engine: Path = ENGINE) -> None:
    for package, expected in catalog["packages"].items():
        actual = version(package)
        if actual != expected:
            raise RuntimeError(f"AlmondCOS expects {package} {expected}; installed: {actual}. Recheck compatibility.")
    for name, path in source_paths(engine).items():
        if digest(path) != catalog["sources"][name]:
            raise RuntimeError(f"Almond {path.name} changed after this COS build. Recheck compatibility before connecting.")


def schema_identity(tool: dict) -> dict:
    return {key: tool.get(key) for key in ("name", "inputSchema", "outputSchema", "annotations")}


def validate_worker_tools(catalog: dict, tools: list[dict]) -> None:
    expected = {t["name"]: schema_identity(t) for t in catalog["tools"]}
    actual = {t["name"]: schema_identity(t) for t in tools if t["name"] != WORKER_STATE_TOOL}
    if expected != actual:
        raise RuntimeError("Almond worker tool schemas changed. No modeling request was sent.")
