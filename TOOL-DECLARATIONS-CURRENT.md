# 현행 툴 선언

> 교정안: 설명과 입력 주석을 다듬은 문서다. 실제 도구에 아직 적용하지 않았다. 43번 입력 선언도 검토용이며, 아래 해시는 수집 당시 값이다.

## 기준 및 선언 표기

beyond·CoS의 공개 도구 81개. 연결 대상 입력, 연결 관리 도구 설명, 연결 성공 응답의 ID 필드 설명은 경로별로 다름.

- 수집일: 2026-11-24. 기준: 이 문서와 함께 관리하는 소스.
- 수집 경로: `src/cos/codex_host.py`와 `src/cos/cos_host.py`의 공용 `external_host.main`. 격리된 데이터 폴더에서 Rhino 연결 없이 stdio `initialize`·`tools/list` 호출.
- 실행 패키지: almond-mcp 0.7.0rc2 / fastmcp 4.1.0 / mcp 2.3.0 / mcp-types 2.3.0.
- CoS 선언 SHA-256: `413113ec6d84ac821eb7635001d91486f898f38ae38d09ee5b8328a05bb9a413`
- beyond 선언 SHA-256: `eb277287e2c8515db525ce202bccb226cf2e909119ddcf854a6327e12478bcbf`
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
- `plan_12-update` tool로 Plan을 실제 완료한 응답의 `next_step_guide`에는 해당 Plan에서만 사용했고 이제 필요 없는 객체·레이어·레이아웃·Named View를 정리하라는 안내가 추가된다.
- `plan_03-execute_looping` tool의 성공 응답은 다음 Step의 선택·기록 방법과 회차 결과를 보고할 때 시각적 근거를 포함하라는 안내를 제공한다.
- `connect_02-session` tool 또는 `connect_03-start_session` tool로 연결. CoS의 일반 호출은 선택한 연결을 사용. beyond는 각 호출에서 연결 ID를 지정하며 `script_03-get_execution` tool로 실행을 재조회할 때도 원래의 `connection_id`와 `request_id`를 함께 전달.
- 외부 실행의 첫 대기 한도는 `min(요청 timeout, 60초)`. `pending`이면 같은 `request_id`로 완료 여부 조회. 외부 클라이언트 제한은 600초. 대기 종료·취소·오류 후에는 실제 문서 상태와 실행 결과를 확인하고 재실행 여부를 결정. [RhinoCode 실행 계약](src/mcp/runtime/RHINOCODE-SPEC.md) · [외부 연결기 SPEC](src/cos/SPEC.md)

## 선언 갱신 절차

[저장소 지침](AGENTS.md)에 따라 두 외부 서버를 격리된 데이터 폴더에서 시작. `initialize`에서 초기 안내를 확인하고, `tools/list`에서 목록·설명·입출력 스키마 전체를 비교한 뒤 이 문서와 해시를 갱신. Rhino 연결·모델링 호출 없이 검사 가능.

# Tool

## analysis

### 1. analysis\_05-check\_egress

```txt
층 평면의 피난안을 검토할 때 출구 수·유효 폭·출구 간 이격과 보행거리를 예비 기준과 비교한다. Rhino에서 경로를 찾아 계산하지는 않는다. 층 경계, 문 중심과 유효 폭, 가장 불리한 경로의 길이를 실측해 입력한다.

BCI와 통상적인 IBC 수치를 사용한다. 비업무 용도의 보행거리와 스프링클러가 설치된 막다른 복도는 업무용 기준으로 계산한다. 막다른 복도에 업무용 기준을 적용했다는 별도 경고는 없다. source_note에서 계산 근거를, warnings에서 적용 조건을 확인하고 프로젝트 법규와 대조한다. 경계값에서는 반올림된 표시와 판정이 다르게 보일 수 있다.
```

```ts
declare const tools: {
  mcp__rhino__analysis_05_check_egress(args: {
    // [min_x, min_y, max_x, max_y], mm. 유한 좌표, 면적 양수.
    plate_bounds_mm: Array<number>;
    // 문별 {name, x_mm, y_mm, width_mm}. 문 중심·유효 폭 필수, 유한값, 중심 중복 금지.
    // 폭은 0 이상(0도 폭 부족 판정). 출구가 둘 이상이면 가장 먼 두 출구의 직선 이격 검사.
    exits: Array<{
      [key: string]: unknown;
    }>;
    // business, mercantile, assembly_unconcentrated, classroom, residential, storage.
    // default: "business"
    occupancy?: string;
    // 담당 층수(양의 정수). 2층 이상: 최소 출구 2개, 계단 폭 7.6 mm/인.
    // default: 1
    stories?: number;
    // 전체 구역 설치 기준.
    // default: true
    sprinklered?: boolean;
    // 실제 재실 면적(m²), 유한값 0 이상. 0이면 경계 사각형 면적 사용.
    // default: 0.0
    net_area_m2?: number;
    // 실측 보행 거리(m, 유한값 0 이상). 최댓값 검사, []는 생략.
    // default: []
    travel_distances_m?: Array<number>;
    // 가장 긴 막다른 복도(m, 유한값 0 이상). 0은 검사 생략.
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
이미 수행한 구조 해석의 결과를 Markdown 보고서로 저장한다. 각 실행의 실제 엔진과 적용 입력을 함께 기록한다. 보고서 파일은 응답의 path에서 찾는다. 새로 해석하지 않으며, 당시 기록하지 않은 입력은 알 수 없음으로 표시한다.
```

```ts
declare const tools: {
  mcp__rhino__analysis_04_export_structural_report(args: {
    // 저장 위치. 관리형: 선택 Plan의 산출물 폴더 기준 상대 경로(기본 reports/structural-validation.md).
    // 독립 실행에서 생략: 사용자 데이터의 reports/structural-validation-<timestamp>.md.
    // default: ""
    path?: string;
    // 최근 실행부터 1..500회(범위 밖 값은 보정).
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
구조 해석에 적용할 설계기준을 고를 수 있다. 기준값·출처·검토 기록 중 필요한 항목을 골라 프로필을 비교한다. 적용할 기준의 ID는 include_ids=true로 받아 해석의 design_code에 넣는다.
```

```ts
declare const tools: {
  mcp__rhino__analysis_01_list_design_codes(args: {
    // true: 해석에 넘길 프로필 ID 포함.
    // default: false
    include_ids?: boolean;
    // parameters=기준값, source=출처, audit=검토 기록, all=전체. 생략·[]: 요약.
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
Rhino 모델을 해석해 예상 하중에서 구조가 어떻게 거동하고 설계기준을 충족하는지 검토한다. 현재 Rhino 문서에서 해석할 객체 GUID와 구조 유형을 먼저 고른다. 용도에 맞춰 하중과 지점·접합을 정한다.

engine=auto면 셸·그리드셸·막 구조는 Karamba를 사용하고, 나머지는 네이티브 프레임 해석부터 시도한다. 바닥·자산 하중을 빼면 안 되거나 부재별 단면력·사용률·처짐 및 지점 반력이 필요하면 native를 고른다. Karamba에서는 바닥·자산 하중을 적용하지 않는다.

요청 옵션, 실제 엔진·입력·결과를 실행 이력에 남긴다. 네이티브 해석은 모델과 하중도 기록한다. 이력을 보고서로 받으려면 analysis_04-export_structural_report를 쓴다. 과거 이력에 없는 옵션은 알 수 없음으로 표시한다.
```

```ts
declare const tools: {
  mcp__rhino__analysis_02_validate_structure(args: {
    // 현재 문서의 해석 대상 객체 GUID.
    guids: Array<string>;
    // beam=단순 보 휨·처짐, truss=축력·좌굴, shell=셸 응력·변위, frame=프레임 모멘트·전단.
    // canopy=캔틸레버 캐노피, gridshell=대변형 그리드셸, membrane=막 형상 탐색, highrise=고층 구조 시스템.
    // default: "beam"
    structure_type?: string;
    // 전체 부과하중(kN). native: 자유 절점에 -Z 방향으로 균등 분배. 이미 바닥·자산 하중에 반영한 항목은 중복 제외(필요 시 0).
    // default: 10.0
    load_kn?: number;
    // "Steel", "S355", "Concrete", "Wood", "Aluminium".
    // default: "Steel"
    material?: string;
    // native=네이티브 해석만, karamba=Karamba 경로, auto=구조 유형과 실행 가능 여부로 선택.
    // Karamba 경로는 api → template → rule_based 순으로 시도. 실제 경로는 analysis_method·warnings 확인.
    // default: "auto"
    engine?: string;
    // true는 완전 고정, false는 회전이 자유로운 핀 지점.
    // default: true
    fixed_supports?: boolean;
    // true: 자중을 해석 하중에 포함.
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
Rhino 모델 위에 처짐 형상이나 좌굴 모드를 띄운다. 변위와 사용률 중 하나를 골라 어느 부재가 더 크게 변형되거나 한계에 가까운지 색으로 본다. 표시는 임시 오버레이다. 직전 계산의 하중이나 구조를 바꾸지 않는다면 reanalyze=false로 배율·색·표시 범위만 조정할 수 있다. 같은 부재를 일반 형상과도 비교할 수 있다.
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
    // true: 자중 포함.
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
    // false: 직전 계산 재사용. scale·color_by·reveal·physics·title만 갱신.
    // default: true
    reanalyze?: boolean;
    // false: 해석 오버레이 대신 같은 부재의 일반 형상 표시.
    // default: true
    physics?: boolean;
    // 화면에 그릴 부재만 지정. 해석은 guids 전체에 적용.
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
    // deflection=처짐. buckling=지배 ULS 조합의 첫 좌굴 모드와 alpha_cr(≤1 UNSTABLE, 1<alpha_cr<10 SWAY-SENSITIVE, ≥10 STABLE).
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
저장한 SVG·DXF가 도면 패키지 발행 당시와 같은지 확인한다. 도면 생성·조회에서 받은 패키지 경로를 입력한다. 파일별 해시를 대조한다. 등록 원본을 찾았거나 원본 GLB를 제공한 경우에는 원본의 변경 여부도 검사한다. 빈 해시 목록, 파일 누락·변경, 패키지 외부 경로와 파일시스템 링크는 오류다.
```

### 7. asset\_02-generate\_drawing\_views

```txt
모델 외곽을 평면·정면·우측면 실루엣으로 뽑아 지정 축척 SVG와 실물 크기(mm) DXF로 받는다. 세 투영이 A3에 들어갈 때만 시트 SVG를 함께 만든다.

등록 3DM의 자산 ID와 외부 GLB 중 하나를 고른다. 필요한 축척을 지정할 수 있다. GLB라면 원본 단위(mm 또는 m)와 위쪽 축(y 또는 z)도 정한다. 정면은 좌표계 기준이며 내부 가시선·은선·단면은 만들지 않는다. 작은 윤곽은 축척에 따라 단순화될 수 있다. 결과는 별도 drawing-runs에 저장하고 기존 도면은 바꾸지 않는다. 기존 도면을 갱신하려면 asset_08-refresh를, 새 패키지 파일을 검증하려면 asset_01-audit_drawing을 쓴다.
```

### 8. asset\_03-get\_drawings

```txt
이미 생성된 자산의 평면·입면 도면을 가져온다. 배치 인스턴스가 아니라 원본 자산의 투영이다. 파일·축척·치수·출처와 투영 한계는 manifest에서 확인한다. 도면의 변경 여부를 검사하려면 field_groups에 all을 지정해 package_dir를 받고 asset_01-audit_drawing에 넘긴다.
```

```ts
declare const tools: {
  mcp__rhino__asset_03_get_drawings(args: {
    // 등록 자산 ID. 모르면 목록·검색의 include_ids=true로 조회.
    asset_id: string;
    // true: 응답에 ID 포함.
    // default: false
    include_ids?: boolean;
    // dimensions, source, paths, drawing, metadata, audit, all. 생략·[]: 요약.
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
후보 ID로 등록 정보와 사용 가능 상태를 확인한다. 치수·도면·출처·원본 경로 중 필요한 상세 항목을 골라 조회한다. 도면 파일을 직접 보려면 asset_03-get_drawings를 쓴다.
```

```ts
declare const tools: {
  mcp__rhino__asset_04_get(args: {
    // 등록 자산 ID. 모르면 목록·검색의 include_ids=true로 조회.
    asset_id: string;
    // ID 포함 요청. 입력한 asset_id는 반복되지 않을 수 있음.
    // default: false
    include_ids?: boolean;
    // dimensions, source, paths(원본·모델 경로), drawing, metadata, audit, all. 생략·[]: 요약.
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
라이브러리의 모델·2D 자산을 분류별로 훑고, 무엇을 바로 배치할 수 있는지 확인한다. 상세 확인이나 배치에 쓸 후보 ID가 필요하면 include_ids를 켠다. 이름이나 크기로 후보를 좁히려면 asset_11-search를 쓴다.
```

```ts
declare const tools: {
  mcp__rhino__asset_05_list(args: {
    // 찾을 분류. 빈 값은 전체.
    // default: ""
    category?: string;
    // 페이지당 1..100개.
    // default: 20
    limit?: number;
    // 목록에서 건너뛸 자산 수(0 이상).
    // default: 0
    offset?: number;
    // true: 상세 조회에 넘길 자산 ID 포함.
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
라이브러리에서 고른 모델·2D 자산을 Rhino 문서에 블록으로 배치한다. 자산 ID와 원본 기준점을 놓을 위치를 정한다. 필요하면 회전·배율을 지정한다. 3DM은 원본에 연결되며, 공유 정의를 갱신하면 같은 정의를 쓰는 배치에도 반영된다. 배치한 블록을 다시 찾거나 Scene에 넣을 때는 응답의 object_guid를 쓴다.
```

```ts
declare const tools: {
  mcp__rhino__asset_06_place(args: {
    // 배치할 등록 자산 ID. 모르면 목록·검색의 include_ids=true로 조회.
    asset_id: string;
    // 원본 기준점이 놓일 월드 X(문서 단위).
    // default: 0
    x?: number;
    // 원본 기준점이 놓일 월드 Y(문서 단위).
    // default: 0
    y?: number;
    // 원본 기준점이 놓일 월드 Z(문서 단위).
    // default: 0
    z?: number;
    // 월드 Z축을 기준으로 회전(도).
    // default: 0
    rotation_degrees?: number;
    // 세 축에 동일한 배율(0 초과 100 이하).
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
라이브러리에 모델을 올리기 전에 형상과 단위를 미리보기로 검토해 등록용 3DM을 준비한다. 원본은 바꾸지 않는다.

inspect에 원본 경로를 넣고, 메시라면 원본 단위도 지정한다. 이후에는 처음 받은 job_dir를 이어 쓴다. 방향·위치를 바꾸거나 부품을 빼야 할 때만 normalize를 쓴다. 변경 내용과 실제 확인한 미리보기 해시를 review로 보낸다.

첫 verify로 최종 미리보기를 만든다. 이미지를 확인한 뒤 실제로 확인한 최종 해시와 등록할 이름·ID를 review에 넣어 verify를 다시 호출한다. ready_for_registration=true는 등록 완료가 아니라 등록할 준비가 됐다는 뜻이다. 등록하려면 asset_09-register에 source_3dm과 검토한 이름·ID를 넘기고, preparation_job에 job_dir를 넣는다. 이미 저장된 근거만 다시 보려면 status를 사용한다.
```

```ts
declare const tools: {
  mcp__rhino__asset_07_prepare(args: {
    // inspect=원본 미리보기, normalize=사본 수정, verify=최종 미리보기·검토, status=저장 근거만 조회(재실행·단계 변경 없음). 미리보기 경로만 다시 보려면 status에 field_groups:["previews"].
    stage: string;
    // inspect에 넣을 원본 경로. 관리형은 프로젝트 상대, 독립 실행은 절대 경로. 원본 바이트 보존.
    // default: ""
    source_file?: string;
    // inspect가 반환한 작업 폴더. normalize·verify·status 필수. 등록 시 preparation_job에 전달.
    // 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로.
    // default: ""
    job_dir?: string;
    // inspect의 OBJ/STL/PLY/OFF/GLB/glTF 원본 단위: mm, cm, m, in, ft. 이후 단계에는 생략; 3DM은 내장 단위.
    // default: ""
    input_units?: string;
    // normalize: 실제 확인한 inspected_sha256과 vision_reviewed:true. 바꿀 항목만 지정: rotation_degrees_xyz:[x,y,z], translation:[x,y,z](원본 단위), remove:[{object_id,reason}].
    // 첫 verify: 생략. 최종 미리보기 검토 뒤 두 번째 verify: {vision_reviewed:true, final_sha256, name, asset_id}. 해시는 첫 verify 응답의 review_targets.final_sha256.
    // default: null
    review?: ({
      [key: string]: unknown;
    } | null);
    // summary, parts, previews, provenance, all. 생략하면 미리보기 경로 포함, []는 요약. 페이지는 parts만.
    // default: null
    field_groups?: (Array<string> | null);
    // true: parts에 삭제 지정에 쓸 object_id 포함.
    // default: false
    include_ids?: boolean;
    // 부품 목록에서 건너뛸 수(0 이상).
    // default: 0
    offset?: number;
    // 부품 페이지당 1..200개.
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
등록 3DM을 고쳐 저장했다면 다시 측정하고 평면·입면 도면을 새 리비전으로 발행한다. 원본 경로와 이전 도면은 보존한다. 내부 가시선·은선·레이어 표시는 생성하지 않는다.

열린 문서의 연결 블록 갱신·저장은 도면 발행과 별개다. 공유 정의를 갱신하면 기존 배치에도 반영되지만 배치 당시 메타데이터는 유지된다. 새 도면 파일이 필요하면 같은 자산 ID로 asset_03-get_drawings를 조회한다.
```

```ts
declare const tools: {
  mcp__rhino__asset_08_refresh(args: {
    // 편집·저장한 등록 3DM의 자산 ID.
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
검토한 3DM을 라이브러리에 등록해 다른 설계에서도 찾고 배치할 수 있게 한다. 이름과 ID를 정한다. 준비 작업을 거쳤다면 준비한 3DM, 최종 검토한 이름·ID, 준비 작업 폴더를 넘긴다. 등록 결과로 치수와 평면·입면 실루엣 도면을 얻으며 내부 가시선·은선·레이어 표시는 제외한다. 파생 메시가 250,000 삼각형을 넘으면 등록하지 않는다. 결과는 asset_04-get에서 확인한다.
```

```ts
declare const tools: {
  mcp__rhino__asset_09_register(args: {
    // 등록할 3DM. 관리형은 프로젝트 상대, 독립 실행은 절대 경로. 준비한 자산이면 준비 응답의 source_3dm.
    source_3dm: string;
    // 라이브러리 ID. preparation_job을 지정하면 최종 검토 ID와 일치.
    asset_id: string;
    // 표시 이름. preparation_job을 지정하면 최종 검토 이름과 일치.
    name: string;
    // default: "other"
    category?: string;
    // default: null
    tags?: (Array<string> | null);
    // default: ""
    description?: string;
    // default: ""
    source_url?: string;
    // 같은 ID를 바꿀 때만 true.
    // default: false
    replace_existing?: boolean;
    // 완료한 준비 작업의 job_dir. 검토를 거친 다중 형식 변환 등록에 필수. 관리형은 프로젝트 상대, 독립 실행은 절대 경로.
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
자산 아카이브에서 검색어를 모두 만족하는 모델·2D 요소를 찾는다. 모델과 요소 중 하나를 고르거나 도면이 준비된 후보만 남길 수 있다. 원본 파일만 있는 후보는 변환이 필요할 수 있다. 상세 정보와 경로는 후보 ID로 asset_04-get에서 확인한다.
```

```ts
declare const tools: {
  mcp__rhino__asset_10_search_repository(args: {
    // 공백으로 나눈 모든 단어가 일치해야 함(대소문자 무시). 이름·ID·분류·variant·재료 ID·태그·역할에서 검색.
    // default: ""
    query?: string;
    // all, element, model.
    // default: "all"
    kind?: string;
    // true: 준비된 도면인지 검증한 뒤 적합한 후보만 포함.
    // default: false
    drawing_ready?: boolean;
    // 최대 후보 수(1..100으로 보정). total이 반환 수보다 크면 일부 생략.
    // default: 20
    limit?: number;
    // true: 다음 조회에 쓸 ID 포함.
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
라이브러리에서 이름의 일부나 분류·최대 치수로 모델·2D 자산을 찾는다. 한 단어만 맞아도 포함하고, 일치하는 단어가 많은 자산부터 보여준다. 최대 치수를 지정해도 치수가 등록되지 않은 후보는 남을 수 있다. 실제 크기가 중요하면 include_ids=true로 받은 ID를 asset_04-get에 넘겨 확인한다.
```

```ts
declare const tools: {
  mcp__rhino__asset_11_search(args: {
    // 이름·설명·제품·분류·태그 등에서 부분 일치(대소문자 무시).
    // default: ""
    query?: string;
    // 대소문자를 구분하지 않는 정확 일치. 빈 값은 전체 분류.
    // default: ""
    category?: string;
    // 등록 폭 상한(mm). 양수일 때만 적용.
    // default: 0
    max_width_mm?: number;
    // 등록 깊이 상한(mm). 양수일 때만 적용.
    // default: 0
    max_depth_mm?: number;
    // 등록 높이 상한(mm). 양수일 때만 적용.
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

Codex의 RhinoBeyond는 시작할 때 실행 중인 `almondconnect` 호스트들이 Rhino의 View Display Mode Menu에서 확인한 공통 GUID를 공개 입력 `enum`으로 제공한다. 적용 입력은 01의 `rgb_mode`·`edge_mode`, 02의 `views[].display_mode`, 03·04의 `display_mode`다. 호스트가 없거나 목록을 확인할 수 없거나 공통 GUID가 없으면 명시적 모드 입력을 제공하지 않는다. 모드 생략 시 각 도구의 기본 동작을 사용한다. 호스트 또는 메뉴를 바꿨다면 `almondconnect`를 실행한 뒤 새 Codex 세션을 연다. 캡처할 때는 연결된 Rhino의 현재 메뉴와 해당 패스에서 지원하는 렌더 방식도 확인한다.

### 17. capture\_01-conditioning\_pass

```txt
카메라가 이동하는 경로를 따라 RGB·에지·깊이 PNG와 카메라 기록을 저장한다. 경로의 유형과 필요한 이미지 종류를 고른다. 촬영하는 동안 활성 Rhino 뷰가 바뀌며 끝난 뒤 전체 뷰 상태가 복원되지 않을 수 있다. 촬영이 중간에 멈췄다면 errors에서 실패한 프레임 구간을 찾는다. camera_json은 계획 경로 전체를 담으므로 실제로 찍힌 패스와 대상은 PNG에서 확인한다.
```

```ts
declare const tools: {
  mcp__rhino__capture_01_conditioning_pass(args: {
    // 카메라 경로 JSON 문자열. type=orbit: center:[x,y,z], radius, height, 선택 start_deg·end_deg·lens·target_height.
    // type=track: cam0·cam1·target0·target1, 선택 lens. type=keyframes: camera·target·선택 lens를 담은 keyframes 배열.
    // frames 생략: 81. lens는 mm, 좌표는 문서 단위.
    shot: string;
    // 관리형: 선택 Plan의 산출물 폴더 기준 상대 경로(생략: conditioning). 독립 실행에서 생략: 현재 작업 폴더.
    // 폴더 재사용 시 같은 이름을 덮어쓰고 이전 프레임이 일부 남을 수 있음.
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
    // 카메라 기록·영상 조립의 초당 프레임 수. 총 프레임은 shot.frames.
    // default: 16
    fps?: number;
    // 청크당 프레임 수.
    // default: 16
    chunk?: number;
    // RGB 패스에 사용할 뷰 메뉴의 래스터 표시 모드. Codex에서는 시작 시 열거된 GUID.
    // default: "Rendered"
    rgb_mode?: string;
    // 에지 패스에 사용할 뷰 메뉴의 래스터 표시 모드. Codex에서는 시작 시 열거된 GUID.
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
  // executed는 모든 청크 실행 완료, error는 첫 청크 완료 전 실패, partial은 앞선 청크 완료 후 실패.
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
한 시점만으로 판단하기 어려운 부분을 여러 컷으로 비교한다. 결과는 여러 컷을 나란히 담은 PNG 한 장이며 Rhino 작업 화면은 바꾸지 않는다. 현재 모델 화면 그대로의 한 컷이 필요하면 capture_03-current_view를 쓴다.

비교할 부위가 정해져 있다면 먼저 모델에서 대상 GUID를 조회한다. 한 부위를 여러 방향에서 보려면 공통 object_ids를, 컷마다 다른 부위를 보려면 각 views 항목의 object_ids를 쓴다. 두 방식 중 하나를 고른 뒤 각 컷의 방향과 표시 모드를 지정한다.

공통 대상을 평면과 사시에서 비교하는 예: views=[{"direction":"top","display_mode":"Technical"},{"direction":"iso_ne","display_mode":"Shaded"}]. 원래 시점에서 대상만 확대하려면 대상 GUID를 지정하고 direction="current"에 frame_objects:true를 더한다.

그룹 자동 확장과 블록 배치·정의 필터는 지원하지 않는다. 일부 컷이 빠졌다면 complete=false로 표시된다. 실패한 컷과 이유는 tiles에서 확인한다.
```

```ts
declare const tools: {
  mcp__rhino__capture_02_inspection(args: {
    // 타일 1..16개. direction: current(기본), top, bottom, front, back, left, right, iso_ne, iso_nw, iso_se, iso_sw, below_ne, below_nw, below_se, below_sw.
    // display_mode: Rhino 표시 모드 메뉴에 있는 래스터 모드 이름(사용자 정의 포함) 또는 GUID. 이름이 겹치면 GUID. 목록은 inspect_03-get_document_context tool의 sections=["display_modes"].
    // 곡선·와이어=Wireframe, 면·입체=Shaded, 가려진 선을 포함한 선 표현=Technical.
    // label은 최대 120자. 타일별 object_ids는 블록 인스턴스를 제외한 최상위 객체 GUID 최대 512개(중복 금지). 생략·[]이면 공통 범위, 없으면 문서 표시 상태. 픽셀 가시성·가림은 판정하지 않음.
    // frame_objects=true는 current에서 대상 GUID가 있을 때만. 생략하면 원래 카메라 유지.
    views: Array<{
      [key: string]: unknown;
    }>;
    // 타일 너비 128..2048px. 합친 이미지에도 제한 적용.
    // default: 640
    width?: number;
    // 타일 높이 128..2048px. 합친 이미지에도 제한 적용.
    // default: 480
    height?: number;
    // 1..컷 수. 생략하면 자동 배열.
    // default: null
    columns?: (number | null);
    // 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
    // default: ""
    expected_model_path?: string;
    // 활성화하지 않고 사용할 모델 뷰포트 GUID. Layout·Detail에서 작업 중이면 지정하고, 실제 용지가 필요하면 capture_04-defined_view.
    // default: ""
    model_view_id?: string;
    // 모든 타일에 적용할 최상위 객체 GUID 1..4096개(inspect_02-get_objects에서 조회). 중복·빈 배열·타일별 지정과 병용 불가.
    // 공통·타일별 입력에 최상위 블록 인스턴스 ID를 직접 넣으면 전체 호출 실패(오류에 위치·GUID 포함).
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
지금 Rhino 모델 뷰포트에 보이는 색과 선을 PNG로 기록한다. 현재 구도를 그대로 찍거나, 원하는 대상을 선택·확대해서 찍을 수 있다. 여러 방향을 비교하려면 capture_02-inspection을, Layout 용지를 출력하려면 capture_04-defined_view를 쓴다.

대상 지정은 실제 선택과 카메라를 바꾼다. 격리·표시 모드도 지정하면 작업 화면에 적용된다. PNG를 얻지 못해도 이미 바뀐 화면은 복구되지 않는다. 변경 내용은 view_change를 보고, 적용 여부가 미확정이면 현재 화면을 확인한다. PrintDisplay 설정은 유지한다.
```

```ts
declare const tools: {
  mcp__rhino__capture_03_current_view(args: {
    // 실제 선택·확대할 대상 ID(1개 이상). 생략하면 현재 구도. 호출 뒤 선택·카메라를 별도로 확인.
    // default: null
    target_ids?: (Array<string> | null);
    // object, group, block, holon. object 외에는 대상 ID 필요. block은 정의가 아닌 배치 객체 ID.
    // default: "object"
    target_kind?: string;
    // true면 대상 ID 필요, 확대 전에 격리. 잠긴 주변 객체는 보일 수 있음. Rhino Unisolate로 해제.
    // default: false
    isolate?: boolean;
    // 캡처 크기 배율(1..100%).
    // default: 75
    scale_percent?: number;
    // true: 이미지 크기와 픽셀 기준 토큰 추정.
    // default: false
    include_usage?: boolean;
    // Rhino 표시 모드 메뉴에 있는 래스터 모드 이름 또는 GUID. 목록은 inspect_03-get_document_context tool의 sections=["display_modes"].
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
저장한 Named View의 시점이나 실제 Layout 용지를 PNG로 캡처한다. Named View는 활성 화면을 바꾸지 않고 저장된 카메라에서 그린다. Layout은 기존 용지·Detail 모드와 인쇄 색·선폭을 사용한다. PrintDisplay는 유지하며 인쇄 대상이 없으면 빈 용지 PNG도 정상이다.

PNG를 받았다고 파일까지 저장된 것은 아니다. 경로가 필요하면 image_file의 저장 상태를 확인한다. 사용량 추정과 경고는 별도 텍스트로 반환한다.
```

```ts
declare const tools: {
  mcp__rhino__capture_04_defined_view(args: {
    // named_view=저장 시점, layout=실제 용지.
    target_kind: string;
    // 기존 이름 또는 ID. inspect_03-get_document_context의 named_views 또는 layouts에서 조회. 이름은 대소문자 무시, 단일 일치.
    target: string;
    // 출력 크기 상한(1..100%). 전송 한도에 맞춰 더 작아질 수 있음.
    // default: 75
    scale_percent?: number;
    // 이미지 크기와 픽셀 기준 토큰 추정치 포함.
    // default: false
    include_usage?: boolean;
    // Named View 전용. Rhino 표시 모드 메뉴에 있는 래스터 모드 이름 또는 GUID. 생략 시 Shaded.
    // default: ""
    display_mode?: string;
    // true: 최대 200개 레이블. 주변 레이블과 겹칠 수 있음. Layout Detail에는 미지원.
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
연결할 Rhino 문서는 `targets`에서, 이미 요청한 새 창의 상태는 `starts`에서 찾는다. 작업할 문서를 고르면 같은 `targets` 항목의 `host_id`와 저장된 `model_path`를 `connect_02-session`에 전달한다. 기존 연결도 `targets`에 나타난다. 이 조회로는 `selected_connection_id`가 바뀌지 않는다.
```

beyond

```txt
연결할 Rhino 문서는 `targets`에서, 이미 요청한 새 창의 상태는 `starts`에서 찾는다. 작업할 문서를 고르면 같은 `targets` 항목의 `host_id`와 저장된 `model_path`를 `connect_02-session`에 전달한다.
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
이미 열린 Rhino 문서에 연결하거나 기존 연결로 작업 대상을 바꾼다. `ready`이면 이후 일반 호출은 그 문서에서 실행된다. `recovering`·`unconfirmed`이면 이전 실행 결과를 먼저 확인한다. 파일 자체를 열려면 `connect_03-start_session`을 쓴다.
```

beyond

```txt
이미 열린 Rhino 문서에 연결한다. `ready`이면 후속 호출에 반환된 `connection_id`를 사용한다. `recovering`·`unconfirmed`이면 이전 실행 결과를 먼저 확인한다. 파일 자체를 열려면 `connect_03-start_session`을 쓴다.
```

```ts
declare const tools: {
  mcp__rhino__connect_02_session(args: {
    // `connect_01-list_up`의 `targets`에서 고른 문서의 호스트 ID.
    host_id: string;
    // 같은 `targets` 항목의 저장된 .3dm 경로.
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
저장된 .3dm을 새 Rhino 창에서 열고 일반 호출의 대상으로 연결한다. 이미 열린 문서는 `connect_02-session`으로 선택한다. 시작이 확인되지 않으면 새 요청 대신 같은 모델 경로와 `request_id`로 재조회한다. 일반 작업은 연결이 `ready`가 된 뒤 진행한다.
```

beyond

```txt
저장된 .3dm을 새 Rhino 창에서 열고 연결한다. `ready`이면 해당 문서의 후속 호출에 반환된 `connection_id`를 쓴다. 시작이 확인되지 않으면 새 요청 대신 같은 모델 경로와 `request_id`로 재조회한다.
```

```ts
declare const tools: {
  mcp__rhino__connect_03_start_session(args: {
    // 저장된 로컬 .3dm의 절대 경로.
    model_path: string;
    // 시작 시도마다 고유한 값. 지연·미확인 시 같은 모델 경로와 값으로 기존 요청 조회.
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
선택한 연결만 해제하고 Rhino 창과 문서는 열어 둔다. 문서를 저장한 뒤 Rhino까지 닫으려면 `connect_05-close_session`을 쓴다.
```

beyond

```txt
지정한 `connection_id`의 연결만 해제하고 Rhino 창과 문서는 열어 둔다. 문서를 저장한 뒤 Rhino까지 닫으려면 `connect_05-close_session`을 쓴다.
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
선택한 Rhino 문서를 저장한 뒤 Rhino까지 닫을 때 쓴다. 진행 중이거나 결과가 미확인인 작업이 남아 있으면 종료 요청을 거부한다. 저장이 확인된 뒤에만 Rhino를 닫는다. 창을 남겨 두고 연결만 끊으려면 `connect_04-disconnect`를 쓴다.
```

beyond

```txt
지정한 Rhino 문서를 저장한 뒤 Rhino까지 닫을 때 쓴다. 진행 중이거나 결과가 미확인인 작업이 남아 있으면 종료 요청을 거부한다. 저장이 확인된 뒤에만 Rhino를 닫는다. 종료 결과를 다시 확인하려면 처음 사용한 `connection_id`와 `request_id`를 그대로 쓴다.
```

```ts
declare const tools: {
  mcp__rhino__connect_05_close_session(args: {
    // 새 종료 시도마다 고유한 값. 지연·미확인 시 같은 값으로 기존 결과 조회.
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
Almond에 어떤 도구가 있는지 찾아보거나 Rhino 작업에 필요한 기술 자료를 읽는다. 객체에 어떤 메타데이터 키를 쓰는지는 `metadata`, 스크립트 작성 참고는 `rhino_scripting`, RhinoCode로 코드나 명령을 실행하는 지침은 `rhinocode`에서 확인한다. `guide_version`이 같은 자료는 다시 읽지 않아도 된다.
```

```ts
declare const tools: {
  mcp__rhino__context_01_get_policy(args: {
    // 생략·빈 문자열: `basic`(도구 목록). 자료 종류는 `available_policies` 참조.
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
작업할 Rhino 문서의 상태·Named View·Layout·레이어와 현재 Plan·Loop의 산출물 위치를 확인한다. 산출물 위치만 보려면 `sections=["locations"]`를 쓴다. 작업할 Plan은 `plan_10-set_working`에서 선택한다.

활성 문서를 제외한 Worksession 첨부 파일은 `project.worksession_files`, Phase나 Scene에 쓸 등록 파일명은 프로젝트 DB의 `project.files`에서 확인한다. 참조 파일을 붙이거나 떼도 등록 목록은 바뀌지 않는다. 등록·설명 갱신에는 `context_05-upsert_project_file`을 쓰며, 프로젝트 내부 경로의 기준은 `project_root`다.
```

```ts
declare const tools: {
  mcp__rhino__context_04_get_project_info(args: {
    // `project`, `document`, `named_views`, `layouts`, `layer_tree`, `locations`, `runtime`. 생략: `runtime`을 제외한 전체.
    // `locations`·`runtime`만 요청하면 Rhino 문서를 직접 관찰하지 않음.
    // `named_views`·`layouts`: 각각 최대 128개, ID 항상 포함.
    // default: null
    sections?: (Array<string> | null);
    // 후속 작업에 필요한 Plan·Step ID 등 선택적 식별자 포함.
    // default: false
    include_ids?: boolean;
    // `project.files`의 페이지 크기(정수 1..500).
    // default: 50
    files_limit?: number;
    // `project.files`에서 건너뛸 행 수(0 이상 정수).
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
Phase·Scene에서 파일을 지정할 수 있도록 모델 파일명을 프로젝트 카탈로그에 등록하거나 기존 설명을 갱신한다. Rhino에서 모델을 열거나 Worksession에 참조로 붙이지는 않는다. 등록 결과는 `context_04-get_project_info`의 `project.files`에서 확인한다.
```

```ts
declare const tools: {
  mcp__rhino__context_05_upsert_project_file(args: {
    // 폴더를 뺀 프로젝트 내 고유 파일명. Windows 기준으로 비교하며, 갱신 시 기존 표기 유지.
    file_name: string;
    // 생략·null: 기존 설명 유지. 빈 문자열: 설명 삭제.
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
다이어그램 ID로 등록 정보와 원본 파일의 유무를 확인한다. 배치나 검토에 필요한 치수·출처 같은 항목만 골라 볼 수 있다. 원본이 없어도 등록 정보는 조회된다.
```

```ts
declare const tools: {
  mcp__rhino__diagram_01_get(args: {
    // `diagram_02-list` 또는 `diagram_04-search`의 ID. 대소문자·공백까지 그대로.
    asset_id: string;
    // 추가 식별자 포함. 입력한 `asset_id`는 결과에 반복하지 않음.
    // default: false
    include_ids?: boolean;
    // `dimensions`, `drawing`, `metadata`, `source`, `paths`, `audit`, `all`. 생략·빈 배열: 요약. `all`: 목록 외 등록 필드도 포함.
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
등록된 사람·나무·기호 등 2D 벡터·CAD 다이어그램을 분류별로 둘러본다. 원본이 없는 등록 항목도 목록에 포함한다. 상세 조회나 배치로 이어가려면 `include_ids=true`로 자산 ID를 받는다. 키워드나 치수로 후보를 좁히려면 `diagram_04-search`를 쓴다.
```

```ts
declare const tools: {
  mcp__rhino__diagram_02_list(args: {
    // 분류명 전체 일치(대소문자 무시). 비우면 모든 분류.
    // default: ""
    category?: string;
    // 페이지 크기. 1..50으로 보정.
    // default: 20
    limit?: number;
    // 건너뛸 항목 수. 음수는 0으로 보정.
    // default: 0
    offset?: number;
    // 상세 조회·배치에 쓸 자산 ID 포함.
    // default: false
    include_ids?: boolean;
    // `dimensions`, `drawing`, `metadata`, `source`, `paths`, `audit`, `all`. 생략·빈 배열: 요약.
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
등록된 SVG·DWG·DXF 다이어그램을 지정한 위치·회전·축척으로 Rhino에 배치한다. 결과의 `object_guid`로 배치된 블록 인스턴스를 식별한다. `requires_reconciliation=true`면 다시 호출하기 전에 실제로 배치됐는지 확인한다.
```

```ts
declare const tools: {
  mcp__rhino__diagram_03_place(args: {
    // `diagram_02-list` 또는 `diagram_04-search`에서 `include_ids=true`로 받은 라이브러리 자산 ID.
    asset_id: string;
    // 삽입점 X(현재 문서 단위).
    // default: 0
    x?: number;
    // 삽입점 Y(현재 문서 단위).
    // default: 0
    y?: number;
    // 삽입점 Z(현재 문서 단위).
    // default: 0
    z?: number;
    // 월드 Z축 기준 회전각(도).
    // default: 0
    rotation_degrees?: number;
    // 균일 축척(양수). 1: 문서 단위로 환산한 원래 크기.
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
도면에 쓸 2D 다이어그램을 키워드·분류·최대 치수로 찾는다. 검색 결과에는 원본 파일이 없는 등록 항목도 포함된다. 배치를 검토할 후보는 `include_ids=true`로 ID를 받아 `diagram_01-get`에서 원본 상태를 확인한다.
```

```ts
declare const tools: {
  mcp__rhino__diagram_04_search(args: {
    // 여러 검색어는 OR로 결합. 비우면 키워드 조건 없음.
    // default: ""
    query?: string;
    // 분류명 전체 일치(대소문자 무시). 비우면 모든 분류.
    // default: ""
    category?: string;
    // 최대 너비(mm). 0 이하: 이 치수는 제한하지 않음.
    // default: 0
    max_width_mm?: number;
    // 최대 깊이(mm). 0 이하: 이 치수는 제한하지 않음. 등록 치수는 추정치일 수 있음.
    // default: 0
    max_depth_mm?: number;
    // 최대 높이(mm). 0 이하: 이 치수는 제한하지 않음.
    // default: 0
    max_height_mm?: number;
    // 페이지 크기. 1..50으로 보정.
    // default: 10
    limit?: number;
    // 건너뛸 항목 수. 음수는 0으로 보정. 다음 페이지에도 같은 필터 사용.
    // default: 0
    offset?: number;
    // 상세 조회·배치에 쓸 자산 ID 포함.
    // default: false
    include_ids?: boolean;
    // `dimensions`, `drawing`, `metadata`, `source`, `paths`, `audit`, `all`. 생략·빈 배열: 요약. 등록 정보에 따라 일부 세부 값은 생략될 수 있음.
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
Rhino 레이어의 화면 표시와 인쇄 표현을 한 레시피에 맞춘다. `drawing_05-list_recipes`에서 `include_ids=true`로 후보의 `recipe_id`를 얻는다. 설정을 먼저 보려면 같은 ID로 `drawing_02-get_recipe`를 조회한다.

레시피에 맞춰 레이어 계층과 표시색·출력색·출력 선 두께·선종류를 설정한다. 같은 경로의 기존 레이어도 갱신하며, 개별 객체는 수정하지 않는다. 선종류는 같은 이름의 기존 정의가 없을 때만 Almond 매니페스트에서 가져온다.

변경은 전용 Undo 기록으로 묶고, 실패하면 복구를 시도한다. `mutation_state`는 `none`·`completed`·`rolled_back`·`unknown`을 구별한다. `requires_reconciliation=true`면 재시도하기 전에 Rhino 문서의 실제 상태를 본다. 레시피의 `review_preparation.print_display=true`이면 적용 성공 시 PrintDisplay 설정 명령을 안내한다.
```

```ts
declare const tools: {
  mcp__rhino__drawing_01_apply_style(args: {
    // `drawing_05-list_recipes` 또는 `drawing_02-get_recipe`의 레시피 ID. 생략: 파일명 순으로 처음 로드된 레시피 적용.
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
적용하려는 도면 스타일의 권장 축척과 레이어·출력 설정을 읽는다. 적용할 레시피를 먼저 찾아야 하면 `drawing_05-list_recipes`, 설정을 문서에 반영하려면 `drawing_01-apply_style`을 쓴다.
```

```ts
declare const tools: {
  mcp__rhino__drawing_02_get_recipe(args: {
    // `drawing_05-list_recipes`에서 `include_ids=true`로 얻은 레시피 ID 또는 이미 아는 ID.
    recipe_id: string;
    // 레시피의 추가 식별자 포함.
    // default: false
    include_ids?: boolean;
    // `scales`, `parameters`, `source`, `audit`, `all`. 생략·빈 배열: 요약.
    // 권장 축척·레이어·출력 설정: `["scales","parameters"]`.
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
등록 PAT 파일에서 Rhino 문서에 쓸 해치 패턴 정의를 가져온다. 같은 이름의 정의가 있으면 재사용한다. 이 호출은 해치 객체를 그리지 않는다.
```

```ts
declare const tools: {
  mcp__rhino__drawing_04_import_hatches(args: {
    // 원본 .pat이 있는 도면 자산 ID. 연결된 도면 자산 라이브러리의 `asset_05-list`·`asset_11-search`에서 `include_ids=true`로 확인.
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
사용할 수 있는 도면 스타일 레시피를 나열한다. 권장 축척이나 출력 설정을 더 보려면 `drawing_02-get_recipe`, 레시피를 문서에 적용하려면 `drawing_01-apply_style`을 쓴다.
```

```ts
declare const tools: {
  mcp__rhino__drawing_05_list_recipes(args: {
    // 조회·적용에 쓸 `recipe_id` 포함.
    // default: false
    include_ids?: boolean;
    // `scales`, `parameters`, `source`, `audit`, `all`. 생략·빈 배열: 요약.
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
클리핑 평면을 기준으로, Rhino에서 편집할 단면선·가시 입면선·해치를 저장된 활성 모델에 만든다. 화면 이미지가 아니라 실제 도면 객체가 필요할 때 쓴다.

활성 모델 또는 Worksession 첨부 파일에서 절단할 클리핑 평면의 GUID를 고른다. `Create`는 새 도면을 만들거나 기존 것을 교체하며 배치 원점을 지정할 수 있다. `Update`는 저장 위치에서 다시 뽑기 때문에 수동 편집을 덮어쓸 수 있다. `Move`는 새 원점으로 옮기기만 하므로 수동 편집과 객체 GUID가 유지된다. 첨부 모델의 형상까지 절단·투영할지는 `Create`·`Update`에서 `include_attachments`로 정한다.

성공한 평면마다 도면 객체 GUID(`object_ids`)와 실제 배치 평면(`draw_plane`)을 받는다. 일부만 완료됐거나 취소된 경우에도 먼저 만든 도면은 남을 수 있다.

Rhino는 120초에 취소를 요청한다. 안전한 지점에서 작업을 멈추고 정리를 확인하면 `timeout`과 컷별 결과를 반환한다. 응답 대기가 먼저 끝나면 중단 여부는 미확인이다. 성공과 중단 시의 후속 조치는 `next_step_guide`에서 확인한다.

`mutation_state`가 `partial` 또는 `unknown`이고 `requires_reconciliation=true`면 실제 도면이나 Undo 결과를 확인하기 전에는 재실행하지 않는다. `recovery.attempts`는 객체·속성·레이어별 복구 시도, `tracked_changes_restored`는 추적한 변경의 복구 여부만 나타낸다.
```

```ts
declare const tools: {
  mcp__rhino__drawing_06_generate_plan_section(args: {
    operation: "Create" | "Update" | "Move";
    // 절단 기준인 클리핑 평면의 GUID. 활성 모델·Worksession 첨부 파일에서 하나 이상 지정(중복은 1회 처리).
    clipping_ids: Array<string>;
    // 절대 도면 원점 `[x,y]`(Z=0) 또는 `[x,y,z]`(문서 단위, 유한한 값). 키는 이 호출의 `clipping_ids` 중 하나.
    // `Create`: 생략한 평면은 저장된 `draft_plane`의 원점 사용(저장값이 없으면 월드 원점). `Move`: 모든 평면에 지정. `Update`: 생략.
    // default: null
    points?: ({
      [key: string]: Array<(number | number)>;
    } | null);
    // 원본 단면 스타일의 채움과 형상 조건에 따라 해치 생성.
    // default: true
    hatch?: boolean;
    // 입면 투영에서 작은 상세 보호.
    // default: false
    small_details?: boolean;
    // 가까운 입면선의 출력 두께(mm, 양수, `far_width` 이상).
    // default: 0.09
    near_width?: (number | number);
    // 먼 입면선의 출력 두께(mm, 양수, `near_width` 이하).
    // default: 0.04
    far_width?: (number | number);
    // 가까운 입면선 농도(%, 0..100, `far_dark` 이상).
    // default: 80.0
    near_dark?: (number | number);
    // 먼 입면선 농도(%, 0..100, `near_dark` 이하).
    // default: 45.0
    far_dark?: (number | number);
    // Worksession 첨부 형상을 절단·투영 범위에 포함. `Move`에는 미적용. 생략 시 `Create`: 활성 모델만 / `Update`: 저장 설정.
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
  // success, partial, cancelled(사용자 취소), timeout(120초 취소 후 중단·정리 확인), error
  status?: string;
  // completed, partial, cancelled, failed
  drawing_status?: string;
  mutation_state?: string;
  requires_reconciliation?: boolean;
  unconfirmed_clipping_ids?: Array<string>;
  next_step_guide?: string;
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
    stop_reason?: "deadline" | "user";
    // 중복을 제외한 클리핑 요청 수
    requested?: number;
    completed?: number;
    requires_reconciliation?: boolean;
    results?: Array<{
      clipping_id?: string;
      name?: string | null;
      status?: "completed" | "failed" | "skipped" | "cancelled" | "not_started" | "unconfirmed";
      mutation_state?: string;
      cleanup_error?: string;
      // 생성·갱신·이동에서 관찰한 도면 객체 GUID. 최종 상태 미확인 시 실제 문서와 대조.
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
색인된 Grasshopper 정의에서 Kangaroo·Karamba 등 물리 관련 컴포넌트의 이름 단서와 설명·메타데이터를 찾는다. 추출한 문자열을 바탕으로 찾은 단서이므로 전체 구성·연결 관계나 실행 가능성을 증명하지는 않는다. JSON만 있는 항목은 메타데이터만 반환한다. 실행할 캡슐은 `grasshopper_02-list_capsules`에서 감사 상태와 함께 찾는다.
```

```ts
declare const tools: {
  mcp__rhino__grasshopper_01_get_logic(args: {
    // 확장자를 뺀 파일명(대소문자 무시). `grasshopper_03-list_library`의 `logic_names` 참조.
    logic_id: string;
    // 추가 식별자 포함. 입력한 `logic_id`는 결과에 반복하지 않음.
    // default: false
    include_ids?: boolean;
    // `ports`, `definition`, `source`, `paths`, `audit`, `all`. 실제 제공되는 필드에만 적용.
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
해석·생성·형태 탐색·집합 구성에 쓸 Grasshopper 캡슐을 찾는다. `grasshopper_04-run_definition`으로 실행할 후보라면 감사 상태를 확인하고 `include_ids=true`와 `field_groups=["ports"]`로 ID와 포트 정보를 받는다. 감사를 통과했어도 파일이 있거나 실행이 성공한다는 보장은 없다.
```

```ts
declare const tools: {
  mcp__rhino__grasshopper_02_list_capsules(args: {
    // `analyze`, `generate`, `form_find`, `aggregate`(대소문자 무시).
    // default: ""
    capability?: string;
    // 실행 감사를 통과한 캡슐만 조회.
    // default: false
    audited_only?: boolean;
    // 실행에 쓸 `capsule_id` 포함. `field_groups`의 `all`과 별도.
    // default: false
    include_ids?: boolean;
    // `ports`, `definition`, `source`, `paths`, `audit`, `all`. 포트의 타입·단위·필수 여부가 필요하면 `ports`. 생략·빈 배열: 요약.
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
로컬 Grasshopper 라이브러리에서 참고할 로직의 이름을 찾는다. `logic_names`에서 고른 이름으로 `grasshopper_01-get_logic`에서 상세를 읽는다. 실행할 캡슐을 찾으려면 `grasshopper_02-list_capsules`를 쓴다.
```

```ts
declare const tools: {
  mcp__rhino__grasshopper_03_list_library(args: {
    // `logic_names`와 같은 값의 `logic_ids` 추가.
    // default: false
    include_ids?: boolean;
    // `paths`·`all`: 라이브러리 경로 포함. `ports`·`definition`·`source`·`audit`은 목록에 미적용.
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
실행 감사를 통과한 Grasshopper 캡슐을 Rhino에서 계산하고 포트별 결과를 받는다. 수치 등 값만 출력하는 캡슐은 문서에 형상을 추가하지 않는다. 캡슐의 출력 포트에 곡선·메시·Brep이 선언되어 있으면, 모든 출력 포트를 확인한 뒤 해당 형상을 하나의 Undo 기록으로 Rhino 문서에 만든다(베이크).

`mutation_state`로 `none`·`completed`·`rolled_back`·`unknown`을 구분한다. `requires_reconciliation=true`면 재실행하지 말고 `baked_guids`와 현재 문서에서 형상의 실제 반영을 확인한다.
```

```ts
declare const tools: {
  mcp__rhino__grasshopper_04_run_definition(args: {
    // `grasshopper_02-list_capsules`에서 얻은 감사 통과 캡슐 ID. 예: `karamba_beam_v1`.
    capsule_id: string;
    // 키: `ALMOND_IN_` 포트 이름. `grasshopper_02-list_capsules`의 `field_groups=['ports']`로 타입·단위·필수 여부 확인.
    // 형상은 `{"guids":["객체 GUID"]}`. 숫자·정수·문자열·불리언은 JSON 값, `number[]`·`integer[]`·`string[]`은 평탄한 배열.
    inputs: {
      [key: string]: unknown;
    };
    // 확률적 정의에만 쓰는 정수 시드.
    // default: null
    seed?: (number | null);
    // 솔버 시간 한도(초, 0 초과 600 이하).
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
중첩 블록의 내부 구성과, 정의 하나를 바꾸면 영향을 받는 다른 배치를 읽는다. 계층을 보려면 `outline`, 대상 정의를 공유하는 배치와 참조·링크 제한을 보려면 `resolve-block`을 쓴다. 두 모드 모두 문서를 수정하지 않는다.

대상 블록의 경로가 없으면 바깥 블록을 선택하고 `outline`에 `include_ids=true`, `options.field_groups=["objects"]`를 지정한다. 반환된 대상 블록의 `path`를 `resolve-block`의 `options.path`로 넘긴다.

`definition_impact.complete`는 영향 범위를 끝까지 계산했는지, `occurrences_truncated`는 반환 목록이 잘렸는지 나타낸다. 계산이 끝나지 않았다면 목록에 나온 배치가 전부라고 단정하지 않는다. 정의 내부 구성원 ID를 문서 객체의 편집 GUID로 쓰지 않는다. 문서 객체는 `inspect_02-get_objects`에서 조회한다.
```

```ts
declare const tools: {
  mcp__rhino__inspect_01_analyze_nested_blocks(args: {
    // `outline` 또는 `resolve-block`.
    mode: string;
    // `outline` 대상: `ids`(루트) 또는 `path`(특정 분기). 둘 다 생략하면 `scope`: `selected`(기본), `viewport`, `document`.
    // `outline` 반환 범위: `depth` 0..64(기본 64), `max_items` 1..5000(기본 200), `max_bytes` 2048..262144(기본 48000).
    // `outline`의 `field_groups`: `summary`(기본), `objects`, `annotations`, `transforms` 중 1개 이상을 배열로 지정.
    // `include_geometry`·`annotations`: 형상·주석 추가. `annotation_layer`: TextDot 레이어 필터. `field_groups` 없이 형상·주석 옵션을 쓰면 기존 상세 모드.
    // `resolve-block`: `path`만 지정. 최상위부터 대상 블록까지 GUID 1..65개.
    options: {
      [key: string]: unknown;
    };
    // 생략: 연결 문서 사용. 지정: 경로가 일치할 때만 조회.
    // default: ""
    expected_model_path?: string;
    // 후속 조회에 사용할 ID와 GUID 경로 포함.
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
객체를 조회하여 필요한 정보를 얻는 툴로, 문서 전체·현재 상태·활성 뷰포트 내부 중 하나를 조회 대상으로 선택한다. 레이어·이름·객체 유형·블록 조건에 포함/제외 목록을 함께 지정할 수 있다. 그룹 범위는 `group_ids`로, User Text·User Dictionary는 키와 값 조건으로 좁힌다. 출력 형식은 객체 목록인 `objects`(기본값), 그룹·블록 계층인 `hierarchy`, 레이어·객체 유형별 집계인 `summary` 중 택한다. 다음 편집에 쓸 GUID가 필요하면 `output.include_ids=true`를 지정한다. 조회는 현재 선택을 유지한다.

호출 예: 활성 뷰포트에서 2F::Wall 레이어 객체의 GUID 조회.
{"scope":"inside_viewport","filters":{"layer":{"include":["2F::Wall"]}},"output":{"include_ids":true}}
```

```ts
type IncludeExclude<T> = { include?: T[]; exclude?: T[] };
type OnePerSide<T> = { include?: [T]; exclude?: [T] };
type UserTextTerm = { key: string; any_of: string[] };
type DictionaryTerm = { source: "attributes" | "geometry"; key: string; any_of: Array<string | boolean | number> };
declare const tools: {
  mcp__rhino__inspect_02_get_objects(args: {
    // document: 연결 문서 전체(숨김·잠금 포함)
    // current(기본): 숨김·잠금 제외, 화면 밖 포함
    // inside_viewport: current 중 활성 뷰포트 경계 안·교차(가림·클리핑 미판별)
    scope?: "document" | "current" | "inside_viewport";
    result_mode?: "objects" | "hierarchy" | "summary"; // 기본: objects
    selected?: boolean; // true: current에서 이미 선택된 객체만. 기본 false
    object_ids?: string[]; // 이미 아는 객체 GUID로 조회. document 전용
    filters?: {
      layer?: IncludeExclude<string>; // 전체 경로·GUID 혼용 가능(include/exclude 각 배열)
      name?: IncludeExclude<string>;
      object_type?: IncludeExclude<string>;
      block?: IncludeExclude<string>; // 해당 정의를 쓰는 배치 인스턴스 조회
      group?: {
        include?: string[]; // 1..64개 그룹 이름·GUID
        include_mode?: "any" | "all"; // include가 2개 이상일 때만 필수
        exclude?: string[];
        exclude_mode?: "any" | "all"; // exclude가 2개 이상일 때만 필수. 조건에 해당하면 제외
      };
      material?: IncludeExclude<string>; // 전면 실효 재질 이름/GUID. 직접 지정·레이어 상속을 함께 조회
      user_text?: UserTextTerm[] | OnePerSide<UserTextTerm>;
      user_dictionary?: DictionaryTerm[] | OnePerSide<DictionaryTerm>;
      layer_paths?: string[];
      name_contains?: string;
      object_types?: string[];
    };
    group_ids?: string[]; // 기존 그룹 GUID 범위. hierarchy에서는 시작 그룹을 지정.
    inside_window?: boolean; // current에서 기존 뷰포트 교차 조건
    expected_model_path?: string;
    output?: {
      fields?: string[]; // 결과에 담을 속성. summary에는 사용하지 않음
      include_ids?: boolean; // 기본: false
      include_geometry?: boolean; // objects에서 상세 형상 포함, 기본: false
      limit?: number; // 한 페이지 행 수, 기본: 50
      offset?: number; // 다음 페이지에는 응답의 next_offset 사용
      expected_snapshot?: string; // 다음 페이지에는 첫 응답의 snapshot 사용
    };
    // output의 여섯 필드는 기존 호출처럼 최상위에도 지정할 수 있다. 같은 필드는 output 우선.
    fields?: string[];
    include_ids?: boolean;
    include_geometry?: boolean;
    limit?: number;
    offset?: number;
    expected_snapshot?: string;
    recursive?: boolean;
    depth?: number;
    face_offset?: number;
    face_limit?: number;
    expected_geometry_crcs?: Record<string, number>;
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
이어서 작업할 Rhino 문서와 현재 편집 상태를 확인하거나, 호출에 넘길 뷰·레이아웃을 찾는다. 뷰포트·Named View·Layout·레이어 계층·표시 모드 중 필요한 항목만 고른다. Named View·Layout·표시 모드는 이름과 ID가 함께 나온다. 표시 모드 이름이 중복되면 캡처에서 GUID로 지정한다. 현재 화면을 이미지로 받아야 한다면 capture_03-current_view tool을 쓴다.
```

```ts
declare const tools: {
  mcp__rhino__inspect_03_get_document_context(args: {
    // 선택: document, viewport, editor, viewports, named_views, layouts, layer_tree, display_modes.
    // 생략/null: document, named_views, layouts, layer_tree, display_modes. []: 항목 조회 안 함.
    // named_views·layouts·display_modes: 목록별 최대 128개. display_modes는 Rhino 표시 모드 메뉴에 등재된 모드만 반환.
    // default: null
    sections?: (Array<string> | null);
    // 뷰포트 등 선택적 ID 포함. named_views·layouts·display_modes의 ID는 항상 반환.
    // default: false
    include_ids?: boolean;
    // sections에 editor를 지정했을 때 공급자·명령·Undo 근거 포함.
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
화면에서 선택한 객체를 단서로 관련 작업을 찾을 수 있다. 객체가 속한 Holon과 그 Holon 또는 상위 Holon을 대상으로 등록한 Plan을 반환한다. 일치한 Holon만으로 Plan의 전체 대상을 판단하지 않는다. 결과의 `plan_id`로 등록 대상 전체를 확인하려면 inspect_05-resolve_targets tool을 쓴다.

저장된 문서의 일반 모델에서 사용한다. 선택 객체를 모두 검사했는지는 `selection_truncated`, 관련 Plan을 모두 반환했는지는 `truncated`로 확인한다.
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
    // 상세: steps, references, geometry, artifacts, description, scope, audit, all. 생략/[]: 요약.
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
이 Plan에 작업 대상으로 등록된 Scene·Holon을 찾는다. Plan ID를 넣으면 등록된 대상의 ID와 저장된 Holon 정보를 받는다. Step ID는 그 Plan에 속하는지 확인하는 데만 쓰며 대상 범위는 Plan과 같다. Scene 안의 Holon 전체나 현재 Rhino 구성원은 조회하지 않는다.
```

```ts
declare const tools: {
  mcp__rhino__inspect_05_resolve_targets(args: {
    // plan_08-list tool의 plans[].plan_id 또는 plan_05-get tool의 Plan id.
    plan_id: string;
    // plan_05-get tool의 해당 Plan 상세에 있는 Step ID. 지정해도 대상 범위는 Plan 그대로.
    // default: ""
    step_id?: string;
    // 상세: references, geometry, scope, audit, all. 생략/[]: 요약.
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
닫힌 솔리드 중 실제로 부피가 겹치는 쌍이 몇 개인지 확인한다. 성공하면 객체 쌍의 목록 없이 건수만 나온다. 겹침이 있으면 같은 `object_ids`와 `include_block`으로 intersect_02-resolve tool에서 겹친 쌍을 화면으로 검토한다.

건수는 검사를 모두 마쳐야 반환한다. 검사 범위의 0건은 간격과 설계 전체의 적합성을 보장하지 않는다. 계산하지 못한 대상·쌍이나 페이지 오류가 있으면 건수 대신 `assessment=incomplete`로 반환한다. 면이 닿기만 해도 계산이 실패할 수 있다. 미판정 결과에는 확인된 대상·이유와 해당 페이지의 모델 공차·단위를 담는다. `null`은 확인 불가다.
```

```ts
declare const tools: {
  mcp__rhino__intersect_01_find(args: {
    // 현재 최상위 Rhino 객체의 고유 GUID 1..512개. 내부 페이지는 전체를 한 범위로 검사.
    object_ids: Array<string>;
    // true: 배치 변환을 적용한 중첩 블록 구성원 포함. false: 블록 제외.
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
  // 미판정. 전체 범위의 겹침 건수 미확정.
  assessment?: "incomplete";
  // 검사할 수 없는 것으로 확인된 객체와 사유. null은 확인 불가.
  unsupported_objects?: Array<{ [key: string]: unknown }> | null;
  // 계산을 마치지 못한 쌍과 사유. null은 확인 불가.
  failed_pairs?: Array<{ [key: string]: unknown }> | null;
  // 미판정이 발생한 검사에서 확인한 모델 길이 공차. null은 확인 불가.
  tolerance_model_units?: number | null;
  // 해당 검사에서 확인한 문서 길이 단위. null은 확인 불가.
  document_units?: string | null;
  [key: string]: unknown;
};
```

### 48. intersect\_02-resolve

```txt
겹친 객체를 비교해 한쪽에서 겹침을 제거하거나 양쪽을 그대로 둔다. 첫 호출에 `object_ids`를 지정해 비교 화면을 받는다. 다음 호출에 `object_ids` 대신 화면의 `review_id`와 `choice=1` 또는 `2`를 보내면 그 번호로 표시된 객체에서 겹침을 제거한다. `choice="skip"`은 수정 없이 넘어간다. 블록 구성원은 비교만 가능하며 자동으로 잘라내지는 못한다.

검토 화면을 만들 때 실제 Rhino 카메라와 선택이 바뀐다.

다음 쌍의 검사가 미판정(`assessment=incomplete`)이면 확인된 대상·이유·모델 공차·단위를 돌려준다. 확인하지 못한 값은 `null`이다. 앞서 제출한 수정은 이미 적용됐을 수 있다. `previous_result`와 실제 형상을 확인하기 전에는 같은 선택을 다시 보내지 않는다.
```

```ts
declare const tools: {
  mcp__rhino__intersect_02_resolve(args: {
    // 새 검토: 현재 최상위 객체의 고유 GUID 1..512개. 이어서 검토/선택 제출: 생략.
    // default: null
    object_ids?: (Array<string> | null);
    // 새 검토에 배치 변환을 적용한 중첩 블록 구성원 포함. 블록 정의는 편집 불가.
    // default: false
    include_block?: boolean;
    // 비교 화면에서 반환한 ID. choice 제출 시 필수. 완료·대체된 검토 ID는 재사용 불가.
    // default: ""
    review_id?: string;
    // 1/2: 해당 번호 객체에서 겹친 부분 제거. skip: 두 객체 유지.
    // 제출: review_id 필수, object_ids 생략. 검토 시작/재개만 할 때: choice 생략.
    // default: null
    choice?: (number | "skip" | null);
    // 새 검토의 속성 User Text 조건. 예: [{"key":"floor","any_of":["2F"]}].
    // 한 객체가 모든 조건에 맞는 쌍만 표시. 두 값은 objects[].attributes.user_strings.values 참조.
    // 중첩 블록: 정의 구성원의 속성 기준.
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
    // 미판정. 전체 범위의 겹침 건수 미확정.
    assessment?: "incomplete";
    // 검사할 수 없는 것으로 확인된 객체와 사유. null은 확인 불가.
    unsupported_objects?: Array<{ [key: string]: unknown }> | null;
    // 계산을 마치지 못한 쌍과 사유. null은 확인 불가.
    failed_pairs?: Array<{ [key: string]: unknown }> | null;
    // 미판정이 발생한 검사에서 확인한 모델 길이 공차. null은 확인 불가.
    tolerance_model_units?: number | null;
    // 해당 검사에서 확인한 문서 길이 단위. null은 확인 불가.
    document_units?: string | null;
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
지정한 Rhino 객체에 라이브러리 렌더 재료를 입힌다. 구축 정보를 함께 기록하거나 재료는 바꾸지 않고 정보만 남길 수도 있다. 재료는 레이어를 바꾸지 않고 객체에 직접 지정한다. 같은 GUID는 한 번만 처리하며, 기록한 구축 정보는 inspect_02-get_objects tool에서 User Text로 읽거나 검색한다.

`success`는 전체 처리, `partial`은 일부 처리다. `executed`라면 적용된 객체가 없거나 적용 결과를 읽지 못한 상태이므로, 그대로 재시도하기 전에 Rhino에서 객체를 확인한다.
```

```ts
declare const tools: {
  mcp__rhino__model_01_assign_material(args: {
    // 관찰·생성 결과에서 확인한 현재 Rhino 객체 GUID.
    guids: Array<string>;
    // model_04-list_materials tool에 include_ids=true로 요청해 받은 표준 재료 ID.
    material_id: string;
    // default: true
    apply_render_material?: boolean;
    // Almond 재료·구축 메타데이터를 객체 속성에 기록.
    // default: false
    attach_metadata?: boolean;
    // attach_metadata=true일 때 기록할 구조 역할
    // default: ""
    structural_role?: string;
    // attach_metadata=true로 기록할 라이브러리 구축 시스템 ID. construction_reference와 같은 시스템이어야 함.
    // default: ""
    construction_system?: string;
    // attach_metadata=true일 때 기록할 층 레이블
    // default: ""
    floor?: string;
    // attach_metadata=true일 때 기록할 구축 상세
    // default: ""
    construction_detail?: string;
    // attach_metadata=true로 기록. 형식: {"kind":"construction_system","id":"확인한 system_id"}.
    // construction_system과 함께 쓰면 같은 시스템.
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
닫힌 솔리드의 한쪽 면을 옮겨 끝 위치나 치수를 조정한다. 잠기지 않은 최상위 닫힌 Brep의 평면 한 면을 PushPull Extend로 이동한다. 그룹·블록 편집을 끝낸 일반 모델에서 사용한다. 일부 오류 응답에는 `mutation_state`가 없을 수 있다.
```

```ts
declare const tools: {
  mcp__rhino__model_02_edit_planar_face(args: {
    // 연결 문서에서 확인한 최상위 닫힌 Brep의 GUID. 잠긴 객체 제외.
    object_id: string;
    // inspect_02-get_objects tool의 평면 인덱스(0부터). expected_geometry_crc와 같은 관찰값.
    face_index: number;
    // 같은 객체·면 조회에서 받은 geometry_crc. 현재 형상과 다르면 교체 전에 거부.
    expected_geometry_crc: number;
    // 유한한 [X, Y, Z], 문서 단위. 면 법선 성분의 절댓값은 문서 허용오차 초과.
    translation: Array<(number | number)>;
    // 생략: 연결된 저장 문서 경로. 지정: 그 경로와 일치해야 함.
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
여러 솔리드의 면을 함께 조정하고 변경을 Undo 기록 하나로 남긴다. 그룹·블록 편집을 끝낸 일반 모델에서 서로 다른 닫힌 Brep를 골라 객체당 한 면을 지정한다. 준비 단계에서 한 항목이라도 거부되면 객체를 교체하지 않는다.
```

```ts
declare const tools: {
  mcp__rhino__model_03_edit_planar_faces(args: {
    // 서로 다른 Brep 1..32개. 항목: object_id, face_index, expected_geometry_crc, translation.
    // 면 번호·CRC는 같은 관찰값. 나머지 조건은 model_02-edit_planar_face tool과 동일.
    edits: Array<{
      [key: string]: unknown;
    }>;
    // 생략: 연결된 저장 문서 경로. 지정: 그 경로와 일치해야 함.
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
객체에 입힐 표준 재료를 라이브러리에서 찾는다. 이름·설명·태그를 검색하거나 분류로 좁힌다. 이어서 재료를 할당하려면 `include_ids=true`로 조회한 뒤, 고른 재료의 `material_id`를 model_01-assign_material tool에 넘긴다.
```

```ts
declare const tools: {
  mcp__rhino__model_04_list_materials(args: {
    // 정확한 분류명(대소문자 구분). 생략: 전체 분류.
    // default: ""
    category?: string;
    // 이름·설명·태그 검색(대소문자 무관).
    // default: ""
    query?: string;
    // default: false
    include_ids?: boolean;
    // 상세: display, physical, metadata, source, paths, audit, all. 생략/[]: 요약.
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
문서에 표준 재료를 등록하고 `M` 아래에 분류·시스템·부재 역할별 레이어와 색·재료를 설정한다. 누락 항목만 만들고 기존 값과의 차이를 볼지, 기존 속성도 표준에 맞출지 선택한다.

차이도 오류도 없을 때 `applied=true`다. `incomplete`여도 일부는 이미 생성·변경됐을 수 있다. 문서 설정이 아니라 개별 객체의 재료를 바꾸려면 model_04-list_materials tool과 model_01-assign_material tool을 쓴다.
```

```ts
declare const tools: {
  mcp__rhino__model_05_setup(args: {
    // false: 누락분 생성, 기존 속성은 유지하고 차이 보고. true: 누락분 생성 + 기존 사전 정의 속성 갱신.
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
작업을 묶을 Phase를 만들거나, 목표와 대상을 정해 새 Plan을 등록한다. Plan은 `scope`에 해당하는 Step 템플릿으로 첫 실행 전 상태(`loop_no=0`, `revision=1`)에 만들어진다. 이 호출로 실제 작업을 시작하지 않는다. `result.status`로 생성 여부를 확인한다. 만들어진 Step은 받은 Plan ID로 plan_05-get tool에서 상세 조회한다.
```

```ts
declare const tools: {
  mcp__rhino__plan_02_create(args: {
    request: ({
      target: "phase";
      // 이름 필수. 공백만 있으면 거부.
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
      // 제목 필수. 공백만 있으면 거부.
      title: string;
      // 목표 필수. 공백만 있으면 거부.
      goal: string;
      // Step 템플릿 키: spatial_development, drawing_development, semantic_exploration,
      // plan_editing, model_revision, inspection, structure, construction_detail, drawing,
      // component, house, interior 또는 등록한 사용자 템플릿.
      // default: "house"
      scope?: string;
      // 단일 Scene용 호환 입력. scene_ids를 함께 쓰면 첫 ID와 일치해야 함.
      // default: ""
      scene_id?: string;
      // default: ""
      phase_id?: string;
      // 생략하거나 `null`이면 `scene_id` 사용.
      // default: null
      scene_ids?: (Array<string> | null);
      // default: null
      holon_ids?: (Array<string> | null);
      // 결과·결정에 의존하는 관련 Plan. ID 형식만 검사; 존재·순환·순서는 검사하거나 강제하지 않음.
      // default: null
      depends_on?: (Array<string> | null);
      // 작업 순서상 직전 Plan. ID 형식만 검사; 존재는 확인하지 않음.
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
Plan에 새 회차를 열거나 이미 시작한 최신 회차를 다시 이어간다. 최신 회차를 이어갈 때 `resume=true`를 쓴다. 새 회차를 열면 Step은 `pending`에서 시작하고 직전 회차 기록은 `previous_loop`에 담긴다.

새 회차를 열기 전, 사용자 피드백과 작업 방향에 맞춰 현재 Plan Goal을 확인·조정하고 다음 회차에 불필요함이 분명한 Rhino 객체·Layout·Named View·레이어를 정리한다. 이 호출 자체는 Rhino 정리나 Step 실행을 하지 않는다.
```

```ts
declare const tools: {
  mcp__rhino__plan_03_execute_looping(args: {
    // plan_02-create tool 또는 plan_08-list tool에서 받은 Plan ID.
    plan_id: string;
    // true: 이미 실행된 최신 회차 재개. false: 새 회차 시작.
    // default: false
    resume?: boolean;
    // 재개할 때 생략/빈 문자열: 이전 피드백 유지.
    // default: ""
    feedback?: string;
    // 최초 산출물 폴더명. 생략 시 목표에서 이름을 정하고 YYMMDD_를 붙임. 기존 폴더가 있으면 재사용.
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
ID를 아는 Phase·Plan·Step의 작업 기록을 읽는다. 상태만 확인할지, Plan의 목표·Step 목록이나 Step의 입출력 참조까지 볼지에 따라 요약과 상세를 고른다. Plan·Step의 과거 기록은 plan_07-list_revisions tool에서 받은 회차·리비전으로 지정한다. `revision`을 지정하면 현재 번호여도 읽기 전용이다. 작업 파일은 결과의 프로젝트 상대경로로 찾아 연다.
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
      // 생략/null: 선택한 회차의 최신 상태.
      // default: null
      revision?: (number | null);
      // default: false
      include_details?: boolean;
      // 0 이상. 생략/null: 최신 회차. 0: 실행 전 기록.
      // default: null
      loop_no?: (number | null);
    } | {
      target: "step";
      plan_id: string;
      // 같은 요청의 plan_id에 속한 Step ID.
      step_id: string;
      // 생략/null: 선택한 회차의 최신 상태.
      // default: null
      revision?: (number | null);
      // default: false
      include_details?: boolean;
      // 0 이상. 생략/null: 최신 회차. 0: 실행 전 기록.
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
Plan ID는 알지만 어느 시점의 기록을 읽을지 모를 때, 변경된 회차와 리비전 번호를 찾는다. 최신 회차와 리비전부터 반환한다. 특정 Step을 고르면 그 Step을 직접 변경한 기록만 볼 수 있다. `offset`은 지원하지 않는다. 읽을 기록을 고른 뒤 `plan_id`와 함께 그 항목의 `loop_no`·`revision`을 plan_05-get tool에 넘긴다.
```

```ts
declare const tools: {
  mcp__rhino__plan_07_list_revisions(args: {
    // plan_08-list tool의 plans[].plan_id 또는 plan_05-get tool의 Plan id.
    plan_id: string;
    // 1~500.
    // default: 50
    limit?: number;
    // audit/all: 생성 시각 포함. 생략/[]: 기본 필드만.
    // default: null
    field_groups?: (Array<string> | null);
    // 생략/null: 모든 회차. 0: 실행 전 기록.
    // default: null
    loop_no?: (number | null);
    // 지정한 Step의 직접 변경만 포함. 생략/빈 문자열: Step 필터 없음.
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
작업에 필요한 Phase나 Plan의 ID를 찾거나, 이미 아는 Plan의 Step 순서를 확인한다. Phase는 등록 목록을 받는다. Plan 목록은 Phase·Scene·상태로 좁힐 수 있다. Step은 지정한 Plan의 작업 순서대로 나온다. Step 목록과 리비전 정보는 같은 스냅샷의 결과이며, `offset`은 지원하지 않는다.
```

```ts
declare const tools: {
  mcp__rhino__plan_08_list(args: {
    request: ({
      target: "phase";
      // 1~500.
      // default: 50
      limit?: number;
      // 상세: description(설명), scope(연결 파일), audit(생성·수정 시각), all(전체). 생략/[]: 요약.
      // default: null
      field_groups?: (Array<string> | null);
    } | {
      target: "plan";
      // 생략/빈 문자열: Phase로 거르지 않음.
      // default: ""
      phase_id?: string;
      // 생략/빈 문자열: Scene으로 거르지 않음.
      // default: ""
      scene_id?: string;
      // 생략/빈 문자열: 상태로 거르지 않음.
      // default: ""
      status?: "" | "pending" | "running" | "paused" | "completed" | "failed" | "blocked";
      // 1~500.
      // default: 50
      limit?: number;
    } | {
      target: "step";
      plan_id: string;
      // 생략/null: 선택한 회차의 최신 상태. 지정: 읽기 전용 스냅샷.
      // default: null
      revision?: (number | null);
      // 0 이상. 생략/null: 최신 회차. 0: 실행 전 기록.
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
Plan의 산출물 폴더 이름을 바로잡을 때 저장된 Plan·Step의 경로 참조도 같이 바꾼다. plan_10-set_working tool로 폴더를 먼저 지정해야 한다. 해당 Plan의 Loop를 이미 실행했거나 다른 Plan의 과거 회차가 이 폴더를 참조하면 바꿀 수 없다. 같은 이름이면 변경 없이 성공한다. 대상 경로가 이미 있거나 다른 Plan 소유면 실패한다. 이름을 실제로 바꾸면 이전 리비전은 보존하고 새 리비전을 남긴다. 바뀐 경로는 `artifact_dir`에서 확인한다.
```

```ts
declare const tools: {
  mcp__rhino__plan_09_rename_artifact_folder(args: {
    // 경로가 아닌 폴더명 하나. YYMMDD_ 생략 시 현재 날짜를 붙임. Windows 금지 문자 제외.
    name: string;
    // 생략/빈 문자열: 현재 선택된 Plan.
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
앞으로 만들 산출물을 어느 작업에 보관할지 정한다. 현재 연결에서 저장 대상 Plan을 고르고, Step과 연결해야 하면 해당 Step도 지정한다. 이 호출로 작업을 실행하거나 상태를 바꾸지는 않는다. 처음 경로를 정할 때 리비전이 증가할 수 있다. 그 뒤에는 같은 경로를 재사용한다. 다음 산출물을 저장할 위치는 응답의 `artifact_dir`에서 확인한다. Loop 실행 전에는 Plan 루트, 실행 후에는 현재 회차 폴더다.
```

```ts
declare const tools: {
  mcp__rhino__plan_10_set_working(args: {
    // plan_08-list tool의 plans[].plan_id 또는 plan_05-get tool의 Plan id.
    plan_id: string;
    // 현재 회차에서 해당 Plan에 속한 Step ID. 생략: Plan만 선택.
    // default: ""
    step_id?: string;
    // 최초 폴더명. 생략 시 목표에서 이름을 정하고 YYMMDD_를 붙임. 기존 폴더명과 다르면 거부.
    // default: ""
    artifact_name?: string;
    // 생략/null: 현재 회차. 이전·미존재 회차는 선택 불가.
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
결정과 진행 상황을 남기거나 작업 범위를 조정할 수 있다. 무엇을 바꿀지에 따라 대상을 고른다. 단계 구분과 연결 파일은 Phase, 목표와 작업 대상은 Plan, 진행 상태와 입출력 참조·설계 판단은 Step이다. Plan과 Step은 현재 회차만 수정하며, Plan의 `completed`는 사용자가 완료를 확인한 뒤에 지정한다.

기존 목록을 유지하면서 일부만 바꿀 수 있는 항목은 `depends_on`·`input_refs`·`output_refs`다. 여기에 `add`/`remove`를 쓴다. 그 밖의 대상·산출물·상하위 관계 목록은 통째로 교체한다. 생략 또는 `null`은 유지, 교체 목록의 `[]`는 비우기다.

요청한 변경이 전부 저장되면 `updated`, 저장 값이 그대로면 `no_change`, 일부만 저장되면 `partial_success`다. 건너뛴 항목은 `issues`에서 확인한다. Step을 완료하면서 함께 보낸 항목은 한 번에 저장한다. Rhino 정리 중 오류가 나도 Step은 이미 완료됐을 수 있으므로, 재시도 전에 기록과 실제 문서를 확인한다.
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
      // context_04-get_project_info tool의 project.files에 등록된 파일명. ""/[]: 해제. 생략/null: 유지.
      // default: null
      file_name?: (string | Array<string> | null);
      // default: null
      status?: ("pending" | "running" | "paused" | "completed" | "failed" | "blocked" | null);
      // 같은 종류의 Phase ID만 사용. 대상 존재·순환·완료 여부는 검사하지 않음.
      // default: null
      depends_on?: ({
        // 기존·중복·무효 값은 건너뛰고 issues에 기록. remove와 겹치면 양쪽 모두 제외.
        add?: Array<string>;
        // 미등록·중복·무효 값은 건너뛰고 issues에 기록.
        remove?: Array<string>;
      } | null);
      // 빈 문자열은 연결 해제.
      // default: null
      previous_id?: (string | null);
    } | {
      target: "plan";
      // plan_08-list tool의 plans[].plan_id 또는 plan_05-get tool의 Plan id.
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
      // plan_05-get tool로 읽은 리비전. 현재 값과 다르면 거부. Loop 실행 후에는 loop_no도 지정.
      // default: null
      expected_revision?: (number | null);
      // 결과·결정에 의존하는 관련 Plan. ID 형식만 검사. 존재·자기 참조·순환 검사 및 순서·완료 강제 없음.
      // default: null
      depends_on?: ({
        // 기존·중복·무효 값은 건너뛰고 issues에 기록. remove와 겹치면 양쪽 모두 제외.
        add?: Array<string>;
        // 미등록·중복·무효 값은 건너뛰고 issues에 기록.
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
      // 작업 순서상 직전 Plan. 빈 문자열은 연결 해제.
      // default: null
      previous_id?: (string | null);
      // 상대 Plan을 자동 수정하거나 참조 대상의 존재를 검사하지 않음.
      // default: null
      parent_plan?: (Array<string> | null);
      // 상대 Plan을 자동 수정하거나 참조 대상의 존재를 검사하지 않음.
      // default: null
      child_plan?: (Array<string> | null);
      // 현재 회차만 허용. 생략: 현재 회차.
      // default: null
      loop_no?: (number | null);
    } | {
      target: "step";
      // plan_08-list tool의 plans[].plan_id 또는 plan_05-get tool의 Plan id.
      plan_id: string;
      // plan_05-get tool의 Plan 상세에서 확인한 Step ID.
      step_id: string;
      // default: null
      status?: ("pending" | "running" | "paused" | "completed" | "failed" | "blocked" | null);
      // default: null
      input_refs?: ({
        // 기존·중복·무효 값은 건너뛰고 issues에 기록. remove와 겹치면 양쪽 모두 제외.
        add?: Array<string>;
        // 미등록·중복·무효 값은 건너뛰고 issues에 기록.
        remove?: Array<string>;
      } | null);
      // default: null
      output_refs?: ({
        // 기존·중복·무효 값은 건너뛰고 issues에 기록. remove와 겹치면 양쪽 모두 제외.
        add?: Array<string>;
        // 미등록·중복·무효 값은 건너뛰고 issues에 기록.
        remove?: Array<string>;
      } | null);
      // 후속 작업에 넘길 결론·확인 사항. 빈 문자열: 삭제.
      // default: null
      takeaways?: (string | null);
      // 설계 결정의 이유·근거. 빈 문자열: 삭제.
      // default: null
      design_rationale?: (string | null);
      // plan_05-get tool로 읽은 리비전. 현재 값과 다르면 거부. Loop 실행 후에는 loop_no도 지정.
      // default: null
      expected_revision?: (number | null);
      // 현재 회차만 허용. 생략: 현재 회차.
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
  status?: "updated" | "no_change" | "partial_success" | "error";
  // 저장 값이 실제로 바뀌면 true. 후속 Rhino 작업에서 오류가 나도 저장된 변경은 남을 수 있다.
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
설계 중인 바닥·벽·지붕·기초에 적용할 구법 후보를 비교한다. 필요한 부위·재료·구조 유형으로 좁히고, 경간이 정해졌다면 등록된 경간 범위와 부재 깊이 경험칙에 대조한다. 이 결과는 후보를 거르는 참고 자료이며 구조 검증을 대신하지 않는다.
```

```ts
declare const tools: {
  mcp__rhino__research_01_get_construction_guidance(args: {
    // 예: `glulam`, `longspan`, `bearing wall`.
    // default: ""
    query?: string;
    // floor, wall, roof, foundation. 빈 문자열: 전체 분류.
    // default: ""
    category?: string;
    // 재료명: Wood, Steel, Concrete. analysis_02-validate_structure tool과 동일.
    // default: ""
    material?: string;
    // 구조 유형: beam, truss, shell, frame, canopy, gridshell, membrane, highrise. analysis_02-validate_structure tool과 동일.
    // default: ""
    structure_type?: string;
    // 경간(m). 0 초과 시 등록된 범위·깊이 규칙으로 fits_span·권장 깊이 계산.
    // default: 0.0
    span_m?: number;
    // load_kn 산정 참고: 용도별 활하중(kPa)·재료 밀도(kg/m³) 포함.
    // default: false
    include_reference_data?: boolean;
    // default: false
    include_ids?: boolean;
    // 상세: rules, narrative, source, metadata, audit, all. 생략/[]: 요약.
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
중정이나 목조 홀처럼 설계 중인 건축 유형을 다룰 때 참고할 서사와 선례를 찾는다. 유형을 검색하고, 구법이나 구조 유형이 정해졌다면 그 조건으로 좁힌다.
```

```ts
declare const tools: {
  mcp__rhino__research_02_get_typology_narrative(args: {
    // 유형 검색어. 예: courtyard, skyscraper, timber hall.
    // default: ""
    query?: string;
    // research_01-get_construction_guidance tool 등에서 확인한 구법 system_id. 예: steel-column-frame.
    // default: ""
    construction_system?: string;
    // analysis_02-validate_structure tool과 같은 구조 유형. 예: shell, truss, frame, membrane.
    // default: ""
    structure_type?: string;
    // 반환할 항목 수. 1 미만은 1로 처리.
    // default: 5
    limit?: number;
    // default: false
    include_ids?: boolean;
    // 상세: rules, narrative, source, metadata, audit, all. 생략/[]: 요약.
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
접합이나 단면 같은 건축 디테일에 참고할 자료를 찾는다. 등록된 자료의 제목·태그·파일 형식을 검색한다. 도면·상세 자체의 본문 검색은 아니다.
```

```ts
declare const tools: {
  mcp__rhino__research_03_search_details(args: {
    // 자료 제목·태그·파일 형식의 검색어. 일부 한국어 단어는 관련 영문 검색어로 확장. 빈 문자열: 전체 자료.
    // default: ""
    query?: string;
    // default: false
    include_ids?: boolean;
    // 상세: rules, narrative, source, metadata, audit, all. 생략/[]: 요약.
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
Rhino 그룹의 구성은 그대로 두고 Scene에 객체를 보탠다. 해당 Scene에서 제외했던 Holon 구성원도 다시 포함할 수 있다. 추가에 실패한 객체와 이미 포함돼 있던 객체는 결과에 따로 표시된다.
```

```ts
declare const tools: {
  mcp__rhino__scene_01_add_objects(args: {
    // scene_07-list에서 include_ids=true로 조회한 Scene ID.
    scene_id: string;
    // 일반 형상·클리핑 평면 GUID 최대 4096개. failed_indices·already_present_indices는 이 배열의 위치(0부터).
    object_ids: Array<string>;
    // 생략: 연결 문서의 저장 경로. 지정: 해당 경로와 일치해야 함.
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
설계 영역이나 프로그램, 특정 상황을 묶어 관리할 Scene을 만든다. 프로젝트 파일별로 구분하려면 파일도 연결한다. 생성 결과의 `scene_id`로 그 Scene을 조회하거나 객체를 추가할 수 있다.
```

```ts
declare const tools: {
  mcp__rhino__scene_02_create(args: {
    // 빈 이름: Untitled scene.
    name: string;
    // mm, cm, m, in, ft.
    // default: "mm"
    units?: string;
    // context_04-get_project_info의 project.files에 등록된 파일명. 폴더 경로 제외.
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
Holon과 하위 Holon이 차지하는 범위를 모델에서 살펴본다. 현재 선택은 해당 구성원으로 바뀌고, 뷰는 대상을 격리해 화면에 맞춰 확대한다. 잠긴 주변 객체는 남을 수 있다. `Unisolate`가 되돌리는 것은 표시 상태뿐이다. `mutation_applied=null`이면 다시 호출하기 전에 현재 선택·가시성·카메라를 확인한다.
```

```ts
declare const tools: {
  mcp__rhino__scene_03_focus_holons(args: {
    // 서로 다른 Holon ID 1~32개(scene_08-list_holons의 include_ids=true). 유효 최상위 객체 최대 4096개; 활성 모델 뷰에서 선택 가능해야 함.
    holon_ids: Array<string>;
    // 지정한 경우 연결 문서 경로와 일치해야 함.
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
Scene의 이름, 단위, Holon·객체 수처럼 프로젝트에 저장된 정보를 확인한다. 현재 Rhino 문서에서 객체를 골라 후속 작업에 써야 한다면 `scene_06-get_objects`를 쓴다.
```

```ts
declare const tools: {
  mcp__rhino__scene_04_get(args: {
    // 기록해 둔 Scene ID 또는 scene_07-list에서 include_ids=true로 조회한 ID.
    scene_id: string;
    // true: 관련 ID 포함. 입력한 scene_id는 생략.
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
Holon에 어떤 구성과 관계가 등록돼 있는지 읽는다. 저장된 등록 정보만 필요하면 기본 조회로 충분하다. 모델이 바뀌어 지금 Rhino의 구성과도 비교해야 한다면 `live=true`를 쓴다. `live_verified`는 현황을 직접 확인했는지, `requires_sync`는 등록을 맞출 필요가 있는지를 나타낸다. 이 도구는 등록을 바꾸지 않는다. 하위 Holon까지 보고 싶다면 `recursive`를 켠다.
```

```ts
declare const tools: {
  mcp__rhino__scene_05_get_holon(args: {
    // 등록 결과 또는 scene_08-list_holons의 include_ids=true로 확인한 ID.
    holon_id: string;
    // default: false
    live?: boolean;
    // true: 지정한 필드 그룹의 ID만 포함. 입력한 holon_id는 요약에서 생략.
    // default: false
    include_ids?: boolean;
    // true: 하위 Holon까지 확장. Rhino 블록 정의 경계는 유지.
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
연결된 Rhino 문서에서 Scene을 이루는 실제 객체를 확인한다. 직접 추가한 객체와 Holon을 통해 들어온 객체가 대상이고, 해당 Scene에서 제외한 객체는 결과에 나오지 않는다. 직접 등록한 객체가 문서에서 사라졌다면 자동으로 제외되지 않으며 조회가 실패할 수 있다.
```

```ts
declare const tools: {
  mcp__rhino__scene_06_get_objects(args: {
    // 기록해 둔 Scene ID 또는 scene_07-list에서 include_ids=true로 조회한 ID.
    scene_id: string;
    // true: 포함·제외 등 후속 객체 작업에 사용할 GUID를 반환.
    // default: false
    include_ids?: boolean;
    // scope, state, geometry, audit, all. 생략·빈 배열: 요약.
    // default: null
    field_groups?: (Array<string> | null);
    // 한 번에 1~200개.
    // default: 50
    limit?: number;
    // 첫 페이지는 0. truncated=true면 다음 호출에서 반환된 객체 수만큼 offset을 늘림.
    // default: 0
    offset?: number;
    // 지정한 경우 연결 문서 경로와 일치해야 함.
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
프로젝트에 등록된 Scene을 이름이나 연결 파일명으로 찾는다. 그 Scene을 후속 호출에 넘기려면 `include_ids=true`로 ID를 받는다. 등록 상세는 `scene_04-get`, 현재 모델의 구성원은 `scene_06-get_objects`에서 본다.
```

```ts
declare const tools: {
  mcp__rhino__scene_07_list(args: {
    // 이름 부분 일치. 대소문자 구분 없음.
    // default: ""
    name?: string;
    // 확장자를 포함한 정확한 프로젝트 파일명. 생략: 프로젝트 전체.
    // default: ""
    file_name?: string;
    // 한 번에 1~200개.
    // default: 50
    limit?: number;
    // 앞에서 건너뛸 Scene 수(0 이상).
    // default: 0
    offset?: number;
    // true: 후속 호출에 사용할 Scene ID 포함.
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
모델에 등록된 Holon 중 작업 대상을 찾는다. 기본은 최상위 Holon이고, 특정 Scene에 연결된 것만 찾거나 하위 Holon까지 넓혀 볼 수 있다. 목록에서 고른 Holon의 현재 Rhino 구성원은 `scene_05-get_holon`에서 `live=true`로 확인한다.
```

```ts
declare const tools: {
  mcp__rhino__scene_08_list_holons(args: {
    // 관리형 세션에서 생략하면 현재 연결 모델 기준.
    // default: ""
    expected_model_path?: string;
    // true: 상세 조회·뷰 집중·갱신에 넘길 Holon ID 포함.
    // default: false
    include_ids?: boolean;
    // scene_07-list에서 찾은 Scene ID. 지정: 해당 Scene에 연결된 Holon. 생략: 기본은 최상위 Holon.
    // default: ""
    scene_id?: string;
    // true: 하위 Holon도 포함. 해당 Scene에 직접 등록되지 않았을 수 있음.
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
더 이상 Holon으로 다루지 않을 요소의 등록을 해제한다. Rhino 형상과 그룹은 그대로 두고, 하위 Holon도 등록을 유지한다. 하위 Holon과 해제 대상 사이의 부모 연결은 끊는다. 특정 Scene에서 객체만 빼려면 `scene_10-remove_objects`를 쓴다.
```

```ts
declare const tools: {
  mcp__rhino__scene_09_remove_holon(args: {
    // 등록 결과나 scene_08-list_holons에서 확인한 ID. 부모 Holon·Plan·Step의 참조를 먼저 해제.
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
특정 Scene에서만 객체를 뺀다. Rhino 형상과 그룹, Holon 등록은 남는다. 실패한 객체와 원래 포함돼 있지 않았던 객체는 결과에 따로 표시된다.
```

```ts
declare const tools: {
  mcp__rhino__scene_10_remove_objects(args: {
    // scene_07-list에서 include_ids=true로 조회한 Scene ID.
    scene_id: string;
    // 일반 형상·클리핑 평면 GUID 최대 4096개. scene_06-get_objects의 include_ids=true로 조회 가능. failed_indices·already_absent_indices는 이 배열의 위치(0부터).
    object_ids: Array<string>;
    // 생략: 연결 문서의 저장 경로. 지정: 해당 경로와 일치해야 함.
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
Rhino 그룹의 현재 구성을 Holon 등록에 반영한다. 그룹 자체를 편집하지는 않는다. 갱신 범위는 Holon 하나, 여러 개 또는 특정 Scene 중에서 고른다. 지정하지 않으면 연결 문서 전체가 대상이다. 그룹·블록 편집 상태에서는 먼저 그 편집을 끝내야 한다. 쓰기 전에 차이만 보고 싶다면 `scene_05-get_holon`에서 `live=true`로 조회할 수 있다.

`changed`는 실제로 내용이 달라진 등록 수다. `problems`에 문제가 나와도 나머지 등록은 갱신됐을 수 있다.
```

```ts
declare const tools: {
  mcp__rhino__scene_11_sync_holon(args: {
    // 대상의 공통 한도: 하위 Holon까지 최대 64개.
    // scene_08-list_holons의 include_ids=true로 찾은 Holon ID. holon_ids·scene_id와 동시 지정 불가.
    // default: ""
    holon_id?: string;
    // 생략: 연결 문서의 저장 경로. 지정: 해당 경로와 일치해야 함.
    // default: ""
    expected_model_path?: string;
    // holon_id와 함께 지정해 등록된 Rhino 그룹 GUID가 맞는지 확인.
    // default: ""
    rhino_group_id?: string;
    // 서로 다른 Holon ID 1~64개. holon_id·rhino_group_id·scene_id와 동시 지정 불가.
    // default: null
    holon_ids?: (Array<string> | null);
    // 해당 Scene의 Holon을 대상으로 함. holon_id·holon_ids·rhino_group_id와 동시 지정 불가.
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
Scene은 유지한 채 연결 프로젝트 파일만 바꾸거나 끊는다. 이후에도 같은 Scene ID로 조회한다.
```

```ts
declare const tools: {
  mcp__rhino__scene_12_update(args: {
    // 기록해 둔 Scene ID 또는 scene_07-list에서 include_ids=true로 조회한 ID.
    scene_id: string;
    // context_04-get_project_info의 project.files에 등록된 파일명.
    // 파일명: 연결 변경. 빈 문자열: 해제. 생략·null: 유지.
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
설계 요소를 Rhino 그룹에 연결된 단위인 Holon으로 등록하거나 기존 등록을 바꾼다. 새로 등록할 때는 연결할 Scene을 한 개 이상 정한다. 기존 등록을 바꿀 때는 대상 Holon ID를 지정한다.

기존 Rhino 그룹의 구성원을 가져오려면 해당 그룹을 연결하고 `object_ids`를 생략한다. 객체를 직접 지정한다면 기존 그룹에 연결할 때 실제 구성과 일치해야 하며, 새로 등록하면서 일치하는 그룹이 없으면 그룹을 만든다. 부모 Holon 아래에 다른 Holon을 묶을 때는 `child_holon_ids`를 지정한다. Rhino에서 이미 고친 그룹에 등록 정보만 맞추려면 `scene_11-sync_holon`을 쓴다.
```

```ts
declare const tools: {
  mcp__rhino__scene_13_upsert_holon(args: {
    // 기존 Rhino 그룹을 연결할 때는 그 그룹의 정확한 이름.
    name: string;
    // 최상위 Rhino 객체 GUID. 직접 소유하는 Holon은 객체당 하나.
    // 생략: 기존 그룹의 구성원에서 직접 구성원 추론. 빈 배열: 하위 Holon으로만 구성된 부모에 한함.
    // default: null
    object_ids?: (Array<string> | null);
    // 생략: 연결 문서의 저장 경로. 지정: 해당 경로와 일치해야 함.
    // default: ""
    expected_model_path?: string;
    // scene_07-list에서 조회한 Scene ID. 새 등록: 한 개 이상 필수. 갱신 시 생략: 기존 연결 유지.
    // default: null
    scene_ids?: (Array<string> | null);
    // scene_08-list_holons 등에서 확인한 갱신 대상 ID. 생략: 새 등록.
    // default: ""
    holon_id?: string;
    // 연결할 Rhino 그룹 GUID. 동명 그룹 구분에 사용. 새 등록에서 object_ids를 생략한다면 필수.
    // default: ""
    rhino_group_id?: string;
    // 빈 배열: 기존 자식 분리. 생략: 유지. 자식당 부모 하나, 순환 금지.
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
연결된 Rhino에서 Python 3으로 편집하거나 파일을 다룰 때, Plan·Loop의 산출물 폴더를 작업 디렉터리로 쓸 수 있다. `plan_10-set_working`에서 쓰기 가능한 폴더를 선택하거나 이미 선택한 폴더를 사용한다.

`executed`는 스크립트 본문이 끝났다는 뜻이다. 의도한 모델 변경과 파일 생성은 결과와 산출물로 확인하고, 문서 저장 여부는 따로 확인한다. 대기 시간이 지나도 실행이 이어지거나 오류 뒤 일부 변경이 남을 수 있다. 완료가 미확정이면 같은 `request_id`로 `script_03-get_execution`을 조회하고 문서 상태를 본 뒤 재실행 여부를 정한다.
```

```ts
declare const tools: {
  mcp__rhino__script_01_run_project_python(args: {
    // 동기식 Python 3. doc·scriptcontext.doc은 연결 문서. 상대 경로는 산출물 폴더 기준.
    // 반환할 JSON 호환 값은 result에 할당.
    code: string;
    // 완료 확인을 기다리는 한도: 1~600초. beyond·CoS는 최초 최대 60초 뒤 pending과 request_id를 반환할 수 있음.
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
연결된 Rhino에서 형상을 만들거나 고치고, 값을 측정하거나 명령을 자동화한다. Python, C# 또는 명령 매크로 중 작업에 맞는 방식을 고른다. Plan·Loop 폴더가 작업 디렉터리여야 하는 Python 작업에는 `script_01-run_project_python`을 쓴다.

`executed`는 본문이 끝났다는 뜻이다. 작업의 실제 결과는 `result`와 `mutation_state`에서 확인한다. 완료가 미확정이면 같은 `request_id`로 `script_03-get_execution`을 조회하고, 문서 상태를 확인하기 전에는 같은 변경을 다시 실행하지 않는다.
```

```ts
declare const tools: {
  mcp__rhino__script_02_run_rhino(args: {
    // 동기식 Python 소스, C# 문장 본문 또는 명령 매크로. doc은 연결 문서.
    // Python은 JSON 호환 값을 result에, C#은 JSON을 result_json에 할당.
    // command: !·Pause·대화상자 없이 끝나는 매크로.
    script: string;
    // python(Python 3), python2, csharp, csharp-script, command.
    // default: "python"
    language?: string;
    // 완료 확인을 기다리는 한도: 1~600초. beyond·CoS는 최초 최대 60초 뒤 pending과 request_id를 반환할 수 있음.
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
대기 중이거나 시간 초과로 돌아온 RhinoCode 실행의 상태와 결과를 재실행 없이 확인한다. 처음 받은 `request_id`를 지정한다. 연결이 끝났더라도 원래 실행의 기록이 남아 있으면 같은 ID로 읽을 수 있다.

긴 결과는 `result_page`에 표시된 다음 오프셋으로 이어 읽는다. 로그가 필요하면 `include_stdout=true`를 지정하고, 로그의 다음 바이트 오프셋을 사용한다. 변경이 적용됐는지 불확실하다면 `mutation_state`와 현재 Rhino 문서를 확인한다.
```

```ts
declare const tools: {
  mcp__rhino__script_03_get_execution(args: {
    // 지정: beyond·CoS는 ID로 최초 실행 연결을 찾음. 생략: 현재 연결의 최근 실행.
    // default: ""
    request_id?: string;
    // true: 보관된 결과 본문 포함.
    // default: true
    include_result?: boolean;
    // true: stdout·stderr 및 CLI 로그 포함.
    // default: false
    include_stdout?: boolean;
    // 객체 결과의 최상위 키 또는 객체 배열에서 행마다 남길 키.
    // default: null
    result_fields?: (Array<string> | null);
    // 0 이상. 결과는 배열 항목·문자열 문자, 로그는 바이트 단위. 같은 offset 값.
    // default: 0
    offset?: number;
    // 결과 페이지당 1~1000. 로그에는 별도 크기 제한 적용.
    // default: 100
    limit?: number;
    // false: 결과 본문의 식별자 생략. 실행 request_id는 유지.
    // default: true
    include_ids?: boolean;
    // true: 정상 완료에서도 축약 전 실행 근거 포함.
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
사용자가 영구 저장을 요청하면 연결된 Rhino 문서 전체를 기존 `.3dm`에 저장한다. `saved=true`는 저장 확인, `false`는 저장되지 않았다는 응답, `null`은 결과 미확정이다. 미확정이면 다시 호출하기 전에 현재 문서 상태를 확인한다.
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
