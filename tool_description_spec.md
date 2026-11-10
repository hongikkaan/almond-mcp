## Prefix 명명

문서의 도구명은 유형별 prefix 뒤에 해당 유형 안의 두 자리 순번을 붙인다. 예: connect-01_list_up, connect-02_session. 순번은 각 유형에서 01부터 시작하며, 기존 전체 도구 번호 01–92도 함께 유지한다. 각 도구 아래의 기준 API는 실제 서버 호출명이다. 실제 API·schema·출력은 아래 구현 계약을 따릅니다.

수정: November 9, 2026 · 기존 묶음을 영어로 명명하고 prefix를 붙이라는 요청

| Group | Prefix | 기존 묶음 |
| --- | --- | --- |
| Connect | connect-NN_ | 연결·세션 관리 |
| Context | context-NN_ | 기본 가이드·프로젝트 정보·운영 정책 |
| Plan | plan-NN_ | 작업 계획·단계·산출물 관리 |
| Inspect | inspect-NN_ | Rhino 문서·객체·선택 조회 |
| Capture | capture-NN_ | 화면 캡처·시각 검토 |
| Model | model-NN_ | 모델링 설정·재료·형상 편집 |
| Script | script-NN_ | 스크립트 실행·결과 확인·저장 |
| Scene | scene-NN_ | Scene·Holon 의미 구조 관리 |
| Intersect | intersect-NN_ | 교차·겹침 검토와 해결 |
| Asset | asset-NN_ | 모델·도면 자산 검색·준비·배치 |
| Diagram | diagram-NN_ | 다이어그램 자산 검색·배치 |
| Drawing | drawing-NN_ | 도면 스타일·해치·평면 및 단면 생성 |
| Grasshopper | grasshopper-NN_ | Grasshopper 로직·캡슐 조회와 실행 |
| Research | research-NN_ | 구법·건축 유형·참고자료 조사 |
| Analysis | analysis-NN_ | 구조·피난 검토와 보고서 |
| Exchange | exchange-NN_ | 앱 간 자산 교환·Chestnut 게시 |

# 설명

## 문서 기준

- 공개 도구는 공통 **85개**와 외부 연결 관리 **4개**, 총 **89개**입니다.
- DESCRIPTION은 도구를 선택할 때 필요한 역할과 핵심 조건을 설명합니다.
- TOOL INPUT은 실제 공개 schema입니다. 변수명·타입·선택지·입력 설명을 확인합니다.
- TOOL OUTPUT은 코드 기반 예시이며 Rhino 실측 응답이 아닙니다. 이름·ID·수치·경로는 예시 값이고, // 뒤는 출력 필드의 의미를 설명하는 문서용 주석입니다.
- 실제 outputSchema에도 결과 필드의 타입과 설명을 제공합니다. JSON 문자열을 반환하는 도구는 result.contentSchema가 그 안의 JSON을 설명합니다. 이미지와 실행기 도구는 객체로 반환합니다.
- next_step_guide는 현재 결과에서 필요한 후속 작업이 있을 때 반환하는 문자열입니다. 빈 목록·오류·부분 적용·과거 기록·실행 대기에 따라 안내가 달라집니다.
- 요청한 상세 그룹이나 실행 상태에 따라 출력 필드는 달라집니다. 입력에 사용한 ID가 응답에서 생략되면 후속 호출에 재사용할 수 있도록 보관합니다.

# Connect

연결·세션 관리 · prefix: `connect-NN_` · 유형 내 순번 01–04

## 01. connect-01_list_up

기준 API: `list_connections`

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

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "instructions": "초기화는 도구를 공개하기만 하며 Rhino나 모델링 워커를 시작하지 않습니다. …", // 연결 가능한 Rhino와 연결 선택 방법입니다.
  "targets": [], // 연결 가능한 Rhino 문서 후보입니다.
  "connections": [], // 현재 유지 중인 연결입니다.
  "starts": [], // Rhino 시작 요청과 진행 상태입니다.
  "selected_connection_id": null, // 이후 호출에서 사용하는 연결 ID입니다. 선택된 연결이 없으면 null입니다.
  "next_step_guide": "연결할 Rhino의 저장된 문서에서 almondconnect를 실행한 뒤 목록을 다시 조회합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 02. connect-02_session

기준 API: `connect`

근거: src/cos/external_host.py

### DESCRIPTION

목록에서 고른 Rhino 문서에 연결하거나 기존 연결을 다시 선택합니다. 다른 문서의 연결도 유지됩니다.

### TOOL INPUT

```json
{
  "type": "object",
  "properties": {
    "host_id": {
      "type": "string",
      "description": "list_connections.targets에서 선택한 Rhino 프로세스의 host_id입니다."
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

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
  "artifact_dir": ".almond/produced/example", // 이 연결의 임시 작업 폴더입니다.
  "in_flight": false, // 해당 연결에 호출이 진행 중인지 여부
  "next_step_guide": "이후 호출은 선택한 연결을 사용합니다. 프로젝트 정보는 project_info, 기존 작업은 list_plans로 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 03. connect-03_start_session

기준 API: `start_session`

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
      "description": "이 시작 요청의 고유 ID입니다. 같은 시작 시도를 확인할 때 그대로 재사용합니다."
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

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
  "artifact_dir": ".almond/produced/example", // 이 연결의 임시 작업 폴더입니다.
  "in_flight": false, // 해당 연결에 호출이 진행 중인지 여부
  "request_id": "example-start", // 동일 시작 시도에 재사용. 대기·실패 상태는 list_connections.starts에서 확인
  "next_step_guide": "이후 호출은 선택한 연결을 사용합니다. 프로젝트 정보는 project_info, 기존 작업은 list_plans로 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 04. connect-04_disconnect

기준 API: `disconnect`

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
      "description": "생략하면 선택한 연결을 해제합니다. 다른 연결을 해제하려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [],
  "additionalProperties": false
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "connection_id": "example-connection", // 해제한 연결 ID입니다.
  "worker_closed": true, // worker가 종료됐는지 여부
  "rhino_closed": false, // Rhino가 닫혔는지 여부. disconnect는 false
  "released": true, // Rhino에서 연결 해제를 확인했는지 나타냅니다.
  "reason": "" // 해제 결과 또는 남아 있는 잠금의 사유입니다.
}
```

# Context

기본 가이드·프로젝트 정보·운영 정책 · prefix: `context-NN_` · 유형 내 순번 01–04


## 67. context-04_get_project_info

기준 API: `project_info`

근거: src/mcp/runtime/mcp_server.py

### DESCRIPTION

프로젝트 경로·등록 파일·현재 문서·작업 공간 정보를 조회합니다.

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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
    "database": ".almond/example.db"
  },
  "next_step_guide": "- list_plans으로 프로젝트 진행상황 파악합니다.\n- 산출물 작업 공간은 set_working_plan으로 선택합니다.\n- 객체 상태가 필요하면 get_objects로 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 36. context-01_get_policy

기준 API: `get_policy`

근거: src/mcp/features/guidance/tools.py

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
        "rhinocode"
      ],
      "type": "string",
      "description": "조회할 지침입니다. basic=설계·검증, metadata=객체·그룹 메타데이터, rhino_scripting=스크립트 작성 참고, rhinocode=코드·커맨드 실행. 생략하거나 빈 문자열이면 basic입니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "guide_version": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", // 지침 버전을 비교하는 해시입니다.
  "text": "---\nname: rhino-almond\ndescription: \"Rhino에서 Almond MCP로 기존 설계를 발전시키기 위한 건축적 판단.\"\n---\n\n# Rhino Almond\nAlmond MCP를 사용해 Rhino로 건축 설계를 발전시킨다. \n\n**작업 태도**\n 설계 내용의 충돌은, 현재 설계 의도와 작업 목적을 기준으로 …", // 선택한 policy의 지침 본문입니다.
  "source_refs": [ // 선택한 지침의 출처 파일과 해시입니다.
    {
      "path": "src/mcp/BASIC-INSTRUCTIONS.md",
      "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    }
  ],
  "tools": [ // 사용할 수 있는 도구 이름 목록입니다.
    "get_policy"
  ],
  "selected_policy": "basic", // 선택한 policy 이름입니다.
  "available_policies": { // 선택 가능한 policy 이름과 설명입니다.
    "basic": "설계·검증 기본 지침",
    "metadata": "metadata 입력 지침",
    "rhino_scripting": "Rhino 내부 스크립팅 지침",
    "rhinocode": "RhinoCode 실행 지침"
  }
}
```

# Plan

작업 계획·단계·산출물 관리 · prefix: `plan-NN_` · 유형 내 순번 01–13

## 14. plan-01_create_phase

기준 API: `create_phase`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

관련 Plan을 묶는 Phase를 생성합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "name": {
      "type": "string",
      "description": "Phase 이름을 문자열로 입력합니다. 빈 문자열은 사용할 수 없습니다."
    },
    "description": {
      "default": "",
      "type": "string",
      "description": "Phase의 목적이나 작업 범위를 문자열로 입력합니다."
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
      "enum": [
        "pending",
        "running",
        "paused",
        "completed",
        "failed",
        "blocked"
      ],
      "type": "string",
      "description": "pending, running, paused, completed, failed, blocked 중 하나를 선택합니다."
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
      "description": "이 Phase가 의존하는 Phase ID 목록입니다."
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
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "name"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "phase": { // 생성한 Phase입니다.
    "phase_id": "phase_example"
  },
  "next_step_guide": "이 phase_id로 create_plan을 호출해 Phase에 Plan을 추가할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 15. plan-02_create

기준 API: `create_plan`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

작업 목표와 템플릿에 따라 Plan과 Step을 생성합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "title": {
      "type": "string",
      "description": "Plan 목록에서 사용할 비어 있지 않은 짧은 제목입니다."
    },
    "goal": {
      "type": "string",
      "description": "비어 있지 않은 전체 목표와 의도한 결과입니다."
    },
    "scope": {
      "default": "house",
      "type": "string",
      "description": "작업 목적에 맞는 Step 템플릿을 선택합니다: spatial_development, semantic_exploration, plan_editing, model_revision, inspection, structure, construction_detail, drawing, component, house, interior. 등록한 사용자 템플릿도 사용할 수 있습니다."
    },
    "scene_id": {
      "default": "",
      "type": "string",
      "description": "기존 방식의 단일 Scene ID입니다. scene_ids를 우선 사용합니다. 둘 다 전달하면 scene_ids의 첫 번째 항목과 같아야 합니다."
    },
    "phase_id": {
      "default": "",
      "type": "string",
      "description": "선택 사항인 기존 Phase ID입니다. 비어 있으면 Plan을 Phase에 소속시키지 않습니다."
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
      "description": "맥락을 설명하는 선택 사항인 기존 Scene ID 배열로, 여러 Scene을 포함할 수 있습니다. 생략하면 Scene 없이 작업할 수 있습니다. 형상 대상 집합을 확장하지는 않습니다."
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
      "description": "이 Plan을 위해 명시적으로 지정하는 선택 사항인 등록된 Holon 대상입니다. Step에는 별도의 Holon 할당이 없습니다."
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
      "description": "이 Plan이 의존하는 Plan ID 목록입니다."
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
      "description": "선택 사항인 상위 Plan ID 배열입니다."
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
      "description": "선택 사항인 하위 Plan ID 배열입니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "title",
    "goal"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "plan": { // 생성한 Plan입니다.
    "plan_id": "plan_example",
    "loop_no": 0,
    "revision": 1
  },
  "next_step_guide": "get_phase_plan_step에서 plan_id와 include_details=true로 Step을 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 18. plan-03_execute_looping

기준 API: `execute_looping`

근거: src/mcp/runtime/mcp_server.py

### DESCRIPTION

Plan의 새 회차를 시작하거나 최신 회차를 재개하고 산출물 작업 공간을 준비합니다. Step 작업은 에이전트가 수행합니다. 저장된 수행·검증·보고 기록을 확인해 완료한 작업을 반복하지 않고, 회차가 끝나면 목표·변경 내용·시각적 근거·검증 결과·남은 선택지를 보고합니다. Plan 완료는 사용자가 결정합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "plan_id": {
      "type": "string",
      "description": "다음 Loop를 시작하거나 최신 Loop를 재개할 기존 Plan ID입니다. create_plan 또는 list_plans에서 얻은 ID를 사용합니다."
    },
    "resume": {
      "default": false,
      "type": "boolean",
      "description": "false는 새 회차 시작, true는 최신 회차 재개입니다. 새 회차는 이전 회차를 보고한 뒤 시작합니다. 시작 결과가 불확실하면 get_phase_plan_step으로 현재 회차를 확인한 뒤 결정합니다."
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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "plan_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "plan_id": "plan_example", // Plan ID
  "loop_no": 1, // Loop 회차 번호
  "next_step_id": "step_example", // 아직 완료되지 않은 첫 Step의 ID입니다. 없으면 null입니다.
  "previous_loop": null, // 이전 회차의 번호와 Step 기록입니다.
  "step_id": "", // 선택한 Step ID입니다.
  "plan_artifact_dir": ".almond/produced/example", // Plan 산출물 폴더
  "artifact_dir": ".almond/produced/example/01", // 작업 산출물 폴더
  "revision": 1, // 현재 Plan·Loop의 저장 리비전입니다.
  "title": "예시 계획", // 저장된 제목
  "goal": "예시 목표", // 저장된 목표
  "plan_status": "pending", // Plan의 업무 상태입니다. 회차 시작만으로 변경되지는 않습니다.
  "feedback": "", // 저장된 피드백
  "steps": [ // 이 회차의 Step과 작업 기록입니다.
    {
      "step_id": "step_example",
      "name": "예시 단계",
      "status": "pending"
    }
  ],
  "policy_reminder": "…", // 이번 작업과 결과 보고에 적용할 지침입니다.
  "next_step_guide": "수행할 Step을 set_working_plan으로 선택하고, 수행·검증 결과를 update_step에 기록합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 41. plan-05_get_phase_plan_step

기준 API: `get_phase_plan_step`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

Phase, Plan 또는 Step 중 하나를 조회합니다. 상세 내용의 포함 여부를 선택할 수 있습니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "phase_id": {
      "default": "",
      "type": "string",
      "description": "조회할 Phase ID입니다. plan_id와 함께 입력하지 않습니다."
    },
    "plan_id": {
      "default": "",
      "type": "string",
      "description": "조회할 Plan ID입니다. Step 조회에도 함께 입력합니다."
    },
    "step_id": {
      "default": "",
      "type": "string",
      "description": "조회할 Step ID입니다. 해당 plan_id와 함께 입력합니다."
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
      "type": "boolean",
      "description": "true이면 선택한 유형의 상세 내용을 추가합니다."
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
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). Phase를 include_details=true로 조회한 예시입니다. false이면 공통 식별·상태 정보만 반환합니다. Plan·Step은 상세 선택과 무관하게 plan_id·loop_no·revision·read_only를 포함합니다.

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
  "next_step_guide": "이 id를 list_plans의 phase_id에 입력해 소속 Plan을 조회합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 60. plan-06_list_phases

기준 API: `list_phases`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

프로젝트의 Phase 목록을 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "limit": {
      "default": 50,
      "type": "integer",
      "description": "최대 Phase 수입니다. 범위는 1..500이며, 이 목록에는 offset 인수가 없습니다."
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
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "phases": [], // Phase 목록입니다.
  "total": 0, // 필터에 일치하는 전체 항목 수
  "limit": 50, // 페이지 최대 항목 수
  "truncated": false // limit 때문에 목록 일부만 반환했는지 나타냅니다.
}
```

## 61. plan-07_list_revisions

기준 API: `list_plan_revisions`

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
      "description": "list_plans.plans[].plan_id 또는 get_phase_plan_step.id에서 얻은 기존 Plan ID입니다."
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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "plan_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "plan_id": "plan_example", // 각 행의 loop_no/revision과 함께 get_phase_plan_step에 사용
  "revisions": [], // 저장 리비전 목록입니다.
  "total": 0, // 필터에 일치하는 전체 항목 수
  "limit": 50, // 페이지 최대 항목 수
  "truncated": false // limit 때문에 최신 리비전 일부만 반환했는지 나타냅니다.
}
```

## 62. plan-08_list

기준 API: `list_plans`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

프로젝트의 Plan 목록을 조회합니다. Phase·Scene·상태로 범위를 좁힐 수 있습니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "phase_id": {
      "default": "",
      "type": "string",
      "description": "선택 사항인 Phase ID 필터입니다. 비어 있으면 여러 Phase를 범위로 합니다."
    },
    "scene_id": {
      "default": "",
      "type": "string",
      "description": "선택 사항인 Scene ID 필터입니다. 비어 있으면 어떤 Scene에 속하든, Scene이 없든 모든 Plan을 포함합니다."
    },
    "status": {
      "default": "",
      "enum": [
        "",
        "pending",
        "running",
        "paused",
        "completed",
        "failed",
        "blocked"
      ],
      "type": "string",
      "description": "pending, running, paused, completed, failed, blocked 중 하나를 선택합니다. 빈 문자열이면 모든 상태를 포함합니다."
    },
    "limit": {
      "default": 50,
      "type": "integer",
      "description": "최대 Plan 수입니다. 범위는 1..500이며, 이 목록에는 offset 인수가 없습니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "plans": [], // Plan 목록입니다.
  "total": 0, // 필터에 일치하는 전체 항목 수
  "limit": 50, // 페이지 최대 항목 수
  "truncated": false // limit 때문에 목록 일부만 반환했는지 나타냅니다.
}
```

## 74. plan-09_rename_artifact_folder

기준 API: `rename_artifact_folder`

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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "name"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "artifact_dir": ".almond/produced/example-new", // 변경 후 산출물 폴더 경로입니다.
  "previous_artifact_dir": ".almond/produced/example-old", // 변경 전 폴더 경로입니다. 실제 변경이 있을 때 반환합니다.
  "next_step_guide": "이후 산출물 작업에는 갱신된 artifact_dir를 사용합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 83. plan-10_set_working

기준 API: `set_working_plan`

근거: src/mcp/runtime/mcp_server.py

### DESCRIPTION

기존 Plan 또는 Step을 이 연결의 산출물 작업 공간으로 선택합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "plan_id": {
      "type": "string",
      "description": "list_plans.plans[].plan_id 또는 get_phase_plan_step.id에서 얻은 기존 Plan ID입니다."
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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "plan_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "plan_id": "plan_example", // Plan ID
  "step_id": "step_example", // 선택한 Step. Step 미선택이면 빈 문자열
  "loop_no": 1, // Loop 회차 번호
  "revision": 2, // 작업 공간 설정 후의 저장 리비전입니다.
  "artifact_dir": ".almond/produced/example/01", // 현재 연결의 산출물 폴더입니다. execute_project_python의 작업 디렉터리로 사용합니다.
  "plan_artifact_dir": ".almond/produced/example", // Plan 산출물 루트입니다. Loop 시작 전에는 이 폴더를 사용합니다.
  "next_step_guide": "이 artifact_dir에서 작업하고, 재사용한 파일은 input_refs에, 새로 만든 산출물은 output_refs에 기록합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 87. plan-11_update_phase

기준 API: `update_phase`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

Phase의 이름·설명·상태·파일 연결·관계를 수정합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "phase_id": {
      "type": "string",
      "description": "list_phases.phases[].phase_id 또는 get_phase_plan_step.id에서 얻은 기존 Phase ID입니다."
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
      "description": "Phase ID만 사용하는 선택 사항인 {add: string[], remove: string[]} 패치입니다. 충돌하거나 유효하지 않은 문자열 항목은 보고하고 건너뜁니다. 잘못된 타입은 요청 전체를 거부합니다."
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
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "phase_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "changed": true, // 실제 저장 변경 여부. status=success여도 false일 수 있음
  "phase": { // 수정한 Phase의 확인 정보입니다.
    "phase_id": "phase_example",
    "status": "pending"
  },
  "issues": [], // 적용하지 못한 패치 항목입니다. 나머지 항목은 적용되었을 수 있습니다.
  "next_step_guide": "get_phase_plan_step으로 변경된 Phase를 확인할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 88. plan-12_update

기준 API: `update_plan`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

Plan의 목표·상태·대상·관계·산출물 참조를 수정합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "plan_id": {
      "type": "string",
      "description": "list_plans.plans[].plan_id 또는 get_phase_plan_step.id에서 얻은 기존 Plan ID입니다."
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
      "description": "선택 사항인 대체 Scene ID 배열입니다. []이면 비우고 생략/null이면 유지합니다. Scene은 맥락을 설명하며 자동 편집 대상이 아닙니다."
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
      "description": "Plan ID만 사용하는 선택 사항인 {add: string[], remove: string[]} 패치입니다. 문자열 항목에 문제가 있으면 건너뛰고 보고합니다."
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
      "description": "선택 사항인 대체 상위 Plan ID 배열입니다. 생략/null이면 유지하고 []이면 비웁니다."
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
      "description": "선택 사항인 대체 하위 Plan ID 배열입니다. 생략/null이면 유지하고 []이면 비웁니다."
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
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "plan_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
  "next_step_guide": "get_phase_plan_step으로 변경된 Plan을 확인할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 89. plan-13_update_step

기준 API: `update_step`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

Step의 상태와 입력·출력 근거를 기록합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "plan_id": {
      "type": "string",
      "description": "list_plans.plans[].plan_id 또는 get_phase_plan_step.id에서 얻은 기존 Plan ID입니다."
    },
    "step_id": {
      "type": "string",
      "description": "선택한 Plan의 상세 결과에서 얻은 Step ID입니다. 해당 Plan ID와 함께 사용합니다."
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
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "plan_id",
    "step_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
  "next_step_guide": "다음에 수행할 Step을 정했다면 set_working_plan으로 선택합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

# Inspect

Rhino 문서·객체·선택 조회 · prefix: `inspect-NN_` · 유형 내 순번 01–05

## 06. inspect-01_analyze_nested_blocks

기준 API: `analyze_block_reculviely`

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
      "description": "outline은 객체와 중첩 정의를 순회합니다. resolve-block은 명시적인 배치 인스턴스 경로를 해석하고 공유 정의에 미치는 영향을 보고합니다. 경로 해석에는 선택 가능 조건이 필요하지 않으며 편집기 소유 관계를 부여하지도 않습니다. 중첩 정의 구성원은 독립적인 편집 ID가 아닙니다."
    },
    "options": {
      "additionalProperties": true,
      "type": "object",
      "description": "outline: ids(루트 GUID 배열) 또는 path(배치 GUID 경로)를 선택합니다. 둘 다 없으면 scope=selected|viewport|document로 범위를 정합니다. depth=0..64, max_items=1..5000, max_bytes=2048..262144이며 기본값은 각각 64, 200, 48000입니다. field_groups는 summary, objects, annotations, transforms 중 선택한 비어 있지 않은 배열입니다. include_geometry/annotations는 상세 포함 여부, annotation_layer는 텍스트 도트의 레이어 필터입니다. resolve-block: 최상위에서 내부 방향의 배치 GUID 1..65개를 path에 입력합니다."
    },
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "일반적으로 생략합니다. 런타임이 연결된 문서 경로를 제공합니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
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

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
  "next_step_guide": "블록 편집에 들어간 뒤에는 get_objects로 현재 편집 대상 ID를 다시 조회합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 39. inspect-02_get_objects

기준 API: `get_objects`

근거: src/mcp/features/context/tools.py

### DESCRIPTION

Rhino 객체의 속성·그룹·블록 계층·Brep 면을 관찰합니다.

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
      "description": "일반적으로 생략합니다. 런타임이 연결된 저장 문서를 제공합니다."
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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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

## 44. inspect-03_get_document_context

기준 API: `get_rhino_context`

근거: src/mcp/features/context/tools.py

### DESCRIPTION

현재 Rhino 문서와 편집 상태, 뷰·디스플레이 모드를 조회합니다.

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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
  "next_step_guide": "현재 화면을 보려면 get_current_viewcapture를 사용하세요." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 47. inspect-04_get_selection_references

기준 API: `get_selection_references`

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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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

## 76. inspect-05_resolve_targets

기준 API: `resolve_targets`

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
      "description": "list_plans.plans[].plan_id 또는 get_phase_plan_step.id에서 얻은 기존 Plan ID입니다."
    },
    "step_id": {
      "default": "",
      "type": "string",
      "description": "컨텍스트를 검증하는 선택 사항인 Step ID입니다. Plan 대상을 재정의하지 않습니다."
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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "plan_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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

화면 캡처·시각 검토 · prefix: `capture-NN_` · 유형 내 순번 01–04

## 10. capture-01_conditioning_pass

기준 API: `capture_conditioning_pass`

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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "shot"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
  "out_dir": ".almond/produced/example/capture", // 패스별 PNG와 doc.json/camera.json/zrange.csv/summary.json을 쓰는 폴더
  "camera_json": ".almond/produced/example/capture/camera.json", // 전체 계획 경로 기록. frames[].camera/target/lens_mm를 포함하며 부분 캡처에도 계획은 전체 길이
  "videos": { // 완전 캡처 후 패스별 MP4. ffmpeg 조립 실패는 null이며 부분 캡처에는 빈 객체일 수 있음
    "rgb": null
  },
  "document": {}, // 원본 문서·단위·뷰·경계 정보입니다.
  "next_step_guide": "프레임과 camera_json을 확인하고, 사용할 산출물 경로를 update_step의 output_refs에 기록합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 11. capture-02_inspection

기준 API: `capture_rhino_inspection`

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
      "description": "일반적으로 생략합니다. 런타임이 연결된 저장 문서를 제공합니다."
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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "views"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
    "path": ".almond/produced/example/captures/example.png",
    "lifetime": "plan",
    "bytes": 12345,
    "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  },
  "next_step_guide": "보관할 이미지라면 image_file.path를 update_step의 output_refs에 기록합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 28. capture-03_current_view

기준 API: `get_current_viewcapture`

근거: src/mcp/features/context/tools.py

### DESCRIPTION

현재 모델 화면을 캡처합니다. 대상·격리·디스플레이 옵션을 지정하면 실제 화면에도 적용됩니다.

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
      "description": "객체, 그룹 또는 Holon ID로 구성된 선택 사항인 비어 있지 않은 문자열 배열입니다. 확인된 객체가 중복되면 한 번만 선택합니다."
    },
    "target_kind": {
      "default": "object",
      "type": "string",
      "description": "object(기본값), group, block(일반 객체 ID) 또는 holon입니다. 허용할 형상 유형이 아니라 ID 이름 공간을 선택합니다."
    },
    "isolate": {
      "default": false,
      "type": "boolean",
      "description": "기본값은 false입니다. true이면 Zoom Selected 전에 실제 Rhino Isolate를 실행합니다. 가시성을 복원하려면 Unisolate를 사용합니다."
    },
    "scale_percent": {
      "default": 75,
      "type": "integer",
      "description": "범위는 1..100이며 기본값은 75입니다. 뷰포트 창 크기가 아니라 이미지 해상도를 변경합니다."
    },
    "include_usage": {
      "default": false,
      "type": "boolean",
      "description": "치수와 설명용 픽셀 기반 토큰 추정치를 포함합니다. 측정된 사용량은 아닙니다."
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
      "description": "선택 사항인 이미지의 픽셀 너비로, 범위는 128..2048입니다. height도 제공하고 scale_percent=100으로 설정합니다. Rhino 창 크기를 바꾸지는 않습니다."
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
      "description": "선택 사항인 이미지의 픽셀 높이로, 범위는 128..2048입니다. width도 제공하고 scale_percent=100으로 설정합니다. Rhino 창 크기를 바꾸지는 않습니다."
    },
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "일반적으로 생략합니다. 런타임이 연결된 모델을 제공합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "image_file": { // PNG 저장 결과입니다. 이미지 전달 여부와 별도로 확인합니다.
    "status": "saved",
    "path": ".almond/produced/example/captures/example.png",
    "lifetime": "plan",
    "bytes": 12345,
    "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  },
  "next_step_guide": "보관할 이미지라면 image_file.path를 update_step의 output_refs에 기록합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 29. capture-04_defined_view

기준 API: `get_defined_viewcapture`

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
      "description": "실제 치수와 설명용 픽셀 기반 토큰 추정치를 포함합니다. 측정된 사용량은 아닙니다."
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
      "description": "일반적으로 생략합니다. 런타임이 연결된 모델을 제공합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
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

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "image_file": { // PNG 저장 결과입니다. 실제 치수와 축소 경고는 캡처 메타데이터에서 확인합니다.
    "status": "saved",
    "path": ".almond/produced/example/captures/example.png",
    "lifetime": "plan",
    "bytes": 12345,
    "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  },
  "next_step_guide": "보관할 이미지라면 image_file.path를 update_step의 output_refs에 기록합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

# Model

모델링 설정·재료·형상 편집 · prefix: `model-NN_` · 유형 내 순번 01–05

## 08. model-01_assign_material

기준 API: `assign_material`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

Rhino 객체에 라이브러리 PBR 재료를 적용합니다. 요청한 경우 구법 metadata도 기록합니다.

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
      "description": "list_materials(include_ids=true)에서 얻은 라이브러리의 표준 재료 ID입니다."
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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
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

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
  "next_step_guide": "get_objects로 적용된 재료를 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 16. model-02_edit_planar_face

기준 API: `edit_planar_face`

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
      "description": "일반적으로 생략합니다. 런타임이 연결된 저장 문서를 제공합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
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

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "result": { // 단일 면의 편집 결과입니다.
    "edited": true,
    "object_id": "00000000-0000-0000-0000-000000000001",
    "previous_geometry_crc": 123,
    "geometry_crc": 456
  },
  "next_step_guide": "get_objects로 변경된 형상과 CRC를 다시 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 17. model-03_edit_planar_faces

기준 API: `edit_planar_faces`

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
      "description": "일반적으로 생략합니다. 런타임이 연결된 저장 문서를 제공합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "edits"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
  "next_step_guide": "get_objects로 변경된 객체의 형상과 CRC를 다시 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 58. model-04_list_materials

기준 API: `list_materials`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

라이브러리 PBR 재료와 매핑 정보를 조회합니다.

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
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "선택 사항인 상세 그룹: display, physical, metadata, source, paths, audit 또는 all. 생략하거나 비워 두면 요약을 유지하며, include_ids는 식별 정보 포함 여부를 별도로 제어합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "total": 1, // 조건에 일치하는 라이브러리 재료 수입니다.
  "materials": [ // 재료의 이름·분류와 요청한 속성입니다.
    {
      "name": "예시 재료",
      "category": "wood"
    }
  ],
  "next_step_guide": "선택한 material_id를 assign_material에 입력합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 84. model-05_setup

기준 API: `setup_modeling`

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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "overwrite"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "applied": true, // 모든 지정 속성이 일치하는지 여부. false여도 누락 항목 생성·일부 변경이 있었을 수 있음
  "next_step_guide": "객체에 재료를 적용하려면 list_materials에서 선택한 재료를 assign_material에 사용합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

# Script

스크립트 실행·결과 확인·저장 · prefix: `script-NN_` · 유형 내 순번 01–04

## 19. script-01_run_project_python

기준 API: `execute_project_python`

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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "code"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "completed": true, // Rhino 실행 완료가 확인됐는지 나타냅니다.
  "request_id": "00000000000000000000000000000001", // 미완료·불확실성·결과 페이지를 get_rhino_execution으로 회수할 정확한 ID
  "artifact_dir": ".almond/produced/example/01" // 실행에 사용한 Plan·Loop 산출물 폴더입니다.
}
```

## 20. script-02_run_rhino

기준 API: `execute_rhino_script`

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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "script"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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

## 45. script-03_get_execution

기준 API: `get_rhino_execution`

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
      "description": "생략하면 선택한 연결을 사용합니다. 다른 연결은 connection_id로 지정합니다. 클라이언트 재시작 후에는 정확한 request_id로 보관된 결과를 조회할 수 있습니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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

## 78. script-04_save_document

기준 API: `save_rhino_document`

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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "saved": true, // true는 확인된 저장, false는 확인된 실패, null은 미확정이며 requires_reconciliation=true
  "modified": false // 저장 확인 직후의 문서 수정 플래그입니다.
}
```

# Scene

Scene·Holon 의미 구조 관리 · prefix: `scene-NN_` · 유형 내 순번 01–13

## 05. scene-01_add_objects

기준 API: `add_scene_objects`

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
      "description": "list_design_scenes(include_ids=true)에서 얻은 기존 Scene ID입니다."
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
      "description": "일반적으로 생략합니다. 관리형 세션이 연결된 저장 문서를 제공합니다. 명시한 경로는 해당 문서와 일치해야 합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
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

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "failed_indices": [], // 입력 object_ids에서 처리하지 못한 항목의 인덱스입니다. 0부터 시작합니다.
  "already_present_indices": [], // 이미 포함되어 변경하지 않은 입력 위치. Holon을 통해 포함된 경우도 포함
  "next_step_guide": "get_scene_objects로 Scene의 현재 구성원을 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 13. scene-02_create

기준 API: `create_design_scene`

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
      "description": "Scene 단위 코드: mm, cm, m, in 또는 ft. Rhino 문서 단위를 바꾸지는 않습니다."
    },
    "file_name": {
      "default": "",
      "type": "string",
      "description": "폴더를 제외한 프로젝트 파일 이름입니다. 중복 파일 이름을 구분하려면 project_file_id를 사용합니다. 이는 저장된 연결 정보이며, 파일 작업이 아닙니다."
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
      "description": "project_info(sections=[\"project\"], include_ids=true)에서 얻은 기존 project.files[].project_file_id입니다. file_name과 함께 제공하면 서로 일치해야 합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "name"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "scene": { // 생성한 Scene의 확인 정보입니다.
    "scene_id": "scene_example",
    "revision": 0
  },
  "next_step_guide": "객체를 포함하려면 add_scene_objects에 이 scene_id를 사용합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 23. scene-03_focus_holons

기준 API: `focus_holons`

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
      "description": "일반적으로 생략합니다. 관리형 세션이 연결된 저장 Rhino 문서를 제공합니다. 명시한 경로는 이 연결 정보와 일치해야 하며, 문서를 전환하지는 않습니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "holon_ids"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "zoom_selected": true, // 선택 객체로 줌했는지 여부
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

## 30. scene-04_get

기준 API: `get_design_scene`

근거: src/mcp/features/scenes/tools.py

### DESCRIPTION

Scene의 저장된 정보와 등록 요약을 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "scene_id": {
      "type": "string",
      "description": "list_design_scenes(include_ids=true) 또는 기록된 Scene 참조에서 얻은 기존 Scene ID입니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "선택 사항인 상세 그룹: scope, state, geometry, audit 또는 all. 생략하거나 비워 두면 요약을 유지하며, include_ids는 식별 정보 포함 여부를 별도로 제어합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "scene_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
  "next_step_guide": "현재 Rhino 구성원은 get_scene_objects로 조회합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 40. scene-05_get_holon

기준 API: `get_ontological_holon`

근거: src/mcp/features/components/tools.py

### DESCRIPTION

Holon의 등록 정보 또는 현재 Rhino 그룹 구성원을 조회합니다.

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
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "선택 사항인 상세 그룹: references, geometry, scope, audit 또는 all. 생략하거나 비워 두면 요약을 유지하며, include_ids는 식별 정보 포함 여부를 별도로 제어합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "holon_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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

## 46. scene-06_get_objects

기준 API: `get_scene_objects`

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
      "description": "list_design_scenes(include_ids=true) 또는 기록된 Scene 참조에서 얻은 기존 Scene ID입니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "선택 사항인 상세 그룹: scope, state, geometry, audit 또는 all. 생략하거나 비워 두면 요약을 유지하며, include_ids는 식별 정보 포함 여부를 별도로 제어합니다."
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
      "description": "일반적으로 생략합니다. 관리형 세션이 연결된 저장 Rhino 문서를 제공합니다. 명시한 경로는 이 연결 정보와 일치해야 하며, 문서를 전환하지는 않습니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "scene_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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

## 53. scene-07_list

기준 API: `list_design_scenes`

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
      "description": "선택 사항인 저장된 프로젝트 파일 이름 필터입니다. 현재 형상을 검증하지는 않습니다."
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
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "선택 사항인 상세 그룹: scope, state, geometry, audit 또는 all. 생략하거나 비워 두면 요약을 유지하며, include_ids는 식별 정보 포함 여부를 별도로 제어합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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

## 59. scene-08_list_holons

기준 API: `list_ontological_holons`

근거: src/mcp/features/components/tools.py

### DESCRIPTION

문서 또는 Scene에 등록된 Holon 목록을 조회합니다.

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
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "선택 가능한 세부 그룹은 references, geometry, scope, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별 정보는 include_ids로 별도 제어합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "holons": [], // 등록된 Holon의 저장 요약입니다.
  "total": 0, // 필터에 일치하는 전체 항목 수
  "live_verified": false // Holon을 현재 Rhino에서 확인했는지 나타냅니다.
}
```

## 72. scene-09_remove_holon

기준 API: `remove_ontological_holon`

근거: src/mcp/features/components/tools.py

### DESCRIPTION

Rhino 형상과 그룹을 유지하면서 Holon 등록을 해제합니다. 부모 Holon과 Plan의 참조를 먼저 해제해야 합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "holon_id": {
      "type": "string",
      "description": "include_ids=true를 지정한 Holon 조회 또는 이전 등록 결과에서 얻은 등록된 Holon ID입니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "holon_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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

## 73. scene-10_remove_objects

기준 API: `remove_scene_objects`

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
      "description": "list_design_scenes(include_ids=true)에서 얻은 기존 Scene ID입니다."
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
      "description": "보통 생략합니다. 관리형 세션이 연결된 저장 문서를 제공합니다. 경로를 명시하면 해당 문서와 일치해야 합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
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

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "failed_indices": [], // 입력 object_ids에서 처리하지 못한 항목의 인덱스입니다. 0부터 시작합니다.
  "already_absent_indices": [], // Scene에 이미 포함되지 않은 입력 항목의 인덱스입니다. 0부터 시작합니다.
  "next_step_guide": "get_scene_objects로 Scene의 현재 구성원을 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 85. scene-11_sync_holon

기준 API: `sync_ontological_holon`

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
      "description": "보통 생략합니다. 관리형 세션이 연결된 저장 Rhino 문서를 제공합니다. 경로를 명시하면 해당 연결과 일치해야 하며, 문서를 전환하지는 않습니다."
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
      "description": "일괄 상태 대조 및 정합성 확인에 사용할 Scene 범위입니다. 선택 사항이며, 새 Holon을 생성하거나 추론하지 않습니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "checked": 1, // 확인한 Holon 수
  "changed": 0, // 실제 대장 갱신 수. 변경 없으면 새 리비전도 없음
  "unavailable": 0, // 상태가 present가 아닌 등록 수
  "problems": [], // 항목별 문제. 관련 없는 유효 등록은 함께 갱신될 수 있음
  "scene_revisions": {}, // 갱신한 Scene ID와 저장 리비전의 대응입니다.
  "live_verified": true, // 문제 없이 모든 대상의 현재 상태를 확인했는지 나타냅니다.
  "next_step_guide": "갱신된 구성원은 get_ontological_holon으로 확인할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 86. scene-12_update

기준 API: `update_design_scene`

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
      "description": "list_design_scenes(include_ids=true) 또는 기록된 Scene 참조에서 얻은 기존 Scene ID입니다."
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
      "description": "기존 프로젝트 파일 ID입니다. 선택 사항이며, file_name과 함께 제공하면 서로 일치해야 합니다. 디스크의 파일이 아니라 메타데이터를 변경합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "scene_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "scene": { // 수정한 Scene의 확인 정보입니다.
    "scene_id": "scene_example",
    "revision": 1
  },
  "next_step_guide": "get_design_scene으로 변경된 Scene을 확인할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 90. scene-13_upsert_holon

기준 API: `upsert_ontological_holon`

근거: src/mcp/features/components/tools.py

### DESCRIPTION

물리적 요소와 관계를 역할·동작·구조 정보가 있는 Holon으로 등록하거나 갱신합니다. 직접 객체는 Holon 하나에 속합니다.

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
      "description": "등록할 현재 최상위 Rhino 객체 GUID입니다. 생략하면 이름이 지정된 기존 그룹을 찾아 사용할 수 있습니다. []는 child_holon_ids가 있는 부모에만 유효합니다."
    },
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "보통 생략합니다. 관리형 세션이 연결된 저장 Rhino 문서를 제공합니다. 경로를 명시하면 해당 연결과 일치해야 하며, 문서를 전환하지는 않습니다."
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
      "description": "기존 Scene 소속 관계입니다. 새 Holon에는 필수입니다. 생략하면 기존 등록을 유지하며, Scene을 생성하지는 않습니다."
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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "name"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "holon": { // 등록한 Holon의 확인 정보입니다.
    "holon_id": "example-holon",
    "availability": "present",
    "object_count": 1,
    "live_verified": true
  },
  "next_step_guide": "get_ontological_holon으로 등록 결과와 현재 구성원을 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

# Intersect

교차·겹침 검토와 해결 · prefix: `intersect-NN_` · 유형 내 순번 01–02

## 38. intersect-01_find

기준 API: `get_object_intersections`

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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "object_ids"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "intersections": { // 겹침 집계
    "number": 0
  },
  "next_step_guide": "이 범위에서 양의 부피 겹침이 발견되지 않았으므로 해결 도구를 호출할 필요가 없습니다. 이 결과가 다른 설계 조건이나 이격 거리 조건을 충족함을 입증하지는 않습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 75. intersect-02_resolve

기준 API: `resolve_object_intersection`

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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "state": "completed", // 검토 진행 상태입니다. awaiting_choice이면 비교 결과를 확인한 뒤 선택합니다.
  "skipped_pairs": 0, // 건너뛴 쌍은 수정하지 않음. completed가 모든 겹침 제거를 뜻하지 않음
  "message": "검토할 겹침이 더 없습니다. skip한 쌍은 수정하지 않았습니다." // 현재 결과 또는 오류의 설명입니다.
}
```

# Asset

모델·도면 자산 검색·준비·배치 · prefix: `asset-NN_` · 유형 내 순번 01–11

## 09. asset-01_audit_drawing

기준 API: `audit_asset_drawing`

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
      "description": "이전 생성/조회 결과의 도면 패키지 디렉터리입니다. 관리형 Almond 세션에서는 프로젝트 상대 경로를 사용하며, 독립 실행 라이브러리 호출에서는 절대 경로가 필요합니다."
    },
    "source_glb": {
      "default": "",
      "type": "string",
      "description": "원본 변경으로 오래된 상태가 되었는지 확인할 현재 원본 GLB입니다. 선택 사항이며, 동일한 관리형/독립 실행 경로 규칙을 사용합니다. 라이브러리에서 원본을 확인할 수 있으면 생략합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "package_dir"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "source_geometry": "source_file_current", // current/source_file_current/stale/not_checked. not_checked는 success여도 원본 비교 미실시
  "asset_id": "example-asset", // 패키지 원본 ID. custom-*는 등록 자산 ID가 아님
  "checked_files": 6, // 해시를 검사한 파일 수. 시각적 검토가 아님
  "failures": [] // 실패 항목이 하나라도 있으면 status=error
}
```

## 24. asset-02_generate_drawing_views

기준 API: `generate_asset_drawing_views`

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
      "description": "source_id/title/url/publisher/locator/accessed_on/relationship/used_for/terms_url을 포함하는 참조 객체입니다. 선택 사항이며, 출처 이력이 정확성을 보증하지는 않습니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "package_dir": ".almond/produced/example/drawing", // 생성한 도면 패키지 폴더입니다.
  "manifest": {} // 생성한 도면과 원본·축척·단위 기록입니다.
}
```

## 25. asset-03_get_drawings

기준 API: `get_asset_drawing`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

등록 모델의 저장 도면 매니페스트와 뷰를 조회합니다.

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
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별 정보는 include_ids로 별도 제어합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "plan_svg_uri": "almond://drawing/example-asset/drawing/plan/50", // 저장된 평면 SVG를 읽는 리소스 URI입니다.
  "manifest": {} // 도면 패키지의 원본·파일·축척 기록입니다.
}
```

## 32. asset-04_get

기준 API: `get_drawing_asset`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

모델·2D 자산의 파일·출처·변환·갱신 상태를 조회합니다.

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
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별 정보는 include_ids로 별도 제어합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "asset": { // 선택한 도면 자산과 준비 상태입니다.
    "name": "예시 자산",
    "file_available": true,
    "model_status": "ready",
    "drawing_ready": true
  },
  "next_step_guide": "선택한 자산의 ID로 place_drawing_asset을 호출할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 55. asset-05_list

기준 API: `list_drawing_assets`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

모델·2D 자산 목록을 조회합니다. 변환 대기 원본도 포함합니다.

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
      "description": "이 응답에서 반환할 최대 행 수입니다. 페이지를 전체 결과로 간주하기 전에 total과 페이지 처리 필드를 확인합니다."
    },
    "offset": {
      "default": 0,
      "type": "integer",
      "description": "이 페이지의 시작 행을 0부터 세는 값입니다. 다음 페이지를 요청할 때도 같은 필터를 사용합니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별 정보는 include_ids로 별도 제어합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "library_id": "model_assets", // include_ids=true에서 유지되는 라이브러리 구분자
  "assets": [], // 도면 자산 목록입니다. 추가 준비가 필요한 항목에는 next_tool과 next_step_guide가 있습니다.
  "total": 0, // 필터에 일치하는 전체 항목 수
  "limit": 20, // 페이지 최대 항목 수
  "offset": 0, // 현재 페이지 시작 위치
  "truncated": false, // true이면 같은 필터로 offset+현재 항목 수부터 계속. next_offset 필드는 없음
  "purpose": "3DM 모델 및 2D 표현. 기존 원본은 명시적인 변환이 필요합니다." // 이 라이브러리의 용도입니다.
}
```

## 64. asset-06_place

기준 API: `place_drawing_asset`

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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "asset_id": "example-asset", // 자산 ID
  "object_guid": "00000000-0000-0000-0000-000000000001", // 삽입한 최상위 블록 GUID. get_objects 또는 Scene 구성원 입력에 재사용
  "definition_created": true, // 새 정의 생성 여부. 공유 정의 갱신 시 definition_refreshed/affected_existing_instances가 추가될 수 있음
  "next_step_guide": "get_objects와 캡처로 배치 위치·축척을 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 66. asset-07_prepare

기준 API: `prepare_drawing_asset`

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
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "stage"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "state": "ready", // ready일 때만 source_3dm 제공. running/unconfirmed/failed는 error와 next_stage=null
  "ready_for_registration": true, // 현재 파일 해시에 대한 이미지 검토를 호출자가 확인했는지 나타냅니다.
  "job_dir": ".almond/produced/example/job", // 이후 단계 및 등록의 preparation_job에 재사용. status는 저장 근거만 읽고 늦은 실행을 자동 정합화하지 않음
  "source_3dm": ".almond/produced/example/job/final.3dm", // 검토 완료 최종 파일. register_drawing_asset에 검토한 name/asset_id와 함께 전달
  "next_stage": "register_drawing_asset", // 현재 상태의 다음 단계. 오류에서 자동 진행을 유도하지 않음
  "review_evidence": "파일 해시에 연결된 호출자의 검토 확인이며, 자동 시각 검증은 수행하지 않습니다.", // 저장된 검토 증거에 대한 설명입니다.
  "next_step_guide": "게시하려는 경우 이 응답의 source_3dm, preparation_job=job_dir, 검토한 asset_id/name을 지정하여 register_drawing_asset을 호출합니다. category는 선택 사항입니다. …" // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 70. asset-08_refresh

기준 API: `refresh_asset`

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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "registration_applied": true, // true면 인덱스 갱신 실패여도 게시 적용. 무작정 반복하지 않음
  "source_path_preserved": true, // 기존 원본 경로를 보존했는지 여부
  "rhino_linked_instances_updated": false, // false: 기존 Rhino 연결 인스턴스 재로드는 별도
  "live_index_refreshed": true, // false인데 게시가 적용됐다면 재연결하여 인덱스 갱신
  "asset": {}, // 갱신한 자산의 정보입니다.
  "model_path": ".almond/produced/example/asset.3dm", // 갱신한 라이브러리 3DM 경로입니다.
  "package_dir": ".almond/produced/example/drawing", // 갱신한 도면 패키지 폴더입니다.
  "previous_files_retained": true, // 이전 도면·매니페스트 백업·원본 리비전 사본 보존
  "next_step_guide": "갱신된 도면은 get_asset_drawing으로 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 71. asset-09_register

기준 API: `register_drawing_asset`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

준비한 3DM을 측정 치수와 평면·정면·우측면 도면이 있는 라이브러리 자산으로 등록합니다.

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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
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

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "registration_applied": true, // true면 게시 적용. 불명확한 오류는 null과 requires_reconciliation; 단순 재시도 금지
  "live_index_refreshed": true, // 게시 true·인덱스 false이면 등록을 반복하지 말고 재연결
  "source_path_preserved": false, // 기존 원본 경로를 보존했는지 여부
  "linked_instances_may_update": false, // 교체로 기존 연결 인스턴스에 영향 가능
  "asset": {}, // 등록한 자산의 정보입니다.
  "library_dir": ".almond/produced/example", // 라이브러리 폴더
  "model_path": ".almond/produced/example/asset.3dm", // 저장된 모델의 경로
  "package_dir": ".almond/produced/example/drawing", // 생성한 도면 패키지 폴더입니다. DXF와 치수는 mm 단위입니다.
  "manifest_path": ".almond/produced/example/manifest.json", // 라이브러리 manifest.json 경로입니다.
  "previous_files_retained": false, // 교체 전 원본·도면·매니페스트 백업 보존
  "previous_source_sha256": null, // 기존 원본 해시. 없으면 null
  "next_step_guide": "등록한 자산은 get_drawing_asset으로 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 79. asset-10_search_repository

기준 API: `search_asset_repository`

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
      "description": "간략 목록에 포함할 최대 자산 수이며, 1..100 범위로 제한됩니다. 반환된 assets의 길이를 total과 비교합니다. 이 도구에는 offset/has_more 필드가 없습니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별 정보는 include_ids로 별도 제어합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "total": 0, // 전체 매치 수. assets는 limit까지이며 offset/has_more 없음
  "assets": [] // 검색된 자산과 준비 상태입니다. id를 후속 도구의 asset_id로 사용합니다.
}
```

## 82. asset-11_search

기준 API: `search_drawing_assets`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

텍스트·분류·측정 치수로 모델·2D 자산을 검색합니다.

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
      "description": "이 응답에서 반환할 최대 행 수입니다. 페이지를 전체 결과로 간주하기 전에 total과 페이지 처리 필드를 확인합니다."
    },
    "offset": {
      "default": 0,
      "type": "integer",
      "description": "이 페이지의 시작 행을 0부터 세는 값입니다. 다음 페이지를 요청할 때도 같은 필터를 사용합니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별 정보는 include_ids로 별도 제어합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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

다이어그램 자산 검색·배치 · prefix: `diagram-NN_` · 유형 내 순번 01–04

## 31. diagram-01_get

기준 API: `get_diagram_asset`

근거: src/mcp/features/diagrams/tools.py

### DESCRIPTION

다이어그램 자산의 metadata와 파일 상태를 조회합니다.

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
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "선택 가능한 세부 그룹은 dimensions, drawing, metadata, source, paths, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별 정보는 include_ids로 별도 제어합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "asset": { // 선택한 다이어그램 자산의 정보입니다.
    "name": "예시 다이어그램",
    "file_available": true
  },
  "next_step_guide": "선택한 자산의 ID로 place_diagram_asset을 호출할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 54. diagram-02_list

기준 API: `list_diagram_assets`

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
      "description": "이 응답에서 반환할 최대 행 수입니다. 페이지를 전체 결과로 간주하기 전에 total과 페이지 처리 필드를 확인합니다."
    },
    "offset": {
      "default": 0,
      "type": "integer",
      "description": "이 페이지의 시작 행을 0부터 세는 값입니다. 다음 페이지를 요청할 때도 같은 필터를 사용합니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "선택 가능한 세부 그룹은 dimensions, drawing, metadata, source, paths, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별 정보는 include_ids로 별도 제어합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "library_id": "diagram_assets", // include_ids=true에서 유지되는 라이브러리 구분자
  "assets": [], // 다이어그램 자산과 요청한 속성입니다.
  "total": 0, // 필터에 일치하는 전체 항목 수
  "offset": 0, // 현재 페이지 시작 위치
  "limit": 20, // 페이지 최대 항목 수
  "next_offset": null, // 다음 페이지의 시작 위치입니다. null이면 다음 페이지가 없습니다.
  "purpose": "2D 벡터 다이어그램 및 선화" // 이 라이브러리의 용도입니다.
}
```

## 63. diagram-03_place

기준 API: `place_diagram_asset`

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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "asset_id": "example-asset", // 자산 ID
  "object_guid": "00000000-0000-0000-0000-000000000001", // 삽입한 최상위 블록 GUID. get_objects 또는 Scene 구성원 입력에 재사용
  "definition_created": true, // 새 블록 정의를 생성했는지 나타냅니다.
  "next_step_guide": "get_objects와 캡처로 배치 위치·축척을 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 81. diagram-04_search

기준 API: `search_diagram_assets`

근거: src/mcp/features/diagrams/tools.py

### DESCRIPTION

텍스트·분류·기록된 치수로 다이어그램 자산을 검색합니다.

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
      "description": "이 응답에서 반환할 최대 행 수입니다. 페이지를 전체 결과로 간주하기 전에 total과 페이지 처리 필드를 확인합니다."
    },
    "offset": {
      "default": 0,
      "type": "integer",
      "description": "이 페이지의 시작 행을 0부터 세는 값입니다. 다음 페이지를 요청할 때도 같은 필터를 사용합니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "선택 가능한 세부 그룹은 dimensions, drawing, metadata, source, paths, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별 정보는 include_ids로 별도 제어합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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

도면 스타일·해치·평면 및 단면 생성 · prefix: `drawing-NN_` · 유형 내 순번 01–06

## 07. drawing-01_apply_style

기준 API: `apply_drawing_style`

근거: src/mcp/features/drawings/tools.py

### DESCRIPTION

도면 레시피의 레이어·색상·출력 선 두께·선종류를 Rhino 문서에 적용합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "recipe_id": {
      "default": "technical_axon_v1",
      "type": "string",
      "description": "list_drawing_recipes(include_ids=true)에서 얻은 도면 레시피 ID 또는 이미 알고 있는 레시피 ID입니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
    "message": "…",
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

## 33. drawing-02_get_recipe

기준 API: `get_drawing_recipe`

근거: src/mcp/features/drawings/tools.py

### DESCRIPTION

저장된 도면 레시피의 목적과 설정을 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "recipe_id": {
      "type": "string",
      "description": "list_drawing_recipes(include_ids=true)에서 얻은 도면 레시피 ID 또는 이미 알고 있는 레시피 ID입니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "상세 그룹: scales, parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다. ID는 include_ids로 선택합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "recipe_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
  "next_step_guide": "선택한 규칙을 문서에 적용하려면 apply_drawing_style을 사용합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 42. drawing-03_get_plan_section_result

기준 API: `get_plan_section_result`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

보관된 PlanSection 실행 결과를 페이지별로 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "result_id": {
      "type": "string",
      "description": "plan_section.result.result_id에서 얻은 의미를 해석하지 않는 32자 결과 영수증 ID입니다."
    },
    "offset": {
      "default": 0,
      "type": "integer",
      "description": "첫 페이지는 0, 이후에는 같은 결과의 next_offset을 그대로 입력합니다. UTF-16 코드 단위이므로 Python 문자열 길이로 계산하지 않습니다."
    },
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "바인딩된 저장 문서 경로입니다. 값을 명시하면 런타임 바인딩과 일치해야 합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "result_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "result_id": "00000000000000000000000000000001", // 같은 Rhino 문서 인스턴스에 보관된 결과 ID입니다.
  "offset": 0, // 결과 문자열의 UTF-16 코드 단위 시작 위치입니다.
  "json_chunk": "{\"status\":\"completed\"}", // 전체 객체가 아니라 JSON 문자열 조각
  "total_characters": 22, // UTF-16 코드 단위 길이
  "next_offset": null, // 이어 읽을 UTF-16 코드 단위 위치입니다. null이면 마지막 페이지입니다.
  "result_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", // 보관된 전체 결과 문자열의 SHA-256 해시입니다.
  "observation": "…" // 보관된 실행 결과의 관찰 시점에 대한 안내입니다.
}
```

## 50. drawing-04_import_hatches

기준 API: `import_drawing_hatch_patterns`

근거: src/mcp/features/drawings/tools.py

### DESCRIPTION

등록된 PAT 자산의 해치 정의를 Rhino 문서에 추가합니다. 같은 이름의 정의는 재사용합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "asset_id": {
      "type": "string",
      "description": "include_ids=true로 조회한 일치하는 목록/검색 결과의 기존 라이브러리 자산 ID 또는 이미 알고 있는 ID입니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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

## 56. drawing-05_list_recipes

기준 API: `list_drawing_recipes`

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
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "상세 그룹: scales, parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다. ID는 include_ids로 선택합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
  "next_step_guide": "선택한 레시피의 ID로 get_drawing_recipe을 호출할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 65. drawing-06_generate_plan_section

기준 API: `plan_section`

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
      "description": "런타임이 제공하는 바인딩된 저장 문서 경로입니다. 값을 명시하면 해당 바인딩과 일치해야 합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
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

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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

Grasshopper 로직·캡슐 조회와 실행 · prefix: `grasshopper-NN_` · 유형 내 순번 01–04

## 34. grasshopper-01_get_logic

기준 API: `get_logic_by_id`

근거: src/mcp/features/grasshopper/tools.py

### DESCRIPTION

로컬 Grasshopper 정의의 구성요소·설명·metadata를 조회합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "logic_id": {
      "type": "string",
      "description": "기존 Grasshopper 라이브러리 파일명에서 확장자를 뺀 이름입니다. 알고 있는 ID를 재사용하거나 list_library(include_ids=true)에서 얻습니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "상세 그룹: ports, definition, source, paths, audit, all입니다. 생략하거나 비우면 요약을 반환합니다. ID는 include_ids로 선택합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "logic_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
  "next_step_guide": "캡슐 계약과 실행 감사가 확인된 경우 run_gh_definition으로 계산할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 51. grasshopper-02_list_capsules

기준 API: `list_capsules`

근거: src/mcp/features/grasshopper/tools.py

### DESCRIPTION

기능별 Grasshopper 캡슐과 실행 감사 여부를 조회합니다.

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
      "description": "true이면 run_gh_definition이 실행을 허용하는 캡슐만 나열합니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "상세 그룹: ports, definition, source, paths, audit, all입니다. 생략하거나 비우면 요약을 반환합니다. ID는 include_ids로 선택합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
      "structure_type": "beam",
      "definition_file": "example.ghx",
      "title": "Example capsule",
      "audited": true,
      "inputs": [
        "ALMOND_IN_example"
      ],
      "outputs": [
        "ALMOND_OUT_example"
      ]
    }
  ],
  "next_step_guide": "definition_file의 파일명(확장자 제외)을 get_logic_by_id에 입력해 포트 타입·단위를 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 57. grasshopper-03_list_library

기준 API: `list_library`

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
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "상세 그룹: ports, definition, source, paths, audit, all입니다. 생략하거나 비우면 요약을 반환합니다. ID는 include_ids로 선택합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "total_entries": 1, // 라이브러리 전체 항목 수입니다.
  "logic_names": [ // 기본 응답에서도 get_logic_by_id.logic_id로 사용 가능
    "example-logic"
  ],
  "logic_count": 1, // include_ids=false에서 logic_ids 대신 추가됨
  "next_step_guide": "logic_names에서 선택한 이름을 get_logic_by_id에 입력합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 77. grasshopper-04_run_definition

기준 API: `run_gh_definition`

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
      "description": "list_capsules에서 얻은 안정적인 캡슐 식별자입니다(예: \"karamba_beam_v1\")."
    },
    "inputs": {
      "additionalProperties": true,
      "type": "object",
      "description": "ALMOND_IN_ 포트 이름과 값의 객체입니다. 형상은 {\"guids\":[\"객체 GUID\"]}, 숫자·정수·문자열·불리언은 JSON 값, 목록은 number[]/integer[]/string[]의 평탄한 배열입니다. 타입·단위·필수 여부는 metadata.capsule.inputs 계약을 따릅니다."
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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
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

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
  "next_step_guide": "베이크한 형상이 있으면 get_objects와 캡처로 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

# Research

구법·건축 유형·참고자료 조사 · prefix: `research-NN_` · 유형 내 순번 01–03

## 27. research-01_get_construction_guidance

기준 API: `get_construction_guidance`

근거: src/mcp/features/guidance/tools.py

### DESCRIPTION

구법 라이브러리에서 구조 시스템·예비 경간·부재 깊이·조립 방식을 비교합니다.

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
      "description": "validate_structure에서 사용하는 이름: \"Wood\", \"Steel\", \"Concrete\"."
    },
    "structure_type": {
      "default": "",
      "type": "string",
      "description": "validate_structure의 유형입니다(\"beam\", \"truss\", \"shell\", \"frame\", \"canopy\", \"gridshell\", \"membrane\", \"highrise\")."
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
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "상세 그룹: rules, narrative, source, metadata, audit, all입니다. 생략하거나 비우면 요약을 반환합니다. ID는 include_ids로 선택합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
  "next_step_guide": "선택한 구법을 객체에 기록하려면 assign_material을 사용합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 48. research-02_get_typology_narrative

기준 API: `get_typology_narrative`

근거: src/mcp/features/guidance/tools.py

### DESCRIPTION

역사 라이브러리에서 건축 유형의 서사·선례·도시적 역할을 조회합니다.

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
      "description": "validate_structure의 유형으로 필터링합니다(\"shell\", \"truss\", \"frame\", \"membrane\" 등)."
    },
    "limit": {
      "default": 5,
      "type": "integer",
      "description": "반환할 최대 항목 수입니다. 기본값은 5입니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "상세 그룹: rules, narrative, source, metadata, audit, all입니다. 생략하거나 비우면 요약을 반환합니다. ID는 include_ids로 선택합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
  "next_step_guide": "관련 구법은 get_construction_guidance로 비교할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 80. research-03_search_details

기준 API: `search_detail_sources`

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
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "상세 그룹: rules, narrative, source, metadata, audit, all입니다. 생략하거나 비우면 요약을 반환합니다. ID는 include_ids로 선택합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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

구조·피난 검토와 보고서 · prefix: `analysis-NN_` · 유형 내 순번 01–05

## 12. analysis-01_check_egress

기준 API: `check_egress`

근거: src/mcp/features/egress/tools.py

### DESCRIPTION

제공된 층 경계·출구·경로 측정값으로 피난 조건을 예비 검토합니다.

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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
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

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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

## 22. analysis-02_export_structural_report

기준 API: `export_structural_report`

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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "path": ".almond/produced/example/structure-report.md", // 작성된 Markdown 파일
  "runs": 1, // 실제 포함한 저장 실행 수
  "latest_method": "native" // 가장 최근 저장된 실행 방식
}
```

## 52. analysis-03_list_design_codes

기준 API: `list_design_codes`

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
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "상세 그룹: parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다. ID는 include_ids로 선택합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
  "next_step_guide": "선택한 기준 ID를 validate_structure 또는 visualize_structure에 사용합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 91. analysis-04_validate_structure

기준 API: `validate_structure`

근거: src/mcp/features/structure/tools.py

### DESCRIPTION

Rhino 구조 형상을 지정한 하중·지지·접합·설계기준 가정으로 해석합니다.

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
      "description": "설계기준 또는 국가 부록에서 정하는 수치(gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, 처짐 한계)에 사용할 설계기준 프로필입니다. \"eurocode\"(기본값, EN 권장값), list_design_codes의 프로필 또는 \"off\"를 사용합니다. \"off\"는 부분계수 없이 G + Q를 적용하며 design_basis=\"unfactored\"와 같습니다. 결과의 \"design_code\"에는 사용한 값과 검증되지 않은 값이 포함됩니다."
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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "guids"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
  "next_step_guide": "문제 부재는 visualize_structure로 검토할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 92. analysis-05_visualize_structure

기준 API: `visualize_structure`

근거: src/mcp/features/structure/tools.py

### DESCRIPTION

구조 해석 결과를 변형·사용률·좌굴의 임시 뷰포트 오버레이로 표시합니다.

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
      "description": "validate_structure와 동일하게 배치된 라이브러리 자산의 하중을 추가합니다(네이티브 엔진). 하중 작용점에 하중 화살표를 그립니다."
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
      "description": "validate_structure와 동일한 \"rigid\" 또는 \"simple\"입니다. 핀 접합 단부는 작은 원으로 그립니다."
    },
    "stability": {
      "default": "auto",
      "type": "string",
      "description": "validate_structure와 동일한 \"auto\" 또는 \"off\"입니다."
    },
    "design_code": {
      "default": "eurocode",
      "type": "string",
      "description": "설계기준 또는 국가 부록에서 정하는 수치(gamma_G, gamma_Q, psi_0, xi, gamma_M0, gamma_M1, 처짐 한계)에 사용할 설계기준 프로필입니다. \"eurocode\"(기본값, EN 권장값), list_design_codes의 프로필 또는 \"off\"를 사용합니다. \"off\"는 부분계수 없이 G + Q를 적용하며 design_basis=\"unfactored\"와 같습니다. 결과의 \"design_code\"에는 사용한 값과 검증되지 않은 값이 포함됩니다."
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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "pass", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "analysis_method": "native", // 해석 방식입니다.
  "max_displacement_mm": 12, // 최대 변위(mm)입니다.
  "deflection_limit_mm": 24, // 허용 처짐(mm)입니다.
  "span_m": 6, // 검토 스팬(m)입니다.
  "max_utilization": 0.72, // 최대 부재 사용률입니다.
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
  "next_step_guide": "판정을 검증 이력으로 남기려면 validate_structure를 사용합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

# Exchange

앱 간 자산 교환·Chestnut 게시 · prefix: `exchange-NN_` · 유형 내 순번 01–05

## 21. exchange-01_export_asset_contract

기준 API: `export_asset_contract`

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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
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

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "asset_id": "example-asset", // 자산 ID입니다.
  "glb_path": ".almond/produced/example/example-asset.glb", // 내보낸 GLB 파일 경로입니다.
  "contract_path": ".almond/produced/example/example-asset.almond.json", // import_asset_contract에 전달
  "dimensions_mm": { // 내보낸 자산의 경계 치수입니다. 단위는 mm입니다.
    "width": 1000,
    "depth": 500,
    "height": 800
  },
  "materials": [], // 인식된 Almond 재료 그룹. 비어 있어도 모든 재료가 보존됐다는 뜻은 아님
  "next_step_guide": "대상 Rhino로 가져오려면 반환된 contract_path를 import_asset_contract에 전달하고 mm 단위 배치를 선택합니다. 내보내기만으로 추가 가져오기를 요청한 것은 아닙니다. …" // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 26. exchange-02_get_blender_script

기준 API: `get_blender_helper_script`

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
      "description": "true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다."
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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "action"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "action": "export", // 스크립트의 작업 종류입니다.
  "script": "<생성된 Blender Python 소스>", // Blender에서 실행할 Python 코드입니다.
  "next_step_guide": "생성한 코드는 Blender에서 실행합니다. export 실행이 성공하면 얻은 계약을 import_asset_contract에 사용할 수 있습니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 49. exchange-03_import_asset_contract

기준 API: `import_asset_contract`

근거: src/mcp/features/exchange/tools.py

### DESCRIPTION

Almond 계약과 GLB를 Rhino 문서로 가져와 재료·metadata·배치를 복원합니다.

### TOOL INPUT

```json
{
  "additionalProperties": false,
  "properties": {
    "contract_path": {
      "type": "string",
      "description": "export_asset_contract 또는 Blender 내보내기가 반환한 계약 경로입니다. 관리형 세션에서는 프로젝트 기준 상대 .almond.json 경로이고, 독립 실행에서는 절대 경로입니다."
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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "required": [
    "contract_path"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

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
  "next_step_guide": "get_objects와 캡처로 가져온 형상·재료·배치를 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 68. exchange-04_publish_chestnut_advanced

기준 API: `publish_objects_to_chestnut`

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
      "description": "모델을 1미터 크기의 전시 소품으로 정규화하지 않고 Rhino의 실제 치수를 유지합니다."
    },
    "mass": {
      "default": 0.0,
      "type": "number",
      "description": "물리 질량(kg)입니다. static 바디는 항상 0을 사용합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
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

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "success": true, // 원격 /api/props/upsert 응답에서 온 값
  "chestnut_url": "https://chestnut-mnvo.onrender.com", // 게시한 Chestnut 서비스의 주소입니다.
  "next_step_guide": "Chestnut에서 게시 결과를 확인하고, 갱신할 때는 확인한 자산 ID를 재사용합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```

## 69. exchange-05_publish_chestnut

기준 API: `publish_to_chestnut`

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
      "description": "관찰, 선택 또는 모델링 결과에서 얻은 현재 Rhino 객체 GUID입니다. 스크립팅 호출은 필요하지 않습니다."
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
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
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

코드 기반 예시(실측 아님). //는 실제 응답에 없는 문서용 설명입니다.

```jsonc
{
  "status": "success", // 현재 처리의 상태입니다. 오류이면 message와 error_code를 확인합니다.
  "success": true, // 하위 publish_objects_to_chestnut의 원격 응답을 그대로 반환
  "chestnut_url": "https://chestnut-mnvo.onrender.com", // 게시한 Chestnut 서비스의 주소입니다.
  "next_step_guide": "Chestnut에서 게시 결과를 확인합니다." // 이 결과에서 이어갈 수 있는 다음 작업입니다. 필요한 경우에만 반환합니다.
}
```
