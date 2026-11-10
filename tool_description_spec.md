> 1차 서버 반영: get_policy 선택 조회, 삭제 도구 3개 제거, 연결 선택 기억 및 project_info 안내. 분류·기존 번호는 보존합니다. 설명·출력 예시 전체 재검수는 2차 범위이며, 예시는 실측이 아닙니다.

**DESCRIPTION 간결화와 후속 도구 안내 제안**
실제 서버에 등록된 description·스키마·반환값은 변경하지 않았다.

## Prefix 명명

문서의 도구명은 유형별 prefix 뒤에 해당 유형 안의 두 자리 순번을 붙인다. 예: connect-01_list_up, connect-02_session. 순번은 각 유형에서 01부터 시작하며, 기존 전체 도구 번호 01–92도 함께 유지한다. 각 도구 아래의 기준 API는 실제 서버 호출명이다. 설명·스키마·출력에서 쓰는 API 이름과 서버 코드는 이번 문서 편집으로 변경하지 않는다.

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

- 확인일: 2026-11-09.
- 기준 저장소: 공개 GitHub 저장소 hongikkaan/almond-mcp (MIT License).
- 현재 대조 기준: main · 098703619e10f68f3721a32033f0da0f6eaf6159. 기존 기준 b2108b2 이후 92개 도구의 description·입력 계약·반환 구현은 바뀌지 않았다. 각 도구의 고정 커밋 근거 링크도 유효하다.
- 버전: almond-mcp 0.7.0rc2, FastMCP 4.1.0, MCP 2.3.0.
- 총 **89개**: 공통 공개 도구 **85개** + beyond·CoS 외부 연결 관리 도구 **4개**. 내부 상태 확인용 worker_state는 외부 공개 도구가 아니므로 이 목록에 포함하지 않는다.
- 도구 본문이 실행되지 않는 AST 등록 방식으로 현재 description·inputSchema를 재생성하고, 외부 연결기가 추가하는 connection_id와 관리 도구 4개의 스키마를 적용했다. 배포 중인 Rhino 서버에서 수집한 실측 목록은 아니다.
- DESCRIPTION에서 입력 필드·기본값·출력 키를 되풀이하던 설명을 줄였다. 스키마에 없는 실행 조건·부작용·오류 후 재시도 제한은 남기고, 특정 입력의 상세 계약은 TOOL INPUT의 보충 설명에 둔다. 후속 안내는 반환 코드와 다음 도구의 실제 입력 계약을 대조했다.

## 읽는 방법

- **DESCRIPTION: 서버 미반영 개편안.** 도구의 역할·선택 기준과 스키마만으로 알 수 없는 핵심 조건을 적는다. 원문 그대로의 인용이 아니며, 기존 전체 설명은 각 도구의 기준 코드에서 확인할 수 있다.
- **TOOL INPUT: 현재 코드의 inputSchema.** 필드명·타입·필수 목록·기본값·제약은 그대로이며 description 값만 한국어로 번역했다. 필요한 경우 스키마 아래에 **입력 보충 설명(문서용)**을 붙인다. 이 설명은 실제 전달되는 스키마에 포함되지 않는다.
- **TOOL OUTPUT: 현재 코드 기반 예시.** 따옴표 안의 키·값은 반환 데이터 영역이며, **// 뒤는 실제 응답에 없는 독자용 주석**이다. 서버가 반환하는 안내문도 데이터 영역에 포함하되 영어 설명은 한국어로 번역했다. 실제 응답 언어를 바꿨다는 뜻은 아니다. 주석을 붙인 표기는 JSONC다.
- **후속 안내 제안 · 서버 미반영:** 실제 출력 예시와 분리한 next_step_guide 문구다. 기존 next_step·next_tool과 같은 현재 반환 필드를 교체하거나 이미 구현된 필드로 표시하지 않는다. 필요한 경우에만 후속 역할을 안내하며, 후속 호출의 입력 형식은 해당 TOOL INPUT을 따른다.
- 예시는 실측 응답이 아니다. 이름·ID·수치·경로는 예시 값이고, …와 주석에 표시한 상세 객체·배열은 축약이다. MCP 포장·이미지 바이너리는 생략했다. API·필드명·상태값 등 기술 식별자는 번역하지 않았다.
- **연계 조건:** 반환 상태와 작업 목적에 맞는 안내만 사용한다. ID를 생략하는 조회는 필요한 식별자·상세 그룹을 요청해야 하며, 재출력하지 않는 ID는 기존 입력에서 보관한다. 참고값·경로·자산 ID를 확인 없이 객체 GUID나 다른 단위의 값으로 넘기지 않는다. 안내 자체가 실행·검증·게시 권한을 뜻하지 않는다.
- 근거는 main의 등록 코드, 반환 투영·런타임 구현과 재생성한 92개 inputSchema다. Rhino 연결이나 모델 변경 도구 실행은 하지 않았으며, 실행 성공을 검증한 문서는 아니다.

# Connect

연결·세션 관리 · prefix: `connect-NN_` · 유형 내 순번 01–04

## 01. connect-01_list_up

기준 API: `list_connections`

근거: src/cos/external_host.py

### DESCRIPTION

연결 대상으로 공개된 Rhino 문서와 이 클라이언트의 연결·시작 시도를 조회합니다. **Rhino를 새로 실행하지 않습니다.** 기존 Rhino를 연결 대상으로 공개하려면 저장된 문서에서 almondconnect를 실행합니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

```json
{
  "type": "object",
  "properties": {},
  "required": [],
  "additionalProperties": false
}
```

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "instructions": "초기화는 도구를 공개하기만 하며 Rhino나 모델링 워커를 시작하지 않습니다. …", // 서버가 실제 반환하는 연결 안내문. 값은 앞부분만 발췌
  "targets": [], // 대상별 host_id/model_path를 connect에 함께 사용. state가 in_use/unavailable이면 연결 후보가 아님
  "connections": [], // 이 클라이언트의 연결. 각 활성 항목의 connection_id를 업무 도구에 재사용
  "starts": [] // 명시적 시작 시도만 기록. waiting 시도는 같은 request_id/model_path로 start_session을 이어감
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 연결 가능한 문서는 `connect`로 연결하고, 이미 연결된 문서는 해당 연결로 작업합니다. 새 Rhino가 필요한 경우에만 `start_session`을 사용합니다.
코드 1 · 코드 2 · 코드 3

## 02. connect-02_session

기준 API: `connect`

근거: src/cos/external_host.py

### DESCRIPTION

목록에서 확인한 Rhino 문서 하나에 독립 슬롯·세션으로 연결합니다. **같은 폴더의 모델은 데이터베이스와 산출물 루트를 공유합니다.**

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

```json
{
  "type": "object",
  "properties": {
    "host_id": {
      "type": "string",
      "description": "대상 Rhino 프로세스에 대해 list_connections가 연결 대상으로 공개한 정확한 host_id입니다."
    },
    "model_path": {
      "type": "string",
      "description": "목록에 표시된 저장된 모델의 정확한 경로입니다."
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

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "connection_id": "example-connection", // 이 연결의 업무 도구 및 disconnect에 전달
  "host_id": "example-host", // Rhino 호스트 ID
  "state": "ready", // 현재 상태
  "reason": "", // 상태 사유 또는 오류 내용. 없으면 빈 문자열
  "model_path": "C:\\Example\\example.3dm", // 저장된 모델의 경로
  "model_filename": "example.3dm", // 모델 파일명
  "slot": "A", // 독립 연결 슬롯. 같은 폴더의 모델은 DB·산출물 루트를 공유
  "pid": 1234, // Rhino 프로세스 ID
  "artifact_dir": ".almond/produced/example", // 연결 call_root 예시. 선택된 Plan/Loop 작업 폴더와 구별
  "in_flight": false // 해당 연결에 호출이 진행 중인지 여부
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 연결 후, 1.필요한 프로젝트 정보는 `project_info`로, 2. 기존 작업은 `list_phases` 또는 `list_plans`로 확인합니다. 

## 03. connect-03_start_session

기준 API: `start_session`

근거: src/cos/external_host.py

### DESCRIPTION

저장된 모델을 화면에 표시되는 새 Rhino에서 열고 연결합니다. Rhino를 저장하거나 닫지 않습니다. 시작 확인이 지연되면 **같은 요청 ID로 확인**하며, 새 ID는 별도의 Rhino를 시작합니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

```json
{
  "type": "object",
  "properties": {
    "model_path": {
      "type": "string",
      "description": "기존에 저장된 로컬 .3dm의 절대 경로입니다. 저장하지 않고 엽니다."
    },
    "request_id": {
      "type": "string",
      "minLength": 1,
      "maxLength": 128,
      "description": "이번 명시적인 시작 시도의 고유 ID입니다. 같은 시도를 확인할 때는 변경하지 않습니다."
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

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "connection_id": "example-connection", // 연결 성공 후 업무 도구에 전달
  "host_id": "example-host", // Rhino 호스트 ID
  "state": "ready", // 현재 상태
  "reason": "", // 상태 사유 또는 오류 내용. 없으면 빈 문자열
  "model_path": "C:\\Example\\example.3dm", // 저장된 모델의 경로
  "model_filename": "example.3dm", // 모델 파일명
  "slot": "A", // 연결 슬롯
  "pid": 1234, // Rhino 프로세스 ID
  "artifact_dir": ".almond/produced/example", // 연결 call_root 예시. Plan/Loop 선택 폴더와 구별
  "in_flight": false, // 해당 연결에 호출이 진행 중인지 여부
  "request_id": "example-start" // 동일 시작 시도에 재사용. 대기·실패 상태는 list_connections.starts에서 확인
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 연결되면 해당 연결로 작업합니다. 시작 여부가 불확실하면 `list_connections`에서 시도를 확인한 뒤 같은 `start_session` 요청을 이어갑니다.

## 04. connect-04_disconnect

기준 API: `disconnect`

근거: src/cos/external_host.py

### DESCRIPTION

연결을 해제합니다. **Rhino를 닫거나 저장하지 않으며**, 완료가 확인되지 않은 네이티브 작업의 잠금은 남을 수 있습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

```json
{
  "type": "object",
  "properties": {
    "connection_id": {
      "type": "string",
      "description": "connect 또는 list_connections가 반환한 이 클라이언트의 활성 connection_id입니다. 해당 연결만 해제합니다."
    }
  },
  "required": [
  ],
  "additionalProperties": false
}
```

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "connection_id": "example-connection", // 해제된 연결. 이후 업무 도구에 재사용하지 않음
  "worker_closed": true, // worker가 종료됐는지 여부
  "rhino_closed": false, // Rhino가 닫혔는지 여부. disconnect는 false
  "released": true, // Rhino 측 해제 확인. false이면 이 성공 예시 대신 오류로 보고될 수 있음
  "reason": "" // 미확정 네이티브 작업으로 잠금이 남으면 상태를 확인한 뒤 재연결
}
```

코드

# Context

기본 가이드·프로젝트 정보·운영 정책 · prefix: `context-NN_` · 유형 내 순번 01–04


## 67. context-04_get_project_info

기준 API: `project_info`

근거: src/mcp/runtime/mcp_server.py

### DESCRIPTION

필요한 프로젝트 경로·등록 파일·현재 문서·작업 공간 정보를 읽습니다. 확인한 정보는 재사용하되 **문서 변경이나 재연결 뒤에는 갱신**합니다. 등록 파일 목록은 디스크 존재 증명이 아니며, 조회가 Plan을 선택하거나 모델을 저장하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청한 출력에 식별 필드를 포함합니다. false이면 부가 ID를 생략합니다. 이후 도구에 반환된 ID가 필요할 때 true를 요청합니다. 추가 상세 그룹을 선택하는 옵션은 아닙니다."
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
  "type": "object",
  "required": [
  ]
}
```

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석. `next_step_guide`는 후속 안내 제안으로 서버 미반영.

```json
{
  "status": "success",
  "project": { // project/document는 실시간 문서 관찰 1회를 공유. locations/runtime만 요청하면 관찰하지 않음
    "project_root": "C:\\Example", // 절대 프로젝트 루트. 관리 도구에는 이 루트 기준 상대 경로를 전달
    "file_name": "example.3dm",
    "file_path": "example.3dm",
    "is_bound_document": true, // 관찰한 현재 문서가 연결 모델과 같음. 관찰 실패는 false가 아니라 오류
    "files": [ // DB 등록 목록이며 디스크 스캔·존재 확인 결과가 아님
      {
        "project_file_id": "file_example", // include_ids=true일 때 반환. Phase/Scene의 project_file_id에 사용
        "file_name": "example.3dm"
      }
    ],
    "files_page": {
      "total": 1,
      "limit": 50,
      "offset": 0,
      "truncated": false // true면 같은 조건에서 files_offset을 offset+limit으로 이어감
    }
  },
  "locations": {
    "plan_id": "", // include_ids=true 예시. 선택된 Plan이 없으면 빈 값
    "step_id": "",
    "artifact_dir": null, // Plan/Loop 선택 전에는 null. DB는 프로젝트 공유, 이 작업 공간 선택은 연결별
    "database": ".almond/example.db"
  },
  "next_step_guide": "- `list_plans`으로 프로젝트 진행상황 파악합니다.\n- 산출물 작업 공간은 `set_working_plan`으로 선택합니다.\n- 객체 상태가 필요하면 `get_objects`로 확인합니다."
}
```

## 36. context-01_get_policy

기준 API: `get_policy`

근거: src/mcp/features/guidance/tools.py

### DESCRIPTION

BASIC 설계·검증 지침과 사용 가능한 공통 도구 이름을 조회합니다. 

policy를 생략하면 기본 지침과 도구명·policy 목록을 반환합니다. metadata, rhino_scripting, rhinocode를 선택하면 해당 지침을 반환합니다.
### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "Optional connection override from list_connections. Omit to use the connection selected by connect or start_session."
    }
  },
  "type": "object"
}
```

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "guide_version": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", // 같은 버전 지침 재사용용 해시. 다른 도구의 입력 핸들이 아님
  "text": "---\nname: rhino-almond\ndescription: \"Rhino에서 Almond MCP로 기존 설계를 발전시키기 위한 건축적 판단.\"\n---\n\n# Rhino Almond\nAlmond MCP를 사용해 Rhino로 건축 설계를 발전시킨다. \n\n**작업 태도**\n 설계 내용의 충돌은, 현재 설계 의도와 작업 목적을 기준으로 …", // 실제 BASIC 본문 일부. 정적 지침이지 현재 모델의 검증 결과가 아님
  "source_refs": [ // 출처와 해시. rhino_scripting 선택 시 scripting_skill과 해당 출처 반환
    {
      "path": "src/mcp/BASIC-INSTRUCTIONS.md", // 안내문 출처 경로
      "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" // 파일 해시. 예시 값은 가상
    }
  ],
  "selected_policy": "basic",
  "available_policies": {"basic": "설계·검증", "metadata": "메타데이터", "rhino_scripting": "스크립트 작성", "rhinocode": "실행"},
  "tools": [ // 공개 이름 목록만 제공. 도구별 description 전문이나 호출 인수 묶음이 아님
    "get_policy"
  ]
}
```



# Plan

작업 계획·단계·산출물 관리 · prefix: `plan-NN_` · 유형 내 순번 01–13

## 14. plan-01_create_phase

기준 API: `create_phase`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

관련 Plan을 묶는 관리 단위인 Phase를 생성합니다. 파일 연결과 의존성은 기록만 하며, 모델·Plan을 만들거나 **의존성에 따라 실행을 강제하지 않습니다.**

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

```json
{
  "additionalProperties": false, // phase를 create하는데 이 값이 왜 필요한지?
  "properties": {
    "name": {
      "type": "string",
      "description": "작업 구성에 사용할 비어 있지 않은 Phase 이름입니다."
    },
    "description": {
      "default": "",
      "type": "string",
      "description": "선택 사항인 프로젝트 단계 또는 작업 묶음에 대한 설명입니다."
    },
    "file_name": {
      "default": "",
      "type": "string", // array로, file명.3dm으로. 
      "description": "phase가 속한 라이노 파일명을 기입, array입력 가능. 저장된 연결 관계이며 파일 작업이 아닙니다.??"
    },
    "project_file_id": { // 불필요
    },
    "status": {
      "default": "pending",
      "type": "string",
      "description": "초기 워크플로 상태입니다. pending, running, paused, completed, failed 또는 blocked를 사용할 수 있습니다."
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
      "description": "설명을 좆같이 써놨더라고? 필요한 말만 써라. "
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
      "description": "앞선 Phase ID 하나입니다(phase_ 접두사). depends_on 관계와 별개입니다. 
      갱신 시 생략/null이면 유지하고 빈 문자열이면 지웁니다. 실행을 제한하거나 완료를 요구하지 않고 연속성을 기록합니다." // 이 line문장은 꼭 필요한 건가??
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

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "phase": { // 생성 확인만 반환. depends_on은 미생성·자기·순환 참조도 기록하며 실행을 강제하지 않음
    "phase_id": "phase_example" // create_plan의 소속 또는 list_plans/get_phase_plan_step의 Phase 대상
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 새 Phase에 `create_plan`으로 Plan을 만들거나, `list_plans`와 `get_phase_plan_step`으로 구성 내용을 확인합니다.
코드

## 15. plan-02_create

기준 API: `create_plan`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

목표와 작업 목적에 맞는 템플릿으로 Plan과 Step을 생성합니다. 기존에 선택한 템플릿을 존중하며, **생성만으로 작업 공간을 선택하거나 작업을 실행하지 않습니다.** 시공 상세 템플릿이 해당 모델링에 대한 사용자 요청을 대신하지는 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "등록된 Step 템플릿 키이며 기본값은 house입니다. 기본 제공 키는 spatial_development, semantic_exploration, plan_editing, model_revision, inspection, structure, construction_detail, drawing, component, house, interior입니다. 등록된 사용자 지정 scope는 기본 제공 템플릿에 매핑됩니다. 작업 목적에 따라 선택합니다. 생성 시 Step이 실행되지는 않습니다."
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
      "description": "선택 사항인 Plan ID 배열입니다(plan_ 접두사만 허용). 실행 순서를 강제하지 않고 의존성을 기록합니다."
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
      "description": "앞선 Plan ID 하나입니다(plan_ 접두사). depends_on 관계와 별개입니다. 갱신 시 생략/null이면 유지하고 빈 문자열이면 지웁니다. 실행을 제한하거나 완료를 요구하지 않고 연속성을 기록합니다."
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

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "plan": { // 생성 확인. Step은 get_phase_plan_step에서 조회하며 inspection 템플릿에는 모델링 Step이 없음
    "plan_id": "plan_example", // 상세 조회·execute_looping·set_working_plan에 사용. depends_on은 실행을 제한하지 않음
    "loop_no": 0, // 아직 회차를 시작하지 않음. Step UUID는 회차 사이에 유지
    "revision": 1 // 자동 할당. 필요하면 loop_no와 함께 update_plan의 expected_revision 검사에 사용
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: `get_phase_plan_step`으로 작업 단계를 확인합니다. 회차를 시작하려면 `execute_looping`을, 산출물 위치만 선택하려면 `set_working_plan`을 사용합니다.
코드

## 18. plan-03_execute_looping

기준 API: `execute_looping`

근거: src/mcp/runtime/mcp_server.py

### DESCRIPTION

Plan의 다음 Loop를 시작하거나 최신 Loop를 재개하여 작업 맥락과 산출물 위치를 준비합니다. Step이나 Rhino 작업을 자동 실행하지 않으며, 에이전트가 다음 기준에 따라 수행·검증·보고합니다.

- 반환된 Step 순서를 기본으로 따르되 실행을 강제하는 조건으로 취급하지 않습니다. 재개 전에는 저장된 기록을 확인하여 이미 수행한 작업, 남은 검증, 아직 전달하지 않은 보고를 구별하고 완료한 Rhino 작업을 반복하지 않습니다.
- Plan과 Step의 상태(pending, running, paused, completed, failed, blocked)는 명시적으로 기록합니다. Step의 수행·검증·보고 진행과 근거는 `update_step`의 상태 및 `input_refs`·`output_refs`로 남기고, Plan의 변경은 `update_plan`으로 기록합니다. 일반 Rhino/Python 호출 자체는 Plan 리비전을 생성하지 않습니다.
- 이전 결과는 현재에도 유효한지 확인한 뒤 재사용합니다. 사용할 이전 파일 경로는 `input_refs`에, 이번 Loop에서 새로 만들거나 수정한 결과 경로는 `output_refs`에 기록합니다.
- Loop에는 별도 업무 상태가 없고, 더 높은 Loop가 시작되면 이전 Loop는 읽기 전용 참고자료입니다. Step 상태는 Plan 상태와 독립적입니다. 모든 Step을 마치거나 회차를 보고했더라도 Plan 완료는 사용자가 결정하며, 그 결정 후에만 Plan 상태를 completed로 기록합니다.
- 회차가 끝나면 목표, 바뀐 내용, 판단을 뒷받침하는 시각 자료, 검증 결과와 남은 선택지를 사용자에게 보고합니다. 질문은 관련 근거와 연결하고 보고는 간결하게 하며, 이미지 수를 고정하지 않습니다.

### TOOL INPUT

현재 inputSchema의 필드·타입·필수 목록·기본값은 유지합니다. 아래 description은 Loop 운영 정책을 포함한 서버 미반영 개편안입니다.

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
      "description": "false이면 첫 호출에서 Loop 1을, 이후 호출에서는 다음 Loop를 시작합니다. true이면 이미 시작된 최신 Loop의 번호와 Step 기록을 유지하며, 시작된 Loop가 없거나 이전 Loop를 재개하려는 경우에는 사용할 수 없습니다. 다음 회차를 시작하려면 앞 회차를 보고한 뒤 false로 호출합니다. 시작 결과가 불확실하면 get_phase_plan_step으로 현재 Loop와 기록을 먼저 확인하고, 확인 없이 false로 재호출하지 않습니다. 변경 없는 재개는 리비전을 추가하지 않습니다."
    },
    "feedback": {
      "default": "",
      "type": "string",
      "description": "이번 회차에서 반영할 피드백입니다. 새 회차에서는 기본값이 빈 문자열이며, 재개할 때 빈 문자열은 기존 피드백을 유지합니다. 재개 시 기존 값과 다른 비어 있지 않은 피드백을 주면 같은 Loop의 피드백을 갱신하고 리비전을 추가합니다."
    },
    "artifact_name": {
      "default": "",
      "type": "string",
      "description": "최초 Plan 산출물 폴더의 이름이며 경로가 아닙니다. 생략하면 목표에서 이름을 정하고, 날짜 접두사가 없으면 YYMMDD_를 붙입니다. 이미 정해진 Plan 폴더를 이 입력으로 바꾸지 않습니다. 이번 Loop의 모든 산출물은 반환된 artifact_dir(Plan 폴더 아래 01, 02, …)에 저장합니다. 같은 Loop 안에서 덮어쓸 수 있지만 중간 결과를 보존하려면 다른 파일명을 사용합니다. 재사용할 이전 파일을 Plan 루트로 옮기거나 과거 산출물을 자동 삭제하지 않습니다. 다음 Loop 폴더가 이미 있으면 기존 파일을 보존하기 위해 시작을 거부합니다. 리비전은 기록과 참조를 보존하며 덮어쓴 파일 내용이나 Rhino 형상을 복원하지 않습니다."
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

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "plan_id": "plan_example", // Plan ID
  "loop_no": 1, // Loop 회차 번호
  "next_step_id": "step_example", // 미완료 Step 중 다음 후보. 자동 선택·실행은 아니며 없으면 null
  "previous_loop": null, // 이전 회차의 loop_no/steps 요약 또는 null. 이전 Loop는 읽기 전용
  "step_id": "", // 아직 특정 Step은 선택하지 않음. 후보를 set_working_plan.step_id로 전달
  "plan_artifact_dir": ".almond/produced/example", // Plan 산출물 폴더
  "artifact_dir": ".almond/produced/example/01", // 작업 산출물 폴더
  "revision": 1, // Plan+Loop 범위에서 할당. 변경 없는 재개는 리비전을 추가하지 않음
  "title": "예시 계획", // 저장된 제목
  "goal": "예시 목표", // 저장된 목표
  "plan_status": "pending", // 예시 Plan 상태. 회차 시작이 상태를 자동 변경하지 않으며 Loop 자체에는 업무 상태가 없음
  "feedback": "", // 저장된 피드백
  "steps": [ // Step UUID는 회차 간 유지. 상태·입출력 근거는 회차별 기록이며 예시는 일부만 발췌
    {
      "step_id": "step_example", // Step ID
      "name": "예시 단계", // 저장된 이름
      "status": "pending" // Step 업무 상태
    }
  ],
  "policy_reminder": "…" // 서버가 실제 반환하는 지침 안내문. 값 축약
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 제안된 Step을 `set_working_plan`으로 선택해 수행하고 `update_step`으로 상태·근거를 기록합니다.
코드

## 41. plan-05_get_phase_plan_step

기준 API: `get_phase_plan_step`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

%% 표현이 존나 모호해서 툴 잘못 이해할 설명임. 하 씨발... 1. 조회도구이다 2. phsae/plan/step 중에서 조회할 유형을 하나만 선택해서 실행할 수 있다 3. 상세내용(공통이 아닌 값들)조회는 true/false선택해라- 이렇게만 적으면 될 것을 어휴 씨발.....그리고 뭐 백업도구 어쩌고 이런 필요 이상의 설명은 왜 붙이는데 %%

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

```json
{
  "additionalProperties": false,
  "properties": {
    "phase_id": {
      "default": "",
      "type": "string",
      "description": "Phase를 선택합니다. plan_id와 함께 사용할 수 없습니다."
    },
    "plan_id": {
      "default": "",
      "type": "string",
      "description": "Plan을 선택합니다. phase_id와 함께 사용할 수 없습니다. Step 하나만 읽으려면 step_id를 추가합니다."
    },
    "step_id": {
      "default": "",
      "type": "string",
      "description": "선택 사항인 plan_id 내 Step ID입니다. Plan 요약 대신 해당 Step의 입력/출력 기록을 선택합니다."
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
    "include_holons": {
      "default": false,
      "type": "boolean",
      "description": "Plan의 holon_ids를 포함합니다. Plan 조회에만 유효하며 Phase 또는 Step에는 사용할 수 없습니다."
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
  "type": "object",
  "required": [
  ]
}
```

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "id": "plan_example", // type=plan이면 plan_id. type=phase이면 phase_id, type=step이면 step_id
  "type": "plan",
  "status": "pending", // 선택한 항목의 업무 상태. 조회 실패의 status=error와 구별
  "read_only": false, // 과거 상태이면 true. 메타데이터 이력이지 Rhino 형상 복원본이 아님
  "plan": { // Step 조회에서는 대신 step{plan_id, loop_no, revision, step_type, name, input_refs, output_refs}를 반환
    "title": "예시 계획", // 과거 기록에 title이 없으면 goal에서 도출
    "goal": "예시 목표",
    "scope": "inspection",
    "loop_no": 1, // 저장 상태를 다시 조회할 때 revision과 함께 유지
    "revision": 2, // 최신 상태의 선택적 수정 검사는 expected_revision+loop_no로 전달
    "phase": null, // Phase 연결이 없으면 null. 과거 Phase 이름을 확인할 수 없으면 해당 name도 null
    "depends_on": [], // Plan 참조만 기록. 미생성·자기·순환 참조를 허용하며 실행을 제한하지 않음
    "scene_ids": [], // 설계 맥락. 자동 형상 대상 확장 아님
    "artifact_dir": ".almond/produced/example",
    "loop_artifact_dir": ".almond/produced/example/01",
    "artifact_refs": [],
    "steps": [
      {
        "step_id": "123e4567-e89b-42d3-a456-426614174000", // id와 함께 Step 상세 조회·작업 선택에 사용
        "step_type": "observe",
        "name": "예시 단계",
        "status": "pending",
        "loop_no": 1
      }
    ],
    "available_details": ["include_holons"] // include_holons=true이면 holon_ids를 반환하고 이 목록은 비움
  },
  "next_step": "id와 plan.steps[].step_id로 Step 기록을 조회합니다. …" // 실제 안내 일부. 과거 상태에서 작업할 때는 현재 상태부터 재조회
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 현재 Plan은 Step 상세 조회, `execute_looping`의 회차 시작·재개, `set_working_plan`의 작업 선택으로 이어갑니다. 과거 기록에서 작업으로 전환하려면 현재 상태부터 다시 조회합니다.
코드 1 · 코드 2

## 60. plan-06_list_phases

기준 API: `list_phases`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

프로젝트의 Phase 목록을 조회해 Phase → Plan → Step으로 작업을 탐색합니다. 저장된 구성과 상태를 보여 주며 **설계 완료를 검증하지 않습니다.**

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
  "type": "object",
  "required": [
  ]
}
```

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "phases": [], // 기본 phase_id/name/status/plan_count/depends_on/previous_id. ID는 항상 포함하며 Phase 상세·Plan 목록에 사용
  "total": 0, // 필터에 일치하는 전체 항목 수
  "limit": 50, // 페이지 최대 항목 수
  "truncated": false, // true면 전체 목록이 아님. offset 없이 limit(최대 500)만 지원
  "next_step": "반환된 Phase ID가 없습니다. 이 페이지는 Phase 상세 조회나 Plan 필터에 사용할 대상을 제공하지 않습니다." // 서버가 실제 반환하는 다음 작업 안내. 문서 작성자의 주석이 아님
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: `get_phase_plan_step`으로 Phase 상세를 읽거나 `list_plans`로 해당 Phase의 Plan을 찾습니다.
코드 1 · 코드 2

## 61. plan-07_list_revisions

기준 API: `list_plan_revisions`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

Plan·Loop의 저장 리비전 목록과 변경 작업을 조회합니다. 이력은 Plan 메타데이터와 Step 기록이며, **Rhino 형상 백업이나 모든 스크립트 실행 기록은 아닙니다.**

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "plan_id": "plan_example", // 각 행의 loop_no/revision과 함께 get_phase_plan_step에 사용
  "revisions": [], // loop_no/revision/operation/step_id. step_id=null은 Plan 전체 변경, audit/all이면 created_at 추가
  "total": 0, // 필터에 일치하는 전체 항목 수
  "limit": 50, // 페이지 최대 항목 수
  "truncated": false // Loop·revision 최신순. offset 없음. step_id 필터는 직접 Step 변경만 조회
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: `get_phase_plan_step`으로 선택한 회차·리비전의 Plan 또는 Step 기록을 읽습니다.
코드 1 · 코드 2

## 62. plan-08_list

기준 API: `list_plans`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

프로젝트 또는 특정 Phase·Scene·상태에 해당하는 Plan의 간략한 목록을 조회합니다. 저장된 업무 상태는 **설계 완료의 증명이 아닙니다.**

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "type": "string",
      "description": "선택 사항인 워크플로 상태 필터입니다. 비어 있으면 모든 상태를 포함합니다."
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
  "type": "object",
  "required": [
  ]
}
```

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "plans": [], // plan_id/title/scope/status/loop_no/revision만 요약. ID로 상세 조회하며 goal·Step ID는 상세에서 확인
  "total": 0, // 필터에 일치하는 전체 항목 수
  "limit": 50, // 페이지 최대 항목 수
  "truncated": false, // true면 전체 목록이 아님. offset 없이 필터와 limit으로 좁힘
  "next_step": "이 필터에 일치하는 Plan ID가 없습니다. 더 넓게 검색해야 한다면 list_plans에서 phase_id, scene_id 또는 status를 조정합니다. 상세 조회나 작업 선택에 사용할 대상은 반환되지 않았습니다." // 서버가 실제 반환하는 다음 작업 안내. 문서 작성자의 주석이 아님
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: `get_phase_plan_step`으로 Plan과 Step을 살펴본 뒤, 필요한 작업을 `execute_looping`으로 시작하거나 `set_working_plan`으로 선택합니다.
코드 1 · 코드 2

## 74. plan-09_rename_artifact_folder

기준 API: `rename_artifact_folder`

근거: src/mcp/runtime/mcp_server.py

### DESCRIPTION

Plan이 소유한 산출물 폴더를 이름 변경하거나 이전 위치에서 옮기고 현재 참조를 갱신합니다. **실행된 Loop가 있거나 과거 Loop가 해당 파일을 참조하면 변경하지 않으며**, 기존 대상 폴더를 덮어쓰지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "artifact_dir": ".almond/produced/example-new", // 변경 후 경로 예시. name/artifact_name 입력에는 이 경로를 그대로 쓰지 않음
  "previous_artifact_dir": ".almond/produced/example-old" // 실제 변경일 때만 반환. 현재 파일 참조는 갱신하지만 불변 과거 리비전은 재작성하지 않음
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 갱신된 경로로 산출물 작업을 이어갑니다. 작업 공간을 새로 선택해야 하면 기존 Plan을 `set_working_plan`으로 다시 선택합니다.
코드

## 83. plan-10_set_working

기준 API: `set_working_plan`

근거: src/mcp/runtime/mcp_server.py

### DESCRIPTION

기존 Plan과 선택적인 Step을 이 연결의 산출물 작업 공간으로 선택합니다. 최신 Loop만 선택하며, 새 회차를 시작하거나 Step을 실행·완료하지 않습니다. 다른 연결이 회차를 진행했다면 **다시 선택해야 산출물을 쓸 수 있습니다.** 기존 tmp 계열 Plan 폴더는 `rename_artifact_folder`로 먼저 이전합니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "선택 사항인 Plan 내 Step ID입니다. 비어 있으면 Step 없이 Plan을 선택합니다. 선택해도 실행하거나 완료하지 않습니다."
    },
    "artifact_name": {
      "default": "",
      "type": "string",
      "description": "최초 폴더 이름만 전달하며 절대 경로나 상대 경로는 사용할 수 없습니다. 생략하면 Plan의 goal을 사용합니다. 파일은 .almond/produced/YYMMDD_name 아래에 저장됩니다. 기존 폴더는 재사용합니다."
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

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "plan_id": "plan_example", // Plan ID
  "step_id": "step_example", // 선택한 Step. Step 미선택이면 빈 문자열
  "loop_no": 1, // Loop 회차 번호
  "revision": 2, // 최초 폴더 설정 후의 값. update_plan/update_step 검사에 쓰며 이 선택 도구는 expected_revision 입력을 받지 않음
  "artifact_dir": ".almond/produced/example/01", // 선택 연결의 현재 출력 위치. execute_project_python은 이를 cwd로 사용
  "plan_artifact_dir": ".almond/produced/example" // 공유 Plan 루트. loop_no=0이면 이 루트를 사용하며 폴더는 필요할 때 생성
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 선택한 작업 공간에서 `execute_project_python` 등으로 산출물을 만들고, 수행 결과는 `update_step`으로 기록합니다. 새 회차가 필요하면 `execute_looping`을 사용합니다.
코드

## 87. plan-11_update_phase

기준 API: `update_phase`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

Phase의 이름·설명·상태·파일 연결과 관계를 수정합니다. 의존성은 실행 순서를 강제하지 않으며, 모델 파일을 이동하거나 다른 항목의 상태를 바꾸지 않습니다. 일부 패치 항목이 건너뛰어질 수 있으므로 **적용 결과를 확인**합니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택 사항인 저장할 파일명입니다. project_file_id를 생략한 경우 비어 있으면 연결 관계를 해제합니다."
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
      "description": "project_info(sections=[\"project\"], include_ids=true)에서 얻은 기존 project.files[].project_file_id입니다. file_name도 함께 전달하면 두 값이 일치해야 합니다."
    },
    "status": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택적으로 pending, running, paused, completed, failed 또는 blocked를 사용할 수 있습니다. 생략/null이면 상태를 유지합니다."
    },
    "depends_on": {
      "anyOf": [
        {
          "additionalProperties": false,
          "description": "추가/삭제할 문자열 값입니다. 생략하거나 빈 배열이면 해당 작업을 수행하지 않습니다.",
          "properties": {
            "add": {
              "description": "추가할 문자열 값입니다. 이미 존재하거나 중복되거나 유효하지 않은 항목은 보고하고 건너뜁니다. remove에도 있는 값은 양쪽 작업에서 모두 건너뜁니다.",
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            "remove": {
              "description": "삭제할, 앞서 관찰한 문자열 값입니다. 존재하지 않거나 중복되거나 유효하지 않은 항목은 보고하고 건너뜁니다. 생략하거나 빈 배열이면 변경하지 않습니다.",
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
      "description": "앞선 Phase ID 하나입니다(phase_ 접두사). depends_on 관계와 별개입니다. 갱신 시 생략/null이면 유지하고 빈 문자열이면 지웁니다. 실행을 제한하거나 완료를 요구하지 않고 연속성을 기록합니다."
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

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // issues 없음. partial_success=변경+건너뜀, no_change=건너뜀만 존재
  "changed": true, // 실제 저장 변경 여부. status=success여도 false일 수 있음
  "phase": { // 수정 확인. depends_on은 미생성·자기·순환 Phase 참조도 허용하며 실행을 강제하지 않음
    "phase_id": "phase_example", // Phase ID
    "status": "pending" // Phase 업무 상태
  },
  "issues": [] // 건너뛴 필드/작업/인덱스/값/사유. 잘못된 일반 필드·타입은 요청 전체를 거부
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: `get_phase_plan_step`으로 변경된 Phase를 읽거나 `list_plans`로 그 안의 작업을 이어갑니다.
코드

## 88. plan-12_update

기준 API: `update_plan`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

Plan의 목표·분류·대상·관계·상태와 산출물 참조를 수정합니다. 형상은 바꾸지 않으며 Plan 상태는 Step 상태와 독립적입니다. **Plan 완료는 사용자가 결정**하고, 일부 패치 항목은 건너뛰어질 수 있습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "선택 사항인 오래된 상태 검사이며 새 리비전 번호가 아닙니다. 실행이 시작된 후에는 관찰한 현재 revision과 loop_no를 함께 사용합니다. 일치하지 않으면 변경을 거부합니다. 일반적으로 생략하며, 리비전은 서버가 할당합니다."
    },
    "depends_on": {
      "anyOf": [
        {
          "additionalProperties": false,
          "description": "추가/삭제할 문자열 값입니다. 생략하거나 빈 배열이면 해당 작업을 수행하지 않습니다.",
          "properties": {
            "add": {
              "description": "추가할 문자열 값입니다. 이미 존재하거나 중복되거나 유효하지 않은 항목은 보고하고 건너뜁니다. remove에도 있는 값은 양쪽 작업에서 모두 건너뜁니다.",
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            "remove": {
              "description": "삭제할, 앞서 관찰한 문자열 값입니다. 존재하지 않거나 중복되거나 유효하지 않은 항목은 보고하고 건너뜁니다. 생략하거나 빈 배열이면 변경하지 않습니다.",
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
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택적으로 pending, running, paused, completed, failed 또는 blocked를 사용할 수 있습니다. 생략/null이면 유지합니다."
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
      "description": "앞선 Plan ID 하나입니다(plan_ 접두사). depends_on 관계와 별개입니다. 갱신 시 생략/null이면 유지하고 빈 문자열이면 지웁니다. 실행을 제한하거나 완료를 요구하지 않고 연속성을 기록합니다."
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
      "description": "선택 사항인 현재 Loop 번호 보호 검사입니다. 이전 또는 알 수 없는 Loop는 모두 거부합니다. Plan이 Loop를 실행한 후에는 expected_revision과 함께 필수로 전달해야 합니다."
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

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // issues 없음. partial_success=변경+건너뜀, no_change=건너뜀만 존재
  "changed": true, // 실제 변경일 때만 리비전 하나 생성. success여도 false일 수 있음
  "plan": { // 수정 확인만 반환. depends_on의 미생성·자기·순환 Plan 참조는 허용하나 Phase/Scene/Holon 대상은 검증
    "plan_id": "plan_example", // Plan ID
    "status": "pending", // Plan 업무 상태
    "loop_no": 1, // Loop 회차 번호
    "revision": 2 // 다음 수정의 선택적 expected_revision 값. loop_no도 함께 사용
  },
  "issues": [] // 건너뛴 필드/작업/인덱스/값/사유. 잘못된 일반 필드·대상·가드·타입은 요청 전체 거부
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: `get_phase_plan_step`으로 변경된 작업을 확인합니다. Holon 대상을 바꿨다면 `resolve_targets`로 대상을 확인하고, Step 기록은 `update_step`에서 관리합니다.
코드

## 89. plan-13_update_step

기준 API: `update_step`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

Plan의 Step 상태와 입력·출력 근거를 기록합니다. 근거 문자열을 검증하거나 작업을 실행하지 않으며 **Plan 상태도 바꾸지 않습니다.** 패치가 일부만 적용될 수 있으므로 적용 여부와 건너뛴 항목을 확인합니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "default": null,
      "description": "선택적으로 pending, running, paused, completed, failed 또는 blocked를 사용할 수 있습니다. 생략/null이면 유지합니다. Plan 상태는 변경하지 않습니다."
    },
    "input_refs": {
      "anyOf": [
        {
          "additionalProperties": false,
          "description": "추가/삭제할 문자열 값입니다. 생략하거나 빈 배열이면 해당 작업을 수행하지 않습니다.",
          "properties": {
            "add": {
              "description": "추가할 문자열 값입니다. 이미 존재하거나 중복되거나 유효하지 않은 항목은 보고하고 건너뜁니다. remove에도 있는 값은 양쪽 작업에서 모두 건너뜁니다.",
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            "remove": {
              "description": "삭제할, 앞서 관찰한 문자열 값입니다. 존재하지 않거나 중복되거나 유효하지 않은 항목은 보고하고 건너뜁니다. 생략하거나 빈 배열이면 변경하지 않습니다.",
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
          "description": "추가/삭제할 문자열 값입니다. 생략하거나 빈 배열이면 해당 작업을 수행하지 않습니다.",
          "properties": {
            "add": {
              "description": "추가할 문자열 값입니다. 이미 존재하거나 중복되거나 유효하지 않은 항목은 보고하고 건너뜁니다. remove에도 있는 값은 양쪽 작업에서 모두 건너뜁니다.",
              "items": {
                "type": "string"
              },
              "type": "array"
            },
            "remove": {
              "description": "삭제할, 앞서 관찰한 문자열 값입니다. 존재하지 않거나 중복되거나 유효하지 않은 항목은 보고하고 건너뜁니다. 생략하거나 빈 배열이면 변경하지 않습니다.",
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
      "description": "선택 사항인 오래된 상태 검사이며 새 리비전 번호가 아닙니다. 실행이 시작된 후에는 관찰한 현재 revision과 loop_no를 함께 사용합니다. 일치하지 않으면 변경을 거부합니다. 일반적으로 생략하며, 리비전은 서버가 할당합니다."
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
      "description": "선택 사항인 현재 Loop 번호 보호 검사입니다. 이전 또는 알 수 없는 Loop는 모두 거부합니다. Plan이 Loop를 실행한 후에는 expected_revision과 함께 필수로 전달해야 합니다."
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

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // issues 없음. partial_success=변경+건너뜀, no_change=건너뜀만 존재
  "changed": true, // 실제 변경일 때만 Plan 리비전 하나 생성. success여도 false일 수 있음
  "plan": { // Plan 확인 또는 상세 객체
    "plan_id": "plan_example", // Plan ID
    "status": "pending", // Plan 업무 상태
    "loop_no": 1, // Loop 회차 번호
    "revision": 2 // 다음 수정의 선택적 expected_revision 값. loop_no도 함께 사용
  },
  "issues": [], // 건너뛴 필드/작업/인덱스/값/사유. refs 전체는 반환하지 않으므로 필요하면 Step 상세 조회
  "step": { // Step 상세 또는 갱신 확인 객체
    "step_id": "step_example", // Step ID
    "status": "pending", // Step 업무 상태
    "loop_no": 1 // Loop 회차 번호
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: `get_phase_plan_step`으로 Step 기록을 확인하고, 다음 작업은 `set_working_plan`으로 선택합니다. 새 회차는 `execute_looping`으로 시작합니다.
코드

# Inspect

Rhino 문서·객체·선택 조회 · prefix: `inspect-NN_` · 유형 내 순번 01–05

## 06. inspect-01_analyze_nested_blocks

기준 API: `analyze_block_reculviely`

근거: src/mcp/features/context/tools.py

### DESCRIPTION

중첩 블록 구조와 특정 배치 경로의 공유 정의 영향을 읽습니다. 블록 내부를 편집하기 전에는 영향 범위와 실제 편집기 상태를 확인합니다. **정의 구성원 ID나 후보 ID는 독립 편집 대상·편집기 소유 증거가 아니며**, 불완전한 관찰을 전체 영향으로 단정하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "outline의 경우 ids(루트 GUID 배열) 또는 path(한 배치 인스턴스의 GUID 배열)를 사용하며 둘을 함께 사용할 수 없습니다. 둘 다 없으면 scope=selected(기본값), viewport 또는 document를 사용합니다. depth=0..64(기본값 64, 루트=0)이며, max_items=1..5000(기본값 200)은 방문 수도 제한합니다. max_bytes=2048..262144(기본값 48000)입니다. 선택 사항인 field_groups는 summary, objects, annotations, transforms로 구성된 비어 있지 않은 배열입니다. 생략하면 기존 상세 플래그를 전달하지 않은 한 summary가 기본값입니다. include_geometry와 annotations는 해당 상세 정보를 제어하는 선택 사항인 불리언입니다. annotation_layer는 레이어 경로/이름으로 텍스트 도트를 필터링합니다. 결과가 잘리면 ids/path/depth의 범위를 좁힙니다. resolve-block은 path만 받으며, 최상위 인스턴스에서 내부 방향으로 이어지는 GUID 1..65개를 전달합니다. 마지막 GUID는 배치 인스턴스이며 정의 ID가 아닙니다. 반환되는 definition_impact는 방문 100000회/깊이 64 이내에서 배치 인스턴스를 스캔하고 최대 512개의 경로와 포함 관계를 나열합니다."
    },
    "expected_model_path": {
      "default": "",
      "type": "string",
      "description": "일반적으로 생략합니다. 런타임이 연결된 문서 경로를 제공합니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "필요할 때 ID를 포함합니다. 전달한 대상 ID는 반복해서 표시하지 않습니다."
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

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success",
  "mode": "outline",
  "document": {
    "units": "Millimeters",
    "absolute_tolerance": 0.01
  },
  "data": { // outline 예시. resolve-block의 definition_impact는 공유 배치 영향이며 complete=false/null 개수는 미확정; 목록만 잘려도 집계는 완전할 수 있음
    "records": [ // 기본은 요약. 이 예시는 include_ids=true와 options.field_groups=["objects"]를 요청한 경우
      {
        "kind": "occurrence",
        "id": "123e4567-e89b-42d3-a456-426614174000",
        "type": "InstanceReference",
        "path": ["123e4567-e89b-42d3-a456-426614174000"], // 블록 배치이면 resolve-block의 options.path에 사용. 그 결과의 정의 ID/candidate_object_ids는 독립 편집 ID가 아님
        "definition": "예시 블록"
      }
    ],
    "items": 1,
    "truncated": false // 예산·순회 제한이면 ids/path/depth를 좁힘. 요청·응답 각각 UTF-8 JSON 256 KiB 제한
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: outline에서 찾은 블록 배치는 resolve-block으로 영향을 확인합니다. 의도한 BlockEditNew 진입 후에는 `get_objects`로 현재 작업 ID를 새로 얻어 관찰·캡처합니다.
코드 1 · 코드 2 · 코드 3

## 39. inspect-02_get_objects

기준 API: `get_objects`

근거: src/mcp/features/context/tools.py

### DESCRIPTION

Rhino 객체의 실제 속성·그룹·블록 계층·Brep 면을 변경 없이 관찰합니다. 편집기에 진입하거나 확정·취소한 뒤에는 **ID와 CRC를 새로 확인**합니다. 정의 구성원이나 관찰 가능한 편집기 작업 ID가 모든 변경 도구의 대상인 것은 아니며, 현재 면·교차 수정은 편집기 밖에서 다시 관찰한 문서 객체를 사용합니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "객체/그룹/배치 인스턴스 식별 정보를 포함합니다. 기본값은 false입니다. id 또는 faces 필드를 명시하면 식별 정보도 활성화됩니다."
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
  "type": "object",
  "required": [
  ]
}
```

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success",
  "scope": "document", // 스캔·순회 최대 100000개, JSON 256 KiB. inside_window는 바운딩 박스 교차이며 가림·클리핑 증명이 아님
  "objects": [ // objects 모드의 faces 요청 예시. hierarchy는 nodes의 document_object/root_object_id/block_path_ids로 문서 객체와 정의 배치를 구별
    {
      "id": "123e4567-e89b-42d3-a456-426614174000", // include_ids 또는 fields의 id/faces로 유지. 현재 문서 객체라면 교차 검사·캡처에 사용
      "geometry_crc": 123456789, // 관찰 버전 예시. 면 수정의 expected_geometry_crc 또는 면 페이징 CRC 맵에 사용
      "face_count": 6,
      "faces": [
        {
          "face_index": 0, // 이 id·CRC와 함께 edit_planar_face의 object_id/face_index/expected_geometry_crc로 전달
          "planar": true,
          "face_edit_supported": true // 기본 면 적격성. 편집기 내부 변경 지원이나 최종 변경 허가를 뜻하지 않음
        }
      ],
      "faces_truncated": true,
      "face_page": {
        "offset": 0,
        "limit": 1,
        "returned": 1,
        "next_offset": 1, // 다음 face_offset. document object_ids와 모든 대상의 {ID: CRC}를 함께 전달
        "complete": false
      }
    }
  ],
  "matched_count": 1,
  "offset": 0,
  "limit": 50,
  "next_offset": null, // 객체 페이지가 더 있으면 다음 offset으로 사용
  "snapshot": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", // 예시 토큰. 후속 offset 페이지의 expected_snapshot에 그대로 전달
  "editing": {}, // 실제 상세는 생략. 편집기 current_save_target은 원래 영구 그룹 GUID 증명이 아니며 불완전 구성원 관계는 보증하지 않음
  "complete": true // 객체 페이지 완료일 뿐. hierarchy의 children_state가 collapsed/depth_limit/cycle/unavailable이면 그 하위까지 보증하지 않음
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 관찰한 문서 객체로 교차 검사·검토 캡처를 이어가고, 블록은 `analyze_block_reculviely`로 영향을 확인합니다. 면 수정이 필요하면 같은 관찰의 면·CRC를 `edit_planar_face` 또는 `edit_planar_faces`에 사용합니다.
코드 1 · 코드 2 · 코드 3 · 코드 4

## 44. inspect-03_get_document_context

기준 API: `get_rhino_context`

근거: src/mcp/features/context/tools.py

### DESCRIPTION

현재 Rhino 문서의 속성, 편집 상태와 사용 가능한 뷰·디스플레이 모드를 **필요한 범위만 읽습니다**. 관찰 불가 값은 경고와 함께 null로 반환하며, 객체 형상이나 화면의 실제 가시성을 검증하지는 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "선택 사항인 섹션 이름 목록입니다. 생략하면 document, named_views, layouts 및 display_modes를 요청합니다."
    },
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "항상 식별 정보가 제공되는 Named View/Layout/Display Mode 목록 외의 식별 정보도 포함합니다."
    },
    "include_editor_details": {
      "default": false,
      "type": "boolean",
      "description": "editor를 요청한 경우에만 provider/command/Undo 근거를 포함합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- sections는 document, viewport, editor, named_views, layouts, display_modes, viewports 중 선택합니다. 생략하면 document/named_views/layouts/display_modes를, []이면 status/warnings만 반환합니다. editor 상세는 editor 섹션과 include_editor_details=true를 함께 요청합니다.
- Bridge context_sections>=2가 필요합니다. 이미 알고 있는 최신 문서 정보는 재사용합니다.
- named_views/layouts/display_modes의 ID는 include_ids=false여도 반환합니다. model_view_id에 쓸 viewports ID는 include_ids=true로 요청합니다. editor 기본은 mode/target/stable/warnings이며 stable은 검증된 일반 모델을 뜻합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "warnings": [], // 관찰할 수 없는 값·목록 제한 등의 경고. display_modes는 최대 128개
  "document": { // 요청한 문서 속성. 관찰 불가 값은 null이며 document 요청이 editor 관찰을 뜻하지 않음
    "units": "Millimeters", // 문서 길이 단위
    "absolute_tolerance": 0.01, // 문서 길이 단위의 절대 허용오차
    "modified": false, // 문서 수정 플래그
    "object_count": 0, // 객체 수
    "layer_count": 1, // 레이어 수
    "angle_tolerance": 0.0174532925199433 // 라디안 단위의 각도 허용오차
  },
  "next_step": "현재 화면을 보려면 get_current_viewcapture를 사용하세요." // sections를 생략했을 때만 서버가 실제 반환하는 안내
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 저장된 뷰·Layout 캡처는 `get_defined_viewcapture`, 여러 시점 비교는 `capture_rhino_inspection`을 사용합니다. 현재 화면은 `get_current_viewcapture`, 선택 객체는 `get_objects`로 확인합니다.
코드

## 47. inspect-04_get_selection_references

기준 API: `get_selection_references`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

현재 Rhino 선택 객체와 그 상위 Holon을 참조하는 저장된 Plan을 찾습니다. 객체 소유 관계는 현재 상태로 확인하지만 **Plan 관계는 저장 정보**이며, Step별 편집 대상이나 편집 승인을 뜻하지 않습니다. 저장된 문서와 검증 가능한 일반 모델 컨텍스트가 필요합니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- 열려 있는 저장 문서가 필요합니다. 그룹·블록 편집 중에는 영속 Holon 소유 관계를 확인할 수 없어 오류가 반환되며, 빈 참조 목록을 뜻하지 않습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "objects": [], // 선택 객체의 object_id/registered와 존재할 때 holon_id. 핸들은 별도 include_ids 없이 유지
  "holons": [], // 선택 객체 소유 Holon과 상위 Holon 요약. 기본 holon_id/name
  "plans": [], // 참조 Plan 요약. 기본 plan_id/title이며 steps·references 상세는 field_groups로 선택
  "total_plans": 0, // 참조 Plan 전체 개수
  "truncated": false, // 현재 응답에서 결과가 잘렸는지 여부
  "ownership_live_verified": false, // 선택 객체 소유 관계의 현재 확인 여부. 선택이 없으면 false
  "references_live_verified": false, // false: Plan·계층 참조는 저장 정보이며 현재 형상 검증이 아님
  "selection_total": 0, // 선택된 객체 전체 수
  "selection_truncated": false // 선택 조회의 일부가 생략되었는지 여부. Plan 목록의 truncated와 별개
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 관련 Plan과 Step 기록은 `get_phase_plan_step`, 등록된 대상 집합은 `resolve_targets`로 이어서 확인합니다.
코드 1 · 코드 2

## 76. inspect-05_resolve_targets

기준 API: `resolve_targets`

근거: src/mcp/features/planning/tools.py

### DESCRIPTION

Plan에 명시적으로 등록된 Holon 대상 집합을 읽습니다. **빈 대상은 그대로 유지**하고 Scene이나 Step으로 확장하지 않습니다. 저장된 식별 정보이며 현재 구성원·형상이나 편집 권한을 검증하지는 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "required": [
    "plan_id"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- Scene은 대상 집합을 확장하지 않으며 Step은 별도 Holon 대상을 소유하지 않습니다. 수정 보호값으로 revision을 쓸 때 실행된 Plan은 현재 loop_no도 필요합니다. 이 조회만으로 loop_no를 얻을 수는 없습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "plan_id": "plan_example", // Plan ID
  "step_id": null, // Step ID
  "revision": 1, // Plan revision. 실행된 Plan의 변경 guard에는 별도로 현재 loop_no도 필요
  "scene_ids": [], // Plan의 Scene 컨텍스트. 이 목록으로 Holon 대상을 확장하지 않음
  "holon_ids": [], // Plan에 명시한 Holon 대상. 빈 배열은 빈 대상으로 유지
  "holons": [], // 저장된 대상 요약. 기본 holon_id/name, 관계·모델 정보는 선택 그룹에 따름
  "live_verified": false, // false: 저장 식별 정보이며 현재 구성원 검증이 아님
  "source": "plan" // 항상 plan. Step을 지정해도 별도 대상 집합으로 바뀌지 않음
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 대상의 현재 구성원은 `get_ontological_holon`, 실제 선택·격리·확대는 `focus_holons`로 이어갑니다.
코드 1 · 코드 2

# Capture

화면 캡처·시각 검토 · prefix: `capture-NN_` · 유형 내 순번 01–04

## 10. capture-01_conditioning_pass

기준 API: `capture_conditioning_pass`

근거: src/mcp/features/capture/tools.py

### DESCRIPTION

Rhino 카메라 경로를 따라 RGB·에지·깊이 조건 프레임과 카메라 기록을 생성합니다. 활성 카메라·디스플레이를 변경하고 **출력 파일을 쓰거나 덮어쓰며**, 카메라 복원은 보장되지 않습니다. AI 영상 생성이 아니며 깊이는 실제 거리값이 아닌 8비트 회색조입니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

```json
{
  "additionalProperties": false,
  "properties": {
    "shot": {
      "type": "string",
      "description": "orbit, track 또는 keyframes 샷을 설명하는 JSON 문자열입니다. 좌표에는 문서 단위를, 렌즈 값에는 밀리미터를 사용합니다. 이 도구 설명의 shot 예시를 참고합니다."
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
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "required": [
    "shot"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- shot은 JSON 문자열입니다. type=orbit은 center/radius/height, type=track은 cam0/cam1/target0/target1, type=keyframes는 keyframes 배열의 camera/target을 받습니다. frames 기본값은 81, lens 기본값은 35이며 keyframes에서는 각 항목에 lens를 둡니다. 좌표·반경·높이는 문서 단위, lens는 mm입니다.
- 관리형 실행은 선택한 Plan의 현재 산출물 폴더를 사용합니다. 같은 출력 이름은 덮어쓸 수 있습니다. camera.json의 lens_mm를 shot에 재사용하려면 lens로 바꿉니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 캡처 청크 오류가 없으면 success, 일부 실패하면 partial. 개별 파일 완성 보장은 아님
  "frames_requested": 2, // 요청 프레임 수
  "frames_captured": 2, // 성공한 스크립트 청크의 프레임 수. 모든 PNG를 독립 검증한 수가 아님
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
    "rgb": null // RGB 영상 경로. 이 예시는 영상 조립이 되지 않은 경우
  },
  "document": {} // 원본 문서·단위·뷰·경계 정보. 깊이는 거리값이 아닌 8비트 회색조, 기본 가까울수록 밝음
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 완성된 프레임과 카메라 기록을 확인한 뒤 `update_step`으로 산출물 참조를 남기거나 `execute_project_python`으로 후처리합니다.
코드

## 11. capture-02_inspection

기준 API: `capture_rhino_inspection`

근거: src/mcp/features/context/tools.py

### DESCRIPTION

**작업 화면을 바꾸지 않고** 여러 시점·객체 범위를 하나의 PNG로 비교합니다. 이미지 파일은 추가로 저장하지만 카메라·선택·가시성·모델 내용은 유지합니다. 명시적 객체 필터는 블록 인스턴스·내부 객체를 지원하지 않으며, 캡처 범위 충족이 픽셀 노출이나 설계 정확성을 보장하지는 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "required": [
    "views"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- Bridge inspection_capture=1이 필요하며 공통 범위·모델 뷰·편집 컨텍스트에는 각각 해당 capability가 필요합니다. 알 수 없거나 전환 중인 편집 컨텍스트는 거부됩니다.
- PNG는 결합 16M픽셀/4 MiB, 요청은 256 KiB로 제한됩니다. Layout이 활성화되었으면 model_view_id로 모델 뷰를 지정하거나 용지는 `get_defined_viewcapture`로 캡처합니다.
- 비어 있지 않은 타일 object_ids와 공통 object_ids는 함께 쓰지 않습니다. 편집기가 숨긴 외부 객체는 자동으로 표시하지 않습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 캡처 상태. PNG 이미지도 별도로 함께 반환
  "complete": true, // 요청한 모든 타일 캡처 여부. 실제 픽셀 노출·설계 정확성의 증거가 아님
  "tiles": [ // 타일별 결과와 scope. scope.complete는 문서 가시 범위 충족이며 부분 성공 때 오류 타일도 보존. 공통 범위는 shared_scope_ref로 참조하며 타일 GUID 목록은 최대 512개
    {
      "index": 0, // 0부터 시작하는 항목 인덱스
      "status": "success", // 타일 캡처 상태
      "direction": "top" // 캡처 시점. 편집 컨텍스트·복원 확인 결과는 반환된 메타데이터에 보존
    }
  ],
  "image_file": { // PNG 파일 저장 결과. 이미지 전달과 별개이며 저장 실패여도 이미지가 제공될 수 있음
    "status": "saved", // saved이면 path를 사용. error이면 파일 저장 실패이며 유효 경로가 없음
    "path": ".almond/produced/example/captures/example.png", // 프로젝트 기준 PNG 상대 경로. output_refs에 기록할 때는 이 문자열만 사용
    "lifetime": "plan", // plan은 Plan 산출물, connection은 연결 정리까지의 임시 파일
    "bytes": 12345, // 파일 바이트 수
    "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" // 파일 해시. 예시 값은 가상
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 추가 형상 확인은 `get_objects`, Layout 용지 캡처는 `get_defined_viewcapture`를 사용합니다. 보관할 이미지는 `update_step`으로 산출물에 연결합니다.
코드 1 · 코드 2

## 28. capture-03_current_view

기준 API: `get_current_viewcapture`

근거: src/mcp/features/context/tools.py

### DESCRIPTION

현재 모델 화면을 캡처합니다. 대상을 지정하면 실제 선택·카메라를 바꾸고 선택적으로 격리하며, 디스플레이 모드 재정의도 **화면에 남습니다**. 캡처 실패 후에도 적용되거나 불확실한 화면 변경은 되돌리지 않으므로 자동 재시도하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- 모델 뷰의 현재 선택 가능한 최상위 객체만 대상으로 삼습니다. 숨김·잠금을 자동 해제하지 않으며 확인된 대상은 최대 4096개입니다. Layout 용지는 `get_defined_viewcapture`를 사용합니다.
- Bridge view_capture=1과 지원되는 래스터 모드가 필요합니다. PNG는 16M픽셀/4 MiB, 레이블은 최대 200개입니다. 기본 Isolate는 잠긴 주변 객체를 남길 수 있습니다.
- include_usage=true는 실제 이미지 치수와 예시 픽셀 토큰 추정치를 별도 텍스트로 추가합니다. 측정된 사용량이 아니며 기본 structured JSON 필드로 가정하지 않습니다. 3DM은 저장하지 않습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "image_file": { // PNG 파일 저장 결과. 이미지 전달과 별개이며 저장 실패여도 이미지가 제공될 수 있음. 화면 변경은 별도 view_change/mutation_applied/requires_reconciliation에 보존
    "status": "saved", // saved이면 path를 사용. error이면 파일 저장 실패이며 유효 경로가 없음
    "path": ".almond/produced/example/captures/example.png", // 프로젝트 기준 PNG 상대 경로. output_refs에 기록할 때는 이 문자열만 사용
    "lifetime": "plan", // plan은 Plan 산출물, connection은 연결 정리까지의 임시 파일
    "bytes": 12345, // 파일 바이트 수
    "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" // 파일 해시. 예시 값은 가상
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 화면을 바꾸지 않는 다중 시점 비교는 `capture_rhino_inspection`, Named View·Layout 캡처는 `get_defined_viewcapture`를 사용합니다. 보관할 이미지는 `update_step`으로 산출물에 연결합니다.
코드 1 · 코드 2

## 29. capture-04_defined_view

기준 API: `get_defined_viewcapture`

근거: src/mcp/features/context/tools.py

### DESCRIPTION

저장된 Named View 또는 Layout 용지를 **활성화하지 않고** 캡처합니다. 작업 카메라·선택·가시성·모델을 유지하며 PNG 파일만 추가 저장합니다. Layout은 각 Detail의 기존 디스플레이 모드와 실제 용지 비율을 유지합니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "required": [
    "target_kind",
    "target"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- Bridge view_capture=1과 지원되는 래스터 모드가 필요합니다. Named View에 display_mode를 생략하면 저장 모드와 무관하게 Shaded를 사용합니다.
- Layout은 디스플레이 모드·명시적 픽셀 크기 재정의를 받지 않습니다. 오버레이는 최대 200개이고 Layout Detail 레이블은 지원하지 않습니다.
- Layout은 100% 기준 144 dpi와 실제 용지 비율로 렌더링합니다. 백분율 캡처는 16M픽셀/4 MiB 예산에 맞춰 축소될 수 있지만 명시적인 Named View 픽셀 크기는 알리지 않고 변경하지 않습니다.
- include_usage=true는 실제 치수와 예시 픽셀 토큰 추정치를 별도 텍스트로 추가합니다. 측정된 사용량이 아닙니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "image_file": { // PNG 파일 저장 결과. 이미지 전달과 별개이며 저장 실패여도 이미지가 제공될 수 있음. 백분율 캡처는 예산 내 축소되며 경고·실제 치수를 확인
    "status": "saved", // saved이면 path를 사용. error이면 파일 저장 실패이며 유효 경로가 없음
    "path": ".almond/produced/example/captures/example.png", // 프로젝트 기준 PNG 상대 경로. output_refs에 기록할 때는 이 문자열만 사용
    "lifetime": "plan", // plan은 Plan 산출물, connection은 연결 정리까지의 임시 파일
    "bytes": 12345, // 파일 바이트 수
    "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" // 파일 해시. 예시 값은 가상
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 다른 시점·객체 범위를 함께 비교하려면 `capture_rhino_inspection`을 사용합니다. 보관할 이미지는 `update_step`으로 산출물에 연결합니다.
코드 1 · 코드 2

# Model

모델링 설정·재료·형상 편집 · prefix: `model-NN_` · 유형 내 순번 01–05

## 08. model-01_assign_material

기준 API: `assign_material`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

현재 Rhino 객체의 레이어를 유지하면서 라이브러리 PBR 재료를 적용합니다. 메타데이터는 **명시적으로 요청한 경우에만** 추가하며, 지정하지 않은 속성은 유지합니다. 일부 적용이나 결과 불확실성을 확인한 뒤 후속 작업을 진행하고, 이 호출을 전체 모델링 설정이나 문서 저장으로 해석하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "선택 사항인 구축 시스템 레이블이며, attach_metadata와 함께 사용합니다."
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
      "description": "선택 사항인 출처 참조 객체이며, attach_metadata와 함께 사용합니다. 생략하면 참조를 추가하지 않습니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "required": [
    "guids",
    "material_id"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- construction_reference는 {"kind":"construction_system","id":"확인된 system_id"}를 받습니다. construction_system도 알려진 시스템 ID여야 하며 둘을 함께 주면 같은 시스템이어야 합니다. 상세 레이블을 생략하면 시스템 이름을 사용합니다.
- attach_metadata는 명시적인 메타데이터 요청에만 사용합니다. 메타데이터 전용 호출에도 알려진 material_id가 필요하며, 지정하지 않은 속성은 유지합니다.
- Bridge modeling_materials=2가 필요합니다. `setup_modeling`을 먼저 실행할 필요는 없습니다. 블록 인스턴스 재료는 ByParent인 정의 형상에 영향을 주며 메타데이터는 인스턴스에 붙습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 처리 결과. 통상적이지 않은 시스템 재료는 warnings를 남기고 적용하며 result_error/unknown은 재확인 필요
  "material_id": "example-material", // 라이브러리 재료 ID
  "applied_count": 1, // 처리 성공한 객체 수. requested_count와 비교하며 실제 변경 수와 구분
  "requested_count": 1, // 요청한 수
  "render_material_applied": true, // 렌더 재료 적용을 요청한 모드. 객체 레이어는 변경하지 않음
  "material_metadata_attached": false, // 재료 메타데이터가 부착됐는지 여부
  "rhino_material_name": "예시 재료", // Rhino에 적용한 재료명
  "ue_material_slot": "example-slot", // 재료 슬롯명
  "applied_guids": [ // 처리 성공한 GUID. 선택적 changed_guids/changed_count는 확인된 실제 변경 집합
    "00000000-0000-0000-0000-000000000001"
  ],
  "metadata_attached": false, // 요청한 메타데이터 적용 여부. 지정하지 않은 속성·출처는 유지
  "layer_path": "Example layer" // 네이티브가 제공한 레이어 정보 또는 null. 새 레이어로 옮겼다는 뜻이 아님
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 적용된 객체는 `get_objects`로 확인하고, 교환용 파일이 필요하면 `export_asset_contract`로 내보냅니다.
코드

## 16. model-02_edit_planar_face

기준 API: `edit_planar_face`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

잠기지 않은 최상위 닫힌 Brep의 평면 한 면을 PushPull Extend로 늘리거나 줄입니다. 선택한 면과 인접 면이 평면인 일반 모델만 지원하며, **그룹·블록 편집 중에는 사용할 수 없습니다**. 속성·그룹과 지원되는 형상 메타데이터를 유지하고, 불확실한 실행을 자동 재시도하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
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

**입력 보충 설명(문서용)**

- face_index와 expected_geometry_crc는 같은 현재 `get_objects` 관찰에서 가져옵니다. 잠기지 않은 최상위 닫힌 Brep만 지원하며 선택·인접 면이 평면이어야 합니다. Extrusion 변환과 블록 내부는 지원하지 않습니다.
- Bridge face_edit>=1·Rhino 8.16+가 필요합니다. 검증할 수 없는 사용자 정의 형상 데이터는 거부하며, 교체본의 유효성·닫힘·다양체·방향·양의 유한 체적을 확인합니다.
- 객체 속성·그룹·형상 UserStrings와 UserDictionary는 보존합니다. 이 편집은 구축·여유 공간 검증이나 3DM 저장이 아닙니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "result": { // 확인된 단일 면 편집 결과. 사용자 스크립트의 임의 결과가 아님
    "edited": true, // true와 대상 ID·이전 CRC 일치 및 새 CRC가 확인되어야 성공
    "object_id": "00000000-0000-0000-0000-000000000001", // Rhino 객체 GUID
    "previous_geometry_crc": 123, // 편집 전 형상 CRC
    "geometry_crc": 456 // 편집 후 CRC. 면 인덱스도 바뀔 수 있어 추가 면 편집 전 새 faces 관찰 필요
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 추가 면 편집 전에는 `get_objects`로 바뀐 면과 CRC를 다시 관찰합니다. 시각적 검토는 `capture_rhino_inspection`, 요청된 영구 저장은 `save_rhino_document`로 이어갑니다.
코드 1 · 코드 2

## 17. model-03_edit_planar_faces

기준 API: `edit_planar_faces`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

서로 다른 닫힌 Brep의 평면 한 면씩을 단일 호출·Undo 기록으로 늘리거나 줄입니다. 모든 교체본을 먼저 검증하지만 교체 중 실패한 배치는 **자동 롤백되지 않으며**, 부분 적용·불확실한 배치를 통째로 다시 실행하지 않습니다. 단일 면 편집과 같은 대상·보존 규칙을 따릅니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "required": [
    "edits"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- 각 edits 항목의 면과 CRC는 그 객체의 같은 현재 관찰에서 가져옵니다. 객체별 한 면만 허용하며 `edit_planar_face`의 대상·보존 조건을 따릅니다. Bridge face_edit_batch>=1이 필요합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 실행 상태 및 result 안의 배치 처리 상태
  "result": { // 배치 결과. 준비 실패는 교체 전이며 교체 중 실패는 부분 적용일 수 있음
    "status": "success", // 배치 상태. 외부 status와 항목별 상태를 함께 확인
    "complete": true, // 모든 항목 적용이 확인되었는지 여부
    "requested_count": 1, // 요청한 수
    "applied_count": 1, // 실제 적용된 수
    "mutation_state": "applied", // not_started/applied/partial/unknown 등. partial·unknown은 전체 배치 재실행 금지
    "items": [ // 입력 순서의 항목별 결과. applied/rejected/failed/unknown/not_attempted와 stage/message 등을 보존
      {
        "status": "applied", // 항목별 적용 상태
        "edited": true, // 형상 편집 적용 여부
        "previous_geometry_crc": 123, // 편집 전 형상 CRC
        "geometry_crc": 456 // 변경 후 CRC. 다음 면 편집 전 면 인덱스를 다시 관찰
      }
    ]
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 추가 면 편집 전에는 `get_objects`로 바뀐 면과 CRC를 다시 관찰합니다. 시각적 검토는 `capture_rhino_inspection`, 요청된 영구 저장은 `save_rhino_document`로 이어갑니다.
코드 1 · 코드 2

## 58. model-04_list_materials

기준 API: `list_materials`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

할당이나 응용 프로그램 간 재료 매핑에 사용할 라이브러리 PBR 재료를 찾습니다. Rhino 문서는 변경하지 않으며, 조회 결과가 재료의 **설치·적용 상태를 뜻하지는 않습니다**.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청한 출력에 식별 필드를 포함합니다. false이면 보조 ID를 생략합니다. 후속 도구에서 반환된 ID가 필요하면 true를 요청합니다. 추가 상세 그룹이 선택되는 것은 아닙니다."
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
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "total": 1, // 필터에 일치하는 라이브러리 재료 수. 정상 응답에 별도 status 키는 없음
  "materials": [ // 기본 name/category. include_ids=true이면 material_id, display 그룹이면 PBR·ue_material_slot 등
    {
      "name": "예시 재료", // 저장된 이름
      "category": "wood" // 분류
    }
  ]
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 선택한 재료는 `assign_material`로 Rhino 객체에 적용하거나 `get_blender_helper_script`로 Blender 적용 스크립트를 준비합니다.
코드 1 · 코드 2

## 84. model-05_setup

기준 API: `setup_modeling`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

사전 정의된 Material과 구축 Layer를 현재 Rhino 문서에 함께 등록·정렬합니다. 객체의 레이어·ByLayer 설정·메타데이터는 바꾸지 않으며, 다른 모델링이나 재료 할당의 필수 선행 작업은 아닙니다. incomplete·오류여도 **일부 항목은 이미 생성·변경되었을 수 있습니다**.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "required": [
    "overwrite"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- Bridge modeling_materials=2·modeling_setup=1이 필요합니다. overwrite는 Material과 Layer 모두에 적용하며 기존 프로젝트 설정을 고려해 선택합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 일치하면 success. differences/errors가 남으면 incomplete와 applied=false
  "applied": true // 모든 지정 속성이 일치하는지 여부. false여도 누락 항목 생성·일부 변경이 있었을 수 있음
}
```

코드

# Script

스크립트 실행·결과 확인·저장 · prefix: `script-NN_` · 유형 내 순번 01–04

## 19. script-01_run_project_python

기준 API: `execute_project_python`

근거: src/mcp/runtime/mcp_server.py

### DESCRIPTION

선택한 Plan의 현재 산출물 폴더에서 연결된 Rhino의 Python 3 코드를 실행합니다. Rhino 내장 실행 환경이며 작업자 venv나 파일 쓰기를 차단하는 OS 샌드박스가 아닙니다. 문서 전환·백그라운드 쓰기를 만들지 말고, 시간 초과나 불확실한 결과는 동일 요청으로 확인하며 **코드를 재실행하지 않습니다**.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

```json
{
  "additionalProperties": false,
  "properties": {
    "code": {
      "type": "string",
      "description": "동기식 Python 3 소스입니다. JSON으로 안전하게 표현할 수 있는 값을 result에 할당합니다."
    },
    "timeout_seconds": {
      "default": 60,
      "type": "integer",
      "description": "1-600의 정수이며 기본값은 60입니다. 대기 시간 제한이며, 실행을 취소하지 않습니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "required": [
    "code"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- `set_working_plan`으로 선택한 현재 Plan/Loop를 사용합니다. 기존 유효 선택은 재사용하며 상대 경로의 수정 결과는 현재 산출물 폴더에 씁니다. 이전 Loop 폴더는 입력으로만 사용합니다.
- doc와 scriptcontext.doc는 연결된 RhinoDoc입니다. JSON-safe 값을 result에 할당합니다. 없는 Rhino 내장 패키지를 자동 설치하지 않습니다.
- Rhino 스크립트 작성 참고는 `get_policy`(policy="rhino_scripting")에서 얻습니다. 래퍼는 임시 cwd·환경·scriptcontext·Undo·다시 그리기를 관리하지만 설계 정확성·부분 변경 롤백·문서 저장을 보장하지 않습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "completed": true, // Rhino 실행 완료 확인. timeout·CLI 종료만으로 true라고 판단하지 않음
  "request_id": "00000000000000000000000000000001", // 미완료·불확실성·결과 페이지를 get_rhino_execution으로 회수할 정확한 ID
  "artifact_dir": ".almond/produced/example/01" // 선택한 현재 Plan/Loop의 상대 산출물 폴더. 반환 result 구조는 실행 코드가 결정
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 미완료·불확실한 실행이나 추가 결과·로그는 `get_rhino_execution`으로 확인합니다. 확인된 산출물은 `update_step`에 연결하고, 영구 저장을 요청받았으면 `save_rhino_document`를 사용합니다.
코드

## 20. script-02_run_rhino

기준 API: `execute_rhino_script`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

전용 도구로 처리할 수 없는 모델링·편집·사용자 정의 측정을 연결된 Rhino에서 공식 RhinoCode로 실행합니다. 문서 전환·백그라운드 쓰기를 만들지 말고, 시간 초과나 불확실한 결과는 동일 요청으로 확인하며 **코드를 재실행하지 않습니다**. 실행 완료가 설계 검증·자동 롤백·문서 저장을 뜻하지는 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

```json
{
  "additionalProperties": false,
  "properties": {
    "script": {
      "type": "string",
      "description": "동기식 Python 소스, C# 문장 본문 또는 완전한 명령 매크로입니다."
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
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "required": [
    "script"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- Python/Python2는 JSON-safe 값을 result에 할당합니다. dict/list는 구조화된 값을 유지하고 json.dumps는 문자열을 반환합니다. C#은 class/Run 래퍼가 아닌 doc·result_json을 사용하는 문장 본문을 받습니다.
- command는 !, Pause, 대화상자 없이 완료되는 하나의 매크로를 받습니다. 실행 전 관찰한 대상·문서 단위·허용오차를 사용합니다.
- 공식 RhinoCode/StartScriptServer가 필요합니다. 일반 실행의 cwd는 프로젝트 루트이며 Plan 산출물 폴더가 필요하면 `execute_project_python`을 사용합니다.
- Rhino 스크립트 작성 참고는 `get_policy`(policy="rhino_scripting")에서 얻습니다. 래퍼는 doc/scriptcontext·cwd/환경·Undo·다시 그리기를 관리하며 Rhino 내장 패키지는 작업자 venv와 다를 수 있습니다.
- Floor 메타데이터는 실제 객체의 층만 기록합니다. 여러 층은 명시적인 문자열 배열, 한 층은 문자열로 저장하고 관련 없는 속성을 보존합니다. Scene의 전체 층 범위를 모든 객체에 복사하지 않습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "completed": true, // status·mutation_state·result와 함께 확인. timeout·print·CLI 종료는 완료나 롤백의 증거가 아님
  "request_id": "00000000000000000000000000000001", // 필요할 때 get_rhino_execution으로 같은 요청을 조회하는 ID
  "result": { // 스크립트가 정한 JSON 값. 첫 배열/목록 필드는 최대 20개, 최상위 문자열은 최대 4096자이며 추가 페이지는 result_page로 안내
    "example": "스크립트가 반환한 값" // 예시 스크립트가 정한 키. 도구가 보장하는 키가 아님
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 미완료·불확실한 실행이나 추가 결과·로그는 `get_rhino_execution`으로 확인합니다. 확인된 산출물은 `update_step`에 연결하고, 영구 저장을 요청받았으면 `save_rhino_document`를 사용합니다.
코드 1 · 코드 2

## 45. script-03_get_execution

기준 API: `get_rhino_execution`

근거: src/mcp/runtime/mcp_server.py

### DESCRIPTION

기존 RhinoCode 요청을 **다시 실행하지 않고** 완료 근거·결과 페이지·로그를 읽습니다. 대기 중이거나 불확실한 실행을 대조하는 조회이며, 작업을 취소·롤백하거나 모델에 재연결하지 않습니다. CLI 종료만으로 실행 완료를 판단하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청/실행 식별 필드를 포함합니다. 기본값은 true입니다."
    },
    "include_diagnostics": {
      "default": false,
      "type": "boolean",
      "description": "true이면 상세 실행 진단을 포함합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "추적 복구에 사용할 현재 연결입니다. 클라이언트 재시작 후 보관된 결과를 읽으려면 이를 생략하고 정확한 request_id를 제공합니다."
    }
  },
  "type": "object",
  "anyOf": [
    {
      "required": [
        "connection_id"
      ]
    },
    {
      "required": [
        "request_id"
      ],
      "properties": {
        "request_id": {
          "type": "string",
          "pattern": "^[0-9a-f]{32}$"
        }
      }
    }
  ]
}
```

**입력 보충 설명(문서용)**

- 완료 응답에 필요한 결과가 이미 있으면 추가 조회하지 않습니다. 클라이언트 재시작 뒤 보관 결과만 읽을 때는 정확한 request_id를 지정하고 외부 connection_id는 생략합니다.
- 요청 증거는 연결 정리까지 보관되며 원래 세션 저장소가 남아 있으면 모델 이름 변경·삭제 후에도 읽을 수 있습니다. 대기·마무리 중인 실행은 소유권을 유지합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "request_id": "00000000000000000000000000000001", // 같은 실행을 계속 조회할 회수 핸들. include_ids=false여도 유지
  "completed": true, // 최종 Rhino 처리 근거와 CLI 종료가 모두 확인되었는지 여부. native_completed와 다를 수 있음
  "status": "success", // 보관된 실행의 상태. 조회 호출 성공과 실행 성공을 구분
  "result": { // 보관된 사용자 정의 결과. result_page.pages의 next_offset으로 계속 읽으며 include_ids=false는 내부 ID를 숨길 수 있음
    "count": 3 // 예시 스크립트가 정한 키. 도구 고정 필드가 아님
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 남은 결과는 같은 요청의 다음 페이지에서 읽습니다. 완료가 확인된 결과를 후속 작업에 재사용하고 산출물은 `update_step`에 연결합니다.
코드 1 · 코드 2

## 78. script-04_save_document

기준 API: `save_rhino_document`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

영구 저장을 요청받았을 때 연결된 **문서 전체**를 기존 .3dm 경로에 저장합니다. 다른 작업의 변경도 함께 저장하므로 미확정 편집과 그룹·블록 편집을 먼저 정리해야 합니다. SaveAs를 지원하지 않으며, 확인되지 않은 저장을 자동 반복하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

```json
{
  "additionalProperties": false,
  "properties": {
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- 별도 경로·명령·프롬프트 답변을 받지 않습니다. 현재 연결의 기존 저장 경로를 사용하며 읽기 전용 파일·문서 불일치·활성 또는 검증되지 않은 편집 컨텍스트는 거부합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "saved": true, // true는 확인된 저장, false는 확인된 실패, null은 미확정이며 requires_reconciliation=true
  "modified": false // 확인된 저장 직후 문서 수정 플래그. 설계·형상 검증 결과가 아님
}
```

코드 1 · 코드 2

# Scene

Scene·Holon 의미 구조 관리 · prefix: `scene-NN_` · 유형 내 순번 01–13

## 05. scene-01_add_objects

기준 API: `add_scene_objects`

근거: src/mcp/features/scenes/tools.py

### DESCRIPTION

최상위 Rhino 객체를 Scene의 직접 구성원으로 등록하거나 해당 Scene에서 제외된 Holon 구성원을 복원합니다. **모델별 Scene 관계만 저장**하며 형상·그룹은 편집하지 않습니다. 이미 Holon을 통해 포함된 객체는 중복 등록하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "required": [
    "scene_id",
    "object_ids"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- 중복을 포함한 입력 순서를 유지합니다. 잘못된·없는·지원되지 않는 GUID는 항목별로 실패하며 전체 배치 오류와 구분됩니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 배치 평가 완료. failed_indices가 있으면 그 항목은 등록되지 않음
  "failed_indices": [], // 원래 object_ids 배열에서 실패한 0-based 위치. 성공 GUID·인덱스는 반환하지 않음
  "already_present_indices": [] // 이미 포함되어 변경하지 않은 입력 위치. Holon을 통해 포함된 경우도 포함
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 등록 후 현재 구성원은 `get_scene_objects`, Scene 메타데이터는 `get_design_scene`으로 확인합니다.
코드 1 · 코드 2

## 13. scene-02_create

기준 API: `create_design_scene`

근거: src/mcp/features/scenes/tools.py

### DESCRIPTION

**형상을 만들지 않고** 설계 영역·프로그램·상황을 나타내는 지속적인 Scene 메타데이터 핸들을 생성합니다. 단위와 프로젝트 파일 연결은 기록 정보이며 Rhino 문서의 단위·파일명·활성 문서를 바꾸거나 편집 대상을 확정하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "required": [
    "name"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "scene": { // 전체 메타데이터가 아닌 생성 확인 핸들
    "scene_id": "scene_example", // Scene ID
    "revision": 0 // 신규 Scene은 revision=0. 모델 상태·저장 결과가 아님
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: Scene 상세는 `get_design_scene`, 객체 등록은 `add_scene_objects`로 이어갑니다. 계획의 공간적 맥락으로 쓰려면 `create_plan` 또는 `update_plan`에 연결합니다.
코드

## 23. scene-03_focus_holons

기준 API: `focus_holons`

근거: src/mcp/features/components/tools.py

### DESCRIPTION

등록된 Holon과 하위 Holon의 현재 구성원을 **실제 Rhino에서 선택·격리·확대**합니다. 카메라·선택·가시성이 바뀌며 잠긴 주변 객체는 남을 수 있습니다. 일부 변경이나 결과 불확실성이 있으면 현재 상태를 확인하고 자동 재시도하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "required": [
    "holon_ids"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- 일반 모델 뷰가 활성화되고 명령·Undo/Redo가 끝난 상태여야 합니다. 대상은 보이고 선택 가능해야 하며 도구가 현재 재귀적 구성원을 자체 확인합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "zoom_selected": true, // 선택 객체로 줌했는지 여부
  "isolated": true, // 대상을 격리했는지 여부
  "locked_context_remains_visible": true, // 잠긴 주변 객체를 계속 표시하는지 여부
  "restore_visibility_command": "Unisolate", // Unisolate는 가시성 복구 명령이며 이전 카메라·선택 복원을 보장하지 않음
  "model_path": "C:\\Example\\example.3dm", // 저장된 모델의 경로
  "viewport_id": "00000000-0000-0000-0000-000000000001", // 포커스된 실제 모델 뷰포트 GUID
  "selected_ids": [ // 실제 선택된 Rhino 객체 GUID. 의미적 Holon 핸들과 구분
    "00000000-0000-0000-0000-000000000001"
  ]
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 초점을 맞춘 화면은 `get_current_viewcapture`, 대상 형상은 `get_objects`, 화면을 바꾸지 않는 추가 시점 비교는 `capture_rhino_inspection`으로 확인합니다.
코드

## 30. scene-04_get

기준 API: `get_design_scene`

근거: src/mcp/features/scenes/tools.py

### DESCRIPTION

Scene의 저장된 메타데이터와 등록 요약을 읽습니다. 개수는 **현재 Rhino 형상 검증이 아니며** 직접 구성원·제외 관계가 있으면 전체 객체 수를 확정하지 않습니다. Scene 구성원 관계는 설계상의 기록으로, 자동으로 대상을 보정하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청한 출력에 식별 필드를 포함합니다. false이면 보조 ID를 생략합니다. 후속 도구에서 반환된 ID가 필요하면 true를 요청합니다. 추가 상세 그룹이 선택되는 것은 아닙니다."
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
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "required": [
    "scene_id"
  ],
  "type": "object"
}
```

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "scene": { // 저장 요약. 입력과 같은 scene_id는 include_ids=true여도 다시 반환하지 않음
    "name": "예시 Scene", // 저장된 이름
    "units": "mm", // Scene에 기록한 단위. 현재 Rhino 문서 단위를 조회하거나 변경한 값이 아님
    "revision": 1, // 저장 상태의 revision
    "holons": 0, // Scene의 Holon 개수
    "objects": 0, // 저장된 구성원 수. 직접 등록·제외 override가 있으면 null이며 빈 Scene을 뜻하지 않음
    "direct_objects": 0, // 직접 등록된 객체 수
    "live_verified": false // false: 캐시 요약이며 현재 Rhino 객체 수 검증이 아님
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 현재 Scene 객체는 `get_scene_objects`로 확인합니다. 파일 연결을 바꾸려면 `update_design_scene`, 계획 컨텍스트로 쓰려면 `create_plan` 또는 `update_plan`을 사용합니다.
코드 1 · 코드 2

## 40. scene-05_get_holon

기준 API: `get_ontological_holon`

근거: src/mcp/features/components/tools.py

### DESCRIPTION

등록된 Holon의 저장 요약 또는 현재 Rhino 그룹 구성원을 변경 없이 읽습니다. 현재 상태 관찰에는 검증 가능한 일반 모델이 필요하며 그룹·블록 편집 중에는 오류를 반환합니다. 등록 불일치를 보고할 뿐 **자동 동기화나 설계·편집 적합성 검증을 하지 않습니다**.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청한 출력에 식별 필드를 포함합니다. false이면 보조 ID를 생략합니다. 후속 도구에서 반환된 ID가 필요하면 true를 요청합니다. 추가 상세 그룹이 선택되는 것은 아닙니다."
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
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "required": [
    "holon_id"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- 현재 구성원 GUID는 live=true, include_ids=true, field_groups=["geometry"]로 조회합니다. 하위 Holon까지 포함한 effective_object_ids가 필요하면 recursive=true를 사용하고 관계 핸들은 references를 추가합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "holon": { // Holon 요약. 입력과 같은 holon_id는 반복 반환하지 않음
    "name": "예시 Holon", // 저장된 이름
    "availability": "present", // 조회 모드에 따른 등록/관찰 상태. live=false이면 현재 존재 확인이 아님
    "object_count": 2, // 객체 수
    "live_verified": false // 현재 관찰 여부. live=true+geometry+include_ids일 때 현재 GUID를 얻고 recursive=true이면 하위 유효 구성원도 포함
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 현재 구성원의 상세 형상·면은 `get_objects`, 교차 검토는 `resolve_object_intersection`, 실제 선택·격리·확대는 `focus_holons`로 이어갑니다.
코드 1 · 코드 2

## 46. scene-06_get_objects

기준 API: `get_scene_objects`

근거: src/mcp/features/scenes/tools.py

### DESCRIPTION

연결된 저장 모델에서 Scene의 직접 객체와 하위 Holon 구성원을 현재 상태로 읽습니다. 불완전한 관찰·불안정한 편집 상태·사라진 직접 등록 객체는 오류로 처리하며 **빈 Scene이나 캐시 결과로 대체하지 않습니다**.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청한 출력에 식별 필드를 포함합니다. false이면 보조 ID를 생략합니다. 후속 도구에서 반환된 ID가 필요하면 true를 요청합니다. 추가 상세 그룹이 선택되는 것은 아닙니다."
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
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "required": [
    "scene_id"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- 현재 저장 모델의 안정적인 일반 편집 컨텍스트가 필요합니다. 관찰은 해당 모델의 최대 64개 Holon 등록을 지원하며 페이지를 나누어도 이 제한은 바뀌지 않습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "objects": [], // 현재 Scene 객체. 기본 name/object_type, include_ids=true면 rhino_guid, geometry면 존재하는 holon_id·bounds_mm
  "total": 0, // 현재 연결 모델에서 확인한 Scene 객체 전체 수. 프로젝트 전체 형상 수가 아님
  "limit": 50, // 페이지 최대 항목 수
  "offset": 0, // 현재 페이지 시작 위치
  "truncated": false, // 뒤 페이지가 남았는지 여부. 다음 offset은 현재 offset+objects 길이
  "live_verified": true, // 현재 Rhino 상태를 확인했는지 여부
  "model_path": "C:\\Example\\example.3dm" // 관찰한 연결 모델 경로. 제공한 scene_id는 반복 출력하지 않음
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 개별 형상은 `get_objects`, 객체가 속한 Holon은 `get_ontological_holon`으로 확인합니다. 명시적으로 Holon 등록을 원할 때만 `upsert_ontological_holon`으로 이어갑니다.
코드

## 53. scene-07_list

기준 API: `list_design_scenes`

근거: src/mcp/features/scenes/tools.py

### DESCRIPTION

프로젝트에 저장된 Scene을 이름·파일 연결로 찾습니다. 현재 Rhino 문서나 객체 형상을 조회하지 않는 **메타데이터 목록**입니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청한 출력에 식별 필드를 포함합니다. false이면 보조 ID를 생략합니다. 후속 도구에서 반환된 ID가 필요하면 true를 요청합니다. 추가 상세 그룹이 선택되는 것은 아닙니다."
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
      "description": "connect가 반환한 현재 연결의 정확한 ID입니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- name은 대소문자를 구분하지 않는 부분 일치, file_name은 저장된 이름의 정확 일치입니다. 페이지를 이어 읽을 때 같은 필터를 유지합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "scenes": [], // 저장 Scene 목록. 기본 name, include_ids=true면 scene_id, scope면 존재하는 파일 연결 정보
  "total": 0, // 필터에 일치하는 전체 항목 수
  "limit": 50, // 페이지 최대 항목 수
  "offset": 0, // 현재 페이지 시작 위치
  "truncated": false // 뒤 페이지가 남았는지 여부. 같은 필터로 offset+scenes 길이부터 계속 조회
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 선택한 Scene의 요약은 `get_design_scene`, 현재 객체는 `get_scene_objects`로 확인합니다. Plan의 공간적 맥락으로는 `create_plan` 또는 `update_plan`에 연결합니다.
코드

## 59. scene-08_list_holons

기준 API: `list_ontological_holons`

근거: src/mcp/features/components/tools.py

### DESCRIPTION

**캐시된 Holon 등록 정보**를 문서 또는 Scene 범위로 조회합니다. Rhino의 현재 형상·구성원 관계를 확인하거나 등록 대장을 갱신하지는 않습니다. 현재 구성원이 필요한 작업에는 유효한 실시간 관찰 근거를 사용합니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청한 출력에 식별 필드를 포함합니다. false는 보조 ID를 생략합니다. 이후 도구에 반환된 ID가 필요하면 true를 요청합니다. 이 설정은 추가 세부 그룹을 선택하지 않습니다."
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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- recursive=false는 문서 범위에서 루트 등록만 나열합니다. Scene 필터의 루트는 정규 Scene 연결을 따르므로 다른 Scene에 부모가 있어도 포함될 수 있습니다. Holon ID와 Rhino 객체·그룹 GUID는 서로 바꿔 쓰지 않습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "holons": [], // 캐시 요약. include_ids=true일 때 holon_id; references에서 그룹·Scene·부모·자식 핸들. geometry_available=false이면 구성원 GUID/형상 없음
  "total": 0, // 필터에 일치하는 전체 항목 수
  "live_verified": false // false: Rhino 현재 상태를 확인하지 않음. geometry 그룹을 요청해도 실시간 근거가 되지 않음
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: `get_ontological_holon`으로 현재 구성원과 상세를 확인하거나 `focus_holons`로 등록 단위에 포커스할 수 있습니다. 실제 불일치가 있으면 `sync_ontological_holon`으로 대장을 맞추고, 의미 구조 변경은 `upsert_ontological_holon`으로 진행합니다.
코드 1 · 코드 2

## 72. scene-09_remove_holon

기준 API: `remove_ontological_holon`

근거: src/mcp/features/components/tools.py

### DESCRIPTION

Rhino 형상·일반 그룹·객체 속성을 보존하고 Holon의 **의미 등록만 해제**합니다. 부모 및 Plan/Step 참조를 먼저 해제해야 하며, 자식은 독립된 등록 루트로 남습니다. 결과가 불확실하면 현재 상태를 대조하고, 제거를 자동 재시도하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "required": [
    "holon_id"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- 부모가 있는 Holon은 부모의 자식 목록에서 먼저 분리하고, 해당 Holon의 Plan/Step 참조도 해제해야 합니다. 유효한 기존 holon_id가 있다면 ID를 얻기 위한 재조회는 필요하지 않습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "holon": { // 등록 해제 확인. 일반 그룹·형상·자식의 직접 소유권 및 Scene 연결은 유지
    "holon_id": "example-holon", // 해제된 의미 ID. 살아 있는 등록 핸들처럼 재사용하지 않음
    "status": "unregistered", // unregistered는 의미 등록 해제. 형상 삭제가 아니며 Undo는 그룹 테이블 변경까지 되돌리지 않음
    "live_verified": true // 현재 Rhino 상태를 확인했는지 여부
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 남은 등록 구조는 `list_ontological_holons`로 확인할 수 있습니다. 해제 결과나 Undo 이후 상태가 불확실할 때는 `sync_ontological_holon`으로 정합성을 확인합니다.
코드 1 · 코드 2

## 73. scene-10_remove_objects

기준 API: `remove_scene_objects`

근거: src/mcp/features/scenes/tools.py

### DESCRIPTION

**Scene의 직접 구성원 관계**를 제거하거나 Holon 구성원을 해당 Scene에서 제외합니다. Rhino 객체·Holon 그룹은 삭제하거나 수정하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "required": [
    "scene_id",
    "object_ids"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- object_ids는 중복을 포함해 입력 순서대로 처리됩니다. 결과의 인덱스를 해석할 수 있도록 원래 배열을 보관합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 성공 응답이어도 아래 실패/기존 부재 인덱스를 함께 확인
  "failed_indices": [], // 원래 object_ids의 0-based 실패 위치. 성공 GUID/인덱스는 반환하지 않음
  "already_absent_indices": [] // 0-based 위치. Scene에 없는 유효 GUID는 문서에도 없어도 여기에 포함
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: `get_scene_objects`로 변경 후의 실제 Scene 구성원을 확인할 수 있습니다. 다시 포함하려는 경우에는 `add_scene_objects`를 사용합니다.
코드 1 · 코드 2

## 85. scene-11_sync_holon

기준 API: `sync_ontological_holon`

근거: src/mcp/features/components/tools.py

### DESCRIPTION

안정된 Rhino 편집 상태에서 현재 Holon 등록을 읽어 **대장을 한 차례 맞춥니다**. 형상이나 그룹을 복구·수정하는 도구는 아니며, 유효한 기존 근거가 있으면 정례 동기화는 필요하지 않습니다. 불확실한 변경 작업의 재실행을 대신해 상태를 대조할 때 사용합니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- holon_id, holon_ids, scene_id 중 한 방식만 사용하며 모두 생략하면 연결 문서 전체입니다. 하위 등록을 포함해 최대 64개로 범위를 좁히고, 그룹·블록 편집 중이거나 격리 상태가 불명확할 때는 먼저 편집 상태를 안정화합니다. Scene/문서 범위는 대장에 없는 네이티브 등록도 발견할 수 있지만 명시적 Holon 범위는 임의로 확장하지 않습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 일괄 처리가 평가됨. 모든 항목 확인 완료를 뜻하지 않음
  "checked": 1, // 확인한 Holon 수
  "changed": 0, // 실제 대장 갱신 수. 변경 없으면 새 리비전도 없음
  "unavailable": 0, // 상태가 present가 아닌 등록 수
  "problems": [], // 항목별 문제. 관련 없는 유효 등록은 함께 갱신될 수 있음
  "scene_revisions": {}, // Scene ID → Scene 리비전. Plan expected_revision이 아님
  "live_verified": true // problems가 없을 때 true. 단일 대상 성공 시 holon 확인 객체도 추가될 수 있음
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 항목별 문제를 해결한 뒤 필요한 범위만 다시 대조합니다. 확인된 등록은 `get_ontological_holon`으로 조회하거나 `focus_holons`로 살펴볼 수 있습니다.
코드 1 · 코드 2

## 86. scene-12_update

기준 API: `update_design_scene`

근거: src/mcp/features/scenes/tools.py

### DESCRIPTION

Scene의 **프로젝트 파일 연결 메타데이터**를 변경하거나 해제합니다. Scene 이름·단위·형상·Holon 소유권과 실제 Rhino 문서의 이름·경로는 변경하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "required": [
    "scene_id"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- 프로젝트 파일 이름이 중복되면 `project_info`(sections=["project"], include_ids=true)의 project.files[].project_file_id로 정확한 파일을 지정합니다. expected_revision 입력은 없습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "scene": { // Scene 확인 또는 상세 객체
    "scene_id": "scene_example", // 이후 Scene 조회에 재사용할 핸들
    "revision": 1 // 실제 파일 연결 변경 시에만 증가. Plan/Loop expected_revision이 아님
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: `get_design_scene`으로 연결 정보를 확인하거나 `get_scene_objects`로 해당 Scene의 현재 구성원을 살펴볼 수 있습니다.
코드 1 · 코드 2

## 90. scene-13_upsert_holon

기준 API: `upsert_ontological_holon`

근거: src/mcp/features/components/tools.py

### DESCRIPTION

물리적 요소와 그 관계가 이루는 역할·동작·구조를 **Holon으로 등록하거나 갱신**하며 형상은 복제하지 않습니다. 직접 객체 소유권은 Holon 하나에만 속하고, 일반 그룹·블록이 자동으로 의미 단위가 되지는 않습니다. 기존 그룹 이름 변경은 거부되며, 불확실한 결과나 Undo 뒤에는 자동 재등록 대신 현재 상태를 대조합니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "required": [
    "name"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- **object_ids 생략/null에는 기존 그룹 연결이 필요합니다.** rhino_group_id 또는 기존 holon_id의 연결이 있어야 하며 이름만으로 추론하지 않습니다. 직접 소유 객체의 현재 최상위 GUID만 제공하고 자식 소유 객체는 제외합니다. []는 직접 객체 없이 기존 자식을 묶을 때만 유효합니다.
- 등록에는 design_components=1과 component_registry=2, 구성원 추론에는 component_group_inference=1이 추가로 필요합니다. 추론은 기존 그룹의 유효 구성원 1–4096개를 읽으며 이름·Scene·자식 관계를 추론하거나 없는 그룹을 만들지 않습니다. 명시적으로 요청한 새 그룹만 생성할 수 있으며 이름 충돌은 실패합니다. 자식 Holon은 부모와 같은 문서에 있어야 합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "holon": { // 등록 확인. holon_id/rhino_group_id와 존재하는 상태 필드만 축약
    "holon_id": "example-holon", // 조회·동기화·포커스에 재사용할 의미 ID. 객체 GUID가 아님
    "availability": "present", // 대상 이용 가능 상태
    "object_count": 1, // 객체 수
    "live_verified": true // 현재 네이티브 등록 확인. Undo 후 무조건 재등록하지 않으며 빈 일반 그룹 항목은 남을 수 있음
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 등록된 Holon은 `get_ontological_holon`으로 조회하고 `focus_holons`로 살펴볼 수 있습니다. 네이티브 결과와 대장이 어긋났거나 결과가 불확실하면 `sync_ontological_holon`으로 정합성을 확인합니다.
코드 1 · 코드 2

# Intersect

교차·겹침 검토와 해결 · prefix: `intersect-NN_` · 유형 내 순번 01–02

## 38. intersect-01_find

기준 API: `get_object_intersections`

근거: src/mcp/features/context/tools.py

### DESCRIPTION

식별된 닫힌 솔리드의 **양의 부피 겹침 쌍**을 문서 수정 없이 셉니다. 닫힌 Brep/Extrusion과 면 방향이 정렬된 매니폴드 Mesh를 지원하며, Brep/Mesh 혼합 계산은 임시 메시 근사입니다. 겹침 0은 이격 거리·설계 적합성·법규 준수의 확인이 아닙니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "required": [
    "object_ids"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- 그룹 소속만으로 검사 객체가 추가되지는 않습니다. 블록 확장 후 최대 2048개 출현 항목, 20000개 후보 쌍으로 제한되며 Mesh는 최대 500000면을 지원합니다. cursor/max_pairs 등 네이티브 페이지 제어는 공개 입력이 아닙니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "intersections": { // 겹침 집계
    "number": 0 // 전체 범위의 양의 부피 겹침 쌍 수. 겹침 영역 수·다자간 동시 교차 수가 아님
  },
  "next_step": "이 범위에서 양의 부피 겹침이 발견되지 않았으므로 해결 도구를 호출할 필요가 없습니다. 이 결과가 다른 설계 조건이나 이격 거리 조건을 충족함을 입증하지는 않습니다." // 실제 안내 문자열. 양수면 원래 object_ids/include_block으로 검토. 계산 불가·범위 변경은 불완전한 수나 0 대신 오류
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 겹침이 있으면 `resolve_object_intersection`으로 비교 이미지를 보며 한 쌍씩 검토할 수 있습니다. 겹침이 없으면 이 범위에 대한 해결 호출은 필요하지 않습니다.
코드 1

## 75. intersect-02_resolve

기준 API: `resolve_object_intersection`

근거: src/mcp/features/components/tools.py

### DESCRIPTION

겹친 객체를 한 쌍씩 이미지로 비교하고, **명시적으로 고른 객체**에서 겹친 부분만 제거합니다. 검토 중 실제 선택·카메라가 바뀌며 안정된 저장 문서와 래스터 모델 뷰포트가 필요합니다. 형상만 보고 설계 선택을 추론하지 않으며, 불확실한 변경 결과에서는 자동 진행을 멈춥니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- object_ids로 새 검토를 시작하면 기존 검토와 건너뛴 쌍이 초기화됩니다. 미리 겹침 개수를 조회할 필요는 없습니다. intersection_review=1과 보이고 선택 가능한 대상이 필요합니다.
- 블록은 비교 검토만 지원합니다. 자동 편집은 블록·원본 파일, Mesh/Brep 혼합, 텍스처/정점색 Mesh, 보존 불가 형상 사용자 데이터, 대상 전체 삭제, 여러 Brep 결과를 지원하지 않습니다. review_id는 표시한 객체를 식별하며 적용 직전에 현재 형상을 다시 계산합니다. 이 도구는 모델 저장·원본 자산 편집·Holon 등록을 수행하지 않습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "state": "completed", // 검토 종료 예시. 대기 시 awaiting_choice와 review_id/objects[].number/비교 이미지/next_step을 반환
  "skipped_pairs": 0, // 건너뛴 쌍은 수정하지 않음. completed가 모든 겹침 제거를 뜻하지 않음
  "message": "검토할 겹침이 더 없습니다. skip한 쌍은 수정하지 않았습니다." // 직전 편집/skip이 있으면 previous_result도 유지. 재연결하면 검토 상태가 사라짐
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 같은 도구에서 비교 이미지를 확인한 뒤 제거할 객체를 선택하거나 건너뜁니다. 완료 후 실제 전체 겹침 수를 다시 확인해야 한다면 `get_object_intersections`를 사용할 수 있습니다.
코드 1 · 코드 2

# Asset

모델·도면 자산 검색·준비·배치 · prefix: `asset-NN_` · 유형 내 순번 01–11

## 09. asset-01_audit_drawing

기준 API: `audit_asset_drawing`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

저장 도면 패키지의 **파일 해시**를 검사하고, 원본을 확인할 수 있으면 변경 여부도 대조합니다. 읽기 전용 무결성 검사이며 시각적 품질·설계·시공 검증이나 재생성을 수행하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "required": [
    "package_dir"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- 알려진 라이브러리 자산의 원본은 자동 탐색합니다. 사용자 지정 패키지의 원본 변경까지 확인하려면 현재 source_glb가 필요합니다. **반환 경로에 ../ 또는 unavailable 표시가 있으면 관리형 입력으로 그대로 사용할 수 없습니다.** 필요한 파일을 프로젝트 내부에 준비한 뒤 허용 상대 경로를 사용합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "source_geometry": "source_file_current", // current/source_file_current/stale/not_checked. not_checked는 success여도 원본 비교 미실시
  "asset_id": "example-asset", // 패키지 원본 ID. custom-*는 등록 자산 ID가 아님
  "checked_files": 6, // 해시를 검사한 파일 수. 시각적 검토가 아님
  "failures": [] // 실패 항목이 하나라도 있으면 status=error
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 등록 3DM의 원본이 바뀌었다면 `refresh_asset`으로 저장 도면을 갱신할 수 있습니다. 사용자 지정 GLB는 `generate_asset_drawing_views`로 새 패키지를 생성합니다.
코드 1

## 24. asset-02_generate_drawing_views

기준 API: `generate_asset_drawing_views`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

등록 3DM 또는 사용자 지정 GLB로 평면·정면·우측면 실루엣의 **새 도면 패키지**를 만듭니다. 기존 등록 도면은 교체하지 않으며, 숨은선·시공 상세·제품의 정면 방향을 추론하지 않습니다. 등록 원본의 저장된 변경을 반영하려면 `refresh_asset`을 사용합니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- 등록 자산은 원본 해시가 일치하는 3DM이어야 하며 추출을 지원하는 Bridge가 필요합니다. 비-3DM 모델 원본은 먼저 준비·등록합니다. 사용자 GLB는 비압축 정적 삼각형이며 최대 100 MB/250k 삼각형입니다. scales는 5–1000의 서로 다른 정수 1–4개, source_references는 고유 source_id를 가진 최대 30개입니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "package_dir": ".almond/produced/example/drawing", // 생성 폴더. 관리형 후속 입력은 프로젝트 내부 경로만 허용하므로 ../ 등을 확인
  "manifest": {} // 상세 생략. DXF는 mm 실물 크기, SVG는 선택 축척, A3는 가능한 경우. 첨부 출처는 원본 생성 근거를 소급 증명하지 않음
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 생성 패키지는 `audit_asset_drawing`으로 파일 무결성과 원본 일치 여부를 대조할 수 있습니다. 생성 성공과 별개로 실제 도면을 확인합니다.
코드 1

## 25. asset-03_get_drawings

기준 API: `get_asset_drawing`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

등록 모델의 **저장 도면 매니페스트와 뷰 URI** 또는 사용 가능한 기존 시범 패키지를 가져옵니다. 도면을 생성·갱신하지 않으며, 저장 패키지가 현재 원본과 일치한다는 보장은 하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청한 출력에 식별 필드를 포함합니다. false는 보조 ID를 생략합니다. 이후 도구에 반환된 ID가 필요하면 true를 요청합니다. 이 설정은 추가 세부 그룹을 선택하지 않습니다."
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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- 파일 경로가 필요하면 field_groups=["paths"]를 요청합니다. 입력한 asset_id는 응답에 다시 포함되지 않으므로 보관합니다. 경로에 ../ 또는 unavailable 표시가 있으면 관리형 후속 도구에 그대로 입력할 수 없습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "plan_svg_uri": "almond://drawing/example-asset/drawing/plan/50", // 저장 SVG의 리소스 URI. 첨부 파일이나 audit의 package_dir가 아님
  "manifest": {} // 상세 생략. 현재 원본 일치 보장 없음. paths 요청 시 package_dir와 등록 패키지의 dimensions_path 추가
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 현재 원본과 저장 도면의 일치 여부가 필요하면 `audit_asset_drawing`으로 대조합니다. 등록 원본의 저장된 변경은 `refresh_asset`으로 반영할 수 있습니다.
코드 1 · 코드 2

## 32. asset-04_get

기준 API: `get_drawing_asset`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

알고 있는 모델·2D 자산의 파일 사용 가능 여부, 출처와 **변환·갱신 상태**를 확인합니다. 실제 형상을 가져오거나 시각적으로 검증하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청한 출력에 식별 필드를 포함합니다. false는 보조 ID를 생략합니다. 이후 도구에 반환된 ID가 필요하면 true를 요청합니다. 이 설정은 추가 세부 그룹을 선택하지 않습니다."
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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- 입력한 asset_id는 include_ids=true여도 성공 응답에서 생략되므로 보관합니다. 변환에 필요한 경로는 field_groups=["paths"]로 조회하되, 프로젝트 밖 경로는 프로젝트 내부에 원본을 준비한 뒤 사용합니다. 원본의 실제 단위와 작업 Plan도 필요합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "asset": { // 입력 asset_id는 재출력하지 않음. 필요한 후보에는 실제 next_tool/next_step 포함
    "name": "예시 자산", // 저장된 이름
    "file_available": true, // 원본·등록 파일의 존재 여부
    "model_status": "ready", // ready/needs_conversion/needs_refresh 등. source_only는 원본이 있어도 배치 준비 안 됨
    "drawing_ready": true // 도면 패키지와 현재 원본 대조 상태. 실제 가져오기·시각적 승인 아님
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 준비된 자산은 `place_drawing_asset`으로 배치하거나 `get_asset_drawing`으로 저장 도면을 볼 수 있습니다. 변환이 필요한 원본은 `prepare_drawing_asset`으로 준비하고, 저장 원본이 바뀌었다면 `refresh_asset`으로 갱신합니다.
코드 1 · 코드 2

## 55. asset-05_list

기준 API: `list_drawing_assets`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

변환 대기 원본을 포함한 **모델·2D 자산 모음**을 둘러봅니다. 다이어그램은 별도 라이브러리이며, 카탈로그의 파일 준비 상태는 배치 결과나 시각적 품질을 보증하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청한 출력에 식별 필드를 포함합니다. false는 보조 ID를 생략합니다. 이후 도구에 반환된 ID가 필요하면 true를 요청합니다. 이 설정은 추가 세부 그룹을 선택하지 않습니다."
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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- limit은 1–100, offset은 0 이상입니다. 변환 원본 경로가 필요하면 field_groups=["paths"]를 요청하되 프로젝트 밖 경로를 관리형 입력에 그대로 전달하지 않습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "library_id": "model_assets", // include_ids=true에서 유지되는 라이브러리 구분자
  "assets": [], // include_ids=true에서 asset_id. source_only/needs_conversion은 변환 필요; next_tool/next_step은 조건부 안내
  "total": 0, // 필터에 일치하는 전체 항목 수
  "limit": 20, // 페이지 최대 항목 수
  "offset": 0, // 현재 페이지 시작 위치
  "truncated": false, // true이면 같은 필터로 offset+현재 항목 수부터 계속. next_offset 필드는 없음
  "purpose": "3DM 모델 및 2D 표현. 기존 원본은 명시적인 변환이 필요합니다." // 서버가 실제 반환하는 라이브러리 용도 설명
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: `get_drawing_asset`으로 후보를 자세히 확인하거나 준비된 자산을 `place_drawing_asset`으로 배치할 수 있습니다. 변환·갱신이 필요한 후보는 응답의 조건부 안내에 따라 `prepare_drawing_asset` 또는 `refresh_asset`으로 이어집니다.
코드 1 · 코드 2

## 64. asset-06_place

기준 API: `place_drawing_asset`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

관리되는 모델·2D 자산을 편집 가능한 Rhino 문서에 배치하며 3DM은 원본에 연결된 블록으로 삽입합니다. 공유 연결 정의를 갱신해 **기존 인스턴스에도 영향을 줄 수 있습니다**. 시간 초과나 불확실한 실패는 변경 미적용을 뜻하지 않으므로 재시도 전에 문서를 대조합니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- 모든 배치 수치는 유한값이며 0<scale<=100입니다. 3DM에는 표준 문서·원본 단위와 drawing_asset_linked=1이 필요합니다. 원본 원점이 배치 기준점이고 원본 단위는 문서 단위로 변환됩니다. 진행 중인 편집·Undo/Redo는 먼저 끝냅니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "asset_id": "example-asset", // 자산 ID
  "object_guid": "00000000-0000-0000-0000-000000000001", // 삽입한 최상위 블록 GUID. get_objects 또는 Scene 구성원 입력에 재사용
  "definition_created": true // 새 정의 생성 여부. 공유 정의 갱신 시 definition_refreshed/affected_existing_instances가 추가될 수 있음
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: `get_objects`로 삽입된 객체를 확인하거나 `add_scene_objects`로 의도한 Scene에 포함할 수 있습니다. 원본 변경으로 배치가 거부되었다면 `refresh_asset`으로 저장 원본과 도면을 먼저 맞춥니다.
코드 1 · 코드 2

## 66. asset-07_prepare

기준 API: `prepare_drawing_asset`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

원본 사본을 검사하고, 필요한 경우 명시적으로 편집한 뒤 최종 이미지를 검토할 수 있는 3DM 준비 작업을 만듭니다. 기본 조립 구조·레이어·재질·원점은 보존합니다. 검토 확인은 **실제 이미지와 파일 해시**에 연결되어야 하며, 불확실한 실행은 자동 반복하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "정규화 또는 최종 검증 승인에 필요한 명시적 검토/편집 근거 객체입니다. 정확한 출력 해시와 「이전 결과에서 가져올 입력」에 제시된 지원 필드를 사용합니다. 생략하더라도 시각적 승인을 뜻하지 않습니다."
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
      "description": "요청한 출력에 식별 필드를 포함합니다. false는 보조 ID를 생략합니다. 이후 도구에 반환된 ID가 필요하면 true를 요청합니다. 이 설정은 추가 세부 그룹을 선택하지 않습니다."
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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "required": [
    "stage"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- inspect 전에 작업 Plan의 산출물 디렉터리를 선택합니다. 이후에는 반환된 job_dir를 재사용하고 source_file/input_units를 다시 지정하지 않습니다. 입력은 최대 100 MB, 최상위 객체 10000개, 미리 보기 블록 깊이 32단계입니다.
- **normalize의 review**: vision_reviewed=true와 정확한 review_targets.inspected_sha256를 inspected_sha256에 넣습니다. rotation_degrees_xyz와 translation은 각각 유한한 수 3개이며 생략하면 항등 변환입니다. translation은 원본 문서 단위입니다. remove는 {object_id, reason} 배열이며 parts에서 얻은 고유 최상위 ID와 비어 있지 않은 이유(최대 2000자)가 필요합니다. 편집할 내용이 없으면 normalize를 건너뜁니다.
- **최종 verify의 review**: 첫 verify가 만든 이미지를 실제로 확인한 뒤, 같은 job_dir에 vision_reviewed=true, final_sha256=<review_targets.final_sha256>, name=<검토한 이름>, asset_id=<검토한 ID>로 다시 verify합니다. 제거 ID·이미지가 필요하면 field_groups=["parts","previews"]와 include_ids=true를 요청합니다. 명시한 최상위 객체만 제거하며 정의·레이어·객체 이름은 유지합니다. 미리 보기는 메시를 샘플링하므로 텍스처·PBR 채널·의도한 정면을 검증하지 않습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "state": "ready", // ready일 때만 source_3dm 제공. running/unconfirmed/failed는 error와 next_stage=null
  "ready_for_registration": true, // 파일 해시에 연결된 호출자의 실제 이미지 검토 확인이며 자동 시각 인증 아님
  "job_dir": ".almond/produced/example/job", // 이후 단계 및 등록의 preparation_job에 재사용. status는 저장 근거만 읽고 늦은 실행을 자동 정합화하지 않음
  "source_3dm": ".almond/produced/example/job/final.3dm", // 검토 완료 최종 파일. register_drawing_asset에 검토한 name/asset_id와 함께 전달
  "next_stage": "register_drawing_asset", // 현재 상태의 다음 단계. 오류에서 자동 진행을 유도하지 않음
  "review_evidence": "파일 해시에 연결된 호출자의 검토 확인이며, 자동 시각 검증은 수행하지 않습니다.", // 서버가 실제 반환하는 검토 증거의 성격 설명
  "next_step": "게시하려는 경우 이 응답의 source_3dm, preparation_job=job_dir, 검토한 asset_id/name을 지정하여 register_drawing_asset을 호출합니다. category는 선택 사항입니다. …" // 서버가 실제 반환하는 다음 작업 안내. 문서 작성자의 주석이 아님
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 같은 작업에서 최종 이미지를 만들고 확인한 뒤 `register_drawing_asset`으로 게시할 수 있습니다. 편집이 필요하지 않으면 정규화 단계를 건너뛰며, 오류나 불확실한 실행은 status로 저장 근거를 확인합니다.
코드 1

## 70. asset-08_refresh

기준 API: `refresh_asset`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

**편집 후 저장된 등록 3DM**을 다시 측정하고 저장 도면을 재생성하며 연결 원본 경로를 유지합니다. Rhino 문서를 저장하거나 기존 연결 인스턴스를 다시 불러오지는 않습니다. 게시가 적용되었거나 불확실한 오류에서는 갱신을 무작정 반복하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- 먼저 자산의 라이브러리 3DM에 편집 내용을 저장합니다. 등록된 3DM의 asset_id와 drawing_asset_extract=2가 필요하며, 기존 원본 변환이나 열린 문서 저장을 대신하지 않습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "registration_applied": true, // true면 인덱스 갱신 실패여도 게시 적용. 무작정 반복하지 않음
  "source_path_preserved": true, // 기존 원본 경로를 보존했는지 여부
  "rhino_linked_instances_updated": false, // false: 기존 Rhino 연결 인스턴스 재로드는 별도
  "live_index_refreshed": true, // false인데 게시가 적용됐다면 재연결하여 인덱스 갱신
  "asset": {}, // 자산 상세 일부 생략. asset_id는 후속 조회·배치에 재사용; 시각 검증 아님
  "model_path": ".almond/produced/example/asset.3dm", // 기존 라이브러리 3DM 경로. 현재 Rhino 문서 저장을 뜻하지 않음
  "package_dir": ".almond/produced/example/drawing", // 갱신 도면 폴더. 프로젝트 밖 ../ 경로는 관리형 audit에 직접 재입력 불가
  "previous_files_retained": true // 이전 도면·매니페스트 백업·원본 리비전 사본 보존
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: `get_asset_drawing`으로 갱신 도면을 확인할 수 있습니다. Rhino의 기존 인스턴스는 별도로 연결 원본을 갱신해야 하며, 인덱스 갱신만 실패했다면 재등록 대신 다시 연결합니다.
코드 1 · 코드 2

## 71. asset-09_register

기준 API: `register_drawing_asset`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

준비된 3DM을 측정 치수와 평면·정면·우측면 실루엣 도면을 갖춘 **라이브러리 자산으로 게시**합니다. 별도 준비 도구는 필수가 아니며, 준비 작업을 첨부하지 않은 등록은 시각적 검토를 증명하지 않습니다. 기존 자산 교체는 연결 인스턴스에 영향을 줄 수 있고, 게시 후 오류를 미적용으로 보고 재시도하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
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

**입력 보충 설명(문서용)**

- asset_id는 영문·숫자·점·밑줄·하이픈 1–100자이며 . 또는 ..는 금지합니다. 기존 원본을 변환하면 원래 ID를 유지하고 Diagram ID는 재사용하지 않습니다. 준비 작업을 쓰면 반환 source_3dm/job_dir와 검토한 name/asset_id를 일치시킵니다.
- 표준 Rhino 단위와 drawing_asset_extract=2가 필요하며 최대 100 MB/250k 삼각형입니다. Mesh·Brep·Extrusion·Surface·SubD·내장 중첩 블록을 지원하고, 확인되지 않은 외부 종속 항목은 게시하지 않습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "registration_applied": true, // true면 게시 적용. 불명확한 오류는 null과 requires_reconciliation; 단순 재시도 금지
  "live_index_refreshed": true, // 게시 true·인덱스 false이면 등록을 반복하지 말고 재연결
  "source_path_preserved": false, // 기존 원본 경로를 보존했는지 여부
  "linked_instances_may_update": false, // 교체로 기존 연결 인스턴스에 영향 가능
  "asset": {}, // 등록 자산 상세 일부 생략. asset_id를 후속 조회·배치·refresh에 재사용
  "library_dir": ".almond/produced/example", // 라이브러리 폴더
  "model_path": ".almond/produced/example/asset.3dm", // 저장된 모델의 경로
  "package_dir": ".almond/produced/example/drawing", // 실루엣 도면 폴더. DXF/치수는 mm, SVG 기본 1:50/1:100, A3는 가능한 경우. 프로젝트 밖 경로는 관리형 audit에 직접 입력 불가
  "manifest_path": ".almond/produced/example/manifest.json", // 라이브러리 manifest.json 경로. 도면 패키지의 drawing.json과 다름
  "previous_files_retained": false, // 교체 전 원본·도면·매니페스트 백업 보존
  "previous_source_sha256": null // 기존 원본 해시. 없으면 null
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: `get_asset_drawing`으로 저장 도면을 확인하거나 `place_drawing_asset`으로 배치할 수 있습니다. 이후 같은 원본에 저장된 편집을 반영할 때는 `refresh_asset`을 사용합니다.
코드 1 · 코드 2

## 79. asset-10_search_repository

기준 API: `search_asset_repository`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

모델·2D 요소 아카이브를 검색하고 필요하면 도면 준비가 완료된 후보로 좁힙니다. **비-3DM 모델은 별도 변환·등록이 필요**하며, 검색은 실제 가져오기나 외관 검증을 수행하지 않습니다. 다이어그램 라이브러리는 포함하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청한 출력에 식별 필드를 포함합니다. false는 보조 ID를 생략합니다. 이후 도구에 반환된 ID가 필요하면 true를 요청합니다. 이 설정은 추가 세부 그룹을 선택하지 않습니다."
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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- include_ids=true로 받은 assets[].id를 자산 도구의 asset_id로 사용합니다. 이 검색에는 원본 파일 경로가 없어 paths 그룹으로도 추가되지 않으므로 변환할 때 `get_drawing_asset`의 paths 상세를 사용합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "total": 0, // 전체 매치 수. assets는 limit까지이며 offset/has_more 없음
  "assets": [] // include_ids=true에서 id → 후속 asset_id. kind=element도 모델·2D 항목. 조건부 next_tool/next_step; 원본 경로는 미포함
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: `get_drawing_asset`으로 후보를 자세히 확인하거나 준비된 자산을 `place_drawing_asset`으로 배치할 수 있습니다. 변환·갱신이 필요한 후보는 `prepare_drawing_asset` 또는 `refresh_asset`으로 이어집니다.
코드 1 · 코드 2

## 82. asset-11_search

기준 API: `search_drawing_assets`

근거: src/mcp/features/assets/tools.py

### DESCRIPTION

텍스트·분류·측정 치수로 **모델·2D 자산**을 찾습니다. 원본이 존재하는 변환 대기 모델도 포함하며, 치수 조건 일치는 Scene 내 적합성이나 이격 거리 검증이 아닙니다. 다이어그램은 별도 검색 도구를 사용합니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청한 출력에 식별 필드를 포함합니다. false는 보조 ID를 생략합니다. 이후 도구에 반환된 ID가 필요하면 true를 요청합니다. 이 설정은 추가 세부 그룹을 선택하지 않습니다."
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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- limit은 1–100, offset은 0 이상입니다. source_only 후보의 변환에는 실제 원본 경로·단위·작업 Plan이 필요합니다. 프로젝트 밖 반환 경로는 관리형 입력에 직접 전달하지 않습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "assets": [], // include_ids=true에서 asset_id. source_only는 배치 준비 완료 아님; 필요한 후보에 next_tool/next_step
  "total": 0, // 필터에 일치하는 전체 항목 수
  "limit": 10, // 페이지 최대 항목 수
  "offset": 0, // 현재 페이지 시작 위치
  "truncated": false // true이면 같은 필터로 offset+현재 항목 수부터 계속
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: `get_drawing_asset`으로 후보를 확인하거나 준비된 자산을 `place_drawing_asset`으로 배치할 수 있습니다. 원본 변환은 `prepare_drawing_asset`, 저장 원본 갱신은 `refresh_asset`으로 이어집니다.
코드 1 · 코드 2

# Diagram

다이어그램 자산 검색·배치 · prefix: `diagram-NN_` · 유형 내 순번 01–04

## 31. diagram-01_get

기준 API: `get_diagram_asset`

근거: src/mcp/features/diagrams/tools.py

### DESCRIPTION

알고 있는 **다이어그램 자산의 메타데이터**와 색인된 파일 사용 가능 여부를 확인합니다. 자산을 배치하거나 실제 가져오기·시각적 품질을 검증하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청한 출력에 식별 필드를 포함합니다. false는 보조 ID를 생략합니다. 이후 도구에 반환된 ID가 필요하면 true를 요청합니다. 이 설정은 추가 세부 그룹을 선택하지 않습니다."
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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- 입력한 asset_id는 include_ids=true여도 성공 응답에서 생략되므로 배치에 사용할 값을 보관합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "asset": { // 입력 asset_id는 include_ids=true여도 재출력하지 않음
    "name": "예시 다이어그램", // 저장된 이름
    "file_available": true // 색인 원본 파일 상태. 실제 가져오기·시각적 품질 확인이 아님
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 사용할 자산을 결정했다면 `place_diagram_asset`으로 배치할 수 있습니다. 다른 후보는 `search_diagram_assets`로 찾습니다.
코드 1 · 코드 2

## 54. diagram-02_list

기준 API: `list_diagram_assets`

근거: src/mcp/features/diagrams/tools.py

### DESCRIPTION

사람·나무·기호 등 **별도 다이어그램 라이브러리**를 둘러봅니다. 카탈로그와 파일 상태를 보여주며 모델 자산 검색이나 실제 배치를 수행하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청한 출력에 식별 필드를 포함합니다. false는 보조 ID를 생략합니다. 이후 도구에 반환된 ID가 필요하면 true를 요청합니다. 이 설정은 추가 세부 그룹을 선택하지 않습니다."
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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- 조회 limit은 1–50으로 제한되고 음수 offset은 0으로 보정됩니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "library_id": "diagram_assets", // include_ids=true에서 유지되는 라이브러리 구분자
  "assets": [], // include_ids=true에서 asset_id. 역할/LOD는 drawing, 치수는 dimensions, 파일 정보는 paths
  "total": 0, // 필터에 일치하는 전체 항목 수
  "offset": 0, // 현재 페이지 시작 위치
  "limit": 20, // 페이지 최대 항목 수
  "next_offset": null, // null이 아니면 같은 필터로 offset에 재사용. null이면 마지막 페이지
  "purpose": "2D 벡터 다이어그램 및 선화" // 서버가 실제 반환하는 라이브러리 용도 설명
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: `get_diagram_asset`으로 후보를 자세히 확인하거나 선택한 자산을 `place_diagram_asset`으로 배치할 수 있습니다. 조건으로 찾으려면 `search_diagram_assets`를 사용합니다.
코드 1 · 코드 2

## 63. diagram-03_place

기준 API: `place_diagram_asset`

근거: src/mcp/features/diagrams/tools.py

### DESCRIPTION

관리되는 SVG·DWG·DXF 다이어그램을 편집 가능한 Rhino 문서의 블록 인스턴스로 삽입합니다. 시간 초과는 미삽입을 뜻하지 않으므로 **재시도 전에 문서 상태를 확인**합니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "required": [
    "asset_id"
  ],
  "type": "object"
}
```

**입력 보충 설명(문서용)**

- 위치·회전·축척은 유한값이어야 하며 scale은 양수입니다. 진행 중인 편집·Undo/Redo를 마치고 색인된 asset_id를 사용합니다. 임의 파일 경로는 받지 않습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 해당 처리·항목의 상태
  "asset_id": "example-asset", // 자산 ID
  "object_guid": "00000000-0000-0000-0000-000000000001", // 삽입한 최상위 블록 GUID. get_objects 또는 Scene 구성원 입력에 재사용
  "definition_created": true // 블록 정의 생성 여부. 모델용 연결 필드가 일반 다이어그램에서 항상 반환되지는 않음
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: `get_objects`로 삽입된 인스턴스를 확인하거나 `add_scene_objects`로 의도한 Scene에 포함할 수 있습니다. 실제 뷰에서 위치와 축척도 확인합니다.
코드 1 · 코드 2

## 81. diagram-04_search

기준 API: `search_diagram_assets`

근거: src/mcp/features/diagrams/tools.py

### DESCRIPTION

텍스트·분류·기록된 치수로 **별도 다이어그램 라이브러리**를 검색합니다. 검색 일치는 Scene 내 적합성, 가져오기 성공 또는 시각적 품질을 보증하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청한 출력에 식별 필드를 포함합니다. false는 보조 ID를 생략합니다. 이후 도구에 반환된 ID가 필요하면 true를 요청합니다. 이 설정은 추가 세부 그룹을 선택하지 않습니다."
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
      "description": "connect가 반환한 정확한 실시간 연결 ID입니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- 조회 limit은 1–50으로 제한되고 음수 offset은 0으로 보정됩니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "assets": [], // include_ids=true에서 asset_id. 치수는 dimensions, 역할/LOD는 drawing 그룹 요청
  "total": 0, // 필터에 일치하는 전체 항목 수
  "offset": 0, // 현재 페이지 시작 위치
  "limit": 10, // 페이지 최대 항목 수
  "next_offset": null // null이 아니면 같은 검색 조건의 offset에 재사용. null이면 마지막 페이지
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: `get_diagram_asset`으로 후보를 확인한 뒤 선택한 자산을 `place_diagram_asset`으로 배치할 수 있습니다.
코드 1 · 코드 2

# Drawing

도면 스타일·해치·평면 및 단면 생성 · prefix: `drawing-NN_` · 유형 내 순번 01–06

## 07. drawing-01_apply_style

기준 API: `apply_drawing_style`

근거: src/mcp/features/drawings/tools.py

### DESCRIPTION

도면 레시피의 레이어 계층·색상·출력 선 두께·선종류를 Rhino 문서에 적용합니다. **도면 형상이나 PrintDisplay는 만들거나 변경하지 않습니다.** 선종류 정의 충돌은 변경 전에 거부하며, 시간 초과 후에는 문서 상태를 확인한 뒤 재시도합니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
  "type": "object",
  "required": [
  ]
}
```

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 레이어 적용 완료. 도면 완성·인쇄 검토 완료는 아님
  "recipe_id": "architectural_plan_section_a4_v1",
  "layers": [ // 전체 적용 목록 중 한 항목만 발췌
    {
      "path": "ALMOND-DRAW::SECTION-CUT", // get_objects의 layer_paths 필터로 연결 가능
      "role": "section_cut",
      "layer_index": 1,
      "plot_weight_mm": 0.35,
      "linetype": "Continuous"
    }
  ],
  "review_preparation": { // A4 레시피의 조건부 실제 필드
    "status": "not_executed", // PrintDisplay를 검사하거나 변경하지 않았음
    "message": "…", // 연결 Rhino PID·문서 경로에 맞는 파이프 확인 안내
    "cli": {
      "program": "rhinocode",
      "discovery_arguments": ["list", "--json"],
      "arguments_template": [
        "--rhino", "{matched_pipeId}", "command",
        "_PrintDisplay _Scope=_Document _Viewport=_Model _State=_On _Color=_Print _Viewport=_Layout _State=_On _Color=_Print _DetailBorder=_UsePrintWidth _Enter"
      ] // 해당 문서의 Model/Layout 설정이 이미 확인됐다면 실행 생략
    }
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 적용 레이어의 객체 확인이 필요하면 `get_objects`를 사용합니다. 출력 검토 준비는 반환된 review_preparation 안내를 확인합니다.
코드 1 · 코드 2 · 코드 3

## 33. drawing-02_get_recipe

기준 API: `get_drawing_recipe`

근거: src/mcp/features/drawings/tools.py

### DESCRIPTION

저장된 도면 레시피의 목적과 선택한 상세 설정을 조회합니다. *현재 문서를 검사하거나 레이어·PrintDisplay를 변경하지 않습니다.*

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청한 출력에 식별자 필드를 포함합니다. false이면 보조 ID를 생략합니다. 이후 도구에 반환된 ID가 필요하면 true를 요청합니다. 이 설정은 추가 상세 그룹을 선택하지 않습니다."
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
      "description": "선택 가능한 상세 그룹은 scales, parameters, source, audit, all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별자 포함 여부는 include_ids로 별도 제어합니다."
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

**입력 보충 설명(문서용)**

- `field_groups`: 선택 상세 그룹: scales(권장 축척), parameters(레이어·스타일·review_preparation), source(출처), audit(타임스탬프), all. 생략/빈 배열은 요약이며, ID 포함 여부는 include_ids로 따로 선택합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success",
  "recipe": { // 기본 요약 예시. 입력한 recipe_id는 반복되지 않음
    "name": "Architectural Plan and Section A4",
    "description": "…", // 레시피 자체의 설명 문자열
    "projection": { "type": "parallel" }
    // parameters 그룹: layers·style·review_preparation 등 저장된 설정
    // review_preparation은 실행된 결과가 아님. scales는 recommended_scales 추가
  }
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 선택한 규칙을 문서에 적용하려면 `apply_drawing_style`을 사용합니다.
코드 1 · 코드 2

## 42. drawing-03_get_plan_section_result

기준 API: `get_plan_section_result`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

같은 문서 인스턴스에 보관된 PlanSection 실행 결과를 읽기 전용으로 복구합니다. 결과는 현재 형상 관찰이 아니며, 만료·누락된 응답을 복구하려고 **도면을 재생성하지 않습니다.**

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "0부터 시작합니다. 이후에는 앞 페이지의 next_offset을 그대로 사용합니다."
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

**입력 보충 설명(문서용)**

- `result_id`: `plan_section`의 result.result_delivery=paged 응답에서 얻은 result.result_id입니다. 동일한 바인딩 문서 인스턴스에만 유효합니다.
- `offset`: 첫 페이지는 0, 이후에는 같은 결과의 next_offset을 그대로 사용합니다. UTF-16 코드 단위이며 Python 문자열 길이로 계산하지 않습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success",
  "result_id": "00000000000000000000000000000001", // 같은 문서 인스턴스의 영수증
  "offset": 0,
  "json_chunk": "{\"status\":\"completed\"}", // 전체 객체가 아니라 JSON 문자열 조각
  "total_characters": 22, // UTF-16 코드 단위 길이
  "next_offset": null, // null이면 종료, 아니면 같은 도구의 offset으로 그대로 전달
  "result_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", // 가상 해시
  "observation": "…" // 보관된 실행 결과이며 현재 형상 관찰이 아니라는 안내
  // 조각을 순서대로 합쳐 파싱. 해시는 복원 문자열의 UTF-8 바이트 기준
  // 한 페이지 최대 4096 UTF-16 코드 단위. Python len으로 다음 offset을 계산하지 않음
  // 최대 1시간·최신 8개·총 64 MiB, 재시작/제거로 조기 만료 가능
  // plan_section_result_expired여도 도면이 취소된 것은 아니므로 재생성하지 않음
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 다음 페이지가 있으면 `get_plan_section_result`로 이어 읽고, 모든 조각을 합쳐 원래 결과를 복원합니다.
코드 1 · 코드 2 · 코드 3

## 50. drawing-04_import_hatches

기준 API: `import_drawing_hatch_patterns`

근거: src/mcp/features/drawings/tools.py

### DESCRIPTION

등록된 PAT 도면 자산의 해치 정의를 Rhino 문서에 추가합니다. <u>같은 이름은 덮어쓰지 않고 재사용</u>하며, 해치 객체나 영역을 생성하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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

**입력 보충 설명(문서용)**

- `asset_id`: 관리되는 DrawingAssetfiles에 등록되고 원본 .pat 파일을 사용할 수 있는 도면 자산 ID입니다. 목록/검색의 asset_id는 include_ids=true로 얻습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success",
  "patterns": ["ExamplePattern"], // 신규뿐 아니라 기존에 있어 사용 가능한 패턴 이름도 포함
  "message": "…", // 신규 추가 수와 전체 사용 가능 수를 구분
  "error_trace": null
  // 해치 정의만 추가. 영역·해치 객체 생성이나 도면 축척에서의 외관 확인은 별도
}
```

코드 1 · 코드 2

## 56. drawing-05_list_recipes

기준 API: `list_drawing_recipes`

근거: src/mcp/features/drawings/tools.py

### DESCRIPTION

도면 목적·투영 방식에 따라 저장된 스타일 레시피를 찾습니다. 카탈로그 조회이며 *현재 문서가 레시피를 따르는지 검사하지 않습니다.*

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

```json
{
  "additionalProperties": false,
  "properties": {
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "요청한 출력에 식별자 필드를 포함합니다. false이면 보조 ID를 생략합니다. 이후 도구에 반환된 ID가 필요하면 true를 요청합니다. 이 설정은 추가 상세 그룹을 선택하지 않습니다."
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
      "description": "선택 가능한 상세 그룹은 scales, parameters, source, audit, all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별자 포함 여부는 include_ids로 별도 제어합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- `field_groups`: scales는 권장 축척, source/audit/all은 제공 가능한 추가 필드를 선택합니다. 목록에는 전체 레이어/스타일 설정이 없으며 parameters를 요청해도 새로 채우지 않습니다. 상세 규칙은 `get_drawing_recipe`로 조회합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "total": 1, // 예시 목록 수
  "recipes": [ // include_ids=true, field_groups=["scales"] 예시
    {
      "recipe_id": "architectural_plan_section_a4_v1", // get_drawing_recipe / apply_drawing_style에 재사용
      "name": "Architectural Plan and Section A4",
      "description": "…",
      "projection": "parallel",
      "recommended_scales": ["1:50", "1:100", "1:200"]
    }
  ] // 전체 레이어/스타일은 이 목록의 all에도 추가되지 않으며 get_drawing_recipe에서 확인
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 규칙을 더 살펴보려면 `get_drawing_recipe`, 선택한 스타일을 적용하려면 `apply_drawing_style`을 사용합니다.
코드 1 · 코드 2 · 코드 3

## 65. drawing-06_generate_plan_section

기준 API: `plan_section`

근거: src/mcp/features/modeling/tools.py

### DESCRIPTION

확인된 클리핑 평면에서 모델 공간의 단면·해치·입면 도면을 생성하거나 갱신합니다. Create는 해당 도면을 생성·교체하고 Update는 저장된 배치의 기존 도면만 갱신합니다. Layout·PDF·파일 출력이나 모델 저장은 하지 않습니다. **부분 완료·취소·시간 초과는 롤백이 아니므로 응답 복구를 위해 재실행하지 않습니다.**

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "default": 80,
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
      "default": 45,
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

**입력 보충 설명(문서용)**

- `operation`: Create는 새 도면을 만들거나 해당 클리핑의 기존 로컬 도면을 교체합니다. Update는 저장된 배치의 기존 도면을 갱신하고 없는 도면은 건너뜁니다.
- `points`: Create 전용: 요청한 클리핑 GUID를 문서 단위의 유한 [x,y] 또는 [x,y,z] 절대 도면 원점에 대응시킵니다. 생략한 배치는 저장된 draft_plane 또는 원점을 사용하므로 도면이 겹칠 수 있습니다. Update에서는 생략합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 전체 완료. partial/cancelled는 전체 완료가 아니며 이미 생성한 도면은 남을 수 있음
  "drawing_status": "completed",
  "result": { // 페이지 영수증 분기의 일부 발췌
    "status": "completed",
    "requested": 1,
    "completed": 1,
    "output": "Document",
    "result_delivery": "paged",
    "result_id": "00000000000000000000000000000001", // get_plan_section_result로 복구
    "result_characters": 40000, // 가상 길이, UTF-16 코드 단위
    "result_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", // 가상 해시
    "retention": "…" // 동일 문서·Bridge, 최대 1시간·최신 8개·총 64 MiB 보관 안내
  }
  // 작은 결과는 result.results[]에 직접 반환. paged는 읽어 합친 원래 JSON에서 results[] 확인
  // 각 results[]: clipping_id, name, status와 완료 시 object_ids, report
  // object_ids → get_objects / 캡처 대상. Update의 기존 도면 없음은 skipped 가능
  // report.metadata_conflicts는 최대 64개 표본, metadata_conflict_count는 전체 건수
  // unavailable/미확인 오류·영수증 만료·시간 초과는 롤백이 아니므로 응답 복구용 재실행 금지
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 페이지 영수증은 `get_plan_section_result`로 복구하고, 생성 객체는 `get_objects`나 캡처 도구로 검토합니다.
코드 1 · 코드 2 · 코드 3

# Grasshopper

Grasshopper 로직·캡슐 조회와 실행 · prefix: `grasshopper-NN_` · 유형 내 순번 01–04

## 34. grasshopper-01_get_logic

기준 API: `get_logic_by_id`

근거: src/mcp/features/grasshopper/tools.py

### DESCRIPTION

로컬 Grasshopper 정의의 구성요소·설명·사이드카 메타데이터를 실행 없이 읽습니다. 바이너리 문자열 탐지는 *그래프 평가나 실행 가능성 검증이 아닙니다.*

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청한 출력에 식별자 필드를 포함합니다. false이면 보조 ID를 생략합니다. 이후 도구에 반환된 ID가 필요하면 true를 요청합니다. 이 설정은 추가 상세 그룹을 선택하지 않습니다."
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
      "description": "선택 가능한 상세 그룹은 ports, definition, source, paths, audit, all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별자 포함 여부는 include_ids로 별도 제어합니다."
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

**입력 보충 설명(문서용)**

- `logic_id`: 기존 로컬 파일명의 확장자를 뺀 이름입니다. `list_library`.logic_names[]를 그대로 사용하거나 `list_capsules`의 definition_file에서 경로·마지막 확장자를 제거합니다. 알려진 이름은 바로 사용할 수 있습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "file_name": "example.ghx",
  "components": [
    { "name": "Example component", "category": "Params", "descriptions": ["…"] }
  ],
  "all_descriptions": ["…"],
  "metadata": {} // 원본 메타데이터 생략. 파싱이지 그래프 실행/검증이 아님
  // 유효한 사이드카가 있으면 metadata.capsule에 타입·단위·필수값·출력 의미가 있음
  // 잘못된 계약은 metadata.capsule_errors. 실행은 audited=true인 계약만 가능
  // 중첩 capsule_id를 유지하려면 include_ids=true. inputs는 포트 이름→실제 값으로 구성
  // GHX > GH 순서로 읽으며 JSON만 있는 항목은 metadata만 반환
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 유효한 캡슐 계약이 있고 실행 감사가 확인되면 `run_gh_definition`으로 계산할 수 있습니다.
코드 1 · 코드 2 · 코드 3

## 51. grasshopper-02_list_capsules

기준 API: `list_capsules`

근거: src/mcp/features/grasshopper/tools.py

### DESCRIPTION

기능별 Grasshopper 캡슐을 찾아 실행 감사 여부를 구분합니다. **audited는 실행 허용 조건이지 공학적 신뢰도 인증이 아닙니다.** 최대 50개를 반환하며 추가 페이지를 요청하는 입력은 없습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청한 출력에 식별자 필드를 포함합니다. false이면 보조 ID를 생략합니다. 이후 도구에 반환된 ID가 필요하면 true를 요청합니다. 이 설정은 추가 상세 그룹을 선택하지 않습니다."
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
      "description": "선택 가능한 상세 그룹은 ports, definition, source, paths, audit, all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별자 포함 여부는 include_ids로 별도 제어합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- `field_groups`: ports는 입력/출력 포트 이름, definition 또는 paths는 definition_file, source/audit/all은 제공 가능한 추가 정보를 선택합니다. 이 카드의 ports에는 타입·단위·기본값이 없습니다. IDs는 include_ids로 별도 선택합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "total": 1,
  "offset": 0,
  "limit": 50,
  "next_offset": null, // 공개 입력에 offset이 없어 추가 페이지를 직접 요청할 수 없음
  "capsules": [ // include_ids=true, field_groups=["ports","definition"]의 가상 카드
    {
      "capsule_id": "example-capsule", // audited=true일 때 run_gh_definition에 사용 가능
      "capability": "analyze",
      "structure_type": "beam",
      "definition_file": "example.ghx", // 경로·확장자를 뺀 로컬 이름 → get_logic_by_id
      "title": "Example capsule",
      "audited": true, // 실행 허용 조건이며 공학 인증이 아님
      "inputs": ["ALMOND_IN_example"], // 이름만 있음. 타입·단위·필수값은 여기서 확인할 수 없음
      "outputs": ["ALMOND_OUT_example"]
    }
  ]
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 계약의 타입·단위는 `get_logic_by_id`로 확인하고, 실행 가능한 캡슐은 `run_gh_definition`으로 계산합니다.
코드 1 · 코드 2 · 코드 3

## 57. grasshopper-03_list_library

기준 API: `list_library`

근거: src/mcp/features/grasshopper/tools.py

### DESCRIPTION

기존 로컬 색인에서 조회 가능한 Grasshopper 로직 이름을 찾습니다. *색인에 있다는 사실은 실행 감사나 계산 성공을 뜻하지 않습니다.*

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

```json
{
  "additionalProperties": false,
  "properties": {
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "요청한 출력에 식별자 필드를 포함합니다. false이면 보조 ID를 생략합니다. 이후 도구에 반환된 ID가 필요하면 true를 요청합니다. 이 설정은 추가 상세 그룹을 선택하지 않습니다."
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
      "description": "선택 가능한 상세 그룹은 ports, definition, source, paths, audit, all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별자 포함 여부는 include_ids로 별도 제어합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "total_entries": 1,
  "logic_names": ["example-logic"], // 기본 응답에서도 get_logic_by_id.logic_id로 사용 가능
  "logic_count": 1 // include_ids=false에서 logic_ids 대신 추가됨
  // include_ids=true면 logic_ids가 유지되고, paths 그룹은 library_dir를 추가
  // 색인 존재는 실행 감사·플러그인 준비·계산 성공의 증거가 아님
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 정의 내용을 읽으려면 `get_logic_by_id`, 실행 가능한 캡슐을 찾으려면 `list_capsules`를 사용합니다.
코드 1 · 코드 2 · 코드 3

## 77. grasshopper-04_run_definition

기준 API: `run_gh_definition`

근거: src/mcp/features/grasshopper/tools.py

### DESCRIPTION

실행 감사를 통과한 Grasshopper 캡슐을 Rhino에서 계산하고 선언된 출력을 반환합니다. 단위는 자동 변환하지 않으며 정의에 따라 문서에 형상을 베이크할 수 있습니다. **시간 초과는 미실행이나 롤백의 증거가 아닙니다.**

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "ALMOND_IN_* 포트 이름을 값에 대응시키는 객체입니다. 형식은 위 설명을 참조합니다."
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
      "default": 60,
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

**입력 보충 설명(문서용)**

- `inputs`: 정확한 ALMOND_IN_* 포트 이름→값 매핑입니다. 유효한 캡슐 계약의 타입·단위·필수 여부를 따릅니다. 형상 타입은 현재 문서 객체를 참조하는 {"guids":["<object-guid>",...]}만 받으며, 일반형은 number/integer/string/bool 및 지원되는 number[]/integer[]/string[]의 중첩 없는 배열입니다. 알 수 없는 포트·필수값 누락·지원되지 않는 타입은 거부하고 생략한 선택 포트는 정의 기본값을 사용합니다.
- `timeout_s`: 솔버 시간 한도(초), 0 초과 600 이하이며 기본값은 60입니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "ok", // 네이티브 실행 성공. 사전 검증/네이티브 실패는 error
  "capsule_id": "example-capsule",
  "outputs": {}, // ALMOND_OUT_*별 값 생략. 의미·타입·단위는 해당 캡슐 계약에 따름
  "baked_guids": ["00000000-0000-0000-0000-000000000001"], // 생성 객체 관찰·캡처에 재사용
  "analysis_method": "template",
  "confidence": "medium", // 매니페스트 선언: api/high, template/medium, rule_based/low
  "warnings": [],
  "error": null
  // confidence는 독립 검증이나 안전 확률이 아님. rule_based는 FEA가 아닌 추정
  // 다른 캡슐의 형상 입력은 해당 계약에 맞춰 {"guids":[...]}로 구성
  // 이미 반환된 객체 ID를 얻으려고 재실행하지 않음. 시간 초과는 롤백의 증거가 아님
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 베이크된 형상은 `get_objects`로 확인하거나 캡처 도구로 검토합니다. 다른 캡슐 연결은 출력 의미·타입·단위가 맞을 때만 사용합니다.
코드 1 · 코드 2 · 코드 3

# Research

구법·건축 유형·참고자료 조사 · prefix: `research-NN_` · 유형 내 순번 01–03

## 27. research-01_get_construction_guidance

기준 API: `get_construction_guidance`

근거: src/mcp/features/guidance/tools.py

### DESCRIPTION

로컬 구법 라이브러리에서 구조 시스템과 예비 경간·부재 깊이·조립 방식을 비교합니다. **경험칙 기반 안내이며 구조 내력 검증이 아닙니다.** 요청 없이 시공 상세 작업을 시작하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "default": 0,
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
      "description": "요청한 출력에 식별자 필드를 포함합니다. false이면 보조 ID를 생략합니다. 이후 도구에 반환된 ID가 필요하면 true를 요청합니다. 이 설정은 추가 상세 그룹을 선택하지 않습니다."
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
      "description": "선택 가능한 상세 그룹은 rules, narrative, source, metadata, audit, all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별자 포함 여부는 include_ids로 별도 제어합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- `span_m`: 미터 단위의 검토 경간입니다. 양수이고 시스템의 유효 경간 상한이 있을 때 fits_span과 depth_guidance가 계산됩니다. 벽 시스템의 span_axis가 수직이면 비지지 높이로 해석합니다.
- `include_reference_data`: 활하중(kPa)·밀도(kg/m³) 등 라이브러리 참고값을 추가합니다. 전체 kN 하중으로 사용할 때는 적용 면적·체적에 맞게 변환해야 합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "total": 1,
  "source": "…", // 예비 치수 산정용 라이브러리 출처
  "systems": [ // include_ids=true, field_groups=["rules"]의 query="wood-joist-floor", span_m=4.8 예시
    {
      "system_id": "wood-joist-floor", // typology의 construction_system 또는 재료 메타데이터로 연결
      "name": "Wood joist floor (dimension lumber)",
      "category": "floor",
      "structural_material": "Wood",
      "fits_span": true, // 입력 span_m과 경험칙 범위 비교이지 내력 판정이 아님
      "depth_guidance": [
        { "element": "joist", "suggested_depth_mm": 300, "rule": "span/16" }
      ],
      "construction_detail": "Wood joist floor (dimension lumber)",
      "construction_reference": { "kind": "construction_system", "id": "wood-joist-floor" },
      "render_material_ids": ["wood-oak"] // 의도한 유효 재료 하나를 assign_material에 선택
    }
  ]
  // assign_material로 구법 메타데이터를 기록하려면 attach_metadata=true와 실제 객체 GUID 필요
  // include_ids=false면 중첩 construction_reference.id·render_material_ids도 사라짐
  // include_reference_data의 kPa·kg/m³ 값을 전체 kN 하중으로 복사하지 않고 면적·체적에 맞게 환산
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 구법의 역사적 맥락은 `get_typology_narrative`로 확인하고, 선택한 재료·구법 정보는 `assign_material`로 객체에 기록할 수 있습니다.
코드 1 · 코드 2 · 코드 3

## 48. research-02_get_typology_narrative

기준 API: `get_typology_narrative`

근거: src/mcp/features/guidance/tools.py

### DESCRIPTION

로컬 역사 라이브러리에서 건축 유형의 서사·선례·도시적 역할을 찾습니다. 역사적 맥락을 위한 자료이며 *프로젝트의 하중·부재 치수·내력 근거는 아닙니다.*

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청한 출력에 식별자 필드를 포함합니다. false이면 보조 ID를 생략합니다. 이후 도구에 반환된 ID가 필요하면 true를 요청합니다. 이 설정은 추가 상세 그룹을 선택하지 않습니다."
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
      "description": "선택 가능한 상세 그룹은 rules, narrative, source, metadata, audit, all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별자 포함 여부는 include_ids로 별도 제어합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- `limit`: 반환할 최대 항목 수이며 기본값은 5입니다. 실제 적용 최솟값은 1입니다.
- `field_groups`: narrative는 서사·선례·도시적 역할·관련 구법 목록, source는 gha_ref 등 출처를 추가합니다. 기본 요약은 name·era·region이며 typology_id는 include_ids=true에서 유지됩니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "total": 1, // limit를 적용하기 전 전체 일치 수
  "entries": [ // include_ids=true, field_groups=["narrative"]의 가상 카드
    {
      "typology_id": "example-typology",
      "name": "예시 건축 유형",
      "era": "예시 시대",
      "region": "예시 지역",
      "narrative": "…",
      "urban_role": "…",
      "related_construction_systems": ["example-system"] // get_construction_guidance의 query로 검색 가능
    }
  ],
  "source": "…"
  // source 그룹은 gha_ref 등 출처, narrative 그룹은 선례·서사 등을 추가
  // related_construction_systems는 현재 키 필터상 include_ids=false여도 남음
  // 역사적 맥락이지 프로젝트의 치수·하중·내력 근거가 아님
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 관련 구법을 더 비교하려면 `get_construction_guidance`를 사용합니다.
코드 1 · 코드 2 · 코드 3

## 80. research-03_search_details

기준 API: `search_detail_sources`

근거: src/mcp/features/guidance/tools.py

### DESCRIPTION

선별된 건축 자료 디렉터리의 메타데이터를 오프라인으로 검색합니다. 외부 상세 콘텐츠를 가져오거나 프로젝트 근거로 검증하지 않으므로 **실제 자료와 재사용 권리를 따로 확인합니다.**

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "요청한 출력에 식별자 필드를 포함합니다. false이면 보조 ID를 생략합니다. 이후 도구에 반환된 ID가 필요하면 true를 요청합니다. 이 설정은 추가 상세 그룹을 선택하지 않습니다."
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
      "description": "선택 가능한 상세 그룹은 rules, narrative, source, metadata, audit, all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별자 포함 여부는 include_ids로 별도 제어합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- `query`: 디렉터리 제목·태그·형식에 맞는 검색어입니다. 비우면 전체 출처를 나열합니다. 영어 카탈로그 용어를 권장하며 일부 한국어 용어만 정해진 영어 표현으로 확장합니다.
- `field_groups`: source는 URL·형식·접근 안내를 추가합니다. 실제 자료의 terms_url·redistribution·generation_use까지 필요하면 all을 선택합니다. 기본값은 title·matched_terms 등 요약입니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success",
  "query": "timber",
  "query_terms": ["timber"],
  "expanded_terms": [],
  "sources": [ // include_ids=true, field_groups=["all"], 일치 목록 중 하나 발췌
    {
      "source_id": "dataholz",
      "title": "dataholz timber assemblies",
      "url": "https://www.dataholz.eu/en/index.htm",
      "terms_url": "https://www.dataholz.eu/allgemeine-nutzungsbedingungen.htm", // all에서 유지
      "formats": ["web", "pdf"],
      "access": "공개 참고자료",
      "redistribution": "제한됨. 개별 항목 검토 필요", // all에서 유지
      "generation_use": "candidate_only", // all에서 유지. 프로젝트 출처로 검증된 자료가 아님
      "matched_terms": ["timber"]
    }
  ],
  "scope": "…" // 선별 디렉터리 검색 범위. 외부 콘텐츠를 가져온 결과가 아님
  // source 그룹만으로는 terms_url·redistribution·generation_use가 보존되지 않음
  // URL·접근·재사용 권리는 실제 출처에서 확인해야 함
}
```

코드 1 · 코드 2 · 코드 3

# Analysis

구조·피난 검토와 보고서 · prefix: `analysis-NN_` · 유형 내 순번 01–05

## 12. analysis-01_check_egress

기준 API: `check_egress`

근거: src/mcp/features/egress/tools.py

### DESCRIPTION

제공된 층 경계·출구·경로 측정값으로 피난 조건을 예비 검토합니다. Rhino 형상이나 경로를 추론하지 않으며, **전체 통과는 실행된 검사에만 해당합니다.** 단순화된 참고 규칙이므로 적용 법규 인증으로 사용하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "default": 0,
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
      "default": 0,
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

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "passed": false, // 실제 수행한 검사만 합산. 빠진 경로 검사를 통과한 것이 아님
  "occupancy": "business",
  "occupant_load": 65, // ceil(600 / business 9.3 m²/인)
  "area_m2": 600,
  "gross_area_m2": 600, // 경계 직사각형 면적이지 불규칙 바닥의 실측 면적은 아님
  "checks": [ // 검사 목록 중 하나 발췌
    {
      "check": "exit_count", // 개수 또는 check 이름에 표시된 m/mm 단위를 확인
      "required": 2,
      "provided": 1,
      "passed": false,
      "basis": "…" // 해당 비교의 근거
    }
  ],
  "warnings": [], // 다른 용도에도 업무시설 보행거리 기준을 쓴 경우 등 경고
  "source_note": "…"
  // 보행거리 미입력·dead_end_m 비양수면 해당 검사 생략. 출구 이격은 가장 먼 두 출구 비교
  // net_area_m2는 재실 면적만 변경하며 이격 검토의 바닥 대각선은 변경하지 않음
  // 지역별 실제 법규 검토를 대체하지 않음
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 미달 항목의 배치·너비·경로를 수정하고 측정값을 갱신한 뒤 `check_egress`로 다시 검토합니다.
코드 1

## 22. analysis-02_export_structural_report

기준 API: `export_structural_report`

근거: src/mcp/features/structure/tools.py

### DESCRIPTION

저장된 구조 검증 이력을 최신순 Markdown 보고서로 작성합니다. 새 해석을 하지 않으며 **대상 파일을 덮어쓸 수 있습니다.** 저장된 이력은 과거 실행의 요약이지 현재 모델의 검증 결과가 아닙니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- `limit`: 포함할 최대 실행 개수이며 기본값은 50입니다. 1..500 범위로 보정됩니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success",
  "path": ".almond/produced/example/structure-report.md", // 작성된 Markdown 파일
  "runs": 1, // 실제 포함한 저장 실행 수
  "latest_method": "native" // 가장 최근 저장된 실행 방식
  // 새 해석 아님. 과거 pass/fail의 best-effort 저장 이력을 읽으며 누락 가능
  // 원래 결과의 모든 설정·부재 상세를 보존하지 않으며 error/indicative는 이 기록 경로에서 제외
  // 이력이 비면 오류. 보고서의 고정 해석 설명은 현재 엔진 구현과 따로 확인
  // 부모 폴더를 만들고 같은 경로의 기존 파일을 덮어씀
}
```

코드 1 · 코드 2 · 코드 3

## 52. analysis-03_list_design_codes

기준 API: `list_design_codes`

근거: src/mcp/features/structure/tools.py

### DESCRIPTION

구조 해석에 사용할 설계기준 프로필과 값의 검증 상태를 조회합니다. 프로필의 verified는 **프로젝트의 법규 준수나 구조 안전 승인이 아닙니다.**

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

```json
{
  "additionalProperties": false,
  "properties": {
    "include_ids": {
      "default": false,
      "type": "boolean",
      "description": "요청한 출력에 식별자 필드를 포함합니다. false이면 보조 ID를 생략합니다. 이후 도구에 반환된 ID가 필요하면 true를 요청합니다. 이 설정은 추가 상세 그룹을 선택하지 않습니다."
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
      "description": "선택 가능한 상세 그룹은 parameters, source, audit, all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별자 포함 여부는 include_ids로 별도 제어합니다."
    },
    "connection_id": {
      "type": "string",
      "minLength": 1,
      "description": "생략하면 connect/start_session으로 선택한 연결을 사용합니다. 이 호출만 다른 연결에 보내려면 list_connections의 connection_id를 입력합니다."
    }
  },
  "type": "object",
  "required": [
  ]
}
```

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "default": "eurocode",
  "profiles": [ // include_ids=true, field_groups=["parameters"]의 일부 발췌
    {
      "id": "eurocode", // validate_structure / visualize_structure의 design_code에 사용
      "name": "…",
      "basis": "…",
      "verified": true, // 프로필 값 검증이며 프로젝트의 법규 준수/구조 승인과 다름
      "unverified": [],
      "deflection_limit_ratio": 250, // L/250. visualize_structure의 동일 입력에 사용 가능
      "imposed_floor_kn_m2": {} // 실제 프로필 권장값 생략. 모델에 이미 적용된 하중은 아님
    }
  ],
  "problems": [], // 로딩 중 거부된 사용자 프로필 문제
  "user_dir": "…"
  // parameters는 ULS 선택지도 표시. 목록 카드에는 values 전체를 생성하지 않음
  // off는 무계수 계산이지만 참고 처짐 한계 L/250은 유지
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 선택한 기준은 `validate_structure` 또는 `visualize_structure`에서 사용할 수 있습니다.
코드 1 · 코드 2 · 코드 3

## 91. analysis-04_validate_structure

기준 API: `validate_structure`

근거: src/mcp/features/structure/tools.py

### DESCRIPTION

현재 Rhino 구조 형상을 지정한 하중·지지·접합·설계기준 가정으로 해석합니다. 형상은 편집하지 않습니다. 엔진의 적용 범위와 경고를 확인해야 하며, 규칙 기반 추정·참고용 내력·높은 confidence를 **구조 안전 인증으로 해석하지 않습니다.**

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "default": 10,
      "type": "number",
      "description": "적용 하중(kN)입니다. 기본값은 10.0입니다."
    },
    "material": {
      "default": "Steel",
      "type": "string",
      "description": "재료 유형: \"Steel\", \"S355\", \"Concrete\", \"Wood\", \"Aluminium\". 기본값은 \"Steel\"입니다."
    },
    "engine": {
      "default": "auto",
      "type": "string",
      "description": "\"auto\" | \"native\" | \"karamba\" 중 하나입니다. 위 설명을 참조합니다."
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
      "description": "배치된 라이브러리 자산이 프레임 위에 놓이거나 프레임에 매달린 위치에 중력 하중을 추가합니다. 각 자산의 하중 항목에 따른 추정 자중과 사용 중 내용물/재실자 하중을 포함합니다(예: 물이 채워진 욕조). 배치는 Almond 자산 ID로 태그된 Rhino 객체에서 가져옵니다. 네이티브 엔진 전용입니다. 결과의 \"asset_loads\"에는 각 배치의 하중과 하중을 지지하는 부재 또는 적용하지 않은 이유가 나열됩니다."
    },
    "floor_load_kn_m2": {
      "default": 0,
      "type": "number",
      "description": "한 층에서 보로 둘러싸인 모든 구획에 적용할 부과 바닥 하중(kN/m2)입니다(예: 주거용 2.0, EN 1991-1-1의 category A). 보는 45도 분배 규칙에 따라 하중을 받습니다(2방향, 장단변비 2:1 초과 시 1방향). 네이티브 엔진 전용입니다. 설계기준의 바닥 하중에는 이동 가능한 가구와 사람이 이미 포함되므로, asset_loads는 무거운 특정 물품에 대해서만 함께 사용하고 중복 계산을 피하려면 load_kn을 0으로 설정합니다."
    },
    "floor_dead_kn_m2": {
      "default": 0,
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
      "description": "네이티브 엔진 전용입니다. \"members\"와 \"supports\"를 추가합니다. \"members\"는 부재별 역할, 길이, 단면, ULS 설계 단면력 N/V/M/T, 지배 조합과 검토 항목, 세장비, chi, 응력, 사용률, SLS 처짐과 경간/처짐 비, 핀 접합 단부를 포함합니다. \"supports\"는 SLS와 각 ULS 조합의 반력 Fx..Mz를 포함합니다. 응답을 짧게 유지하도록 기본적으로 꺼져 있습니다."
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

**입력 보충 설명(문서용)**

- `load_kn`: 전체 부과하중(kN), 기본값 10입니다. 네이티브 엔진에서는 자유 절점에 균등 분배하는 하향(-Z) 하중입니다. 바닥 활하중·자산 내용물 하중과 겹치지 않게 산정하며 필요한 경우 0으로 둡니다.
- `engine`: auto는 지원되는 선 모델에 네이티브 프레임 해석을 시도하고 비지원 유형·내보내기 문제에는 Karamba 경로를 사용할 수 있습니다. native는 네이티브를 강제하며, karamba는 해당 런타임 경로(api/template/rule_based)를 사용합니다. 실제 경로와 경고는 응답에서 확인합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "pass", // 가상 네이티브 예시. 실제 상태는 pass/fail/indicative/error
  "passed": true, // indicative인 경우 null 가능. 구조 안전 인증을 뜻하지 않음
  "structure_type": "beam",
  "material": "Steel",
  "confidence": "high", // 경고·가정·미검증 값과 함께 해석
  "results": {
    "analysis_method": "native",
    "max_deflection_mm": 12,
    "deflection_limit_mm": 24,
    "span_m": 6,
    "utilization_ratio": 0.72,
    "per_element_utilization": [ // 최상위가 아니라 results 안에 있음
      {
        "source_guids": ["00000000-0000-0000-0000-000000000001"], // 표시 대상 display_guids로 재사용 가능
        "utilization": 0.72,
        "combination": "…"
      }
    ]
  },
  "worst_member_guids": ["00000000-0000-0000-0000-000000000001"], // 상위 최대 5개, 전체 해석 범위 아님
  "warnings": [],
  "assumptions": ["…"],
  "design_code": { "id": "eurocode", "unverified": [] } // 실제 객체의 일부 발췌
  // detail=true: 최상위 members/supports 추가. 엔진마다 상세 필드가 다를 수 있음
  // construction_check가 있으면 경간/깊이 경험칙 비교이지 내력 증거가 아님
  // Karamba 대체 경로는 바닥/자산 하중이나 계수를 적용하지 않을 수 있어 경고 확인
  // 비강재 indicative·규칙 기반 추정·횡비틀림좌굴 제외 등 해석 한계를 함께 보고
  // pass/fail의 기록에 성공한 경우에만 export_structural_report 이력으로 이어짐
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 문제 부재는 `get_objects`로 확인하거나 `visualize_structure`로 검토합니다. 저장된 검증 이력이 필요하면 `export_structural_report`를 사용합니다.
코드 1 · 코드 2 · 코드 3

## 92. analysis-05_visualize_structure

기준 API: `visualize_structure`

근거: src/mcp/features/structure/tools.py

### DESCRIPTION

구조 형상을 해석해 변형·사용률·좌굴의 임시 뷰포트 오버레이를 표시합니다. 객체를 베이크하지 않지만 뷰포트 상태는 바뀝니다. **재계산 없는 표시 변경은 수정된 형상·하중 검증이 아니며**, 과장된 변형이나 좌굴 모드를 실제 형상으로 해석하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "default": 10,
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
      "default": 1,
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
      "default": 0,
      "type": "number",
      "description": "한 층에서 보로 둘러싸인 모든 구획에 적용할 부과 바닥 하중(kN/m2)입니다(예: 주거용 2.0, EN 1991-1-1의 category A). 보는 45도 분배 규칙에 따라 하중을 받습니다(2방향, 장단변비 2:1 초과 시 1방향). 네이티브 엔진 전용입니다. 설계기준의 바닥 하중에는 이동 가능한 가구와 사람이 이미 포함되므로, asset_loads는 무거운 특정 물품에 대해서만 함께 사용하고 중복 계산을 피하려면 load_kn을 0으로 설정합니다."
    },
    "floor_dead_kn_m2": {
      "default": 0,
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
  "type": "object",
  "required": [
  ]
}
```

**입력 보충 설명(문서용)**

- `guids`: 구조 축선 곡선과 지점 표시 점의 현재 Rhino GUID입니다. 점이 없으면 최하단 절점을 지점으로 사용합니다. clear=true가 아니라면 reanalyze=false여도 비어 있지 않은 목록이 필요합니다.
- `reanalyze`: 기본값 true는 해석을 갱신합니다. false는 이전 뷰 해석 결과를 재사용해 표현만 바꾸므로 형상·하중이 달라졌다면 검증에 사용할 수 없습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "pass", // 가상 해석 예시. fail/indicative/error 가능, clear=true 성공은 cleared
  "analysis_method": "native",
  "max_displacement_mm": 12,
  "deflection_limit_mm": 24,
  "span_m": 6,
  "max_utilization": 0.72,
  "scale": 30, // 실제 변위가 아닌 표시 과장 배율
  "elements": [ // validate_structure의 results.per_element_utilization과 경로가 다름
    {
      "source_guids": ["00000000-0000-0000-0000-000000000001"], // display_guids 또는 객체 관찰에 재사용
      "max_displacement_mm": 12,
      "utilization": 0.72
    }
  ],
  "nodes": 2,
  "warnings": []
  // display_guids는 표시만 제한. guids에는 전체 해석 범위·지점 유지
  // reanalyze=false는 이전 뷰 계산 재사용이며 변경된 형상/하중 검증이 아님
  // buckling 뷰는 buckling/생성된 passed를 추가하고 max_displacement_mm 제거
  // alpha_cr>1만으로 모드 pass 가능. 1<alpha_cr<10은 횡변위 민감, >=10은 1차 해석 기준
  // 시각화 자체는 validate_structure의 보고서 이력으로 저장되지 않음
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 관심 부재는 `get_objects`로 확인하거나 `visualize_structure`에서 표시만 좁힐 수 있습니다. 검증 이력에 남길 판정은 `validate_structure`로 수행합니다.
코드 1 · 코드 2 · 코드 3

# Exchange

앱 간 자산 교환·Chestnut 게시 · prefix: `exchange-NN_` · 유형 내 순번 01–05

## 21. exchange-01_export_asset_contract

기준 API: `export_asset_contract`

근거: src/mcp/features/exchange/tools.py

### DESCRIPTION

선택한 Rhino 객체를 GLB와 Almond 자산 계약 파일로 내보냅니다. **같은 폴더의 동일 자산 파일을 덮어쓸 수 있으며**, 계약은 기록된 의미만 보존하므로 임의의 Rhino 데이터나 수신 앱의 완전한 복원을 보장하지 않습니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success",
  "asset_id": "example-asset",
  "glb_path": ".almond/produced/example/example-asset.glb",
  "contract_path": ".almond/produced/example/example-asset.almond.json", // import_asset_contract에 전달
  "dimensions_mm": { "width": 1000, "depth": 500, "height": 800 }, // 가상 측정 치수(mm)
  "materials": [], // 인식된 Almond 재료 그룹. 비어 있어도 모든 재료가 보존됐다는 뜻은 아님
  "next_step": "대상 Rhino로 가져오려면 반환된 contract_path를 import_asset_contract에 전달하고 mm 단위 배치를 선택합니다. 내보내기만으로 추가 가져오기를 요청한 것은 아닙니다. …"
  // next_step은 실제 안내 필드이며 제안 next_step_guide와 다름
  // 계약·GLB를 함께 유지. 다른 컴퓨터로 자동 전송되거나 모든 앱에서 자동 복원되는 것은 아님
  // 계약 기본 앵커는 하단 중앙, 지지는 바닥, 여유 공간은 0
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 대상 Rhino로 가져오려면 `import_asset_contract`를 사용합니다. 내보내기만 요청된 경우 추가 가져오기는 하지 않습니다.
코드 1 · 코드 2 · 코드 3

## 26. exchange-02_get_blender_script

기준 API: `get_blender_helper_script`

근거: src/mcp/features/exchange/tools.py

### DESCRIPTION

Blender의 선택 형상 내보내기 또는 지정 객체 재료 설정을 위한 Python 코드를 생성합니다. **코드를 실행하지 않으며** 실행 시 내보내기는 파일을 쓰고 재료 설정은 일치 객체의 재료 슬롯을 교체합니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "보조 식별자 필드를 포함합니다. 입력한 대상 ID는 반복하지 않습니다."
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

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success", // 코드 생성 완료이며 Blender 실행 완료가 아님
  "action": "export",
  "script": "<생성된 Blender Python 소스>" // 코드 본문 생략. 기본 응답에 항상 유지
  // notes/all이면 export의 note도 표시. materials도 동일하게 script를 반환
  // export 실행: 선택한 메시/곡선/서피스를 측정해 GLB·계약 파일 작성
  // 성공 실행 stdout의 ALMOND_CONTRACT 경로 → 접근 가능한 대상 Rhino의 import_asset_contract
  // materials 실행: 일치 객체의 재료 슬롯 교체. 생성만으로는 실행되지 않음
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 생성 코드는 Blender 실행 도구에서 실행합니다. 내보내기 실행이 성공한 뒤 얻은 계약은 `import_asset_contract`로 Rhino에 가져올 수 있습니다.
코드 1 · 코드 2 · 코드 3

## 49. exchange-03_import_asset_contract

기준 API: `import_asset_contract`

근거: src/mcp/features/exchange/tools.py

### DESCRIPTION

Almond 계약과 GLB를 Rhino 문서로 가져와 인식 가능한 재료·메타데이터·앵커 배치를 복원합니다. 모든 원본 정보를 복구하는 것은 아니며, **복원·배치 오류 뒤에도 가져온 객체가 남을 수 있으므로 확인 없이 재가져오지 않습니다.**

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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

**입력 보충 설명(문서용)**

- `contract_path`: `export_asset_contract`가 반환한 계약 경로 또는 실제 Blender export 실행 후 얻은 계약 경로입니다. 계약과 참조 GLB 파일이 함께 접근 가능해야 합니다.
- `x_mm / y_mm / z_mm`: 문서 단위와 관계없이 밀리미터 배치 좌표입니다. rotation_degrees는 월드 Z축 회전이며 layer가 없으면 생성됩니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success",
  "asset_id": "example-asset",
  "source_app": "blender",
  "imported_count": 1,
  "imported_guids": ["00000000-0000-0000-0000-000000000001"], // 객체 관찰·캡처·재료 보정에 재사용
  "metadata_restored": 1, // 메타데이터를 기록한 객체 수
  "materials_deduplicated": 0,
  "unknown_material_ids": [], // 유효한 assign_material ID로 그대로 쓰지 않음
  "dimension_check": {
    "status": "ok", // mismatch/unknown 가능. 시각적 정확성 보장은 아님
    "expected_sorted_mm": [500, 800, 1000],
    "measured_sorted_mm": [500, 800, 1000],
    "worst_relative_error": 0,
    "tolerance": 0.02 // 축별 크기를 정렬해 2% 비교. 회전 후 월드 경계 크기는 달라질 수 있음
  },
  "layer": "ALMOND-EXCHANGE"
  // 복원/배치 오류에도 imported_guids가 남을 수 있음. 재가져오기 전 기존 객체를 확인
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 가져온 객체는 `get_objects`나 캡처 도구로 확인하고, 필요한 재료 보정은 `assign_material`로 수행합니다.
코드 1 · 코드 2 · 코드 3

## 68. exchange-04_publish_chestnut_advanced

기준 API: `publish_objects_to_chestnut`

근거: src/mcp/features/publishing/tools.py

### DESCRIPTION

선택한 Rhino 객체를 지정한 물리·콜라이더 설정의 GLB로 Chestnut에 게시합니다. 형상과 **원본 문서 경로·GUID 등 메타데이터가 업로드**되며 같은 자산 ID는 기존 자산을 갱신합니다. 네트워크 결과가 불확실하면 서비스 상태를 확인한 뒤 재시도합니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "default": 0,
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

**입력 보충 설명(문서용)**

- `asset_id`: 후속 갱신에 유지할 Chestnut 자산 ID입니다. 생략하면 이름 슬러그와 문서 경로·정렬된 내보낸 객체 GUID의 해시로 생성합니다. 영문자·숫자·점·밑줄·하이픈 1..80자만 허용합니다.
- `mass`: kg 단위의 음이 아닌 질량입니다. static이면 0으로 기록하며, 다른 body_type에서 0이면 1 kg으로 보정합니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success",
  "success": true, // 원격 /api/props/upsert 응답에서 온 값
  "chestnut_url": "https://chestnut-mnvo.onrender.com"
  // 원격 응답의 추가 키는 그대로 병합되며 동일 키를 덮어쓸 수도 있음
  // 고정 asset_id 반환 필드는 이 코드에서 보장되지 않음
  // 갱신할 때는 실제 원격에서 확인한 ID 또는 명시한 요청 asset_id를 보관해 사용
  // 성공은 서비스 수신 확인이지 외관·물리·콜라이더 거동 검증이 아님
  // 원본 문서 경로·GUID·문서 serial·단위·경계도 업로드됨
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 게시 결과는 Chestnut에서 확인하고, 후속 갱신에는 실제 확인한 자산 ID를 재사용합니다.
코드 1

## 69. exchange-05_publish_chestnut

기준 API: `publish_to_chestnut`

근거: src/mcp/features/publishing/tools.py

### DESCRIPTION

선택한 Rhino 객체를 간단한 동작 프리셋으로 Chestnut에 게시합니다. 형상과 **원본 문서 경로·GUID 등을 업로드**하며 같은 자산 ID는 기존 자산을 갱신합니다. 성공은 외관·시뮬레이션 검증이 아니고, 불확실한 네트워크 결과는 재시도 전에 확인합니다.

### TOOL INPUT

현재 inputSchema (description만 한국어 번역).

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
      "description": "선택적인 안정적 연결 ID입니다. 생략하면 결정적인 Rhino 연결을 사용합니다."
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

**입력 보충 설명(문서용)**

- `behavior`: architecture=static, object=dynamic, animated=kinematic입니다. 모두 실제 축척 유지·box 콜라이더를 사용합니다. auto는 형상이 아니라 asset_name의 영어 단어로 architecture/object를 선택합니다. animated는 애니메이션을 생성하지 않습니다. static 외 질량은 하위 도구에서 1 kg으로 보정됩니다.
- `asset_id`: 기존 Chestnut 자산을 갱신할 때 확인한 ID입니다. 생략하면 문서 경로·객체 GUID·이름 슬러그로 결정적 ID를 만듭니다. 응답에 동일 이름의 asset_id 키가 항상 존재한다고 가정하지 않습니다.

### TOOL OUTPUT

현재 코드 기반 예시(실측 아님·일부 발췌). //는 실제 응답에 없는 문서용 주석.

```json
{
  "status": "success",
  "success": true, // 하위 publish_objects_to_chestnut의 원격 응답을 그대로 반환
  "chestnut_url": "https://chestnut-mnvo.onrender.com"
  // 추가 키와 자산 ID의 정확한 키/존재는 원격 계약에 따름
  // 실제 확인한 자산 ID 또는 요청 asset_id를 유지해 후속 갱신에 사용
  // animated는 kinematic 바디 선택이지 애니메이션 생성이 아님
  // 성공은 외관·시뮬레이션 검증이 아니며 불확실한 게시 결과는 재시도 전 확인
}
```

**후속 안내 제안 · 서버 미반영**

`next_step_guide`: 게시 결과는 Chestnut에서 확인합니다. 세부 물리 설정으로 갱신할 필요가 있으면 `publish_objects_to_chestnut`을 사용합니다.
코드 1 · 코드 2
