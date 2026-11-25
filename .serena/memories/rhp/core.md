# Rhino 플러그인과 공유 Engine

- `src/rhp/Engine`은 Bridge와 AlmondRhino가 공유하는 `Almond.Engine.dll`이며 개별 호스트에 의존하지 않는다. 두 연결 경로에서 모델 경로의 정규화·비교는 Engine의 `SessionFiles`가 맡는다. `src/rhp/RhinoAlmondBridge`는 Bridge RHP와 Terminal·패널·MCP 기능별 native 소스를 컴파일한다. Terminal은 별도 플러그인이 아니다.
- 공용 패널 웹 원본은 `src/rhp/Asset_Panel/web`이며 Bridge archive와 wheel의 소비 경로를 함께 고려한다. Bridge·AlmondRhino의 assembly·GUID·명령과 Undo/Redo 계약을 보존한다.
- 빌드·출력 계약은 `src/rhp/SPEC.md`, 오프라인 fixture 범위는 `src/rhp/tests/README.md`. Bridge 기능 소스를 개별 컴파일하는 fixture에서 `GeometryJson.Point`를 쓰면 `src/mcp/rhino/GeometryJson.cs`도 포함한다. PlanSection의 보존된 RhinoCore fixture는 개발 검사 범위 밖이다.
- Engine `NativeBinding`이 Terminal/AlmondRhino의 binding 발행·무효화·drain을 공유한다. `BridgeDispatchContext`와 명시적인 Bridge provider가 private reflection을 대체하고 검증한 문서를 전달한다. `NativeUndoRecord`가 스크립트·도면 스타일·GH 변경의 Undo 소유권을 공유한다. 패널은 실제 표시한 결과의 문서/모델 근거를 대조하고, `RuntimeEnvironment`가 Terminal에 의존하지 않는 공용 실행 경로를 해석한다.
- Bridge/Yak staging은 `tools/build_runtime.ps1`, 등록 identity·계획·복구는 `tools/runtime_registration.ps1`이 공유한다. Python/Bridge 릴리스 버전 원본은 `src/mcp/__init__.py`이며 native 호환 판정은 Engine provider 계약이다. 도면 archive의 선택 파일은 실제 제공 bytes의 SHA-256까지 확인한다.
- Rhino 실행 자체는 RHP 빌드 중단 조건이 아니다. 대상 출력의 사용 가능 여부를 검사하고 staging 후 교체한다. 등록·로드·실제 문서 검증은 빌드와 별도이며 사용자 승인된 실제 Rhino 검사 범위는 유지한다. 통합 검수는 기존 사용자 Rhino를 유지한 채 새 검수 PID에만 워크트리 RHP를 임시 등록·로드하고 원래 등록을 즉시 복원한다. 새 PID·시작 시각·시험 모델을 대조하며 검수 인스턴스만 정상 종료한다. 절차는 tests/README.md의 실제 Rhino 통합 검수에 둔다.
