# 고정 관찰 fixture

기존 `rhino-almond` 스킬 폴더에 있던 관찰 검사를 Bridge 소유 위치로 옮겼다.
`Probes/*.cs`와 `ProbeObservation.cs`를 컴파일하며 RHP 출력·등록은 바꾸지 않는다.

저장소 루트에서 .NET SDK로 빌드한다.

```powershell
dotnet build src/rhp/RhinoAlmondBridge/tests/probe_observation/ProbeObservationFixture.csproj -c Release
```

`bin/Release/net48/ProbeObservationFixture.exe`의 `tests` 모드는 새 report 경로를
받는다. `verify_pipeline.py`는 `.artifacts/`에 일회용 문서와 요청을 만들어
고정 관찰 경로를 확인한다. 두 실행 모두 설치된 Rhino 8의 RhinoCore를 사용하므로
Rhino 없는 검증에는 실행하지 않는다. 빌드 성공은 실제 Rhino 관찰 검증과 구분한다.
