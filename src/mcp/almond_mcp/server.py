"""
MCP Server for Rhino AI Plugin (v1.4)

Exposes tools for Claude to:
  1. list_library          — discover available physics archetypes
  2. get_logic_by_id       — retrieve parsed physics context for a specific archetype
  3. execute_rhino_script  — send C# RhinoCommon code to the Rhino bridge
  4. validate_structure    — run Karamba3D structural analysis on generated geometry
"""
import os
import base64
import io
import json
import math
import socket
import struct
import hashlib
import re
import sys
import tempfile
import uuid
import urllib.error
import urllib.request
from pathlib import Path
from fastmcp import FastMCP
from fastmcp.resources import ResourceContent, ResourceResult
from fastmcp.tools import ToolResult
from mcp.types import ImageContent, TextContent
from PIL import Image as PillowImage
from pydantic import StrictFloat, StrictInt
from almond_mcp.ghx_parser import GHParser, validate_capsule_manifest
from almond_mcp.retrieval_store import AlmondStore, ComponentReconciliationError, DrawingSheetReconciliationError
from almond_mcp import modeling_policy, modeling_setup, drawing_assets
from almond_mcp import asset_passport, asset_loads, conditioning, exchange, paths, drafting, native_structure, structure_study, design_codes

from almond_mcp.features.guidance.library import ConstructionLibrary, HistoryLibrary

from almond_mcp.features.modeling.library import MaterialLibrary

from almond_mcp.features.grasshopper.library import LibraryIndexer, _sync_capsule_library
from almond_mcp.features.grasshopper.tools import _CAPSULE_GEOMETRY_TYPES

from almond_mcp.features.structure.tools import KARAMBA_ONLY_TYPES

from almond_mcp.features.drawings.library import DrawingRecipeIndexer

# ── Constants ────────────────────────────────────────────────────────────────

DELIMITER = b'\n<<EOF>>\n'
LIBRARY_DIR = paths.resolve_dir("RHINO_MCP_LIBRARY_DIR")
DRAWING_LIBRARY_DIR = paths.resolve_dir("RHINO_MCP_DRAWING_ASSET_DIR")
DIAGRAM_LIBRARY_DIR = paths.resolve_dir("RHINO_MCP_DIAGRAM_ASSET_DIR")
GENERATED_LIBRARY_DIR = paths.resolve_dir("RHINO_MCP_GENERATED_ASSET_DIR")
DRAWING_RECIPE_DIR = paths.resolve_dir("RHINO_MCP_DRAWING_RECIPE_DIR")
DRAFTING_LIBRARY_DIR = paths.resolve_dir("RHINO_MCP_DRAFTING_DIR")
CAPSULE_LIBRARY_DIR = paths.resolve_dir("RHINO_MCP_CAPSULE_DIR")
MATERIAL_LIBRARY_DIR = paths.resolve_dir("RHINO_MCP_MATERIAL_DIR")
CONSTRUCTION_LIBRARY_DIR = paths.resolve_dir("RHINO_MCP_CONSTRUCTION_DIR")
STATE_DB_PATH = paths.resolve_state_db()
BRIDGE_HOST = '127.0.0.1'
BRIDGE_PORT = 5000
CHESTNUT_URL = os.environ.get(
    "CHESTNUT_URL",
    "https://chestnut-mnvo.onrender.com",
).rstrip("/")
print(f"Chestnut publish target: {CHESTNUT_URL}", file=sys.stderr)

# ── MCP Server ───────────────────────────────────────────────────────────────

mcp = FastMCP("Almond", instructions=(
    "Almond combines Rhino modelling with a semantic asset library. "
    "Before editing an existing model, inspect get_rhino_context; use "
    "get_rhino_viewport_image when the current view matters. Inspect relevant objects "
    "and validate proposed geometry against the task before replacing originals. "
    "Execution success and a viewport image do not establish geometric correctness. "
    "For reusable objects: prepare and visually review a millimeter, Z-up, bottom-center 3DM, "
    "then register_drawing_asset. Registration derives plan/front/right DXF and SVG plus dimensions "
    "under the same asset ID. Use get_drawing_asset, get_asset_drawing and place_drawing_asset. "
    "generate_asset_drawing_views remains available for a custom static GLB; verify outputs with audit_asset_drawing. "
    "search_detail_sources returns candidate directories, not verified construction details. "
    "Choose materials with get_material and use assign_material; existing layers are preserved. "
    "Use setup_modeling to register library materials or create construction-system layers. "
    "Register physical assemblies as Components: an object has at most one Component, "
    "each Component belongs to one or more Scenes, and raw objects may also link directly to a Scene. "
    "Use get_modeling_policy for keys; object names are free. "
    "Organize work as Phase > Plan > Step; Plans reference Scenes and Components, "
    "Steps may override Component targets. Resolve and inspect live targets before editing. "
    "Asset instances and Room bounds remain optional legacy placement checks; "
    "validate_scene_layout covers those cached asset instances, not all Component geometry. "
    "Use measured dimensions, not nominal prompt targets. Usage suggestions are "
    "heuristics and clearances are design allowances, not certified code compliance."
))

# ── Library Indexer ──────────────────────────────────────────────────────────



class AssetLibraryIndexer:
    """Indexes one controlled asset manifest and resolves safe local files."""

    def __init__(self, directory: str, library_id: str, label: str):
        self.directory = Path(directory).resolve()
        self.manifest_path = self.directory / "manifest.json"
        self.library_id = library_id
        self.label = label
        self.assets: dict[str, dict] = {}
        self.catalogue_region = ""
        self.catalogue_checked = ""
        self._load()

    def _load(self):
        if not self.manifest_path.is_file():
            print(f"{self.label} manifest not found: {self.manifest_path}", file=sys.stderr)
            return

        with self.manifest_path.open("r", encoding="utf-8") as manifest_file:
            manifest = json.load(manifest_file)

        self.catalogue_region = manifest.get("catalogue_region", "")
        self.catalogue_checked = manifest.get("catalogue_checked", "")
        manifest_library_id = manifest.get("library_id", self.library_id)
        if manifest_library_id != self.library_id:
            print(
                f"Skipping {self.label}: expected library_id {self.library_id}, "
                f"found {manifest_library_id}.",
                file=sys.stderr,
            )
            return
        # Treat each successful manifest read as a complete snapshot. Updating
        # the old map in place would keep removed IDs searchable after reload.
        assets: dict[str, dict] = {}
        for asset in manifest.get("assets", []):
            asset_id = str(asset.get("asset_id", "")).strip()
            relative_file = str(asset.get("file", "")).strip()
            if not asset_id or not relative_file:
                continue
            resolved_file = (self.directory / relative_file).resolve()
            try:
                resolved_file.relative_to(self.directory)
            except ValueError:
                print(f"Skipping {self.label} asset outside library root: {asset_id}", file=sys.stderr)
                continue
            record = dict(asset)
            record["library_id"] = self.library_id
            record["_resolved_file"] = str(resolved_file)
            record["file_available"] = resolved_file.is_file()
            assets[asset_id] = record

        self.assets = assets
        print(f"Indexed {len(self.assets)} {self.label} assets.", file=sys.stderr)

    def public_record(self, asset: dict) -> dict:
        return {key: value for key, value in asset.items() if not key.startswith("_")}

    def get(self, asset_id: str) -> dict | None:
        return self.assets.get(asset_id)

    def search(
        self,
        query: str = "",
        category: str = "",
        max_width_mm: float = 0,
        max_depth_mm: float = 0,
        max_height_mm: float = 0,
        exact_dimensions_only: bool = False,
        limit: int = 10,
    ) -> list[dict]:
        query_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
        category = category.lower().strip()
        results = []

        for asset in self.assets.values():
            if category and asset.get("category", "").lower() != category:
                continue
            if exact_dimensions_only and asset.get("match_status") != "exact_dimensions":
                continue

            dimensions = asset.get("dimensions_mm", {})
            if max_width_mm > 0 and dimensions.get("width", 0) > max_width_mm:
                continue
            if max_depth_mm > 0 and dimensions.get("depth", 0) > max_depth_mm:
                continue
            if max_height_mm > 0 and dimensions.get("height", 0) > max_height_mm:
                continue

            searchable = " ".join([
                asset.get("series", ""),
                asset.get("product", ""),
                asset.get("variant", ""),
                asset.get("category", ""),
                " ".join(asset.get("tags", [])),
            ]).lower()
            score = sum(1 for token in query_tokens if token in searchable)
            if query_tokens and score == 0:
                continue
            results.append((score, asset.get("series", ""), self.public_record(asset)))

        results.sort(key=lambda item: (-item[0], item[1], item[2]["asset_id"]))
        return [item[2] for item in results[:max(1, min(limit, 50))]]




# Build index once on startup
indexer = LibraryIndexer(LIBRARY_DIR)
drawing_asset_indexer = AssetLibraryIndexer(
    DRAWING_LIBRARY_DIR,
    library_id="drawing_assets",
    label="drawing",
)
diagram_asset_indexer = AssetLibraryIndexer(
    DIAGRAM_LIBRARY_DIR,
    library_id="diagram_assets",
    label="diagram",
)
generated_asset_indexer = AssetLibraryIndexer(
    GENERATED_LIBRARY_DIR,
    library_id="generated_assets",
    label="generated",
)
drawing_recipe_indexer = DrawingRecipeIndexer(DRAWING_RECIPE_DIR)








material_library = MaterialLibrary(MATERIAL_LIBRARY_DIR)
construction_library = ConstructionLibrary(CONSTRUCTION_LIBRARY_DIR)
history_library = HistoryLibrary(paths.resolve_dir("RHINO_MCP_HISTORY_DIR"))
retrieval_store = AlmondStore(STATE_DB_PATH)
retrieval_store.sync_assets(
    list(drawing_asset_indexer.assets.values()),
    library_id="drawing_assets",
)
# Retire the legacy supplier catalogue from searchable cache; local files and
# scene history are retained.
retrieval_store.sync_assets([], library_id="ikea")
retrieval_store.sync_assets(
    list(diagram_asset_indexer.assets.values()),
    library_id="diagram_assets",
)
retrieval_store.sync_assets(
    list(generated_asset_indexer.assets.values()),
    library_id="generated_assets",
)




capsule_sync_report = _sync_capsule_library(retrieval_store, CAPSULE_LIBRARY_DIR)

# ── TCP Helpers ──────────────────────────────────────────────────────────────

def _send_and_receive(payload_bytes: bytes, timeout: float = 60.0) -> str:
    """Send payload to the Rhino bridge using a length-prefix protocol and receive response."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((BRIDGE_HOST, BRIDGE_PORT))

        # Length-prefix: send 4-byte big-endian length header, then data
        length = len(payload_bytes)
        s.sendall(length.to_bytes(4, 'big'))
        s.sendall(payload_bytes)

        # Receive: read 4-byte length header, then exact data
        header = b''
        while len(header) < 4:
            chunk = s.recv(4 - len(header))
            if not chunk:
                raise ConnectionError("Bridge closed connection while reading response header.")
            header += chunk

        resp_length = int.from_bytes(header, 'big')
        resp_data = b''
        while len(resp_data) < resp_length:
            chunk = s.recv(min(16384, resp_length - len(resp_data)))
            if not chunk:
                raise ConnectionError("Bridge closed connection while reading response body.")
            resp_data += chunk

        return resp_data.decode('utf-8')
    finally:
        s.close()









# ── MCP Tools ────────────────────────────────────────────────────────────────





















# Legacy generated-asset implementations remain for resources, load tables and
# existing Python callers; the public modeling catalog uses drawing_assets.



















































































































































































_VIEW_ENGINE: str | None = None   # which engine drew the current overlay ("native" | "api")


































































# Feature factories: explicit composition, no runtime directory discovery.
from almond_mcp.feature_context import FeatureContext
from almond_mcp.features.assets.tools import register as _register_assets
from almond_mcp.features.capture.tools import register as _register_capture
from almond_mcp.features.components.tools import register as _register_components
from almond_mcp.features.context.tools import register as _register_context
from almond_mcp.features.diagrams.tools import register as _register_diagrams
from almond_mcp.features.drawings.tools import register as _register_drawings
from almond_mcp.features.egress.tools import register as _register_egress
from almond_mcp.features.exchange.tools import register as _register_exchange
from almond_mcp.features.grasshopper.tools import register as _register_grasshopper
from almond_mcp.features.guidance.tools import register as _register_guidance
from almond_mcp.features.modeling.tools import register as _register_modeling
from almond_mcp.features.placement.tools import register as _register_placement
from almond_mcp.features.planning.tools import register as _register_planning
from almond_mcp.features.publishing.tools import register as _register_publishing
from almond_mcp.features.scenes.tools import register as _register_scenes
from almond_mcp.features.structure.tools import register as _register_structure

_feature_context = FeatureContext(globals())
globals().update(_register_assets(mcp, _feature_context))
globals().update(_register_capture(mcp, _feature_context))
globals().update(_register_components(mcp, _feature_context))
globals().update(_register_context(mcp, _feature_context))
globals().update(_register_diagrams(mcp, _feature_context))
globals().update(_register_drawings(mcp, _feature_context))
globals().update(_register_egress(mcp, _feature_context))
globals().update(_register_exchange(mcp, _feature_context))
globals().update(_register_grasshopper(mcp, _feature_context))
globals().update(_register_guidance(mcp, _feature_context))
globals().update(_register_modeling(mcp, _feature_context))
globals().update(_register_placement(mcp, _feature_context))
globals().update(_register_planning(mcp, _feature_context))
globals().update(_register_publishing(mcp, _feature_context))
globals().update(_register_scenes(mcp, _feature_context))
globals().update(_register_structure(mcp, _feature_context))
# End feature composition.

if __name__ == "__main__":
    mcp.run()

