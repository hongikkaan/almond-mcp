# Almond MCP

- Rhino 8 모델링·도면을 위한 MCP와 Rhino 플러그인. `AGENTS.md`는 작업 규칙, `SPEC.md`는 모듈 경계, `GLOSSARY.md`는 제품·설계 용어의 원본이다.
- Python MCP·CLI·연결 실행기: `mem:mcp/core`. beyond/CoS의 호스트·카탈로그: `mem:cos/core`. Bridge·패널·Terminal·공유 Engine: `mem:rhp/core`.
- 작업 환경과 버전은 `mem:tech_stack`, 검사·빌드의 진입점은 `mem:suggested_commands`, 공개 인터페이스·데이터 보존 규칙은 `mem:conventions`, 변경별 검증·보고 기준은 `mem:task_completion`.
- 현행 공개 도구 선언의 읽기용 스냅샷은 `TOOL-DECLARATIONS-CURRENT.md`다. 시작 공통 지침은 initialize.instructions, 개별 도구 설명은 tools/list에서 전달되며 클라이언트의 지침 준수까지 서버가 강제하지 않는다. 갱신·검증 규칙은 `mem:task_completion`.
- 개발 검사·티켓별 검증은 오프라인이다. 사용자 허가를 받은 통합 오케스트레이터는 `tests/README.md`의 실제 Rhino 통합 검수 절차를 따른다.
- 개발 워크트리, 일상 체크아웃, 디스크의 플러그인, Rhino 등록, 로드된 assembly는 별개다. 워크트리만으로 모델 DB·세션·로드된 플러그인이 격리되지 않는다.
