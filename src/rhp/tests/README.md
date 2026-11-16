# Native 오프라인 검사

개발 환경 준비, .NET SDK 지정과 변경 유형별 실행기 선택은 [개발 검사 안내](../../../tests/README.md)를 따른다.

| 실행기 | Native 검사 범위 |
| --- | --- |
| 외부 연결기 실행기 | [NativeFixture](../Engine/tests/NativeFixture.csproj)는 실제 Engine의 세션 경로, 공유·배타 잠금과 완료 영수증 fence를 검사한다. [AlmondHostContracts](../RhinoTerminal/tests/AlmondHostContracts/AlmondHostContracts.csproj)는 Rhino UI와 native bridge를 대역으로 두고 Terminal의 종료 소유권을 검사한다. [PipeFixture](../../cos/tests/PipeFixture.csproj)는 제어 파이프의 토큰과 연결 종료를 검사한다. |
| 루트 실행기 | [ArchiveHost](../RhinoAlmondBridge/tests/archive_host/ArchiveHost.csproj)를 빌드해 실제 `ArchiveMeshData` 디코더를 사용하는 Python 통합 검사에 제공한다. |
| Asset Panel Node 검사 | 모델 배치 가능 여부와 결과 선택·정렬을 검사한다. 체크아웃 루트에서 아래 명령을 실행한다. |

```powershell
node --test (Get-ChildItem src/rhp/Asset_Panel/tests -Filter *.test.mjs | ForEach-Object FullName)
```

이 fixture들은 Rhino 프로세스를 열거나 연결하지 않고 실행한다. Undo/Redo와 Rhino 문서 관측의 현재 상태는 [Undo·관측 검증 안내](../RhinoAlmondBridge/tests/script_executor_undo/README.md)를 참고한다. Rhino UI·ConPTY와 실제 AlmondRhino host의 전체 수명주기는 오프라인 검증 범위 밖이다. 빌드·등록·실제 로드의 증거와 미검증 동작은 [결과 보고 기준](../../../tests/README.md#결과-보고-기준)에 따라 기록한다.
