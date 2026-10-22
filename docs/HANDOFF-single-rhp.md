# Almond 단일 RHP 통합 및 실제 Rhino 검증 기록

갱신일: 2026-10-22 (실제 Rhino 검증 종료 12:55 UTC, 이후 기본 pytest 리뷰 수정 검증)

## 현재 상태

Bridge·Structural_Analysis·Asset_Panel·RhinoTerminal의 단일 RHP 통합과 로컬 등록, 실제 Rhino 검증을 완료했다. 이 문서는 구현 전 인계문서를 대체한다. COS 소스와 연결은 이번 범위에서 제외했고 Engine과 MCP는 분리 상태로 유지했다.

PR #2의 기존 리뷰 수정은 `74488900f11b78fe95c4e5e841fef15efd1e8c19`로 먼저 push했다. 이번 통합 커밋도 같은 PR의 head `codex/repository-layout`에 정상 fast-forward로 반영한다. `main` 직접 push나 upstream Undo PR 변경은 하지 않는다. PR 병합과 Slack 전송은 자동 승인 검토가 직접 승인을 요구하며 거절해 아직 실행하지 못했다.

## 구현과 보존 계약

- `src/rhp/RhinoAlmondBridge/RhinoAlmondBridge.csproj`를 `net8.0-windows`로 전환하고 Terminal C#·Engine project reference·Porta.Pty·4개 web resource를 포함했다.
- 설치된 RhinoCommon/Rhino.UI/Eto/Grasshopper/GH_IO SDK를 참조한다. Rhino 8.34.26223.11001, .NET 8.0.14에서 실제 실행했다. 호스트 SDK DLL은 배포하지 않는다.
- 유일한 plugin entry는 `RhinoAlmondBridge.RhinoAlmondBridgePlugin`이다. 여기서 Terminal을 등록하고 종료 시 `TerminalPanel.StopAll()` 후 기존 archive/server 정리를 수행한다.
- 별도 Terminal csproj·lock·build entry·plugin GUID를 제거하고 `Commands.cs`에 `RhinoTerminal` 명령을 유지했다. Terminal UI·ConPTY·Ctrl·연결 로직은 바꾸지 않았다.
- Bridge assembly 이름 `RhinoAlmondBridge`, informational version `0.7.0-rc.2`, GUID `c337dbb8-394a-4593-9c2b-a3d7cfc91893`를 유지했다.
- Engine이 검사하는 `Instance`, `_server`, `HandleRequest(string)`, `_validator`, `_definitionRunner`, `_drawingAssetManager`, `_drawingStyleManager` 계약을 유지했다.
- Terminal panel GUID `4B3493B2-3421-4BEC-A8C8-F7F1786E8495`와 `RhinoTerminal.terminal.html`, `.xterm.js`, `.xterm.css`, `.addon-fit.js` logical name을 유지했다.
- `src/rhp/build.ps1`은 새 staging에서 빌드·archive 생성 후 출력을 교체한다. 로드된 RHP/DLL은 덮어쓰지 않는다. 출력은 `src/rhp/RhinoAlmondBridge/plugin-build`이며 Terminal의 `../../../engine` 탐색 깊이를 유지한다.
- 기존 Undo/Redo 수정, solver 수식, MCP schema, 자산·패널 JS, Engine/COS 기능은 변경하지 않았다.

PR 리뷰 수정에서는 Terminal의 공용 저장소 경로를 `src/engine/data`로 맞추고, Bridge의 checkout 자산 탐색 깊이를 새 폴더 구조에 맞춰 한 단계 늘렸다. 기존 프로세스 소유권과 경로를 검증하는 HostContracts를 보강했다. 두 리뷰 thread는 resolve했다.

최종 리뷰 재확인에서는 기본 pytest가 준비되지 않은 COS pipe fixture까지 수집하는 P1을 추가로 확인했다. `pyproject.toml`의 기본 `testpaths`에서 `tests/cos`만 제외하고 import 경로와 기존 `src/cos/run_tests.ps1`은 유지했다. COS 환경변수 없이 MCP 400개·Engine 80개가 모두 수집되고 COS는 0개임을 확인했다. ArchiveHost를 준비한 실제 기본 pytest는 479 passed, 1 skipped, 21 subtests passed였다.

## 설치 상태와 사용자 세션

등록 경로:

```text
C:\TOOL\Rhino\mcp\almond-mcp\src\rhp\RhinoAlmondBridge\plugin-build\RhinoAlmondBridge.rhp
```

기존 Bridge GUID의 등록을 위 통합본으로 맞췄다. 파일이 이미 없던 별도 Terminal GUID `27d4b9a1-8fad-421c-b64a-7a213d3b4079` 등록은 백업 후 제거했다. COS 등록은 그대로다.

기존 명시적 설정을 보존하고, 설정이 없던 10개 User `RHINO_MCP_*_DIR`에 기존 AppData 라이브러리 경로를 지정했다. 라이브러리 파일을 복사·삭제·초기화하지 않았다. 재시작한 검증 Rhino에서 Engine과 Bridge helper 5개의 실제 경로 일치를 확인했다. 환경 변경 알림도 전송했다. `ALMOND_SOLVER_COMMAND`는 검증 Rhino에만 지정했으며 User 환경에 영구 등록하지 않았다.

사용자가 열어 둔 Rhino PID **29560**과 `주민시설.3dm`은 변경하거나 종료하지 않았다. 이 프로세스는 새 등록·환경이 적용된 검증 프로세스가 아니므로 **작업을 저장하고 정상 재시작한 뒤 통합본을 사용해야 한다.**

실제 작업은 ignored `data/single-rhp-verification-20261022/ui_fixture.3dm`에서 수행했다. 검증 Rhino PID 39824와 재시작한 PID 28732는 각각 정상 `_Exit`로 종료했다. 마지막 확인에서 소유 shell PID 31192/28820과 conhost 24064, Bridge/Terminal/archive의 해당 listen port가 모두 정리됐고 사용자 Rhino는 계속 실행 중이었다.

## 검증 결과

| 항목 | 이번 작업의 실제 결과 |
|---|---|
| Terminal HostContracts | 8개 통과 — 공용 경로, 연결·프로세스 소유권 포함 |
| ConPTY smoke | 5개 통과 — 한글 입력·경로, resize, 자식 정리, exit code, startup stop |
| Panel JS | 19개 통과 |
| PR 경로 resolver | reflection 검사 3개 통과 |
| 기본 pytest / release 테스트 단계 | 479 passed, 1 skipped, 21 subtests passed — COS 전용 fixture 환경 없이 통과 |
| NativeUndoTests | 실제 로드한 Rhino 안에서 21/21 통과 |
| 단일 RHP 빌드 | 성공, 기존 `ResultsPanel.Load` CS0108 warning 1개 |
| 실제 assembly | plugin subclass 1개, 명령 12개, Terminal resource 4개, 기대 GUID/version/path 확인 |
| 재시작 자동 로드 | 등록된 통합본이 정상 Rhino 시작에서 자동 로드됨 |
| Terminal UI | 실제 터미널 화면과 `almond -CheckOnly` attach → PID/port/config 확인 → detach 통과 |
| Bridge native 실행 | 성공 script 객체 추가, 실패 script 추가 객체 rollback 확인 |
| 실제 GUI Undo/Redo | 성공 script의 point·dimension 삭제와 동일 GUID 복구, idle Undo/Redo flag 정상 |
| 자산 패널 | 실제 Place로 Stool block 배치, attribution/passport 보존, GUI Undo/Redo로 동일 GUID 복구 |
| Structure 패널 | 선택 3개 → 3개 beam 인식 → Run native analysis → 뷰포트 변형 형상 표시 |
| Results 패널 | 실제 AlmondResults 화면에서 Pass, 부재 3개와 변위·이용률·안정성 수치 확인 |
| 종료 | 검증 Rhino 정상 종료 시 Terminal shell/child 및 listener 정리 확인 |
| Yak | 의존성·라이선스·archive 392개 route·hash 검증 통과, 설치·게시하지 않음 |
| 최종 정적 검사 | PowerShell 3개 script parse, verify_yak Python compile, git diff whitespace 검사 통과 |

검증에서 로드한 Bridge MVID는 `dfd797a4-8c11-4272-bb4a-9a4d800bf67b`다. 최종 Yak에 포함된 RHP 및 의존 DLL 총 9개의 SHA-256이 실제 Rhino에서 사용한 로컬 출력과 모두 동일했다.

### 구조해석 fixture

mm 문서에 높이 3 m인 기둥 2개와 경간 6 m의 보 1개를 만들었다. native engine 0.7.0rc2, Steel/S235, 기본 CHS 114.3×4, rigid 연결, 10 kN 하중과 자중, Eurocode 권장값을 사용했다. 명시적 anchor가 없어 최저 Z의 2개 node를 fixed support로 선택했다는 경고를 기록했다.

- 해석 방식: `native`, first-order, 12 elements / 13 nodes.
- 최대 변위: **1.549 mm**, 설정된 한계 **24 mm**.
- 최대 이용률: **0.0696**; UI **7.0%**.
- 최소 alpha-cr: **15.046**; 평형 오차 **0 kN**.
- 부재 3개의 결과 GUID가 원본 선택 3개와 일치하고 `drawn=true`, `passed=true`였다.

이는 해당 fixture의 실행·연결·표시 검증이다. Karamba API는 설치돼 있지 않아 검증하지 않았다. MCP 클라이언트 초기화나 대화형 Codex 작업도 이번 Terminal `-CheckOnly` 결과에 포함하지 않는다.

### 관찰된 UI 제약과 검증 과정

Rhino 8.34의 floating Almond 패널은 Structure 전환 후 창이 숨는 상태가 관찰됐다. `Panels.PanelDockBar(TerminalGuid)`가 반환한 기존 dock에 `Panels.OpenPanel(dock, AlmondPanelGuid, true)`로 열어 복구했고, 이후 선택·해석·결과 화면을 검증했다. plugin panel type/GUID나 제품 UI 코드는 변경하지 않았다. floating 표시 문제의 근본 수정으로 주장하지 않는다. 조사 중 잠시 바꾼 `TestHideOnDeactivate`는 원래 **Yes**로 복구했다.

초기 modeless Undo 실험은 테스트 callback 자신의 undo record를 닫지 않아 Redo가 실패했다. 해당 실패 로그는 보존했고, 새 fixture에서 실제 Rhino `_Undo`/`_Redo` 명령으로 위 통과 결과를 확보했다. 이 실험 때문에 제품 Undo 코드를 수정하거나 불확실한 mutation을 재실행하지 않았다.

최종 Yak 첫 로그 수집은 PowerShell 5.1의 전체 stream redirection이 Yak의 기존 name mismatch warning을 terminating error로 승격해 중단됐다. redirection 없이 별도 staging 빌드를 실행해 정상 완료했다. assembly/package 이름은 기존 연결 계약 때문에 유지했다.

기본 pytest의 8개 경고는 FastMCP deprecation 4개와 Node 출력의 Windows cp949 reader 경고 4개였다. 출력 경고가 발생한 UI 테스트 4개를 `python -X utf8 -m pytest`로 재실행해 4 passed, 경고 없음으로 확인했다. 이 때문에 제품 코드나 테스트 assertion을 완화하지 않았다.

## 산출물과 재현

```powershell
./src/rhp/build.ps1
./tools/build_yak.ps1 -PythonExecutable "$PWD/src/engine/.venv/Scripts/python.exe" -DotnetExecutable "$PWD/src/rhp/RhinoTerminal/data/sdk/dotnet.exe"
```

최종 패키지: `dist/yak/almondbridge-0.7.0-rc.2-rh8_34-win.yak` (49.67 MB).
SHA-256: `3c3508302eb5154faff75bf1388419c0708cc0fa560c3ea48c3f3e812419a605`.

`tools/build_yak.ps1`은 실제 참조 SDK에 맞는 Rhino 태그와 net8 의존성·라이선스를 검사한다. `tools/prepare_release.ps1`은 새 staging Yak만 사용하고 이전 release 출력이 남아 있으면 중단한다. 전체 prepare_release pipeline은 실행하지 않았고, 변경된 기본 pytest 단계와 Yak 빌드·검증을 각각 실행했다.

상세 로컬 증거는 ignored `data/single-rhp-verification-20261022/`에 있다:

- `live_bootstrap_report.json`, `native_undo_live.txt`, `terminal-check.txt`.
- `ui_bridge_trial.json`, `ui_commands.jsonl`, `frame_create.json`, `live_state.json`, `live_states.jsonl`.
- `installation-backup.json`, `installation-result.json`, GUID별 registry backup.
- `reopened_fixture_report.json`, `postflight.json`, `final-evidence.json`.
- `default-pytest-collection.json`, `default-pytest.log`, `default-pytest.xml`.

RHP·Yak·SDK·venv·검증 모델·로그는 Git에 넣지 않는다. 저작권·vendor·asset 고지와 manifest/hash는 유지한다. 자세한 빌드·실행 절차는 [LOCAL_SETUP](../LOCAL_SETUP.md), 계약은 [SPEC](../SPEC.md)을 따른다.

## Git와 남은 외부 작업

- Child repo: `C:\TOOL\Rhino\mcp\almond-mcp`, origin `git@github.com:hongikkaan/almond-mcp.git`.
- PR: https://github.com/hongikkaan/almond-mcp/pull/2, base `main`, head `codex/repository-layout`.
- 통합 작업은 `codex/single-rhp-integration`에서 완료하고 기존 PR head에 정상 fast-forward push한다. 다른 원격 변경이 있으면 먼저 검토하며 force push하지 않는다.
- Child push 후 상위 `C:\TOOL\Rhino`의 `mcp/almond-mcp` gitlink만 커밋한다. parent branch는 `almond`, remote는 없다.
- parent의 기존 `01_WorkFlow/02_Agent_Skill/rhino-almond/tests/` 삭제 5개와 `FloorPlan_made_using_Bonsai.png`는 stage하거나 변경하지 않는다.
- upstream `codex/undo-recovery` / Undo PR #39는 변경하지 않는다.

자동 승인 검토가 거절한 미완료 작업은 **PR #2의 main 병합**과 **Slack 최종 보고 전송**이다. 도구의 보충 문맥에 전달된 요청을 직접 승인으로 인정하지 않았고, default branch 병합과 메시지 전송에 대해 명시적 확인을 요구했다. 다른 API·CLI로 우회하지 않는다. 사용자에게 이 두 동작에 대한 직접 승인을 받은 후 최종 PR head와 상태를 다시 확인해 처리한다.

Slack 보고 대상은 `#almond` (`C0CA8BC1SS1`), thread `1792650597.726109`, 멘션 `<@U0C6K22KK0A>`이며 기존 스레드 https://hih-z6k5791.slack.com/archives/C0CA8BC1SS1/p1792650597726109 이다. 이번 작업의 Slack 보고는 아직 전송되지 않았다.

Ponytail은 연결된 플러그인 검색에서 찾지 못해 Core/Desktop으로 작업했다. 복잡하지 않은 검토는 요청한 medium worker에, 핵심 통합 검토는 default Pro worker에 맡겼다. worker의 파일 도구 호출 일부가 장시간 중단돼 실제 변경과 검증은 root가 결과를 직접 확인했다.
