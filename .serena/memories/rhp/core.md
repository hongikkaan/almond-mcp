# Rhino 플러그인과 공유 Engine

- `src/rhp/Engine`은 Bridge와 AlmondRhino가 공유하는 `Almond.Engine.dll`이며 개별 호스트에 의존하지 않는다. `src/rhp/RhinoAlmondBridge`는 Bridge RHP와 Terminal·패널·MCP 기능별 native 소스를 컴파일한다. Terminal은 별도 플러그인이 아니다.
- 공용 패널 웹 원본은 `src/rhp/Asset_Panel/web`이며 Bridge archive와 wheel의 소비 경로를 함께 고려한다. Bridge·AlmondRhino의 assembly·GUID·명령과 Undo/Redo 계약을 보존한다.
- 빌드·출력 계약은 `src/rhp/SPEC.md`, 오프라인 fixture 범위는 `src/rhp/tests/README.md`. PlanSection의 보존된 RhinoCore fixture는 개발 검사 범위 밖이다.