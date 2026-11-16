# 현행 툴 선언

## 기준 및 선언 표기

실사용 외부 연결 서버 beyond·CoS의 도구 선언 81개를 TypeScript로 정리했습니다. 두 경로의 도구 설명과 입력·출력 스키마는 같습니다.

- 리포지토리: [hongikkaan/almond-mcp](https://github.com/hongikkaan/almond-mcp)
- 기준 커밋 `38d6ee1fcb680df29d79cfa7dae114caba19cbb1` (실사용 로컬 `Fix`).
- 수집일 2026-11-13. Almond MCP 0.7.0rc2 / FastMCP 4.1.0 / MCP SDK 2.3.0 / mcp-types 2.3.0.
- 진입점은 beyond의 `codex_host.py`와 CoS의 `cos_host.py`입니다. 기본 도구 선언 70개, 작업환경 도구 선언 6개, 연결 관리 도구 선언 5개를 수록합니다.
- `connect_02-session` tool이나 `connect_03-start_session` tool에서 문서를 선택하면 일반 호출·연결 해제·새 종료 요청에 해당 연결을 적용합니다. `script_03-get_execution` tool에 실행 `request_id`를 지정하면 원래 실행 연결을 찾습니다.
- 비교 문서: [오리지널 툴 선언](https://app.notion.com/p/417e0a3941208127aebcdbec1d2e7052)

아래 선언은 실제 `tools/list` 응답을 Codex 선언 형식으로 변환한 것입니다. `mcp__rhino__`는 예시에 사용한 연결 이름입니다.

필수 인자와 선택 인자는 `?`로 구분합니다. 배열은 `Array<T>`, null을 허용하는 타입은 `| null`로 표시합니다. 필드 설명은 주석에 표시하고, JSON 내용을 담는 문자열은 `result: string`으로 표기합니다.

## connect

### 82. connect\_01-list\_up

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
    connections?: Array<{
      artifact_dir?: string | null;
      connection_id?: string | null;
      host_id?: string | null;
      in_flight?: boolean;
      model_filename?: string | null;
      model_path?: string | null;
      pid?: number | null;
      reason?: string;
      // 자동 할당된 실행 슬롯 A–J
      slot?: string | null;
      state?: string;
    }>;
    error_code?: string;
    instructions?: string;
    message?: string;
    next_step_guide?: string;
    selected_connection_id?: string | null;
    starts?: Array<{
      connection_id?: string | null;
      model_path?: string;
      reason?: string;
      // connect_03-start_session 시작 요청 ID. 동일 요청 상태 추적에 사용
      request_id?: string;
      state?: string;
    }>;
    targets?: Array<{
      artifact_dir?: string | null;
      connection_id?: string | null;
      host_id?: string | null;
      in_flight?: boolean;
      model_filename?: string | null;
      model_path?: string | null;
      pid?: number | null;
      reason?: string;
      slot?: string | null;
      state?: string;
    }>;
  }>>;
};
```

### 83. connect\_02-session

```txt
열려 있는 저장된 Rhino 문서에 연결하거나 이 클라이언트의 작업 대상을 전환합니다. `connect_01-list_up` tool의 `targets`에서 선택한 같은 대상의 `host_id`와 `model_path`를 사용합니다. 이미 유지 중인 연결도 다시 선택할 수 있습니다.

**선택된 연결**은 이후 일반 도구 호출에 사용됩니다. 반환된 `state`: `ready`는 일반 작업 가능, `recovering`·`unconfirmed`는 이전 실행 결과 확인이 필요한 상태입니다.
```

```ts
declare const tools: {
  mcp__rhino__connect_02_session(args: {
    host_id: string;
    model_path: string;
  }): Promise<CallToolResult<{
    artifact_dir?: string | null;
    connection_id?: string | null;
    error_code?: string;
    host_id?: string | null;
    in_flight?: boolean;
    message?: string;
    model_filename?: string | null;
    model_path?: string | null;
    next_step_guide?: string;
    pid?: number | null;
    reason?: string;
    // 자동 할당된 실행 슬롯 A–J
    slot?: string | null;
    state?: string;
  }>>;
};
```

### 84. connect\_03-start\_session

```txt
저장된 모델을 새 Rhino 창에서 열고 연결합니다.
```

```ts
declare const tools: { mcp__rhino__connect_03_start_session(args: {
  // 새 Rhino에서 열 저장된 로컬 .3dm 파일의 절대 경로입니다.
  model_path: string;
  // 이 시작 요청의 고유 ID입니다. 시작이 지연되거나 결과가 불확실하면 새 ID를 만들지 말고 같은 값을 재사용해 상태를 확인합니다.
  request_id: string;
}): Promise<CallToolResult<{
  // 이 연결의 임시 작업 폴더입니다.
  artifact_dir?: string | null;
  // 연결 상태 확인용 ID입니다.
  connection_id?: string | null;
  // 오류 유형입니다.
  error_code?: string;
  // Rhino 호스트 ID
  host_id?: string | null;
  // 해당 연결에 호출이 진행 중인지 여부
  in_flight?: boolean;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 모델 파일명
  model_filename?: string | null;
  // 저장된 모델의 경로
  model_path?: string | null;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // Rhino 프로세스 ID
  pid?: number | null;
  // 상태 사유 또는 오류 내용. 없으면 빈 문자열
  reason?: string;
  // 동일 시작 시도에 재사용. 대기·실패 상태는 connect_01-list_up tool.starts에서 확인
  request_id?: string;
  // 독립 연결 슬롯. 같은 폴더의 모델은 DB·산출물 루트를 공유
  slot?: string | null;
  // 연결 상태입니다. ready에서 일반 작업을 수행하며 recovering/unconfirmed에서는 실행 결과부터 확인합니다.
  state?: string;
}>>; };
```

### 85. connect\_04-disconnect

```txt
선택한 연결을 해제하고 Rhino 창과 문서는 유지합니다.
```

```ts
declare const tools: { mcp__rhino__connect_04_disconnect(args: {}): Promise<CallToolResult<{
  // 해제한 연결 ID입니다.
  connection_id?: string;
  // 오류 유형입니다.
  error_code?: string;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 해제한 연결에 저장된 모델 경로입니다. 저장·종료 전에 현재 문서 경로와 일치하는지 확인합니다.
  model_path?: string | null;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // 해제한 연결의 Rhino 프로세스 ID입니다. 종료할 창을 식별할 때 model_path와 함께 확인합니다.
  pid?: number | null;
  // 해제 결과 또는 남아 있는 잠금의 사유입니다.
  reason?: string;
  // Rhino에서 연결 해제를 확인했는지 나타냅니다.
  released?: boolean;
  // Rhino가 닫혔는지 여부. connect_04-disconnect tool는 false
  rhino_closed?: boolean;
  // worker가 종료됐는지 여부
  worker_closed?: boolean;
}>>; };
```

### 86. connect\_05-close\_session

```txt
선택한 Rhino 문서를 저장하고 완료를 확인한 뒤 정상 종료합니다.
```

```ts
declare const tools: { mcp__rhino__connect_05_close_session(args: {
  // 이 종료 요청의 고유 ID입니다. 지연·불확실 상태에서는 같은 ID로 결과를 조회합니다. 저장 확인 전에는 종료하지 않습니다.
  request_id: string;
}): Promise<CallToolResult<{
  // 종료 대상 연결 ID입니다.
  connection_id?: string;
  // 저장과 종료를 요청한 모델의 절대 경로입니다.
  model_path?: string;
  // Save 후 확인한 문서 변경 여부입니다.
  modified_after?: boolean;
  // Save 전에 확인한 문서 변경 여부입니다.
  modified_before?: boolean;
  // 현재 상태에서 가능한 후속 작업 안내입니다.
  next_step_guide?: string;
  // 시작 identity까지 대조한 종료 대상 Rhino PID입니다.
  pid?: number;
  // 저장 실패, 종료 거부 또는 남아 있는 불확실성의 사유입니다.
  reason?: string;
  // 해당 연결의 소유권 해제를 확인했는지 나타냅니다.
  released?: boolean;
  // 종료 요청 ID. 같은 값으로 재호출하면 보관된 결과만 조회합니다.
  request_id?: string;
  // 정확한 대상 Rhino 프로세스의 종료를 확인했는지 나타냅니다.
  rhino_closed?: boolean;
  // script_03-get_execution tool으로 확인할 Save 실행 ID입니다.
  save_request_id?: string;
  // Save 완료와 같은 문서의 modified=false를 확인했는지 나타냅니다.
  saved?: boolean;
  // 보관된 마지막 종료 처리 단계입니다.
  stage?: string;
  // completed만 저장 확인·Rhino 종료·worker 종료·소유권 해제를 모두 입증합니다.
  status?: "closing" | "completed" | "rejected" | "save_failed" | "unconfirmed";
  // 해당 연결 worker의 종료를 확인했는지 나타냅니다.
  worker_closed?: boolean;
}>>; };
```

## context

### 21. context\_01-get\_policy

```txt
Almond 작업의 기본 지침과 활동별 지침을 조회합니다. policy를 생략하면 기본 지침, 공통 도구 이름과 available_policies를 반환하며, 작업에 필요한 지침을 policy로 선택해 읽습니다.

basic 또는 빈 값은 기본 지침과 공통 도구 이름을 반환합니다. metadata는 객체·그룹 메타데이터 규칙, rhino_scripting은 내장 Rhino 스크립팅 참고자료, rhinocode는 코드·명령 실행 지침입니다. spatial_modeling, observation, drawing, design_exploration, feedback_reporting은 각 활동의 판단 기준입니다. 여러 활동이 있으면 필요한 지침을 각각 조회합니다.

선택에 따라 본문은 text, policy 또는 scripting_skill에 담깁니다. source_refs에서 출처와 해시를 확인하고 같은 guide_version에서 이미 읽은 지침은 재사용할 수 있습니다. 개별 도구의 호출법은 해당 도구의 공개 설명과 스키마를 확인합니다.
```

```ts
declare const tools: {
  mcp__rhino__context_01_get_policy(args: {
    // 생략 또는 빈 문자열은 basic. 선택값의 용도는 available_policies 참고.
    policy?: "" | "basic" | "metadata" | "rhino_scripting" | "rhinocode" | "spatial_modeling" | "observation" | "drawing" | "design_exploration" | "feedback_reporting";
  }): Promise<CallToolResult<{
    // 처리 상태. 도구 호출 오류는 별도 오류 응답일 수 있습니다.
    status?: string;
    error_code?: string;
    message?: string;
    next_step_guide?: string;
    // 지침 묶음의 버전 해시
    guide_version?: string;
    selected_policy?: string;
    // 선택할 수 있는 각 지침의 이름과 설명.
    available_policies?: { [key: string]: string };
    // basic·rhinocode·활동별 지침의 본문.
    text?: string;
    // basic에서 반환하는 공통 worker 도구 이름 목록.
    tools?: Array<string>;
    // metadata 지침 객체.
    policy?: { [key: string]: unknown };
    // rhino_scripting의 내장 자료. 각 자료는 원문과 출처 해시를 포함합니다.
    scripting_skill?: {
      name?: string;
      [key: string]: unknown;
      sources?: Array<{
        path?: string;
        sha256?: string;
        text?: string;
      }>;
    };
    // 지침 출처의 저장소 상대 경로와 정규화 SHA-256.
    source_refs?: Array<{
      path?: string;
      sha256?: string;
    }>;
  }>>;
};
```

### 22. context\_04-get\_project\_info

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
    // 등록 파일 페이지 크기: 정수 1~500, 기본 50.
    files_limit?: number;
    // 등록 파일의 시작 위치: 0 이상의 정수, 기본 0.
    files_offset?: number;
    // 기본 false.
    include_ids?: boolean;
    // project, document, named_views, layouts, layer_tree, locations, runtime. 기본은 runtime을 제외한 모든 섹션.
    sections?: Array<string> | null;
  }): Promise<CallToolResult<{
    status?: string;
    error_code?: string;
    message?: string;
    warnings?: Array<string>;
    project?: {
      project_root?: string;
      file_name?: string | null;
      file_path?: string | null;
      is_bound_document?: boolean;
      files?: Array<{
        file_name: string;
        description: string | null;
      }>;
      worksession_files?: Array<{file_name: string; file_path: string}> | null;
      files_page?: {
        total?: number;
        limit?: number;
        offset?: number;
        truncated?: boolean;
      };
    };
    named_views?: Array<{name?: string; id?: string}> | null;
    layouts?: Array<{name?: string; id?: string}> | null;
    layer_tree?: string | null;
    document?: {
      runtime_serial_number?: number | null;
      units?: string | null;
      absolute_tolerance?: number | null;
      angle_tolerance_radians?: number | null;
      modified?: boolean | null;
      object_count?: number | null;
      layer_count?: number | null;
    } | null;
    locations?: {
      plan_id?: string;
      step_id?: string;
      loop_no?: number;
      read_only?: boolean;
      plan_artifact_dir?: string | null;
      artifact_dir?: string | null;
      database?: string;
      path_rule?: string;
      artifact_rule?: string;
    };
    runtime?: {
      slot?: string;
      port?: number;
      session_dir?: string;
      scratch_root?: string;
      rhino_temp_at_attach?: string | null;
      rhino_temp_note?: string;
      python_executable?: string;
      attachment?: string;
      rhinocode?: {
        available?: boolean;
        executable?: string;
        pipe_id?: string;
        version?: unknown;
        languages?: Array<string>;
        message?: string;
      };
    };
    next_step_guide?: string;
    // native 오류 응답은 추가 근거 필드를 포함할 수 있습니다.
    [key: string]: unknown;
  }>>;
};
```

### 87. context\_05-upsert\_project\_file

```txt
프로젝트 파일 카탈로그에 모델 파일을 등록하거나, 등록된 파일의 설명을 수정합니다. 같은 프로젝트에서 Windows 기준으로 같은 이름은 한 파일입니다. 기존 파일은 원래 표기를 유지합니다. 이 작업은 Rhino에서 파일을 열거나 Worksession에 첨부하지 않습니다.

등록 결과는 context_04-get_project_info tool의 project.files에 나타납니다. Phase와 Scene은 그 목록의 파일명을 사용합니다.
```

```ts
declare const tools: { mcp__rhino__context_05_upsert_project_file(args: {
  // 프로젝트 안에서 고유한 모델 파일명입니다. 폴더는 생략합니다.
  file_name: string;
  // 생략하거나 null이면 기존 설명을 유지합니다. 빈 문자열은 설명을 비웁니다.
  description?: string | null;
}): Promise<CallToolResult<{
  status?: string;
  file_name?: string;
  description?: string | null;
  message?: string;
  error_code?: string;
}>>; };
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
declare const tools: { mcp__rhino__inspect_01_analyze_nested_blocks(args: {
  // 생략: 연결 문서. 지정 시 경로 일치 검사.
  expected_model_path?: string;
  // 기본 false.
  include_ids?: boolean;
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
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 43. inspect\_02-get\_objects

```txt
Rhino 문서의 최상위 모델 객체를 조회합니다. `current`는 표시되고 잠기지 않은 객체(화면 밖 포함), `document`는 숨김·잠금 객체도 포함합니다. 객체·그룹 ID와 메타데이터로 범위를 좁히고 객체, 요약 또는 계층으로 관찰합니다. 그룹은 선택한 범위와 구성원의 교집합입니다. 계층 조회는 그룹·블록 배치를 펼치며 문서 객체와 블록 정의 내부 항목을 구분합니다.

조건 하나로 객체의 UserDictionary를 조회하는 호출 예시는 `{"filters":{"user_dictionary":[{"source":"attributes","key":"brief_probe","any_of":["yes"]}]}}`입니다.

행과 면은 각각 페이지를 나눕니다. 행 후속 조회에는 같은 조건과 첫 응답의 snapshot·next_offset을, 면 후속 조회에는 document 객체 ID와 geometry_crc를 사용합니다. objects/summary의 complete는 전체 행이 첫 단일 응답에 포함되고 편집 상태가 안정적일 때 true입니다. 마지막 페이지는 next_offset=null로 확인합니다. hierarchy의 complete에는 관계 완전성도 반영되며 깊이 제한이 있을 수 있습니다. face_page.complete는 전체 면이 첫 단일 응답에 있을 때 true입니다.

표시 여부는 픽셀 가시성이나 가림 여부를 뜻하지 않습니다.
```

```ts
declare const tools: { mcp__rhino__inspect_02_get_objects(args: {
  // 1..8, 루트=1. 1 초과 시 recursive=true.
  depth?: number;
  // 객체 GUID별 CRC. 면 연속 조회 중 형상 변경 시 거부.
  expected_geometry_crcs?: {
    [key: string]: number;
  } | null;
  // 생략: 연결 문서. 지정 시 경로 일치 검사.
  expected_model_path?: string;
  // 첫 페이지 snapshot. offset > 0에서 필수.
  expected_snapshot?: string;
  // 1..128, 기본 128. objects 모드.
  face_limit?: number;
  // 기본 0. 양수: document object_ids와 각 객체의 expected_geometry_crcs 필수.
  face_offset?: number;
  // 선택 사항인 비어 있지 않은 필드 목록입니다. id, name, layer_path, object_type, geometry_kind, geometry_crc, visible, selected, hidden, locked, bounds, groups, user_dictionary, geometry_valid, solid, manifold, volume, faces, face_count를 사용할 수 있습니다. 형상 상세 정보와 faces에는 objects 모드가 필요합니다. summary는 fields를 거부합니다.
  fields?: Array<string> | null;
  // AND 조건입니다. layer_paths(정확한 전체 경로), object_types(관찰된 Rhino 이름), name_contains(대소문자 구분 없음), user_dictionary(source=attributes|geometry, key, 스칼라 any_of)를 사용할 수 있습니다.
  filters?: {
    [key: string]: unknown;
  } | null;
  // 어느 scope에서든 사용할 수 있는 선택 사항인 서로 다른 Rhino 그룹 GUID입니다(1..64개). 구성원과 선택한 범위의 교집합을 사용합니다. object_ids와 함께 사용하지 않습니다.
  group_ids?: Array<string> | null;
  // fields를 생략했을 때 objects 모드에서 형상 상세 정보를 포함합니다. 명시적인 fields가 우선합니다.
  include_geometry?: boolean;
  // 기본 false. true: ID 포함.
  include_ids?: boolean;
  // current에서만 사용하며 기본값은 false입니다. 활성 뷰포트 경계에 걸친 바운딩 박스를 포함합니다. 클리핑 평면이나 픽셀 가림 검사는 수행하지 않습니다. selected와 함께 사용할 수 없습니다.
  inside_window?: boolean;
  // 1..200, 기본 50.
  limit?: number;
  // document 범위에서만 사용할 수 있는 선택 사항인 서로 다른 최상위 객체 GUID입니다(1..4096개). group_ids와 함께 사용하지 않습니다.
  object_ids?: Array<string> | null;
  // 0..100000. 양수: expected_snapshot 필수.
  offset?: number;
  // 기본 false. true: hierarchy 모드.
  recursive?: boolean;
  // objects(기본), hierarchy, summary. recursive=true와 summary는 배타.
  result_mode?: string;
  // current(기본), document.
  scope?: string;
  // current에서만 사용하며 기본값은 false입니다. 화면 밖의 선택도 포함하여 적격한 선택 객체로 필터링합니다. inside_window와 함께 사용할 수 없습니다.
  selected?: boolean;
}): Promise<CallToolResult<{
  result: string;
}>>; };
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
    // editor 요청 시 공급자·명령·Undo 근거 포함. 기본 false.
    include_editor_details?: boolean;
    // viewport 등에서 ID 포함. 기본 false.
    include_ids?: boolean;
    // document, viewport, editor, viewports, named_views, layouts, layer_tree, display_modes 중 선택.
    // 생략 또는 null은 document, named_views, layouts, layer_tree, display_modes. []는 status와 warnings만.
    sections?: Array<string> | null;
  }): Promise<CallToolResult<{
    // 요청한 섹션·상태·경고 또는 오류 상세가 담긴 JSON 문자열.
    result: string;
  }>>;
};
```

### 45. inspect\_04-get\_selection\_references

```txt
현재 선택된 Rhino 객체의 소속 Holon과 상위 Holon을 참조하는 Plan을 찾습니다. 저장된 문서의 일반 모델에서 사용합니다.

Plan의 일치 Holon과 Plan 전체 대상은 다를 수 있습니다. 선택 객체와 Plan 목록의 잘림 여부는 각각 selection_truncated와 truncated로 확인합니다. result는 조회 결과 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: { mcp__rhino__inspect_04_get_selection_references(args: {
  // steps, references, geometry, artifacts, description, scope, audit, all. 생략·빈 배열: 요약.
  field_groups?: Array<string> | null;
  // 반환할 Plan 수: 1..500.
  limit?: number;
  // 검사할 선택 객체 수: 1..200.
  selection_limit?: number;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 46. inspect\_05-resolve\_targets

```txt
Plan에 등록된 Scene·Holon 대상과 선택한 Holon 정보를 조회합니다. Step 지정 시 해당 Plan 소속 여부를 확인하지만 대상은 Plan 기준입니다. Scene의 모든 Holon을 자동으로 확장하지 않습니다.

저장된 대상 조회이며 Rhino의 현재 구성원은 검증하지 않습니다. result는 조회 결과 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: { mcp__rhino__inspect_05_resolve_targets(args: {
  // references, geometry, scope, audit, all. 생략·빈 배열: 기본 요약.
  field_groups?: Array<string> | null;
  // plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다.
  plan_id: string;
  // Plan 소속 검사. 생략 시 Plan 기준.
  step_id?: string;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

## capture

### 17. capture\_01-conditioning\_pass

대응 오리지널: `capture_conditioning_pass`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
활성 Rhino 뷰의 카메라 경로를 따라 RGB·에지·깊이 PNG와 카메라 기록을 저장합니다. 관리형 연결은 Plan 작업 공간을 먼저 선택합니다. 촬영 중 활성 뷰가 변경되며 전체 뷰 상태의 복원은 보장되지 않습니다.

status와 frames_captured는 촬영 실행 결과이며 대상이 잘 보인다는 보장은 아닙니다. videos의 null은 MP4가 생성되지 않았음을 뜻합니다. 같은 출력 폴더를 재사용하면 기존 프레임·기록을 덮어쓰고 잔여 프레임이 남을 수 있습니다.
```

```ts
declare const tools: { mcp__rhino__capture_01_conditioning_pass(args: {
  // 청크당 프레임 수. 기본 16.
  chunk?: number;
  // 에지 프레임에 사용할 설치된 Rhino 디스플레이 모드이며, 기본값은 Technical입니다.
  edge_mode?: string;
  // 초당 프레임 수. 기본 16.
  fps?: number;
  // 짝수, 기본 480px.
  height?: number;
  // 기본 false: 가까울수록 밝음.
  invert_depth?: boolean;
  // 관리형 세션: 선택한 Plan의 산출물 디렉터리 아래 상대 폴더이며, 기본값은 conditioning입니다. 먼저 Plan을 선택합니다. 독립 실행: 출력 폴더이며, 기본값은 현재 작업 디렉터리입니다.
  out_dir?: string;
  // 쉼표 구분: rgb, edge, depth. 기본 전체.
  passes?: string;
  // RGB 프레임에 사용할 설치된 Rhino 디스플레이 모드이며, 기본값은 Rendered입니다.
  rgb_mode?: string;
  // 카메라 경로를 담은 JSON 문자열입니다. type=orbit은 center:[x,y,z], radius, height와 선택적 start_deg/end_deg/lens/target_height; type=track은 cam0/cam1/target0/target1 좌표와 선택적 lens; type=keyframes는 camera·target·선택적 lens를 가진 keyframes 배열입니다. frames 기본값은 81, lens는 mm, 좌표는 문서 단위입니다.
  shot: string;
  // 짝수, 기본 832px.
  width?: number;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 18. capture\_02-inspection

```txt
작업 화면을 유지하면서 여러 시점과 객체 범위를 하나의 PNG로 비교합니다. 객체 범위는 문서 표시 상태를 기준으로 하며 픽셀 가시성이나 가림을 보장하지 않습니다. 그룹 자동 확장과 블록 배치·정의 필터는 지원하지 않습니다.

설치된 표시 모드의 이름과 GUID는 inspect_03-get_document_context tool에서 sections=["display_modes"]로 조회합니다. Wireframe은 와이어와 곡선 검토, Shaded는 면과 입체 형태 검토, Technical은 가려진 선을 포함한 선 표현 검토에 적합합니다. 사용자 정의 래스터 모드도 설치된 이름이나 GUID로 선택할 수 있습니다. 이름이 중복되면 GUID를 사용합니다.

inspect_02-get_objects tool에서 include_ids=true로 최상위 모델 객체의 GUID를 확인합니다. 모든 타일을 같은 대상에 맞추려면 공통 object_ids에 GUID 배열을 넣고 views에서 각 방향과 모드를 선택합니다. 예를 들어 views=[{"direction":"top","display_mode":"Technical"},{"direction":"iso_ne","display_mode":"Shaded"}]는 같은 대상을 평면과 사시 방향으로 비교합니다. 원본 뷰 방향에서 지정 객체에 맞춰 확대하려면 공통 또는 타일별 object_ids와 함께 views=[{"direction":"current","frame_objects":true}]를 사용합니다. frame_objects를 생략한 current 타일은 원본 카메라 구도를 사용합니다.

일부 타일이 실패해도 status=success일 수 있습니다. 전체 성공 여부는 complete에서, 개별 결과와 적용된 모드의 이름·GUID는 tiles에서 확인합니다. PNG 전달과 image_file 저장은 별개입니다.
```

```ts
declare const tools: { mcp__rhino__capture_02_inspection(args: {
  // 선택 사항인 열 개수이며, 범위는 1..뷰 개수입니다. 생략하면 자동 격자를 사용합니다.
  columns?: number | null;
  // 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
  expected_model_path?: string;
  // 타일의 픽셀 높이로, 범위는 128..2048이며 기본값은 480입니다. 결합 이미지 제한도 적용됩니다.
  height?: number;
  // 선택 사항인, 목록에 있는 모델 뷰포트 GUID입니다. Layout/Detail이 활성화된 경우를 포함하여 해당 뷰포트를 활성화하지 않고 사용합니다.
  model_view_id?: string;
  // 공통 최상위 객체 GUID 1..4096개. 빈 배열 불가; 타일별 object_ids와 배타.
  object_ids?: Array<string> | null;
  // 타일 1..16개. direction: current(기본), top, bottom, front, back, left, right, iso_ne, iso_nw, iso_se, iso_sw, below_ne, below_nw, below_se, below_sw.\n  // display_mode: 설치된 이름/GUID, label: 최대 120자. object_ids: 최상위 GUID 1..512개; 생략·빈 배열은 공통 범위 또는 문서 표시 상태.
  views: Array<{
    [key: string]: unknown;
  }>;
  // 타일의 픽셀 너비로, 범위는 128..2048이며 기본값은 640입니다. 결합 이미지 제한도 적용됩니다.
  width?: number;
}): Promise<CallToolResult<{
  // 요청한 모든 타일을 캡처했는지 나타냅니다.
  complete?: boolean;
  // 오류 유형입니다.
  error_code?: string;
  // PNG 파일 저장 결과. 이미지 전달과 별개이며 저장 실패여도 이미지가 제공될 수 있음
  image_file?: {
    // 파일 바이트 수
    bytes?: number;
    // plan은 Plan 산출물, connection은 연결 정리까지의 임시 파일
    lifetime?: string;
    // 프로젝트 기준 PNG 상대 경로. output_refs에 기록할 때는 이 문자열만 사용
    path?: string;
    // 파일 해시.
    sha256?: string;
    // 파일 저장 결과입니다. saved일 때 path를 사용할 수 있습니다.
    status?: string;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // 이미지 캡처의 처리 상태입니다.
  status?: string;
  // 타일별 캡처 결과와 관찰 범위입니다. 실패한 타일도 포함합니다.
  tiles?: Array<{
    // 캡처한 시점입니다.
    direction?: string;
    // 0부터 시작하는 항목 인덱스
    index?: number;
    // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
    status?: string;
  }>;
}>>; };
```

### 19. capture\_03-current\_view

```txt
현재 Rhino 모델 뷰포트를 일반 화면 색과 선 표현으로 PNG에 캡처합니다. 캡처 중 문서의 PrintDisplay 설정은 유지됩니다. 대상 지정 시 실제 선택과 카메라가 바뀌며, isolate와 display_mode도 실제 화면 상태를 변경합니다. 설치된 모드의 이름과 GUID는 inspect_03-get_document_context tool에서 sections=["display_modes"]로 조회합니다. 작업 화면을 유지하면서 선택한 객체를 여러 방향이나 모드로 비교하려면 capture_02-inspection tool을 사용합니다. 격리 해제는 Rhino Unisolate를 사용합니다. 잠긴 주변 객체는 보일 수 있고, 선택·카메라는 별도로 확인해야 합니다.

PNG 이미지 전달과 image_file 저장은 별개입니다. include_usage의 토큰 수는 픽셀 기준 추정치입니다. labels는 주변 객체에도 표시되어 화면을 가릴 수 있습니다.
```

```ts
declare const tools: { mcp__rhino__capture_03_current_view(args: {
  // 레이블 확장 깊이: 1..8, 기본 1.
  depth?: number;
  // 선택 사항인 설치된 래스터 모드 이름/ID입니다. 제공하면 실제 모델 뷰포트를 변경합니다.
  display_mode?: string;
  // 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
  expected_model_path?: string;
  // 이미지의 픽셀 높이입니다. 128..2048 범위이며 width도 입력하고 scale_percent=100으로 지정합니다.
  height?: number | null;
  // true이면 이미지 크기와 픽셀 기준 토큰 추정치를 포함합니다.
  include_usage?: boolean;
  // 기본 false. true: target_ids 필수, 확대 전 Isolate.
  isolate?: boolean;
  // 기본 false. 주변 객체에도 최대 200개 표시 가능.
  labels?: boolean;
  // 이미지 해상도의 백분율입니다. 1..100 범위이며 기본값은 75입니다.
  scale_percent?: number;
  // 화면에서 선택·확대할 객체, 그룹 또는 Holon의 ID 배열입니다. 생략하면 현재 화면을 사용하며, 입력할 때는 하나 이상의 ID를 지정합니다.
  target_ids?: Array<string> | null;
  // object(기본), group, block, holon. block은 배치 객체 ID; 비기본값은 target_ids 필요.
  target_kind?: string;
  // 이미지의 픽셀 너비입니다. 128..2048 범위이며 height도 입력하고 scale_percent=100으로 지정합니다.
  width?: number | null;
}): Promise<CallToolResult<{
  // 오류 유형입니다.
  error_code?: string;
  // 실패한 단계입니다: validate, select, isolate, verify_selection, zoom_selected, redraw.
  failed_stage?: string;
  // 포커스 실행 전후에 확인한 대상과 뷰 상태입니다.
  focus_observation?: {
    // 포커스 작업 실패 후 관측한 뷰 상태입니다.
    after_failure?: {
      // 문서 단위의 카메라 위치 [x, y, z]입니다.
      camera_location?: Array<number>;
      // 문서 단위의 카메라 대상 [x, y, z]입니다.
      camera_target?: Array<number>;
      // 관측한 [left, right, bottom, top, near, far]입니다.
      frustum?: Array<number>;
      // 뷰 관측 중 확인하지 못한 정보의 오류입니다.
      observation_error?: string;
      // 평행 투영이면 true입니다.
      parallel_projection?: boolean;
      // 관측한 뷰포트의 UUID입니다.
      viewport_id?: string;
    };
    // 확대 작업 직전에 관측한 뷰 상태입니다.
    before_zoom?: {
      // 문서 단위의 카메라 위치 [x, y, z]입니다.
      camera_location?: Array<number>;
      // 문서 단위의 카메라 대상 [x, y, z]입니다.
      camera_target?: Array<number>;
      // 관측한 [left, right, bottom, top, near, far]입니다.
      frustum?: Array<number>;
      // 뷰 관측 중 확인하지 못한 정보의 오류입니다.
      observation_error?: string;
      // 평행 투영이면 true입니다.
      parallel_projection?: boolean;
      // 관측한 뷰포트의 UUID입니다.
      viewport_id?: string;
    };
    // 문서 단위의 대상 합집합 경계입니다.
    target_bounds?: {
      // 최대 [x, y, z] 좌표입니다.
      max?: Array<number>;
      // 최소 [x, y, z] 좌표입니다.
      min?: Array<number>;
    };
    // 대상 경계를 관측하지 못한 이유입니다.
    target_bounds_error?: string;
    // 포커스 대상으로 확인한 객체 수입니다.
    target_count?: number;
    // 대상 경계 확대의 관측 결과입니다. null이면 완료 여부를 확인하지 못했습니다.
    zoom_bounding_box?: boolean | null;
    // 기본 선택 확대의 관측 결과입니다. null이면 완료 여부를 확인하지 못했습니다.
    zoom_extents_selected?: boolean | null;
  };
  // PNG 저장 결과입니다. 이미지 전달 여부와 별도로 확인합니다.
  image_file?: {
    // 파일 바이트 수
    bytes?: number;
    // plan은 Plan 산출물, connection은 연결 정리까지의 임시 파일
    lifetime?: string;
    // 프로젝트 기준 PNG 상대 경로. output_refs에 기록할 때는 이 문자열만 사용
    path?: string;
    // 파일 해시.
    sha256?: string;
    // 파일 저장 결과입니다. saved일 때 path를 사용할 수 있습니다.
    status?: string;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 뷰 변경 적용 여부입니다. null이면 중간 상태를 확인해야 합니다.
  mutation_applied?: boolean | null;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // true이면 현재 Rhino 상태를 확인한 뒤 다음 작업을 정합니다.
  requires_reconciliation?: boolean;
  // 이미지 캡처의 처리 상태입니다.
  status?: string;
  // 이 호출에서 완료한 뷰 작업입니다. null인 항목은 시도 후 완료를 확인하지 못했습니다.
  view_change?: {
    // 화면 표시 모드 변경 완료 여부입니다.
    display_mode_changed?: boolean | null;
    // Isolate 완료 여부입니다.
    isolated?: boolean | null;
    // 격리된 객체의 가시성을 복구하는 Rhino 명령입니다. 카메라와 선택은 별도로 확인합니다.
    restore_visibility_command?: string;
    // 대상 선택 작업 완료 여부입니다.
    selection_changed?: boolean | null;
    // 성공한 확대 방식입니다. selected는 기본 선택 확대, bounding_box는 기본 방식 실패 후 대상 경계 확대입니다.
    zoom_method?: "selected" | "bounding_box";
    // 기본 선택 확대 또는 대상 경계 확대를 완료했는지 나타냅니다.
    zoom_selected?: boolean | null;
  };
}>>; };
```

### 20. capture\_04-defined\_view

```txt
저장된 Named View 또는 Layout 용지를 PNG로 캡처합니다. 이름·ID는 inspect_03-get_document_context tool에서 조회합니다.

Named View는 저장된 카메라를 사용하고, Layout은 용지와 Detail의 기존 표시 모드를 사용합니다. Named View에 사용할 설치 모드와 용도는 capture_02-inspection tool의 설명을 참고합니다. Layout에는 픽셀 크기와 display_mode를 지정할 수 없습니다. 이미지와 image_file 저장 결과는 별개이며, 사용량 추정·경고는 별도 text content로 반환됩니다. Layout은 인쇄 색과 선폭으로 출력하며 문서의 PrintDisplay 설정을 바꾸지 않습니다. 용지와 Detail에 보이는 인쇄 대상이 없으면 빈 PNG도 정상 결과입니다. Layout Detail 레이블은 지원하지 않습니다.
```

```ts
declare const tools: { mcp__rhino__capture_04_defined_view(args: {
  // 레이블 깊이: 1..8, 기본 1.
  depth?: number;
  // Named View 전용. 기본 Shaded; 설치된 래스터 모드 이름 또는 ID.
  display_mode?: string;
  // 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
  expected_model_path?: string;
  // 선택 사항인 Named View의 픽셀 높이로, 범위는 128..2048입니다. width도 제공하고 scale_percent=100으로 설정합니다. Layout에는 사용하지 않습니다.
  height?: number | null;
  // true이면 이미지 크기와 픽셀 기준 토큰 추정치를 포함합니다.
  include_usage?: boolean;
  // 기본 false. 최대 200개; 주변 레이블이 겹칠 수 있음.
  labels?: boolean;
  // 범위는 1..100이며 기본값은 75입니다. 원하는 상한이며, 백분율 캡처는 전달 용량 제한에 맞게 축소될 수 있습니다.
  scale_percent?: number;
  // 기존 이름 또는 ID입니다. 대소문자를 구분하지 않는 이름 일치는 유일해야 합니다.
  target: string;
  // named_view | layout.
  target_kind: string;
  // 선택 사항인 Named View의 픽셀 너비로, 범위는 128..2048입니다. height도 제공하고 scale_percent=100으로 설정합니다. Layout에는 사용하지 않습니다.
  width?: number | null;
}): Promise<CallToolResult<{
  // 오류 유형입니다.
  error_code?: string;
  // PNG 저장 결과입니다. 실제 치수와 축소 경고는 캡처 메타데이터에서 확인합니다.
  image_file?: {
    // 파일 바이트 수
    bytes?: number;
    // plan은 Plan 산출물, connection은 연결 정리까지의 임시 파일
    lifetime?: string;
    // 프로젝트 기준 PNG 상대 경로. output_refs에 기록할 때는 이 문자열만 사용
    path?: string;
    // 파일 해시.
    sha256?: string;
    // 파일 저장 결과입니다. saved일 때 path를 사용할 수 있습니다.
    status?: string;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // 오류 등에서 반환. 성공 응답에는 없을 수 있음.
  status?: string;
}>>; };
```

## scene

### 65. scene\_01-add\_objects

```txt
Rhino 객체를 Scene에 포함하거나 해당 Scene에서 제외했던 Holon 구성원을 복원합니다.
```

```ts
declare const tools: { mcp__rhino__scene_01_add_objects(args: {
  // 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
  expected_model_path?: string;
  // 일반 형상이나 클리핑 평면을 포함하는 객체 GUID 배열로, 최대 4096개 항목을 허용합니다.
  object_ids: Array<string>;
  // scene_07-list tool(include_ids=true)에서 얻은 기존 Scene ID입니다.
  scene_id: string;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 66. scene\_02-create

대응 오리지널: `create_design_scene`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
설계 영역·프로그램·상황을 나타내는 Scene을 생성합니다.
```

```ts
declare const tools: { mcp__rhino__scene_02_create(args: {
  // project.files의 등록 파일명입니다. 생략하거나 빈 값으로 연결 없이 생성할 수 있습니다.
  file_name?: string;
  // 설계 영역 또는 행위/프로그램 맥락을 설명하는 Scene 이름입니다. 비어 있으면 Untitled가 됩니다.
  name: string;
  // Scene에 기록할 단위입니다. mm, cm, m, in, ft 중 하나를 선택합니다.
  units?: string;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 67. scene\_03-focus\_holons

```txt
선택한 Holon과 하위 Holon의 현재 유효 구성원을 Rhino에서 선택·격리·확대합니다. 잠긴 주변 객체는 보일 수 있습니다. Unisolate로 격리 전 표시 상태를 복원할 수 있지만, 선택과 카메라는 별도로 변경된 상태로 남을 수 있습니다.

result는 선택된 객체와 격리·확대 결과 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: { mcp__rhino__scene_03_focus_holons(args: {
  // 생략: 연결된 문서. 지정 시 연결 문서와 일치해야 함.
  expected_model_path?: string;
  // 서로 다른 Holon ID 1~32개. 유효 최상위 객체 최대 4096개.
  holon_ids: Array<string>;
}): Promise<CallToolResult<{ result: string }>>; };
```

### 68. scene\_04-get

대응 오리지널: `get_design_scene`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
Scene의 등록 정보와 Holon·객체 수를 조회합니다. 저장된 요약이며 현재 Rhino 구성원을 실시간 검증하지 않습니다. 객체 수가 null이면 수를 확정할 수 없는 상태입니다. 현재 구성원은 scene_06-get_objects tool로 조회합니다.

result는 scene 또는 오류를 담은 JSON 문자열입니다. include_ids=true여도 입력한 scene_id는 반복 반환하지 않습니다.
```

```ts
declare const tools: { mcp__rhino__scene_04_get(args: {
  // scope, state, geometry, audit, all. 생략·빈 배열: 요약.
  field_groups?: Array<string> | null;
  // 기본 false. 범위에 관련 식별자를 포함합니다.
  include_ids?: boolean;
  scene_id: string;
}): Promise<CallToolResult<{ result: string }>>; };
```

### 69. scene\_05-get\_holon

```txt
Holon의 등록 정보와 구성원을 조회합니다. 기본값은 저장된 정보이며, live=true는 현재 Rhino 그룹·형상을 조회하고 등록 정보와의 차이를 확인합니다. requires_sync는 동기화 필요 여부입니다.

recursive=true는 자손 Holon을 포함한 유효 구성원을 확장합니다. 이는 Holon 계층이며 Rhino 블록 정의의 내부 확장이 아닙니다. result는 Holon 정보 또는 오류를 담은 JSON 문자열입니다. include_ids=true여도 입력한 holon_id는 요약에 반복 반환되지 않습니다.
```

```ts
declare const tools: { mcp__rhino__scene_05_get_holon(args: {
  // references, geometry, scope, audit, all. 생략·빈 배열: 요약.
  field_groups?: Array<string> | null;
  holon_id: string;
  // 기본 false. true: 요청 그룹에 해당하는 ID 포함.
  include_ids?: boolean;
  // 기본 false. true: 현재 Rhino 구성원·형상 조회.
  live?: boolean;
  // 기본 false. true: 자손 Holon 확장.
  recursive?: boolean;
}): Promise<CallToolResult<{ result: string }>>; };
```

### 70. scene\_06-get\_objects

```txt
Scene의 직접 객체와 Holon 구성원을 현재 Rhino 문서에서 조회합니다. Scene에서 제외한 구성원은 목록에 포함되지 않습니다.

result는 objects, total, limit, offset, truncated 및 live_verified 또는 오류를 담은 JSON 문자열입니다. truncated=true이면 같은 조건에서 offset을 limit만큼 늘려 다음 페이지를 조회합니다.
```

```ts
declare const tools: { mcp__rhino__scene_06_get_objects(args: {
  // 생략: 연결된 문서. 지정 시 연결 문서와 일치해야 함.
  expected_model_path?: string;
  // scope, state, geometry, audit, all. 생략·빈 배열: 요약.
  field_groups?: Array<string> | null;
  // 기본 false. true: 객체 GUID 포함.
  include_ids?: boolean;
  // 1~200, 기본 50.
  limit?: number;
  // 0부터 시작. 기본 0.
  offset?: number;
  scene_id: string;
}): Promise<CallToolResult<{ result: string }>>; };
```

### 71. scene\_07-list

```txt
공유 프로젝트 DB에 등록된 Scene 목록을 조회합니다. 파일명을 생략하면 연결된 파일뿐 아니라 프로젝트의 모든 파일을 포함합니다.

result는 scenes, total, limit, offset, truncated를 담은 JSON 문자열입니다. truncated=true이면 같은 필터에서 offset을 limit만큼 늘려 다음 페이지를 조회합니다. Scene 상세는 scene_04-get tool, 현재 Rhino 구성원은 scene_06-get_objects tool로 확인합니다.
```

```ts
declare const tools: { mcp__rhino__scene_07_list(args: {
  // scope, state, geometry, audit, all. 생략·빈 배열: 요약.
  field_groups?: Array<string> | null;
  // 확장자를 포함한 정확한 프로젝트 파일명. 생략: 전체 파일.
  file_name?: string;
  // 기본 false. true: scene_id 등 포함.
  include_ids?: boolean;
  // 1~200, 기본 50.
  limit?: number;
  // Scene 이름 부분 검색. 대소문자 무관.
  name?: string;
  // 0부터 시작. 기본 0.
  offset?: number;
}): Promise<CallToolResult<{ result: string }>>; };
```

### 72. scene\_08-list\_holons

```txt
모델에 등록된 Holon 목록을 조회합니다. Scene을 지정하면 연결된 Holon을 조회하며, recursive=true이면 그 자손도 포함합니다. 자손은 해당 Scene에 직접 등록되어 있지 않을 수 있습니다. Scene 미지정 시 기본 목록은 최상위 Holon입니다.

목록은 저장된 등록 정보이며 현재 Rhino 구성원의 실시간 검증 결과가 아닙니다. 현재 구성원은 scene_05-get_holon tool의 live=true로 조회합니다. result는 목록 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: { mcp__rhino__scene_08_list_holons(args: {
  // 관리형 기본: 연결된 모델. 지정 경로에 등록된 Holon이 없으면 빈 목록.
  expected_model_path?: string;
  // references, geometry, scope, audit, all. 생략·빈 배열: 요약.
  field_groups?: Array<string> | null;
  // 기본 false. true: 후속 호출용 ID 포함.
  include_ids?: boolean;
  // 기본 false. true: 자손 포함.
  recursive?: boolean;
  // 생략·빈 문자열: Scene 필터 없음.
  scene_id?: string;
}): Promise<CallToolResult<{ result: string }>>; };
```

### 73. scene\_09-remove\_holon

```txt
Holon 등록을 해제하고 Rhino 형상과 그룹은 유지합니다.
```

```ts
declare const tools: { mcp__rhino__scene_09_remove_holon(args: {
  // 등록을 해제할 Holon ID입니다. 이 Holon을 참조하는 부모 Holon과 Plan의 관계를 먼저 해제합니다.
  holon_id: string;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 74. scene\_10-remove\_objects

```txt
객체를 Scene에서 제외합니다. Rhino 형상과 Holon 그룹은 유지됩니다.
```

```ts
declare const tools: { mcp__rhino__scene_10_remove_objects(args: {
  // 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
  expected_model_path?: string;
  // 일반 형상 또는 클리핑 평면을 포함하는 객체 GUID 배열이며, 최대 4096개 항목을 받습니다.
  object_ids: Array<string>;
  // scene_07-list tool(include_ids=true)에서 얻은 기존 Scene ID입니다.
  scene_id: string;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 75. scene\_11-sync\_holon

```txt
Rhino의 현재 구성원을 읽어 Holon 등록 정보를 갱신합니다.
```

```ts
declare const tools: { mcp__rhino__scene_11_sync_holon(args: {
  // 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
  expected_model_path?: string;
  // 단일 대상의 상태 대조 및 정합성 확인에 사용할 등록된 Holon ID입니다. 선택 사항입니다.
  holon_id?: string;
  // 명시적 Holon ID 일괄 목록입니다. 선택 사항이며, 단일 Holon/그룹 선택자와 함께 사용하지 않습니다.
  holon_ids?: Array<string> | null;
  // holon_id와 함께 제공하는 선택 항목으로, 현재 Rhino 그룹 GUID의 일관성을 확인합니다. 이 값만으로 그룹을 선택하거나 연결 대상을 바꾸지 않습니다.
  rhino_group_id?: string;
  // 구성원을 갱신할 Scene ID입니다. holon_id, holon_ids, rhino_group_id와 함께 입력하지 않습니다.
  scene_id?: string;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 76. scene\_12-update

```txt
Scene의 프로젝트 파일 연결을 변경하거나 해제합니다.
```

```ts
declare const tools: { mcp__rhino__scene_12_update(args: {
  // project.files의 등록 파일명입니다. 빈 문자열은 연결 해제, 생략 또는 null은 기존 연결 유지입니다.
  file_name?: string | null;
  // scene_07-list tool(include_ids=true) 또는 기록된 Scene 참조에서 얻은 기존 Scene ID입니다.
  scene_id: string;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 77. scene\_13-upsert\_holon

```txt
물리적 요소와 관계를 Holon으로 등록하거나 갱신합니다.
```

```ts
declare const tools: { mcp__rhino__scene_13_upsert_holon(args: {
  // 등록된 자식 Holon 목록입니다. 선택 사항이며, []는 기존 자식을 분리하고 생략하면 유지합니다. 자식당 부모는 하나만 허용하고 계층 순환을 금지합니다.
  child_holon_ids?: Array<string> | null;
  // 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
  expected_model_path?: string;
  // 수정할 기존 Holon ID입니다. 선택 사항이며, 생략하면 등록을 생성합니다.
  holon_id?: string;
  // 의미적 Holon 이름입니다. 기존 Rhino 그룹에 연결할 때는 해당 그룹의 정확한 이름과 일치해야 합니다.
  name: string;
  // 등록할 최상위 Rhino 객체 GUID 배열입니다. 각 객체는 하나의 Holon에 속합니다. 생략하면 name과 일치하는 기존 그룹을 사용합니다. []는 child_holon_ids가 있는 부모에만 사용합니다.
  object_ids?: Array<string> | null;
  // 기존 Rhino 그룹의 정확한 GUID입니다. 선택 사항이며, 이름의 모호성을 해소하는 데 사용합니다.
  rhino_group_id?: string;
  // Holon이 속할 기존 Scene ID 배열입니다. 새 Holon에는 필수이며, 수정 시 생략하면 유지합니다.
  scene_ids?: Array<string> | null;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

## plan

### 54. plan\_02-create

대응 오리지널: `create_generation_plan`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
Phase 또는 Plan을 생성합니다. Plan은 scope에 맞는 Step을 자동으로 만들며 **작업을 실행하지 않습니다.**

`result`는 생성된 `phase_id` 또는 `plan_id`와 상태를 담은 JSON 문자열입니다. 생성 오류도 `result.status`에 반환될 수 있습니다. Plan은 초기 loop_no=0, revision=1로 생성됩니다. 생성된 Plan의 Step은 plan_05-get tool에서 확인할 수 있습니다.
```

```ts
declare const tools: { mcp__rhino__plan_02_create(args: {
  request: {
    // 같은 종류의 ID 형식만 검사하며 대상 존재·순환·작업 순서를 검증하거나 강제하지 않습니다.
    depends_on?: Array<string> | null;
    description?: string;
    // project.files에 등록된 파일명 하나 또는 배열. 생략하면 파일 연결 없음.
    file_name?: string | Array<string>;
    // 공백만 있는 이름은 허용하지 않습니다.
    name: string;
    // 이전 Phase 참조. 같은 종류의 ID 형식을 검사하며 존재는 검증하지 않습니다.
    previous_id?: string | null;
    // 생략하면 pending.
    status?: "pending" | "running" | "paused" | "completed" | "failed" | "blocked";
    target: "phase";
  } | {
    // 기록할 하위 Plan ID. 상대 Plan을 자동 수정하거나 존재를 검증하지 않습니다.
    child_plan?: Array<string> | null;
    // 같은 종류의 ID 형식만 검사하며 대상 존재·순환·작업 순서를 검증하거나 강제하지 않습니다.
    depends_on?: Array<string> | null;
    // 공백만 있는 목표는 허용하지 않습니다.
    goal: string;
    // 작업 대상인 기존 Holon ID 배열.
    holon_ids?: Array<string> | null;
    // 기록할 상위 Plan ID. 상대 Plan을 자동 수정하거나 존재를 검증하지 않습니다.
    parent_plan?: Array<string> | null;
    // 기존 Phase ID. 생략·빈 문자열은 소속 없음.
    phase_id?: string;
    // 이전 Plan 참조. 같은 종류의 ID 형식을 검사하며 존재는 검증하지 않습니다.
    previous_id?: string | null;
    // 단일 Scene의 호환 입력. scene_ids와 함께 쓰면 첫 항목과 같아야 합니다.
    scene_id?: string;
    // 기존 Scene ID 배열. 생략하면 scene_id를 사용하고 둘 다 없으면 Scene 연결 없음.
    scene_ids?: Array<string> | null;
    // Step 템플릿. 생략하면 house. 기본 제공: spatial_development, drawing_development, semantic_exploration, plan_editing, model_revision, inspection, structure, construction_detail, drawing, component, house, interior. 등록된 사용자 템플릿도 사용 가능.
    scope?: string;
    target: "plan";
    // 공백만 있는 제목은 허용하지 않습니다.
    title: string;
  };
}): Promise<CallToolResult<{ result: string; }>>; };
```

### 55. plan\_03-execute\_looping

```txt
Plan의 새 작업 회차를 시작하거나 최신 회차를 재개합니다. Step 실행은 에이전트가 직접 수행합니다.

새 회차는 Step을 pending으로 시작하며 이전 회차의 상태와 참조는 previous_loop에 반환합니다. resume=true는 기존 회차를 유지하며, 피드백을 생략하거나 비우면 기존 피드백을 유지합니다. 실행된 회차가 없으면 재개할 수 없습니다. next_step_id는 미완료 첫 Step이며 없으면 null입니다.
```

```ts
declare const tools: { mcp__rhino__plan_03_execute_looping(args: {
  // 최초 산출물 폴더명. 생략 시 목표 기반, YYMMDD_ 접두사. 기존 폴더 재사용.
  artifact_name?: string;
  // 재개 시 생략·빈 문자열은 기존 값 유지.
  feedback?: string;
  plan_id: string;
  // 기본 false: 새 회차. true: 최신 회차 재개.
  resume?: boolean;
}): Promise<CallToolResult<{
  artifact_dir?: string | null;
  error_code?: string;
  feedback?: string;
  goal?: string;
  loop_no?: number;
  message?: string;
  next_step_guide?: string;
  next_step_id?: string | null;
  plan_artifact_dir?: string;
  plan_id?: string;
  plan_status?: string;
  policy_reminder?: string;
  previous_loop?: {
    loop_no?: number;
    steps?: Array<{
      step_id?: string;
      step_type?: string;
      name?: string;
      position?: number;
      kind?: string;
      status?: string;
      loop_no?: number;
      depends_on?: Array<string>;
      input_refs?: Array<string>;
      output_refs?: Array<string>;
      [key: string]: unknown;
    }>;
    [key: string]: unknown;
  } | null;
  revision?: number;
  status?: string;
  step_id?: string;
  steps?: Array<{
    step_id?: string;
    step_type?: string;
    name?: string;
    position?: number;
    kind?: string;
    status?: string;
    loop_no?: number;
    depends_on?: Array<string>;
    input_refs?: Array<string>;
    output_refs?: Array<string>;
    [key: string]: unknown;
  }>;
  title?: string;
}>>; };
```

### 56. plan\_05-get

대응 오리지널: `get_generation_plan`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
Phase, Plan 또는 Step의 작업 기록을 조회합니다. 기본값은 식별·상태 요약이며, include_details=true이면 선택한 대상의 상세를 함께 반환합니다. Plan 상세에는 Step 요약이, Step 상세에는 입출력 참조와 Takeaways·Design rationale이 포함됩니다. 다음 작업에 필요한 파일은 반환된 프로젝트 상대경로를 열어 내용을 확인합니다.

`result`는 조회 결과 또는 오류를 담은 JSON 문자열입니다. 성공 시 status는 대상의 작업 상태이며, 오류는 status=error입니다. Plan과 Step은 `loop_no`·`revision`·`read_only`를 함께 반환합니다. **revision을 명시하면 현재 번호여도 읽기 전용 스냅샷**입니다.
```

```ts
declare const tools: { mcp__rhino__plan_05_get(args: {
  request: {
    // 기본 false. true이면 Phase 상세를 포함합니다.
    include_details?: boolean;
    phase_id: string;
    target: "phase";
  } | {
    // 기본 false. true이면 Plan 상세와 Step 요약을 포함합니다.
    include_details?: boolean;
    // 0 이상의 Loop 번호. 생략·null이면 최신 Loop, 0은 실행 전 기록.
    loop_no?: number | null;
    plan_id: string;
    // 선택한 Loop의 리비전. 생략·null이면 해당 Loop의 최신 상태; 지정하면 읽기 전용 스냅샷.
    revision?: number | null;
    target: "plan";
  } | {
    // 기본 false. true이면 이 Step의 유형, 입출력 참조, Takeaways와 Design rationale을 포함합니다.
    include_details?: boolean;
    // 0 이상의 Loop 번호. 생략·null이면 최신 Loop, 0은 실행 전 기록.
    loop_no?: number | null;
    plan_id: string;
    // 선택한 Loop의 리비전. 생략·null이면 해당 Loop의 최신 상태; 지정하면 읽기 전용 스냅샷.
    revision?: number | null;
    // 해당 Plan에 속한 Step ID.
    step_id: string;
    target: "step";
  };
}): Promise<CallToolResult<{ result: string; }>>; };
```

### 57. plan\_07-list\_revisions

```txt
Plan의 저장 리비전 목록을 최신 회차·리비전 순으로 조회합니다. Loop나 Step으로 필터링할 수 있으며, Step 필터는 그 Step의 직접 변경만 포함합니다.

result는 revisions, total, limit, truncated를 담은 JSON 문자열입니다. offset은 지원하지 않으며 limit은 최대 500입니다. 선택한 과거 기록은 plan_05-get tool에서 같은 loop_no와 revision으로 조회합니다.
```

```ts
declare const tools: { mcp__rhino__plan_07_list_revisions(args: {
  // audit 또는 all: 생성 시각 포함. 생략·빈 배열: 기본 필드.
  field_groups?: Array<string> | null;
  // 1~500, 기본 50.
  limit?: number;
  // 생략·null: 전체. 0: 실행 전 기록.
  loop_no?: number | null;
  plan_id: string;
  // 생략·빈 문자열: Plan 전체.
  step_id?: string;
}): Promise<CallToolResult<{ result: string }>>; };
```

### 58. plan\_08-list

```txt
Phase·Plan 목록 또는 한 Plan의 순서 있는 Step 목록을 조회합니다.

`result`는 상태와 `phases`·`plans`·`steps` 중 해당 목록을 담은 JSON 문자열입니다. `total`과 `truncated`는 목록 크기와 잘림 여부를 나타냅니다. **offset은 지원하지 않으며** `limit`은 최대 500입니다. Step 조회는 같은 스냅샷의 `loop_no`·`revision`과 `read_only`를 함께 반환합니다.
```

```ts
declare const tools: { mcp__rhino__plan_08_list(args: {
  request: {
    // description: 설명, scope: 연결 파일, audit: 생성·수정 시각, all: 전체. 생략·빈 배열은 요약.
    field_groups?: Array<string> | null;
    // 1~500, 기본 50.
    limit?: number;
    target: "phase";
  } | {
    // 1~500, 기본 50.
    limit?: number;
    // 생략·빈 문자열이면 Phase 소속 여부와 관계없이 포함.
    phase_id?: string;
    // 생략·빈 문자열이면 Scene 소속 여부와 관계없이 포함.
    scene_id?: string;
    // 생략·빈 문자열이면 모든 상태.
    status?: "" | "pending" | "running" | "paused" | "completed" | "failed" | "blocked";
    target: "plan";
  } | {
    // 1~500, 기본 50. 지정 순서의 앞부분부터 반환.
    limit?: number;
    // 0 이상의 Loop 번호. 생략·null은 최신, 0은 실행 전 기록.
    loop_no?: number | null;
    plan_id: string;
    // 선택한 Loop의 저장 리비전. 생략·null은 최신 상태; 지정하면 읽기 전용 스냅샷.
    revision?: number | null;
    target: "step";
  };
}): Promise<CallToolResult<{ result: string; }>>; };
```

### 59. plan\_09-rename\_artifact\_folder

```txt
Plan의 산출물 폴더 이름을 바꾸고 현재 Plan·Step의 저장 경로 참조를 갱신합니다. 먼저 plan_10-set_working tool으로 산출물 폴더를 지정해야 합니다.

Loop 실행 이후 또는 다른 Plan의 과거 Loop가 참조하는 폴더는 실제 이름을 변경할 수 없습니다. 같은 이름 요청은 변경 없이 성공하며, 대상 폴더가 이미 존재하거나 다른 Plan에 속하면 실패합니다. 기존 revision은 유지됩니다.
```

```ts
declare const tools: { mcp__rhino__plan_09_rename_artifact_folder(args: {
  // 폴더명 하나. YYMMDD_가 없으면 현재 날짜 추가. 경로·Windows 금지 문자 불가.
  name: string;
  // 생략 또는 빈 문자열: 현재 선택된 Plan.
  plan_id?: string;
}): Promise<CallToolResult<{
  // 변경 후 프로젝트 상대 경로.
  artifact_dir?: string | null;
  error_code?: string;
  message?: string;
  next_step_guide?: string;
  // 실제 변경된 경우 이전 경로.
  previous_artifact_dir?: string;
  status?: string;
}>>; };
```

### 60. plan\_10-set\_working

```txt
현재 연결에서 Plan과 선택적인 Step을 산출물 작업 대상으로 선택합니다. 선택 자체는 **작업 실행이나 Plan·Step 상태 변경이 아닙니다.**

최초 선택은 Plan 산출물 경로를 정하며 revision이 증가할 수 있습니다. 이후에는 같은 Plan의 경로를 재사용합니다. Loop 시작 전 `artifact_dir`은 Plan 루트, 시작 후에는 현재 Loop의 번호 폴더입니다. 반환된 `loop_no`와 `revision`은 선택 시점의 값입니다.
```

```ts
declare const tools: { mcp__rhino__plan_10_set_working(args: {
  // 최초 폴더명. 생략 시 목표에서 정하고 YYMMDD_ 접두사를 붙임. 기존 폴더와 다른 이름은 거부.
  artifact_name?: string;
  // 현재 Loop 보호 값. 생략·null은 현재 Loop. 이전·존재하지 않는 Loop 선택 불가.
  loop_no?: number | null;
  plan_id: string;
  // 생략 시 Plan만 선택.
  step_id?: string;
}): Promise<CallToolResult<{
  artifact_dir?: string | null;
  error_code?: string;
  loop_no?: number;
  message?: string;
  next_step_guide?: string;
  // Plan 산출물 루트의 프로젝트 상대 경로
  plan_artifact_dir?: string;
  plan_id?: string;
  revision?: number;
  status?: string;
  // Step 미선택 시 빈 문자열
  step_id?: string;
}>>; };
```

### 61. plan\_12-update

대응 오리지널: `update_generation_step`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
Phase·Plan의 작업 정보 또는 Step의 상태, 입출력 참조, Takeaways·Design rationale을 수정합니다. Plan·Step은 현재 Loop만 변경할 수 있습니다.

`depends_on`, `input_refs`, `output_refs`는 add/remove 패치이며 Plan의 대상·산출물·상하위 관계 배열은 전체 교체합니다. 생략 또는 null은 유지, 교체 배열의 []는 비웁니다. `takeaways`와 `design_rationale`은 빈 문자열로 비웁니다.

응답은 JSON 문자열입니다. `changed`는 실제 변경 여부, `issues`는 건너뛴 항목입니다. 중복·충돌 등 적용하지 못한 패치 항목은 `issues`에 기록하며, 일부만 적용되면 `partial_success`를 반환합니다. Loop 실행 후 `expected_revision`을 지정할 때는 `loop_no`도 함께 지정합니다.

Step을 실제로 `completed`로 바꾸려면 먼저 `confirmation_required`와 `confirmation`의 경고·선택지를 읽고 에이전트가 후속 호출에서 선택합니다. 보존할 객체가 있으면 먼저 `completion_token`과 `completion_decision=no`로 취소하고, 객체를 temp 밖으로 옮긴 후 새로 완료를 요청합니다. 정리할 범위가 확인되면 같은 요청 필드와 함께 새 `confirmation.token`을 `completion_token`에 넣어 `completion_decision=yes`로 답합니다. 토큰은 발급된 연결과 요청에서 한 번만 사용할 수 있으며, 발급 뒤 Loop 또는 리비전이 바뀌면 새로 확인해야 합니다.

Yes는 Step 완료를 먼저 저장한 뒤 현재 연결 문서의 temp와 그 하위 레이어에 속한 객체를 제거합니다. 최상위 temp 레이어를 유지하고 그 하위 레이어를 모두 삭제합니다. 로컬 블록 정의에서도 해당 레이어의 구성원만 제거하며, 정의와 temp 밖 인스턴스의 배치를 보존합니다. Worksession 첨부, PlanSection 관리 데이터, Step 참조가 가리키는 파일도 보존합니다. 정리 건수는 `cleanup`에 있습니다. 실패 시 `cleanup_state`와 Step 상태를 읽습니다. Step 완료를 저장한 뒤 정리가 실패하면 `requires_reconciliation=true`를 반환하므로 Rhino의 temp 상태를 확인합니다.
```

```ts
declare const tools: { mcp__rhino__plan_12_update(args: {
  request: {
    // 동일 종류 ID의 add/remove 패치. 존재·순환·완료 여부는 검사하지 않음.
    depends_on?: {
      add?: Array<string>;
      remove?: Array<string>;
    } | null;
    // 빈 문자열은 설명 삭제.
    description?: string | null;
    // 빈 문자열 또는 []는 연결 해제.
    file_name?: string | Array<string> | null;
    // 빈 이름 불가.
    name?: string | null;
    phase_id: string;
    // 빈 문자열은 연결 해제.
    previous_id?: string | null;
    status?: "pending" | "running" | "paused" | "completed" | "failed" | "blocked" | null;
    target: "phase";
  } | {
    artifact_refs?: Array<string> | null;
    // 상호 관계 자동 변경 및 참조 대상 존재 검증 없음.
    child_plan?: Array<string> | null;
    depends_on?: {
      add?: Array<string>;
      remove?: Array<string>;
    } | null;
    expected_revision?: number | null;
    // 빈 목표 불가.
    goal?: string | null;
    holon_ids?: Array<string> | null;
    loop_no?: number | null;
    // 상호 관계 자동 변경 및 참조 대상 존재 검증 없음.
    parent_plan?: Array<string> | null;
    // 빈 문자열은 소속 해제.
    phase_id?: string | null;
    plan_id: string;
    // 빈 문자열은 연결 해제.
    previous_id?: string | null;
    scene_ids?: Array<string> | null;
    status?: "pending" | "running" | "paused" | "completed" | "failed" | "blocked" | null;
    target: "plan";
    // 빈 제목 불가.
    title?: string | null;
  } | {
    // 완료 경고를 받은 뒤 선택할 값입니다.
    completion_decision?: "yes" | "no" | null;
    // 앞선 완료 확인 결과의 confirmation.token입니다.
    completion_token?: string | null;
    expected_revision?: number | null;
    input_refs?: {
      add?: Array<string>;
      remove?: Array<string>;
    } | null;
    loop_no?: number | null;
    output_refs?: {
      add?: Array<string>;
      remove?: Array<string>;
    } | null;
    plan_id: string;
    status?: "pending" | "running" | "paused" | "completed" | "failed" | "blocked" | null;
    step_id: string;
    // Takeaways. 다음 작업에 전달할 핵심 결론이나 확인 사항입니다. 생략 또는 null은 유지하고 빈 문자열은 비웁니다.
    takeaways?: string | null;
    // Design rationale. 설계 결정을 내린 이유와 근거입니다. 생략 또는 null은 유지하고 빈 문자열은 비웁니다.
    design_rationale?: string | null;
    target: "step";
  };
}): Promise<CallToolResult<{
  // 수정 결과, Step 완료 확인 또는 Rhino 정리 결과가 담긴 JSON 문자열.
  result: string;
}>>; };
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
    // 1~600초의 정수, 기본 60초.
    timeout_seconds?: number;
  }): Promise<CallToolResult<{
    // 실행에 사용된 산출물 폴더.
    artifact_dir?: string | null;
    completed?: boolean;
    error_code?: string;
    message?: string;
    // completed, partial, not_started, unknown.
    mutation_state?: string;
    next_step_guide?: string;
    // script_03-get_execution tool에서 상태와 저장된 결과를 조회할 때 사용합니다.
    request_id?: string;
    result?: unknown;
    result_display_error?: string | null;
    // 결과 회수·해석 중 오류이며 문서 변경의 롤백을 의미하지 않습니다.
    result_error?: string | null;
    // 잘린 결과의 다음 페이지는 request_id와 해당 필드·offset으로 script_03-get_execution tool에서 조회합니다.
    result_page?: {
      available_fields?: Array<string>;
      // 배열·문자열 전체 결과는 result 키를 사용합니다.
      pages?: {
        [key: string]: {
          // null이면 마지막 페이지.
          next_offset?: number | null;
          offset?: number;
          // 항목 수 또는 문자열 길이.
          returned?: number;
          total?: number;
        };
      };
      // object, array, string, scalar.
      type?: string;
      // 문자열 페이지 위치의 단위.
      unit?: string;
    };
    status?: string;
  }>>;
};
```

### 79. script\_02-run\_rhino

대응 오리지널: `execute_rhino_script`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
연결된 RhinoCode에서 모델링·편집·측정 코드를 실행합니다. 전용 도구로 처리하기 어려운 작업에 사용합니다.
```

```ts
declare const tools: { mcp__rhino__script_02_run_rhino(args: {
  // python(기본값 Python 3), python2, csharp, csharp-script 또는 command입니다. 모든 모드는 공식 RhinoCode를 사용합니다.
  language?: string;
  // 동기식 Python 소스, C# 문장 본문 또는 명령 매크로입니다. Python은 JSON-safe 값을 result에, C#은 결과 JSON을 result_json에 할당합니다. doc은 연결된 문서입니다. command는 !·Pause·대화상자 없이 끝나는 매크로를 입력합니다.
  script: string;
  // 1-600의 정수이며 기본값은 60입니다. 대기 시간만 제한합니다. 시간 초과 후에는 동일한 요청을 조회합니다.
  timeout_seconds?: number;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 80. script\_03-get\_execution

```txt
이전에 요청한 RhinoCode 실행의 상태와 보관된 결과·로그를 조회합니다. **코드를 다시 실행하지 않습니다.** request_id를 생략하면 현재 연결의 가장 최근 실행을 조회하며, beyond·CoS에서는 ID를 지정해 원래 실행 연결을 찾습니다. 연결이 끝난 뒤에도 해당 실행 기록이 남아 있으면 조회할 수 있습니다.

결과의 배열이나 문자열은 페이지로 조회할 수 있습니다. 로그는 별도의 바이트 오프셋을 사용합니다.
```

```ts
declare const tools: {
  mcp__rhino__script_03_get_execution(args: {
    // 기본 false.
    include_diagnostics?: boolean;
    // 결과의 식별자 포함 여부. 기본 true.
    include_ids?: boolean;
    // 기본 true.
    include_result?: boolean;
    // stdout·stderr와 CLI 로그 포함 여부. 기본 false.
    include_stdout?: boolean;
    // 결과 페이지 크기. 1~1000, 기본 100. 로그는 별도 크기 제한 적용.
    limit?: number;
    // 결과는 배열 항목 또는 문자열 문자, 로그는 바이트 단위. 기본 0.
    offset?: number;
    request_id?: string;
    // 객체 결과의 최상위 키 또는 객체 배열의 행에서 남길 키.
    result_fields?: Array<string> | null;
  }): Promise<CallToolResult<{
    completed?: boolean;
    error_code?: string;
    message?: string;
    mutation_state?: string;
    next_step_guide?: string;
    request_id?: string;
    result?: unknown;
    result_display_error?: string | null;
    result_error?: string | null;
    result_page?: {
      available_fields?: Array<string>;
      // 배열·문자열 전체 결과는 result 키를 사용합니다.
      pages?: { [key: string]: {
        next_offset?: number | null;
        offset?: number;
        returned?: number;
        total?: number;
      }; };
      type?: string;
      unit?: string;
    };
    status?: string;
  }>>;
};
```

### 81. script\_04-save\_document

```txt
연결된 문서 전체를 기존 .3dm 경로에 저장합니다. 사용자에게 영구 저장을 요청받은 경우 사용합니다.
```

```ts
declare const tools: { mcp__rhino__script_04_save_document(args: {}): Promise<CallToolResult<{
  result: string;
}>>; };
```

## model

### 49. model\_01-assign\_material

대응 오리지널: `assign_material`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
Rhino 객체에 라이브러리 재료와 선택적인 구축 메타데이터를 적용합니다. 렌더 재료는 객체에 직접 지정되며 레이어는 바뀌지 않습니다. 중복 GUID는 하나로 처리합니다.

반환 result는 적용 결과 또는 오류를 담은 JSON 문자열입니다. 실제 렌더 재료와 사용자 문자열은 Rhino 객체 속성에서 확인할 수 있습니다. inspect_02의 user_dictionary는 이 사용자 문자열과 같은 항목이 아닙니다.
```

```ts
declare const tools: { mcp__rhino__model_01_assign_material(args: {
  // true이면 지정된 객체에 표준 렌더 재료를 적용합니다.
  apply_render_material?: boolean;
  // true이면 Almond 재료/구축 메타데이터를 부착합니다. false이면 요청한 렌더 재료만 적용합니다.
  attach_metadata?: boolean;
  // 선택 사항인 구축 상세 설명이며, attach_metadata와 함께 사용합니다.
  construction_detail?: string;
  // {"kind":"construction_system","id":"확인한 system_id"} 형식의 출처 참조입니다. attach_metadata=true일 때 사용합니다. construction_system도 지정하면 같은 시스템이어야 합니다.
  construction_reference?: {
    [key: string]: unknown;
  } | null;
  // 알려진 구축 시스템 ID입니다. attach_metadata=true일 때 사용합니다. construction_reference를 함께 지정하면 같은 시스템이어야 합니다.
  construction_system?: string;
  // 선택 사항인 층 레이블 메타데이터이며, attach_metadata와 함께 사용합니다.
  floor?: string;
  // 할당할 현재 Rhino 객체 GUID입니다. 관찰 결과나 생성 결과를 재사용합니다.
  guids: Array<string>;
  // model_04-list_materials tool(include_ids=true)에서 얻은 라이브러리의 표준 재료 ID입니다.
  material_id: string;
  // 선택 사항인 구조 역할 메타데이터이며, attach_metadata와 함께 사용합니다.
  structural_role?: string;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 50. model\_02-edit\_planar\_face

```txt
닫힌 Brep의 평면 한 면을 PushPull Extend로 이동합니다. 그룹·블록 편집을 종료한 일반 모델에서 사용합니다. 현재 객체의 면 번호와 geometry_crc를 같은 관찰에서 얻어 입력합니다.

result는 편집 결과 또는 오류를 담은 JSON 문자열입니다. 오류 응답에 mutation_state가 항상 포함되지는 않습니다.
```

```ts
declare const tools: { mcp__rhino__model_02_edit_planar_face(args: {
  // 해당 관찰 결과의 형상 CRC입니다. 형상이 변경되었으면 교체 전에 편집을 거부합니다.
  expected_geometry_crc: number;
  // 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
  expected_model_path?: string;
  // expected_geometry_crc와 동일한 형상 관찰 결과에서 얻은 0부터 시작하는 평면 인덱스입니다.
  face_index: number;
  // 연결된 문서의 관찰 결과에서 얻은 현재 잠기지 않은 최상위 닫힌 Brep GUID입니다.
  object_id: string;
  // 문서 단위의 유한한 XYZ 숫자 3개입니다. 면 법선 방향 성분이 문서 허용오차를 초과해야 합니다.
  translation: Array<number>;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 51. model\_03-edit\_planar\_faces

```txt
서로 다른 닫힌 Brep의 평면을 한 면씩 단일 Undo 기록으로 이동합니다. 그룹·블록 편집을 종료한 일반 모델에서 사용합니다. 각 객체의 면 번호와 CRC는 같은 형상 관찰에서 얻습니다.

result는 배치 결과 또는 오류를 담은 JSON 문자열입니다. 준비 단계에서 한 항목이 거부되면 객체 교체를 시작하지 않습니다. 처리 상태와 항목별 결과는 mutation_state와 items에서 확인합니다.
```

```ts
declare const tools: { mcp__rhino__model_03_edit_planar_faces(args: {
  // 서로 다른 Brep에 대한 항목 1..32개이며, 각 항목에는 object_id, face_index, expected_geometry_crc 및 translation이 들어갑니다. 단일 면 도구의 적용 대상 조건이 적용됩니다.
  edits: Array<{
    [key: string]: unknown;
  }>;
  // 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
  expected_model_path?: string;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 52. model\_04-list\_materials

대응 오리지널: `list_materials`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
라이브러리 재료를 이름·설명·태그 또는 분류로 찾습니다. 결과는 Rhino 문서에 이미 적용된 재료 목록이 아닙니다. 적용에 필요한 material_id는 include_ids=true로 조회합니다. result는 재료 목록 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: { mcp__rhino__model_04_list_materials(args: {
  // 분류 정확히 일치. 대소문자 구분; 생략 시 전체.
  category?: string;
  // 선택 사항인 상세 그룹: display, physical, metadata, source, paths, audit 또는 all. 생략하거나 비워 두면 요약을 조회합니다.
  field_groups?: Array<string> | null;
  // true이면 후속 호출에 사용할 ID를 포함합니다.
  include_ids?: boolean;
  // 이름·설명·태그 검색. 대소문자 구분 없음.
  query?: string;
}): Promise<CallToolResult<{
  result: string;
}>>; };
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
    overwrite: boolean;
  }): Promise<CallToolResult<{
    // JSON: status, applied, changes, differences, errors
    result: string;
  }>>;
};
```

## intersect

### 47. intersect\_01-find

```txt
닫힌 솔리드 사이에서 양의 부피가 겹치는 객체 쌍의 수를 찾습니다. include_block=false면 블록을 검사 범위에서 제외합니다. 0건은 선택된 검사 범위에서의 결과이며 전체 설계 적합성이나 간격을 보장하지 않습니다.

계산할 수 없는 객체·쌍이 있으면 intersection_count_incomplete 오류와 상세를 반환합니다. 접촉만 하는 면도 계산 불완전으로 반환될 수 있습니다. result는 결과 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: { mcp__rhino__intersect_01_find(args: {
  // true이면 변환이 적용된 중첩 블록 구성원까지 펼칩니다. 기본값 false는 범위에서 블록을 제외합니다.
  include_block?: boolean;
  // 서로 다른 현재 최상위 Rhino 객체 GUID 1..512개입니다. 내부 페이지 처리를 통해 하나의 범위로 검사합니다.
  object_ids: Array<string>;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 48. intersect\_02-resolve

```txt
겹친 객체 쌍을 이미지로 검토하고 선택한 객체에서 겹친 부분을 제거합니다. 검토 시 실제 카메라와 선택이 바뀝니다.

choice=1 또는 2는 해당 객체를 잘라내고 skip은 두 객체를 유지합니다. 완료 상태라도 건너뛴 쌍은 남습니다. 수정 후 다음 쌍을 계산하는 과정에서 오류가 나더라도 직전 수정이 적용됐을 수 있습니다. 응답의 previous_result와 실제 형상 상태를 확인합니다.
```

```ts
declare const tools: { mcp__rhino__intersect_02_resolve(args: {
  // 1 또는 2는 해당 번호의 객체에서 겹친 부분을 제거합니다. "skip"은 두 객체를 모두 그대로 둡니다. review_id를 제공하고 object_ids는 생략합니다. 확인/계속 진행하려면 choice를 생략합니다.
  choice?: number | "skip" | null;
  // 새 검토 범위에 변환이 적용된 중첩 블록 구성원을 포함합니다. 기본값은 false입니다. 블록 정의 편집은 여전히 지원하지 않습니다.
  include_block?: boolean;
  // 검토 범위를 시작할 서로 다른 현재 최상위 객체 GUID 1..512개입니다. 선택 사항이며, 현재 범위를 이어서 검토하거나 선택을 제출할 때는 생략합니다.
  object_ids?: Array<string> | null;
  // 반환된 결정 핸들로, choice와 함께 사용할 때 필수입니다. 화면에 표시된 연산 대상을 식별합니다. 완료되었거나 새 검토로 대체된 핸들로는 변경을 다시 실행할 수 없습니다.
  review_id?: string;
}): Promise<CallToolResult<{
  // 오류 유형입니다.
  error_code?: string;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // 건너뛴 쌍은 수정하지 않음. completed가 모든 겹침 제거를 뜻하지 않음
  skipped_pairs?: number;
  // 검토 진행 상태입니다. awaiting_choice이면 비교 결과를 확인한 뒤 선택합니다.
  state?: string;
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
}>>; };
```

## analysis

### 1. analysis\_01-check\_egress

대응 오리지널: `check_egress`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
코어와 출구를 배치한 뒤, 상세 설계 전에 층의 피난 조건을 예비 검토합니다. Rhino에서 형상이나 경로를 자동으로 읽지 않으므로 층 경계와 출구별 중심·유효 폭을 직접 확인해 입력하세요.

입력 경계의 직사각형으로 기본 바닥 면적과 출구 이격 기준의 대각선을 계산합니다. 실제 재실 면적이 다르면 별도로 입력하세요. 보행거리와 막다른 복도는 길이를 입력해야 검사합니다. 가장 불리한 보행 경로를 직접 측정하세요. 이 툴은 경로를 찾거나 입력한 경로가 최악인지 확인하지 않습니다.

출구 수와 총·최소 폭을 검사하고, 출구가 둘 이상이면 가장 먼 두 출구의 직선 이격을 검사합니다. 용도·스프링클러·담당 층수의 기본값이 실제 조건과 맞는지 확인하세요. 비업무 용도의 보행거리에는 업무용 기준을 대신 쓰며, 막다른 복도도 스프링클러가 있으면 업무용 기준을 사용하지만 용도 경고는 나오지 않습니다.

반환된 JSON의 checks에 포함된 검사의 기준값·입력값·판정을 확인하고 생략된 검사와 구분하세요. passed는 수행한 검사만의 결과입니다. 일부 출력값이 반올림돼 경계값에서는 표시값과 판정이 달라 보일 수 있습니다. 미달 항목의 배치·폭·경로를 검토하고 측정값을 갱신해 다시 검사하세요.

BCI 체계와 통상적인 IBC 수치를 사용합니다. source_note와 warnings를 읽고 프로젝트에 적용되는 법규와 대조하세요. 경고가 없거나 검사가 통과해도 모든 피난 조건의 적합성이 확인된 것은 아닙니다.
```

```ts
declare const tools: { mcp__rhino__analysis_01_check_egress(args: {
  // 가장 긴 막다른 복도 길이(m). 기본값 0이며, 0이면 검사 생략.
  dead_end_m?: number;
  // 출구마다 {"name": string, "x_mm": number, "y_mm": number, "width_mm": number}. 좌표는 문 중심(mm), 폭은 유효 피난 폭(mm).
  exits: Array<{
    [key: string]: unknown;
  }>;
  // 재실 면적(m²). 기본값 0이며, 0이면 경계 직사각형 면적 사용.
  net_area_m2?: number;
  // 용도: business, mercantile, assembly_unconcentrated, classroom, residential, storage. 기본값 business.
  occupancy?: string;
  // 층 바닥 경계 [min_x, min_y, max_x, max_y](mm).
  plate_bounds_mm: Array<number>;
  // 전체 스프링클러 설치 여부. 기본값 true.
  sprinklered?: boolean;
  // 출구가 담당하는 층수. 기본값 1. 1 초과면 최소 2개 출구와 계단 폭 계수(7.6mm/인) 적용.
  stories?: number;
  // 측정한 보행거리(m) 배열. 입력 중 최댓값을 검사하며, 기본값 []는 검사 생략.
  travel_distances_m?: Array<number>;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 2. analysis\_02-export\_structural\_report

대응 오리지널: `export_structural_report`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
저장된 구조 검증 이력을 Markdown 보고서로 작성합니다.
```

```ts
declare const tools: { mcp__rhino__analysis_02_export_structural_report(args: {
  // 포함할 최대 실행 개수입니다. 기본값은 50, 최댓값은 500입니다.
  limit?: number;
  // 관리형 세션에서는 선택한 Plan 산출물 디렉터리 아래의 상대 파일 경로이며, 기본값은 reports/structural-validation.md입니다. 독립 실행의 기본값은 사용자 데이터의 reports/structural-validation-<timestamp>.md입니다.
  path?: string;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 3. analysis\_03-list\_design\_codes

대응 오리지널: `list_design_codes`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
구조 해석에 사용할 설계기준 프로필을 조회합니다.
```

```ts
declare const tools: { mcp__rhino__analysis_03_list_design_codes(args: {
  // 상세 그룹: parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
  field_groups?: Array<string> | null;
  // true이면 후속 호출에 사용할 ID를 포함합니다.
  include_ids?: boolean;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 4. analysis\_04-validate\_structure

대응 오리지널: `validate_structure`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
Rhino 구조 형상을 해석하고 설계기준에 따라 검토합니다.
```

```ts
declare const tools: { mcp__rhino__analysis_04_validate_structure(args: {
  // true이면 배치된 라이브러리 자산의 자중·내용물·재실자 하중을 추가합니다. 네이티브 엔진에서 사용합니다. 다른 하중 입력에 이미 포함한 무게를 중복 적용하지 않습니다.
  asset_loads?: boolean;
  // "rigid"(기본값)는 모든 접합부가 모멘트를 전달합니다. "simple"은 보를 핀 접합(강축 휨 해제)으로, 가새를 양축 핀 접합으로 처리하되, 다른 부재가 같은 선상으로 계속 이어지는 지점이 아니라 해당 부재가 끝나는 지점에 적용하며 기둥은 연속으로 유지합니다. 일반적인 볼트 접합 강구조와 목구조 프레임은 "simple"에 더 가깝습니다. 강접합은 보 처짐을 실제보다 유리하게 보이게 할 수 있습니다. 곡선의 사용자 텍스트 almond:release = "pinned" | "pinned_start" | "pinned_end" | "rigid"는 두 모드보다 우선합니다. 네이티브 엔진에 적용됩니다.
  connections?: string;
  // "en1990"(기본값)은 SLS 특성 조합(G + Q)에서 처짐을, ULS 1.35 G + 1.5 Q에서 부재를 검토합니다. G는 자중, 바닥 구성층, 배치된 물품의 중량이고, Q는 load_kn, 용도별 바닥 활하중, 내용물, 재실자입니다. "unfactored"는 둘 다 G + Q에서 검토합니다(Karamba 경로의 기준). 네이티브 엔진에 적용됩니다.
  design_basis?: string;
  // 설계기준 또는 국가 부록에서 정하는 수치(gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, 처짐 한계)에 사용할 설계기준 프로필입니다. "eurocode"(기본값, EN 권장값), analysis_03-list_design_codes tool의 프로필 또는 "off"를 사용합니다. "off"는 부분계수 없이 G + Q를 적용하며 design_basis="unfactored"와 같습니다. 결과의 "design_code"에는 사용한 값과 검증되지 않은 값이 포함됩니다.
  design_code?: string;
  // true이면 네이티브 해석의 부재별 단면력·사용률·처짐과 지점 반력을 포함합니다.
  detail?: boolean;
  // auto, native, karamba 중 선택합니다. auto는 선형 프레임에 native를, 그 외에는 Karamba를 사용합니다. karamba는 사용 가능한 api, template, rule_based 순으로 시도합니다. 결과의 analysis_method와 warnings를 확인합니다.
  engine?: string;
  // 중공 강재 단면(CHS/RHS)은 "cold_formed"(기본값, EN 10219, 좌굴 곡선 c) 또는 "hot_finished"(EN 10210, 곡선 a, S460은 a0)입니다. 좌굴 내력에 최대 약 23% 차이가 있으므로, hot_finished는 명시된 경우에만 사용합니다.
  fabrication?: string;
  // True는 완전 고정 지점, False는 핀 지점(회전 자유)을 뜻합니다.
  fixed_supports?: boolean;
  // 같은 구획에 적용할 추가 고정하중(kN/m2)입니다. 바닥 구성층과 마감 등을 포함합니다.
  floor_dead_kn_m2?: number;
  // 한 층에서 보로 둘러싸인 모든 구획에 적용할 부과 바닥 하중(kN/m2)입니다(예: 주거용 2.0, EN 1991-1-1의 category A). 보는 45도 분배 규칙에 따라 하중을 받습니다(2방향, 장단변비 2:1 초과 시 1방향). 네이티브 엔진 전용입니다. 설계기준의 바닥 하중에는 이동 가능한 가구와 사람이 이미 포함되므로, asset_loads는 무거운 특정 물품에 대해서만 함께 사용하고 중복 계산을 피하려면 load_kn을 0으로 설정합니다.
  floor_load_kn_m2?: number;
  // 해석 범위에 포함되는 현재 Rhino 객체 GUID 문자열입니다.
  guids: Array<string>;
  // 전체 부과하중(kN)입니다. native에서는 자유 절점에 하향(-Z) 균등 분배합니다. 바닥·자산 하중과 중복 계산되지 않게 산정하며 필요한 경우 0으로 입력합니다.
  load_kn?: number;
  // 재료 유형: "Steel", "S355", "Concrete", "Wood", "Aluminium". 기본값은 "Steel"입니다.
  material?: string;
  // 부재 자중을 포함합니다.
  self_weight?: boolean;
  // 부재가 모든 절점에서 분할됐을 때 L/250 한계에 사용할 구조 경간(미터)입니다. 예를 들어 6.2 m 장선을 3.1 m 구간 두 개로 그린 경우에 사용합니다. 네이티브 엔진 전용입니다.
  span_m?: number | null;
  // "auto"(기본값)는 모든 ULS 조합의 탄성 임계 하중 계수 alpha_cr(EN 1993-1-1 5.2.1)과 +/-x 및 +/-y 방향의 횡변위 초기 불완전성 phi = 1/200 x alpha_h x alpha_m(5.3.2)을 적용합니다. alpha_cr < 10이면 2차(P-Delta) ULS 해석을 실행하며, alpha_cr <= 1이면 불안정으로 실패 처리합니다. "off"는 초기 불완전성 없는 1차 해석입니다.
  stability?: string;
  // 사용할 해석 템플릿입니다. 선택지: "beam"은 단순 보의 휨/처짐, "truss"는 축력/좌굴 해석, "shell"은 셸 응력/변위, "frame"은 프레임 모멘트/전단 해석, "canopy"는 캔틸레버 캐노피, "gridshell"은 대변형 그리드셸, "membrane"은 막 구조 형상 탐색, "highrise"는 고층 구조 시스템입니다.
  structure_type?: string;
  // "6.10" 또는 "6.10ab"입니다. "6.10ab"는 부재별로 6.10a와 6.10b 중 더 불리한 결과를 사용합니다. 기본값은 설계기준이 선택한 식입니다(Eurocode 프로필: 6.10). 특정 식을 지정한 프로필은 요청보다 우선하며 경고를 반환합니다.
  uls_combination?: string | null;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 5. analysis\_05-visualize\_structure

대응 오리지널: `visualize_structure`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
구조 해석 결과를 임시 뷰포트 오버레이로 표시합니다.
```

```ts
declare const tools: { mcp__rhino__analysis_05_visualize_structure(args: {
  // analysis_04-validate_structure tool와 동일하게 배치된 라이브러리 자산의 하중을 추가합니다(네이티브 엔진). 하중 작용점에 하중 화살표를 그립니다.
  asset_loads?: boolean;
  // 선택 항목인 원형 부재 외경(밀리미터)입니다.
  beam_diameter_mm?: number | null;
  // 선택 항목인 중공 부재의 벽 두께(밀리미터)입니다.
  beam_wall_mm?: number | null;
  // 오버레이를 제거합니다.
  clear?: boolean;
  // "displacement" 또는 "utilization"입니다.
  color_by?: string;
  // analysis_04-validate_structure tool와 동일한 "rigid" 또는 "simple"입니다. 핀 접합 단부는 작은 원으로 그립니다.
  connections?: string;
  // 경간/비율 한계입니다. 예를 들어 L/250은 250입니다. 기본값은 설계기준의 한계입니다(Eurocode 프로필: 250).
  deflection_limit_ratio?: number | null;
  // "en1990"(기본값)은 SLS 특성 조합(G + Q)에서 처짐을, ULS 1.35 G + 1.5 Q에서 부재를 검토합니다. G는 자중, 바닥 구성층, 배치된 물품의 중량이고, Q는 load_kn, 용도별 바닥 활하중, 내용물, 재실자입니다. "unfactored"는 둘 다 G + Q에서 검토합니다(Karamba 경로의 기준). 네이티브 엔진에 적용됩니다.
  design_basis?: string;
  // 설계기준 또는 국가 부록에서 정하는 수치(gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, 처짐 한계)에 사용할 설계기준 프로필입니다. "eurocode"(기본값, EN 권장값), analysis_03-list_design_codes tool의 프로필 또는 "off"를 사용합니다. "off"는 부분계수 없이 G + Q를 적용하며 design_basis="unfactored"와 같습니다. 결과의 "design_code"에는 사용한 값과 검증되지 않은 값이 포함됩니다.
  design_code?: string;
  // 이 부재들만 그립니다(예: 단면 보기를 위한 한 줄의 프레임). 해석은 여전히 guids의 모든 부재를 포함합니다.
  display_guids?: Array<string> | null;
  // "auto"(기본값), "native", "karamba" 중 하나입니다. "auto"는 Karamba 없이 Almond 네이티브 프레임 솔버를 사용하되, 선택에 셸이 있거나 브리지가 모델을 내보낼 수 없으면 Karamba를 사용합니다.
  engine?: string;
  // 중공 강재 단면(CHS/RHS)은 "cold_formed"(기본값, EN 10219, 좌굴 곡선 c) 또는 "hot_finished"(EN 10210, 곡선 a, S460은 a0)입니다. 좌굴 내력에 최대 약 23% 차이가 있으므로, hot_finished는 명시된 경우에만 사용합니다.
  fabrication?: string;
  // True는 완전 고정 지점, False는 핀 지점(회전 자유)을 뜻합니다.
  fixed_supports?: boolean;
  // 같은 구획에 적용할 추가 고정하중(kN/m2)입니다. 바닥 구성층과 마감 등을 포함합니다.
  floor_dead_kn_m2?: number;
  // 한 층에서 보로 둘러싸인 모든 구획에 적용할 부과 바닥 하중(kN/m2)입니다(예: 주거용 2.0, EN 1991-1-1의 category A). 보는 45도 분배 규칙에 따라 하중을 받습니다(2방향, 장단변비 2:1 초과 시 1방향). 네이티브 엔진 전용입니다. 설계기준의 바닥 하중에는 이동 가능한 가구와 사람이 이미 포함되므로, asset_loads는 무거운 특정 물품에 대해서만 함께 사용하고 중복 계산을 피하려면 load_kn을 0으로 설정합니다.
  floor_load_kn_m2?: number;
  // 구조 축선의 곡선 GUID와 지점을 표시하는 점 GUID입니다(fixed_supports 참조). 점이 없으면 최하단 절점을 지점으로 사용합니다.
  guids?: Array<string> | null;
  // 자유 절점에 하향(-Z)으로 균등 분배할 전체 부과하중(kN)입니다.
  load_kn?: number;
  // "Steel", "S355", "Concrete", "Wood", "Aluminium" 중 하나입니다.
  material?: string;
  // False이면 해석 오버레이 없이 같은 부재를 일반 형상으로 그립니다("physics off"). 전후 비교에 사용합니다.
  physics?: boolean;
  // False이면 마지막 계산을 재사용하고 표시(scale / color_by / reveal / physics / title)만 변경합니다. 애니메이션에 사용할 수 있을 만큼 계산 부담이 작습니다.
  reanalyze?: boolean;
  // 그릴 부재의 비율이며 0..1 범위입니다. 단계별 시공 재생에 사용합니다.
  reveal?: number;
  // 변형 과장 배율입니다. 생략하면 자동으로 정합니다(경간의 약 6%).
  scale?: number | null;
  // 중력을 포함합니다.
  self_weight?: boolean;
  // 한계에 사용할 기준 경간(미터)입니다. 기본값은 가장 긴 부재입니다. 부재가 모든 절점에서 분할됐다면 지정합니다. 예: 6.2 m 장선을 3.1 m 구간 두 개로 그린 경우.
  span_m?: number | null;
  // analysis_04-validate_structure tool와 동일한 "auto" 또는 "off"입니다.
  stability?: string;
  // 범례 제목입니다.
  title?: string;
  // "6.10" 또는 "6.10ab"입니다. "6.10ab"는 부재별로 6.10a와 6.10b 중 더 불리한 결과를 사용합니다. 기본값은 설계기준이 선택한 식입니다(Eurocode 프로필: 6.10). 특정 식을 지정한 프로필은 요청보다 우선하며 경고를 반환합니다.
  uls_combination?: string | null;
  // "deflection"(기본값) 또는 "buckling"입니다. "buckling"은 처짐 형상 대신 지배 ULS 조합의 첫 번째 좌굴 모드를 alpha_cr과 함께 그립니다(STABLE >= 10, SWAY-SENSITIVE 1-10, UNSTABLE <= 1).
  view?: string;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

## research

### 62. research\_01-get\_construction\_guidance

대응 오리지널: `get_construction_guidance`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
건축 구법을 비교하고 선택할 참고 자료를 조회합니다.
```

```ts
declare const tools: { mcp__rhino__research_01_get_construction_guidance(args: {
  // "floor", "wall", "roof", "foundation" 중 하나입니다. 비워 두면 모두 포함합니다.
  category?: string;
  // 상세 그룹: rules, narrative, source, metadata, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
  field_groups?: Array<string> | null;
  // true이면 후속 호출에 사용할 ID를 포함합니다.
  include_ids?: boolean;
  // load_kn 입력을 정하는 데 사용할 용도별 활하중(kPa)과 재료 밀도(kg/m3)도 반환합니다.
  include_reference_data?: boolean;
  // analysis_04-validate_structure tool에서 사용하는 이름: "Wood", "Steel", "Concrete".
  material?: string;
  // 자유 텍스트 필터입니다(예: "glulam", "longspan", "bearing wall").
  query?: string;
  // 0보다 크면 반환되는 각 시스템이 fits_span과 경간 비율 규칙에 따른 권장 부재 깊이를 보고합니다.
  span_m?: number;
  // analysis_04-validate_structure tool의 유형입니다("beam", "truss", "shell", "frame", "canopy", "gridshell", "membrane", "highrise").
  structure_type?: string;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 63. research\_02-get\_typology\_narrative

대응 오리지널: `get_typology_narrative`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
건축 유형의 서사와 선례를 조회합니다.
```

```ts
declare const tools: { mcp__rhino__research_02_get_typology_narrative(args: {
  // 구법 라이브러리의 system_id와 관련된 항목으로 필터링합니다(예: "steel-column-frame").
  construction_system?: string;
  // 상세 그룹: rules, narrative, source, metadata, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
  field_groups?: Array<string> | null;
  // true이면 후속 호출에 사용할 ID를 포함합니다.
  include_ids?: boolean;
  // 반환할 최대 항목 수입니다. 기본값은 5입니다.
  limit?: number;
  // 자유 텍스트입니다(예: "courtyard", "skyscraper", "timber hall").
  query?: string;
  // analysis_04-validate_structure tool의 유형으로 필터링합니다("shell", "truss", "frame", "membrane" 등).
  structure_type?: string;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 64. research\_03-search\_details

대응 오리지널: `search_detail_sources`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
건축 자료 디렉터리의 metadata를 검색합니다.
```

```ts
declare const tools: { mcp__rhino__research_03_search_details(args: {
  // 상세 그룹: rules, narrative, source, metadata, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
  field_groups?: Array<string> | null;
  // true이면 후속 호출에 사용할 ID를 포함합니다.
  include_ids?: boolean;
  // 자유 텍스트 검색어입니다. 비워 두면 텍스트 필터를 적용하지 않습니다.
  query?: string;
}): Promise<CallToolResult<{
  // 오류 유형입니다.
  error_code?: string;
  // 검색에 추가한 관련 단어입니다.
  expanded_terms?: Array<unknown>;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // 검색어입니다.
  query?: string;
  // 원래 검색어에서 추출한 단어입니다.
  query_terms?: Array<string>;
  // 검색한 출처 디렉터리의 범위입니다.
  scope?: string;
  // 조건에 일치하는 상세 자료 출처입니다.
  sources?: Array<{
    // 자료 접근 조건입니다.
    access?: string;
    // 제공하는 자료 형식입니다.
    formats?: Array<string>;
    // 생성 작업에서의 이용 조건입니다.
    generation_use?: string;
    // 일치한 검색 단어입니다.
    matched_terms?: Array<string>;
    // 자료 재배포 조건입니다.
    redistribution?: string;
    // 출처 ID입니다.
    source_id?: string;
    // 자료 이용 조건의 웹 주소입니다.
    terms_url?: string;
    // 제목입니다.
    title?: string;
    // 자료 출처의 웹 주소입니다.
    url?: string;
  }>;
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
}>>; };
```

## asset

### 6. asset\_01-audit\_drawing

대응 오리지널: `audit_asset_drawing`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
저장 도면 패키지의 manifest에 기록된 파일 해시와 원본을 비교합니다. 검사 성공은 도면 내용의 적합성이나 manifest의 완전성을 보장하지 않으며, 목록이 비어 있으면 검사 파일 0개로도 성공할 수 있습니다. 원본을 찾지 못하면 파일만 검사하고 원본 비교는 생략합니다.
```

```ts
declare const tools: { mcp__rhino__asset_01_audit_drawing(args: {
  // 생성/조회 결과의 package_dir를 그대로 입력합니다. 관리형 세션은 프로젝트 안의 패키지와 설정된 도면 라이브러리·drawing-runs의 패키지를 검사합니다. 독립 실행에서는 절대 경로가 필요합니다.
  package_dir: string;
  // 원본 변경으로 오래된 상태가 되었는지 확인할 현재 원본 GLB입니다. 선택 사항이며, 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. 라이브러리에서 원본을 확인할 수 있으면 생략합니다.
  source_glb?: string;
}): Promise<CallToolResult<{
  // 패키지 원본 ID. custom-*는 등록 자산 ID가 아님
  asset_id?: string;
  // manifest에 기록된 검사 대상 수. 0일 수 있음.
  checked_files?: number;
  // 오류 유형입니다.
  error_code?: string;
  // 실패 항목이 하나라도 있으면 status=error
  failures?: Array<unknown>;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // GLB 형상 해시 일치: current; 3DM 파일 해시 일치: source_file_current; 불일치: stale; 비교 미실시: not_checked.
  source_geometry?: string;
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
}>>; };
```

### 7. asset\_02-generate\_drawing\_views

대응 오리지널: `generate_asset_drawing_views`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
등록 3DM 또는 사용자 지정 GLB의 메쉬를 평면·정면·우측면 실루엣으로 투영합니다. 실물 크기 mm DXF와 축척 SVG를 생성하며, 세 뷰가 A3 시트 영역에 들어가면 시트 SVG도 생성합니다. 시트가 생략되어도 성공할 수 있습니다.

실루엣에는 단면과 내부 가시선·은선이 없으며 정면은 좌표계 기준입니다. 축척에 따른 단순화나 근사로 작은 형상의 윤곽이 달라질 수 있습니다. 결과는 별도 drawing-runs 패키지에 저장되며 등록 자산의 도면을 갱신하지 않습니다.
```

```ts
declare const tools: { mcp__rhino__asset_02_generate_drawing_views(args: {
  // 등록 3DM 자산 ID. source_glb와 택일.
  asset_id?: string;
  // GLB 원본 단위 mm 또는 m. source_glb에 필수.
  input_units?: string;
  // 축척 분모 1~4개, 중복 없는 정수 5~1000. 기본 [50, 100].
  scales?: Array<number> | null;
  // 정적·비압축 삼각형 GLB, 최대 100 MB·250,000 삼각형.
  // 관리형: 프로젝트 상대 경로 / 독립 실행: 절대 경로.
  source_glb?: string;
  // 이 도면에 첨부하는 출처. 원본 모델 생성 이력의 증빙은 아님.
  // 필수: source_id, title, url, publisher, locator, accessed_on, relationship, used_for, terms_url.
  // relationship: background_reading, dimensional_reference, assembly_reference, post_generation_reference.
  source_references?: Array<{
    [key: string]: unknown;
  }> | null;
  // GLB 위쪽 축 y 또는 z. 기본 y: (X,-Z,Y)로 변환. 등록 3DM에는 미적용.
  up_axis?: string;
}): Promise<CallToolResult<{
  // 오류 유형입니다.
  error_code?: string;
  // 원본·축척·투영 방식·파일 목록. 시트 생략 사유: source.sheet_warnings.
  manifest?: {
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // asset_01-audit_drawing tool의 package_dir에 그대로 전달할 경로입니다. 관리 연결에서는 프로젝트 상대 경로이며, 다른 드라이브의 라이브러리는 절대 경로를 유지합니다.
  package_dir?: string;
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
}>>; };
```

### 8. asset\_03-get\_drawings

대응 오리지널: `get_asset_drawing`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
등록 자산의 저장 도면 패키지를 조회합니다. manifest에서 도면 파일·축척·치수·출처와 투영 한계를 확인할 수 있습니다. 도면은 자산의 원본 형상을 투영한 것으로 배치 인스턴스의 변환이 적용된 결과는 아닙니다.
```

```ts
declare const tools: { mcp__rhino__asset_03_get_drawings(args: {
  // include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다.
  asset_id: string;
  // 선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다.
  field_groups?: Array<string> | null;
  // true이면 후속 호출에 사용할 ID를 포함합니다.
  include_ids?: boolean;
}): Promise<CallToolResult<{
  // 오류 유형입니다.
  error_code?: string;
  // 도면 패키지의 원본·파일·축척 기록입니다.
  manifest?: {
    [key: string]: unknown;
  };
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // paths 또는 all 조회에서 반환. asset_01-audit_drawing tool의 입력에 사용.
  package_dir?: string;
  // 저장된 평면 SVG를 읽는 리소스 URI입니다.
  plan_svg_uri?: string;
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
}>>; };
```

### 9. asset\_04-get

대응 오리지널: `get_drawing_asset`, `get_generated_asset_passport`, `get_generated_asset`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
모델·2D 자산의 등록 정보와 사용 가능 상태를 조회합니다. paths로 원본·모델 경로를 확인할 수 있습니다. result는 자산 정보 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: { mcp__rhino__asset_04_get(args: {
  // include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다.
  asset_id: string;
  // 선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다.
  field_groups?: Array<string> | null;
  // ID 포함 옵션. 조회한 asset_id는 응답에 반복되지 않을 수 있습니다.
  include_ids?: boolean;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 10. asset\_05-list

대응 오리지널: `list_drawing_assets`, `list_generated_assets`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
모델·2D 자산 목록과 사용 준비 상태를 조회합니다. 원본만 있는 자산은 바로 배치할 3DM이 아닐 수 있습니다. 상세 조회에 필요한 ID는 include_ids=true로 포함합니다.

페이지 결과에 next_offset은 없으며, truncated=true면 같은 필터로 offset에 반환된 자산 수를 더해 이어 읽습니다. result는 목록 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: { mcp__rhino__asset_05_list(args: {
  // 라이브러리 분류 필터입니다. 선택 사항이며, 비어 있으면 모든 분류를 포함합니다.
  category?: string;
  // 선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다.
  field_groups?: Array<string> | null;
  // true이면 후속 호출에 사용할 ID를 포함합니다.
  include_ids?: boolean;
  // 한 페이지에 반환할 최대 항목 수입니다.
  limit?: number;
  // 이 페이지의 시작 행을 0부터 세는 값입니다. 다음 페이지를 요청할 때도 같은 필터를 사용합니다.
  offset?: number;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 11. asset\_06-place

대응 오리지널: `place_drawing_asset`, `place_generated_asset`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
모델·2D 자산을 Rhino 문서에 블록으로 배치합니다. 3DM은 원본에 연결된 블록이며 같은 정의를 사용하는 배치에 정의 갱신이 반영됩니다. 결과는 성공 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: { mcp__rhino__asset_06_place(args: {
  // include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다.
  asset_id: string;
  // 월드 Z축 기준 회전각(도). 기본 0.
  rotation_degrees?: number;
  // 균일 배치 축척. 기본 1, 0 초과 100 이하.
  scale?: number;
  // 원본 기준점의 월드 X 좌표. 문서 단위, 기본 0.
  x?: number;
  // 원본 기준점의 월드 Y 좌표. 문서 단위, 기본 0.
  y?: number;
  // 원본 기준점의 월드 Z 좌표. 문서 단위, 기본 0.
  z?: number;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 12. asset\_07-prepare

```txt
원본 사본을 검사·편집·시각 검토해 등록용 3DM을 준비합니다. inspect로 job을 만들고, 필요하면 normalize로 수정한 뒤 verify합니다. 수정이 필요 없으면 normalize를 건너뛰고 verify할 수 있습니다.

첫 verify는 최종 미리보기와 해시를 생성합니다. 이를 검토한 뒤 같은 해시·이름·ID를 넣어 다시 verify하면 등록 준비 상태가 됩니다. ready_for_registration은 호출자의 해시 연계 검토 확인이며 형상 적합성을 자동 판정했다는 뜻은 아닙니다. 관리형 source_file은 프로젝트 내부 경로여야 합니다.
```

```ts
declare const tools: { mcp__rhino__asset_07_prepare(args: {
  // 선택 가능한 값은 summary, parts, previews, provenance 또는 all입니다. 생략하면 미리 보기 경로를 포함하고, []이면 간략한 결과를 유지합니다. 페이지 처리는 parts에 적용됩니다.
  field_groups?: Array<string> | null;
  // true이면 후속 호출에 사용할 ID를 포함합니다.
  include_ids?: boolean;
  // OBJ/STL/PLY/OFF/GLB/glTF의 명시적 원본 단위로 mm, cm, m, in 또는 ft를 지정합니다. 측정한 원본 단위를 사용합니다. 이후 단계에서는 생략하며, 3DM은 내장된 단위를 보존합니다.
  input_units?: string;
  // 이전에 반환된 준비 작업의 job_dir입니다. 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. normalize, verify, status에 필수입니다.
  job_dir?: string;
  // 부품 목록의 페이지 크기이며, 범위는 1..200입니다.
  limit?: number;
  // 이 페이지의 시작 행을 0부터 세는 값입니다. 다음 페이지를 요청할 때도 같은 필터를 사용합니다.
  offset?: number;
  // 검토 결과 객체입니다. normalize: {vision_reviewed:true, inspected_sha256:"확인한 해시", rotation_degrees_xyz:[x,y,z], translation:[x,y,z], remove:[{object_id:"ID",reason:"사유"}]}. 생략한 변환은 유지하며 translation은 원본 단위입니다. 최종 이미지를 본 뒤 verify: {vision_reviewed:true, final_sha256:"확인한 해시", name:"이름", asset_id:"ID"}. 첫 verify로 최종 이미지를 만든 후 검토 확인을 제출합니다.
  review?: {
    [key: string]: unknown;
  } | null;
  // inspect에 사용할 원본 모델입니다. 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. 원본 바이트는 변경하지 않고 유지합니다.
  source_file?: string;
  // inspect, normalize, verify 또는 status입니다. inspect는 작업을 생성하고, 이후 단계는 job_dir를 재사용합니다. status는 저장된 근거만 다시 읽습니다. 네이티브 작업을 실행하거나, 나중에 완료되었다는 이유로 확인되지 않은 작업의 단계를 올리지 않습니다.
  stage: string;
}): Promise<CallToolResult<{
  // 오류 유형입니다.
  error_code?: string;
  // 이후 단계 및 등록의 preparation_job에 재사용. status는 저장 근거만 읽고 늦은 실행을 자동 정합화하지 않음
  job_dir?: string;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 현재 상태의 다음 단계. 오류에서 자동 진행을 유도하지 않음
  next_stage?: string | null;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // 현재 파일 해시에 대한 이미지 검토를 호출자가 확인했는지 나타냅니다.
  ready_for_registration?: boolean;
  // 저장된 검토 증거에 대한 설명입니다.
  review_evidence?: string;
  // 검토 완료 최종 파일. asset_09-register tool에 검토한 name/asset_id와 함께 전달
  source_3dm?: string;
  // ready일 때만 source_3dm 제공. running/unconfirmed/failed는 error와 next_stage=null
  state?: string;
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
}>>; };
```

### 13. asset\_08-refresh

```txt
편집·저장된 등록 3DM을 다시 측정하고 평면·입면 도면을 새 리비전으로 발행합니다. 원본 경로와 이전 도면은 유지됩니다. 도면은 메쉬 투영 실루엣으로 내부 가시선·은선이나 구성 레이어를 표현하지 않습니다.

열린 Rhino 문서의 연결 블록을 갱신하거나 저장하지 않습니다. 공유 블록 정의를 별도로 갱신하면 기존 인스턴스에도 반영되지만, 배치 당시 메타데이터는 자동 갱신되지 않습니다.
```

```ts
declare const tools: { mcp__rhino__asset_08_refresh(args: {
  // 등록 3DM 모델 자산 ID.
  asset_id: string;
}): Promise<CallToolResult<{
  // 갱신한 자산의 정보입니다.
  asset?: {
    [key: string]: unknown;
  };
  // 오류 유형입니다.
  error_code?: string;
  // false인데 게시가 적용됐다면 재연결하여 인덱스 갱신
  live_index_refreshed?: boolean;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 갱신한 라이브러리 3DM 경로입니다.
  model_path?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // 갱신한 도면 패키지 폴더입니다.
  package_dir?: string;
  // 이전 도면·매니페스트 백업·원본 리비전 사본 보존
  previous_files_retained?: boolean;
  // true면 인덱스 갱신 실패여도 게시 적용. 무작정 반복하지 않음
  registration_applied?: boolean;
  // false: 기존 Rhino 연결 인스턴스 재로드는 별도
  rhino_linked_instances_updated?: boolean;
  // 기존 원본 경로를 보존했는지 여부
  source_path_preserved?: boolean;
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
}>>; };
```

### 14. asset\_09-register

```txt
준비한 3DM을 모델 라이브러리에 등록하고 치수와 평면·입면 도면 패키지를 생성합니다. 생성 도면은 투영 실루엣으로 내부 가시선·숨은선이나 구성 레이어를 표현하지 않습니다.

파생 메시가 250,000 삼각형을 넘으면 등록에 실패합니다. asset_07-prepare tool의 준비 완료는 등록 성공을 보장하지 않습니다. 등록 후 asset_04-get tool로 자산 상태를 확인할 수 있습니다.
```

```ts
declare const tools: { mcp__rhino__asset_09_register(args: {
  // 자산 ID. preparation_job 사용 시 검토한 ID와 일치.
  asset_id: string;
  // 새 자산의 라이브러리 분류입니다.
  category?: string;
  // 선택 사항인 자산 설명입니다.
  description?: string;
  // preparation_job 사용 시 검토한 이름과 일치.
  name: string;
  // 완료된 준비 작업의 job_dir입니다. 선택 사항이며, 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. 검토를 거치는 다중 형식 변환 절차에는 필수입니다.
  preparation_job?: string;
  // true이면 이 ID를 가진 기존 자산을 명시적으로 교체합니다. false이면 교체를 거부합니다.
  replace_existing?: boolean;
  // 검토한 3DM 원본입니다. 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. preparation_job을 사용할 때는 해당 작업 응답의 source_3dm을 사용합니다.
  source_3dm: string;
  // 출처 이력으로 보존할 원래 원본 URL입니다. 선택 사항입니다.
  source_url?: string;
  // 선택 사항인 설명용 검색 태그입니다.
  tags?: Array<string> | null;
}): Promise<CallToolResult<{
  // 등록한 자산의 정보입니다.
  asset?: {
    [key: string]: unknown;
  };
  // 오류 유형입니다.
  error_code?: string;
  // 라이브러리 폴더
  library_dir?: string;
  // 교체로 기존 연결 인스턴스에 영향 가능
  linked_instances_may_update?: boolean;
  // 게시 true·인덱스 false이면 등록을 반복하지 말고 재연결
  live_index_refreshed?: boolean;
  // 라이브러리 manifest.json 경로입니다.
  manifest_path?: string;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 저장된 모델의 경로
  model_path?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  // 생성한 도면 패키지 폴더입니다. DXF와 치수는 mm 단위입니다.
  package_dir?: string;
  // 교체 전 원본·도면·매니페스트 백업 보존
  previous_files_retained?: boolean;
  // 기존 원본 해시. 없으면 null
  previous_source_sha256?: string | null;
  // true면 게시 적용. 불명확한 오류는 null과 requires_reconciliation; 단순 재시도 금지
  registration_applied?: boolean | null;
  // 기존 원본 경로를 보존했는지 여부
  source_path_preserved?: boolean;
  // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  status?: string;
}>>; };
```

### 15. asset\_10-search\_repository

대응 오리지널: `search_asset_repository`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
모델·2D 요소 아카이브를 검색하고 후보의 사용 가능 상태를 확인합니다. 결과는 전체 매치 수와 limit개까지의 후보이며 이어지는 페이지는 없습니다. 잘린 경우 검색어나 유형으로 범위를 좁힐 수 있습니다.

원본만 있는 자산은 즉시 배치 가능한 상태가 아닐 수 있습니다. 상세 정보와 경로는 후보 ID로 asset_04-get tool에서 조회합니다.
```

```ts
declare const tools: { mcp__rhino__asset_10_search_repository(args: {
  // true이면 도면 데이터가 준비된 자산으로 제한합니다.
  drawing_ready?: boolean;
  // dimensions, source, paths, drawing, metadata, audit 또는 all. 검색 결과에 있는 필드만 표시.
  field_groups?: Array<string> | null;
  // true이면 후속 호출에 사용할 ID를 포함합니다.
  include_ids?: boolean;
  // all(기본), element 또는 model.
  kind?: string;
  // 반환 개수: 기본 20, 1..100으로 보정.
  limit?: number;
  // 이름·ID·분류·variant·재료 ID·태그·역할 검색. 대소문자 무시, 공백으로 구분한 모든 단어 포함.
  query?: string;
}): Promise<CallToolResult<{
  // 검색된 자산과 준비 상태입니다. id를 후속 도구의 asset_id로 사용합니다.
  assets?: Array<{
    [key: string]: unknown;
  }>;
  // 오류 유형입니다.
  error_code?: string;
  // 현재 결과 또는 오류의 설명입니다.
  message?: string;
  // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  next_step_guide?: string;
  total?: number;
}>>; };
```

### 16. asset\_11-search

대응 오리지널: `search_drawing_assets`, `search_generated_assets`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
모델·2D 자산을 검색어, 분류와 최대 치수로 검색합니다. 여러 검색어 중 하나 이상 일치하면 포함하고, 일치 단어가 많은 순으로 표시합니다. 결과에는 파일·모델·도면 상태와 페이지 정보가 포함됩니다.

최대 치수 필터는 등록 치수를 비교하며, 해당 치수가 없는 자산도 포함될 수 있습니다. 상세 정보는 include_ids=true로 얻은 ID를 asset_04-get tool에 전달합니다. result는 검색 결과 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: { mcp__rhino__asset_11_search(args: {
  // 분류의 정확한 값. 대소문자 무시, 빈 값은 전체.
  category?: string;
  // 선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다.
  field_groups?: Array<string> | null;
  // true이면 후속 호출에 사용할 ID를 포함합니다.
  include_ids?: boolean;
  // 페이지 크기: 기본 10, 1..100.
  limit?: number;
  // 깊이 상한(mm). 양수일 때 적용.
  max_depth_mm?: number;
  // 높이 상한(mm). 양수일 때 적용.
  max_height_mm?: number;
  // 너비 상한(mm). 양수일 때 적용.
  max_width_mm?: number;
  // 0부터 시작. truncated=true면 같은 조건의 offset에 반환 건수를 더해 이어 조회.
  offset?: number;
  // 이름·설명·제품·분류·태그 등 부분 일치. 대소문자 무시.
  query?: string;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

## diagram

### 23. diagram\_01-get

대응 오리지널: `get_diagram_asset`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
다이어그램 자산 하나의 등록 정보와 파일 존재 상태를 조회합니다. 목록이나 검색에서 얻은 ID로 조회하며, 파일이 없는 등록 항목도 조회됩니다.
```

```ts
declare const tools: { mcp__rhino__diagram_01_get(args: {
  // 목록·검색에서 얻은 자산 ID. 대소문자·공백까지 정확히 지정.
  asset_id: string;
  // dimensions, drawing, metadata, source, paths, audit, all. 생략·빈 배열: 요약. all: 다른 그룹 외 등록 필드도 포함.
  field_groups?: Array<string> | null;
  // true: 다른 식별자 포함. 입력 asset_id는 응답에 반복되지 않음.
  include_ids?: boolean;
}): Promise<CallToolResult<{
  // 상태와 asset 또는 오류를 담은 JSON 문자열. asset.file_available: 등록 파일 존재 여부.
  result: string;
}>>; };
```

### 24. diagram\_02-list

대응 오리지널: `list_diagram_assets`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
사람·나무·기호 등 2D 벡터·CAD 다이어그램의 등록 목록을 조회합니다. 목록에 파일이 없는 항목도 포함되며, 자산 ID로 diagram_01-get tool에서 세부 정보와 사용 가능 상태를 확인할 수 있습니다. 키워드·치수 검색은 diagram_04-search tool을 사용합니다.
```

```ts
declare const tools: { mcp__rhino__diagram_02_list(args: {
  // 분류값 전체 일치, 대소문자 무시. 빈 값: 전체.
  category?: string;
  // 선택 가능한 세부 그룹은 dimensions, drawing, metadata, source, paths, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다.
  field_groups?: Array<string> | null;
  // true이면 후속 호출에 사용할 ID를 포함합니다.
  include_ids?: boolean;
  // 기본 20, 1..50으로 보정.
  limit?: number;
  // 0부터 시작. 음수는 0으로 보정.
  offset?: number;
}): Promise<CallToolResult<{
  // 목록·페이지 정보(next_offset 포함) 또는 오류를 담은 JSON 문자열.
  result: string;
}>>; };
```

### 25. diagram\_03-place

대응 오리지널: `place_diagram_asset`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
SVG·DWG·DXF 다이어그램을 Rhino 문서의 블록 인스턴스로 배치합니다.
```

```ts
declare const tools: { mcp__rhino__diagram_03_place(args: {
  // include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다.
  asset_id: string;
  // 월드 Z축을 중심으로 한 회전각이며, 단위는 도입니다.
  rotation_degrees?: number;
  // 양수인 균일 배치 축척입니다. 1이면 단위 변환 후 자산 크기를 유지합니다.
  scale?: number;
  // 현재 Rhino 문서 단위를 사용하는 배치 X 좌표입니다.
  x?: number;
  // 현재 Rhino 문서 단위를 사용하는 배치 Y 좌표입니다.
  y?: number;
  // 현재 Rhino 문서 단위를 사용하는 배치 Z 좌표입니다.
  z?: number;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 26. diagram\_04-search

대응 오리지널: `search_diagram_assets`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
사람·나무 등 등록된 2D 다이어그램을 키워드·분류·최대 치수로 검색합니다. 파일이 없는 자산도 결과에 포함됩니다. 상세 등록 정보와 파일 존재 상태는 diagram_01-get tool에서 조회할 수 있습니다.
```

```ts
declare const tools: { mcp__rhino__diagram_04_search(args: {
  // 분류 전체 일치, 대소문자 무시. 빈 값: 전체.
  category?: string;
  // dimensions, drawing, metadata, source, paths, audit, all. 생략·빈 배열: 요약. 세부 항목은 검색 결과에 나타나지 않을 수 있음.
  field_groups?: Array<string> | null;
  // true: 자산 ID 포함.
  include_ids?: boolean;
  // 기본 10, 1..50으로 보정.
  limit?: number;
  // 등록 치수 상한(mm). 0 이하: 필터 해제. 등록 치수는 추정치일 수 있음.
  max_depth_mm?: number;
  max_height_mm?: number;
  max_width_mm?: number;
  // 0부터 시작, 음수는 0으로 보정. 다음 페이지에도 같은 필터 사용.
  offset?: number;
  // 여러 검색어는 OR로 결합. 빈 값: 전체.
  query?: string;
}): Promise<CallToolResult<{
  // 목록·페이지 정보(next_offset 포함) 또는 오류를 담은 JSON 문자열.
  result: string;
}>>; };
```

## drawing

### 27. drawing\_01-list\_recipes

대응 오리지널: `list_drawing_recipes`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
사용 가능한 도면 스타일 레시피를 조회합니다. A4 평면·단면에는 Architectural Plan and Section A4를 선택합니다. include_ids=true로 얻은 recipe_id는 drawing_02-get_recipe tool의 입력에 사용합니다. result는 목록 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: { mcp__rhino__drawing_01_list_recipes(args: {
  // 상세 그룹: scales, parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
  field_groups?: Array<string> | null;
  // true이면 후속 호출에 사용할 ID를 포함합니다.
  include_ids?: boolean;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 28. drawing\_02-get\_recipe

대응 오리지널: `get_drawing_recipe`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
지정한 도면 스타일 레시피를 조회합니다. field_groups=["scales","parameters"]로 권장 축척·레이어·출력 설정을 확인한 뒤 같은 recipe_id를 drawing_01-apply_style tool에 전달합니다. result는 레시피 또는 오류를 담은 JSON 문자열입니다.
```

```ts
declare const tools: { mcp__rhino__drawing_02_get_recipe(args: {
  // 상세 그룹: scales, parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
  field_groups?: Array<string> | null;
  // true이면 후속 호출에 사용할 ID를 포함합니다.
  include_ids?: boolean;
  // drawing_05-list_recipes tool(include_ids=true)에서 얻은 도면 레시피 ID 또는 이미 알고 있는 레시피 ID입니다.
  recipe_id: string;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```

### 29. drawing\_03-apply\_style

대응 오리지널: `apply_drawing_style`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
도면 레시피의 레이어 계층과 색·출력색·출력 선 두께·선종류를 Rhino 문서에 생성하거나 갱신합니다. 같은 경로의 기존 레이어에도 적용됩니다. 문서에 같은 이름의 선종류가 있으면 기존 정의를 재사용합니다. 새 선종류를 만들 때는 Almond에 포함된 선종 매니페스트를 사용합니다. 레시피의 투영·축척·용지 설정으로 도면이나 Layout을 만들지는 않습니다.
```

```ts
declare const tools: { mcp__rhino__drawing_03_apply_style(args: {
  // drawing_05-list_recipes tool 또는 drawing_02-get_recipe tool의 레시피 ID. 생략: technical_axon_v1.
  recipe_id?: string;
}): Promise<CallToolResult<{
  // 적용 상태·레이어 목록 또는 오류를 담은 JSON 문자열. 오류·시간 초과가 롤백을 뜻하지는 않음.
  result: string;
}>>; };
```

### 30. drawing\_04-import\_hatches

대응 오리지널: `import_drawing_hatch_patterns`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
등록된 PAT 자산의 해치 패턴 정의를 Rhino 문서에 가져옵니다. 같은 이름이 이미 있으면 기존 정의를 재사용합니다. 도면에 해치 객체를 배치하지는 않습니다.
```

```ts
declare const tools: { mcp__rhino__drawing_04_import_hatches(args: {
  // 등록된 PAT 도면 자산 ID.
  asset_id: string;
}): Promise<CallToolResult<{
  // 상태·사용 가능한 패턴 이름 또는 오류의 JSON 문자열. patterns에는 신규와 기존 재사용 패턴이 함께 포함됨.
  result: string;
}>>; };
```

### 31. drawing\_06-generate\_plan\_section

```txt
활성 모델 또는 현재 Worksession에 첨부된 파일의 클리핑 평면으로 단면선·가시 입면선과 선택적 해치를 활성 모델에 생성합니다. 첨부 형상이 필요하면 먼저 필요한 파일을 Worksession에 첨부한 뒤 include_attachments를 선택합니다. Update는 저장된 위치에서 도면을 다시 계산하므로 기존 도면의 수동 편집이 교체될 수 있습니다. Move는 기존 도면 객체의 GUID와 수동 편집을 유지하며 원점을 옮깁니다.

응답에는 클리핑별 상태와 도면 객체 GUID, 실제 배치 평면이 포함됩니다. Create·Update에는 실제 계산에 들어간 원본 레이어와 객체 수, 숨김·잠금·첨부 입력의 처리 조건도 포함됩니다. 일부 완료 또는 취소 뒤에는 완료된 도면이 남을 수 있습니다.
```

```ts
declare const tools: { mcp__rhino__drawing_06_generate_plan_section(args: {
  // 클리핑 평면 GUID 목록. 비어 있을 수 없으며 중복은 한 번만 처리.
  clipping_ids: Array<string>;
  // 먼 입면선 출력 농도 0..100%. 기본 45, near_dark 이하.
  far_dark?: number;
  // 먼 입면선 출력 두께(mm). 기본 0.04, 양수이며 near_width 이하.
  far_width?: number;
  // 해치 생성 허용. 원본 단면 스타일의 채움과 형상 조건을 따름. 기본 true.
  hatch?: boolean;
  // 현재 모델만 계산하려면 false, 실제 첨부도 계산하려면 true. 생략 시 생성은 현재 모델, 갱신은 저장 범위를 사용합니다.
  include_attachments?: boolean | null;
  // 가까운 입면선 출력 농도 0..100%. 기본 80, far_dark 이상.
  near_dark?: number;
  // 가까운 입면선 출력 두께(mm). 기본 0.09, 양수이며 far_width 이상.
  near_width?: number;
  // Create: 생성 또는 교체. Update: 저장 위치에서 재생성. Move: 기존 도면의 평행 이동.
  operation: "Create" | "Update" | "Move";
  // 클리핑 GUID별 절대 도면 원점. Create에서 선택, Move에서 필수, Update에서 생략.
  points?: {
    [key: string]: Array<number>;
  } | null;
  // 작은 상세 보호 여부. 기본 false.
  small_details?: boolean;
}): Promise<CallToolResult<{
  // 상태·클리핑별 배치와 객체 GUID, 실제 추출 조건 또는 오류의 JSON 문자열.
  result: string;
}>>; };
```

## grasshopper

### 38. grasshopper\_01-get\_logic

대응 오리지널: `get_logic_by_id`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
색인된 Grasshopper 로직 파일에서 추출한 물리 관련 항목·설명과 제공된 메타데이터를 조회합니다. JSON만 있는 항목은 메타데이터를 반환합니다. 추출 정보는 완전한 구성·연결 관계나 실행 가능성을 보장하지 않습니다.
```

```ts
declare const tools: { mcp__rhino__grasshopper_01_get_logic(args: {
  // ports, definition, source, paths, audit, all. 제공된 필드에만 적용.
  field_groups?: Array<string> | null;
  // true: 다른 식별자 포함. 입력 logic_id는 반복되지 않음.
  include_ids?: boolean;
  // 확장자를 뺀 라이브러리 파일명. grasshopper_03-list_library tool의 logic_names 사용 가능.
  logic_id: string;
}): Promise<CallToolResult<{
  // 추출 정보·메타데이터 또는 오류의 JSON 문자열.
  result: string;
}>>; };
```

### 39. grasshopper\_02-list\_capsules

대응 오리지널: `list_capsules`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
등록된 Grasshopper 캡슐의 기능과 감사 상태를 조회합니다. 포트와 ID를 확인해 grasshopper_04-run_definition tool의 입력을 준비할 수 있습니다. 감사 상태는 정의 파일의 존재나 실행 성공을 보장하지 않습니다.
```

```ts
declare const tools: { mcp__rhino__grasshopper_02_list_capsules(args: {
  // true: audited로 등록된 캡슐만.
  audited_only?: boolean;
  // 기능 필터: analyze, generate, form_find, aggregate. 대소문자 무시.
  capability?: string;
  // ports, definition, source, paths, audit, all. 생략·빈 배열: 요약.
  field_groups?: Array<string> | null;
  // true: capsule_id 포함. all과 별도 지정.
  include_ids?: boolean;
}): Promise<CallToolResult<{
  // 최대 50개 캡슐과 전체 개수 또는 오류의 JSON 문자열. 다음 페이지를 지정하는 입력은 없음.
  result: string;
}>>; };
```

### 40. grasshopper\_03-list\_library

대응 오리지널: `list_library`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
로컬 Grasshopper 라이브러리에서 색인된 로직 이름을 조회합니다. logic_names의 이름으로 grasshopper_01-get_logic tool에서 상세 내용을 조회할 수 있습니다.
```

```ts
declare const tools: { mcp__rhino__grasshopper_03_list_library(args: {
  // paths·all: 라이브러리 경로 포함. ports·definition·source·audit은 목록에 상세를 추가하지 않음.
  field_groups?: Array<string> | null;
  // true: logic_names와 같은 값의 logic_ids 포함.
  include_ids?: boolean;
}): Promise<CallToolResult<{
  // 이름·개수·선택된 경로 또는 오류의 JSON 문자열.
  result: string;
}>>; };
```

### 41. grasshopper\_04-run\_definition

대응 오리지널: `run_gh_definition`. 기능 대응이며 호출 계약의 동일성을 뜻하지 않습니다.

```txt
실행 감사를 통과한 Grasshopper 캡슐을 Rhino에서 계산합니다. 정의에 따라 형상을 베이크할 수 있습니다.
```

```ts
declare const tools: { mcp__rhino__grasshopper_04_run_definition(args: {
  // grasshopper_02-list_capsules tool에서 얻은 안정적인 캡슐 식별자입니다(예: "karamba_beam_v1").
  capsule_id: string;
  // ALMOND_IN_ 포트 이름과 값의 객체입니다. grasshopper_02-list_capsules tool(field_groups=['ports'])의 input_ports에서 타입·단위·필수 여부를 확인합니다. 형상은 {"guids":["객체 GUID"]}, 숫자·정수·문자열·불리언은 JSON 값, 목록은 number[]/integer[]/string[]의 평탄한 배열입니다.
  inputs: {
    [key: string]: unknown;
  };
  // 확률적 정의에 사용할 선택적 정수 시드입니다. 결정적인 정의에서는 생략합니다.
  seed?: number | null;
  // 솔버 시간 한도(초)입니다. 기본값은 60, 최댓값은 600입니다.
  timeout_s?: number;
}): Promise<CallToolResult<{
  result: string;
}>>; };
```
