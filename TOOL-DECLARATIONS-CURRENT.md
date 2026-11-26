# 현행 툴 선언

이 문서는 beyond에서 호출하는 81개 도구의 공개 계약 원본이다. RhinoTerminal은 연결 관리 도구 5개를 제외한 76개를 현재 문서에 연결해 제공하며 `connection_id`를 받지 않는다. `Integer`는 정수다. `JsonResult<T>`는 `CallToolResult<{ result: string }>`이며, `result`를 JSON으로 파싱하면 `T`를 얻는다. 실제 두 경로의 스키마는 [런타임 선언 스냅샷](tests/integration/tool_catalogs.md)에서 확인한다.

`connection_id`는 `connect_02-session` 또는 `connect_03-start_session`에서 받은 소문자 16진수 32자리 문자열이다. 필요한 도구에는 필수 인자로 표시했다.

---

## connect

### connect_01-list_up

열린 Rhino 문서와 연결 상태를 조회한다. available이면 host_id와 model_path로 connect_02-session tool에 연결을 요청한다. ready이면 connection_id로 바로 작업한다.

```ts
declare const tools: {
  mcp__rhino__connect_01_list_up(args: Record<string, never>): Promise<CallToolResult<{
    targets: Array<{
      // recovering·unconfirmed이면 이전 실행 결과부터 확인한다.
      state: string;
      model_path?: string;
      host_id?: string;
      connection_id?: string;
      reason?: string;
    }>;
  }>>;
};
```

### connect_02-session

connect_01-list_up tool에서 고른 문서의 host_id와 model_path로 연결한다. 같은 문서에 이미 연결되어 있으면 기존 connection_id를 반환한다.

```ts
type ConnectedSession = {
  connection_id: string;
  state: "ready" | "recovering" | "unconfirmed";
  reason?: string;
};

declare const tools: {
  mcp__rhino__connect_02_session(args: {
    host_id: string;
    model_path: string;
  }): Promise<CallToolResult<ConnectedSession>>;
};
```

### connect_03-start_session

저장된 .3dm을 새 Rhino 창에서 연다. 시작을 기다리는 중이면 같은 경로와 request_id로 조회한다. 독립 실행이 거부되면 Rhino에서 파일을 열고 almondconnect를 실행한다.

```ts
declare const tools: {
  mcp__rhino__connect_03_start_session(args: {
    // 로컬 .3dm 파일의 절대 경로.
    model_path: string;
    // 새 창을 열 때마다 정하는 1~128자 고유 문자열.
    request_id: string;
  }): Promise<CallToolResult<ConnectedSession>>;
};
```

### connect_04-disconnect

연결 슬롯을 해제하고 Rhino 문서는 열어 둔다. 실행 중인 호출이 끝나야 해제할 수 있다.

```ts
declare const tools: {
  mcp__rhino__connect_04_disconnect(args: {
    connection_id: string;
  }): Promise<CallToolResult<{
    released: true;
    // 연결은 해제됐지만 내부 정리 중 오류가 생긴 경우.
    reason?: string;
  }>>;
};
```

### connect_05-close_session

Rhino 문서를 저장한 뒤 해당 Rhino 창을 닫는다. 같은 connection_id와 request_id로 다시 호출하면 이전 결과를 조회한다.

```ts
declare const tools: {
  mcp__rhino__connect_05_close_session(args: {
    connection_id: string;
    // 종료 요청마다 새로 정하는 1~128자 문자열.
    request_id: string;
  }): Promise<CallToolResult<{
    // completed이면 저장, Rhino 종료, 연결 해제가 모두 끝났다.
    status: "completed" | "closing" | "rejected" | "save_failed" | "unconfirmed";
    reason?: string;
    // 저장 결과가 불확실할 때 script_03-get_execution tool에 전달할 request_id.
    save_request_id?: string;
  }>>;
};
```

## context

### context_01-get_policy

Rhino 기술 자료를 조회한다. `basic`(기본값)은 공통 도구명과 자료 목록, `metadata`는 객체 메타데이터 키 사전, `rhino_scripting`은 스크립팅 문서, `rhinocode`는 실행 지침이다.

```ts
type PolicyName = "basic" | "metadata" | "rhino_scripting" | "rhinocode";
type SourceRef = { path: string; sha256: string };
type PolicyContent =
  | { selected_policy: "basic"; available_policies: Record<PolicyName, string>; tools: string[] }
  | { selected_policy: "metadata"; policy: Record<string, unknown>; source_refs: SourceRef[] }
  | { selected_policy: "rhino_scripting"; scripting_skill: { sources: Array<SourceRef & { text: string }> } }
  | { selected_policy: "rhinocode"; text: string; source_refs: SourceRef[] };

declare const tools: {
  mcp__rhino__context_01_get_policy(args: {
    policy?: PolicyName;
  }): Promise<CallToolResult<{ guide_version: string } & PolicyContent>>;
};
```

### context_04-get_project_info

연결한 문서와 프로젝트를 조회한다. 기본 조회에는 레이어 트리, Named View, Layout, 작업 경로가 포함된다. sections로 일부만 고를 수 있고 runtime은 요청할 때만 읽는다.

```ts
type ProjectSection = "project" | "document" | "layer_tree" | "named_views" | "layouts" | "locations" | "runtime";
type ViewRef = { name: string; id: string };

declare const tools: {
  mcp__rhino__context_04_get_project_info(args: {
    connection_id: string;
    sections?: ProjectSection[] | null;
    // Plan·Step ID, 문서 실행 번호와 RhinoCode pipe ID도 조회한다.
    include_ids?: boolean;
    // 등록 파일만 페이지로 읽는다. 기본 50개, 범위 1~500. offset에 읽은 개수를 더해 total까지 조회한다.
    files_limit?: Integer;
    files_offset?: Integer;
  }): Promise<CallToolResult<{
    status: "success";
    project?: {
      project_root: string;
      file_name: string | null;
      file_path: string | null;
      is_bound_document: boolean;
      // Phase·Scene에서 참조하는 프로젝트 등록 파일.
      files: Array<{ file_name: string; description: string | null }>;
      files_page: { total: Integer; offset: Integer };
      // 현재 Rhino에 첨부한 파일. []는 첨부 없음, null은 조회 실패.
      worksession_files: Array<{ file_path: string }> | null;
    };
    document?: {
      units: string | null;
      absolute_tolerance: number | null;
      angle_tolerance_radians: number | null;
      modified: boolean | null;
      layer_count: Integer | null;
      object_count: Integer | null;
      runtime_serial_number?: Integer | null;
    };
    // 한 줄에 한 레이어, 깊이마다 두 칸 들여쓴다. inspect_02-get_objects tool의 레이어 필터에는 부모부터 이름을 ::로 이은 전체 경로를 쓴다.
    layer_tree?: string | null;
    // 이름과 ID는 capture_04-defined_view tool의 target에 쓸 수 있다.
    named_views?: ViewRef[] | null;
    layouts?: ViewRef[] | null;
    locations?: {
      database: string;
      plan_id?: string;
      step_id?: string;
      loop_no?: Integer;
      read_only?: boolean;
      plan_artifact_dir?: string | null;  // Plan 전체 폴더
      artifact_dir: string | null;       // 현재 작업의 산출물 폴더
    };
    runtime?: {
      slot: string;
      scratch_root: string;
      python_executable: string;
      rhinocode: {
        available: boolean;
        languages: string[];
        executable?: string;
        version?: unknown;
        pipe_id?: string;
        message?: string;
      };
    };
    // 조회 실패나 뷰 목록 잘림을 알린다. Named View와 Layout은 각각 최대 128개다.
    warnings?: string[];
  } | { status: "error"; message: string; error_code?: string; warnings?: string[] }>>;
};
```

### context_05-upsert_project_file

프로젝트에 파일명을 등록하거나 설명을 갱신한다. 기존 파일은 등록된 대소문자와 실제 저장된 설명을 돌려준다.

```ts
declare const tools: {
  mcp__rhino__context_05_upsert_project_file(args: {
    connection_id: string;
    file_name: string;  // 폴더를 제외한 파일명
    // 생략하거나 null이면 기존 설명을 유지하고, 빈 문자열이면 지운다.
    description?: string | null;
  }): Promise<CallToolResult<
    | { status: "success"; file_name: string; description: string | null }
    | { status: "error"; message: string }
  >>;
};
```

## plan

### plan_02-create

Phase 또는 Plan을 만든다. Plan은 scope에 맞는 Step과 회차 0에서 시작한다.

```ts
type PlanningStatus = "pending" | "running" | "paused" | "completed" | "failed" | "blocked";
type PlanningStep = { step_id: string; name: string; step_type: string; status: PlanningStatus };

declare const tools: {
  mcp__rhino__plan_02_create(args: {
    connection_id: string;
    request: {
      target: "phase";
      // 공백만 있는 이름은 거부.
      name: string;
      // 같은 종류의 ID 형식만 검사. 대상 존재·순환·작업 순서는 확인하거나 강제하지 않음.
      depends_on?: string[] | null;
      description?: string;
      // context_04-get_project_info tool의 `project.files`에 등록된 파일명.
      file_name?: string[];
      // Phase ID 형식만 검사. 참조 대상의 존재는 확인하지 않음.
      previous_id?: string | null;
      // 기본값 "pending"
      status?: PlanningStatus;
    } | {
      target: "plan";
      // 공백만 있는 목표는 거부.
      goal: string;
      // 공백만 있는 제목은 거부.
      title: string;
      // 하위 Plan의 존재를 검사하거나 상대 Plan을 자동 수정하지 않음.
      child_plan?: string[] | null;
      // 결과나 결정에 의존하는 관련 Plan. 같은 종류의 ID 형식만 검사. 대상 존재·순환·작업 순서는 확인하거나 강제하지 않음.
      depends_on?: string[] | null;
      holon_ids?: string[] | null;
      // 상위 Plan의 존재를 검사하거나 상대 Plan을 자동 수정하지 않음.
      parent_plan?: string[] | null;
      phase_id?: string;
      // 작업 순서상 직전 Plan. Plan ID 형식만 검사. 참조 대상의 존재는 확인하지 않음.
      previous_id?: string | null;
      scene_ids?: string[] | null;
      // Step 템플릿. 기본 제공 키는 `spatial_development`, `drawing_development`, `semantic_exploration`, `plan_editing`, `model_revision`, `inspection`, `structure`, `construction_detail`, `drawing`, `component`, `house`, `interior`. 등록된 사용자 템플릿도 사용 가능. · 기본값 "house"
      scope?: string;
    };
  }): Promise<JsonResult<{
    error_code?: string;
    message?: string;
    phase?: {
      phase_id?: string;
    };
    plan?: {
      loop_no?: Integer;
      plan_id?: string;
      // 수정 시 `loop_no`와 함께 `expected_revision`으로 사용 가능.
      revision?: Integer;
    };
    status?: string;
  }>>;
};
```

### plan_03-execute_looping

새 회차를 시작하거나 resume으로 최신 회차를 재개한다. plan_10-set_working tool의 step_id에 next_step_id를 전달해 Step을 선택한다.

```ts
type LoopStep = PlanningStep & {
  kind?: string;
  depends_on?: string[]; input_refs?: string[]; output_refs?: string[];
  design_rationale?: string; takeaways?: string;
};

declare const tools: {
  mcp__rhino__plan_03_execute_looping(args: {
    connection_id: string;
    // plan_02-create tool 또는 plan_08-list tool에서 얻은 ID.
    plan_id: string;
    // 최초 산출물 폴더명. 생략하면 목표에서 정하고 `YYMMDD_` 접두사를 붙임. 기존 폴더는 재사용.
    artifact_name?: string;
    // 재개 시 생략하거나 비우면 이전 피드백 유지.
    feedback?: string;
    // `true`면 최신 회차 재개, `false`면 새 회차 시작.
    resume?: boolean;
  }): Promise<CallToolResult<{
    artifact_dir?: string | null;
    error_code?: string;
    feedback?: string;
    goal?: string;
    loop_no?: Integer;
    message?: string;
    // 다음 작업으로 선택할 첫 미완료 Step.
    next_step_id?: string | null;
    plan_artifact_dir?: string;
    plan_id?: string;
    // 회차를 시작해도 Plan 상태는 유지.
    plan_status?: PlanningStatus;
    // 첫 회차에는 실행 전 0번 기록을 포함할 수 있음.
    previous_loop?: {
      loop_no?: Integer;
      steps?: LoopStep[];
    } | null;
    revision?: Integer;
    status?: string;
    steps?: LoopStep[];
    title?: string;
  }>>;
};
```

### plan_05-get

Phase·Plan·Step 작업 기록 조회. `include_details=true`로 상세를 포함. 다음 작업에 필요한 파일은 반환된 프로젝트 상대경로로 열어 확인.

Plan·Step 조회에 `revision`을 지정하면 현재 번호여도 읽기 전용 스냅샷 반환.

```ts
declare const tools: {
  mcp__rhino__plan_05_get(args: {
    connection_id: string;
    request: {
      target: "phase";
      phase_id: string;
      include_details?: boolean;
    } | {
      target: "plan";
      plan_id: string;
      include_details?: boolean;
      // 0 이상. 생략·`null`은 최신 회차, 0은 실행 전 기록.
      loop_no?: Integer | null;
      // 생략·`null`은 선택한 회차의 최신 상태.
      revision?: Integer | null;
    } | {
      target: "step";
      plan_id: string;
      // 같은 요청의 `plan_id`에 속한 Step만 조회 가능.
      step_id: string;
      include_details?: boolean;
      // 0 이상. 생략·`null`은 최신 회차, 0은 실행 전 기록.
      loop_no?: Integer | null;
      // 생략·`null`은 선택한 회차의 최신 상태.
      revision?: Integer | null;
    };
  }): Promise<JsonResult<{
    error_code?: string;
    phase_id?: string;
    step_id?: string;
    // 0은 회차 시작 전 기록.
    loop_no?: Integer;
    message?: string;
    name?: string;
    phase?: {
      depends_on?: string[];
      description?: string;
      file_name?: string[];
      plan_titles?: string[];
      previous_id?: string | null;
    };
    plan?: {
      // 회차별 산출물 폴더를 담는 Plan 루트.
      artifact_dir?: string;
      artifact_refs?: string[];
      child_plan?: string[];
      // 한국 시간 `YYYY-MM-DD-HH:MM`.
      created_at?: string;
      depends_on?: string[];
      feedback?: string;
      goal?: string;
      holon_ids?: string[];
      loop_artifact_dir?: string;
      parent_plan?: string[];
      phase?: {
        name?: string;
        phase_id?: string;
      } | null;
      previous_id?: string | null;
      scene_ids?: string[];
      // Step 템플릿 키.
      scope?: string;
      steps?: PlanningStep[];
      // 한국 시간 `YYYY-MM-DD-HH:MM`.
      updated_at?: string;
    };
    plan_id?: string;
    // 과거 회차 또는 명시적으로 지정한 리비전이면 `true`. 수정 전 최신 기록 재조회.
    read_only?: boolean;
    revision?: Integer;
    status?: PlanningStatus | "error";
    step?: {
      design_rationale?: string;
      input_refs?: string[];
      output_refs?: string[];
      step_type?: string;
      // 다음 작업에 넘길 주요 발견과 교훈.
      takeaways?: string;
    };
    type?: "phase" | "plan" | "step";
  }>>;
};
```

### plan_07-list_revisions

Plan 리비전 목록을 최신 회차·리비전 순으로 조회. Step 필터는 해당 Step의 직접 변경만 포함. `offset` 미지원.

과거 기록은 plan_05-get tool에 같은 `loop_no`와 `revision`을 넣어 조회.

```ts
declare const tools: {
  mcp__rhino__plan_07_list_revisions(args: {
    connection_id: string;
    // plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 plan_id
    plan_id: string;
    // `audit` 또는 `all`은 생성 시각 포함. 생략하거나 비우면 기본 필드만 반환.
    field_groups?: string[] | null;
    // 1~500. · 기본값 50
    limit?: Integer;
    // 생략·`null`은 모든 회차, 0은 실행 전 기록.
    loop_no?: Integer | null;
    // 생략하거나 비우면 Step으로 필터링하지 않음.
    step_id?: string;
  }): Promise<JsonResult<{
    error_code?: string;
    limit?: Integer;
    message?: string;
    // 행의 `loop_no`·`revision`과 함께 plan_05-get tool의 `request`에 사용.
    plan_id?: string;
    revisions?: Array<{
      // `audit` 또는 `all` 그룹에서 반환.
      created_at?: string;
      loop_no?: Integer;
      operation?: string;
      revision?: Integer;
      step_id?: string | null;
    }>;
    status?: string;
    total?: Integer;
    truncated?: boolean;
  }>>;
};
```

### plan_08-list

Phase·Plan 목록 또는 한 Plan의 순서 있는 Step 목록 조회. `offset` 미지원. Step 목록과 리비전 정보는 같은 스냅샷을 기준으로 반환.

```ts
declare const tools: {
  mcp__rhino__plan_08_list(args: {
    connection_id: string;
    request: {
      target: "phase";
      // `description`은 설명, `scope`는 연결 파일, `audit`는 생성·수정 시각, `all`은 전체. 생략하거나 비우면 요약 반환.
      field_groups?: string[] | null;
      // 1~500. · 기본값 50
      limit?: Integer;
    } | {
      target: "plan";
      // 1~500. · 기본값 50
      limit?: Integer;
      // 생략하거나 비우면 Phase 소속 여부와 관계없이 조회.
      phase_id?: string;
      // 생략하거나 비우면 Scene 연결 여부와 관계없이 조회.
      scene_id?: string;
      // 생략하거나 비우면 상태 필터를 적용하지 않음.
      status?: "" | PlanningStatus;
    } | {
      target: "step";
      plan_id: string;
      // 1~500. 정의된 순서의 앞부분을 반환. · 값 1~500 · 기본값 50
      limit?: Integer;
      // 0 이상. 생략·`null`은 최신 회차, 0은 실행 전 기록.
      loop_no?: Integer | null;
      // 생략·`null`은 선택한 회차의 최신 상태. 지정하면 읽기 전용 스냅샷.
      revision?: Integer | null;
    };
  }): Promise<JsonResult<{
    error_code?: string;
    limit?: Integer;
    loop_no?: Integer;
    message?: string;
    phases?: Array<{
      depends_on?: string[];
      // `description` 또는 `all` 그룹에서 반환.
      description?: string;
      // `scope` 또는 `all` 그룹에서 반환하는 Rhino 파일명.
      file_name?: string[];
      name?: string;
      phase_id?: string;
      plan_count?: Integer;
      previous_id?: string | null;
      status?: string;
      // `audit` 또는 `all` 그룹에서 반환.
      created_at?: string;
      updated_at?: string;
    }>;
    plan_id?: string;
    plans?: Array<{
      loop_no?: Integer;
      plan_id?: string;
      revision?: Integer;
      // Step 템플릿 키.
      scope?: string;
      status?: string;
      title?: string;
    }>;
    // 과거 회차 또는 명시적으로 지정한 리비전이면 `true`.
    read_only?: boolean;
    revision?: Integer;
    status?: string;
    steps?: PlanningStep[];
    total?: Integer;
    truncated?: boolean;
  }>>;
};
```

### plan_09-rename_artifact_folder

첫 Loop를 시작하기 전에 현재 Plan의 산출물 폴더명을 바꾼다. 먼저 plan_10-set_working tool로 폴더를 만든다.

```ts
declare const tools: {
  mcp__rhino__plan_09_rename_artifact_folder(args: {
    connection_id: string;
    // 경로 대신 폴더명 하나. `YYMMDD_` 접두사가 없으면 현재 날짜를 붙임. Windows 금지 문자 사용 불가.
    name: string;
    // 생략하거나 비우면 현재 선택된 Plan 사용.
    plan_id?: string;
  }): Promise<CallToolResult<{
    artifact_dir?: string | null;
    error_code?: string;
    message?: string;
    // 폴더 이름이 실제로 변경된 경우에만 반환.
    previous_artifact_dir?: string;
    status?: string;
  }>>;
};
```

### plan_10-set_working

현재 연결의 산출물 작업 대상으로 Plan과 선택적인 Step 지정. 작업 실행과 Plan·Step 상태 변경은 별도.

최초 선택에서 산출물 경로를 정하면 리비전이 증가할 수 있음. 이후 같은 경로 재사용. `artifact_dir`은 Loop 시작 전 Plan 루트, 시작 후 현재 회차 폴더.

```ts
declare const tools: {
  mcp__rhino__plan_10_set_working(args: {
    connection_id: string;
    // plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 plan_id
    plan_id: string;
    // 최초 폴더명. 생략하면 목표에서 정하고 `YYMMDD_` 접두사를 붙임. 기존 폴더와 다른 이름은 거부.
    artifact_name?: string;
    // 지정한 회차가 최신 회차인지 확인한다.
    loop_no?: Integer | null;
    // 생략하면 Plan만 선택.
    step_id?: string;
  }): Promise<CallToolResult<{
    // script_01-run_project_python tool의 작업 디렉터리.
    artifact_dir?: string | null;
    error_code?: string;
    loop_no?: Integer;
    message?: string;
    plan_artifact_dir?: string;
    plan_id?: string;
    revision?: Integer;
    status?: string;
    step_id?: string;
  }>>;
};
```

### plan_12-update

Phase·Plan 작업 정보 또는 Step 상태·입출력 참조·판단 기록 수정. Plan·Step은 현재 회차만 수정 가능.

`depends_on`, `input_refs`, `output_refs`는 `add`/`remove` 패치. 나머지 대상·산출물·상하위 관계 배열은 전체 교체. 생략·`null`은 기존 값 유지, 교체 배열의 `[]`는 전체 삭제.

응답 `status`는 모두 반영해 값이 바뀌면 `updated`, 바뀐 값이 없으면 `no_change`, 변경과 건너뛴 항목이 함께 있으면 `partial_success`. 이미 추가된 값, 없어서 지울 수 없는 값, 중복·잘못된 값과 두 목록에 동시에 넣은 값은 issues에서 확인. Step을 `completed`로 지정하면 함께 전달한 필드와 한 번에 저장.

Plan 완료는 사용자 확인 후 지정.

```ts
type StringListPatch = { add?: string[]; remove?: string[] };

declare const tools: {
  mcp__rhino__plan_12_update(args: {
    connection_id: string;
    request: {
      target: "phase";
      // plan_08-list tool의 `request.target="phase"` 결과에 있는 `phases[].phase_id` 또는 plan_05-get tool의 phase_id.
      phase_id: string;
      // 같은 종류의 Phase ID만 사용. 대상 존재·순환·완료 여부는 검사하지 않음.
      depends_on?: StringListPatch | null;
      // 빈 문자열은 설명 삭제.
      description?: string | null;
      // project.files에 등록된 파일명. []는 연결 해제.
      file_name?: string[] | null;
      // 빈 이름은 거부.
      name?: string | null;
      // 빈 문자열은 연결 해제.
      previous_id?: string | null;
      status?: PlanningStatus | null;
    } | {
      target: "plan";
      // plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 plan_id
      plan_id: string;
      artifact_refs?: string[] | null;
      // 상대 Plan을 자동 수정하거나 참조 대상의 존재를 검사하지 않음.
      child_plan?: string[] | null;
      // 결과나 결정에 의존하는 관련 Plan. Plan ID 형식만 검사. 대상 존재·자기 참조·순환은 확인하지 않으며 순서나 완료도 강제하지 않음.
      depends_on?: StringListPatch | null;
      // 현재 리비전과 다르면 수정 거부. Loop 시작 후에는 `loop_no`도 함께 지정.
      expected_revision?: Integer | null;
      // 빈 목표는 거부.
      goal?: string | null;
      holon_ids?: string[] | null;
      // 현재 회차만 허용. 생략하면 현재 회차 적용.
      loop_no?: Integer | null;
      // 상대 Plan을 자동 수정하거나 참조 대상의 존재를 검사하지 않음.
      parent_plan?: string[] | null;
      // 빈 문자열은 Phase 소속 해제.
      phase_id?: string | null;
      // 작업 순서상 직전 Plan. 빈 문자열은 연결 해제.
      previous_id?: string | null;
      scene_ids?: string[] | null;
      // `completed`는 사용자의 완료 결정 후 지정.
      status?: PlanningStatus | null;
      // 빈 제목은 거부.
      title?: string | null;
    } | {
      target: "step";
      // plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 plan_id
      plan_id: string;
      // plan_05-get tool의 Plan 상세에서 확인한 Step ID.
      step_id: string;
      // 설계 결정의 이유와 근거. 빈 문자열은 내용 삭제.
      design_rationale?: string | null;
      // 현재 리비전과 다르면 수정 거부. Loop 시작 후에는 `loop_no`도 함께 지정.
      expected_revision?: Integer | null;
      input_refs?: StringListPatch | null;
      // 현재 회차만 허용. 생략하면 현재 회차 적용.
      loop_no?: Integer | null;
      output_refs?: StringListPatch | null;
      status?: PlanningStatus | null;
      // 다음 작업에 넘길 핵심 결론과 확인 사항. 빈 문자열은 내용 삭제.
      takeaways?: string | null;
    };
  }): Promise<JsonResult<{
    // 실제 저장 값이 바뀌었으면 true. Step 완료 후 Rhino 후속 작업이 실패해도 저장된 변경은 유지.
    changed?: boolean;
    // 실패 시 확인된 Rhino 후속 작업 상태.
    cleanup_state?: "not_started" | "rolled_back" | "unknown";
    error_code?: string;
    // 이 목록에 없는 변경은 저장되었을 수 있음.
    issues?: Array<{
      field?: string;
      // 해당 패치 배열에서의 0 기반 위치.
      index?: Integer;
      // `add` 또는 `remove`.
      operation?: string;
      reason?: string;
      value?: unknown;
    }>;
    message?: string;
    phase?: {
      phase_id?: string;
      status?: PlanningStatus;
    };
    // Step 수정 응답에도 소속 Plan의 저장 정보 포함.
    plan?: {
      // 0은 회차 시작 전 기록.
      loop_no?: Integer;
      plan_id?: string;
      // 다음 수정에서 `loop_no`와 함께 `expected_revision`으로 사용 가능.
      revision?: Integer;
      status?: PlanningStatus;
    };
    // `true`면 Rhino 또는 DB 상태를 확인해 후속 작업을 결정.
    requires_reconciliation?: boolean;
    // 수정 결과. 실제 변경은 updated, 무변경은 no_change, 변경과 건너뛴 항목이 함께 있으면 partial_success.
    status?: "updated" | "no_change" | "partial_success" | "error";
    step?: {
      status?: PlanningStatus;
      step_id?: string;
    };
  }>>;
};
```

## script

### script_01-run_project_python

선택한 Plan·Loop 폴더에서 Python을 실행한다. 상대 경로로 산출물을 쓰고 JSON 결과는 result에 할당한다.

```ts
type LogPage = { returned_bytes?: Integer; retained_bytes?: Integer; next_offset?: Integer | null };
type ExecutionReceipt = {
  request_id?: string; status?: string; completed?: boolean; pending?: boolean;
  mutation_state?: string; completion_state?: string; connection_state?: string;
  timed_out?: boolean; uncertain?: boolean;
  diagnostics_truncated?: boolean;
  result?: unknown; result_error?: string | null; result_display_error?: string | null;
  error_code?: string; message?: string;
  result_file?: string; result_bytes?: Integer; result_sha256?: string;
  result_page?: {
    type?: string; unit?: string; available_fields?: string[]; metadata_truncated?: boolean;
    pages?: Record<string, { returned?: Integer; total?: Integer; next_offset?: Integer | null }>;
  };
};

declare const tools: {
  mcp__rhino__script_01_run_project_python(args: {
    connection_id: string;
    // 동기식 Python. doc과 scriptcontext.doc은 연결 문서. 상대 경로는 산출물 폴더 기준.
    code: string;
    // 1~600초, 기본 60. 60초 이내에 완료를 확인하지 못하면 pending과 request_id를 반환할 수 있다.
    timeout_seconds?: Integer;
  }): Promise<CallToolResult<ExecutionReceipt & { artifact_dir?: string | null }>>;
};
```

### script_02-run_rhino

RhinoCode에서 스크립트나 명령을 실행한다. 완료가 불확실하면 request_id로 실행 기록과 모델 상태를 확인한다.

```ts
declare const tools: {
  mcp__rhino__script_02_run_rhino(args: {
    connection_id: string;
    // Python은 result에 JSON 호환 값, C# 문장 본문은 result_json에 JSON을 할당. doc은 연결 문서. 명령 매크로는 !·Pause·대화상자 없이 종료해야 한다.
    script: string;
    // 기본값 "python" (Python 3)
    language?: "python" | "python2" | "csharp" | "csharp-script" | "command";
    // 1~600초, 기본 60. 60초 이내에 완료를 확인하지 못하면 pending과 request_id를 반환할 수 있다.
    timeout_seconds?: Integer;
  }): Promise<JsonResult<ExecutionReceipt>>;
};
```

### script_03-get_execution

실행 상태·결과·로그를 조회한다. 결과의 배열은 항목, 문자열은 문자, 로그는 바이트 단위로 페이지를 읽는다.

```ts
declare const tools: {
  mcp__rhino__script_03_get_execution(args: {
    connection_id: string;
    // 정상 완료에서도 CLI·Undo·호출 식별 근거를 diagnostics에 포함.
    include_diagnostics?: boolean;
    // 기본값 true
    include_ids?: boolean;
    // 기본값 true
    include_result?: boolean;
    // stdout·stderr와 CLI 로그 포함
    include_stdout?: boolean;
    // 결과 페이지당 1~1000. 로그에는 별도 크기 제한 적용 · 기본값 100
    limit?: Integer;
    // 기본값 0
    offset?: Integer;
    // 생략 시 현재 연결의 최근 실행. 시간 초과 후에는 반환된 ID를 지정.
    request_id?: string;
    // 객체 결과의 최상위 키 또는 객체 배열의 각 행에서 유지할 키
    result_fields?: string[] | null;
  }): Promise<CallToolResult<ExecutionReceipt & {
    stdout?: string; stderr?: string; cli_stdout?: string; cli_stderr?: string;
    stdout_page?: LogPage; stderr_page?: LogPage; cli_stdout_page?: LogPage; cli_stderr_page?: LogPage;
    native_completed?: boolean; cleanup_errors?: unknown[]; requires_reconnect?: boolean; recovery_only?: boolean;
    // include_result=false일 때 보관된 결과 유무.
    result_available?: boolean;
    // 상세 요청 또는 실패·미확정 실행의 근거. 요청한 로그가 잘리거나 읽히지 않은 경우와 연결 종료 후 조회한 실행의 Rhino 식별 정보도 포함한다.
    diagnostics?: Record<string, unknown>;
  }>>;
};
```

### script_04-save_document

사용자가 영구 저장을 요청하면 연결 문서 전체를 기존 .3dm 경로에 저장한다.

```ts
declare const tools: {
  mcp__rhino__script_04_save_document(args: {
    connection_id: string;
  }): Promise<JsonResult<{
    error_code?: string;
    message?: string;
    modified?: boolean;
    requires_reconciliation?: boolean;
    // 저장이 미확정이면 null이다. 재호출 전 문서 상태를 확인한다.
    saved?: boolean | null;
    status?: string;
  }>>;
};
```

## inspect

### inspect_01-analyze_nested_blocks

outline으로 중첩 블록 구조를 조회하고 resolve-block으로 공유 정의의 영향 범위와 참조·링크 제한을 확인한다. 후속 조회에 ID가 필요하면 include_ids=true를 지정한다.

```ts
declare const tools: {
  mcp__rhino__inspect_01_analyze_nested_blocks(args: {
    connection_id: string;
    mode: "outline" | "resolve-block";
    // outline: ids 또는 path로 지정. 둘 다 생략하면 scope=selected(기본)·viewport·document 중 사용.
    // depth 0..64(기본 64), max_items 1..5000(기본 200), max_bytes 2048..262144(기본 48000).
    // field_groups: summary(기본), objects, annotations, transforms. annotation_layer는 TextDot 레이어 필터. field_groups 생략 시 include_geometry·annotations로 상세 조회.
    // resolve-block: options에는 최상위부터 대상까지 GUID 1..65개를 담은 path만 지정.
    options: Record<string, unknown>;
    // 생략하면 연결 문서 사용. 지정하면 일치하는 경로에서만 조회.
    expected_model_path?: string;
    include_ids?: boolean;
  }): Promise<JsonResult<{
    data?: {
      items?: Integer;
      depth_limited?: boolean;
      reason?: string | null;
      // resolve-block에서 확인한 조회 대상. 정의 배치 행렬은 행 우선 4×4 배열.
      definition?: string;
      definition_to_world?: number[];
      id?: string;
      name?: string | null;
      layer?: string | null;
      type?: string;
      document_object?: boolean;
      root_object_id?: string;
      block_path_ids?: string[];
      selectable_now?: boolean;
      candidate_count?: Integer;
      candidate_object_ids?: string[];
      candidates_truncated?: boolean;
      editor_owner_verified?: boolean;
      editing_permission?: string;
      definition_impact?: {
        // 영향 범위 계수 완료 여부와 반환 목록의 잘림 여부
        complete?: boolean;
        occurrence_count?: Integer | null;
        observed_occurrence_count?: Integer;
        affected_root_count?: Integer | null;
        observed_affected_root_count?: Integer;
        occurrences?: Array<Record<string, unknown>>;
        occurrences_truncated?: boolean;
        container_definitions?: Array<Record<string, unknown>>;
        container_definitions_truncated?: boolean;
        definition_is_reference?: boolean;
        update_type?: string;
        source_archive_present?: boolean;
        limits?: string[];
      };
      records?: Array<{
        definition?: string;
        // 배치 객체 또는 정의 구성원의 ID. 편집 가능한 문서 객체 ID는 inspect_02-get_objects tool로 확인.
        id?: string;
        kind?: "summary" | "occurrence" | "owner" | "note" | "note_target";
        name?: string | null;
        layer?: string | null;
        hidden?: boolean;
        locked?: boolean;
        // summary의 선택 범위 집계
        root_count?: Integer;
        names?: string[];
        names_truncated?: boolean;
        types?: Record<string, Integer>;
        // annotations의 소유 범위와 TextDot
        owner?: string;
        note_id?: string;
        member_types?: Record<string, Integer>;
        point_local?: [number, number, number];
        text?: string | null;
        text_limited?: boolean;
        // transforms의 행 우선 4×4 배열
        definition_to_world?: number[];
        geometry_to_world?: number[];
        // 공유 정의 영향을 조회할 때 resolve-block의 options.path에 재사용
        path?: string[];
        type?: string;
      }>;
      truncated?: boolean;
    };
    document?: {
      // 문서 길이 단위
      absolute_tolerance?: number;
      units?: string;
    };
    error_code?: string;
    message?: string;
    status?: string;
  }>>;
};
```

### inspect_02-get_objects

현재·전체 문서·뷰포트에서 객체를 필터링한다. hierarchy는 그룹·블록을 펼친다. 다음 행 페이지에는 snapshot과 next_offset, 면 편집에는 최상위 객체 ID·geometry_crc·face_index를 사용한다.

```ts
type XYZ = [number, number, number];
type Bounds = { min: XYZ; max: XYZ };
type ObjectMetadata = { values?: Record<string, unknown>; total_keys?: Integer; truncated?: boolean };
type ObservedObject = {
  id?: string; name?: string; layer_path?: string; object_type?: string; geometry_kind?: string;
  visible?: boolean; selected?: boolean; hidden?: boolean; locked?: boolean;
  bounds?: Bounds | null; groups?: Array<Record<string, unknown>>; groups_truncated?: boolean; user_text?: ObjectMetadata;
  user_dictionary?: { attributes?: ObjectMetadata; geometry?: ObjectMetadata };
};
type Terms = { include?: string[]; exclude?: string[] };
type TextTest = { key: string; any_of: string[] };
type DictionaryTest = { source: "attributes" | "geometry"; key: string; any_of: Array<string | boolean | number> };
// 배열은 최대 16개 조건을 모두 만족해야 한다. include·exclude는 각각 조건 하나다.
type MetadataFilter<T> = T[] | { include?: [T]; exclude?: [T] };

declare const tools: {
  mcp__rhino__inspect_02_get_objects(args: {
    connection_id: string;
    // 1..8, 루트=1(기본). 하위 깊이에는 recursive=true 필요.
    depth?: Integer;
    // 객체 GUID별 CRC. 면을 이어서 조회할 때 형상이 바뀌면 거부.
    expected_geometry_crcs?: Record<string, Integer> | null;
    // 생략하면 연결 문서 사용. 지정하면 일치하는 경로에서만 조회.
    expected_model_path?: string;
    // offset > 0이면 첫 페이지의 snapshot 필요
    expected_snapshot?: string;
    // 1..128. objects 모드에서 사용. · 기본값 128
    face_limit?: Integer;
    // 양수이면 scope=document, object_ids 및 객체별 expected_geometry_crcs 필요 · 기본값 0
    face_offset?: Integer;
    // 1개 이상 선택: id, name, layer_path, object_type, geometry_kind, geometry_crc, visible, selected, hidden, locked, bounds, groups, user_dictionary, user_text, geometry_valid, solid, manifold, volume, faces, face_count. 형상 상세와 faces는 objects 모드에서만 사용. summary에서는 fields 지정 불가.
    fields?: string[] | null;
    // layer는 전체 경로 또는 GUID. group은 여러 값일 때 해당 쪽의 mode를 지정한다.
    filters?: {
      layer?: Terms; block?: Terms; material?: Terms; name?: Terms; object_type?: Terms;
      name_contains?: string;
      group?: Terms & { include_mode?: "any" | "all"; exclude_mode?: "any" | "all" };
      user_text?: MetadataFilter<TextTest>;
      user_dictionary?: MetadataFilter<DictionaryTest>;
    } | null;
    // 서로 다른 Rhino 그룹 GUID 1..64개. 모든 scope에서 사용 가능, object_ids와 동시 지정 불가.
    group_ids?: string[] | null;
    // fields를 생략한 objects 모드에서 형상 상세를 포함. fields를 명시하면 그 목록 우선.
    include_geometry?: boolean;
    include_ids?: boolean;
    // current 전용. 활성 뷰포트 경계에 걸친 바운딩 박스 포함. 클리핑 평면과 픽셀 가림은 고려하지 않으며 selected와 동시 지정 불가.
    inside_window?: boolean;
    // 1..200 · 기본값 50
    limit?: Integer;
    // scope=document 전용. 서로 다른 최상위 객체 GUID 1..4096개. group_ids와 동시 지정 불가.
    object_ids?: string[] | null;
    // 0..100000, 기본 0
    offset?: Integer;
    // 블록·그룹 하위를 펼친다.
    recursive?: boolean;
    // 기본값 "objects". summary에서 recursive=true 사용 불가.
    result_mode?: "objects" | "hierarchy" | "summary";
    // 기본값 "current". document는 숨김·잠금 포함. inside_viewport는 current 중 활성 뷰 또는 Detail과 경계 상자가 교차하는 객체.
    scope?: "current" | "document" | "inside_viewport";
    // current 전용. 화면 밖에서 선택된 객체도 포함. inside_window와 동시 지정 불가.
    selected?: boolean;
  }): Promise<JsonResult<{
    // 계층 하위의 관찰 상태는 각 children_state 참조
    complete?: boolean;
    editing?: { mode?: string; target?: unknown; stable?: boolean; warnings?: string[] };
    limitations?: string[];
    error_code?: string;
    matched_count?: Integer;
    message?: string;
    next_offset?: Integer | null;
    page_complete?: boolean; membership_complete?: boolean; depth_limited?: boolean; cycle_limited?: boolean;
    summary?: Array<{ layer_path?: string; object_type?: string; geometry_kind?: string; object_count?: Integer; visible_count?: Integer }>;
    nodes?: Array<ObservedObject & {
      number?: Integer; parent_number?: Integer | null; depth?: Integer; children_state?: string;
      root_object_id?: string; block_path_ids?: string[]; document_object?: boolean; entity_kind?: string;
    }>;
    objects?: Array<ObservedObject & {
      face_count?: Integer;
      face_edit_supported?: boolean;
      geometry_valid?: boolean;
      solid?: boolean;
      manifold?: boolean;
      // 문서 길이 단위의 세제곱. null은 계산 실패.
      volume?: number | null;
      face_page?: {
        complete?: boolean;
        next_offset?: Integer | null;
        returned?: Integer;
      };
      faces?: Array<{
        // 기본 편집 조건만 확인한 값. 실제 편집 전에 형상 버전을 다시 검사.
        face_edit_supported?: boolean;
        // 같은 관찰의 id·geometry_crc와 묶어 model_02-edit_planar_face tool의 object_id·face_index·expected_geometry_crc에 전달
        face_index?: Integer; planar?: boolean; normal?: XYZ | null; plane_origin?: XYZ | null; bounds?: Bounds | null;
      }>;
      faces_truncated?: boolean;
      // 면 편집과 후속 면 조회에 사용할 형상 버전
      geometry_crc?: number;
    }>;
    // 후속 행 조회의 expected_snapshot에 그대로 전달
    snapshot?: string;
    status?: string;
  }>>;
};
```

### inspect_03-get_document_context

연결 문서의 상태와 Named View·Layout·레이어 계층·표시 모드를 조회한다. Named View·Layout·표시 모드는 목록별 최대 128개이며 항상 ID를 반환한다.

```ts
declare const tools: {
  mcp__rhino__inspect_03_get_document_context(args: {
    connection_id: string;
    // editor 요청 시 공급자·명령·Undo 근거 포함
    include_editor_details?: boolean;
    // 뷰포트 등 선택적으로 ID를 반환하는 항목에 적용
    include_ids?: boolean;
    // 기본값: document, named_views, layouts, layer_tree, display_modes. []이면 조회 항목 없음.
    sections?: Array<"document" | "viewport" | "editor" | "viewports" | "named_views" | "layouts" | "layer_tree" | "display_modes"> | null;
  }): Promise<JsonResult<{
    document?: {
      // 문서 길이 단위
      absolute_tolerance?: number | null;
      // 라디안
      angle_tolerance?: number | null;
      layer_count?: number | null;
      modified?: boolean | null;
      object_count?: Integer | null;
      units?: string | null;
    };
    viewport?: Record<string, unknown> | null;
    viewports?: Array<Record<string, unknown>> | null;
    editor?: { mode?: string; target?: unknown; stable?: boolean; warnings?: string[]; evidence?: Record<string, unknown> };
    display_modes?: Array<{ id?: string; name?: string }> | null;
    error_code?: string;
    layer_tree?: string | null;
    layouts?: Array<{
      id?: string;
      name?: string;
    }> | null;
    message?: string;
    named_views?: Array<{
      id?: string;
      name?: string;
    }> | null;
    status?: string;
    warnings?: string[];
  }>>;
};
```

### inspect_04-get_selection_references

저장된 Rhino 문서의 일반 모델에서 선택 객체의 소속 Holon과 상위 Holon을 참조하는 Plan을 조회한다. 선택과 일치한 Holon을 반환하며 Plan의 전체 대상은 별도 조회한다.

```ts
declare const tools: {
  mcp__rhino__inspect_04_get_selection_references(args: {
    connection_id: string;
    // steps, references, geometry, artifacts, description, scope, audit, all. 생략·빈 배열이면 요약.
    field_groups?: string[] | null;
    // 반환할 Plan 수 1..500 · 기본값 50
    limit?: Integer;
    // 검사할 선택 객체 수 1..200 · 기본값 50
    selection_limit?: Integer;
  }): Promise<JsonResult<{
    error_code?: string;
    // 선택 객체를 소유한 Holon과 상위 Holon
    holons?: Array<Record<string, unknown>>;
    message?: string;
    // 선택 객체의 등록 여부와 소유 Holon 포함
    objects?: Array<Record<string, unknown>>;
    // 현재 Rhino에서 소유 관계를 확인한 결과. 선택이 없으면 false.
    ownership_live_verified?: boolean;
    plans?: Array<Record<string, unknown>>;
    selection_total?: Integer;
    selection_truncated?: boolean;
    status?: string;
    total_plans?: Integer;
    // 반환한 Plan 목록의 잘림 여부
    truncated?: boolean;
  }>>;
};
```

### inspect_05-resolve_targets

Plan의 Scene 참조와 등록 Holon을 조회한다. Step을 지정하면 소속 Plan을 확인한다. 현재 Rhino 구성원은 별도 조회한다.

```ts
declare const tools: {
  mcp__rhino__inspect_05_resolve_targets(args: {
    connection_id: string;
    // plan_08-list tool의 request.target=plan 응답에 있는 plans[].plan_id 또는 plan_05-get tool의 plan_id
    plan_id: string;
    // references, geometry, scope, audit, all. 생략·빈 배열이면 요약.
    field_groups?: string[] | null;
    step_id?: string;
  }): Promise<JsonResult<{
    error_code?: string;
    holon_ids?: Array<unknown>;
    holons?: Array<Record<string, unknown>>;
    message?: string;
    // 변경을 검사할 때 현재 loop_no와 함께 사용
    revision?: Integer;
    scene_ids?: Array<unknown>;
    status?: string;
  }>>;
};
```

## model

### model_01-assign_material

층·구조 역할을 기록하고 재료를 ByLayer로 적용한다. applied_guids는 처리 성공, changed_guids는 실제 변경 대상이다.

```ts
declare const tools: {
  mcp__rhino__model_01_assign_material(args: {
    connection_id: string;
    // 객체 속성 UserDictionary의 Floor에 기록. 기존 User Text의 floor는 유지.
    floor: string;
    // 현재 Rhino 객체 GUID
    guids: string[];
    // model_04-list_materials tool의 materials[].material_id
    material_id: string;
    // 객체 속성 User Text의 structural_role에 기록하는 모델 분류. 해석 설정은 별도.
    structural_role: string;
    // 기본 true. 재료 레이어(기본 M::<category>::<material_id>)에 배치하며 새 레이어에만 스타일을 적용. false는 메타데이터만 기록.
    apply_render_material?: boolean;
    // 렌더 재료 적용 시 User Text에 material_id도 기록.
    attach_metadata?: boolean;
    // 생략·공백이면 키가 없는 객체에만 공백 한 칸을 기록.
    construction_detail?: string;
    // id는 구법 라이브러리의 system_id. 생략 시 키가 없는 객체에만 공백 한 칸을 기록.
    construction_reference?: { kind: "construction_system"; id: string } | null;
  }): Promise<JsonResult<{
    applied_guids?: string[];
    changed_guids?: string[];
    error_code?: string;
    layer_action?: "created" | "reused" | "not_applied";
    // 실제로 다른 레이어로 옮긴 객체 GUID. 같은 레이어에서 ByLayer만 복구했으면 제외.
    layer_changed_guids?: string[];
    // 자동 배정한 전체 레이어 경로. 메타데이터 전용 호출이면 null.
    layer_path?: string | null;
    // 렌더 재료와 함께 material_id를 기록하고 확인한 대상이 있는지 표시
    material_metadata_attached?: boolean;
    message?: string;
    mutation_state?: string;
    result_error?: string;
    rhino_material_name?: string;
    status?: string;
    warnings?: string[];
  }>>;
};
```

### model_02-edit_planar_face

일반 모델에서 닫힌 Brep의 평면 한 면을 PushPull Extend로 이동한다. 편집 후 후속 작업에 필요한 faces와 geometry_crc를 다시 조회한다.

```ts
declare const tools: {
  mcp__rhino__model_02_edit_planar_face(args: {
    connection_id: string;
    // 면 번호와 같은 관찰에서 얻은 형상 CRC. 형상이 바뀌면 객체 교체 전에 거부.
    expected_geometry_crc: Integer;
    // 같은 형상 관찰에서 얻은 평면 인덱스. 0부터 시작.
    face_index: Integer;
    // 연결 문서에서 관찰한 잠기지 않은 최상위 닫힌 Brep의 GUID
    object_id: string;
    // 문서 단위의 유한한 XYZ 값 3개. 면 법선 방향 성분의 절댓값은 문서 허용오차를 넘어야 한다.
    translation: [number, number, number];
    // 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
    expected_model_path?: string;
  }): Promise<JsonResult<{
    error_code?: string;
    message?: string;
    mutation_state?: string;
    requires_reconciliation?: boolean;
    result?: {
      edited?: boolean;
      geometry_crc?: number;
    };
    status?: string;
  }>>;
};
```

### model_03-edit_planar_faces

일반 모델에서 서로 다른 닫힌 Brep의 평면을 한 면씩 단일 Undo 기록으로 이동한다. 준비 단계에서 한 항목이라도 거부되면 객체 교체를 시작하지 않는다.

```ts
declare const tools: {
  mcp__rhino__model_03_edit_planar_faces(args: {
    connection_id: string;
    // 서로 다른 Brep 1..32개. 각 항목은 model_02-edit_planar_face tool의 입력 조건 적용.
    edits: Array<{ object_id: string; face_index: Integer; expected_geometry_crc: Integer; translation: [number, number, number] }>;
    // 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
    expected_model_path?: string;
  }): Promise<JsonResult<{
    error_code?: string;
    message?: string;
    mutation_state?: string;
    requires_reconciliation?: boolean;
    // 객체 교체 중 실패하면 일부 편집이 남을 수 있다.
    result?: {
      applied_count?: Integer;
      complete?: boolean;
      // 입력 순서의 항목별 결과. 실패 단계와 메시지 포함.
      items?: Array<{
        // 다음 면 편집 전 면 인덱스와 CRC를 다시 조회
        geometry_crc?: number;
        stage?: "prepare" | "recheck" | "replace";
        message?: string;
        status?: "applied" | "rejected" | "failed" | "unknown" | "not_attempted";
      }>;
      // not_started, applied, partial, unknown 등. partial 또는 unknown이면 전체 배치를 자동 재실행하지 않음.
      mutation_state?: string;
      status?: string;
    };
    status?: string;
  }>>;
};
```

### model_04-list_materials

라이브러리에서 이름·ID·설명·태그나 분류로 재료를 검색한다. material_id는 model_01-assign_material tool에 전달한다.

```ts
declare const tools: {
  mcp__rhino__model_04_list_materials(args: {
    connection_id: string;
    // 분류와 정확히 일치, 대소문자 구분. 생략하면 전체 분류.
    category?: string;
    // display, physical, metadata, source, paths, audit, all. 생략·빈 배열이면 요약.
    field_groups?: string[] | null;
    // 대소문자 구분 없는 부분 일치
    query?: string;
  }): Promise<JsonResult<{
    error_code?: string;
    materials?: Array<{
      category?: string;
      name?: string;
      material_id: string;
      // display
      base_color?: number[];
      metallic?: number;
      roughness?: number;
      opacity?: number;
      emission?: unknown;
      ior?: number;
      textures?: unknown;
      ue_material_slot?: string;
      // physical
      density?: number;
      density_kg_m3?: number;
      structural_material?: unknown;
      physical?: unknown;
      // metadata, source, paths, audit
      description?: string;
      tags?: string[];
      source?: unknown;
      provenance?: unknown;
      license?: unknown;
      file?: string;
      created_at?: unknown;
      updated_at?: unknown;
    }>;
    library_dir?: string;
    message?: string;
    total?: Integer;
  }>>;
};
```

## intersect

### intersect_01-find

닫힌 솔리드 사이에 양의 부피가 겹치는 쌍을 센다. assessment=incomplete이면 전체 건수는 미확정이다.

```ts
declare const tools: {
  mcp__rhino__intersect_01_find(args: {
    connection_id: string;
    // 서로 다른 최상위 Rhino 객체 GUID 1..512개
    object_ids: string[];
    // true이면 배치 변환을 적용해 중첩 블록 구성원까지 검사.
    include_block?: boolean;
  }): Promise<JsonResult<{
    assessment?: "incomplete";
    // 미판정 검사에서 확인한 문서 길이 단위
    document_units?: string | null;
    error_code?: string;
    // 미판정 쌍과 사유
    failed_pairs?: Array<Record<string, unknown>> | null;
    intersections?: {
      // 양의 부피가 겹치는 객체 쌍의 수
      number?: Integer;
    };
    message?: string;
    // 미판정 검사에서 확인한 모델 길이 공차
    tolerance_model_units?: number | null;
    // 검사할 수 없는 객체와 사유
    unsupported_objects?: Array<Record<string, unknown>> | null;
  }>>;
};
```

### intersect_02-resolve

겹치는 쌍을 비교해 선택한 객체에서 겹친 부분을 제거한다. 비교 시 실제 카메라와 선택이 바뀐다. 다음 검사에 실패하면 previous_result에서 직전 편집을 확인한다.

```ts
declare const tools: {
  mcp__rhino__intersect_02_resolve(args: {
    connection_id: string;
    // review_id와 함께 지정. 1·2는 해당 번호 객체의 겹친 부분 제거, skip은 두 객체 유지.
    choice?: 1 | 2 | "skip" | null;
    // true이면 중첩 블록 구성원도 비교. 이 도구에서 블록에 속한 쌍은 skip만 지원.
    include_block?: boolean;
    // 새 검토에만 서로 다른 최상위 객체 GUID 1..512개 지정.
    object_ids?: string[] | null;
    // choice 제출에 사용할 현재 비교 ID. 이미 처리된 ID는 재사용 불가.
    review_id?: string;
    // 새 검토의 UserDictionary 조건. 한 객체가 User Text와 UserDictionary 조건을 모두 충족해야 해당 쌍 표시.
    user_dictionary?: MetadataFilter<DictionaryTest> | null;
    // 새 검토의 객체 속성 User Text 조건. 중첩 블록은 정의 구성원 속성 기준.
    user_text?: TextTest[] | null;
  }): Promise<CallToolResult<{
    assessment?: "incomplete";
    // 미판정 검사에서 확인한 문서 길이 단위
    document_units?: string | null;
    error_code?: string;
    // 미판정 쌍과 사유
    failed_pairs?: Array<Record<string, unknown>> | null;
    message?: string;
    review_id?: string;
    image_file?: { path?: string; status?: string };
    previous_result?: { status?: "resolved" | "skipped"; edited?: boolean; trim_id?: string; keep_id?: string; geometry_crc?: Integer };
    mutation_state?: string;
    requires_reconciliation?: boolean;
    geometry_change_possible?: boolean;
    objects?: Array<{
      number?: Integer; guid?: string; member_id?: string; handle?: { object_id: string; path: string[] };
      attributes?: {
        user_strings?: {
          total_keys?: Integer;
          truncated?: boolean;
          values?: Record<string, unknown>;
        };
      };
      // 객체 속성과 형상의 UserDictionary를 구분
      user_dictionary?: Record<string, unknown>;
    }>;
    overlap?: { status?: string; volume_model_units3?: number; method?: string };
    regions?: Array<{ region_index?: Integer; bounds?: number[][]; centroid?: number[] | null; volume_model_units3?: number | null }>;
    warnings?: string[];
    skipped_pairs?: number;
    state?: "awaiting_choice" | "completed";
    status?: string;
    // 미판정 검사에서 확인한 모델 길이 공차
    tolerance_model_units?: number | null;
    // 검사할 수 없는 객체와 사유
    unsupported_objects?: Array<Record<string, unknown>> | null;
  }>>;
};
```

## research

### research_01-get_construction_guidance

구법 후보와 예비 부재 깊이 조회. `field_groups`를 생략하면 요약을 반환한다. 부재 깊이와 재료 참조는 `rules`를 요청한다.

```ts
type ResearchGroup = "rules" | "narrative" | "source" | "metadata" | "audit" | "all";

declare const tools: {
  mcp__rhino__research_01_get_construction_guidance(args: {
    connection_id: string;
    // floor, wall, roof, foundation. 기본값은 전체.
    category?: string;
    field_groups?: ResearchGroup[] | null;
    // `load_kn` 산정에 참고할 용도별 활하중(kPa)과 재료 밀도(kg/m³)를 포함.
    include_reference_data?: boolean;
    // `Wood`, `Steel`, `Concrete`. `S355`는 `Steel`로 조회.
    material?: string;
    // 예: `glulam`, `longspan`, `bearing wall`.
    query?: string;
    // 양수면 경간 적합 여부와 권장 깊이 계산. 벽 구법에는 비지지 높이.
    span_m?: number;
    // `beam`, `truss`, `shell`, `frame`, `canopy`, `gridshell`, `membrane`, `highrise`.
    structure_type?: string;
  }): Promise<JsonResult<{
    error_code?: string;
    message?: string;
    reference?: {
      live_loads_kpa: Record<string, number>;
      material_densities_kg_m3: Record<string, number>;
      egress_rules: Record<string, unknown>;
      notes: string;
    };
    source?: string;
    systems?: Array<{
      category?: string;
      depth_guidance?: Array<{
        element?: string;
        rule?: string;
        suggested_depth_mm?: number;
      }>;
      // 경험칙의 경간 범위에 해당하는지 표시. 내력은 별도 검토.
      fits_span?: boolean;
      name?: string;
      // model_01-assign_material tool에 전달할 재료 ID 후보.
      render_material_ids?: string[];
      structural_material?: string;
      // 유형 조회의 construction_system 또는 model_01-assign_material tool의 construction_reference.id로 사용.
      system_id: string;
    }>;
    total?: Integer;
  }>>;
};
```

### research_02-get_typology_narrative

건축 유형 조회. 서사·선례·관련 구법은 `field_groups: ["narrative"]`로 요청한다.

```ts
declare const tools: {
  mcp__rhino__research_02_get_typology_narrative(args: {
    connection_id: string;
    // research_01-get_construction_guidance tool의 `system_id`.
    construction_system?: string;
    field_groups?: ResearchGroup[] | null;
    // 기본값 5
    limit?: Integer;
    // 예: `courtyard`, `skyscraper`, `timber hall`.
    query?: string;
    // research_01-get_construction_guidance tool과 같은 구조 유형.
    structure_type?: string;
  }): Promise<JsonResult<{
    entries?: Array<{
      era?: string;
      name?: string;
      narrative?: string;
      precedents?: Array<{ name?: string; place?: string; date?: string }>;
      region?: string;
      // research_01-get_construction_guidance tool의 `query`로 검색 가능.
      related_construction_systems?: string[];
      typology_id: string;
      urban_role?: string;
    }>;
    error_code?: string;
    message?: string;
    source?: string;
    // `limit` 적용 전 전체 일치 수.
    total?: Integer;
  }>>;
};
```

### research_03-search_details

건축 자료 출처의 제목·태그·형식 검색. URL과 이용 조건은 `field_groups: ["all"]`로 요청한다.

```ts
declare const tools: {
  mcp__rhino__research_03_search_details(args: {
    connection_id: string;
    field_groups?: ResearchGroup[] | null;
    // 빈 문자열로 출처 목록 조회. 검색 가능한 단어가 없으면 `invalid_query`.
    query?: string;
  }): Promise<CallToolResult<{
    error_code?: string;
    message?: string;
    scope?: string;
    sources?: Array<{
      access?: string;
      formats?: string[];
      generation_use?: string;
      matched_terms?: string[];
      redistribution?: string;
      source_id: string;
      tags?: string[];
      terms_url?: string | null;
      title?: string;
      url?: string;
    }>;
    status?: string;
  }>>;
};
```

## diagram

### diagram_01-get

다이어그램의 등록 정보와 원본 유무 조회. 치수는 `dimensions`, 경로는 `paths` 그룹으로 요청한다.

```ts
type DiagramGroup = "dimensions" | "drawing" | "metadata" | "source" | "paths" | "audit" | "all";
type DiagramAsset = {
  asset_id: string;
  category?: string;
  product?: string;
  variant?: string;
  name?: string;
  file_available?: boolean;
  dimensions_mm?: { width?: number; depth?: number; height?: number };
};

declare const tools: {
  mcp__rhino__diagram_01_get(args: {
    connection_id: string;
    // diagram_02-list tool 또는 diagram_04-search tool의 ID를 그대로 사용.
    asset_id: string;
    field_groups?: DiagramGroup[] | null;
    include_ids?: boolean;
  }): Promise<JsonResult<{
    asset?: Omit<DiagramAsset, "asset_id"> & {
      // 라이브러리 기준 원본 상대 경로.
      file?: string;
      source?: Record<string, unknown>;
    };
    error_code?: string;
    message?: string;
    status?: string;
  }>>;
};
```

### diagram_02-list

등록된 2D 다이어그램 목록. asset_id는 상세 조회와 배치에 사용한다.

```ts
declare const tools: {
  mcp__rhino__diagram_02_list(args: {
    connection_id: string;
    // 분류 전체 일치, 대소문자 무시. 기본값은 전체.
    category?: string;
    field_groups?: DiagramGroup[] | null;
    // 1..50으로 보정. · 기본값 20
    limit?: Integer;
    // 다음 페이지에는 `next_offset` 사용. 기본값 0.
    offset?: Integer;
  }): Promise<JsonResult<{
    assets?: DiagramAsset[];
    error_code?: string;

    message?: string;
    next_offset?: Integer | null;
    total?: Integer;
  }>>;
};
```

### diagram_03-place

도면 라이브러리의 SVG·DWG·DXF를 Rhino 블록으로 배치한다. 결과는 `object_guid`와 `bounds`로 확인한다.

```ts
declare const tools: {
  mcp__rhino__diagram_03_place(args: {
    connection_id: string;
    // 목록·검색이 반환한 asset_id.
    asset_id: string;
    // 월드 Z축 기준 각도. 기본값 0°.
    rotation_degrees?: number;
    // 양수인 균일 축척. 기본값 1은 문서 단위로 환산한 원래 크기.
    scale?: number;
    // 삽입점 x·y·z는 Rhino 문서 단위. 기본값은 원점.
    x?: number;
    y?: number;
    z?: number;
  }): Promise<JsonResult<{
    definition_created?: boolean;
    block_definition?: string | null;
    bounds?: Bounds | null;
    error_code?: string;
    message?: string;
    // null이면 변경 적용 여부 미확인.
    mutation_applied?: boolean | null;
    // unknown·partial이면 문서에 변경이 남아 있을 수 있음.
    mutation_state?: string;
    // inspect_02-get_objects tool과 Scene 구성원 입력에 전달할 블록 GUID.
    object_guid?: string | null;
    // true이면 Rhino 문서의 실제 변경 상태를 확인. 자동 재실행 금지.
    requires_reconciliation?: boolean;
    status?: string;
  }>>;
};
```

### diagram_04-search

등록된 2D 다이어그램을 키워드·분류·최대 치수로 검색한다. asset_id는 상세 조회와 배치에 사용한다.

```ts
declare const tools: {
  mcp__rhino__diagram_04_search(args: {
    connection_id: string;
    // 분류 전체 일치, 대소문자 무시. 기본값은 전체.
    category?: string;
    field_groups?: DiagramGroup[] | null;
    // 1..50으로 보정. · 기본값 10
    limit?: Integer;
    // 등록 치수는 추정치일 수 있다. 각 한계가 0 이하면 해당 치수 필터 해제.
    max_depth_mm?: number;
    max_height_mm?: number;
    max_width_mm?: number;
    // 다음 페이지에는 같은 필터와 `next_offset` 사용. 기본값 0.
    offset?: Integer;
    // 여러 검색어는 OR로 결합. 비워 두면 키워드 조건 없이 검색.
    query?: string;
  }): Promise<JsonResult<{
    assets?: DiagramAsset[];
    error_code?: string;
    message?: string;
    next_offset?: Integer | null;
    total?: Integer;
  }>>;
};
```

## analysis

### analysis_01-list_design_codes

구조 해석의 설계기준 프로필 조회. 프로필 ID는 해석·시각화의 design_code에 전달한다.

```ts
declare const tools: {
  mcp__rhino__analysis_01_list_design_codes(args: {
    connection_id: string;
    // 기본은 요약. 수치와 조합식은 `parameters`로 요청.
    field_groups?: ("parameters" | "source" | "audit" | "all")[] | null;
  }): Promise<JsonResult<{
    default?: string;
    error_code?: string;
    message?: string;
    // 로딩 중 거절된 사용자 프로필의 문제.
    problems?: string[];
    profiles?: Array<{
      basis?: string;
      // 허용 처짐 L/n의 n.
      deflection_limit_ratio?: number;
      // 구조 해석·시각화의 `design_code`에 전달.
      id: string;
      // 용도별 권장 활하중.
      imposed_floor_kn_m2?: Record<string, number>;
      name?: string;
      uls_expression?: string;
      uls_default?: string;
      // 확인되지 않은 프로필 항목. 빈 배열이면 모든 항목을 확인했다.
      unverified: string[];
    }>;
    user_dir?: string;
  }>>;
};
```

### analysis_02-validate_structure

Rhino 구조 형상을 해석하고 설계기준을 검토한다. 실제 엔진과 적용 입력은 실행 이력에 기록한다. 엔진·경고·가정과 미검증 설계기준 값을 함께 확인한다.

```ts
type StructuralOptions = {
  // native에서 배치 자산의 자중·내용물·재실자 하중 추가. 다른 하중과 중복을 피한다.
  asset_loads?: boolean;
  // 기본 rigid. simple은 보 강축·가새 양축의 단부 휨을 해제하고 동축 부재·기둥의 연속성을 유지.
  // 곡선 User Text의 release(pinned, pinned_start, pinned_end, rigid)가 우선.
  connections?: string;
  // 기본 en1990은 선택 프로필의 SLS·ULS 조합 적용. unfactored는 양쪽에 G + Q 사용.
  design_basis?: string;
  // analysis_01-list_design_codes tool의 프로필 ID. 기본 eurocode, off는 비계수 G + Q.
  design_code?: string;
  // 기본 auto는 native 프레임 해석 우선. 셸·그리드셸·막 구조 또는 지원 불가 형상은 Karamba.
  // karamba는 api → template → rule_based 순. 실제 경로는 analysis_method와 warnings에서 확인.
  engine?: string;
  // 강재 중공 단면 제작 방식. 기본 cold_formed는 좌굴 곡선 c, hot_finished는 a(S460은 a0).
  fabrication?: string;
  // true는 완전 고정, false는 회전이 자유로운 핀 지점. · 기본값 true
  fixed_supports?: boolean;
  // 바닥 구성층·마감의 추가 고정하중. 기본값 0.
  floor_dead_kn_m2?: number;
  // native 바닥 구획의 용도별 활하중. 45° 양방향 분담, 장단변비가 2:1을 넘으면 일방향. 기본값 0.
  // 가구·재실자 하중이 중복되지 않게 asset_loads와 load_kn을 조정.
  floor_load_kn_m2?: number;
  // 전체 추가 하중. native는 자유 절점에 하향(-Z) 균등 분배. 기본 10, 바닥·자산 하중으로 충당 시 0.
  load_kn?: number;
  // "Steel", "S355", "Concrete", "Wood", "Aluminium". · 기본값 "Steel"
  material?: string;
  // 기본값 true
  self_weight?: boolean;
  // 여러 절점으로 분할한 부재의 처짐 검토용 전체 경간.
  span_m?: number | null;
  // 기본 auto는 초기 불완전성을 반영하고 alpha_cr < 10에서 2차 해석, ≤ 1이면 불안정.
  // off는 초기 불완전성을 생략하는 1차 해석.
  stability?: string;
  // 6.10 또는 6.10ab(부재별로 더 불리한 6.10a/b). 프로필 고정식이 우선하며 충돌 시 경고.
  uls_combination?: string | null;
};

declare const tools: {
  mcp__rhino__analysis_02_validate_structure(args: StructuralOptions & {
    connection_id: string;
    // 현재 Rhino 문서의 해석 대상 객체 GUID.
    guids: string[];
    // 네이티브 결과에 부재별 단면력·사용률·처짐과 지점 반력 포함.
    detail?: boolean;
    // beam(기본), truss, shell, frame, canopy, gridshell, membrane, highrise.
    structure_type?: string;
  }): Promise<JsonResult<{
    assumptions?: string[];
    confidence?: string;
    design_code?: {
      id?: string;
      unverified?: string[];
    };
    error_code?: string;
    message?: string;
    // native에서 `detail: true`일 때 부재별 단면력·처짐과 지점 반력.
    members?: { source_guids?: string[]; utilization?: number; m_max_knm?: number; v_max_kn?: number; deflection_mm?: number }[];
    supports?: { node?: Integer; position_m?: number[]; sls?: Record<string, number>; uls?: Record<string, Record<string, number>> }[];
    // indicative 해석에서는 판정이 없을 수 있음(null). 구조 안전 인증은 별도.
    passed?: boolean | null;
    results?: {
      analysis_method?: string;
      deflection_limit_mm?: number;
      max_deflection_mm?: number;
      per_element_utilization?: Array<{
        // 부재 판정을 지배한 하중 조합.
        combination?: string;
        // analysis_03-visualize_structure tool의 display_guids에 재사용.
        source_guids?: string[];
        utilization?: number;
      }>;
      span_m?: number;
      utilization_ratio?: number;
    };
    status?: string;
    warnings?: string[];
    // 사용률 상위 최대 5개. 시각화의 `display_guids`에 전달.
    worst_member_guids?: string[];
  }>>;
};
```

### analysis_03-visualize_structure

구조 해석의 임시 뷰포트 오버레이를 표시한다. `clear: true`로 제거한다.

```ts
declare const tools: {
  mcp__rhino__analysis_03_visualize_structure(args: StructuralOptions & {
    connection_id: string;
    // 원형 부재의 외경.
    beam_diameter_mm?: number | null;
    // 외경을 지정했을 때 기본 두께는 외경의 1/20.
    beam_wall_mm?: number | null;
    clear?: boolean;
    // "displacement" 또는 "utilization". · 기본값 "displacement"
    color_by?: string;
    // L/n의 n. 생략하면 설계기준 한계 사용.
    deflection_limit_ratio?: number | null;
    // 오버레이 대상 부재만 지정. 해석에는 `guids` 전체 사용.
    display_guids?: string[] | null;
    // clear일 때만 생략 가능. 축선 곡선과 지점 점 GUID. 지점 점이 없으면 최하단 절점을 사용한다.
    guids?: string[] | null;
    // false면 변형 없이 표시. 기본값 true.
    physics?: boolean;
    // false면 현재 오버레이의 해석을 재사용해 표시만 갱신. 오버레이가 없으면 오류. 기본값 true.
    reanalyze?: boolean;
    // 표시할 부재 비율 0..1. 단계별 시공 재생에 사용. · 기본값 1.0
    reveal?: number;
    // 변형 표시 배율. 생략 시 표시 변형을 경간의 약 6%로 조정.
    scale?: number | null;
    title?: string;
    // deflection은 처짐, buckling은 native 해석의 첫 ULS 조합에 대한 좌굴 모드와 alpha_cr을 표시한다.
    view?: string;
  }): Promise<JsonResult<{
    analysis_method?: string;
    buckling?: { alpha_cr: number; combination?: string };
    deflection_limit_mm?: number;
    elements?: Array<{
      max_displacement_mm?: number;
      // display_guids 또는 객체 관찰에 재사용.
      source_guids?: string[];
      utilization?: number | null;
    }>;
    error_code?: string;
    max_displacement_mm?: number;
    max_utilization?: number | null;
    message?: string;
    nodes?: Integer;
    // null이면 참고 해석 결과로 재료 내력 판정은 생략.
    passed?: boolean | null;
    // 변형을 화면에 그릴 때 적용한 과장 배율.
    scale?: number;
    span_m?: number;
    status?: string;
    warnings?: string[];
  }>>;
};
```

### analysis_04-export_structural_report

구조 검증 이력의 Markdown 보고서를 저장한다. 실제 엔진·입력과 과거 미기록 입력의 상태를 담는다. 이력이 없으면 analysis_02-validate_structure tool을 먼저 호출한다.

```ts
declare const tools: {
  mcp__rhino__analysis_04_export_structural_report(args: {
    connection_id: string;
    // 최대 500회. · 기본값 50
    limit?: Integer;
    // 관리형은 선택한 Plan 산출물 폴더 기준 상대 경로. 기본 reports/structural-validation.md.
    // 독립 실행의 기본은 사용자 데이터 아래 reports/structural-validation-<timestamp>.md.
    path?: string;
  }): Promise<JsonResult<{
    error_code?: string;
    latest_method?: string;
    message?: string;
    path?: string;
    runs?: Integer;
    status?: string;
  }>>;
};
```

### analysis_05-check_egress

직접 측정한 층 경계·출구 중심·유효 폭·경로 길이로 피난 조건을 예비 검토한다. 보행거리와 스프링클러 설치 구역의 막다른 복도는 업무용 기준을 적용하므로 `basis`·`source_note`·`warnings`를 적용 법규와 대조한다.

```ts
declare const tools: {
  mcp__rhino__analysis_05_check_egress(args: {
    connection_id: string;
    // 문 하나당 한 항목. 중심 좌표와 유효 폭을 mm로 지정.
    exits: Array<{ name?: string; x_mm: number; y_mm: number; width_mm: number }>;
    // 층 바닥 경계 [min_x, min_y, max_x, max_y].
    plate_bounds_mm: [number, number, number, number];
    // 가장 긴 막다른 복도 길이. 0이면 검사 생략. · 기본값 0.0
    dead_end_m?: number;
    // 실제 재실 면적. 생략 또는 0이면 경계의 직사각형 면적.
    net_area_m2?: number;
    // business, mercantile, assembly_unconcentrated, classroom, residential, storage. · 기본값 "business"
    occupancy?: string;
    // 전체 구역 설치 기준. · 기본값 true
    sprinklered?: boolean;
    // 출구가 담당하는 층수. 기본 1. 2층 이상은 최소 2개 출구와 계단 폭 기준 적용.
    stories?: Integer;
    // 입력 길이 중 최댓값 검사. 빈 배열이면 검사 생략. · 기본값 []
    travel_distances_m?: Array<number>;
  }): Promise<JsonResult<{
    area_m2?: number;
    checks?: Array<{
      basis?: string;
      check?: string;
      passed?: boolean;
      provided?: number;
      required?: number;
    }>;
    error_code?: string;
    // 입력 경계의 직사각형 면적.
    gross_area_m2?: number;
    message?: string;
    // 재실 면적을 용도별 1인당 면적으로 나누어 올림.
    occupant_load?: Integer;
    // 수행한 검사만의 종합 판정. 길이를 입력하지 않은 경로는 미검사.
    passed?: boolean;
    source_note?: string;
    warnings?: string[];
  }>>;
};
```

## scene

### scene_01-add_objects

Rhino 객체를 Scene에 추가하거나 해당 Scene에서 제외한 Holon 구성원을 복원
응답의 인덱스는 object_ids에서 0부터 센다.

```ts
type SceneFieldGroup = "scope" | "state" | "geometry" | "audit" | "all";
type HolonFieldGroup = "references" | "geometry" | "scope" | "audit" | "all";
type ScenePageInput = { limit?: Integer; offset?: Integer };
type ScenePage = { total?: Integer; truncated?: boolean };
type SceneRecord = { scene_id: string; name?: string; file_name?: string; units?: SceneUnits; revision?: Integer; created_at?: string; updated_at?: string };
type SceneUnits = "mm" | "cm" | "m" | "in" | "ft";
type HolonDetails = {
  // `references` 또는 `all`과 include_ids=true에서 반환.
  parent_holon_id?: string | null;
  child_holon_ids?: string[];
  scene_ids?: string[];
  rhino_group_id?: string;
  // `geometry` 또는 `all`에서 반환하는 유효 구성원의 경계.
  bounds_mm?: [number, number, number, number, number, number] | null;
  // `scope` 또는 `all`에서 반환.
  file_name?: string;
  model_path?: string;
  // `audit` 또는 `all`에서 반환.
  created_at?: string;
  updated_at?: string;
};

declare const tools: {
  mcp__rhino__scene_01_add_objects(args: {
    connection_id: string;
    // 일반 형상·클리핑 평면의 Rhino 객체 GUID, 최대 4096개.
    object_ids: string[];
    // scene_07-list tool에서 조회한 Scene ID
    scene_id: string;
    // 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
    expected_model_path?: string;
  }): Promise<JsonResult<{
    // Holon을 통해 이미 포함된 객체도 해당
    already_present_indices?: Integer[];
    error_code?: string;
    failed_indices?: Integer[];
    message?: string;
    status?: string;
  }>>;
};
```

### scene_02-create

설계 영역이나 프로그램, 상황을 나타내는 Scene 생성

```ts
declare const tools: {
  mcp__rhino__scene_02_create(args: {
    connection_id: string;
    // 빈 이름은 Untitled scene으로 저장.
    name: string;
    // context_04-get_project_info tool의 project.files에 등록된 파일명으로, 폴더 제외
    file_name?: string;
    units?: SceneUnits;  // 기본 mm
  }): Promise<JsonResult<{
    error_code?: string;
    message?: string;
    scene?: { scene_id: string; revision: Integer };
    status?: string;
  }>>;
};
```

### scene_03-focus_holons

Holon의 유효 구성원을 선택·격리·확대한다. 격리 해제는 view_change.restore_visibility_command를 쓴다. 카메라와 선택은 별도로 복원한다.

```ts
type FocusView = {
  camera_location?: [number, number, number];
  camera_target?: [number, number, number];
  frustum?: [number, number, number, number, number, number];  // left, right, bottom, top, near, far
  observation_error?: string;
  parallel_projection?: boolean;
  viewport_id?: string;
};

declare const tools: {
  mcp__rhino__scene_03_focus_holons(args: {
    connection_id: string;
    // 서로 다른 ID 1~32개. 유효 최상위 객체는 최대 4096개
    holon_ids: string[];
  }): Promise<JsonResult<{
    error_code?: string;
    // validate, select, isolate, verify_selection, zoom_selected, redraw 중 실패한 단계.
    failed_stage?: string;
    focus_observation?: {
      after_failure?: FocusView;
      before_zoom?: FocusView;
      // 문서 단위의 대상 합집합 경계.
      target_bounds?: { min: [number, number, number]; max: [number, number, number] };
      target_bounds_error?: string;
      target_count?: Integer;
      zoom_bounding_box?: boolean | null;
      zoom_extents_selected?: boolean | null;
    };
    locked_context_remains_visible?: boolean;
    message?: string;
    model_path?: string;
    // null이면 뷰 변경 적용을 확인하지 못한 상태.
    mutation_applied?: boolean | null;
    // true면 현재 Rhino 상태를 확인한 뒤 다음 작업을 결정.
    requires_reconciliation?: boolean;
    selected_ids?: string[];
    status?: string;
    view_change?: {
      display_mode_changed?: boolean | null;
      isolated?: boolean | null;
      // 격리 가시성만 복구. 카메라와 선택은 별도로 확인.
      restore_visibility_command?: string;
      selection_changed?: boolean | null;
      // selected는 기본 선택 확대, bounding_box는 기본 확대 실패 후 대상 경계로 확대한 경우.
      zoom_method?: "selected" | "bounding_box";
      // 선택 확대 또는 대체 경계 확대를 완료하면 true.
      zoom_selected?: boolean | null;
    };
    viewport_id?: string;
  }>>;
};
```

### scene_04-get

저장된 Scene과 Holon·객체 수를 조회한다. 현재 Rhino 구성원은 scene_06-get_objects tool에서 확인한다.

```ts
declare const tools: {
  mcp__rhino__scene_04_get(args: {
    connection_id: string;
    // scene_07-list tool에서 조회하거나 이전에 기록한 Scene ID
    scene_id: string;
    field_groups?: SceneFieldGroup[] | null;
  }): Promise<JsonResult<{
    error_code?: string;
    message?: string;
    scene?: Omit<SceneRecord, "scene_id" | "created_at"> & {
      direct_objects?: Integer;
      holons?: Integer;
      // 직접 등록 또는 제외 override가 있으면 저장된 정보만으로 수를 확정하기 어려워 null 반환
      objects?: Integer | null;
    };
    status?: string;
  }>>;
};
```

### scene_05-get_holon

Holon의 등록 정보와 구성원 조회. live=true로 현재 Rhino 상태를 등록 정보와 대조하고 requires_sync로 동기화 필요 여부를 확인. recursive=true는 Rhino 블록 정의 경계는 유지하며 자손 Holon을 확장. include_ids=true일 때도 입력한 holon_id는 요약에서 생략.

```ts
declare const tools: {
  mcp__rhino__scene_05_get_holon(args: {
    connection_id: string;
    // include_ids=true로 조회하거나 이전 등록 결과에서 확인한 Holon ID
    holon_id: string;
    field_groups?: HolonFieldGroup[] | null;
    // 요청한 필드 그룹에 해당하는 ID만 포함
    include_ids?: boolean;
    live?: boolean;
    recursive?: boolean;
  }): Promise<JsonResult<{
    error_code?: string;
    holon?: HolonDetails & {
      // 등록 정보와 현재 관찰 결과의 구분은 live_verified로 확인
      availability?: string;
      live_verified?: boolean;
      requires_sync?: boolean;
      name?: string;
      object_count?: Integer;
      effective_object_count?: Integer | null;
      objects?: SceneMember[];
      effective_objects?: SceneMember[];
    };
    message?: string;
    status?: string;
  }>>;
};
```

### scene_06-get_objects

현재 Rhino 문서에서 Scene의 직접 객체와 Holon 구성원 조회. Scene에서 제외한 구성원은 생략.
페이지 기본값은 limit=50, offset=0이며 limit은 1~200이다. truncated이면 같은 조건에서 반환한 항목 수만큼 offset을 늘린다.

```ts
type SceneMember = { rhino_guid?: string; holon_id?: string; name?: string; object_type?: string; bounds_mm?: [number, number, number, number, number, number] };

declare const tools: {
  mcp__rhino__scene_06_get_objects(args: ScenePageInput & {
    connection_id: string;
    // scene_07-list tool에서 조회하거나 이전에 기록한 Scene ID
    scene_id: string;
    // 지정한 경로가 연결 문서와 일치해야 함
    expected_model_path?: string;
    field_groups?: SceneFieldGroup[] | null;
    include_ids?: boolean;
  }): Promise<JsonResult<ScenePage & {
    error_code?: string;
    message?: string;
    model_path?: string;
    objects?: SceneMember[];
    status?: string;
  }>>;
};
```

### scene_07-list

공유 프로젝트 DB의 Scene 목록 조회. Scene 상세는 scene_04-get tool, 현재 Rhino 구성원은 scene_06-get_objects tool로 조회.
페이지 기본값은 limit=50, offset=0이며 limit은 1~200이다. truncated이면 같은 조건에서 반환한 항목 수만큼 offset을 늘린다.

```ts
declare const tools: {
  mcp__rhino__scene_07_list(args: ScenePageInput & {
    connection_id: string;
    field_groups?: SceneFieldGroup[] | null;
    // 확장자를 포함한 정확한 프로젝트 파일명. 생략 시 프로젝트 전체 범위에서 조회
    file_name?: string;
    // 대소문자를 구분하지 않는 부분 검색
    name?: string;
  }): Promise<JsonResult<ScenePage & {
    error_code?: string;
    message?: string;
    scenes?: SceneRecord[];
    status?: string;
  }>>;
};
```

### scene_08-list_holons

모델에서 저장된 Holon 등록 목록 조회. Scene을 지정하면 연결된 Holon을, 생략하면 기본으로 최상위 Holon을 조회. recursive=true는 자손을 포함하며 이 자손은 Scene에 직접 등록되지 않았을 수 있다. 현재 Rhino 구성원은 scene_05-get_holon tool에서 live=true로 조회.

```ts
type HolonRecord = HolonDetails & { holon_id?: string; name?: string; availability?: string; object_count?: Integer; effective_object_count?: Integer | null; requires_sync?: boolean };

declare const tools: {
  mcp__rhino__scene_08_list_holons(args: {
    connection_id: string;
    // 관리형 세션에서 생략하면 연결된 모델 기준
    expected_model_path?: string;
    field_groups?: HolonFieldGroup[] | null;
    include_ids?: boolean;
    recursive?: boolean;
    scene_id?: string;
  }): Promise<JsonResult<{
    error_code?: string;
    holons?: HolonRecord[];
    message?: string;
    status?: string;
  }>>;
};
```

### scene_09-remove_holon

Holon 등록 해제. Rhino 형상과 그룹은 보존.

```ts
declare const tools: {
  mcp__rhino__scene_09_remove_holon(args: {
    connection_id: string;
    // 이 Holon을 참조하는 부모 Holon과 Plan의 관계를 먼저 해제
    holon_id: string;
  }): Promise<JsonResult<{
    error_code?: string;

    message?: string;
    status?: string;
  }>>;
};
```

### scene_10-remove_objects

객체를 Scene에서 제외. Rhino 형상과 Holon 그룹은 보존.
응답의 인덱스는 object_ids에서 0부터 센다.

```ts
declare const tools: {
  mcp__rhino__scene_10_remove_objects(args: {
    connection_id: string;
    // 일반 형상·클리핑 평면의 Rhino 객체 GUID, 최대 4096개.
    object_ids: string[];
    // scene_07-list tool에서 조회한 Scene ID
    scene_id: string;
    // 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
    expected_model_path?: string;
  }): Promise<JsonResult<{
    already_absent_indices?: Integer[];
    error_code?: string;
    failed_indices?: Integer[];
    message?: string;
    status?: string;
  }>>;
};
```

### scene_11-sync_holon

현재 Rhino 구성원으로 Holon 등록 정보를 갱신한다. holon_ids 또는 scene_id로 대상을 선택한다. 둘 다 생략하면 연결 모델 전체를 확인한다. holon_ids는 서로 다른 ID 1~64개다. 한 Holon의 그룹 일치를 확인하려면 holon_id와 rhino_group_id를 함께 보낸다.

```ts
declare const tools: {
  mcp__rhino__scene_11_sync_holon(args: {
    connection_id: string;
    // 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
    expected_model_path?: string;
  } & (
    | { holon_ids: string[]; holon_id?: never; scene_id?: never; rhino_group_id?: never }
    | { holon_id: string; rhino_group_id?: string; holon_ids?: never; scene_id?: never }
    | { scene_id?: string; holon_ids?: never; holon_id?: never; rhino_group_id?: never }
  )): Promise<JsonResult<{
    // 등록 내용이 바뀐 항목만 계산하며 변경이 없으면 리비전 유지
    changed?: Integer;
    checked?: Integer;
    error_code?: string;
    // 모든 대상의 현재 Rhino 상태를 문제 없이 확인한 경우 true
    live_verified?: boolean;
    message?: string;
    // 문제 항목과 무관한 유효 등록은 함께 갱신될 수 있음
    problems?: Array<unknown>;
    scene_revisions?: Record<string, Integer>;
    status?: string;
    // present 이외 상태의 등록 수
    unavailable?: Integer;
  }>>;
};
```

### scene_12-update

Scene의 프로젝트 파일 연결 변경 또는 해제

```ts
declare const tools: {
  mcp__rhino__scene_12_update(args: {
    connection_id: string;
    // scene_07-list tool에서 조회하거나 이전에 기록한 Scene ID
    scene_id: string;
    // 빈 문자열은 연결 해제. 생략하거나 null이면 기존 파일 연결을 유지한다.
    file_name?: string | null;
  }): Promise<JsonResult<{
    error_code?: string;
    message?: string;
    scene?: { revision: Integer };  // 파일 연결이 바뀌면 증가
    status?: string;
  }>>;
};
```

### scene_13-upsert_holon

물리적 요소와 관계를 Holon으로 등록하거나 갱신

```ts
declare const tools: {
  mcp__rhino__scene_13_upsert_holon(args: {
    connection_id: string;
    // 기존 Rhino 그룹을 연결할 때는 그룹의 정확한 이름과 일치해야 함
    name: string;
    // 빈 배열은 기존 자식 분리, 생략은 유지. 자식당 부모 한 개만 허용하며 순환 금지
    child_holon_ids?: string[] | null;
    // 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
    expected_model_path?: string;
    // 생략하면 새 Holon 등록
    holon_id?: string;
    // 최상위 Rhino 객체만 지정 가능하며 객체당 Holon 한 개. 생략하면 name과 일치하는 기존 그룹을 사용하고 빈 배열은 child_holon_ids가 있는 부모에만 허용
    object_ids?: string[] | null;
    // 동명 Rhino 그룹을 구분할 때 사용
    rhino_group_id?: string;
    // 새 Holon은 필수. 수정 시 생략하면 기존 Scene 연결 유지
    scene_ids?: string[] | null;
  }): Promise<JsonResult<{
    error_code?: string;
    holon?: Pick<HolonRecord, "holon_id" | "rhino_group_id" | "availability" | "object_count"> & { live_verified?: boolean };
    message?: string;
    status?: string;
  }>>;
};
```

## capture

### capture_01-conditioning_pass

활성 Rhino 뷰의 카메라 경로를 따라 RGB·에지·깊이 PNG와 카메라 기록을 저장한다. 뷰가 변경되고 복원이 일부만 적용될 수 있다. 출력 폴더를 재사용하면 기존 파일을 덮어쓰거나 이전 프레임이 남을 수 있다. PNG와 대상 가시성은 파일에서 확인한다.

```ts
// inspect_03-get_document_context tool의 display_modes[].id
type DisplayModeId = string;
// path는 프로젝트 상대 경로. connection 파일은 연결 해제 때 정리된다.
type CaptureFile = { status?: "saved" | "error"; path?: string; lifetime?: "plan" | "connection"; bytes?: Integer; sha256?: string; error_code?: string; message?: string };

declare const tools: {
  mcp__rhino__capture_01_conditioning_pass(args: {
    connection_id: string;
    // 카메라 경로 JSON 문자열. 좌표는 문서 단위, lens는 mm, frames 기본 81.
    // type=orbit: center, radius, height, 선택 start_deg·end_deg·lens·target_height.
    // type=track: cam0, cam1, target0, target1, 선택 lens.
    // type=keyframes: keyframes 배열의 각 항목에 camera, target, 선택 lens.
    shot: string;
    // 기본 Rendered
    rgb_mode?: DisplayModeId;
    // 기본 Technical
    edge_mode?: DisplayModeId;
    // 청크당 프레임 수. 양의 정수 · 기본값 16
    chunk?: Integer;
    // 초당 프레임 수. 양의 정수 · 기본값 16
    fps?: Integer;
    // 양의 짝수 픽셀 · 기본값 480
    height?: Integer;
    // false이면 가까울수록 밝게 표현.
    invert_depth?: boolean;
    // 선택한 Plan의 산출물 폴더 기준 상대 경로. 기본 conditioning.
    out_dir?: string;
    // 쉼표로 구분한 rgb, edge, depth. · 기본값 "rgb,edge,depth"
    passes?: string;
    // 양의 짝수 픽셀 · 기본값 832
    width?: Integer;
  }): Promise<JsonResult<{
    // 촬영 성공 범위와 무관하게 계획한 전체 경로를 기록한 파일.
    camera_json?: string;
    document?: Record<string, unknown>;
    error_code?: string;
    // 실패 청크의 프레임 범위와 메시지. 일부 출력 파일이 남을 수 있음.
    errors?: Array<unknown>;
    // 실행 완료 응답을 받은 청크에 포함된 프레임 수.
    frames_captured?: Integer;
    frames_requested?: Integer;
    message?: string;
    // 패스별 PNG와 doc.json, camera.json, zrange.csv, summary.json 저장 위치.
    out_dir?: string;
    // executed는 전체 청크 완료. partial은 일부 청크만 완료.
    status?: "executed" | "partial" | "error";
    videos?: Partial<Record<"rgb" | "edge" | "depth", string | null>>;
  }>>;
};
```

### capture_02-inspection

작업 화면을 유지하며 여러 시점과 객체 범위를 타일 PNG로 비교한다. 범위는 문서의 표시 상태 기준이며 픽셀 가시성은 이미지에서 확인한다.

```ts
declare const tools: {
  mcp__rhino__capture_02_inspection(args: {
    connection_id: string;
    // 타일 1..16개. 타일별 범위가 비어 있으면 공통 범위 또는 문서 표시 상태를 사용.
    views: Array<{
      // 기본 current
      direction?: "current" | "top" | "bottom" | "front" | "back" | "left" | "right"
        | "iso_ne" | "iso_nw" | "iso_se" | "iso_sw" | "below_ne" | "below_nw" | "below_se" | "below_sw";
      display_mode?: DisplayModeId;
      // current에서 범위 객체에 맞게 확대. object_ids 필요.
      frame_objects?: boolean;
      label?: string; // 120자 이하
      object_ids?: string[]; // 최상위 객체 GUID 1..512개, 블록 인스턴스 제외
    }>;
    // 1..뷰 개수. 생략 시 자동 격자.
    columns?: Integer | null;
    // 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
    expected_model_path?: string;
    // 타일당 128..2048픽셀. 결합 이미지 제한도 적용. · 기본값 480
    height?: Integer;
    // 활성화 없이 사용할 모델 뷰포트 GUID. Layout·Detail에서도 지정 가능.
    model_view_id?: string;
    // 모든 타일의 최상위 객체 GUID 1..4096개, 블록 인스턴스 제외. 타일별 object_ids와 동시 지정 불가.
    object_ids?: string[] | null;
    // 타일당 128..2048픽셀. 결합 이미지 제한도 적용. · 기본값 640
    width?: Integer;
  }): Promise<CallToolResult<{
    complete?: boolean;
    error_code?: string;
    // 저장에 실패해도 PNG는 전달될 수 있다.
    image_file?: CaptureFile;
    message?: string;
    status?: string;
    // 실패한 타일도 포함.
    tiles?: Array<{
      // 성공한 타일에 실제로 적용된 모드.
      display_mode?: {
        id?: string;
        name?: string;
      };
      // 0부터 시작.
      index?: Integer;
      status?: "success" | "error";
      error_code?: string;
      message?: string;
      scope?: {
        complete?: boolean;
        eligible_count?: Integer;
        excluded_requested_ids?: string[];
      };
    }>;
  }>>;
};
```

### capture_03-current_view

현재 모델 뷰를 PNG로 캡처한다. 대상을 지정하면 실제 선택과 카메라가 바뀌며 isolate와 display_mode도 작업 화면에 적용된다. 고정 크기는 width·height와 scale_percent=100을 함께 지정한다.

```ts
type FocusCamera = {
  // 좌표와 프러스텀 경계는 문서 단위.
  camera_location?: [number, number, number];
  camera_target?: [number, number, number];
  // left, right, bottom, top, near, far
  frustum?: [number, number, number, number, number, number];
  observation_error?: string;
  parallel_projection?: boolean;
  viewport_id?: string;
};

declare const tools: {
  mcp__rhino__capture_03_current_view(args: {
    connection_id: string;
    // 레이블 확장 깊이 1..8. · 기본값 1
    depth?: Integer;
    // 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
    expected_model_path?: string;
    // 128..2048픽셀
    height?: Integer | null;
    // 이미지 크기와 픽셀 기준 토큰 추정치 포함.
    include_usage?: boolean;
    // target_ids가 필요하며 확대 전에 격리.
    isolate?: boolean;
    // 주변 객체에도 최대 200개 표시하므로 화면을 가릴 수 있다.
    labels?: boolean;
    // 1..100. · 기본값 75
    scale_percent?: Integer;
    // 선택·확대할 대상 ID를 하나 이상 지정. 생략 시 현재 구도로 캡처.
    target_ids?: string[] | null;
    // 기본 object. 다른 종류에는 target_ids 필요. block에는 배치 객체 ID 사용.
    target_kind?: "object" | "group" | "block" | "holon";
    display_mode?: DisplayModeId;
    // 128..2048픽셀
    width?: Integer | null;
  }): Promise<CallToolResult<{
    error_code?: string;
    // validate, select, isolate, verify_selection, zoom_selected, redraw 중 실패한 단계.
    failed_stage?: string;
    focus_observation?: {
      before_zoom?: FocusCamera;
      after_failure?: FocusCamera;
      // 대상 합집합 경계. 좌표는 문서 단위.
      target_bounds?: { min?: [number, number, number]; max?: [number, number, number] };
      target_bounds_error?: string;
      target_count?: Integer;
      zoom_bounding_box?: boolean | null;
      zoom_extents_selected?: boolean | null;
    };
    // 저장과 PNG 전달은 별개로 확인.
    image_file?: CaptureFile;
    message?: string;
    // null이면 뷰 변경 적용을 확인하지 못한 상태.
    mutation_applied?: boolean | null;
    // true면 현재 Rhino 상태를 확인한 뒤 다음 작업을 결정.
    requires_reconciliation?: boolean;
    status?: string;
    view_change?: {
      display_mode_changed?: boolean | null;
      // Unisolate로 가시성을 복구. 카메라와 선택은 별도로 확인.
      isolated?: boolean | null;
      selection_changed?: boolean | null;
      // bounding_box는 기본 확대 실패 후 대상 경계로 확대한 경우.
      zoom_method?: "selected" | "bounding_box";
      // 선택 확대 또는 대체 경계 확대를 완료하면 true.
      zoom_selected?: boolean | null;
    };
  }>>;
};
```

### capture_04-defined_view

Named View는 저장된 카메라로 캡처한다. Layout은 용지와 Detail의 인쇄 설정을 사용하므로 픽셀 크기·표시 모드·Detail 레이블을 생략한다.

```ts
declare const tools: {
  mcp__rhino__capture_04_defined_view(args: {
    connection_id: string;
    // 기존 이름 또는 ID. 이름은 대소문자 무시 기준으로 하나만 일치해야 한다.
    target: string;
    target_kind: "named_view" | "layout";
    display_mode?: DisplayModeId; // Named View 전용, 기본 Shaded
    // 레이블 깊이 1..8. · 기본값 1
    depth?: Integer;
    // 생략 시 현재 연결의 저장 문서 경로 사용. 지정 시 그 경로와 일치해야 한다.
    expected_model_path?: string;
    // Named View 전용 128..2048픽셀. width와 scale_percent=100을 함께 지정.
    height?: Integer | null;
    // 이미지 크기와 픽셀 기준 토큰 추정치 포함.
    include_usage?: boolean;
    // 최대 200개. 주변 레이블과 겹칠 수 있다.
    labels?: boolean;
    // 1..100 범위의 상한. 전달 용량에 맞춰 더 작아질 수 있다. · 기본값 75
    scale_percent?: Integer;
    // Named View 전용 128..2048픽셀
    width?: Integer | null;
  }): Promise<CallToolResult<{
    error_code?: string;
    image_file?: CaptureFile;
    message?: string;
    status?: string;
  }>>;
};
```

### capture_05-manipulate_view

활성 원근 모델 뷰를 회전하거나 확대한다. 결과는 capture_03-current_view tool에 대상 없이 호출해 확인한다.

```ts
declare const tools: {
  mcp__rhino__capture_05_manipulate_view(args: {
    connection_id: string;
    // look은 카메라 위치 고정. orbit은 타깃과 카메라 거리 고정.
    mode: "look" | "orbit";
    operation: "rotate";
    // 주면 현재 문서의 모델 경로와 일치해야 한다.
    expected_model_path?: string;
    // 주면 현재 활성 뷰포트 ID와 일치해야 한다.
    expected_viewport_id?: string;
    // yaw_deg 적용 후 상대 상하 회전(도). 양수는 위, 기본 0.
    pitch_deg?: number;
    // 상대 좌우 회전(도). 양수는 오른쪽, 기본 0. 두 각도 중 하나는 0이 아니어야 하며 수직 회전은 거부.
    yaw_deg?: number;
  } | {
    connection_id: string;
    // 0보다 큰 유한 배율. 2는 2배 확대, 0.5는 절반으로 축소.
    factor: number;
    operation: "zoom";
    // 주면 현재 문서의 모델 경로와 일치해야 한다.
    expected_model_path?: string;
    // 주면 현재 활성 뷰포트 ID와 일치해야 한다.
    expected_viewport_id?: string;
  }): Promise<CallToolResult<{
    status: "success" | "error";
    camera_location?: [number, number, number];
    camera_target?: [number, number, number];
    error_code?: string;
    mutation_applied?: boolean | null;
    requires_reconciliation?: boolean;
    viewport_id?: string;
  }>>;
};
```

## grasshopper

### grasshopper_01-get_logic

색인된 로직의 물리 컴포넌트·설명·메타데이터 조회. JSON 단독 항목은 메타데이터를 반환한다. 연결 관계와 실행 가능성은 별도 확인한다.

```ts
type GrasshopperGroup = "ports" | "definition" | "source" | "paths" | "audit" | "all";

declare const tools: {
  mcp__rhino__grasshopper_01_get_logic(args: {
    connection_id: string;
    // grasshopper_03-list_library tool의 `logic_names`에서 선택.
    logic_id: string;
    field_groups?: GrasshopperGroup[] | null;
    include_ids?: boolean;
  }): Promise<JsonResult<{
    all_descriptions?: string[];
    components?: Array<{
      category?: string;
      descriptions?: string[];
      name?: string;
    }>;
    // 로직 미등록 시 grasshopper_03-list_library tool로 이름 조회.
    error?: string;
    error_code?: string;
    file_name?: string;
    source?: string;
    message?: string;
    metadata?: Record<string, unknown>;
  }>>;
};
```

### grasshopper_02-list_capsules

등록 캡슐의 기능과 실행 감사 상태를 최대 50개 조회한다. capsule_id로 실행한다. 포트 이름과 타입은 `field_groups: ["ports"]`로 확인한다. 정의 파일의 존재와 실행 결과는 별도 확인한다.

```ts
type CapsulePort = {
  name?: string;
  // [] 접미사는 배열.
  type?: string;
  units?: string;
  description?: string;
};

declare const tools: {
  mcp__rhino__grasshopper_02_list_capsules(args: {
    connection_id: string;
    audited_only?: boolean;
    // analyze, generate, form_find, aggregate. 대소문자 구분 없음.
    capability?: string;
    field_groups?: GrasshopperGroup[] | null;
  }): Promise<JsonResult<{
    capsules?: Array<{
      audited?: boolean;
      capability?: string;
      // `audited: true`인 ID를 grasshopper_04-run_definition tool에 전달.
      capsule_id: string;
      definition_file?: string;
      // 포트 이름은 실행의 `inputs`·`outputs` 키. 입력은 `required: false`일 때만 선택.
      input_ports?: (CapsulePort & { required?: boolean })[];
      output_ports?: CapsulePort[];
      structure_type?: string | null;
      title?: string;
    }>;
    error_code?: string;
    message?: string;
    total?: Integer;
  }>>;
};
```

### grasshopper_03-list_library

색인된 로직 이름 목록. `logic_names`를 grasshopper_01-get_logic tool에 전달한다.

```ts
declare const tools: {
  mcp__rhino__grasshopper_03_list_library(args: {
    connection_id: string;
    // `paths` 또는 `all`로 라이브러리 경로 포함.
    field_groups?: GrasshopperGroup[] | null;
  }): Promise<JsonResult<{
    error_code?: string;
    library_dir?: string;
    logic_names?: string[];
    message?: string;
    total_entries?: Integer;
  }>>;
};
```

### grasshopper_04-run_definition

실행 감사를 통과한 캡슐을 Rhino에서 계산한다. 출력 포트를 확인한 뒤 정의에 따라 하나의 Undo 기록으로 형상을 베이크한다.

```ts
declare const tools: {
  mcp__rhino__grasshopper_04_run_definition(args: {
    connection_id: string;
    // grasshopper_02-list_capsules tool의 감사 통과 ID.
    capsule_id: string;
    // `ALMOND_IN_` 포트 이름과 `input_ports`의 타입·단위·필수 조건을 사용한다.
    inputs: Record<string, number | string | boolean | number[] | string[] | { guids: string[] }>;
    // 확률적 정의에만 정수 시드 사용
    seed?: Integer | null;
    // 솔버 시간 한도(초). 0 초과, 600 이하. · 기본값 60.0
    timeout_s?: number;
  }): Promise<JsonResult<{
    analysis_method?: string;
    // 미등록 ID 요청 시 반환. 감사 상태는 목록에서 확인.
    available_capsules?: string[];
    baked_guids?: string[];
    // 매니페스트 선언 기준: api/high, template/medium, rule_based/low
    confidence?: string;
    error?: unknown;
    error_code?: string;
    message?: string;
    // `unknown`이면 문서에 변경이 남을 수 있음.
    mutation_state?: "none" | "completed" | "rolled_back" | "unknown";
    // 값의 의미·타입·단위는 캡슐 포트 계약을 따름
    outputs?: Record<string, unknown>;
    // true 또는 응답 유실 시 `baked_guids`와 실제 문서 확인 후 재시도 판단.
    requires_reconciliation?: boolean;
    status?: string;
    // 입력 검증 실패 시 유효한 입력 포트 이름.
    valid_inputs?: string[];
    warnings?: string[];
  }>>;
};
```

## drawing

### drawing_01-apply_style

수동 2D 작도에 사용할 표준 D 레이어와 속성을 적용한다. 작도 전에 용도에 맞는 layer_path를 선택하고, 반환된 레이어에서 객체의 선종을 ByLayer로 사용한다. D::PlanSection은 별도다. 다른 레시피를 지정한 경우에는 layer_path를 생략한다. print_display_review가 있으면 현재 연결과 일치하는 RhinoCode에서 Document 범위의 Model·Layout 인쇄 표시를 확인하고 필요할 때 macro를 실행한다.

```ts
declare const tools: {
  mcp__rhino__drawing_01_apply_style(args: {
    connection_id: string;
    layer_path?: "D::Section" | "D::Elev" | "D::Line" | "D::Line::Hidden" | "D::Line::Axis" | "D::Dim" | "D::Annotation" | "D::Note" | "D::Symbol" | "D::Hatch";
    // true로 표준 D 기존 정의 덮어쓰기. 생략하면 표준 D는 보존하고 다른 레이어는 덮어쓴다.
    overwrite?: boolean;
    recipe_id?: string;  // 기본 standard_d
  }): Promise<JsonResult<{
    error_code?: string;
    layers?: Array<{
      linetype?: string;
      // inspect_02-get_objects tool의 filters.layer.include에 재사용 가능.
      path?: string;
      plot_weight_mm?: number;
      role?: string;
    }>;
    message?: string;
    // unknown·partial이면 문서에 변경이 남아 있을 수 있음.
    mutation_state?: string;
    // true이면 Rhino 문서의 실제 변경 상태를 확인. 자동 재실행 금지.
    requires_reconciliation?: boolean;
    print_display_review?: { macro: string };  // 연결 모델의 Document PrintDisplay 확인이 필요할 때 반환
    status?: string;
  }>>;
};
```

### drawing_02-get_recipe

도면 스타일 레시피 조회. field_groups=["scales","parameters"]로 권장 축척·레이어·출력 설정을 확인한 뒤 같은 recipe_id를 drawing_01-apply_style tool에 전달한다.

```ts
type RecipeFieldGroup = "scales" | "parameters" | "source" | "audit" | "all";
type RecipeSummary = { name?: string | null; description?: string | null; recommended_scales?: string[] };
type RecipeFields = {
  scales?: unknown;
  layers?: Record<string, unknown>[];
  output?: Record<string, unknown>;
  linework?: unknown; hatches?: unknown; style?: unknown; parameters?: unknown;
  views?: unknown; layout?: unknown; annotations?: unknown; display?: unknown; units?: unknown;
  review_preparation?: unknown;
  source?: unknown; references?: unknown; license?: unknown;
  created_at?: unknown; updated_at?: unknown;
};

declare const tools: {
  mcp__rhino__drawing_02_get_recipe(args: {
    connection_id: string;
    // 이미 확인한 레시피 ID 또는 drawing_05-list_recipes tool의 recipe_id.
    recipe_id: string;
    field_groups?: RecipeFieldGroup[];
  }): Promise<JsonResult<{
    error_code?: string;
    message?: string;
    recipe?: RecipeSummary & RecipeFields & {
      projection?: { type?: string } & Record<string, unknown>;
    };
    status?: string;
  }>>;
};
```

### drawing_04-import_hatches

등록된 PAT의 패턴 정의를 가져오고 이름 목록을 반환한다. 같은 이름이 이미 있으면 기존 정의를 재사용한다.

```ts
declare const tools: {
  mcp__rhino__drawing_04_import_hatches(args: {
    connection_id: string;
    asset_id: string;
  }): Promise<JsonResult<{
    error_code?: string;
    message?: string;
    patterns?: string[];
    status?: string;
  }>>;
};
```

### drawing_05-list_recipes

로드된 도면 스타일 레시피 목록. recipe_id는 drawing_02-get_recipe tool과 drawing_01-apply_style tool에서 사용.

```ts
declare const tools: {
  mcp__rhino__drawing_05_list_recipes(args: {
    connection_id: string;
    field_groups?: RecipeFieldGroup[];
  }): Promise<JsonResult<{
    error_code?: string;
    message?: string;
    recipes?: (RecipeSummary & RecipeFields & { recipe_id: string; projection?: string | null })[];
  }>>;
};
```

### drawing_06-generate_plan_section

클리핑 평면에서 도면을 생성·갱신·이동한다. Update는 기존 위치와 저장된 첨부 형상 설정을 사용한다. Create의 기본 범위는 활성 모델이다. include_attachments로 범위를 바꿀 수 있다. Move는 원점만 바꾼다. points는 클리핑 GUID별 문서 단위 절대 좌표다. 일부 클리핑만 끝날 수 있으므로 cuts와 unconfirmed_clipping_ids를 확인한다. Move에서는 모든 클리핑의 새 원점을 지정한다.

```ts
type DrawingRecovery = {
  attempts?: Array<{ target?: string; action?: string; error?: string; status?: string }>;
  mutation_state?: string; requires_reconciliation?: boolean; tracked_changes_restored?: boolean;
};

type DrawingPoint = [number, number] | [number, number, number];
type PlanSectionStyle = {
  near_width?: number;  // 기본 0.09 mm
  far_width?: number;   // 기본 0.04 mm, near_width 이하
  near_dark?: number;   // 기본 80%
  far_dark?: number;    // 기본 45%, near_dark 이하
  hatch?: boolean;     // 기본 true, 원본 채움·형상에 따라 생성
  small_details?: boolean;
  section_width_source?: "source" | "output_layer";  // 기본 source, 원본 또는 D::PlanSection::Section 선폭
};

declare const tools: {
  mcp__rhino__drawing_06_generate_plan_section(args: {
    connection_id: string;
    // 활성 모델 또는 Worksession 첨부 파일의 클리핑 평면 GUID. 최소 1개, 중복은 한 번만 처리.
    clipping_ids: string[];
  } & (
    | { operation: "Create"; points?: Record<string, DrawingPoint>; include_attachments?: boolean } & PlanSectionStyle
    | { operation: "Update"; points?: never; include_attachments?: boolean } & PlanSectionStyle
    | { operation: "Move"; points: Record<string, DrawingPoint>; include_attachments?: never }
  )): Promise<JsonResult<{
    error_code?: string;
    message?: string;
    mutation_state?: string;
    requires_reconciliation?: boolean;
    completed?: Integer;
    requested?: Integer;  // 중복을 제외한 클리핑 수
    stop_reason?: "deadline" | "user";
    cuts?: {
      cleanup_error?: string;
      clipping_id?: string;
      // 원점과 축으로 표현한 실제 배치 평면
      draw_plane?: { origin: [number, number, number]; xaxis: [number, number, number]; yaxis: [number, number, number] };
      error?: string;
      // Create·Update에서 실제 계산에 사용한 추출 조건
      extraction?: {
        // Worksession 첨부 형상을 계산 범위에 허용했는지 표시
        include_attachments?: boolean;
        include_hidden?: boolean;
        include_locked?: boolean;
        // 계산에 사용한 원본 레이어 전체 경로
        layers?: string[];
        source_object_count?: Integer;
      };
      // 변경 후 최종 결과 미확인 시 unknown
      mutation_state?: string;
      name?: string | null;
      // 생성·갱신·이동에서 관찰한 객체 GUID. unconfirmed이면 최종 문서에 남았는지 대조 필요
      object_ids?: string[];
      // 추적한 변경에 대한 보상 결과. 성공해도 원자적 롤백은 보장되지 않음.
      recovery?: DrawingRecovery;
      // 계산 단계와 제외·정리한 형상에 대한 기록
      report?: Record<string, unknown>;
      status?: "completed" | "failed" | "skipped" | "cancelled" | "not_started" | "unconfirmed";
    }[];
    // timeout은 120초 취소 요청 뒤 중단·정리가 확인된 경우.
    status?: "success" | "partial" | "cancelled" | "timeout" | "error";
    // 최종 변경 상태를 확인할 수 없는 클리핑 GUID
    unconfirmed_clipping_ids?: string[];
  }>>;
};
```

## asset

### asset_01-audit_drawing

저장된 도면 패키지의 SVG·DXF를 파일 해시 목록과 대조. 빈 해시 목록, 누락·변경 파일, 패키지 외부 경로, 파일시스템 링크는 오류. 원본을 찾으면 원본 변경도 검사.

```ts
type AssetFieldGroup = "dimensions" | "source" | "paths" | "drawing" | "metadata" | "audit" | "all";
type AssetPage = { total?: Integer; next_offset?: Integer | null };

declare const tools: {
  mcp__rhino__asset_01_audit_drawing(args: {
    connection_id: string;
    // 도면 생성·조회 응답의 package_dir 사용. 관리형은 프로젝트와 설정된 도면 라이브러리·drawing-runs의 패키지, 독립 실행은 절대 경로.
    package_dir: string;
    // 원본이 바뀌었는지 비교할 GLB. 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로. 라이브러리에서 원본을 찾을 수 있으면 생략 가능.
    source_glb?: string;
  }): Promise<CallToolResult<{
    // 파일 해시 검사 건수. 시각 검토는 별도.
    checked_files?: Integer;
    error_code?: string;
    failures?: Array<unknown>;
    message?: string;
    // not_checked이면 파일만 검사했다.
    source_geometry?: "current" | "source_file_current" | "stale" | "not_checked";
    status?: string;
  }>>;
};
```

### asset_02-generate_drawing_views

등록 3DM 또는 삼각형 GLB(정적·비압축, 최대 100 MB·250,000 삼각형)에서 평면·정면·우측면 실루엣을 생성한다. GLB 경로는 관리형에서 프로젝트 상대 경로, 독립 실행에서 절대 경로다. 기본 위쪽 축은 y이고 (X, -Z, Y)로 변환한다. 실물 크기 mm DXF와 축척 SVG를 출력. 세 뷰가 A3에 들어가면 시트 SVG도 생성하며, 시트 없이도 성공 가능.

정면은 좌표계 기준. 실루엣에 단면·내부 가시선·은선은 없으며 축척별 단순화로 작은 윤곽이 달라질 수 있음. 결과는 별도 drawing-runs에 저장하고 등록 자산의 도면은 갱신하지 않음.

```ts
type DrawingSourceReference = {
  source_id: string; title: string; url: string; publisher: string; locator: string;
  accessed_on: string; used_for: string; terms_url: string;
  relationship: "background_reading" | "dimensional_reference" | "assembly_reference" | "post_generation_reference";
};

declare const tools: {
  mcp__rhino__asset_02_generate_drawing_views(args: {
    connection_id: string;
    scales?: Integer[];  // 서로 다른 5~1000 범위의 분모 1~4개. 기본 [50, 100].
    source_references?: DrawingSourceReference[];
  } & (
    | { asset_id: string; source_glb?: never; input_units?: never; up_axis?: never }
    | { asset_id?: never; source_glb: string; input_units: "mm" | "m"; up_axis?: "y" | "z" }
  )): Promise<CallToolResult<{
    error_code?: string;
    manifest?: Record<string, unknown>;
    message?: string;
    // asset_01-audit_drawing tool의 package_dir에 그대로 전달. 관리형은 프로젝트 상대 경로이며 다른 드라이브의 라이브러리는 절대 경로 유지.
    package_dir?: string;
    status?: string;
  }>>;
};
```

### asset_03-get_drawings

등록 자산의 저장 도면 패키지 조회. 도면은 배치 인스턴스 변환을 적용하지 않은 자산 원본 형상의 투영. manifest에서 파일·축척·치수·출처·투영 한계를 확인.

```ts
declare const tools: {
  mcp__rhino__asset_03_get_drawings(args: {
    connection_id: string;
    // 목록·검색이 반환한 asset_id.
    asset_id: string;
  }): Promise<CallToolResult<{
    error_code?: string;
    manifest?: Record<string, unknown>;
    message?: string;
    // asset_01-audit_drawing tool에 전달.
    package_dir?: string;
    plan_svg_uri?: string;
    status?: string;
  }>>;
};
```

### asset_04-get

모델·2D 자산의 등록 정보와 사용 가능 상태 조회. field_groups에 paths를 지정하면 원본·모델 경로를 확인.

```ts
type ModelAsset = {
  asset_id: string; product?: string; category?: string; variant?: string;
  source_available?: boolean; file_available?: boolean; source_only?: boolean;
  model_status?: string; drawing_status?: string;
  source_path?: string; model_path?: string;
  next_tool?: string;  // 변환이나 갱신이 필요할 때 호출할 도구.
  dimensions_mm?: Record<string, number>; spatial?: Record<string, unknown>;
};

declare const tools: {
  mcp__rhino__asset_04_get(args: {
    connection_id: string;
    // 목록·검색이 반환한 asset_id.
    asset_id: string;
    field_groups?: AssetFieldGroup[];
  }): Promise<JsonResult<{
    asset?: Omit<ModelAsset, "asset_id">;
    error_code?: string;
    message?: string;
    status?: string;
  }>>;
};
```

### asset_05-list

모델·2D 자산 목록과 배치 준비 상태 조회. asset_id는 상세 조회와 배치에 사용한다.
next_offset이 있으면 같은 조건으로 다음 페이지를 조회한다.

```ts
declare const tools: {
  mcp__rhino__asset_05_list(args: {
    connection_id: string;
    // 빈 값은 전체 분류.
    category?: string;
    field_groups?: AssetFieldGroup[];
    // 기본값 20
    limit?: Integer;
    // 페이지의 시작 위치(0부터). · 기본값 0
    offset?: Integer;
  }): Promise<JsonResult<AssetPage & {
    assets?: ModelAsset[];
    error_code?: string;
    message?: string;
  }>>;
};
```

### asset_06-place

모델·2D 자산을 Rhino 문서에 블록으로 배치. 3DM은 원본에 연결되며 정의를 갱신하면 같은 정의를 사용하는 기존 배치에 반영.

```ts
declare const tools: {
  mcp__rhino__asset_06_place(args: {
    connection_id: string;
    // 목록·검색이 반환한 asset_id.
    asset_id: string;
    // 월드 Z축 기준. · 기본값 0
    rotation_degrees?: number;
    // 균일 배치 축척(0 초과 100 이하). · 기본값 1
    scale?: number;
    // 원본 기준점의 월드 좌표(문서 단위). · 기본값 0
    x?: number;
    // 원본 기준점의 월드 좌표(문서 단위). · 기본값 0
    y?: number;
    // 원본 기준점의 월드 좌표(문서 단위). · 기본값 0
    z?: number;
  }): Promise<JsonResult<{
    definition_created?: boolean;
    definition_refreshed?: boolean;
    affected_existing_instances?: Integer;
    error_code?: string;
    message?: string;
    // null이면 변경 적용 여부 미확인.
    mutation_applied?: boolean | null;
    // unknown·partial이면 문서에 변경이 남아 있을 수 있음.
    mutation_state?: string;
    // 삽입한 최상위 블록 GUID. inspect_02-get_objects tool 또는 Scene 구성원 입력에 재사용.
    object_guid?: string;
    // 3DM 변환이 필요한 원본의 준비 도구.
    next_tool?: "asset_07-prepare";
    // true이면 Rhino 문서의 실제 변경 상태를 확인. 자동 재실행 금지.
    requires_reconciliation?: boolean;
    status?: string;
  }>>;
};
```

### asset_07-prepare

inspect는 원본을 보존하고 미리보기를 만든다. 3DM은 내장 단위를 쓰고 다른 형식은 입력 단위를 지정한다. 새 normalize에는 검토를 제출한다. 이미 끝난 단계는 같은 job_dir로 조회할 수 있다. 첫 verify에서 받은 최종 이미지와 해시를 확인한 뒤 같은 job_dir로 검토를 제출한다. ready면 source_3dm과 job_dir를 등록에 사용한다. status는 저장된 근거만 읽는다. 관리형 경로는 프로젝트 상대 경로, 독립 실행에서는 절대 경로다.

```ts
type PrepareFieldGroup = "summary" | "parts" | "previews" | "provenance" | "all";
type NormalizeReview = {
  vision_reviewed: true;
  inspected_sha256: string;
  rotation_degrees_xyz?: [number, number, number];
  translation?: [number, number, number];  // 원본 단위
  remove?: { object_id: string; reason: string }[];
};
type FinalAssetReview = { vision_reviewed: true; final_sha256: string; name: string; asset_id: string };

declare const tools: {
  mcp__rhino__asset_07_prepare(args: {
    connection_id: string;
    // 생략 시 미리보기 포함, []는 요약. limit·offset은 parts에만 적용.
    field_groups?: PrepareFieldGroup[];
    include_ids?: boolean;
    limit?: Integer;  // 1~200, 기본 50
    offset?: Integer;
  } & (
    | { stage: "inspect"; source_file: string; input_units?: "mm" | "cm" | "m" | "in" | "ft"; job_dir?: never; review?: never }
    | { stage: "normalize"; job_dir: string; review?: NormalizeReview; source_file?: never; input_units?: never }
    | { stage: "verify"; job_dir: string; review?: FinalAssetReview; source_file?: never; input_units?: never }
    | { stage: "status"; job_dir: string; review?: never; source_file?: never; input_units?: never }
  )): Promise<CallToolResult<AssetPage & {
    error_code?: string;
    // 이후 단계에 전달. asset_09-register tool에는 preparation_job으로 전달.
    job_dir?: string;
    message?: string;
    // verified 상태에서 verify를 호출할 때는 최종 이미지 검토를 제출. ready면 source_3dm으로 등록.
    next_stage?: "verify" | null;
    previews?: string[];
    provenance?: Record<string, unknown>;
    review_targets?: { inspected_sha256?: string; normalized_sha256?: string; final_sha256?: string };
    summary?: { units?: string; dimensions_mm?: Record<string, number>; object_count?: Integer; limitations?: string[] };
    parts?: Array<Record<string, unknown>>;
    // 검토를 마친 최종 3DM. 검토한 name·asset_id와 함께 asset_09-register tool에 전달.
    source_3dm?: string;
    // ready는 해당 해시의 이미지 검토가 기록됐다는 뜻이다.
    state?: "new" | "running" | "inspected" | "normalized" | "verified" | "ready" | "failed" | "unconfirmed";
    // passed는 단계 검사 통과. 등록에는 state가 ready일 때의 source_3dm을 쓴다.
    status?: "pending" | "passed" | "error";
    requires_reconciliation?: boolean;
  }>>;
};
```

### asset_08-refresh

편집·저장한 등록 3DM을 다시 측정해 평면·입면 도면을 새 리비전으로 발행. 원본 경로와 이전 도면은 보존. 내부 가시선·은선·레이어 표시는 생성 범위에서 제외.

열린 Rhino 문서의 연결 블록 갱신·저장은 별도. 공유 정의를 갱신하면 기존 인스턴스에 반영되며 배치 당시 메타데이터는 유지.

```ts
declare const tools: {
  mcp__rhino__asset_08_refresh(args: {
    connection_id: string;
    asset_id: string;
  }): Promise<CallToolResult<{
    error_code?: string;
    // 게시됐지만 인덱스 갱신에 실패하면 false. 다시 게시하지 말고 재연결한다.
    live_index_refreshed?: boolean;
    message?: string;
    model_path?: string;
    package_dir?: string;
    // 변경이 미확정이면 모델과 라이브러리를 확인한 뒤 재시도한다.
    requires_reconciliation?: boolean;
    registration_applied?: boolean | null;
    status?: string;
  }>>;
};
```

### asset_09-register

검토한 3DM을 모델 라이브러리에 등록하고 치수·평면·입면 실루엣 도면을 생성. 내부 가시선·은선·레이어 표시는 생성 범위에서 제외. 준비를 마쳤어도 파생 메시가 250,000 삼각형을 넘으면 등록 실패. 등록 결과는 asset_04-get tool에서 확인.

```ts
declare const tools: {
  mcp__rhino__asset_09_register(args: {
    connection_id: string;
    // preparation_job을 지정하면 준비 단계에서 검토한 ID와 일치해야 함.
    asset_id: string;
    // preparation_job을 지정하면 준비 단계에서 검토한 이름과 일치해야 함.
    name: string;
    // 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로. preparation_job을 지정하면 준비 단계 응답의 source_3dm 사용.
    source_3dm: string;
    // 기본값 "other"
    category?: string;
    description?: string;
    // 완료한 준비 작업의 job_dir. 검토를 거친 다중 형식 변환 등록에 필수. 관리형은 프로젝트 상대 경로, 독립 실행은 절대 경로.
    preparation_job?: string;
    // true일 때만 같은 ID의 기존 자산 교체.
    replace_existing?: boolean;
    source_url?: string;
    tags?: string[] | null;
  }): Promise<CallToolResult<{
    error_code?: string;
    // 기존 원본을 교체하면 해당 원본에 연결된 인스턴스에 영향 가능.
    linked_instances_may_update?: boolean;
    // 게시됐지만 인덱스 갱신에 실패하면 false. 다시 게시하지 말고 재연결한다.
    live_index_refreshed?: boolean;
    message?: string;
    model_path?: string;
    // DXF와 치수는 mm 단위.
    package_dir?: string;
    // 교체 전 원본·도면·매니페스트 백업 보존 여부.
    previous_files_retained?: boolean;
    previous_source_sha256?: string | null;
    // 게시 결과가 불명확하면 null과 requires_reconciliation 반환. 상태 확인 없이 재시도 금지.
    requires_reconciliation?: boolean;
    registration_applied?: boolean | null;
    status?: string;
  }>>;
};
```

### asset_10-search_repository

모델·2D 요소 아카이브 검색. 후보가 limit에서 잘리면 검색어나 유형을 좁혀 다시 조회. 원본만 있는 자산은 변환이 필요할 수 있으며 asset_id를 asset_04-get tool에 전달해 상세 정보·경로를 조회한다.

```ts
declare const tools: {
  mcp__rhino__asset_10_search_repository(args: {
    connection_id: string;
    drawing_ready?: boolean;
    field_groups?: AssetFieldGroup[];
    // all, element, model. · 기본값 "all"
    kind?: "all" | "model" | "element";
    // 1..100으로 보정. · 기본값 20
    limit?: Integer;
    // 이름·ID·분류·variant·재료 ID·태그·역할에서 대소문자 구분 없이 공백으로 나눈 모든 단어 검색.
    query?: string;
  }): Promise<CallToolResult<{
    assets?: (Pick<ModelAsset, "model_status" | "drawing_status" | "source_only" | "source_available" | "dimensions_mm"> & { asset_id: string; name?: string; kind?: "model" | "element"; available?: boolean; drawing_ready?: boolean })[];
    error_code?: string;
    message?: string;
    // limit 적용 전 전체 일치 건수. 다음 페이지 없음.
    total?: Integer;
  }>>;
};
```

### asset_11-search

모델·2D 자산을 검색어·분류·최대 치수로 검색. 단어가 하나라도 일치하면 포함하고 일치 단어가 많은 순으로 반환. 치수 필터는 등록 치수를 비교하며 해당 치수가 없는 자산도 포함할 수 있음. asset_id를 asset_04-get tool에 전달해 상세 조회.
next_offset이 있으면 같은 조건으로 다음 페이지를 조회한다.

```ts
declare const tools: {
  mcp__rhino__asset_11_search(args: {
    connection_id: string;
    // 대소문자를 구분하지 않는 정확 일치. 빈 값은 전체 분류.
    category?: string;
    field_groups?: AssetFieldGroup[];
    // 페이지당 1~100개. · 기본값 10
    limit?: Integer;
    // 양수일 때만 필터 적용. · 기본값 0
    max_depth_mm?: number;
    // 양수일 때만 필터 적용. · 기본값 0
    max_height_mm?: number;
    // 양수일 때만 필터 적용. · 기본값 0
    max_width_mm?: number;
    // 페이지의 시작 위치(0부터). · 기본값 0
    offset?: Integer;
    // 이름·설명·제품·분류·태그 등에서 대소문자 구분 없이 부분 일치 검색.
    query?: string;
  }): Promise<JsonResult<AssetPage & {
    assets?: ModelAsset[];
    error_code?: string;
    message?: string;
  }>>;
};
```
