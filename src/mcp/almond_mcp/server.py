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






























_VIEW_ENGINE: str | None = None   # which engine drew the current overlay ("native" | "api")










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
from almond_mcp.features.planning.tools import register as _register_planning
from almond_mcp.features.publishing.tools import register as _register_publishing
from almond_mcp.features.scenes.tools import register as _register_scenes
from almond_mcp.features.structure.tools import register as _register_structure

_feature_context = FeatureContext(globals())
globals().update(_register_capture(mcp, _feature_context))
globals().update(_register_components(mcp, _feature_context))
globals().update(_register_context(mcp, _feature_context))
globals().update(_register_egress(mcp, _feature_context))
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

