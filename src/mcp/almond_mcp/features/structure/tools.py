"""MCP tools and bridge helpers for structural validation and overlays."""
from almond_mcp.tool_response import error_payload
from almond_mcp.query_output import query_output
from almond_mcp.instruction_text import tool_instruction, read_instruction
from pydantic import StrictBool
import json
import math
import socket
from pathlib import Path

from almond_mcp import paths
from . import asset_loads, design_codes, native_structure, structure_study

KARAMBA_ONLY_TYPES = ("shell", "gridshell", "membrane")


def register(mcp, context):
    """Register structural tools against the assembling server's current services."""

    @mcp.tool()
    @tool_instruction(__file__, 'validate_structure')
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
        engine = (engine or "auto").lower()
        if engine not in ("auto", "native", "karamba"):
            return json.dumps(error_payload("engine must be 'auto', 'native' or 'karamba'."))
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
        floor, err = context._floor_spec(floor_load_kn_m2, floor_dead_kn_m2, engine)
        if err:
            return json.dumps(error_payload(err))
        try:
            native_structure.combinations(design_basis, uls_combination, design_code)
            if (connections or "rigid").lower() not in native_structure.CONNECTIONS:
                raise ValueError("connections must be 'rigid' or 'simple'.")
            if (stability or "auto").lower() not in ("auto", "off"):
                raise ValueError("stability must be 'auto' or 'off'.")
        except ValueError as e:
            return json.dumps(error_payload(str(e)))
        if asset_loads:
            if engine == "karamba":
                return json.dumps(error_payload("asset_loads needs the native engine (engine='auto' or 'native')."))
            spec, err = context._asset_load_spec(scene_id)
            if err:
                return json.dumps(error_payload(err))
        if engine == "native" or (engine == "auto" and structure_type.lower() not in KARAMBA_ONLY_TYPES):
            result, note = context._native_validation(guids, structure_type, load_kn, material, fixed_supports,
                                              self_weight, span_m, required=engine == "native", asset_spec=spec,
                                              floor_spec=floor, design=(design_basis, uls_combination, design_code),
                                              connections=connections, stability=stability, detail=detail,
                                              fabrication=fabrication)
            if isinstance(result, str):          # hard error (explicit native request, or no bridge)
                return result
        if result is None:
            try:
                response = context._send_and_receive(json.dumps(request).encode('utf-8'), timeout=60.0)
            except socket.timeout:
                return json.dumps(error_payload("Structural validation timed out (>60s)."))
            except ConnectionRefusedError:
                return json.dumps(error_payload("Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?"))
            except Exception as e:
                return json.dumps(error_payload(f"Bridge error: {e}"))
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
                    check = context.construction_library.assess_span(structure_type, material, span)
                    result["construction_check"] = check
                    if check.get("warnings"):
                        result.setdefault("warnings", [])
                        result["warnings"].extend(check["warnings"])
                except Exception:
                    pass
                context.retrieval_store.record_validation_run(request, result, guids)
        except Exception:
            pass
        return json.dumps(result)


    def _structural_loads_path() -> Path:
        return Path(context.GENERATED_LIBRARY_DIR) / "structural-loads.json"


    def _asset_load_spec(scene_id: str = ""):
        """Placements + load table + catalogue facts for asset loads: (spec, None) or (None, error)."""
        try:
            table = asset_loads.LoadTable(context._structural_loads_path())
        except Exception as e:
            return None, f"The asset load table is unavailable ({e})."
        if scene_id:
            try:
                placements = asset_loads.placements_from_scene(context.retrieval_store.scene_instances(scene_id))
            except KeyError as e:
                return None, str(e).strip("'")
        else:
            try:
                reply = json.loads(context._send_and_receive(json.dumps({"type": "asset_placements"}).encode('utf-8'), timeout=60.0))
            except ConnectionRefusedError:
                return None, "Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?"
            except Exception as e:
                return None, f"Could not read asset placements from Rhino ({e})."
            if not isinstance(reply, dict) or reply.get("status") != "ok":
                return None, "This bridge version cannot export asset placements (update almondbridge)."
            placements = reply.get("placements") or []
        catalogue = structure_study.asset_catalogue(placements, context.generated_asset_indexer.get)
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
                return json.dumps(error_payload(msg)), None
            return None, msg + " Fell back to the Karamba route."
        try:
            reply = json.loads(context._send_and_receive(
                json.dumps({"type": "structure_model", "guids": guids}).encode('utf-8'), timeout=60.0))
        except socket.timeout:
            return unavailable("Exporting the structural model timed out.")
        except ConnectionRefusedError:
            return json.dumps(error_payload("Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?")), None
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
            return json.dumps(error_payload(str(e))), None
        return result, None


    @mcp.tool()
    @tool_instruction(__file__, 'list_design_codes')
    @query_output
    def list_design_codes(include_ids: StrictBool = False) -> str:
        return json.dumps(design_codes.listing())


    @mcp.tool()
    @tool_instruction(__file__, 'visualize_structure')
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
        if not clear and not guids:
            return json.dumps(error_payload("Provide the curve (and support point) GUIDs to analyse."))
        if color_by not in ("displacement", "utilization"):
            return json.dumps(error_payload("color_by must be 'displacement' or 'utilization'."))
        engine = (engine or "auto").lower()
        if engine not in ("auto", "native", "karamba"):
            return json.dumps(error_payload("engine must be 'auto', 'native' or 'karamba'."))
        if deflection_limit_ratio is None:
            try:
                deflection_limit_ratio = native_structure.design_profile(design_basis, design_code).deflection_limit_ratio
            except ValueError as e:
                return json.dumps(error_payload(str(e)))
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
        note = None
        spec = None
        floor = None
        if not clear and reanalyze:
            floor, err = context._floor_spec(floor_load_kn_m2, floor_dead_kn_m2, engine)
            if err:
                return json.dumps(error_payload(err))
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
                return json.dumps(error_payload(str(e)))
        if asset_loads and not clear and reanalyze:
            if engine == "karamba":
                return json.dumps(error_payload("asset_loads needs the native engine (engine='auto' or 'native')."))
            spec, err = context._asset_load_spec(scene_id)
            if err:
                return json.dumps(error_payload(err))
        if not clear and engine != "karamba" and not (not reanalyze and context._VIEW_ENGINE == "api"):
            if not reanalyze and context._VIEW_ENGINE == "native":
                draw = {k: v for k, v in request.items() if k not in ("guids", "reanalyze", "clear")}
                draw["type"] = "structure_draw"
                return context._bridge_call(draw, 30.0)
            reply, note = context._native_view(request, guids, required=engine == "native", asset_spec=spec, floor_spec=floor,
                                       design=(design_basis, uls_combination, design_code), connections=connections,
                                       stability=stability, view=view, fabrication=fabrication)
            if reply is not None:
                return reply
        out = context._bridge_call(request, 90.0)
        if clear:
            context.set_state("_VIEW_ENGINE", None)
        elif reanalyze:
            context.set_state("_VIEW_ENGINE", "api")
        if note:
            try:
                parsed = json.loads(out)
                parsed.setdefault("warnings", []).append(note)
                out = json.dumps(parsed)
            except Exception:
                pass
        return out


    def _bridge_call(message: dict, timeout: float) -> str:
        try:
            return context._send_and_receive(json.dumps(message).encode('utf-8'), timeout=timeout)
        except socket.timeout:
            return json.dumps(error_payload(f"Structure view timed out (>{timeout:.0f}s)."))
        except ConnectionRefusedError:
            return json.dumps(error_payload("Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?"))
        except Exception as e:
            return json.dumps(error_payload(f"Bridge error: {e}"))


    def _native_view(request: dict, guids, required: bool, asset_spec=None, floor_spec=None, design=("en1990", None, "eurocode"),
                     connections="rigid", stability="auto", view="deflection", fabrication="cold_formed"):
        """Solve natively and draw through the bridge's structure_draw overlay.

        Returns (reply_json, None) when it ran or must stop, (None, note) to fall back to Karamba."""

        def unavailable(msg):
            if required:
                return json.dumps(error_payload(msg)), None
            return None, msg + " Fell back to the Karamba route."
        try:
            model = json.loads(context._send_and_receive(
                json.dumps({"type": "structure_model", "guids": guids}).encode('utf-8'), timeout=60.0))
        except ConnectionRefusedError:
            return json.dumps(error_payload("Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?")), None
        except Exception as e:
            return unavailable(f"The bridge could not export a structural model ({e}).")
        if not isinstance(model, dict) or model.get("status") != "ok" or "members" not in model:
            return unavailable("This bridge version cannot export structural models (update almondbridge).")
        if model.get("shells"):
            return unavailable(f"The model contains {model['shells']} shell element(s), which the native frame solver does not analyse.")
        if not model["members"]:
            return json.dumps(error_payload("No curve members found for the given GUIDs.")), None
        try:
            result, span = native_structure.view_result(
                model, request["load_kn"], request["material"], fixed_supports=request["fixed_rotations"],
                self_weight=request["self_weight"], diameter_mm=request.get("beam_diameter_mm"),
                wall_mm=request.get("beam_wall_mm"), span_m=request.get("span_m"), asset_loads=asset_spec,
                floor_loads=floor_spec, design_basis=design[0], uls=design[1], connections=connections,
                stability=stability, view=view, design_code=design[2], fabrication=fabrication)
        except native_structure.InstabilityError as e:
            return json.dumps({"status": "fail", "analysis_method": "native", "message": str(e),
                               "stability": e.report, "hint": read_instruction(__file__, 'response-1031')}), None
        except native_structure.fs.MechanismError as e:
            return json.dumps({"status": "fail", "analysis_method": "native", "message": str(e),
                               "mechanism_nodes": len(e.nodes)}), None
        except ValueError as e:
            return json.dumps(error_payload(str(e))), None
        draw, reports = structure_study.draw_message(request, result, span)
        report, floor_report, combos = reports["asset_loads"], reports["floor_loads"], reports["combinations"]
        conn_report, stab_report, buckling = reports["connections"], reports["stability"], reports["buckling"]
        code_report = reports["design_code"]
        out = context._bridge_call(draw, 60.0)
        try:
            parsed = json.loads(out)
        except Exception:
            return out, None
        if isinstance(parsed, dict) and parsed.get("status") in ("pass", "fail"):
            context.set_state("_VIEW_ENGINE", "native")
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
            read_instruction(__file__, 'response-981'),
            read_instruction(__file__, 'response-982'),
            "  plus self-weight (equilibrium).",
            read_instruction(__file__, 'response-983'),
            read_instruction(__file__, 'response-984'),
            read_instruction(__file__, 'response-985'),
            read_instruction(__file__, 'response-986'),
            read_instruction(__file__, 'response-987'),
            read_instruction(__file__, 'response-988'),
            "",
        ]
        return "\n".join(lines)


    @mcp.tool()
    @tool_instruction(__file__, 'export_structural_report')
    def export_structural_report(path: str = "", limit: int = 50) -> str:
        from datetime import datetime, timezone

        try:
            runs = context.retrieval_store.list_validation_runs(limit=limit)
            if not runs:
                return json.dumps(error_payload(read_instruction(__file__, 'response-1026')))
            target = Path(path) if path else (
                paths.user_data_dir() / "reports" /
                f"structural-validation-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.md"
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(context._render_validation_report(runs), encoding="utf-8")
            return json.dumps({
                "status": "success",
                "path": str(target),
                "runs": len(runs),
                "latest_method": runs[0]["analysis_method"],
            })
        except Exception as exc:
            return json.dumps(error_payload(str(exc)))

    return {
        "validate_structure": validate_structure,
        "_structural_loads_path": _structural_loads_path,
        "_asset_load_spec": _asset_load_spec,
        "_floor_spec": _floor_spec,
        "_native_validation": _native_validation,
        "list_design_codes": list_design_codes,
        "visualize_structure": visualize_structure,
        "_bridge_call": _bridge_call,
        "_native_view": _native_view,
        "_render_validation_report": _render_validation_report,
        "export_structural_report": export_structural_report,
    }
