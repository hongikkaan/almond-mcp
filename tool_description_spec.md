# Almond MCP 도구 설명·입출력 예시

## Prefix 명명

공개 호출명은 `<category>_<NN>-<name>` 형식입니다. 예: `connect_01-list_up`, `connect_02-session`. 제목과 `기준 API`는 실제 tools/list·tools/call 이름이며 기존 이름의 별칭은 제공하지 않습니다. 원문의 식별 번호를 유지하므로 제거된 도구의 번호는 비어 있습니다. 설명에서 등록된 도구는 `<공개 도구명> tool`로 표기합니다.

| Group | Prefix | 기존 묶음 |
| --- | --- | --- |
| Connect | connect_NN- | 연결·세션 관리 |
| Context | context_NN- | 기본 가이드·프로젝트 정보·운영 정책 |
| Plan | plan_NN- | 작업 계획·단계·산출물 관리 |
| Inspect | inspect_NN- | Rhino 문서·객체·선택 조회 |
| Capture | capture_NN- | 화면 캡처·시각 검토 |
| Model | model_NN- | 모델링 설정·재료·형상 편집 |
| Script | script_NN- | 스크립트 실행·결과 확인·저장 |
| Scene | scene_NN- | Scene·Holon 의미 구조 관리 |
| Intersect | intersect_NN- | 교차·겹침 검토와 해결 |
| Asset | asset_NN- | 모델·도면 자산 검색·준비·배치 |
| Diagram | diagram_NN- | 다이어그램 자산 검색·배치 |
| Drawing | drawing_NN- | 도면 스타일·해치·평면 및 단면 생성 |
| Grasshopper | grasshopper_NN- | Grasshopper 로직·캡슐 조회와 실행 |
| Research | research_NN- | 구법·건축 유형·참고자료 조사 |
| Analysis | analysis_NN- | 구조·피난 검토와 보고서 |
| Exchange | exchange_NN- | 앱 간 자산 교환·Chestnut 게시 |

# 설명

## 문서 기준

- 이 문서는 beyond·CoS 외부 연결 경로의 공개 도구 **86개**(공통 81개 + 연결 관리 5개)를 다룹니다. `tools/list`의 도구명·DESCRIPTION·inputSchema와 대조합니다. 독립 Python 서버는 실행기 도구 없이 75개를 공개합니다.
- 출력 타입·필드 설명은 [공개 출력 계약](src/mcp/output_contracts.py)에 있으며 실제 `tools/list`의 outputSchema로 노출됩니다. 각 항목의 `근거`는 반환 구현을 확인할 소스입니다.
- DESCRIPTION은 도구를 선택할 때 필요한 역할과 핵심 조건을 설명합니다. 계획 CRUD 네 도구는 단일 request 안의 target으로 대상을 선택합니다. create는 phase/plan, get/list/update는 phase/plan/step을 지원하며 Step은 Plan 생성 시 템플릿에서 자동 생성합니다.
- TOOL INPUT은 실제 공개 schema입니다. 변수명·타입·선택지·입력 설명을 확인합니다.
- TOOL OUTPUT은 현재 반환 구현에 따른 예시이며 Rhino 실측 응답이 아닙니다. 별도 표시가 없으면 일부 필드를 발췌했습니다. 이름·ID·수치·경로는 예시 값이며 `…`는 문서상 생략입니다. 고정 안내문은 서버 원문을 사용하고, `//` 뒤의 한국어 설명은 응답에 없는 문서용 주석입니다.
- 예시는 도구 결과의 JSON 본문을 보여 줍니다. JSON 문자열을 반환하는 도구는 outputSchema의 properties.result.contentSchema가 그 본문을 설명합니다. 객체를 직접 반환하는 도구는 outputSchema 자체를 따르며, 이미지 도구는 MCP 이미지 콘텐츠도 함께 반환할 수 있습니다.
- next_step_guide는 현재 결과에서 필요한 후속 작업이 있을 때 반환하는 문자열입니다. 빈 목록·오류·부분 적용·과거 기록·실행 대기에 따라 안내가 달라집니다.
- 요청한 상세 그룹이나 실행 상태에 따라 출력 필드는 달라집니다. include_ids 옵션이 있는 조회에서 ID가 포함된 예시는 true를 사용한 경우이며, 기본값 예시는 따로 표시합니다. 입력에 사용한 ID가 응답에서 생략되면 후속 호출에 재사용할 수 있도록 보관합니다.

# Connect

연결·세션 관리 · prefix: `connect_NN-` · 유형 내 순번 01–05

## 01. connect_01-list_up

기준 API: `connect_01-list_up`

근거: src/cos/external_host.py

### DESCRIPTION

연결 가능한 Rhino 문서와 현재 연결·시작 요청을 조회합니다.

### TOOL INPUT

```json
{
  "type": "object",
  "properties": {},
  "required": [],
  "additionalProperties": false
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "instructions": "targets는 발견한 Rhino 문서, connections는 유지 중인 연결, starts는 새 Rhino 시작 요청의 상태입니다. 대상의 state와 reason으로 사용 가능 여부를 확인합니다. 사용 중이거나 확인할 수 없는 대상은 파일 정보가 비어 있을 수 있습니다.", // 연결 목록의 구분과 상태를 읽는 방법입니다.
  "targets": [], // 연결 가능한 Rhino 문서 후보입니다.
  "connections": [], // 현재 유지 중인 연결입니다.
  "starts": [], // Rhino 시작 요청과 진행 상태입니다.
  "selected_connection_id": null, // 이후 호출에서 사용하는 연결 ID입니다. 선택된 연결이 없으면 null입니다.
  "next_step_guide": "연결할 Rhino의 저장된 문서에서 almondconnect를 실행한 뒤 목록을 다시 조회합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 02. connect_02-session

기준 API: `connect_02-session`

근거: src/cos/external_host.py

### DESCRIPTION

열려 있는 Rhino 문서에 연결하거나 작업할 문서를 전환합니다.

### TOOL INPUT

```json
{
  "type": "object",
  "properties": {
    "host_id": {
      "type": "string",
      "description": "connect_01-list_up tool의 targets에서 선택한 Rhino 프로세스의 host_id입니다."
    },
    "model_path": {
      "type": "string",
      "description": "같은 연결 대상에 표시된 저장 모델의 정확한 model_path입니다."
    }
  },
  "required": [
    "host_id",
    "model_path"
  ],
  "additionalProperties": false
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "connection_id": "example-connection", // 연결 ID입니다. 선택 후 일반 호출에서는 생략할 수 있습니다.
  "host_id": "example-host", // Rhino 호스트 ID
  "state": "ready", // 연결 상태입니다. ready에서 일반 작업을 수행하며 recovering/unconfirmed에서는 실행 결과부터 확인합니다.
  "reason": "", // 상태 사유 또는 오류 내용. 없으면 빈 문자열
  "model_path": "C:\\Example\\example.3dm", // 저장된 모델의 경로
  "model_filename": "example.3dm", // 모델 파일명
  "slot": "A", // 독립 연결 슬롯. 같은 폴더의 모델은 DB·산출물 루트를 공유
  "pid": 1234, // Rhino 프로세스 ID
  "artifact_dir": "C:\\Example\\.almond\\tmp\\python\\aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", // 이 연결의 임시 작업 폴더입니다.
  "in_flight": false, // 해당 연결에 호출이 진행 중인지 여부
  "next_step_guide": "연결된 문서가 의도한 문서인지 확인합니다. 프로젝트 정보는 context_04-get_project_info tool, 기존 작업은 plan_08-list tool의 request에 target='plan'을 넣어 조회합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 03. connect_03-start_session

기준 API: `connect_03-start_session`

근거: src/cos/external_host.py

### DESCRIPTION

저장된 모델을 새 Rhino 창에서 열고 연결합니다.

### TOOL INPUT

```json
{
  "type": "object",
  "properties": {
    "model_path": {
      "type": "string",
      "description": "새 Rhino에서 열 저장된 로컬 .3dm 파일의 절대 경로입니다."
    },
    "request_id": {
      "type": "string",
      "minLength": 1,
      "maxLength": 128,
      "description": "이 시작 요청의 고유 ID입니다. 시작이 지연되거나 결과가 불확실하면 새 ID를 만들지 말고 같은 값을 재사용해 상태를 확인합니다."
    }
  },
  "required": [
    "model_path",
    "request_id"
  ],
  "additionalProperties": false
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "connection_id": "example-connection", // 연결 ID입니다. 선택 후 일반 호출에서는 생략할 수 있습니다.
  "host_id": "example-host", // Rhino 호스트 ID
  "state": "ready", // 연결 상태입니다. ready에서 일반 작업을 수행하며 recovering/unconfirmed에서는 실행 결과부터 확인합니다.
  "reason": "", // 상태 사유 또는 오류 내용. 없으면 빈 문자열
  "model_path": "C:\\Example\\example.3dm", // 저장된 모델의 경로
  "model_filename": "example.3dm", // 모델 파일명
  "slot": "A", // 독립 연결 슬롯. 같은 폴더의 모델은 DB·산출물 루트를 공유
  "pid": 1234, // Rhino 프로세스 ID
  "artifact_dir": "C:\\Example\\.almond\\tmp\\python\\aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", // 이 연결의 임시 작업 폴더입니다.
  "in_flight": false, // 해당 연결에 호출이 진행 중인지 여부
  "request_id": "example-start", // 동일 시작 시도에 재사용. 대기·실패 상태는 list_connections.starts에서 확인
  "next_step_guide": "연결된 문서가 의도한 문서인지 확인합니다. 프로젝트 정보는 context_04-get_project_info tool, 기존 작업은 plan_08-list tool의 request에 target='plan'을 넣어 조회합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 04. connect_04-disconnect

기준 API: `connect_04-disconnect`

근거: src/cos/external_host.py

### DESCRIPTION

선택한 연결을 해제하고 Rhino 창과 문서는 유지합니다.

### TOOL INPUT

```json
{
  "type": "object",
  "properties": {
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 선택한 연결을 해제합니다. 다른 연결을 해제하려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [],
  "additionalProperties": false
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "connection_id": "example-connection", // 해제한 연결 ID입니다.
  "worker_closed": true, // worker가 종료됐는지 여부
  "rhino_closed": false, // Rhino가 닫혔는지 여부. disconnect는 false
  "released": true, // Rhino에서 연결 해제를 확인했는지 나타냅니다.
  "reason": "", // 해제 결과 또는 남아 있는 잠금의 사유입니다.
  "pid": 12340, // 해제한 연결의 Rhino 프로세스 ID입니다. 종료할 창을 식별할 때 model_path와 함께 확인합니다.
  "model_path": "C:\\Projects\\Example\\model.3dm", // 해제한 연결에 저장된 모델 경로입니다. 저장·종료 전에 현재 문서 경로와 일치하는지 확인합니다.
  "next_step_guide": "연결을 해제했으며 Rhino 창과 문서는 유지됩니다. 저장하고 Rhino까지 종료하려면 connect_01-list_up tool에서 해당 문서를 확인하고 connect_02-session tool로 다시 연결한 뒤 connect_05-close_session tool을 호출합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 90. connect_05-close_session

기준 API: `connect_05-close_session`

근거: src/cos/external_host.py, src/cos/session_close.py, src/cos/session_close_guard.py.txt

### DESCRIPTION

선택한 Rhino 문서를 저장하고 완료를 확인한 뒤 정상 종료합니다.

### TOOL INPUT

```json
{
  "type": "object",
  "properties": {
    "request_id": {
      "type": "string",
      "minLength": 1,
      "maxLength": 128,
      "description": "이 종료 요청의 고유 ID입니다. 지연·불확실 상태에서는 같은 ID로 결과를 조회합니다. 저장 확인 전에는 종료하지 않습니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 선택한 연결을 종료합니다. 기존 request_id 조회에는 연결이 없어도 됩니다."
    }
  },
  "required": [
    "request_id"
  ],
  "additionalProperties": false
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "request_id": "example-close", // 같은 ID 재호출은 결과만 조회합니다.
  "connection_id": "example-connection", // 저장·종료 대상 연결입니다.
  "pid": 12340, // 시작 identity까지 대조한 Rhino 프로세스입니다.
  "model_path": "C:\\Projects\\Example\\model.3dm", // 저장 대상의 절대 경로입니다.
  "status": "completed", // 저장 확인·실제 종료·worker 종료·소유권 해제를 모두 확인했습니다.
  "stage": "completed", // 마지막 처리 단계입니다.
  "modified_before": true, // Save 전 변경 여부입니다.
  "modified_after": false, // Save 후 변경이 없음을 확인했습니다.
  "saved": true, // 정확한 Save 완료와 같은 문서 상태를 확인했습니다.
  "save_request_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", // get_rhino_execution으로 조회할 Save 실행입니다.
  "rhino_closed": true, // 정확한 Rhino와 종료 CLI의 프로세스 종료를 확인했습니다.
  "worker_closed": true, // 해당 worker가 정상 종료됐습니다.
  "released": true, // 연결 소유권을 해제했습니다.
  "reason": "" // 거부·실패·불확실한 결과이면 원인이 담깁니다.
}
```

고정 실행 순서는 기존 저장 문서에 대한 `_Save` → 정확한 저장 완료와 `modified=false` 확인 → `_-Exit`입니다. `closing`·`unconfirmed`는 같은 `request_id`로 조회합니다. `rejected`·`save_failed`는 Exit를 완료하지 않은 결과입니다. 사유를 해결하고 종료하려는 경우에만 새 요청 ID를 사용합니다. Save의 늦은 완료 확인은 Exit를 자동 재개하지 않습니다.

# Context

기본 가이드·프로젝트 정보·운영 정책 · prefix: `context_NN-` · 유형 내 순번 01–04


## 67. context_04-get_project_info

기준 API: `context_04-get_project_info`

근거: src/mcp/runtime/mcp_server.py

### DESCRIPTION

프로젝트와 현재 문서의 작업 정보를 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "sections": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "요청할 섹션은 project, document, locations, runtime입니다. 생략하면 project/document/locations가 기본값입니다. project에는 등록된 파일이 포함되며, document는 현재 문서의 속성을 읽습니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다."
    },
    "files_limit": {
      "default": 50,
      "type": "integer",
      "description": "project 섹션 내 등록 파일의 페이지 크기입니다. 범위는 1..500입니다."
    },
    "files_offset": {
      "default": 0,
      "type": "integer",
      "description": "project 섹션 내 등록 파일의 오프셋입니다. 0부터 시작합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

sections=["project", "locations"], include_ids=true이고 아직 작업할 Plan을 선택하지 않은 경우입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "project": { // 현재 연결 문서와 프로젝트 정보입니다.
    "project_root": "C:\\Example",
    "file_name": "example.3dm",
    "file_path": "example.3dm",
    "is_bound_document": true,
    "files": [
      {
        "project_file_id": "file_example",
        "file_name": "example.3dm"
      }
    ],
    "files_page": {
      "total": 1,
      "limit": 50,
      "offset": 0,
      "truncated": false
    }
  },
  "locations": { // 현재 연결의 작업 공간과 공유 데이터베이스 위치입니다.
    "plan_id": "",
    "step_id": "",
    "artifact_dir": null,
    "database": ".almond/scene.sqlite3",
    "path_rule": "Managed tools apply ALMOND_PROJECT_ROOT automatically; pass relative paths.",
    "artifact_rule": "Select a Plan with plan_10-set_working tool; managed outputs use its current Loop folder .almond/produced/YYMMDD_name/01, /02, etc.; before plan_03-execute_looping tool they use the Plan root."
  },
  "next_step_guide": "- plan_08-list tool에 request.target='plan'으로 프로젝트 진행상황을 조회합니다.\n- 산출물 작업 공간은 plan_10-set_working tool으로 선택합니다.\n- 객체 상태가 필요하면 inspect_02-get_objects tool로 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 36. context_01-get_policy

기준 API: `context_01-get_policy`

근거: src/mcp/features/guidance/tools.py, src/mcp/modeling_guidance.py, src/mcp/features/guidance/policies/

### DESCRIPTION

Almond 작업에 필요한 지침을 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "policy": {
      "default": "",
      "enum": [
        "",
        "basic",
        "metadata",
        "rhino_scripting",
        "rhinocode",
        "spatial_modeling",
        "observation",
        "drawing",
        "design_exploration",
        "feedback_reporting"
      ],
      "type": "string",
      "description": "조회할 지침입니다. 생략하거나 빈 문자열이면 basic입니다. 각 선택값의 용도는 응답의 available_policies에서 확인합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

다음 두 예시는 현재 로컬 소스의 정책 reader로 생성했습니다. Rhino 실행 결과가 아닙니다. 기본값은 BASIC과 공통 도구명, 선택 가능한 policy를 반환합니다. 활동별 선택값은 해당 Markdown 전문을 같은 `text`·`source_refs` 형식으로 반환합니다. 선택지·파일·내용 해시는 [정책 등록 정보](src/mcp/modeling_guidance.py)와 대응합니다.

기본값 (`{}`):

```json
{
  "status": "success",
  "guide_version": "b17672ab4bca378d81cf96fedac8e3e9b33c1234addbd6bc06256be83c2a4e5d",
  "selected_policy": "basic",
  "available_policies": {
    "basic": "건축 설계·모델링·도면 검증 지침과 공통 도구 목록",
    "metadata": "객체·그룹 메타데이터 키, 레이어·재료 기록 규칙",
    "rhino_scripting": "Rhino 스크립트 작성과 API 참고 자료",
    "rhinocode": "RhinoCode 코드·Rhino 커맨드 실행과 결과 확인",
    "spatial_modeling": "설계 의도에 맞춘 공간·구축 모델링과 수정 후 확인",
    "observation": "모델과 도면을 관찰하고 판단에 필요한 근거를 확인하는 기준",
    "drawing": "도면의 목적·표현 기준과 작성·수정 결과의 검수",
    "design_exploration": "설계 질문을 구체화하고 대안을 구성·비교하는 기준",
    "feedback_reporting": "사용자 피드백을 작업에 반영하고 결과와 판단 근거를 전달하는 기준"
  },
  "text": "---\nname: rhino-almond\ndescription: \"Architectural judgment for developing existing designs with Almond MCP in Rhino.\"\n---\n\n# Rhino Almond\nAlmond MCP를 사용해 Rhino로 건축 설계를 develop한다. \n\n**Attitude**\n 설계 내용의 충돌은, 현재 설계 의도와 작업 목적을 기준으로 하여 주체적으로 추론·고찰하여 필요한 부분을 정합한다. \n 판단한 방향이 사용자의 지시나 설계 방향과 충돌하면, 차이가 생긴 구체적 근거와 선택의 영향을 사용자에게 설명하며 논의를 요청해 작업 방향을 사용자 주도 하에 align한다.\n\n## 작업 최초 실행 시\n1. 프로젝트 기본 구조를 `context_04-get_project_info` tool로 조회하여 파악\n2. 작업 하다가 `inspect_03-get_document_context` tool를 사용하여 작업 중의 맥락 파악\n\n### Plan 흐름과 판단의 연결\n\n프로젝트의 설계·모델링·도면·검수 작업은 목적에 맞는 Plan 템플릿의 Step을 따라 수행한다. 작업에 필요한 초기 맥락을 확인한 뒤 기존 Plan을 찾아 이어가거나 필요한 Plan을 만든다. scope 이름에서 순서를 추측하지 않고 현재 Plan에 저장된 Step 순서와 작업 기록을 읽는다. 각 Step에서는 해당 도구의 설명·입력·출력과 Next Step Guide를 함께 사용한다.\n\n다음 Step으로 넘어갈 때 앞 단계의 결론이 현재 대상·설계안·조건에도 유효한지 판단한다. 입력 근거와 달라진 조건, 그로 인해 다시 확인할 관계를 작업 기록에 연결한다. 순서에 있는 Step이나 후속 도구 안내는 그 작업의 범위·설계 선택을 승인하지 않는다. 요청에 해당하지 않는 작업은 이유와 다음 판단에 미치는 영향을 남기고, 필요한 선행 근거가 없으면 이를 확보한 뒤 이어간다.\n\n같은 목표의 피드백은 기존 Plan의 판단과 연결한다. 중단한 작업을 그대로 이어가는지, 이미 내린 판단을 바꾸는 재검토인지 구분해 회차를 선택한다. 재검토에서는 영향을 받는 가장 앞선 판단부터 순서대로 다시 확인하고, 여전히 유효한 결과는 근거를 연결해 재사용한다. 이전 결과·사용자 결정과 새 결과를 구분해 보존한다.\n\n### 활동별 policy\n\n아래 활동이 포함되면 `context_01-get_policy` tool에서 해당 policy를 읽는다. 여러 활동이 이어지면 필요한 기준을 함께 적용하며, 같은 `guide_version`에서 읽은 자료는 재사용한다. policy는 현재 Step의 판단을 보완하며 현재 과업과 별개의 Plan 생성이나 일률적인 승인 절차를 요구하지 않는다. 도구의 인자·지원 범위·실행 상태·결과 회수 방법은 각 도구 계약을 따른다.\n\n| 활동 | policy |\n|---|---|\n| 형상·구성원·공유 구성의 변경 범위와 보존 관계 판단 | `spatial_modeling` |\n| 여러 관찰 결과를 연결해 판단하거나 변경 뒤 근거 재사용 | `observation` |\n| 도면의 작성·편집·갱신과 Layout·출력물 전달 | `drawing` |\n| 공간 가능성·대안 탐색과 시각 비교 | `design_exploration` |\n| 사용자 피드백 요청·반영 또는 결과 보고·정리 | `feedback_reporting` |\n \n### Scene·ontological-holon\n\nScene은 행태·프로그램·장면의 맥락이고, ontological-holon는 그 장면을 가능하게 하는 건축 요소와 의미의 묶음이다. ontological-holon는 여러 Scene에 포함될 수 있다.\n\n#### Scene\n\nScene은 특정 공간에서 일어나는 **행태·프로그램·장면·가치**다. 파일 전체를 Scene 하나로 치환하지 않는다.\n\n#### ontological-holon\n\nontological-holon는 **건축 요소와, 그 요소들이 함께 가능하게 하는 사용·행태·구조적 역할을 묶은 의미 단위**다.\n-  무엇을 만들었는지와 그 묶음이 무엇을 가능하게 하는지를 함께 설명할 수 있어야 하며, 객체 종류·재료·거리만으로 경계를 정하지 않는다. \n\n##### 예시\n1. 마루와 계단참\n\n![마루·계단참·지지 구조·가구의 공간 관계](features/guidance/guides/references/assets/resident-porch.png)\n\n작은 계단참과 마루에서 사람들이 머물고 교류하는 행태가 Scene이다. 그 Scene을 이루는 ontological-holon는 다음처럼 **실물 구성과 그것이 가능하게 하는 것**을 함께 갖는다.\n\n| ontological-holon | 함께 구성하는 요소와 의미 |\n|---|---|\n| 마루 위 공간을 지지하는 구조 | 기둥·보 여러 개가 함께 위에서 오는 하중을 지지한다. 기둥마다 따로 등록하지 않는다. |\n| 사람들이 걸터앉는 마루·계단참 | 지지 콘크리트와 마루 마감이 함께 단차와 앉을 자리를 만든다. 마루라는 실물이면서 걸터앉을 수 있게 하는 장치다. 공유 바닥슬래브 전체를 포함할 필요는 없다. |\n| 마루에서 바둑 두는 가구 묶음 | 방석·낮은 탁자·바둑판·바둑알과 통·시계 등이 함께 앉아서 바둑 두는 행위를 가능하게 하고 유도한다. 가구 하나씩 나누지 않고, 그 행위와 사용 관계로 묶는다. |\n\n2. 지붕과 우수관\n\n![지붕과 우수관](features/guidance/guides/references/assets/roof-drainage.png)\n\n지붕의 의미에는 덮는 역할과 함께 집수·배수가 이어진다. 우수관이 여러 층을 지나거나 기둥 속 콘크리트에 매립돼 있어도 그 역할이 이어지므로 지붕 ontological-holon에 포함한다. 지붕 안의 구축 시스템과 우수관 element들은 일반 group으로 나눠 관리할 수 있다. **물리적으로 떨어져 있어도 하나의 역할을 이루면 같은 ontological-holon가 될 수 있다.** 두 사례의 [사용자 설명 원문과 사진](features/guidance/guides/references/component-feedback.md)은 별도로 보존한다.\n\n## 모델링\n\n### 건축물을 모델로 다루기\n\n건축 모델링은 공간을 이루는 물질적 구성을 설계하고 구체화하는 일이다. 모델에서 부재와 재료가 차지하는 부분, 그 사이에 생기는 공간, 공간을 연결하거나 나누는 경계를 함께 읽는다. 형상의 크기·두께·방향·배치는 사람이 머물고 움직이는 방식과 빛·시선·환경을 받아들이는 조건을 만든다. 형상을 수정할 때는 그 변화가 어떤 공간과 사용을 가능하게 하고 무엇을 어렵게 하는지 판단한다.\n\n모델의 요소는 건축물 안에서 서로 역할을 주고받는다. 한 요소가 여러 공간을 형성하거나 다른 요소를 지지할 수 있고, 떨어진 요소들이 하나의 기능을 함께 수행할 수도 있다. 따라서 요소의 이름이나 현재 묶음만으로 역할을 확정하지 않고, 어디에 놓여 무엇과 연결되며 어떤 구성에 참여하는지 해석한다. 과업의 규모에 따라 이 관계를 실내에서 건축물 전체와 주변 환경까지 연결해 이해한다.\n\nRhino 객체는 이 건축을 표현하는 편집 단위다. 하나의 실물 부재가 여러 객체로 나뉘거나 하나의 객체가 복합적인 구성을 단순화해 나타낼 수 있다. 모델을 읽을 때는 형상이 무엇을 나타내는지와 실제로 어느 정도까지 구체화돼 있는지를 구별한다. 분할된 객체 사이의 경계와 실물의 이음, 모델에 생긴 빈틈과 의도한 공간은 그 의미를 확인해야 구분할 수 있다.\n\n### 텍토닉: 재료와 구성, 접합\n\n텍토닉은 재료의 성질과 부재의 구성·결합이 건축의 공간과 표현을 성립시키는 방식이다. 재료의 물성과 가공 방식, 부재를 만들고 조립하는 순서는 가능한 형상·치수·접합을 제약한다. 요소를 이해할 때는 이 조건 속에서 부재가 무엇을 받치거나 감싸며, 힘과 기능이 다른 요소로 어떻게 이어지는지 읽는다. 실제 역할과 만드는 방식이 부재의 구분과 연결을 판단하는 근거다.\n\n접합부에는 요소 사이의 의존 관계가 드러난다. 연속돼야 할 부분, 힘이나 기능을 넘겨받는 부분, 서로 움직이거나 교체할 수 있도록 분리할 부분은 서로 다른 구성을 요구한다. 맞닿음·겹침·틈은 이 관계를 표현하는 기하 상태이므로, 각각이 재료·시공·사용 조건에 맞는지 판단한다. 모델에서 면이 맞거나 솔리드가 닫혔다는 사실과, 실제로 조립되고 역할을 수행할 수 있다는 판단은 별도의 근거를 갖는다.\n\n공간과 구축은 함께 발전한다. 부재의 위치와 깊이, 재료의 두께, 접합과 지지 방식은 공간의 여유·개방감·경계의 성질을 바꾸고, 원하는 공간은 다시 구성 방식의 선택에 영향을 준다. 현재 설계 단계에서 판단하려는 내용에 맞춰 형상을 구체화한다. 단순화한 표현으로 남긴 구성과 실제 상세를 결정한 부분을 구별하고, 상세를 추가할 때는 전체 구성과의 관계를 이어 간다.\n\n#### 구축 시스템과 표현 단계\n\nLayer는 `건축 유형 → 구축 시스템 → 구성 요소 역할`의 위계로 구성됩니다. 시스템이 미정일 때는 유형 Layer를, 시스템이 정해진 단순 모델에는 시스템 Layer를, 부재·마감을 구체화할 때는 요소 역할 Layer를 사용합니다. 시스템과 요소 Layer에는 각각 기본 Material과 표시·출력 색이 설정됩니다.\n\n실제 경로는 `M::유형::시스템명::요소역할`이다. 구축 상세를 적용할 대상이 이미 시스템 Layer에 있으면 그 시스템을 출발점으로 자료와 실제 구성을 대조한다. 유형 Layer에만 있으면 시스템은 미정이므로 적합한 시스템을 조사·구상하고 대안을 사용자와 논의한 뒤 적용한다. 대안을 모두 모델링해 놓고 사후 선택을 요구하지 않는다.\n\n시스템의 요소 역할·재료·간격·초기 치수·구성 메모는 모델의 지지·경계·접합 및 주변 조건과 대조한다. Layer 이름은 이런 조건의 검증 결과가 아니다. 합의한 부재·마감을 기존 요소 역할 Layer에 배치한다. 하나의 구축 구성을 함께 조립·편집할 수 있도록 group으로 묶는 것을 권장한다. 라이브러리 자료는 초기 설계 참고이며 검증된 시공 상세로 취급하지 않는다.\n\n\n### 객체들의 묶음 단위 유형\n\n함께 다룰 구성과 변경을 공유할 범위에 따라 group과 block을 선택·조합한다. Group은 개별 객체와 재귀적 묶음을 유지하고, group 자체는 복사본 사이에 변경을 전파하지 않는다. 한 객체가 여러 group에 속할 수 있으므로 중첩과 멤버 중복을 구분한다. Block은 definition을 공유하는 instance의 배치로, 각 배치의 위치·회전·축척은 개별적이고 정의 변경은 공유 배치에 반영된다. 일부 배치의 구성만 달라져야 하면 정의를 분리한다. 중첩 block은 보존되지만 일반 group의 묶음 관계는 block definition 내부에 보존되지 않으며, 바깥 group을 복사해도 내부 block은 정의를 공유한다. 묶음을 전환·해체·재조립할 때는 개별화할 형상과 남길 하위 구성, 변경이 전파될 배치를 구분한다.\n\n#### BlockEditNew에서 편집 범위를 다루기\n\nBlockEditNew에서는 뷰포트에서 선택한 group이나 block instance를 열고, 중첩 구성의 필요한 단계로 들어가 편집한다. Group 편집은 묶음의 구성원들을 다루는 작업이고, block 편집은 선택한 배치를 통해 공유 정의의 내용을 고치는 작업이다. Block을 열었을 때 화면에서 선택 가능한 작업 객체는 저장된 definition 내부 객체와 같은 식별 대상이 아니다. 정의 내부 GUID와 현재 편집 객체의 ID를 구분하고, 편집 진입·완료·재구성 뒤에는 대상을 다시 조회한다. 정의와 배치 변환은 이때 어떤 구성과 위치를 편집하는지 연결하는 근거가 된다.\n\n격리된 부분에서는 부재의 형상과 내부 구성을 읽기 쉽고, 그 부분이 전체에서 맡는 역할은 주변 관계 속에서 판단할 수 있다. 검토할 관계에 맞춰 편집 깊이와 관찰 범위를 선택하고, 부분의 변경이 끝나면 영향을 받는 상위 구성과 공유 배치에서 결과를 확인한다. 중첩 단계 밖의 선택·표시 상태를 임의로 재설정해 현재 편집 맥락을 잃지 않도록 한다.\n\n### 모델링 검수\n\n관찰·검수용 이미지를 만들기 위해 원본 모델을 별도 위치에 복사하거나, 실제 모델의 수정·검수 대신 이미지에 형상을 덧그리지 않는다.\n\n검수는 바뀐 모델이 해결하려던 설계 문제를 해결했는지, 의도한 공간과 구축을 성립시키는지 판단하는 과정이다. 수정한 형상에서 출발해 그 요소의 역할, 접합과 연속, 영향을 받은 공간과 다른 요소로 판단을 이어 간다. 국소적인 형상 개선이 주변의 사용이나 구성에 새로운 문제를 만들었는지도 살핀다.\n\n무엇을 판단할지에 따라 관찰 방법을 정한다. 전체 배치와 공간 관계, 부재의 연결, 가려진 내부 구성은 필요한 관찰 범위와 시점이 다르다. 판단에 필요한 요소들이 함께 드러나도록 화면을 구성하고 실제 이미지를 읽는다. 격리한 화면이 보여 주는 관계와 제외한 관계를 구분하며, 잘린 요소나 빠진 주변 구성 때문에 판단 근거가 달라지지 않는지 확인한다.\n\n시각적으로 읽은 내용은 그 판단에 필요한 형상과 치수로 대조한다. 부재 전체의 연속성을 판단하려면 그 부재를 이루는 객체들의 관계를, 접합을 판단하려면 맞물리는 요소의 실제 형상과 구성을 확인한다. 수치상 교차·간격이나 객체별 유효성은 해당 질문의 근거로 해석한다. 검사를 통과한 항목만으로 아직 보지 않은 관계까지 성립한다고 확대하지 않는다.\n\n의미 있는 편집 묶음이 끝나면 결과를 사용자의 목표와 보존 조건에 대조해 추가 개입이 필요한지 판단한다. 요청된 결과가 성립하고 관련 보존 조건을 확인했으면 해당 작업을 완료한다. 불일치나 판단에 필요한 미확인이 남아 있으면 이를 해소할 관찰·검증·수정으로 이어간다. 변경으로 새롭게 드러난 문제가 작업 범위를 넘으면 근거와 영향을 설명하고 별도 제안으로 다룬다.\n\n확인한 사실, 설계 의도에 대한 해석, 가정과 미확인 사항을 구분한다. 실행 성공과 형상의 유효성, 공간·구축의 적합성, 사용자 요청의 완료는 각각의 근거로 판단하며 미검사 범위와 남은 문제를 보고한다.\n\n## Drafting\n\n도면은 건축 요소의 표현이자 공간의 구성과 사용을 구상하고 전달하는 설계 도구다. 도면을 읽을 때는 그려진 형상과 표현을 파악하는 동시에, 그 구성이 만들어 내는 공간과 경험, 사람들이 그 안에서 맺는 관계를 이해한다.\n\n### 도면을 공간과 의미로 읽기\n\n도면의 요소를 독립된 객체나 선의 집합으로만 보지 않는다. 요소들이 함께 형성하는 공간적 관계와 그 관계가 가능하게 하는 사용·행태·경험을 읽는다. 하나의 요소가 여러 공간과 역할에 걸쳐 작용할 수 있음을 고려하고, 물리적으로 떨어진 요소도 하나의 사용이나 역할을 함께 이룰 수 있음을 살핀다.\n\n공간의 의미는 실의 명칭이나 도면 기호만으로 결정되지 않는다. 공간의 구성과 주변 관계를 바탕으로 그곳에서 일어날 수 있는 행태를 구상하고, 그 행태가 공간과 건축 요소에 의해 어떻게 뒷받침되는지 판단한다.\n\n평면·단면·입면은 같은 건축을 서로 다른 관점에서 보여 준다. 하나의 도면에서 읽은 관계를 다른 도면이나 모델과 연결해 이해하고, 확인할 수 없는 사항은 추론의 범위와 함께 구분한다.\n\n#### 행태와 공간 경험\n\n공간을 구상하고 검토할 때 사람이 그곳을 어떻게 경험하고 이용할지 생각한다. 공간의 크기나 형태뿐 아니라 공간 사이의 연결과 전이, 경계와 개방, 이용의 가능성과 제약을 함께 이해한다.\n\n사람의 행태는 고정된 하나의 장면이 아니다. 공간은 이용자와 상황에 따라 다르게 사용될 수 있으며, 그 변화가 공간 구성과 어떤 관계를 맺는지 살핀다. 설계가 어떤 경험을 유도하고 무엇을 선택할 수 있게 하는지, 또는 어떤 이용을 어렵게 하는지 판단한다.\n\n도면에 표현된 행태를 그대로 받아들이는 데 그치지 않고, 실제 공간에서 가능한 관계인지 검토한다. 도면만으로 확인할 수 없는 이용 조건은 필요한 자료와 시점을 통해 보완한다.\n\n#### 공간의 규모와 사회적 관계\n\n도면을 개별 실과 건축 요소에서 시작해 더 넓은 공간적 맥락과 연결해 읽는다. 과업의 규모와 목적에 따라 개인의 생활, 공동체의 관계, 거리와 도시, 사회적 가치까지 건축적 판단의 범위에 포함한다.\n\n사람과 사람, 개인과 공동체, 건축과 주변 환경의 관계가 공간을 통해 어떻게 형성되는지 고찰한다. 공간적 구성과 사회적 가치 사이의 관계를 살피되, 도면만으로 확정할 수 없는 운영이나 사회적 효과는 해석과 제안으로 구분한다.\n\n### 설계와 도면의 발전\n\n도면 작업에서는 사용자의 의도와 설계 방향을 바탕으로 공간을 발전시키고, 그 결과가 도면에 정확하게 반영되도록 한다. 피드백이 특정 요소를 가리키더라도 그것이 놓인 공간과 주변 관계를 함께 이해한다.\n\n평면을 수정하거나 새롭게 구성할 때는 도면상 형상의 변화가 실제 공간의 사용과 경험에 어떤 영향을 주는지 판단한다. 설계 과정에서 발견한 관계와 문제를 도면의 구성에 반영하고, 변경에 따라 함께 달라져야 할 사항을 정합한다.\n\n확인된 조건을 바탕으로 전문적으로 판단하되, 사용자의 의도나 중요한 설계 선택이 불확실하면 그 불확실성과 선택의 영향을 분명히 설명한다.\n\n작업의 목적과 대상, 설계 단계, 사용자의 결정과 조건을 파악한다. 현재 도면과 관련 스케치·피드백을 함께 읽고 공간의 구성과 맥락을 이해한다.\n\n실제 도면 이미지를 보며 공간의 구성과 사용 관계를 검토한다. 그려진 요소가 의도한 공간과 행태를 뒷받침하는지, 도면이 설계의 관계를 정확하게 전달하는지 확인한다.\n\n시각적으로 읽은 내용은 필요한 형상과 치수로 대조한다. 평면에서 확인하기 어려운 사항은 단면·입면·모델을 함께 살피고, 수정한 부분과 그 영향을 받는 공간을 다시 검토한다. 지정된 Named View가 있으면 검수에 활용한다.\n\n도면에서 확인한 사실과 그에 대한 해석, 설계상 가정과 미확인 사항을 구분한다.\n\n벽·문·가구·동선·프로그램 관계를 촘촘히 검토한 과거 과정의 참고 이미지가 필요하면 [Bonsai 평면 개요](features/guidance/guides/Bonsai-FloorPlan-overview.png)를 확인하되, 이를 최신 공간 결정이나 완성 도면 원본으로 사용하지 않는다.\n\n### 도면의 작성과 관리\n먼저 도면으로 무엇을 보여주고 어떤 판단을 돕는지 정하고, 그 목적에 필요한 범위와 축척을 선택한다. 선·면·색·두께의 위계가 전달할 관계를 드러내도록 구성하며, 주변 맥락을 포함하느라 핵심 대상이 읽히지 않으면 범위를 조절하거나 별도 도면으로 나눈다.",
  "source_refs": [
    {
      "path": "src/mcp/BASIC-INSTRUCTIONS.md",
      "sha256": "0e8270647c41c01daffa395166312e9c924ac4270e0beed56f21d8bfc3237d4c"
    }
  ],
  "tools": [
    "analysis_01-check_egress",
    "analysis_02-export_structural_report",
    "analysis_03-list_design_codes",
    "analysis_04-validate_structure",
    "analysis_05-visualize_structure",
    "asset_01-audit_drawing",
    "asset_02-generate_drawing_views",
    "asset_03-get_drawings",
    "asset_04-get",
    "asset_05-list",
    "asset_06-place",
    "asset_07-prepare",
    "asset_08-refresh",
    "asset_09-register",
    "asset_10-search_repository",
    "asset_11-search",
    "capture_01-conditioning_pass",
    "capture_02-inspection",
    "capture_03-current_view",
    "capture_04-defined_view",
    "context_01-get_policy",
    "context_04-get_project_info",
    "diagram_01-get",
    "diagram_02-list",
    "diagram_03-place",
    "diagram_04-search",
    "drawing_01-apply_style",
    "drawing_02-get_recipe",
    "drawing_03-get_plan_section_result",
    "drawing_04-import_hatches",
    "drawing_05-list_recipes",
    "drawing_06-generate_plan_section",
    "exchange_01-export_asset_contract",
    "exchange_02-get_blender_script",
    "exchange_03-import_asset_contract",
    "exchange_04-publish_chestnut_advanced",
    "exchange_05-publish_chestnut",
    "grasshopper_01-get_logic",
    "grasshopper_02-list_capsules",
    "grasshopper_03-list_library",
    "grasshopper_04-run_definition",
    "inspect_01-analyze_nested_blocks",
    "inspect_02-get_objects",
    "inspect_03-get_document_context",
    "inspect_04-get_selection_references",
    "inspect_05-resolve_targets",
    "intersect_01-find",
    "intersect_02-resolve",
    "model_01-assign_material",
    "model_02-edit_planar_face",
    "model_03-edit_planar_faces",
    "model_04-list_materials",
    "model_05-setup",
    "plan_02-create",
    "plan_03-execute_looping",
    "plan_05-get",
    "plan_07-list_revisions",
    "plan_08-list",
    "plan_09-rename_artifact_folder",
    "plan_10-set_working",
    "plan_12-update",
    "research_01-get_construction_guidance",
    "research_02-get_typology_narrative",
    "research_03-search_details",
    "scene_01-add_objects",
    "scene_02-create",
    "scene_03-focus_holons",
    "scene_04-get",
    "scene_05-get_holon",
    "scene_06-get_objects",
    "scene_07-list",
    "scene_08-list_holons",
    "scene_09-remove_holon",
    "scene_10-remove_objects",
    "scene_11-sync_holon",
    "scene_12-update",
    "scene_13-upsert_holon",
    "script_01-run_project_python",
    "script_02-run_rhino",
    "script_03-get_execution",
    "script_04-save_document"
  ]
}
```

활동별 선택 (`{"policy":"observation"}`):

```json
{
  "status": "success",
  "guide_version": "b17672ab4bca378d81cf96fedac8e3e9b33c1234addbd6bc06256be83c2a4e5d",
  "selected_policy": "observation",
  "available_policies": {
    "basic": "건축 설계·모델링·도면 검증 지침과 공통 도구 목록",
    "metadata": "객체·그룹 메타데이터 키, 레이어·재료 기록 규칙",
    "rhino_scripting": "Rhino 스크립트 작성과 API 참고 자료",
    "rhinocode": "RhinoCode 코드·Rhino 커맨드 실행과 결과 확인",
    "spatial_modeling": "설계 의도에 맞춘 공간·구축 모델링과 수정 후 확인",
    "observation": "모델과 도면을 관찰하고 판단에 필요한 근거를 확인하는 기준",
    "drawing": "도면의 목적·표현 기준과 작성·수정 결과의 검수",
    "design_exploration": "설계 질문을 구체화하고 대안을 구성·비교하는 기준",
    "feedback_reporting": "사용자 피드백을 작업에 반영하고 결과와 판단 근거를 전달하는 기준"
  },
  "text": "# 관찰·검수\n\n현재 Step의 결론에 여러 조회·이미지·계산 결과를 연결하거나, 이전 Step의 근거를 재사용할 때 적용한다. 관찰 시점과 범위를 고르고 실제 이미지를 읽는 기본 원칙은 BASIC을 따른다.\n\n## OB1. 같은 대상을 설명하는 근거끼리 연결한다\n\n관찰 전에 요청에서 확인할 관계와 적용할 판정 기준을 정한다. 기준이 확인되지 않았으면 임의의 통과값을 만들지 않고 미확인으로 남겨 관찰·평가·보고에 연결한다.\n\n근거의 문서·대상 집합·설계안·변경 시점과 표현 상태를 맞춘다. Scene 구성원 목록, 화면에 보이는 객체, 실제 공간의 연결은 서로 다른 범위다. 격리·clipping으로 제외된 부재를 실제로 없는 것으로 읽지 않는다. 단면이나 다른 시점에서 이어지는 관계가 필요하면 그 관계를 드러내는 근거를 보완한다.\n\n수치와 그림이 다르면 먼저 같은 대상과 조건을 비교하는지 확인한다. 비교 범위를 맞춰도 모순이 남으면 어느 결과가 어떤 결론을 지지하는지 구분하고, 결론에 필요한 쪽을 추가 관찰한다. 편리한 결과 하나를 골라 나머지를 무시하지 않는다.\n\n## OB2. 발견하지 못한 것과 확인한 부재를 구분한다\n\n현재 범위의 조회에서 나오지 않은 객체, 일부 검사에서 발견되지 않은 충돌, 해석 불가능한 결과는 각각 그 범위의 결과다. 결과가 비어 있어도 확인하려던 관계 전체를 검사했는지 먼저 판단한다. 충돌 없는 솔리드 쌍이 나왔다는 사실은 통행·접근·조립 가능성의 검증이 아니다.\n\n보고할 주장을 확인된 범위로 제한한다. 요청의 핵심 판단에 미확인이 남으면 필요한 관찰·검증으로 이어가고, 관측 수단이 부족하면 해당 판단을 미확인으로 남겨 다음 결정의 조건에 포함한다. 관측 도구의 페이지·지원 형상·오류·결과 회수 절차는 해당 출력과 안내를 따른다.\n\n## OB3. 근거의 유효기간을 변경 영향으로 판단한다\n\n다음 Step의 작업이 이전 근거의 대상이나 조건을 바꿨으면 해당 근거로 현재 결과를 설명할 수 있는지 다시 판단한다. 모델 수정 전 캡처, 도면 갱신 전 Layout, 다른 설계안의 치수를 최신 결과에 섞지 않는다. 변화와 무관한 기존 근거는 원래 대상·시점을 밝혀 재사용한다.\n\n검수 Step이 끝난 뒤에도 Layout 배치·출력·정리가 전달 내용을 바꾸면 그 영향 범위를 확인한다. 상태값이나 마지막 검수 Step의 존재가 최종 전달물의 정확성을 대신하지 않는다.",
  "source_refs": [
    {
      "path": "src/mcp/features/guidance/policies/observation.md",
      "sha256": "db6061a39ce192d11a68e2a949eaa702a33e65aeffd2fde33ab04c26cf558eb7"
    }
  ]
}
```

`metadata`는 기존 `policy` 객체, `rhino_scripting`은 기존 `scripting_skill` 자료 묶음을 유지합니다. `rhinocode`와 활동별 정책은 `text`입니다. 선택하지 않은 다른 정책 전문은 반환하지 않습니다. 시나리오 검토 범위는 [policy 검증 안내](src/mcp/features/guidance/policy-validation/README.md)를 참조합니다.

# Plan

작업 계획·단계·산출물 관리 · prefix: `plan_NN-` · 유형 내 순번 01–13

## 15. plan_02-create

기준 API: `plan_02-create`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

Phase 또는 Plan을 생성합니다. Plan의 Step은 선택한 scope의 템플릿에서 자동 생성합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "request": {
      "oneOf": [
        {
          "additionalProperties": false,
          "properties": {
            "target": {
              "const": "phase",
              "description": "작업할 대상 종류입니다.",
              "type": "string"
            },
            "name": {
              "description": "Phase 이름을 문자열로 입력합니다. 빈 문자열은 사용할 수 없습니다.",
              "type": "string"
            },
            "description": {
              "default": "",
              "description": "Phase의 목적이나 작업 범위를 문자열로 입력합니다.",
              "type": "string"
            },
            "file_name": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                }
              ],
              "default": "",
              "description": "이 Phase가 속한 Rhino 파일명입니다. 문자열 하나 또는 문자열 배열로 입력합니다."
            },
            "status": {
              "default": "pending",
              "description": "pending, running, paused, completed, failed, blocked 중 하나를 선택합니다.",
              "enum": [
                "pending",
                "running",
                "paused",
                "completed",
                "failed",
                "blocked"
              ],
              "type": "string"
            },
            "depends_on": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "이 Phase가 의존하는 Phase ID 목록입니다. 같은 종류의 ID 형식만 검사하며 대상의 존재·자기 참조·순환을 검사하거나 실행 순서·완료를 강제하지 않습니다."
            },
            "previous_id": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "이전 Phase의 ID입니다."
            }
          },
          "required": [
            "target",
            "name"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "target": {
              "const": "plan",
              "description": "작업할 대상 종류입니다.",
              "type": "string"
            },
            "title": {
              "description": "Plan 목록에서 사용할 비어 있지 않은 짧은 제목입니다.",
              "type": "string"
            },
            "goal": {
              "description": "비어 있지 않은 전체 목표와 의도한 결과입니다.",
              "type": "string"
            },
            "scope": {
              "default": "house",
              "description": "작업 목적에 맞는 Step 템플릿을 선택합니다: spatial_development, drawing_development, semantic_exploration, plan_editing, model_revision, inspection, structure, construction_detail, drawing, component, house, interior. 등록한 사용자 템플릿도 사용할 수 있습니다.",
              "type": "string"
            },
            "scene_id": {
              "default": "",
              "description": "기존 방식의 단일 Scene ID입니다. scene_ids를 우선 사용합니다. 둘 다 전달하면 scene_ids의 첫 번째 항목과 같아야 합니다.",
              "type": "string"
            },
            "phase_id": {
              "default": "",
              "description": "선택 사항인 기존 Phase ID입니다. 비어 있으면 Plan을 Phase에 소속시키지 않습니다.",
              "type": "string"
            },
            "scene_ids": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Plan의 작업 맥락이 되는 기존 Scene ID 배열입니다. 생략하면 Scene 없이 생성합니다."
            },
            "holon_ids": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "이 Plan에서 작업할 기존 Holon ID 배열입니다."
            },
            "depends_on": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "이 Plan이 의존하는 Plan ID 목록입니다. 같은 종류의 ID 형식만 검사하며 대상의 존재·자기 참조·순환을 검사하거나 실행 순서·완료를 강제하지 않습니다."
            },
            "previous_id": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "이전 Plan의 ID입니다."
            },
            "parent_plan": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "이 Plan에 기록할 선택 사항인 상위 Plan ID 배열입니다. 상대 Plan을 자동으로 수정하거나 참조 대상의 존재를 검증하지 않습니다."
            },
            "child_plan": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "이 Plan에 기록할 선택 사항인 하위 Plan ID 배열입니다. 상대 Plan을 자동으로 수정하거나 참조 대상의 존재를 검증하지 않습니다."
            }
          },
          "required": [
            "target",
            "title",
            "goal"
          ],
          "type": "object"
        }
      ],
      "description": "target으로 phase 또는 plan을 선택하고 해당 생성 정보를 입력합니다. Step 독립 생성은 제공하지 않습니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "request"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

Phase 결과 예시:

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "phase": { // 생성한 Phase입니다.
    "phase_id": "phase_example"
  },
  "next_step_guide": "Plan을 추가하려면 plan_02-create tool의 request에 target='plan', title, goal과 반환된 phase_id를 입력합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

Plan 결과 예시:

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "plan": { // 생성한 Plan입니다.
    "plan_id": "plan_example",
    "loop_no": 0,
    "revision": 1
  },
  "next_step_guide": "plan_05-get tool의 request에 target='plan', 반환된 plan_id와 include_details=true를 넣어 자동 생성된 Step을 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 18. plan_03-execute_looping

기준 API: `plan_03-execute_looping`

근거: src/mcp/runtime/mcp_server.py

### DESCRIPTION

Plan의 작업 회차를 시작하거나 재개합니다. 각 Step은 에이전트가 수행합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "plan_id": {
      "type": "string",
      "description": "다음 Loop를 시작하거나 최신 Loop를 재개할 기존 Plan ID입니다. plan_02-create tool 또는 plan_08-list tool에서 얻은 ID를 사용합니다."
    },
    "resume": {
      "default": false,
      "type": "boolean",
      "description": "false는 새 회차 시작, true는 최신 회차 재개입니다. 이전 회차의 결과를 보고한 뒤 새 회차를 시작합니다. 시작 결과가 불확실하면 plan_05-get tool의 request에 target='plan'과 plan_id를 넣어 현재 회차를 먼저 확인합니다."
    },
    "feedback": {
      "default": "",
      "type": "string",
      "description": "이번 회차에 반영할 피드백입니다. 재개 시 생략하거나 비우면 기존 값을 유지합니다."
    },
    "artifact_name": {
      "default": "",
      "type": "string",
      "description": "Plan의 최초 산출물 폴더 이름입니다. 생략하면 목표에서 정하며 날짜 접두사 YYMMDD_를 붙입니다. 기존 폴더는 재사용합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "plan_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "plan_id": "plan_example", // Plan ID
  "loop_no": 1, // Loop 회차 번호
  "next_step_id": "step_example", // 아직 완료되지 않은 첫 Step의 ID입니다. 없으면 null입니다.
  "previous_loop": null, // 이전 회차의 번호와 Step 기록입니다. 새 작업에 앞서 수행·검증·보고 내용을 확인합니다.
  "step_id": "", // 선택한 Step ID입니다.
  "plan_artifact_dir": ".almond/produced/261111_example", // Plan 산출물 폴더
  "artifact_dir": ".almond/produced/261111_example/01", // 작업 산출물 폴더
  "revision": 1, // 현재 Plan·Loop의 저장 리비전입니다.
  "title": "예시 계획", // 저장된 제목
  "goal": "예시 목표", // 저장된 목표
  "plan_status": "pending", // Plan의 업무 상태입니다. 회차 시작만으로 변경되지는 않습니다.
  "feedback": "", // 저장된 피드백
  "steps": [ // 현재 회차의 Step과 저장된 수행 상태입니다. 미완료 작업을 선택할 때 사용합니다.
    {
      "step_id": "step_example",
      "name": "예시 단계",
      "status": "pending"
    }
  ],
  "policy_reminder": "Step은 기본 순서대로 수행합니다. 기존 결과는 확인한 뒤 재사용하고 산출물은 이 회차의 artifact_dir에 작성합니다. Plan 완료는 사용자가 결정합니다.", // Step 순서·기존 결과 재사용·산출물 위치·Plan 완료 결정에 적용할 지침입니다.
  "next_step_guide": "저장된 수행·검증·보고 기록을 확인하고 미완료 Step이 있으면 plan_10-set_working tool으로 선택합니다. 완료한 작업은 반복하지 않고, 수행·검증 결과는 plan_12-update tool의 request에 target='step', plan_id, step_id와 기록할 필드를 넣어 갱신합니다. 기록할 Step ID가 없으면 먼저 plan_08-list tool의 request에 target='step', 같은 plan_id·loop_no를 넣어 목록에서 Step을 선택합니다. 근거를 얻은 작업 맥락의 loop_no를 유지해 request.loop_no로 함께 전달합니다. expected_revision 검사도 사용할 경우 plan_05-get tool의 request에 같은 target·ID·loop_no를 넣어 조회한 최신 revision을 사용합니다. Loop가 바뀌었으면 기록 대상을 먼저 재검토합니다.\n회차가 끝나면 목표·변경 내용·시각적 근거·검증 결과·남은 선택지를 보고합니다." // 저장 기록 확인, Step 수행·검증 기록과 회차 결과 보고 안내입니다.
}
```

## 41. plan_05-get

기준 API: `plan_05-get`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

Phase, Plan 또는 Step의 작업 기록을 조회합니다. Plan과 Step은 현재 상태 또는 저장된 Loop·리비전을 읽습니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "request": {
      "oneOf": [
        {
          "additionalProperties": false,
          "properties": {
            "target": {
              "const": "phase",
              "description": "작업할 대상 종류입니다.",
              "type": "string"
            },
            "phase_id": {
              "description": "조회할 Phase ID입니다.",
              "type": "string"
            },
            "include_details": {
              "default": false,
              "description": "false이면 식별·상태 요약, true이면 선택한 Phase·Plan·Step의 상세 작업 기록을 함께 조회합니다.",
              "type": "boolean"
            }
          },
          "required": [
            "target",
            "phase_id"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "target": {
              "const": "plan",
              "description": "작업할 대상 종류입니다.",
              "type": "string"
            },
            "plan_id": {
              "description": "조회할 Plan ID입니다. Step 조회에는 해당 Step의 Plan ID를 사용합니다.",
              "type": "string"
            },
            "revision": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "선택한 Loop 안에 저장된 선택적 리비전입니다. 생략하면 선택한 Loop의 최신 상태를 읽습니다. Phase에는 사용할 수 없습니다."
            },
            "include_details": {
              "default": false,
              "description": "false이면 식별·상태 요약, true이면 선택한 Phase·Plan·Step의 상세 작업 기록을 함께 조회합니다.",
              "type": "boolean"
            },
            "loop_no": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Plan/Step 조회에 사용할 선택 사항인 0 이상의 Loop 번호입니다. 생략하면 최신 Loop를 선택합니다. 0은 실행 전 기록을 읽습니다. Phase에는 사용할 수 없습니다."
            }
          },
          "required": [
            "target",
            "plan_id"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "target": {
              "const": "step",
              "description": "작업할 대상 종류입니다.",
              "type": "string"
            },
            "plan_id": {
              "description": "조회할 Plan ID입니다. Step 조회에는 해당 Step의 Plan ID를 사용합니다.",
              "type": "string"
            },
            "step_id": {
              "description": "선택한 Plan에 속한 Step ID입니다.",
              "type": "string"
            },
            "revision": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "선택한 Loop 안에 저장된 선택적 리비전입니다. 생략하면 선택한 Loop의 최신 상태를 읽습니다. Phase에는 사용할 수 없습니다."
            },
            "include_details": {
              "default": false,
              "description": "false이면 식별·상태 요약, true이면 선택한 Phase·Plan·Step의 상세 작업 기록을 함께 조회합니다.",
              "type": "boolean"
            },
            "loop_no": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Plan/Step 조회에 사용할 선택 사항인 0 이상의 Loop 번호입니다. 생략하면 최신 Loop를 선택합니다. 0은 실행 전 기록을 읽습니다. Phase에는 사용할 수 없습니다."
            }
          },
          "required": [
            "target",
            "plan_id",
            "step_id"
          ],
          "type": "object"
        }
      ],
      "description": "target으로 phase, plan, step을 선택하고 해당 ID를 입력합니다. include_details로 상세 기록을 선택합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "request"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

Phase 결과 예시:

```jsonc
{
  "id": "phase_example", // 조회한 Phase·Plan·Step의 ID입니다.
  "type": "phase", // 조회한 유형입니다.
  "name": "배치 검토", // 조회한 항목의 이름입니다.
  "status": "pending", // 업무 상태입니다. pending, running, paused, completed, failed, blocked 중 하나이며 조회 실패는 error입니다.
  "phase": { // include_details=true인 Phase의 상세 내용입니다.
    "description": "대지와 건물 검토",
    "file_name": [
      "site.3dm",
      "building.3dm"
    ],
    "depends_on": [],
    "previous_id": null,
    "plan_titles": [
      "진입 동선 검토"
    ]
  },
  "next_step_guide": "plan_08-list tool의 request에 target='plan'과 이 id를 phase_id로 입력해 소속 Plan을 조회합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 61. plan_07-list_revisions

기준 API: `plan_07-list_revisions`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

Plan과 Loop에 저장된 리비전과 변경 작업을 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "plan_id": {
      "type": "string",
      "description": "plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다."
    },
    "limit": {
      "default": 50,
      "type": "integer",
      "description": "최대 리비전 기록 수입니다. 범위는 1..500입니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "저장된 타임스탬프를 포함하려면 선택적으로 audit 또는 all을 사용합니다. 생략하거나 비어 있으면 loop_no, revision, operation 및 step_id를 반환합니다."
    },
    "loop_no": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 사항인 0 이상의 Loop 필터입니다. 생략하면 모든 Loop를 포함하며, 0은 실행 전 이력을 선택합니다."
    },
    "step_id": {
      "default": "",
      "type": "string",
      "description": "직접적인 Step 변경에 사용할 선택 사항인 UUID Step 필터입니다. 비어 있으면 Plan 전체 기록도 포함합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "plan_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "plan_id": "plan_example", // 각 행의 loop_no/revision과 함께 plan_05-get tool의 request에 사용
  "revisions": [], // 저장 리비전 목록입니다.
  "total": 0, // 필터에 일치하는 전체 항목 수
  "limit": 50, // 페이지 최대 항목 수
  "truncated": false // limit 때문에 최신 리비전 일부만 반환했는지 나타냅니다.
}
```

## 62. plan_08-list

기준 API: `plan_08-list`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

Phase·Plan 목록 또는 한 Plan의 순서 있는 Step 목록을 조회합니다. Step 목록은 같은 스냅샷의 Loop·리비전과 함께 반환합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "request": {
      "oneOf": [
        {
          "additionalProperties": false,
          "properties": {
            "target": {
              "const": "phase",
              "description": "작업할 대상 종류입니다.",
              "type": "string"
            },
            "limit": {
              "default": 50,
              "description": "최대 Phase 수입니다. 범위는 1..500입니다.",
              "type": "integer"
            },
            "field_groups": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "선택 사항인 그룹은 description, scope, audit 또는 all입니다. 생략하거나 비어 있으면 요약과 ID를 유지합니다."
            }
          },
          "required": [
            "target"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "target": {
              "const": "plan",
              "description": "작업할 대상 종류입니다.",
              "type": "string"
            },
            "phase_id": {
              "default": "",
              "description": "선택 사항인 Phase ID 필터입니다. 비어 있으면 여러 Phase를 범위로 합니다.",
              "type": "string"
            },
            "scene_id": {
              "default": "",
              "description": "선택 사항인 Scene ID 필터입니다. 비어 있으면 어떤 Scene에 속하든, Scene이 없든 모든 Plan을 포함합니다.",
              "type": "string"
            },
            "status": {
              "default": "",
              "description": "pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. 빈 문자열이면 모든 상태를 포함합니다.",
              "enum": [
                "",
                "pending",
                "running",
                "paused",
                "completed",
                "failed",
                "blocked"
              ],
              "type": "string"
            },
            "limit": {
              "default": 50,
              "description": "최대 Plan 수입니다. 범위는 1..500입니다.",
              "type": "integer"
            }
          },
          "required": [
            "target"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "target": {
              "const": "step",
              "description": "Step 목록을 선택합니다.",
              "type": "string"
            },
            "plan_id": {
              "description": "Step 목록을 읽을 기존 Plan ID입니다.",
              "type": "string"
            },
            "revision": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "선택한 Loop 안의 리비전입니다. 생략하면 해당 Loop의 최신 상태를 읽습니다."
            },
            "loop_no": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "선택할 0 이상의 Loop 번호입니다. 생략하면 최신 Loop, 0은 실행 전 기록입니다."
            },
            "limit": {
              "default": 50,
              "description": "정의된 순서대로 반환할 최대 Step 수입니다. 범위는 1..500입니다.",
              "maximum": 500,
              "minimum": 1,
              "type": "integer"
            }
          },
          "required": [
            "target",
            "plan_id"
          ],
          "type": "object"
        }
      ],
      "description": "target으로 phase, plan, step을 선택합니다. Step에는 plan_id가 필요하며 대상별 필터와 limit을 지정합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "request"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

Phase 결과 예시:

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "phases": [], // Phase 목록입니다.
  "total": 0, // 필터에 일치하는 전체 항목 수
  "limit": 50, // 페이지 최대 항목 수
  "truncated": false // limit 때문에 목록 일부만 반환했는지 나타냅니다.
}
```

Plan 결과 예시:

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "plans": [], // Plan 목록입니다.
  "total": 0, // 필터에 일치하는 전체 항목 수
  "limit": 50, // 페이지 최대 항목 수
  "truncated": false // limit 때문에 목록 일부만 반환했는지 나타냅니다.
}
```

Step 결과 예시(한 스냅샷의 정의 순서, limit=1):

```jsonc
{
  "status": "success",
  "plan_id": "plan_example",
  "loop_no": 1,
  "revision": 7,
  "read_only": false,
  "steps": [
    {
      "step_id": "step_example",
      "step_type": "inspect_context",
      "name": "현황 확인",
      "status": "completed",
      "loop_no": 1
    }
  ],
  "total": 4,
  "limit": 1,
  "truncated": true,
  "next_step_guide": "plan_05-get tool의 request에 target='step', 이 plan_id와 선택한 step_id를 입력합니다. 같은 스냅샷을 상세 조회하려면 반환된 loop_no·revision과 include_details=true를 함께 넣습니다."
}
```

## 74. plan_09-rename_artifact_folder

기준 API: `plan_09-rename_artifact_folder`

근거: src/mcp/runtime/mcp_server.py

### DESCRIPTION

Plan 산출물 폴더를 옮기거나 이름을 바꾸고 저장된 참조를 갱신합니다. 실행된 회차가 있으면 변경할 수 없습니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "name": {
      "type": "string",
      "description": "Plan 산출물 폴더의 새 이름입니다. 날짜 접두사는 런타임이 관리합니다. 소유한 폴더를 이동하고 관련된 저장 참조를 갱신합니다."
    },
    "plan_id": {
      "default": "",
      "type": "string",
      "description": "선택 사항인 Plan ID입니다. 비어 있으면 현재 선택된 작업 Plan을 사용합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "name"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "artifact_dir": ".almond/produced/261111_example-new", // 변경 후 산출물 폴더 경로입니다.
  "previous_artifact_dir": ".almond/produced/261111_example-old", // 변경 전 폴더 경로입니다. 실제 변경이 있을 때 반환합니다.
  "next_step_guide": "이후 산출물 작업에는 갱신된 artifact_dir를 사용합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 83. plan_10-set_working

기준 API: `plan_10-set_working`

근거: src/mcp/runtime/mcp_server.py

### DESCRIPTION

Plan 또는 Step을 산출물 작업 공간으로 선택합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "plan_id": {
      "type": "string",
      "description": "plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다."
    },
    "step_id": {
      "default": "",
      "type": "string",
      "description": "선택할 Step ID입니다. 생략하면 Plan만 선택합니다."
    },
    "artifact_name": {
      "default": "",
      "type": "string",
      "description": "Plan의 최초 산출물 폴더 이름입니다. 생략하면 목표에서 정하고 날짜 접두사 YYMMDD_를 붙입니다. 기존 폴더는 재사용합니다."
    },
    "loop_no": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 사항인 현재 Loop 번호 보호 검사입니다. 이전 또는 알 수 없는 Loop는 쓰기 대상으로 선택할 수 없습니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "plan_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "plan_id": "plan_example", // Plan ID
  "step_id": "step_example", // 선택한 Step. Step 미선택이면 빈 문자열
  "loop_no": 1, // Loop 회차 번호
  "revision": 2, // 작업 공간 설정 후의 저장 리비전입니다.
  "artifact_dir": ".almond/produced/261111_example/01", // 현재 연결의 산출물 폴더입니다. execute_project_python의 작업 디렉터리로 사용합니다.
  "plan_artifact_dir": ".almond/produced/261111_example", // Plan 산출물 루트입니다. Loop 시작 전에는 이 폴더를 사용합니다.
  "next_step_guide": "이 artifact_dir에서 작업하고, plan_12-update tool의 request에 target='step', plan_id, step_id와 재사용한 파일은 input_refs.add, 새 산출물은 output_refs.add로 기록합니다. 기록할 Step ID가 없으면 먼저 plan_08-list tool의 request에 target='step', 같은 plan_id·loop_no를 넣어 목록에서 Step을 선택합니다. 근거를 얻은 작업 맥락의 loop_no를 유지해 request.loop_no로 함께 전달합니다. expected_revision 검사도 사용할 경우 plan_05-get tool의 request에 같은 target·ID·loop_no를 넣어 조회한 최신 revision을 사용합니다. Loop가 바뀌었으면 기록 대상을 먼저 재검토합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 88. plan_12-update

기준 API: `plan_12-update`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

Phase·Plan의 작업 정보 또는 Step의 상태와 입력·출력 근거를 수정합니다. 기존 Loop·리비전 보호와 부분 적용 보고를 유지합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "request": {
      "oneOf": [
        {
          "additionalProperties": false,
          "properties": {
            "target": {
              "const": "phase",
              "description": "작업할 대상 종류입니다.",
              "type": "string"
            },
            "phase_id": {
              "description": "plan_08-list tool에 request.target=phase로 조회한 phases[].phase_id 또는 plan_05-get tool의 id에서 얻은 기존 Phase ID입니다.",
              "type": "string"
            },
            "name": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "선택 사항인 비어 있지 않은 대체 Phase 이름입니다."
            },
            "description": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "선택 사항인 대체 설명입니다. 비어 있으면 지웁니다."
            },
            "file_name": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "이 Phase가 속한 Rhino 파일명입니다. 문자열 하나 또는 문자열 배열로 입력합니다. [] 또는 \"\"는 연결 해제, 생략/null은 유지입니다."
            },
            "status": {
              "anyOf": [
                {
                  "enum": [
                    "pending",
                    "running",
                    "paused",
                    "completed",
                    "failed",
                    "blocked"
                  ],
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. 생략하거나 null이면 유지합니다."
            },
            "depends_on": {
              "anyOf": [
                {
                  "additionalProperties": false,
                  "description": "문자열 목록의 추가·제거 패치입니다. 생략한 연산과 빈 배열은 현재 값을 유지합니다.",
                  "properties": {
                    "add": {
                      "description": "추가할 문자열 배열입니다. 이미 존재하거나 중복·유효하지 않은 값은 건너뛰고 issues로 보고합니다. remove에도 있는 값은 양쪽에서 건너뜁니다.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "remove": {
                      "description": "제거할 기존 문자열 배열입니다. 없는 값이나 중복·유효하지 않은 값은 건너뛰고 issues로 보고합니다. 생략하거나 빈 배열이면 유지합니다.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    }
                  },
                  "type": "object"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Phase ID만 사용하는 선택 사항인 {add: string[], remove: string[]} 패치입니다. 충돌하거나 유효하지 않은 문자열 항목은 보고하고 건너뜁니다. 잘못된 타입은 요청 전체를 거부합니다. 같은 종류의 ID 형식만 검사하며 대상의 존재·자기 참조·순환을 검사하거나 실행 순서·완료를 강제하지 않습니다."
            },
            "previous_id": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "이전 Phase ID입니다. 생략/null이면 유지하고 빈 문자열이면 해제합니다."
            }
          },
          "required": [
            "target",
            "phase_id"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "target": {
              "const": "plan",
              "description": "작업할 대상 종류입니다.",
              "type": "string"
            },
            "plan_id": {
              "description": "plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다.",
              "type": "string"
            },
            "goal": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "선택 사항인 비어 있지 않은 대체 전체 목표입니다."
            },
            "phase_id": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "선택 사항인 기존 Phase ID입니다. 비어 있으면 Phase 소속을 해제하고, 생략/null이면 유지합니다."
            },
            "scene_ids": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Plan의 작업 맥락이 되는 기존 Scene ID 배열로 교체합니다. []이면 비우고 생략/null이면 유지합니다."
            },
            "holon_ids": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "선택 사항인 대체 Plan Holon 대상 배열입니다. []이면 비우고 생략/null이면 유지합니다."
            },
            "expected_revision": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "현재 조회한 리비전 번호입니다. 현재 값과 다르면 변경을 거부합니다. 선택 사항이며, Loop 실행 후 이 검사를 사용하려면 loop_no도 입력합니다."
            },
            "depends_on": {
              "anyOf": [
                {
                  "additionalProperties": false,
                  "description": "문자열 목록의 추가·제거 패치입니다. 생략한 연산과 빈 배열은 현재 값을 유지합니다.",
                  "properties": {
                    "add": {
                      "description": "추가할 문자열 배열입니다. 이미 존재하거나 중복·유효하지 않은 값은 건너뛰고 issues로 보고합니다. remove에도 있는 값은 양쪽에서 건너뜁니다.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "remove": {
                      "description": "제거할 기존 문자열 배열입니다. 없는 값이나 중복·유효하지 않은 값은 건너뛰고 issues로 보고합니다. 생략하거나 빈 배열이면 유지합니다.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    }
                  },
                  "type": "object"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "Plan ID만 사용하는 선택 사항인 {add: string[], remove: string[]} 패치입니다. 문자열 항목에 문제가 있으면 건너뛰고 보고합니다. 같은 종류의 ID 형식만 검사하며 대상의 존재·자기 참조·순환을 검사하거나 실행 순서·완료를 강제하지 않습니다."
            },
            "status": {
              "anyOf": [
                {
                  "enum": [
                    "pending",
                    "running",
                    "paused",
                    "completed",
                    "failed",
                    "blocked"
                  ],
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. completed는 사용자의 완료 결정 후 지정합니다. 생략/null은 유지입니다."
            },
            "artifact_refs": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "선택 사항인 대체 산출물 참조 문자열 배열입니다. []이면 비우고 생략/null이면 유지합니다."
            },
            "title": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "선택 사항인 비어 있지 않은 대체 짧은 제목입니다."
            },
            "previous_id": {
              "anyOf": [
                {
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "이전 Plan ID입니다. 생략/null이면 유지하고 빈 문자열이면 해제합니다."
            },
            "parent_plan": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "이 Plan에 기록할 대체 상위 Plan ID 배열입니다. 생략/null이면 유지하고 []이면 비웁니다. 상대 Plan을 자동으로 수정하거나 참조 대상의 존재를 검증하지 않습니다."
            },
            "child_plan": {
              "anyOf": [
                {
                  "items": {
                    "type": "string"
                  },
                  "type": "array"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "이 Plan에 기록할 대체 하위 Plan ID 배열입니다. 생략/null이면 유지하고 []이면 비웁니다. 상대 Plan을 자동으로 수정하거나 참조 대상의 존재를 검증하지 않습니다."
            },
            "loop_no": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "선택 사항인 현재 Loop 번호 보호 검사입니다. 이전 또는 알 수 없는 Loop는 모두 거부합니다. Loop 실행 후 expected_revision을 입력할 때 함께 지정합니다. 둘 다 생략하면 현재 상태를 수정합니다."
            }
          },
          "required": [
            "target",
            "plan_id"
          ],
          "type": "object"
        },
        {
          "additionalProperties": false,
          "properties": {
            "target": {
              "const": "step",
              "description": "작업할 대상 종류입니다.",
              "type": "string"
            },
            "plan_id": {
              "description": "plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다.",
              "type": "string"
            },
            "step_id": {
              "description": "선택한 Plan의 상세 결과에서 얻은 Step ID입니다. 해당 Plan ID와 함께 사용합니다.",
              "type": "string"
            },
            "status": {
              "anyOf": [
                {
                  "enum": [
                    "pending",
                    "running",
                    "paused",
                    "completed",
                    "failed",
                    "blocked"
                  ],
                  "type": "string"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. 생략하거나 null이면 유지합니다."
            },
            "input_refs": {
              "anyOf": [
                {
                  "additionalProperties": false,
                  "description": "문자열 목록의 추가·제거 패치입니다. 생략한 연산과 빈 배열은 현재 값을 유지합니다.",
                  "properties": {
                    "add": {
                      "description": "추가할 문자열 배열입니다. 이미 존재하거나 중복·유효하지 않은 값은 건너뛰고 issues로 보고합니다. remove에도 있는 값은 양쪽에서 건너뜁니다.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "remove": {
                      "description": "제거할 기존 문자열 배열입니다. 없는 값이나 중복·유효하지 않은 값은 건너뛰고 issues로 보고합니다. 생략하거나 빈 배열이면 유지합니다.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    }
                  },
                  "type": "object"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "입력 근거 문자열의 선택 사항인 {add: string[], remove: string[]} 패치입니다. 생략/null/{}이면 변경하지 않습니다. 유효하지 않은 문자열 항목은 건너뛰고 보고합니다."
            },
            "output_refs": {
              "anyOf": [
                {
                  "additionalProperties": false,
                  "description": "문자열 목록의 추가·제거 패치입니다. 생략한 연산과 빈 배열은 현재 값을 유지합니다.",
                  "properties": {
                    "add": {
                      "description": "추가할 문자열 배열입니다. 이미 존재하거나 중복·유효하지 않은 값은 건너뛰고 issues로 보고합니다. remove에도 있는 값은 양쪽에서 건너뜁니다.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    },
                    "remove": {
                      "description": "제거할 기존 문자열 배열입니다. 없는 값이나 중복·유효하지 않은 값은 건너뛰고 issues로 보고합니다. 생략하거나 빈 배열이면 유지합니다.",
                      "items": {
                        "type": "string"
                      },
                      "type": "array"
                    }
                  },
                  "type": "object"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "출력 근거 문자열의 선택 사항인 {add: string[], remove: string[]} 패치입니다. 생략/null/{}이면 변경하지 않습니다. [] 형식의 전체 교체 배열은 허용하지 않습니다."
            },
            "expected_revision": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "현재 조회한 리비전 번호입니다. 현재 값과 다르면 변경을 거부합니다. 선택 사항이며, Loop 실행 후 이 검사를 사용하려면 loop_no도 입력합니다."
            },
            "loop_no": {
              "anyOf": [
                {
                  "type": "integer"
                },
                {
                  "type": "null"
                }
              ],
              "default": null,
              "description": "선택 사항인 현재 Loop 번호 보호 검사입니다. 이전 또는 알 수 없는 Loop는 모두 거부합니다. Loop 실행 후 expected_revision을 입력할 때 함께 지정합니다. 둘 다 생략하면 현재 상태를 수정합니다."
            }
          },
          "required": [
            "target",
            "plan_id",
            "step_id"
          ],
          "type": "object"
        }
      ],
      "description": "target으로 phase, plan, step을 선택하고 해당 ID와 바꿀 필드만 입력합니다. Step은 상태와 문자열 목록 패치로 기록을 갱신합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "request"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

Phase 결과 예시:

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "changed": true, // 실제 저장 변경 여부. status=success여도 false일 수 있음
  "phase": { // 수정한 Phase의 확인 정보입니다.
    "phase_id": "phase_example",
    "status": "pending"
  },
  "issues": [], // 적용하지 못한 패치 항목입니다. 나머지 항목은 적용되었을 수 있습니다.
  "next_step_guide": "plan_05-get tool의 request에 target='phase'과 해당 phase_id를 넣어 변경된 기록을 확인할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

Plan 결과 예시:

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "changed": true, // 실제 변경일 때만 리비전 하나 생성. success여도 false일 수 있음
  "plan": { // 수정한 Plan의 확인 정보입니다.
    "plan_id": "plan_example",
    "status": "pending",
    "loop_no": 1,
    "revision": 2
  },
  "issues": [], // 적용하지 못한 패치 항목입니다. 나머지 항목은 적용되었을 수 있습니다.
  "next_step_guide": "plan_05-get tool의 request에 target='plan'과 해당 plan_id를 넣어 변경된 기록을 확인할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

Step 결과 예시:

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "changed": true, // 실제 변경일 때만 Plan 리비전 하나 생성. success여도 false일 수 있음
  "plan": { // 수정한 Step이 속한 Plan의 확인 정보입니다.
    "plan_id": "plan_example",
    "status": "pending",
    "loop_no": 1,
    "revision": 2
  },
  "issues": [], // 적용하지 못한 패치 항목입니다. 나머지 항목은 적용되었을 수 있습니다.
  "step": { // 수정한 Step의 확인 정보입니다.
    "step_id": "step_example",
    "status": "pending",
    "loop_no": 1
  },
  "next_step_guide": "다음에 수행할 Step을 정했다면 plan_10-set_working tool으로 선택합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

# Inspect

Rhino 문서·객체·선택 조회 · prefix: `inspect_NN-` · 유형 내 순번 01–05

## 06. inspect_01-analyze_nested_blocks

기준 API: `inspect_01-analyze_nested_blocks`

근거: src/mcp/features/context/tools.py

### DESCRIPTION

중첩 블록 구조와 특정 배치 경로의 공유 정의 영향을 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "mode": {
      "type": "string",
      "description": "outline은 중첩 블록 구조, resolve-block은 지정한 배치 경로의 공유 정의 영향을 조회합니다."
    },
    "options": {
      "additionalProperties": true,
      "type": "object",
      "description": "outline: ids(루트 GUID 배열) 또는 path(배치 GUID 경로)를 선택합니다. 둘 다 없으면 scope=selected|viewport|document로 범위를 정합니다. depth=0..64, max_items=1..5000, max_bytes=2048..262144이며 기본값은 각각 64, 200, 48000입니다. field_groups는 summary, objects, annotations, transforms 중 선택한 비어 있지 않은 배열입니다. include_geometry/annotations는 상세 포함 여부, annotation_layer는 텍스트 도트의 레이어 필터입니다. resolve-block: 최상위에서 내부 방향의 배치 GUID 1..65개를 path에 입력합니다."
    },
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "mode",
    "options"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "mode": "outline", // 선택한 분석 모드입니다.
  "document": { // 관찰한 문서 정보입니다.
    "units": "Millimeters",
    "absolute_tolerance": 0.01
  },
  "data": { // 선택한 블록 분석 모드의 결과입니다.
    "records": [
      {
        "kind": "occurrence",
        "id": "123e4567-e89b-42d3-a456-426614174000",
        "type": "InstanceReference",
        "path": [
          "123e4567-e89b-42d3-a456-426614174000"
        ],
        "definition": "예시 블록"
      }
    ],
    "items": 1,
    "truncated": false
  },
  "next_step_guide": "블록 편집에 들어간 뒤에는 inspect_02-get_objects tool로 현재 편집 대상 ID를 다시 조회합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 39. inspect_02-get_objects

기준 API: `inspect_02-get_objects`

근거: src/mcp/features/context/tools.py

### DESCRIPTION

Rhino 객체와 모델 구성을 관찰합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "scope": {
      "default": "current",
      "type": "string",
      "description": "current(기본값)는 화면 밖에 있더라도 표시 상태이고 잠기지 않은 모델 객체를 포함합니다. document는 숨김/잠금 객체도 포함합니다."
    },
    "object_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "document 범위에서만 사용할 수 있는 선택 사항인 서로 다른 최상위 객체 GUID입니다(1..4096개). group_ids와 함께 사용하지 않습니다."
    },
    "filters": {
      "anyOf": [
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "AND 조건입니다. layer_paths(정확한 전체 경로), object_types(관찰된 Rhino 이름), name_contains(대소문자 구분 없음), user_dictionary(source=attributes|geometry, key, 스칼라 any_of)를 사용할 수 있습니다."
    },
    "include_geometry": {
      "default": false,
      "type": "boolean",
      "description": "fields를 생략했을 때 objects 모드에서 형상 상세 정보를 포함합니다. 명시적인 fields가 우선합니다."
    },
    "offset": {
      "default": 0,
      "type": "integer",
      "description": "행 오프셋으로, 범위는 0..100000입니다. 0보다 큰 값에는 첫 페이지의 expected_snapshot이 필요합니다."
    },
    "limit": {
      "default": 50,
      "type": "integer",
      "description": "페이지당 행 수입니다. 범위는 1..200이며 기본값은 50입니다."
    },
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다."
    },
    "result_mode": {
      "default": "objects",
      "type": "string",
      "description": "objects(기본값), hierarchy 또는 summary입니다. recursive=true는 hierarchy를 선택하며 summary와 함께 사용할 수 없습니다."
    },
    "fields": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 사항인 비어 있지 않은 필드 목록입니다. id, name, layer_path, object_type, geometry_kind, geometry_crc, visible, selected, hidden, locked, bounds, groups, user_dictionary, geometry_valid, solid, manifold, volume, faces, face_count를 사용할 수 있습니다. 형상 상세 정보와 faces에는 objects 모드가 필요합니다. summary는 fields를 거부합니다."
    },
    "face_offset": {
      "default": 0,
      "type": "integer",
      "description": "면 페이지 오프셋이며 기본값은 0입니다. 두 번째 이후 면 페이지에는 document 범위의 object_ids와 모든 객체에 대한 expected_geometry_crcs가 필요합니다."
    },
    "face_limit": {
      "default": 128,
      "type": "integer",
      "description": "객체별 페이지의 면 수입니다. 범위는 1..128이며 기본값은 128입니다. 면 옵션에는 objects 모드가 필요합니다."
    },
    "expected_geometry_crcs": {
      "anyOf": [
        {
          "additionalProperties": {
            "type": "integer"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "요청한 각 객체 GUID를 키로 하는 관찰된 CRC입니다. 면을 페이지 단위로 조회하는 동안 형상이 변경되면 거부합니다."
    },
    "group_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "어느 scope에서든 사용할 수 있는 선택 사항인 서로 다른 Rhino 그룹 GUID입니다(1..64개). 구성원과 선택한 범위의 교집합을 사용합니다. object_ids와 함께 사용하지 않습니다."
    },
    "selected": {
      "default": false,
      "type": "boolean",
      "description": "current에서만 사용하며 기본값은 false입니다. 화면 밖의 선택도 포함하여 적격한 선택 객체로 필터링합니다. inside_window와 함께 사용할 수 없습니다."
    },
    "inside_window": {
      "default": false,
      "type": "boolean",
      "description": "current에서만 사용하며 기본값은 false입니다. 활성 뷰포트 경계에 걸친 바운딩 박스를 포함합니다. 클리핑 평면이나 픽셀 가림 검사는 수행하지 않습니다. selected와 함께 사용할 수 없습니다."
    },
    "recursive": {
      "default": false,
      "type": "boolean",
      "description": "그룹과 블록 배치 인스턴스를 계층 구조로 함께 펼칩니다. 기본값은 false입니다."
    },
    "depth": {
      "default": 1,
      "type": "integer",
      "description": "계층 깊이는 1..8이며 루트는 1입니다. 1보다 큰 값에는 recursive=true가 필요합니다."
    },
    "expected_snapshot": {
      "default": "",
      "type": "string",
      "description": "첫 페이지에서는 생략합니다. 이후 offset 페이지에는 첫 페이지의 snapshot 토큰을 변경 없이 전달합니다. 스냅샷이 변경되면 이어서 조회하는 요청을 거부합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "scope": "document", // 이번 조회에서 관찰한 객체 범위입니다.
  "objects": [ // 조회한 객체와 요청한 속성입니다.
    {
      "id": "123e4567-e89b-42d3-a456-426614174000",
      "geometry_crc": 123456789,
      "face_count": 6,
      "faces": [
        {
          "face_index": 0,
          "planar": true,
          "face_edit_supported": true
        }
      ],
      "faces_truncated": true,
      "face_page": {
        "offset": 0,
        "limit": 1,
        "returned": 1,
        "next_offset": 1,
        "complete": false
      }
    }
  ],
  "matched_count": 1, // 조회 조건에 맞는 객체 수입니다.
  "offset": 0, // 이번 페이지의 시작 위치입니다.
  "limit": 50, // 이번 응답의 최대 항목 수입니다.
  "next_offset": null, // 다음 페이지의 시작 위치입니다. null이면 다음 페이지가 없습니다.
  "snapshot": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", // 후속 offset 페이지의 expected_snapshot에 그대로 전달
  "editing": {}, // 현재 편집 컨텍스트와 저장 대상 정보입니다.
  "complete": true, // 요청한 객체 페이지가 완전한지 나타냅니다. 계층 하위의 관찰 상태는 각 children_state에 있습니다.
  "next_step_guide": "같은 객체 ID와 geometry_crc를 유지하고 face_offset에 face_page.next_offset을 입력해 다음 면을 조회합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 44. inspect_03-get_document_context

기준 API: `inspect_03-get_document_context`

근거: src/mcp/features/context/tools.py

### DESCRIPTION

Rhino 문서와 화면의 현재 상태를 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "sections": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "document, viewport, editor, display_modes, named_views, layouts, viewports 중 필요한 항목의 배열입니다. 생략하면 document, named_views, layouts, display_modes를 조회합니다. []는 status와 warnings만 반환합니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다."
    },
    "include_editor_details": {
      "default": false,
      "type": "boolean",
      "description": "editor를 요청한 경우에만 provider/command/Undo 근거를 포함합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "warnings": [], // 결과를 해석할 때 확인할 경고입니다.
  "document": { // 요청한 현재 문서 속성입니다. 관찰할 수 없는 값은 null입니다.
    "units": "Millimeters",
    "absolute_tolerance": 0.01,
    "modified": false,
    "object_count": 0,
    "layer_count": 1,
    "angle_tolerance": 0.0174532925199433
  },
  "next_step_guide": "현재 화면을 보려면 capture_03-current_view tool를 사용하세요." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 47. inspect_04-get_selection_references

기준 API: `inspect_04-get_selection_references`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

현재 선택한 Rhino 객체와 상위 Holon을 참조하는 Plan을 찾습니다. 저장된 문서의 일반 모델에서 사용합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "selection_limit": {
      "default": 50,
      "type": "integer",
      "description": "검사할 선택된 Rhino 객체의 최대 개수이며, 범위는 1..200입니다."
    },
    "limit": {
      "default": 50,
      "type": "integer",
      "description": "반환할 일치 Plan의 최대 개수이며, 범위는 1..500입니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 사항인 그룹: steps, references, geometry, artifacts, description, scope, audit 또는 all. 생략하거나 비워 두면 요약을 유지합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "objects": [], // 선택한 객체의 ID·등록 여부와 소유 Holon입니다.
  "holons": [], // 선택 객체를 소유한 Holon과 상위 Holon의 요약입니다.
  "plans": [], // 선택 객체를 참조하는 Plan의 요약입니다.
  "total_plans": 0, // 참조 Plan 전체 개수
  "truncated": false, // 현재 응답에서 결과가 잘렸는지 여부
  "ownership_live_verified": false, // 선택 객체 소유 관계의 현재 확인 여부. 선택이 없으면 false
  "references_live_verified": false, // 저장된 Plan·계층 참조를 현재 Rhino에서 확인했는지 나타냅니다.
  "selection_total": 0, // 선택된 객체 전체 수
  "selection_truncated": false // 선택 조회의 일부가 생략되었는지 여부. Plan 목록의 truncated와 별개
}
```

## 76. inspect_05-resolve_targets

기준 API: `inspect_05-resolve_targets`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

Plan에 등록된 Holon 대상 집합을 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "plan_id": {
      "type": "string",
      "description": "plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다."
    },
    "step_id": {
      "default": "",
      "type": "string",
      "description": "선택한 Plan에 속하는지 확인할 Step ID입니다. 생략해도 Plan의 Holon 대상을 조회합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 사항: references, geometry, scope, audit 또는 all. 생략하거나 비워 두면 저장된 Plan 대상 ID를 반환합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "plan_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "plan_id": "plan_example", // Plan ID
  "step_id": null, // Step ID
  "revision": 1, // Plan의 저장 리비전입니다. 변경 검사에는 현재 loop_no도 함께 사용합니다.
  "scene_ids": [], // Plan에 지정한 Scene 컨텍스트입니다.
  "holon_ids": [], // Plan에 명시한 Holon 대상입니다. 빈 배열이면 지정 대상이 없습니다.
  "holons": [], // 저장된 대상 Holon의 요약입니다.
  "live_verified": false, // 대상의 현재 Rhino 상태를 확인했는지 나타냅니다.
  "source": "plan" // 대상 정보의 출처입니다. 현재는 plan입니다.
}
```

# Capture

화면 캡처·시각 검토 · prefix: `capture_NN-` · 유형 내 순번 01–04

## 10. capture_01-conditioning_pass

기준 API: `capture_01-conditioning_pass`

근거: src/mcp/features/capture/tools.py

### DESCRIPTION

Rhino 카메라 경로를 따라 RGB·에지·깊이 프레임과 카메라 기록을 저장합니다. 활성 화면과 출력 파일이 변경됩니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "shot": {
      "type": "string",
      "description": "카메라 경로를 담은 JSON 문자열입니다. type=orbit은 center:[x,y,z], radius, height와 선택적 start_deg/end_deg/lens/target_height; type=track은 cam0/cam1/target0/target1 좌표와 선택적 lens; type=keyframes는 camera·target·선택적 lens를 가진 keyframes 배열입니다. frames 기본값은 81, lens는 mm, 좌표는 문서 단위입니다."
    },
    "out_dir": {
      "default": "",
      "type": "string",
      "description": "관리형 세션: 선택한 Plan의 산출물 디렉터리 아래 상대 폴더이며, 기본값은 conditioning입니다. 먼저 Plan을 선택합니다. 독립 실행: 출력 폴더이며, 기본값은 현재 작업 디렉터리입니다."
    },
    "width": {
      "default": 832,
      "type": "integer",
      "description": "출력 프레임의 픽셀 너비이며, 짝수여야 합니다."
    },
    "height": {
      "default": 480,
      "type": "integer",
      "description": "출력 프레임의 픽셀 높이이며, 짝수여야 합니다."
    },
    "passes": {
      "default": "rgb,edge,depth",
      "type": "string",
      "description": "쉼표로 구분한 패스 이름: rgb, edge, depth."
    },
    "fps": {
      "default": 16,
      "type": "integer",
      "description": "샷에 기록할 초당 프레임 수입니다."
    },
    "chunk": {
      "default": 16,
      "type": "integer",
      "description": "Rhino 실행 청크마다 캡처할 프레임 수입니다."
    },
    "rgb_mode": {
      "default": "Rendered",
      "type": "string",
      "description": "RGB 프레임에 사용할 설치된 Rhino 디스플레이 모드이며, 기본값은 Rendered입니다."
    },
    "edge_mode": {
      "default": "Technical",
      "type": "string",
      "description": "에지 프레임에 사용할 설치된 Rhino 디스플레이 모드이며, 기본값은 Technical입니다."
    },
    "invert_depth": {
      "default": false,
      "type": "boolean",
      "description": "true이면 깊이 패스를 반전합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "shot"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "frames_requested": 2, // 요청 프레임 수
  "frames_captured": 2, // 성공한 캡처 청크의 프레임 수입니다.
  "passes": [ // 생성한 패스 종류
    "rgb"
  ],
  "resolution": [ // 출력 이미지 해상도 [너비, 높이]
    832,
    480
  ],
  "fps": 16, // 영상 프레임 레이트
  "errors": [], // 실패한 청크의 프레임 범위와 메시지. 부분 생성 파일이 남을 수 있음
  "out_dir": ".almond/produced/261111_example/capture", // 패스별 PNG와 doc.json/camera.json/zrange.csv/summary.json을 쓰는 폴더
  "camera_json": ".almond/produced/261111_example/capture/camera.json", // 전체 계획 경로 기록. frames[].camera/target/lens_mm를 포함하며 부분 캡처에도 계획은 전체 길이
  "videos": { // 완전 캡처 후 패스별 MP4. ffmpeg 조립 실패는 null이며 부분 캡처에는 빈 객체일 수 있음
    "rgb": null
  },
  "document": {}, // 원본 문서·단위·뷰·경계 정보입니다.
  "next_step_guide": "프레임과 camera_json을 확인하고, plan_12-update tool의 request에 target='step', plan_id, step_id와 output_refs.add에 사용할 산출물 경로를 입력합니다. 기록할 Step ID가 없으면 먼저 plan_08-list tool의 request에 target='step', 같은 plan_id·loop_no를 넣어 목록에서 Step을 선택합니다. 근거를 얻은 작업 맥락의 loop_no를 유지해 request.loop_no로 함께 전달합니다. expected_revision 검사도 사용할 경우 plan_05-get tool의 request에 같은 target·ID·loop_no를 넣어 조회한 최신 revision을 사용합니다. Loop가 바뀌었으면 기록 대상을 먼저 재검토합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 11. capture_02-inspection

기준 API: `capture_02-inspection`

근거: src/mcp/features/context/tools.py

### DESCRIPTION

작업 화면을 유지하면서 여러 시점과 객체 범위를 하나의 PNG로 비교합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "views": {
      "items": {
        "additionalProperties": true,
        "type": "object"
      },
      "type": "array",
      "description": "타일 객체 1..16개입니다. direction 기본값은 current이며, 선택지는 current, top, bottom, front, back, left, right, iso_ne, iso_nw, iso_se, iso_sw, below_ne, below_nw, below_se, below_sw입니다. display_mode는 선택 사항인 설치된 이름/GUID(최대 512자)이며, label도 선택 사항(최대 120자)입니다. 선택 사항인 object_ids에는 서로 다른 최상위 GUID 1..512개를 넣습니다. ID를 생략하거나 비워 두면 공통 object_ids가 제공된 경우를 제외하고 문서 가시성을 사용합니다."
    },
    "width": {
      "default": 640,
      "type": "integer",
      "description": "타일의 픽셀 너비로, 범위는 128..2048이며 기본값은 640입니다. 결합 이미지 제한도 적용됩니다."
    },
    "height": {
      "default": 480,
      "type": "integer",
      "description": "타일의 픽셀 높이로, 범위는 128..2048이며 기본값은 480입니다. 결합 이미지 제한도 적용됩니다."
    },
    "columns": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 사항인 열 개수이며, 범위는 1..뷰 개수입니다. 생략하면 자동 격자를 사용합니다."
    },
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다."
    },
    "model_view_id": {
      "default": "",
      "type": "string",
      "description": "선택 사항인, 목록에 있는 모델 뷰포트 GUID입니다. Layout/Detail이 활성화된 경우를 포함하여 해당 뷰포트를 활성화하지 않고 사용합니다."
    },
    "object_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "모든 타일에 공통으로 적용할, 서로 다른 최상위 GUID 1..4096개의 선택 사항인 집합입니다. 비어 있지 않은 타일별 object_ids와 함께 사용하지 않습니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "views"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 이미지 캡처의 처리 상태입니다.
  "complete": true, // 요청한 모든 타일을 캡처했는지 나타냅니다.
  "tiles": [ // 타일별 캡처 결과와 관찰 범위입니다. 실패한 타일도 포함합니다.
    {
      "index": 0,
      "status": "success",
      "direction": "top"
    }
  ],
  "image_file": { // PNG 파일 저장 결과. 이미지 전달과 별개이며 저장 실패여도 이미지가 제공될 수 있음
    "status": "saved",
    "path": ".almond/produced/261111_example/captures/example.png",
    "lifetime": "plan",
    "bytes": 12345,
    "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  },
  "next_step_guide": "보관할 이미지라면 plan_12-update tool의 request에 target='step', plan_id, step_id와 output_refs={add:[image_file.path]}를 입력합니다. 기록할 Step ID가 없으면 먼저 plan_08-list tool의 request에 target='step', 같은 plan_id·loop_no를 넣어 목록에서 Step을 선택합니다. 근거를 얻은 작업 맥락의 loop_no를 유지해 request.loop_no로 함께 전달합니다. expected_revision 검사도 사용할 경우 plan_05-get tool의 request에 같은 target·ID·loop_no를 넣어 조회한 최신 revision을 사용합니다. Loop가 바뀌었으면 기록 대상을 먼저 재검토합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 28. capture_03-current_view

기준 API: `capture_03-current_view`

근거: src/mcp/features/context/tools.py

### DESCRIPTION

현재 모델 화면을 캡처하고 표시 상태를 조정합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "target_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "화면에서 선택·확대할 객체, 그룹 또는 Holon의 ID 배열입니다. 생략하면 현재 화면을 사용하며, 입력할 때는 하나 이상의 ID를 지정합니다."
    },
    "target_kind": {
      "default": "object",
      "type": "string",
      "description": "target_ids의 종류입니다. object, group, block, holon 중 선택합니다. block에는 배치 객체 ID를 입력합니다."
    },
    "isolate": {
      "default": false,
      "type": "boolean",
      "description": "기본값은 false입니다. true이면 Zoom Selected 전에 실제 Rhino Isolate를 실행합니다. 가시성을 복원하려면 Unisolate를 사용합니다."
    },
    "scale_percent": {
      "default": 75,
      "type": "integer",
      "description": "이미지 해상도의 백분율입니다. 1..100 범위이며 기본값은 75입니다."
    },
    "include_usage": {
      "default": false,
      "type": "boolean",
      "description": "true이면 이미지 크기와 픽셀 기준 토큰 추정치를 포함합니다."
    },
    "display_mode": {
      "default": "",
      "type": "string",
      "description": "선택 사항인 설치된 래스터 모드 이름/ID입니다. 제공하면 실제 모델 뷰포트를 변경합니다."
    },
    "labels": {
      "default": false,
      "type": "boolean",
      "description": "선택 사항인 일시적 레이블이며 기본값은 false입니다. 선택 강조 표시는 Rhino의 기본 표시를 유지합니다."
    },
    "depth": {
      "default": 1,
      "type": "integer",
      "description": "레이블 확장 깊이이며, 범위는 1..8입니다."
    },
    "width": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "이미지의 픽셀 너비입니다. 128..2048 범위이며 height도 입력하고 scale_percent=100으로 지정합니다."
    },
    "height": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "이미지의 픽셀 높이입니다. 128..2048 범위이며 width도 입력하고 scale_percent=100으로 지정합니다."
    },
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). 대상 선택·격리 후 기본 선택 확대와 대상 경계 확대가 모두 실패해 캡처하지 않은 경우입니다. 현재 뷰와 선택 상태부터 확인합니다. 성공하면 `view_change.zoom_method`는 기본 선택 확대인 `selected` 또는 기본 방식 실패 뒤 같은 대상의 경계로 확대한 `bounding_box`입니다. //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "error", // 이미지 캡처의 처리 상태입니다.
  "error_code": "component_focus_error", // 오류 유형입니다.
  "message": "Rhino could not zoom to the selected Components or their bounds.", // 현재 결과 또는 오류의 설명입니다.
  "mutation_applied": null, // 뷰 변경 적용 여부입니다. null이면 중간 상태를 확인해야 합니다.
  "requires_reconciliation": true, // true이면 현재 Rhino 상태를 확인한 뒤 다음 작업을 정합니다.
  "failed_stage": "zoom_selected", // 실패한 단계입니다: validate, select, isolate, verify_selection, zoom_selected, redraw.
  "view_change": { // 이 호출에서 완료한 뷰 작업입니다. null인 항목은 시도 후 완료를 확인하지 못했습니다.
    "selection_changed": true,
    "isolated": true,
    "zoom_selected": null,
    "display_mode_changed": false,
    "restore_visibility_command": "Unisolate"
  },
  "focus_observation": { // 포커스 실행 전후에 확인한 대상과 뷰 상태입니다.
    "zoom_extents_selected": false, // 기본 선택 확대의 관측 결과입니다. null이면 완료 여부를 확인하지 못했습니다.
    "zoom_bounding_box": false, // 대상 경계 확대의 관측 결과입니다. null이면 완료 여부를 확인하지 못했습니다.
    "target_count": 2,
    "target_bounds": {
      "min": [
        0,
        0,
        0
      ],
      "max": [
        3000,
        1000,
        0
      ]
    },
    "before_zoom": {
      "viewport_id": "00000000-0000-0000-0000-000000000001",
      "parallel_projection": true,
      "camera_location": [
        1500,
        500,
        1000
      ],
      "camera_target": [
        1500,
        500,
        0
      ],
      "frustum": [
        -100,
        100,
        -75,
        75,
        1,
        10000
      ]
    }
  }
}
```

## 29. capture_04-defined_view

기준 API: `capture_04-defined_view`

근거: src/mcp/features/context/tools.py

### DESCRIPTION

저장된 Named View 또는 Layout 용지를 작업 화면 전환 없이 캡처합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "target_kind": {
      "type": "string",
      "description": "named_view는 저장된 카메라를 사용하며, display_mode가 제공되지 않으면 기본값은 Shaded입니다. layout은 각 Detail의 기존 모드를 유지하며 display_mode 재정의를 허용하지 않습니다."
    },
    "target": {
      "type": "string",
      "description": "기존 이름 또는 ID입니다. 대소문자를 구분하지 않는 이름 일치는 유일해야 합니다."
    },
    "scale_percent": {
      "default": 75,
      "type": "integer",
      "description": "범위는 1..100이며 기본값은 75입니다. 원하는 상한이며, 백분율 캡처는 전달 용량 제한에 맞게 축소될 수 있습니다."
    },
    "include_usage": {
      "default": false,
      "type": "boolean",
      "description": "true이면 이미지 크기와 픽셀 기준 토큰 추정치를 포함합니다."
    },
    "display_mode": {
      "default": "",
      "type": "string",
      "description": "Named View 전용: 생략하거나 비워 두면 Shaded를 선택하며, 다른 설치된 래스터 모드 이름/ID를 제공할 수도 있습니다. 단면 검토 시 display_modes에서 확인한 뒤 AGENT_Section_Glass를 고려합니다. Layout: 각 Detail의 기존 모드를 유지하려면 생략합니다. 재정의는 거부됩니다."
    },
    "labels": {
      "default": false,
      "type": "boolean",
      "description": "선택 사항인 일시적 엔터티 레이블이며, 기본값은 false입니다."
    },
    "depth": {
      "default": 1,
      "type": "integer",
      "description": "엔터티 레이블 확장 깊이이며, 범위는 1..8입니다."
    },
    "width": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 사항인 Named View의 픽셀 너비로, 범위는 128..2048입니다. height도 제공하고 scale_percent=100으로 설정합니다. Layout에는 사용하지 않습니다."
    },
    "height": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 사항인 Named View의 픽셀 높이로, 범위는 128..2048입니다. width도 제공하고 scale_percent=100으로 설정합니다. Layout에는 사용하지 않습니다."
    },
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "target_kind",
    "target"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "image_file": { // PNG 저장 결과입니다. 실제 치수와 축소 경고는 캡처 메타데이터에서 확인합니다.
    "status": "saved",
    "path": ".almond/produced/261111_example/captures/example.png",
    "lifetime": "plan",
    "bytes": 12345,
    "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  },
  "next_step_guide": "보관할 이미지라면 plan_12-update tool의 request에 target='step', plan_id, step_id와 output_refs={add:[image_file.path]}를 입력합니다. 기록할 Step ID가 없으면 먼저 plan_08-list tool의 request에 target='step', 같은 plan_id·loop_no를 넣어 목록에서 Step을 선택합니다. 근거를 얻은 작업 맥락의 loop_no를 유지해 request.loop_no로 함께 전달합니다. expected_revision 검사도 사용할 경우 plan_05-get tool의 request에 같은 target·ID·loop_no를 넣어 조회한 최신 revision을 사용합니다. Loop가 바뀌었으면 기록 대상을 먼저 재검토합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

# Model

모델링 설정·재료·형상 편집 · prefix: `model_NN-` · 유형 내 순번 01–05

## 08. model_01-assign_material

기준 API: `model_01-assign_material`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

Rhino 객체에 라이브러리 재료를 적용합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "guids": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "description": "할당할 현재 Rhino 객체 GUID입니다. 관찰 결과나 생성 결과를 재사용합니다."
    },
    "material_id": {
      "type": "string",
      "description": "model_04-list_materials tool(include_ids=true)에서 얻은 라이브러리의 표준 재료 ID입니다."
    },
    "apply_render_material": {
      "default": true,
      "type": "boolean",
      "description": "true이면 지정된 객체에 표준 렌더 재료를 적용합니다."
    },
    "attach_metadata": {
      "default": false,
      "type": "boolean",
      "description": "true이면 Almond 재료/구축 메타데이터를 부착합니다. false이면 요청한 렌더 재료만 적용합니다."
    },
    "structural_role": {
      "default": "",
      "type": "string",
      "description": "선택 사항인 구조 역할 메타데이터이며, attach_metadata와 함께 사용합니다."
    },
    "construction_system": {
      "default": "",
      "type": "string",
      "description": "알려진 구축 시스템 ID입니다. attach_metadata=true일 때 사용합니다. construction_reference를 함께 지정하면 같은 시스템이어야 합니다."
    },
    "floor": {
      "default": "",
      "type": "string",
      "description": "선택 사항인 층 레이블 메타데이터이며, attach_metadata와 함께 사용합니다."
    },
    "construction_detail": {
      "default": "",
      "type": "string",
      "description": "선택 사항인 구축 상세 설명이며, attach_metadata와 함께 사용합니다."
    },
    "construction_reference": {
      "anyOf": [
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "{\"kind\":\"construction_system\",\"id\":\"확인한 system_id\"} 형식의 출처 참조입니다. attach_metadata=true일 때 사용합니다. construction_system도 지정하면 같은 시스템이어야 합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "guids",
    "material_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "material_id": "example-material", // 라이브러리 재료 ID
  "applied_count": 1, // 처리 성공한 객체 수. requested_count와 비교하며 실제 변경 수와 구분
  "requested_count": 1, // 요청한 수
  "render_material_applied": true, // 렌더 재료를 적용하도록 요청했는지 나타냅니다.
  "material_metadata_attached": false, // 재료 메타데이터가 부착됐는지 여부
  "rhino_material_name": "예시 재료", // Rhino에 적용한 재료명
  "ue_material_slot": "example-slot", // 재료 슬롯명
  "applied_guids": [ // 처리가 성공한 객체 GUID입니다. 실제 변경이 확인된 객체는 changed_guids에 있습니다.
    "00000000-0000-0000-0000-000000000001"
  ],
  "metadata_attached": false, // 요청한 메타데이터 적용 여부입니다.
  "layer_path": "Example layer", // 대상의 레이어 경로입니다. 제공되지 않으면 null입니다.
  "next_step_guide": "inspect_02-get_objects tool로 적용된 재료를 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 16. model_02-edit_planar_face

기준 API: `model_02-edit_planar_face`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

닫힌 Brep의 평면 한 면을 PushPull Extend로 이동합니다. 그룹·블록 편집을 종료한 일반 모델에서 사용합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "object_id": {
      "type": "string",
      "description": "연결된 문서의 관찰 결과에서 얻은 현재 잠기지 않은 최상위 닫힌 Brep GUID입니다."
    },
    "face_index": {
      "type": "integer",
      "description": "expected_geometry_crc와 동일한 형상 관찰 결과에서 얻은 0부터 시작하는 평면 인덱스입니다."
    },
    "expected_geometry_crc": {
      "type": "integer",
      "description": "해당 관찰 결과의 형상 CRC입니다. 형상이 변경되었으면 교체 전에 편집을 거부합니다."
    },
    "translation": {
      "items": {
        "anyOf": [
          {
            "type": "number"
          },
          {
            "type": "integer"
          }
        ]
      },
      "type": "array",
      "description": "문서 단위의 유한한 XYZ 숫자 3개입니다. 면 법선 방향 성분이 문서 허용오차를 초과해야 합니다."
    },
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "object_id",
    "face_index",
    "expected_geometry_crc",
    "translation"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "result": { // 단일 면의 편집 결과입니다.
    "edited": true,
    "object_id": "00000000-0000-0000-0000-000000000001",
    "previous_geometry_crc": 123,
    "geometry_crc": 456
  },
  "next_step_guide": "inspect_02-get_objects tool로 변경된 형상과 CRC를 다시 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 17. model_03-edit_planar_faces

기준 API: `model_03-edit_planar_faces`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

서로 다른 닫힌 Brep의 평면을 한 면씩 단일 Undo 기록으로 이동합니다. 그룹·블록 편집을 종료한 일반 모델에서 사용합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "edits": {
      "items": {
        "additionalProperties": true,
        "type": "object"
      },
      "type": "array",
      "description": "서로 다른 Brep에 대한 항목 1..32개이며, 각 항목에는 object_id, face_index, expected_geometry_crc 및 translation이 들어갑니다. 단일 면 도구의 적용 대상 조건이 적용됩니다."
    },
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "edits"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "result": { // 배치 결과. 준비 실패는 교체 전이며 교체 중 실패는 부분 적용일 수 있음
    "status": "success",
    "complete": true,
    "requested_count": 1,
    "applied_count": 1,
    "mutation_state": "applied",
    "items": [
      {
        "status": "applied",
        "edited": true,
        "previous_geometry_crc": 123,
        "geometry_crc": 456
      }
    ]
  },
  "next_step_guide": "inspect_02-get_objects tool로 변경된 객체의 형상과 CRC를 다시 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 58. model_04-list_materials

기준 API: `model_04-list_materials`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

라이브러리에서 사용할 재료를 찾습니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "default": "",
      "type": "string",
      "description": "선택 사항인 라이브러리 분류 필터입니다. 비워 두면 모든 분류를 포함합니다."
    },
    "query": {
      "default": "",
      "type": "string",
      "description": "자유 텍스트 검색어입니다. 비워 두면 텍스트 필터를 설정하지 않습니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 사항인 상세 그룹: display, physical, metadata, source, paths, audit 또는 all. 생략하거나 비워 두면 요약을 조회합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

기본 include_ids=false로 조회한 예시입니다. 재료 ID가 필요하면 안내에 따라 include_ids=true로 조회합니다.

```jsonc
{
  "total": 1, // 조건에 일치하는 라이브러리 재료 수입니다.
  "materials": [ // 재료의 이름·분류와 요청한 속성입니다.
    {
      "name": "예시 재료",
      "category": "wood"
    }
  ],
  "next_step_guide": "재료를 적용하려면 include_ids=true로 재료 ID를 조회해 model_01-assign_material tool에 사용합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 84. model_05-setup

기준 API: `model_05-setup`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

정의된 Material과 구축 Layer를 Rhino 문서에 등록·정렬합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "overwrite": {
      "type": "boolean",
      "description": "Material과 Layer 모두에 적용되는 필수 불리언입니다. false는 기존 값을 유지하고, 없는 항목을 만들며, 차이를 보고합니다. true는 사전 정의된 속성을 갱신합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "overwrite"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). overwrite=false에서 기존 재료 속성을 보존하고 누락된 레이어는 생성했으나, 요청 속성과 차이가 남은 경우입니다. //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "incomplete", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "applied": false, // 모든 지정 속성이 일치하는지 여부. false여도 누락 항목 생성·일부 변경이 있었을 수 있음
  "changes": [ // 재료 레시피별 RenderMaterial과 지정 레이어 경로의 처리 내역입니다. 레이어 재료 할당으로 추가될 수 있는 Rhino Materials 테이블 레코드는 집계하지 않습니다. 이 필드가 없으면 변경 내역을 제공하지 않는 Bridge입니다.
    {
      "kind": "material",
      "name": "Oak",
      "action": "preserved",
      "previous_count": 1, // 처리 전 레시피와 일치하는 RenderMaterial 수입니다.
      "current_count": 1 // 처리 후 레시피와 일치하는 RenderMaterial 수입니다.
    },
    {
      "kind": "layer",
      "name": "M::wood",
      "action": "created",
      "previous_count": 0, // 처리 전 지정 레이어 존재 여부(0/1)입니다.
      "current_count": 1 // 처리 후 지정 레이어 존재 여부(0/1)입니다.
    }
  ],
  "differences": [ // 최종 관측값과 요청한 속성이 다른 항목입니다.
    {
      "kind": "material",
      "name": "Oak",
      "property": "roughness",
      "current": 0.2,
      "expected": 0.5
    }
  ],
  "errors": [] // 처리 중 발생한 오류입니다. 비어 있어도 differences가 남을 수 있습니다.
}
```

# Script

스크립트 실행·결과 확인·저장 · prefix: `script_NN-` · 유형 내 순번 01–04

## 19. script_01-run_project_python

기준 API: `script_01-run_project_python`

근거: src/mcp/runtime/mcp_server.py

### DESCRIPTION

선택한 Plan의 산출물 폴더를 작업 디렉터리로 삼아 Rhino 내부에서 Python 3 코드를 실행합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "code": {
      "type": "string",
      "description": "연결된 Rhino에서 실행할 동기식 Python 3 코드입니다. doc과 scriptcontext.doc은 연결된 문서이며 JSON-safe 결과를 result에 할당합니다. 상대 출력 경로는 선택한 Plan/Loop의 산출물 폴더를 기준으로 합니다."
    },
    "timeout_seconds": {
      "default": 60,
      "type": "integer",
      "description": "1-600의 정수이며 기본값은 60입니다. 대기 시간 제한이며, 실행을 취소하지 않습니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "code"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "completed": true, // Rhino 실행 완료가 확인됐는지 나타냅니다.
  "request_id": "00000000000000000000000000000001", // 미완료·불확실성·결과 페이지를 get_rhino_execution으로 회수할 정확한 ID
  "artifact_dir": ".almond/produced/261111_example/01" // 실행에 사용한 Plan·Loop 산출물 폴더입니다.
}
```

## 20. script_02-run_rhino

기준 API: `script_02-run_rhino`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

연결된 RhinoCode에서 모델링·편집·측정 코드를 실행합니다. 전용 도구로 처리하기 어려운 작업에 사용합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "script": {
      "type": "string",
      "description": "동기식 Python 소스, C# 문장 본문 또는 명령 매크로입니다. Python은 JSON-safe 값을 result에, C#은 결과 JSON을 result_json에 할당합니다. doc은 연결된 문서입니다. command는 !·Pause·대화상자 없이 끝나는 매크로를 입력합니다."
    },
    "language": {
      "default": "python",
      "type": "string",
      "description": "python(기본값 Python 3), python2, csharp, csharp-script 또는 command입니다. 모든 모드는 공식 RhinoCode를 사용합니다."
    },
    "timeout_seconds": {
      "default": 60,
      "type": "integer",
      "description": "1-600의 정수이며 기본값은 60입니다. 대기 시간만 제한합니다. 시간 초과 후에는 동일한 요청을 조회합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "script"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "completed": true, // Rhino 실행 완료가 확인됐는지 나타냅니다. 변경 결과는 mutation_state와 result에서 확인합니다.
  "request_id": "00000000000000000000000000000001", // 필요할 때 get_rhino_execution으로 같은 요청을 조회하는 ID
  "result": { // 실행 코드가 정한 JSON 값입니다.
    "example": "스크립트가 반환한 값"
  }
}
```

## 45. script_03-get_execution

기준 API: `script_03-get_execution`

근거: src/mcp/runtime/mcp_server.py

### DESCRIPTION

기존 RhinoCode 요청의 실행 상태·결과·로그를 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "request_id": {
      "default": "",
      "type": "string",
      "description": "이전에 반환된 실행 request_id입니다. 비워 두면 이 세션의 가장 최근 요청을 선택합니다. 시간 초과 시에는 코드를 다시 제출하지 말고 동일 요청을 조회해야 합니다."
    },
    "include_result": {
      "default": true,
      "type": "boolean",
      "description": "true이면 저장된 결과를 포함합니다."
    },
    "include_stdout": {
      "default": false,
      "type": "boolean",
      "description": "true이면 캡처된 stdout을 포함합니다. 코드를 다시 실행하지는 않습니다."
    },
    "result_fields": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "유지할 최상위 결과 필드 이름으로, 선택 사항입니다. 생략하면 결과 필드를 유지합니다."
    },
    "offset": {
      "default": 0,
      "type": "integer",
      "description": "0부터 시작하는 결과 페이지 오프셋(배열 행 또는 문자열 문자 수)입니다. stdout은 바이트 스트림 오프셋을 사용합니다."
    },
    "limit": {
      "default": 100,
      "type": "integer",
      "description": "결과 페이지 크기로, 범위는 1..1000입니다. stdout은 해당 스트림 용량 한도에 따라 독립적으로 제한됩니다."
    },
    "include_ids": {
      "default": true,
      "type": "boolean",
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다."
    },
    "include_diagnostics": {
      "default": false,
      "type": "boolean",
      "description": "true이면 상세 실행 진단을 포함합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 현재 연결을 자동 적용합니다. 다른 연결의 보관된 결과를 찾을 때는 해당 connection_id와 request_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "request_id": "00000000000000000000000000000001", // 보관된 실행 요청 ID입니다. 같은 실행의 상태나 다음 결과 페이지 조회에 사용합니다.
  "completed": true, // 최종 Rhino 처리 근거와 CLI 종료가 모두 확인되었는지 여부. native_completed와 다를 수 있음
  "status": "success", // 보관된 실행의 상태입니다. 조회 호출 자체의 성공과 구분합니다.
  "result": { // 실행 코드가 정한 JSON 값입니다.
    "count": 3
  }
}
```

## 78. script_04-save_document

기준 API: `script_04-save_document`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

연결된 문서 전체를 기존 .3dm 경로에 저장합니다. 사용자에게 영구 저장을 요청받은 경우 사용합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "saved": true, // true는 확인된 저장, false는 확인된 실패, null은 미확정이며 requires_reconciliation=true
  "modified": false // 저장 확인 직후의 문서 수정 플래그입니다.
}
```

# Scene

Scene·Holon 의미 구조 관리 · prefix: `scene_NN-` · 유형 내 순번 01–13

## 05. scene_01-add_objects

기준 API: `scene_01-add_objects`

근거: src/mcp/features/scenes/tools.py

### DESCRIPTION

Rhino 객체를 Scene에 포함하거나 해당 Scene에서 제외했던 Holon 구성원을 복원합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "scene_id": {
      "type": "string",
      "description": "scene_07-list tool(include_ids=true)에서 얻은 기존 Scene ID입니다."
    },
    "object_ids": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "description": "일반 형상이나 클리핑 평면을 포함하는 객체 GUID 배열로, 최대 4096개 항목을 허용합니다."
    },
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "scene_id",
    "object_ids"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "failed_indices": [], // 입력 object_ids에서 처리하지 못한 항목의 인덱스입니다. 0부터 시작합니다.
  "already_present_indices": [], // 이미 포함되어 변경하지 않은 입력 위치. Holon을 통해 포함된 경우도 포함
  "next_step_guide": "scene_06-get_objects tool로 Scene의 현재 구성원을 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 13. scene_02-create

기준 API: `scene_02-create`

근거: src/mcp/features/scenes/tools.py

### DESCRIPTION

설계 영역·프로그램·상황을 나타내는 Scene을 생성합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "name": {
      "type": "string",
      "description": "설계 영역 또는 행위/프로그램 맥락을 설명하는 Scene 이름입니다. 비어 있으면 Untitled가 됩니다."
    },
    "units": {
      "default": "mm",
      "type": "string",
      "description": "Scene에 기록할 단위입니다. mm, cm, m, in, ft 중 하나를 선택합니다."
    },
    "file_name": {
      "default": "",
      "type": "string",
      "description": "이 Scene이 속한 프로젝트 파일명을 문자열로 입력합니다. 폴더는 제외하고, 같은 이름의 파일이 여러 개면 project_file_id로 지정합니다."
    },
    "project_file_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "context_04-get_project_info tool(sections=[\"project\"], include_ids=true)에서 얻은 기존 project.files[].project_file_id입니다. file_name과 함께 제공하면 서로 일치해야 합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "name"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "scene": { // 생성한 Scene의 확인 정보입니다.
    "scene_id": "scene_example",
    "revision": 0
  },
  "next_step_guide": "객체를 포함하려면 scene_01-add_objects tool에 이 scene_id를 사용합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 23. scene_03-focus_holons

기준 API: `scene_03-focus_holons`

근거: src/mcp/features/components/tools.py

### DESCRIPTION

Holon과 하위 Holon의 현재 구성원을 Rhino에서 선택·격리·확대합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "holon_ids": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "description": "현재 유효 구성원으로 해석할 등록된 Holon ID 1..32개입니다. 확인된 최상위 객체는 최대 4096개를 지원합니다. 실제 선택, 격리 및 카메라를 변경합니다."
    },
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "holon_ids"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "zoom_selected": true, // 기본 선택 확대 또는 대상 경계 확대를 완료했는지 나타냅니다.
  "view_change": {
    "selection_changed": true,
    "isolated": true,
    "zoom_selected": true, // 기본 선택 확대 또는 대상 경계 확대를 완료했는지 나타냅니다.
    "zoom_method": "bounding_box", // selected: 기본 선택 확대, bounding_box: 기본 방식 실패 후 같은 대상의 경계로 확대 성공.
    "display_mode_changed": false,
    "restore_visibility_command": "Unisolate"
  },
  "isolated": true, // 대상을 격리했는지 여부
  "locked_context_remains_visible": true, // 잠긴 주변 객체를 계속 표시하는지 여부
  "restore_visibility_command": "Unisolate", // 격리한 객체의 가시성을 복구하는 명령입니다.
  "model_path": "C:\\Example\\example.3dm", // 저장된 모델의 경로
  "viewport_id": "00000000-0000-0000-0000-000000000001", // 포커스된 실제 모델 뷰포트 GUID
  "selected_ids": [ // 포커스할 때 실제로 선택한 Rhino 객체 GUID입니다.
    "00000000-0000-0000-0000-000000000001"
  ]
}
```

## 30. scene_04-get

기준 API: `scene_04-get`

근거: src/mcp/features/scenes/tools.py

### DESCRIPTION

Scene의 등록 정보를 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "scene_id": {
      "type": "string",
      "description": "scene_07-list tool(include_ids=true) 또는 기록된 Scene 참조에서 얻은 기존 Scene ID입니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 사항인 상세 그룹: scope, state, geometry, audit 또는 all. 생략하거나 비워 두면 요약을 조회합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "scene_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "scene": { // Scene의 저장 요약입니다.
    "name": "예시 Scene",
    "units": "mm",
    "revision": 1,
    "holons": 0,
    "objects": 0,
    "direct_objects": 0,
    "live_verified": false
  },
  "next_step_guide": "현재 Rhino 구성원은 scene_06-get_objects tool로 조회합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 40. scene_05-get_holon

기준 API: `scene_05-get_holon`

근거: src/mcp/features/components/tools.py

### DESCRIPTION

Holon의 등록 정보와 구성원을 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "holon_id": {
      "type": "string",
      "description": "include_ids=true를 사용한 Holon 조회 또는 이전 등록 결과에서 얻은 등록된 Holon ID입니다."
    },
    "live": {
      "default": false,
      "type": "boolean",
      "description": "true이면 현재 Rhino 그룹 구성원 관계와 형상을 읽습니다. false이면 저장된 등록 정보만 읽습니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "recursive": {
      "default": false,
      "type": "boolean",
      "description": "true이면 등록된 하위 Holon을 확장합니다. 이는 의미적 계층이며, 블록 정의 확장이 아닙니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 사항인 상세 그룹: references, geometry, scope, audit 또는 all. 생략하거나 비워 두면 요약을 조회합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "holon_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "holon": { // 조회한 Holon의 요약입니다.
    "name": "예시 Holon",
    "availability": "present",
    "object_count": 2,
    "live_verified": false
  }
}
```

## 46. scene_06-get_objects

기준 API: `scene_06-get_objects`

근거: src/mcp/features/scenes/tools.py

### DESCRIPTION

Scene에 포함된 직접 객체와 하위 Holon의 현재 구성원을 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "scene_id": {
      "type": "string",
      "description": "scene_07-list tool(include_ids=true) 또는 기록된 Scene 참조에서 얻은 기존 Scene ID입니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 사항인 상세 그룹: scope, state, geometry, audit 또는 all. 생략하거나 비워 두면 요약을 조회합니다."
    },
    "limit": {
      "default": 50,
      "type": "integer",
      "description": "현재 상태를 검증한 Scene 객체의 페이지 크기이며, 범위는 1..200입니다."
    },
    "offset": {
      "default": 0,
      "type": "integer",
      "description": "이 페이지의 0부터 시작하는 첫 행 위치입니다. 다음 페이지를 요청할 때는 동일한 필터를 사용합니다."
    },
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "scene_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "objects": [], // 현재 연결 모델에서 확인한 Scene 객체와 요청한 속성입니다.
  "total": 0, // 현재 연결 모델에서 확인한 Scene 객체 수입니다.
  "limit": 50, // 페이지 최대 항목 수
  "offset": 0, // 현재 페이지 시작 위치
  "truncated": false, // 뒤 페이지가 남았는지 여부. 다음 offset은 현재 offset+objects 길이
  "live_verified": true, // 현재 Rhino 상태를 확인했는지 여부
  "model_path": "C:\\Example\\example.3dm" // 관찰한 연결 모델의 경로입니다.
}
```

## 53. scene_07-list

기준 API: `scene_07-list`

근거: src/mcp/features/scenes/tools.py

### DESCRIPTION

프로젝트에 등록된 Scene 목록을 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "name": {
      "default": "",
      "type": "string",
      "description": "선택 사항인 대소문자를 구분하지 않는 Scene 이름 필터입니다."
    },
    "file_name": {
      "default": "",
      "type": "string",
      "description": "이 파일에 속한 Scene을 찾습니다. 프로젝트 파일명을 문자열로 입력하며, 생략하면 모든 파일을 포함합니다."
    },
    "limit": {
      "default": 50,
      "type": "integer",
      "description": "페이지 크기이며, 범위는 1..200입니다."
    },
    "offset": {
      "default": 0,
      "type": "integer",
      "description": "이 페이지의 0부터 시작하는 첫 행 위치입니다. 다음 페이지를 요청할 때는 동일한 필터를 사용합니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 사항인 상세 그룹: scope, state, geometry, audit 또는 all. 생략하거나 비워 두면 요약을 조회합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "scenes": [], // 저장된 Scene의 이름과 요청한 속성입니다.
  "total": 0, // 필터에 일치하는 전체 항목 수
  "limit": 50, // 페이지 최대 항목 수
  "offset": 0, // 현재 페이지 시작 위치
  "truncated": false // 뒤 페이지가 남았는지 여부. 같은 필터로 offset+scenes 길이부터 계속 조회
}
```

## 59. scene_08-list_holons

기준 API: `scene_08-list_holons`

근거: src/mcp/features/components/tools.py

### DESCRIPTION

등록된 Holon 목록을 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "관리형 세션의 기본값은 연결된 모델입니다. 독립 실행에서 빈 입력을 사용하면 여러 모델의 등록 정보를 나열합니다. 활성 Rhino 문서를 전환하지 않습니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "scene_id": {
      "default": "",
      "type": "string",
      "description": "선택 사항인 등록된 Scene ID 필터입니다. 비어 있으면 Scene으로 필터링하지 않습니다."
    },
    "recursive": {
      "default": false,
      "type": "boolean",
      "description": "true이면 등록된 자식 Holon을 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 가능한 세부 그룹은 references, geometry, scope, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "holons": [], // 등록된 Holon의 저장 요약입니다.
  "total": 0, // 필터에 일치하는 전체 항목 수
  "live_verified": false // Holon을 현재 Rhino에서 확인했는지 나타냅니다.
}
```

## 72. scene_09-remove_holon

기준 API: `scene_09-remove_holon`

근거: src/mcp/features/components/tools.py

### DESCRIPTION

Holon 등록을 해제하고 Rhino 형상과 그룹은 유지합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "holon_id": {
      "type": "string",
      "description": "등록을 해제할 Holon ID입니다. 이 Holon을 참조하는 부모 Holon과 Plan의 관계를 먼저 해제합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "holon_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "holon": { // Holon 등록 해제 결과입니다.
    "holon_id": "example-holon",
    "status": "unregistered",
    "live_verified": true
  }
}
```

## 73. scene_10-remove_objects

기준 API: `scene_10-remove_objects`

근거: src/mcp/features/scenes/tools.py

### DESCRIPTION

객체를 Scene에서 제외합니다. Rhino 형상과 Holon 그룹은 유지됩니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "scene_id": {
      "type": "string",
      "description": "scene_07-list tool(include_ids=true)에서 얻은 기존 Scene ID입니다."
    },
    "object_ids": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "description": "일반 형상 또는 클리핑 평면을 포함하는 객체 GUID 배열이며, 최대 4096개 항목을 받습니다."
    },
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "scene_id",
    "object_ids"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "failed_indices": [], // 입력 object_ids에서 처리하지 못한 항목의 인덱스입니다. 0부터 시작합니다.
  "already_absent_indices": [], // Scene에 이미 포함되지 않은 입력 항목의 인덱스입니다. 0부터 시작합니다.
  "next_step_guide": "scene_06-get_objects tool로 Scene의 현재 구성원을 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 85. scene_11-sync_holon

기준 API: `scene_11-sync_holon`

근거: src/mcp/features/components/tools.py

### DESCRIPTION

Rhino의 현재 구성원을 읽어 Holon 등록 정보를 갱신합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "holon_id": {
      "default": "",
      "type": "string",
      "description": "단일 대상의 상태 대조 및 정합성 확인에 사용할 등록된 Holon ID입니다. 선택 사항입니다."
    },
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다."
    },
    "rhino_group_id": {
      "default": "",
      "type": "string",
      "description": "holon_id와 함께 제공하는 선택 항목으로, 현재 Rhino 그룹 GUID의 일관성을 확인합니다. 이 값만으로 그룹을 선택하거나 연결 대상을 바꾸지 않습니다."
    },
    "holon_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "명시적 Holon ID 일괄 목록입니다. 선택 사항이며, 단일 Holon/그룹 선택자와 함께 사용하지 않습니다."
    },
    "scene_id": {
      "default": "",
      "type": "string",
      "description": "구성원을 갱신할 Scene ID입니다. holon_id, holon_ids, rhino_group_id와 함께 입력하지 않습니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "checked": 1, // 확인한 Holon 수
  "changed": 0, // 실제 대장 갱신 수. 변경 없으면 새 리비전도 없음
  "unavailable": 0, // 상태가 present가 아닌 등록 수
  "problems": [], // 항목별 문제. 관련 없는 유효 등록은 함께 갱신될 수 있음
  "scene_revisions": {}, // 갱신한 Scene ID와 저장 리비전의 대응입니다.
  "live_verified": true, // 문제 없이 모든 대상의 현재 상태를 확인했는지 나타냅니다.
  "next_step_guide": "갱신된 구성원은 scene_05-get_holon tool으로 확인할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 86. scene_12-update

기준 API: `scene_12-update`

근거: src/mcp/features/scenes/tools.py

### DESCRIPTION

Scene의 프로젝트 파일 연결을 변경하거나 해제합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "scene_id": {
      "type": "string",
      "description": "scene_07-list tool(include_ids=true) 또는 기록된 Scene 참조에서 얻은 기존 Scene ID입니다."
    },
    "file_name": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "폴더를 포함하지 않는 교체 파일 이름입니다. 선택 사항이며, project_file_id를 생략한 상태에서 빈 문자열을 지정하면 연결을 해제합니다. 생략하면 유지합니다."
    },
    "project_file_id": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "연결할 기존 프로젝트 파일의 ID입니다. file_name도 입력하면 같은 파일을 가리켜야 합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "scene_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "scene": { // 수정한 Scene의 확인 정보입니다.
    "scene_id": "scene_example",
    "revision": 1
  },
  "next_step_guide": "scene_04-get tool으로 변경된 Scene을 확인할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 90. scene_13-upsert_holon

기준 API: `scene_13-upsert_holon`

근거: src/mcp/features/components/tools.py

### DESCRIPTION

물리적 요소와 관계를 Holon으로 등록하거나 갱신합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "name": {
      "type": "string",
      "description": "의미적 Holon 이름입니다. 기존 Rhino 그룹에 연결할 때는 해당 그룹의 정확한 이름과 일치해야 합니다."
    },
    "object_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "등록할 최상위 Rhino 객체 GUID 배열입니다. 각 객체는 하나의 Holon에 속합니다. 생략하면 name과 일치하는 기존 그룹을 사용합니다. []는 child_holon_ids가 있는 부모에만 사용합니다."
    },
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다."
    },
    "scene_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Holon이 속할 기존 Scene ID 배열입니다. 새 Holon에는 필수이며, 수정 시 생략하면 유지합니다."
    },
    "holon_id": {
      "default": "",
      "type": "string",
      "description": "수정할 기존 Holon ID입니다. 선택 사항이며, 생략하면 등록을 생성합니다."
    },
    "rhino_group_id": {
      "default": "",
      "type": "string",
      "description": "기존 Rhino 그룹의 정확한 GUID입니다. 선택 사항이며, 이름의 모호성을 해소하는 데 사용합니다."
    },
    "child_holon_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "등록된 자식 Holon 목록입니다. 선택 사항이며, []는 기존 자식을 분리하고 생략하면 유지합니다. 자식당 부모는 하나만 허용하고 계층 순환을 금지합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "name"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "holon": { // 등록한 Holon의 확인 정보입니다.
    "holon_id": "example-holon",
    "availability": "present",
    "object_count": 1,
    "live_verified": true
  },
  "next_step_guide": "scene_05-get_holon tool으로 등록 결과와 현재 구성원을 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

# Intersect

교차·겹침 검토와 해결 · prefix: `intersect_NN-` · 유형 내 순번 01–02

## 38. intersect_01-find

기준 API: `intersect_01-find`

근거: src/mcp/features/context/tools.py

### DESCRIPTION

닫힌 솔리드 사이에서 부피가 겹치는 객체 쌍을 찾습니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "object_ids": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "description": "서로 다른 현재 최상위 Rhino 객체 GUID 1..512개입니다. 내부 페이지 처리를 통해 하나의 범위로 검사합니다."
    },
    "include_block": {
      "default": false,
      "type": "boolean",
      "description": "true이면 변환이 적용된 중첩 블록 구성원까지 펼칩니다. 기본값 false는 범위에서 블록을 제외합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "object_ids"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "intersections": { // 겹침 집계
    "number": 0
  },
  "next_step_guide": "No positive-volume overlap was found in this scope; no resolution call is needed. This does not establish other design or clearance conditions." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 75. intersect_02-resolve

기준 API: `intersect_02-resolve`

근거: src/mcp/features/components/tools.py

### DESCRIPTION

겹친 객체 쌍을 이미지로 검토하고 선택한 객체에서 겹친 부분을 제거합니다. 검토 시 실제 카메라와 선택이 바뀝니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "object_ids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "검토 범위를 시작할 서로 다른 현재 최상위 객체 GUID 1..512개입니다. 선택 사항이며, 현재 범위를 이어서 검토하거나 선택을 제출할 때는 생략합니다."
    },
    "include_block": {
      "default": false,
      "type": "boolean",
      "description": "새 검토 범위에 변환이 적용된 중첩 블록 구성원을 포함합니다. 기본값은 false입니다. 블록 정의 편집은 여전히 지원하지 않습니다."
    },
    "review_id": {
      "default": "",
      "type": "string",
      "description": "반환된 결정 핸들로, choice와 함께 사용할 때 필수입니다. 화면에 표시된 연산 대상을 식별합니다. 완료되었거나 새 검토로 대체된 핸들로는 변경을 다시 실행할 수 없습니다."
    },
    "choice": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "const": "skip",
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "1 또는 2는 해당 번호의 객체에서 겹친 부분을 제거합니다. \"skip\"은 두 객체를 모두 그대로 둡니다. review_id를 제공하고 object_ids는 생략합니다. 확인/계속 진행하려면 choice를 생략합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "state": "completed", // 검토 진행 상태입니다. awaiting_choice이면 비교 결과를 확인한 뒤 선택합니다.
  "skipped_pairs": 0, // 건너뛴 쌍은 수정하지 않음. completed가 모든 겹침 제거를 뜻하지 않음
  "message": "검토할 겹침이 더 없습니다. skip한 쌍은 수정하지 않았습니다." // 현재 결과 또는 오류의 설명입니다.
}
```

# Asset

모델·도면 자산 검색·준비·배치 · prefix: `asset_NN-` · 유형 내 순번 01–11

## 09. asset_01-audit_drawing

기준 API: `asset_01-audit_drawing`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

저장 도면 패키지의 파일 해시와 원본 변경 여부를 검사합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "package_dir": {
      "type": "string",
      "description": "생성/조회 결과의 package_dir를 그대로 입력합니다. 관리형 세션은 프로젝트 안의 패키지와 설정된 도면 라이브러리·drawing-runs의 패키지를 검사합니다. 독립 실행에서는 절대 경로가 필요합니다."
    },
    "source_glb": {
      "default": "",
      "type": "string",
      "description": "원본 변경으로 오래된 상태가 되었는지 확인할 현재 원본 GLB입니다. 선택 사항이며, 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. 라이브러리에서 원본을 확인할 수 있으면 생략합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "package_dir"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

아래 성공 예시는 프로젝트 내부의 기존 패키지를 검사한 경우입니다. 현재 관리형 입력 검사는 절대 경로와 `..`를 거부하므로, generate_asset_drawing_views가 프로젝트 밖 AppData에 생성해 반환한 경로는 그대로 검사할 수 없습니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "source_geometry": "source_file_current", // current/source_file_current/stale/not_checked. not_checked는 success여도 원본 비교 미실시
  "asset_id": "example-asset", // 패키지 원본 ID. custom-*는 등록 자산 ID가 아님
  "checked_files": 6, // 해시를 검사한 파일 수. 시각적 검토가 아님
  "failures": [] // 실패 항목이 하나라도 있으면 status=error
}
```

## 24. asset_02-generate_drawing_views

기준 API: `asset_02-generate_drawing_views`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

등록 3DM 또는 GLB에서 평면·정면·우측면 도면 패키지를 생성합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "default": "",
      "type": "string",
      "description": "라이브러리 자산 ID입니다. 선택 사항이며, 이 값 또는 source_glb 중 하나를 제공합니다."
    },
    "source_glb": {
      "default": "",
      "type": "string",
      "description": "사용자 지정 정적 GLB 원본입니다. 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. 이 값 또는 asset_id 중 하나를 제공합니다."
    },
    "input_units": {
      "default": "",
      "type": "string",
      "description": "사용자 지정 GLB 원본 단위로 mm 또는 m을 사용합니다. source_glb를 제공할 때 필수입니다."
    },
    "up_axis": {
      "default": "y",
      "type": "string",
      "description": "원본의 위쪽 축으로 y 또는 z를 사용합니다. 기본값은 y입니다."
    },
    "scales": {
      "anyOf": [
        {
          "items": {
            "type": "integer"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "도면 축척의 분모 목록입니다. 선택 사항이며, 생략하면 [50, 100]을 사용합니다."
    },
    "source_references": {
      "anyOf": [
        {
          "items": {
            "additionalProperties": true,
            "type": "object"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "출처 이력입니다. source_id/title/url/publisher/locator/accessed_on/relationship/used_for/terms_url을 담은 참조 객체를 입력합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

Windows의 생성 위치는 `%LOCALAPPDATA%/Almond/drawing-runs/<UUID>`입니다. 공개 입력에는 출력 위치 옵션이 없습니다. 아래는 프로젝트가 C:/Projects/Example, LOCALAPPDATA가 C:/Users/example/AppData/Local인 관리형 세션의 반환 형식입니다. 프로젝트 밖 경로가 `../` 형태로 반환될 수 있습니다. 이 값을 audit_asset_drawing에 그대로 전달하며, 현재 설정된 도면 라이브러리·drawing-runs 안의 패키지인지 검사합니다. 다른 드라이브의 라이브러리 경로는 절대 경로로 반환합니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "package_dir": "../../Users/example/AppData/Local/Almond/drawing-runs/123e4567-e89b-42d3-a456-426614174000", // audit_asset_drawing의 package_dir에 그대로 전달할 경로입니다. 관리 연결에서는 프로젝트 상대 경로이며, 다른 드라이브의 라이브러리는 절대 경로를 유지합니다.
  "manifest": {} // 생성한 도면과 원본·축척·단위 기록입니다.
}
```

## 25. asset_03-get_drawings

기준 API: `asset_03-get_drawings`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

등록 모델의 저장 도면을 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "type": "string",
      "description": "include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). field_groups=["all"]로 조회한 경우입니다. 프로젝트 C:/Projects/Example, 라이브러리 C:/Users/example/AppData/Local/Almond/DrawingAssetfiles 기준입니다. //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "plan_svg_uri": "almond://drawing/example-asset/drawing/plan/50", // 저장된 평면 SVG를 읽는 리소스 URI입니다.
  "manifest": {}, // 도면 패키지의 원본·파일·축척 기록입니다.
  "package_dir": "../../Users/example/AppData/Local/Almond/DrawingAssetfiles/registered/example-asset-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/drawing" // all 조회에서 반환하는 도면 패키지 경로입니다. audit_asset_drawing의 package_dir에 그대로 전달할 수 있습니다.
}
```

## 32. asset_04-get

기준 API: `asset_04-get`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

모델·2D 자산의 등록 정보와 사용 가능 상태를 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "type": "string",
      "description": "include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "asset": { // 선택한 도면 자산과 준비 상태입니다.
    "name": "예시 자산",
    "file_available": true,
    "model_status": "ready",
    "drawing_ready": true
  },
  "next_step_guide": "선택한 자산의 ID로 asset_06-place tool을 호출할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 55. asset_05-list

기준 API: `asset_05-list`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

모델·2D 자산 목록을 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "default": "",
      "type": "string",
      "description": "라이브러리 분류 필터입니다. 선택 사항이며, 비어 있으면 모든 분류를 포함합니다."
    },
    "limit": {
      "default": 20,
      "type": "integer",
      "description": "한 페이지에 반환할 최대 항목 수입니다."
    },
    "offset": {
      "default": 0,
      "type": "integer",
      "description": "이 페이지의 시작 행을 0부터 세는 값입니다. 다음 페이지를 요청할 때도 같은 필터를 사용합니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "library_id": "model_assets", // include_ids=true에서 유지되는 라이브러리 구분자
  "assets": [], // 도면 자산 목록입니다. 추가 준비가 필요한 항목에는 next_tool과 next_step_guide가 있습니다.
  "total": 0, // 필터에 일치하는 전체 항목 수
  "limit": 20, // 페이지 최대 항목 수
  "offset": 0, // 현재 페이지 시작 위치
  "truncated": false, // true이면 같은 필터로 offset+현재 항목 수부터 계속. next_offset 필드는 없음
  "purpose": "3DM models and 2D representations; legacy sources require explicit conversion" // 이 라이브러리의 용도입니다.
}
```

## 64. asset_06-place

기준 API: `asset_06-place`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

모델·2D 자산을 Rhino 문서에 배치합니다. 연결된 3DM 블록 정의를 갱신하면 기존 인스턴스에도 반영됩니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "type": "string",
      "description": "include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다."
    },
    "x": {
      "default": 0,
      "type": "number",
      "description": "현재 Rhino 문서 단위를 사용하는 배치 X 좌표입니다."
    },
    "y": {
      "default": 0,
      "type": "number",
      "description": "현재 Rhino 문서 단위를 사용하는 배치 Y 좌표입니다."
    },
    "z": {
      "default": 0,
      "type": "number",
      "description": "현재 Rhino 문서 단위를 사용하는 배치 Z 좌표입니다."
    },
    "rotation_degrees": {
      "default": 0,
      "type": "number",
      "description": "월드 Z축을 중심으로 한 회전각이며, 단위는 도입니다."
    },
    "scale": {
      "default": 1,
      "type": "number",
      "description": "양수인 균일 배치 축척입니다. 1이면 단위 변환 후 자산 크기를 유지합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "asset_id": "example-asset", // 자산 ID
  "object_guid": "00000000-0000-0000-0000-000000000001", // 삽입한 최상위 블록 GUID. get_objects 또는 Scene 구성원 입력에 재사용
  "definition_created": true, // 새 정의 생성 여부. 공유 정의 갱신 시 definition_refreshed/affected_existing_instances가 추가될 수 있음
  "next_step_guide": "inspect_02-get_objects tool와 캡처로 배치 위치·축척을 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 66. asset_07-prepare

기준 API: `asset_07-prepare`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

원본 사본을 검사·편집·시각 검토해 등록용 3DM을 준비합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "stage": {
      "type": "string",
      "description": "inspect, normalize, verify 또는 status입니다. inspect는 작업을 생성하고, 이후 단계는 job_dir를 재사용합니다. status는 저장된 근거만 다시 읽습니다. 네이티브 작업을 실행하거나, 나중에 완료되었다는 이유로 확인되지 않은 작업의 단계를 올리지 않습니다."
    },
    "source_file": {
      "default": "",
      "type": "string",
      "description": "inspect에 사용할 원본 모델입니다. 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. 원본 바이트는 변경하지 않고 유지합니다."
    },
    "job_dir": {
      "default": "",
      "type": "string",
      "description": "이전에 반환된 준비 작업의 job_dir입니다. 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. normalize, verify, status에 필수입니다."
    },
    "input_units": {
      "default": "",
      "type": "string",
      "description": "OBJ/STL/PLY/OFF/GLB/glTF의 명시적 원본 단위로 mm, cm, m, in 또는 ft를 지정합니다. 측정한 원본 단위를 사용합니다. 이후 단계에서는 생략하며, 3DM은 내장된 단위를 보존합니다."
    },
    "review": {
      "anyOf": [
        {
          "additionalProperties": true,
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "검토 결과 객체입니다. normalize: {vision_reviewed:true, inspected_sha256:\"확인한 해시\", rotation_degrees_xyz:[x,y,z], translation:[x,y,z], remove:[{object_id:\"ID\",reason:\"사유\"}]}. 생략한 변환은 유지하며 translation은 원본 단위입니다. 최종 이미지를 본 뒤 verify: {vision_reviewed:true, final_sha256:\"확인한 해시\", name:\"이름\", asset_id:\"ID\"}. 첫 verify로 최종 이미지를 만든 후 검토 확인을 제출합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 가능한 값은 summary, parts, previews, provenance 또는 all입니다. 생략하면 미리 보기 경로를 포함하고, []이면 간략한 결과를 유지합니다. 페이지 처리는 parts에 적용됩니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "offset": {
      "default": 0,
      "type": "integer",
      "description": "이 페이지의 시작 행을 0부터 세는 값입니다. 다음 페이지를 요청할 때도 같은 필터를 사용합니다."
    },
    "limit": {
      "default": 50,
      "type": "integer",
      "description": "부품 목록의 페이지 크기이며, 범위는 1..200입니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "stage"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

현재 관리형 세션에서는 선택한 Plan·Loop의 상대 경로가 ALMOND_ARTIFACT_DIR로 전달되지만, 준비 함수는 기존 절대 경로를 요구합니다. 따라서 set_working_plan 성공 후에도 inspect·normalize·verify·status에서 status=error와 message=`Select a working Plan artifact directory before preparing an asset`를 반환할 수 있습니다. Plan 선택·Loop 시작은 경로를 기록하며 해당 폴더를 생성하지 않습니다. 이 경로 검사 실패는 준비 작업 생성과 네이티브 요청 전에 발생합니다.

아래는 경로 조건이 충족되고 최종 검토가 기록되어 state=ready인 경우의 코드 기반 구조이며, 현재 관리형 호출의 성공 실측이 아닙니다. inspect가 만드는 작업 폴더명은 `asset-preparation-<UUID hex>`이고, Loop가 시작되면 선택한 Plan 폴더의 회차 하위 폴더에 둡니다. review_evidence와 next_step_guide는 현재 서버가 반환하는 영어 원문입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "state": "ready", // ready일 때만 source_3dm 제공. running/unconfirmed/failed는 error와 next_stage=null
  "ready_for_registration": true, // 현재 파일 해시에 대한 이미지 검토를 호출자가 확인했는지 나타냅니다.
  "job_dir": ".almond/produced/261111_example/01/asset-preparation-123e4567e89b42d3a456426614174000", // 이후 단계 및 등록의 preparation_job에 재사용. status는 저장 근거만 읽고 늦은 실행을 자동 정합화하지 않음
  "source_3dm": ".almond/produced/261111_example/01/asset-preparation-123e4567e89b42d3a456426614174000/final.3dm", // 검토 완료 최종 파일. register_drawing_asset에 검토한 name/asset_id와 함께 전달
  "next_stage": "asset_09-register", // 현재 상태의 다음 단계. 오류에서 자동 진행을 유도하지 않음
  "review_evidence": "caller attestations tied to file hashes; no automatic vision verification", // 저장된 검토 증거에 대한 설명입니다.
  "next_step_guide": "If publication is intended, call asset_09-register tool with source_3dm from this response, preparation_job=job_dir, and the reviewed asset_id/name; category is optional. Choose replace_existing explicitly when replacing an existing asset." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 70. asset_08-refresh

기준 API: `asset_08-refresh`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

편집 후 저장된 등록 3DM을 다시 측정하고 도면을 갱신합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "type": "string",
      "description": "include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

model_path는 기존에 등록된 라이브러리 3DM 경로를 유지하고, 새 도면은 같은 라이브러리의 `revisions/<asset_id>-<버전>/drawing`에 저장합니다. 아래는 프로젝트 C:/Projects/Example, 라이브러리 C:/Users/example/AppData/Local/Almond/DrawingAssetfiles를 사용한 관리형 세션의 반환 예시입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "registration_applied": true, // true면 인덱스 갱신 실패여도 게시 적용. 무작정 반복하지 않음
  "source_path_preserved": true, // 기존 원본 경로를 보존했는지 여부
  "rhino_linked_instances_updated": false, // false: 기존 Rhino 연결 인스턴스 재로드는 별도
  "live_index_refreshed": true, // false인데 게시가 적용됐다면 재연결하여 인덱스 갱신
  "asset": {}, // 갱신한 자산의 정보입니다.
  "model_path": "../../Users/example/AppData/Local/Almond/DrawingAssetfiles/registered/example-asset-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/model.3dm", // 갱신한 라이브러리 3DM 경로입니다.
  "package_dir": "../../Users/example/AppData/Local/Almond/DrawingAssetfiles/revisions/example-asset-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb/drawing", // 갱신한 도면 패키지 폴더입니다.
  "previous_files_retained": true, // 이전 도면·매니페스트 백업·원본 리비전 사본 보존
  "next_step_guide": "갱신된 도면은 asset_03-get_drawings tool으로 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 71. asset_09-register

기준 API: `asset_09-register`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

준비한 3DM을 라이브러리 자산으로 등록합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "source_3dm": {
      "type": "string",
      "description": "검토한 3DM 원본입니다. 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. preparation_job을 사용할 때는 해당 작업 응답의 source_3dm을 사용합니다."
    },
    "asset_id": {
      "type": "string",
      "description": "검토한 자산에 사용할 새 고정 라이브러리 식별자입니다."
    },
    "name": {
      "type": "string",
      "description": "사람이 읽을 수 있는 자산 이름입니다."
    },
    "category": {
      "default": "other",
      "type": "string",
      "description": "새 자산의 라이브러리 분류입니다."
    },
    "tags": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 사항인 설명용 검색 태그입니다."
    },
    "description": {
      "default": "",
      "type": "string",
      "description": "선택 사항인 자산 설명입니다."
    },
    "source_url": {
      "default": "",
      "type": "string",
      "description": "출처 이력으로 보존할 원래 원본 URL입니다. 선택 사항입니다."
    },
    "replace_existing": {
      "default": false,
      "type": "boolean",
      "description": "true이면 이 ID를 가진 기존 자산을 명시적으로 교체합니다. false이면 교체를 거부합니다."
    },
    "preparation_job": {
      "default": "",
      "type": "string",
      "description": "완료된 준비 작업의 job_dir입니다. 선택 사항이며, 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. 검토를 거치는 다중 형식 변환 절차에는 필수입니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "source_3dm",
    "asset_id",
    "name"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

source_3dm은 준비 산출물에서 읽지만 등록 결과는 `DRAWING_LIBRARY_DIR`의 `registered/<asset_id>-<버전>/`에 저장합니다. 아래는 새 등록이며, 프로젝트 C:/Projects/Example, 라이브러리 C:/Users/example/AppData/Local/Almond/DrawingAssetfiles를 사용한 관리형 세션의 반환 예시입니다. 실제 라이브러리는 환경 변수·개발 체크아웃·사용자 데이터 경로 설정에 따라 달라집니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "registration_applied": true, // true면 게시 적용. 불명확한 오류는 null과 requires_reconciliation; 단순 재시도 금지
  "live_index_refreshed": true, // 게시 true·인덱스 false이면 등록을 반복하지 말고 재연결
  "source_path_preserved": false, // 기존 원본 경로를 보존했는지 여부
  "linked_instances_may_update": false, // 교체로 기존 연결 인스턴스에 영향 가능
  "asset": {}, // 등록한 자산의 정보입니다.
  "library_dir": "../../Users/example/AppData/Local/Almond/DrawingAssetfiles", // 라이브러리 폴더
  "model_path": "../../Users/example/AppData/Local/Almond/DrawingAssetfiles/registered/example-asset-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/model.3dm", // 저장된 모델의 경로
  "package_dir": "../../Users/example/AppData/Local/Almond/DrawingAssetfiles/registered/example-asset-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/drawing", // 생성한 도면 패키지 폴더입니다. DXF와 치수는 mm 단위입니다.
  "manifest_path": "../../Users/example/AppData/Local/Almond/DrawingAssetfiles/manifest.json", // 라이브러리 manifest.json 경로입니다.
  "previous_files_retained": false, // 교체 전 원본·도면·매니페스트 백업 보존
  "previous_source_sha256": null, // 기존 원본 해시. 없으면 null
  "next_step_guide": "등록한 자산은 asset_04-get tool으로 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 79. asset_10-search_repository

기준 API: `asset_10-search_repository`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

모델·2D 요소 아카이브를 검색합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "query": {
      "default": "",
      "type": "string",
      "description": "자유 텍스트 검색어입니다. 비어 있으면 텍스트 필터를 설정하지 않습니다."
    },
    "kind": {
      "default": "all",
      "type": "string",
      "description": "저장소 유형 필터로 all, element 또는 model을 사용합니다."
    },
    "drawing_ready": {
      "default": false,
      "type": "boolean",
      "description": "true이면 도면 데이터가 준비된 자산으로 제한합니다."
    },
    "limit": {
      "default": 20,
      "type": "integer",
      "description": "반환할 최대 자산 수입니다. 1..100 범위입니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "total": 0, // 전체 매치 수. assets는 limit까지이며 offset/has_more 없음
  "assets": [] // 검색된 자산과 준비 상태입니다. id를 후속 도구의 asset_id로 사용합니다.
}
```

## 82. asset_11-search

기준 API: `asset_11-search`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

조건에 맞는 모델·2D 자산을 검색합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "query": {
      "default": "",
      "type": "string",
      "description": "자유 텍스트 검색어입니다. 비어 있으면 텍스트 필터를 설정하지 않습니다."
    },
    "category": {
      "default": "",
      "type": "string",
      "description": "라이브러리 분류 필터입니다. 선택 사항이며, 비어 있으면 모든 분류를 포함합니다."
    },
    "max_width_mm": {
      "default": 0,
      "type": "number",
      "description": "측정된 자산 너비의 최댓값이며, 밀리미터 단위입니다. 선택 사항이며, 0은 이 크기 필터를 해제합니다."
    },
    "max_depth_mm": {
      "default": 0,
      "type": "number",
      "description": "측정된 자산 깊이의 최댓값이며, 밀리미터 단위입니다. 선택 사항이며, 0은 이 크기 필터를 해제합니다."
    },
    "max_height_mm": {
      "default": 0,
      "type": "number",
      "description": "측정된 자산 높이의 최댓값이며, 밀리미터 단위입니다. 선택 사항이며, 0은 이 크기 필터를 해제합니다."
    },
    "limit": {
      "default": 10,
      "type": "integer",
      "description": "한 페이지에 반환할 최대 항목 수입니다."
    },
    "offset": {
      "default": 0,
      "type": "integer",
      "description": "이 페이지의 시작 행을 0부터 세는 값입니다. 다음 페이지를 요청할 때도 같은 필터를 사용합니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "assets": [], // 검색된 도면 자산과 준비 상태입니다.
  "total": 0, // 필터에 일치하는 전체 항목 수
  "limit": 10, // 페이지 최대 항목 수
  "offset": 0, // 현재 페이지 시작 위치
  "truncated": false // true이면 같은 필터로 offset+현재 항목 수부터 계속
}
```

# Diagram

다이어그램 자산 검색·배치 · prefix: `diagram_NN-` · 유형 내 순번 01–04

## 31. diagram_01-get

기준 API: `diagram_01-get`

근거: src/mcp/features/diagrams/tools.py

### DESCRIPTION

다이어그램 자산의 등록 정보와 사용 가능 상태를 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "type": "string",
      "description": "include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 가능한 세부 그룹은 dimensions, drawing, metadata, source, paths, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "asset": { // 선택한 다이어그램 자산의 정보입니다.
    "name": "예시 다이어그램",
    "file_available": true
  },
  "next_step_guide": "선택한 자산의 ID로 diagram_03-place tool을 호출할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 54. diagram_02-list

기준 API: `diagram_02-list`

근거: src/mcp/features/diagrams/tools.py

### DESCRIPTION

사람·나무·기호 등 다이어그램 자산 목록을 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "category": {
      "default": "",
      "type": "string",
      "description": "라이브러리 분류 필터입니다. 선택 사항이며, 비어 있으면 모든 분류를 포함합니다."
    },
    "limit": {
      "default": 20,
      "type": "integer",
      "description": "한 페이지에 반환할 최대 항목 수입니다."
    },
    "offset": {
      "default": 0,
      "type": "integer",
      "description": "이 페이지의 시작 행을 0부터 세는 값입니다. 다음 페이지를 요청할 때도 같은 필터를 사용합니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 가능한 세부 그룹은 dimensions, drawing, metadata, source, paths, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "library_id": "diagram_assets", // include_ids=true에서 유지되는 라이브러리 구분자
  "assets": [], // 다이어그램 자산과 요청한 속성입니다.
  "total": 0, // 필터에 일치하는 전체 항목 수
  "offset": 0, // 현재 페이지 시작 위치
  "limit": 20, // 페이지 최대 항목 수
  "next_offset": null, // 다음 페이지의 시작 위치입니다. null이면 다음 페이지가 없습니다.
  "purpose": "2D vector diagramming and line-art" // 이 라이브러리의 용도입니다.
}
```

## 63. diagram_03-place

기준 API: `diagram_03-place`

근거: src/mcp/features/diagrams/tools.py

### DESCRIPTION

SVG·DWG·DXF 다이어그램을 Rhino 문서의 블록 인스턴스로 배치합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "type": "string",
      "description": "include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다."
    },
    "x": {
      "default": 0,
      "type": "number",
      "description": "현재 Rhino 문서 단위를 사용하는 배치 X 좌표입니다."
    },
    "y": {
      "default": 0,
      "type": "number",
      "description": "현재 Rhino 문서 단위를 사용하는 배치 Y 좌표입니다."
    },
    "z": {
      "default": 0,
      "type": "number",
      "description": "현재 Rhino 문서 단위를 사용하는 배치 Z 좌표입니다."
    },
    "rotation_degrees": {
      "default": 0,
      "type": "number",
      "description": "월드 Z축을 중심으로 한 회전각이며, 단위는 도입니다."
    },
    "scale": {
      "default": 1,
      "type": "number",
      "description": "양수인 균일 배치 축척입니다. 1이면 단위 변환 후 자산 크기를 유지합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "asset_id": "example-asset", // 자산 ID
  "object_guid": "00000000-0000-0000-0000-000000000001", // 삽입한 최상위 블록 GUID. get_objects 또는 Scene 구성원 입력에 재사용
  "definition_created": true, // 새 블록 정의를 생성했는지 나타냅니다.
  "next_step_guide": "inspect_02-get_objects tool와 캡처로 배치 위치·축척을 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 81. diagram_04-search

기준 API: `diagram_04-search`

근거: src/mcp/features/diagrams/tools.py

### DESCRIPTION

조건에 맞는 다이어그램 자산을 검색합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "query": {
      "default": "",
      "type": "string",
      "description": "자유 텍스트 검색어입니다. 비어 있으면 텍스트 필터를 설정하지 않습니다."
    },
    "category": {
      "default": "",
      "type": "string",
      "description": "라이브러리 분류 필터입니다. 선택 사항이며, 비어 있으면 모든 분류를 포함합니다."
    },
    "max_width_mm": {
      "default": 0,
      "type": "number",
      "description": "측정된 자산 너비의 최댓값이며, 밀리미터 단위입니다. 선택 사항이며, 0은 이 크기 필터를 해제합니다."
    },
    "max_depth_mm": {
      "default": 0,
      "type": "number",
      "description": "측정된 자산 깊이의 최댓값이며, 밀리미터 단위입니다. 선택 사항이며, 0은 이 크기 필터를 해제합니다."
    },
    "max_height_mm": {
      "default": 0,
      "type": "number",
      "description": "측정된 자산 높이의 최댓값이며, 밀리미터 단위입니다. 선택 사항이며, 0은 이 크기 필터를 해제합니다."
    },
    "limit": {
      "default": 10,
      "type": "integer",
      "description": "한 페이지에 반환할 최대 항목 수입니다."
    },
    "offset": {
      "default": 0,
      "type": "integer",
      "description": "이 페이지의 시작 행을 0부터 세는 값입니다. 다음 페이지를 요청할 때도 같은 필터를 사용합니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 가능한 세부 그룹은 dimensions, drawing, metadata, source, paths, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "assets": [], // 검색된 다이어그램 자산과 요청한 속성입니다.
  "total": 0, // 필터에 일치하는 전체 항목 수
  "offset": 0, // 현재 페이지 시작 위치
  "limit": 10, // 페이지 최대 항목 수
  "next_offset": null // 다음 페이지의 시작 위치입니다. null이면 다음 페이지가 없습니다.
}
```

# Drawing

도면 스타일·해치·평면 및 단면 생성 · prefix: `drawing_NN-` · 유형 내 순번 01–06

## 07. drawing_01-apply_style

기준 API: `drawing_01-apply_style`

근거: src/mcp/features/drawings/tools.py

### DESCRIPTION

도면 스타일 레시피를 Rhino 문서에 적용합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "recipe_id": {
      "default": "technical_axon_v1",
      "type": "string",
      "description": "drawing_05-list_recipes tool(include_ids=true)에서 얻은 도면 레시피 ID 또는 이미 알고 있는 레시피 ID입니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "recipe_id": "architectural_plan_section_a4_v1", // 도면 레시피 ID입니다.
  "layers": [ // 스타일을 적용한 레이어입니다.
    {
      "path": "ALMOND-DRAW::SECTION-CUT",
      "role": "section_cut",
      "layer_index": 1,
      "plot_weight_mm": 0.35,
      "linetype": "Continuous"
    }
  ],
  "review_preparation": { // A4 레시피에서 준비한 검토용 정보입니다.
    "status": "not_executed",
    "message": "PrintDisplay was not inspected or changed. Reuse a discovered pipe matching this connection's Rhino PID and saved document path; discover it only if unconfirmed. Skip this step if Document-scoped Model/Layout PrintDisplay On with Print colors is already confirmed.",
    "cli": {
      "program": "rhinocode",
      "discovery_arguments": [
        "list",
        "--json"
      ],
      "arguments_template": [
        "--rhino",
        "{matched_pipeId}",
        "command",
        "_PrintDisplay _Scope=_Document _Viewport=_Model _State=_On _Color=_Print _Viewport=_Layout _State=_On _Color=_Print _DetailBorder=_UsePrintWidth _Enter"
      ]
    }
  },
  "next_step_guide": "출력 검토에는 review_preparation의 설정을 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 33. drawing_02-get_recipe

기준 API: `drawing_02-get_recipe`

근거: src/mcp/features/drawings/tools.py

### DESCRIPTION

도면 스타일 레시피를 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "recipe_id": {
      "type": "string",
      "description": "drawing_05-list_recipes tool(include_ids=true)에서 얻은 도면 레시피 ID 또는 이미 알고 있는 레시피 ID입니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "상세 그룹: scales, parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "recipe_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "recipe": { // 선택한 도면 레시피의 요약입니다.
    "name": "Architectural Plan and Section A4",
    "description": "…",
    "projection": {
      "type": "parallel"
    }
  },
  "next_step_guide": "선택한 규칙을 문서에 적용하려면 drawing_01-apply_style tool을 사용합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 42. drawing_03-get_plan_section_result

기준 API: `drawing_03-get_plan_section_result`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

보관된 PlanSection 실행 결과를 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "result_id": {
      "type": "string",
      "description": "drawing_06-generate_plan_section tool의 result.result_id에서 얻은 의미를 해석하지 않는 32자 결과 영수증 ID입니다."
    },
    "offset": {
      "default": 0,
      "type": "integer",
      "description": "첫 페이지는 0, 이후에는 같은 결과의 next_offset을 그대로 입력합니다. UTF-16 코드 단위이므로 Python 문자열 길이로 계산하지 않습니다."
    },
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "result_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "result_id": "00000000000000000000000000000001", // 같은 Rhino 문서 인스턴스에 보관된 PlanSection 결과의 ID입니다. 다음 페이지 조회에 재사용합니다.
  "offset": 0, // 결과 문자열의 UTF-16 코드 단위 시작 위치입니다.
  "json_chunk": "{\"status\":\"completed\"}", // 전체 객체가 아니라 JSON 문자열 조각
  "total_characters": 22, // UTF-16 코드 단위 길이
  "next_offset": null, // 이어 읽을 UTF-16 코드 단위 위치입니다. null이면 마지막 페이지입니다.
  "result_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", // 보관된 전체 결과 문자열의 SHA-256 해시입니다.
  "observation": "…" // 보관된 실행 결과의 관찰 시점에 대한 안내입니다.
}
```

## 50. drawing_04-import_hatches

기준 API: `drawing_04-import_hatches`

근거: src/mcp/features/drawings/tools.py

### DESCRIPTION

등록된 PAT 자산의 해치 정의를 Rhino 문서에 추가합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "type": "string",
      "description": "해치 정의를 가져올 PAT 자산 ID입니다. 같은 이름의 해치 정의가 있으면 재사용합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "patterns": [ // 신규뿐 아니라 기존에 있어 사용 가능한 패턴 이름도 포함
    "ExamplePattern"
  ],
  "message": "…", // 현재 결과 또는 오류의 설명입니다.
  "error_trace": null // 오류 진단 정보입니다.
}
```

## 56. drawing_05-list_recipes

기준 API: `drawing_05-list_recipes`

근거: src/mcp/features/drawings/tools.py

### DESCRIPTION

도면 목적·투영 방식에 맞는 스타일 레시피를 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "상세 그룹: scales, parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

include_ids=true로 조회한 예시입니다.

```jsonc
{
  "total": 1, // 조회된 레시피 수입니다.
  "recipes": [ // 도면 레시피와 요청한 속성입니다.
    {
      "recipe_id": "architectural_plan_section_a4_v1",
      "name": "Architectural Plan and Section A4",
      "description": "…",
      "projection": "parallel",
      "recommended_scales": [
        "1:50",
        "1:100",
        "1:200"
      ]
    }
  ],
  "next_step_guide": "선택한 레시피의 ID로 drawing_02-get_recipe tool을 호출할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 65. drawing_06-generate_plan_section

기준 API: `drawing_06-generate_plan_section`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

클리핑 평면에서 모델 공간의 단면·해치·입면 도면을 생성하거나 갱신합니다. 부분 완료나 취소 뒤에도 만들어진 도면은 남을 수 있습니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "operation": {
      "enum": [
        "Create",
        "Update"
      ],
      "type": "string",
      "description": "Create 또는 Update입니다."
    },
    "clipping_ids": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "description": "확인된 클리핑 평면 GUID의 비어 있지 않은 목록입니다. 중복된 식별자는 한 번만 처리합니다."
    },
    "points": {
      "anyOf": [
        {
          "additionalProperties": {
            "items": {
              "anyOf": [
                {
                  "type": "number"
                },
                {
                  "type": "integer"
                }
              ]
            },
            "type": "array"
          },
          "type": "object"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "Create에서만 사용하는 선택적 매핑입니다. 요청한 클리핑 GUID를 문서 단위의 절대 도면 원점 [x,y] 또는 [x,y,z]에 대응시킵니다. Update에서는 생략합니다."
    },
    "hatch": {
      "default": true,
      "type": "boolean",
      "description": "기존 원본 단면 스타일로 단면 해치를 생성합니다."
    },
    "elevation": {
      "default": true,
      "type": "boolean",
      "description": "클리핑 평면 뒤에 보이는 입면 곡선을 포함합니다."
    },
    "small_details": {
      "default": true,
      "type": "boolean",
      "description": "true이면 기존의 작은 상세 보호 모드를 유지합니다."
    },
    "near_width": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "integer"
        }
      ],
      "default": 0.09,
      "description": "가장 가까운 입면 객체의 출력 선 두께(mm)입니다. 양수이며 far_width 이상이어야 합니다. 최종 출력에도 유지됩니다."
    },
    "far_width": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "integer"
        }
      ],
      "default": 0.04,
      "description": "가장 먼 입면 객체의 출력 선 두께(mm)입니다. 양수이며 near_width 이하여야 합니다. 최종 출력에도 유지됩니다."
    },
    "near_dark": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "integer"
        }
      ],
      "default": 80.0,
      "description": "가장 가까운 입면 객체의 출력 농도 백분율입니다. 0..100 범위이며 far_dark 이상이어야 합니다. 최종 출력에도 유지됩니다."
    },
    "far_dark": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "integer"
        }
      ],
      "default": 45.0,
      "description": "가장 먼 입면 객체의 출력 농도 백분율입니다. 0..100 범위이며 near_dark 이하여야 합니다. 최종 출력에도 유지됩니다."
    },
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "operation",
    "clipping_ids"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "drawing_status": "completed", // 생성된 도면의 상태입니다.
  "result": { // 단면 생성 결과입니다. 큰 결과에는 페이지 조회용 result_id가 포함됩니다.
    "status": "completed",
    "requested": 1,
    "completed": 1,
    "output": "Document",
    "result_delivery": "paged",
    "result_id": "00000000000000000000000000000001",
    "result_characters": 40000,
    "result_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "retention": "…"
  }
}
```

# Grasshopper

Grasshopper 로직·캡슐 조회와 실행 · prefix: `grasshopper_NN-` · 유형 내 순번 01–04

## 34. grasshopper_01-get_logic

기준 API: `grasshopper_01-get_logic`

근거: src/mcp/features/grasshopper/tools.py

### DESCRIPTION

Grasshopper 정의의 구성과 사용 계약을 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "logic_id": {
      "type": "string",
      "description": "기존 Grasshopper 라이브러리 파일명에서 확장자를 뺀 이름입니다. 알고 있는 ID를 재사용하거나 grasshopper_03-list_library tool(include_ids=true)에서 얻습니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "상세 그룹: ports, definition, source, paths, audit, all입니다. 생략하거나 비우면 요약을 반환합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "logic_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "file_name": "example.ghx", // 파일명입니다.
  "components": [ // 정의에 사용한 컴포넌트입니다.
    {
      "name": "Example component",
      "category": "Params",
      "descriptions": [
        "…"
      ]
    }
  ],
  "all_descriptions": [ // 정의에서 수집한 설명 목록입니다.
    "…"
  ],
  "metadata": {}, // 정의 파일에서 읽은 메타데이터입니다.
  "next_step_guide": "캡슐 계약과 실행 감사가 확인된 경우 grasshopper_04-run_definition tool으로 계산할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 51. grasshopper_02-list_capsules

기준 API: `grasshopper_02-list_capsules`

근거: src/mcp/features/grasshopper/tools.py

### DESCRIPTION

사용할 Grasshopper 캡슐을 찾습니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "capability": {
      "default": "",
      "type": "string",
      "description": "선택 필터: \"analyze\", \"generate\", \"form_find\", \"aggregate\"."
    },
    "audited_only": {
      "default": false,
      "type": "boolean",
      "description": "true이면 grasshopper_04-run_definition tool이 실행을 허용하는 캡슐만 나열합니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "상세 그룹: ports, definition, source, paths, audit, all입니다. 생략하거나 비우면 요약을 반환합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

include_ids=true, field_groups=["definition", "ports"]로 조회한 예시입니다.

```jsonc
{
  "total": 1, // 조회 조건에 맞는 전체 항목 수입니다.
  "offset": 0, // 이번 페이지의 시작 위치입니다.
  "limit": 50, // 이번 응답의 최대 항목 수입니다.
  "next_offset": null, // 다음 페이지의 시작 위치입니다. null이면 다음 페이지가 없습니다.
  "capsules": [ // 실행 캡슐과 요청한 포트·정의 정보입니다.
    {
      "capsule_id": "example-capsule",
      "capability": "analyze",
      "structure_type": null,
      "definition_file": "example.ghx",
      "title": "Example capsule",
      "audited": true,
      "inputs": [
        "ALMOND_IN_example"
      ],
      "outputs": [
        "ALMOND_OUT_example"
      ],
      "input_ports": [
        {
          "name": "ALMOND_IN_example",
          "type": "number",
          "units": "mm",
          "required": true
        }
      ],
      "output_ports": [
        {
          "name": "ALMOND_OUT_example",
          "type": "number",
          "units": "mm"
        }
      ]
    }
  ],
  "next_step_guide": "audited=true인 캡슐의 input_ports에 맞춰 inputs를 구성하고, capsule_id와 함께 grasshopper_04-run_definition tool에 입력합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 57. grasshopper_03-list_library

기준 API: `grasshopper_03-list_library`

근거: src/mcp/features/grasshopper/tools.py

### DESCRIPTION

로컬 색인에서 Grasshopper 로직 이름을 찾습니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "상세 그룹: ports, definition, source, paths, audit, all입니다. 생략하거나 비우면 요약을 반환합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "total_entries": 1, // 라이브러리 전체 항목 수입니다.
  "logic_names": [ // 기본 응답에서도 get_logic_by_id.logic_id로 사용 가능
    "example-logic"
  ],
  "logic_count": 1, // include_ids=false에서 logic_ids 대신 추가됨
  "next_step_guide": "logic_names에서 선택한 이름을 grasshopper_01-get_logic tool에 입력합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 77. grasshopper_04-run_definition

기준 API: `grasshopper_04-run_definition`

근거: src/mcp/features/grasshopper/tools.py

### DESCRIPTION

실행 감사를 통과한 Grasshopper 캡슐을 Rhino에서 계산합니다. 정의에 따라 형상을 베이크할 수 있습니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "capsule_id": {
      "type": "string",
      "description": "grasshopper_02-list_capsules tool에서 얻은 안정적인 캡슐 식별자입니다(예: \"karamba_beam_v1\")."
    },
    "inputs": {
      "additionalProperties": true,
      "type": "object",
      "description": "ALMOND_IN_ 포트 이름과 값의 객체입니다. grasshopper_02-list_capsules tool(field_groups=['ports'])의 input_ports에서 타입·단위·필수 여부를 확인합니다. 형상은 {\"guids\":[\"객체 GUID\"]}, 숫자·정수·문자열·불리언은 JSON 값, 목록은 number[]/integer[]/string[]의 평탄한 배열입니다."
    },
    "seed": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "확률적 정의에 사용할 선택적 정수 시드입니다. 결정적인 정의에서는 생략합니다."
    },
    "timeout_s": {
      "default": 60.0,
      "type": "number",
      "description": "솔버 시간 한도(초)입니다. 기본값은 60, 최댓값은 600입니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "capsule_id",
    "inputs"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "ok", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "capsule_id": "example-capsule", // 실행한 캡슐 ID입니다.
  "outputs": {}, // 출력 포트별 값입니다. 의미·타입·단위는 캡슐 계약에 따릅니다.
  "baked_guids": [ // 생성 객체 관찰·캡처에 재사용
    "00000000-0000-0000-0000-000000000001"
  ],
  "analysis_method": "template", // 해석 방식입니다.
  "confidence": "medium", // 매니페스트 선언: api/high, template/medium, rule_based/low
  "warnings": [], // 결과를 해석할 때 확인할 경고입니다.
  "error": null, // 오류 내용입니다.
  "next_step_guide": "베이크한 형상이 있으면 inspect_02-get_objects tool와 캡처로 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

# Research

구법·건축 유형·참고자료 조사 · prefix: `research_NN-` · 유형 내 순번 01–03

## 27. research_01-get_construction_guidance

기준 API: `research_01-get_construction_guidance`

근거: src/mcp/features/guidance/tools.py

### DESCRIPTION

건축 구법을 비교하고 선택할 참고 자료를 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "query": {
      "default": "",
      "type": "string",
      "description": "자유 텍스트 필터입니다(예: \"glulam\", \"longspan\", \"bearing wall\")."
    },
    "category": {
      "default": "",
      "type": "string",
      "description": "\"floor\", \"wall\", \"roof\", \"foundation\" 중 하나입니다. 비워 두면 모두 포함합니다."
    },
    "material": {
      "default": "",
      "type": "string",
      "description": "analysis_04-validate_structure tool에서 사용하는 이름: \"Wood\", \"Steel\", \"Concrete\"."
    },
    "structure_type": {
      "default": "",
      "type": "string",
      "description": "analysis_04-validate_structure tool의 유형입니다(\"beam\", \"truss\", \"shell\", \"frame\", \"canopy\", \"gridshell\", \"membrane\", \"highrise\")."
    },
    "span_m": {
      "default": 0.0,
      "type": "number",
      "description": "0보다 크면 반환되는 각 시스템이 fits_span과 경간 비율 규칙에 따른 권장 부재 깊이를 보고합니다."
    },
    "include_reference_data": {
      "default": false,
      "type": "boolean",
      "description": "load_kn 입력을 정하는 데 사용할 용도별 활하중(kPa)과 재료 밀도(kg/m3)도 반환합니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "상세 그룹: rules, narrative, source, metadata, audit, all입니다. 생략하거나 비우면 요약을 반환합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "total": 1, // 조회 조건에 맞는 전체 항목 수입니다.
  "source": "…", // 예비 치수 산정용 라이브러리 출처
  "systems": [ // 검색한 구조 시스템과 요청한 경험칙·재료 정보입니다.
    {
      "system_id": "wood-joist-floor",
      "name": "Wood joist floor (dimension lumber)",
      "category": "floor",
      "structural_material": "Wood",
      "fits_span": true,
      "depth_guidance": [
        {
          "element": "joist",
          "suggested_depth_mm": 300,
          "rule": "span/16"
        }
      ],
      "construction_detail": "Wood joist floor (dimension lumber)",
      "construction_reference": {
        "kind": "construction_system",
        "id": "wood-joist-floor"
      },
      "render_material_ids": [
        "wood-oak"
      ]
    }
  ],
  "next_step_guide": "선택한 구법을 객체에 기록하려면 model_01-assign_material tool을 사용합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 48. research_02-get_typology_narrative

기준 API: `research_02-get_typology_narrative`

근거: src/mcp/features/guidance/tools.py

### DESCRIPTION

건축 유형의 서사와 선례를 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "query": {
      "default": "",
      "type": "string",
      "description": "자유 텍스트입니다(예: \"courtyard\", \"skyscraper\", \"timber hall\")."
    },
    "construction_system": {
      "default": "",
      "type": "string",
      "description": "구법 라이브러리의 system_id와 관련된 항목으로 필터링합니다(예: \"steel-column-frame\")."
    },
    "structure_type": {
      "default": "",
      "type": "string",
      "description": "analysis_04-validate_structure tool의 유형으로 필터링합니다(\"shell\", \"truss\", \"frame\", \"membrane\" 등)."
    },
    "limit": {
      "default": 5,
      "type": "integer",
      "description": "반환할 최대 항목 수입니다. 기본값은 5입니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "상세 그룹: rules, narrative, source, metadata, audit, all입니다. 생략하거나 비우면 요약을 반환합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "total": 1, // limit를 적용하기 전 전체 일치 수
  "entries": [ // 검색된 유형 설명과 요청한 속성입니다.
    {
      "typology_id": "example-typology",
      "name": "예시 건축 유형",
      "era": "예시 시대",
      "region": "예시 지역",
      "narrative": "…",
      "urban_role": "…",
      "related_construction_systems": [
        "example-system"
      ]
    }
  ],
  "source": "…", // 자료 출처입니다.
  "next_step_guide": "관련 구법은 research_01-get_construction_guidance tool로 비교할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 80. research_03-search_details

기준 API: `research_03-search_details`

근거: src/mcp/features/guidance/tools.py

### DESCRIPTION

건축 자료 디렉터리의 metadata를 검색합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "query": {
      "default": "",
      "type": "string",
      "description": "자유 텍스트 검색어입니다. 비워 두면 텍스트 필터를 적용하지 않습니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "상세 그룹: rules, narrative, source, metadata, audit, all입니다. 생략하거나 비우면 요약을 반환합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "query": "timber", // 검색어입니다.
  "query_terms": [ // 원래 검색어에서 추출한 단어입니다.
    "timber"
  ],
  "expanded_terms": [], // 검색에 추가한 관련 단어입니다.
  "sources": [ // 조건에 일치하는 상세 자료 출처입니다.
    {
      "source_id": "dataholz",
      "title": "dataholz timber assemblies",
      "url": "https://www.dataholz.eu/en/index.htm",
      "terms_url": "https://www.dataholz.eu/allgemeine-nutzungsbedingungen.htm",
      "formats": [
        "web",
        "pdf"
      ],
      "access": "공개 참고자료",
      "redistribution": "제한됨. 개별 항목 검토 필요",
      "generation_use": "candidate_only",
      "matched_terms": [
        "timber"
      ]
    }
  ],
  "scope": "…" // 검색한 출처 디렉터리의 범위입니다.
}
```

# Analysis

구조·피난 검토와 보고서 · prefix: `analysis_NN-` · 유형 내 순번 01–05

## 12. analysis_01-check_egress

기준 API: `analysis_01-check_egress`

근거: src/mcp/features/egress/tools.py

### DESCRIPTION

피난 조건을 예비 검토합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "plate_bounds_mm": {
      "items": {
        "type": "number"
      },
      "type": "array",
      "description": "mm 단위의 층 바닥 경계 [min_x, min_y, max_x, max_y]입니다. 전체 면적과 출구 이격거리에 사용하는 대각선을 결정합니다."
    },
    "exits": {
      "items": {
        "additionalProperties": true,
        "type": "object"
      },
      "type": "array",
      "description": "출구(계단실 문 또는 외부 출입문)마다 항목 하나를 제공합니다: {\"name\": str, \"x_mm\": float, \"y_mm\": float, \"width_mm\": float}. 위치는 문 중심이며, 너비는 피난에 사용할 수 있는 유효 너비입니다."
    },
    "occupancy": {
      "default": "business",
      "type": "string",
      "description": "재실 인원 산정에 사용할 키: business, mercantile, assembly_unconcentrated, classroom, residential, storage."
    },
    "stories": {
      "default": 1,
      "type": "integer",
      "description": "담당하는 층수입니다. 1을 초과하면 최소 2개 출구가 필요하며, 필요 출구 너비에는 문 계수(5.1) 대신 계단 계수(재실자당 7.6 mm)를 사용합니다."
    },
    "sprinklered": {
      "default": true,
      "type": "boolean",
      "description": "전체에 스프링클러가 설치됐는지 여부입니다. 이격 비율, 보행거리, 막다른 복도 길이 제한에 영향을 줍니다."
    },
    "net_area_m2": {
      "default": 0.0,
      "type": "number",
      "description": "재실 면적을 대체합니다. 0이면 전체 바닥 면적을 사용합니다."
    },
    "travel_distances_m": {
      "default": [],
      "items": {
        "type": "number"
      },
      "type": "array",
      "description": "측정한 최악 조건의 보행거리입니다(예: 그려진 피난 경로에서 측정). 비워 두면 보행거리 검사를 건너뜁니다."
    },
    "dead_end_m": {
      "default": 0.0,
      "type": "number",
      "description": "가장 긴 막다른 복도의 길이(미터)입니다. 0이면 검사를 건너뜁니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "plate_bounds_mm",
    "exits"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "passed": false, // 실제 수행한 검사만 합산. 빠진 경로 검사를 통과한 것이 아님
  "occupancy": "business", // 건물 용도입니다.
  "occupant_load": 65, // 면적과 용도별 1인당 면적으로 계산해 올림한 재실 인원입니다.
  "area_m2": 600, // 입력한 면적(m²)입니다.
  "gross_area_m2": 600, // 경계 직사각형 면적이지 불규칙 바닥의 실측 면적은 아님
  "checks": [ // 수행한 항목별 검사 결과입니다.
    {
      "check": "exit_count",
      "required": 2,
      "provided": 1,
      "passed": false,
      "basis": "…"
    }
  ],
  "warnings": [], // 결과를 해석할 때 확인할 경고입니다.
  "source_note": "…", // 계산 기준의 출처와 적용 범위입니다.
  "next_step_guide": "미달 항목의 배치·너비·경로를 수정하고 측정값을 갱신해 다시 검토합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 22. analysis_02-export_structural_report

기준 API: `analysis_02-export_structural_report`

근거: src/mcp/features/structure/tools.py

### DESCRIPTION

저장된 구조 검증 이력을 Markdown 보고서로 작성합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "path": {
      "default": "",
      "type": "string",
      "description": "관리형 세션에서는 선택한 Plan 산출물 디렉터리 아래의 상대 파일 경로이며, 기본값은 reports/structural-validation.md입니다. 독립 실행의 기본값은 사용자 데이터의 reports/structural-validation-<timestamp>.md입니다."
    },
    "limit": {
      "default": 50,
      "type": "integer",
      "description": "포함할 최대 실행 개수입니다. 기본값은 50, 최댓값은 500입니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "path": ".almond/produced/261111_example/structure-report.md", // 작성된 Markdown 파일
  "runs": 1, // 실제 포함한 저장 실행 수
  "latest_method": "native" // 가장 최근 저장된 실행 방식
}
```

## 52. analysis_03-list_design_codes

기준 API: `analysis_03-list_design_codes`

근거: src/mcp/features/structure/tools.py

### DESCRIPTION

구조 해석에 사용할 설계기준 프로필을 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "상세 그룹: parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

include_ids=true로 조회한 예시입니다.

```jsonc
{
  "default": "eurocode", // 기본 설계 기준 ID입니다.
  "profiles": [ // 설계 기준 프로필과 요청한 매개변수입니다.
    {
      "id": "eurocode",
      "name": "…",
      "basis": "…",
      "verified": true,
      "unverified": [],
      "deflection_limit_ratio": 250,
      "imposed_floor_kn_m2": {}
    }
  ],
  "problems": [], // 로딩 중 거부된 사용자 프로필 문제
  "user_dir": "…", // 사용자 설계 기준 프로필 폴더입니다.
  "next_step_guide": "기준을 적용하려면 include_ids=true로 설계 기준 ID를 조회합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 91. analysis_04-validate_structure

기준 API: `analysis_04-validate_structure`

근거: src/mcp/features/structure/tools.py

### DESCRIPTION

Rhino 구조 형상을 해석하고 설계기준에 따라 검토합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "guids": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "description": "해석 범위에 포함되는 현재 Rhino 객체 GUID 문자열입니다."
    },
    "structure_type": {
      "default": "beam",
      "type": "string",
      "description": "사용할 해석 템플릿입니다. 선택지: \"beam\"은 단순 보의 휨/처짐, \"truss\"는 축력/좌굴 해석, \"shell\"은 셸 응력/변위, \"frame\"은 프레임 모멘트/전단 해석, \"canopy\"는 캔틸레버 캐노피, \"gridshell\"은 대변형 그리드셸, \"membrane\"은 막 구조 형상 탐색, \"highrise\"는 고층 구조 시스템입니다."
    },
    "load_kn": {
      "default": 10.0,
      "type": "number",
      "description": "전체 부과하중(kN)입니다. native에서는 자유 절점에 하향(-Z) 균등 분배합니다. 바닥·자산 하중과 중복 계산되지 않게 산정하며 필요한 경우 0으로 입력합니다."
    },
    "material": {
      "default": "Steel",
      "type": "string",
      "description": "재료 유형: \"Steel\", \"S355\", \"Concrete\", \"Wood\", \"Aluminium\". 기본값은 \"Steel\"입니다."
    },
    "engine": {
      "default": "auto",
      "type": "string",
      "description": "auto, native, karamba 중 선택합니다. auto는 선형 프레임에 native를, 그 외에는 Karamba를 사용합니다. karamba는 사용 가능한 api, template, rule_based 순으로 시도합니다. 결과의 analysis_method와 warnings를 확인합니다."
    },
    "fixed_supports": {
      "default": true,
      "type": "boolean",
      "description": "True는 완전 고정 지점, False는 핀 지점(회전 자유)을 뜻합니다."
    },
    "self_weight": {
      "default": true,
      "type": "boolean",
      "description": "부재 자중을 포함합니다."
    },
    "span_m": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "부재가 모든 절점에서 분할됐을 때 L/250 한계에 사용할 구조 경간(미터)입니다. 예를 들어 6.2 m 장선을 3.1 m 구간 두 개로 그린 경우에 사용합니다. 네이티브 엔진 전용입니다."
    },
    "asset_loads": {
      "default": false,
      "type": "boolean",
      "description": "true이면 배치된 라이브러리 자산의 자중·내용물·재실자 하중을 추가합니다. 네이티브 엔진에서 사용합니다. 다른 하중 입력에 이미 포함한 무게를 중복 적용하지 않습니다."
    },
    "floor_load_kn_m2": {
      "default": 0.0,
      "type": "number",
      "description": "한 층에서 보로 둘러싸인 모든 구획에 적용할 부과 바닥 하중(kN/m2)입니다(예: 주거용 2.0, EN 1991-1-1의 category A). 보는 45도 분배 규칙에 따라 하중을 받습니다(2방향, 장단변비 2:1 초과 시 1방향). 네이티브 엔진 전용입니다. 설계기준의 바닥 하중에는 이동 가능한 가구와 사람이 이미 포함되므로, asset_loads는 무거운 특정 물품에 대해서만 함께 사용하고 중복 계산을 피하려면 load_kn을 0으로 설정합니다."
    },
    "floor_dead_kn_m2": {
      "default": 0.0,
      "type": "number",
      "description": "같은 구획에 적용할 추가 고정하중(kN/m2)입니다. 바닥 구성층과 마감 등을 포함합니다."
    },
    "design_basis": {
      "default": "en1990",
      "type": "string",
      "description": "\"en1990\"(기본값)은 SLS 특성 조합(G + Q)에서 처짐을, ULS 1.35 G + 1.5 Q에서 부재를 검토합니다. G는 자중, 바닥 구성층, 배치된 물품의 중량이고, Q는 load_kn, 용도별 바닥 활하중, 내용물, 재실자입니다. \"unfactored\"는 둘 다 G + Q에서 검토합니다(Karamba 경로의 기준). 네이티브 엔진에 적용됩니다."
    },
    "uls_combination": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "\"6.10\" 또는 \"6.10ab\"입니다. \"6.10ab\"는 부재별로 6.10a와 6.10b 중 더 불리한 결과를 사용합니다. 기본값은 설계기준이 선택한 식입니다(Eurocode 프로필: 6.10). 특정 식을 지정한 프로필은 요청보다 우선하며 경고를 반환합니다."
    },
    "connections": {
      "default": "rigid",
      "type": "string",
      "description": "\"rigid\"(기본값)는 모든 접합부가 모멘트를 전달합니다. \"simple\"은 보를 핀 접합(강축 휨 해제)으로, 가새를 양축 핀 접합으로 처리하되, 다른 부재가 같은 선상으로 계속 이어지는 지점이 아니라 해당 부재가 끝나는 지점에 적용하며 기둥은 연속으로 유지합니다. 일반적인 볼트 접합 강구조와 목구조 프레임은 \"simple\"에 더 가깝습니다. 강접합은 보 처짐을 실제보다 유리하게 보이게 할 수 있습니다. 곡선의 사용자 텍스트 almond:release = \"pinned\" | \"pinned_start\" | \"pinned_end\" | \"rigid\"는 두 모드보다 우선합니다. 네이티브 엔진에 적용됩니다."
    },
    "stability": {
      "default": "auto",
      "type": "string",
      "description": "\"auto\"(기본값)는 모든 ULS 조합의 탄성 임계 하중 계수 alpha_cr(EN 1993-1-1 5.2.1)과 +/-x 및 +/-y 방향의 횡변위 초기 불완전성 phi = 1/200 x alpha_h x alpha_m(5.3.2)을 적용합니다. alpha_cr < 10이면 2차(P-Delta) ULS 해석을 실행하며, alpha_cr <= 1이면 불안정으로 실패 처리합니다. \"off\"는 초기 불완전성 없는 1차 해석입니다."
    },
    "design_code": {
      "default": "eurocode",
      "type": "string",
      "description": "설계기준 또는 국가 부록에서 정하는 수치(gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, 처짐 한계)에 사용할 설계기준 프로필입니다. \"eurocode\"(기본값, EN 권장값), analysis_03-list_design_codes tool의 프로필 또는 \"off\"를 사용합니다. \"off\"는 부분계수 없이 G + Q를 적용하며 design_basis=\"unfactored\"와 같습니다. 결과의 \"design_code\"에는 사용한 값과 검증되지 않은 값이 포함됩니다."
    },
    "detail": {
      "default": false,
      "type": "boolean",
      "description": "true이면 네이티브 해석의 부재별 단면력·사용률·처짐과 지점 반력을 포함합니다."
    },
    "fabrication": {
      "default": "cold_formed",
      "type": "string",
      "description": "중공 강재 단면(CHS/RHS)은 \"cold_formed\"(기본값, EN 10219, 좌굴 곡선 c) 또는 \"hot_finished\"(EN 10210, 곡선 a, S460은 a0)입니다. 좌굴 내력에 최대 약 23% 차이가 있으므로, hot_finished는 명시된 경우에만 사용합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "guids"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "pass", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "passed": true, // indicative인 경우 null 가능. 구조 안전 인증을 뜻하지 않음
  "structure_type": "beam", // 구조 유형입니다.
  "material": "Steel", // 재료입니다.
  "confidence": "high", // 경고·가정·미검증 값과 함께 해석
  "results": { // 구조 검토의 수치와 부재별 결과입니다.
    "analysis_method": "native",
    "max_deflection_mm": 12,
    "deflection_limit_mm": 24,
    "span_m": 6,
    "utilization_ratio": 0.72,
    "per_element_utilization": [
      {
        "source_guids": [
          "00000000-0000-0000-0000-000000000001"
        ],
        "utilization": 0.72,
        "combination": "…"
      }
    ]
  },
  "worst_member_guids": [ // 상위 최대 5개, 전체 해석 범위 아님
    "00000000-0000-0000-0000-000000000001"
  ],
  "warnings": [], // 결과를 해석할 때 확인할 경고입니다.
  "assumptions": [ // 검토에 사용한 가정입니다.
    "…"
  ],
  "design_code": { // 검토에 사용한 설계 기준 프로필입니다.
    "id": "eurocode",
    "unverified": []
  },
  "next_step_guide": "문제 부재는 analysis_05-visualize_structure tool로 검토할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 92. analysis_05-visualize_structure

기준 API: `analysis_05-visualize_structure`

근거: src/mcp/features/structure/tools.py

### DESCRIPTION

구조 해석 결과를 임시 뷰포트 오버레이로 표시합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "guids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "구조 축선의 곡선 GUID와 지점을 표시하는 점 GUID입니다(fixed_supports 참조). 점이 없으면 최하단 절점을 지점으로 사용합니다."
    },
    "load_kn": {
      "default": 10.0,
      "type": "number",
      "description": "자유 절점에 하향(-Z)으로 균등 분배할 전체 부과하중(kN)입니다."
    },
    "material": {
      "default": "Steel",
      "type": "string",
      "description": "\"Steel\", \"S355\", \"Concrete\", \"Wood\", \"Aluminium\" 중 하나입니다."
    },
    "beam_diameter_mm": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 항목인 원형 부재 외경(밀리미터)입니다."
    },
    "beam_wall_mm": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 항목인 중공 부재의 벽 두께(밀리미터)입니다."
    },
    "self_weight": {
      "default": true,
      "type": "boolean",
      "description": "중력을 포함합니다."
    },
    "fixed_supports": {
      "default": true,
      "type": "boolean",
      "description": "True는 완전 고정 지점, False는 핀 지점(회전 자유)을 뜻합니다."
    },
    "deflection_limit_ratio": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "경간/비율 한계입니다. 예를 들어 L/250은 250입니다. 기본값은 설계기준의 한계입니다(Eurocode 프로필: 250)."
    },
    "span_m": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "한계에 사용할 기준 경간(미터)입니다. 기본값은 가장 긴 부재입니다. 부재가 모든 절점에서 분할됐다면 지정합니다. 예: 6.2 m 장선을 3.1 m 구간 두 개로 그린 경우."
    },
    "color_by": {
      "default": "displacement",
      "type": "string",
      "description": "\"displacement\" 또는 \"utilization\"입니다."
    },
    "scale": {
      "anyOf": [
        {
          "type": "number"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "변형 과장 배율입니다. 생략하면 자동으로 정합니다(경간의 약 6%)."
    },
    "reveal": {
      "default": 1.0,
      "type": "number",
      "description": "그릴 부재의 비율이며 0..1 범위입니다. 단계별 시공 재생에 사용합니다."
    },
    "reanalyze": {
      "default": true,
      "type": "boolean",
      "description": "False이면 마지막 계산을 재사용하고 표시(scale / color_by / reveal / physics / title)만 변경합니다. 애니메이션에 사용할 수 있을 만큼 계산 부담이 작습니다."
    },
    "physics": {
      "default": true,
      "type": "boolean",
      "description": "False이면 해석 오버레이 없이 같은 부재를 일반 형상으로 그립니다(\"physics off\"). 전후 비교에 사용합니다."
    },
    "display_guids": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "이 부재들만 그립니다(예: 단면 보기를 위한 한 줄의 프레임). 해석은 여전히 guids의 모든 부재를 포함합니다."
    },
    "title": {
      "default": "",
      "type": "string",
      "description": "범례 제목입니다."
    },
    "clear": {
      "default": false,
      "type": "boolean",
      "description": "오버레이를 제거합니다."
    },
    "engine": {
      "default": "auto",
      "type": "string",
      "description": "\"auto\"(기본값), \"native\", \"karamba\" 중 하나입니다. \"auto\"는 Karamba 없이 Almond 네이티브 프레임 솔버를 사용하되, 선택에 셸이 있거나 브리지가 모델을 내보낼 수 없으면 Karamba를 사용합니다."
    },
    "asset_loads": {
      "default": false,
      "type": "boolean",
      "description": "analysis_04-validate_structure tool와 동일하게 배치된 라이브러리 자산의 하중을 추가합니다(네이티브 엔진). 하중 작용점에 하중 화살표를 그립니다."
    },
    "floor_load_kn_m2": {
      "default": 0.0,
      "type": "number",
      "description": "한 층에서 보로 둘러싸인 모든 구획에 적용할 부과 바닥 하중(kN/m2)입니다(예: 주거용 2.0, EN 1991-1-1의 category A). 보는 45도 분배 규칙에 따라 하중을 받습니다(2방향, 장단변비 2:1 초과 시 1방향). 네이티브 엔진 전용입니다. 설계기준의 바닥 하중에는 이동 가능한 가구와 사람이 이미 포함되므로, asset_loads는 무거운 특정 물품에 대해서만 함께 사용하고 중복 계산을 피하려면 load_kn을 0으로 설정합니다."
    },
    "floor_dead_kn_m2": {
      "default": 0.0,
      "type": "number",
      "description": "같은 구획에 적용할 추가 고정하중(kN/m2)입니다. 바닥 구성층과 마감 등을 포함합니다."
    },
    "design_basis": {
      "default": "en1990",
      "type": "string",
      "description": "\"en1990\"(기본값)은 SLS 특성 조합(G + Q)에서 처짐을, ULS 1.35 G + 1.5 Q에서 부재를 검토합니다. G는 자중, 바닥 구성층, 배치된 물품의 중량이고, Q는 load_kn, 용도별 바닥 활하중, 내용물, 재실자입니다. \"unfactored\"는 둘 다 G + Q에서 검토합니다(Karamba 경로의 기준). 네이티브 엔진에 적용됩니다."
    },
    "uls_combination": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "\"6.10\" 또는 \"6.10ab\"입니다. \"6.10ab\"는 부재별로 6.10a와 6.10b 중 더 불리한 결과를 사용합니다. 기본값은 설계기준이 선택한 식입니다(Eurocode 프로필: 6.10). 특정 식을 지정한 프로필은 요청보다 우선하며 경고를 반환합니다."
    },
    "connections": {
      "default": "rigid",
      "type": "string",
      "description": "analysis_04-validate_structure tool와 동일한 \"rigid\" 또는 \"simple\"입니다. 핀 접합 단부는 작은 원으로 그립니다."
    },
    "stability": {
      "default": "auto",
      "type": "string",
      "description": "analysis_04-validate_structure tool와 동일한 \"auto\" 또는 \"off\"입니다."
    },
    "design_code": {
      "default": "eurocode",
      "type": "string",
      "description": "설계기준 또는 국가 부록에서 정하는 수치(gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, 처짐 한계)에 사용할 설계기준 프로필입니다. \"eurocode\"(기본값, EN 권장값), analysis_03-list_design_codes tool의 프로필 또는 \"off\"를 사용합니다. \"off\"는 부분계수 없이 G + Q를 적용하며 design_basis=\"unfactored\"와 같습니다. 결과의 \"design_code\"에는 사용한 값과 검증되지 않은 값이 포함됩니다."
    },
    "fabrication": {
      "default": "cold_formed",
      "type": "string",
      "description": "중공 강재 단면(CHS/RHS)은 \"cold_formed\"(기본값, EN 10219, 좌굴 곡선 c) 또는 \"hot_finished\"(EN 10210, 곡선 a, S460은 a0)입니다. 좌굴 내력에 최대 약 23% 차이가 있으므로, hot_finished는 명시된 경우에만 사용합니다."
    },
    "view": {
      "default": "deflection",
      "type": "string",
      "description": "\"deflection\"(기본값) 또는 \"buckling\"입니다. \"buckling\"은 처짐 형상 대신 지배 ULS 조합의 첫 번째 좌굴 모드를 alpha_cr과 함께 그립니다(STABLE >= 10, SWAY-SENSITIVE 1-10, UNSTABLE <= 1)."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "pass", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "analysis_method": "native", // 해석 방식입니다.
  "max_displacement_mm": 12, // 최대 변위(mm)입니다.
  "deflection_limit_mm": 24, // 허용 처짐(mm)입니다.
  "span_m": 6, // 검토 스팬(m)입니다.
  "max_utilization": 0.72, // 최대 부재 사용률입니다. 해당 해석에서 계산하지 않으면 null입니다.
  "scale": 30, // 실제 변위가 아닌 표시 과장 배율
  "elements": [ // 시각화한 부재별 결과입니다.
    {
      "source_guids": [
        "00000000-0000-0000-0000-000000000001"
      ],
      "max_displacement_mm": 12,
      "utilization": 0.72
    }
  ],
  "nodes": 2, // 해석 노드 수입니다.
  "warnings": [], // 결과를 해석할 때 확인할 경고입니다.
  "next_step_guide": "판정을 검증 이력으로 남기려면 analysis_04-validate_structure tool를 사용합니다.", // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
  "passed": true // 검토 기준 충족 여부입니다. indicative의 null은 해석은 완료했으나 재료 내력 합격 판정을 하지 않았음을 뜻합니다.
}
```

# Exchange

앱 간 자산 교환·Chestnut 게시 · prefix: `exchange_NN-` · 유형 내 순번 01–05

## 21. exchange_01-export_asset_contract

기준 API: `exchange_01-export_asset_contract`

근거: src/mcp/features/exchange/tools.py

### DESCRIPTION

Rhino 객체를 GLB와 Almond 자산 계약 파일로 내보냅니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "guids": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "description": "기존 객체 관찰, 선택 또는 모델링 결과에서 얻은 현재 Rhino 객체 GUID입니다."
    },
    "asset_id": {
      "type": "string",
      "description": "안정적으로 유지할 ID입니다. 예: \"canopy-pavilion-01\". 영문자, 숫자, . _ -를 사용합니다."
    },
    "name": {
      "default": "",
      "type": "string",
      "description": "사람이 읽을 수 있는 이름입니다. 기본값은 asset_id입니다."
    },
    "output_dir": {
      "default": "",
      "type": "string",
      "description": "관리형 세션에서는 선택한 Plan 산출물 폴더에 대한 상대 경로이며, 기본값은 exchange입니다. 독립 실행에서는 대상 폴더이며, 기본값은 <user data dir>/exchange입니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "guids",
    "asset_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

next_step_guide는 현재 서버가 반환하는 영어 원문입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "asset_id": "example-asset", // 자산 ID입니다.
  "glb_path": ".almond/produced/261111_example/example-asset.glb", // 내보낸 GLB 파일 경로입니다.
  "contract_path": ".almond/produced/261111_example/example-asset.almond.json", // import_asset_contract에 전달
  "dimensions_mm": { // 내보낸 자산의 경계 치수입니다. 단위는 mm입니다.
    "width": 1000,
    "depth": 500,
    "height": 800
  },
  "materials": [], // 인식된 Almond 재료 그룹. 비어 있어도 모든 재료가 보존됐다는 뜻은 아님
  "next_step_guide": "If importing into a destination Rhino is intended, pass the returned contract_path to exchange_03-import_asset_contract tool(contract_path=...) and choose its placement coordinates in mm; exporting alone does not request another import. For Blender, import the returned glb_path there and verify materials/placement; exchange_02-get_blender_script tool supports export and materials, not import." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 26. exchange_02-get_blender_script

기준 API: `exchange_02-get_blender_script`

근거: src/mcp/features/exchange/tools.py

### DESCRIPTION

Blender의 선택 형상 내보내기 또는 재료 설정에 사용할 Python 코드를 생성합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "action": {
      "type": "string",
      "description": "\"export\" 또는 \"materials\"입니다."
    },
    "asset_id": {
      "default": "",
      "type": "string",
      "description": "export에 필요한 값으로, 내보낸 파일에 사용할 안정적인 식별자입니다."
    },
    "name": {
      "default": "",
      "type": "string",
      "description": "내보내기 표시 이름입니다. 기본값은 asset_id입니다."
    },
    "output_dir": {
      "default": "",
      "type": "string",
      "description": "내보내기 대상 위치입니다. 관리형 세션에서는 선택한 Plan이 필요하며, 해당 산출물 디렉터리 아래의 상대 폴더를 사용합니다. 기본값은 exchange입니다. 독립 실행 호출의 기본값은 사용자 데이터의 exchange 폴더입니다."
    },
    "material_id": {
      "default": "",
      "type": "string",
      "description": "materials에 필요한, 알고 있는 라이브러리 재료 ID입니다."
    },
    "object_names": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "materials에 필요한 실제 Blender 객체 이름의 비어 있지 않은 목록입니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 사용할 ID를 포함합니다."
    },
    "field_groups": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 항목은 notes, audit, all입니다. script는 기본 응답에 유지됩니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "action"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "action": "export", // 스크립트의 작업 종류입니다.
  "script": "<생성된 Blender Python 소스>", // Blender에서 실행할 Python 코드입니다.
  "next_step_guide": "생성한 코드는 Blender에서 실행합니다. export 실행이 성공하면 얻은 계약을 exchange_03-import_asset_contract tool에 사용할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 49. exchange_03-import_asset_contract

기준 API: `exchange_03-import_asset_contract`

근거: src/mcp/features/exchange/tools.py

### DESCRIPTION

Almond 자산 계약에 따라 GLB를 Rhino 문서로 가져옵니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "contract_path": {
      "type": "string",
      "description": "exchange_01-export_asset_contract tool 또는 Blender 내보내기가 반환한 계약 경로입니다. 관리형 세션에서는 프로젝트 기준 상대 .almond.json 경로이고, 독립 실행에서는 절대 경로입니다."
    },
    "x_mm": {
      "default": 0,
      "type": "number",
      "description": "계약 앵커의 X 배치 좌표(밀리미터)입니다. 기본값은 0입니다."
    },
    "y_mm": {
      "default": 0,
      "type": "number",
      "description": "계약 앵커의 Y 배치 좌표(밀리미터)입니다. 기본값은 0입니다."
    },
    "z_mm": {
      "default": 0,
      "type": "number",
      "description": "계약 앵커의 Z 배치 좌표(밀리미터)입니다. 기본값은 0입니다."
    },
    "rotation_degrees": {
      "default": 0,
      "type": "number",
      "description": "월드 Z축 기준 회전입니다."
    },
    "layer": {
      "default": "ALMOND-EXCHANGE",
      "type": "string",
      "description": "대상 레이어입니다. 없으면 생성합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "contract_path"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "asset_id": "example-asset", // 자산 ID입니다.
  "source_app": "blender", // 자산을 내보낸 앱입니다.
  "imported_count": 1, // 가져온 객체 수입니다.
  "imported_guids": [ // 객체 관찰·캡처·재료 보정에 재사용
    "00000000-0000-0000-0000-000000000001"
  ],
  "metadata_restored": 1, // 메타데이터를 기록한 객체 수
  "materials_deduplicated": 0, // 중복 제거한 재료 수입니다.
  "unknown_material_ids": [], // Almond 라이브러리에서 찾지 못한 재료 ID입니다.
  "dimension_check": { // 내보내기 전후의 경계 치수 비교입니다.
    "status": "ok",
    "expected_sorted_mm": [
      500,
      800,
      1000
    ],
    "measured_sorted_mm": [
      500,
      800,
      1000
    ],
    "worst_relative_error": 0,
    "tolerance": 0.02
  },
  "layer": "ALMOND-EXCHANGE", // 가져온 객체의 레이어입니다.
  "next_step_guide": "inspect_02-get_objects tool와 캡처로 가져온 형상·재료·배치를 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

응답 유실 시의 코드 기반 예시입니다. 실제 Rhino 검증 결과가 아니며, 오류를 되돌리기 완료로 해석하지 않습니다.

```jsonc
{
  "status": "error",
  "message": "Import completion is unconfirmed: reply lost after native import",
  "requires_reconciliation": true, // 기존 Rhino 객체를 확인하기 전 같은 가져오기를 재시도하지 않습니다.
  "mutation_applied": null // 변경 완료 여부를 확인하지 못했습니다.
}
```

복원 단계에서 응답을 잃으면 확인된 `imported_guids`도 함께 반환합니다. 결과 직렬화 실패에는 `result_error`, 관리형 가져오기 보고서 검증 실패에는 `report_path`가 포함될 수 있습니다.

## 68. exchange_04-publish_chestnut_advanced

기준 API: `exchange_04-publish_chestnut_advanced`

근거: src/mcp/features/publishing/tools.py

### DESCRIPTION

Rhino 객체를 물리·콜라이더 설정이 있는 GLB로 Chestnut에 게시합니다. 원본 문서 경로·GUID 등의 metadata도 업로드됩니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "guids": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "description": "내보낼 Rhino 객체 GUID입니다. 관련 없는 문서 객체는 제외합니다."
    },
    "asset_name": {
      "type": "string",
      "description": "Chestnut에 표시할 사람이 읽을 수 있는 이름입니다."
    },
    "asset_id": {
      "default": "",
      "type": "string",
      "description": "연결된 갱신에 사용할 선택적이고 안정적인 ID입니다. 생략하면 Rhino 문서와 GUID에서 결정적으로 생성합니다."
    },
    "body_type": {
      "default": "static",
      "type": "string",
      "description": "건축물은 \"static\", 고정되지 않은 소품은 \"dynamic\", 스크립트로 구동하는 객체는 \"kinematic\"입니다."
    },
    "collider": {
      "default": "box",
      "type": "string",
      "description": "의도한 콜라이더: \"box\", \"convex\", \"compound\", \"trimesh\". 현재 Chestnut은 필요하면 box로 대체합니다."
    },
    "preserve_scale": {
      "default": true,
      "type": "boolean",
      "description": "true이면 Rhino의 실제 치수를 유지하고, false이면 1미터 크기로 정규화합니다."
    },
    "mass": {
      "default": 0.0,
      "type": "number",
      "description": "물리 질량(kg)입니다. static 바디는 항상 0을 사용합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "guids",
    "asset_name"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "success": true, // 원격 /api/props/upsert 응답에서 온 값
  "chestnut_url": "https://chestnut-mnvo.onrender.com", // 게시한 Chestnut 서비스의 주소입니다.
  "next_step_guide": "Chestnut에서 게시 결과를 확인하고, 갱신할 때는 확인한 자산 ID를 재사용합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 69. exchange_05-publish_chestnut

기준 API: `exchange_05-publish_chestnut`

근거: src/mcp/features/publishing/tools.py

### DESCRIPTION

Rhino 객체를 동작 프리셋으로 Chestnut에 게시합니다. 원본 문서 경로·GUID 등의 metadata도 업로드됩니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "guids": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "description": "게시할 현재 Rhino 객체 GUID 배열입니다. 관찰·선택·모델링 결과의 ID를 사용합니다."
    },
    "asset_name": {
      "type": "string",
      "description": "사람이 읽을 수 있는 자산 이름입니다."
    },
    "behavior": {
      "default": "auto",
      "type": "string",
      "description": "선택적인 의미 기반 프리셋입니다. auto는 이름에서 추론하고, architecture는 고정형, object는 이동 가능하고 중력의 영향을 받는 유형, animated는 스크립트 구동형입니다. 의도한 물리 설정을 선택하며 애니메이션을 생성하지 않습니다."
    },
    "asset_id": {
      "default": "",
      "type": "string",
      "description": "Chestnut 자산의 고정 ID입니다. 같은 ID로 게시하면 기존 자산을 갱신합니다. 비우면 서버가 생성합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 connect_01-list_up tool의 connection_id를 입력합니다."
    }
  },
  "required": [
    "guids",
    "asset_name"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(일부 필드 발췌·Rhino 실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "success": true, // 하위 publish_objects_to_chestnut의 원격 응답을 그대로 반환
  "chestnut_url": "https://chestnut-mnvo.onrender.com", // 게시한 Chestnut 서비스의 주소입니다.
  "next_step_guide": "Chestnut에서 게시 결과를 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```
