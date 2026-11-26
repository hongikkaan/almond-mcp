# 개발 검사와 검증 범위

## 변경에 맞는 검사 선택

체크아웃 루트의 PowerShell에서 실행한다. 모든 범위를 한 번씩 실행하려면 다음 명령을 쓴다.

```powershell
./tests/run_tests.ps1 -Development
```

작은 변경은 같은 명령에 `-Scope`를 붙여 영향을 받는 경계를 선택한다. 예를 들어 `./tests/run_tests.ps1 -Development -Scope Mcp`는 모델을 열지 않고 기능 호출과 저장 결과를 확인한다.

| 범위 | 실패하면 확인할 동작 |
| --- | --- |
| `Mcp` | Plan·Step 수정 후 재조회, 기존 DB 이전 중 데이터 보존, 자산 파일 경계와 무결성, 구조 계산·보고서, 모델 요청의 불확실한 결과, 연결별 저장 공간과 Dashboard 조회 |
| `Beyond` | 특정 문서에 연결·종료, 중복 실행 방지, 취소·시간 초과 뒤 결과를 원래 요청에서만 조회, Python과 C# 제어 파이프 통신 |
| `Native` | [native 검사 안내](../src/rhp/tests/README.md)에 지정된 C# 동작, 패널 선택, PlanSection 출력의 성공·실패 처리 |
| `Dot` | 로컬 통신 상대와 실제 Dot CLI 사이의 요청·응답·오류 처리 |
| `Integration` | 실제 stdio에서 양쪽 도구 선언과 시작 안내, 두 연결의 데이터 격리, 설치 패키지의 정책 조회, 배포 모델의 ArchiveHost 디코딩과 변경된 파일 거부, 런타임 배포·등록 계약 |

공개 도구가 바뀌면 해당 기능 범위와 `Integration`을 함께 실행한다. [출력 계약](../src/mcp/output_contracts.py), [공개 스키마](integration/tool_schemas.json), [런타임 선언 스냅샷](integration/tool_catalogs.md)를 실제 응답과 대조한다. Engine 변경은 [두 RHP의 빌드와 manifest 기록](../AGENTS.md#개발빌드반영)을 마친 뒤 전체 검사를 실행한다.

검사를 추가하기 전에 어떤 입력에서 사용자에게 보이는 결과가 어떻게 달라지는지 정한다. 저장과 복구는 새 연결에서 다시 읽은 값으로, 구조 계산은 독립적인 손계산으로, 공개 계약은 실제 메시지로 판정한다. 실패 시 보존해야 할 파일이나 기록도 확인한다. 동일한 고장을 기존 검사에서 재현할 수 있으면 그 사례를 사용한다.

## 오프라인 검사 준비

1. 이 체크아웃에서 `./src/mcp/rebuild_environment.ps1 -Development`로 `data/development/.venv`를 준비한다.
2. 전체 검사에는 .NET 8 SDK, Node.js, 로컬 Python 패키지 빌드 캐시가 필요하다. SDK 자동 탐색에 실패하면 `-DotNet '<SDK의 dotnet.exe 절대 경로>'`를 추가한다. `Mcp`와 `Dot`은 Python만으로 실행한다.
3. 실행기는 현 체크아웃의 Python·자산 경로와 오프라인 DB·임시 폴더를 설정한다. 기본 위치는 `data/offline/`, `data/t/`다. `-ScratchDirectory`로 별도 검사 폴더를 지정할 수 있다. 개별 명령을 직접 실행할 때는 별도 셸에서 `./src/mcp/use_offline_environment.ps1 -Development`로 같은 경로를 설정한다.

Python 범위 안에서 한 사례를 재실행하려면 `-Scope`와 pytest 인자를 함께 준다. 예를 들어 `-Scope Mcp -TestArgs @('-k', 'cantilever')`로 외팔보 계산·보고서를 확인한다. 전체 실행에 준 `-TestArgs`는 루트 통합 검사에 적용된다. [릴리스 준비](../src/rhp/tools/prepare_release.ps1)도 같은 전체 진입점을 사용하고 각 Python 범위의 JUnit 결과를 릴리스 폴더에 기록한다.

Beyond 검사가 실패하면 실행기가 출력한 임시 폴더에서 해당 요청의 `request.json`과 완료 기록을 대조한다. 각 실행은 별도 폴더에 제어 파이프 검사 프로그램을 빌드한다.

## 별도 확인이 필요한 작업

- 설치된 Codex의 설정 해석은 [수동 CLI 검사](../src/mcp/tests/runtime/test_terminal_launch.ps1)에 `-Codex <설치한 codex.exe>`를 전달해 확인한다.
- Dashboard 화면 변경은 [브라우저 검사](../src/mcp/runtime/dashboard/README.md#개발-검사)로 좁은 창에서 필터와 이전 Loop의 Step 선택을 확인한다. 이 검사는 로컬 Chrome과 Playwright가 필요하다.
- 생성 자산의 배포 파일 전체와 출처는 `& ./data/development/.venv/Scripts/python.exe -B tests/verify_library_sources.py`로 대조한다.
- 안내 문서만 변경한 경우 링크와 명령을 확인한다. MCP 클라이언트나 배포 패키지가 실제로 읽는 문서는 소비하는 경로까지 실행한다.
- 오프라인 검사는 일회용 입력을 사용한다. 실제 모델의 형상·Undo/Redo·화면·Rhino 플러그인 로드는 아래 통합 검수에서 확인한다.

## 실제 Rhino 통합 검수

1. 통합 오케스트레이터는 사용자에게 검수할 워크트리·모델·변경 범위와 실제 Rhino 사용을 승인받는다. 문서나 DB를 바꾸는 검수는 별도 프로젝트 폴더의 복사본에서 한다. Worksession에는 필요한 파일만 붙인다.
2. 사용 중인 Rhino는 그대로 유지한다. 이미 로드된 assembly는 디스크의 새 빌드나 임시 등록 변경으로 교체되지 않는다. 기존 Rhino의 PID·시작 시각을 기록하고, 검수할 워크트리에서 `verify_runtime.py`로 소스·실행 파일의 manifest와 양쪽 Engine DLL을 확인한다. 일치하면 기존 빌드를 사용한다. 불일치하는 RHP만 대상 출력 사용 가능 여부를 확인한 뒤 다시 빌드하고 manifest를 기록·검증한다. Engine 변경은 양쪽을 빌드한다. 해당 워크트리 RHP를 이미 로드한 이전 검수 인스턴스가 있다면 그 인스턴스만 정상 종료한 뒤 출력 교체를 진행한다.
3. 검수할 워크트리에서 `./src/rhp/tools/start_integration_rhino.ps1 -ModelPath '<시험 파일.3dm>'`을 실행한다. 스크립트는 시작 전에 시험 파일의 절대 경로를 출력하고, 기존 등록을 보존한 뒤 두 RHP 경로를 워크트리로 임시 지정해 새 Rhino를 시작한다. 이때 시작한 PID·시작 시각으로만 프로세스를 추적한다. 새 인스턴스에서 워크트리 RHP 두 개의 실제 로드 경로가 확인되면 즉시 기존 등록값을 복원하며, 시작 실패 시에도 복원을 수행한다. 이어서 같은 워크트리의 beyond에서 Rhino PID·시작 시각·시험 파일 경로가 일치하는 대상에 `ready`로 연결되는지 확인한다. 검증 연결을 해제하고 같은 PID의 RHP를 재확인한 뒤 검증 결과를 반환한다.
4. 기능 검수는 같은 워크트리에서 시작한 beyond에서 수행한다. `connect_01-list_up` tool에서 시작 스크립트가 확인한 대상의 `host_id`·PID·모델 경로를 대조하고 `connect_02-session` tool로 연결한다. 변경된 기능은 공개 도구로 검수한다. Rhino 내부 확인은 연결된 시험 문서에서 `script_02-run_rhino` tool을 사용한다. 결과를 기록하고 시험 연결과 식별한 검수용 Rhino만 정상 종료한 뒤 일상 경로에서 `install_runtime.ps1 -VerifyOnly`로 등록을 확인한다. 사용자의 기존 Rhino에는 연결·종료·문서 변경을 수행하지 않는다.

시작기는 기존 독립 Rhino launcher로 상위 Windows Job에서 분리한 프로세스만 실행한다. 원래 등록값과 형식은 `data/runtime-integration/<id>/registration.json`, 새 PID·시작 시각·모델·RHP 경로는 같은 폴더의 `process.json`에 남긴다. 원복 실패 시에도 이 근거로 검수 인스턴스만 재식별한다.

사용자와 일상 체크아웃에서 특정 커밋을 검수하기로 합의했다면 기존 HEAD·브랜치를 기록하고 깨끗한 상태에서 `git switch --detach <SHA>`로 이동한 뒤 같은 절차를 따른다. 끝나면 합의한 HEAD와 브랜치로 되돌린다. 전원이 끊기는 등 시작 스크립트의 복구가 완료되지 않았다면 저장된 등록 백업과 현재 값을 대조해 원래 경로를 복원한다. 검수 중 다른 작업이 바꾼 등록은 덮어쓰지 않고 차이를 보고한다.

## 작업 워크트리와 squash 검증

위임 직전에 새 티켓 워크트리의 `HEAD`를 오케스트레이터가 정한 통합 커밋의 전체 SHA와 대조한다. 검사가 통과하면 위임한다.

```powershell
./tests/verify_integration_worktree.ps1 -TicketWorktree '<티켓 워크트리>' -ExpectedBase '<통합 커밋 전체 SHA>'
```

일상 폴더에 `main`을 체크아웃한 뒤, 원본 작업 브랜치나 커밋 참조를 삭제하기 전에 검사한다. `-ExpectedBase`는 squash 직전 `main`의 전체 SHA, `-SourceCommit`은 squash한 작업의 전체 SHA다. 검사기는 `main`의 부모 하나, 원본과 동일한 파일 트리, 일상 폴더의 `main` 체크아웃과 추적 파일 상태를 검증한다.

```powershell
./tests/verify_integration_worktree.ps1 -ExpectedBase '<이전 main 전체 SHA>' -SourceCommit '<작업 커밋 전체 SHA>'
```

## 결과 보고 기준

| 확인한 단계 | 확보한 증거 |
| --- | --- |
| 오프라인 검사 | 실행한 모듈·계약·fixture에서 어떤 검사가 통과하거나 실패했는지. 현재 [native 검사 범위](../src/rhp/tests/README.md)와 [Undo·관측 검사 상태](../src/rhp/RhinoAlmondBridge/tests/script_executor_undo/README.md)도 확인한다. |
| RHP 빌드와 출력 검증 | 빌드한 구성요소, 생성·배치된 파일, `verify_runtime.py`로 확인한 소스·배포 파일의 manifest 정합성. 전체 검증은 양쪽 Engine DLL의 바이트 일치도 확인한다. `--record`는 manifest를 갱신하고 기본 호출은 기록을 대조한다. |
| Rhino 등록 | 일상 체크아웃에서 `./src/rhp/tools/install_runtime.ps1 -VerifyOnly`로 확인한 등록 파일 경로, 로드 모드와 연결 명령 캐시. |
| 실제 플러그인 로드 | 허가된 통합 검수에서 Rhino PID, 로드된 플러그인과 실제 assembly 경로. |
| Rhino에서만 확인 가능한 동작 | 통합 검수에서 확인한 모델링·뷰·Layout·UI 동작과 재현 조건. 실행하지 못한 항목을 명시한다. |

실행한 단계와 확인 범위를 근거와 함께 보고한다. 실패나 실행할 수 없었던 검사, 현재 자동 검사가 다루지 않는 동작도 명시한다.
