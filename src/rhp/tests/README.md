# Native 오프라인 검사

저장소 루트에서 개발 환경을 준비한 다음 실행한다. Rhino를 실행하거나 연결하지 않고 일회용 경로와 대역을 사용한다. 실제 .NET 8 SDK 자동 탐색이 안 되면 `-DotNet <SDK/dotnet.exe>`를 추가한다. SDK가 없거나 fixture 빌드에 실패하면 검사는 중단된다.

```powershell
./src/cos/run_tests.ps1 -Development
./tests/run_tests.ps1 -Development
node --test (Get-ChildItem src/rhp/Asset_Panel/tests -Filter *.test.mjs | ForEach-Object FullName)
```

외부 연결기 실행기는 실제 Engine의 세션 경로 검증, 공유·배타 잠금과 완료 영수증 fence, Terminal의 종료 소유권 유지, 제어 파이프의 토큰과 연결 종료를 검사한다. Terminal 검사는 Rhino UI와 native bridge를 대역으로 대체한다. 루트 실행기는 ArchiveHost를 빌드해 실제 `ArchiveMeshData` 디코더를 사용하는 Python 통합 검사에 제공한다. Node 검사는 모델 배치 가능 여부와 결과 선택·정렬을 검사한다.

이 검사들은 RHP 빌드·등록·실제 로드의 증거가 아니다. 현재 Undo/Redo, Rhino 관측과 UI·ConPTY, 실제 AlmondRhino host의 전체 수명주기는 자동 검증하지 않는다. 실제 기능 확인은 사용자가 작업에 연결한 Rhino 파일에서 기존 모델과 문서 상태를 보존하며 별도로 수행한다. 테스트만을 위한 새 Rhino 문서나 별도 Rhino 프로세스를 만들지 않는다.
