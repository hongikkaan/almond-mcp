# tools.py explain

## check_egress

<!-- instruction:check_egress -->
코어와 출구를 배치한 뒤, 상세 설계 전에 층의 피난 조건을 예비 검토합니다. Rhino에서 형상이나 경로를 자동으로 읽지 않으므로 층 경계와 출구별 중심·유효 폭을 직접 확인해 입력하세요.

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
<!-- /instruction:check_egress -->

## response-651

<!-- instruction:response-651 -->
; no {0}-specific limit in the library - verify
<!-- /instruction:response-651 -->

## response-656

<!-- instruction:response-656 -->
Travel-distance limit uses business values for '{0}' occupancy; verify the governing code.
<!-- /instruction:response-656 -->
