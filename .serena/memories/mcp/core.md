# Python MCP와 연결 실행기

- `src/mcp/server.py`는 공통 MCP 도구를 조립한다. `src/mcp/runtime`은 checkout CLI·세션 바인딩·저장소·Rhino 문서 연결 실행기이며 외부 연결기에는 공개 확장 훅을 제공한다. Python MCP가 외부 연결기 구현을 import하지 않는다.
- 모델링·도면·Scene/Component·Plan·자산의 책임과 계약은 `src/mcp/SPEC.md`와 기능별 문서. 고정 조회와 일반 수정 실행은 `src/mcp/rhino/OBSERVATION-SPEC.md`를 따른다.
- Rhino 문서 전용 실행기와 beyond·CoS host는 공용 `modeling_guidance.py`를 통해 initialize.instructions에 `BASIC-INSTRUCTIONS.md`와 `design_judgment.md`를 전달한다. 시작 문서의 가용 상태와 본문은 guide_version에 반영한다. 상세 정책은 context_01-get_policy tool, 도구별 공개 설명은 구현 옆 Markdown, 동적 후속 안내는 `tool_guidance.py` 경로로 전달된다.
- 프로젝트 초기 조회의 관찰 요청과 응답 조립은 `features/context/project_info.py`가 맡는다. 연결 설정은 바인딩을 확인한다. MCP 조회와 첨부 범위를 지정한 PlanSection 호출에서 사용하는 Worksession 정보는 Rhino의 읽기 전용 관측이다.
- 프로젝트 파일 카탈로그의 관계 키는 등록 파일명이다. `context_05-upsert_project_file` tool로 명시 등록과 설명 갱신을 하고 Phase와 Scene은 그 목록의 이름을 선택한다. Worksession 첨부는 Rhino에서 별도로 관찰하며 자동 등록하지 않는다. `drawing_06-generate_plan_section` tool의 `include_attachments`는 Create에서 기본 false, Update에서 생략하면 저장된 값을 사용한다. Move는 기존 도면의 GUID·수동 편집을 보존하며 배치만 바꾼다.
- `plan_12-update` tool은 Step을 실제 완료로 전환할 때 에이전트의 결정을 받는다. No는 상태·모델 변경 없이 토큰을 닫고, 새 시도에는 새 토큰이 필요하다. Yes는 SQLite에 Step 완료를 먼저 저장한 뒤 현재 모델의 `temp` 트리 객체와 하위 레이어를 정리한다. 최상위 `temp`는 유지하고 로컬 블록 정의에서 해당 레이어의 구성원만 제거한다. DB 상태와 정리 결과는 따로 보고한다. 코드 진입점은 `features/planning/completion.py`와 `features/planning/native/StepTempCleanup.cs`다.
