"""Register asset tools and resources against the calling server's live context."""
from almond_mcp.tool_response import error_payload
from almond_mcp.instruction_text import tool_instruction, read_instruction

import json
import math
from pathlib import Path
import socket
import struct
import uuid

from fastmcp.resources import ResourceContent, ResourceResult

from almond_mcp.features.structure import asset_loads
from almond_mcp import asset_passport, paths
from almond_mcp.features.assets import drawing_assets, drafting


def register(mcp, context):
    """Register the existing asset API without freezing mutable server services."""

    @mcp.tool()
    @tool_instruction(__file__, 'list_drawing_assets')
    def list_drawing_assets(
        category: str = "",
        limit: int = 20,
        offset: int = 0,
    ) -> str:
        page = context.retrieval_store.search_assets(
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
    @tool_instruction(__file__, 'search_drawing_assets')
    def search_drawing_assets(
        query: str = "",
        category: str = "",
        max_width_mm: float = 0,
        max_depth_mm: float = 0,
        max_height_mm: float = 0,
        limit: int = 10,
        offset: int = 0,
    ) -> str:
        return json.dumps(context.retrieval_store.search_assets(
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
    @tool_instruction(__file__, 'get_drawing_asset')
    def get_drawing_asset(asset_id: str) -> str:
        asset = context.retrieval_store.get_asset(asset_id, library_id="drawing_assets")
        if not asset:
            return json.dumps(error_payload(f"Unknown drawing asset_id: {asset_id}"))
        return json.dumps({"status": "success", "asset": asset})


    def _extract_drawing_asset(source_path: str, output_path: str) -> dict:
        rhino_context = json.loads(context._send_and_receive(b'{"type":"get_rhino_context","selection_limit":0}'))
        if rhino_context.get("status") != "success" or rhino_context.get("capabilities", {}).get("drawing_asset_extract") != 1:
            raise ValueError(read_instruction(__file__, 'response-400'))
        response = context._send_and_receive(json.dumps({"type": "drawing_asset_extract",
            "source_path": source_path, "output_path": output_path}).encode("utf-8"), timeout=90.0)
        if len(response.encode("utf-8")) > 262144:
            raise ValueError("Native extraction acknowledgement exceeds 256 KiB")
        return json.loads(response)


    @mcp.tool(annotations={"destructiveHint": False, "openWorldHint": False})
    @tool_instruction(__file__, 'register_drawing_asset')
    def register_drawing_asset(source_3dm: str, asset_id: str, name: str,
                               category: str = "other", tags: list[str] | None = None,
                               description: str = "", source_url: str = "",
                               replace_existing: bool = False) -> dict:
        try:
            if asset_id in context.generated_asset_indexer.assets or asset_id in context.diagram_asset_indexer.assets:
                raise ValueError(read_instruction(__file__, 'response-409'))
            result = drawing_assets.register_prepared_3dm(Path(context.DRAWING_LIBRARY_DIR),
                source_3dm=source_3dm, asset_id=asset_id, name=name, category=category,
                tags=tags, description=description, source_url=source_url,
                replace_existing=replace_existing, extract=_extract_drawing_asset)
        except Exception as exc:
            return {"status": "error", "registration_applied": False, "message": str(exc)}
        try:
            context.drawing_asset_indexer._load()
            context.retrieval_store.sync_assets(list(context.drawing_asset_indexer.assets.values()), library_id="drawing_assets")
        except Exception as exc:
            return {**result, "status": "error", "registration_applied": True,
                    "live_index_refreshed": False,
                    "message": read_instruction(__file__, 'response-410').format(exc)}
        return {**result, "registration_applied": True, "live_index_refreshed": True}


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
        page = context.retrieval_store.search_assets(
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
        return json.dumps(context.retrieval_store.search_assets(
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
                list(context.generated_asset_indexer.assets.values()), query, category, room_type,
                width_mm, depth_mm, height_mm, max_triangles, include_clearances, limit)
        except ValueError as exc:
            return error_payload(str(exc))


    def get_generated_asset_passport(asset_id: str) -> dict:
        """Read portable asset metadata: measured vs nominal dimensions, provenance,
    materials, spatial contract, usage suggestions, quality limits and rights."""
        asset = context.generated_asset_indexer.get(asset_id)
        if not asset:
            return error_payload(f"Unknown generated asset_id: {asset_id}")
        if not asset.get("passport"):
            return error_payload(read_instruction(__file__, 'response-403'))
        out = {"status": "success", "passport": asset["passport"],
               "file_available": asset.get("file_available", False),
               "preview_uri": f"almond://generated/{asset_id}/preview"}
        try:
            table = asset_loads.LoadTable(context._structural_loads_path())
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
        asset = context.generated_asset_indexer.get(asset_id)
        if not asset:
            return error_payload(f"Unknown generated asset_id: {asset_id}")
        try:
            return {"status": "success", **asset_passport.evaluate_fit(
                asset, width_mm, depth_mm, height_mm, rotation_degrees, include_clearances)}
        except ValueError as exc:
            return error_payload(str(exc))


    def get_generation_sources(asset_id: str) -> dict:
        """Get original recorded provider/task IDs, prompt, transformations and evidence gaps.
    Includes Higgsfield image job IDs where recorded before the Meshy stage.
    This is local evidence, not an independent provider/account verification."""
        path = Path(context.GENERATED_LIBRARY_DIR)/"source-register.json"
        if not path.exists():
            return error_payload(read_instruction(__file__, 'response-404'))
        data = json.loads(path.read_text(encoding="utf-8"))
        record = next((a for a in data["assets"] if a["asset_id"] == asset_id), None)
        if not record:
            return error_payload("Unknown generated asset ID")
        asset = context.generated_asset_indexer.get(asset_id)
        if not asset or record["model_sha256"] != asset["sha256"]:
            return error_payload("Source register is stale for this asset")
        return {"status": "success", "record": record}


    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
    @tool_instruction(__file__, 'get_asset_drawing')
    def get_asset_drawing(asset_id: str) -> dict:
        asset = context.drawing_asset_indexer.get(asset_id)
        if asset and asset.get("drawing_package"):
            root = Path(context.DRAWING_LIBRARY_DIR).resolve()
            package = (root / asset["drawing_package"]).resolve()
            package.relative_to(root)
            manifest = json.loads((package / "drawing.json").read_text(encoding="utf-8"))
            return {"status": "success", "asset_id": asset_id, "package_dir": str(package), "manifest": manifest,
                    "dimensions_path": str(package / "dimensions.json"),
                    "plan_svg_uri": f"almond://drawing/{asset_id}/drawing/plan/50"}
        root = Path(context.DRAFTING_LIBRARY_DIR)
        data = json.loads((root/"manifest.json").read_text(encoding="utf-8"))
        record = next((a for a in data["assets"] if a["asset_id"] == asset_id), None)
        if not record:
            return error_payload(read_instruction(__file__, 'response-406'))
        package = (root/record["package"]).resolve()
        package.relative_to(root.resolve())
        manifest = json.loads((package/"drawing.json").read_text(encoding="utf-8"))
        return {"status": "success", "package_dir": str(package), "manifest": manifest,
                "plan_svg_uri": f"almond://generated/{asset_id}/drawing/plan/50"}


    @mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False})
    @tool_instruction(__file__, 'generate_asset_drawing_views')
    def generate_asset_drawing_views(asset_id: str = "", source_glb: str = "",
                                     input_units: str = "", up_axis: str = "y",
                                     scales: list[int] | None = None,
                                     source_references: list[dict] | None = None) -> dict:
        try:
            if bool(asset_id) == bool(source_glb):
                raise ValueError(read_instruction(__file__, 'response-411'))
            source_record = None
            if asset_id:
                asset = context.generated_asset_indexer.get(asset_id)
                if not asset:
                    raise ValueError("Unknown generated asset ID")
                model = (Path(context.GENERATED_LIBRARY_DIR)/asset["file"]).resolve()
                model.relative_to(Path(context.GENERATED_LIBRARY_DIR).resolve())
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
            return error_payload(str(exc))


    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
    @tool_instruction(__file__, 'audit_asset_drawing')
    def audit_asset_drawing(package_dir: str, source_glb: str = "") -> dict:
        try:
            package = Path(package_dir)
            if not package.is_absolute():
                raise ValueError("Supply an absolute package directory")
            manifest = json.loads((package/"drawing.json").read_text(encoding="utf-8"))
            source = Path(source_glb) if source_glb else None
            if source is not None and not source.is_absolute():
                raise ValueError("Supply an absolute source GLB path")
            if source is None:
                asset = context.drawing_asset_indexer.get(manifest["source"]["asset_id"])
                root = Path(context.DRAWING_LIBRARY_DIR) if asset else Path(context.GENERATED_LIBRARY_DIR)
                asset = asset or context.generated_asset_indexer.get(manifest["source"]["asset_id"])
                if asset:
                    source = (root / asset["file"]).resolve()
                    source.relative_to(root.resolve())
            return drafting.audit_package(package, source)
        except (OSError, ValueError, KeyError, IndexError, TypeError, struct.error) as exc:
            return error_payload(str(exc))


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
        model = context.drawing_asset_indexer.get(asset_id)
        root = Path(context.DRAWING_LIBRARY_DIR) if model else Path(context.GENERATED_LIBRARY_DIR)
        model = model or context.generated_asset_indexer.get(asset_id)
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
    @tool_instruction(__file__, 'generated_catalogue_resource')
    def generated_catalogue_resource() -> ResourceResult:
        return ResourceResult([ResourceContent({"library_id": "generated_assets", "assets": [
            {"asset_id": a["asset_id"], "product": a["product"], "category": a["category"],
             "dimensions_mm": a["dimensions_mm"],
             "passport_uri": f"almond://generated/{a['asset_id']}/passport",
             "preview_uri": f"almond://generated/{a['asset_id']}/preview"}
            for a in context.generated_asset_indexer.assets.values()]}, mime_type="application/json")])


    @mcp.resource("almond://generated/{asset_id}/passport", mime_type="application/json")
    def generated_passport_resource(asset_id: str) -> ResourceResult:
        return ResourceResult([ResourceContent(get_generated_asset_passport(asset_id), mime_type="application/json")])


    @mcp.resource("almond://generated/{asset_id}/preview", mime_type="image/png")
    @tool_instruction(__file__, 'generated_preview_resource')
    def generated_preview_resource(asset_id: str) -> ResourceResult:
        if asset_id not in context.generated_asset_indexer.assets:
            raise ValueError("Unknown generated asset id")
        root = Path(context.GENERATED_LIBRARY_DIR).resolve()
        preview = (root / "previews" / f"{asset_id}.png").resolve()
        preview.relative_to(root)
        return ResourceResult([ResourceContent(preview.read_bytes(), mime_type="image/png")])


    def get_generated_asset(asset_id: str) -> str:
        """Returns one generated asset's measured dimensions, spatial contract,
    material, generation provenance (Meshy task ids, prompt) and availability."""
        asset = context.retrieval_store.get_asset(asset_id, library_id="generated_assets")
        if not asset:
            return json.dumps(error_payload(f"Unknown generated asset_id: {asset_id}"))
        return json.dumps({"status": "success", "asset": asset})


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
            "note": read_instruction(__file__, 'response-399'),
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
            response = json.loads(context._send_and_receive(payload, timeout=30.0))
            return response.get("status") == "success"
        except Exception:
            return False


    @mcp.tool()
    @tool_instruction(__file__, 'place_drawing_asset')
    def place_drawing_asset(
        asset_id: str,
        x: float = 0,
        y: float = 0,
        z: float = 0,
        rotation_degrees: float = 0,
        scale: float = 1,
    ) -> str:
        asset = context.drawing_asset_indexer.get(asset_id)
        if not asset:
            return json.dumps(error_payload(f"Unknown drawing asset_id: {asset_id}"))
        if not asset.get("file_available"):
            return json.dumps(error_payload(f"Drawing asset file is missing for {asset_id}."))
        numeric_values = [x, y, z, rotation_degrees, scale]
        if not all(
            isinstance(value, (int, float))
            and abs(value) != float("inf")
            and value == value
            for value in numeric_values
        ):
            return json.dumps(error_payload("Placement values must be finite numbers."))
        if scale <= 0 or scale > 100:
            return json.dumps(error_payload("scale must be greater than 0 and no more than 100."))

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
            return context._send_and_receive(payload, timeout=90.0)
        except socket.timeout:
            return json.dumps({"status": "error", "requires_reconciliation": True,
                "message": read_instruction(__file__, 'response-423')})
        except ConnectionRefusedError:
            return json.dumps(error_payload(read_instruction(__file__, 'response-424')))
        except Exception as exc:
            return json.dumps(error_payload(f"Drawing asset placement failed: {exc}"))


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
        asset = context.generated_asset_indexer.get(asset_id)
        if not asset:
            return json.dumps(error_payload(f"Unknown generated asset_id: {asset_id}"))
        if not asset.get("file_available"):
            return json.dumps(error_payload(read_instruction(__file__, 'response-417').format(asset_id)))
        values = [x_mm, y_mm, z_mm, rotation_degrees]
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
            return json.dumps(error_payload("Placement values must be finite numbers."))
        contract_rel = str(asset.get("contract_file") or "").strip()
        if not contract_rel:
            return json.dumps(error_payload(f"{asset_id} has no contract_file."))
        library_root = Path(context.GENERATED_LIBRARY_DIR).resolve()
        contract_path = (library_root / contract_rel).resolve()
        try:
            contract_path.relative_to(library_root)
            contract = context.exchange.load_contract(contract_path)
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))
        result = context._receive_contract(contract, x_mm, y_mm, z_mm, rotation_degrees, layer)
        if result.get("status") == "success":
            result.update({
                "library_id": "generated_assets",
                "product": asset.get("product"),
                "dimensions_mm": asset.get("dimensions_mm"),
                "clearance_mm": (asset.get("spatial") or {}).get("clearance_mm"),
                "render_material_id": asset.get("render_material_id"),
                "next_step": read_instruction(__file__, 'response-419'),
            })
        return json.dumps(result)


    @mcp.tool()
    @tool_instruction(__file__, 'search_asset_repository')
    def search_asset_repository(query: str = "", kind: str = "all", drawing_ready: bool = False, limit: int = 20) -> dict:
        from almond_mcp.features.assets.asset_repository import AssetRepository
        try:
            return AssetRepository().search(query, kind, drawing_ready, limit)
        except ValueError as exc:
            return error_payload(str(exc))


    @mcp.resource("almond://repository/{asset_id}")
    @tool_instruction(__file__, 'repository_asset_resource')
    def repository_asset_resource(asset_id: str) -> str:
        from almond_mcp.features.assets.asset_repository import AssetRepository
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


    return {
        "list_drawing_assets": list_drawing_assets,
        "search_drawing_assets": search_drawing_assets,
        "get_drawing_asset": get_drawing_asset,
        "_extract_drawing_asset": _extract_drawing_asset,
        "register_drawing_asset": register_drawing_asset,
        "list_generated_assets": list_generated_assets,
        "search_generated_assets": search_generated_assets,
        "recommend_generated_assets": recommend_generated_assets,
        "get_generated_asset_passport": get_generated_asset_passport,
        "evaluate_generated_asset_fit": evaluate_generated_asset_fit,
        "get_generation_sources": get_generation_sources,
        "get_asset_drawing": get_asset_drawing,
        "generate_asset_drawing_views": generate_asset_drawing_views,
        "audit_asset_drawing": audit_asset_drawing,
        "generation_sources_resource": generation_sources_resource,
        "asset_drawing_resource": asset_drawing_resource,
        "drawing_asset_view_resource": drawing_asset_view_resource,
        "generated_catalogue_resource": generated_catalogue_resource,
        "generated_passport_resource": generated_passport_resource,
        "generated_preview_resource": generated_preview_resource,
        "get_generated_asset": get_generated_asset,
        "_dimension_check": _dimension_check,
        "_apply_import_correction": _apply_import_correction,
        "place_drawing_asset": place_drawing_asset,
        "place_generated_asset": place_generated_asset,
        "search_asset_repository": search_asset_repository,
        "repository_asset_resource": repository_asset_resource,
    }
