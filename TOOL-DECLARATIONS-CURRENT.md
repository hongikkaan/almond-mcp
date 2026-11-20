# 현행 툴 선언

## 기준 및 선언 표기

현재 체크아웃의 beyond·CoS가 공개하는 도구 81개를 정리합니다. 두 경로의 `tools/list` 전체 응답을 대조했으며 도구 설명과 입력·출력 스키마가 같습니다.

- 기준: 이 문서와 함께 커밋된 소스. 수집일 2026-11-20.
- 수집 경로: `src/cos/codex_host.py`와 `src/cos/cos_host.py`가 사용하는 공용 `external_host.main`의 stdio `initialize`·`tools/list`. 격리된 데이터 폴더에서 수집했으며 Rhino 연결·도구 실행은 하지 않았습니다.
- 실행 패키지: almond-mcp 0.7.0rc2 / fastmcp 4.1.0 / mcp 2.3.0 / mcp-types 2.3.0.
- 선언 SHA-256: `a4af576e60c6a511aed2561a62cfc776050f4b49a8c1b1382ee4615958f42c3f`. 이름순 tools 배열을 UTF-8 JSON(`sort_keys=True`, `ensure_ascii=False`, `separators=(",", ":")`)으로 직렬화한 값입니다.
- 도구명·설명 원본은 MCP 구현 함수와 그 docstring, 출력 원본은 `src/mcp/output_contracts.py`, 공통 스키마 기준은 `tests/integration/tool_schemas.json`입니다. 외부 연결 도구는 `src/cos/external_host.py`에서 조립합니다.

필수 인자와 선택 인자는 `?`로 구분합니다. 배열은 `Array<T>`, null 허용은 `| null`입니다. 기본값·범위는 주석에 표시합니다. JSON Schema의 검증 의미가 우선하며 TypeScript 표기는 읽기용입니다(`oneOf`의 배타성 등은 TypeScript로 강제하지 않습니다). `additionalProperties`가 허용된 객체는 인덱스 시그니처로 표시합니다.

`mcp__rhino__`는 예시 연결 이름이며 실제 공개 도구명은 각 제목에 표시합니다. `CallToolResult<T>`의 `T`는 MCP의 구조화된 출력입니다. `result: string`이면 JSON 문자열 wrapper이며, 공개 `contentSchema`가 있는 경우 별도의 `DecodedResult`로 내부 결과를 함께 표시합니다. 이미지·텍스트 content 블록과 오류 여부 등 MCP envelope는 이 타입 밖에 있습니다.

## 적용 범위

이 목록은 외부 연결기 beyond·CoS의 공개 계약을 다룹니다. RhinoTerminal과 관리 실행기의 문서 전용 `rhino_session`은 [연결 경로 사양](src/mcp/runtime/CONNECTION-SPEC.md)을, 독립 Python MCP는 [MCP 사양](src/mcp/SPEC.md)을 따릅니다. [Almond Project Dashboard](src/mcp/runtime/dashboard/README.md)는 로컬 HTTP로 기존 SQLite를 읽는 화면이며, 이번 `tools/list`에서 Dashboard 도구는 등록되지 않았습니다.

## 공통 안내와 실행 결과

- 외부 서버의 경로별 소개는 `serverInfo.description`과 `initialize.instructions` 첫머리에 들어갑니다. 공용 `modeling_guidance.py`가 구성한 `BASIC-INSTRUCTIONS.md`와 `design_judgment.md` 본문은 `initialize.instructions`의 소개 뒤에 이어집니다. 개별 도구 설명은 `tools/list`의 `description`에서 전달됩니다. `context_01-get_policy` tool은 정책을 명시적으로 조회하는 경로이며 기본 정책은 BASIC입니다. 클라이언트가 초기 instructions를 모델에게 표시·준수하게 하는 것까지 서버가 강제하지는 않습니다.
- `context_01-get_policy` tool은 Rhino 연결을 선택하기 전에도 조회할 수 있습니다. `policy="metadata"`는 Rhino 메타데이터 편집 지침과 객체 키 사전을 함께 반환합니다. `connect_02-session` tool 또는 `connect_03-start_session` tool으로 선택한 연결이 모델 호출에 적용됩니다. `script_03-get_execution` tool에 `request_id`를 지정하면 원래 실행 연결의 결과를 회수합니다.
- 외부 실행의 첫 완료 대기는 `min(요청 timeout, 60초)`입니다. 작업이 계속되면 `pending`과 실제 실행 `request_id`를 반환하고 같은 ID로 완료를 조회합니다. 외부 클라이언트 600초 제한은 이 최초 대기와 별개입니다. 대기 종료·취소·오류는 실행 중단이나 문서 rollback의 증거가 아니므로 결과가 불확실한 수정을 자동 재실행하지 않습니다. Terminal 등 경로별 계약은 [RhinoCode 실행 계약](src/mcp/runtime/RHINOCODE-SPEC.md)과 [외부 연결기 SPEC](src/cos/SPEC.md)을 따릅니다.

## 선언 갱신 절차

공개 계약을 변경할 때 [저장소 지침](AGENTS.md)에 따라 현재 체크아웃의 두 외부 서버를 격리된 데이터 폴더에서 시작해 `initialize`와 `tools/list`를 수집합니다. 전체 도구 목록·description·inputSchema·outputSchema가 두 경로에서 일치하는지 확인하고 아래 선언을 갱신합니다. 도구의 추가·삭제·이름 변경, 기본값·nullable·중첩 입력·출력 wrapper도 대조합니다. 초기 안내 전달 방식은 공용 안내 구현과 별도로 대조합니다. 수집을 위해 Rhino에 연결하거나 모델링 도구를 호출할 필요는 없습니다.

## analysis

### 1. analysis\_01-check\_egress

```txt
코어와 출구를 배치한 뒤, 상세 설계 전에 층의 피난 조건을 예비 검토합니다. Rhino에서 형상이나 경로를 자동으로 읽지 않으므로 층 경계와 출구별 중심·유효 폭을 직접 확인해 입력하세요.

입력 경계의 직사각형으로 기본 바닥 면적과 출구 이격 기준의 대각선을 계산합니다. 실제 재실 면적이 다르면 별도로 입력하세요. 보행거리와 막다른 복도는 길이를 입력해야 검사합니다. 가장 불리한 보행 경로를 직접 측정하세요. 이 툴은 경로를 찾거나 입력한 경로가 최악인지 확인하지 않습니다.

출구 수와 총·최소 폭을 검사하고, 출구가 둘 이상이면 가장 먼 두 출구의 직선 이격을 검사합니다. 용도·스프링클러·담당 층수의 기본값이 실제 조건과 맞는지 확인하세요. 비업무 용도의 보행거리에는 업무용 기준을 대신 쓰며, 막다른 복도도 스프링클러가 있으면 업무용 기준을 사용하지만 용도 경고는 나오지 않습니다.

출구는 실제 문마다 한 번만 입력하세요. 같은 중심 좌표를 중복하면 오류를 반환합니다. 좌표·폭 누락, 비유한 수, 음수 폭·거리·면적, 1 미만 또는 정수가 아닌 층수, 면적이 0인 경계도 계산 전에 거절합니다. 폭 0은 유효 폭 부족 판정을 위해 허용합니다.

반환된 JSON의 checks에 포함된 검사의 기준값·입력값·판정을 확인하고 생략된 검사와 구분하세요. passed는 수행한 검사만의 결과입니다. 일부 출력값이 반올림돼 경계값에서는 표시값과 판정이 달라 보일 수 있습니다. 미달 항목의 배치·폭·경로를 검토하고 측정값을 갱신해 다시 검사하세요.

BCI 체계와 통상적인 IBC 수치를 사용합니다. source_note와 warnings를 읽고 프로젝트에 적용되는 법규와 대조하세요. 경고가 없거나 검사가 통과해도 모든 피난 조건의 적합성이 확인된 것은 아닙니다.
```

```ts
declare const tools: {
  mcp__rhino__analysis_01_check_egress(args: {
    // 층 바닥 경계 [min_x, min_y, max_x, max_y](mm).
    plate_bounds_mm: Array<number>;
    // 출구마다 {"name": string, "x_mm": number, "y_mm": number, "width_mm": number}. 좌표는 문 중심(mm), 폭은 유효 피난 폭(mm).
    exits: Array<{
      [key: string]: unknown;
    }>;
    // 용도: business, mercantile, assembly_unconcentrated, classroom, residential, storage. 기본값 business.
    // default: "business"
    occupancy?: string;
    // 출구가 담당하는 층수. 기본값 1. 1 초과면 최소 2개 출구와 계단 폭 계수(7.6mm/인) 적용.
    // default: 1
    stories?: number;
    // 전체 스프링클러 설치 여부. 기본값 true.
    // default: true
    sprinklered?: boolean;
    // 재실 면적(m²). 기본값 0이며, 0이면 경계 직사각형 면적 사용.
    // default: 0.0
    net_area_m2?: number;
    // 측정한 보행거리(m) 배열. 입력 중 최댓값을 검사하며, 기본값 []는 검사 생략.
    // default: []
    travel_distances_m?: Array<number>;
    // 가장 긴 막다른 복도 길이(m). 기본값 0이며, 0이면 검사 생략.
    // default: 0.0
    dead_end_m?: number;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 실제 수행한 검사만 합산. 빠진 경로 검사를 통과한 것이 아님
  passed?: boolean;
  // 건물 용도입니다.
  occupancy?: string;
  // 면적과 용도별 1인당 면적으로 계산해 올림한 재실 인원입니다.
  occupant_load?: number;
  // 입력한 면적(m²)입니다.
  area_m2?: number;
  // 경계 직사각형 면적이지 불규칙 바닥의 실측 면적은 아님
  gross_area_m2?: number;
  // 수행한 항목별 검사 결과입니다.
  checks?: Array<{
    // 검사 항목 이름입니다.
    check?: string;
    // 검사 항목에서 요구하는 최소값입니다.
    required?: number;
    // 현재 입력에서 제공한 값입니다.
    provided?: number;
    // 이 항목이 비교 기준을 충족했는지 나타냅니다.
    passed?: boolean;
    // 해당 비교의 근거
    basis?: string;
    [key: string]: unknown;
  }>;
  // 결과를 해석할 때 확인할 경고입니다.
  warnings?: Array<string>;
  // 계산 기준의 출처와 적용 범위입니다.
  source_note?: string;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 2. analysis\_02-export\_structural\_report

```txt
저장된 구조 검증 이력을 Markdown 보고서로 작성합니다.

각 실행의 실제 엔진과 적용 입력을 함께 표시합니다. 저장 당시 입력이 없던 이전 이력은 알 수 없음으로 표시하며, 현재 기본값으로 과거 설정을 채우지 않습니다.
```

```ts
declare const tools: {
  mcp__rhino__analysis_02_export_structural_report(args: {
    // 관리형 세션에서는 선택한 Plan 산출물 디렉터리 아래의 상대 파일 경로이며, 기본값은 reports/structural-validation.md입니다. 독립 실행의 기본값은 사용자 데이터의 reports/structural-validation-<timestamp>.md입니다.
    // default: ""
    path?: string;
    // 포함할 최대 실행 개수입니다. 기본값은 50, 최댓값은 500입니다.
    // default: 50
    limit?: number;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 작성된 Markdown 파일
  path?: string;
  // 실제 포함한 저장 실행 수
  runs?: number;
  // 가장 최근 저장된 실행 방식
  latest_method?: string;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 3. analysis\_03-list\_design\_codes

```txt
구조 해석에 사용할 설계기준 프로필을 조회합니다.
```

```ts
declare const tools: {
  mcp__rhino__analysis_03_list_design_codes(args: {
    // true이면 후속 호출에 사용할 ID를 포함합니다.
    // default: false
    include_ids?: boolean;
    // 상세 그룹: parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 기본 설계 기준 ID입니다.
  default?: string;
  // 설계 기준 프로필과 요청한 매개변수입니다.
  profiles?: Array<{
    // analysis_04-validate_structure tool / analysis_05-visualize_structure tool의 design_code에 사용
    id?: string;
    // 이름입니다.
    name?: string;
    // 기준의 근거입니다.
    basis?: string;
    // 프로필 값 검증이며 프로젝트의 법규 준수/구조 승인과 다름
    verified?: boolean;
    // 검증되지 않은 매개변수 목록입니다.
    unverified?: Array<unknown>;
    // 허용 처짐 L/n의 분모 n입니다.
    deflection_limit_ratio?: number;
    // 프로필의 권장 바닥 활하중입니다. 단위는 kN/m²입니다.
    imposed_floor_kn_m2?: {
      [key: string]: unknown;
    };
    [key: string]: unknown;
  }>;
  // 로딩 중 거부된 사용자 프로필 문제
  problems?: Array<unknown>;
  // 사용자 설계 기준 프로필 폴더입니다.
  user_dir?: string;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 4. analysis\_04-validate\_structure

```txt
Rhino 구조 형상을 해석하고 설계기준에 따라 검토합니다.

완료된 해석은 요청 옵션과 실제 적용 엔진·입력·계산 결과를 이력에 보관합니다. native 이력은 내보낸 모델과 적용 하중 입력을 포함합니다. 이전 이력에 저장되지 않은 옵션은 현재 기본값으로 추정하지 않고 알 수 없음으로 표시합니다.
```

```ts
declare const tools: {
  mcp__rhino__analysis_04_validate_structure(args: {
    // 해석 범위에 포함되는 현재 Rhino 객체 GUID 문자열입니다.
    guids: Array<string>;
    // 사용할 해석 템플릿입니다. 선택지: "beam"은 단순 보의 휨/처짐, "truss"는 축력/좌굴 해석, "shell"은 셸 응력/변위, "frame"은 프레임 모멘트/전단 해석, "canopy"는 캔틸레버 캐노피, "gridshell"은 대변형 그리드셸, "membrane"은 막 구조 형상 탐색, "highrise"는 고층 구조 시스템입니다.
    // default: "beam"
    structure_type?: string;
    // 전체 부과하중(kN)입니다. native에서는 자유 절점에 하향(-Z) 균등 분배합니다. 바닥·자산 하중과 중복 계산되지 않게 산정하며 필요한 경우 0으로 입력합니다.
    // default: 10.0
    load_kn?: number;
    // 재료 유형: "Steel", "S355", "Concrete", "Wood", "Aluminium". 기본값은 "Steel"입니다.
    // default: "Steel"
    material?: string;
    // auto, native, karamba 중 선택합니다. auto는 선형 프레임에 native를, 그 외에는 Karamba를 사용합니다. karamba는 사용 가능한 api, template, rule_based 순으로 시도합니다. 결과의 analysis_method와 warnings를 확인합니다.
    // default: "auto"
    engine?: string;
    // True는 완전 고정 지점, False는 핀 지점(회전 자유)을 뜻합니다.
    // default: true
    fixed_supports?: boolean;
    // 부재 자중을 포함합니다.
    // default: true
    self_weight?: boolean;
    // 부재가 모든 절점에서 분할됐을 때 L/250 한계에 사용할 구조 경간(미터)입니다. 예를 들어 6.2 m 장선을 3.1 m 구간 두 개로 그린 경우에 사용합니다. 네이티브 엔진 전용입니다.
    // default: null
    span_m?: (number | null);
    // true이면 배치된 라이브러리 자산의 자중·내용물·재실자 하중을 추가합니다. 네이티브 엔진에서 사용합니다. 다른 하중 입력에 이미 포함한 무게를 중복 적용하지 않습니다.
    // default: false
    asset_loads?: boolean;
    // 한 층에서 보로 둘러싸인 모든 구획에 적용할 부과 바닥 하중(kN/m2)입니다(예: 주거용 2.0, EN 1991-1-1의 category A). 보는 45도 분배 규칙에 따라 하중을 받습니다(2방향, 장단변비 2:1 초과 시 1방향). 네이티브 엔진 전용입니다. 설계기준의 바닥 하중에는 이동 가능한 가구와 사람이 이미 포함되므로, asset_loads는 무거운 특정 물품에 대해서만 함께 사용하고 중복 계산을 피하려면 load_kn을 0으로 설정합니다.
    // default: 0.0
    floor_load_kn_m2?: number;
    // 같은 구획에 적용할 추가 고정하중(kN/m2)입니다. 바닥 구성층과 마감 등을 포함합니다.
    // default: 0.0
    floor_dead_kn_m2?: number;
    // "en1990"(기본값)은 SLS 특성 조합(G + Q)에서 처짐을, ULS 1.35 G + 1.5 Q에서 부재를 검토합니다. G는 자중, 바닥 구성층, 배치된 물품의 중량이고, Q는 load_kn, 용도별 바닥 활하중, 내용물, 재실자입니다. "unfactored"는 둘 다 G + Q에서 검토합니다(Karamba 경로의 기준). 네이티브 엔진에 적용됩니다.
    // default: "en1990"
    design_basis?: string;
    // "6.10" 또는 "6.10ab"입니다. "6.10ab"는 부재별로 6.10a와 6.10b 중 더 불리한 결과를 사용합니다. 기본값은 설계기준이 선택한 식입니다(Eurocode 프로필: 6.10). 특정 식을 지정한 프로필은 요청보다 우선하며 경고를 반환합니다.
    // default: null
    uls_combination?: (string | null);
    // "rigid"(기본값)는 모든 접합부가 모멘트를 전달합니다. "simple"은 보를 핀 접합(강축 휨 해제)으로, 가새를 양축 핀 접합으로 처리하되, 다른 부재가 같은 선상으로 계속 이어지는 지점이 아니라 해당 부재가 끝나는 지점에 적용하며 기둥은 연속으로 유지합니다. 일반적인 볼트 접합 강구조와 목구조 프레임은 "simple"에 더 가깝습니다. 강접합은 보 처짐을 실제보다 유리하게 보이게 할 수 있습니다. 곡선의 사용자 텍스트 almond:release = "pinned" | "pinned_start" | "pinned_end" | "rigid"는 두 모드보다 우선합니다. 네이티브 엔진에 적용됩니다.
    // default: "rigid"
    connections?: string;
    // "auto"(기본값)는 모든 ULS 조합의 탄성 임계 하중 계수 alpha_cr(EN 1993-1-1 5.2.1)과 +/-x 및 +/-y 방향의 횡변위 초기 불완전성 phi = 1/200 x alpha_h x alpha_m(5.3.2)을 적용합니다. alpha_cr < 10이면 2차(P-Delta) ULS 해석을 실행하며, alpha_cr <= 1이면 불안정으로 실패 처리합니다. "off"는 초기 불완전성 없는 1차 해석입니다.
    // default: "auto"
    stability?: string;
    // 설계기준 또는 국가 부록에서 정하는 수치(gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, 처짐 한계)에 사용할 설계기준 프로필입니다. "eurocode"(기본값, EN 권장값), analysis_03-list_design_codes tool의 프로필 또는 "off"를 사용합니다. "off"는 부분계수 없이 G + Q를 적용하며 design_basis="unfactored"와 같습니다. 결과의 "design_code"에는 사용한 값과 검증되지 않은 값이 포함됩니다.
    // default: "eurocode"
    design_code?: string;
    // true이면 네이티브 해석의 부재별 단면력·사용률·처짐과 지점 반력을 포함합니다.
    // default: false
    detail?: boolean;
    // 중공 강재 단면(CHS/RHS)은 "cold_formed"(기본값, EN 10219, 좌굴 곡선 c) 또는 "hot_finished"(EN 10210, 곡선 a, S460은 a0)입니다. 좌굴 내력에 최대 약 23% 차이가 있으므로, hot_finished는 명시된 경우에만 사용합니다.
    // default: "cold_formed"
    fabrication?: string;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // indicative인 경우 null 가능. 구조 안전 인증을 뜻하지 않음
  passed?: boolean | null;
  // 구조 유형입니다.
  structure_type?: string;
  // 재료입니다.
  material?: string;
  // 경고·가정·미검증 값과 함께 해석
  confidence?: string;
  // 구조 검토의 수치와 부재별 결과입니다.
  results?: {
    // 해석 방식입니다.
    analysis_method?: string;
    // 최대 처짐(mm)입니다.
    max_deflection_mm?: number;
    // 허용 처짐(mm)입니다.
    deflection_limit_mm?: number;
    // 검토 스팬(m)입니다.
    span_m?: number;
    // 기준 대비 사용률입니다.
    utilization_ratio?: number;
    // 부재별 검토 결과와 사용률입니다.
    per_element_utilization?: Array<{
      // 표시 대상 display_guids로 재사용 가능
      source_guids?: Array<string>;
      // 부재 사용률입니다.
      utilization?: number;
      // 지배 하중 조합입니다.
      combination?: string;
      [key: string]: unknown;
    }>;
    [key: string]: unknown;
  };
  // 상위 최대 5개, 전체 해석 범위 아님
  worst_member_guids?: Array<string>;
  // 결과를 해석할 때 확인할 경고입니다.
  warnings?: Array<string>;
  // 검토에 사용한 가정입니다.
  assumptions?: Array<string>;
  // 검토에 사용한 설계 기준 프로필입니다.
  design_code?: {
    // 검토에 사용한 설계 기준 ID입니다.
    id?: string;
    // 검증되지 않은 매개변수 목록입니다.
    unverified?: Array<unknown>;
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 5. analysis\_05-visualize\_structure

```txt
구조 해석 결과를 임시 뷰포트 오버레이로 표시합니다.
```

```ts
declare const tools: {
  mcp__rhino__analysis_05_visualize_structure(args: {
    // 구조 축선의 곡선 GUID와 지점을 표시하는 점 GUID입니다(fixed_supports 참조). 점이 없으면 최하단 절점을 지점으로 사용합니다.
    // default: null
    guids?: (Array<string> | null);
    // 자유 절점에 하향(-Z)으로 균등 분배할 전체 부과하중(kN)입니다.
    // default: 10.0
    load_kn?: number;
    // "Steel", "S355", "Concrete", "Wood", "Aluminium" 중 하나입니다.
    // default: "Steel"
    material?: string;
    // 선택 항목인 원형 부재 외경(밀리미터)입니다.
    // default: null
    beam_diameter_mm?: (number | null);
    // 선택 항목인 중공 부재의 벽 두께(밀리미터)입니다.
    // default: null
    beam_wall_mm?: (number | null);
    // 중력을 포함합니다.
    // default: true
    self_weight?: boolean;
    // True는 완전 고정 지점, False는 핀 지점(회전 자유)을 뜻합니다.
    // default: true
    fixed_supports?: boolean;
    // 경간/비율 한계입니다. 예를 들어 L/250은 250입니다. 기본값은 설계기준의 한계입니다(Eurocode 프로필: 250).
    // default: null
    deflection_limit_ratio?: (number | null);
    // 한계에 사용할 기준 경간(미터)입니다. 기본값은 가장 긴 부재입니다. 부재가 모든 절점에서 분할됐다면 지정합니다. 예: 6.2 m 장선을 3.1 m 구간 두 개로 그린 경우.
    // default: null
    span_m?: (number | null);
    // "displacement" 또는 "utilization"입니다.
    // default: "displacement"
    color_by?: string;
    // 변형 과장 배율입니다. 생략하면 자동으로 정합니다(경간의 약 6%).
    // default: null
    scale?: (number | null);
    // 그릴 부재의 비율이며 0..1 범위입니다. 단계별 시공 재생에 사용합니다.
    // default: 1.0
    reveal?: number;
    // False이면 마지막 계산을 재사용하고 표시(scale / color_by / reveal / physics / title)만 변경합니다. 애니메이션에 사용할 수 있을 만큼 계산 부담이 작습니다.
    // default: true
    reanalyze?: boolean;
    // False이면 해석 오버레이 없이 같은 부재를 일반 형상으로 그립니다("physics off"). 전후 비교에 사용합니다.
    // default: true
    physics?: boolean;
    // 이 부재들만 그립니다(예: 단면 보기를 위한 한 줄의 프레임). 해석은 여전히 guids의 모든 부재를 포함합니다.
    // default: null
    display_guids?: (Array<string> | null);
    // 범례 제목입니다.
    // default: ""
    title?: string;
    // 오버레이를 제거합니다.
    // default: false
    clear?: boolean;
    // "auto"(기본값), "native", "karamba" 중 하나입니다. "auto"는 Karamba 없이 Almond 네이티브 프레임 솔버를 사용하되, 선택에 셸이 있거나 브리지가 모델을 내보낼 수 없으면 Karamba를 사용합니다.
    // default: "auto"
    engine?: string;
    // analysis_04-validate_structure tool와 동일하게 배치된 라이브러리 자산의 하중을 추가합니다(네이티브 엔진). 하중 작용점에 하중 화살표를 그립니다.
    // default: false
    asset_loads?: boolean;
    // 한 층에서 보로 둘러싸인 모든 구획에 적용할 부과 바닥 하중(kN/m2)입니다(예: 주거용 2.0, EN 1991-1-1의 category A). 보는 45도 분배 규칙에 따라 하중을 받습니다(2방향, 장단변비 2:1 초과 시 1방향). 네이티브 엔진 전용입니다. 설계기준의 바닥 하중에는 이동 가능한 가구와 사람이 이미 포함되므로, asset_loads는 무거운 특정 물품에 대해서만 함께 사용하고 중복 계산을 피하려면 load_kn을 0으로 설정합니다.
    // default: 0.0
    floor_load_kn_m2?: number;
    // 같은 구획에 적용할 추가 고정하중(kN/m2)입니다. 바닥 구성층과 마감 등을 포함합니다.
    // default: 0.0
    floor_dead_kn_m2?: number;
    // "en1990"(기본값)은 SLS 특성 조합(G + Q)에서 처짐을, ULS 1.35 G + 1.5 Q에서 부재를 검토합니다. G는 자중, 바닥 구성층, 배치된 물품의 중량이고, Q는 load_kn, 용도별 바닥 활하중, 내용물, 재실자입니다. "unfactored"는 둘 다 G + Q에서 검토합니다(Karamba 경로의 기준). 네이티브 엔진에 적용됩니다.
    // default: "en1990"
    design_basis?: string;
    // "6.10" 또는 "6.10ab"입니다. "6.10ab"는 부재별로 6.10a와 6.10b 중 더 불리한 결과를 사용합니다. 기본값은 설계기준이 선택한 식입니다(Eurocode 프로필: 6.10). 특정 식을 지정한 프로필은 요청보다 우선하며 경고를 반환합니다.
    // default: null
    uls_combination?: (string | null);
    // analysis_04-validate_structure tool와 동일한 "rigid" 또는 "simple"입니다. 핀 접합 단부는 작은 원으로 그립니다.
    // default: "rigid"
    connections?: string;
    // analysis_04-validate_structure tool와 동일한 "auto" 또는 "off"입니다.
    // default: "auto"
    stability?: string;
    // 설계기준 또는 국가 부록에서 정하는 수치(gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, 처짐 한계)에 사용할 설계기준 프로필입니다. "eurocode"(기본값, EN 권장값), analysis_03-list_design_codes tool의 프로필 또는 "off"를 사용합니다. "off"는 부분계수 없이 G + Q를 적용하며 design_basis="unfactored"와 같습니다. 결과의 "design_code"에는 사용한 값과 검증되지 않은 값이 포함됩니다.
    // default: "eurocode"
    design_code?: string;
    // 중공 강재 단면(CHS/RHS)은 "cold_formed"(기본값, EN 10219, 좌굴 곡선 c) 또는 "hot_finished"(EN 10210, 곡선 a, S460은 a0)입니다. 좌굴 내력에 최대 약 23% 차이가 있으므로, hot_finished는 명시된 경우에만 사용합니다.
    // default: "cold_formed"
    fabrication?: string;
    // "deflection"(기본값) 또는 "buckling"입니다. "buckling"은 처짐 형상 대신 지배 ULS 조합의 첫 번째 좌굴 모드를 alpha_cr과 함께 그립니다(STABLE >= 10, SWAY-SENSITIVE 1-10, UNSTABLE <= 1).
    // default: "deflection"
    view?: string;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 해석 방식입니다.
  analysis_method?: string;
  // 검토 기준 충족 여부입니다. indicative의 null은 해석은 완료했으나 재료 내력 합격 판정을 하지 않았음을 뜻합니다.
  passed?: boolean | null;
  // 최대 변위(mm)입니다.
  max_displacement_mm?: number;
  // 허용 처짐(mm)입니다.
  deflection_limit_mm?: number;
  // 검토 스팬(m)입니다.
  span_m?: number;
  // 최대 부재 사용률입니다. 해당 해석에서 계산하지 않으면 null입니다.
  max_utilization?: number | null;
  // 실제 변위가 아닌 표시 과장 배율
  scale?: number;
  // 시각화한 부재별 결과입니다.
  elements?: Array<{
    // display_guids 또는 객체 관찰에 재사용
    source_guids?: Array<string>;
    // 최대 변위(mm)입니다.
    max_displacement_mm?: number;
    // 부재 사용률입니다. 해당 해석에서 계산하지 않으면 null입니다.
    utilization?: number | null;
    [key: string]: unknown;
  }>;
  // 해석 노드 수입니다.
  nodes?: number;
  // 결과를 해석할 때 확인할 경고입니다.
  warnings?: Array<string>;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

## asset

### 6. asset\_01-audit\_drawing

```txt
저장 도면 패키지에서 선언한 뷰의 SVG·DXF와 파일 해시 목록을 대조합니다. 빈 해시 목록, 누락·변경 파일, 패키지 밖 경로와 파일시스템 링크는 오류로 반환합니다. 원본을 찾을 수 있을 때 원본 변경도 확인합니다.
```

```ts
declare const tools: {
  mcp__rhino__asset_01_audit_drawing(args: {
    // 생성/조회 결과의 package_dir를 그대로 입력합니다. 관리형 세션은 프로젝트 안의 패키지와 설정된 도면 라이브러리·drawing-runs의 패키지를 검사합니다. 독립 실행에서는 절대 경로가 필요합니다.
    package_dir: string;
    // 원본 변경으로 오래된 상태가 되었는지 확인할 현재 원본 GLB입니다. 선택 사항이며, 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. 라이브러리에서 원본을 확인할 수 있으면 생략합니다.
    // default: ""
    source_glb?: string;
  }): Promise<CallToolResult<{
    // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
    status?: string;
    // current/source_file_current/stale/not_checked. not_checked는 success여도 원본 비교 미실시
    source_geometry?: string;
    // 패키지 원본 ID. custom-*는 등록 자산 ID가 아님
    asset_id?: string;
    // 해시를 검사한 파일 수. 시각적 검토가 아님
    checked_files?: number;
    // 실패 항목이 하나라도 있으면 status=error
    failures?: Array<unknown>;
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 7. asset\_02-generate\_drawing\_views

```txt
등록 3DM 또는 사용자 지정 GLB의 메쉬를 평면·정면·우측면 실루엣으로 투영합니다. 실물 크기 mm DXF와 축척 SVG를 생성하며, 세 뷰가 A3 시트 영역에 들어가면 시트 SVG도 생성합니다. 시트가 생략되어도 성공할 수 있습니다.

실루엣에는 단면과 내부 가시선·은선이 없으며 정면은 좌표계 기준입니다. 축척에 따른 단순화나 근사로 작은 형상의 윤곽이 달라질 수 있습니다. 결과는 별도 drawing-runs 패키지에 저장되며 등록 자산의 도면을 갱신하지 않습니다.
```

```ts
declare const tools: {
  mcp__rhino__asset_02_generate_drawing_views(args: {
    // 등록 3DM 자산 ID. source_glb와 택일.
    // default: ""
    asset_id?: string;
    // 정적·비압축 삼각형 GLB, 최대 100 MB·250,000 삼각형.
    // 관리형: 프로젝트 상대 경로 / 독립 실행: 절대 경로.
    // default: ""
    source_glb?: string;
    // GLB 원본 단위 mm 또는 m. source_glb에 필수.
    // default: ""
    input_units?: string;
    // GLB 위쪽 축 y 또는 z. 기본 y: (X,-Z,Y)로 변환. 등록 3DM에는 미적용.
    // default: "y"
    up_axis?: string;
    // 축척 분모 1~4개, 중복 없는 정수 5~1000. 기본 [50, 100].
    // default: null
    scales?: (Array<number> | null);
    // 이 도면에 첨부하는 출처. 원본 모델 생성 이력의 증빙은 아님.
    // 필수: source_id, title, url, publisher, locator, accessed_on, relationship, used_for, terms_url.
    // relationship: background_reading, dimensional_reference, assembly_reference, post_generation_reference.
    // default: null
    source_references?: (Array<{
      [key: string]: unknown;
    }> | null);
  }): Promise<CallToolResult<{
    // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
    status?: string;
    // asset_01-audit_drawing tool의 package_dir에 그대로 전달할 경로입니다. 관리 연결에서는 프로젝트 상대 경로이며, 다른 드라이브의 라이브러리는 절대 경로를 유지합니다.
    package_dir?: string;
    // 생성한 도면과 원본·축척·단위 기록입니다.
    manifest?: {
      [key: string]: unknown;
    };
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 8. asset\_03-get\_drawings

```txt
등록 자산의 저장 도면 패키지를 조회합니다. manifest에서 도면 파일·축척·치수·출처와 투영 한계를 확인할 수 있습니다. 도면은 자산의 원본 형상을 투영한 것으로 배치 인스턴스의 변환이 적용된 결과는 아닙니다.
```

```ts
declare const tools: {
  mcp__rhino__asset_03_get_drawings(args: {
    // include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다.
    asset_id: string;
    // true이면 후속 호출에 사용할 ID를 포함합니다.
    // default: false
    include_ids?: boolean;
    // 선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
    status?: string;
    // all 조회에서 반환하는 도면 패키지 경로입니다. asset_01-audit_drawing tool의 package_dir에 그대로 전달할 수 있습니다.
    package_dir?: string;
    // 저장된 평면 SVG를 읽는 리소스 URI입니다.
    plan_svg_uri?: string;
    // 도면 패키지의 원본·파일·축척 기록입니다.
    manifest?: {
      [key: string]: unknown;
    };
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 9. asset\_04-get

```txt
모델·2D 자산의 등록 정보와 사용 가능 상태를 조회합니다. paths로 원본·모델 경로를 확인할 수 있습니다. result는 자산 정보 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: {
  mcp__rhino__asset_04_get(args: {
    // include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다.
    asset_id: string;
    // ID 포함 옵션. 조회한 asset_id는 응답에 반복되지 않을 수 있습니다.
    // default: false
    include_ids?: boolean;
    // 선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 선택한 도면 자산과 준비 상태입니다.
  asset?: {
    // 저장된 이름
    name?: string;
    // 원본·등록 파일의 존재 여부
    file_available?: boolean;
    // ready/needs_conversion/needs_refresh 등. source_only는 원본이 있어도 배치 준비 안 됨
    model_status?: string;
    // 현재 원본에 대응하는 도면 패키지가 준비됐는지 나타냅니다.
    drawing_ready?: boolean;
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 10. asset\_05-list

```txt
모델·2D 자산 목록과 사용 준비 상태를 조회합니다. 원본만 있는 자산은 바로 배치할 3DM이 아닐 수 있습니다. 상세 조회에 필요한 ID는 include_ids=true로 포함합니다.

페이지 결과에 next_offset은 없으며, truncated=true면 같은 필터로 offset에 반환된 자산 수를 더해 이어 읽습니다. result는 목록 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: {
  mcp__rhino__asset_05_list(args: {
    // 라이브러리 분류 필터입니다. 선택 사항이며, 비어 있으면 모든 분류를 포함합니다.
    // default: ""
    category?: string;
    // 한 페이지에 반환할 최대 항목 수입니다.
    // default: 20
    limit?: number;
    // 이 페이지의 시작 행을 0부터 세는 값입니다. 다음 페이지를 요청할 때도 같은 필터를 사용합니다.
    // default: 0
    offset?: number;
    // true이면 후속 호출에 사용할 ID를 포함합니다.
    // default: false
    include_ids?: boolean;
    // 선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // include_ids=true에서 유지되는 라이브러리 구분자
  library_id?: string;
  // 도면 자산 목록입니다. 추가 준비가 필요한 항목에는 next_tool과 next_step_guide가 있습니다.
  assets?: Array<{
    [key: string]: unknown;
  }>;
  // 필터에 일치하는 전체 항목 수
  total?: number;
  // 페이지 최대 항목 수
  limit?: number;
  // 현재 페이지 시작 위치
  offset?: number;
  // true이면 같은 필터로 offset+현재 항목 수부터 계속. next_offset 필드는 없음
  truncated?: boolean;
  // 이 라이브러리의 용도입니다.
  purpose?: string;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 11. asset\_06-place

```txt
모델·2D 자산을 Rhino 문서에 블록으로 배치합니다. 3DM은 원본에 연결된 블록이며 같은 정의를 사용하는 배치에 정의 갱신이 반영됩니다. 결과는 성공 또는 오류를 담은 JSON 문자열입니다.
응답 유실 등으로 requires_reconciliation이 true이면 Rhino 문서에서 실제 배치 결과를 확인한 뒤 다음 작업을 결정합니다.
```

```ts
declare const tools: {
  mcp__rhino__asset_06_place(args: {
    // include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다.
    asset_id: string;
    // 원본 기준점의 월드 X 좌표. 문서 단위, 기본 0.
    // default: 0
    x?: number;
    // 원본 기준점의 월드 Y 좌표. 문서 단위, 기본 0.
    // default: 0
    y?: number;
    // 원본 기준점의 월드 Z 좌표. 문서 단위, 기본 0.
    // default: 0
    z?: number;
    // 월드 Z축 기준 회전각(도). 기본 0.
    // default: 0
    rotation_degrees?: number;
    // 균일 배치 축척. 기본 1, 0 초과 100 이하.
    // default: 1
    scale?: number;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 자산 ID
  asset_id?: string;
  // 삽입한 최상위 블록 GUID. inspect_02-get_objects tool 또는 Scene 구성원 입력에 재사용
  object_guid?: string;
  // 새 정의 생성 여부. 공유 정의 갱신 시 definition_refreshed/affected_existing_instances가 추가될 수 있음
  definition_created?: boolean;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // 실제 변경 근거에 따른 상태입니다. unknown/partial이면 변경이 남았을 수 있습니다.
  mutation_state?: string;
  // true이면 실제 문서 상태를 확인한 뒤 다음 작업을 결정합니다. 자동 재실행을 허용하지 않습니다.
  requires_reconciliation?: boolean;
  // 변경 적용 여부입니다. null이면 실제 적용 여부를 확인하지 못했습니다.
  mutation_applied?: boolean | null;
  [key: string]: unknown;
};
```

### 12. asset\_07-prepare

```txt
원본 사본을 검사·편집·시각 검토해 등록용 3DM을 준비합니다. inspect로 job을 만들고, 필요하면 normalize로 수정한 뒤 verify합니다. 수정이 필요 없으면 normalize를 건너뛰고 verify할 수 있습니다.

첫 verify는 최종 미리보기와 해시를 생성합니다. 이를 검토한 뒤 같은 해시·이름·ID를 넣어 다시 verify하면 등록 준비 상태가 됩니다. ready_for_registration은 호출자의 해시 연계 검토 확인이며 형상 적합성을 자동 판정했다는 뜻은 아닙니다. 관리형 source_file은 프로젝트 내부 경로여야 합니다.
```

```ts
declare const tools: {
  mcp__rhino__asset_07_prepare(args: {
    // inspect, normalize, verify 또는 status입니다. inspect는 작업을 생성하고, 이후 단계는 job_dir를 재사용합니다. status는 저장된 근거만 다시 읽습니다. 네이티브 작업을 실행하거나, 나중에 완료되었다는 이유로 확인되지 않은 작업의 단계를 올리지 않습니다.
    stage: string;
    // inspect에 사용할 원본 모델입니다. 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. 원본 바이트는 변경하지 않고 유지합니다.
    // default: ""
    source_file?: string;
    // 이전에 반환된 준비 작업의 job_dir입니다. 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. normalize, verify, status에 필수입니다.
    // default: ""
    job_dir?: string;
    // OBJ/STL/PLY/OFF/GLB/glTF의 명시적 원본 단위로 mm, cm, m, in 또는 ft를 지정합니다. 측정한 원본 단위를 사용합니다. 이후 단계에서는 생략하며, 3DM은 내장된 단위를 보존합니다.
    // default: ""
    input_units?: string;
    // 검토 결과 객체입니다. normalize: {vision_reviewed:true, inspected_sha256:"확인한 해시", rotation_degrees_xyz:[x,y,z], translation:[x,y,z], remove:[{object_id:"ID",reason:"사유"}]}. 생략한 변환은 유지하며 translation은 원본 단위입니다. 최종 이미지를 본 뒤 verify: {vision_reviewed:true, final_sha256:"확인한 해시", name:"이름", asset_id:"ID"}. 첫 verify로 최종 이미지를 만든 후 검토 확인을 제출합니다.
    // default: null
    review?: ({
      [key: string]: unknown;
    } | null);
    // 선택 가능한 값은 summary, parts, previews, provenance 또는 all입니다. 생략하면 미리 보기 경로를 포함하고, []이면 간략한 결과를 유지합니다. 페이지 처리는 parts에 적용됩니다.
    // default: null
    field_groups?: (Array<string> | null);
    // true이면 후속 호출에 사용할 ID를 포함합니다.
    // default: false
    include_ids?: boolean;
    // 이 페이지의 시작 행을 0부터 세는 값입니다. 다음 페이지를 요청할 때도 같은 필터를 사용합니다.
    // default: 0
    offset?: number;
    // 부품 목록의 페이지 크기이며, 범위는 1..200입니다.
    // default: 50
    limit?: number;
  }): Promise<CallToolResult<{
    // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
    status?: string;
    // ready일 때만 source_3dm 제공. running/unconfirmed/failed는 error와 next_stage=null
    state?: string;
    // 현재 파일 해시에 대한 이미지 검토를 호출자가 확인했는지 나타냅니다.
    ready_for_registration?: boolean;
    // 이후 단계 및 등록의 preparation_job에 재사용. status는 저장 근거만 읽고 늦은 실행을 자동 정합화하지 않음
    job_dir?: string;
    // 검토 완료 최종 파일. asset_09-register tool에 검토한 name/asset_id와 함께 전달
    source_3dm?: string;
    // 현재 상태의 다음 단계. 오류에서 자동 진행을 유도하지 않음
    next_stage?: string | null;
    // 저장된 검토 증거에 대한 설명입니다.
    review_evidence?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    [key: string]: unknown;
  }>>;
};
```

### 13. asset\_08-refresh

```txt
편집·저장된 등록 3DM을 다시 측정하고 평면·입면 도면을 새 리비전으로 발행합니다. 원본 경로와 이전 도면은 유지됩니다. 도면은 메쉬 투영 실루엣으로 내부 가시선·은선이나 구성 레이어를 표현하지 않습니다.

열린 Rhino 문서의 연결 블록을 갱신하거나 저장하지 않습니다. 공유 블록 정의를 별도로 갱신하면 기존 인스턴스에도 반영되지만, 배치 당시 메타데이터는 자동 갱신되지 않습니다.
```

```ts
declare const tools: {
  mcp__rhino__asset_08_refresh(args: {
    // 등록 3DM 모델 자산 ID.
    asset_id: string;
  }): Promise<CallToolResult<{
    // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
    status?: string;
    // true면 인덱스 갱신 실패여도 게시 적용. 무작정 반복하지 않음
    registration_applied?: boolean;
    // 기존 원본 경로를 보존했는지 여부
    source_path_preserved?: boolean;
    // false: 기존 Rhino 연결 인스턴스 재로드는 별도
    rhino_linked_instances_updated?: boolean;
    // false인데 게시가 적용됐다면 재연결하여 인덱스 갱신
    live_index_refreshed?: boolean;
    // 갱신한 자산의 정보입니다.
    asset?: {
      [key: string]: unknown;
    };
    // 갱신한 라이브러리 3DM 경로입니다.
    model_path?: string;
    // 갱신한 도면 패키지 폴더입니다.
    package_dir?: string;
    // 이전 도면·매니페스트 백업·원본 리비전 사본 보존
    previous_files_retained?: boolean;
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 14. asset\_09-register

```txt
준비한 3DM을 모델 라이브러리에 등록하고 치수와 평면·입면 도면 패키지를 생성합니다. 생성 도면은 투영 실루엣으로 내부 가시선·숨은선이나 구성 레이어를 표현하지 않습니다.

파생 메시가 250,000 삼각형을 넘으면 등록에 실패합니다. asset_07-prepare tool의 준비 완료는 등록 성공을 보장하지 않습니다. 등록 후 asset_04-get tool로 자산 상태를 확인할 수 있습니다.
```

```ts
declare const tools: {
  mcp__rhino__asset_09_register(args: {
    // 검토한 3DM 원본입니다. 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. preparation_job을 사용할 때는 해당 작업 응답의 source_3dm을 사용합니다.
    source_3dm: string;
    // 자산 ID. preparation_job 사용 시 검토한 ID와 일치.
    asset_id: string;
    // preparation_job 사용 시 검토한 이름과 일치.
    name: string;
    // 새 자산의 라이브러리 분류입니다.
    // default: "other"
    category?: string;
    // 선택 사항인 설명용 검색 태그입니다.
    // default: null
    tags?: (Array<string> | null);
    // 선택 사항인 자산 설명입니다.
    // default: ""
    description?: string;
    // 출처 이력으로 보존할 원래 원본 URL입니다. 선택 사항입니다.
    // default: ""
    source_url?: string;
    // true이면 이 ID를 가진 기존 자산을 명시적으로 교체합니다. false이면 교체를 거부합니다.
    // default: false
    replace_existing?: boolean;
    // 완료된 준비 작업의 job_dir입니다. 선택 사항이며, 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. 검토를 거치는 다중 형식 변환 절차에는 필수입니다.
    // default: ""
    preparation_job?: string;
  }): Promise<CallToolResult<{
    // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
    status?: string;
    // true면 게시 적용. 불명확한 오류는 null과 requires_reconciliation; 단순 재시도 금지
    registration_applied?: boolean | null;
    // 게시 true·인덱스 false이면 등록을 반복하지 말고 재연결
    live_index_refreshed?: boolean;
    // 기존 원본 경로를 보존했는지 여부
    source_path_preserved?: boolean;
    // 교체로 기존 연결 인스턴스에 영향 가능
    linked_instances_may_update?: boolean;
    // 등록한 자산의 정보입니다.
    asset?: {
      [key: string]: unknown;
    };
    // 라이브러리 폴더
    library_dir?: string;
    // 저장된 모델의 경로
    model_path?: string;
    // 생성한 도면 패키지 폴더입니다. DXF와 치수는 mm 단위입니다.
    package_dir?: string;
    // 라이브러리 manifest.json 경로입니다.
    manifest_path?: string;
    // 교체 전 원본·도면·매니페스트 백업 보존
    previous_files_retained?: boolean;
    // 기존 원본 해시. 없으면 null
    previous_source_sha256?: string | null;
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 15. asset\_10-search\_repository

```txt
모델·2D 요소 아카이브를 검색하고 후보의 사용 가능 상태를 확인합니다. 결과는 전체 매치 수와 limit개까지의 후보이며 이어지는 페이지는 없습니다. 잘린 경우 검색어나 유형으로 범위를 좁힐 수 있습니다.

원본만 있는 자산은 즉시 배치 가능한 상태가 아닐 수 있습니다. 상세 정보와 경로는 후보 ID로 asset_04-get tool에서 조회합니다.
```

```ts
declare const tools: {
  mcp__rhino__asset_10_search_repository(args: {
    // 이름·ID·분류·variant·재료 ID·태그·역할 검색. 대소문자 무시, 공백으로 구분한 모든 단어 포함.
    // default: ""
    query?: string;
    // all(기본), element 또는 model.
    // default: "all"
    kind?: string;
    // true이면 도면 데이터가 준비된 자산으로 제한합니다.
    // default: false
    drawing_ready?: boolean;
    // 반환 개수: 기본 20, 1..100으로 보정.
    // default: 20
    limit?: number;
    // true이면 후속 호출에 사용할 ID를 포함합니다.
    // default: false
    include_ids?: boolean;
    // dimensions, source, paths, drawing, metadata, audit 또는 all. 검색 결과에 있는 필드만 표시.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    // 전체 매치 수. assets는 limit까지이며 offset/has_more 없음
    total?: number;
    // 검색된 자산과 준비 상태입니다. id를 후속 도구의 asset_id로 사용합니다.
    assets?: Array<{
      [key: string]: unknown;
    }>;
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 16. asset\_11-search

```txt
모델·2D 자산을 검색어, 분류와 최대 치수로 검색합니다. 여러 검색어 중 하나 이상 일치하면 포함하고, 일치 단어가 많은 순으로 표시합니다. 결과에는 파일·모델·도면 상태와 페이지 정보가 포함됩니다.

최대 치수 필터는 등록 치수를 비교하며, 해당 치수가 없는 자산도 포함될 수 있습니다. 상세 정보는 include_ids=true로 얻은 ID를 asset_04-get tool에 전달합니다. result는 검색 결과 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: {
  mcp__rhino__asset_11_search(args: {
    // 이름·설명·제품·분류·태그 등 부분 일치. 대소문자 무시.
    // default: ""
    query?: string;
    // 분류의 정확한 값. 대소문자 무시, 빈 값은 전체.
    // default: ""
    category?: string;
    // 너비 상한(mm). 양수일 때 적용.
    // default: 0
    max_width_mm?: number;
    // 깊이 상한(mm). 양수일 때 적용.
    // default: 0
    max_depth_mm?: number;
    // 높이 상한(mm). 양수일 때 적용.
    // default: 0
    max_height_mm?: number;
    // 페이지 크기: 기본 10, 1..100.
    // default: 10
    limit?: number;
    // 0부터 시작. truncated=true면 같은 조건의 offset에 반환 건수를 더해 이어 조회.
    // default: 0
    offset?: number;
    // true이면 후속 호출에 사용할 ID를 포함합니다.
    // default: false
    include_ids?: boolean;
    // 선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 검색된 도면 자산과 준비 상태입니다.
  assets?: Array<{
    [key: string]: unknown;
  }>;
  // 필터에 일치하는 전체 항목 수
  total?: number;
  // 페이지 최대 항목 수
  limit?: number;
  // 현재 페이지 시작 위치
  offset?: number;
  // true이면 같은 필터로 offset+현재 항목 수부터 계속
  truncated?: boolean;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

## capture

### 17. capture\_01-conditioning\_pass

```txt
활성 Rhino 뷰의 카메라 경로를 따라 RGB·에지·깊이 PNG와 카메라 기록을 저장합니다. 관리형 연결은 Plan 작업 공간을 먼저 선택합니다. 촬영 중 활성 뷰가 변경되며 전체 뷰 상태의 복원은 보장되지 않습니다.

status와 frames_captured는 촬영 실행 결과이며 대상이 잘 보인다는 보장은 아닙니다. videos의 null은 MP4가 생성되지 않았음을 뜻합니다. 같은 출력 폴더를 재사용하면 기존 프레임·기록을 덮어쓰고 잔여 프레임이 남을 수 있습니다.
```

```ts
declare const tools: {
  mcp__rhino__capture_01_conditioning_pass(args: {
    // 카메라 경로를 담은 JSON 문자열입니다. type=orbit은 center:[x,y,z], radius, height와 선택적 start_deg/end_deg/lens/target_height; type=track은 cam0/cam1/target0/target1 좌표와 선택적 lens; type=keyframes는 camera·target·선택적 lens를 가진 keyframes 배열입니다. frames 기본값은 81, lens는 mm, 좌표는 문서 단위입니다.
    shot: string;
    // 관리형 세션: 선택한 Plan의 산출물 디렉터리 아래 상대 폴더이며, 기본값은 conditioning입니다. 먼저 Plan을 선택합니다. 독립 실행: 출력 폴더이며, 기본값은 현재 작업 디렉터리입니다.
    // default: ""
    out_dir?: string;
    // 짝수, 기본 832px.
    // default: 832
    width?: number;
    // 짝수, 기본 480px.
    // default: 480
    height?: number;
    // 쉼표 구분: rgb, edge, depth. 기본 전체.
    // default: "rgb,edge,depth"
    passes?: string;
    // 초당 프레임 수. 기본 16.
    // default: 16
    fps?: number;
    // 청크당 프레임 수. 기본 16.
    // default: 16
    chunk?: number;
    // RGB 프레임에 사용할 설치된 Rhino 디스플레이 모드이며, 기본값은 Rendered입니다.
    // default: "Rendered"
    rgb_mode?: string;
    // 에지 프레임에 사용할 설치된 Rhino 디스플레이 모드이며, 기본값은 Technical입니다.
    // default: "Technical"
    edge_mode?: string;
    // 기본 false: 가까울수록 밝음.
    // default: false
    invert_depth?: boolean;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 요청 프레임 수
  frames_requested?: number;
  // 성공한 캡처 청크의 프레임 수입니다.
  frames_captured?: number;
  // 생성한 패스 종류
  passes?: Array<string>;
  // 출력 이미지 해상도 [너비, 높이]
  resolution?: Array<number>;
  // 영상 프레임 레이트
  fps?: number;
  // 실패한 청크의 프레임 범위와 메시지. 부분 생성 파일이 남을 수 있음
  errors?: Array<unknown>;
  // 패스별 PNG와 doc.json/camera.json/zrange.csv/summary.json을 쓰는 폴더
  out_dir?: string;
  // 전체 계획 경로 기록. frames[].camera/target/lens_mm를 포함하며 부분 캡처에도 계획은 전체 길이
  camera_json?: string;
  // 완전 캡처 후 패스별 MP4. ffmpeg 조립 실패는 null이며 부분 캡처에는 빈 객체일 수 있음
  videos?: {
    // 조립된 RGB 영상 경로입니다. 조립하지 못하면 null입니다.
    rgb?: string | null;
    [key: string]: unknown;
  };
  // 원본 문서·단위·뷰·경계 정보입니다.
  document?: {
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 18. capture\_02-inspection

```txt
작업 화면을 유지하면서 여러 시점과 객체 범위를 하나의 PNG로 비교합니다. 객체 범위는 문서 표시 상태를 기준으로 하며 픽셀 가시성이나 가림을 보장하지 않습니다. 그룹 자동 확장과 블록 배치·정의 필터는 지원하지 않습니다.

설치된 표시 모드의 이름과 GUID는 inspect_03-get_document_context tool에서 sections=["display_modes"]로 조회합니다. Wireframe은 와이어와 곡선 검토, Shaded는 면과 입체 형태 검토, Technical은 가려진 선을 포함한 선 표현 검토에 적합합니다. 사용자 정의 래스터 모드도 설치된 이름이나 GUID로 선택할 수 있습니다. 이름이 중복되면 GUID를 사용합니다.

inspect_02-get_objects tool에서 include_ids=true로 최상위 모델 객체의 GUID를 확인합니다. 모든 타일을 같은 대상에 맞추려면 공통 object_ids에 GUID 배열을 넣고 views에서 각 방향과 모드를 선택합니다. 예를 들어 views=[{"direction":"top","display_mode":"Technical"},{"direction":"iso_ne","display_mode":"Shaded"}]는 같은 대상을 평면과 사시 방향으로 비교합니다. 원본 뷰 방향에서 지정 객체에 맞춰 확대하려면 공통 또는 타일별 object_ids와 함께 views=[{"direction":"current","frame_objects":true}]를 사용합니다. frame_objects를 생략한 current 타일은 원본 카메라 구도를 사용합니다.

일부 타일이 실패해도 status=success일 수 있습니다. 전체 성공 여부는 complete에서, 개별 결과와 적용된 모드의 이름·GUID는 tiles에서 확인합니다. PNG 전달과 image_file 저장은 별개입니다.
```

```ts
declare const tools: {
  mcp__rhino__capture_02_inspection(args: {
    // 타일 1..16개. direction: current(기본), top, bottom, front, back, left, right, iso_ne, iso_nw, iso_se, iso_sw, below_ne, below_nw, below_se, below_sw.\n  // display_mode: 설치된 이름/GUID, label: 최대 120자. object_ids: 최상위 GUID 1..512개; 생략·빈 배열은 공통 범위 또는 문서 표시 상태.
    views: Array<{
      [key: string]: unknown;
    }>;
    // 타일의 픽셀 너비로, 범위는 128..2048이며 기본값은 640입니다. 결합 이미지 제한도 적용됩니다.
    // default: 640
    width?: number;
    // 타일의 픽셀 높이로, 범위는 128..2048이며 기본값은 480입니다. 결합 이미지 제한도 적용됩니다.
    // default: 480
    height?: number;
    // 선택 사항인 열 개수이며, 범위는 1..뷰 개수입니다. 생략하면 자동 격자를 사용합니다.
    // default: null
    columns?: (number | null);
    // 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
    // default: ""
    expected_model_path?: string;
    // 선택 사항인, 목록에 있는 모델 뷰포트 GUID입니다. Layout/Detail이 활성화된 경우를 포함하여 해당 뷰포트를 활성화하지 않고 사용합니다.
    // default: ""
    model_view_id?: string;
    // 공통 최상위 객체 GUID 1..4096개. 빈 배열 불가; 타일별 object_ids와 배타.
    // default: null
    object_ids?: (Array<string> | null);
  }): Promise<CallToolResult<{
    // 이미지 캡처의 처리 상태입니다.
    status?: string;
    // 요청한 모든 타일을 캡처했는지 나타냅니다.
    complete?: boolean;
    // 타일별 캡처 결과와 관찰 범위입니다. 실패한 타일도 포함합니다.
    tiles?: Array<{
      // 0부터 시작하는 항목 인덱스
      index?: number;
      // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
      status?: string;
      // 캡처한 시점입니다.
      direction?: string;
      // 성공한 타일의 실제 표시 모드입니다.
      display_mode?: {
        // 설치된 표시 모드 이름입니다.
        name?: string;
        // 표시 모드 GUID입니다.
        id?: string;
        [key: string]: unknown;
      };
      [key: string]: unknown;
    }>;
    // PNG 파일 저장 결과. 이미지 전달과 별개이며 저장 실패여도 이미지가 제공될 수 있음
    image_file?: {
      // 파일 저장 결과입니다. saved일 때 path를 사용할 수 있습니다.
      status?: string;
      // 프로젝트 기준 PNG 상대 경로. output_refs에 기록할 때는 이 문자열만 사용
      path?: string;
      // plan은 Plan 산출물, connection은 연결 정리까지의 임시 파일
      lifetime?: string;
      // 파일 바이트 수
      bytes?: number;
      // 파일 해시.
      sha256?: string;
      [key: string]: unknown;
    };
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 19. capture\_03-current\_view

```txt
현재 Rhino 모델 뷰포트를 일반 화면 색과 선 표현으로 PNG에 캡처합니다. 캡처 중 문서의 PrintDisplay 설정은 유지됩니다. 대상 지정 시 실제 선택과 카메라가 바뀌며, isolate와 display_mode도 실제 화면 상태를 변경합니다. 설치된 모드의 이름과 GUID는 inspect_03-get_document_context tool에서 sections=["display_modes"]로 조회합니다. 작업 화면을 유지하면서 선택한 객체를 여러 방향이나 모드로 비교하려면 capture_02-inspection tool을 사용합니다. 격리 해제는 Rhino Unisolate를 사용합니다. 잠긴 주변 객체는 보일 수 있고, 선택·카메라는 별도로 확인해야 합니다.

PNG 이미지 전달과 image_file 저장은 별개입니다. include_usage의 토큰 수는 픽셀 기준 추정치입니다. labels는 주변 객체에도 표시되어 화면을 가릴 수 있습니다.
```

```ts
declare const tools: {
  mcp__rhino__capture_03_current_view(args: {
    // 화면에서 선택·확대할 객체, 그룹 또는 Holon의 ID 배열입니다. 생략하면 현재 화면을 사용하며, 입력할 때는 하나 이상의 ID를 지정합니다.
    // default: null
    target_ids?: (Array<string> | null);
    // object(기본), group, block, holon. block은 배치 객체 ID; 비기본값은 target_ids 필요.
    // default: "object"
    target_kind?: string;
    // 기본 false. true: target_ids 필수, 확대 전 Isolate.
    // default: false
    isolate?: boolean;
    // 이미지 해상도의 백분율입니다. 1..100 범위이며 기본값은 75입니다.
    // default: 75
    scale_percent?: number;
    // true이면 이미지 크기와 픽셀 기준 토큰 추정치를 포함합니다.
    // default: false
    include_usage?: boolean;
    // 선택 사항인 설치된 래스터 모드 이름/ID입니다. 제공하면 실제 모델 뷰포트를 변경합니다.
    // default: ""
    display_mode?: string;
    // 기본 false. 주변 객체에도 최대 200개 표시 가능.
    // default: false
    labels?: boolean;
    // 레이블 확장 깊이: 1..8, 기본 1.
    // default: 1
    depth?: number;
    // 이미지의 픽셀 너비입니다. 128..2048 범위이며 height도 입력하고 scale_percent=100으로 지정합니다.
    // default: null
    width?: (number | null);
    // 이미지의 픽셀 높이입니다. 128..2048 범위이며 width도 입력하고 scale_percent=100으로 지정합니다.
    // default: null
    height?: (number | null);
    // 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
    // default: ""
    expected_model_path?: string;
  }): Promise<CallToolResult<{
    // 뷰 변경 적용 여부입니다. null이면 중간 상태를 확인해야 합니다.
    mutation_applied?: boolean | null;
    // true이면 현재 Rhino 상태를 확인한 뒤 다음 작업을 정합니다.
    requires_reconciliation?: boolean;
    // 실패한 단계입니다: validate, select, isolate, verify_selection, zoom_selected, redraw.
    failed_stage?: string;
    // 이 호출에서 완료한 뷰 작업입니다. null인 항목은 시도 후 완료를 확인하지 못했습니다.
    view_change?: {
      // 대상 선택 작업 완료 여부입니다.
      selection_changed?: boolean | null;
      // Isolate 완료 여부입니다.
      isolated?: boolean | null;
      // 기본 선택 확대 또는 대상 경계 확대를 완료했는지 나타냅니다.
      zoom_selected?: boolean | null;
      // 성공한 확대 방식입니다. selected는 기본 선택 확대, bounding_box는 기본 방식 실패 후 대상 경계 확대입니다.
      zoom_method?: "selected" | "bounding_box";
      // 화면 표시 모드 변경 완료 여부입니다.
      display_mode_changed?: boolean | null;
      // 격리된 객체의 가시성을 복구하는 Rhino 명령입니다. 카메라와 선택은 별도로 확인합니다.
      restore_visibility_command?: string;
      [key: string]: unknown;
    };
    // 포커스 실행 전후에 확인한 대상과 뷰 상태입니다.
    focus_observation?: {
      // 포커스 대상으로 확인한 객체 수입니다.
      target_count?: number;
      // 문서 단위의 대상 합집합 경계입니다.
      target_bounds?: {
        // 최소 [x, y, z] 좌표입니다.
        // minItems: 3
        // maxItems: 3
        min?: Array<number>;
        // 최대 [x, y, z] 좌표입니다.
        // minItems: 3
        // maxItems: 3
        max?: Array<number>;
        [key: string]: unknown;
      };
      // 대상 경계를 관측하지 못한 이유입니다.
      target_bounds_error?: string;
      // 기본 선택 확대의 관측 결과입니다. null이면 완료 여부를 확인하지 못했습니다.
      zoom_extents_selected?: boolean | null;
      // 대상 경계 확대의 관측 결과입니다. null이면 완료 여부를 확인하지 못했습니다.
      zoom_bounding_box?: boolean | null;
      // 확대 작업 직전에 관측한 뷰 상태입니다.
      before_zoom?: {
        // 관측한 뷰포트의 UUID입니다.
        viewport_id?: string;
        // 평행 투영이면 true입니다.
        parallel_projection?: boolean;
        // 문서 단위의 카메라 위치 [x, y, z]입니다.
        // minItems: 3
        // maxItems: 3
        camera_location?: Array<number>;
        // 문서 단위의 카메라 대상 [x, y, z]입니다.
        // minItems: 3
        // maxItems: 3
        camera_target?: Array<number>;
        // 관측한 [left, right, bottom, top, near, far]입니다.
        // minItems: 6
        // maxItems: 6
        frustum?: Array<number>;
        // 뷰 관측 중 확인하지 못한 정보의 오류입니다.
        observation_error?: string;
        [key: string]: unknown;
      };
      // 포커스 작업 실패 후 관측한 뷰 상태입니다.
      after_failure?: {
        // 관측한 뷰포트의 UUID입니다.
        viewport_id?: string;
        // 평행 투영이면 true입니다.
        parallel_projection?: boolean;
        // 문서 단위의 카메라 위치 [x, y, z]입니다.
        // minItems: 3
        // maxItems: 3
        camera_location?: Array<number>;
        // 문서 단위의 카메라 대상 [x, y, z]입니다.
        // minItems: 3
        // maxItems: 3
        camera_target?: Array<number>;
        // 관측한 [left, right, bottom, top, near, far]입니다.
        // minItems: 6
        // maxItems: 6
        frustum?: Array<number>;
        // 뷰 관측 중 확인하지 못한 정보의 오류입니다.
        observation_error?: string;
        [key: string]: unknown;
      };
      [key: string]: unknown;
    };
    // PNG 저장 결과입니다. 이미지 전달 여부와 별도로 확인합니다.
    image_file?: {
      // 파일 저장 결과입니다. saved일 때 path를 사용할 수 있습니다.
      status?: string;
      // 프로젝트 기준 PNG 상대 경로. output_refs에 기록할 때는 이 문자열만 사용
      path?: string;
      // plan은 Plan 산출물, connection은 연결 정리까지의 임시 파일
      lifetime?: string;
      // 파일 바이트 수
      bytes?: number;
      // 파일 해시.
      sha256?: string;
      [key: string]: unknown;
    };
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    // 이미지 캡처의 처리 상태입니다.
    status?: string;
    [key: string]: unknown;
  }>>;
};
```

### 20. capture\_04-defined\_view

```txt
저장된 Named View 또는 Layout 용지를 PNG로 캡처합니다. 이름·ID는 inspect_03-get_document_context tool에서 조회합니다.

Named View는 저장된 카메라를 사용하고, Layout은 용지와 Detail의 기존 표시 모드를 사용합니다. Named View에 사용할 설치 모드와 용도는 capture_02-inspection tool의 설명을 참고합니다. Layout에는 픽셀 크기와 display_mode를 지정할 수 없습니다. 이미지와 image_file 저장 결과는 별개이며, 사용량 추정·경고는 별도 text content로 반환됩니다. Layout은 인쇄 색과 선폭으로 출력하며 문서의 PrintDisplay 설정을 바꾸지 않습니다. 용지와 Detail에 보이는 인쇄 대상이 없으면 빈 PNG도 정상 결과입니다. Layout Detail 레이블은 지원하지 않습니다.
```

```ts
declare const tools: {
  mcp__rhino__capture_04_defined_view(args: {
    // named_view | layout.
    target_kind: string;
    // 기존 이름 또는 ID입니다. 대소문자를 구분하지 않는 이름 일치는 유일해야 합니다.
    target: string;
    // 범위는 1..100이며 기본값은 75입니다. 원하는 상한이며, 백분율 캡처는 전달 용량 제한에 맞게 축소될 수 있습니다.
    // default: 75
    scale_percent?: number;
    // true이면 이미지 크기와 픽셀 기준 토큰 추정치를 포함합니다.
    // default: false
    include_usage?: boolean;
    // Named View 전용. 기본 Shaded; 설치된 래스터 모드 이름 또는 ID.
    // default: ""
    display_mode?: string;
    // 기본 false. 최대 200개; 주변 레이블이 겹칠 수 있음.
    // default: false
    labels?: boolean;
    // 레이블 깊이: 1..8, 기본 1.
    // default: 1
    depth?: number;
    // 선택 사항인 Named View의 픽셀 너비로, 범위는 128..2048입니다. height도 제공하고 scale_percent=100으로 설정합니다. Layout에는 사용하지 않습니다.
    // default: null
    width?: (number | null);
    // 선택 사항인 Named View의 픽셀 높이로, 범위는 128..2048입니다. width도 제공하고 scale_percent=100으로 설정합니다. Layout에는 사용하지 않습니다.
    // default: null
    height?: (number | null);
    // 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
    // default: ""
    expected_model_path?: string;
  }): Promise<CallToolResult<{
    // PNG 저장 결과입니다. 실제 치수와 축소 경고는 캡처 메타데이터에서 확인합니다.
    image_file?: {
      // 파일 저장 결과입니다. saved일 때 path를 사용할 수 있습니다.
      status?: string;
      // 프로젝트 기준 PNG 상대 경로. output_refs에 기록할 때는 이 문자열만 사용
      path?: string;
      // plan은 Plan 산출물, connection은 연결 정리까지의 임시 파일
      lifetime?: string;
      // 파일 바이트 수
      bytes?: number;
      // 파일 해시.
      sha256?: string;
      [key: string]: unknown;
    };
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    // 이미지 캡처의 처리 상태입니다.
    status?: string;
    [key: string]: unknown;
  }>>;
};
```

## connect

### 21. connect\_01-list\_up

```txt
열린 Rhino 문서와 이 클라이언트의 연결·시작 요청을 조회합니다.

- `targets`: 발견된 문서. 사용 중이거나 확인할 수 없는 대상은 파일 정보가 비어 있을 수 있습니다.
- `connections`: 이 클라이언트가 유지 중인 연결. 연결된 대상은 `targets`에도 표시됩니다.
- `starts`: 이 클라이언트의 Rhino 시작 요청과 상태.

**선택된 연결이 `ready`면 그대로 사용할 수 있습니다.** 대상의 `state`와 `reason`을 확인하세요. 연결할 문서가 있으면 같은 대상의 `host_id`와 저장된 `model_path`를 `connect_02-session` tool에 전달할 수 있습니다. `selected_connection_id`는 이후 일반 호출에 사용할 선택된 연결이며, 선택이 없으면 null입니다. 연결의 `ready`는 일반 작업 가능 상태이며 `recovering`·`unconfirmed`에서는 이전 실행 결과 확인이 필요합니다.
```

```ts
declare const tools: {
  mcp__rhino__connect_01_list_up(args: {}): Promise<CallToolResult<{
    // 연결 목록의 구분과 상태를 읽는 방법입니다.
    instructions?: string;
    // 연결 가능한 Rhino 문서 후보입니다.
    targets?: Array<{
      // 연결 ID입니다. 선택 후 일반 호출에서는 생략할 수 있습니다.
      connection_id?: string | null;
      // Rhino 호스트 ID
      host_id?: string | null;
      // 연결 상태입니다. ready에서 일반 작업을 수행하며 recovering/unconfirmed에서는 실행 결과부터 확인합니다.
      state?: string;
      // 상태 사유 또는 오류 내용. 없으면 빈 문자열
      reason?: string;
      // 저장된 모델의 경로
      model_path?: string | null;
      // 모델 파일명
      model_filename?: string | null;
      // 독립 연결 슬롯. 같은 폴더의 모델은 DB·산출물 루트를 공유
      slot?: string | null;
      // Rhino 프로세스 ID
      pid?: number | null;
      // 이 연결의 임시 작업 폴더입니다.
      artifact_dir?: string | null;
      // 해당 연결에 호출이 진행 중인지 여부
      in_flight?: boolean;
      [key: string]: unknown;
    }>;
    // 현재 유지 중인 연결입니다.
    connections?: Array<{
      // 연결 ID입니다. 선택 후 일반 호출에서는 생략할 수 있습니다.
      connection_id?: string | null;
      // Rhino 호스트 ID
      host_id?: string | null;
      // 연결 상태입니다. ready에서 일반 작업을 수행하며 recovering/unconfirmed에서는 실행 결과부터 확인합니다.
      state?: string;
      // 상태 사유 또는 오류 내용. 없으면 빈 문자열
      reason?: string;
      // 저장된 모델의 경로
      model_path?: string | null;
      // 모델 파일명
      model_filename?: string | null;
      // 독립 연결 슬롯. 같은 폴더의 모델은 DB·산출물 루트를 공유
      slot?: string | null;
      // Rhino 프로세스 ID
      pid?: number | null;
      // 이 연결의 임시 작업 폴더입니다.
      artifact_dir?: string | null;
      // 해당 연결에 호출이 진행 중인지 여부
      in_flight?: boolean;
      [key: string]: unknown;
    }>;
    // Rhino 시작 요청과 진행 상태입니다.
    starts?: Array<{
      // 재사용할 시작 요청 ID입니다.
      request_id?: string;
      // 시작 요청의 상태입니다.
      state?: string;
      // 열 모델의 절대 경로입니다.
      model_path?: string;
      // 연결된 경우의 ID입니다.
      connection_id?: string | null;
      // 현재 상태의 사유입니다.
      reason?: string;
      [key: string]: unknown;
    }>;
    // 이후 호출에서 사용하는 연결 ID입니다. 선택된 연결이 없으면 null입니다.
    selected_connection_id?: string | null;
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 22. connect\_02-session

```txt
열려 있는 저장된 Rhino 문서에 연결하거나 이 클라이언트의 작업 대상을 전환합니다. `connect_01-list_up` tool의 `targets`에서 선택한 같은 대상의 `host_id`와 `model_path`를 사용합니다. 이미 유지 중인 연결도 다시 선택할 수 있습니다.

**선택된 연결**은 이후 일반 도구 호출에 사용됩니다. 반환된 `state`: `ready`는 일반 작업 가능, `recovering`·`unconfirmed`는 이전 실행 결과 확인이 필요한 상태입니다.
```

```ts
declare const tools: {
  mcp__rhino__connect_02_session(args: {
    // connect_01-list_up tool의 targets에서 선택한 Rhino 프로세스의 host_id입니다.
    host_id: string;
    // 같은 연결 대상에 표시된 저장 모델의 정확한 model_path입니다.
    model_path: string;
  }): Promise<CallToolResult<{
    // 연결 상태 확인용 ID입니다.
    connection_id?: string | null;
    // Rhino 호스트 ID
    host_id?: string | null;
    // 연결 상태입니다. ready에서 일반 작업을 수행하며 recovering/unconfirmed에서는 실행 결과부터 확인합니다.
    state?: string;
    // 상태 사유 또는 오류 내용. 없으면 빈 문자열
    reason?: string;
    // 저장된 모델의 경로
    model_path?: string | null;
    // 모델 파일명
    model_filename?: string | null;
    // 독립 연결 슬롯. 같은 폴더의 모델은 DB·산출물 루트를 공유
    slot?: string | null;
    // Rhino 프로세스 ID
    pid?: number | null;
    // 이 연결의 임시 작업 폴더입니다.
    artifact_dir?: string | null;
    // 해당 연결에 호출이 진행 중인지 여부
    in_flight?: boolean;
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 23. connect\_03-start\_session

```txt
저장된 모델을 새 Rhino 창에서 열고 연결합니다.
```

```ts
declare const tools: {
  mcp__rhino__connect_03_start_session(args: {
    // 새 Rhino에서 열 저장된 로컬 .3dm 파일의 절대 경로입니다.
    model_path: string;
    // 이 시작 요청의 고유 ID입니다. 시작이 지연되거나 결과가 불확실하면 새 ID를 만들지 말고 같은 값을 재사용해 상태를 확인합니다.
    // minLength: 1
    // maxLength: 128
    request_id: string;
  }): Promise<CallToolResult<{
    // 연결 상태 확인용 ID입니다.
    connection_id?: string | null;
    // Rhino 호스트 ID
    host_id?: string | null;
    // 연결 상태입니다. ready에서 일반 작업을 수행하며 recovering/unconfirmed에서는 실행 결과부터 확인합니다.
    state?: string;
    // 상태 사유 또는 오류 내용. 없으면 빈 문자열
    reason?: string;
    // 저장된 모델의 경로
    model_path?: string | null;
    // 모델 파일명
    model_filename?: string | null;
    // 독립 연결 슬롯. 같은 폴더의 모델은 DB·산출물 루트를 공유
    slot?: string | null;
    // Rhino 프로세스 ID
    pid?: number | null;
    // 이 연결의 임시 작업 폴더입니다.
    artifact_dir?: string | null;
    // 해당 연결에 호출이 진행 중인지 여부
    in_flight?: boolean;
    // 동일 시작 시도에 재사용. 대기·실패 상태는 connect_01-list_up tool.starts에서 확인
    request_id?: string;
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 24. connect\_04-disconnect

```txt
선택한 연결을 해제하고 Rhino 창과 문서는 유지합니다.
```

```ts
declare const tools: {
  mcp__rhino__connect_04_disconnect(args: {}): Promise<CallToolResult<{
    // 해제한 연결 ID입니다.
    connection_id?: string;
    // 해제한 연결의 Rhino 프로세스 ID입니다. 종료할 창을 식별할 때 model_path와 함께 확인합니다.
    pid?: number | null;
    // 해제한 연결에 저장된 모델 경로입니다. 저장·종료 전에 현재 문서 경로와 일치하는지 확인합니다.
    model_path?: string | null;
    // worker가 종료됐는지 여부
    worker_closed?: boolean;
    // Rhino가 닫혔는지 여부. connect_04-disconnect tool는 false
    rhino_closed?: boolean;
    // Rhino에서 연결 해제를 확인했는지 나타냅니다.
    released?: boolean;
    // 해제 결과 또는 남아 있는 잠금의 사유입니다.
    reason?: string;
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 25. connect\_05-close\_session

```txt
선택한 Rhino 문서를 저장하고 완료를 확인한 뒤 정상 종료합니다.
```

```ts
declare const tools: {
  mcp__rhino__connect_05_close_session(args: {
    // 이 종료 요청의 고유 ID입니다. 지연·불확실 상태에서는 같은 ID로 결과를 조회합니다. 저장 확인 전에는 종료하지 않습니다.
    // minLength: 1
    // maxLength: 128
    request_id: string;
  }): Promise<CallToolResult<{
    // 종료 요청 ID. 같은 값으로 재호출하면 보관된 결과만 조회합니다.
    request_id?: string;
    // 종료 대상 연결 ID입니다.
    connection_id?: string;
    // 시작 identity까지 대조한 종료 대상 Rhino PID입니다.
    pid?: number;
    // 저장과 종료를 요청한 모델의 절대 경로입니다.
    model_path?: string;
    // completed만 저장 확인·Rhino 종료·worker 종료·소유권 해제를 모두 입증합니다.
    status?: "closing" | "completed" | "rejected" | "save_failed" | "unconfirmed";
    // 보관된 마지막 종료 처리 단계입니다.
    stage?: string;
    // Save 완료와 같은 문서의 modified=false를 확인했는지 나타냅니다.
    saved?: boolean;
    // Save 전에 확인한 문서 변경 여부입니다.
    modified_before?: boolean;
    // Save 후 확인한 문서 변경 여부입니다.
    modified_after?: boolean;
    // script_03-get_execution tool으로 확인할 Save 실행 ID입니다.
    save_request_id?: string;
    // 정확한 대상 Rhino 프로세스의 종료를 확인했는지 나타냅니다.
    rhino_closed?: boolean;
    // 해당 연결 worker의 종료를 확인했는지 나타냅니다.
    worker_closed?: boolean;
    // 해당 연결의 소유권 해제를 확인했는지 나타냅니다.
    released?: boolean;
    // 저장 실패, 종료 거부 또는 남아 있는 불확실성의 사유입니다.
    reason?: string;
    // 현재 상태에서 가능한 후속 작업 안내입니다.
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

## context

### 26. context\_01-get\_policy

```txt
Almond 작업의 기본 지침과 활동별 지침을 조회합니다. policy를 생략하면 기본 지침, 공통 도구 이름과 available_policies를 반환하며, 작업에 필요한 지침을 policy로 선택해 읽습니다.

basic 또는 빈 값은 기본 지침과 공통 도구 이름을 반환합니다. metadata는 User Text·UserDictionary를 편집하기 전 확인하는 지침(text)과 객체 키 사전(policy)을 함께 반환합니다. rhino_scripting은 내장 Rhino 스크립팅 참고자료, rhinocode는 코드·명령 실행 지침입니다. spatial_modeling, observation, drawing, feedback_reporting은 각 활동의 판단 기준입니다.

선택에 따라 본문은 text, policy 또는 scripting_skill에 담깁니다. source_refs에서 출처와 해시를 확인하고 같은 guide_version에서 이미 읽은 지침은 재사용할 수 있습니다. 개별 도구의 호출법은 해당 도구의 공개 설명과 스키마를 확인합니다.
```

```ts
declare const tools: {
  mcp__rhino__context_01_get_policy(args: {
    // 생략 또는 빈 문자열은 basic. 선택값의 용도는 available_policies 참고.
    // default: ""
    policy?: "" | "basic" | "metadata" | "rhino_scripting" | "rhinocode" | "spatial_modeling" | "observation" | "drawing" | "feedback_reporting";
  }): Promise<CallToolResult<{
    // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
    status?: string;
    // 지침 버전을 비교하는 해시입니다.
    guide_version?: string;
    // 선택한 policy의 지침 본문입니다.
    text?: string;
    // 선택한 지침의 출처 파일과 해시입니다.
    source_refs?: Array<{
      // 안내문 출처 경로
      path?: string;
      // 파일 해시.
      sha256?: string;
      [key: string]: unknown;
    }>;
    // 사용할 수 있는 도구 이름 목록입니다.
    tools?: Array<string>;
    // 선택한 policy 이름입니다.
    selected_policy?: string;
    // 선택 가능한 policy 이름과 설명입니다.
    available_policies?: {
      [key: string]: string;
    };
    // metadata 지침 JSON입니다. 키와 중첩 값은 열린 객체로 유지합니다.
    policy?: {
      [key: string]: unknown;
    };
    // rhino_scripting 선택 시 반환하는 내장 Rhino 스크립팅 자료입니다.
    scripting_skill?: {
      // 내장 스크립팅 skill의 이름입니다.
      name?: string;
      // 출처 경로·해시와 원문을 포함한 스크립팅 참고자료입니다.
      sources?: Array<{
        // 저장소 기준 출처 경로입니다. src/mcp/로 시작합니다.
        path?: string;
        // 줄바꿈 등을 정규화한 출처 파일의 SHA-256입니다.
        sha256?: string;
        // 해당 참고자료의 원문입니다.
        text?: string;
        [key: string]: unknown;
      }>;
      [key: string]: unknown;
    };
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 27. context\_04-get\_project\_info

```txt
연결된 Rhino 문서와 프로젝트의 작업 정보를 조회합니다. 작업을 시작하거나 이어갈 때 현재 문서, 등록 파일과 작업 공간을 확인하는 데 사용합니다.

`sections`로 필요한 정보를 선택합니다. project는 프로젝트 경로·현재 문서와 연결 모델의 일치 여부·등록 파일, document는 현재 문서의 단위·허용오차·객체 수 등, named_views와 layouts는 저장된 뷰와 용지, layer_tree는 모든 활성 레이어의 들여쓰기 계층, locations는 선택된 작업 공간과 공유 DB, runtime은 연결 실행 환경입니다. 위치·실행 환경만 요청하면 Rhino 문서 관찰을 수행하지 않습니다. sections를 생략하면 runtime을 제외한 모든 섹션을 조회합니다. 문서의 개별 값을 읽지 못하면 해당 값은 null이며 warnings에 사유가 나옵니다.

`project.worksession_files`는 활성 문서를 제외하고 Rhino에 현재 첨부된 Worksession 파일입니다. `[]`는 첨부 없음, `null`은 조회 실패이며 실패 사유는 warnings에서 확인합니다. `project.files`는 DB의 별도 등록 목록입니다. 등록한 모델은 실제 파일이 확인되면 필요할 때 첨부할 수 있습니다. Worksession 조회·첨부·해제로 DB 등록은 바뀌지 않습니다.

Named View와 Layout은 각각 이름과 ID를 최대 128개 반환하며 목록이 잘리면 warnings에 표시합니다. 두 목록의 ID는 include_ids 설정과 관계없이 반환합니다. 레이어 트리는 깊이당 공백 두 칸을 사용하며 레이어가 없으면 빈 문자열, 조회 실패 시 null입니다.

`project.files`에 파일명과 파일별 설명이 표시됩니다. 파일 등록과 설명 갱신에는 context_05-upsert_project_file tool을 사용합니다. Phase와 Scene에서 파일을 연결할 때는 등록 파일명을 선택합니다. 목록이 잘리면 `files_page`의 offset과 limit을 더해 `files_offset`으로 다음 페이지를 조회합니다. 후속 작업에 필요한 Plan과 Step 식별자는 `include_ids=true`로 포함합니다. 프로젝트 내부 경로는 project_root 기준 상대경로로 반환됩니다.
```

```ts
declare const tools: {
  mcp__rhino__context_04_get_project_info(args: {
    // project, document, named_views, layouts, layer_tree, locations, runtime. 기본은 runtime을 제외한 모든 섹션.
    // default: null
    sections?: (Array<string> | null);
    // 기본 false.
    // default: false
    include_ids?: boolean;
    // 등록 파일 페이지 크기: 정수 1~500, 기본 50.
    // default: 50
    files_limit?: number;
    // 등록 파일의 시작 위치: 0 이상의 정수, 기본 0.
    // default: 0
    files_offset?: number;
  }): Promise<CallToolResult<{
    // 저장된 Named View 이름과 ID입니다. 최대 128개이며 일부만 반환하면 warnings에 표시합니다. 조회 실패 시 null입니다.
    named_views?: Array<{
      // Named View 이름입니다.
      name?: string;
      // Named View 식별자입니다. include_ids 설정과 관계없이 반환합니다.
      id?: string;
      [key: string]: unknown;
    }> | null;
    // 저장된 Layout 이름과 ID입니다. 최대 128개이며 일부만 반환하면 warnings에 표시합니다. 조회 실패 시 null입니다.
    layouts?: Array<{
      // Layout 이름입니다.
      name?: string;
      // Layout 식별자입니다. include_ids 설정과 관계없이 반환합니다.
      id?: string;
      [key: string]: unknown;
    }> | null;
    // 삭제되지 않은 모든 레이어의 이름과 부모 관계입니다. 깊이당 공백 두 칸으로 들여씁니다. 레이어가 없으면 빈 문자열, 조회에 실패하면 null입니다.
    layer_tree?: string | null;
    // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
    status?: string;
    // 문서 속성을 읽지 못한 사유 등 native 관찰 경고입니다. 읽지 못한 개별 값은 null일 수 있습니다.
    warnings?: Array<string>;
    // 현재 연결 문서와 프로젝트 정보입니다.
    project?: {
      // 프로젝트의 절대 경로입니다. 프로젝트 파일 도구의 상대 경로 기준입니다.
      project_root?: string;
      // 파일명입니다.
      file_name?: string | null;
      // 파일 경로입니다.
      file_path?: string | null;
      // 현재 Rhino 문서가 이 연결의 모델과 일치하는지 나타냅니다.
      is_bound_document?: boolean;
      // 프로젝트에 등록한 Rhino 파일 목록입니다.
      files?: Array<{
        // Phase 또는 Scene에서 선택할 수 있는 등록 파일명입니다.
        file_name?: string;
        // 파일별 설명입니다. 기록된 설명이 없으면 null입니다.
        description?: string | null;
        [key: string]: unknown;
      }>;
      // Rhino에 현재 첨부한 참조 목록입니다. 활성 문서는 제외합니다. 첨부가 없으면 빈 배열, 조회에 실패하면 null입니다.
      worksession_files?: Array<{
        // 첨부 파일명입니다.
        file_name?: string;
        // 첨부 파일 경로입니다. 다른 드라이브의 경로는 절대 경로로 반환합니다.
        file_path?: string;
        [key: string]: unknown;
      }> | null;
      // 등록 파일 목록의 페이지 정보입니다.
      files_page?: {
        // 조회 조건에 맞는 전체 항목 수입니다.
        total?: number;
        // 이번 응답의 최대 항목 수입니다.
        limit?: number;
        // 이번 페이지의 시작 위치입니다.
        offset?: number;
        // true면 같은 조건에서 files_offset을 offset+limit으로 이어감
        truncated?: boolean;
        [key: string]: unknown;
      };
      [key: string]: unknown;
    };
    // 현재 Rhino 문서의 관찰 속성입니다. 개별 값은 관찰 실패 시 null이며, 오류 응답의 원문 document 자체도 null일 수 있습니다.
    document?: {
      // Rhino 문서의 런타임 일련번호입니다. include_ids=true일 때 포함합니다.
      runtime_serial_number?: number | null;
      // 현재 문서의 모델 단위입니다.
      units?: string | null;
      // 현재 문서 단위로 표현한 절대 허용오차입니다.
      absolute_tolerance?: number | null;
      // 각도 허용오차이며 단위는 라디안입니다.
      angle_tolerance_radians?: number | null;
      // 문서에 저장하지 않은 변경이 있는지 나타냅니다.
      modified?: boolean | null;
      // 관찰한 문서의 객체 수입니다.
      object_count?: number | null;
      // 관찰한 문서의 활성 레이어 수입니다.
      layer_count?: number | null;
      [key: string]: unknown;
    };
    // 현재 연결의 작업 공간과 공유 데이터베이스 위치입니다.
    locations?: {
      // 현재 작업 대상으로 선택한 Plan ID입니다.
      plan_id?: string;
      // Step ID입니다.
      step_id?: string;
      // 현재 연결에서 선택한 작업 회차입니다. 0은 실행 전 기록입니다.
      loop_no?: number;
      // 선택한 회차가 최신 회차보다 과거이면 true입니다.
      read_only?: boolean;
      // 선택한 Plan의 산출물 루트이며 프로젝트 기준 상대경로입니다.
      plan_artifact_dir?: string | null;
      // 현재 연결에서 사용할 Plan·Loop 산출물 폴더입니다. 선택 전에는 null입니다.
      artifact_dir?: string | null;
      // 공유 데이터베이스 경로입니다.
      database?: string;
      // 관리형 도구에 전달할 프로젝트 상대경로 사용 안내입니다.
      path_rule?: string;
      // Plan 선택과 현재 회차의 산출물 폴더 사용 안내입니다.
      artifact_rule?: string;
      [key: string]: unknown;
    };
    // 요청한 runtime 섹션의 연결 실행 환경입니다. 프로젝트 내부 경로는 상대경로로 반환합니다.
    runtime?: {
      // 현재 연결의 슬롯 이름입니다.
      slot?: string;
      // 현재 연결 binding의 포트 번호입니다.
      port?: number;
      // 현재 연결의 세션 기록 폴더입니다.
      session_dir?: string;
      // 현재 연결의 Python 작업별 임시자료 루트입니다.
      scratch_root?: string;
      // 연결 시 기록한 Rhino 프로세스의 TEMP 경로입니다. 기록이 없으면 null입니다.
      rhino_temp_at_attach?: string | null;
      // Rhino TEMP와 산출물 폴더의 차이를 설명합니다.
      rhino_temp_note?: string;
      // 현재 worker가 실행 중인 Python 실행 파일 경로입니다.
      python_executable?: string;
      // 현재 연결 binding의 attachment 식별자입니다.
      attachment?: string;
      // 현재 연결에서 RhinoCode를 사용할 수 있는지와 실행 환경 또는 불가 사유입니다.
      rhinocode?: {
        // 현재 연결에서 허용된 RhinoCode 실행 언어를 사용할 수 있는지 나타냅니다.
        available?: boolean;
        // 발견한 RhinoCode 실행 파일 경로입니다.
        executable?: string;
        // 선택한 RhinoCode 인스턴스의 pipe ID입니다. include_ids=true일 때 포함합니다.
        pipe_id?: string;
        // RhinoCode 인스턴스의 processVersion 원본 값입니다. 반환 타입을 강제하지 않습니다.
        version?: unknown;
        // 현재 연결에서 허용된 실행 언어 목록입니다. 사용할 수 없으면 빈 목록입니다.
        languages?: Array<string>;
        // RhinoCode를 사용할 수 없는 경우의 사유입니다.
        message?: string;
        [key: string]: unknown;
      };
      [key: string]: unknown;
    };
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    [key: string]: unknown;
  }>>;
};
```

### 28. context\_05-upsert\_project\_file

```txt
프로젝트 파일 카탈로그에 모델 파일을 등록하거나, 등록된 파일의 설명을 수정합니다. 같은 프로젝트에서 Windows 기준으로 같은 이름은 한 파일입니다. 기존 파일은 원래 표기를 유지합니다. 이 작업은 Rhino에서 파일을 열거나 Worksession에 첨부하지 않습니다.

등록 결과는 context_04-get_project_info tool의 project.files에 나타납니다. Phase와 Scene은 그 목록의 파일명을 사용합니다.
```

```ts
declare const tools: {
  mcp__rhino__context_05_upsert_project_file(args: {
    // 폴더를 제외한 모델 파일명입니다. 프로젝트 안에서 고유해야 합니다.
    file_name: string;
    // 파일을 사용하는 목적이나 내용을 설명합니다. 생략/null은 기존 설명 유지, 빈 문자열은 설명 삭제입니다.
    // default: null
    description?: (string | null);
  }): Promise<CallToolResult<{
    // 등록 또는 설명 갱신의 결과입니다.
    status?: string;
    // 프로젝트에 등록한 파일명입니다.
    file_name?: string;
    // 저장한 파일 설명입니다.
    description?: string | null;
    // 등록 또는 갱신에 실패한 사유입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    [key: string]: unknown;
  }>>;
};
```

## diagram

### 29. diagram\_01-get

```txt
다이어그램 자산 하나의 등록 정보와 파일 존재 상태를 조회합니다. 목록이나 검색에서 얻은 ID로 조회하며, 파일이 없는 등록 항목도 조회됩니다.
```

```ts
declare const tools: {
  mcp__rhino__diagram_01_get(args: {
    // 목록·검색에서 얻은 자산 ID. 대소문자·공백까지 정확히 지정.
    asset_id: string;
    // true: 다른 식별자 포함. 입력 asset_id는 응답에 반복되지 않음.
    // default: false
    include_ids?: boolean;
    // dimensions, drawing, metadata, source, paths, audit, all. 생략·빈 배열: 요약. all: 다른 그룹 외 등록 필드도 포함.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 선택한 다이어그램 자산의 정보입니다.
  asset?: {
    // 저장된 이름
    name?: string;
    // 색인에 기록한 원본 파일의 존재 여부입니다.
    file_available?: boolean;
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 30. diagram\_02-list

```txt
사람·나무·기호 등 2D 벡터·CAD 다이어그램의 등록 목록을 조회합니다. 목록에 파일이 없는 항목도 포함되며, 자산 ID로 diagram_01-get tool에서 세부 정보와 사용 가능 상태를 확인할 수 있습니다. 키워드·치수 검색은 diagram_04-search tool을 사용합니다.
```

```ts
declare const tools: {
  mcp__rhino__diagram_02_list(args: {
    // 분류값 전체 일치, 대소문자 무시. 빈 값: 전체.
    // default: ""
    category?: string;
    // 기본 20, 1..50으로 보정.
    // default: 20
    limit?: number;
    // 0부터 시작. 음수는 0으로 보정.
    // default: 0
    offset?: number;
    // true이면 후속 호출에 사용할 ID를 포함합니다.
    // default: false
    include_ids?: boolean;
    // 선택 가능한 세부 그룹은 dimensions, drawing, metadata, source, paths, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // include_ids=true에서 유지되는 라이브러리 구분자
  library_id?: string;
  // 다이어그램 자산과 요청한 속성입니다.
  assets?: Array<{
    [key: string]: unknown;
  }>;
  // 필터에 일치하는 전체 항목 수
  total?: number;
  // 현재 페이지 시작 위치
  offset?: number;
  // 페이지 최대 항목 수
  limit?: number;
  // 다음 페이지의 시작 위치입니다. null이면 다음 페이지가 없습니다.
  next_offset?: number | null;
  // 이 라이브러리의 용도입니다.
  purpose?: string;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 31. diagram\_03-place

```txt
SVG·DWG·DXF 다이어그램을 Rhino 문서의 블록 인스턴스로 배치합니다.
응답 유실 등으로 requires_reconciliation이 true이면 Rhino 문서에서 실제 배치 결과를 확인한 뒤 다음 작업을 결정합니다.
```

```ts
declare const tools: {
  mcp__rhino__diagram_03_place(args: {
    // include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다.
    asset_id: string;
    // 현재 Rhino 문서 단위를 사용하는 배치 X 좌표입니다.
    // default: 0
    x?: number;
    // 현재 Rhino 문서 단위를 사용하는 배치 Y 좌표입니다.
    // default: 0
    y?: number;
    // 현재 Rhino 문서 단위를 사용하는 배치 Z 좌표입니다.
    // default: 0
    z?: number;
    // 월드 Z축을 중심으로 한 회전각이며, 단위는 도입니다.
    // default: 0
    rotation_degrees?: number;
    // 양수인 균일 배치 축척입니다. 1이면 단위 변환 후 자산 크기를 유지합니다.
    // default: 1
    scale?: number;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 자산 ID
  asset_id?: string;
  // 삽입한 최상위 블록 GUID. inspect_02-get_objects tool 또는 Scene 구성원 입력에 재사용
  object_guid?: string;
  // 새 블록 정의를 생성했는지 나타냅니다.
  definition_created?: boolean;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // 실제 변경 근거에 따른 상태입니다. unknown/partial이면 변경이 남았을 수 있습니다.
  mutation_state?: string;
  // true이면 실제 문서 상태를 확인한 뒤 다음 작업을 결정합니다. 자동 재실행을 허용하지 않습니다.
  requires_reconciliation?: boolean;
  // 변경 적용 여부입니다. null이면 실제 적용 여부를 확인하지 못했습니다.
  mutation_applied?: boolean | null;
  [key: string]: unknown;
};
```

### 32. diagram\_04-search

```txt
사람·나무 등 등록된 2D 다이어그램을 키워드·분류·최대 치수로 검색합니다. 파일이 없는 자산도 결과에 포함됩니다. 상세 등록 정보와 파일 존재 상태는 diagram_01-get tool에서 조회할 수 있습니다.
```

```ts
declare const tools: {
  mcp__rhino__diagram_04_search(args: {
    // 여러 검색어는 OR로 결합. 빈 값: 전체.
    // default: ""
    query?: string;
    // 분류 전체 일치, 대소문자 무시. 빈 값: 전체.
    // default: ""
    category?: string;
    // 측정된 자산 너비의 최댓값이며, 밀리미터 단위입니다. 선택 사항이며, 0은 이 크기 필터를 해제합니다.
    // default: 0
    max_width_mm?: number;
    // 등록 치수 상한(mm). 0 이하: 필터 해제. 등록 치수는 추정치일 수 있음.
    // default: 0
    max_depth_mm?: number;
    // 측정된 자산 높이의 최댓값이며, 밀리미터 단위입니다. 선택 사항이며, 0은 이 크기 필터를 해제합니다.
    // default: 0
    max_height_mm?: number;
    // 기본 10, 1..50으로 보정.
    // default: 10
    limit?: number;
    // 0부터 시작, 음수는 0으로 보정. 다음 페이지에도 같은 필터 사용.
    // default: 0
    offset?: number;
    // true: 자산 ID 포함.
    // default: false
    include_ids?: boolean;
    // dimensions, drawing, metadata, source, paths, audit, all. 생략·빈 배열: 요약. 세부 항목은 검색 결과에 나타나지 않을 수 있음.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 검색된 다이어그램 자산과 요청한 속성입니다.
  assets?: Array<{
    [key: string]: unknown;
  }>;
  // 필터에 일치하는 전체 항목 수
  total?: number;
  // 현재 페이지 시작 위치
  offset?: number;
  // 페이지 최대 항목 수
  limit?: number;
  // 다음 페이지의 시작 위치입니다. null이면 다음 페이지가 없습니다.
  next_offset?: number | null;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

## drawing

### 33. drawing\_01-apply\_style

```txt
도면 레시피의 레이어 계층과 색·출력색·출력 선 두께·선종류를 Rhino 문서에 생성하거나 갱신합니다. 같은 경로의 기존 레이어에도 적용됩니다. 문서에 같은 이름의 선종류가 있으면 기존 정의를 재사용합니다. 새 선종류를 만들 때는 Almond에 포함된 선종 매니페스트를 사용합니다. 레시피의 투영·축척·용지 설정으로 도면이나 Layout을 만들지는 않습니다. 변경 전에 전용 Undo record를 확보하며 실패 시 그 record만 복구합니다. mutation_state는 none·completed·rolled_back·unknown이며 requires_reconciliation=true이면 문서를 확인하기 전 자동 재시도하지 않습니다.
```

```ts
declare const tools: {
  mcp__rhino__drawing_01_apply_style(args: {
    // drawing_05-list_recipes tool 또는 drawing_02-get_recipe tool의 레시피 ID. 생략: technical_axon_v1.
    // default: "technical_axon_v1"
    recipe_id?: string;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 도면 레시피 ID입니다.
  recipe_id?: string;
  // 스타일을 적용한 레이어입니다.
  layers?: Array<{
    // inspect_02-get_objects tool의 layer_paths 필터로 연결 가능
    path?: string;
    // 레이어 역할입니다.
    role?: string;
    // Rhino 레이어 인덱스입니다.
    layer_index?: number;
    // 출력 선 두께(mm)입니다.
    plot_weight_mm?: number;
    // 선 종류입니다.
    linetype?: string;
    [key: string]: unknown;
  }>;
  // A4 레시피에서 준비한 검토용 정보입니다.
  review_preparation?: {
    // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
    status?: string;
    // 연결 Rhino PID·문서 경로에 맞는 파이프 확인 안내
    message?: string;
    // 검토 출력에 사용할 CLI 실행 정보입니다.
    cli?: {
      // 실행할 프로그램입니다.
      program?: string;
      // 실행 환경 확인에 사용할 인수입니다.
      discovery_arguments?: Array<string>;
      // 검토 출력 명령의 인수 템플릿입니다.
      arguments_template?: Array<string>;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // 실제 변경 근거에 따른 상태입니다. unknown/partial이면 변경이 남았을 수 있습니다.
  mutation_state?: string;
  // true이면 실제 문서 상태를 확인한 뒤 다음 작업을 결정합니다. 자동 재실행을 허용하지 않습니다.
  requires_reconciliation?: boolean;
  [key: string]: unknown;
};
```

### 34. drawing\_02-get\_recipe

```txt
지정한 도면 스타일 레시피를 조회합니다. field_groups=["scales","parameters"]로 권장 축척·레이어·출력 설정을 확인한 뒤 같은 recipe_id를 drawing_01-apply_style tool에 전달합니다. result는 레시피 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: {
  mcp__rhino__drawing_02_get_recipe(args: {
    // drawing_05-list_recipes tool(include_ids=true)에서 얻은 도면 레시피 ID 또는 이미 알고 있는 레시피 ID입니다.
    recipe_id: string;
    // true이면 후속 호출에 사용할 ID를 포함합니다.
    // default: false
    include_ids?: boolean;
    // 상세 그룹: scales, parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 선택한 레시피의 요약과 field_groups로 요청한 설정입니다. 적용에 같은 recipe_id를 사용합니다.
  recipe?: {
    // 이름입니다.
    name?: string;
    // 레시피 자체의 설명 문자열
    description?: string;
    // 도면 투영 설정입니다.
    projection?: {
      // 투영 방식입니다.
      type?: string;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 35. drawing\_04-import\_hatches

```txt
등록된 PAT 자산의 해치 패턴 정의를 Rhino 문서에 가져옵니다. 같은 이름이 이미 있으면 기존 정의를 재사용합니다. 도면에 해치 객체를 배치하지는 않습니다.
```

```ts
declare const tools: {
  mcp__rhino__drawing_04_import_hatches(args: {
    // 등록된 PAT 도면 자산 ID.
    asset_id: string;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 신규뿐 아니라 기존에 있어 사용 가능한 패턴 이름도 포함
  patterns?: Array<string>;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 진단 정보입니다.
  error_trace?: unknown;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 36. drawing\_05-list\_recipes

```txt
사용 가능한 도면 스타일 레시피를 조회합니다. A4 평면·단면에는 Architectural Plan and Section A4를 선택합니다. include_ids=true로 얻은 recipe_id는 drawing_02-get_recipe tool의 입력에 사용합니다. result는 목록 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: {
  mcp__rhino__drawing_05_list_recipes(args: {
    // true이면 후속 호출에 사용할 ID를 포함합니다.
    // default: false
    include_ids?: boolean;
    // 상세 그룹: scales, parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 조회된 레시피 수입니다.
  total?: number;
  // 도면 레시피의 요약과 field_groups로 요청한 추가 속성입니다.
  recipes?: Array<{
    // drawing_02-get_recipe tool 또는 drawing_01-apply_style tool에 입력하는 레시피 ID입니다.
    recipe_id?: string;
    // 이름입니다.
    name?: string | null;
    // 설명입니다.
    description?: string | null;
    // 투영 방식입니다.
    projection?: string | null;
    // 권장 축척의 분모 목록입니다.
    recommended_scales?: Array<string>;
    [key: string]: unknown;
  }>;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 37. drawing\_06-generate\_plan\_section

```txt
활성 모델 또는 현재 Worksession에 첨부된 파일의 클리핑 평면으로 단면선·가시 입면선과 선택적 해치를 활성 모델에 생성합니다. 첨부 형상이 필요하면 먼저 필요한 파일을 Worksession에 첨부한 뒤 include_attachments를 선택합니다. Update는 저장된 위치에서 도면을 다시 계산하므로 기존 도면의 수동 편집이 교체될 수 있습니다. Move는 기존 도면 객체의 GUID와 수동 편집을 유지하며 원점을 옮깁니다.

응답에는 클리핑별 상태와 도면 객체 GUID, 실제 배치 평면이 포함됩니다. Create·Update에는 실제 계산에 들어간 원본 레이어와 객체 수, 숨김·잠금·첨부 입력의 처리 조건도 포함됩니다. 일부 완료 또는 취소 뒤에는 완료된 도면이 남을 수 있습니다.

변경 도중 실패하면 각 항목의 recovery.attempts에 객체·속성·레이어의 복구 대상과 성공/실패를 보존합니다. 한 복구가 실패해도 나머지는 계속 시도합니다. tracked_changes_restored는 추적한 변경의 복구 결과이며 원자적 rollback을 보장하지 않습니다. mutation_state가 partial 또는 unknown이고 requires_reconciliation이 true이면 실제 도면을 확인하거나 Undo한 뒤 다음 작업을 결정하고 자동으로 재시도하지 마세요.
```

```ts
declare const tools: {
  mcp__rhino__drawing_06_generate_plan_section(args: {
    // Create는 생성 또는 교체, Update는 저장 위치에서 재생성, Move는 기존 도면의 평행이동.
    operation: "Create" | "Update" | "Move";
    // 활성 모델 또는 현재 Worksession 첨부 파일의 클리핑 평면 GUID 목록. 비어 있을 수 없으며 중복은 한 번만 처리.
    clipping_ids: Array<string>;
    // 클리핑 GUID별 절대 도면 원점 [x,y] 또는 [x,y,z], 문서 단위. Create에서 선택, Move에서 모든 GUID에 필수, Update에서 생략.
    // default: null
    points?: ({
      [key: string]: Array<(number | number)>;
    } | null);
    // 해치 생성 허용. 원본 단면 스타일의 채움과 형상 조건을 따름. 기본 true.
    // default: true
    hatch?: boolean;
    // 작은 입면 상세를 보호할지 여부. 기본 false.
    // default: false
    small_details?: boolean;
    // 가까운 입면선 출력 두께(mm). 기본 0.09, 양수이며 far_width 이상.
    // default: 0.09
    near_width?: (number | number);
    // 먼 입면선 출력 두께(mm). 기본 0.04, 양수이며 near_width 이하.
    // default: 0.04
    far_width?: (number | number);
    // 가까운 입면선 출력 농도 0..100%. 기본 80, far_dark 이상.
    // default: 80.0
    near_dark?: (number | number);
    // 먼 입면선 출력 농도 0..100%. 기본 45, near_dark 이하.
    // default: 45.0
    far_dark?: (number | number);
    // true면 활성 모델과 현재 Worksession 첨부 형상을 계산합니다. false면 활성 모델 형상만 계산합니다. Create에서 기본 false, Update에서 생략하면 기존 도면의 설정을 사용합니다. Move는 배치만 변경합니다.
    // default: null
    include_attachments?: (boolean | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 요청 결과입니다. success, partial, cancelled, error를 구분합니다.
  status?: string;
  // 도면 계산의 completed, partial, cancelled, failed 상태입니다.
  drawing_status?: string;
  // 알려진 모델 변경 상태입니다. unknown이면 도면을 확인합니다.
  mutation_state?: string;
  // 재호출 전 현재 도면 상태를 확인해야 합니다.
  requires_reconciliation?: boolean;
  // 보상이 필요했던 클리핑별 오류와 복구 근거입니다.
  recovery?: Array<{
    // 처리한 클리핑 평면 GUID입니다.
    clipping_id?: string;
    // 최초 도면 변경 실패 원문입니다.
    error?: string;
    // 시도한 보상과 실패 내역입니다. 알려진 변경 복구는 원자적 rollback의 증명이 아닙니다.
    recovery?: {
      // 보상 실패가 있으면 partial, 미확인 변경 가능성이 남으면 unknown입니다.
      mutation_state?: string;
      // 다음 변경 전에 실제 도면을 확인해야 하는지 나타냅니다.
      requires_reconciliation?: boolean;
      // 기록된 변경에 대한 모든 보상 시도가 성공했는지 나타냅니다.
      tracked_changes_restored?: boolean;
      // 모든 보상 시도의 결과입니다.
      attempts?: Array<{
        // 시도한 보상 동작입니다.
        action?: string;
        // 보상 대상 객체, 레이어 또는 기록입니다.
        target?: string;
        // restored 또는 failed입니다.
        status?: string;
        // 보상 실패 원문입니다.
        error?: string;
        [key: string]: unknown;
      }>;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  }>;
  // 클리핑별 도면 결과와 실제 추출 조건입니다.
  result?: {
    // 도면 계산의 종합 상태입니다.
    status?: string;
    // 요청한 서로 다른 클리핑 수입니다.
    requested?: number;
    // 처리를 완료한 클리핑 수입니다.
    completed?: number;
    // 실패한 도면 변경의 실제 상태 확인이 필요한지 나타냅니다.
    requires_reconciliation?: boolean;
    // 처리한 클리핑별 결과입니다.
    results?: Array<{
      // 실제로 처리한 클리핑 평면의 GUID입니다.
      clipping_id?: string;
      // 클리핑 평면의 이름입니다.
      name?: string | null;
      // 해당 클리핑의 처리 상태입니다.
      status?: string;
      // 생성, 갱신 또는 이동한 도면 객체의 GUID입니다.
      object_ids?: Array<string>;
      // 완료한 도면의 실제 배치 평면입니다.
      draw_plane?: {
        // minItems: 3
        // maxItems: 3
        origin?: Array<number>;
        // minItems: 3
        // maxItems: 3
        xaxis?: Array<number>;
        // minItems: 3
        // maxItems: 3
        yaxis?: Array<number>;
        [key: string]: unknown;
      };
      // Create·Update에서 실제 계산에 사용한 추출 조건입니다.
      extraction?: {
        // 사용한 원본 레이어 전체 경로입니다.
        layers?: Array<string>;
        // 계산에 사용한 원본 객체 수입니다.
        source_object_count?: number;
        // 숨겨진 원본 객체 처리 허용 여부입니다.
        include_hidden?: boolean;
        // 잠긴 원본 객체 처리 허용 여부입니다.
        include_locked?: boolean;
        // Worksession 첨부 형상의 처리 허용 여부입니다.
        include_attachments?: boolean;
        [key: string]: unknown;
      };
      // 계산 단계와 제외 또는 정리된 형상에 대한 보고입니다.
      report?: {
        [key: string]: unknown;
      };
      // 해당 클리핑의 계산 오류입니다.
      error?: string;
      // 시도한 보상과 실패 내역입니다. 알려진 변경 복구는 원자적 rollback의 증명이 아닙니다.
      recovery?: {
        // 보상 실패가 있으면 partial, 미확인 변경 가능성이 남으면 unknown입니다.
        mutation_state?: string;
        // 다음 변경 전에 실제 도면을 확인해야 하는지 나타냅니다.
        requires_reconciliation?: boolean;
        // 기록된 변경에 대한 모든 보상 시도가 성공했는지 나타냅니다.
        tracked_changes_restored?: boolean;
        // 모든 보상 시도의 결과입니다.
        attempts?: Array<{
          // 시도한 보상 동작입니다.
          action?: string;
          // 보상 대상 객체, 레이어 또는 기록입니다.
          target?: string;
          // restored 또는 failed입니다.
          status?: string;
          // 보상 실패 원문입니다.
          error?: string;
          [key: string]: unknown;
        }>;
        [key: string]: unknown;
      };
      [key: string]: unknown;
    }>;
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  [key: string]: unknown;
};
```

## grasshopper

### 38. grasshopper\_01-get\_logic

```txt
색인된 Grasshopper 로직 파일에서 추출한 물리 관련 항목·설명과 제공된 메타데이터를 조회합니다. JSON만 있는 항목은 메타데이터를 반환합니다. 추출 정보는 완전한 구성·연결 관계나 실행 가능성을 보장하지 않습니다.
```

```ts
declare const tools: {
  mcp__rhino__grasshopper_01_get_logic(args: {
    // 확장자를 뺀 라이브러리 파일명. grasshopper_03-list_library tool의 logic_names 사용 가능.
    logic_id: string;
    // true: 다른 식별자 포함. 입력 logic_id는 반복되지 않음.
    // default: false
    include_ids?: boolean;
    // ports, definition, source, paths, audit, all. 제공된 필드에만 적용.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 파일명입니다.
  file_name?: string;
  // 정의에 사용한 컴포넌트입니다.
  components?: Array<{
    // 이름입니다.
    name?: string;
    // 분류입니다.
    category?: string;
    // 컴포넌트에 기록된 설명입니다.
    descriptions?: Array<string>;
    [key: string]: unknown;
  }>;
  // 정의에서 수집한 설명 목록입니다.
  all_descriptions?: Array<string>;
  // 정의 파일에서 읽은 메타데이터입니다.
  metadata?: {
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 39. grasshopper\_02-list\_capsules

```txt
등록된 Grasshopper 캡슐의 기능과 감사 상태를 조회합니다. 포트와 ID를 확인해 grasshopper_04-run_definition tool의 입력을 준비할 수 있습니다. 감사 상태는 정의 파일의 존재나 실행 성공을 보장하지 않습니다.
```

```ts
declare const tools: {
  mcp__rhino__grasshopper_02_list_capsules(args: {
    // 기능 필터: analyze, generate, form_find, aggregate. 대소문자 무시.
    // default: ""
    capability?: string;
    // true: audited로 등록된 캡슐만.
    // default: false
    audited_only?: boolean;
    // true: capsule_id 포함. all과 별도 지정.
    // default: false
    include_ids?: boolean;
    // ports, definition, source, paths, audit, all. 생략·빈 배열: 요약.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 조회 조건에 맞는 전체 항목 수입니다.
  total?: number;
  // 이번 페이지의 시작 위치입니다.
  offset?: number;
  // 이번 응답의 최대 항목 수입니다.
  limit?: number;
  // 다음 페이지의 시작 위치입니다. null이면 다음 페이지가 없습니다.
  next_offset?: number | null;
  // 실행 캡슐과 요청한 포트·정의 정보입니다.
  capsules?: Array<{
    // audited=true일 때 grasshopper_04-run_definition tool에 사용 가능
    capsule_id?: string;
    // 캡슐의 기능입니다.
    capability?: string;
    // 구조 유형입니다. 지정되지 않은 캡슐은 null입니다.
    structure_type?: string | null;
    // 캡슐 라이브러리 안의 정의 파일명입니다.
    definition_file?: string;
    // 제목입니다.
    title?: string;
    // 실행 허용 검사를 통과했는지 나타냅니다.
    audited?: boolean;
    // 캡슐 입력 포트 이름입니다. 타입·단위·필수 여부는 input_ports에 있습니다.
    inputs?: Array<string>;
    // inputs를 구성할 때 따르는 입력 포트 계약입니다.
    input_ports?: Array<{
      // inputs 객체의 키로 사용할 포트 이름입니다.
      name?: string;
      // 값의 타입입니다. []는 해당 타입의 배열입니다.
      type?: string;
      // 값의 단위입니다. 생략되면 단위를 선언하지 않은 포트입니다.
      units?: string;
      // true이거나 생략되면 반드시 입력합니다.
      required?: boolean;
      // 캡슐 제작자가 제공한 입력 안내입니다.
      description?: string;
      [key: string]: unknown;
    }>;
    // 실행 결과 outputs의 이름·타입·단위입니다.
    output_ports?: Array<{
      // outputs 객체에 반환되는 포트 이름입니다.
      name?: string;
      // 반환 값의 타입입니다. []는 배열입니다.
      type?: string;
      // 반환 값의 단위입니다.
      units?: string;
      // 캡슐 제작자가 제공한 출력 안내입니다.
      description?: string;
      [key: string]: unknown;
    }>;
    // 출력 포트 이름 목록입니다.
    outputs?: Array<string>;
    [key: string]: unknown;
  }>;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 40. grasshopper\_03-list\_library

```txt
로컬 Grasshopper 라이브러리에서 색인된 로직 이름을 조회합니다. logic_names의 이름으로 grasshopper_01-get_logic tool에서 상세 내용을 조회할 수 있습니다.
```

```ts
declare const tools: {
  mcp__rhino__grasshopper_03_list_library(args: {
    // true: logic_names와 같은 값의 logic_ids 포함.
    // default: false
    include_ids?: boolean;
    // paths·all: 라이브러리 경로 포함. ports·definition·source·audit은 목록에 상세를 추가하지 않음.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 라이브러리 전체 항목 수입니다.
  total_entries?: number;
  // 기본 응답에서도 grasshopper_01-get_logic tool.logic_id로 사용 가능
  logic_names?: Array<string>;
  // include_ids=false에서 logic_ids 대신 추가됨
  logic_count?: number;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 41. grasshopper\_04-run\_definition

```txt
실행 감사를 통과한 Grasshopper 캡슐을 Rhino에서 계산합니다. 정의에 따라 형상을 베이크할 수 있습니다. 모든 출력 포트를 먼저 확인하고 형상 베이크는 하나의 전용 Undo record로 처리합니다. mutation_state는 none·completed·rolled_back·unknown이며 requires_reconciliation=true이면 baked_guids와 현재 문서를 확인하기 전 자동 재시도하지 않습니다.
```

```ts
declare const tools: {
  mcp__rhino__grasshopper_04_run_definition(args: {
    // grasshopper_02-list_capsules tool에서 얻은 안정적인 캡슐 식별자입니다(예: "karamba_beam_v1").
    capsule_id: string;
    // ALMOND_IN_ 포트 이름과 값의 객체입니다. grasshopper_02-list_capsules tool(field_groups=['ports'])의 input_ports에서 타입·단위·필수 여부를 확인합니다. 형상은 {"guids":["객체 GUID"]}, 숫자·정수·문자열·불리언은 JSON 값, 목록은 number[]/integer[]/string[]의 평탄한 배열입니다.
    inputs: {
      [key: string]: unknown;
    };
    // 확률적 정의에 사용할 선택적 정수 시드입니다. 결정적인 정의에서는 생략합니다.
    // default: null
    seed?: (number | null);
    // 솔버 시간 한도(초)입니다. 기본값은 60, 최댓값은 600입니다.
    // default: 60.0
    timeout_s?: number;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 이 캡슐이 받는 입력 이름입니다. 값의 타입·단위·필수 여부는 grasshopper_02-list_capsules tool의 input_ports에서 확인합니다.
  valid_inputs?: Array<string>;
  // 요청한 ID를 찾지 못했을 때 반환하는 등록 캡슐 ID입니다. 실행 가능 여부는 grasshopper_02-list_capsules tool의 audited로 확인합니다.
  available_capsules?: Array<string>;
  // 실행한 캡슐 ID입니다.
  capsule_id?: string;
  // 출력 포트별 값입니다. 의미·타입·단위는 캡슐 계약에 따릅니다.
  outputs?: {
    [key: string]: unknown;
  };
  // 생성 객체 관찰·캡처에 재사용
  baked_guids?: Array<string>;
  // 해석 방식입니다.
  analysis_method?: string;
  // 매니페스트 선언: api/high, template/medium, rule_based/low
  confidence?: string;
  // 결과를 해석할 때 확인할 경고입니다.
  warnings?: Array<string>;
  // 오류 내용입니다.
  error?: unknown;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // 실제 변경 근거에 따른 상태입니다. unknown/partial이면 변경이 남았을 수 있습니다.
  mutation_state?: string;
  // true이면 실제 문서 상태를 확인한 뒤 다음 작업을 결정합니다. 자동 재실행을 허용하지 않습니다.
  requires_reconciliation?: boolean;
  [key: string]: unknown;
};
```

## inspect

### 42. inspect\_01-analyze\_nested\_blocks

```txt
중첩 블록 구조와 특정 배치 경로의 공유 정의 영향을 조회합니다. 읽기 전용입니다.

- outline: 기본적으로 선택된 루트의 요약. ids·path·scope로 대상을 정하고 field_groups로 상세를 선택합니다.
- resolve-block: 루트부터 대상 블록까지의 path로 정의의 공유 배치와 참조·링크 제한을 확인합니다.
- truncated·depth_limited: 조회 범위의 제한. definition_impact의 complete는 영향 범위 계수 완료 여부, occurrences_truncated는 반환 목록의 잘림 여부입니다.
- 정의 내부 ID는 현재 편집 가능한 문서 객체 ID와 다를 수 있습니다. 후속 호출에 ID가 필요하면 include_ids=true를 사용합니다.
```

```ts
declare const tools: {
  mcp__rhino__inspect_01_analyze_nested_blocks(args: {
    // outline | resolve-block
    mode: string;
    // outline: ids 또는 path. 생략 시 scope=selected(기본)|viewport|document.
    // depth 0..64(기본 64), max_items 1..5000(기본 200), max_bytes 2048..262144(기본 48000).
    // field_groups: summary(기본), objects, annotations, transforms 중 선택.
    // include_geometry, annotations, annotation_layer: 형상·주석 출력 및 TextDot 레이어 필터.
    // field_groups 생략 + include_geometry 또는 annotations 지정: legacy 상세 모드.
    // resolve-block: path에 최상위부터 목표 블록까지 GUID 1..65개.
    options: {
      [key: string]: unknown;
    };
    // 생략: 연결 문서. 지정 시 경로 일치 검사.
    // default: ""
    expected_model_path?: string;
    // 기본 false.
    // default: false
    include_ids?: boolean;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 선택한 분석 모드입니다.
  mode?: string;
  // 관찰한 문서 정보입니다.
  document?: {
    // 문서의 길이 단위입니다.
    units?: string;
    // 문서 길이 단위의 절대 허용오차입니다.
    absolute_tolerance?: number;
    [key: string]: unknown;
  };
  // 선택한 블록 분석 모드의 결과입니다.
  data?: {
    // 블록 배치 또는 정의의 분석 항목입니다.
    records?: Array<{
      // 항목의 종류입니다.
      kind?: string;
      // 배치 객체 또는 블록 정의 구성원의 ID입니다. 모델 편집에 쓸 객체 ID는 편집 상태에서 inspect_02-get_objects tool로 확인합니다.
      id?: string;
      // 객체 유형입니다.
      type?: string;
      // 중첩 블록의 배치 경로입니다. 공유 정의 영향을 확인할 때 resolve-block의 options.path에 재사용합니다.
      path?: Array<string>;
      // 블록 정의 이름입니다.
      definition?: string;
      [key: string]: unknown;
    }>;
    // 반환한 분석 항목 수입니다.
    items?: number;
    // 조회 한도 때문에 분석 항목 일부가 생략됐는지 나타냅니다.
    truncated?: boolean;
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 43. inspect\_02-get\_objects

```txt
Rhino 문서의 최상위 모델 객체를 조회합니다. `current`는 표시되고 잠기지 않은 객체(화면 밖 포함), `document`는 숨김·잠금 객체도 포함합니다. 객체·그룹 ID와 메타데이터로 범위를 좁히고 객체, 요약 또는 계층으로 관찰합니다. 그룹은 선택한 범위와 구성원의 교집합입니다. 계층 조회는 그룹·블록 배치를 펼치며 문서 객체와 블록 정의 내부 항목을 구분합니다.

조건 하나로 객체의 UserDictionary를 조회하는 호출 예시는 `{"filters":{"user_dictionary":[{"source":"attributes","key":"brief_probe","any_of":["yes"]}]}}`입니다.

행과 면은 각각 페이지를 나눕니다. 행 후속 조회에는 같은 조건과 첫 응답의 snapshot·next_offset을, 면 후속 조회에는 document 객체 ID와 geometry_crc를 사용합니다. objects/summary의 complete는 전체 행이 첫 단일 응답에 포함되고 편집 상태가 안정적일 때 true입니다. 마지막 페이지는 next_offset=null로 확인합니다. hierarchy의 complete에는 관계 완전성도 반영되며 깊이 제한이 있을 수 있습니다. face_page.complete는 전체 면이 첫 단일 응답에 있을 때 true입니다.

표시 여부는 픽셀 가시성이나 가림 여부를 뜻하지 않습니다.
```

```ts
declare const tools: {
  mcp__rhino__inspect_02_get_objects(args: {
    // current(기본), document.
    // default: "current"
    scope?: string;
    // document 범위에서만 사용할 수 있는 선택 사항인 서로 다른 최상위 객체 GUID입니다(1..4096개). group_ids와 함께 사용하지 않습니다.
    // default: null
    object_ids?: (Array<string> | null);
    // layer_paths(정확한 전체 경로), object_types(관찰된 Rhino 이름), name_contains(대소문자 구분 없음), user_dictionary 조건을 모두 적용합니다. user_dictionary는 조건 하나도 조건 객체의 JSON 배열에 담으며 최대 16개 조건이 모두 일치해야 합니다. 각 조건의 source는 attributes(객체 속성) 또는 geometry(형상), key는 비어 있지 않은 키입니다. any_of는 문자열·불리언·숫자를 1~64개 담은 배열이며, 해당 키의 값 또는 배열 원소가 그중 하나와 일치하면 조건을 충족합니다.
    // default: null
    filters?: ({
      [key: string]: unknown;
    } | null);
    // fields를 생략했을 때 objects 모드에서 형상 상세 정보를 포함합니다. 명시적인 fields가 우선합니다.
    // default: false
    include_geometry?: boolean;
    // 0..100000. 양수: expected_snapshot 필수.
    // default: 0
    offset?: number;
    // 1..200, 기본 50.
    // default: 50
    limit?: number;
    // 생략: 연결 문서. 지정 시 경로 일치 검사.
    // default: ""
    expected_model_path?: string;
    // 기본 false. true: ID 포함.
    // default: false
    include_ids?: boolean;
    // objects(기본), hierarchy, summary. recursive=true와 summary는 배타.
    // default: "objects"
    result_mode?: string;
    // 선택 사항인 비어 있지 않은 필드 목록입니다. id, name, layer_path, object_type, geometry_kind, geometry_crc, visible, selected, hidden, locked, bounds, groups, user_dictionary, geometry_valid, solid, manifold, volume, faces, face_count를 사용할 수 있습니다. 형상 상세 정보와 faces에는 objects 모드가 필요합니다. summary는 fields를 거부합니다.
    // default: null
    fields?: (Array<string> | null);
    // 기본 0. 양수: document object_ids와 각 객체의 expected_geometry_crcs 필수.
    // default: 0
    face_offset?: number;
    // 1..128, 기본 128. objects 모드.
    // default: 128
    face_limit?: number;
    // 객체 GUID별 CRC. 면 연속 조회 중 형상 변경 시 거부.
    // default: null
    expected_geometry_crcs?: ({
      [key: string]: number;
    } | null);
    // 어느 scope에서든 사용할 수 있는 선택 사항인 서로 다른 Rhino 그룹 GUID입니다(1..64개). 구성원과 선택한 범위의 교집합을 사용합니다. object_ids와 함께 사용하지 않습니다.
    // default: null
    group_ids?: (Array<string> | null);
    // current에서만 사용하며 기본값은 false입니다. 화면 밖의 선택도 포함하여 적격한 선택 객체로 필터링합니다. inside_window와 함께 사용할 수 없습니다.
    // default: false
    selected?: boolean;
    // current에서만 사용하며 기본값은 false입니다. 활성 뷰포트 경계에 걸친 바운딩 박스를 포함합니다. 클리핑 평면이나 픽셀 가림 검사는 수행하지 않습니다. selected와 함께 사용할 수 없습니다.
    // default: false
    inside_window?: boolean;
    // 기본 false. true: hierarchy 모드.
    // default: false
    recursive?: boolean;
    // 1..8, 루트=1. 1 초과 시 recursive=true.
    // default: 1
    depth?: number;
    // 첫 페이지 snapshot. offset > 0에서 필수.
    // default: ""
    expected_snapshot?: string;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 이번 조회에서 관찰한 객체 범위입니다.
  scope?: string;
  // 조회한 객체와 요청한 속성입니다.
  objects?: Array<{
    // 관찰한 객체 ID입니다.
    id?: string;
    // 관찰한 형상 버전입니다. 면 편집이나 다음 면 페이지 조회에 사용합니다.
    geometry_crc?: number;
    // 객체의 전체 면 수입니다.
    face_count?: number;
    // 관찰한 면 목록입니다.
    faces?: Array<{
      // 이 id·CRC와 함께 model_02-edit_planar_face tool의 object_id/face_index/expected_geometry_crc로 전달
      face_index?: number;
      // 평면 여부입니다.
      planar?: boolean;
      // 이 면의 기본 편집 조건 충족 여부입니다. 실행 전에는 형상 버전을 다시 검사합니다.
      face_edit_supported?: boolean;
      [key: string]: unknown;
    }>;
    // 면 목록이 일부 생략됐는지 여부입니다.
    faces_truncated?: boolean;
    // 이 객체의 면 목록 페이지 정보입니다.
    face_page?: {
      // 이번 페이지의 시작 위치입니다.
      offset?: number;
      // 이번 응답의 최대 항목 수입니다.
      limit?: number;
      // 이 페이지에서 반환한 수입니다.
      returned?: number;
      // 다음 페이지의 시작 위치입니다. null이면 다음 페이지가 없습니다.
      next_offset?: number | null;
      // 이 객체의 면 목록을 모두 반환했는지 나타냅니다.
      complete?: boolean;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  }>;
  // 조회 조건에 맞는 객체 수입니다.
  matched_count?: number;
  // 이번 페이지의 시작 위치입니다.
  offset?: number;
  // 이번 응답의 최대 항목 수입니다.
  limit?: number;
  // 다음 페이지의 시작 위치입니다. null이면 다음 페이지가 없습니다.
  next_offset?: number | null;
  // 후속 offset 페이지의 expected_snapshot에 그대로 전달
  snapshot?: string;
  // 현재 편집 컨텍스트와 저장 대상 정보입니다.
  editing?: {
    [key: string]: unknown;
  };
  // 요청한 객체 페이지가 완전한지 나타냅니다. 계층 하위의 관찰 상태는 각 children_state에 있습니다.
  complete?: boolean;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 44. inspect\_03-get\_document\_context

```txt
연결된 Rhino 문서·뷰·편집 상태와 저장된 Named View·Layout·레이어 계층·표시 모드를 조회합니다.

- `document`: 단위·공차·변경 여부·객체와 레이어 수
- `viewport` / `viewports`: 활성 화면의 카메라·투영·표시 모드 / 뷰포트 목록
- `editor`: 편집 모드와 안정성
- `named_views` / `layouts` / `display_modes`: 저장된 뷰·용지·표시 모드 목록. 목록마다 최대 128개이며 일부만 반환하면 warnings에 표시합니다.
- `layer_tree`: 삭제되지 않은 모든 레이어의 이름과 계층. 깊이당 공백 두 칸으로 들여쓰며 레이어가 없으면 빈 문자열, 조회 실패 시 null입니다.

**Named View·Layout·표시 모드 목록의 ID**는 `include_ids`와 무관하게 반환됩니다. 화면 이미지 캡처는 `capture_03-current_view` tool을 사용합니다.
```

```ts
declare const tools: {
  mcp__rhino__inspect_03_get_document_context(args: {
    // document, viewport, editor, viewports, named_views, layouts, layer_tree, display_modes 중 선택.
    // 생략 또는 null은 document, named_views, layouts, layer_tree, display_modes. []는 status와 warnings만.
    // default: null
    sections?: (Array<string> | null);
    // viewport 등에서 ID 포함. 기본 false.
    // default: false
    include_ids?: boolean;
    // editor 요청 시 공급자·명령·Undo 근거 포함. 기본 false.
    // default: false
    include_editor_details?: boolean;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 저장된 Named View 이름과 ID입니다. 최대 128개이며 일부만 반환하면 warnings에 표시합니다. 조회 실패 시 null입니다.
  named_views?: Array<{
    // Named View 이름입니다.
    name?: string;
    // Named View 식별자입니다. include_ids 설정과 관계없이 반환합니다.
    id?: string;
    [key: string]: unknown;
  }> | null;
  // 저장된 Layout 이름과 ID입니다. 최대 128개이며 일부만 반환하면 warnings에 표시합니다. 조회 실패 시 null입니다.
  layouts?: Array<{
    // Layout 이름입니다.
    name?: string;
    // Layout 식별자입니다. include_ids 설정과 관계없이 반환합니다.
    id?: string;
    [key: string]: unknown;
  }> | null;
  // 삭제되지 않은 모든 레이어의 이름과 부모 관계입니다. 깊이당 공백 두 칸으로 들여씁니다. 레이어가 없으면 빈 문자열, 조회에 실패하면 null입니다.
  layer_tree?: string | null;
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 결과를 해석할 때 확인할 경고입니다.
  warnings?: Array<string>;
  // 요청한 현재 문서 속성입니다. 관찰할 수 없는 값은 null입니다.
  document?: {
    // 문서 길이 단위
    units?: string | null;
    // 문서 길이 단위의 절대 허용오차
    absolute_tolerance?: number | null;
    // 문서 수정 플래그
    modified?: boolean | null;
    // 객체 수
    object_count?: number | null;
    // 레이어 수
    layer_count?: number | null;
    // 라디안 단위의 각도 허용오차
    angle_tolerance?: number | null;
    [key: string]: unknown;
  };
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  [key: string]: unknown;
};
```

### 45. inspect\_04-get\_selection\_references

```txt
현재 선택된 Rhino 객체의 소속 Holon과 상위 Holon을 참조하는 Plan을 찾습니다. 저장된 문서의 일반 모델에서 사용합니다.

Plan의 일치 Holon과 Plan 전체 대상은 다를 수 있습니다. 선택 객체와 Plan 목록의 잘림 여부는 각각 selection_truncated와 truncated로 확인합니다. result는 조회 결과 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: {
  mcp__rhino__inspect_04_get_selection_references(args: {
    // 검사할 선택 객체 수: 1..200.
    // default: 50
    selection_limit?: number;
    // 반환할 Plan 수: 1..500.
    // default: 50
    limit?: number;
    // steps, references, geometry, artifacts, description, scope, audit, all. 생략·빈 배열: 요약.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 선택한 객체의 ID·등록 여부와 소유 Holon입니다.
  objects?: Array<{
    [key: string]: unknown;
  }>;
  // 선택 객체를 소유한 Holon과 상위 Holon의 요약입니다.
  holons?: Array<{
    [key: string]: unknown;
  }>;
  // 선택 객체를 참조하는 Plan의 요약입니다.
  plans?: Array<{
    [key: string]: unknown;
  }>;
  // 참조 Plan 전체 개수
  total_plans?: number;
  // 현재 응답에서 결과가 잘렸는지 여부
  truncated?: boolean;
  // 선택 객체 소유 관계의 현재 확인 여부. 선택이 없으면 false
  ownership_live_verified?: boolean;
  // 저장된 Plan·계층 참조를 현재 Rhino에서 확인했는지 나타냅니다.
  references_live_verified?: boolean;
  // 선택된 객체 전체 수
  selection_total?: number;
  // 선택 조회의 일부가 생략되었는지 여부. Plan 목록의 truncated와 별개
  selection_truncated?: boolean;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 46. inspect\_05-resolve\_targets

```txt
Plan에 등록된 Scene·Holon 대상과 선택한 Holon 정보를 조회합니다. Step 지정 시 해당 Plan 소속 여부를 확인하지만 대상은 Plan 기준입니다. Scene의 모든 Holon을 자동으로 확장하지 않습니다.

저장된 대상 조회이며 Rhino의 현재 구성원은 검증하지 않습니다. result는 조회 결과 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: {
  mcp__rhino__inspect_05_resolve_targets(args: {
    // plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다.
    plan_id: string;
    // Plan 소속 검사. 생략 시 Plan 기준.
    // default: ""
    step_id?: string;
    // references, geometry, scope, audit, all. 생략·빈 배열: 기본 요약.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // Plan ID
  plan_id?: string;
  // Step ID
  step_id?: unknown;
  // Plan의 저장 리비전입니다. 변경 검사에는 현재 loop_no도 함께 사용합니다.
  revision?: number;
  // Plan에 지정한 Scene 컨텍스트입니다.
  scene_ids?: Array<unknown>;
  // Plan에 명시한 Holon 대상입니다. 빈 배열이면 지정 대상이 없습니다.
  holon_ids?: Array<unknown>;
  // 저장된 대상 Holon의 요약입니다.
  holons?: Array<{
    [key: string]: unknown;
  }>;
  // 대상의 현재 Rhino 상태를 확인했는지 나타냅니다.
  live_verified?: boolean;
  // 대상 정보의 출처입니다. 현재는 plan입니다.
  source?: string;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

## intersect

### 47. intersect\_01-find

```txt
닫힌 솔리드 사이에서 양의 부피가 겹치는 객체 쌍의 수를 찾습니다. include_block=false면 블록을 검사 범위에서 제외합니다. 0건은 선택된 검사 범위에서의 결과이며 전체 설계 적합성이나 간격을 보장하지 않습니다.

계산할 수 없는 객체·쌍이 있으면 intersection_count_incomplete 오류와 상세를 반환합니다. 접촉만 하는 면도 계산 불완전으로 반환될 수 있습니다. result는 결과 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: {
  mcp__rhino__intersect_01_find(args: {
    // 서로 다른 현재 최상위 Rhino 객체 GUID 1..512개입니다. 내부 페이지 처리를 통해 하나의 범위로 검사합니다.
    object_ids: Array<string>;
    // true이면 변환이 적용된 중첩 블록 구성원까지 펼칩니다. 기본값 false는 범위에서 블록을 제외합니다.
    // default: false
    include_block?: boolean;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 겹침 집계
  intersections?: {
    // 양의 부피가 겹치는 객체 쌍의 수입니다.
    number?: number;
    [key: string]: unknown;
  };
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  [key: string]: unknown;
};
```

### 48. intersect\_02-resolve

```txt
겹친 객체 쌍을 이미지로 검토하고 선택한 객체에서 겹친 부분을 제거합니다. 검토 시 실제 카메라와 선택이 바뀝니다.

choice=1 또는 2는 해당 객체를 잘라내고 skip은 두 객체를 유지합니다. 완료 상태라도 건너뛴 쌍은 남습니다. 수정 후 다음 쌍을 계산하는 과정에서 오류가 나더라도 직전 수정이 적용됐을 수 있습니다. 응답의 previous_result와 실제 형상 상태를 확인합니다.
```

```ts
declare const tools: {
  mcp__rhino__intersect_02_resolve(args: {
    // 검토 범위를 시작할 서로 다른 현재 최상위 객체 GUID 1..512개입니다. 선택 사항이며, 현재 범위를 이어서 검토하거나 선택을 제출할 때는 생략합니다.
    // default: null
    object_ids?: (Array<string> | null);
    // 새 검토 범위에 변환이 적용된 중첩 블록 구성원을 포함합니다. 기본값은 false입니다. 블록 정의 편집은 여전히 지원하지 않습니다.
    // default: false
    include_block?: boolean;
    // 반환된 결정 핸들로, choice와 함께 사용할 때 필수입니다. 화면에 표시된 연산 대상을 식별합니다. 완료되었거나 새 검토로 대체된 핸들로는 변경을 다시 실행할 수 없습니다.
    // default: ""
    review_id?: string;
    // 1 또는 2는 해당 번호의 객체에서 겹친 부분을 제거합니다. "skip"은 두 객체를 모두 그대로 둡니다. review_id를 제공하고 object_ids는 생략합니다. 확인/계속 진행하려면 choice를 생략합니다.
    // default: null
    choice?: (number | "skip" | null);
  }): Promise<CallToolResult<{
    // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
    status?: string;
    // 검토 진행 상태입니다. awaiting_choice이면 비교 결과를 확인한 뒤 선택합니다.
    state?: string;
    // 건너뛴 쌍은 수정하지 않음. completed가 모든 겹침 제거를 뜻하지 않음
    skipped_pairs?: number;
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

## model

### 49. model\_01-assign\_material

```txt
Rhino 객체에 라이브러리 재료와 선택적인 구축 메타데이터를 적용합니다. 렌더 재료는 객체에 직접 지정되며 레이어는 바뀌지 않습니다. 중복 GUID는 하나로 처리합니다.

반환 result는 적용 결과 또는 오류를 담은 JSON 문자열입니다. 실제 렌더 재료와 사용자 문자열은 Rhino 객체 속성에서 확인할 수 있습니다. inspect_02의 user_dictionary는 이 사용자 문자열과 같은 항목이 아닙니다.
```

```ts
declare const tools: {
  mcp__rhino__model_01_assign_material(args: {
    // 할당할 현재 Rhino 객체 GUID입니다. 관찰 결과나 생성 결과를 재사용합니다.
    guids: Array<string>;
    // model_04-list_materials tool(include_ids=true)에서 얻은 라이브러리의 표준 재료 ID입니다.
    material_id: string;
    // true이면 지정된 객체에 표준 렌더 재료를 적용합니다.
    // default: true
    apply_render_material?: boolean;
    // true이면 Almond 재료/구축 메타데이터를 부착합니다. false이면 요청한 렌더 재료만 적용합니다.
    // default: false
    attach_metadata?: boolean;
    // 선택 사항인 구조 역할 메타데이터이며, attach_metadata와 함께 사용합니다.
    // default: ""
    structural_role?: string;
    // 알려진 구축 시스템 ID입니다. attach_metadata=true일 때 사용합니다. construction_reference를 함께 지정하면 같은 시스템이어야 합니다.
    // default: ""
    construction_system?: string;
    // 선택 사항인 층 레이블 메타데이터이며, attach_metadata와 함께 사용합니다.
    // default: ""
    floor?: string;
    // 선택 사항인 구축 상세 설명이며, attach_metadata와 함께 사용합니다.
    // default: ""
    construction_detail?: string;
    // {"kind":"construction_system","id":"확인한 system_id"} 형식의 출처 참조입니다. attach_metadata=true일 때 사용합니다. construction_system도 지정하면 같은 시스템이어야 합니다.
    // default: null
    construction_reference?: ({
      [key: string]: unknown;
    } | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 라이브러리 재료 ID
  material_id?: string;
  // 처리 성공한 객체 수. requested_count와 비교하며 실제 변경 수와 구분
  applied_count?: number;
  // 요청한 수
  requested_count?: number;
  // 렌더 재료를 적용하도록 요청했는지 나타냅니다.
  render_material_applied?: boolean;
  // 재료 메타데이터가 부착됐는지 여부
  material_metadata_attached?: boolean;
  // Rhino에 적용한 재료명
  rhino_material_name?: string;
  // 재료 슬롯명
  ue_material_slot?: string;
  // 처리가 성공한 객체 GUID입니다. 실제 변경이 확인된 객체는 changed_guids에 있습니다.
  applied_guids?: Array<string>;
  // 요청한 메타데이터 적용 여부입니다.
  metadata_attached?: boolean;
  // 대상의 레이어 경로입니다. 제공되지 않으면 null입니다.
  layer_path?: string | null;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 50. model\_02-edit\_planar\_face

```txt
닫힌 Brep의 평면 한 면을 PushPull Extend로 이동합니다. 그룹·블록 편집을 종료한 일반 모델에서 사용합니다. 현재 객체의 면 번호와 geometry_crc를 같은 관찰에서 얻어 입력합니다.

result는 편집 결과 또는 오류를 담은 JSON 문자열입니다. 오류 응답에 mutation_state가 항상 포함되지는 않습니다.
```

```ts
declare const tools: {
  mcp__rhino__model_02_edit_planar_face(args: {
    // 연결된 문서의 관찰 결과에서 얻은 현재 잠기지 않은 최상위 닫힌 Brep GUID입니다.
    object_id: string;
    // expected_geometry_crc와 동일한 형상 관찰 결과에서 얻은 0부터 시작하는 평면 인덱스입니다.
    face_index: number;
    // 해당 관찰 결과의 형상 CRC입니다. 형상이 변경되었으면 교체 전에 편집을 거부합니다.
    expected_geometry_crc: number;
    // 문서 단위의 유한한 XYZ 숫자 3개입니다. 면 법선 방향 성분이 문서 허용오차를 초과해야 합니다.
    translation: Array<(number | number)>;
    // 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
    // default: ""
    expected_model_path?: string;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 단일 면의 편집 결과입니다.
  result?: {
    // 대상 객체와 이전 CRC를 확인하고 편집을 적용했는지 나타냅니다.
    edited?: boolean;
    // Rhino 객체 GUID
    object_id?: string;
    // 편집 전 형상 CRC
    previous_geometry_crc?: number;
    // 편집 후 CRC. 면 인덱스도 바뀔 수 있어 추가 면 편집 전 새 faces 관찰 필요
    geometry_crc?: number;
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 51. model\_03-edit\_planar\_faces

```txt
서로 다른 닫힌 Brep의 평면을 한 면씩 단일 Undo 기록으로 이동합니다. 그룹·블록 편집을 종료한 일반 모델에서 사용합니다. 각 객체의 면 번호와 CRC는 같은 형상 관찰에서 얻습니다.

result는 배치 결과 또는 오류를 담은 JSON 문자열입니다. 준비 단계에서 한 항목이 거부되면 객체 교체를 시작하지 않습니다. 처리 상태와 항목별 결과는 mutation_state와 items에서 확인합니다.
```

```ts
declare const tools: {
  mcp__rhino__model_03_edit_planar_faces(args: {
    // 서로 다른 Brep에 대한 항목 1..32개이며, 각 항목에는 object_id, face_index, expected_geometry_crc 및 translation이 들어갑니다. 단일 면 도구의 적용 대상 조건이 적용됩니다.
    edits: Array<{
      [key: string]: unknown;
    }>;
    // 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
    // default: ""
    expected_model_path?: string;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 배치 결과. 준비 실패는 교체 전이며 교체 중 실패는 부분 적용일 수 있음
  result?: {
    // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
    status?: string;
    // 모든 항목 적용이 확인되었는지 여부
    complete?: boolean;
    // 요청한 수
    requested_count?: number;
    // 실제 적용된 수
    applied_count?: number;
    // not_started/applied/partial/unknown 등. partial·unknown은 전체 배치 재실행 금지
    mutation_state?: string;
    // 입력 순서의 항목별 결과. applied/rejected/failed/unknown/not_attempted와 stage/message 등을 보존
    items?: Array<{
      // 항목 처리 상태입니다. applied, rejected, failed, unknown, not_attempted 중 하나입니다.
      status?: string;
      // 형상 편집 적용 여부
      edited?: boolean;
      // 편집 전 형상 CRC
      previous_geometry_crc?: number;
      // 변경 후 CRC. 다음 면 편집 전 면 인덱스를 다시 관찰
      geometry_crc?: number;
      [key: string]: unknown;
    }>;
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 52. model\_04-list\_materials

```txt
라이브러리 재료를 이름·설명·태그 또는 분류로 찾습니다. 결과는 Rhino 문서에 이미 적용된 재료 목록이 아닙니다. 적용에 필요한 material_id는 include_ids=true로 조회합니다. result는 재료 목록 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: {
  mcp__rhino__model_04_list_materials(args: {
    // 분류 정확히 일치. 대소문자 구분; 생략 시 전체.
    // default: ""
    category?: string;
    // 이름·설명·태그 검색. 대소문자 구분 없음.
    // default: ""
    query?: string;
    // true이면 후속 호출에 사용할 ID를 포함합니다.
    // default: false
    include_ids?: boolean;
    // 선택 사항인 상세 그룹: display, physical, metadata, source, paths, audit 또는 all. 생략하거나 비워 두면 요약을 조회합니다.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 조건에 일치하는 라이브러리 재료 수입니다.
  total?: number;
  // 재료의 이름·분류와 요청한 속성입니다.
  materials?: Array<{
    // 저장된 이름
    name?: string;
    // 분류
    category?: string;
    [key: string]: unknown;
  }>;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 53. model\_05-setup

```txt
라이브러리의 표준 재료와 구축 시스템별 레이어를 연결된 Rhino 문서에 설정합니다. 재료를 등록하고 `M` 아래 분류·시스템·부재 역할별 레이어와 색·재료를 구성합니다.

- **`overwrite=false`**: 없는 항목 생성, 기존 속성 유지 및 차이 보고.
- **`overwrite=true`**: 없는 항목 생성, 기존 항목의 사전 정의 속성 갱신.

반환 JSON의 `applied=true`는 기준과의 차이·오류가 없는 상태를 뜻합니다. 차이나 오류가 남으면 `incomplete`이며, 이 경우에도 일부 항목이 이미 생성·변경됐을 수 있습니다.

객체별 재료 지정에는 `model_04-list_materials` tool과 `model_01-assign_material` tool을 사용합니다.
```

```ts
declare const tools: {
  mcp__rhino__model_05_setup(args: {
    // Material과 Layer 모두에 적용되는 필수 불리언입니다. false는 기존 값을 유지하고, 없는 항목을 만들며, 차이를 보고합니다. true는 사전 정의된 속성을 갱신합니다.
    overwrite: boolean;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 모든 지정 속성이 일치하는지 여부. false여도 누락 항목 생성·일부 변경이 있었을 수 있음
  applied?: boolean;
  // 재료 레시피별 RenderMaterial과 지정 레이어 경로의 처리 내역입니다. 레이어 재료 할당으로 추가될 수 있는 Rhino Materials 테이블 레코드는 집계하지 않습니다. 이 필드가 없으면 변경 내역을 제공하지 않는 Bridge입니다.
  changes?: Array<{
    // material은 RenderMaterial을 확인한 재료 레시피, layer는 지정 레이어입니다.
    kind?: "material" | "layer";
    // 재료 레시피 이름 또는 레이어 전체 경로입니다.
    name?: string;
    // created=해당 RenderMaterial 수 증가 또는 지정 레이어 생성, updated=기존 값 변경, preserved=기존 값 유지, unchanged=작성 후 관측값 동일, unconfirmed=작성 후 확인 실패, skipped=작성 전 중단입니다.
    action?: "created" | "updated" | "preserved" | "unchanged" | "unconfirmed" | "skipped";
    // 처리 전 레시피와 일치하는 RenderMaterial 수 또는 지정 레이어 존재 여부(0/1)입니다. 확인하지 못하면 null입니다.
    previous_count?: number | null;
    // 처리 후 레시피와 일치하는 RenderMaterial 수 또는 지정 레이어 존재 여부(0/1)입니다. 확인하지 못하면 null입니다.
    current_count?: number | null;
    [key: string]: unknown;
  }>;
  // 최종 관측값과 요청한 속성이 다른 항목입니다.
  differences?: Array<{
    // material 또는 layer입니다.
    kind?: string;
    // 재료 이름 또는 레이어 경로입니다.
    name?: string;
    // 일치하지 않는 속성 이름입니다.
    property?: string;
    // 현재 관측한 값입니다.
    current?: unknown;
    // 설정에 지정된 값입니다.
    expected?: unknown;
    [key: string]: unknown;
  }>;
  // 처리 중 발생한 오류입니다. 비어 있어도 differences가 남을 수 있습니다.
  errors?: Array<{
    // 처리 대상의 종류입니다.
    kind?: string;
    // 처리 대상의 이름입니다.
    name?: string;
    // 처리를 완료하지 못한 이유입니다.
    message?: string;
    [key: string]: unknown;
  }>;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

## plan

### 54. plan\_02-create

```txt
Phase 또는 Plan을 생성합니다. Plan은 scope에 맞는 Step을 자동으로 만들며 **작업을 실행하지 않습니다.**

`result`는 생성된 `phase_id` 또는 `plan_id`와 상태를 담은 JSON 문자열입니다. 생성 오류도 `result.status`에 반환될 수 있습니다. Plan은 초기 loop_no=0, revision=1로 생성됩니다. 생성된 Plan의 Step은 plan_05-get tool에서 확인할 수 있습니다.
```

```ts
declare const tools: {
  mcp__rhino__plan_02_create(args: {
    // target으로 phase 또는 plan을 선택하고 해당 생성 정보를 입력합니다. Step 독립 생성은 제공하지 않습니다.
    request: ({
      // 작업할 대상 종류입니다.
      target: "phase";
      // 공백만 있는 이름은 허용하지 않습니다.
      name: string;
      // Phase의 목적이나 작업 범위를 문자열로 입력합니다.
      // default: ""
      description?: string;
      // context_04-get_project_info tool의 project.files에 등록된 파일명 하나 또는 배열. 생략하면 파일 연결 없음.
      // default: ""
      file_name?: (string | Array<string>);
      // 생략하면 pending.
      // default: "pending"
      status?: "pending" | "running" | "paused" | "completed" | "failed" | "blocked";
      // 같은 종류의 ID 형식만 검사하며 대상 존재·순환·작업 순서를 검증하거나 강제하지 않습니다.
      // default: null
      depends_on?: (Array<string> | null);
      // 이전 Phase 참조. 같은 종류의 ID 형식을 검사하며 존재는 검증하지 않습니다.
      // default: null
      previous_id?: (string | null);
    } | {
      // 작업할 대상 종류입니다.
      target: "plan";
      // 공백만 있는 제목은 허용하지 않습니다.
      title: string;
      // 공백만 있는 목표는 허용하지 않습니다.
      goal: string;
      // Step 템플릿. 생략하면 house. 기본 제공: spatial_development, drawing_development, semantic_exploration, plan_editing, model_revision, inspection, structure, construction_detail, drawing, component, house, interior. 등록된 사용자 템플릿도 사용 가능.
      // default: "house"
      scope?: string;
      // 단일 Scene의 호환 입력. scene_ids와 함께 쓰면 첫 항목과 같아야 합니다.
      // default: ""
      scene_id?: string;
      // 기존 Phase ID. 생략·빈 문자열은 소속 없음.
      // default: ""
      phase_id?: string;
      // 기존 Scene ID 배열. 생략하면 scene_id를 사용하고 둘 다 없으면 Scene 연결 없음.
      // default: null
      scene_ids?: (Array<string> | null);
      // 작업 대상인 기존 Holon ID 배열.
      // default: null
      holon_ids?: (Array<string> | null);
      // 같은 종류의 ID 형식만 검사하며 대상 존재·순환·작업 순서를 검증하거나 강제하지 않습니다.
      // default: null
      depends_on?: (Array<string> | null);
      // 이전 Plan 참조. 같은 종류의 ID 형식을 검사하며 존재는 검증하지 않습니다.
      // default: null
      previous_id?: (string | null);
      // 기록할 상위 Plan ID. 상대 Plan을 자동 수정하거나 존재를 검증하지 않습니다.
      // default: null
      parent_plan?: (Array<string> | null);
      // 기록할 하위 Plan ID. 상대 Plan을 자동 수정하거나 존재를 검증하지 않습니다.
      // default: null
      child_plan?: (Array<string> | null);
    });
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 생성한 Phase입니다.
  phase?: {
    // 생성한 Phase ID입니다. Plan의 소속 지정이나 Phase 조회에 사용합니다.
    phase_id?: string;
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // 생성한 Plan입니다.
  plan?: {
    // 생성한 Plan ID입니다. 상세 조회·회차 시작·작업 공간 선택에 사용합니다.
    plan_id?: string;
    // 현재 Loop 번호입니다. 0은 회차 시작 전입니다.
    loop_no?: number;
    // 저장 리비전입니다. 수정 시 loop_no와 함께 expected_revision에 사용할 수 있습니다.
    revision?: number;
    [key: string]: unknown;
  };
  [key: string]: unknown;
};
```

### 55. plan\_03-execute\_looping

```txt
Plan의 새 작업 회차를 시작하거나 최신 회차를 재개합니다. Step 실행은 에이전트가 직접 수행합니다.

새 회차는 Step을 pending으로 시작하며 이전 회차의 상태와 참조는 previous_loop에 반환합니다. resume=true는 기존 회차를 유지하며, 피드백을 생략하거나 비우면 기존 피드백을 유지합니다. 실행된 회차가 없으면 재개할 수 없습니다. next_step_id는 미완료 첫 Step이며 없으면 null입니다.
```

```ts
declare const tools: {
  mcp__rhino__plan_03_execute_looping(args: {
    // 다음 Loop를 시작하거나 최신 Loop를 재개할 기존 Plan ID입니다. plan_02-create tool 또는 plan_08-list tool에서 얻은 ID를 사용합니다.
    plan_id: string;
    // 기본 false: 새 회차. true: 최신 회차 재개.
    // default: false
    resume?: boolean;
    // 재개 시 생략·빈 문자열은 기존 값 유지.
    // default: ""
    feedback?: string;
    // 최초 산출물 폴더명. 생략 시 목표 기반, YYMMDD_ 접두사. 기존 폴더 재사용.
    // default: ""
    artifact_name?: string;
  }): Promise<CallToolResult<{
    // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
    status?: string;
    // Plan ID
    plan_id?: string;
    // Loop 회차 번호
    loop_no?: number;
    // 아직 완료되지 않은 첫 Step의 ID입니다. 없으면 null입니다.
    next_step_id?: string | null;
    // 이전 회차의 번호와 Step 기록입니다. 첫 회차에는 실행 전 0번 기록을 포함할 수 있으며, 이전 기록이 없으면 null입니다.
    previous_loop?: {
      // 이전 기록의 회차 번호입니다. 0은 실행 전 기록입니다.
      loop_no?: number;
      // 이전 회차에 저장된 순서 있는 Step과 수행 상태·입출력 참조입니다.
      steps?: Array<{
        // 회차가 바뀌어도 유지되는 Step UUID입니다.
        step_id?: string;
        // Step의 역할 유형입니다.
        step_type?: string;
        // 저장된 Step 표시 이름입니다.
        name?: string;
        // Plan 안에서 정의한 Step의 순서 값입니다.
        position?: number;
        // Step에 정의된 작업 종류입니다.
        kind?: string;
        // 해당 회차의 Step 상태입니다. pending, running, paused, completed, failed, blocked 중 하나입니다.
        status?: string;
        // 이 Step 기록이 속한 회차 번호입니다. 0은 실행 전 기록입니다.
        loop_no?: number;
        // 선행 Step의 UUID 목록입니다.
        depends_on?: Array<string>;
        // 해당 회차의 Step에 기록한 입력 참조입니다.
        input_refs?: Array<string>;
        // 해당 회차의 Step에 기록한 산출물·결과 참조입니다.
        output_refs?: Array<string>;
        // 다음 작업에 넘길 이 Step의 주요 발견과 교훈입니다.
        takeaways?: string;
        // 이 Step의 설계 결정과 근거입니다.
        design_rationale?: string;
        [key: string]: unknown;
      }>;
      [key: string]: unknown;
    };
    // 선택한 Step ID입니다.
    step_id?: string;
    // Plan 산출물 폴더
    plan_artifact_dir?: string;
    // 작업 산출물 폴더
    artifact_dir?: string | null;
    // 현재 Plan·Loop의 저장 리비전입니다.
    revision?: number;
    // 저장된 제목
    title?: string;
    // 저장된 목표
    goal?: string;
    // Plan의 업무 상태입니다. 회차 시작만으로 변경되지는 않습니다.
    plan_status?: string;
    // 저장된 피드백
    feedback?: string;
    // 현재 회차의 Step과 저장된 수행 상태입니다. 미완료 작업을 선택할 때 사용합니다.
    steps?: Array<{
      // 회차가 바뀌어도 유지되는 Step UUID입니다.
      step_id?: string;
      // Step의 역할 유형입니다.
      step_type?: string;
      // 저장된 Step 표시 이름입니다.
      name?: string;
      // Plan 안에서 정의한 Step의 순서 값입니다.
      position?: number;
      // Step에 정의된 작업 종류입니다.
      kind?: string;
      // 해당 회차의 Step 상태입니다. pending, running, paused, completed, failed, blocked 중 하나입니다.
      status?: string;
      // 이 Step 기록이 속한 회차 번호입니다. 0은 실행 전 기록입니다.
      loop_no?: number;
      // 선행 Step의 UUID 목록입니다.
      depends_on?: Array<string>;
      // 해당 회차의 Step에 기록한 입력 참조입니다.
      input_refs?: Array<string>;
      // 해당 회차의 Step에 기록한 산출물·결과 참조입니다.
      output_refs?: Array<string>;
      // 다음 작업에 넘길 이 Step의 주요 발견과 교훈입니다.
      takeaways?: string;
      // 이 Step의 설계 결정과 근거입니다.
      design_rationale?: string;
      [key: string]: unknown;
    }>;
    // Step 순서·기존 결과 재사용·산출물 위치·Plan 완료 결정에 적용할 지침입니다.
    policy_reminder?: string;
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 저장 기록 확인, Step 수행·검증 기록과 회차 결과 보고 안내입니다.
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 56. plan\_05-get

```txt
Phase, Plan 또는 Step의 작업 기록을 조회합니다. 기본값은 식별·상태 요약이며, include_details=true이면 선택한 대상의 상세를 함께 반환합니다. Plan 상세에는 Step 요약이, Step 상세에는 입출력 참조와 Takeaways·Design rationale이 포함됩니다. 다음 작업에 필요한 파일은 반환된 프로젝트 상대경로를 열어 내용을 확인합니다.

`result`는 조회 결과 또는 오류를 담은 JSON 문자열입니다. 성공 시 status는 대상의 작업 상태이며, 오류는 status=error입니다. Plan과 Step은 `loop_no`·`revision`·`read_only`를 함께 반환합니다. **revision을 명시하면 현재 번호여도 읽기 전용 스냅샷**입니다.
```

```ts
declare const tools: {
  mcp__rhino__plan_05_get(args: {
    // target으로 phase, plan, step을 선택하고 해당 ID를 입력합니다. include_details로 상세 기록을 선택합니다.
    request: ({
      // 작업할 대상 종류입니다.
      target: "phase";
      // 조회할 Phase ID입니다.
      phase_id: string;
      // 기본 false. true이면 Phase 상세를 포함합니다.
      // default: false
      include_details?: boolean;
    } | {
      // 작업할 대상 종류입니다.
      target: "plan";
      // 조회할 Plan ID입니다. Step 조회에는 해당 Step의 Plan ID를 사용합니다.
      plan_id: string;
      // 선택한 Loop의 리비전. 생략·null이면 해당 Loop의 최신 상태; 지정하면 읽기 전용 스냅샷.
      // default: null
      revision?: (number | null);
      // 기본 false. true이면 Plan 상세와 Step 요약을 포함합니다.
      // default: false
      include_details?: boolean;
      // 0 이상의 Loop 번호. 생략·null이면 최신 Loop, 0은 실행 전 기록.
      // default: null
      loop_no?: (number | null);
    } | {
      // 작업할 대상 종류입니다.
      target: "step";
      // 조회할 Plan ID입니다. Step 조회에는 해당 Step의 Plan ID를 사용합니다.
      plan_id: string;
      // 해당 Plan에 속한 Step ID.
      step_id: string;
      // 선택한 Loop의 리비전. 생략·null이면 해당 Loop의 최신 상태; 지정하면 읽기 전용 스냅샷.
      // default: null
      revision?: (number | null);
      // 기본 false. true이면 이 Step의 유형, 입출력 참조, Takeaways와 Design rationale을 포함합니다.
      // default: false
      include_details?: boolean;
      // 0 이상의 Loop 번호. 생략·null이면 최신 Loop, 0은 실행 전 기록.
      // default: null
      loop_no?: (number | null);
    });
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 조회한 Phase·Plan·Step의 ID입니다.
  id?: string;
  // 조회한 유형입니다.
  type?: "phase" | "plan" | "step";
  // 조회한 항목의 이름입니다.
  name?: string;
  // 업무 상태입니다. pending, running, paused, completed, failed, blocked 중 하나이며 조회 실패는 error입니다.
  status?: string;
  // Plan·Step이 속한 Plan ID입니다.
  plan_id?: string;
  // Loop 번호입니다. 0은 회차 시작 전입니다.
  loop_no?: number;
  // 이 회차에 저장된 리비전 번호입니다.
  revision?: number;
  // 과거 회차·리비전이면 true입니다. 수정하려면 현재 상태를 다시 조회합니다.
  read_only?: boolean;
  // include_details=true인 Phase의 상세 내용입니다.
  phase?: {
    // Phase 설명입니다.
    description?: string;
    // Phase가 속한 Rhino 파일명 목록입니다.
    file_name?: Array<string>;
    // 의존하는 Phase ID 목록입니다.
    depends_on?: Array<string>;
    // 이전 Phase ID입니다.
    previous_id?: string | null;
    // 소속 Plan의 제목입니다.
    plan_titles?: Array<string>;
    [key: string]: unknown;
  };
  // include_details=true인 Plan의 목표·대상·관계·산출물·Step 요약입니다.
  plan?: {
    // 작업 목표입니다.
    goal?: string;
    // Step 템플릿입니다.
    scope?: string;
    // Plan에 지정한 Holon ID입니다.
    holon_ids?: Array<string>;
    // Step 요약 목록입니다.
    steps?: Array<{
      // Step ID입니다.
      step_id?: string;
      // 템플릿 역할입니다.
      step_type?: string;
      // Step 이름입니다.
      name?: string;
      // Step의 업무 상태입니다.
      status?: string;
      // 해당 회차 번호입니다.
      loop_no?: number;
      [key: string]: unknown;
    }>;
    // Plan 산출물의 참조입니다.
    artifact_refs?: Array<string>;
    // Plan 산출물 루트입니다.
    artifact_dir?: string;
    // 선택한 회차의 산출물 폴더입니다.
    loop_artifact_dir?: string;
    // 소속 Phase의 ID와 이름입니다.
    phase?: {
      // Phase ID입니다.
      phase_id?: string;
      // Phase 이름입니다.
      name?: string;
      [key: string]: unknown;
    };
    // 작업 맥락으로 지정한 Scene ID입니다.
    scene_ids?: Array<string>;
    // 의존하는 Plan ID입니다.
    depends_on?: Array<string>;
    // 이전 Plan ID입니다.
    previous_id?: string | null;
    // 상위 Plan ID입니다.
    parent_plan?: Array<string>;
    // 하위 Plan ID입니다.
    child_plan?: Array<string>;
    // 현재 Loop에 기록한 피드백입니다.
    feedback?: string;
    // 생성 시각입니다. 한국 시간 YYYY-MM-DD-HH:MM 형식입니다.
    created_at?: string;
    // 수정 시각입니다. 한국 시간 YYYY-MM-DD-HH:MM 형식입니다.
    updated_at?: string;
    [key: string]: unknown;
  };
  // include_details=true인 Step의 상세 내용입니다.
  step?: {
    // 템플릿에서 정한 Step 역할입니다.
    step_type?: string;
    // 작업에 사용한 입력 근거입니다.
    input_refs?: Array<string>;
    // 작업 결과의 근거입니다.
    output_refs?: Array<string>;
    // 다음 작업에 넘길 이 Step의 주요 발견과 교훈입니다.
    takeaways?: string;
    // 이 Step의 설계 결정과 근거입니다.
    design_rationale?: string;
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 57. plan\_07-list\_revisions

```txt
Plan의 저장 리비전 목록을 최신 회차·리비전 순으로 조회합니다. Loop나 Step으로 필터링할 수 있으며, Step 필터는 그 Step의 직접 변경만 포함합니다.

result는 revisions, total, limit, truncated를 담은 JSON 문자열입니다. offset은 지원하지 않으며 limit은 최대 500입니다. 선택한 과거 기록은 plan_05-get tool에서 같은 loop_no와 revision으로 조회합니다.
```

```ts
declare const tools: {
  mcp__rhino__plan_07_list_revisions(args: {
    // plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다.
    plan_id: string;
    // 1~500, 기본 50.
    // default: 50
    limit?: number;
    // audit 또는 all: 생성 시각 포함. 생략·빈 배열: 기본 필드.
    // default: null
    field_groups?: (Array<string> | null);
    // 생략·null: 전체. 0: 실행 전 기록.
    // default: null
    loop_no?: (number | null);
    // 생략·빈 문자열: Plan 전체.
    // default: ""
    step_id?: string;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 각 행의 loop_no/revision과 함께 plan_05-get tool의 request에 사용
  plan_id?: string;
  // 저장 리비전 목록입니다.
  revisions?: Array<{
    // 기록된 Loop 번호입니다.
    loop_no?: number;
    // 저장 리비전 번호입니다.
    revision?: number;
    // 이 기록을 만든 변경 작업입니다.
    operation?: string;
    // 변경한 Step ID입니다. Plan 전체 변경이면 null입니다.
    step_id?: string | null;
    // audit 그룹에서 반환하는 저장 시각입니다.
    created_at?: string;
    [key: string]: unknown;
  }>;
  // 필터에 일치하는 전체 항목 수
  total?: number;
  // 페이지 최대 항목 수
  limit?: number;
  // limit 때문에 최신 리비전 일부만 반환했는지 나타냅니다.
  truncated?: boolean;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 58. plan\_08-list

```txt
Phase·Plan 목록 또는 한 Plan의 순서 있는 Step 목록을 조회합니다.

`result`는 상태와 `phases`·`plans`·`steps` 중 해당 목록을 담은 JSON 문자열입니다. `total`과 `truncated`는 목록 크기와 잘림 여부를 나타냅니다. **offset은 지원하지 않으며** `limit`은 최대 500입니다. Step 조회는 같은 스냅샷의 `loop_no`·`revision`과 `read_only`를 함께 반환합니다.
```

```ts
declare const tools: {
  mcp__rhino__plan_08_list(args: {
    // target으로 phase, plan, step을 선택합니다. Step에는 plan_id가 필요하며 대상별 필터와 limit을 지정합니다.
    request: ({
      // 작업할 대상 종류입니다.
      target: "phase";
      // 1~500, 기본 50.
      // default: 50
      limit?: number;
      // description: 설명, scope: 연결 파일, audit: 생성·수정 시각, all: 전체. 생략·빈 배열은 요약.
      // default: null
      field_groups?: (Array<string> | null);
    } | {
      // 작업할 대상 종류입니다.
      target: "plan";
      // 생략·빈 문자열이면 Phase 소속 여부와 관계없이 포함.
      // default: ""
      phase_id?: string;
      // 생략·빈 문자열이면 Scene 소속 여부와 관계없이 포함.
      // default: ""
      scene_id?: string;
      // 생략·빈 문자열이면 모든 상태.
      // default: ""
      status?: "" | "pending" | "running" | "paused" | "completed" | "failed" | "blocked";
      // 1~500, 기본 50.
      // default: 50
      limit?: number;
    } | {
      // Step 목록을 선택합니다.
      target: "step";
      // Step 목록을 읽을 기존 Plan ID입니다.
      plan_id: string;
      // 선택한 Loop의 저장 리비전. 생략·null은 최신 상태; 지정하면 읽기 전용 스냅샷.
      // default: null
      revision?: (number | null);
      // 0 이상의 Loop 번호. 생략·null은 최신, 0은 실행 전 기록.
      // default: null
      loop_no?: (number | null);
      // 1~500, 기본 50. 지정 순서의 앞부분부터 반환.
      // default: 50
      // minimum: 1
      // maximum: 500
      limit?: number;
    });
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 조회 성공 또는 오류 상태입니다.
  status?: string;
  // Phase 목록입니다.
  phases?: Array<{
    // Phase ID입니다.
    phase_id?: string;
    // Phase 이름입니다.
    name?: string;
    // Phase의 업무 상태입니다.
    status?: string;
    // 소속 Plan 수입니다.
    plan_count?: number;
    // 의존하는 Phase ID입니다.
    depends_on?: Array<string>;
    // 이전 Phase ID입니다.
    previous_id?: string | null;
    // scope 그룹에서 반환하는 Rhino 파일명 목록입니다.
    file_name?: Array<string>;
    [key: string]: unknown;
  }>;
  // 선택한 목록의 전체 항목 수입니다. Step은 선택한 Plan 스냅샷을 기준으로 합니다.
  total?: number;
  // 요청한 최대 항목 수입니다.
  limit?: number;
  // limit으로 일부 항목을 생략했으면 true입니다.
  truncated?: boolean;
  // 현재 결과에서 이어갈 수 있는 후속 조회 안내입니다.
  next_step_guide?: string;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // Plan 목록입니다.
  plans?: Array<{
    // Plan ID입니다.
    plan_id?: string;
    // Plan 제목입니다.
    title?: string;
    // Step 템플릿 키입니다.
    scope?: string;
    // Plan의 업무 상태입니다.
    status?: string;
    // 현재 Loop 번호입니다.
    loop_no?: number;
    // 현재 리비전입니다.
    revision?: number;
    [key: string]: unknown;
  }>;
  // Step이 속한 Plan ID입니다.
  plan_id?: string;
  // Step 목록을 읽은 Loop 번호입니다.
  loop_no?: number;
  // Step 목록을 읽은 스냅샷의 리비전입니다.
  revision?: number;
  // 과거 Loop 또는 저장된 리비전이면 true입니다.
  read_only?: boolean;
  // 정의된 순서를 유지한 Step 요약 목록입니다.
  steps?: Array<{
    // 변하지 않는 Step UUID입니다.
    step_id?: string;
    // Step의 역할 유형입니다.
    step_type?: string;
    // Step의 표시 이름입니다.
    name?: string;
    // 선택한 Loop에서의 Step 상태입니다.
    status?: string;
    // 이 Step 상태의 Loop 번호입니다.
    loop_no?: number;
    [key: string]: unknown;
  }>;
  [key: string]: unknown;
};
```

### 59. plan\_09-rename\_artifact\_folder

```txt
Plan의 산출물 폴더 이름을 바꾸고 현재 Plan·Step의 저장 경로 참조를 갱신합니다. 먼저 plan_10-set_working tool으로 산출물 폴더를 지정해야 합니다.

Loop 실행 이후 또는 다른 Plan의 과거 Loop가 참조하는 폴더는 실제 이름을 변경할 수 없습니다. 같은 이름 요청은 변경 없이 성공하며, 대상 폴더가 이미 존재하거나 다른 Plan에 속하면 실패합니다. 기존 revision은 유지됩니다.
```

```ts
declare const tools: {
  mcp__rhino__plan_09_rename_artifact_folder(args: {
    // 폴더명 하나. YYMMDD_가 없으면 현재 날짜 추가. 경로·Windows 금지 문자 불가.
    name: string;
    // 생략 또는 빈 문자열: 현재 선택된 Plan.
    // default: ""
    plan_id?: string;
  }): Promise<CallToolResult<{
    // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
    status?: string;
    // 변경 후 산출물 폴더 경로입니다.
    artifact_dir?: string | null;
    // 변경 전 폴더 경로입니다. 실제 변경이 있을 때 반환합니다.
    previous_artifact_dir?: string;
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 60. plan\_10-set\_working

```txt
현재 연결에서 Plan과 선택적인 Step을 산출물 작업 대상으로 선택합니다. 선택 자체는 **작업 실행이나 Plan·Step 상태 변경이 아닙니다.**

최초 선택은 Plan 산출물 경로를 정하며 revision이 증가할 수 있습니다. 이후에는 같은 Plan의 경로를 재사용합니다. Loop 시작 전 `artifact_dir`은 Plan 루트, 시작 후에는 현재 Loop의 번호 폴더입니다. 반환된 `loop_no`와 `revision`은 선택 시점의 값입니다.
```

```ts
declare const tools: {
  mcp__rhino__plan_10_set_working(args: {
    // plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다.
    plan_id: string;
    // 생략 시 Plan만 선택.
    // default: ""
    step_id?: string;
    // 최초 폴더명. 생략 시 목표에서 정하고 YYMMDD_ 접두사를 붙임. 기존 폴더와 다른 이름은 거부.
    // default: ""
    artifact_name?: string;
    // 현재 Loop 보호 값. 생략·null은 현재 Loop. 이전·존재하지 않는 Loop 선택 불가.
    // default: null
    loop_no?: (number | null);
  }): Promise<CallToolResult<{
    // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
    status?: string;
    // Plan ID
    plan_id?: string;
    // 선택한 Step. Step 미선택이면 빈 문자열
    step_id?: string;
    // Loop 회차 번호
    loop_no?: number;
    // 작업 공간 설정 후의 저장 리비전입니다.
    revision?: number;
    // 현재 연결의 산출물 폴더입니다. script_01-run_project_python tool의 작업 디렉터리로 사용합니다.
    artifact_dir?: string | null;
    // Plan 산출물 루트입니다. Loop 시작 전에는 이 폴더를 사용합니다.
    plan_artifact_dir?: string;
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 61. plan\_12-update

```txt
Phase·Plan의 작업 정보 또는 Step의 상태, 입출력 참조, Takeaways·Design rationale을 수정합니다. Plan·Step은 현재 Loop만 변경할 수 있습니다.

`depends_on`, `input_refs`, `output_refs`는 add/remove 패치이며 Plan의 대상·산출물·상하위 관계 배열은 전체 교체합니다. 생략 또는 null은 유지, 교체 배열의 []는 비웁니다. `takeaways`와 `design_rationale`은 빈 문자열로 비웁니다.

응답은 JSON 문자열입니다. `changed`는 실제 변경 여부, `issues`는 건너뛴 항목입니다. 중복·충돌 등 적용하지 못한 패치 항목은 `issues`에 기록하며, 일부만 적용되면 `partial_success`를 반환합니다. Loop 실행 후 `expected_revision`을 지정할 때는 `loop_no`도 함께 지정합니다.

Step 상태를 `completed`로 지정하면 다른 수정 필드와 함께 한 번의 요청으로 저장합니다.
```

```ts
declare const tools: {
  mcp__rhino__plan_12_update(args: {
    // target으로 phase, plan, step을 선택하고 해당 ID와 바꿀 필드만 입력합니다. Step은 상태·입출력 참조·판단 기록 중 필요한 필드만 갱신합니다.
    request: ({
      // 작업할 대상 종류입니다.
      target: "phase";
      // plan_08-list tool에 request.target=phase로 조회한 phases[].phase_id 또는 plan_05-get tool의 id에서 얻은 기존 Phase ID입니다.
      phase_id: string;
      // 빈 이름 불가.
      // default: null
      name?: (string | null);
      // 빈 문자열은 설명 삭제.
      // default: null
      description?: (string | null);
      // context_04-get_project_info tool의 project.files에 등록된 파일명 하나 또는 배열. 빈 문자열 또는 []는 연결 해제, 생략/null은 유지.
      // default: null
      file_name?: (string | Array<string> | null);
      // pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. 생략하거나 null이면 유지합니다.
      // default: null
      status?: ("pending" | "running" | "paused" | "completed" | "failed" | "blocked" | null);
      // 동일 종류 ID의 add/remove 패치. 존재·순환·완료 여부는 검사하지 않음.
      // default: null
      depends_on?: ({
        // 추가할 문자열 배열입니다. 이미 존재하거나 중복·유효하지 않은 값은 건너뛰고 issues로 보고합니다. remove에도 있는 값은 양쪽에서 건너뜁니다.
        add?: Array<string>;
        // 제거할 기존 문자열 배열입니다. 없는 값이나 중복·유효하지 않은 값은 건너뛰고 issues로 보고합니다. 생략하거나 빈 배열이면 유지합니다.
        remove?: Array<string>;
      } | null);
      // 빈 문자열은 연결 해제.
      // default: null
      previous_id?: (string | null);
    } | {
      // 작업할 대상 종류입니다.
      target: "plan";
      // plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다.
      plan_id: string;
      // 빈 목표 불가.
      // default: null
      goal?: (string | null);
      // 빈 문자열은 소속 해제.
      // default: null
      phase_id?: (string | null);
      // Plan의 작업 맥락이 되는 기존 Scene ID 배열로 교체합니다. []이면 비우고 생략/null이면 유지합니다.
      // default: null
      scene_ids?: (Array<string> | null);
      // 선택 사항인 대체 Plan Holon 대상 배열입니다. []이면 비우고 생략/null이면 유지합니다.
      // default: null
      holon_ids?: (Array<string> | null);
      // 현재 조회한 리비전 번호입니다. 현재 값과 다르면 변경을 거부합니다. 선택 사항이며, Loop 실행 후 이 검사를 사용하려면 loop_no도 입력합니다.
      // default: null
      expected_revision?: (number | null);
      // Plan ID만 사용하는 선택 사항인 {add: string[], remove: string[]} 패치입니다. 문자열 항목에 문제가 있으면 건너뛰고 보고합니다. 같은 종류의 ID 형식만 검사하며 대상의 존재·자기 참조·순환을 검사하거나 실행 순서·완료를 강제하지 않습니다.
      // default: null
      depends_on?: ({
        // 추가할 문자열 배열입니다. 이미 존재하거나 중복·유효하지 않은 값은 건너뛰고 issues로 보고합니다. remove에도 있는 값은 양쪽에서 건너뜁니다.
        add?: Array<string>;
        // 제거할 기존 문자열 배열입니다. 없는 값이나 중복·유효하지 않은 값은 건너뛰고 issues로 보고합니다. 생략하거나 빈 배열이면 유지합니다.
        remove?: Array<string>;
      } | null);
      // pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. completed는 사용자의 완료 결정 후 지정합니다. 생략/null은 유지입니다.
      // default: null
      status?: ("pending" | "running" | "paused" | "completed" | "failed" | "blocked" | null);
      // 선택 사항인 대체 산출물 참조 문자열 배열입니다. []이면 비우고 생략/null이면 유지합니다.
      // default: null
      artifact_refs?: (Array<string> | null);
      // 빈 제목 불가.
      // default: null
      title?: (string | null);
      // 빈 문자열은 연결 해제.
      // default: null
      previous_id?: (string | null);
      // 상호 관계 자동 변경 및 참조 대상 존재 검증 없음.
      // default: null
      parent_plan?: (Array<string> | null);
      // 상호 관계 자동 변경 및 참조 대상 존재 검증 없음.
      // default: null
      child_plan?: (Array<string> | null);
      // 선택 사항인 현재 Loop 번호 보호 검사입니다. 이전 또는 알 수 없는 Loop는 모두 거부합니다. Loop 실행 후 expected_revision을 입력할 때 함께 지정합니다. 둘 다 생략하면 현재 상태를 수정합니다.
      // default: null
      loop_no?: (number | null);
    } | {
      // 작업할 대상 종류입니다.
      target: "step";
      // plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다.
      plan_id: string;
      // 선택한 Plan의 상세 결과에서 얻은 Step ID입니다. 해당 Plan ID와 함께 사용합니다.
      step_id: string;
      // 생략하거나 null이면 유지합니다. completed를 지정하면 현재 Step의 상태를 완료로 저장합니다.
      // default: null
      status?: ("pending" | "running" | "paused" | "completed" | "failed" | "blocked" | null);
      // 입력 근거 문자열의 선택 사항인 {add: string[], remove: string[]} 패치입니다. 생략/null/{}이면 변경하지 않습니다. 유효하지 않은 문자열 항목은 건너뛰고 보고합니다.
      // default: null
      input_refs?: ({
        // 추가할 문자열 배열입니다. 이미 존재하거나 중복·유효하지 않은 값은 건너뛰고 issues로 보고합니다. remove에도 있는 값은 양쪽에서 건너뜁니다.
        add?: Array<string>;
        // 제거할 기존 문자열 배열입니다. 없는 값이나 중복·유효하지 않은 값은 건너뛰고 issues로 보고합니다. 생략하거나 빈 배열이면 유지합니다.
        remove?: Array<string>;
      } | null);
      // 출력 근거 문자열의 선택 사항인 {add: string[], remove: string[]} 패치입니다. 생략/null/{}이면 변경하지 않습니다. [] 형식의 전체 교체 배열은 허용하지 않습니다.
      // default: null
      output_refs?: ({
        // 추가할 문자열 배열입니다. 이미 존재하거나 중복·유효하지 않은 값은 건너뛰고 issues로 보고합니다. remove에도 있는 값은 양쪽에서 건너뜁니다.
        add?: Array<string>;
        // 제거할 기존 문자열 배열입니다. 없는 값이나 중복·유효하지 않은 값은 건너뛰고 issues로 보고합니다. 생략하거나 빈 배열이면 유지합니다.
        remove?: Array<string>;
      } | null);
      // Takeaways. 다음 작업에 전달할 핵심 결론이나 확인 사항입니다. 생략 또는 null은 유지하고 빈 문자열은 비웁니다.
      // default: null
      takeaways?: (string | null);
      // Design rationale. 설계 결정을 내린 이유와 근거입니다. 생략 또는 null은 유지하고 빈 문자열은 비웁니다.
      // default: null
      design_rationale?: (string | null);
      // 현재 조회한 리비전 번호입니다. 현재 값과 다르면 변경을 거부합니다. 선택 사항이며, Loop 실행 후 이 검사를 사용하려면 loop_no도 입력합니다.
      // default: null
      expected_revision?: (number | null);
      // 선택 사항인 현재 Loop 번호 보호 검사입니다. 이전 또는 알 수 없는 Loop는 모두 거부합니다. Loop 실행 후 expected_revision을 입력할 때 함께 지정합니다. 둘 다 생략하면 현재 상태를 수정합니다.
      // default: null
      loop_no?: (number | null);
    });
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 실제 저장 값이 변경되었는지 나타냅니다. success여도 false일 수 있습니다.
  changed?: boolean;
  // 수정한 Phase의 확인 정보입니다.
  phase?: {
    // Phase ID
    phase_id?: string;
    // 업무 상태입니다. pending, running, paused, completed, failed, blocked 중 하나입니다.
    status?: string;
    [key: string]: unknown;
  };
  // 적용하지 못한 패치 항목입니다. 나머지 항목은 적용되었을 수 있습니다.
  issues?: Array<{
    // 문제가 있는 입력 필드입니다.
    field?: string;
    // add 또는 remove입니다.
    operation?: string;
    // 해당 배열에서의 0부터 시작하는 위치입니다.
    index?: number;
    // 요청한 값입니다.
    value?: unknown;
    // 건너뛴 이유입니다.
    reason?: string;
    [key: string]: unknown;
  }>;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // Plan 수정 또는 소속 Step 수정 후의 Plan 확인 정보입니다.
  plan?: {
    // Plan ID
    plan_id?: string;
    // 업무 상태입니다. pending, running, paused, completed, failed, blocked 중 하나입니다.
    status?: string;
    // Loop 번호입니다. 0은 회차 시작 전입니다.
    loop_no?: number;
    // 다음 수정의 선택적 expected_revision 값. loop_no도 함께 사용
    revision?: number;
    [key: string]: unknown;
  };
  // 수정한 Step의 확인 정보입니다.
  step?: {
    // Step ID
    step_id?: string;
    // 업무 상태입니다. pending, running, paused, completed, failed, blocked 중 하나입니다.
    status?: string;
    // Loop 번호입니다. 0은 회차 시작 전입니다.
    loop_no?: number;
    [key: string]: unknown;
  };
  // 실패 응답에서 확인한 Rhino 후속 작업 상태입니다.
  cleanup_state?: "not_started" | "rolled_back" | "unknown";
  // 오류 처리에 Rhino 또는 DB 상태 확인이 필요한지 나타냅니다.
  requires_reconciliation?: boolean;
  [key: string]: unknown;
};
```

## research

### 62. research\_01-get\_construction\_guidance

```txt
건축 구법을 비교하고 선택할 참고 자료를 조회합니다.
```

```ts
declare const tools: {
  mcp__rhino__research_01_get_construction_guidance(args: {
    // 자유 텍스트 필터입니다(예: "glulam", "longspan", "bearing wall").
    // default: ""
    query?: string;
    // "floor", "wall", "roof", "foundation" 중 하나입니다. 비워 두면 모두 포함합니다.
    // default: ""
    category?: string;
    // analysis_04-validate_structure tool에서 사용하는 이름: "Wood", "Steel", "Concrete".
    // default: ""
    material?: string;
    // analysis_04-validate_structure tool의 유형입니다("beam", "truss", "shell", "frame", "canopy", "gridshell", "membrane", "highrise").
    // default: ""
    structure_type?: string;
    // 0보다 크면 반환되는 각 시스템이 fits_span과 경간 비율 규칙에 따른 권장 부재 깊이를 보고합니다.
    // default: 0.0
    span_m?: number;
    // load_kn 입력을 정하는 데 사용할 용도별 활하중(kPa)과 재료 밀도(kg/m3)도 반환합니다.
    // default: false
    include_reference_data?: boolean;
    // true이면 후속 호출에 사용할 ID를 포함합니다.
    // default: false
    include_ids?: boolean;
    // 상세 그룹: rules, narrative, source, metadata, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 조회 조건에 맞는 전체 항목 수입니다.
  total?: number;
  // 예비 치수 산정용 라이브러리 출처
  source?: string;
  // 검색한 구조 시스템과 요청한 경험칙·재료 정보입니다.
  systems?: Array<{
    // typology의 construction_system 또는 재료 메타데이터로 연결
    system_id?: string;
    // 이름입니다.
    name?: string;
    // 분류입니다.
    category?: string;
    // 구조 재료입니다.
    structural_material?: string;
    // 입력 span_m과 경험칙 범위 비교이지 내력 판정이 아님
    fits_span?: boolean;
    // 입력 스팬과 경험칙으로 계산한 부재 깊이입니다.
    depth_guidance?: Array<{
      // 부재 종류입니다.
      element?: string;
      // 계산한 권장 부재 깊이(mm)입니다.
      suggested_depth_mm?: number;
      // 부재 깊이를 계산한 스팬 비율입니다.
      rule?: string;
      [key: string]: unknown;
    }>;
    // 구법 이름입니다.
    construction_detail?: string;
    // 구법 참조를 기록할 종류와 ID입니다.
    construction_reference?: {
      // 참조 종류입니다. construction_system은 구조 시스템입니다.
      kind?: string;
      // 참조할 구조 시스템 ID입니다.
      id?: string;
      [key: string]: unknown;
    };
    // 의도한 유효 재료 하나를 model_01-assign_material tool에 선택
    render_material_ids?: Array<string>;
    [key: string]: unknown;
  }>;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 63. research\_02-get\_typology\_narrative

```txt
건축 유형의 서사와 선례를 조회합니다.
```

```ts
declare const tools: {
  mcp__rhino__research_02_get_typology_narrative(args: {
    // 자유 텍스트입니다(예: "courtyard", "skyscraper", "timber hall").
    // default: ""
    query?: string;
    // 구법 라이브러리의 system_id와 관련된 항목으로 필터링합니다(예: "steel-column-frame").
    // default: ""
    construction_system?: string;
    // analysis_04-validate_structure tool의 유형으로 필터링합니다("shell", "truss", "frame", "membrane" 등).
    // default: ""
    structure_type?: string;
    // 반환할 최대 항목 수입니다. 기본값은 5입니다.
    // default: 5
    limit?: number;
    // true이면 후속 호출에 사용할 ID를 포함합니다.
    // default: false
    include_ids?: boolean;
    // 상세 그룹: rules, narrative, source, metadata, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // limit를 적용하기 전 전체 일치 수
  total?: number;
  // 검색된 유형 설명과 요청한 속성입니다.
  entries?: Array<{
    // 건축 유형 ID입니다.
    typology_id?: string;
    // 이름입니다.
    name?: string;
    // 시대입니다.
    era?: string;
    // 지역입니다.
    region?: string;
    // 유형의 배경과 특징입니다.
    narrative?: string;
    // 도시에서의 역할입니다.
    urban_role?: string;
    // research_01-get_construction_guidance tool의 query로 검색 가능
    related_construction_systems?: Array<string>;
    [key: string]: unknown;
  }>;
  // 자료 출처입니다.
  source?: string;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 64. research\_03-search\_details

```txt
건축 자료 디렉터리의 metadata를 검색합니다.
```

```ts
declare const tools: {
  mcp__rhino__research_03_search_details(args: {
    // 자유 텍스트 검색어입니다. 비워 두면 텍스트 필터를 적용하지 않습니다.
    // default: ""
    query?: string;
    // true이면 후속 호출에 사용할 ID를 포함합니다.
    // default: false
    include_ids?: boolean;
    // 상세 그룹: rules, narrative, source, metadata, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
    status?: string;
    // 검색어입니다.
    query?: string;
    // 원래 검색어에서 추출한 단어입니다.
    query_terms?: Array<string>;
    // 검색에 추가한 관련 단어입니다.
    expanded_terms?: Array<unknown>;
    // 조건에 일치하는 상세 자료 출처입니다.
    sources?: Array<{
      // 출처 ID입니다.
      source_id?: string;
      // 제목입니다.
      title?: string;
      // 자료 출처의 웹 주소입니다.
      url?: string;
      // 자료 이용 조건의 웹 주소입니다.
      terms_url?: string;
      // 제공하는 자료 형식입니다.
      formats?: Array<string>;
      // 자료 접근 조건입니다.
      access?: string;
      // 자료 재배포 조건입니다.
      redistribution?: string;
      // 생성 작업에서의 이용 조건입니다.
      generation_use?: string;
      // 일치한 검색 단어입니다.
      matched_terms?: Array<string>;
      [key: string]: unknown;
    }>;
    // 검색한 출처 디렉터리의 범위입니다.
    scope?: string;
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

## scene

### 65. scene\_01-add\_objects

```txt
Rhino 객체를 Scene에 포함하거나 해당 Scene에서 제외했던 Holon 구성원을 복원합니다.
```

```ts
declare const tools: {
  mcp__rhino__scene_01_add_objects(args: {
    // scene_07-list tool(include_ids=true)에서 얻은 기존 Scene ID입니다.
    scene_id: string;
    // 일반 형상이나 클리핑 평면을 포함하는 객체 GUID 배열로, 최대 4096개 항목을 허용합니다.
    object_ids: Array<string>;
    // 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
    // default: ""
    expected_model_path?: string;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 입력 object_ids에서 처리하지 못한 항목의 인덱스입니다. 0부터 시작합니다.
  failed_indices?: Array<unknown>;
  // 이미 포함되어 변경하지 않은 입력 위치. Holon을 통해 포함된 경우도 포함
  already_present_indices?: Array<unknown>;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 66. scene\_02-create

```txt
설계 영역·프로그램·상황을 나타내는 Scene을 생성합니다.
```

```ts
declare const tools: {
  mcp__rhino__scene_02_create(args: {
    // 설계 영역 또는 행위/프로그램 맥락을 설명하는 Scene 이름입니다. 비어 있으면 Untitled가 됩니다.
    name: string;
    // Scene에 기록할 단위입니다. mm, cm, m, in, ft 중 하나를 선택합니다.
    // default: "mm"
    units?: string;
    // context_04-get_project_info tool의 project.files에 등록된 파일명입니다. 폴더는 제외하며, 비어 있으면 파일에 연결하지 않습니다.
    // default: ""
    file_name?: string;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 생성한 Scene의 확인 정보입니다.
  scene?: {
    // Scene ID
    scene_id?: string;
    // Scene의 저장 리비전입니다. 생성 시 0입니다.
    revision?: number;
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 67. scene\_03-focus\_holons

```txt
선택한 Holon과 하위 Holon의 현재 유효 구성원을 Rhino에서 선택·격리·확대합니다. 잠긴 주변 객체는 보일 수 있습니다. Unisolate로 격리 전 표시 상태를 복원할 수 있지만, 선택과 카메라는 별도로 변경된 상태로 남을 수 있습니다.

result는 선택된 객체와 격리·확대 결과 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: {
  mcp__rhino__scene_03_focus_holons(args: {
    // 서로 다른 Holon ID 1~32개. 유효 최상위 객체 최대 4096개.
    holon_ids: Array<string>;
    // 생략: 연결된 문서. 지정 시 연결 문서와 일치해야 함.
    // default: ""
    expected_model_path?: string;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 뷰 변경 적용 여부입니다. null이면 중간 상태를 확인해야 합니다.
  mutation_applied?: boolean | null;
  // true이면 현재 Rhino 상태를 확인한 뒤 다음 작업을 정합니다.
  requires_reconciliation?: boolean;
  // 실패한 단계입니다: validate, select, isolate, verify_selection, zoom_selected, redraw.
  failed_stage?: string;
  // 이 호출에서 완료한 뷰 작업입니다. null인 항목은 시도 후 완료를 확인하지 못했습니다.
  view_change?: {
    // 대상 선택 작업 완료 여부입니다.
    selection_changed?: boolean | null;
    // Isolate 완료 여부입니다.
    isolated?: boolean | null;
    // 기본 선택 확대 또는 대상 경계 확대를 완료했는지 나타냅니다.
    zoom_selected?: boolean | null;
    // 성공한 확대 방식입니다. selected는 기본 선택 확대, bounding_box는 기본 방식 실패 후 대상 경계 확대입니다.
    zoom_method?: "selected" | "bounding_box";
    // 화면 표시 모드 변경 완료 여부입니다.
    display_mode_changed?: boolean | null;
    // 격리된 객체의 가시성을 복구하는 Rhino 명령입니다. 카메라와 선택은 별도로 확인합니다.
    restore_visibility_command?: string;
    [key: string]: unknown;
  };
  // 포커스 실행 전후에 확인한 대상과 뷰 상태입니다.
  focus_observation?: {
    // 포커스 대상으로 확인한 객체 수입니다.
    target_count?: number;
    // 문서 단위의 대상 합집합 경계입니다.
    target_bounds?: {
      // 최소 [x, y, z] 좌표입니다.
      // minItems: 3
      // maxItems: 3
      min?: Array<number>;
      // 최대 [x, y, z] 좌표입니다.
      // minItems: 3
      // maxItems: 3
      max?: Array<number>;
      [key: string]: unknown;
    };
    // 대상 경계를 관측하지 못한 이유입니다.
    target_bounds_error?: string;
    // 기본 선택 확대의 관측 결과입니다. null이면 완료 여부를 확인하지 못했습니다.
    zoom_extents_selected?: boolean | null;
    // 대상 경계 확대의 관측 결과입니다. null이면 완료 여부를 확인하지 못했습니다.
    zoom_bounding_box?: boolean | null;
    // 확대 작업 직전에 관측한 뷰 상태입니다.
    before_zoom?: {
      // 관측한 뷰포트의 UUID입니다.
      viewport_id?: string;
      // 평행 투영이면 true입니다.
      parallel_projection?: boolean;
      // 문서 단위의 카메라 위치 [x, y, z]입니다.
      // minItems: 3
      // maxItems: 3
      camera_location?: Array<number>;
      // 문서 단위의 카메라 대상 [x, y, z]입니다.
      // minItems: 3
      // maxItems: 3
      camera_target?: Array<number>;
      // 관측한 [left, right, bottom, top, near, far]입니다.
      // minItems: 6
      // maxItems: 6
      frustum?: Array<number>;
      // 뷰 관측 중 확인하지 못한 정보의 오류입니다.
      observation_error?: string;
      [key: string]: unknown;
    };
    // 포커스 작업 실패 후 관측한 뷰 상태입니다.
    after_failure?: {
      // 관측한 뷰포트의 UUID입니다.
      viewport_id?: string;
      // 평행 투영이면 true입니다.
      parallel_projection?: boolean;
      // 문서 단위의 카메라 위치 [x, y, z]입니다.
      // minItems: 3
      // maxItems: 3
      camera_location?: Array<number>;
      // 문서 단위의 카메라 대상 [x, y, z]입니다.
      // minItems: 3
      // maxItems: 3
      camera_target?: Array<number>;
      // 관측한 [left, right, bottom, top, near, far]입니다.
      // minItems: 6
      // maxItems: 6
      frustum?: Array<number>;
      // 뷰 관측 중 확인하지 못한 정보의 오류입니다.
      observation_error?: string;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 기본 선택 확대 또는 대상 경계 확대를 완료했는지 나타냅니다.
  zoom_selected?: boolean;
  // 대상을 격리했는지 여부
  isolated?: boolean;
  // 잠긴 주변 객체를 계속 표시하는지 여부
  locked_context_remains_visible?: boolean;
  // 격리한 객체의 가시성을 복구하는 명령입니다.
  restore_visibility_command?: string;
  // 저장된 모델의 경로
  model_path?: string;
  // 포커스된 실제 모델 뷰포트 GUID
  viewport_id?: string;
  // 포커스할 때 실제로 선택한 Rhino 객체 GUID입니다.
  selected_ids?: Array<string>;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 68. scene\_04-get

```txt
Scene의 등록 정보와 Holon·객체 수를 조회합니다. 저장된 요약이며 현재 Rhino 구성원을 실시간 검증하지 않습니다. 객체 수가 null이면 수를 확정할 수 없는 상태입니다. 현재 구성원은 scene_06-get_objects tool로 조회합니다.

result는 scene 또는 오류를 담은 JSON 문자열입니다. include_ids=true여도 입력한 scene_id는 반복 반환하지 않습니다.
```

```ts
declare const tools: {
  mcp__rhino__scene_04_get(args: {
    // scene_07-list tool(include_ids=true) 또는 기록된 Scene 참조에서 얻은 기존 Scene ID입니다.
    scene_id: string;
    // 기본 false. 결과에 포함된 식별자를 표시합니다.
    // default: false
    include_ids?: boolean;
    // scope, state, geometry, audit, all. 생략·빈 배열: 요약.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // Scene의 저장 요약입니다.
  scene?: {
    // 저장된 이름
    name?: string;
    // Scene에 기록한 길이 단위입니다.
    units?: string;
    // 저장 상태의 revision
    revision?: number;
    // Scene의 Holon 개수
    holons?: number;
    // 저장된 구성원 수. 직접 등록·제외 override가 있으면 null이며 빈 Scene을 뜻하지 않음
    objects?: number | null;
    // 직접 등록된 객체 수
    direct_objects?: number;
    // Scene 구성원을 현재 Rhino에서 확인했는지 나타냅니다.
    live_verified?: boolean;
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 69. scene\_05-get\_holon

```txt
Holon의 등록 정보와 구성원을 조회합니다. 기본값은 저장된 정보이며, live=true는 현재 Rhino 그룹·형상을 조회하고 등록 정보와의 차이를 확인합니다. requires_sync는 동기화 필요 여부입니다.

recursive=true는 자손 Holon을 포함한 유효 구성원을 확장합니다. 이는 Holon 계층이며 Rhino 블록 정의의 내부 확장이 아닙니다. result는 Holon 정보 또는 오류를 담은 JSON 문자열입니다. include_ids=true여도 입력한 holon_id는 요약에 반복 반환되지 않습니다.
```

```ts
declare const tools: {
  mcp__rhino__scene_05_get_holon(args: {
    // include_ids=true를 사용한 Holon 조회 또는 이전 등록 결과에서 얻은 등록된 Holon ID입니다.
    holon_id: string;
    // 기본 false. true: 현재 Rhino 구성원·형상 조회.
    // default: false
    live?: boolean;
    // 기본 false. true: 요청 그룹에 해당하는 ID 포함.
    // default: false
    include_ids?: boolean;
    // 기본 false. true: 자손 Holon 확장.
    // default: false
    recursive?: boolean;
    // references, geometry, scope, audit, all. 생략·빈 배열: 요약.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 조회한 Holon의 요약입니다.
  holon?: {
    // 저장된 이름
    name?: string;
    // Holon의 등록 상태 또는 현재 관찰 상태입니다. live_verified와 함께 확인합니다.
    availability?: string;
    // 객체 수
    object_count?: number;
    // Holon 구성원을 현재 Rhino에서 확인했는지 나타냅니다.
    live_verified?: boolean;
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 70. scene\_06-get\_objects

```txt
Scene의 직접 객체와 Holon 구성원을 현재 Rhino 문서에서 조회합니다. Scene에서 제외한 구성원은 목록에 포함되지 않습니다.

result는 objects, total, limit, offset, truncated 및 live_verified 또는 오류를 담은 JSON 문자열입니다. truncated=true이면 같은 조건에서 offset을 limit만큼 늘려 다음 페이지를 조회합니다.
```

```ts
declare const tools: {
  mcp__rhino__scene_06_get_objects(args: {
    // scene_07-list tool(include_ids=true) 또는 기록된 Scene 참조에서 얻은 기존 Scene ID입니다.
    scene_id: string;
    // 기본 false. true: 객체 GUID 포함.
    // default: false
    include_ids?: boolean;
    // scope, state, geometry, audit, all. 생략·빈 배열: 요약.
    // default: null
    field_groups?: (Array<string> | null);
    // 1~200, 기본 50.
    // default: 50
    limit?: number;
    // 0부터 시작. 기본 0.
    // default: 0
    offset?: number;
    // 생략: 연결된 문서. 지정 시 연결 문서와 일치해야 함.
    // default: ""
    expected_model_path?: string;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 현재 연결 모델에서 확인한 Scene 객체와 요청한 속성입니다.
  objects?: Array<{
    [key: string]: unknown;
  }>;
  // 현재 연결 모델에서 확인한 Scene 객체 수입니다.
  total?: number;
  // 페이지 최대 항목 수
  limit?: number;
  // 현재 페이지 시작 위치
  offset?: number;
  // 뒤 페이지가 남았는지 여부. 다음 offset은 현재 offset+objects 길이
  truncated?: boolean;
  // 현재 Rhino 상태를 확인했는지 여부
  live_verified?: boolean;
  // 관찰한 연결 모델의 경로입니다.
  model_path?: string;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 71. scene\_07-list

```txt
공유 프로젝트 DB에 등록된 Scene 목록을 조회합니다. 파일명을 생략하면 연결된 파일뿐 아니라 프로젝트의 모든 파일을 포함합니다.

result는 scenes, total, limit, offset, truncated를 담은 JSON 문자열입니다. truncated=true이면 같은 필터에서 offset을 limit만큼 늘려 다음 페이지를 조회합니다. Scene 상세는 scene_04-get tool, 현재 Rhino 구성원은 scene_06-get_objects tool로 확인합니다.
```

```ts
declare const tools: {
  mcp__rhino__scene_07_list(args: {
    // Scene 이름 부분 검색. 대소문자 무관.
    // default: ""
    name?: string;
    // 확장자를 포함한 정확한 프로젝트 파일명. 생략: 전체 파일.
    // default: ""
    file_name?: string;
    // 1~200, 기본 50.
    // default: 50
    limit?: number;
    // 0부터 시작. 기본 0.
    // default: 0
    offset?: number;
    // 기본 false. true: scene_id 등 포함.
    // default: false
    include_ids?: boolean;
    // scope, state, geometry, audit, all. 생략·빈 배열: 요약.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 저장된 Scene의 이름과 요청한 속성입니다.
  scenes?: Array<{
    [key: string]: unknown;
  }>;
  // 필터에 일치하는 전체 항목 수
  total?: number;
  // 페이지 최대 항목 수
  limit?: number;
  // 현재 페이지 시작 위치
  offset?: number;
  // 뒤 페이지가 남았는지 여부. 같은 필터로 offset+scenes 길이부터 계속 조회
  truncated?: boolean;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 72. scene\_08-list\_holons

```txt
모델에 등록된 Holon 목록을 조회합니다. Scene을 지정하면 연결된 Holon을 조회하며, recursive=true이면 그 자손도 포함합니다. 자손은 해당 Scene에 직접 등록되어 있지 않을 수 있습니다. Scene 미지정 시 기본 목록은 최상위 Holon입니다.

목록은 저장된 등록 정보이며 현재 Rhino 구성원의 실시간 검증 결과가 아닙니다. 현재 구성원은 scene_05-get_holon tool의 live=true로 조회합니다. result는 목록 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: {
  mcp__rhino__scene_08_list_holons(args: {
    // 관리형 기본: 연결된 모델. 지정 경로에 등록된 Holon이 없으면 빈 목록.
    // default: ""
    expected_model_path?: string;
    // 기본 false. true: 후속 호출용 ID 포함.
    // default: false
    include_ids?: boolean;
    // 생략·빈 문자열: Scene 필터 없음.
    // default: ""
    scene_id?: string;
    // 기본 false. true: 자손 포함.
    // default: false
    recursive?: boolean;
    // references, geometry, scope, audit, all. 생략·빈 배열: 요약.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 등록된 Holon의 저장 요약입니다.
  holons?: Array<{
    [key: string]: unknown;
  }>;
  // 필터에 일치하는 전체 항목 수
  total?: number;
  // Holon을 현재 Rhino에서 확인했는지 나타냅니다.
  live_verified?: boolean;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 73. scene\_09-remove\_holon

```txt
Holon 등록을 해제하고 Rhino 형상과 그룹은 유지합니다.
```

```ts
declare const tools: {
  mcp__rhino__scene_09_remove_holon(args: {
    // 등록을 해제할 Holon ID입니다. 이 Holon을 참조하는 부모 Holon과 Plan의 관계를 먼저 해제합니다.
    holon_id: string;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // Holon 등록 해제 결과입니다.
  holon?: {
    // 등록 해제한 Holon ID입니다.
    holon_id?: string;
    // Holon 등록 해제 상태입니다.
    status?: string;
    // 현재 Rhino 상태를 확인했는지 여부
    live_verified?: boolean;
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 74. scene\_10-remove\_objects

```txt
객체를 Scene에서 제외합니다. Rhino 형상과 Holon 그룹은 유지됩니다.
```

```ts
declare const tools: {
  mcp__rhino__scene_10_remove_objects(args: {
    // scene_07-list tool(include_ids=true)에서 얻은 기존 Scene ID입니다.
    scene_id: string;
    // 일반 형상 또는 클리핑 평면을 포함하는 객체 GUID 배열이며, 최대 4096개 항목을 받습니다.
    object_ids: Array<string>;
    // 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
    // default: ""
    expected_model_path?: string;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 입력 object_ids에서 처리하지 못한 항목의 인덱스입니다. 0부터 시작합니다.
  failed_indices?: Array<unknown>;
  // Scene에 이미 포함되지 않은 입력 항목의 인덱스입니다. 0부터 시작합니다.
  already_absent_indices?: Array<unknown>;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 75. scene\_11-sync\_holon

```txt
Rhino의 현재 구성원을 읽어 Holon 등록 정보를 갱신합니다.
```

```ts
declare const tools: {
  mcp__rhino__scene_11_sync_holon(args: {
    // 단일 대상의 상태 대조 및 정합성 확인에 사용할 등록된 Holon ID입니다. 선택 사항입니다.
    // default: ""
    holon_id?: string;
    // 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
    // default: ""
    expected_model_path?: string;
    // holon_id와 함께 제공하는 선택 항목으로, 현재 Rhino 그룹 GUID의 일관성을 확인합니다. 이 값만으로 그룹을 선택하거나 연결 대상을 바꾸지 않습니다.
    // default: ""
    rhino_group_id?: string;
    // 명시적 Holon ID 일괄 목록입니다. 선택 사항이며, 단일 Holon/그룹 선택자와 함께 사용하지 않습니다.
    // default: null
    holon_ids?: (Array<string> | null);
    // 구성원을 갱신할 Scene ID입니다. holon_id, holon_ids, rhino_group_id와 함께 입력하지 않습니다.
    // default: ""
    scene_id?: string;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 확인한 Holon 수
  checked?: number;
  // 실제 대장 갱신 수. 변경 없으면 새 리비전도 없음
  changed?: number;
  // 상태가 present가 아닌 등록 수
  unavailable?: number;
  // 항목별 문제. 관련 없는 유효 등록은 함께 갱신될 수 있음
  problems?: Array<unknown>;
  // 갱신한 Scene ID와 저장 리비전의 대응입니다.
  scene_revisions?: {
    [key: string]: unknown;
  };
  // 문제 없이 모든 대상의 현재 상태를 확인했는지 나타냅니다.
  live_verified?: boolean;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 76. scene\_12-update

```txt
Scene의 프로젝트 파일 연결을 변경하거나 해제합니다.
```

```ts
declare const tools: {
  mcp__rhino__scene_12_update(args: {
    // scene_07-list tool(include_ids=true) 또는 기록된 Scene 참조에서 얻은 기존 Scene ID입니다.
    scene_id: string;
    // context_04-get_project_info tool의 project.files에 등록된 교체 파일명입니다. 빈 문자열은 연결 해제, 생략/null은 유지입니다.
    // default: null
    file_name?: (string | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 수정한 Scene의 확인 정보입니다.
  scene?: {
    // 이후 Scene 조회에 재사용할 핸들
    scene_id?: string;
    // Scene의 저장 리비전입니다. 실제 파일 연결이 바뀔 때 증가합니다.
    revision?: number;
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 77. scene\_13-upsert\_holon

```txt
물리적 요소와 관계를 Holon으로 등록하거나 갱신합니다.
```

```ts
declare const tools: {
  mcp__rhino__scene_13_upsert_holon(args: {
    // 의미적 Holon 이름입니다. 기존 Rhino 그룹에 연결할 때는 해당 그룹의 정확한 이름과 일치해야 합니다.
    name: string;
    // 등록할 최상위 Rhino 객체 GUID 배열입니다. 각 객체는 하나의 Holon에 속합니다. 생략하면 name과 일치하는 기존 그룹을 사용합니다. []는 child_holon_ids가 있는 부모에만 사용합니다.
    // default: null
    object_ids?: (Array<string> | null);
    // 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
    // default: ""
    expected_model_path?: string;
    // Holon이 속할 기존 Scene ID 배열입니다. 새 Holon에는 필수이며, 수정 시 생략하면 유지합니다.
    // default: null
    scene_ids?: (Array<string> | null);
    // 수정할 기존 Holon ID입니다. 선택 사항이며, 생략하면 등록을 생성합니다.
    // default: ""
    holon_id?: string;
    // 기존 Rhino 그룹의 정확한 GUID입니다. 선택 사항이며, 이름의 모호성을 해소하는 데 사용합니다.
    // default: ""
    rhino_group_id?: string;
    // 등록된 자식 Holon 목록입니다. 선택 사항이며, []는 기존 자식을 분리하고 생략하면 유지합니다. 자식당 부모는 하나만 허용하고 계층 순환을 금지합니다.
    // default: null
    child_holon_ids?: (Array<string> | null);
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // 등록한 Holon의 확인 정보입니다.
  holon?: {
    // 등록한 Holon ID입니다. 조회·동기화·포커스에 사용합니다.
    holon_id?: string;
    // 대상 이용 가능 상태
    availability?: string;
    // 객체 수
    object_count?: number;
    // 현재 Rhino에서 등록을 확인했는지 나타냅니다.
    live_verified?: boolean;
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```

## script

### 78. script\_01-run\_project\_python

```txt
연결된 Rhino 문서에서 Python 3 코드를 실행합니다. Rhino 형상을 생성·편집하거나 산출물 파일을 만들 때 사용하며, 선택된 Plan·Loop의 산출물 폴더가 작업 디렉터리가 됩니다.

실행하려면 **유효하고 쓰기 가능한 작업 공간**이 선택되어 있어야 합니다. 선택된 작업 공간이 없다면 `plan_10-set_working` tool으로 선택하세요. 기존 선택은 재사용할 수 있습니다.

코드는 실제 문서를 변경할 수 있으며 실행 완료가 문서 저장을 뜻하지는 않습니다. **시간 초과는 실행을 취소하지 않습니다.** 완료 여부가 불확실하면 반환된 `request_id`로 `script_03-get_execution` tool을 조회하고, 변경을 다시 실행하기 전에 문서 상태를 확인하세요. 오류가 발생해도 부분 변경이 롤백되었다고 가정하지 마세요.
```

```ts
declare const tools: {
  mcp__rhino__script_01_run_project_python(args: {
    // 비어 있지 않은 동기식 Python 3 코드. doc·scriptcontext.doc은 연결된 문서이며, 반환할 JSON 호환 값은 result에 할당합니다. 상대 경로는 선택된 산출물 폴더 기준입니다.
    code: string;
    // 1~600초의 정수, 기본 60초. 실행 종료가 아닌 완료 근거 대기 한도입니다. beyond·CoS는 첫 대기를 최대 60초로 줄여 pending과 request_id를 먼저 반환할 수 있습니다. 미완료 응답은 같은 ID로 script_03-get_execution tool을 조회합니다.
    // default: 60
    timeout_seconds?: number;
  }): Promise<CallToolResult<{
    // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
    status?: string;
    // Rhino 실행 완료가 확인됐는지 나타냅니다.
    completed?: boolean;
    // 미완료·불확실성·결과 페이지를 script_03-get_execution tool으로 회수할 정확한 ID
    request_id?: string;
    // 실행에 사용한 Plan·Loop 산출물 폴더입니다.
    artifact_dir?: string | null;
    // 실행 코드가 정한 JSON 값입니다.
    result?: unknown;
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    // 변경 적용 상태입니다. partial 또는 unknown이면 같은 수정을 다시 실행하기 전에 현재 상태를 확인합니다.
    mutation_state?: string;
    // 결과를 나누어 읽기 위한 정보입니다.
    result_page?: {
      // 결과 유형입니다. object, array, string, scalar 중 하나입니다.
      type?: string;
      // 문자열 페이지의 위치 단위입니다.
      unit?: string;
      // 조회할 수 있는 최상위 결과 필드입니다.
      available_fields?: Array<string>;
      // 결과 필드 이름별 페이지 정보입니다. 배열·문자열 전체는 result 키를 사용합니다.
      pages?: {
        [key: string]: {
          // 전체 항목 수 또는 문자열 길이입니다.
          total?: number;
          // 이번 페이지의 시작 위치입니다.
          offset?: number;
          // 반환한 항목 수 또는 문자열 길이입니다.
          returned?: number;
          // 다음 페이지의 offset입니다. null이면 마지막 페이지입니다.
          next_offset?: number | null;
          [key: string]: unknown;
        };
      };
      [key: string]: unknown;
    };
    // 실행 결과를 회수하거나 해석하는 중 발생한 오류입니다.
    result_error?: string | null;
    // 결과를 응답에 표시하는 중 발생한 오류입니다.
    result_display_error?: string | null;
    // 실행의 완료 근거를 기다리고 있으면 true입니다. 같은 request_id로 script_03-get_execution tool을 조회합니다.
    pending?: boolean;
    // 정확한 완료 근거가 아직 확인되지 않았는지 나타냅니다. 자동 재실행을 허용하지 않습니다.
    uncertain?: boolean;
    // 첫 응답을 위한 대기가 끝났는지 나타냅니다. 실행 종료나 rollback을 뜻하지 않습니다.
    timed_out?: boolean;
    // 보관된 실행의 running, finishing, awaiting_receipt, completed, not_started 또는 unconfirmed 상태입니다.
    completion_state?: string;
    // 외부 연결의 현재 상태입니다. recovering이면 실행 확인과 원 호출 정리를 기다립니다.
    connection_state?: string;
    [key: string]: unknown;
  }>>;
};
```

### 79. script\_02-run\_rhino

```txt
연결된 RhinoCode에서 모델링·편집·측정 코드를 실행합니다. 전용 도구로 처리하기 어려운 작업에 사용합니다.
```

```ts
declare const tools: {
  mcp__rhino__script_02_run_rhino(args: {
    // 동기식 Python 소스, C# 문장 본문 또는 명령 매크로입니다. Python은 JSON-safe 값을 result에, C#은 결과 JSON을 result_json에 할당합니다. doc은 연결된 문서입니다. command는 !·Pause·대화상자 없이 끝나는 매크로를 입력합니다.
    script: string;
    // python(기본값 Python 3), python2, csharp, csharp-script 또는 command입니다. 모든 모드는 공식 RhinoCode를 사용합니다.
    // default: "python"
    language?: string;
    // 1-600의 정수이며 기본값은 60입니다. 실행 종료가 아닌 완료 근거 대기 한도입니다. beyond·CoS는 첫 대기를 최대 60초로 줄여 pending과 request_id를 먼저 반환할 수 있습니다. 미완료 응답은 같은 ID로 script_03-get_execution tool을 조회합니다.
    // default: 60
    timeout_seconds?: number;
  }): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // Rhino 실행 완료가 확인됐는지 나타냅니다. 변경 결과는 mutation_state와 result에서 확인합니다.
  completed?: boolean;
  // 필요할 때 script_03-get_execution tool으로 같은 요청을 조회하는 ID
  request_id?: string;
  // 실행 코드가 정한 JSON 값입니다.
  result?: unknown;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // 변경 적용 상태입니다. partial 또는 unknown이면 같은 수정을 다시 실행하기 전에 현재 상태를 확인합니다.
  mutation_state?: string;
  // 결과를 나누어 읽기 위한 정보입니다.
  result_page?: {
    // 결과 유형입니다. object, array, string, scalar 중 하나입니다.
    type?: string;
    // 문자열 페이지의 위치 단위입니다.
    unit?: string;
    // 조회할 수 있는 최상위 결과 필드입니다.
    available_fields?: Array<string>;
    // 결과 필드 이름별 페이지 정보입니다. 배열·문자열 전체는 result 키를 사용합니다.
    pages?: {
      [key: string]: {
        // 전체 항목 수 또는 문자열 길이입니다.
        total?: number;
        // 이번 페이지의 시작 위치입니다.
        offset?: number;
        // 반환한 항목 수 또는 문자열 길이입니다.
        returned?: number;
        // 다음 페이지의 offset입니다. null이면 마지막 페이지입니다.
        next_offset?: number | null;
        [key: string]: unknown;
      };
    };
    [key: string]: unknown;
  };
  // 실행 결과를 회수하거나 해석하는 중 발생한 오류입니다.
  result_error?: string | null;
  // 결과를 응답에 표시하는 중 발생한 오류입니다.
  result_display_error?: string | null;
  // 실행의 완료 근거를 기다리고 있으면 true입니다. 같은 request_id로 script_03-get_execution tool을 조회합니다.
  pending?: boolean;
  // 정확한 완료 근거가 아직 확인되지 않았는지 나타냅니다. 자동 재실행을 허용하지 않습니다.
  uncertain?: boolean;
  // 첫 응답을 위한 대기가 끝났는지 나타냅니다. 실행 종료나 rollback을 뜻하지 않습니다.
  timed_out?: boolean;
  // 보관된 실행의 running, finishing, awaiting_receipt, completed, not_started 또는 unconfirmed 상태입니다.
  completion_state?: string;
  // 외부 연결의 현재 상태입니다. recovering이면 실행 확인과 원 호출 정리를 기다립니다.
  connection_state?: string;
  [key: string]: unknown;
};
```

### 80. script\_03-get\_execution

```txt
이전에 요청한 RhinoCode 실행의 상태와 보관된 결과·로그를 조회합니다. **코드를 다시 실행하지 않습니다.** request_id를 생략하면 현재 연결의 가장 최근 실행을 조회하며, beyond·CoS에서는 ID를 지정해 원래 실행 연결을 찾습니다. 연결이 끝난 뒤에도 해당 실행 기록이 남아 있으면 조회할 수 있습니다.

결과의 배열이나 문자열은 페이지로 조회할 수 있습니다. 로그는 별도의 바이트 오프셋을 사용합니다.
```

```ts
declare const tools: {
  mcp__rhino__script_03_get_execution(args: {
    // 이전에 반환된 실행 request_id입니다. 비워 두면 현재 연결의 가장 최근 요청을 읽습니다. beyond·CoS는 지정한 ID의 원래 실행 연결을 찾습니다. 시간 초과 시에는 같은 ID로 결과를 조회합니다.
    // default: ""
    request_id?: string;
    // 기본 true.
    // default: true
    include_result?: boolean;
    // stdout·stderr와 CLI 로그 포함 여부. 기본 false.
    // default: false
    include_stdout?: boolean;
    // 객체 결과의 최상위 키 또는 객체 배열의 행에서 남길 키.
    // default: null
    result_fields?: (Array<string> | null);
    // 결과는 배열 항목 또는 문자열 문자, 로그는 바이트 단위. 기본 0.
    // default: 0
    offset?: number;
    // 결과 페이지 크기. 1~1000, 기본 100. 로그는 별도 크기 제한 적용.
    // default: 100
    limit?: number;
    // 결과의 식별자 포함 여부. 기본 true.
    // default: true
    include_ids?: boolean;
    // 기본 false.
    // default: false
    include_diagnostics?: boolean;
  }): Promise<CallToolResult<{
    // 보관된 실행 요청 ID입니다. 같은 실행의 상태나 다음 결과 페이지 조회에 사용합니다.
    request_id?: string;
    // 최종 Rhino 처리 근거와 CLI 종료가 모두 확인되었는지 여부. native_completed와 다를 수 있음
    completed?: boolean;
    // 보관된 실행의 상태입니다. 조회 호출 자체의 성공과 구분합니다.
    status?: string;
    // 실행 코드가 정한 JSON 값입니다.
    result?: unknown;
    // 현재 결과 또는 오류의 설명입니다.
    message?: string;
    // 오류 유형입니다.
    error_code?: string;
    // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
    next_step_guide?: string;
    // 변경 적용 상태입니다. partial 또는 unknown이면 같은 수정을 다시 실행하기 전에 현재 상태를 확인합니다.
    mutation_state?: string;
    // 결과를 나누어 읽기 위한 정보입니다.
    result_page?: {
      // 결과 유형입니다. object, array, string, scalar 중 하나입니다.
      type?: string;
      // 문자열 페이지의 위치 단위입니다.
      unit?: string;
      // 조회할 수 있는 최상위 결과 필드입니다.
      available_fields?: Array<string>;
      // 결과 필드 이름별 페이지 정보입니다. 배열·문자열 전체는 result 키를 사용합니다.
      pages?: {
        [key: string]: {
          // 전체 항목 수 또는 문자열 길이입니다.
          total?: number;
          // 이번 페이지의 시작 위치입니다.
          offset?: number;
          // 반환한 항목 수 또는 문자열 길이입니다.
          returned?: number;
          // 다음 페이지의 offset입니다. null이면 마지막 페이지입니다.
          next_offset?: number | null;
          [key: string]: unknown;
        };
      };
      [key: string]: unknown;
    };
    // 실행 결과를 회수하거나 해석하는 중 발생한 오류입니다.
    result_error?: string | null;
    // 결과를 응답에 표시하는 중 발생한 오류입니다.
    result_display_error?: string | null;
    [key: string]: unknown;
  }>>;
};
```

### 81. script\_04-save\_document

```txt
연결된 문서 전체를 기존 .3dm 경로에 저장합니다. 사용자에게 영구 저장을 요청받은 경우 사용합니다.
```

```ts
declare const tools: {
  mcp__rhino__script_04_save_document(args: {}): Promise<CallToolResult<{
    result: string;
    [key: string]: unknown;
  }>>;
};
```

`result`의 JSON 내용:

```ts
type DecodedResult = {
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
  // true는 확인된 저장, false는 확인된 실패, null은 미확정이며 requires_reconciliation=true
  saved?: boolean | null;
  // 저장 확인 직후의 문서 수정 플래그입니다.
  modified?: boolean;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  [key: string]: unknown;
};
```
