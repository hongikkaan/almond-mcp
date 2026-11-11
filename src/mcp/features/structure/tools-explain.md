# tools.py explain

## validate_structure

<!-- instruction:validate_structure -->
Rhino 구조 형상을 해석하고 설계기준에 따라 검토합니다.

Args:
    guids: 해석 범위에 포함되는 현재 Rhino 객체 GUID 문자열입니다.
    structure_type: 사용할 해석 템플릿입니다. 선택지: "beam"은 단순 보의 휨/처짐, "truss"는 축력/좌굴 해석, "shell"은 셸 응력/변위, "frame"은 프레임 모멘트/전단 해석, "canopy"는 캔틸레버 캐노피, "gridshell"은 대변형 그리드셸, "membrane"은 막 구조 형상 탐색, "highrise"는 고층 구조 시스템입니다.
    load_kn: 전체 부과하중(kN)입니다. native에서는 자유 절점에 하향(-Z) 균등 분배합니다. 바닥·자산 하중과 중복 계산되지 않게 산정하며 필요한 경우 0으로 입력합니다.
    material: 재료 유형: "Steel", "S355", "Concrete", "Wood", "Aluminium". 기본값은 "Steel"입니다.
    engine: auto, native, karamba 중 선택합니다. auto는 선형 프레임에 native를, 그 외에는 Karamba를 사용합니다. karamba는 사용 가능한 api, template, rule_based 순으로 시도합니다. 결과의 analysis_method와 warnings를 확인합니다.
    fixed_supports: True는 완전 고정 지점, False는 핀 지점(회전 자유)을 뜻합니다.
    self_weight: 부재 자중을 포함합니다.
    span_m: 부재가 모든 절점에서 분할됐을 때 L/250 한계에 사용할 구조 경간(미터)입니다. 예를 들어 6.2 m 장선을 3.1 m 구간 두 개로 그린 경우에 사용합니다. 네이티브 엔진 전용입니다.
    asset_loads: true이면 배치된 라이브러리 자산의 자중·내용물·재실자 하중을 추가합니다. 네이티브 엔진에서 사용합니다. 다른 하중 입력에 이미 포함한 무게를 중복 적용하지 않습니다.
    floor_load_kn_m2: 한 층에서 보로 둘러싸인 모든 구획에 적용할 부과 바닥 하중(kN/m2)입니다(예: 주거용 2.0, EN 1991-1-1의 category A). 보는 45도 분배 규칙에 따라 하중을 받습니다(2방향, 장단변비 2:1 초과 시 1방향). 네이티브 엔진 전용입니다. 설계기준의 바닥 하중에는 이동 가능한 가구와 사람이 이미 포함되므로, asset_loads는 무거운 특정 물품에 대해서만 함께 사용하고 중복 계산을 피하려면 load_kn을 0으로 설정합니다.
    floor_dead_kn_m2: 같은 구획에 적용할 추가 고정하중(kN/m2)입니다. 바닥 구성층과 마감 등을 포함합니다.
    design_basis: "en1990"(기본값)은 SLS 특성 조합(G + Q)에서 처짐을, ULS 1.35 G + 1.5 Q에서 부재를 검토합니다. G는 자중, 바닥 구성층, 배치된 물품의 중량이고, Q는 load_kn, 용도별 바닥 활하중, 내용물, 재실자입니다. "unfactored"는 둘 다 G + Q에서 검토합니다(Karamba 경로의 기준). 네이티브 엔진에 적용됩니다.
    uls_combination: "6.10" 또는 "6.10ab"입니다. "6.10ab"는 부재별로 6.10a와 6.10b 중 더 불리한 결과를 사용합니다. 기본값은 설계기준이 선택한 식입니다(Eurocode 프로필: 6.10). 특정 식을 지정한 프로필은 요청보다 우선하며 경고를 반환합니다.
    connections: "rigid"(기본값)는 모든 접합부가 모멘트를 전달합니다. "simple"은 보를 핀 접합(강축 휨 해제)으로, 가새를 양축 핀 접합으로 처리하되, 다른 부재가 같은 선상으로 계속 이어지는 지점이 아니라 해당 부재가 끝나는 지점에 적용하며 기둥은 연속으로 유지합니다. 일반적인 볼트 접합 강구조와 목구조 프레임은 "simple"에 더 가깝습니다. 강접합은 보 처짐을 실제보다 유리하게 보이게 할 수 있습니다. 곡선의 사용자 텍스트 almond:release = "pinned" | "pinned_start" | "pinned_end" | "rigid"는 두 모드보다 우선합니다. 네이티브 엔진에 적용됩니다.
    stability: "auto"(기본값)는 모든 ULS 조합의 탄성 임계 하중 계수 alpha_cr(EN 1993-1-1 5.2.1)과 +/-x 및 +/-y 방향의 횡변위 초기 불완전성 phi = 1/200 x alpha_h x alpha_m(5.3.2)을 적용합니다. alpha_cr < 10이면 2차(P-Delta) ULS 해석을 실행하며, alpha_cr <= 1이면 불안정으로 실패 처리합니다. "off"는 초기 불완전성 없는 1차 해석입니다.
    design_code: 설계기준 또는 국가 부록에서 정하는 수치(gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, 처짐 한계)에 사용할 설계기준 프로필입니다. "eurocode"(기본값, EN 권장값), analysis_03-list_design_codes tool의 프로필 또는 "off"를 사용합니다. "off"는 부분계수 없이 G + Q를 적용하며 design_basis="unfactored"와 같습니다. 결과의 "design_code"에는 사용한 값과 검증되지 않은 값이 포함됩니다.
    detail: true이면 네이티브 해석의 부재별 단면력·사용률·처짐과 지점 반력을 포함합니다.
    fabrication: 중공 강재 단면(CHS/RHS)은 "cold_formed"(기본값, EN 10219, 좌굴 곡선 c) 또는 "hot_finished"(EN 10210, 곡선 a, S460은 a0)입니다. 좌굴 내력에 최대 약 23% 차이가 있으므로, hot_finished는 명시된 경우에만 사용합니다.
<!-- /instruction:validate_structure -->

## list_design_codes

<!-- instruction:list_design_codes -->
구조 해석에 사용할 설계기준 프로필을 조회합니다.

Args:
    include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
    field_groups: 상세 그룹: parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
<!-- /instruction:list_design_codes -->

## visualize_structure

<!-- instruction:visualize_structure -->
구조 해석 결과를 임시 뷰포트 오버레이로 표시합니다.

Args:
    guids: 구조 축선의 곡선 GUID와 지점을 표시하는 점 GUID입니다(fixed_supports 참조). 점이 없으면 최하단 절점을 지점으로 사용합니다.
    load_kn: 자유 절점에 하향(-Z)으로 균등 분배할 전체 부과하중(kN)입니다.
    material: "Steel", "S355", "Concrete", "Wood", "Aluminium" 중 하나입니다.
    beam_diameter_mm: 선택 항목인 원형 부재 외경(밀리미터)입니다.
    beam_wall_mm: 선택 항목인 중공 부재의 벽 두께(밀리미터)입니다.
    self_weight: 중력을 포함합니다.
    fixed_supports: True는 완전 고정 지점, False는 핀 지점(회전 자유)을 뜻합니다.
    deflection_limit_ratio: 경간/비율 한계입니다. 예를 들어 L/250은 250입니다. 기본값은 설계기준의 한계입니다(Eurocode 프로필: 250).
    span_m: 한계에 사용할 기준 경간(미터)입니다. 기본값은 가장 긴 부재입니다. 부재가 모든 절점에서 분할됐다면 지정합니다. 예: 6.2 m 장선을 3.1 m 구간 두 개로 그린 경우.
    color_by: "displacement" 또는 "utilization"입니다.
    scale: 변형 과장 배율입니다. 생략하면 자동으로 정합니다(경간의 약 6%).
    reveal: 그릴 부재의 비율이며 0..1 범위입니다. 단계별 시공 재생에 사용합니다.
    reanalyze: False이면 마지막 계산을 재사용하고 표시(scale / color_by / reveal / physics / title)만 변경합니다. 애니메이션에 사용할 수 있을 만큼 계산 부담이 작습니다.
    physics: False이면 해석 오버레이 없이 같은 부재를 일반 형상으로 그립니다("physics off"). 전후 비교에 사용합니다.
    display_guids: 이 부재들만 그립니다(예: 단면 보기를 위한 한 줄의 프레임). 해석은 여전히 guids의 모든 부재를 포함합니다.
    title: 범례 제목입니다.
    clear: 오버레이를 제거합니다.
    engine: "auto"(기본값), "native", "karamba" 중 하나입니다. "auto"는 Karamba 없이 Almond 네이티브 프레임 솔버를 사용하되, 선택에 셸이 있거나 브리지가 모델을 내보낼 수 없으면 Karamba를 사용합니다.
    asset_loads: analysis_04-validate_structure tool와 동일하게 배치된 라이브러리 자산의 하중을 추가합니다(네이티브 엔진). 하중 작용점에 하중 화살표를 그립니다.
    floor_load_kn_m2: 한 층에서 보로 둘러싸인 모든 구획에 적용할 부과 바닥 하중(kN/m2)입니다(예: 주거용 2.0, EN 1991-1-1의 category A). 보는 45도 분배 규칙에 따라 하중을 받습니다(2방향, 장단변비 2:1 초과 시 1방향). 네이티브 엔진 전용입니다. 설계기준의 바닥 하중에는 이동 가능한 가구와 사람이 이미 포함되므로, asset_loads는 무거운 특정 물품에 대해서만 함께 사용하고 중복 계산을 피하려면 load_kn을 0으로 설정합니다.
    floor_dead_kn_m2: 같은 구획에 적용할 추가 고정하중(kN/m2)입니다. 바닥 구성층과 마감 등을 포함합니다.
    design_basis: "en1990"(기본값)은 SLS 특성 조합(G + Q)에서 처짐을, ULS 1.35 G + 1.5 Q에서 부재를 검토합니다. G는 자중, 바닥 구성층, 배치된 물품의 중량이고, Q는 load_kn, 용도별 바닥 활하중, 내용물, 재실자입니다. "unfactored"는 둘 다 G + Q에서 검토합니다(Karamba 경로의 기준). 네이티브 엔진에 적용됩니다.
    uls_combination: "6.10" 또는 "6.10ab"입니다. "6.10ab"는 부재별로 6.10a와 6.10b 중 더 불리한 결과를 사용합니다. 기본값은 설계기준이 선택한 식입니다(Eurocode 프로필: 6.10). 특정 식을 지정한 프로필은 요청보다 우선하며 경고를 반환합니다.
    connections: analysis_04-validate_structure tool와 동일한 "rigid" 또는 "simple"입니다. 핀 접합 단부는 작은 원으로 그립니다.
    stability: analysis_04-validate_structure tool와 동일한 "auto" 또는 "off"입니다.
    design_code: 설계기준 또는 국가 부록에서 정하는 수치(gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, 처짐 한계)에 사용할 설계기준 프로필입니다. "eurocode"(기본값, EN 권장값), analysis_03-list_design_codes tool의 프로필 또는 "off"를 사용합니다. "off"는 부분계수 없이 G + Q를 적용하며 design_basis="unfactored"와 같습니다. 결과의 "design_code"에는 사용한 값과 검증되지 않은 값이 포함됩니다.
    fabrication: 중공 강재 단면(CHS/RHS)은 "cold_formed"(기본값, EN 10219, 좌굴 곡선 c) 또는 "hot_finished"(EN 10210, 곡선 a, S460은 a0)입니다. 좌굴 내력에 최대 약 23% 차이가 있으므로, hot_finished는 명시된 경우에만 사용합니다.
    view: "deflection"(기본값) 또는 "buckling"입니다. "buckling"은 처짐 형상 대신 지배 ULS 조합의 첫 번째 좌굴 모드를 alpha_cr과 함께 그립니다(STABLE >= 10, SWAY-SENSITIVE 1-10, UNSTABLE <= 1).
<!-- /instruction:visualize_structure -->

## export_structural_report

<!-- instruction:export_structural_report -->
저장된 구조 검증 이력을 Markdown 보고서로 작성합니다.

Args:
    path: 관리형 세션에서는 선택한 Plan 산출물 디렉터리 아래의 상대 파일 경로이며, 기본값은 reports/structural-validation.md입니다. 독립 실행의 기본값은 사용자 데이터의 reports/structural-validation-<timestamp>.md입니다.
    limit: 포함할 최대 실행 개수입니다. 기본값은 50, 최댓값은 500입니다.
<!-- /instruction:export_structural_report -->

## response-981

<!-- instruction:response-981 -->
- **native** and **api** runs use finite element analysis. Their reactions_kn
<!-- /instruction:response-981 -->

## response-982

<!-- instruction:response-982 -->
  should balance the modeled load for the reported load combination,
<!-- /instruction:response-982 -->

## response-983

<!-- instruction:response-983 -->
- Known gaps in karambaCommon 3.1.60519 (issue #6): api-mode
<!-- /instruction:response-983 -->

## response-984

<!-- instruction:response-984 -->
  max_deflection and per-element utilization may read 0.0 due to
<!-- /instruction:response-984 -->

## response-985

<!-- instruction:response-985 -->
  signature drift — trust reactions and stability diagnostics;
<!-- /instruction:response-985 -->

## response-986

<!-- instruction:response-986 -->
  cross-check deflection against the rule_based estimate.
<!-- /instruction:response-986 -->

## response-987

<!-- instruction:response-987 -->
- rule_based results are labeled LOW CONFIDENCE for a reason: treat
<!-- /instruction:response-987 -->

## response-988

<!-- instruction:response-988 -->
  them as sanity checks, not engineering.
<!-- /instruction:response-988 -->

## response-1026

<!-- instruction:response-1026 -->
No validation runs recorded yet - call analysis_04-validate_structure tool first.
<!-- /instruction:response-1026 -->

## response-1031

<!-- instruction:response-1031 -->
view='buckling' draws the buckling mode.
<!-- /instruction:response-1031 -->
