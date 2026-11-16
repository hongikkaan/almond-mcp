# 외부 연결기와 AlmondRhino

- `src/cos`는 beyond·CoS 공용 host/worker와 도구 카탈로그를 소유한다. MCP runtime의 확장 훅 위에서 검증·바인딩한다. 계약은 `src/cos/SPEC.md`.
- 카탈로그는 AST에서 공개 스키마를 읽고 실제 worker 계약과 대조한다. source fingerprint와 선택한 연결의 lease·receipt를 보존한다.
- AlmondRhino C# 원본은 `src/cos/rhp`, 출력은 `src/rhp/AlmondRhino/plugin-runtime`. 개발 워크트리로 Rhino 등록을 돌리지 않는다.