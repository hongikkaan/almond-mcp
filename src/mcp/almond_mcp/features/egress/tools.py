"""Egress tool registration using the shared construction library."""
from almond_mcp.instruction_text import tool_instruction, read_instruction
import json


def register(mcp, context):
    """Register egress checks and return the server compatibility exports."""
    @mcp.tool()
    @tool_instruction(__file__, 'check_egress')
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
                basis += read_instruction(__file__, 'response-651').format(occupancy)
                warnings.append(read_instruction(__file__, 'response-656').format(occupancy))
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
