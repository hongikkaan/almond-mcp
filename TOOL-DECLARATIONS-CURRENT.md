# 현행 툴 선언

## 기준 및 선언 표기

beyond·CoS의 공개 도구 81개. 연결 대상 입력, 연결 관리 도구 설명, 연결 성공 응답의 ID 필드 설명은 경로별로 다름.

- 수집일: 2026-11-22. 기준: 이 문서와 함께 관리하는 소스.
- 수집 경로: `src/cos/codex_host.py`와 `src/cos/cos_host.py`의 공용 `external_host.main`. 격리된 데이터 폴더에서 Rhino 연결 없이 stdio `initialize`·`tools/list` 호출.
- 실행 패키지: almond-mcp 0.7.0rc2 / fastmcp 4.1.0 / mcp 2.3.0 / mcp-types 2.3.0.
- CoS 선언 SHA-256: `eff0cde93691f7e5d8c79fdc94fdb215d2acc2cb2886fd0e224e2d615d4c5cfe`
- beyond 선언 SHA-256: `0a4419681889de81948fe91a0bc56fef0d505b9368ec9dcb9a46d805d754e087`
- 이름순 tools 배열을 UTF-8 JSON(`sort_keys=True`, `ensure_ascii=False`, `separators=(",", ":")`)으로 직렬화한 해시.
- 도구명·입력 설명은 구현 함수와 docstring, 출력 설명은 `src/mcp/output_contracts.py`에서 확인. 공통 스키마 기준은 `tests/integration/tool_schemas.json`, 외부 연결 도구 정의는 `src/cos/external_host.py` 참조.

TypeScript 표기에서 `?`는 선택 인자, `Array<T>`는 배열, `| null`은 null 허용. 기본값과 범위는 필드 위에 표시. 검증 기준은 JSON Schema이며 TypeScript 표기에서 `oneOf`의 배타성은 생략. 인덱스 시그니처는 `additionalProperties` 허용을 뜻함.

각 도구의 TypeScript 입력 표기는 CoS 기준. beyond에서는 `context_01-get_policy` tool, `connect_01-list_up` tool, `connect_02-session` tool, `connect_03-start_session` tool을 제외한 77개 도구의 최상위 `args`에 필수 `connection_id: string` 추가. 값은 소문자 16진수 32자리(`^[0-9a-f]{32}$`)이며 연결 또는 시작 응답에서 받은 값. 중첩된 `request`가 있는 경우에도 이 ID는 `request`와 같은 레벨에 전달. 필수 ID 생략 시 `connection_id가 지정되지 않았습니다` 오류를 반환하고 실행 중단.

각 제목이 실제 공개 도구명. `mcp__rhino__`는 연결 이름의 예시. `CallToolResult<T>`의 `T`는 구조화된 출력. `result: string`의 JSON 내부 구조는 공개 `contentSchema`가 있을 때 `DecodedResult`로 표시. 이미지·텍스트 블록과 오류 여부는 MCP 응답 봉투에 포함.

## 적용 범위

beyond·CoS 외부 연결기 기준. RhinoTerminal과 관리 실행기의 문서 전용 `rhino_session`은 [연결 경로 사양](src/mcp/runtime/CONNECTION-SPEC.md), 독립 Python MCP는 [MCP 사양](src/mcp/SPEC.md) 참조. [Almond Project Dashboard](src/mcp/runtime/dashboard/README.md)는 로컬 HTTP로 기존 SQLite를 조회.

## 공통 안내와 실행 결과

- 서버 소개는 `serverInfo.description`과 `initialize.instructions` 첫머리에 전달. 이어서 기술 참고 자료 조회 방법과 `guide_version`을 전달. 설계 지침 본문과 별도 설치 스킬은 읽지 않음. 개별 도구 설명은 `tools/list`의 `description`에서 확인. 초기 지침을 모델에 표시하는 방식은 클라이언트에 따름.
- 정책은 Rhino 연결 선택 전에도 `context_01-get_policy` tool로 조회 가능. 기본값 `basic`은 공통 도구 참고 목록과 참고 자료 종류를 반환. 이 연결에서 호출할 수 있는 도구는 `tools/list`에서 확인. `policy="metadata"`는 객체 키 사전을 반환.
- `plan_03-execute_looping` tool의 성공 응답은 다음 Step의 선택·기록 방법과 회차 결과를 보고할 때 시각적 근거를 포함하라는 안내를 제공한다.
- `connect_02-session` tool 또는 `connect_03-start_session` tool로 연결. CoS의 일반 호출은 선택한 연결을 사용. beyond는 각 호출에서 연결 ID를 지정하며 `script_03-get_execution` tool로 실행을 재조회할 때도 원래의 `connection_id`와 `request_id`를 함께 전달.
- 외부 실행의 첫 대기 한도는 `min(요청 timeout, 60초)`. `pending`이면 같은 `request_id`로 완료 여부 조회. 외부 클라이언트 제한은 600초. 대기 종료·취소·오류 후에는 실제 문서 상태와 실행 결과를 확인하고 재실행 여부를 결정. [RhinoCode 실행 계약](src/mcp/runtime/RHINOCODE-SPEC.md) · [외부 연결기 SPEC](src/cos/SPEC.md)

## 선언 갱신 절차

[저장소 지침](AGENTS.md)에 따라 두 외부 서버를 격리된 데이터 폴더에서 시작. `initialize`에서 초기 안내를 확인하고, `tools/list`에서 목록·설명·입출력 스키마 전체를 비교한 뒤 이 문서와 해시를 갱신. Rhino 연결·모델링 호출 없이 검사 가능.

# Tool

## analysis

### 1. analysis\_05-check\_egress

```txt
층별 출구 수·유효 폭·이격·보행거리 예비 검토. Rhino에서 형상이나 경로를 읽지 않으므로 실제 층 경계와 문 중심·유효 폭, 가장 불리한 보행 경로를 직접 측정해 입력. 출구가 둘 이상이면 가장 먼 두 출구의 직선 이격을 검사.

출구는 문마다 한 번만 입력. 중복 중심, 좌표·폭 누락, 비유한 수, 음수 폭·거리·면적, 양의 정수가 아닌 층수, 면적이 0인 경계는 거절. 폭 0은 폭 부족 판정을 위해 허용.

비업무 용도의 보행거리는 업무용 기준으로 대체. 스프링클러가 있는 막다른 복도도 업무용 기준을 쓰며 용도 경고는 별도로 나오지 않음. 경계값에서는 표시값 반올림으로 판정이 달라 보일 수 있음. BCI와 통상적인 IBC 수치를 사용하므로 source_note·warnings를 프로젝트 적용 법규와 대조.
```

```ts
declare const tools: {
  mcp__rhino__analysis_05_check_egress(args: {
    // 층 바닥 경계 [min_x, min_y, max_x, max_y].
    plate_bounds_mm: Array<number>;
    // 문마다 {"name": string, "x_mm": number, "y_mm": number, "width_mm": number}. 좌표는 문 중심, 폭은 유효 피난 폭.
    exits: Array<{
      [key: string]: unknown;
    }>;
    // business, mercantile, assembly_unconcentrated, classroom, residential, storage.
    // default: "business"
    occupancy?: string;
    // 출구가 담당하는 층수. 2층 이상이면 최소 2개 출구와 계단 폭 계수(7.6 mm/인) 적용.
    // default: 1
    stories?: number;
    // 전체 구역 설치 기준.
    // default: true
    sprinklered?: boolean;
    // 실제 재실 면적. 0이면 층 경계의 직사각형 면적 사용.
    // default: 0.0
    net_area_m2?: number;
    // 입력 길이 중 최댓값 검사. 빈 배열이면 검사 생략.
    // default: []
    travel_distances_m?: Array<number>;
    // 가장 긴 막다른 복도 길이. 0이면 검사 생략.
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
  // 수행한 검사만의 종합 판정. 길이를 입력하지 않은 경로는 미검사.
  passed?: boolean;
  occupancy?: string;
  // 재실 면적을 용도별 1인당 면적으로 나누어 올림.
  occupant_load?: number;
  area_m2?: number;
  // 입력 경계의 직사각형 면적.
  gross_area_m2?: number;
  checks?: Array<{
    check?: string;
    required?: number;
    provided?: number;
    passed?: boolean;
    basis?: string;
    [key: string]: unknown;
  }>;
  warnings?: Array<string>;
  source_note?: string;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 2. analysis\_04-export\_structural\_report

```txt
구조 검증 이력의 Markdown 보고서 생성. 각 실행에 실제 엔진과 적용 입력을 기록하고, 저장되지 않은 과거 입력은 알 수 없음으로 표시.
```

```ts
declare const tools: {
  mcp__rhino__analysis_04_export_structural_report(args: {
    // 관리형은 선택한 Plan 산출물 폴더 기준 상대 경로(생략 시 reports/structural-validation.md). 독립 실행에서 생략 시 사용자 데이터의 reports/structural-validation-<timestamp>.md.
    // default: ""
    path?: string;
    // 최대 500회.
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
  status?: string;
  path?: string;
  runs?: number;
  latest_method?: string;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 3. analysis\_01-list\_design\_codes

```txt
구조 해석에 사용할 설계기준 프로필 조회.
```

```ts
declare const tools: {
  mcp__rhino__analysis_01_list_design_codes(args: {
    // default: false
    include_ids?: boolean;
    // parameters, source, audit, all. 생략하거나 빈 배열이면 요약.
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
  // 기본으로 적용되는 프로필 ID.
  default?: string;
  profiles?: Array<{
    // analysis_02-validate_structure tool과 analysis_03-visualize_structure tool의 design_code에 전달.
    id?: string;
    name?: string;
    basis?: string;
    // 프로필 값의 검증 여부. 프로젝트 법규 준수나 구조 승인은 별도.
    verified?: boolean;
    unverified?: Array<unknown>;
    // 허용 처짐 L/n의 n.
    deflection_limit_ratio?: number;
    // 프로필 권장 활하중.
    imposed_floor_kn_m2?: {
      [key: string]: unknown;
    };
    [key: string]: unknown;
  }>;
  // 로딩 중 거절된 사용자 프로필의 문제.
  problems?: Array<unknown>;
  user_dir?: string;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 4. analysis\_02-validate\_structure

```txt
Rhino 구조 형상의 해석과 설계기준 검토. 실행 이력에는 요청 옵션, 실제 엔진·입력·결과를 보관. native는 내보낸 모델과 적용한 하중도 기록. 이전 이력에 기록되지 않은 옵션은 알 수 없음으로 표시.
```

```ts
declare const tools: {
  mcp__rhino__analysis_02_validate_structure(args: {
    // 현재 Rhino 문서의 해석 대상 객체 GUID.
    guids: Array<string>;
    // "beam" 단순 보 휨·처짐, "truss" 축력·좌굴, "shell" 셸 응력·변위, "frame" 프레임 모멘트·전단, "canopy" 캔틸레버 캐노피, "gridshell" 대변형 그리드셸, "membrane" 막 구조 형상 탐색, "highrise" 고층 구조 시스템.
    // default: "beam"
    structure_type?: string;
    // 전체 부과하중. native는 자유 절점에 하향(-Z) 균등 분배. 바닥·자산 하중과 중복되지 않게 산정하고 필요 시 0 지정.
    // default: 10.0
    load_kn?: number;
    // "Steel", "S355", "Concrete", "Wood", "Aluminium".
    // default: "Steel"
    material?: string;
    // auto, native, karamba 중 선택. auto는 선형 프레임에 native, 그 외에 Karamba 선택. karamba는 api → template → rule_based 순으로 시도. 실제 적용 방식은 analysis_method·warnings에서 확인.
    // default: "auto"
    engine?: string;
    // true는 완전 고정, false는 회전이 자유로운 핀 지점.
    // default: true
    fixed_supports?: boolean;
    // default: true
    self_weight?: boolean;
    // 네이티브 해석에서 부재가 여러 절점으로 분할된 경우 L/250을 적용할 전체 경간(예: 3.1 m 두 구간으로 그린 6.2 m 장선).
    // default: null
    span_m?: (number | null);
    // 네이티브 해석에서 배치 자산의 자중·내용물·재실자 하중 추가. 다른 입력에 반영한 하중과 중복되지 않게 산정.
    // default: false
    asset_loads?: boolean;
    // 네이티브 해석에서 한 층의 보로 둘러싸인 모든 구획에 적용(예: EN 1991-1-1 Category A 주거용 2.0 kN/m²). 보는 45° 규칙에 따라 양방향 분담하며 장단변비가 2:1을 넘으면 일방향 분담. 용도별 활하중에 가구·재실자가 포함되므로 asset_loads는 무거운 특정 물품에만 병행하고 중복 계산을 피하려면 load_kn을 0으로 지정.
    // default: 0.0
    floor_load_kn_m2?: number;
    // 같은 바닥 구획의 구성층·마감 등 추가 고정하중.
    // default: 0.0
    floor_dead_kn_m2?: number;
    // 네이티브 하중 조합. "en1990"은 처짐에 SLS G + Q, 부재 검토에 ULS 1.35 G + 1.5 Q 사용. G는 자중·바닥 구성층·배치 물품 중량, Q는 load_kn·용도별 활하중·내용물·재실자. "unfactored"는 Karamba와 같이 둘 다 G + Q 적용.
    // default: "en1990"
    design_basis?: string;
    // "6.10" 또는 "6.10ab". "6.10ab"는 각 부재에서 6.10a·6.10b 중 불리한 결과를 적용. 생략 시 프로필의 식을 사용(Eurocode: 6.10). 프로필이 식을 지정한 경우 요청보다 우선하며 경고 반환.
    // default: null
    uls_combination?: (string | null);
    // 네이티브 접합 조건. "rigid"는 모든 접합부의 모멘트를 전달하고, "simple"은 보 단부의 강축 휨과 가새 단부의 양축 휨을 해제. 같은 선상으로 이어지는 부재와 기둥은 연속 유지. 일반 볼트 접합 강구조·목구조는 "simple"에 가깝고 강접합은 보 처짐을 과소평가할 수 있음. 곡선 User Text의 release 값("pinned", "pinned_start", "pinned_end", "rigid") 우선.
    // default: "rigid"
    connections?: string;
    // "auto"는 모든 ULS 조합의 탄성 임계 하중 계수 alpha_cr(EN 1993-1-1 5.2.1)과 ±X·±Y 횡변위 초기 불완전성 φ = 1/200 × αh × αm(5.3.2) 적용. alpha_cr < 10이면 2차 P-Delta ULS 해석, alpha_cr ≤ 1이면 불안정으로 실패 처리. "off"는 초기 불완전성을 적용하지 않는 1차 해석.
    // default: "auto"
    stability?: string;
    // 설계기준·국가 부록의 gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, 처짐 한계를 정하는 프로필. "eurocode"는 EN 권장값, 기타 프로필은 analysis_01-list_design_codes tool에서 선택. "off"는 design_basis="unfactored"와 같이 G + Q 적용.
    // default: "eurocode"
    design_code?: string;
    // 네이티브 결과에 부재별 단면력·사용률·처짐과 지점 반력 포함.
    // default: false
    detail?: boolean;
    // 강재 중공 단면(CHS/RHS)의 제작 방식. "cold_formed"는 EN 10219 좌굴 곡선 c, "hot_finished"는 EN 10210 곡선 a(S460은 a0). 좌굴 내력 차이가 최대 약 23%이므로 명시된 경우에만 "hot_finished" 사용.
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
  status?: string;
  // indicative 해석에서는 판정이 없을 수 있음(null). 구조 안전 인증은 별도.
  passed?: boolean | null;
  structure_type?: string;
  material?: string;
  // warnings·assumptions와 설계기준의 미검증 값까지 함께 검토.
  confidence?: string;
  results?: {
    analysis_method?: string;
    max_deflection_mm?: number;
    deflection_limit_mm?: number;
    span_m?: number;
    utilization_ratio?: number;
    per_element_utilization?: Array<{
      // analysis_03-visualize_structure tool의 display_guids에 재사용.
      source_guids?: Array<string>;
      utilization?: number;
      // 부재 판정을 지배한 하중 조합.
      combination?: string;
      [key: string]: unknown;
    }>;
    [key: string]: unknown;
  };
  // 검토 결과가 가장 불리한 부재 최대 5개.
  worst_member_guids?: Array<string>;
  warnings?: Array<string>;
  assumptions?: Array<string>;
  design_code?: {
    id?: string;
    unverified?: Array<unknown>;
    [key: string]: unknown;
  };
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 5. analysis\_03-visualize\_structure

```txt
구조 해석 결과를 임시 뷰포트 오버레이로 표시.
```

```ts
declare const tools: {
  mcp__rhino__analysis_03_visualize_structure(args: {
    // 구조 축선 곡선과 지점 표식 점의 GUID. 지점 표식이 없으면 최하단 절점을 지점으로 사용(fixed_supports 참조).
    // default: null
    guids?: (Array<string> | null);
    // 자유 절점에 하향(-Z) 균등 분배할 전체 부과하중.
    // default: 10.0
    load_kn?: number;
    // "Steel", "S355", "Concrete", "Wood", "Aluminium".
    // default: "Steel"
    material?: string;
    // 원형 부재의 외경.
    // default: null
    beam_diameter_mm?: (number | null);
    // default: null
    beam_wall_mm?: (number | null);
    // default: true
    self_weight?: boolean;
    // true는 완전 고정, false는 회전이 자유로운 핀 지점.
    // default: true
    fixed_supports?: boolean;
    // 허용 처짐 L/n의 n. 생략 시 설계기준 한계 사용(예: Eurocode의 L/250은 250).
    // default: null
    deflection_limit_ratio?: (number | null);
    // 처짐 한계 평가에 쓸 기준 경간. 생략 시 가장 긴 부재 사용. 6.2 m 장선을 3.1 m씩 분할했다면 6.2 지정.
    // default: null
    span_m?: (number | null);
    // "displacement" 또는 "utilization".
    // default: "displacement"
    color_by?: string;
    // 변형 표시 배율. 생략 시 표시 변형을 경간의 약 6%로 조정.
    // default: null
    scale?: (number | null);
    // 표시할 부재 비율 0..1. 단계별 시공 재생에 사용.
    // default: 1.0
    reveal?: number;
    // false이면 마지막 계산을 재사용하고 표시 옵션(scale, color_by, reveal, physics, title)만 갱신.
    // default: true
    reanalyze?: boolean;
    // false이면 해석 오버레이 없이 같은 부재의 일반 형상을 그려 전후 비교.
    // default: true
    physics?: boolean;
    // 그릴 부재만 선택(예: 단면을 보여 줄 한 줄의 프레임). 해석은 guids 전체에 적용.
    // default: null
    display_guids?: (Array<string> | null);
    // default: ""
    title?: string;
    // 현재 해석 오버레이 제거.
    // default: false
    clear?: boolean;
    // "native", "karamba", "auto". "auto"는 네이티브 프레임 솔버를 우선 사용하고 셸이 포함되거나 브리지에서 모델을 내보낼 수 없으면 Karamba 사용.
    // default: "auto"
    engine?: string;
    // 네이티브 해석에서 analysis_02-validate_structure tool과 같은 배치 자산 하중을 추가하고 작용점에 하중 화살표 표시.
    // default: false
    asset_loads?: boolean;
    // 네이티브 해석에서 한 층의 보로 둘러싸인 모든 구획에 적용(예: EN 1991-1-1 Category A 주거용 2.0 kN/m²). 보는 45° 규칙에 따라 양방향 분담하며 장단변비가 2:1을 넘으면 일방향 분담. 용도별 활하중에 가구·재실자가 포함되므로 asset_loads는 무거운 특정 물품에만 병행하고 중복 계산을 피하려면 load_kn을 0으로 지정.
    // default: 0.0
    floor_load_kn_m2?: number;
    // 같은 바닥 구획의 구성층·마감 등 추가 고정하중.
    // default: 0.0
    floor_dead_kn_m2?: number;
    // 네이티브 하중 조합. "en1990"은 처짐에 SLS G + Q, 부재 검토에 ULS 1.35 G + 1.5 Q 사용. G는 자중·바닥 구성층·배치 물품 중량, Q는 load_kn·용도별 활하중·내용물·재실자. "unfactored"는 Karamba와 같이 둘 다 G + Q 적용.
    // default: "en1990"
    design_basis?: string;
    // "6.10" 또는 "6.10ab". "6.10ab"는 각 부재에서 6.10a·6.10b 중 불리한 결과를 적용. 생략 시 프로필의 식을 사용(Eurocode: 6.10). 프로필이 식을 지정한 경우 요청보다 우선하며 경고 반환.
    // default: null
    uls_combination?: (string | null);
    // analysis_02-validate_structure tool과 같은 "rigid" 또는 "simple". 핀 접합 단부는 작은 원으로 표시.
    // default: "rigid"
    connections?: string;
    // analysis_02-validate_structure tool과 같은 "auto" 또는 "off".
    // default: "auto"
    stability?: string;
    // 설계기준·국가 부록의 gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, 처짐 한계를 정하는 프로필. "eurocode"는 EN 권장값, 기타 프로필은 analysis_01-list_design_codes tool에서 선택. "off"는 design_basis="unfactored"와 같이 G + Q 적용.
    // default: "eurocode"
    design_code?: string;
    // 강재 중공 단면(CHS/RHS)의 제작 방식. "cold_formed"는 EN 10219 좌굴 곡선 c, "hot_finished"는 EN 10210 곡선 a(S460은 a0). 좌굴 내력 차이가 최대 약 23%이므로 명시된 경우에만 "hot_finished" 사용.
    // default: "cold_formed"
    fabrication?: string;
    // "deflection"은 처짐 형상, "buckling"은 지배 ULS 조합의 첫 좌굴 모드와 alpha_cr 표시(STABLE ≥ 10, SWAY-SENSITIVE 1~10, UNSTABLE ≤ 1).
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
  status?: string;
  analysis_method?: string;
  // indicative에서 null이면 해석까지 완료했으며 재료 내력의 합격 판정은 생략.
  passed?: boolean | null;
  max_displacement_mm?: number;
  deflection_limit_mm?: number;
  span_m?: number;
  max_utilization?: number | null;
  // 변형을 화면에 그릴 때 적용한 과장 배율.
  scale?: number;
  elements?: Array<{
    // display_guids 또는 객체 관찰에 재사용.
    source_guids?: Array<string>;
    max_displacement_mm?: number;
    utilization?: number | null;
    [key: string]: unknown;
  }>;
  nodes?: number;
  warnings?: Array<string>;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

## asset

### 6. asset\_01-audit\_drawing

```txt
저장된 도면 패키지의 SVG·DXF를 파일 해시 목록과 대조. 빈 해시 목록, 누락·변경 파일, 패키지 외부 경로, 파일시스템 링크는 오류. 원본을 찾으면 원본 변경도 검사.
```

### 7. asset\_02-generate\_drawing\_views

```txt
등록 3DM 또는 사용자 GLB 메시의 평면·정면·우측면 실루엣 생성. 실물 크기 mm DXF와 축척 SVG를 출력. 세 뷰가 A3에 들어가면 시트 SVG도 생성하며, 시트 없이도 성공 가능.

정면은 좌표계 기준. 실루엣에 단면·내부 가시선·은선은 없으며 축척별 단순화로 작은 윤곽이 달라질 수 있음. 결과는 별도 drawing-runs에 저장하고 등록 자산의 도면은 갱신하지 않음.
```

### 8. asset\_03-get\_drawings

```txt
등록 자산의 저장 도면 패키지 조회. 도면은 배치 인스턴스 변환을 적용하지 않은 자산 원본 형상의 투영. manifest에서 파일·축척·치수·출처·투영 한계를 확인.
```

```ts
declare const tools: {
  mcp__rhino__asset_03_get_drawings(args: {
    // 기존 라이브러리 자산 ID. 모르는 경우 include_ids=true로 목록·검색 결과에서 확인.
    asset_id: string;
    // default: false
    include_ids?: boolean;
    // dimensions, source, paths, drawing, metadata, audit, all. 생략하거나 빈 배열이면 요약.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    status?: string;
    // field_groups에 all을 지정해 반환받은 경로를 asset_01-audit_drawing tool의 package_dir에 전달.
    package_dir?: string;
    plan_svg_uri?: string;
    manifest?: {
      [key: string]: unknown;
    };
    message?: string;
    error_code?: string;
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 9. asset\_04-get

```txt
모델·2D 자산의 등록 정보와 사용 가능 상태 조회. field_groups에 paths를 지정하면 원본·모델 경로를 확인.
```

```ts
declare const tools: {
  mcp__rhino__asset_04_get(args: {
    // 기존 라이브러리 자산 ID. 모르는 경우 include_ids=true로 목록·검색 결과에서 확인.
    asset_id: string;
    // 조회에 사용한 asset_id는 응답에 반복되지 않을 수 있음.
    // default: false
    include_ids?: boolean;
    // dimensions, source, paths, drawing, metadata, audit, all. 생략하거나 빈 배열이면 요약.
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
  status?: string;
  asset?: {
    name?: string;
    // 원본·등록 파일의 존재 여부.
    file_available?: boolean;
    // ready, needs_conversion, needs_refresh 등. source_only인 자산은 배치 전 변환 필요.
    model_status?: string;
    // 현재 원본과 일치하는 도면 패키지가 준비된 상태.
    drawing_ready?: boolean;
    [key: string]: unknown;
  };
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 10. asset\_05-list

```txt
모델·2D 자산 목록과 배치 준비 상태 조회. 상세 조회용 ID는 include_ids=true로 포함.
```

```ts
declare const tools: {
  mcp__rhino__asset_05_list(args: {
    // 빈 값은 전체 분류.
    // default: ""
    category?: string;
    // default: 20
    limit?: number;
    // 페이지의 시작 위치(0부터).
    // default: 0
    offset?: number;
    // default: false
    include_ids?: boolean;
    // dimensions, source, paths, drawing, metadata, audit, all. 생략하거나 빈 배열이면 요약.
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
  // include_ids=true일 때 포함.
  library_id?: string;
  // 추가 준비가 필요한 항목은 next_tool·next_step_guide 참고.
  assets?: Array<{
    [key: string]: unknown;
  }>;
  total?: number;
  limit?: number;
  offset?: number;
  // true이면 같은 필터로 offset에 이번에 반환된 자산 수를 더해 다음 페이지 조회.
  truncated?: boolean;
  purpose?: string;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 11. asset\_06-place

```txt
모델·2D 자산을 Rhino 문서에 블록으로 배치. 3DM은 원본에 연결되며 정의를 갱신하면 같은 정의를 사용하는 기존 배치에 반영.
```

```ts
declare const tools: {
  mcp__rhino__asset_06_place(args: {
    // 기존 라이브러리 자산 ID. 모르는 경우 include_ids=true로 목록·검색 결과에서 확인.
    asset_id: string;
    // 원본 기준점의 월드 좌표(문서 단위).
    // default: 0
    x?: number;
    // 원본 기준점의 월드 좌표(문서 단위).
    // default: 0
    y?: number;
    // 원본 기준점의 월드 좌표(문서 단위).
    // default: 0
    z?: number;
    // 월드 Z축 기준.
    // default: 0
    rotation_degrees?: number;
    // 균일 배치 축척(0 초과 100 이하).
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
  status?: string;
  asset_id?: string;
  // 삽입한 최상위 블록 GUID. inspect_02-get_objects tool 또는 Scene 구성원 입력에 재사용.
  object_guid?: string;
  // 공유 정의 갱신 시 definition_refreshed·affected_existing_instances가 추가될 수 있음.
  definition_created?: boolean;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  // unknown·partial이면 문서에 변경이 남아 있을 수 있음.
  mutation_state?: string;
  // true이면 Rhino 문서의 실제 변경 상태를 확인. 자동 재실행 금지.
  requires_reconciliation?: boolean;
  // null이면 변경 적용 여부 미확인.
  mutation_applied?: boolean | null;
  [key: string]: unknown;
};
```

### 12. asset\_07-prepare

```txt
원본 사본을 시각 검토해 등록용 3DM을 준비. inspect로 작업을 만들고, 수정이 필요할 때만 normalize 실행. 첫 verify가 생성한 최종 미리보기를 확인한 뒤 같은 해시·이름·ID로 verify를 다시 호출.
```

```ts
declare const tools: {
  mcp__rhino__asset_07_prepare(args: {
    // inspect, normalize, verify, status. status는 저장 근거만 조회하며 네이티브 실행 재개나 단계 갱신은 하지 않음.
    stage: string;
    // inspect에 사용할 모델. 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로. 원본 바이트는 보존.
    // default: ""
    source_file?: string;
    // 이전 응답의 job_dir. normalize·verify·status에 필수. 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로.
    // default: ""
    job_dir?: string;
    // OBJ/STL/PLY/OFF/GLB/glTF의 측정된 원본 단위(mm, cm, m, in, ft). inspect 이후 생략. 3DM은 내장 단위 유지.
    // default: ""
    input_units?: string;
    // normalize: {vision_reviewed:true, inspected_sha256:"확인한 해시", rotation_degrees_xyz:[x,y,z], translation:[x,y,z], remove:[{object_id:"ID", reason:"사유"}]}. 생략한 변환은 그대로 두며 translation은 원본 단위. 최종 미리보기 확인 후 verify: {vision_reviewed:true, final_sha256:"확인한 해시", name:"이름", asset_id:"ID"}.
    // default: null
    review?: ({
      [key: string]: unknown;
    } | null);
    // summary, parts, previews, provenance, all. 생략 시 미리보기 경로 포함, []는 요약. 페이지 처리는 parts에만 적용.
    // default: null
    field_groups?: (Array<string> | null);
    // default: false
    include_ids?: boolean;
    // 페이지의 시작 위치(0부터).
    // default: 0
    offset?: number;
    // 부품 목록 페이지당 1~200개.
    // default: 50
    limit?: number;
  }): Promise<CallToolResult<{
    // passed는 해당 단계의 검사 통과, pending은 검사 대기, error는 실패 또는 완료 미확정. 등록 가능 여부는 ready_for_registration으로 확인.
    status?: string;
    // ready일 때만 source_3dm 제공. running·unconfirmed·failed이면 status=error.
    state?: string;
    // 현재 파일 해시에 대해 호출자가 이미지 검토를 확인한 상태. 형상 적합성은 별도 판단.
    ready_for_registration?: boolean;
    // 이후 단계에 전달. asset_09-register tool에는 preparation_job으로 전달.
    job_dir?: string;
    // 검토를 마친 최종 3DM. 검토한 name·asset_id와 함께 asset_09-register tool에 전달.
    source_3dm?: string;
    next_stage?: string | null;
    review_evidence?: string;
    next_step_guide?: string;
    message?: string;
    error_code?: string;
    [key: string]: unknown;
  }>>;
};
```

### 13. asset\_08-refresh

```txt
편집·저장한 등록 3DM을 다시 측정해 평면·입면 도면을 새 리비전으로 발행. 원본 경로와 이전 도면은 보존. 내부 가시선·은선·레이어 표시는 생성 범위에서 제외.

열린 Rhino 문서의 연결 블록 갱신·저장은 별도. 공유 정의를 갱신하면 기존 인스턴스에 반영되며 배치 당시 메타데이터는 유지.
```

```ts
declare const tools: {
  mcp__rhino__asset_08_refresh(args: {
    asset_id: string;
  }): Promise<CallToolResult<{
    status?: string;
    // true이면 인덱스 갱신 오류가 있어도 게시 완료. 다시 게시하기 전에 상태 확인.
    registration_applied?: boolean;
    source_path_preserved?: boolean;
    rhino_linked_instances_updated?: boolean;
    // 게시 완료 후 인덱스 갱신만 실패했다면 재연결.
    live_index_refreshed?: boolean;
    asset?: {
      [key: string]: unknown;
    };
    model_path?: string;
    package_dir?: string;
    // 이전 도면, 매니페스트 백업, 원본 리비전 사본 보존 여부.
    previous_files_retained?: boolean;
    message?: string;
    error_code?: string;
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 14. asset\_09-register

```txt
검토한 3DM을 모델 라이브러리에 등록하고 치수·평면·입면 실루엣 도면을 생성. 내부 가시선·은선·레이어 표시는 생성 범위에서 제외. 준비를 마쳤어도 파생 메시가 250,000 삼각형을 넘으면 등록 실패. 등록 결과는 asset_04-get tool에서 확인.
```

```ts
declare const tools: {
  mcp__rhino__asset_09_register(args: {
    // 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로. preparation_job을 지정하면 준비 단계 응답의 source_3dm 사용.
    source_3dm: string;
    // preparation_job을 지정하면 준비 단계에서 검토한 ID와 일치해야 함.
    asset_id: string;
    // preparation_job을 지정하면 준비 단계에서 검토한 이름과 일치해야 함.
    name: string;
    // default: "other"
    category?: string;
    // default: null
    tags?: (Array<string> | null);
    // default: ""
    description?: string;
    // default: ""
    source_url?: string;
    // true일 때만 같은 ID의 기존 자산 교체.
    // default: false
    replace_existing?: boolean;
    // 완료한 준비 작업의 job_dir. 검토를 거친 다중 형식 변환 등록에 필수. 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로.
    // default: ""
    preparation_job?: string;
  }): Promise<CallToolResult<{
    status?: string;
    // 게시 결과가 불명확하면 null과 requires_reconciliation 반환. 상태 확인 없이 재시도 금지.
    registration_applied?: boolean | null;
    // 게시 완료 후 인덱스 갱신만 실패했다면 재등록 없이 재연결.
    live_index_refreshed?: boolean;
    source_path_preserved?: boolean;
    // 기존 원본을 교체하면 해당 원본에 연결된 인스턴스에 영향 가능.
    linked_instances_may_update?: boolean;
    asset?: {
      [key: string]: unknown;
    };
    library_dir?: string;
    model_path?: string;
    // DXF와 치수는 mm 단위.
    package_dir?: string;
    manifest_path?: string;
    // 교체 전 원본·도면·매니페스트 백업 보존 여부.
    previous_files_retained?: boolean;
    previous_source_sha256?: string | null;
    message?: string;
    error_code?: string;
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 15. asset\_10-search\_repository

```txt
모델·2D 요소 아카이브 검색. 후보가 limit에서 잘리면 검색어나 유형을 좁혀 다시 조회. 원본만 있는 자산은 변환이 필요할 수 있으며 상세 정보·경로는 후보 ID로 asset_04-get tool에서 조회.
```

```ts
declare const tools: {
  mcp__rhino__asset_10_search_repository(args: {
    // 이름·ID·분류·variant·재료 ID·태그·역할에서 대소문자 구분 없이 공백으로 나눈 모든 단어 검색.
    // default: ""
    query?: string;
    // all, element, model.
    // default: "all"
    kind?: string;
    // default: false
    drawing_ready?: boolean;
    // 1..100으로 보정.
    // default: 20
    limit?: number;
    // default: false
    include_ids?: boolean;
    // dimensions, source, paths, drawing, metadata, audit, all.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    // limit 적용 전 전체 일치 건수. 다음 페이지 없음.
    total?: number;
    // id를 후속 조회의 asset_id로 전달.
    assets?: Array<{
      [key: string]: unknown;
    }>;
    message?: string;
    error_code?: string;
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 16. asset\_11-search

```txt
모델·2D 자산을 검색어·분류·최대 치수로 검색. 단어가 하나라도 일치하면 포함하고 일치 단어가 많은 순으로 반환. 치수 필터는 등록 치수를 비교하며 해당 치수가 없는 자산도 포함할 수 있음. include_ids=true로 얻은 ID를 asset_04-get tool에 전달해 상세 조회.
```

```ts
declare const tools: {
  mcp__rhino__asset_11_search(args: {
    // 이름·설명·제품·분류·태그 등에서 대소문자 구분 없이 부분 일치 검색.
    // default: ""
    query?: string;
    // 대소문자를 구분하지 않는 정확 일치. 빈 값은 전체 분류.
    // default: ""
    category?: string;
    // 양수일 때만 필터 적용.
    // default: 0
    max_width_mm?: number;
    // 양수일 때만 필터 적용.
    // default: 0
    max_depth_mm?: number;
    // 양수일 때만 필터 적용.
    // default: 0
    max_height_mm?: number;
    // 페이지당 1~100개.
    // default: 10
    limit?: number;
    // 페이지의 시작 위치(0부터).
    // default: 0
    offset?: number;
    // default: false
    include_ids?: boolean;
    // dimensions, source, paths, drawing, metadata, audit, all. 생략하거나 빈 배열이면 요약.
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
  assets?: Array<{
    [key: string]: unknown;
  }>;
  total?: number;
  limit?: number;
  offset?: number;
  // true이면 같은 필터로 offset에 이번 반환 건수를 더해 다음 페이지 조회.
  truncated?: boolean;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

## capture

### 17. capture\_01-conditioning\_pass

```txt
활성 Rhino 뷰의 카메라 경로를 따라 RGB·에지·깊이 PNG 및 카메라 기록 저장. 촬영 중 뷰가 바뀌며 전체 뷰 상태가 복원되지 않을 수 있음. 패스별 PNG 생성과 대상 가시성은 출력 파일에서 확인. 같은 출력 폴더를 재사용하면 기존 파일을 덮어쓰고 일부 이전 프레임이 남을 수 있음.
```

```ts
declare const tools: {
  mcp__rhino__capture_01_conditioning_pass(args: {
    // 카메라 경로를 담은 JSON 문자열. orbit은 center:[x,y,z], radius, height, 선택 start_deg·end_deg·lens·target_height. track은 cam0·cam1·target0·target1 좌표, 선택 lens. keyframes는 camera·target·선택 lens를 가진 keyframes 배열. type으로 경로 유형 지정. frames 생략 시 81, lens는 mm, 좌표는 문서 단위.
    shot: string;
    // 관리형은 먼저 Plan을 선택한 뒤 산출물 폴더 기준 상대 경로 사용(생략 시 conditioning). 독립 실행에서 생략 시 현재 작업 폴더.
    // default: ""
    out_dir?: string;
    // 짝수 픽셀.
    // default: 832
    width?: number;
    // 짝수 픽셀.
    // default: 480
    height?: number;
    // 쉼표로 구분한 rgb, edge, depth.
    // default: "rgb,edge,depth"
    passes?: string;
    // default: 16
    fps?: number;
    // 청크당 프레임 수.
    // default: 16
    chunk?: number;
    // 설치된 Rhino 디스플레이 모드 이름.
    // default: "Rendered"
    rgb_mode?: string;
    // 설치된 Rhino 디스플레이 모드 이름.
    // default: "Technical"
    edge_mode?: string;
    // false이면 가까울수록 밝게 표현.
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
  // executed는 모든 청크 실행 완료, partial은 청크 실행 중 오류.
  status?: string;
  frames_requested?: number;
  // 실행 완료 응답을 받은 청크에 포함된 프레임 수.
  frames_captured?: number;
  passes?: Array<string>;
  // [너비, 높이].
  resolution?: Array<number>;
  fps?: number;
  // 실패 청크의 프레임 범위와 메시지. 일부 출력 파일이 남을 수 있음.
  errors?: Array<unknown>;
  // 패스별 PNG와 doc.json, camera.json, zrange.csv, summary.json 저장 위치.
  out_dir?: string;
  // 계획 경로 전체 기록. 촬영이 일부만 끝나도 frames[].camera·target·lens_mm는 전체 경로 기준.
  camera_json?: string;
  videos?: {
    rgb?: string | null;
    [key: string]: unknown;
  };
  document?: {
    [key: string]: unknown;
  };
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 18. capture\_02-inspection

```txt
작업 화면을 유지하면서 여러 시점과 객체 범위를 한 PNG로 비교. 범위는 문서 표시 상태 기준이며 픽셀 가시성이나 가림은 판정하지 않는다. 그룹 자동 확장과 블록 배치·정의 필터는 지원하지 않는다.

표시 모드 이름·GUID는 inspect_03-get_document_context tool의 sections=["display_modes"]에서 조회. Wireframe은 곡선·와이어, Shaded는 면과 입체, Technical은 가려진 선을 포함한 선 표현 검토에 적합하다. 사용자 정의 래스터 모드도 선택할 수 있으며 이름이 중복되면 GUID를 사용한다.

최상위 모델 객체 GUID는 inspect_02-get_objects tool의 include_ids=true로 조회. 공통 object_ids를 지정한 뒤 views=[{"direction":"top","display_mode":"Technical"},{"direction":"iso_ne","display_mode":"Shaded"}]로 같은 대상을 평면과 사시에서 비교한다. 원본 뷰 방향에서 대상에 맞춰 확대하려면 공통 또는 타일별 object_ids와 views=[{"direction":"current","frame_objects":true}]를 사용한다. frame_objects를 생략한 current 타일은 원본 카메라 구도를 유지한다.

일부 타일이 실패해도 status=success일 수 있으므로 complete와 tiles를 함께 확인한다.
```

```ts
declare const tools: {
  mcp__rhino__capture_02_inspection(args: {
    // 타일 1..16개. direction: current(기본), top, bottom, front, back, left, right, iso_ne, iso_nw, iso_se, iso_sw, below_ne, below_nw, below_se, below_sw. display_mode: 설치된 모드 이름 또는 GUID. label: 최대 120자. object_ids: 블록 인스턴스를 제외한 최상위 객체 GUID 1..512개. 생략하거나 비우면 공통 범위 또는 문서 표시 상태를 사용한다.
    views: Array<{
      [key: string]: unknown;
    }>;
    // 타일당 128..2048픽셀. 결합 이미지 제한도 적용.
    // default: 640
    width?: number;
    // 타일당 128..2048픽셀. 결합 이미지 제한도 적용.
    // default: 480
    height?: number;
    // 1..뷰 개수. 생략 시 자동 격자.
    // default: null
    columns?: (number | null);
    // 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
    // default: ""
    expected_model_path?: string;
    // 활성화하지 않고 사용할 모델 뷰포트 GUID. Layout·Detail에서 작업 중일 때도 지정 가능.
    // default: ""
    model_view_id?: string;
    // 모든 타일에 적용할 최상위 객체 GUID 1..4096개. 블록 인스턴스 제외. 타일별 object_ids와 함께 지정할 수 없다.
    // default: null
    object_ids?: (Array<string> | null);
  }): Promise<CallToolResult<{
    status?: string;
    complete?: boolean;
    // 실패한 타일도 포함.
    tiles?: Array<{
      // 0부터 시작.
      index?: number;
      status?: string;
      direction?: string;
      // 성공한 타일에 실제로 적용된 모드.
      display_mode?: {
        name?: string;
        id?: string;
        [key: string]: unknown;
      };
      [key: string]: unknown;
    }>;
    // 저장에 실패해도 PNG는 전달될 수 있다.
    image_file?: {
      // saved일 때만 path 사용 가능.
      status?: string;
      // 프로젝트 기준 상대 경로. output_refs에는 이 문자열만 기록.
      path?: string;
      // plan은 Plan 산출물, connection은 연결 정리까지 유지되는 임시 파일.
      lifetime?: string;
      bytes?: number;
      sha256?: string;
      [key: string]: unknown;
    };
    message?: string;
    error_code?: string;
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 19. capture\_03-current\_view

```txt
현재 Rhino 모델 뷰포트를 화면 색과 선 표현으로 PNG 캡처. 문서의 PrintDisplay 설정은 유지한다. 대상 지정은 실제 선택과 카메라를 바꾸고 isolate와 display_mode도 작업 화면에 적용된다.

표시 모드 이름·GUID는 inspect_03-get_document_context tool의 sections=["display_modes"]에서 조회. 작업 화면을 유지하면서 여러 방향이나 모드를 비교하려면 capture_02-inspection tool을 사용한다. 격리는 Rhino Unisolate로 해제할 수 있다. 잠긴 주변 객체는 격리 중에도 보일 수 있으며 선택과 카메라 상태는 별도로 확인한다.
```

```ts
declare const tools: {
  mcp__rhino__capture_03_current_view(args: {
    // 선택·확대할 대상 ID를 하나 이상 지정. 생략 시 현재 구도로 캡처.
    // default: null
    target_ids?: (Array<string> | null);
    // object, group, block, holon. block에는 배치 객체 ID 사용. object 이외에는 target_ids 필요.
    // default: "object"
    target_kind?: string;
    // target_ids가 필요하며 확대 전에 격리.
    // default: false
    isolate?: boolean;
    // 1..100.
    // default: 75
    scale_percent?: number;
    // 이미지 크기와 픽셀 기준 토큰 추정치 포함.
    // default: false
    include_usage?: boolean;
    // 설치된 래스터 모드 이름 또는 GUID.
    // default: ""
    display_mode?: string;
    // 주변 객체에도 최대 200개 표시하므로 화면을 가릴 수 있다.
    // default: false
    labels?: boolean;
    // 레이블 확장 깊이 1..8.
    // default: 1
    depth?: number;
    // 128..2048픽셀. height와 함께 지정하고 scale_percent=100 사용.
    // default: null
    width?: (number | null);
    // 128..2048픽셀. width와 함께 지정하고 scale_percent=100 사용.
    // default: null
    height?: (number | null);
    // 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
    // default: ""
    expected_model_path?: string;
  }): Promise<CallToolResult<{
    // null이면 뷰 변경 적용을 확인하지 못한 상태.
    mutation_applied?: boolean | null;
    // true면 현재 Rhino 상태를 확인한 뒤 다음 작업을 결정.
    requires_reconciliation?: boolean;
    // validate, select, isolate, verify_selection, zoom_selected, redraw 중 실패한 단계.
    failed_stage?: string;
    view_change?: {
      selection_changed?: boolean | null;
      isolated?: boolean | null;
      // 선택 확대 또는 대체 경계 확대를 완료하면 true.
      zoom_selected?: boolean | null;
      // selected는 기본 선택 확대, bounding_box는 기본 확대 실패 후 대상 경계로 확대한 경우.
      zoom_method?: "selected" | "bounding_box";
      display_mode_changed?: boolean | null;
      // 격리 가시성만 복구. 카메라와 선택은 별도로 확인.
      restore_visibility_command?: string;
      [key: string]: unknown;
    };
    focus_observation?: {
      target_count?: number;
      // 문서 단위의 대상 합집합 경계.
      target_bounds?: {
        // [x, y, z] 순서.
        // minItems: 3
        // maxItems: 3
        min?: Array<number>;
        // [x, y, z] 순서.
        // minItems: 3
        // maxItems: 3
        max?: Array<number>;
        [key: string]: unknown;
      };
      target_bounds_error?: string;
      zoom_extents_selected?: boolean | null;
      zoom_bounding_box?: boolean | null;
      before_zoom?: {
        viewport_id?: string;
        parallel_projection?: boolean;
        // 문서 단위의 [x, y, z].
        // minItems: 3
        // maxItems: 3
        camera_location?: Array<number>;
        // 문서 단위의 [x, y, z].
        // minItems: 3
        // maxItems: 3
        camera_target?: Array<number>;
        // [left, right, bottom, top, near, far] 순서.
        // minItems: 6
        // maxItems: 6
        frustum?: Array<number>;
        observation_error?: string;
        [key: string]: unknown;
      };
      after_failure?: {
        viewport_id?: string;
        parallel_projection?: boolean;
        // 문서 단위의 [x, y, z].
        // minItems: 3
        // maxItems: 3
        camera_location?: Array<number>;
        // 문서 단위의 [x, y, z].
        // minItems: 3
        // maxItems: 3
        camera_target?: Array<number>;
        // [left, right, bottom, top, near, far] 순서.
        // minItems: 6
        // maxItems: 6
        frustum?: Array<number>;
        observation_error?: string;
        [key: string]: unknown;
      };
      [key: string]: unknown;
    };
    // 저장과 PNG 전달은 별개로 확인.
    image_file?: {
      // saved일 때만 path 사용 가능.
      status?: string;
      // 프로젝트 기준 상대 경로. output_refs에는 이 문자열만 기록.
      path?: string;
      // plan은 Plan 산출물, connection은 연결 정리까지 유지되는 임시 파일.
      lifetime?: string;
      bytes?: number;
      sha256?: string;
      [key: string]: unknown;
    };
    message?: string;
    error_code?: string;
    next_step_guide?: string;
    status?: string;
    [key: string]: unknown;
  }>>;
};
```

### 20. capture\_04-defined\_view

```txt
저장된 Named View 또는 Layout 용지를 PNG로 캡처. 대상 이름·ID는 inspect_03-get_document_context tool에서 조회한다.

Named View는 저장된 카메라를 사용하며 표시 모드 선택은 capture_02-inspection tool 참고. Layout은 용지·Detail의 기존 모드와 인쇄 색·선폭으로 출력하고 PrintDisplay는 유지한다. Layout에는 픽셀 크기·display_mode를 지정할 수 없고 Detail 레이블도 지원하지 않는다. 인쇄 대상이 없으면 빈 PNG도 정상이다.

PNG 전달과 파일 저장은 별개다. 사용량 추정·경고는 별도 text content로 전달한다.
```

```ts
declare const tools: {
  mcp__rhino__capture_04_defined_view(args: {
    // named_view 또는 layout.
    target_kind: string;
    // 기존 이름 또는 ID. 이름은 대소문자 무시 기준으로 하나만 일치해야 한다.
    target: string;
    // 1..100 범위의 상한. 전달 용량에 맞춰 더 작아질 수 있다.
    // default: 75
    scale_percent?: number;
    // 이미지 크기와 픽셀 기준 토큰 추정치 포함.
    // default: false
    include_usage?: boolean;
    // Named View 전용. 생략 시 Shaded. 설치된 래스터 모드 이름 또는 GUID.
    // default: ""
    display_mode?: string;
    // 최대 200개. 주변 레이블과 겹칠 수 있다.
    // default: false
    labels?: boolean;
    // 레이블 깊이 1..8.
    // default: 1
    depth?: number;
    // Named View 전용. 128..2048픽셀. height와 함께 지정하고 scale_percent=100 사용.
    // default: null
    width?: (number | null);
    // Named View 전용. 128..2048픽셀. width와 함께 지정하고 scale_percent=100 사용.
    // default: null
    height?: (number | null);
    // 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
    // default: ""
    expected_model_path?: string;
  }): Promise<CallToolResult<{
    image_file?: {
      // saved일 때만 path 사용 가능.
      status?: string;
      // 프로젝트 기준 상대 경로. output_refs에는 이 문자열만 기록.
      path?: string;
      // plan은 Plan 산출물, connection은 연결 정리까지 유지되는 임시 파일.
      lifetime?: string;
      bytes?: number;
      sha256?: string;
      [key: string]: unknown;
    };
    message?: string;
    error_code?: string;
    next_step_guide?: string;
    status?: string;
    [key: string]: unknown;
  }>>;
};
```

## connect

### 21. connect\_01-list\_up

CoS

```txt
열린 Rhino 문서와 이 클라이언트의 연결·시작 요청 조회. 연결된 문서도 targets에 표시된다. 연결하려면 같은 대상의 host_id와 저장된 model_path를 connect_02-session tool에 전달한다. 이후 일반 호출은 selected_connection_id의 연결을 사용한다.
```

beyond

```txt
열린 Rhino 문서와 이 클라이언트의 연결·시작 요청 조회. 연결하려면 같은 대상의 host_id와 저장된 model_path를 connect_02-session tool에 전달한다.
```

```ts
declare const tools: {
  mcp__rhino__connect_01_list_up(args: {}): Promise<CallToolResult<{
    instructions?: string;
    targets?: Array<{
      connection_id?: string | null;
      host_id?: string | null;
      // ready면 일반 작업 가능. recovering·unconfirmed이면 이전 실행 결과부터 확인.
      state?: string;
      reason?: string;
      model_path?: string | null;
      model_filename?: string | null;
      // 독립 연결 슬롯. 같은 폴더의 모델은 DB와 산출물 루트를 공유한다.
      slot?: string | null;
      pid?: number | null;
      // 연결 단위 임시 작업 폴더.
      artifact_dir?: string | null;
      in_flight?: boolean;
      [key: string]: unknown;
    }>;
    connections?: Array<{
      connection_id?: string | null;
      host_id?: string | null;
      // ready면 일반 작업 가능. recovering·unconfirmed이면 이전 실행 결과부터 확인.
      state?: string;
      reason?: string;
      model_path?: string | null;
      model_filename?: string | null;
      // 독립 연결 슬롯. 같은 폴더의 모델은 DB와 산출물 루트를 공유한다.
      slot?: string | null;
      pid?: number | null;
      // 연결 단위 임시 작업 폴더.
      artifact_dir?: string | null;
      in_flight?: boolean;
      [key: string]: unknown;
    }>;
    starts?: Array<{
      // 같은 시작 요청을 조회할 때 재사용.
      request_id?: string;
      state?: string;
      // 시작 요청 모델의 절대 경로.
      model_path?: string;
      connection_id?: string | null;
      reason?: string;
      [key: string]: unknown;
    }>;
    selected_connection_id?: string | null;
    message?: string;
    error_code?: string;
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 22. connect\_02-session

CoS

```txt
열린 Rhino 문서에 연결하거나 작업 대상 전환. connect_01-list_up tool의 targets에서 같은 대상의 host_id와 model_path를 가져온다. 유지 중인 연결도 다시 선택할 수 있으며, 선택 후 일반 호출은 그 연결을 사용한다.
```

beyond

```txt
열린 Rhino 문서에 연결하고 해당 문서의 연결 ID를 반환.
```

```ts
declare const tools: {
  mcp__rhino__connect_02_session(args: {
    host_id: string;
    model_path: string;
  }): Promise<CallToolResult<{
    // beyond: model_path와 connection_id를 현재 대화의 변수에 함께 저장하고, 이 문서의 후속 호출마다 connection_id를 전달한다. 성공 응답의 message에도 이 안내를 제공.
    connection_id?: string | null;
    host_id?: string | null;
    // ready면 일반 작업 가능. recovering·unconfirmed이면 이전 실행 결과부터 확인.
    state?: string;
    reason?: string;
    model_path?: string | null;
    model_filename?: string | null;
    // 독립 연결 슬롯. 같은 폴더의 모델은 DB와 산출물 루트를 공유한다.
    slot?: string | null;
    pid?: number | null;
    // 연결 단위 임시 작업 폴더.
    artifact_dir?: string | null;
    in_flight?: boolean;
    message?: string;
    error_code?: string;
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 23. connect\_03-start\_session

CoS

```txt
저장된 모델을 새 Rhino 창에서 열고 연결. model_path와 시작 시도를 식별하는 request_id 필요.
```

beyond

```txt
저장된 모델을 새 Rhino 창에서 열고 해당 문서의 연결 ID를 반환.
```

```ts
declare const tools: {
  mcp__rhino__connect_03_start_session(args: {
    // 저장된 로컬 .3dm 파일의 절대 경로.
    model_path: string;
    // 시작 시도마다 고유한 값. 지연되거나 결과가 불확실하면 같은 값으로 다시 조회.
    // minLength: 1
    // maxLength: 128
    request_id: string;
  }): Promise<CallToolResult<{
    // beyond: model_path와 connection_id를 현재 대화의 변수에 함께 저장하고, 이 문서의 후속 호출마다 connection_id를 전달한다. 성공 응답의 message에도 이 안내를 제공.
    connection_id?: string | null;
    host_id?: string | null;
    // ready면 일반 작업 가능. recovering·unconfirmed이면 이전 실행 결과부터 확인.
    state?: string;
    reason?: string;
    model_path?: string | null;
    model_filename?: string | null;
    // 독립 연결 슬롯. 같은 폴더의 모델은 DB와 산출물 루트를 공유한다.
    slot?: string | null;
    pid?: number | null;
    // 연결 단위 임시 작업 폴더.
    artifact_dir?: string | null;
    in_flight?: boolean;
    // 대기·실패 상태는 connect_01-list_up tool의 starts에서 확인.
    request_id?: string;
    message?: string;
    error_code?: string;
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 24. connect\_04-disconnect

CoS

```txt
선택한 연결 해제. Rhino 창과 문서는 계속 열린 상태로 유지.
```

beyond

```txt
지정한 연결 해제. Rhino 창과 문서는 계속 열린 상태로 유지.
```

```ts
declare const tools: {
  mcp__rhino__connect_04_disconnect(args: {}): Promise<CallToolResult<{
    connection_id?: string;
    // 종료할 Rhino 창은 이 PID와 model_path를 함께 대조해 식별.
    pid?: number | null;
    // 저장·종료 전에 현재 문서 경로와 대조.
    model_path?: string | null;
    worker_closed?: boolean;
    rhino_closed?: boolean;
    // Rhino가 연결 해제를 확인한 경우 true.
    released?: boolean;
    // 잠금이 남은 경우 그 사유 포함.
    reason?: string;
    message?: string;
    error_code?: string;
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 25. connect\_05-close\_session

CoS

```txt
선택한 Rhino 문서의 저장 완료를 확인한 뒤 Rhino를 정상 종료.
```

beyond

```txt
지정한 연결의 Rhino 문서 저장을 확인한 뒤 Rhino를 정상 종료. 결과 재조회에는 원래의 두 ID를 사용한다.
```

```ts
declare const tools: {
  mcp__rhino__connect_05_close_session(args: {
    // 종료 시도마다 고유한 값. 지연되거나 결과가 불확실하면 같은 값으로 재호출해 기존 결과를 조회.
    // minLength: 1
    // maxLength: 128
    request_id: string;
  }): Promise<CallToolResult<{
    request_id?: string;
    connection_id?: string;
    // 프로세스 시작 정보까지 대조한 Rhino PID.
    pid?: number;
    // 저장·종료 대상의 절대 경로.
    model_path?: string;
    // completed는 저장, Rhino·worker 종료, 연결 소유권 해제를 모두 확인한 상태.
    status?: "closing" | "completed" | "rejected" | "save_failed" | "unconfirmed";
    stage?: string;
    // Save 완료와 같은 문서의 modified=false를 모두 확인.
    saved?: boolean;
    modified_before?: boolean;
    modified_after?: boolean;
    // script_03-get_execution tool에서 저장 결과를 조회할 때 사용.
    save_request_id?: string;
    rhino_closed?: boolean;
    worker_closed?: boolean;
    released?: boolean;
    reason?: string;
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

## context

### 26. context\_01-get\_policy

```txt
Almond 도구와 기술 참고 자료 조회. policy를 생략하면 공개 도구 목록과 참고 자료 종류를 반환.

metadata는 User Text 등 객체 메타데이터 키 사전, rhino_scripting은 내장 스크립팅 자료, rhinocode는 코드·명령 실행 지침.

같은 guide_version에서 이미 읽은 지침은 재사용할 수 있다.
```

```ts
declare const tools: {
  mcp__rhino__context_01_get_policy(args: {
    // 생략하거나 비워 두면 basic(공개 도구 목록). 참고 자료 종류는 available_policies 참고.
    // default: ""
    policy?: "" | "basic" | "metadata" | "rhino_scripting" | "rhinocode";
  }): Promise<CallToolResult<{
    status?: string;
    // 같은 지침인지 비교할 수 있는 버전 해시.
    guide_version?: string;
    text?: string;
    source_refs?: Array<{
      path?: string;
      sha256?: string;
      [key: string]: unknown;
    }>;
    tools?: Array<string>;
    selected_policy?: string;
    available_policies?: {
      [key: string]: string;
    };
    policy?: {
      [key: string]: unknown;
    };
    scripting_skill?: {
      name?: string;
      sources?: Array<{
        // 저장소 상대 경로. src/mcp/로 시작.
        path?: string;
        // 줄바꿈 등을 정규화한 출처의 해시.
        sha256?: string;
        text?: string;
        [key: string]: unknown;
      }>;
      [key: string]: unknown;
    };
    message?: string;
    error_code?: string;
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 27. context\_04-get\_project\_info

```txt
연결된 Rhino 문서와 프로젝트 작업 정보 조회.

sections에서 필요한 항목을 선택한다. locations·runtime만 요청하면 Rhino 문서를 직접 관찰하지 않는다. named_views와 layouts는 각각 최대 128개이며 include_ids와 관계없이 ID를 포함한다.

project.worksession_files는 활성 문서를 제외한 현재 Worksession 첨부 파일이다. 이 목록과 DB 등록 목록인 project.files는 별개다. Worksession 첨부·해제로 DB 등록은 바뀌지 않는다. 파일 등록과 설명 갱신은 context_05-upsert_project_file tool을 사용한다. Phase와 Scene에는 등록 파일명을 지정한다.

후속 호출에 쓸 Plan·Step ID가 필요하면 include_ids=true. 프로젝트 내부 경로는 project_root를 기준으로 읽는다.
```

```ts
declare const tools: {
  mcp__rhino__context_04_get_project_info(args: {
    // project, document, named_views, layouts, layer_tree, locations, runtime. 생략 시 runtime을 제외한 전체.
    // default: null
    sections?: (Array<string> | null);
    // default: false
    include_ids?: boolean;
    // 등록 파일 페이지 크기. 정수 1..500.
    // default: 50
    files_limit?: number;
    // 등록 파일 페이지의 시작 위치. 0 이상의 정수.
    // default: 0
    files_offset?: number;
  }): Promise<CallToolResult<{
    named_views?: Array<{
      name?: string;
      id?: string;
      [key: string]: unknown;
    }> | null;
    layouts?: Array<{
      name?: string;
      id?: string;
      [key: string]: unknown;
    }> | null;
    layer_tree?: string | null;
    status?: string;
    warnings?: Array<string>;
    project?: {
      // 프로젝트 파일 도구에서 상대 경로를 해석하는 기준 디렉터리의 절대 경로.
      project_root?: string;
      file_name?: string | null;
      file_path?: string | null;
      // 현재 Rhino 문서가 이 연결에서 선택한 모델과 일치하는지 확인.
      is_bound_document?: boolean;
      files?: Array<{
        file_name?: string;
        description?: string | null;
        [key: string]: unknown;
      }>;
      worksession_files?: Array<{
        file_name?: string;
        // 다른 드라이브의 파일은 절대 경로.
        file_path?: string;
        [key: string]: unknown;
      }> | null;
      files_page?: {
        total?: number;
        limit?: number;
        offset?: number;
        // true면 같은 조건에서 files_offset=offset+limit으로 다음 페이지 조회.
        truncated?: boolean;
        [key: string]: unknown;
      };
      [key: string]: unknown;
    };
    document?: {
      // include_ids=true일 때 포함.
      runtime_serial_number?: number | null;
      units?: string | null;
      // 현재 문서 단위.
      absolute_tolerance?: number | null;
      angle_tolerance_radians?: number | null;
      modified?: boolean | null;
      object_count?: number | null;
      // 활성 레이어만 집계.
      layer_count?: number | null;
      [key: string]: unknown;
    };
    locations?: {
      plan_id?: string;
      step_id?: string;
      // 0은 첫 실행 전 기록.
      loop_no?: number;
      // 선택한 회차가 최신 회차보다 이전이면 true.
      read_only?: boolean;
      // 프로젝트 기준 상대 경로.
      plan_artifact_dir?: string | null;
      // 선택된 Plan·Loop의 산출물 폴더.
      artifact_dir?: string | null;
      // 연결된 모델이 공유하는 DB 경로.
      database?: string;
      path_rule?: string;
      artifact_rule?: string;
      [key: string]: unknown;
    };
    runtime?: {
      slot?: string;
      port?: number;
      session_dir?: string;
      scratch_root?: string;
      // 연결 시 기록한 Rhino 프로세스의 TEMP 경로.
      rhino_temp_at_attach?: string | null;
      rhino_temp_note?: string;
      // 현재 worker의 Python 실행 파일 경로.
      python_executable?: string;
      attachment?: string;
      rhinocode?: {
        // 현재 연결에서 허용된 실행 언어를 사용할 수 있으면 true.
        available?: boolean;
        executable?: string;
        // include_ids=true일 때 포함.
        pipe_id?: string;
        // RhinoCode 인스턴스의 원본 processVersion.
        version?: unknown;
        languages?: Array<string>;
        message?: string;
        [key: string]: unknown;
      };
      [key: string]: unknown;
    };
    next_step_guide?: string;
    message?: string;
    error_code?: string;
    [key: string]: unknown;
  }>>;
};
```

### 28. context\_05-upsert\_project\_file

```txt
프로젝트 파일 카탈로그에 모델 파일을 등록하거나 설명을 갱신. 파일명 비교는 Windows 기준이며 수정 시 기존 표기를 유지한다. Rhino 문서 열기나 Worksession 첨부는 별도 작업이다.

등록 목록은 context_04-get_project_info tool의 project.files에서 조회한다. Phase와 Scene에는 목록에 있는 파일명을 사용한다.
```

```ts
declare const tools: {
  mcp__rhino__context_05_upsert_project_file(args: {
    // 폴더를 뺀 모델 파일명. 프로젝트 안에서 고유해야 한다.
    file_name: string;
    // 생략하거나 null이면 기존 설명 유지. 빈 문자열로 삭제.
    // default: null
    description?: (string | null);
  }): Promise<CallToolResult<{
    status?: string;
    file_name?: string;
    description?: string | null;
    message?: string;
    error_code?: string;
    [key: string]: unknown;
  }>>;
};
```

## diagram

### 29. diagram\_01-get

```txt
다이어그램 자산의 등록 정보와 원본 파일 상태 조회. 파일이 없는 항목도 조회 가능.
```

```ts
declare const tools: {
  mcp__rhino__diagram_01_get(args: {
    // diagram_02-list tool 또는 diagram_04-search tool에서 얻은 ID. 대소문자와 공백까지 그대로 사용.
    asset_id: string;
    // true면 추가 식별자 포함. 입력 asset_id는 응답에 반복하지 않는다.
    // default: false
    include_ids?: boolean;
    // dimensions, drawing, metadata, source, paths, audit, all. 생략하거나 비우면 요약. all은 다른 그룹 밖의 등록 필드도 포함.
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
  status?: string;
  asset?: {
    name?: string;
    file_available?: boolean;
    [key: string]: unknown;
  };
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 30. diagram\_02-list

```txt
사람·나무·기호 등 등록된 2D 벡터·CAD 다이어그램 조회. 파일이 없는 항목도 포함한다. 상세 정보는 diagram_01-get tool, 키워드·치수 검색은 diagram_04-search tool.
```

```ts
declare const tools: {
  mcp__rhino__diagram_02_list(args: {
    // 분류값 전체 일치. 대소문자 무시. 비워 두면 전체 조회.
    // default: ""
    category?: string;
    // 1..50으로 보정.
    // default: 20
    limit?: number;
    // 음수는 0으로 보정.
    // default: 0
    offset?: number;
    // default: false
    include_ids?: boolean;
    // dimensions, drawing, metadata, source, paths, audit, all. 생략하거나 비우면 요약.
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
  // include_ids=true일 때 포함.
  library_id?: string;
  assets?: Array<{
    [key: string]: unknown;
  }>;
  total?: number;
  offset?: number;
  limit?: number;
  next_offset?: number | null;
  purpose?: string;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 31. diagram\_03-place

```txt
SVG·DWG·DXF 다이어그램을 Rhino 문서에 블록 인스턴스로 배치. requires_reconciliation=true면 문서에서 실제 배치를 확인한 뒤 다음 작업을 결정한다.
```

```ts
declare const tools: {
  mcp__rhino__diagram_03_place(args: {
    // 기존 라이브러리 자산 ID. 모르는 경우 include_ids=true로 목록·검색 결과에서 확인.
    asset_id: string;
    // 현재 Rhino 문서 단위.
    // default: 0
    x?: number;
    // 현재 Rhino 문서 단위.
    // default: 0
    y?: number;
    // 현재 Rhino 문서 단위.
    // default: 0
    z?: number;
    // 월드 Z축 기준.
    // default: 0
    rotation_degrees?: number;
    // 양수인 균일 축척. 1은 문서 단위로 변환한 자산의 원래 크기.
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
  status?: string;
  asset_id?: string;
  // 삽입한 최상위 블록 GUID. inspect_02-get_objects tool 또는 Scene 구성원 입력에 재사용.
  object_guid?: string;
  definition_created?: boolean;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  // unknown·partial이면 문서에 변경이 남아 있을 수 있음.
  mutation_state?: string;
  // true이면 Rhino 문서의 실제 변경 상태를 확인. 자동 재실행 금지.
  requires_reconciliation?: boolean;
  // null이면 변경 적용 여부 미확인.
  mutation_applied?: boolean | null;
  [key: string]: unknown;
};
```

### 32. diagram\_04-search

```txt
등록된 2D 다이어그램을 키워드·분류·최대 치수로 검색. 파일이 없는 자산도 포함한다. 상세 정보와 파일 상태는 diagram_01-get tool에서 조회한다.
```

```ts
declare const tools: {
  mcp__rhino__diagram_04_search(args: {
    // 여러 검색어는 OR로 결합. 비워 두면 키워드 조건 없이 검색.
    // default: ""
    query?: string;
    // 분류값 전체 일치. 대소문자 무시. 비워 두면 전체 검색.
    // default: ""
    category?: string;
    // 0 이하이면 치수 필터 해제.
    // default: 0
    max_width_mm?: number;
    // 0 이하이면 치수 필터 해제. 등록 치수는 추정치일 수 있다.
    // default: 0
    max_depth_mm?: number;
    // 0 이하이면 치수 필터 해제.
    // default: 0
    max_height_mm?: number;
    // 1..50으로 보정.
    // default: 10
    limit?: number;
    // 음수는 0으로 보정. 다음 페이지에도 같은 필터 사용.
    // default: 0
    offset?: number;
    // default: false
    include_ids?: boolean;
    // dimensions, drawing, metadata, source, paths, audit, all. 생략하거나 비우면 요약. 일부 세부 값은 포함되지 않을 수 있다.
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
  assets?: Array<{
    [key: string]: unknown;
  }>;
  total?: number;
  offset?: number;
  limit?: number;
  next_offset?: number | null;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

## drawing

### 33. drawing\_01-apply\_style

```txt
도면 레시피의 레이어 계층과 색·출력색·출력 선 두께·선종류를 Rhino 문서에 적용. 같은 경로의 기존 레이어도 갱신한다. 같은 이름의 선종류는 기존 정의를 재사용하고 새 선종류는 Almond 선종 매니페스트에서 가져온다. 적용 범위는 레이어와 속성이다.

변경 전 전용 Undo record를 확보하고 실패 시 해당 record를 복구한다. mutation_state는 none·completed·rolled_back·unknown. requires_reconciliation=true면 재시도 전에 실제 문서 상태를 확인한다.

레시피의 review_preparation.print_display가 true이면 적용 성공 시 PrintDisplay 설정 명령을 안내한다.
```

```ts
declare const tools: {
  mcp__rhino__drawing_01_apply_style(args: {
    // drawing_05-list_recipes tool 또는 drawing_02-get_recipe tool에서 확인. 생략 시 파일명 순으로 처음 로드된 레시피 적용.
    // default: ""
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
  status?: string;
  recipe_id?: string;
  layers?: Array<{
    // inspect_02-get_objects tool의 layer_paths 필터에 재사용 가능.
    path?: string;
    role?: string;
    layer_index?: number;
    plot_weight_mm?: number;
    linetype?: string;
    [key: string]: unknown;
  }>;
  review_preparation?: {
    status?: string;
    // 이 연결의 Rhino PID와 문서 경로로 실행 파이프 확인.
    message?: string;
    cli?: {
      program?: string;
      // 실행 파이프 확인에 사용할 인수.
      discovery_arguments?: Array<string>;
      arguments_template?: Array<string>;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  // unknown·partial이면 문서에 변경이 남아 있을 수 있음.
  mutation_state?: string;
  // true이면 Rhino 문서의 실제 변경 상태를 확인. 자동 재실행 금지.
  requires_reconciliation?: boolean;
  [key: string]: unknown;
};
```

### 34. drawing\_02-get\_recipe

```txt
도면 스타일 레시피 조회. field_groups=["scales","parameters"]로 권장 축척·레이어·출력 설정을 확인한 뒤 같은 recipe_id를 drawing_01-apply_style tool에 전달한다.
```

```ts
declare const tools: {
  mcp__rhino__drawing_02_get_recipe(args: {
    // 이미 확인한 레시피 ID 또는 drawing_05-list_recipes tool에서 include_ids=true로 조회한 ID.
    recipe_id: string;
    // default: false
    include_ids?: boolean;
    // scales, parameters, source, audit, all. 생략하거나 비우면 요약.
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
  status?: string;
  recipe?: {
    name?: string;
    description?: string;
    projection?: {
      type?: string;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 35. drawing\_04-import\_hatches

```txt
등록된 PAT 자산의 해치 패턴 정의를 Rhino 문서에 가져오기. 같은 이름이 있으면 기존 정의 재사용. 적용 범위는 해치 패턴 정의.
```

```ts
declare const tools: {
  mcp__rhino__drawing_04_import_hatches(args: {
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
  status?: string;
  // 새로 가져온 패턴과 재사용한 기존 패턴 모두 포함.
  patterns?: Array<string>;
  message?: string;
  error_trace?: unknown;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 36. drawing\_05-list\_recipes

```txt
로드된 도면 스타일 레시피 목록. include_ids=true로 얻은 recipe_id는 drawing_02-get_recipe tool과 drawing_01-apply_style tool에서 사용.
```

```ts
declare const tools: {
  mcp__rhino__drawing_05_list_recipes(args: {
    // default: false
    include_ids?: boolean;
    // scales, parameters, source, audit, all. 생략하거나 비우면 요약.
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
  total?: number;
  recipes?: Array<{
    recipe_id?: string;
    name?: string | null;
    description?: string | null;
    projection?: string | null;
    // 축척 1:N의 분모 N
    recommended_scales?: Array<string>;
    [key: string]: unknown;
  }>;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 37. drawing\_06-generate\_plan\_section

```txt
활성 모델이나 Worksession 첨부 파일의 클리핑 평면에서 단면선·가시 입면선·해치를 생성. Update는 저장 위치에서 다시 계산해 수동 편집을 교체할 수 있고, Move는 GUID와 수동 편집을 유지한 채 원점만 이동.

일부 완료나 취소 뒤에도 완료된 도면이 남을 수 있다. 변경 실패 시 객체·속성·레이어의 복구를 각각 시도하고 recovery.attempts에 기록. tracked_changes_restored는 추적한 변경의 복구 결과다. mutation_state가 partial 또는 unknown이고 requires_reconciliation=true이면 자동 재시도 금지. 실제 도면이나 Undo 결과 확인.
```

```ts
declare const tools: {
  mcp__rhino__drawing_06_generate_plan_section(args: {
    // Create: 생성 또는 교체. Update: 저장 위치에서 재생성. Move: 기존 도면의 평행이동.
    operation: "Create" | "Update" | "Move";
    // 활성 모델 또는 Worksession 첨부 파일의 클리핑 평면 GUID. 최소 1개, 중복은 한 번만 처리.
    clipping_ids: Array<string>;
    // 클리핑 GUID별 절대 도면 원점 [x,y] 또는 [x,y,z], 문서 단위. Create에서 선택, Move에서 모든 GUID에 필수, Update에서 생략.
    // default: null
    points?: ({
      [key: string]: Array<(number | number)>;
    } | null);
    // 원본 단면 스타일의 채움과 형상 조건에 따라 해치 생성
    // default: true
    hatch?: boolean;
    // 입면 투영에서 작은 상세 보호
    // default: false
    small_details?: boolean;
    // 가까운 입면선 두께(mm). 양수, far_width 이상.
    // default: 0.09
    near_width?: (number | number);
    // 먼 입면선 두께(mm). 양수, near_width 이하.
    // default: 0.04
    far_width?: (number | number);
    // 가까운 입면선 농도(%). 0..100, far_dark 이상.
    // default: 80.0
    near_dark?: (number | number);
    // 먼 입면선 농도(%). 0..100, near_dark 이하.
    // default: 45.0
    far_dark?: (number | number);
    // Worksession 첨부 형상 포함. Create에서 생략하면 활성 모델만, Update에서 생략하면 저장된 설정 사용. Move에는 적용되지 않음.
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
  // success, partial, cancelled, error
  status?: string;
  // completed, partial, cancelled, failed
  drawing_status?: string;
  mutation_state?: string;
  requires_reconciliation?: boolean;
  // 복구가 필요했던 클리핑별 오류와 보상 내역
  recovery?: Array<{
    clipping_id?: string;
    // 복구 시도 전 최초 변경 실패 원문
    error?: string;
    // 추적한 변경에 대한 보상 결과. 성공해도 원자적 롤백은 보장되지 않음.
    recovery?: {
      // 보상 실패는 partial, 미확인 변경 가능성이 남으면 unknown
      mutation_state?: string;
      requires_reconciliation?: boolean;
      // 추적한 변경에 대한 모든 보상 시도의 성공 여부
      tracked_changes_restored?: boolean;
      attempts?: Array<{
        action?: string;
        // 복구 대상 객체·레이어·기록
        target?: string;
        // restored 또는 failed
        status?: string;
        error?: string;
        [key: string]: unknown;
      }>;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  }>;
  result?: {
    status?: string;
    // 중복을 제외한 클리핑 요청 수
    requested?: number;
    completed?: number;
    requires_reconciliation?: boolean;
    results?: Array<{
      clipping_id?: string;
      name?: string | null;
      status?: string;
      // 생성·갱신·이동한 도면 객체의 GUID
      object_ids?: Array<string>;
      // 원점과 축으로 표현한 실제 배치 평면
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
      // Create·Update에서 실제 계산에 사용한 추출 조건
      extraction?: {
        // 계산에 사용한 원본 레이어 전체 경로
        layers?: Array<string>;
        source_object_count?: number;
        include_hidden?: boolean;
        include_locked?: boolean;
        // Worksession 첨부 형상을 계산 범위에 허용했는지 표시
        include_attachments?: boolean;
        [key: string]: unknown;
      };
      // 계산 단계와 제외·정리한 형상에 대한 기록
      report?: {
        [key: string]: unknown;
      };
      error?: string;
      // 추적한 변경에 대한 보상 결과. 성공해도 원자적 롤백은 보장되지 않음.
      recovery?: {
        // 보상 실패는 partial, 미확인 변경 가능성이 남으면 unknown
        mutation_state?: string;
        requires_reconciliation?: boolean;
        // 추적한 변경에 대한 모든 보상 시도의 성공 여부
        tracked_changes_restored?: boolean;
        attempts?: Array<{
          action?: string;
          // 복구 대상 객체·레이어·기록
          target?: string;
          // restored 또는 failed
          status?: string;
          error?: string;
          [key: string]: unknown;
        }>;
        [key: string]: unknown;
      };
      [key: string]: unknown;
    }>;
    [key: string]: unknown;
  };
  message?: string;
  error_code?: string;
  [key: string]: unknown;
};
```

## grasshopper

### 38. grasshopper\_01-get\_logic

```txt
색인된 Grasshopper 로직에서 물리 관련 컴포넌트, 설명, 메타데이터를 추출해 조회. JSON만 있는 항목은 메타데이터만 제공. 구성·연결 관계의 완전성과 실행 가능성은 별도 확인.
```

```ts
declare const tools: {
  mcp__rhino__grasshopper_01_get_logic(args: {
    // 확장자를 뺀 파일명. grasshopper_03-list_library tool의 logic_names 사용 가능.
    logic_id: string;
    // 추가 식별자 포함. 입력 logic_id는 반복하지 않음.
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
  file_name?: string;
  components?: Array<{
    name?: string;
    category?: string;
    descriptions?: Array<string>;
    [key: string]: unknown;
  }>;
  all_descriptions?: Array<string>;
  metadata?: {
    [key: string]: unknown;
  };
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 39. grasshopper\_02-list\_capsules

```txt
등록된 Grasshopper 캡슐의 기능과 실행 감사 상태를 조회. 포트와 ID는 grasshopper_04-run_definition tool의 입력에 사용. 감사 상태와 정의 파일의 존재·실행 성공은 별개.
```

```ts
declare const tools: {
  mcp__rhino__grasshopper_02_list_capsules(args: {
    // analyze, generate, form_find, aggregate. 대소문자 구분 없음.
    // default: ""
    capability?: string;
    // default: false
    audited_only?: boolean;
    // capsule_id 포함. all과 별도 지정.
    // default: false
    include_ids?: boolean;
    // ports, definition, source, paths, audit, all. 생략·빈 배열이면 요약.
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
  total?: number;
  offset?: number;
  limit?: number;
  next_offset?: number | null;
  capsules?: Array<{
    // audited=true인 캡슐을 grasshopper_04-run_definition tool에 지정
    capsule_id?: string;
    capability?: string;
    structure_type?: string | null;
    // 캡슐 라이브러리 기준 정의 파일명
    definition_file?: string;
    title?: string;
    audited?: boolean;
    // 타입·단위·필수 여부는 input_ports 참조
    inputs?: Array<string>;
    input_ports?: Array<{
      // grasshopper_04-run_definition tool에서 inputs의 키로 사용
      name?: string;
      // [] 접미사는 해당 타입의 배열
      type?: string;
      units?: string;
      // true 또는 생략이면 입력 필수
      required?: boolean;
      description?: string;
      [key: string]: unknown;
    }>;
    output_ports?: Array<{
      // grasshopper_04-run_definition tool의 outputs에서 이 이름을 키로 사용
      name?: string;
      // [] 접미사는 해당 타입의 배열
      type?: string;
      units?: string;
      description?: string;
      [key: string]: unknown;
    }>;
    outputs?: Array<string>;
    [key: string]: unknown;
  }>;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 40. grasshopper\_03-list\_library

```txt
로컬 Grasshopper 라이브러리의 색인된 로직 목록. logic_names는 grasshopper_01-get_logic tool에서 조회할 때 사용.
```

```ts
declare const tools: {
  mcp__rhino__grasshopper_03_list_library(args: {
    // logic_names와 같은 값의 logic_ids 포함
    // default: false
    include_ids?: boolean;
    // paths·all은 라이브러리 경로 포함. ports·definition·source·audit은 목록에 적용되지 않음.
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
  total_entries?: number;
  logic_names?: Array<string>;
  // include_ids=false일 때 logic_ids 대신 반환
  logic_count?: number;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 41. grasshopper\_04-run\_definition

```txt
실행 감사를 통과한 Grasshopper 캡슐을 Rhino에서 계산. 모든 출력 포트를 확인한 뒤 정의에 따라 하나의 Undo 기록으로 형상 베이크. mutation_state는 none·completed·rolled_back·unknown. requires_reconciliation=true이면 자동 재시도 금지. baked_guids와 현재 문서 확인.
```

```ts
declare const tools: {
  mcp__rhino__grasshopper_04_run_definition(args: {
    // grasshopper_02-list_capsules tool에서 얻은 캡슐 ID. 예: karamba_beam_v1.
    capsule_id: string;
    // ALMOND_IN_ 포트 이름을 키로 사용. grasshopper_02-list_capsules tool의 field_groups=['ports']로 input_ports의 타입·단위·필수 여부 확인. 형상은 {"guids":["객체 GUID"]}, 숫자·정수·문자열·불리언은 JSON 값, number[]·integer[]·string[]은 평탄한 배열.
    inputs: {
      [key: string]: unknown;
    };
    // 확률적 정의에만 정수 시드 사용
    // default: null
    seed?: (number | null);
    // 솔버 시간 한도(초). 0 초과, 600 이하.
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
  status?: string;
  // 입력 검증 실패 시 반환. 타입·단위·필수 여부는 grasshopper_02-list_capsules tool의 input_ports 참조.
  valid_inputs?: Array<string>;
  // 알 수 없는 capsule_id를 요청했을 때 반환. 실행 감사 상태는 grasshopper_02-list_capsules tool의 audited 참조.
  available_capsules?: Array<string>;
  capsule_id?: string;
  // 값의 의미·타입·단위는 캡슐 포트 계약을 따름
  outputs?: {
    [key: string]: unknown;
  };
  baked_guids?: Array<string>;
  analysis_method?: string;
  // 매니페스트 선언 기준: api/high, template/medium, rule_based/low
  confidence?: string;
  warnings?: Array<string>;
  error?: unknown;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  // unknown·partial이면 문서에 변경이 남아 있을 수 있음.
  mutation_state?: string;
  // true이면 Rhino 문서의 실제 변경 상태를 확인. 자동 재실행 금지.
  requires_reconciliation?: boolean;
  [key: string]: unknown;
};
```

## inspect

### 42. inspect\_01-analyze\_nested\_blocks

```txt
읽기 전용 중첩 블록 조회. outline은 선택된 루트를 기본으로 구조를 요약하고, resolve-block은 루트부터 대상까지의 경로로 공유 배치와 참조·링크 제한을 확인.

definition_impact.complete는 영향 범위 계수 완료 여부, occurrences_truncated는 반환 목록의 잘림 여부. 정의 내부 ID는 편집 가능한 문서 객체 ID와 다를 수 있다. 후속 조회에 ID가 필요하면 include_ids=true 사용.
```

```ts
declare const tools: {
  mcp__rhino__inspect_01_analyze_nested_blocks(args: {
    // outline 또는 resolve-block
    mode: string;
    // outline: ids 또는 path로 지정. 둘 다 생략하면 scope=selected(기본)·viewport·document 중 사용.
    // depth 0..64(기본 64), max_items 1..5000(기본 200), max_bytes 2048..262144(기본 48000).
    // field_groups: summary(기본), objects, annotations, transforms. include_geometry와 annotations로 형상·주석 포함, annotation_layer로 TextDot 레이어 필터링. field_groups를 생략하고 include_geometry 또는 annotations를 지정하면 기존 상세 모드.
    // resolve-block: path에 최상위부터 대상 블록까지 GUID 1..65개.
    options: {
      [key: string]: unknown;
    };
    // 생략하면 연결 문서 사용. 지정하면 일치하는 경로에서만 조회.
    // default: ""
    expected_model_path?: string;
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
  status?: string;
  mode?: string;
  document?: {
    units?: string;
    // 문서 길이 단위
    absolute_tolerance?: number;
    [key: string]: unknown;
  };
  data?: {
    // 블록 배치 또는 정의별 분석 항목
    records?: Array<{
      kind?: string;
      // 배치 객체 또는 정의 구성원의 ID. 편집 가능한 문서 객체 ID는 inspect_02-get_objects tool로 확인.
      id?: string;
      type?: string;
      // 공유 정의 영향을 조회할 때 resolve-block의 options.path에 재사용
      path?: Array<string>;
      definition?: string;
      [key: string]: unknown;
    }>;
    items?: number;
    truncated?: boolean;
    [key: string]: unknown;
  };
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 43. inspect\_02-get\_objects

```txt
Rhino 최상위 모델 객체를 ID·그룹·메타데이터로 조회. current는 표시되고 잠기지 않은 객체(화면 밖 포함), document는 숨김·잠금 객체까지 포함. 그룹은 선택 범위와 구성원의 교집합. 계층 모드는 그룹·블록 배치를 펼쳐 문서 객체와 블록 정의 내부 항목을 구분. 표시 여부는 가림을 고려한 화면 가시성과 별개.

UserDictionary 조건 예: `{"filters":{"user_dictionary":[{"source":"attributes","key":"brief_probe","any_of":["yes"]}]}}`.

행 후속 조회에는 같은 조건과 첫 응답의 snapshot·next_offset을 사용. 면 후속 조회에는 document 객체 ID와 geometry_crc 사용. objects·summary의 complete는 전체 행이 첫 응답에 포함되고 편집 상태가 안정적일 때 true. hierarchy는 관계 완전성도 확인하며 깊이 제한을 적용할 수 있다. face_page.complete는 전체 면이 첫 응답에 포함됐을 때 true. 마지막 행 페이지는 next_offset=null.
```

```ts
declare const tools: {
  mcp__rhino__inspect_02_get_objects(args: {
    // current 또는 document
    // default: "current"
    scope?: string;
    // scope=document 전용. 서로 다른 최상위 객체 GUID 1..4096개. group_ids와 동시 지정 불가.
    // default: null
    object_ids?: (Array<string> | null);
    // 모든 조건을 함께 적용. layer_paths는 정확한 전체 경로, object_types는 관찰된 Rhino 이름, name_contains는 대소문자 구분 없이 검색. 객체 속성 User Text의 user_text와 UserDictionary의 user_dictionary는 각각 조건 객체 1개도 배열로 지정하며 최대 16개 조건이 모두 일치해야 한다. user_text 예: [{"key":"floor","any_of":["2F"]}]. user_dictionary는 source=attributes(객체 속성) 또는 geometry(형상)와 비어 있지 않은 key 필요. any_of는 user_text에서 문자열 1..64개, user_dictionary에서 문자열·불리언·숫자 1..64개. 키의 값 또는 배열 원소가 any_of 중 하나와 정확히 일치해야 한다.
    // default: null
    filters?: ({
      [key: string]: unknown;
    } | null);
    // fields를 생략한 objects 모드에서 형상 상세를 포함. fields를 명시하면 그 목록 우선.
    // default: false
    include_geometry?: boolean;
    // 0..100000. 양수이면 expected_snapshot 필요.
    // default: 0
    offset?: number;
    // 1..200
    // default: 50
    limit?: number;
    // 생략하면 연결 문서 사용. 지정하면 일치하는 경로에서만 조회.
    // default: ""
    expected_model_path?: string;
    // default: false
    include_ids?: boolean;
    // objects, hierarchy, summary. recursive=true와 summary는 동시 지정 불가.
    // default: "objects"
    result_mode?: string;
    // 1개 이상 선택: id, name, layer_path, object_type, geometry_kind, geometry_crc, visible, selected, hidden, locked, bounds, groups, user_dictionary, user_text, geometry_valid, solid, manifold, volume, faces, face_count. 형상 상세와 faces는 objects 모드에서만 사용. summary에서는 fields 지정 불가.
    // default: null
    fields?: (Array<string> | null);
    // 양수이면 scope=document, object_ids 및 객체별 expected_geometry_crcs 필요
    // default: 0
    face_offset?: number;
    // 1..128. objects 모드에서 사용.
    // default: 128
    face_limit?: number;
    // 객체 GUID별 CRC. 면을 이어서 조회할 때 형상이 바뀌면 거부.
    // default: null
    expected_geometry_crcs?: ({
      [key: string]: number;
    } | null);
    // 서로 다른 Rhino 그룹 GUID 1..64개. 모든 scope에서 사용 가능, object_ids와 동시 지정 불가.
    // default: null
    group_ids?: (Array<string> | null);
    // current 전용. 화면 밖에서 선택된 객체도 포함. inside_window와 동시 지정 불가.
    // default: false
    selected?: boolean;
    // current 전용. 활성 뷰포트 경계에 걸친 바운딩 박스 포함. 클리핑 평면과 픽셀 가림은 고려하지 않으며 selected와 동시 지정 불가.
    // default: false
    inside_window?: boolean;
    // true이면 계층 모드 사용
    // default: false
    recursive?: boolean;
    // 1..8, 루트=1. 1 초과 시 recursive=true.
    // default: 1
    depth?: number;
    // offset > 0이면 첫 페이지의 snapshot 필요
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
  status?: string;
  scope?: string;
  objects?: Array<{
    id?: string;
    // 면 편집과 후속 면 조회에 사용할 형상 버전
    geometry_crc?: number;
    face_count?: number;
    faces?: Array<{
      // 같은 관찰의 id·geometry_crc와 묶어 model_02-edit_planar_face tool의 object_id·face_index·expected_geometry_crc에 전달
      face_index?: number;
      planar?: boolean;
      // 기본 편집 조건만 확인한 값. 실제 편집 전에 형상 버전을 다시 검사.
      face_edit_supported?: boolean;
      [key: string]: unknown;
    }>;
    faces_truncated?: boolean;
    face_page?: {
      offset?: number;
      limit?: number;
      returned?: number;
      next_offset?: number | null;
      complete?: boolean;
      [key: string]: unknown;
    };
    // Rhino 객체 속성의 User Text
    user_text?: {
      // 저장된 문자열이나 응답 제한으로 생략된 값의 표시
      values?: {
        [key: string]: unknown;
      };
      // 응답 제한을 적용하기 전 저장된 키 수
      total_keys?: number;
      truncated?: boolean;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  }>;
  matched_count?: number;
  offset?: number;
  limit?: number;
  next_offset?: number | null;
  // 후속 행 조회의 expected_snapshot에 그대로 전달
  snapshot?: string;
  // 편집 컨텍스트와 저장 대상
  editing?: {
    [key: string]: unknown;
  };
  // 계층 하위의 관찰 상태는 각 children_state 참조
  complete?: boolean;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  nodes?: Array<{
    // Rhino 객체 속성의 User Text
    user_text?: {
      // 저장된 문자열이나 응답 제한으로 생략된 값의 표시
      values?: {
        [key: string]: unknown;
      };
      // 응답 제한을 적용하기 전 저장된 키 수
      total_keys?: number;
      truncated?: boolean;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  }>;
  [key: string]: unknown;
};
```

### 44. inspect\_03-get\_document\_context

```txt
연결된 Rhino 문서·뷰·편집 상태와 Named View·Layout·레이어 계층·표시 모드 조회. Named View·Layout·표시 모드는 목록별 최대 128개이며 include_ids와 무관하게 ID를 반환. 화면 캡처에는 capture_03-current_view tool 사용.
```

```ts
declare const tools: {
  mcp__rhino__inspect_03_get_document_context(args: {
    // document, viewport, editor, viewports, named_views, layouts, layer_tree, display_modes 중 선택. 생략 또는 null이면 document, named_views, layouts, layer_tree, display_modes. []이면 항목 조회 생략.
    // default: null
    sections?: (Array<string> | null);
    // 뷰포트 등 선택적으로 ID를 반환하는 항목에 적용
    // default: false
    include_ids?: boolean;
    // editor 요청 시 공급자·명령·Undo 근거 포함
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
  named_views?: Array<{
    name?: string;
    id?: string;
    [key: string]: unknown;
  }> | null;
  layouts?: Array<{
    name?: string;
    id?: string;
    [key: string]: unknown;
  }> | null;
  layer_tree?: string | null;
  status?: string;
  warnings?: Array<string>;
  document?: {
    units?: string | null;
    // 문서 길이 단위
    absolute_tolerance?: number | null;
    modified?: boolean | null;
    object_count?: number | null;
    layer_count?: number | null;
    // 라디안
    angle_tolerance?: number | null;
    [key: string]: unknown;
  };
  next_step_guide?: string;
  message?: string;
  error_code?: string;
  [key: string]: unknown;
};
```

### 45. inspect\_04-get\_selection\_references

```txt
저장된 Rhino 문서의 일반 모델에서 선택 객체의 소속 Holon과 상위 Holon을 참조하는 Plan 조회. 일치한 Holon과 Plan의 전체 대상은 다를 수 있다. selection_truncated는 선택 목록, truncated는 Plan 목록에 적용.
```

```ts
declare const tools: {
  mcp__rhino__inspect_04_get_selection_references(args: {
    // 검사할 선택 객체 수 1..200
    // default: 50
    selection_limit?: number;
    // 반환할 Plan 수 1..500
    // default: 50
    limit?: number;
    // steps, references, geometry, artifacts, description, scope, audit, all. 생략·빈 배열이면 요약.
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
  status?: string;
  // 선택 객체의 등록 여부와 소유 Holon 포함
  objects?: Array<{
    [key: string]: unknown;
  }>;
  // 선택 객체를 소유한 Holon과 상위 Holon
  holons?: Array<{
    [key: string]: unknown;
  }>;
  plans?: Array<{
    [key: string]: unknown;
  }>;
  total_plans?: number;
  truncated?: boolean;
  // 현재 Rhino에서 소유 관계를 확인한 결과. 선택이 없으면 false.
  ownership_live_verified?: boolean;
  // 저장된 Plan·계층 참조의 현재 Rhino 검증 여부
  references_live_verified?: boolean;
  selection_total?: number;
  selection_truncated?: boolean;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 46. inspect\_05-resolve\_targets

```txt
Plan에 등록된 Scene·Holon 대상과 저장된 Holon 정보 조회. Step 지정 시 해당 Plan 소속을 검사하며 대상은 Plan 기준. Scene 전체로 Holon을 늘리거나 Rhino의 현재 구성원을 확인하지 않는다.
```

```ts
declare const tools: {
  mcp__rhino__inspect_05_resolve_targets(args: {
    // plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 id
    plan_id: string;
    // default: ""
    step_id?: string;
    // references, geometry, scope, audit, all. 생략·빈 배열이면 요약.
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
  status?: string;
  plan_id?: string;
  step_id?: unknown;
  // 변경을 검사할 때 현재 loop_no와 함께 사용
  revision?: number;
  scene_ids?: Array<unknown>;
  holon_ids?: Array<unknown>;
  holons?: Array<{
    [key: string]: unknown;
  }>;
  live_verified?: boolean;
  source?: string;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

## intersect

### 47. intersect\_01-find

```txt
닫힌 솔리드 중 양의 부피가 겹치는 객체 쌍을 집계. 0건은 검사 범위의 결과이며 간격이나 전체 설계 적합성은 별개. 계산할 수 없는 객체·쌍이 있으면 intersection_count_incomplete와 상세 반환. 면 접촉만으로도 계산이 불완전할 수 있다.
```

```ts
declare const tools: {
  mcp__rhino__intersect_01_find(args: {
    // 서로 다른 현재 최상위 Rhino 객체 GUID 1..512개. 내부에서 페이지를 나누며 전체를 하나의 범위로 검사.
    object_ids: Array<string>;
    // 중첩 블록의 배치 변환을 적용해 구성원까지 검사. false이면 블록 제외.
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
  intersections?: {
    // 양의 부피가 겹치는 객체 쌍의 수
    number?: number;
    [key: string]: unknown;
  };
  next_step_guide?: string;
  message?: string;
  error_code?: string;
  [key: string]: unknown;
};
```

### 48. intersect\_02-resolve

```txt
겹친 객체 쌍을 캡처해 비교하고 지정한 객체에서 겹친 부분을 제거. 검토 시 실제 카메라와 선택이 바뀐다. 완료 후에도 건너뛴 쌍은 남는다. 다음 쌍 계산이 실패해도 직전 수정이 이미 적용됐을 수 있으므로 previous_result와 실제 형상을 확인.
```

```ts
declare const tools: {
  mcp__rhino__intersect_02_resolve(args: {
    // 새 검토를 시작할 현재 최상위 객체의 서로 다른 GUID 1..512개. 이어서 검토하거나 선택을 제출할 때는 생략.
    // default: null
    object_ids?: (Array<string> | null);
    // 새 검토에 배치 변환을 적용한 중첩 블록 구성원 포함. 블록 정의 편집은 지원하지 않음.
    // default: false
    include_block?: boolean;
    // 비교 화면의 대상을 식별하는 반환 ID. choice 제출 시 필수. 완료됐거나 새 검토로 대체된 ID는 재사용 불가.
    // default: ""
    review_id?: string;
    // 1 또는 2: 해당 번호 객체에서 겹친 부분 제거. skip: 두 객체 유지. 선택 제출 시 review_id를 지정하고 object_ids는 생략. 검토만 하거나 이어갈 때는 choice 생략.
    // default: null
    choice?: (number | "skip" | null);
    // 새 검토 범위의 객체 속성 User Text 조건 배열. 예: [{"key":"floor","any_of":["2F"]}]. 한 객체가 모든 조건과 일치하는 쌍을 표시. 양쪽 값은 objects[].attributes.user_strings.values에서 확인. 중첩 블록에는 정의 구성원의 속성 적용.
    // default: null
    user_text?: Array<{
      [key: string]: unknown;
    }> | null;
  }): Promise<CallToolResult<{
    status?: string;
    // awaiting_choice이면 비교 결과를 보고 choice를 제출
    state?: string;
    skipped_pairs?: number;
    message?: string;
    error_code?: string;
    next_step_guide?: string;
    // choice에서 사용할 번호가 붙은 검토 쌍의 구성원
    objects?: Array<{
      attributes?: {
        // Rhino 객체 속성의 User Text
        user_strings?: {
          // 저장된 문자열이나 응답 제한으로 생략된 값의 표시
          values?: {
            [key: string]: unknown;
          };
          // 응답 제한을 적용하기 전 저장된 키 수
          total_keys?: number;
          truncated?: boolean;
          [key: string]: unknown;
        };
        [key: string]: unknown;
      };
      // 객체 속성과 형상의 UserDictionary를 구분
      user_dictionary?: {
        [key: string]: unknown;
      };
      [key: string]: unknown;
    }>;
    [key: string]: unknown;
  }>>;
};
```

## model

### 49. model\_01-assign\_material

```txt
Rhino 객체에 라이브러리 렌더 재료와 선택적 구축 메타데이터 지정. 재료는 객체에 직접 지정하고 레이어는 유지. 중복 GUID는 한 번만 처리. 메타데이터는 inspect_02-get_objects tool에서 fields=["user_text"]로 읽거나 filters.user_text로 검색.

success는 전체 처리, partial은 일부 처리. executed는 적용한 객체가 없거나 적용 결과를 읽지 못한 상태. 결과 확인이 안 된 경우 재시도 전에 Rhino에서 대상 객체 확인.
```

```ts
declare const tools: {
  mcp__rhino__model_01_assign_material(args: {
    // 현재 Rhino 객체의 GUID. 관찰 또는 생성 결과에서 가져온 값.
    guids: Array<string>;
    // model_04-list_materials tool에서 include_ids=true로 조회한 표준 재료 ID
    material_id: string;
    // default: true
    apply_render_material?: boolean;
    // Almond 재료·구축 메타데이터를 객체 속성에 기록
    // default: false
    attach_metadata?: boolean;
    // attach_metadata=true일 때 기록할 구조 역할
    // default: ""
    structural_role?: string;
    // 라이브러리에서 확인한 구축 시스템 ID. attach_metadata=true일 때 기록하며 construction_reference와 함께 지정하면 동일한 시스템 필요.
    // default: ""
    construction_system?: string;
    // attach_metadata=true일 때 기록할 층 레이블
    // default: ""
    floor?: string;
    // attach_metadata=true일 때 기록할 구축 상세
    // default: ""
    construction_detail?: string;
    // {"kind":"construction_system","id":"확인한 system_id"} 형식. attach_metadata=true일 때 기록하며 construction_system을 함께 지정하면 동일한 시스템 필요.
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
  status?: string;
  result_error?: string;
  material_id?: string;
  // 처리 성공 수. 실제로 달라진 객체 수는 changed_count 참조.
  applied_count?: number;
  requested_count?: number;
  // 렌더 재료 적용을 요청했는지 표시. 변경 확인은 changed_guids 참조.
  render_material_applied?: boolean;
  // attach_metadata와 apply_render_material을 모두 요청했는지 표시
  material_metadata_attached?: boolean;
  rhino_material_name?: string;
  ue_material_slot?: string;
  // 처리 성공 GUID. 실제 변경이 확인된 객체는 changed_guids 참조.
  applied_guids?: Array<string>;
  // attach_metadata와 함께 렌더 재료 적용 또는 추가 구축 메타데이터를 지정했는지 표시
  metadata_attached?: boolean;
  layer_path?: string | null;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 50. model\_02-edit\_planar\_face

```txt
닫힌 Brep의 평면 한 면을 PushPull Extend로 이동. 그룹·블록 편집을 종료한 일반 모델에서 사용. 현재 객체의 면 번호와 geometry_crc를 같은 관찰에서 가져온다. 일부 오류 응답에는 mutation_state가 없을 수 있다.
```

```ts
declare const tools: {
  mcp__rhino__model_02_edit_planar_face(args: {
    // 연결 문서에서 관찰한 잠기지 않은 최상위 닫힌 Brep의 GUID
    object_id: string;
    // 같은 형상 관찰에서 얻은 평면 인덱스. 0부터 시작.
    face_index: number;
    // 면 번호와 같은 관찰에서 얻은 형상 CRC. 형상이 바뀌면 객체 교체 전에 거부.
    expected_geometry_crc: number;
    // 문서 단위의 유한한 XYZ 값 3개. 면 법선 방향 성분의 절댓값은 문서 허용오차를 넘어야 한다.
    translation: Array<(number | number)>;
    // 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
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
  status?: string;
  result?: {
    // 대상 객체와 기존 CRC를 확인한 뒤 편집을 적용한 결과
    edited?: boolean;
    object_id?: string;
    previous_geometry_crc?: number;
    // 추가 면 편집 전 faces와 새 CRC를 다시 조회. 편집 후 면 인덱스가 달라질 수 있다.
    geometry_crc?: number;
    [key: string]: unknown;
  };
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 51. model\_03-edit\_planar\_faces

```txt
서로 다른 닫힌 Brep의 평면을 한 면씩 단일 Undo 기록으로 이동. 그룹·블록 편집을 종료한 일반 모델에서 사용. 객체별 면 번호와 CRC는 같은 관찰에서 가져온다. 준비 단계에서 한 항목이 거부되면 객체 교체를 시작하지 않는다.
```

```ts
declare const tools: {
  mcp__rhino__model_03_edit_planar_faces(args: {
    // 서로 다른 Brep에 대한 항목 1..32개. 각 항목에 object_id, face_index, expected_geometry_crc, translation을 지정하며 model_02-edit_planar_face tool과 동일한 조건 적용.
    edits: Array<{
      [key: string]: unknown;
    }>;
    // 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
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
  status?: string;
  // 객체 교체 중 실패하면 일부 편집이 남을 수 있다.
  result?: {
    status?: string;
    // 모든 항목의 적용을 확인했을 때 true
    complete?: boolean;
    requested_count?: number;
    applied_count?: number;
    // not_started, applied, partial, unknown 등. partial 또는 unknown이면 전체 배치를 자동 재실행하지 않음.
    mutation_state?: string;
    // 입력 순서의 항목별 결과. 실패 단계와 메시지 포함.
    items?: Array<{
      // applied, rejected, failed, unknown, not_attempted
      status?: string;
      edited?: boolean;
      previous_geometry_crc?: number;
      // 다음 면 편집 전 면 인덱스와 CRC를 다시 조회
      geometry_crc?: number;
      [key: string]: unknown;
    }>;
    [key: string]: unknown;
  };
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 52. model\_04-list\_materials

```txt
라이브러리에서 이름·설명·태그나 분류로 재료 검색. model_01-assign_material tool에 사용할 material_id는 include_ids=true로 조회.
```

```ts
declare const tools: {
  mcp__rhino__model_04_list_materials(args: {
    // 분류와 정확히 일치, 대소문자 구분. 생략하면 전체 분류.
    // default: ""
    category?: string;
    // 이름·설명·태그 검색. 대소문자 구분 없음.
    // default: ""
    query?: string;
    // default: false
    include_ids?: boolean;
    // display, physical, metadata, source, paths, audit, all. 생략·빈 배열이면 요약.
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
  total?: number;
  materials?: Array<{
    name?: string;
    category?: string;
    [key: string]: unknown;
  }>;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 53. model\_05-setup

```txt
연결된 Rhino 문서에 표준 재료를 등록하고 M 아래 분류·시스템·부재 역할별 레이어와 색·재료를 설정.

overwrite=false는 누락 항목만 생성하고 기존 속성의 차이를 보고. true는 누락 항목을 생성하고 기존 항목의 사전 정의 속성도 갱신. applied=true는 차이와 오류가 없는 상태. incomplete여도 일부 항목이 이미 생성·변경됐을 수 있다.

객체별 재료는 model_04-list_materials tool로 찾고 model_01-assign_material tool로 지정.
```

```ts
declare const tools: {
  mcp__rhino__model_05_setup(args: {
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
  status?: string;
  applied?: boolean;
  // 재료 레시피별 RenderMaterial과 지정 레이어의 처리 내역. 레이어 재료 지정으로 추가된 Rhino Materials 테이블 항목은 집계에서 제외. 변경 내역을 지원하는 Bridge에서 제공.
  changes?: Array<{
    // material: RenderMaterial을 확인한 재료 레시피. layer: 지정 레이어.
    kind?: "material" | "layer";
    // 재료 레시피 이름 또는 레이어 전체 경로
    name?: string;
    // created: RenderMaterial 수 증가 또는 레이어 생성. updated: 기존 값 변경. preserved: 기존 값 유지. unchanged: 작성 후 관측값 동일. unconfirmed: 작성 후 확인 실패. skipped: 작성 전 중단.
    action?: "created" | "updated" | "preserved" | "unchanged" | "unconfirmed" | "skipped";
    // 처리 전 일치하는 RenderMaterial 수 또는 지정 레이어의 존재 여부(0/1)
    previous_count?: number | null;
    // 처리 후 일치하는 RenderMaterial 수 또는 지정 레이어의 존재 여부(0/1)
    current_count?: number | null;
    [key: string]: unknown;
  }>;
  // 설정 기준과 최종 관측값이 다른 항목
  differences?: Array<{
    kind?: string;
    // 재료 이름 또는 레이어 경로
    name?: string;
    property?: string;
    current?: unknown;
    expected?: unknown;
    [key: string]: unknown;
  }>;
  errors?: Array<{
    kind?: string;
    name?: string;
    message?: string;
    [key: string]: unknown;
  }>;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

## plan

### 54. plan\_02-create

```txt
Phase 또는 Plan 생성. Plan은 `scope`의 Step 템플릿을 적용해 `loop_no=0`, `revision=1`에서 시작하며 실제 작업은 별도 수행. 생성 오류는 `result.status`에서 확인. 자동 생성된 Step은 plan_05-get tool로 확인.
```

```ts
declare const tools: {
  mcp__rhino__plan_02_create(args: {
    request: ({
      target: "phase";
      // 공백만 있는 이름은 거부.
      name: string;
      // default: ""
      description?: string;
      // context_04-get_project_info tool의 `project.files`에 등록된 파일명.
      // default: ""
      file_name?: (string | Array<string>);
      // default: "pending"
      status?: "pending" | "running" | "paused" | "completed" | "failed" | "blocked";
      // 같은 종류의 ID 형식만 검사. 대상 존재·순환·작업 순서는 확인하거나 강제하지 않음.
      // default: null
      depends_on?: (Array<string> | null);
      // Phase ID 형식만 검사. 참조 대상의 존재는 확인하지 않음.
      // default: null
      previous_id?: (string | null);
    } | {
      target: "plan";
      // 공백만 있는 제목은 거부.
      title: string;
      // 공백만 있는 목표는 거부.
      goal: string;
      // Step 템플릿. 기본 제공 키는 `spatial_development`, `drawing_development`, `semantic_exploration`, `plan_editing`, `model_revision`, `inspection`, `structure`, `construction_detail`, `drawing`, `component`, `house`, `interior`. 등록된 사용자 템플릿도 사용 가능.
      // default: "house"
      scope?: string;
      // 단일 Scene용 호환 입력. `scene_ids`와 함께 지정하면 배열의 첫 ID와 일치해야 함.
      // default: ""
      scene_id?: string;
      // default: ""
      phase_id?: string;
      // 생략하거나 `null`이면 `scene_id` 사용.
      // default: null
      scene_ids?: (Array<string> | null);
      // default: null
      holon_ids?: (Array<string> | null);
      // 같은 종류의 ID 형식만 검사. 대상 존재·순환·작업 순서는 확인하거나 강제하지 않음.
      // default: null
      depends_on?: (Array<string> | null);
      // Plan ID 형식만 검사. 참조 대상의 존재는 확인하지 않음.
      // default: null
      previous_id?: (string | null);
      // 상위 Plan의 존재를 검사하거나 상대 Plan을 자동 수정하지 않음.
      // default: null
      parent_plan?: (Array<string> | null);
      // 하위 Plan의 존재를 검사하거나 상대 Plan을 자동 수정하지 않음.
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
  status?: string;
  phase?: {
    phase_id?: string;
    [key: string]: unknown;
  };
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  plan?: {
    plan_id?: string;
    loop_no?: number;
    // 수정 시 `loop_no`와 함께 `expected_revision`으로 사용 가능.
    revision?: number;
    [key: string]: unknown;
  };
  [key: string]: unknown;
};
```

### 55. plan\_03-execute\_looping

```txt
Plan의 새 작업 회차 시작 또는 최신 회차 재개. Step 실행은 에이전트가 직접 수행.

새 회차의 Step은 `pending`에서 시작하며 이전 회차 기록은 `previous_loop`에서 확인. 실행된 회차가 있어야 `resume=true`로 재개 가능.

다음 회차를 시작하기 전, 현재 Plan Goal을 사용자의 피드백 및 작업방향에 맞게 align하여 수정하고, 다음 회차에 필요하지 않음이 분명한 라이노 객체, layout, namedview, layer등을 삭제한다.
```

```ts
declare const tools: {
  mcp__rhino__plan_03_execute_looping(args: {
    // plan_02-create tool 또는 plan_08-list tool에서 얻은 ID.
    plan_id: string;
    // `true`면 최신 회차 재개, `false`면 새 회차 시작.
    // default: false
    resume?: boolean;
    // 재개 시 생략하거나 비우면 이전 피드백 유지.
    // default: ""
    feedback?: string;
    // 최초 산출물 폴더명. 생략하면 목표에서 정하고 `YYMMDD_` 접두사를 붙임. 기존 폴더는 재사용.
    // default: ""
    artifact_name?: string;
  }): Promise<CallToolResult<{
    status?: string;
    plan_id?: string;
    loop_no?: number;
    // 다음 작업으로 선택할 첫 미완료 Step.
    next_step_id?: string | null;
    // 첫 회차에는 실행 전 0번 기록을 포함할 수 있음.
    previous_loop?: {
      loop_no?: number;
      steps?: Array<{
        // 회차가 바뀌어도 유지되는 Step UUID.
        step_id?: string;
        step_type?: string;
        name?: string;
        position?: number;
        kind?: string;
        // Step 상태는 `pending`, `running`, `paused`, `completed`, `failed`, `blocked`.
        status?: string;
        loop_no?: number;
        // 선행 Step UUID.
        depends_on?: Array<string>;
        input_refs?: Array<string>;
        output_refs?: Array<string>;
        // 다음 작업에 넘길 주요 발견과 교훈.
        takeaways?: string;
        design_rationale?: string;
        [key: string]: unknown;
      }>;
      [key: string]: unknown;
    };
    step_id?: string;
    plan_artifact_dir?: string;
    artifact_dir?: string | null;
    revision?: number;
    title?: string;
    goal?: string;
    // 회차를 시작해도 Plan 상태는 유지.
    plan_status?: string;
    feedback?: string;
    steps?: Array<{
      // 회차가 바뀌어도 유지되는 Step UUID.
      step_id?: string;
      step_type?: string;
      name?: string;
      position?: number;
      kind?: string;
      // Step 상태는 `pending`, `running`, `paused`, `completed`, `failed`, `blocked`.
      status?: string;
      loop_no?: number;
      // 선행 Step UUID.
      depends_on?: Array<string>;
      input_refs?: Array<string>;
      output_refs?: Array<string>;
      // 다음 작업에 넘길 주요 발견과 교훈.
      takeaways?: string;
      design_rationale?: string;
      [key: string]: unknown;
    }>;
    policy_reminder?: string;
    message?: string;
    error_code?: string;
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 56. plan\_05-get

```txt
Phase·Plan·Step 작업 기록 조회. `include_details=true`로 상세를 포함. 다음 작업에 필요한 파일은 반환된 프로젝트 상대경로로 열어 확인.

Plan·Step 조회에 `revision`을 지정하면 현재 번호여도 읽기 전용 스냅샷 반환.
```

```ts
declare const tools: {
  mcp__rhino__plan_05_get(args: {
    request: ({
      target: "phase";
      phase_id: string;
      // default: false
      include_details?: boolean;
    } | {
      target: "plan";
      plan_id: string;
      // 생략·`null`은 선택한 회차의 최신 상태.
      // default: null
      revision?: (number | null);
      // default: false
      include_details?: boolean;
      // 0 이상. 생략·`null`은 최신 회차, 0은 실행 전 기록.
      // default: null
      loop_no?: (number | null);
    } | {
      target: "step";
      plan_id: string;
      // 같은 요청의 `plan_id`에 속한 Step만 조회 가능.
      step_id: string;
      // 생략·`null`은 선택한 회차의 최신 상태.
      // default: null
      revision?: (number | null);
      // default: false
      include_details?: boolean;
      // 0 이상. 생략·`null`은 최신 회차, 0은 실행 전 기록.
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
  id?: string;
  type?: "phase" | "plan" | "step";
  name?: string;
  // 성공 시 `pending`, `running`, `paused`, `completed`, `failed`, `blocked` 중 하나. 조회 실패는 `error`.
  status?: string;
  plan_id?: string;
  // 0은 회차 시작 전 기록.
  loop_no?: number;
  revision?: number;
  // 과거 회차 또는 명시적으로 지정한 리비전이면 `true`. 수정 전 최신 기록 재조회.
  read_only?: boolean;
  phase?: {
    description?: string;
    file_name?: Array<string>;
    depends_on?: Array<string>;
    previous_id?: string | null;
    plan_titles?: Array<string>;
    [key: string]: unknown;
  };
  plan?: {
    goal?: string;
    // Step 템플릿 키.
    scope?: string;
    holon_ids?: Array<string>;
    steps?: Array<{
      step_id?: string;
      step_type?: string;
      name?: string;
      status?: string;
      loop_no?: number;
      [key: string]: unknown;
    }>;
    artifact_refs?: Array<string>;
    // 회차별 산출물 폴더를 담는 Plan 루트.
    artifact_dir?: string;
    loop_artifact_dir?: string;
    phase?: {
      phase_id?: string;
      name?: string;
      [key: string]: unknown;
    };
    scene_ids?: Array<string>;
    depends_on?: Array<string>;
    previous_id?: string | null;
    parent_plan?: Array<string>;
    child_plan?: Array<string>;
    feedback?: string;
    // 한국 시간 `YYYY-MM-DD-HH:MM`.
    created_at?: string;
    // 한국 시간 `YYYY-MM-DD-HH:MM`.
    updated_at?: string;
    [key: string]: unknown;
  };
  step?: {
    step_type?: string;
    input_refs?: Array<string>;
    output_refs?: Array<string>;
    // 다음 작업에 넘길 주요 발견과 교훈.
    takeaways?: string;
    design_rationale?: string;
    [key: string]: unknown;
  };
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 57. plan\_07-list\_revisions

```txt
Plan 리비전 목록을 최신 회차·리비전 순으로 조회. Step 필터는 해당 Step의 직접 변경만 포함. `offset` 미지원.

과거 기록은 plan_05-get tool에 같은 `loop_no`와 `revision`을 넣어 조회.
```

```ts
declare const tools: {
  mcp__rhino__plan_07_list_revisions(args: {
    // plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 id
    plan_id: string;
    // 1~500.
    // default: 50
    limit?: number;
    // `audit` 또는 `all`은 생성 시각 포함. 생략하거나 비우면 기본 필드만 반환.
    // default: null
    field_groups?: (Array<string> | null);
    // 생략·`null`은 모든 회차, 0은 실행 전 기록.
    // default: null
    loop_no?: (number | null);
    // 생략하거나 비우면 Step으로 필터링하지 않음.
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
  status?: string;
  // 행의 `loop_no`·`revision`과 함께 plan_05-get tool의 `request`에 사용.
  plan_id?: string;
  revisions?: Array<{
    loop_no?: number;
    revision?: number;
    operation?: string;
    step_id?: string | null;
    // `audit` 또는 `all` 그룹에서 반환.
    created_at?: string;
    [key: string]: unknown;
  }>;
  total?: number;
  limit?: number;
  truncated?: boolean;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 58. plan\_08-list

```txt
Phase·Plan 목록 또는 한 Plan의 순서 있는 Step 목록 조회. `offset` 미지원. Step 목록과 리비전 정보는 같은 스냅샷을 기준으로 반환.
```

```ts
declare const tools: {
  mcp__rhino__plan_08_list(args: {
    request: ({
      target: "phase";
      // 1~500.
      // default: 50
      limit?: number;
      // `description`은 설명, `scope`는 연결 파일, `audit`는 생성·수정 시각, `all`은 전체. 생략하거나 비우면 요약 반환.
      // default: null
      field_groups?: (Array<string> | null);
    } | {
      target: "plan";
      // 생략하거나 비우면 Phase 소속 여부와 관계없이 조회.
      // default: ""
      phase_id?: string;
      // 생략하거나 비우면 Scene 연결 여부와 관계없이 조회.
      // default: ""
      scene_id?: string;
      // 생략하거나 비우면 상태 필터를 적용하지 않음.
      // default: ""
      status?: "" | "pending" | "running" | "paused" | "completed" | "failed" | "blocked";
      // 1~500.
      // default: 50
      limit?: number;
    } | {
      target: "step";
      plan_id: string;
      // 생략·`null`은 선택한 회차의 최신 상태. 지정하면 읽기 전용 스냅샷.
      // default: null
      revision?: (number | null);
      // 0 이상. 생략·`null`은 최신 회차, 0은 실행 전 기록.
      // default: null
      loop_no?: (number | null);
      // 1~500. 정의된 순서의 앞부분을 반환.
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
  status?: string;
  phases?: Array<{
    phase_id?: string;
    name?: string;
    status?: string;
    plan_count?: number;
    depends_on?: Array<string>;
    previous_id?: string | null;
    // `scope` 또는 `all` 그룹에서 반환하는 Rhino 파일명.
    file_name?: Array<string>;
    [key: string]: unknown;
  }>;
  total?: number;
  limit?: number;
  truncated?: boolean;
  next_step_guide?: string;
  message?: string;
  error_code?: string;
  plans?: Array<{
    plan_id?: string;
    title?: string;
    // Step 템플릿 키.
    scope?: string;
    status?: string;
    loop_no?: number;
    revision?: number;
    [key: string]: unknown;
  }>;
  plan_id?: string;
  loop_no?: number;
  revision?: number;
  // 과거 회차 또는 명시적으로 지정한 리비전이면 `true`.
  read_only?: boolean;
  steps?: Array<{
    // 회차가 바뀌어도 유지되는 Step UUID.
    step_id?: string;
    step_type?: string;
    name?: string;
    status?: string;
    loop_no?: number;
    [key: string]: unknown;
  }>;
  [key: string]: unknown;
};
```

### 59. plan\_09-rename\_artifact\_folder

```txt
Plan 산출물 폴더 이름 변경 및 저장된 Plan·Step 경로 참조 갱신. 먼저 plan_10-set_working tool로 산출물 폴더를 지정.

Loop를 이미 실행했거나 다른 Plan의 과거 회차가 참조하는 폴더는 변경 불가. 같은 이름은 변경 없이 성공. 대상이 이미 존재하거나 다른 Plan 소유이면 실패. 실제 변경 시 새 리비전을 저장하고 이전 리비전은 보존.
```

```ts
declare const tools: {
  mcp__rhino__plan_09_rename_artifact_folder(args: {
    // 경로 대신 폴더명 하나. `YYMMDD_` 접두사가 없으면 현재 날짜를 붙임. Windows 금지 문자 사용 불가.
    name: string;
    // 생략하거나 비우면 현재 선택된 Plan 사용.
    // default: ""
    plan_id?: string;
  }): Promise<CallToolResult<{
    status?: string;
    artifact_dir?: string | null;
    // 폴더 이름이 실제로 변경된 경우에만 반환.
    previous_artifact_dir?: string;
    message?: string;
    error_code?: string;
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 60. plan\_10-set\_working

```txt
현재 연결의 산출물 작업 대상으로 Plan과 선택적인 Step 지정. 작업 실행과 Plan·Step 상태 변경은 별도.

최초 선택에서 산출물 경로를 정하면 리비전이 증가할 수 있음. 이후 같은 경로 재사용. `artifact_dir`은 Loop 시작 전 Plan 루트, 시작 후 현재 회차 폴더.
```

```ts
declare const tools: {
  mcp__rhino__plan_10_set_working(args: {
    // plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 id
    plan_id: string;
    // 생략하면 Plan만 선택.
    // default: ""
    step_id?: string;
    // 최초 폴더명. 생략하면 목표에서 정하고 `YYMMDD_` 접두사를 붙임. 기존 폴더와 다른 이름은 거부.
    // default: ""
    artifact_name?: string;
    // 생략·`null`은 현재 회차. 이전 회차 또는 존재하지 않는 회차는 선택 불가.
    // default: null
    loop_no?: (number | null);
  }): Promise<CallToolResult<{
    status?: string;
    plan_id?: string;
    step_id?: string;
    loop_no?: number;
    revision?: number;
    // script_01-run_project_python tool의 작업 디렉터리.
    artifact_dir?: string | null;
    plan_artifact_dir?: string;
    message?: string;
    error_code?: string;
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

### 61. plan\_12-update

```txt
Phase·Plan 작업 정보 또는 Step 상태·입출력 참조·판단 기록 수정. Plan·Step은 현재 회차만 수정 가능.

`depends_on`, `input_refs`, `output_refs`는 `add`/`remove` 패치. 나머지 대상·산출물·상하위 관계 배열은 전체 교체. 생략·`null`은 기존 값 유지, 교체 배열의 `[]`는 전체 삭제.

적용하지 못한 패치 항목은 `issues`에서 확인. 일부만 적용되면 `partial_success`. Step을 `completed`로 지정하면 함께 전달한 필드와 한 번에 저장.

Plan 완료는 사용자 확인 후 지정.
```

```ts
declare const tools: {
  mcp__rhino__plan_12_update(args: {
    request: ({
      target: "phase";
      // plan_08-list tool의 `request.target="phase"` 결과에 있는 `phases[].phase_id` 또는 plan_05-get tool의 Phase `id`.
      phase_id: string;
      // 빈 이름은 거부.
      // default: null
      name?: (string | null);
      // 빈 문자열은 설명 삭제.
      // default: null
      description?: (string | null);
      // context_04-get_project_info tool의 `project.files`에 등록된 파일명. 빈 문자열 또는 `[]`는 연결 해제, 생략·`null`은 연결 유지.
      // default: null
      file_name?: (string | Array<string> | null);
      // default: null
      status?: ("pending" | "running" | "paused" | "completed" | "failed" | "blocked" | null);
      // 같은 종류의 Phase ID만 사용. 대상 존재·순환·완료 여부는 검사하지 않음.
      // default: null
      depends_on?: ({
        // 이미 있는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록. `remove`에도 있는 값은 양쪽에서 건너뜀.
        add?: Array<string>;
        // 없는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록.
        remove?: Array<string>;
      } | null);
      // 빈 문자열은 연결 해제.
      // default: null
      previous_id?: (string | null);
    } | {
      target: "plan";
      // plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 id
      plan_id: string;
      // 빈 목표는 거부.
      // default: null
      goal?: (string | null);
      // 빈 문자열은 Phase 소속 해제.
      // default: null
      phase_id?: (string | null);
      // default: null
      scene_ids?: (Array<string> | null);
      // default: null
      holon_ids?: (Array<string> | null);
      // 현재 리비전과 다르면 수정 거부. Loop 시작 후에는 `loop_no`도 함께 지정.
      // default: null
      expected_revision?: (number | null);
      // Plan ID 형식만 검사. 대상 존재·자기 참조·순환은 확인하지 않으며 순서나 완료도 강제하지 않음.
      // default: null
      depends_on?: ({
        // 이미 있는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록. `remove`에도 있는 값은 양쪽에서 건너뜀.
        add?: Array<string>;
        // 없는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록.
        remove?: Array<string>;
      } | null);
      // `completed`는 사용자의 완료 결정 후 지정.
      // default: null
      status?: ("pending" | "running" | "paused" | "completed" | "failed" | "blocked" | null);
      // default: null
      artifact_refs?: (Array<string> | null);
      // 빈 제목은 거부.
      // default: null
      title?: (string | null);
      // 빈 문자열은 연결 해제.
      // default: null
      previous_id?: (string | null);
      // 상대 Plan을 자동 수정하거나 참조 대상의 존재를 검사하지 않음.
      // default: null
      parent_plan?: (Array<string> | null);
      // 상대 Plan을 자동 수정하거나 참조 대상의 존재를 검사하지 않음.
      // default: null
      child_plan?: (Array<string> | null);
      // 현재 회차만 허용. 생략하면 현재 회차 적용.
      // default: null
      loop_no?: (number | null);
    } | {
      target: "step";
      // plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 id
      plan_id: string;
      // plan_05-get tool의 Plan 상세에서 확인한 Step ID.
      step_id: string;
      // default: null
      status?: ("pending" | "running" | "paused" | "completed" | "failed" | "blocked" | null);
      // default: null
      input_refs?: ({
        // 이미 있는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록. `remove`에도 있는 값은 양쪽에서 건너뜀.
        add?: Array<string>;
        // 없는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록.
        remove?: Array<string>;
      } | null);
      // default: null
      output_refs?: ({
        // 이미 있는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록. `remove`에도 있는 값은 양쪽에서 건너뜀.
        add?: Array<string>;
        // 없는 값, 중복, 유효하지 않은 값은 건너뛰고 `issues`에 기록.
        remove?: Array<string>;
      } | null);
      // 다음 작업에 넘길 핵심 결론과 확인 사항. 빈 문자열은 내용 삭제.
      // default: null
      takeaways?: (string | null);
      // 설계 결정의 이유와 근거. 빈 문자열은 내용 삭제.
      // default: null
      design_rationale?: (string | null);
      // 현재 리비전과 다르면 수정 거부. Loop 시작 후에는 `loop_no`도 함께 지정.
      // default: null
      expected_revision?: (number | null);
      // 현재 회차만 허용. 생략하면 현재 회차 적용.
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
  status?: string;
  // `success`여도 저장 값이 같으면 `false`.
  changed?: boolean;
  phase?: {
    phase_id?: string;
    // 업무 상태는 `pending`, `running`, `paused`, `completed`, `failed`, `blocked`.
    status?: string;
    [key: string]: unknown;
  };
  // 이 목록에 없는 변경은 저장되었을 수 있음.
  issues?: Array<{
    field?: string;
    // `add` 또는 `remove`.
    operation?: string;
    // 해당 패치 배열에서의 0 기반 위치.
    index?: number;
    value?: unknown;
    reason?: string;
    [key: string]: unknown;
  }>;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  // Step 수정 응답에도 소속 Plan의 저장 정보 포함.
  plan?: {
    plan_id?: string;
    // 업무 상태는 `pending`, `running`, `paused`, `completed`, `failed`, `blocked`.
    status?: string;
    // 0은 회차 시작 전 기록.
    loop_no?: number;
    // 다음 수정에서 `loop_no`와 함께 `expected_revision`으로 사용 가능.
    revision?: number;
    [key: string]: unknown;
  };
  step?: {
    step_id?: string;
    // 업무 상태는 `pending`, `running`, `paused`, `completed`, `failed`, `blocked`.
    status?: string;
    // 0은 회차 시작 전 기록.
    loop_no?: number;
    [key: string]: unknown;
  };
  // 실패 시 확인된 Rhino 후속 작업 상태.
  cleanup_state?: "not_started" | "rolled_back" | "unknown";
  // `true`면 Rhino 또는 DB 상태를 확인해 후속 작업을 결정.
  requires_reconciliation?: boolean;
  [key: string]: unknown;
};
```

## research

### 62. research\_01-get\_construction\_guidance

```txt
건축 구법 비교·선정을 위한 참고 자료 조회.
```

```ts
declare const tools: {
  mcp__rhino__research_01_get_construction_guidance(args: {
    // 예: `glulam`, `longspan`, `bearing wall`.
    // default: ""
    query?: string;
    // floor, wall, roof, foundation 중 선택. 빈 값은 전체 분류.
    // default: ""
    category?: string;
    // analysis_02-validate_structure tool과 같은 재료명. `Wood`, `Steel`, `Concrete`.
    // default: ""
    material?: string;
    // analysis_02-validate_structure tool과 같은 유형. `beam`, `truss`, `shell`, `frame`, `canopy`, `gridshell`, `membrane`, `highrise`.
    // default: ""
    structure_type?: string;
    // 0보다 크면 시스템별 `fits_span`과 경험칙에 따른 권장 부재 깊이를 계산.
    // default: 0.0
    span_m?: number;
    // `load_kn` 산정에 참고할 용도별 활하중(kPa)과 재료 밀도(kg/m³)를 포함.
    // default: false
    include_reference_data?: boolean;
    // default: false
    include_ids?: boolean;
    // `rules`, `narrative`, `source`, `metadata`, `audit`, `all`. 생략하거나 비우면 요약 반환.
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
  total?: number;
  // 예비 치수 산정용 구법 라이브러리.
  source?: string;
  systems?: Array<{
    // research_02-get_typology_narrative tool의 `construction_system` 필터 또는 재료 메타데이터에 사용.
    system_id?: string;
    name?: string;
    category?: string;
    structural_material?: string;
    // 입력 경간이 경험칙 범위에 드는지 표시. 내력 판단에는 별도 구조 검토 필요.
    fits_span?: boolean;
    depth_guidance?: Array<{
      element?: string;
      suggested_depth_mm?: number;
      // 권장 깊이 산정에 사용한 경간 비율.
      rule?: string;
      [key: string]: unknown;
    }>;
    construction_detail?: string;
    construction_reference?: {
      kind?: string;
      id?: string;
      [key: string]: unknown;
    };
    // 의도에 맞는 재료 ID 하나를 골라 model_01-assign_material tool에 사용.
    render_material_ids?: Array<string>;
    [key: string]: unknown;
  }>;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 63. research\_02-get\_typology\_narrative

```txt
건축 유형의 서사와 선례 조회.
```

```ts
declare const tools: {
  mcp__rhino__research_02_get_typology_narrative(args: {
    // 예: `courtyard`, `skyscraper`, `timber hall`.
    // default: ""
    query?: string;
    // 구법 라이브러리의 `system_id` 기준 필터. 예: `steel-column-frame`.
    // default: ""
    construction_system?: string;
    // analysis_02-validate_structure tool의 유형으로 필터링. 예: `shell`, `truss`, `frame`, `membrane`.
    // default: ""
    structure_type?: string;
    // default: 5
    limit?: number;
    // default: false
    include_ids?: boolean;
    // `rules`, `narrative`, `source`, `metadata`, `audit`, `all`. 생략하거나 비우면 요약 반환.
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
  // `limit` 적용 전 전체 일치 수.
  total?: number;
  entries?: Array<{
    typology_id?: string;
    name?: string;
    era?: string;
    region?: string;
    narrative?: string;
    urban_role?: string;
    // research_01-get_construction_guidance tool의 `query`로 검색 가능.
    related_construction_systems?: Array<string>;
    [key: string]: unknown;
  }>;
  source?: string;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 64. research\_03-search\_details

```txt
건축 자료 디렉터리의 메타데이터 검색.
```

```ts
declare const tools: {
  mcp__rhino__research_03_search_details(args: {
    // default: ""
    query?: string;
    // default: false
    include_ids?: boolean;
    // `rules`, `narrative`, `source`, `metadata`, `audit`, `all`. 생략하거나 비우면 요약 반환.
    // default: null
    field_groups?: (Array<string> | null);
  }): Promise<CallToolResult<{
    status?: string;
    query?: string;
    query_terms?: Array<string>;
    expanded_terms?: Array<unknown>;
    sources?: Array<{
      source_id?: string;
      title?: string;
      url?: string;
      terms_url?: string;
      formats?: Array<string>;
      access?: string;
      redistribution?: string;
      generation_use?: string;
      matched_terms?: Array<string>;
      [key: string]: unknown;
    }>;
    scope?: string;
    message?: string;
    error_code?: string;
    next_step_guide?: string;
    [key: string]: unknown;
  }>>;
};
```

## scene

### 65. scene\_01-add\_objects

```txt
Rhino 객체를 Scene에 추가하거나 해당 Scene에서 제외한 Holon 구성원을 복원
```

```ts
declare const tools: {
  mcp__rhino__scene_01_add_objects(args: {
    // scene_07-list tool에서 include_ids=true로 조회한 Scene ID
    scene_id: string;
    // 일반 형상·클리핑 평면의 Rhino 객체 GUID, 최대 4096개.
    object_ids: Array<string>;
    // 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
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
  status?: string;
  // object_ids의 0부터 시작하는 위치
  failed_indices?: Array<unknown>;
  // Holon을 통해 이미 포함된 객체도 해당
  already_present_indices?: Array<unknown>;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 66. scene\_02-create

```txt
설계 영역이나 프로그램, 상황을 나타내는 Scene 생성
```

```ts
declare const tools: {
  mcp__rhino__scene_02_create(args: {
    // 빈 이름은 Untitled scene으로 저장.
    name: string;
    // mm, cm, m, in, ft 중 선택.
    // default: "mm"
    units?: string;
    // context_04-get_project_info tool의 project.files에 등록된 파일명으로, 폴더 제외
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
  status?: string;
  scene?: {
    scene_id?: string;
    revision?: number;
    [key: string]: unknown;
  };
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 67. scene\_03-focus\_holons

```txt
선택한 Holon과 하위 Holon의 유효 구성원을 Rhino에서 선택·격리·확대. 잠긴 주변 객체는 계속 보일 수 있다. Unisolate는 격리 전 표시 상태를 복원하며, 선택과 카메라 상태는 별도로 복원해야 할 수 있다.
```

```ts
declare const tools: {
  mcp__rhino__scene_03_focus_holons(args: {
    // 서로 다른 ID 1~32개. 유효 최상위 객체는 최대 4096개
    holon_ids: Array<string>;
    // 지정한 경로가 연결 문서와 일치해야 함
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
  // null이면 뷰 변경 적용을 확인하지 못한 상태.
  mutation_applied?: boolean | null;
  // true면 현재 Rhino 상태를 확인한 뒤 다음 작업을 결정.
  requires_reconciliation?: boolean;
  // validate, select, isolate, verify_selection, zoom_selected, redraw 중 실패한 단계.
  failed_stage?: string;
  view_change?: {
    selection_changed?: boolean | null;
    isolated?: boolean | null;
    // 선택 확대 또는 대체 경계 확대를 완료하면 true.
    zoom_selected?: boolean | null;
    // selected는 기본 선택 확대, bounding_box는 기본 확대 실패 후 대상 경계로 확대한 경우.
    zoom_method?: "selected" | "bounding_box";
    display_mode_changed?: boolean | null;
    // 격리 가시성만 복구. 카메라와 선택은 별도로 확인.
    restore_visibility_command?: string;
    [key: string]: unknown;
  };
  focus_observation?: {
    target_count?: number;
    // 문서 단위의 대상 합집합 경계.
    target_bounds?: {
      // [x, y, z] 순서.
      // minItems: 3
      // maxItems: 3
      min?: Array<number>;
      // [x, y, z] 순서.
      // minItems: 3
      // maxItems: 3
      max?: Array<number>;
      [key: string]: unknown;
    };
    target_bounds_error?: string;
    zoom_extents_selected?: boolean | null;
    zoom_bounding_box?: boolean | null;
    before_zoom?: {
      viewport_id?: string;
      parallel_projection?: boolean;
      // 문서 단위의 [x, y, z].
      // minItems: 3
      // maxItems: 3
      camera_location?: Array<number>;
      // 문서 단위의 [x, y, z].
      // minItems: 3
      // maxItems: 3
      camera_target?: Array<number>;
      // [left, right, bottom, top, near, far] 순서.
      // minItems: 6
      // maxItems: 6
      frustum?: Array<number>;
      observation_error?: string;
      [key: string]: unknown;
    };
    after_failure?: {
      viewport_id?: string;
      parallel_projection?: boolean;
      // 문서 단위의 [x, y, z].
      // minItems: 3
      // maxItems: 3
      camera_location?: Array<number>;
      // 문서 단위의 [x, y, z].
      // minItems: 3
      // maxItems: 3
      camera_target?: Array<number>;
      // [left, right, bottom, top, near, far] 순서.
      // minItems: 6
      // maxItems: 6
      frustum?: Array<number>;
      observation_error?: string;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
  status?: string;
  // 선택 확대 또는 대체 경계 확대를 완료하면 true.
  zoom_selected?: boolean;
  isolated?: boolean;
  locked_context_remains_visible?: boolean;
  restore_visibility_command?: string;
  model_path?: string;
  viewport_id?: string;
  selected_ids?: Array<string>;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 68. scene\_04-get

```txt
Scene의 등록 정보와 저장된 Holon·객체 수 조회. 현재 Rhino 구성원은 scene_06-get_objects tool로 조회. include_ids=true일 때도 입력한 scene_id는 생략.
```

```ts
declare const tools: {
  mcp__rhino__scene_04_get(args: {
    // scene_07-list tool에서 include_ids=true로 조회하거나 이전에 기록한 Scene ID
    scene_id: string;
    // default: false
    include_ids?: boolean;
    // scope, state, geometry, audit, all 중 선택. 생략하거나 빈 배열을 주면 요약 조회
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
  status?: string;
  scene?: {
    name?: string;
    units?: string;
    revision?: number;
    holons?: number;
    // 직접 등록 또는 제외 override가 있으면 저장된 정보만으로 수를 확정하기 어려워 null 반환
    objects?: number | null;
    direct_objects?: number;
    live_verified?: boolean;
    [key: string]: unknown;
  };
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 69. scene\_05-get\_holon

```txt
Holon의 등록 정보와 구성원 조회. live=true로 현재 Rhino 상태를 등록 정보와 대조하고 requires_sync로 동기화 필요 여부를 확인. recursive=true는 Rhino 블록 정의 경계는 유지하며 자손 Holon을 확장. include_ids=true일 때도 입력한 holon_id는 요약에서 생략.
```

```ts
declare const tools: {
  mcp__rhino__scene_05_get_holon(args: {
    // include_ids=true로 조회하거나 이전 등록 결과에서 확인한 Holon ID
    holon_id: string;
    // default: false
    live?: boolean;
    // 요청한 필드 그룹에 해당하는 ID만 포함
    // default: false
    include_ids?: boolean;
    // default: false
    recursive?: boolean;
    // references, geometry, scope, audit, all 중 선택. 생략하거나 빈 배열을 주면 요약 조회
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
  status?: string;
  holon?: {
    name?: string;
    // 등록 정보와 현재 관찰 결과의 구분은 live_verified로 확인
    availability?: string;
    object_count?: number;
    live_verified?: boolean;
    [key: string]: unknown;
  };
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 70. scene\_06-get\_objects

```txt
현재 Rhino 문서에서 Scene의 직접 객체와 Holon 구성원 조회. Scene에서 제외한 구성원은 생략.
```

```ts
declare const tools: {
  mcp__rhino__scene_06_get_objects(args: {
    // scene_07-list tool에서 include_ids=true로 조회하거나 이전에 기록한 Scene ID
    scene_id: string;
    // default: false
    include_ids?: boolean;
    // scope, state, geometry, audit, all 중 선택. 생략하거나 빈 배열을 주면 요약 조회
    // default: null
    field_groups?: (Array<string> | null);
    // 1~200
    // default: 50
    limit?: number;
    // default: 0
    offset?: number;
    // 지정한 경로가 연결 문서와 일치해야 함
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
  status?: string;
  objects?: Array<{
    [key: string]: unknown;
  }>;
  total?: number;
  limit?: number;
  offset?: number;
  // true이면 같은 조건에서 offset을 반환한 objects의 길이만큼 늘려 다음 페이지 조회
  truncated?: boolean;
  live_verified?: boolean;
  model_path?: string;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 71. scene\_07-list

```txt
공유 프로젝트 DB의 Scene 목록 조회. Scene 상세는 scene_04-get tool, 현재 Rhino 구성원은 scene_06-get_objects tool로 조회.
```

```ts
declare const tools: {
  mcp__rhino__scene_07_list(args: {
    // 대소문자를 구분하지 않는 부분 검색
    // default: ""
    name?: string;
    // 확장자를 포함한 정확한 프로젝트 파일명. 생략 시 프로젝트 전체 범위에서 조회
    // default: ""
    file_name?: string;
    // 1~200
    // default: 50
    limit?: number;
    // default: 0
    offset?: number;
    // default: false
    include_ids?: boolean;
    // scope, state, geometry, audit, all 중 선택. 생략하거나 빈 배열을 주면 요약 조회
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
  status?: string;
  scenes?: Array<{
    [key: string]: unknown;
  }>;
  total?: number;
  limit?: number;
  offset?: number;
  // true이면 같은 필터에서 offset을 반환한 scenes의 길이만큼 늘려 다음 페이지 조회
  truncated?: boolean;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 72. scene\_08-list\_holons

```txt
모델에서 저장된 Holon 등록 목록 조회. Scene을 지정하면 연결된 Holon을, 생략하면 기본으로 최상위 Holon을 조회. recursive=true는 자손을 포함하며 이 자손은 Scene에 직접 등록되지 않았을 수 있다. 현재 Rhino 구성원은 scene_05-get_holon tool에서 live=true로 조회.
```

```ts
declare const tools: {
  mcp__rhino__scene_08_list_holons(args: {
    // 관리형 세션에서 생략하면 연결된 모델 기준
    // default: ""
    expected_model_path?: string;
    // default: false
    include_ids?: boolean;
    // default: ""
    scene_id?: string;
    // default: false
    recursive?: boolean;
    // references, geometry, scope, audit, all 중 선택. 생략하거나 빈 배열을 주면 요약 조회
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
  status?: string;
  holons?: Array<{
    [key: string]: unknown;
  }>;
  total?: number;
  live_verified?: boolean;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 73. scene\_09-remove\_holon

```txt
Holon 등록 해제. Rhino 형상과 그룹은 보존.
```

```ts
declare const tools: {
  mcp__rhino__scene_09_remove_holon(args: {
    // 이 Holon을 참조하는 부모 Holon과 Plan의 관계를 먼저 해제
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
  status?: string;
  holon?: {
    holon_id?: string;
    status?: string;
    live_verified?: boolean;
    [key: string]: unknown;
  };
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 74. scene\_10-remove\_objects

```txt
객체를 Scene에서 제외. Rhino 형상과 Holon 그룹은 보존.
```

```ts
declare const tools: {
  mcp__rhino__scene_10_remove_objects(args: {
    // scene_07-list tool에서 include_ids=true로 조회한 Scene ID
    scene_id: string;
    // 일반 형상·클리핑 평면의 Rhino 객체 GUID, 최대 4096개.
    object_ids: Array<string>;
    // 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
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
  status?: string;
  // object_ids의 0부터 시작하는 위치
  failed_indices?: Array<unknown>;
  // object_ids의 0부터 시작하는 위치
  already_absent_indices?: Array<unknown>;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 75. scene\_11-sync\_holon

```txt
현재 Rhino 구성원으로 Holon 등록 정보 갱신
```

```ts
declare const tools: {
  mcp__rhino__scene_11_sync_holon(args: {
    // default: ""
    holon_id?: string;
    // 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
    // default: ""
    expected_model_path?: string;
    // holon_id와 함께 지정해 현재 Rhino 그룹 GUID가 일치하는지 확인하는 용도
    // default: ""
    rhino_group_id?: string;
    // holon_id 또는 rhino_group_id와 동시 지정 불가
    // default: null
    holon_ids?: (Array<string> | null);
    // holon_id, holon_ids, rhino_group_id와 동시 지정 불가
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
  status?: string;
  checked?: number;
  // 등록 내용이 바뀐 항목만 계산하며 변경이 없으면 리비전 유지
  changed?: number;
  // present 이외 상태의 등록 수
  unavailable?: number;
  // 문제 항목과 무관한 유효 등록은 함께 갱신될 수 있음
  problems?: Array<unknown>;
  scene_revisions?: {
    [key: string]: unknown;
  };
  // 모든 대상의 현재 Rhino 상태를 문제 없이 확인한 경우 true
  live_verified?: boolean;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 76. scene\_12-update

```txt
Scene의 프로젝트 파일 연결 변경 또는 해제
```

```ts
declare const tools: {
  mcp__rhino__scene_12_update(args: {
    // scene_07-list tool에서 include_ids=true로 조회하거나 이전에 기록한 Scene ID
    scene_id: string;
    // context_04-get_project_info tool의 project.files에 등록된 파일명. 빈 문자열은 연결 해제, 생략하거나 null이면 기존 연결 유지
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
  status?: string;
  scene?: {
    scene_id?: string;
    // 파일 연결이 실제로 바뀔 때 증가
    revision?: number;
    [key: string]: unknown;
  };
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

### 77. scene\_13-upsert\_holon

```txt
물리적 요소와 관계를 Holon으로 등록하거나 갱신
```

```ts
declare const tools: {
  mcp__rhino__scene_13_upsert_holon(args: {
    // 기존 Rhino 그룹을 연결할 때는 그룹의 정확한 이름과 일치해야 함
    name: string;
    // 최상위 Rhino 객체만 지정 가능하며 객체당 Holon 한 개. 생략하면 name과 일치하는 기존 그룹을 사용하고 빈 배열은 child_holon_ids가 있는 부모에만 허용
    // default: null
    object_ids?: (Array<string> | null);
    // 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
    // default: ""
    expected_model_path?: string;
    // 새 Holon은 필수. 수정 시 생략하면 기존 Scene 연결 유지
    // default: null
    scene_ids?: (Array<string> | null);
    // 생략하면 새 Holon 등록
    // default: ""
    holon_id?: string;
    // 동명 Rhino 그룹을 구분할 때 사용
    // default: ""
    rhino_group_id?: string;
    // 빈 배열은 기존 자식 분리, 생략은 유지. 자식당 부모 한 개만 허용하며 순환 금지
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
  status?: string;
  holon?: {
    holon_id?: string;
    availability?: string;
    object_count?: number;
    live_verified?: boolean;
    [key: string]: unknown;
  };
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```

## script

### 78. script\_01-run\_project\_python

```txt
연결된 Rhino 문서에서 Python 3 코드로 형상을 편집하거나 산출물을 생성. 선택한 Plan·Loop 산출물 폴더가 작업 디렉터리. 쓰기 가능한 공간을 plan_10-set_working tool으로 선택하거나 기존 선택을 재사용한다.

스크립트 실행만 기록할 때는 출력 또는 반환값에 executed를 사용한다. 작업 목적의 달성 여부는 실제 변경과 산출물로 확인하고, 문서 저장 여부는 별도로 확인한다. 시간 초과 뒤에도 실행이 이어지거나 오류 시 부분 변경이 남을 수 있다. 완료가 불확실하면 반환된 request_id로 script_03-get_execution tool을 조회하고, 같은 변경을 다시 실행하기 전에 문서 상태를 확인한다.
```

```ts
declare const tools: {
  mcp__rhino__script_01_run_project_python(args: {
    // 동기식 코드. doc과 scriptcontext.doc은 연결된 문서. JSON 호환 반환값은 result에 할당하고 상대 경로는 선택한 산출물 폴더 기준
    code: string;
    // 완료 근거 대기 한도 1~600초. beyond·CoS는 첫 대기 최대 60초 후 pending과 request_id를 반환할 수 있음.
    // default: 60
    timeout_seconds?: number;
  }): Promise<CallToolResult<{
    // executed는 스크립트 본문 실행 종료를 뜻하며 작업 결과는 result와 mutation_state에서 별도 확인
    status?: string;
    completed?: boolean;
    // 미완료 실행, 불확실한 결과 또는 다음 결과 페이지를 script_03-get_execution tool로 조회할 때 사용
    request_id?: string;
    artifact_dir?: string | null;
    result?: unknown;
    message?: string;
    error_code?: string;
    next_step_guide?: string;
    // partial 또는 unknown이면 같은 수정을 다시 실행하기 전에 현재 문서 상태 확인
    mutation_state?: string;
    result_page?: {
      type?: string;
      unit?: string;
      available_fields?: Array<string>;
      // 배열이나 문자열이 최상위 결과이면 result 키로 페이지 조회
      pages?: {
        [key: string]: {
          total?: number;
          offset?: number;
          returned?: number;
          next_offset?: number | null;
          [key: string]: unknown;
        };
      };
      [key: string]: unknown;
    };
    result_error?: string | null;
    result_display_error?: string | null;
    // true이면 같은 request_id로 script_03-get_execution tool 조회
    pending?: boolean;
    // 완료 근거 미확인. 재실행 전 문서 상태 확인 필요
    uncertain?: boolean;
    // 첫 응답 대기 한도 초과. 이때 실행이 이어지거나 부분 변경이 남을 수 있음
    timed_out?: boolean;
    // finishing은 Rhino 완료 후 CLI 종료 대기, awaiting_receipt는 CLI 종료 후 Rhino 완료 근거 대기.
    completion_state?: string;
    // recovering이면 실행 확인과 최초 호출의 정리가 진행 중
    connection_state?: string;
    [key: string]: unknown;
  }>>;
};
```

### 79. script\_02-run\_rhino

```txt
연결된 RhinoCode에서 모델링·편집·측정 코드 또는 명령 매크로 실행. 실행 완료만 기록할 때는 출력 또는 반환값에 executed를 사용하고, 작업 결과는 result와 mutation_state에서 확인한다. 완료가 불확실하면 반환된 request_id로 script_03-get_execution tool을 조회하고, 같은 변경을 다시 실행하기 전에 문서 상태를 확인한다.
```

```ts
declare const tools: {
  mcp__rhino__script_02_run_rhino(args: {
    // 동기식 Python 소스, C# 문장 본문 또는 명령 매크로. Python은 JSON 호환 값을 result에, C#은 JSON을 result_json에 할당. doc은 연결된 문서. command는 !·Pause·대화상자 없이 종료되는 매크로
    script: string;
    // python(Python 3), python2, csharp, csharp-script, command 중 선택.
    // default: "python"
    language?: string;
    // 완료 근거 대기 한도 1~600초. beyond·CoS는 첫 대기 최대 60초 후 pending과 request_id를 반환할 수 있음.
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
  // executed는 스크립트 본문 실행 종료를 뜻하며 작업 결과는 result와 mutation_state에서 별도 확인
  status?: string;
  completed?: boolean;
  // 같은 실행을 script_03-get_execution tool로 조회할 때 사용
  request_id?: string;
  result?: unknown;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  // partial 또는 unknown이면 같은 수정을 다시 실행하기 전에 현재 문서 상태 확인
  mutation_state?: string;
  result_page?: {
    type?: string;
    unit?: string;
    available_fields?: Array<string>;
    // 배열이나 문자열이 최상위 결과이면 result 키로 페이지 조회
    pages?: {
      [key: string]: {
        total?: number;
        offset?: number;
        returned?: number;
        next_offset?: number | null;
        [key: string]: unknown;
      };
    };
    [key: string]: unknown;
  };
  result_error?: string | null;
  result_display_error?: string | null;
  // true이면 같은 request_id로 script_03-get_execution tool 조회
  pending?: boolean;
  // 완료 근거 미확인. 재실행 전 문서 상태 확인 필요
  uncertain?: boolean;
  // 첫 응답 대기 한도 초과. 이때 실행이 이어지거나 부분 변경이 남을 수 있음
  timed_out?: boolean;
  // finishing은 Rhino 완료 후 CLI 종료 대기, awaiting_receipt는 CLI 종료 후 Rhino 완료 근거 대기.
  completion_state?: string;
  // recovering이면 실행 확인과 최초 호출의 정리가 진행 중
  connection_state?: string;
  [key: string]: unknown;
};
```

### 80. script\_03-get\_execution

```txt
이전 RhinoCode 실행의 상태와 보관된 결과·로그 조회. 조회는 실행 기록만 읽으며, 연결이 끝난 뒤에도 기록이 남아 있으면 조회할 수 있다. 배열이나 문자열 결과는 페이지로 조회하고 로그는 별도의 바이트 오프셋을 사용한다.
```

```ts
declare const tools: {
  mcp__rhino__script_03_get_execution(args: {
    // 생략하면 현재 연결의 최근 실행 조회. beyond·CoS에서 지정한 ID로 최초 실행 연결을 찾으며, 시간 초과 후에는 같은 ID를 지정
    // default: ""
    request_id?: string;
    // default: true
    include_result?: boolean;
    // stdout·stderr와 CLI 로그 포함
    // default: false
    include_stdout?: boolean;
    // 객체 결과의 최상위 키 또는 객체 배열의 각 행에서 유지할 키
    // default: null
    result_fields?: (Array<string> | null);
    // 결과는 배열 항목 또는 문자열 문자, 로그는 바이트 단위
    // default: 0
    offset?: number;
    // 결과 페이지당 1~1000. 로그에는 별도 크기 제한 적용
    // default: 100
    limit?: number;
    // default: true
    include_ids?: boolean;
    // default: false
    include_diagnostics?: boolean;
  }): Promise<CallToolResult<{
    // 같은 실행의 상태나 다음 결과 페이지를 조회할 때 사용
    request_id?: string;
    // 최종 Rhino 처리 근거와 CLI 종료를 모두 확인한 경우 true. native_completed는 Rhino 측 완료 확인
    completed?: boolean;
    // executed는 스크립트 본문 실행 종료를 뜻하며 작업 결과는 별도 확인
    status?: string;
    result?: unknown;
    message?: string;
    error_code?: string;
    next_step_guide?: string;
    // partial 또는 unknown이면 같은 수정을 다시 실행하기 전에 현재 문서 상태 확인
    mutation_state?: string;
    result_page?: {
      type?: string;
      unit?: string;
      available_fields?: Array<string>;
      // 배열이나 문자열이 최상위 결과이면 result 키로 페이지 조회
      pages?: {
        [key: string]: {
          total?: number;
          offset?: number;
          returned?: number;
          next_offset?: number | null;
          [key: string]: unknown;
        };
      };
      [key: string]: unknown;
    };
    result_error?: string | null;
    result_display_error?: string | null;
    [key: string]: unknown;
  }>>;
};
```

### 81. script\_04-save\_document

```txt
사용자의 영구 저장 요청에 따라 연결된 문서 전체를 기존 .3dm 경로에 저장
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
  status?: string;
  // 저장이 미확정이면 null과 requires_reconciliation=true를 반환. 재호출 전 현재 문서 상태 확인
  saved?: boolean | null;
  modified?: boolean;
  message?: string;
  error_code?: string;
  next_step_guide?: string;
  [key: string]: unknown;
};
```
