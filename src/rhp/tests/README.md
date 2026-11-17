# Native 오프라인 검사

개발 환경 준비, .NET SDK 지정과 변경 유형별 실행기 선택은 [개발 검사 안내](../../../tests/README.md)를 따른다.

| 실행기 | Native 검사 범위 |
| --- | --- |
| 외부 연결기 실행기 | [NativeFixture](../Engine/tests/NativeFixture.csproj)는 실제 Engine의 세션 경로, 공유·배타 잠금과 완료 영수증 fence를 검사한다. [AlmondHostContracts](../RhinoTerminal/tests/AlmondHostContracts/AlmondHostContracts.csproj)는 Rhino UI와 native bridge를 대역으로 두고 두 호스트의 종료 소유권과 foreign ready/locator 보존을 검사한다. [DispatchFixture](../Engine/tests/dispatch/DispatchFixture.csproj)는 실제 BoundBridge TCP 인증·큐·native callback·완료/실패 drain을 Rhino adapter 대역으로 실행한다. [PipeFixture](../../cos/tests/PipeFixture.csproj)는 제어 파이프의 토큰과 연결 종료를 검사한다. |
| 루트 실행기 | [ArchiveHost](../RhinoAlmondBridge/tests/archive_host/ArchiveHost.csproj)를 빌드해 실제 `ArchiveMeshData` 디코더를 사용하는 Python 통합 검사에 제공한다. `--overlay <임시 폴더>`는 실제 HTTP 응답에서 같은 size/mtime의 drawing 변조를 거절하는지 검사한다. |
| GH·분석 수명 fixture | [GrasshopperFixture](../RhinoAlmondBridge/tests/grasshopper/GrasshopperFixture.csproj)는 전체 production runner의 출력 preflight·Undo 실패/복구·불확실한 GUID를 검사한다. [AnalysisLifetime](../Structural_Analysis/tests/lifetime/AnalysisLifetime.csproj)는 실제 Request→UI queue→비동기 결과 적용에서 문서/형상/속성/닫기/이름/패널 수명을 검사한다. 계산·Rhino 표시 자체는 adapter 대역이다. |
| 도면 스타일 fixture | Rhino 문서 테이블을 대역으로 두고 실제 스타일 적용 코드에서 임시 매니페스트를 사용한 생성, 동일명 정의와 참조 재사용, 반복 적용 및 새 정의가 없을 때의 오류를 검사한다. |
| Asset Panel Node 검사 | 모델 배치 가능 여부와 결과 선택·정렬을 검사한다. 체크아웃 루트에서 아래 명령을 실행한다. |

```powershell
node --test (Get-ChildItem src/rhp/Asset_Panel/tests -Filter *.test.mjs | ForEach-Object FullName)
```

도면 스타일 fixture는 체크아웃 루트에서 실행한다.

```powershell
dotnet build src/rhp/RhinoAlmondBridge/tests/drawing_style/DrawingStyleFixture.csproj --artifacts-path data/drawing-style-fixture
dotnet data/drawing-style-fixture/bin/DrawingStyleFixture/debug/DrawingStyleFixture.dll
```

이 fixture들은 Rhino 프로세스를 열거나 연결하지 않고 실행한다. 추출한 viewport helper 검사는 raster 설정만 확인하며 production dispatch 검사를 대신하지 않는다. Undo/Redo와 Rhino 문서 관측의 현재 상태는 [Undo·관측 검증 안내](../RhinoAlmondBridge/tests/script_executor_undo/README.md)를 참고한다. Rhino UI·ConPTY와 실제 AlmondRhino host의 전체 수명주기는 오프라인 검증 범위 밖이다. 빌드·등록·실제 로드의 증거와 미검증 동작은 [결과 보고 기준](../../../tests/README.md#결과-보고-기준)에 따라 기록한다.
