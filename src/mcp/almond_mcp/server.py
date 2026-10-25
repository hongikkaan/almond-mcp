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










































# Feature factories: explicit composition, no runtime directory discovery.
from almond_mcp.feature_context import FeatureContext
from almond_mcp.features.assets.tools import register as _register_assets
from almond_mcp.features.capture.tools import register as _register_capture
from almond_mcp.features.components.tools import register as _register_components
from almond_mcp.features.context.tools import register as _register_context
from almond_mcp.features.diagrams.tools import register as _register_diagrams
from almond_mcp.features.drawings.tools import register as _register_drawings
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
globals().update(_register_assets(mcp, _feature_context))
globals().update(_register_capture(mcp, _feature_context))
globals().update(_register_components(mcp, _feature_context))
globals().update(_register_context(mcp, _feature_context))
globals().update(_register_diagrams(mcp, _feature_context))
globals().update(_register_drawings(mcp, _feature_context))
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

