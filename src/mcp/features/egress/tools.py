"""Egress tool registration using the shared construction library."""
from almond_mcp.tool_response import error_payload
from almond_mcp.tool_declarations import public_tool
import json
from .inputs import validate_inputs


def register(mcp, context):
    """Register egress checks and return the server compatibility exports."""
    @public_tool(mcp, wrapped=True)
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
        """층별 출구 수·유효 폭·이격·보행거리 예비 검토. Rhino에서 형상이나 경로를 읽지 않으므로 실제 층 경계와 문 중심·유효 폭, 가장 불리한 보행 경로를 직접 측정해 입력. 출구가 둘 이상이면 가장 먼 두 출구의 직선 이격을 검사.

        출구는 문마다 한 번만 입력. 중복 중심, 좌표·폭 누락, 비유한 수, 음수 폭·거리·면적, 양의 정수가 아닌 층수, 면적이 0인 경계는 거절. 폭 0은 폭 부족 판정을 위해 허용.

        비업무 용도의 보행거리는 업무용 기준으로 대체. 스프링클러가 있는 막다른 복도도 업무용 기준을 쓰며 용도 경고는 별도로 나오지 않음. 경계값에서는 표시값 반올림으로 판정이 달라 보일 수 있음. BCI와 통상적인 IBC 수치를 사용하므로 source_note·warnings를 프로젝트 적용 법규와 대조.

        Args:
            plate_bounds_mm: 층 바닥 경계 [min_x, min_y, max_x, max_y].
            exits: 문마다 {"name": string, "x_mm": number, "y_mm": number, "width_mm": number}. 좌표는 문 중심, 폭은 유효 피난 폭.
            occupancy: business, mercantile, assembly_unconcentrated, classroom, residential, storage.
            stories: 출구가 담당하는 층수. 2층 이상이면 최소 2개 출구와 계단 폭 계수(7.6 mm/인) 적용.
            sprinklered: 전체 구역 설치 기준.
            net_area_m2: 실제 재실 면적. 0이면 층 경계의 직사각형 면적 사용.
            travel_distances_m: 입력 길이 중 최댓값 검사. 빈 배열이면 검사 생략.
            dead_end_m: 가장 긴 막다른 복도 길이. 0이면 검사 생략.
        """
        rules = context.construction_library.reference.get("egress_rules")
        if not rules:
            return json.dumps(error_payload("egress_rules missing from the construction manifest."))
        try:
            validate_inputs(plate_bounds_mm, exits, stories, net_area_m2, travel_distances_m, dead_end_m)
        except (ValueError, TypeError, OverflowError) as error:
            return json.dumps(error_payload(str(error)))

        import math as _math
        x0, y0, x1, y1 = plate_bounds_mm
        width_m, depth_m = abs(x1 - x0) / 1000, abs(y1 - y0) / 1000
        gross_m2 = width_m * depth_m
        area_m2 = net_area_m2 if net_area_m2 > 0 else gross_m2
        diagonal_m = _math.hypot(width_m, depth_m)

        factors = rules["occupant_load_m2_per_person"]
        if occupancy not in factors:
            return json.dumps(error_payload(f"Unknown occupancy '{occupancy}'. "
                                          f"Known: {', '.join(sorted(factors))}"))
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
                basis += '; no {0}-specific limit in the library - verify'.format(occupancy)
                warnings.append("Travel-distance limit uses business values for '{0}' occupancy; verify the governing code.".format(occupancy))
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
