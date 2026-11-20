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
        """코어와 출구를 배치한 뒤, 상세 설계 전에 층의 피난 조건을 예비 검토합니다. Rhino에서 형상이나 경로를 자동으로 읽지 않으므로 층 경계와 출구별 중심·유효 폭을 직접 확인해 입력하세요.

        입력 경계의 직사각형으로 기본 바닥 면적과 출구 이격 기준의 대각선을 계산합니다. 실제 재실 면적이 다르면 별도로 입력하세요. 보행거리와 막다른 복도는 길이를 입력해야 검사합니다. 가장 불리한 보행 경로를 직접 측정하세요. 이 툴은 경로를 찾거나 입력한 경로가 최악인지 확인하지 않습니다.

        출구 수와 총·최소 폭을 검사하고, 출구가 둘 이상이면 가장 먼 두 출구의 직선 이격을 검사합니다. 용도·스프링클러·담당 층수의 기본값이 실제 조건과 맞는지 확인하세요. 비업무 용도의 보행거리에는 업무용 기준을 대신 쓰며, 막다른 복도도 스프링클러가 있으면 업무용 기준을 사용하지만 용도 경고는 나오지 않습니다.

        출구는 실제 문마다 한 번만 입력하세요. 같은 중심 좌표를 중복하면 오류를 반환합니다. 좌표·폭 누락, 비유한 수, 음수 폭·거리·면적, 1 미만 또는 정수가 아닌 층수, 면적이 0인 경계도 계산 전에 거절합니다. 폭 0은 유효 폭 부족 판정을 위해 허용합니다.

        반환된 JSON의 checks에 포함된 검사의 기준값·입력값·판정을 확인하고 생략된 검사와 구분하세요. passed는 수행한 검사만의 결과입니다. 일부 출력값이 반올림돼 경계값에서는 표시값과 판정이 달라 보일 수 있습니다. 미달 항목의 배치·폭·경로를 검토하고 측정값을 갱신해 다시 검사하세요.

        BCI 체계와 통상적인 IBC 수치를 사용합니다. source_note와 warnings를 읽고 프로젝트에 적용되는 법규와 대조하세요. 경고가 없거나 검사가 통과해도 모든 피난 조건의 적합성이 확인된 것은 아닙니다.

        Args:
            plate_bounds_mm: 층 바닥 경계 [min_x, min_y, max_x, max_y](mm).
            exits: 출구마다 {"name": string, "x_mm": number, "y_mm": number, "width_mm": number}. 좌표는 문 중심(mm), 폭은 유효 피난 폭(mm).
            occupancy: 용도: business, mercantile, assembly_unconcentrated, classroom, residential, storage. 기본값 business.
            stories: 출구가 담당하는 층수. 기본값 1. 1 초과면 최소 2개 출구와 계단 폭 계수(7.6mm/인) 적용.
            sprinklered: 전체 스프링클러 설치 여부. 기본값 true.
            net_area_m2: 재실 면적(m²). 기본값 0이며, 0이면 경계 직사각형 면적 사용.
            travel_distances_m: 측정한 보행거리(m) 배열. 입력 중 최댓값을 검사하며, 기본값 []는 검사 생략.
            dead_end_m: 가장 긴 막다른 복도 길이(m). 기본값 0이며, 0이면 검사 생략.
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
