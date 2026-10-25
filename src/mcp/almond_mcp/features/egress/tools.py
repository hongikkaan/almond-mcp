"""Egress tool registration using the shared construction library."""
import json


def register(mcp, context):
    """Register egress checks and return the server compatibility exports."""
    @mcp.tool()
    def check_egress(
        plate_bounds_mm: list[float],
        exits: list[dict],
        occupancy: str = "business",
        stories: int = 1,
        sprinklered: bool = True,
        net_area_m2: float = 0.0,
        travel_distances_m: list[float] = [],
        dead_end_m: float = 0.0,
    ) -> str:
        """
    Checks a floor plate's means of egress against the construction library's
    egress rules (BCI A.10-A.13 framework + IBC-typical numeric factors -
    always verify against the governing code; the response repeats this).

    Call AFTER laying out cores/exits and BEFORE detailing: it verifies exit
    count, exit separation, egress width, travel distances and dead ends in
    one pass, and names the failing requirement so the layout can be fixed
    (add an exit, move a core, widen a stair) instead of guessed at.

    Args:
        plate_bounds_mm: Floor plate [min_x, min_y, max_x, max_y] in mm
            (sets gross area and the diagonal used for exit separation).
        exits: One entry per exit (stair door or exterior exit door):
            {"name": str, "x_mm": float, "y_mm": float, "width_mm": float}.
            Positions are the door centers; width is the clear egress width.
        occupancy: Occupant-load key: business, mercantile, assembly_
            unconcentrated, classroom, residential, storage.
        stories: Stories served. Above 1, at least two exits are required
            and exit width demand uses the stair factor (7.6 mm/occupant)
            instead of the door factor (5.1).
        sprinklered: Sprinklered throughout (affects separation fraction,
            travel-distance and dead-end limits).
        net_area_m2: Override the occupied area; 0 uses the gross plate area.
        travel_distances_m: Measured worst-case travel distances (e.g. from
            drawn egress paths); empty skips the travel check.
        dead_end_m: Longest dead-end corridor in metres; 0 skips the check.
    Returns:
        JSON: {passed, occupant_load, checks: [{check, required, provided,
        passed, basis}], warnings, source_note}.
    """
        rules = context.construction_library.reference.get("egress_rules")
        if not rules:
            return json.dumps({"status": "error",
                               "message": "egress_rules missing from the construction manifest."})
        if len(plate_bounds_mm) != 4:
            return json.dumps({"status": "error",
                               "message": "plate_bounds_mm must be [min_x, min_y, max_x, max_y]."})
        if not exits:
            return json.dumps({"status": "error", "message": "exits must not be empty."})

        import math as _math
        x0, y0, x1, y1 = plate_bounds_mm
        width_m, depth_m = abs(x1 - x0) / 1000, abs(y1 - y0) / 1000
        gross_m2 = width_m * depth_m
        area_m2 = net_area_m2 if net_area_m2 > 0 else gross_m2
        diagonal_m = _math.hypot(width_m, depth_m)

        factors = rules["occupant_load_m2_per_person"]
        if occupancy not in factors:
            return json.dumps({"status": "error",
                               "message": f"Unknown occupancy '{occupancy}'. "
                                          f"Known: {', '.join(sorted(factors))}"})
        occupant_load = _math.ceil(area_m2 / factors[occupancy])

        checks, warnings = [], []

        def add(check, required, provided, passed, basis):
            checks.append({"check": check, "required": required,
                           "provided": provided, "passed": bool(passed), "basis": basis})

        # 1. number of exits
        exits_required = 4
        for tier in rules["exits_required_by_occupant_load"]:
            cap = tier["max_occupants"]
            if cap is None or occupant_load <= cap:
                exits_required = tier["exits"]
                break
        if stories > 1:
            exits_required = max(exits_required, 2)
        add("exit_count", exits_required, len(exits), len(exits) >= exits_required,
            "occupant-load tiers; multi-story business needs two (IBC-typical)")

        # 2. exit separation (straight line between the two most remote exits)
        frac = rules["exit_separation_fraction_of_diagonal"][
            "sprinklered" if sprinklered else "unsprinklered"]
        sep_req_m = diagonal_m * frac
        sep_m = 0.0
        for i in range(len(exits)):
            for j in range(i + 1, len(exits)):
                d = _math.hypot(exits[i]["x_mm"] - exits[j]["x_mm"],
                                exits[i]["y_mm"] - exits[j]["y_mm"]) / 1000
                sep_m = max(sep_m, d)
        if len(exits) >= 2:
            add("exit_separation_m", round(sep_req_m, 2), round(sep_m, 2),
                sep_m >= sep_req_m,
                f"diagonal {diagonal_m:.1f} m x {frac:g} ({'sprinklered' if sprinklered else 'unsprinklered'})")

        # 3. egress width: total, and per-exit minimum
        per_occ = rules["egress_width_mm_per_occupant"][
            "stairs" if stories > 1 else "doors_corridors"]
        total_req = occupant_load * per_occ
        total_prov = sum(float(e.get("width_mm", 0)) for e in exits)
        add("total_egress_width_mm", round(total_req), round(total_prov),
            total_prov >= total_req,
            f"{occupant_load} occupants x {per_occ} mm ({'stair' if stories > 1 else 'door'} factor)")
        min_w = (rules["min_widths_mm"]["exit_stair"] if occupant_load >= 50
                 else rules["min_widths_mm"]["stair_serving_under_50"]) if stories > 1 \
            else rules["min_widths_mm"]["door_clear"]
        narrow = [e.get("name", "?") for e in exits if float(e.get("width_mm", 0)) < min_w]
        add("min_exit_width_mm", min_w,
            min(float(e.get("width_mm", 0)) for e in exits),
            not narrow, "BCI 9.04 stair width" if stories > 1 else "door clear width")
        if narrow:
            warnings.append(f"Exits below minimum width: {', '.join(narrow)}.")

        # 4. travel distance
        if travel_distances_m:
            limit = rules["max_travel_distance_m"][
                "business_sprinklered" if sprinklered else "business_unsprinklered"]
            worst = max(travel_distances_m)
            basis = "business limits (IBC-typical)"
            if occupancy != "business":
                basis += f"; no {occupancy}-specific limit in the library - verify"
                warnings.append(f"Travel-distance limit uses business values for "
                                f"'{occupancy}' occupancy; verify the governing code.")
            add("max_travel_distance_m", limit, round(worst, 1), worst <= limit, basis)

        # 5. dead-end corridor
        if dead_end_m > 0:
            limit = rules["max_dead_end_corridor_m"][
                "sprinklered_business" if sprinklered else "default"]
            add("max_dead_end_m", limit, round(dead_end_m, 1), dead_end_m <= limit,
                "sprinklered" if sprinklered else "unsprinklered default")

        return json.dumps({
            "passed": all(c["passed"] for c in checks),
            "occupancy": occupancy,
            "occupant_load": occupant_load,
            "area_m2": round(area_m2, 1),
            "gross_area_m2": round(gross_m2, 1),
            "checks": checks,
            "warnings": warnings,
            "source_note": rules.get("source_note", ""),
        })


    return {"check_egress": check_egress}
