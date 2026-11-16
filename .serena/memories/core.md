# Almond MCP

- Rhino 8 모델링·도면을 위한 MCP와 Rhino 플러그인. `AGENTS.md`는 작업 규칙, `SPEC.md`는 모듈 경계, `GLOSSARY.md`는 제품·설계 용어의 원본이다.
- Python MCP·CLI·연결 실행기: `mem:mcp/core`. beyond/CoS의 호스트·카탈로그: `mem:cos/core`. Bridge·패널·Terminal·공유 Engine: `mem:rhp/core`.
- 작업 환경과 버전은 `mem:tech_stack`, 검사·빌드의 진입점은 `mem:suggested_commands`, 공개 인터페이스·데이터 보존 규칙은 `mem:conventions`, 변경별 검증·보고 기준은 `mem:task_completion`.
- 개발 검사는 오프라인으로만 수행한다. 실행 중인 Rhino나 사용자 모델을 테스트에 쓰지 않고, 테스트를 위해 Rhino·RhinoCore를 시작하거나 연결하지 않는다.
- 개발 워크트리, 일상 체크아웃, 디스크의 플러그인, Rhino 등록, 로드된 assembly는 별개다. 워크트리만으로 모델 DB·세션·로드된 플러그인이 격리되지 않는다.