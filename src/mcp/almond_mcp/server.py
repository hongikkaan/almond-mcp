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


class DrawingRecipeIndexer:
    """Loads audited drawing-style recipes from a controlled directory."""

    def __init__(self, directory: str):
        self.directory = Path(directory).resolve()
        self.recipes: dict[str, dict] = {}
        if not self.directory.is_dir():
            print(f"Drawing recipe directory not found: {self.directory}", file=sys.stderr)
            return
        for recipe_path in sorted(self.directory.glob("*.json")):
            try:
                recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
                recipe_id = str(recipe.get("recipe_id", "")).strip()
                if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", recipe_id):
                    raise ValueError("invalid recipe_id")
                recipe["_source_file"] = str(recipe_path)
                self.recipes[recipe_id] = recipe
            except Exception as exc:
                print(f"Skipping drawing recipe {recipe_path.name}: {exc}", file=sys.stderr)
        print(f"Indexed {len(self.recipes)} drawing recipes.", file=sys.stderr)

    def get(self, recipe_id: str) -> dict | None:
        return self.recipes.get(recipe_id)

    @staticmethod
    def public_record(recipe: dict) -> dict:
        return {key: value for key, value in recipe.items() if not key.startswith("_")}


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











@mcp.tool()
def list_drawing_assets(
    category: str = "",
    limit: int = 20,
    offset: int = 0,
) -> str:
    """
    Lists representation-only entourage and graphic proxy assets.

    Drawing assets are representation elements and do
    not participate in room collision checks unless explicitly registered.
    """
    page = retrieval_store.search_assets(
        library_id="drawing_assets",
        category=category,
        limit=limit,
        offset=offset,
    )
    return json.dumps({
        "library_id": "drawing_assets",
        "purpose": "architectural representation and entourage",
        **page,
    })


@mcp.tool()
def search_drawing_assets(
    query: str = "",
    category: str = "",
    max_width_mm: float = 0,
    max_depth_mm: float = 0,
    max_height_mm: float = 0,
    limit: int = 10,
    offset: int = 0,
) -> str:
    """Searches only the controlled architectural drawing-asset library."""
    return json.dumps(retrieval_store.search_assets(
        query=query,
        library_id="drawing_assets",
        category=category,
        max_width_mm=max_width_mm,
        max_depth_mm=max_depth_mm,
        max_height_mm=max_height_mm,
        limit=limit,
        offset=offset,
    ))


@mcp.tool()
def get_drawing_asset(asset_id: str) -> str:
    """Returns one drawing asset's provenance, scale guidance, and availability."""
    asset = retrieval_store.get_asset(asset_id, library_id="drawing_assets")
    if not asset:
        return json.dumps({
            "status": "error",
            "message": f"Unknown drawing asset_id: {asset_id}",
        })
    return json.dumps({"status": "success", "asset": asset})


def _extract_drawing_asset(source_path: str, output_path: str) -> dict:
    context = json.loads(_send_and_receive(b'{"type":"get_rhino_context","selection_limit":0}'))
    if context.get("status") != "success" or context.get("capabilities", {}).get("drawing_asset_extract") != 1:
        raise ValueError("Load a Bridge with drawing_asset_extract=1 before registering a 3DM asset")
    response = _send_and_receive(json.dumps({"type": "drawing_asset_extract",
        "source_path": source_path, "output_path": output_path}).encode("utf-8"), timeout=90.0)
    if len(response.encode("utf-8")) > 262144:
        raise ValueError("Native extraction acknowledgement exceeds 256 KiB")
    return json.loads(response)


@mcp.tool(annotations={"destructiveHint": False, "openWorldHint": False})
def register_drawing_asset(source_3dm: str, asset_id: str, name: str,
                           category: str = "other", tags: list[str] | None = None,
                           description: str = "", source_url: str = "",
                           replace_existing: bool = False) -> dict:
    """Register a reviewed 3DM and automatically derive linked plan/front/right drawings.

    Finish cleanup/orientation review with the asset-converter workflow first.
    Supply an absolute prepared 3DM path: millimeters, Z up, bottom-center at origin.
    Native geometry checks support meshes, Breps, extrusions, surfaces, SubD and nested
    blocks, up to 100 MB/250k triangles. Unsupported objects reject the whole asset.
    Copies the source, measures dimensions and writes DXF at full-size mm, SVG at
    1:50/1:100 and A3 sheets where they fit. These are mesh silhouettes, not hidden
    lines or construction details; visual classification/front are not verified.
    Existing IDs require replace_existing=true. Prior files and manifest backups
    are retained. Refreshes this MCP process's index after atomic publication;
    other running processes must reconnect. The bundled Rhino panel is a release
    snapshot; use MCP placement for newly registered local assets.
    """
    try:
        if asset_id in generated_asset_indexer.assets or asset_id in diagram_asset_indexer.assets:
            raise ValueError("Choose an asset_id that does not belong to another library")
        result = drawing_assets.register_prepared_3dm(Path(DRAWING_LIBRARY_DIR),
            source_3dm=source_3dm, asset_id=asset_id, name=name, category=category,
            tags=tags, description=description, source_url=source_url,
            replace_existing=replace_existing, extract=_extract_drawing_asset)
    except Exception as exc:
        return {"status": "error", "registration_applied": False, "message": str(exc)}
    try:
        drawing_asset_indexer._load()
        retrieval_store.sync_assets(list(drawing_asset_indexer.assets.values()), library_id="drawing_assets")
    except Exception as exc:
        return {**result, "status": "error", "registration_applied": True,
                "live_index_refreshed": False,
                "message": f"Asset files and manifest were published. Reconnect to refresh the index; do not repeat registration: {exc}"}
    return {**result, "registration_applied": True, "live_index_refreshed": True}


# Legacy generated-asset implementations remain for resources, load tables and
# existing Python callers; the public modeling catalog uses drawing_assets.
def list_generated_assets(
    category: str = "",
    limit: int = 20,
    offset: int = 0,
) -> str:
    """
    Lists the redistributable generated asset library: 3D entourage (people,
    trees, vehicles), site furniture, columns, balustrades,
    sanitary/kitchen fixtures, and unbranded
    furniture placeholders. Every asset is a GLB normalised to real-world
    millimetres with a measured spatial contract and an Almond material_id,
    so placement, collision checks and material restore work without any
    third-party download. Place with place_generated_asset.
    """
    page = retrieval_store.search_assets(
        library_id="generated_assets",
        category=category,
        limit=limit,
        offset=offset,
    )
    return json.dumps({
        "library_id": "generated_assets",
        "purpose": "redistributable generated entourage, components and fixtures",
        "license": "CC-BY-4.0",
        **page,
    })


def search_generated_assets(
    query: str = "",
    category: str = "",
    max_width_mm: float = 0,
    max_depth_mm: float = 0,
    max_height_mm: float = 0,
    limit: int = 10,
    offset: int = 0,
) -> str:
    """Searches only the generated asset library (FTS over product, variant,
    category and tags; dimension filters use the measured GLB bounds)."""
    return json.dumps(retrieval_store.search_assets(
        query=query,
        library_id="generated_assets",
        category=category,
        max_width_mm=max_width_mm,
        max_depth_mm=max_depth_mm,
        max_height_mm=max_height_mm,
        limit=limit,
        offset=offset,
    ))


def recommend_generated_assets(
    query: str = "", category: str = "", room_type: str = "",
    width_mm: float = 0, depth_mm: float = 0, height_mm: float = 0,
    max_triangles: int = 0, include_clearances: bool = True, limit: int = 5,
) -> dict:
    """Shortlist available models with explicit reasons, quality notes and fit
    options. Query matches product/variant/tags; room_type is an inferred usage
    filter (e.g. living_room, dining_room, office, bathroom, landscape).
    Supply width AND depth for rectangular fit at 0/90 degrees; height 0 is
    unbounded. Authored clearances count by default. No Rhino connection needed.
    """
    try:
        return asset_passport.recommend(
            list(generated_asset_indexer.assets.values()), query, category, room_type,
            width_mm, depth_mm, height_mm, max_triangles, include_clearances, limit)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}


def get_generated_asset_passport(asset_id: str) -> dict:
    """Read portable asset metadata: measured vs nominal dimensions, provenance,
    materials, spatial contract, usage suggestions, quality limits and rights."""
    asset = generated_asset_indexer.get(asset_id)
    if not asset:
        return {"status": "error", "message": f"Unknown generated asset_id: {asset_id}"}
    if not asset.get("passport"):
        return {"status": "error", "message": "Library has no passport; upgrade the asset pack."}
    out = {"status": "success", "passport": asset["passport"],
           "file_available": asset.get("file_available", False),
           "preview_uri": f"almond://generated/{asset_id}/preview"}
    try:
        table = asset_loads.LoadTable(_structural_loads_path())
        entry = table.lookup(asset_id, asset.get("category", ""))
        if entry:
            out["structural_loads"] = {**entry, "basis": table.basis}
    except Exception:
        pass
    return out


def evaluate_generated_asset_fit(
    asset_id: str, width_mm: float, depth_mm: float, height_mm: float = 0,
    rotation_degrees: float = 0, include_clearances: bool = True,
) -> dict:
    """Check one model's rotated clearance envelope against a rectangle in mm.
    This is a preflight size check, not obstacle detection or code certification.
    Mounting heights and actual scene positions are not evaluated."""
    asset = generated_asset_indexer.get(asset_id)
    if not asset:
        return {"status": "error", "message": f"Unknown generated asset_id: {asset_id}"}
    try:
        return {"status": "success", **asset_passport.evaluate_fit(
            asset, width_mm, depth_mm, height_mm, rotation_degrees, include_clearances)}
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}




def get_generation_sources(asset_id: str) -> dict:
    """Get original recorded provider/task IDs, prompt, transformations and evidence gaps.
    Includes Higgsfield image job IDs where recorded before the Meshy stage.
    This is local evidence, not an independent provider/account verification."""
    path = Path(GENERATED_LIBRARY_DIR)/"source-register.json"
    if not path.exists():
        return {"status": "error", "message": "Source register missing; update the asset pack"}
    data = json.loads(path.read_text(encoding="utf-8"))
    record = next((a for a in data["assets"] if a["asset_id"] == asset_id), None)
    if not record:
        return {"status": "error", "message": "Unknown generated asset ID"}
    asset = generated_asset_indexer.get(asset_id)
    if not asset or record["model_sha256"] != asset["sha256"]:
        return {"status": "error", "message": "Source register is stale for this asset"}
    return {"status": "success", "record": record}


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
def get_asset_drawing(asset_id: str) -> dict:
    """Retrieve a registered 3DM's linked drawings and dimensions, or a legacy pilot package."""
    asset = drawing_asset_indexer.get(asset_id)
    if asset and asset.get("drawing_package"):
        root = Path(DRAWING_LIBRARY_DIR).resolve()
        package = (root / asset["drawing_package"]).resolve()
        package.relative_to(root)
        manifest = json.loads((package / "drawing.json").read_text(encoding="utf-8"))
        return {"status": "success", "asset_id": asset_id, "package_dir": str(package), "manifest": manifest,
                "dimensions_path": str(package / "dimensions.json"),
                "plan_svg_uri": f"almond://drawing/{asset_id}/drawing/plan/50"}
    root = Path(DRAFTING_LIBRARY_DIR)
    data = json.loads((root/"manifest.json").read_text(encoding="utf-8"))
    record = next((a for a in data["assets"] if a["asset_id"] == asset_id), None)
    if not record:
        return {"status": "error", "message": "No bundled drawing for this asset; generate views on demand"}
    package = (root/record["package"]).resolve()
    package.relative_to(root.resolve())
    manifest = json.loads((package/"drawing.json").read_text(encoding="utf-8"))
    return {"status": "success", "package_dir": str(package), "manifest": manifest,
            "plan_svg_uri": f"almond://generated/{asset_id}/drawing/plan/50"}


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False})
def generate_asset_drawing_views(asset_id: str = "", source_glb: str = "",
                                 input_units: str = "", up_axis: str = "y",
                                 scales: list[int] | None = None,
                                 source_references: list[dict] | None = None) -> dict:
    """Generate plan/front/right mesh silhouettes with source metadata, full-size DXF,
    scaled SVG and A3 SVG sheets where they fit. Writes a NEW local drawing-runs folder.
    Choose a library asset_id OR an absolute custom source_glb path. Custom files
    REQUIRE input_units mm or m; up_axis y or z. Scales default to [50,100].
    Supports static, uncompressed triangle GLBs only (max 100 MB/250k triangles).
    No hidden lines, inferred construction or product-front recognition.
    Optional item-level source_references require source_id/title/url/publisher/
    locator/accessed_on/relationship/used_for/terms_url. They describe references
    attached to this drawing, never retroactive generation inputs."""
    try:
        if bool(asset_id) == bool(source_glb):
            raise ValueError("Choose exactly one asset_id or source_glb")
        source_record = None
        if asset_id:
            asset = generated_asset_indexer.get(asset_id)
            if not asset:
                raise ValueError("Unknown generated asset ID")
            model = (Path(GENERATED_LIBRARY_DIR)/asset["file"]).resolve()
            model.relative_to(Path(GENERATED_LIBRARY_DIR).resolve())
            if drafting.sha(model.read_bytes()) != asset["sha256"]:
                raise ValueError("Source model checksum differs from catalogue")
            record_result = get_generation_sources(asset_id)
            if record_result["status"] != "success":
                raise ValueError(record_result["message"])
            source_record = record_result["record"]
            name, units, up = asset["product"], "mm", "y"
        else:
            model = Path(source_glb)
            if not model.is_absolute() or model.suffix.lower() != ".glb":
                raise ValueError("Custom source must be an absolute .glb path")
            if model.stat().st_size > 100_000_000:
                raise ValueError("GLB exceeds 100 MB limit")
            name, units, up = model.stem, input_units, up_axis
            asset_id = "custom-" + drafting.sha(model.read_bytes())[:16].lower()
            source_record = {"evidence_status": "user_supplied_mesh", "generation_history": "not_supplied"}
        output = paths.user_data_dir()/"drawing-runs"/str(uuid.uuid4())
        return drafting.create_package(model, output, asset_id=asset_id, name=name,
            units=units, up_axis=up, scales=[50, 100] if scales is None else scales,
            references=source_references or [], source_record=source_record)
    except (OSError, ValueError, KeyError, IndexError, TypeError, struct.error) as exc:
        return {"status": "error", "message": str(exc)}


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
def audit_asset_drawing(package_dir: str, source_glb: str = "") -> dict:
    """Check exported files and whether source geometry changed. Custom packages
    need the current source_glb to check staleness; library assets resolve automatically."""
    try:
        package = Path(package_dir)
        if not package.is_absolute():
            raise ValueError("Supply an absolute package directory")
        manifest = json.loads((package/"drawing.json").read_text(encoding="utf-8"))
        source = Path(source_glb) if source_glb else None
        if source is not None and not source.is_absolute():
            raise ValueError("Supply an absolute source GLB path")
        if source is None:
            asset = drawing_asset_indexer.get(manifest["source"]["asset_id"])
            root = Path(DRAWING_LIBRARY_DIR) if asset else Path(GENERATED_LIBRARY_DIR)
            asset = asset or generated_asset_indexer.get(manifest["source"]["asset_id"])
            if asset:
                source = (root / asset["file"]).resolve()
                source.relative_to(root.resolve())
        return drafting.audit_package(package, source)
    except (OSError, ValueError, KeyError, IndexError, TypeError, struct.error) as exc:
        return {"status": "error", "message": str(exc)}


@mcp.resource("almond://generated/{asset_id}/sources", mime_type="application/json")
def generation_sources_resource(asset_id: str) -> ResourceResult:
    return ResourceResult([ResourceContent(get_generation_sources(asset_id), mime_type="application/json")])


@mcp.resource("almond://generated/{asset_id}/drawing/{view}/{scale}", mime_type="image/svg+xml")
def asset_drawing_resource(asset_id: str, view: str, scale: str) -> ResourceResult:
    if view not in {"plan", "front", "right"} or scale not in {"50", "100"}:
        raise ValueError("Unknown bundled view or scale")
    result = get_asset_drawing(asset_id)
    if result["status"] != "success":
        raise ValueError(result["message"])
    filename = f"{view}-1-{scale}.svg"
    model = drawing_asset_indexer.get(asset_id)
    root = Path(DRAWING_LIBRARY_DIR) if model else Path(GENERATED_LIBRARY_DIR)
    model = model or generated_asset_indexer.get(asset_id)
    source = (root / model["file"]).resolve() if model else None
    if source:
        source.relative_to(root.resolve())
    checked = drafting.audit_package(Path(result["package_dir"]), source)
    if checked["status"] != "success":
        raise ValueError("Drawing package is modified or stale")
    return ResourceResult([ResourceContent((Path(result["package_dir"])/filename).read_text(encoding="utf-8"), mime_type="image/svg+xml")])


@mcp.resource("almond://drawing/{asset_id}/drawing/{view}/{scale}", mime_type="image/svg+xml")
def drawing_asset_view_resource(asset_id: str, view: str, scale: str) -> ResourceResult:
    return asset_drawing_resource(asset_id, view, scale)


@mcp.resource("almond://generated/catalogue", mime_type="application/json")
def generated_catalogue_resource() -> ResourceResult:
    """Compact catalogue; retrieve individual passports/previews on demand."""
    return ResourceResult([ResourceContent({"library_id": "generated_assets", "assets": [
        {"asset_id": a["asset_id"], "product": a["product"], "category": a["category"],
         "dimensions_mm": a["dimensions_mm"],
         "passport_uri": f"almond://generated/{a['asset_id']}/passport",
         "preview_uri": f"almond://generated/{a['asset_id']}/preview"}
        for a in generated_asset_indexer.assets.values()]}, mime_type="application/json")])


@mcp.resource("almond://generated/{asset_id}/passport", mime_type="application/json")
def generated_passport_resource(asset_id: str) -> ResourceResult:
    return ResourceResult([ResourceContent(get_generated_asset_passport(asset_id), mime_type="application/json")])


@mcp.resource("almond://generated/{asset_id}/preview", mime_type="image/png")
def generated_preview_resource(asset_id: str) -> ResourceResult:
    """Existing Blender preview for a known catalogue id."""
    if asset_id not in generated_asset_indexer.assets:
        raise ValueError("Unknown generated asset id")
    root = Path(GENERATED_LIBRARY_DIR).resolve()
    preview = (root / "previews" / f"{asset_id}.png").resolve()
    preview.relative_to(root)
    return ResourceResult([ResourceContent(preview.read_bytes(), mime_type="image/png")])


def get_generated_asset(asset_id: str) -> str:
    """Returns one generated asset's measured dimensions, spatial contract,
    material, generation provenance (Meshy task ids, prompt) and availability."""
    asset = retrieval_store.get_asset(asset_id, library_id="generated_assets")
    if not asset:
        return json.dumps({
            "status": "error",
            "message": f"Unknown generated asset_id: {asset_id}",
        })
    return json.dumps({"status": "success", "asset": asset})


@mcp.tool()
def list_drawing_recipes() -> str:
    """Lists compact audited layer, lineweight, projection, and export recipes."""
    recipes = []
    for recipe_id, recipe in sorted(drawing_recipe_indexer.recipes.items()):
        recipes.append({
            "recipe_id": recipe_id,
            "name": recipe.get("name"),
            "description": recipe.get("description"),
            "projection": recipe.get("projection", {}).get("type"),
            "recommended_scales": recipe.get("recommended_scales", []),
        })
    return json.dumps({"total": len(recipes), "recipes": recipes})


@mcp.tool()
def get_drawing_recipe(recipe_id: str) -> str:
    """Returns one complete audited drawing recipe."""
    recipe = drawing_recipe_indexer.get(recipe_id)
    if not recipe:
        return json.dumps({
            "status": "error",
            "message": f"Unknown drawing recipe_id: {recipe_id}",
        })
    return json.dumps({
        "status": "success",
        "recipe": drawing_recipe_indexer.public_record(recipe),
    })













































@mcp.tool()
def create_generation_phase(name: str, description: str = "") -> str:
    """Create an organizational Phase for Plans; this does not edit Rhino geometry."""
    try:
        return json.dumps({"status": "success", "phase": retrieval_store.create_generation_phase(name, description)})
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


@mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
def get_generation_phase(phase_id: str) -> str:
    """Read a Phase's name, description and Plan count."""
    try:
        phase = retrieval_store.get_generation_phase(phase_id)
        if phase is None:
            return json.dumps({"status": "error", "message": f"Unknown phase_id: {phase_id}"})
        return json.dumps({"status": "success", "phase": phase})
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


@mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
def list_generation_phases(limit: StrictInt = 50) -> str:
    """List organizational Phases with totals and an explicit truncation flag; limit is 1-500."""
    try:
        return json.dumps({"status": "success", **retrieval_store.list_generation_phases(limit)})
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


@mcp.tool()
def update_generation_phase(
    phase_id: str, name: str | None = None, description: str | None = None,
) -> str:
    """Update Phase organization; omitted fields retain their values."""
    try:
        return json.dumps({
            "status": "success", "phase": retrieval_store.update_generation_phase(phase_id, name, description),
        })
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


@mcp.tool()
def create_generation_plan(
    goal: str,
    scope: str = "house",
    scene_id: str = "",
    phase_id: str = "",
    scene_ids: list[str] | None = None,
    component_ids: list[str] | None = None,
) -> str:
    """
    Create a dependency-ordered Plan in an optional organizational Phase.
    scope is house, interior, structure, drawing, or component; component uses
    inspect_context, design, model, validate. scene_ids are context; component_ids
    explicitly bind targets without requiring membership in those Scenes.
    Legacy scene_id must match the first scene_ids entry when both are supplied.
    Plans record state and evidence, do not execute steps, and do not authorize edits.
    """
    try:
        return json.dumps({
            "status": "success",
            "plan": retrieval_store.create_generation_plan(
                goal=goal,
                scope=scope,
                scene_id=scene_id,
                phase_id=phase_id,
                scene_ids=scene_ids,
                component_ids=component_ids,
            ),
        })
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


@mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
def get_generation_plan(plan_id: str, revision: StrictInt | None = None) -> str:
    """Read the current Plan or an immutable saved revision, including legacy baseline 0.

    Snapshots contain Plan metadata, step state and handles; they are not Rhino
    geometry backups. A missing requested revision never falls back to current state.
    """
    try:
        plan = retrieval_store.get_generation_plan(plan_id, revision)
        if plan is None:
            message = (f"Unknown plan_id: {plan_id}" if revision is None else
                       f"Unknown saved revision {revision} for plan_id: {plan_id}")
            return json.dumps({"status": "error", "message": message})
        return json.dumps({"status": "success", "plan": plan})
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


@mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
def list_generation_plans(
    phase_id: str = "", scene_id: str = "", status: str = "", limit: StrictInt = 50,
) -> str:
    """List compact Plan summaries, optionally filtered by Phase, contextual Scene or status."""
    try:
        return json.dumps({
            "status": "success", **retrieval_store.list_generation_plans(phase_id, scene_id, status, limit),
        })
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


@mcp.tool()
def update_generation_plan(
    plan_id: str,
    goal: str | None = None,
    phase_id: str | None = None,
    scene_ids: list[str] | None = None,
    component_ids: list[str] | None = None,
    expected_revision: StrictInt | None = None,
) -> str:
    """Update Plan metadata and bindings atomically, recording a new saved revision.

    Omitted fields retain prior values; [] clears refs, and phase_id='' detaches
    the Phase. expected_revision rejects stale updates without changing the Plan.
    References provide context and explicit targets, not permission to edit geometry.
    """
    try:
        return json.dumps({
            "status": "success", "plan": retrieval_store.update_generation_plan(
                plan_id, goal=goal, phase_id=phase_id, scene_ids=scene_ids,
                component_ids=component_ids, expected_revision=expected_revision,
            ),
        })
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


@mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
def list_generation_plan_revisions(plan_id: str, limit: StrictInt = 50) -> str:
    """List saved Plan revisions newest first, with operation labels and truncation metadata."""
    try:
        return json.dumps({"status": "success", **retrieval_store.list_generation_plan_revisions(plan_id, limit)})
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


@mcp.tool()
def update_generation_step(
    plan_id: str,
    step_id: str,
    status: str,
    input_refs: list[str] | None = None,
    output_refs: list[str] | None = None,
    component_ids: list[str] | None = None,
    expected_revision: StrictInt | None = None,
) -> str:
    """
    Record a Step's status, evidence and optional explicit Component targets.
    Omitted refs retain prior values; [] clears them. Step component_ids=null in a
    returned Plan inherits Plan targets; explicit [] selects none. Scene refs never
    expand the selection. running/completed require completed prerequisites, and a
    prerequisite cannot regress while descendants run or remain completed.
    expected_revision rejects stale updates. No Rhino operation is executed here.
    """
    try:
        return json.dumps({
            "status": "success",
            "plan": retrieval_store.update_plan_step(
                plan_id=plan_id,
                step_id=step_id,
                status=status,
                input_refs=input_refs,
                output_refs=output_refs,
                component_ids=component_ids,
                expected_revision=expected_revision,
            ),
        })
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})




@mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
def resolve_generation_targets(plan_id: str, step_id: str = "") -> str:
    """Resolve registered Step targets, or Plan targets when the Step has no override.

    An explicit empty Step selection stays empty. Contextual Scenes never expand
    targets. Returned group/document identities have live_verified=false; inspect
    current Rhino state and user intent before editing. This does not grant authority.
    """
    try:
        return json.dumps({"status": "success", **retrieval_store.resolve_generation_targets(plan_id, step_id)})
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


def _drawing_sheet_bridge(request: dict) -> dict:
    """Check Layout capability, then send exactly one requested native operation."""
    payload = json.dumps(request, allow_nan=False).encode("utf-8")
    if len(payload) > 2_097_152:
        return {"status": "error", "mutation_applied": False, "message": "Drawing sheet request exceeds 2 MiB."}
    try:
        context = json.loads(_send_and_receive(b'{"type":"get_rhino_context","selection_limit":0}'))
        if not isinstance(context, dict) or context.get("status") != "success":
            raise ValueError("Could not inspect the bound Rhino document.")
        if context.get("capabilities", {}).get("drawing_sheets") != 1:
            raise ValueError("Load a Bridge with drawing_sheets=1 before managing drawing sheets.")
    except Exception as exc:
        return {"status": "error", "mutation_applied": False, "message": str(exc)}
    response = _send_and_receive(payload)
    if len(response.encode("utf-8")) > 2_097_152:
        raise ValueError("Drawing sheet response exceeds 2 MiB.")
    result = json.loads(response)
    if not isinstance(result, dict):
        raise ValueError("Invalid native drawing sheet response.")
    return result


def _drawing_sheet_error(exc: Exception) -> str:
    result = {"status": "error", "message": str(exc)}
    if isinstance(exc, DrawingSheetReconciliationError):
        result.update(error_code="drawing_sheet_reconciliation_required", requires_reconciliation=True,
                      sheet_id=exc.sheet_id, expected_model_path=exc.model_path)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool(annotations={"destructiveHint": False})
def upsert_drawing_sheet(
    expected_model_path: str, title: str, drawing_type: str, scale_denominator: StrictFloat,
    paper_mm: list[StrictFloat], model_bounds_mm: list[StrictFloat],
    scene_ids: list[str] | None = None, component_ids: list[str] | None = None,
    plan_id: str | None = None, sheet_id: str = "", layout_id: str = "",
) -> str:
    """Register one authored modelspace drawing region with one Rhino Layout tab.

    Supply world-XY bounds [minX,minY,minZ,maxX,maxY,maxZ] in mm, positive XY
    extents, paper [width,height] in mm, and a positive scale denominator (100 = 1:100).
    The native Layout uses a parallel Top detail; the region must fit at that scale.
    drawing_type is plan, section, elevation, detail, axonometric, perspective,
    schedule or other. These are labels; this tool does not generate drawing geometry.
    New sheets create a Layout when layout_id is empty. Existing identities cannot
    change model or Layout. Omitted refs preserve existing values; [] clears refs,
    plan_id='' unlinks a Plan. List sheets by Plan at wrapup to inspect duplicates.
    After an uncertain result, sync_drawing_sheet; do not replay the mutation.
    """
    try:
        sheet = retrieval_store.upsert_drawing_sheet(
            model_path=expected_model_path, title=title, drawing_type=drawing_type,
            scale_denominator=scale_denominator, paper_mm=paper_mm, model_bounds_mm=model_bounds_mm,
            scene_ids=scene_ids, component_ids=component_ids, plan_id=plan_id,
            sheet_id=sheet_id, layout_id=layout_id, native_apply=_drawing_sheet_bridge,
        )
        return json.dumps({"status": "success", "sheet": sheet}, ensure_ascii=False)
    except Exception as exc:
        return _drawing_sheet_error(exc)


@mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
def get_drawing_sheet(sheet_id: str) -> str:
    """Read a cached sheet title, scale, paper, modelspace bounds, Layout and context refs."""
    try:
        sheet = retrieval_store.get_drawing_sheet(sheet_id)
        if sheet is None:
            raise KeyError(f"Unknown sheet_id: {sheet_id}")
        return json.dumps({"status": "success", "sheet": sheet}, ensure_ascii=False)
    except Exception as exc:
        return _drawing_sheet_error(exc)


@mcp.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
def list_drawing_sheets(
    plan_id: str = "", scene_id: str = "", component_id: str = "",
    expected_model_path: str = "", limit: StrictInt = 100,
) -> str:
    """List named sheets for Plan wrapup or Scene/Component/model review; combine filters with AND.

    Returns cached registration data, total and truncation. Review names and locations
    before deciding whether drawings are unnecessary; listing never deletes geometry.
    """
    try:
        return json.dumps({"status": "success", **retrieval_store.list_drawing_sheets(
            plan_id=plan_id, scene_id=scene_id, component_id=component_id,
            model_path=expected_model_path, limit=limit,
        )}, ensure_ascii=False)
    except Exception as exc:
        return _drawing_sheet_error(exc)


@mcp.tool(annotations={"destructiveHint": False})
def sync_drawing_sheet(expected_model_path: str, sheet_id: str, layout_id: str = "") -> str:
    """Reconcile a sheet from read-only native Layout inspection without replaying a mutation.

    Use after a lost response, failed database commit or manual edits. Registered
    snapshots can restore a missing ledger row. Verified unregistered retained
    Layouts can release an existing ledger row; a missing Layout is not that proof.
    """
    try:
        sheet = retrieval_store.sync_drawing_sheet(
            model_path=expected_model_path, sheet_id=sheet_id, layout_id=layout_id,
            native_inspect=_drawing_sheet_bridge,
        )
        return json.dumps({"status": "success", "sheet": sheet}, ensure_ascii=False)
    except Exception as exc:
        return _drawing_sheet_error(exc)


@mcp.tool(annotations={"destructiveHint": False})
def remove_drawing_sheet(sheet_id: str) -> str:
    """Unregister a sheet while preserving its Rhino Layout, detail and modelspace drawing geometry."""
    try:
        sheet = retrieval_store.remove_drawing_sheet(sheet_id, native_apply=_drawing_sheet_bridge)
        return json.dumps({"status": "success", "sheet": sheet}, ensure_ascii=False)
    except Exception as exc:
        return _drawing_sheet_error(exc)


def _dimension_check(asset: dict, bounds: dict | None, scale: float) -> dict | None:
    """Flags gross mismatches between placed AABB and catalogue dimensions.

    Sorted-extent comparison so plan rotations don't false-positive. Only
    returns a payload on failure; a clean placement stays silent.
    """
    dims = asset.get("dimensions_mm") or {}
    expected = [dims.get("width"), dims.get("depth"), dims.get("height")]
    if not bounds or not all(isinstance(v, (int, float)) and v > 0 for v in expected):
        return None
    try:
        placed = sorted(
            abs(float(bounds["max"][i]) - float(bounds["min"][i])) for i in range(3)
        )
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    expected_sorted = sorted(float(v) * scale for v in expected)
    tolerance = 0.15
    mismatched = [
        axis for axis, (p, e) in enumerate(zip(placed, expected_sorted))
        if e > 0 and abs(p - e) / e > tolerance
    ]
    if not mismatched:
        return None
    return {
        "status": "mismatch",
        "expected_sorted_mm": [round(v, 1) for v in expected_sorted],
        "placed_sorted_mm": [round(v, 1) for v in placed],
        "tolerance": tolerance,
        "note": "Placed geometry deviates from catalogue dimensions beyond "
                "tolerance; inspect the source model (see manifest match note).",
    }


def _apply_import_correction(object_guid: str, rotate_x_degrees: float, target_z: float) -> bool:
    """Re-orients a placed instance whose source geometry is mis-oriented
    (manifest import_correction), then re-seats it on the placement plane."""
    script = f"""
using System;
using System.Collections.Generic;
using Rhino;
using Rhino.Geometry;

public class Script
{{
    public static List<Guid> Run(RhinoDoc doc)
    {{
        var id = new Guid("{object_guid}");
        var obj = doc.Objects.FindId(id);
        if (obj == null) return new List<Guid>();
        var bb = obj.Geometry.GetBoundingBox(true);
        var rot = Transform.Rotation(RhinoMath.ToRadians({rotate_x_degrees}), Vector3d.XAxis, bb.Center);
        doc.Objects.Transform(id, rot, true);
        var obj2 = doc.Objects.FindId(id);
        if (obj2 != null)
        {{
            var bb2 = obj2.Geometry.GetBoundingBox(true);
            doc.Objects.Transform(id, Transform.Translation(0, 0, {target_z} - bb2.Min.Z), true);
        }}
        doc.Views.Redraw();
        return new List<Guid>();
    }}
}}
"""
    payload = json.dumps({"type": "execute", "script": script}).encode("utf-8")
    try:
        response = json.loads(_send_and_receive(payload, timeout=30.0))
        return response.get("status") == "success"
    except Exception:
        return False
















@mcp.tool()
def place_drawing_asset(
    asset_id: str,
    x: float = 0,
    y: float = 0,
    z: float = 0,
    rotation_degrees: float = 0,
    scale: float = 1,
) -> str:
    """
    Places an indexed representation asset as a reusable Rhino block.

    x/y/z and returned bounds use the active document's units; scale is dimensionless.
    Prepared 3DM geometry is converted from its stored millimeters by Rhino on import.
    Drawing assets are placed on ALMOND-DRAW::ASSETS and remain distinct from
    generated model blocks. The tool accepts only files resolved from the
    controlled asset/drawing/DrawingAssetfiles manifest.
    """
    asset = drawing_asset_indexer.get(asset_id)
    if not asset:
        return json.dumps({
            "status": "error",
            "message": f"Unknown drawing asset_id: {asset_id}",
        })
    if not asset.get("file_available"):
        return json.dumps({
            "status": "error",
            "message": f"Drawing asset file is missing for {asset_id}.",
        })
    numeric_values = [x, y, z, rotation_degrees, scale]
    if not all(
        isinstance(value, (int, float))
        and abs(value) != float("inf")
        and value == value
        for value in numeric_values
    ):
        return json.dumps({
            "status": "error",
            "message": "Placement values must be finite numbers.",
        })
    if scale <= 0 or scale > 100:
        return json.dumps({
            "status": "error",
            "message": "scale must be greater than 0 and no more than 100.",
        })

    payload = json.dumps({
        "type": "place_drawing_asset",
        "asset_id": asset_id,
        "file_path": asset["_resolved_file"],
        "name": f"{asset.get('product', '')} {asset.get('variant', '')}".strip(),
        "position": [x, y, z],
        "rotation_degrees": rotation_degrees,
        "scale": scale,
        "metadata": {
            "library_id": "drawing_assets",
            "product": asset.get("product"),
            "variant": asset.get("variant"),
            "category": asset.get("category"),
            "dimensions_mm": asset.get("dimensions_mm"),
            "drawing_roles": asset.get("drawing_roles", []),
            "lod": asset.get("lod"),
            "warehouse_url": asset.get("warehouse_url"),
            "match_status": asset.get("match_status"),
            "sha256": asset.get("sha256"),
        },
    }).encode("utf-8")

    try:
        return _send_and_receive(payload, timeout=90.0)
    except socket.timeout:
        return json.dumps({"status": "error", "requires_reconciliation": True,
            "message": "Rhino drawing-asset import timed out; inspect the model before retrying."})
    except ConnectionRefusedError:
        return json.dumps({
            "status": "error",
            "message": "Rhino bridge is unavailable. Start RhinoAlmondBridge first.",
        })
    except Exception as exc:
        return json.dumps({
            "status": "error",
            "message": f"Drawing asset placement failed: {exc}",
        })


@mcp.tool()
def apply_drawing_style(recipe_id: str = "technical_axon_v1") -> str:
    """
    Creates or updates the Rhino layer hierarchy, plot weights, colours, and
    linetypes defined by an audited drawing recipe.
    """
    recipe = drawing_recipe_indexer.get(recipe_id)
    if not recipe:
        return json.dumps({
            "status": "error",
            "message": f"Unknown drawing recipe_id: {recipe_id}",
        })
    payload = json.dumps({
        "type": "apply_drawing_style",
        "recipe_id": recipe_id,
        "layers": recipe.get("layers", []),
    }).encode("utf-8")
    try:
        return _send_and_receive(payload, timeout=60.0)
    except socket.timeout:
        return json.dumps({"status": "error", "message": "Applying drawing style timed out."})
    except ConnectionRefusedError:
        return json.dumps({
            "status": "error",
            "message": "Rhino bridge is unavailable. Start RhinoAlmondBridge first.",
        })
    except Exception as exc:
        return json.dumps({
            "status": "error",
            "message": f"Drawing style application failed: {exc}",
        })


@mcp.tool()
def import_drawing_hatch_patterns(asset_id: str) -> str:
    """
    Imports the AutoCAD-style .pat hatch definitions of an indexed drawing
    asset into the active Rhino document's hatch pattern table.

    The tool accepts only .pat files resolved from the controlled
    asset/drawing/DrawingAssetfiles manifest, mirroring the placement tools' security
    boundary.
    """
    asset = drawing_asset_indexer.get(asset_id)
    if not asset:
        return json.dumps({
            "status": "error",
            "message": f"Unknown drawing asset_id: {asset_id}",
        })
    if not asset.get("file_available"):
        return json.dumps({
            "status": "error",
            "message": f"Drawing asset file is missing for {asset_id}.",
        })
    resolved = asset["_resolved_file"]
    if not resolved.lower().endswith(".pat"):
        return json.dumps({
            "status": "error",
            "message": f"Asset {asset_id} is not a .pat hatch definition file.",
        })
    payload = json.dumps({
        "type": "import_hatch_patterns",
        "file_path": resolved,
    }).encode("utf-8")
    try:
        return _send_and_receive(payload, timeout=60.0)
    except socket.timeout:
        return json.dumps({"status": "error", "message": "Hatch pattern import timed out."})
    except ConnectionRefusedError:
        return json.dumps({
            "status": "error",
            "message": "Rhino bridge is unavailable. Start RhinoAlmondBridge first.",
        })
    except Exception as exc:
        return json.dumps({
            "status": "error",
            "message": f"Hatch pattern import failed: {exc}",
        })


@mcp.tool()
def list_diagram_assets(category: str = "", limit: int = 20, offset: int = 0) -> str:
    """Lists available vector and CAD diagram assets (people, trees, symbols)."""
    page = retrieval_store.search_assets(
        library_id="diagram_assets",
        category=category,
        limit=limit,
        offset=offset,
    )
    return json.dumps({
        "library_id": "diagram_assets",
        "purpose": "2D vector diagramming and line-art",
        **page,
    })


@mcp.tool()
def search_diagram_assets(
    query: str = "",
    category: str = "",
    max_width_mm: float = 0,
    max_depth_mm: float = 0,
    max_height_mm: float = 0,
    limit: int = 10,
    offset: int = 0,
) -> str:
    """Searches the diagram asset library."""
    return json.dumps(retrieval_store.search_assets(
        query=query,
        library_id="diagram_assets",
        category=category,
        max_width_mm=max_width_mm,
        max_depth_mm=max_depth_mm,
        max_height_mm=max_height_mm,
        limit=limit,
        offset=offset,
    ))


@mcp.tool()
def get_diagram_asset(asset_id: str) -> str:
    """Returns one diagram asset's metadata."""
    asset = retrieval_store.get_asset(asset_id, library_id="diagram_assets")
    if not asset:
        return json.dumps({"status": "error", "message": f"Unknown diagram asset_id: {asset_id}"})
    return json.dumps({"status": "success", "asset": asset})


@mcp.tool()
def place_diagram_asset(
    asset_id: str,
    x: float = 0,
    y: float = 0,
    z: float = 0,
    rotation_degrees: float = 0,
    scale: float = 1,
) -> str:
    """Places an indexed diagram asset (SVG, DWG, DXF)."""
    asset = diagram_asset_indexer.get(asset_id)
    if not asset:
        return json.dumps({"status": "error", "message": f"Unknown diagram asset_id: {asset_id}"})
    if not asset.get("file_available"):
        return json.dumps({"status": "error", "message": f"Diagram asset file is missing for {asset_id}."})
        
    payload = json.dumps({
        "type": "place_drawing_asset",
        "asset_id": asset_id,
        "file_path": asset["_resolved_file"],
        "name": f"{asset.get('product', '')} {asset.get('variant', '')}".strip(),
        "position": [x, y, z],
        "rotation_degrees": rotation_degrees,
        "scale": scale,
        "metadata": {
            "library_id": "diagram_assets",
            "product": asset.get("product"),
            "variant": asset.get("variant"),
            "category": asset.get("category"),
            "dimensions_mm": asset.get("dimensions_mm"),
            "drawing_roles": asset.get("drawing_roles", []),
            "lod": asset.get("lod"),
        },
    }).encode("utf-8")

    try:
        return _send_and_receive(payload, timeout=90.0)
    except socket.timeout:
        return json.dumps({"status": "error", "message": "Rhino diagram import timed out."})
    except Exception as exc:
        return json.dumps({"status": "error", "message": f"Diagram asset placement failed: {exc}"})














@mcp.tool()
def validate_structure(
    guids: list[str],
    structure_type: str = "beam",
    load_kn: float = 10.0,
    material: str = "Steel",
    engine: str = "auto",
    fixed_supports: bool = True,
    self_weight: bool = True,
    span_m: float | None = None,
    asset_loads: bool = False,
    scene_id: str = "",
    floor_load_kn_m2: float = 0.0,
    floor_dead_kn_m2: float = 0.0,
    design_basis: str = "en1990",
    uls_combination: str | None = None,
    connections: str = "rigid",
    stability: str = "auto",
    design_code: str = "eurocode",
    detail: bool = False,
    fabrication: str = "cold_formed",
) -> str:
    """
    Validates AI-generated geometry with a structural analysis.
    Call this AFTER execute_rhino_script to verify the generated structure is buildable.

    engine="auto" (default) analyses line models (beams, columns, trusses, frames) with
    Almond's built-in 3D frame solver: analysis_method "native", confidence "high",
    no Karamba install needed. It is a linear-elastic first-order frame analysis with
    EN 1993-1-1 member checks (elastic moduli; flexural buckling with L_cr = member
    length; no lateral-torsional buckling), benchmarked against closed-form results
    and live Karamba runs. Models with shells, and shell/gridshell/membrane structure
    types, go to Karamba. engine="karamba" forces the Karamba route, which tries three
    pathways in strict order of confidence and always tells you which one ran:
        analysis_method "api"        — direct Karamba 3.1 API solve, confidence "high"
        analysis_method "template"   — audited capsule GHX template,  confidence "medium"
        analysis_method "rule_based" — heuristic span/slenderness rules, confidence "low"
    The verdict string names the method (e.g. "[RULE-BASED ESTIMATE, LOW CONFIDENCE] ...").
    Treat rule_based/low results as estimates, NOT finite element analysis, and say so
    when reporting to the user.

    If the structure FAILS, modify the design (add supports, increase member size,
    change material) and call execute_rhino_script + validate_structure again.
    When worst_member_guids is present, edit only those offending members instead
    of regenerating everything. Iterate up to 3 times before reporting the best attempt.

    Args:
        guids: List of Rhino object GUID strings from execute_rhino_script output.
        structure_type: Analysis template to use. Options:
            "beam"       — simple beam bending/deflection
            "truss"      — axial force/buckling analysis
            "shell"      — shell stress/displacement
            "frame"      — moment/shear frame analysis
            "canopy"     — cantilevered canopy
            "gridshell"  — large deformation gridshell
            "membrane"   — form-finding membrane
            "highrise"   — high-rise structural systems
        load_kn: Applied load in kN (default 10.0).
        material: Material type: "Steel", "S355", "Concrete", "Wood", "Aluminium" (default "Steel").
        engine: "auto" | "native" | "karamba" (see above).
        fixed_supports: True = fully fixed supports, False = pinned (rotations free).
        self_weight: include member self weight.
        span_m: structural span in meters for the L/250 limit when members are split at
            every node (e.g. a 6.2 m joist drawn as two 3.1 m segments). Native engine only.
        asset_loads: add the gravity loads of placed library assets (estimated self weight
            plus in-use contents/occupants from each asset's load entry, e.g. a filled
            bathtub) where they stand on (or hang from) the frame. Placements come from
            Rhino objects tagged with an Almond asset id, or from the scene ledger when
            scene_id is given. Native engine only; the result's "asset_loads" lists every
            placement with its load and carrying members, or why it was not applied.
        scene_id: scene ledger to read placements from (default: tagged Rhino objects).
        floor_load_kn_m2: imposed floor load in kN/m2 (e.g. 2.0 for homes, EN 1991-1-1
            category A) on every bay enclosed by beams on a level; the beams take it by the
            45-degree rule (two-way, one-way above 2:1). Native engine only. A code floor load
            already covers movable furniture and people: combine it with asset_loads only for
            heavy specific items, and set load_kn to 0 to avoid double counting.
        floor_dead_kn_m2: superimposed dead load in kN/m2 (floor build-up, finishes) on the
            same bays.
        design_basis: "en1990" (default): deflection at SLS characteristic (G + Q), member
            checks at ULS 1.35 G + 1.5 Q. G = self weight, floor build-up and the weight of
            placed items; Q = load_kn, the occupancy floor load, contents and occupants.
            "unfactored" checks both at G + Q (the Karamba route's basis). Native engine.
        uls_combination: "6.10" or "6.10ab" (the worse of 6.10a and 6.10b per member). Default:
            the design code's choice (Eurocode profile: 6.10). A profile that prescribes one
            expression overrides the request (with a warning).
        design_code: design code profile for the numbers a code or National Annex sets
            (gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, deflection limit): "eurocode"
            (default, EN recommended values), any profile from list_design_codes, or "off"
            (unfactored G + Q, no partial factors; same as design_basis="unfactored").
            Results carry "design_code" with the values used and any unverified ones.
        fabrication: hollow steel sections (CHS/RHS) are "cold_formed" (default, EN 10219,
            buckling curve c) or "hot_finished" (EN 10210, curve a; a0 for S460). The difference
            is up to about 23 % in buckling resistance; use hot_finished only when specified.
        detail: native engine only. Adds "members" (per member: role, length, section, ULS design
            forces N/V/M/T, governing combination and check, slenderness, chi, stress,
            utilization, SLS deflection and span/deflection ratio, pinned ends) and "supports"
            (reactions Fx..Mz at SLS and each ULS combination). Off by default to keep replies short.
        connections: "rigid" (default: every joint transmits moment) or "simple": beams are
            pinned (major-axis bending released) and braces pinned in both axes where they
            stop - not where another member carries on in line - while columns stay
            continuous. Typical bolted steel and timber framing is closer to "simple"; rigid
            joints can flatter beam deflection. A curve's user text almond:release = "pinned" |
            "pinned_start" | "pinned_end" | "rigid" overrides either mode. Native engine.
        stability: "auto" (default): elastic critical load factor alpha_cr for every ULS
            combination (EN 1993-1-1 5.2.1) and sway imperfections phi = 1/200 x alpha_h x alpha_m
            (5.3.2) in +/-x and +/-y; alpha_cr < 10 runs a second-order (P-Delta) ULS analysis,
            alpha_cr <= 1 fails as unstable. "off": first-order without imperfections.
    Prefer calling get_construction_guidance BEFORE generating the geometry:
    pick a real construction system and size members from its depth/spacing
    rules. This tool cross-checks the analyzed span against that same library
    and appends a "construction_check" object (matching_systems with
    fits_span and suggested member depths, plus warnings when the span falls
    outside every curated system's range for this structure_type/material).

    Returns:
        JSON from the bridge plus the construction_check. Top-level fields: status
        ("pass"|"fail"|"error"), passed (bool), verdict (text), suggestions,
        confidence ("high"|"medium"|"low"), warnings, and worst_member_guids
        (up to 5 Rhino GUIDs of the most over-utilized members — edit those
        first). The results object carries the numbers: max_deflection_mm,
        deflection_limit_mm, utilization_ratio, max_stress_mpa, yield_stress_mpa,
        span_m, analysis_method ("native"|"api"|"template"|"rule_based"), reactions_kn
        (total vertical reaction, api path only), and per_element_utilization —
        a list of {source_guids, utilization} entries (utilization 1.0 = at
        capacity) keyed back to the Rhino objects that produced each element.
    """
    engine = (engine or "auto").lower()
    if engine not in ("auto", "native", "karamba"):
        return json.dumps({"status": "error", "message": "engine must be 'auto', 'native' or 'karamba'."})
    request = {
        "type": "validate",
        "guids": guids,
        "structure_type": structure_type,
        "load_kn": load_kn,
        "material": material,
    }
    if not fixed_supports:
        request["fixed_rotations"] = False
    if not self_weight:
        request["self_weight"] = False

    result, note = None, None
    spec = None
    floor, err = _floor_spec(floor_load_kn_m2, floor_dead_kn_m2, engine)
    if err:
        return json.dumps({"status": "error", "message": err})
    try:
        native_structure.combinations(design_basis, uls_combination, design_code)
        if (connections or "rigid").lower() not in native_structure.CONNECTIONS:
            raise ValueError("connections must be 'rigid' or 'simple'.")
        if (stability or "auto").lower() not in ("auto", "off"):
            raise ValueError("stability must be 'auto' or 'off'.")
    except ValueError as e:
        return json.dumps({"status": "error", "message": str(e)})
    if asset_loads:
        if engine == "karamba":
            return json.dumps({"status": "error", "message": "asset_loads needs the native engine (engine='auto' or 'native')."})
        spec, err = _asset_load_spec(scene_id)
        if err:
            return json.dumps({"status": "error", "message": err})
    if engine == "native" or (engine == "auto" and structure_type.lower() not in KARAMBA_ONLY_TYPES):
        result, note = _native_validation(guids, structure_type, load_kn, material, fixed_supports,
                                          self_weight, span_m, required=engine == "native", asset_spec=spec,
                                          floor_spec=floor, design=(design_basis, uls_combination, design_code),
                                          connections=connections, stability=stability, detail=detail,
                                          fabrication=fabrication)
        if isinstance(result, str):          # hard error (explicit native request, or no bridge)
            return result
    if result is None:
        try:
            response = _send_and_receive(json.dumps(request).encode('utf-8'), timeout=60.0)
        except socket.timeout:
            return json.dumps({"status": "error", "message": "Structural validation timed out (>60s)."})
        except ConnectionRefusedError:
            return json.dumps({"status": "error", "message": "Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?"})
        except Exception as e:
            return json.dumps({"status": "error", "message": f"Bridge error: {e}"})
        try:
            result = json.loads(response)
        except Exception:
            return response
        if note and isinstance(result, dict):
            result.setdefault("warnings", []).append(note)
        if (spec or floor) and isinstance(result, dict):
            result.setdefault("warnings", []).append(
                "Asset and floor loads were not applied: the Karamba route does not take them.")
        if note and isinstance(result, dict) and (design_basis or "").lower() == "en1990":   # fell back from native
            result.setdefault("warnings", []).append(
                "The Karamba route checks unfactored loads; EN 1990 combinations apply to the native engine only.")

    # Attach the constructibility cross-check (curated construction-system
    # span/depth guidance), then persist the run in the state DB so
    # export_structural_report can render an auditable history. Neither step
    # may ever break validation itself.
    try:
        if isinstance(result, dict) and result.get("status") in ("pass", "fail"):
            span = None
            results_block = result.get("results")
            if isinstance(results_block, dict):
                span = results_block.get("span_m")
            try:
                check = construction_library.assess_span(structure_type, material, span)
                result["construction_check"] = check
                if check.get("warnings"):
                    result.setdefault("warnings", [])
                    result["warnings"].extend(check["warnings"])
            except Exception:
                pass
            retrieval_store.record_validation_run(request, result, guids)
    except Exception:
        pass
    return json.dumps(result)


KARAMBA_ONLY_TYPES = ("shell", "gridshell", "membrane")


def _structural_loads_path() -> Path:
    return Path(GENERATED_LIBRARY_DIR) / "structural-loads.json"


def _asset_load_spec(scene_id: str = ""):
    """Placements + load table + catalogue facts for asset loads: (spec, None) or (None, error)."""
    try:
        table = asset_loads.LoadTable(_structural_loads_path())
    except Exception as e:
        return None, f"The asset load table is unavailable ({e})."
    if scene_id:
        try:
            placements = asset_loads.placements_from_scene(retrieval_store.scene_instances(scene_id))
        except KeyError as e:
            return None, str(e).strip("'")
    else:
        try:
            reply = json.loads(_send_and_receive(json.dumps({"type": "asset_placements"}).encode('utf-8'), timeout=60.0))
        except ConnectionRefusedError:
            return None, "Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?"
        except Exception as e:
            return None, f"Could not read asset placements from Rhino ({e})."
        if not isinstance(reply, dict) or reply.get("status") != "ok":
            return None, "This bridge version cannot export asset placements (update almondbridge)."
        placements = reply.get("placements") or []
    catalogue = structure_study.asset_catalogue(placements, generated_asset_indexer.get)
    return {"placements": placements, "table": table, "catalogue": catalogue}, None


def _floor_spec(imposed, dead, engine):
    """(spec | None, error | None) for floor area loads."""
    imposed, dead = float(imposed or 0.0), float(dead or 0.0)
    if imposed < 0 or dead < 0 or not (math.isfinite(imposed) and math.isfinite(dead)):
        return None, "Floor loads must be finite and non-negative (kN/m2)."
    if not imposed and not dead:
        return None, None
    if engine == "karamba":
        return None, "Floor loads need the native engine (engine='auto' or 'native')."
    return {"imposed": imposed, "dead": dead}, None


def _native_validation(guids, structure_type, load_kn, material, fixed_supports, self_weight, span_m, required,
                       asset_spec=None, floor_spec=None, design=("en1990", None, "eurocode"), connections="rigid",
                       stability="auto", detail=False, fabrication="cold_formed"):
    """Native frame check on the bridge's exported line model.

    Returns (result_dict, None) when it ran, (None, note) to fall back to the Karamba
    route with a note, or (json_error_string, None) when it must stop (explicit native
    request that cannot run, or no bridge)."""
    def unavailable(msg):
        if required:
            return json.dumps({"status": "error", "message": msg}), None
        return None, msg + " Fell back to the Karamba route."
    try:
        reply = json.loads(_send_and_receive(
            json.dumps({"type": "structure_model", "guids": guids}).encode('utf-8'), timeout=60.0))
    except socket.timeout:
        return unavailable("Exporting the structural model timed out.")
    except ConnectionRefusedError:
        return json.dumps({"status": "error", "message": "Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?"}), None
    except Exception as e:
        return unavailable(f"The bridge could not export a structural model ({e}).")
    if not isinstance(reply, dict) or reply.get("status") != "ok" or "members" not in reply:
        return unavailable("This bridge version cannot export structural models (update almondbridge).")
    if reply.get("shells"):
        return unavailable(f"The model contains {reply['shells']} shell element(s), which the native frame solver does not analyse.")
    if not reply["members"]:
        return unavailable("No line members found for the given GUIDs.")
    try:
        result = native_structure.validate(reply, structure_type.lower(), load_kn, material,
                                           fixed_supports=fixed_supports, self_weight=self_weight, span_m=span_m,
                                           asset_loads=asset_spec, floor_loads=floor_spec,
                                           design_basis=design[0], uls=design[1], connections=connections,
                                           stability=stability, design_code=design[2], detail=detail,
                                           fabrication=fabrication)
    except ValueError as e:
        return json.dumps({"status": "error", "message": str(e)}), None
    return result, None


@mcp.tool()
def list_design_codes() -> str:
    """
    Lists the design code profiles validate_structure / visualize_structure accept as design_code.

    A profile holds the numbers a design code or National Annex sets (load factors gamma_G,
    gamma_Q, psi_0, xi; the ULS expression; material factors gamma_M0, gamma_M1; the deflection
    limit; suggested imposed floor loads), each with its source clause and a verified flag.
    "eurocode" (EN recommended values) is built in and the default; "off" is unfactored mechanics.
    Practices add National Annex profiles as JSON files in user_dir (see docs/structure/design-codes.md).
    Unverified values are allowed but flagged in every result that uses them.

    Returns JSON: default, profiles [{id, name, basis, origin, verified, unverified,
    uls_expression, uls_default, deflection_limit_ratio, imposed_floor_kn_m2}], problems
    (files that failed validation), user_dir.
    """
    return json.dumps(design_codes.listing())


@mcp.tool()
def visualize_structure(
    guids: list[str] | None = None,
    load_kn: float = 10.0,
    material: str = "Steel",
    beam_diameter_mm: float | None = None,
    beam_wall_mm: float | None = None,
    self_weight: bool = True,
    fixed_supports: bool = True,
    deflection_limit_ratio: float | None = None,
    span_m: float | None = None,
    color_by: str = "displacement",
    scale: float | None = None,
    reveal: float = 1.0,
    reanalyze: bool = True,
    physics: bool = True,
    display_guids: list[str] | None = None,
    title: str = "",
    clear: bool = False,
    engine: str = "auto",
    asset_loads: bool = False,
    scene_id: str = "",
    floor_load_kn_m2: float = 0.0,
    floor_dead_kn_m2: float = 0.0,
    design_basis: str = "en1990",
    uls_combination: str | None = None,
    connections: str = "rigid",
    stability: str = "auto",
    design_code: str = "eurocode",
    fabrication: str = "cold_formed",
    view: str = "deflection",
) -> str:
    """
    Run a live structural analysis on a line model and SHOW it in every Rhino viewport:
    the undeformed wireframe, the exaggerated deformed shape coloured blue -> red by
    displacement (or by utilization), supports, load arrows and a legend panel with
    max deflection, the L/limit check and PASS/FAIL. Nothing is baked into the document.

    Use it to make structural behaviour visible while designing: model the structural
    axes as curves, include Rhino point objects at the supports, call this tool, then
    fix the members it shows in red (add a column, shorten a cantilever, upsize the
    section via beam_diameter_mm) and call it again. validate_structure gives the
    auditable verdict; this tool is the visual, iterative view of the same solve.

    Args:
        guids: Curve GUIDs of the structural axes plus point GUIDs marking supports
            (see fixed_supports). Without points, the lowest nodes are supported.
        load_kn: Total imposed load in kN, shared equally by the free nodes (-Z).
        material: "Steel", "S355", "Concrete", "Wood", "Aluminium".
        beam_diameter_mm, beam_wall_mm: circular hollow section for every member
            (default: inferred / CHS 114.3x4).
        self_weight: include gravity.
        fixed_supports: True = fully fixed supports, False = pinned (rotations free).
        deflection_limit_ratio: span/ratio limit, e.g. 250 for L/250. Default: the design code's
            limit (Eurocode profile: 250).
        span_m: reference span in meters for the limit (default: longest member).
            Set it when members are split at every node, e.g. a 6.2 m joist drawn
            as two 3.1 m segments.
        color_by: "displacement" or "utilization".
        scale: deformation exaggeration; omit for automatic (~6% of span).
        reveal: 0..1 fraction of members drawn (for staged construction playback).
        reanalyze: False re-uses the last solve and only changes the display
            (scale / color_by / reveal / physics / title) - cheap enough to animate.
        physics: False draws the same members as plain geometry with no analysis
            overlay ("physics off"), for before/after comparisons.
        display_guids: draw only these members (e.g. one frame line for a section
            view); the analysis still covers every member in guids.
        title: legend title.
        clear: remove the overlay.
        engine: "auto" (default: Almond's native frame solver, no Karamba needed; Karamba
            when the selection has shells or the bridge cannot export a model),
            "native" or "karamba".
        asset_loads, scene_id: add the loads of placed library assets (native engine), as in
            validate_structure; loaded points are drawn with load arrows.
        floor_load_kn_m2, floor_dead_kn_m2: floor area loads on every enclosed bay, as in
            validate_structure.
        design_basis, uls_combination, design_code: as in validate_structure; the overlay draws
            the SLS deflected shape coloured by the ULS utilization envelope.
        connections: "rigid" or "simple", as in validate_structure; pinned ends are drawn
            as small circles.
        stability: "auto" or "off", as in validate_structure.
        view: "deflection" (default) or "buckling": draw the first buckling mode of the
            governing ULS combination with its alpha_cr (STABLE >= 10, SWAY-SENSITIVE 1-10,
            UNSTABLE <= 1) instead of the deflected shape.

    Returns JSON: status ("pass"|"fail"|"error"|"cleared"), max_displacement_mm,
    deflection_limit_mm, span_m, max_utilization, scale, per-element
    {source_guids, max_displacement_mm, utilization}, warnings.
    The native engine reports analysis_method "native"; engine="karamba" needs
    Karamba3D 3.1 (the trial caps models at 20 beam elements).
    """
    if not clear and not guids:
        return json.dumps({"status": "error", "message": "Provide the curve (and support point) GUIDs to analyse."})
    if color_by not in ("displacement", "utilization"):
        return json.dumps({"status": "error", "message": "color_by must be 'displacement' or 'utilization'."})
    engine = (engine or "auto").lower()
    if engine not in ("auto", "native", "karamba"):
        return json.dumps({"status": "error", "message": "engine must be 'auto', 'native' or 'karamba'."})
    if deflection_limit_ratio is None:
        try:
            deflection_limit_ratio = native_structure.design_profile(design_basis, design_code).deflection_limit_ratio
        except ValueError as e:
            return json.dumps({"status": "error", "message": str(e)})
    request = {
        "type": "structure_view",
        "guids": guids or [],
        "load_kn": load_kn,
        "material": material,
        "self_weight": self_weight,
        "fixed_rotations": fixed_supports,
        "deflection_limit_ratio": deflection_limit_ratio,
        "color_by": color_by,
        "reveal": max(0.0, min(1.0, reveal)),
        "reanalyze": reanalyze,
        "physics": physics,
        "clear": clear,
    }
    if beam_diameter_mm is not None:
        request["beam_diameter_mm"] = beam_diameter_mm
        request["beam_wall_mm"] = beam_wall_mm if beam_wall_mm is not None else beam_diameter_mm / 20.0
    if scale is not None:
        request["scale"] = scale
    if span_m is not None:
        request["span_m"] = span_m
    if display_guids:
        request["display_guids"] = display_guids
    if title:
        request["title"] = title
    global _VIEW_ENGINE
    note = None
    spec = None
    floor = None
    if not clear and reanalyze:
        floor, err = _floor_spec(floor_load_kn_m2, floor_dead_kn_m2, engine)
        if err:
            return json.dumps({"status": "error", "message": err})
        try:
            native_structure.combinations(design_basis, uls_combination, design_code)
            if (connections or "rigid").lower() not in native_structure.CONNECTIONS:
                raise ValueError("connections must be 'rigid' or 'simple'.")
            if (stability or "auto").lower() not in ("auto", "off"):
                raise ValueError("stability must be 'auto' or 'off'.")
            if (view or "deflection").lower() not in ("deflection", "buckling"):
                raise ValueError("view must be 'deflection' or 'buckling'.")
            if (view or "").lower() == "buckling" and engine == "karamba":
                raise ValueError("view='buckling' needs the native engine.")
        except ValueError as e:
            return json.dumps({"status": "error", "message": str(e)})
    if asset_loads and not clear and reanalyze:
        if engine == "karamba":
            return json.dumps({"status": "error", "message": "asset_loads needs the native engine (engine='auto' or 'native')."})
        spec, err = _asset_load_spec(scene_id)
        if err:
            return json.dumps({"status": "error", "message": err})
    if not clear and engine != "karamba" and not (not reanalyze and _VIEW_ENGINE == "api"):
        if not reanalyze and _VIEW_ENGINE == "native":
            draw = {k: v for k, v in request.items() if k not in ("guids", "reanalyze", "clear")}
            draw["type"] = "structure_draw"
            return _bridge_call(draw, 30.0)
        reply, note = _native_view(request, guids, required=engine == "native", asset_spec=spec, floor_spec=floor,
                                   design=(design_basis, uls_combination, design_code), connections=connections,
                                   stability=stability, view=view, fabrication=fabrication)
        if reply is not None:
            return reply
    out = _bridge_call(request, 90.0)
    if clear:
        _VIEW_ENGINE = None
    elif reanalyze:
        _VIEW_ENGINE = "api"
    if note:
        try:
            parsed = json.loads(out)
            parsed.setdefault("warnings", []).append(note)
            out = json.dumps(parsed)
        except Exception:
            pass
    return out


_VIEW_ENGINE: str | None = None   # which engine drew the current overlay ("native" | "api")


def _bridge_call(message: dict, timeout: float) -> str:
    try:
        return _send_and_receive(json.dumps(message).encode('utf-8'), timeout=timeout)
    except socket.timeout:
        return json.dumps({"status": "error", "message": f"Structure view timed out (>{timeout:.0f}s)."})
    except ConnectionRefusedError:
        return json.dumps({"status": "error", "message": "Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?"})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Bridge error: {e}"})


def _native_view(request: dict, guids, required: bool, asset_spec=None, floor_spec=None, design=("en1990", None, "eurocode"),
                 connections="rigid", stability="auto", view="deflection", fabrication="cold_formed"):
    """Solve natively and draw through the bridge's structure_draw overlay.

    Returns (reply_json, None) when it ran or must stop, (None, note) to fall back to Karamba."""
    global _VIEW_ENGINE

    def unavailable(msg):
        if required:
            return json.dumps({"status": "error", "message": msg}), None
        return None, msg + " Fell back to the Karamba route."
    try:
        model = json.loads(_send_and_receive(
            json.dumps({"type": "structure_model", "guids": guids}).encode('utf-8'), timeout=60.0))
    except ConnectionRefusedError:
        return json.dumps({"status": "error", "message": "Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?"}), None
    except Exception as e:
        return unavailable(f"The bridge could not export a structural model ({e}).")
    if not isinstance(model, dict) or model.get("status") != "ok" or "members" not in model:
        return unavailable("This bridge version cannot export structural models (update almondbridge).")
    if model.get("shells"):
        return unavailable(f"The model contains {model['shells']} shell element(s), which the native frame solver does not analyse.")
    if not model["members"]:
        return json.dumps({"status": "error", "message": "No curve members found for the given GUIDs."}), None
    try:
        result, span = native_structure.view_result(
            model, request["load_kn"], request["material"], fixed_supports=request["fixed_rotations"],
            self_weight=request["self_weight"], diameter_mm=request.get("beam_diameter_mm"),
            wall_mm=request.get("beam_wall_mm"), span_m=request.get("span_m"), asset_loads=asset_spec,
            floor_loads=floor_spec, design_basis=design[0], uls=design[1], connections=connections,
            stability=stability, view=view, design_code=design[2], fabrication=fabrication)
    except native_structure.InstabilityError as e:
        return json.dumps({"status": "fail", "analysis_method": "native", "message": str(e),
                           "stability": e.report, "hint": "view='buckling' draws the buckling mode."}), None
    except native_structure.fs.MechanismError as e:
        return json.dumps({"status": "fail", "analysis_method": "native", "message": str(e),
                           "mechanism_nodes": len(e.nodes)}), None
    except ValueError as e:
        return json.dumps({"status": "error", "message": str(e)}), None
    draw, reports = structure_study.draw_message(request, result, span)
    report, floor_report, combos = reports["asset_loads"], reports["floor_loads"], reports["combinations"]
    conn_report, stab_report, buckling = reports["connections"], reports["stability"], reports["buckling"]
    code_report = reports["design_code"]
    out = _bridge_call(draw, 60.0)
    try:
        parsed = json.loads(out)
    except Exception:
        return out, None
    if isinstance(parsed, dict) and parsed.get("status") in ("pass", "fail"):
        _VIEW_ENGINE = "native"
        parsed["warnings"] = result["warnings"]
        if report is not None:
            parsed["asset_loads"] = report
        if floor_report is not None:
            parsed["floor_loads"] = floor_report
        if combos:
            parsed["combinations"] = combos
        if conn_report:
            parsed["connections"] = conn_report
        if stab_report:
            parsed["stability"] = stab_report
        if code_report:
            parsed["design_code"] = code_report
        if reports.get("indicative") and parsed.get("status") == "pass":
            parsed["status"] = "indicative"                 # the bridge judged utilization; there is no capacity check
            parsed["passed"] = None
        if buckling:
            # a mode shape has no magnitude: the bridge's deflection-limit verdict is meaningless here
            parsed["buckling"] = buckling
            parsed["passed"] = buckling["alpha_cr"] > 1.0
            parsed["status"] = "pass" if parsed["passed"] else "fail"
            parsed.pop("max_displacement_mm", None)
        parsed["nodes"] = len({tuple(p) for e in result["elements"] for p in (e["start_m"], e["end_m"])})
    elif not required:
        # a bridge without structure_draw: fall back to the Karamba overlay
        return None, "This bridge version cannot draw native results (update almondbridge)."
    return json.dumps(parsed), None


def _render_validation_report(runs: list[dict]) -> str:
    """Markdown report of persisted validate_structure runs, newest first."""
    from datetime import datetime, timezone

    lines = [
        "# Structural validation report",
        "",
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
        f"by almond-mcp. {len(runs)} run(s), newest first.",
        "",
        "## How a run works",
        "",
        "`validate_structure(guids, structure_type, load_kn, material)` sends the",
        "referenced Rhino geometry to the bridge, which extracts member axes and",
        "tries three analysis pathways in strict order of confidence:",
        "",
        "1. **api** — direct Karamba 3.1 solve (real FEA), confidence *high*;",
        "2. **template** — audited capsule GHX definition, confidence *medium*;",
        "3. **rule_based** — span/slenderness heuristics (UDL `w = load/span`,",
        "   `5wL^4/384EI`), confidence *low*. An estimate, not FEA.",
        "",
        "Pass criteria: max deflection within **L/250** of the detected span, and",
        "material utilization below yield (default S235 steel, fy = 235 MPa).",
        "The applied load defaults to **10 kN** unless load_kn is given.",
        "",
        "## Runs",
        "",
        "| # | when (UTC) | type | method | confidence | span m | defl mm | limit mm | util | reactions kN | members | result |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for run in runs:
        lines.append(
            f"| {run['id']} | {run['ran_at'][:16].replace('T', ' ')} "
            f"| {run['structure_type']} | {run['analysis_method']} "
            f"| {run['confidence']} | {run['span_m']:.1f} "
            f"| {run['max_deflection_mm']:.2f} | {run['deflection_limit_mm']:.1f} "
            f"| {run['utilization_ratio']:.2f} | {run['reactions_kn']:.2f} "
            f"| {run['member_count']} | {'PASS' if run['passed'] else 'FAIL'} |"
        )
    lines.append("")
    lines.append("## Run details")
    for run in runs:
        lines += [
            "",
            f"### Run {run['id']} — {run['structure_type']}, "
            f"{run['analysis_method']} ({'PASS' if run['passed'] else 'FAIL'})",
            "",
            f"- input: {run['member_count']} object(s), load {run['load_kn']:.1f} kN, "
            f"material {run['material']}",
            f"- verdict: {run['verdict']}",
        ]
        if run["warnings"]:
            lines.append("- warnings:")
            lines += [f"  - {w}" for w in run["warnings"]]
    lines += [
        "",
        "## Reading the numbers",
        "",
        "- Only **api** runs are finite element analysis; reactions_kn is",
        "  populated on the api path only and should equal the applied load",
        "  plus self-weight (equilibrium).",
        "- Known gaps in karambaCommon 3.1.60519 (issue #6): api-mode",
        "  max_deflection and per-element utilization may read 0.0 due to",
        "  signature drift — trust reactions and stability diagnostics;",
        "  cross-check deflection against the rule_based estimate.",
        "- rule_based results are labeled LOW CONFIDENCE for a reason: treat",
        "  them as sanity checks, not engineering.",
        "",
    ]
    return "\n".join(lines)


@mcp.tool()
def export_structural_report(path: str = "", limit: int = 50) -> str:
    """
    Renders the persisted validate_structure history to a Markdown report.

    Every successful validate_structure call is recorded in the local state
    database (inputs, analysis method, confidence, numbers, warnings). This
    tool writes them to a .md file, newest first, with an explanation of the
    analysis pathways and pass criteria.

    Args:
        path: Output file path. Default:
            <user data dir>/reports/structural-validation-<timestamp>.md
        limit: Maximum number of runs to include (default 50, max 500).
    Returns:
        JSON with the report path and run count.
    """
    from datetime import datetime, timezone

    try:
        runs = retrieval_store.list_validation_runs(limit=limit)
        if not runs:
            return json.dumps({
                "status": "error",
                "message": "No validation runs recorded yet - call validate_structure first.",
            })
        target = Path(path) if path else (
            paths.user_data_dir() / "reports" /
            f"structural-validation-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.md"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_render_validation_report(runs), encoding="utf-8")
        return json.dumps({
            "status": "success",
            "path": str(target),
            "runs": len(runs),
            "latest_method": runs[0]["analysis_method"],
        })
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})


def _restore_and_place_script(contract: dict, materials: dict[str, dict],
                              x_mm: float, y_mm: float, z_mm: float,
                              rotation_degrees: float, layer: str) -> str:
    """C# run after a GLB import: restore metadata, correct the colour drift,
    collapse duplicate materials, then place per the contract anchor."""
    lib_rows = []
    for material_id, material in materials.items():
        resolved = modeling_setup.recipe(material)
        # Reuse a recipe revision, not a color-shifted material from the imported GLB.
        revision = hashlib.sha256(json.dumps(resolved, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()[:12]
        resolved["name"] += f" ({revision})"
        values = [material_id, material["name"], material["category"], material["ue_material_slot"],
                  *material["base_color"], material["metallic"], material["roughness"], material["opacity"]]
        encoded = ", ".join(json.dumps(v, ensure_ascii=True) for v in values)
        encoded += ", " + modeling_setup.literal(resolved)
        for alias in dict.fromkeys((exchange.material_name(material_id), material["name"], resolved["name"])):
            lib_rows.append("{ " + json.dumps(alias, ensure_ascii=True) + ", new object[] { " + encoded + " } }")
    anchor = contract["spatial"].get("anchor", "bottom_center")
    # Library GLBs hold numeric millimetres, but Rhino's glTF import reads metres.
    convention = (contract.get("passport") or {}).get("coordinate_convention") or {}
    glb_scale = 0.001 if convention.get("glb_numeric_units") == "mm" else 1.0
    passport_stamp = ""
    if contract.get("passport"):
        # C# verbatim string, so quotes/backslashes in provenance stay data.
        encoded = json.dumps(contract["passport"], ensure_ascii=True).replace('"', '""')
        passport_stamp = f'attributes.SetUserString("almond:passport", @"{encoded}");'
    return f"""
using System;
using System.Collections.Generic;
using System.Linq;
using Rhino;
using Rhino.Geometry;
using Rhino.DocObjects;
using Rhino.Display;

public class Script
{{
    // material name -> {{ id, name, category, ue_slot, r, g, b, metallic, roughness, opacity }}
    static readonly Dictionary<string, object[]> Lib = new Dictionary<string, object[]>
    {{
        {",\n        ".join(lib_rows) if lib_rows else ""}
    }};

    public static List<Guid> Run(RhinoDoc doc)
    {{
        var imported = new List<RhinoObject>();
        foreach (string s in new[] {{ {", ".join('"%s"' % g for g in contract["_imported_guids"])} }})
        {{
            var o = doc.Objects.FindId(new Guid(s));
            if (o != null) imported.Add(o);
        }}
        if (imported.Count == 0) return new List<Guid>();

        // Resolve only imported objects through the shared MCP material implementation.
        var canonical = new Dictionary<string, int>();
        int deduped = 0;
        foreach (var obj in imported)
        {{
            var mat = obj.GetMaterial(true);
            if (mat == null || !Lib.TryGetValue(mat.Name, out var spec)) continue;
            string id = (string)spec[0];
            if (!canonical.ContainsKey(id))
            {{
                using var attributes = RhinoAlmondBridge.ModelingMaterials.CreateAttributes(
                    doc, (string)spec[10], attachMetadata: false, reuseLegacyMaterial: false);
                canonical[id] = attributes.MaterialIndex;
            }}
        }}
        int layerIndex = RhinoAlmondBridge.DocumentLayers.Ensure(doc, {json.dumps(layer, ensure_ascii=True)});

        // 3. re-attach the metadata glTF dropped, keyed off the surviving name
        int stamped = 0;
        foreach (var obj in imported)
        {{
            var attributes = obj.Attributes.Duplicate();
            var mat = obj.GetMaterial(true);
            string matName = mat != null ? mat.Name : "";
            if (matName.Length > 0 && Lib.ContainsKey(matName))
            {{
                var spec = Lib[matName];
                string id = (string)spec[0];
                if (attributes.MaterialIndex != canonical[id])
                {{
                    attributes.MaterialIndex = canonical[id];
                    deduped++;
                }}
                attributes.MaterialSource = ObjectMaterialSource.MaterialFromObject;
                attributes.SetUserString("almond:material_id", (string)spec[0]);
                attributes.ObjectColor = System.Drawing.Color.FromArgb((int)spec[4], (int)spec[5], (int)spec[6]);
                attributes.ColorSource = ObjectColorSource.ColorFromObject;
                stamped++;
            }}
            attributes.SetUserString("almond:asset_id", "{contract['asset_id']}");
            attributes.SetUserString("almond:source_app", "{contract.get('source_app', 'unknown')}");
            {passport_stamp}
            attributes.LayerIndex = layerIndex;
            if (!doc.Objects.ModifyAttributes(obj.Id, attributes, true)) throw new InvalidOperationException("Cannot restore imported attributes.");
        }}

        // 4. place per the contract anchor, in this document's units
        double toDoc = RhinoMath.UnitScale(UnitSystem.Millimeters, doc.ModelUnitSystem);
        var scale = Transform.Scale(Point3d.Origin, {glb_scale!r});
        var bb = BoundingBox.Empty;
        foreach (var o in imported) bb.Union(o.Geometry.GetBoundingBox(true));
        bb.Transform(scale);
        var anchorPt = new Point3d((bb.Min.X + bb.Max.X) / 2, (bb.Min.Y + bb.Max.Y) / 2,
            "{anchor}" == "center" ? (bb.Min.Z + bb.Max.Z) / 2 : bb.Min.Z);
        var target = new Point3d({x_mm} * toDoc, {y_mm} * toDoc, {z_mm} * toDoc);
        var xform = Transform.Translation(target - anchorPt);
        if (Math.Abs({rotation_degrees}) > 1e-9)
            xform = xform * Transform.Rotation(RhinoMath.ToRadians({rotation_degrees}), Vector3d.ZAxis, anchorPt);
        xform = xform * scale;
        foreach (var o in imported) doc.Objects.Transform(o.Id, xform, true);

        // 5. measure what actually landed, for the contract dimension check
        var after = BoundingBox.Empty;
        foreach (var o in imported)
        {{
            var refreshed = doc.Objects.FindId(o.Id);
            if (refreshed != null) after.Union(refreshed.Geometry.GetBoundingBox(true));
        }}
        double toMM = RhinoMath.UnitScale(doc.ModelUnitSystem, UnitSystem.Millimeters);
        RhinoApp.WriteLine(string.Format(
            "ALMOND_IMPORT stamped={{0}} deduped={{1}} w={{2:F1}} d={{3:F1}} h={{4:F1}}",
            stamped, deduped,
            (after.Max.X - after.Min.X) * toMM,
            (after.Max.Y - after.Min.Y) * toMM,
            (after.Max.Z - after.Min.Z) * toMM));
        System.IO.File.WriteAllText(
            System.IO.Path.Combine(System.IO.Path.GetTempPath(), "almond_import_report.json"),
            "{{\\"stamped\\":" + stamped + ",\\"deduped\\":" + deduped
            + ",\\"width\\":" + ((after.Max.X - after.Min.X) * toMM).ToString("F1")
            + ",\\"depth\\":" + ((after.Max.Y - after.Min.Y) * toMM).ToString("F1")
            + ",\\"height\\":" + ((after.Max.Z - after.Min.Z) * toMM).ToString("F1") + "}}");
        doc.Views.Redraw();
        return imported.Select(o => o.Id).ToList();
    }}
}}
"""


@mcp.tool()
def export_asset_contract(
    guids: list[str],
    asset_id: str,
    name: str = "",
    output_dir: str = "",
) -> str:
    """
    Exports Rhino objects as a portable Almond asset: a GLB plus an asset
    contract (.almond.json) carrying what the file cannot.

    The contract records real dimensions in mm, the anchor and support plane,
    clearances, and the Almond material_id of every object - so another
    application (Blender, Unreal, another Rhino) can restore full meaning
    even though glTF drops per-object metadata. Pair with
    import_asset_contract on the receiving side.

    Args:
        guids: Rhino object GUIDs to export (from execute_rhino_script).
        asset_id: Stable id, e.g. "canopy-pavilion-01" (letters, digits, . _ -).
        name: Human-readable name; defaults to asset_id.
        output_dir: Destination folder. Default: <user data dir>/exchange.
    Returns:
        JSON with the glb path, contract path, and recorded dimensions.
    """
    if not guids:
        return json.dumps({"status": "error", "message": "At least one GUID is required."})
    try:
        target_dir = Path(output_dir) if output_dir else paths.user_data_dir() / "exchange"
        glb_path, contract_path = exchange.contract_paths(target_dir, asset_id)
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})

    payload = json.dumps({
        "type": "export_glb",
        "guids": guids,
        "output_path": str(glb_path),
    }).encode("utf-8")
    try:
        result = json.loads(_send_and_receive(payload, timeout=90.0))
    except ConnectionRefusedError:
        return json.dumps({"status": "error", "message": "Rhino bridge is unavailable."})
    except Exception as exc:
        return json.dumps({"status": "error", "message": f"GLB export failed: {exc}"})
    if result.get("status") != "success":
        return json.dumps(result)

    bounds = result.get("bounds") or {}
    if not bounds:
        return json.dumps({"status": "error", "message": "Export returned no bounds."})
    # export_glb reports bounds in document units
    unit_scale = {"Millimeters": 1.0, "Centimeters": 10.0, "Meters": 1000.0,
                  "Inches": 25.4, "Feet": 304.8}.get(result.get("units", "Millimeters"), 1.0)
    bounds_mm = {
        "min": [float(v) * unit_scale for v in bounds["min"]],
        "max": [float(v) * unit_scale for v in bounds["max"]],
    }
    material_groups = _material_groups(guids)
    try:
        contract = exchange.build_contract(
            asset_id=asset_id,
            name=name or asset_id,
            glb_filename=glb_path.name,
            bounds_mm=bounds_mm,
            materials=material_groups,
            source_app="rhino",
            object_count=len(result.get("object_guids", guids)),
        )
    except ValueError as exc:
        return json.dumps({"status": "error", "message": str(exc)})
    contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
    return json.dumps({
        "status": "success",
        "asset_id": asset_id,
        "glb_path": str(glb_path),
        "contract_path": str(contract_path),
        "dimensions_mm": contract["dimensions_mm"],
        "materials": material_groups,
        "next_step": "Open this contract elsewhere with import_asset_contract, or "
                     "run get_blender_helper_script('import') to load it in Blender.",
    })


def _material_groups(guids: list[str]) -> list[dict]:
    """Resolve actual ByObject/ByLayer materials, including readable library names."""
    names = ", ".join("{ " + json.dumps(m["name"], ensure_ascii=True) + ", " + json.dumps(mid) + " }"
                      for mid, m in material_library.materials.items())
    script = """
using System;
using System.Collections.Generic;
using System.IO;
using Rhino;
public class Script
{
    public static object Run(RhinoDoc doc)
    {
        var names = new Dictionary<string, string> { %s };
        var rows = new List<string>();
        foreach (string s in new[] { %s })
        {
            var obj = doc.Objects.FindId(new Guid(s));
            if (obj == null) continue;
            var mat = obj.GetMaterial(true);
            string mid = mat == null ? null : mat.GetUserString("almond:material_id");
            string name = obj.GetRenderMaterial(true)?.Name ?? mat?.Name ?? "";
            if (string.IsNullOrEmpty(mid)) names.TryGetValue(name, out mid);
            if (string.IsNullOrEmpty(mid) && name.StartsWith("ALMOND::"))
                mid = name.Substring(8).Split(new[] { "::" }, StringSplitOptions.None)[0];
            if (!string.IsNullOrEmpty(mid)) rows.Add(mid + "|" + s);
        }
        File.WriteAllLines(Path.Combine(Path.GetTempPath(), "almond_matgroups.txt"), rows);
        return new { recorded = rows.Count };
    }
}
""" % (names, ", ".join(json.dumps(str(uuid.UUID(g))) for g in guids))
    try:
        _send_and_receive(json.dumps({"type": "execute", "script": script}).encode("utf-8"),
                          timeout=45.0)
        report = Path(tempfile.gettempdir()) / "almond_matgroups.txt"
        groups: dict[str, list[str]] = {}
        if report.is_file():
            for line in report.read_text(encoding="utf-8").splitlines():
                if "|" in line:
                    material_id, guid = line.split("|", 1)
                    groups.setdefault(material_id, []).append(guid)
        return [{"material_id": k, "objects": v} for k, v in sorted(groups.items())]
    except Exception:
        return []


@mcp.tool()
def import_asset_contract(
    contract_path: str,
    x_mm: float = 0,
    y_mm: float = 0,
    z_mm: float = 0,
    rotation_degrees: float = 0,
    layer: str = "ALMOND-EXCHANGE",
) -> str:
    """
    Imports an Almond asset contract (from Blender, Unreal, or another Rhino)
    into the open Rhino document, restoring everything the file format drops.

    Runs the full receive sequence: import the GLB, collapse the duplicate
    materials glTF creates, restore canonical PBR values from the Almond
    material library (glTF round trips shift base colours), re-attach the
    almond:* metadata keyed off the surviving material name, place the asset
    at the requested point using the contract's anchor, and verify the
    measured size against the contract's recorded dimensions.

    Args:
        contract_path: Path to a .almond.json contract file.
        x_mm, y_mm, z_mm: Placement point in millimetres (contract anchor).
        rotation_degrees: Rotation about world Z.
        layer: Destination layer, created if absent.
    Returns:
        JSON with counts restored/deduplicated and a dimension_check comparing
        what landed against the contract.
    """
    try:
        contract = exchange.load_contract(contract_path)
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})
    return json.dumps(_receive_contract(contract, x_mm, y_mm, z_mm, rotation_degrees, layer))


def _receive_contract(contract: dict, x_mm: float, y_mm: float, z_mm: float,
                      rotation_degrees: float, layer: str) -> dict:
    """Import a loaded contract's GLB into Rhino, restore materials and
    metadata, place it per the contract anchor, and report the dimension
    check. Shared by import_asset_contract and place_generated_asset."""
    problem = modeling_setup.check_bridge(_send_and_receive)
    if problem:
        return problem
    import_script = """
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Rhino;

public class Script
{
    public static List<Guid> Run(RhinoDoc doc)
    {
        var before = new HashSet<Guid>(doc.Objects.Select(o => o.Id));
        RhinoApp.RunScript("_-Import \\"%s\\" _Enter", false);
        var added = doc.Objects.Where(o => !before.Contains(o.Id)).Select(o => o.Id).ToList();
        File.WriteAllLines(Path.Combine(Path.GetTempPath(), "almond_imported.txt"),
            added.Select(g => g.ToString()));
        return added;
    }
}
""" % contract["_resolved_file"].replace("\\", "\\\\")
    try:
        result = json.loads(_send_and_receive(
            json.dumps({"type": "execute", "script": import_script}).encode("utf-8"),
            timeout=120.0))
    except ConnectionRefusedError:
        return {"status": "error", "message": "Rhino bridge is unavailable."}
    except Exception as exc:
        return {"status": "error", "message": f"Import failed: {exc}"}
    if result.get("status") != "success":
        return result
    imported = result.get("guids") or []
    if not imported:
        return {"status": "error",
                           "message": "Rhino imported no objects from the GLB."}

    contract["_imported_guids"] = imported
    needed = {row["material_id"] for row in contract.get("materials", [])}
    library = {mid: material_library.get(mid) for mid in needed}
    known = {mid: spec for mid, spec in library.items() if spec}
    unknown = sorted(mid for mid, spec in library.items() if not spec)

    script = _restore_and_place_script(contract, known, x_mm, y_mm, z_mm,
                                       rotation_degrees, layer)
    try:
        restore = json.loads(_send_and_receive(
            json.dumps({"type": "execute", "script": script}).encode("utf-8"),
            timeout=120.0))
    except Exception as exc:
        return {"status": "error",
                           "message": f"Imported, but restore/place failed: {exc}",
                           "imported_guids": imported}
    if restore.get("status") != "success":
        return {"status": "error", "message": restore.get("message", "restore failed"),
                           "imported_guids": imported}

    report_path = Path(tempfile.gettempdir()) / "almond_import_report.json"
    report = {}
    if report_path.is_file():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except ValueError:
            report = {}
    check = exchange.dimension_report(contract, report) if report else {"status": "unknown"}
    return {
        "status": "success",
        "asset_id": contract["asset_id"],
        "source_app": contract.get("source_app", "unknown"),
        "imported_count": len(imported),
        "metadata_restored": report.get("stamped", 0),
        "materials_deduplicated": report.get("deduped", 0),
        "unknown_material_ids": unknown,
        "dimension_check": check,
        "layer": layer,
        "imported_guids": imported,
    }


def place_generated_asset(
    asset_id: str,
    x_mm: float = 0,
    y_mm: float = 0,
    z_mm: float = 0,
    rotation_degrees: float = 0,
    layer: str = "ALMOND-GEN",
) -> str:
    """
    Imports a generated-library asset into the open Rhino document and places
    it at a point (contract anchor = bottom centre, mm), restoring its Almond
    material and almond:* metadata and verifying the landed size against the
    contract. Use search_generated_assets to choose an asset_id; afterwards
    call register_scene_instance so the scene ledger and layout validation
    know about it.

    Args:
        asset_id: e.g. "gen-park-bench-1".
        x_mm, y_mm, z_mm: placement point in millimetres.
        rotation_degrees: rotation about world Z.
        layer: destination layer, created if absent.
    """
    asset = generated_asset_indexer.get(asset_id)
    if not asset:
        return json.dumps({"status": "error",
                           "message": f"Unknown generated asset_id: {asset_id}"})
    if not asset.get("file_available"):
        return json.dumps({"status": "error",
                           "message": f"Model file missing for {asset_id}; run "
                                      "almond-mcp fetch-assets to download it."})
    values = [x_mm, y_mm, z_mm, rotation_degrees]
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
        return json.dumps({"status": "error", "message": "Placement values must be finite numbers."})
    contract_rel = str(asset.get("contract_file") or "").strip()
    if not contract_rel:
        return json.dumps({"status": "error", "message": f"{asset_id} has no contract_file."})
    library_root = Path(GENERATED_LIBRARY_DIR).resolve()
    contract_path = (library_root / contract_rel).resolve()
    try:
        contract_path.relative_to(library_root)
        contract = exchange.load_contract(contract_path)
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)})
    result = _receive_contract(contract, x_mm, y_mm, z_mm, rotation_degrees, layer)
    if result.get("status") == "success":
        result.update({
            "library_id": "generated_assets",
            "product": asset.get("product"),
            "dimensions_mm": asset.get("dimensions_mm"),
            "clearance_mm": (asset.get("spatial") or {}).get("clearance_mm"),
            "render_material_id": asset.get("render_material_id"),
            "next_step": "register_scene_instance(scene_id, asset_id=..., x, y, rotation) "
                         "so validate_scene_layout can see this placement.",
        })
    return json.dumps(result)


@mcp.tool()
def get_blender_helper_script(action: str, asset_id: str = "", name: str = "",
                              output_dir: str = "", material_id: str = "",
                              object_names: list[str] | None = None) -> str:
    """
    Returns Python to run inside Blender (via blender-mcp's execute_code) so
    Blender participates in the Almond workflow without a dedicated bridge.

    Actions:
        "export"    - export the current Blender selection as an Almond asset
                      contract + GLB (measured from evaluated mesh data,
                      because Blender inflates curve bounding boxes).
        "materials" - create Almond library materials in Blender (sRGB values
                      converted to linear) and assign them to named objects,
                      tagging both with almond:* properties.

    Args:
        action: "export" or "materials".
        asset_id, name, output_dir: for "export" (output_dir defaults to the
            Almond exchange folder).
        material_id, object_names: for "materials".
    Returns:
        JSON with a "script" field to pass to Blender's execute_code.
    """
    action = action.strip().lower()
    if action == "export":
        if not asset_id:
            return json.dumps({"status": "error", "message": "asset_id is required for export."})
        target = output_dir or str(paths.user_data_dir() / "exchange")
        return json.dumps({
            "status": "success",
            "action": "export",
            "script": exchange.blender_export_script(asset_id, name or asset_id, target),
            "note": "Run in Blender, then call import_asset_contract with the printed path.",
        })
    if action == "materials":
        material = material_library.get(material_id)
        if not material:
            return json.dumps({"status": "error",
                               "message": f"Unknown material_id: {material_id}. Call list_materials."})
        if not object_names:
            return json.dumps({"status": "error", "message": "object_names is required."})
        script = exchange.blender_material_script(
            [material], [{"material_id": material_id, "objects": object_names}])
        return json.dumps({"status": "success", "action": "materials", "script": script})
    return json.dumps({"status": "error", "message": 'action must be "export" or "materials".'})










@mcp.tool()
def search_asset_repository(query: str = "", kind: str = "all", drawing_ready: bool = False, limit: int = 20) -> dict:
    """Search the unified model/drawing archive. kind: all, model or element.

    Returns stable IDs, file availability, dimensions and MCP resource URIs.
    Drawing-ready means a derived projection package is linked to the object.
    """
    from almond_mcp.asset_repository import AssetRepository
    try:
        return AssetRepository().search(query, kind, drawing_ready, limit)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}


@mcp.resource("almond://repository/{asset_id}")
def repository_asset_resource(asset_id: str) -> str:
    """Unified object metadata, source evidence, representations and local files."""
    from almond_mcp.asset_repository import AssetRepository
    repository = AssetRepository()
    record = repository.records.get(asset_id)
    if not record:
        raise ValueError("Unknown repository asset ID")
    # HTTP URLs are relative to `almond-mcp library`; provide resolved locations
    # for MCP clients that do not have a browser server running.
    urls = {record["model"], record["preview"], record["contract"], record.get("generation_image")}
    if record["drawing"]:
        urls.add(record["drawing"]["record"])
        for view in record["drawing"]["views"]:
            urls.update([view["svg"], view["dxf"]])
        urls.update(sheet["svg"] for sheet in record["drawing"]["sheets"])
    record["local_files"] = {url: str(repository.files[url][1]) for url in urls if url in repository.files}
    return json.dumps(record)




















# Feature factories: explicit composition, no runtime directory discovery.
from almond_mcp.feature_context import FeatureContext
from almond_mcp.features.capture.tools import register as _register_capture
from almond_mcp.features.components.tools import register as _register_components
from almond_mcp.features.context.tools import register as _register_context
from almond_mcp.features.egress.tools import register as _register_egress
from almond_mcp.features.grasshopper.tools import register as _register_grasshopper
from almond_mcp.features.guidance.tools import register as _register_guidance
from almond_mcp.features.modeling.tools import register as _register_modeling
from almond_mcp.features.placement.tools import register as _register_placement
from almond_mcp.features.publishing.tools import register as _register_publishing
from almond_mcp.features.scenes.tools import register as _register_scenes

_feature_context = FeatureContext(globals())
globals().update(_register_capture(mcp, _feature_context))
globals().update(_register_components(mcp, _feature_context))
globals().update(_register_context(mcp, _feature_context))
globals().update(_register_egress(mcp, _feature_context))
globals().update(_register_grasshopper(mcp, _feature_context))
globals().update(_register_guidance(mcp, _feature_context))
globals().update(_register_modeling(mcp, _feature_context))
globals().update(_register_placement(mcp, _feature_context))
globals().update(_register_publishing(mcp, _feature_context))
globals().update(_register_scenes(mcp, _feature_context))
# End feature composition.

if __name__ == "__main__":
    mcp.run()

