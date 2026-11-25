# Personal Almond fork

## 작업 원칙

- 한국어로 답하고, 기존 호출부를 확인한 뒤 필요한 최소 변경만 한다. SuperPower는 요청 없이는 사용하지 않는다.
- 사용자는 개발자가 아니다. 실제 사용할 때까지의 절차를 생략하지 말고, 바꾼 파일과 결과를 구체적으로 설명한다.
- 개발 워크트리, GitHub main, 일상 폴더, 디스크의 RHP·의존 파일, Rhino 등록, 실행 중 로드된 assembly를 구분한다. 소스 수정은 설정 변경이라고 축소하지 않는다.
- 빌드 성공·파일 배치·등록·실제 로드·모델링 검증은 각각 별도 증거다. 구현과 현재 상태를 확인하지 않고 재빌드·재시작을 단정하지 않는다.
- 기존 사용자 변경·모델·DB를 보존한다. Rhino를 강제 종료하거나 로드된 RHP를 덮어쓰지 않는다.
- 개발 검사와 티켓별 검증은 오프라인으로 수행한다. 여러 개발 결과를 통합하는 오케스트레이터는 사용자와 대상·변경 범위를 협의하고 명시적으로 허가받은 경우에만 [실제 Rhino 통합 검수](tests/README.md#실제-rhino-통합-검수)를 수행한다.
- PowerShell·UTF-8을 사용하고 `rg` 패턴은 작은따옴표로 감싼다. 재귀 삭제·이동 전 절대 경로가 작업 범위 안인지 확인한다.
- 설정 완료 후 답변하라는 요청에는 일상적인 설명을 줄이고, 중요한 차단과 직접 질문에만 즉시 답한다.
- 태스크는 세션을 기준으로 관리한다. 같은 세션에서 이어지는 작업은 기존 태스크의 범위·진행 내용·결정·검증 근거를 갱신하며 이어가고, 별도 후속 태스크로 분리해 진행 맥락을 끊지 않는다.
- 세션에 위임할 때 질문은 질문 도구 대신 메시지로 하도록 전달한다. 질문과 각 선택지에 각각 번호를 붙이고, 답이 필요한 이유와 작업에 미치는 영향을 함께 설명한다.
- 티켓 위임 직전과 일상 폴더의 squash 반영 후에는 [작업 워크트리와 squash 검증](tests/README.md#작업-워크트리와-squash-검증)의 검사기를 실행한다.

## 구조와 변경 경계

이름과 실행 경로는 [GLOSSARY.md](GLOSSARY.md)와 [연결 경로 안내](src/mcp/runtime/CONNECTION-SPEC.md)를 따른다. 구조는 [SPEC.md](SPEC.md), 기능별 사용법은 [README.md](README.md)의 링크를 필요할 때 읽는다.

- `src/mcp`: upstream Python MCP·계산·라이브러리 API.
- `src/mcp/runtime`: CLI 실행·연결·공유 저장소와 MCP 실행기. 외부 연결기는 이 실행기의 공개 확장 훅을 사용한다.
- `src/rhp/Engine`: Bridge·AlmondRhino가 공유하는 별도 `Almond.Engine.dll`.
- `src/beyond`: Codex 직접 연결의 외부 host/worker, 도구 카탈로그, `rhp/`의 AlmondRhino 플러그인 소스와 자체 빌드·테스트.
- `src/rhp/RhinoAlmondBridge`: Bridge RHP. `Structural_Analysis`, `Asset_Panel`, `RhinoTerminal` 소스도 여기에 컴파일한다. Terminal에는 별도 PlugIn entry가 없다.
- `src/rhp/AlmondRhino`: 공용 외부 연결용 Rhino 플러그인의 출력 폴더. 구현은 `src/beyond/rhp`에 둔다. 패널의 공용 웹 원본은 `src/rhp/Asset_Panel/web`이다.
- `src/engine`: 예전 시작 버튼·설치 명령의 전달 스크립트와 일상 실행용 `.venv`만 유지한다. 구현을 추가하지 않는다.
- 모듈 전용 테스트는 각 모듈의 `tests/`, 여러 모듈의 계약 검사는 루트 `tests/`에 둔다. 의존 방향·변경 범위는 [소유권과 의존 방향](SPEC.md#소유권과-의존-방향)를 따른다.

Bridge assembly·GUID·패널 GUID·명령·도구 schema·Undo/Redo 계약을 보존한다. 경로 정리 때문에 기능을 리팩터링하지 않는다. Engine DLL을 Bridge RHP나 상위 리포의 `mcp/native`와 혼동하지 말고 설치된 패키지를 패치하지 않는다.
이 저장소는 상위 Rhino 리포의 `mcp/almond-mcp` 서브모듈이다. 이 리포의 commit/push 이후 상위 gitlink를 갱신하며, 상위의 다른 작업과 섞지 않는다. 개인 통합은 `main`, upstream `codex/undo-recovery`는 기존 `release/0.7.0rc2` Undo 수정 범위를 유지한다.

## 일상 실행과 최초 설치

일상 폴더는 브랜치 이름과 무관하게 `C:\TOOL\Rhino\mcp\almond-mcp`다. 평소 Rhino의 Bridge/AlmondRhino 등록과 beyond command/args를 이곳에 고정한다. 통합 검수에서 사용자가 워크트리 런타임 직접 등록을 허가하면 [검수 절차](tests/README.md#실제-rhino-통합-검수)의 임시 등록·복구를 따른다. 사용 중인 Rhino는 기존에 로드한 assembly를 계속 사용하므로 유지한다. 검수용 새 PID·시작 시각으로 워크트리 RHP 로드를 확인하면 기존 등록을 즉시 원복하고 시험 모델의 연결을 검증한다. 종료와 기능 검사는 식별한 검수 인스턴스만 대상으로 한다.

최초 설치에는 해당 환경의 host/worker와 Rhino 연결을 종료한 뒤 리포 루트에서 실행한다.

```powershell
./src/mcp/rebuild_environment.ps1
./src/rhp/tools/install_runtime.ps1
```

첫 명령은 `src/engine/.venv`에 Python 3.12.12·`uv.lock` 의존성과 editable MCP를 구성한다. 둘째는 기존 등록을 `data/runtime-install`에 백업하고 다음 고정 파일을 등록한다. 예전 `src/engine/rebuild_environment.ps1`은 첫 명령에 전달한다. 외부 Codex를 사용할 때만 [beyond의 클라이언트 등록 절차](src/beyond/EXTERNAL_CLIENTS.md#한-번-설정하기)를 추가로 따른다.

| 플러그인 | 등록 파일 | GUID |
|---|---|---|
| Bridge | `src/rhp/RhinoAlmondBridge/plugin-runtime/RhinoAlmondBridge.rhp` | `c337dbb8-394a-4593-9c2b-a3d7cfc91893` |
| AlmondRhino | `src/rhp/AlmondRhino/plugin-runtime/AlmondRhino.rhp` | `39eb74f6-8283-4e43-bf26-f0106d891b75` |

등록 확인은 `./src/rhp/tools/install_runtime.ps1 -VerifyOnly`다. RHP 경로, 현행 연결 명령, 폐기된 연결 명령의 잔존 여부를 검사한다. 갱신이 필요하면 Rhino를 닫고 이 스크립트를 `-VerifyOnly` 없이 실행한다. 기존 등록을 백업한 뒤 폐기된 연결 명령을 제거한다. 실제 로드 경로 확인은 사용자가 별도로 요청한 경우 새 Rhino에서 수행하며, 등록 검증과 구분한다. 예전 standalone Terminal GUID `27D4B9A1-8FAD-421C-B64A-7A213D3B4079`가 남았다면 백업 후 중복 등록을 제거한다.

Codex에 이전 연결 주소나 중복 등록이 남았거나 기존 실행·종료 기록을 새 위치로 옮겨야 하면 [일회성 전환 절차](src/beyond/EXTERNAL_CLIENTS.md#기존-설치-전환)를 따른다.

전환을 마친 이후 업데이트는 **Rhino를 정상 종료 → 일상 폴더에서 `git pull --ff-only` → Rhino 시작** 순서다. pull은 fetch와 현재 브랜치·추적 파일의 fast-forward를 수행한다. fetch만으로 파일은 바뀌지 않고, 실행 중 Rhino는 이미 로드한 assembly를 계속 쓴다. 소스와 실행 파일을 함께 받으므로 매번 빌드·복사·등록할 필요가 없다.

- 외부 실행: `src/mcp/runtime/Almond 시작.cmd`에서 저장된 모델을 선택한다.
- Rhino 내부: `RhinoTerminal` → `On`; 패널이 숨으면 `PanelToggle`로 표시한 뒤 `almond`를 입력하거나 우측 상단 버튼을 누른다. 재연결은 `almond resume` 또는 resume 버튼. `Off`는 패널 표시와 무관하게 터미널을 종료한다.
- 외부 Codex (beyond): 저장된 Rhino 문서에서 `almondconnect`를 실행하고 클라이언트에서 host/model을 선택한다. 연결 해제는 `almonddisconnect` 또는 클라이언트의 `connect_04-disconnect` tool다.
- 패널: `Almond`, `AlmondLibrary`, `AlmondStructure`, `AlmondResults`. 패널이 숨으면 Terminal/Layers와 같은 dock에 둔다.

## 개발·빌드·반영

기존 적합한 워크트리를 우선 사용한다. 새 작업은 최신 `main`에서 분기하고 환경은 각 체크아웃에서 새로 구성한다. venv를 복사·공유하지 않는다. 작업 폴더를 바꾸는 것만으로 모델 DB·슬롯·로드된 RHP가 격리되지는 않는다.

일반 시작은 의존성을 동기화하지 않는다. Python 공통 도구 변경 후에는 관련 beyond MCP 또는 Terminal의 almond 세션을 정상 종료하고 새로 시작한다. 시작 시 현재 소스에서 도구 schema를 자동 추출하므로 카탈로그 수동 재생성은 필요 없다. `uv.lock` 버전·세션 source fingerprint·실제 worker schema 검사를 유지한다. 기존 프로세스에 대한 hot reload/restart 도구는 제공하지 않는다.

Rhino 실행 여부와 관계없이 개발 워크트리에서 RHP를 빌드할 수 있다. 빌드 스크립트는 대상 출력 파일의 사용 가능 여부를 확인하고 staging 후 교체한다. .NET 8 SDK와 Windows Rhino 8 SDK를 사용하며 기본 빌드는 설치된 SDK를 참조한다. 선택 SDK 위치는 `src/rhp/RhinoTerminal/data/sdk`다.

```powershell
./src/rhp/build.ps1
./src/beyond/build.ps1
& ./src/engine/.venv/Scripts/python.exe -B src/rhp/tools/verify_runtime.py --record
& ./src/engine/.venv/Scripts/python.exe -B src/rhp/tools/verify_runtime.py
```

Bridge와 AlmondRhino 출력은 위의 각 `plugin-runtime` 폴더다. Engine을 변경했다면 양쪽을 빌드해 `Almond.Engine.dll`이 같게 한다. RHP와 의존 DLL·deps/runtimeconfig JSON·archive를 함께 추적한다. Rhino 제공 DLL은 포함하지 않는다. 빌드는 staging 후 교체하며 등록하지 않는다. Terminal과 AlmondRhino는 이 고정 출력 위치에서 `src/mcp/runtime`을 찾으므로 출력 깊이를 유지한다.

검증 기록은 `src/rhp/RhinoAlmondBridge/runtime-manifest.json`과 `src/beyond/runtime-manifest.json`으로 나뉜다. 모듈별 빌드 후에는 `verify_runtime.py --record --component bridge` 또는 `--component beyond`로 자기 기록만 갱신한다. 통합 시 옵션 없이 검사하면 양쪽 기록과 Engine 바이너리 일치까지 확인한다.

**개발 워크트리에서 구현·빌드·검증 → 소스와 실행 파일을 같은 commit → push·PR·merge → Rhino를 닫고 일상 폴더에서 pull → 사용자 Rhino 시작 시 새 런타임 로드**가 전체 전달 순서다. 실제 로드 검증은 별도 요청이 있을 때 수행한다. 사용자에게 빌드·바이너리 복사·등록 수정을 떠넘기는 소스만의 전달은 하지 않는다. commit, push, merge, 일상 파일 갱신과 실제 로드를 각각 구분해 보고한다.

## 데이터와 실행 안전

기존 AppData 라이브러리와 명시적 `RHINO_MCP_*_DIR`을 보존한다. 저장소 `asset/`, wheel의 `almond_mcp/data/`, AppData의 이름은 서로 다른 배치다. Bridge와 Python의 라이브러리 경로를 일치시키고 원본 다운로드 URL·manifest 상대 경로·모델 바이트·해시를 임의로 바꾸지 않는다. 자산 준비·등록·갱신의 잠금 범위는 [자산 스펙](src/mcp/features/assets/SPEC.md)을 따른다.

모델 폴더는 `.almond/scene.sqlite3`를 공유한다. Plan 산출물은 프로젝트 `.almond/produced/YYMMDD_name`, 연결별 임시자료는 `.almond/tmp/python/<token>/<operation>`에 둔다. 종료된 연결의 소유 임시자료와 `.sessions` 기록은 프로세스·잠금·native 완료로 회수하며 Plan·Step 완료 여부와 연결하지 않는다. 공유 잠금·역할 lease·A–J 슬롯·프로세스 identity·UI thread·native 완료 확인을 유지한다. 모델을 이동·이름 변경하기 전에 연결을 정상 종료한다.

프로젝트 정보가 필요하면 `context_04-get_project_info` tool에서 필요한 sections만 조회한다. document 항목이 live 문서를 함께 확인하므로 같은 확인을 위해 `inspect_03-get_document_context` tool를 반복 호출하지 않는다. 런타임의 `ALMOND_PROJECT_ROOT`를 기준으로 worker는 상대경로를 쓰고, 파일 작성 전 `plan_10-set_working` tool으로 산출물 폴더를 선택한다. 작업은 미완료 상태로 중단·전환·재개할 수 있다. beyond 외부 연결에서는 connect_02-session tool/connect_03-start_session tool으로 선택한 연결을 재사용한다. 고정 조회는 일반 수정 실행기를 사용하지 않는다. timeout·`result_error`는 rollback이 아니며 완료가 불명확한 수정을 자동 재시도하지 않는다. 상세 계약은 [관측 SPEC](src/mcp/rhino/OBSERVATION-SPEC.md)를 따른다.

임시 개발 자료는 ignored `data/`에 두고 모델 데이터와 섞지 않는다. SPEC·AGENTS에는 현재 구조·계약·작업 규칙만 유지한다. 과거 설계안·진행 보고·커밋별 변경 내역·검증 실측은 누적하지 않는다. 사용자 모델·DB 삭제는 명시 요청이 있을 때만 한다.

공개 도구명은 `<category>_<NN>-<name>`을 사용하며 기존 이름의 별칭은 등록하지 않는다. DESCRIPTION·입력 설명·후속 안내에서 등록된 도구를 언급할 때는 `<공개 도구명> tool`로 표기한다. Python 함수명·native command·DB 식별자는 공개 호출명과 구분한다.

공개 도구 계약에 영향을 주는 변경을 마무리할 때 구현 함수의 docstring에 있는 도구 설명·입력 안내, [출력 계약](src/mcp/output_contracts.py), [공통 공개 스키마 기준](tests/integration/tool_schemas.json)을 현재 구현과 실제 공개 스키마에 대조하고, 달라진 내용을 갱신한다. 코드 기반 예시와 실제 Rhino 검증 결과를 구분한다.

공개 도구 등록·입력·출력 스키마 또는 문서에 수록된 계약을 바꾸면 같은 변경에서 [현행 툴 선언](TOOL-DECLARATIONS-CURRENT.md)을 갱신한다. 커밋 전 현재 체크아웃의 beyond·RhinoTerminal `tools/list`로 도구 목록·설명·입력·출력 스키마의 일치와 문서의 누락·폐기 도구 여부를 확인한다. `initialize`에서 공통 안내 전달을 확인한 뒤 변경을 함께 커밋한다.

## 검증

- 변경에 맞는 검사·명령·판정 기준은 [개발 검사 안내](tests/README.md)에서 고른다. 개발 검사는 Rhino와 일상 MCP 호스트를 실행하거나 종료할 필요 없이 수행할 수 있게 유지한다. 체크아웃별 개발 환경을 사용해 일상 venv·호스트·연결 등록을 보존한다. 실행 중 호스트의 소스까지 보호해야 하면 별도 워크트리를 사용한다.
- C# 오프라인 fixture와 RHP 빌드는 Rhino가 열린 상태에서도 수행할 수 있다. 출력 위치와 교체 절차는 [개발·빌드·반영](#개발빌드반영)을 따른다.
- Rhino에서만 확인할 수 있는 동작은 개발 검사 범위 밖이다. 통합 오케스트레이터가 허가받아 검수한 경우 실제 Rhino 결과를 별도로 보고한다. 오프라인 fixture에는 전용 입력을 사용한다.
- 검사별 결과와 실제 확인 범위를 기록한다. 기존 실패와 환경 제약을 보고하고 검증 기준을 보존한다.
