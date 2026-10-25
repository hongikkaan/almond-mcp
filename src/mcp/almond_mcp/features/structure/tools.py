"""MCP tools and bridge helpers for structural validation and overlays."""
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
        floor, err = context._floor_spec(floor_load_kn_m2, floor_dead_kn_m2, engine)
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
            spec, err = context._asset_load_spec(scene_id)
            if err:
                return json.dumps({"status": "error", "message": err})
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
                return json.dumps({"status": "error", "message": msg}), None
            return None, msg + " Fell back to the Karamba route."
        try:
            reply = json.loads(context._send_and_receive(
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
        note = None
        spec = None
        floor = None
        if not clear and reanalyze:
            floor, err = context._floor_spec(floor_load_kn_m2, floor_dead_kn_m2, engine)
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
            spec, err = context._asset_load_spec(scene_id)
            if err:
                return json.dumps({"status": "error", "message": err})
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
            return json.dumps({"status": "error", "message": f"Structure view timed out (>{timeout:.0f}s)."})
        except ConnectionRefusedError:
            return json.dumps({"status": "error", "message": "Connection refused. Is the RhinoAlmondBridge plugin loaded in Rhino?"})
        except Exception as e:
            return json.dumps({"status": "error", "message": f"Bridge error: {e}"})


    def _native_view(request: dict, guids, required: bool, asset_spec=None, floor_spec=None, design=("en1990", None, "eurocode"),
                     connections="rigid", stability="auto", view="deflection", fabrication="cold_formed"):
        """Solve natively and draw through the bridge's structure_draw overlay.

        Returns (reply_json, None) when it ran or must stop, (None, note) to fall back to Karamba."""

        def unavailable(msg):
            if required:
                return json.dumps({"status": "error", "message": msg}), None
            return None, msg + " Fell back to the Karamba route."
        try:
            model = json.loads(context._send_and_receive(
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
            runs = context.retrieval_store.list_validation_runs(limit=limit)
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
            target.write_text(context._render_validation_report(runs), encoding="utf-8")
            return json.dumps({
                "status": "success",
                "path": str(target),
                "runs": len(runs),
                "latest_method": runs[0]["analysis_method"],
            })
        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)})

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
