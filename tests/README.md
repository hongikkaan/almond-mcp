# 개발 검사와 검증 범위

## 변경에 맞는 검사 선택

개발 검사는 Rhino를 사용하지 않는 오프라인 검사로 수행한다. 실행 중인 Rhino와 연결된 사용자 문서, RhinoCore를 사용하는 fixture는 개발 검사 범위 밖이다. 명령은 체크아웃 루트의 PowerShell에서 실행한다. 여러 변경 유형이 겹치면 각 유형이 영향을 주는 검사 범위를 함께 본다.

| 변경 유형 | 검사와 판단 기준 |
| --- | --- |
| 저장소 안내 문서만 변경 | 변경된 링크·앵커를 확인하고 명령·전제·설명은 해당 스크립트와 구현에 대조한다. 문서가 실제 제품 입력으로 쓰이는 경우에는 소비 경로에 맞는 검사도 선택한다. |
| MCP Python 구현 변경 | `./src/mcp/run_tests.ps1 -Development`로 모듈 회귀를 검사한다. 모듈 경계·공개 계약·패키징에 영향이 있으면 루트 검사도 사용한다. |
| Python 공개 도구 계약 변경 | MCP 모듈 검사와 `./tests/run_tests.ps1 -Development`를 사용한다. 구현 옆 지침·[출력 계약](../src/mcp/output_contracts.py)·[공개 스키마 기준](integration/tool_schemas.json)을 비교한다. 스키마 변경이 의도된 경우 기준의 차이를 검토한다. 루트 검사는 실제 stdio와 beyond·CoS 카탈로그의 계약을 확인한다. |
| 외부 연결기·native 계약 변경 | `./src/cos/run_tests.ps1 -Development`로 외부 연결기의 Python 계약과 Engine·Terminal·pipe fixture를 검사한다. Archive·패널 등 변경된 소비 경로는 [native 검사 안내](../src/rhp/tests/README.md)에서 고른다. |
| 공유 Engine 변경 | 외부 연결기 실행기의 Engine fixture를 실행하고 영향을 받는 소비 경로를 검사한다. [RHP 빌드 절차](../AGENTS.md#개발빌드반영)에 따라 Bridge와 AlmondRhino를 모두 빌드한 뒤 두 manifest와 Engine DLL 일치를 확인한다. 루트 전체 검사(`./tests/run_tests.ps1 -Development`)에는 배포 파일 대조가 포함되므로 빌드와 manifest 기록을 마친 상태에서 실행한다. |
| 배포용 자산 원본·출처 변경 | `& ./data/development/.venv/Scripts/python.exe -B tests/verify_library_sources.py`로 저장소에 포함된 생성 모델의 경로·바이트 해시·출처 기록을 확인한다. 설치된 AppData 라이브러리나 Rhino에서의 자산 사용은 별도 확인 범위다. |

## 오프라인 검사 준비

체크아웃별 개발 환경을 처음 준비하거나 잠금 의존성을 동기화할 때 실행한다.

```powershell
./src/mcp/rebuild_environment.ps1 -Development
```

세 `run_tests.ps1`은 `-Development`로 실행하면 이 체크아웃의 `data/development/.venv`를 사용한다. 실행기가 오프라인 경로를 직접 설정한다. 세 실행기 모두 .NET 8 SDK를 확인하며, 자동 탐색에 실패하면 `-DotNet`에 SDK의 `dotnet.exe` 경로를 전달한다.

로컬 도구를 별도 셸에서 직접 실행하면서 같은 데이터 경로가 필요한 경우에만 `./src/mcp/use_offline_environment.ps1 -Development`를 호출한다. 라이브러리는 체크아웃의 `asset/`을 사용하고, 해당 원본 폴더가 없으면 `data/offline/libraries/` 밑에 대체 경로를 만든다. 상태 DB는 `data/offline/state.sqlite3`, TEMP/TMP는 체크아웃의 짧은 `data/t/` 경로를 사용한다. 설정은 현재 셸과 자식 프로세스에 적용되므로 일반 실행은 새 셸에서 시작한다. 검사의 오프라인 범위는 Rhino와 일상 연결·데이터를 사용하지 않는다는 뜻이다. 예를 들어 패키징 검사는 `uv build --offline`이 사용하는 로컬 uv 캐시에 빌드 의존성이 준비되어 있어야 한다.

## 실행기별 확인 범위

- [MCP 모듈 실행기](../src/mcp/run_tests.ps1)는 자체 `pytest.ini`로 `src/mcp/tests`를 실행한다.
- [외부 연결기 실행기](../src/cos/run_tests.ps1)는 Engine·Terminal·pipe fixture를 빌드하고 실행한 뒤 `src/cos/tests`를 실행한다.
- [루트 실행기](run_tests.ps1)는 독립 ArchiveHost를 빌드하고 절대 실행 파일 경로를 `ALMOND_ARCHIVE_TEST_HOST`로 지정한 뒤 루트 `tests/`를 실행한다. ArchiveHost가 필요한 검사를 pytest에서 직접 선택하면 해당 실행 파일이 필수이며, 누락 시 수집 단계에서 오류가 난다.
- [stdio 계약 검사](integration/test_stdio_contract.py)는 실제 Python MCP 서비스를 자식 프로세스로 시작한다. 문서 연결 fixture는 임시 경로와 합성 binding 메타데이터를 사용한다. 초기화 안내, 공개 도구 설명·가이드, worker 스키마와 두 외부 카탈로그의 일치를 확인한다. 실제 모델링 동작은 이 검사의 범위 밖이다.
- [설치된 CLI 실행기 검사](../src/mcp/tests/runtime/test_terminal_launch.ps1)는 `./src/mcp/tests/runtime/test_terminal_launch.ps1 -Codex <installed-codex.exe>`에서 실제 CLI의 설정 해석을 사용한다. OS의 binding 관측은 대역을 사용하고 대화형 실행은 가로챈다. 실제 RhinoTerminal 세션의 도구 목록은 연결 후 별도로 확인한다.

[릴리스 준비 실행기](../src/rhp/tools/prepare_release.ps1)는 별도 셸에서 위 세 실행기와 패널 Node 검사를 호출한다. 릴리스용 Python 환경과 임시 폴더는 체크아웃 `data/t/` 아래에 두고, 세 pytest 결과를 릴리스 출력에 기록한다. SDK 경로를 지정할 때 `-DotNet`을 사용한다.

오프라인 검사에서 다루는 모델링·계산 동작의 범위는 실제로 실행한 사례에 한정된다.

Windows에서 symlink를 만드는 자산 경계 검사는 파일 시스템과 실행 환경의 symlink 생성 지원이 필요하다. `WinError 1314`가 symlink 생성에서 발생하면 해당 검사는 환경에서 중단된 것으로 기록하고, 전체 실행 결과에도 실패로 남긴다.

## 실제 Rhino 통합 검수

1. 통합 오케스트레이터는 사용자에게 검수할 워크트리·모델·변경 범위와 실제 Rhino 사용을 승인받는다. 문서나 DB를 바꾸는 검수는 별도 프로젝트 폴더의 복사본에서 한다. Worksession에는 필요한 파일만 붙인다.
2. 사용 중인 Rhino는 그대로 유지한다. 이미 로드된 assembly는 디스크의 새 빌드나 임시 등록 변경으로 교체되지 않는다. 기존 Rhino의 PID·시작 시각을 기록하고, 검수할 워크트리에서 `verify_runtime.py`로 소스·실행 파일의 manifest와 양쪽 Engine DLL을 확인한다. 일치하면 기존 빌드를 사용한다. 불일치하는 RHP만 대상 출력 사용 가능 여부를 확인한 뒤 다시 빌드하고 manifest를 기록·검증한다. Engine 변경은 양쪽을 빌드한다. 해당 워크트리 RHP를 이미 로드한 이전 검수 인스턴스가 있다면 그 인스턴스만 정상 종료한 뒤 출력 교체를 진행한다.
3. 검수할 워크트리에서 `./src/rhp/tools/start_integration_rhino.ps1 -ModelPath '<시험 파일.3dm>'`을 실행한다. 스크립트는 시작 전에 시험 파일의 절대 경로를 출력하고, 기존 등록을 보존한 뒤 두 RHP 경로를 워크트리로 임시 지정해 새 Rhino를 시작한다. 이때 시작한 PID·시작 시각으로만 프로세스를 추적한다. 새 인스턴스에서 워크트리 RHP 두 개의 실제 로드 경로가 확인되면 즉시 기존 등록값을 복원하며, 시작 실패 시에도 복원을 수행한다. 이어서 같은 워크트리의 Beyond에서 Rhino PID·시작 시각·시험 파일 경로가 일치하는 대상에 `ready`로 연결되는지 확인한다. 검증 연결을 해제하고 같은 PID의 RHP를 재확인한 뒤 검증 결과를 반환한다.
4. 기능 검수는 같은 워크트리에서 시작한 Beyond에서 수행한다. `connect_01-list_up` tool에서 시작 스크립트가 확인한 대상의 `host_id`·PID·모델 경로를 대조하고 `connect_02-session` tool로 연결한다. 변경된 기능은 공개 도구로 검수한다. Rhino 내부 확인은 연결된 시험 문서에서 `script_02-run_rhino` tool을 사용한다. 결과를 기록하고 시험 연결과 식별한 검수용 Rhino만 정상 종료한 뒤 일상 경로에서 `install_runtime.ps1 -VerifyOnly`로 등록을 확인한다. 사용자의 기존 Rhino에는 연결·종료·문서 변경을 수행하지 않는다.

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
