# 외부 연결기와 AlmondRhino

- `src/cos`는 beyond·CoS 공용 host/worker와 도구 카탈로그를 소유한다. MCP runtime의 확장 훅 위에서 검증·바인딩한다. 계약은 `src/cos/SPEC.md`.
- 카탈로그는 AST에서 공개 스키마를 읽고 실제 worker 계약과 대조한다. source fingerprint와 선택한 연결의 lease·receipt를 보존한다.
- AlmondRhino C# 원본은 `src/cos/rhp`, 출력은 `src/rhp/AlmondRhino/plugin-runtime`. 일상 Rhino 등록과 CoS 실행 경로는 `AGENTS.md`의 일상 폴더에 고정한다. 사용자 허가를 받은 통합 검수에서는 `src/rhp/tools/start_integration_rhino.ps1`로 두 워크트리 RHP의 로드를 확인하는 즉시 기존 등록을 복원한다. 시작 스크립트는 같은 워크트리의 Beyond로 Rhino PID·시작 시각·시험 모델을 대조해 `ready` 연결을 확인하고 해제한다. 기능 검수는 반환된 `host_id`로 같은 워크트리에서 연결한다.