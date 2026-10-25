"""Drawing recipes, presentation and persistent Layout tool registration."""
import json
import socket

from pydantic import StrictFloat, StrictInt

from almond_mcp.store_common import DrawingSheetReconciliationError


def register(mcp, context):
    """Register drawing tools against the assembling server's live services."""
    def _drawing_sheet_bridge(request: dict) -> dict:
        """Check Layout capability, then send exactly one requested native operation."""
        payload = json.dumps(request, allow_nan=False).encode("utf-8")
        if len(payload) > 2_097_152:
            return {"status": "error", "mutation_applied": False, "message": "Drawing sheet request exceeds 2 MiB."}
        try:
            rhino_context = json.loads(context._send_and_receive(b'{"type":"get_rhino_context","selection_limit":0}'))
            if not isinstance(rhino_context, dict) or rhino_context.get("status") != "success":
                raise ValueError("Could not inspect the bound Rhino document.")
            if rhino_context.get("capabilities", {}).get("drawing_sheets") != 1:
                raise ValueError("Load a Bridge with drawing_sheets=1 before managing drawing sheets.")
        except Exception as exc:
            return {"status": "error", "mutation_applied": False, "message": str(exc)}
        response = context._send_and_receive(payload)
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


    @mcp.tool()
    def list_drawing_recipes() -> str:
        """Lists compact audited layer, lineweight, projection, and export recipes."""
        recipes = []
        for recipe_id, recipe in sorted(context.drawing_recipe_indexer.recipes.items()):
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
        recipe = context.drawing_recipe_indexer.get(recipe_id)
        if not recipe:
            return json.dumps({
                "status": "error",
                "message": f"Unknown drawing recipe_id: {recipe_id}",
            })
        return json.dumps({
            "status": "success",
            "recipe": context.drawing_recipe_indexer.public_record(recipe),
        })


    @mcp.tool()
    def apply_drawing_style(recipe_id: str = "technical_axon_v1") -> str:
        """
    Creates or updates the Rhino layer hierarchy, plot weights, colours, and
    linetypes defined by an audited drawing recipe.
    """
        recipe = context.drawing_recipe_indexer.get(recipe_id)
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
            return context._send_and_receive(payload, timeout=60.0)
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
        asset = context.drawing_asset_indexer.get(asset_id)
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
            return context._send_and_receive(payload, timeout=60.0)
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
            sheet = context.retrieval_store.upsert_drawing_sheet(
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
            sheet = context.retrieval_store.get_drawing_sheet(sheet_id)
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
            return json.dumps({"status": "success", **context.retrieval_store.list_drawing_sheets(
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
            sheet = context.retrieval_store.sync_drawing_sheet(
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
            sheet = context.retrieval_store.remove_drawing_sheet(sheet_id, native_apply=_drawing_sheet_bridge)
            return json.dumps({"status": "success", "sheet": sheet}, ensure_ascii=False)
        except Exception as exc:
            return _drawing_sheet_error(exc)

    return {
        "list_drawing_recipes": list_drawing_recipes,
        "get_drawing_recipe": get_drawing_recipe,
        "apply_drawing_style": apply_drawing_style,
        "import_drawing_hatch_patterns": import_drawing_hatch_patterns,
        "upsert_drawing_sheet": upsert_drawing_sheet,
        "get_drawing_sheet": get_drawing_sheet,
        "list_drawing_sheets": list_drawing_sheets,
        "sync_drawing_sheet": sync_drawing_sheet,
        "remove_drawing_sheet": remove_drawing_sheet,
        "_drawing_sheet_bridge": _drawing_sheet_bridge,
        "_drawing_sheet_error": _drawing_sheet_error,
    }
