# tools.py explain

## check_egress

<!-- instruction:check_egress -->
피난 조건을 예비 검토합니다.

Args:
    plate_bounds_mm: mm 단위의 층 바닥 경계 [min_x, min_y, max_x, max_y]입니다. 전체 면적과 출구 이격거리에 사용하는 대각선을 결정합니다.
    exits: 출구(계단실 문 또는 외부 출입문)마다 항목 하나를 제공합니다: {"name": str, "x_mm": float, "y_mm": float, "width_mm": float}. 위치는 문 중심이며, 너비는 피난에 사용할 수 있는 유효 너비입니다.
    occupancy: 재실 인원 산정에 사용할 키: business, mercantile, assembly_unconcentrated, classroom, residential, storage.
    stories: 담당하는 층수입니다. 1을 초과하면 최소 2개 출구가 필요하며, 필요 출구 너비에는 문 계수(5.1) 대신 계단 계수(재실자당 7.6 mm)를 사용합니다.
    sprinklered: 전체에 스프링클러가 설치됐는지 여부입니다. 이격 비율, 보행거리, 막다른 복도 길이 제한에 영향을 줍니다.
    net_area_m2: 재실 면적을 대체합니다. 0이면 전체 바닥 면적을 사용합니다.
    travel_distances_m: 측정한 최악 조건의 보행거리입니다(예: 그려진 피난 경로에서 측정). 비워 두면 보행거리 검사를 건너뜁니다.
    dead_end_m: 가장 긴 막다른 복도의 길이(미터)입니다. 0이면 검사를 건너뜁니다.
<!-- /instruction:check_egress -->

## response-651

<!-- instruction:response-651 -->
; no {0}-specific limit in the library - verify
<!-- /instruction:response-651 -->

## response-656

<!-- instruction:response-656 -->
Travel-distance limit uses business values for '{0}' occupancy; verify the governing code.
<!-- /instruction:response-656 -->
