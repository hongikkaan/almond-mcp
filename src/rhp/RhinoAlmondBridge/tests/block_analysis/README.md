# 블록 분석·교차체적 fixture

조회 feature의 `native/`와 Component 교차체적 계산을 컴파일한다. RHP 출력과 등록을 바꾸지 않는다.

```powershell
dotnet build src/rhp/RhinoAlmondBridge/tests/block_analysis/BlockAnalysisFixture.csproj -c Release
```

`verify_pipeline.py`는 `outline`, `resolve-block`의 문서 binding·입력 거절·상태 보존을 확인한다.
실행 파일의 `tests` 모드는 `get_component_intersections`가 사용하는 교차체적 계산을 검사한다.
둘 다 설치된 RhinoCore와 일회용 headless 문서를 사용하는 전용 fixture이며 오프라인 개발 검사에 실행하지 않는다.
실제 기능 검증은 사용자가 연결한 작업 문서에서 수행한다. fixture 빌드는 실제 Rhino 검증과 구분한다.
