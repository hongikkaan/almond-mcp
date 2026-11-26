# Rhino 플러그인 오프라인 검사

리포 루트에서 .NET 8 SDK, 개발용 Python 환경과 Node를 사용한다. SDK가 PATH에 없으면 `-DotNet <dotnet.exe>`를 지정한다. [개발 검사 안내](../../../tests/README.md)를 참고한다.

```powershell
./src/rhp/run_tests.ps1 -Development
```

| 검사 | 확인하는 동작 |
| --- | --- |
| [NativeBehavior](NativeBehavior/Program.cs) | Windows 공유·배타 잠금, localhost TCP 요청 인증, UI 콜백 직전 같은 경로의 다른 문서 인스턴스 거절, 일치하는 RhinoCode 완료 영수증을 받은 뒤 연결 해제를 확인한다. |
| [CapsuleRecovery](CapsuleRecovery/Program.cs) | Grasshopper 출력을 일부 배치한 뒤 실패했을 때 기존 객체를 보존하는지 확인한다. Undo 실패 시 남은 객체 GUID와 재확인 필요 상태를 돌려주는지 확인한다. |
| [PlanSection Update](../../mcp/features/modeling/PlanSection/tests/test_update_placement.py) | 기존 JSON과 typed 배치 메타데이터가 함께 있는 도면의 높이를 유지하고, 두 값이 충돌하면 기존 도면을 보존하는지 확인한다. |
| [Asset Panel](../Asset_Panel/tests/results_view.test.mjs) | 판정 상태에 따른 3DM 배치 버튼과 Karamba 결과의 모델 객체 검색·누락 수치 표시를 확인한다. |

루트 검사의 [ArchiveHost](../RhinoAlmondBridge/tests/archive_host/ArchiveHost.csproj)는 아카이브 디코더와 HTTP 응답 테스트의 실행 도구다. HTTP 검사는 `--serve <bundle-dir> <snapshot.json>`으로 테스트용 서버를 띄운다.

Rhino API 경계는 대역으로 실행한다. 실제 Rhino 문서의 Undo/Redo, 교차·Boolean·HLD·해치, 뷰포트, 패널 렌더링 및 RHP 로드는 별도 검증 범위다. [Undo·관측 안내](../RhinoAlmondBridge/tests/script_executor_undo/README.md)를 참고한다.
