# 외부 연결기와 AlmondRhino 계약

beyond는 외부 Codex와 로컬 stdio MCP 클라이언트의 직접 연결을 제공하며 AlmondRhino 플러그인을 소유한다.
[루트 작업 지침](../../AGENTS.md)과 [공통 경계](../../SPEC.md)를 함께 따른다.

직접 연결은 `src/beyond/codex_host.py`에서 stdio 서버를 시작하고 Rhino 연결마다 `external_worker.py`를 실행한다.
외부 Codex CLI는 실행 시 설정을 전달해 연결할 수 있다. 여러 실행에서 쓸 등록과 이전 기록을 전환하는 절차는 [외부 클라이언트 안내](#한-번-설정하기)와 [기존 설치 전환](#기존-설치-전환)을 따른다.
공개 호출명은 `context_04-get_project_info`, `connect_02-session`, `connect_03-start_session`처럼 `<category>_<NN>-<name>` 형식이며 이전 이름의 alias를 공개하지 않는다. 클라이언트가 붙이는 서버 namespace는 도구 schema와 별개다.
등록·initialize·tools/list는 catalog만 제공하며 broker·worker· Rhino·모델 DB 연결이나 소유권 잠금을 준비하지 않는다. stdio 통신을 위한 클라이언트별 최소 Python 프로세스는 필요하다. 모델링 준비는 명시적 connect_02-session tool/connect_03-start_session tool 호출에서 한다.
사용 방법과 동시 연결 제한은 [외부 클라이언트 안내](#codex와-외부-mcp-클라이언트-사용)에 둔다.

Rhino 연결 명령은 `almondconnect`·`almonddisconnect`다. AlmondRhino의 플러그인 GUID는 `39eb74f6-8283-4e43-bf26-f0106d891b75`다.
connect_02-session tool는 discovery host를 재사용하고 connect_04-disconnect tool는 기존 native drain·worker 종료 확인을 거쳐 연결만 해제한다. Rhino 문서는 유지한다.
`connect_05-close_session` tool은 연결된 문서의 변경 여부를 조회하고 공식 RhinoCode `_Save`로 기존 파일명에 저장한다. 저장 완료·동일 문서의 저장 상태를 확인한 뒤 `_-Exit`로 정상 종료한다. 요청 ID별 OS 잠금·보관 결과·대상별 진행 기록으로 재호출과 호스트 재시작의 중복 저장·종료를 막는다. 종료 직전 guard와 실제 프로세스 종료·worker 종료·lease 해제를 구분해 입증한다. 상세 절차는 [연결 계약](../mcp/runtime/CONNECTION-SPEC.md)에 둔다.

## 구성

| 위치 | 책임 |
|---|---|
| `codex_host.py` | Codex와 외부 로컬 MCP 클라이언트의 직접 연결 진입점, stdio 서버와 연결 관리 |
| `external_worker.py` | Rhino 연결별 worker |
| `codex_host.py`의 서버 설명 | 건축설계·모델링·도면·연결 관리 역할을 담은 공통 소개 |
| `session_start.py` | 명시적 요청으로 새 Rhino를 열고 해당 프로세스의 외부 연결 광고 확인 |
| `execution_invocation.py` | 선택된 연결의 호출 예약·취소·첫 응답 대기·완료 복구. 연결 탐색·attach·detach는 Broker가 소유 |
| `session_close.py` | 저장·종료 순서, 호출별 Rhino 종료 가드 생성, 보관 결과 조회. 연결 잠금 아래 `ExecutionInvocations`에서 저장 결과를 확인하고 별도 프로세스 근거로 종료를 확인한다. |
| `detached_process.py` | 새 프로세스를 suspended 상태로 생성하고 모든 Windows Job 밖임을 확인한 뒤 실행 |
| `runtime.py`, `build_catalog.py` | 시작 시 MCP에서 읽은 공통 schema의 lockfile 버전·source fingerprint·worker schema 검사 |
| `data/tool_catalog.json` | `build_catalog.py`로 만드는 Git 추적 제외 개발용 export. 런타임은 현재 소스에서 schema를 생성함 |
| `binding_watch.py`, `winpipe.py` | 연결 변경 감시와 Windows 제어 채널 |
| `rhp/` | Rhino 내부 almondconnect·almonddisconnect 명령·host 탐색·문서 binding |
| `tests/`, `run_tests.ps1` | 연결 수명과 실행 결과 복구, Python 클라이언트와 C# 제어 파이프 사이의 통신을 검사한다. 실제 AlmondRhino 호스트는 Rhino 통합 검수에서 확인한다. |
| `build.ps1`, `runtime-manifest.json` | AlmondRhino RHP 빌드와 소스·실행 파일 검증 기록 |

## 의존·연결 계약

Python worker는 MCP runtime의 기존 `main`, binding 검증·구성 훅과 완료 receipt를 사용한다. 저장소 잠금·native 완료·자산 helper 정책을 외부 연결기에 복제하지 않는다.
RHP는 [공용 Engine](../rhp/SPEC.md#구성과-빌드)을 참조한다. Bridge·Terminal의 구현 소스를 AlmondRhino에 링크하지 않는다.

새 클라이언트의 catalog는 [공용 MCP 선언 판독기](../mcp/tool_declarations.py)로 feature와 문서 전용 도구의 등록 이름·MCP annotations를 확인하고 패키지의 `public_contract_data.json`에서 해당 schema를 읽는다. 선언 판독기와 실행 서버는 같은 feature 목록을 사용한다. 판독기는 handler나 서버를 import하지 않고 중복 도구명을 거절한다. fingerprint는 runtime의 검토된 소스와 공개 계약 JSON 및 MCP package 전체 Python 파일 목록·내용을 포함하여 feature 파일의 추가·삭제·이동도 감지한다. 패키지 버전은 `uv.lock`과 대조한다. 추출 중 소스 변경, 시작한 클라이언트와 worker의 snapshot 불일치, 실제 worker schema 불일치를 검사하며 불일치하면 모델링 요청을 보내지 않는다.
선언 파일을 처음 읽은 바이트에서 AST와 fingerprint를 함께 구한다. 카탈로그를 완성한 뒤 파일 목록과 내용을 다시 읽어 처음 기록과 대조한다.
관측 이미지는 별도 MCP image content로 전달한다. 호스트는 공통 공개 선언에 맞춰 결과를 전달하며 연결 관리와 실행 기록 복구의 공개 응답에도 같은 계약을 적용한다. 캡처의 표시 모드 인자는 연결 전에도 사용할 수 있다. 클라이언트 초기화 시 확인한 공통 메뉴 GUID를 입력 예시로 제공한다. 현재 모드 목록은 `inspect_03-get_document_context` tool에서 조회하고, 적용 가능 여부는 연결된 Rhino에서 판단한다.
공통 도구 변경 후 수동 catalog 재생성 없이 관련 beyond MCP를 정상 종료·재시작하면 새 구현과 schema를 읽는다. Terminal은 almond 세션을 새로 시작한다. 이미 시작한 프로세스를 자동 교체하거나 restart 도구를 제공하지 않는다. RHP/DLL 변경은 빌드와 Rhino의 정상 종료·새 시작이 별도로 필요하다.

연결별 PID·token·문서 binding·worker·잠금은 각 Connection에 유지한다. connect_02-session tool과 connect_03-start_session tool은 해당 연결의 connection_id를 반환한다. 같은 host_id/model_path에 다시 연결하면 활성 연결 ID를 재사용한다. beyond에서 호출자는 ID를 대화별로 보관하고 일반 호출·연결 해제·종료 요청마다 최상위 인자로 전달한다. host는 이 값으로 연결을 찾아 원래 도구 인자를 worker에 전달한다. 요청 접수 시점의 대상을 유지한다.

종료 요청과 script_03-get_execution tool의 보관 결과는 원래 request_id로 재조회한다. beyond는 원래 connection_id도 일치해야 연결 해제나 호스트 재시작 후에 보관된 결과를 읽는다. 실행 request_id를 비우면 지정한 활성 연결의 최근 실행을 읽는다. connection_id 기록이 도입되기 전의 미확정 실행은 기존 host에서 조회한 뒤 업데이트한다.

connection ID와 token·프로세스 identity·저장 문서를 함께 확인한다. 변경된 binding, 미확인 native 결과, 실행 중 작업의 해제·취소에 대한 기존 소유권 규칙을 유지한다.
다른 연결의 DB 접근은 기존 공유 lease·gate를 통과한다.

연결 감시는 `ready.json`의 생성·삭제·이름 변경만 받아 인증된 RHP 상태를 확인한다. 감시를 등록한 직후 또는 Windows가 통지 일부를 잃었을 때도 상태를 확인한다. RHP는 worker와 native 작업의 종료를 기다리는 동안 발행에 성공한 무효 사유를 반복 기록하지 않는다. 발행 실패와 최종 소유권 해제는 재시도한다.

공유 DB gate와 같은 연결의 요청 직렬화 잠금은 획득을 최대 10초 기다린다. 초과한 대기 호출은 operation/native 요청을 시작하지 않고 종료한다. 실행 중인 소유자의 잠금을 해제하거나 수정을 자동 재시도하지 않는다. 실제 모델링 실행 제한·cleanup·native drain 대기는 이 값과 별개다.

각 adapter는 자신의 connection ID만 처리한다. 활성 제어 연결은 Rhino PID·시작 시각별 독점 파일 lease를 유지한다. 다른 클라이언트의 Rhino는 목록에 `in_use`로 표시하고 그 pipe에 접속하지 않는다. `host.lock`은 같은 데이터 위치의 활성 연결들이 공유하는 잠금이다.
같은 위치에서 singleton host가 독점 중이면 새 연결을 거절한다. 어떤 잠금 파일도 삭제하지 않는다.
adapter lease 해제는 RHP의 native/slot/token 소유권 해제가 아니다. 미확인 native 작업의 기존 RHP binding은 계속 새 attach를 거절한다.

`connect_03-start_session` tool은 저장된 절대 `.3dm` 경로와 request ID를 받는다. 기존 runtime의 모델 경로 검증을 재사용하고 새 Rhino에 `_almondconnect` 명령을 전달한다. 정확히 그 PID·시작 시각의 광고만 기존 connect_02-session tool 경로에 연결한다. A–J 슬롯·DB·native 준비는 기존 RHP Attach와 worker 계약을 사용하며 시작 로직에 복제하지 않는다. 모델을 저장하거나 Rhino를 강제 종료하지 않는다. launch/advertise 실패 후 새 프로세스를 자동 실행하지 않는다.
새 프로세스는 `CREATE_BREAKAWAY_FROM_JOB`으로 생성하고 실행 전 `IsProcessInJob`으로 중첩 Job까지 벗어났는지 확인한다. 분리 불가 시 아직 한 줄도 실행하지 않은 suspended 프로세스만 폐기하고 시작을 거절한다. Terminal의 자식 종료 규칙은 완화하지 않으며 이미 열린 Rhino는 건드리지 않는다. 해당 환경에서는 Rhino를 직접 열고 connect_02-session tool한다.

request ID는 한 adapter 수명 안에서 시작 시도 하나를 가리킨다. startup timeout 뒤 같은 ID로 호출하면 이미 시작한 프로세스만 재조회한다. connect_02-session tool가 실패하면 같은 ID로 attach를 반복하지 않는다. caller 취소 뒤에도 결과를 보존하고, adapter 종료 때는 시작 대기를 취소하고 기존 연결 정리를 수행한다. 열린 Rhino는 남는다. adapter를 재시작한 뒤에는 연결 목록으로 남은 Rhino를 확인해야 한다.

완료 결과 재조회는 공통 runtime이 원본 실행 근거를 읽고 조정한 다음 공개 응답만 축약한다. 정상 완료의 결과·페이지·요청한 로그·복구 대상 정보는 남기며 `include_diagnostics=true`로 전체 근거를 조회한다. 실패·불확실·부분 변경·0이 아닌 CLI 종료 코드·결과 표시 오류는 기본 응답에서도 유지한다. 보관 파일 복구 경로도 같은 projection을 사용하며 journal, worker schema 검사와 완료 판단을 바꾸지 않는다.

외부 worker는 공통 runtime 구성 훅으로 두 공개 스크립트의 첫 완료 근거 대기를 최대 60초로 제한한다. 공개 스크립트의 기본값은 60초, 범위는 1–600초다. 클라이언트 호출 대기의 생성 기본값은 Codex 직접 연결 기준 240초다. `ExecutionInvocations`는 공개 스크립트의 응답 대기가 끝나도 원래 worker tools/call을 취소하지 않는다. 비공개 caller ID·runtime operation ID·durable RhinoCode request ID를 대조하여 CLI-only인 현재 실행의 상태만 반환한다. 아직 durable ID가 없거나 native 결과가 불확실하면 미확인 오류를 반환하며 기존 native fence를 유지한다. 대기 종료는 재실행·강제 종료·완료 증거가 아니다.

원 worker 호출이 정리 중이면 같은 직렬 잠금을 사용하는 worker 조회 대신 검증된 보관 파일을 읽는다. 완료 receipt가 먼저 생겨도 원 호출과 runtime 정리가 끝나기 전에는 예약을 해제하지 않는다. exact 완료·native 상태·binding이 모두 확인된 뒤에만 해당 예약을 end한다. Broker 예약 ID를 공개 실행 request_id로 대신 쓰거나 종료·무효화된 연결을 되살리지 않는다.

## 빌드·검증·설치

`build_catalog.py`는 개발용 카탈로그를 내보낸다. Python 환경과 RHP 설치는 [루트 설치 절차](../../AGENTS.md#일상-실행과-최초-설치), 외부 클라이언트 설정은 [연결 안내](#한-번-설정하기)를 따른다.

`build.ps1`은 `rhp/AlmondRhino.csproj`를 staging에서 빌드한 뒤 출력 위치인 `../rhp/AlmondRhino/plugin-runtime`에 배치한다. 로드된 파일을 덮어쓰지 않으며 빌드가 Rhino 등록·실제 로드를 의미하지 않는다. plugin GUID·assembly identity는 유지한다.

AlmondRhino 전용 C# 변경은 이 모듈의 runtime-manifest.json만 갱신한다. 공유 Engine 변경은 두 소비자 RHP를 빌드하고 양쪽 검사 기록과 Engine DLL 일치를 확인한다. 변경별 실행 순서와 worker·카탈로그 공개 계약 검사는 [개발 검사 안내](../../tests/README.md)를 따른다.

## 공통 모델링 안내

외부 host는 `codex_host.py`의 서버 설명을 초기화 응답의 `serverInfo.description`과 `instructions` 앞부분에 제공한다. MCP 서버 이름은 `beyond`다.
이어서 기술 참고 자료 조회 방법과 `guide_version`을 전달한다. 연결을 선택하기 전에도 `context_01-get_policy` tool에서 공개 도구 목록과 기술 참고 자료를 읽을 수 있다. 연결을 선택한 뒤 `context_04-get_project_info` tool로 현재 문서와 실제 Worksession 첨부, DB 파일 목록 및 작업 경로를 조회한다.
`context_01-get_policy` tool은 연결 선택 전에도 외부 host에서 읽을 수 있다. Rhino-bound worker와 같은 정책 로더를 사용해 JSON text content와 structured content를 전달한다. `metadata`는 Rhino 객체 키 사전을 반환한다. 카탈로그는 worker와 같은 정책 선택값을 공개하고 개별 도구의 설명 전문을 `tools/list`에 제공한다. 정책 파일·도구 소스·설명 Markdown은 session source fingerprint에 포함한다.
안내 조회 계약과 갱신 절차는 [MCP SPEC](../mcp/SPEC.md#모델링-안내-전달)을 따른다.

## Codex와 외부 MCP 클라이언트 사용

Codex 직접 연결은 `src/beyond/codex_host.py`를 표준 **stdio MCP 서버**로 실행한다.
RhinoTerminal과 beyond의 연결 방식은 [연결 경로 안내](../mcp/runtime/CONNECTION-SPEC.md)를 따른다.

MCP 등록과 클라이언트 시작 시에는 **도구 목록을 제공하는 최소 stdio 프로세스**만 실행된다.
모델링 worker·Rhino·모델 DB 연결은 시작하지 않는다. 사용하는 대화에서 연결 또는 시작 도구를 명시적으로 호출하면 필요한 준비를 한다.

### 한 번 설정하기

일상 설치의 Python 환경과 RHP는 [저장소 설치 안내](../../AGENTS.md)를 따른다. 외부 Codex CLI에서 현재 실행에만 beyond를 붙이려면 다음을 PowerShell에서 실행한다. `config.toml`을 수정하지 않는다.

```powershell
$almondRoot = 'C:/TOOL/Rhino/mcp/almond-mcp'
$almondOverrides = @(
    '-c', "mcp_servers.rhino.command='$almondRoot/src/engine/.venv/Scripts/python.exe'",
    '-c', "mcp_servers.rhino.args=['-B', '-X', 'utf8', '-u', '$almondRoot/src/beyond/codex_host.py']",
    '-c', "mcp_servers.rhino.cwd='$almondRoot'",
    '-c', 'mcp_servers.rhino.startup_timeout_sec=120',
    '-c', 'mcp_servers.rhino.tool_timeout_sec=240',
    '-c', "mcp_servers.rhino.env.PYTHONUTF8='1'",
    '-c', "mcp_servers.rhino.env.PYTHONIOENCODING='utf-8'",
    '-c', "mcp_servers.rhino.env_vars=['LOCALAPPDATA', 'TEMP', 'TMP', 'TMPDIR', 'RHINO_MCP_LIBRARY_DIR', 'RHINO_MCP_DRAWING_ASSET_DIR', 'RHINO_MCP_DIAGRAM_ASSET_DIR', 'RHINO_MCP_GENERATED_ASSET_DIR', 'RHINO_MCP_DRAWING_RECIPE_DIR', 'RHINO_MCP_DRAFTING_DIR', 'RHINO_MCP_CAPSULE_DIR', 'RHINO_MCP_MATERIAL_DIR', 'RHINO_MCP_CONSTRUCTION_DIR', 'RHINO_MCP_HISTORY_DIR']",
    '-c', 'mcp_servers.rhino.enabled=true'
)
codex @almondOverrides
```

Codex 앱이나 다음 실행에서도 사용할 등록은 Codex의 MCP 설정에서 직접 관리한다. stdio 항목 이름은 `rhino`, 실행 파일은 일상 폴더의 `src/engine/.venv/Scripts/python.exe`, 인자는 `-B`, `-X`, `utf8`, `-u`, `src/beyond/codex_host.py`의 절대 경로다. 작업 폴더, 시작 및 호출 제한, UTF-8과 라이브러리 환경 변수는 위 예시와 동일하게 지정한다. 이미 현행 `rhino` 등록이 있는 경우 그 등록을 사용한다. 이전 진입점이나 중복 등록은 [기존 설치 전환](#기존-설치-전환)을 따른다.

다른 로컬 MCP 클라이언트에서도 같은 실행 파일과 인자를 stdio 서버로 등록한다. 도구 호출 제한은 클라이언트 설정에서 **600초**로 지정한다. 라이브러리 경로를 별도로 사용하면 해당 `RHINO_MCP_*_DIR` 환경 변수도 서버에 전달한다.

실제로 사용할 Codex 대화에서 **`connect_01-list_up` tool을 직접 호출**해 연결할 Rhino가 나타나는지 확인한다. Codex 직접 연결의 MCP 서버 이름은 `beyond`이고 Rhino 측 플러그인은 `AlmondRhino`다. Codex의 등록 키 `rhino`와 클라이언트가 붙이는 namespace는 서버 이름과 구분한다.

`script_01-run_project_python` tool과 `script_02-run_rhino` tool은 외부 연결에서 첫 완료 대기를 최대 60초로 제한한다. 더 짧은 `timeout_seconds`는 그대로 사용한다. 실행이 계속되면 `pending`과 `request_id`를 받아 `script_03-get_execution` tool로 같은 ID를 조회한다. 완료 근거가 없으면 결과 미확인 오류를 반환한다.

[Codex 공식 MCP 명령 안내](https://learn.chatgpt.com/docs/developer-commands#codex-mcp). RhinoTerminal과 전용 시작기가 띄우는 Codex CLI는 해당 실행에 `rhino_session`을 설정한다.

### 매번 사용하기

저장된 모델을 새 Rhino에서 시작하려면:

1. 일반 Codex 대화에서 "`C:\작업\모델.3dm`을 Almond의 새 세션으로 열어 줘"라고 요청한다.
2. Codex가 `connect_03-start_session` tool에 절대 `model_path`와 새 `request_id`를 전달한다.
   새 Rhino를 열고 `_almondconnect`를 자동 실행한 뒤 해당 프로세스에만 연결한다. 원본 모델을 저장하거나 기존 Rhino를 종료하지 않는다.
3. 시작 결과의 `connection_id`를 이 대화에 보관한다. 프로젝트·문서 정보가 필요하면 `context_04-get_project_info` tool에 그 ID와 필요한 sections를 전달한다. project/document는 한 번의 live 확인을 공유하고, project에 파일 목록·문서 이름·경로·is_bound_document가 나온다. DB·선택 Plan의 산출물 경로는 locations에서 조회한다. 자료를 작성할 때는 `plan_10-set_working` tool으로 Plan의 `artifact_dir`를 선택한다.
4. 작업 문서를 저장하고 Rhino까지 종료하려면 `connect_05-close_session` tool에 `connection_id`와 새 `request_id`를 전달한다. 저장 완료를 확인한 뒤 정상 종료한다. 연결만 해제하고 창을 유지하려면 `connect_04-disconnect` tool에 `connection_id`를 전달한다.

새 Rhino는 디스크에 저장된 파일을 연다. 다른 Rhino 창의 저장되지 않은 변경을 복제하지 않는다.
다른 Codex 대화에서도 별도 Rhino 세션을 시작할 수 있다. beyond와 Terminal은 슬롯 A–J를 공유한다.

이미 열린 일반 Rhino에 연결하려면:

1. 해당 Rhino 8에서 `.3dm`을 열고 저장한 뒤 `almondconnect`를 실행한다.
2. 등록된 Codex 앱이나 외부 Codex CLI에서 "Almond 연결 목록을 확인하고 이 문서에 연결해 줘"라고 요청한다. 클라이언트가 `connect_01-list_up` tool를 호출한다.
3. 목록의 정확한 `host_id`와 `model_path`로 `connect_02-session` tool를 호출한다.
   연결·시작 성공 응답의 `model_path`와 `connection_id`를 현재 대화에 함께 저장한다. `store/load`가 있는 Codex에서는 연결마다 변수를 두고 후속 호출에 작업할 연결의 ID를 전달한다. 같은 경로의 파일을 여러 Rhino 창에서 열었다면 응답의 `host_id`로 창을 구분한다.
4. 필요할 때 `context_04-get_project_info` tool에서 프로젝트·live 문서를 함께 조회한다. 같은 확인을 위해 `inspect_03-get_document_context` tool를 반복 호출하지 않는다. 자료 작성 전 `plan_10-set_working` tool으로 폴더를 선택하고, 설계 작업 지침이 필요하면 별도로 설치한 [RhinoBeyond 스킬](../../.agents/skills/rhinobeyond/SKILL.md)을 사용한다.
5. 저장·정상 종료는 `connect_05-close_session` tool에 연결 ID와 새 요청 ID를, 창을 유지한 연결 해제는 `connect_04-disconnect` tool에 연결 ID를 전달한다. 문서 변경 후에는 재연결한다.

`connect_05-close_session` tool이 지연되거나 결과가 불확실하면 원래의 `connection_id`와 `request_id`로 다시 조회한다. 이 조회는 Save·Exit를 반복하지 않는다. 저장 실패·읽기 전용 문서·저장 뒤 새 변경이 있으면 문서를 닫지 않고 사유를 반환한다. `completed`는 저장 확인, 실제 Rhino 프로세스 종료, worker 종료와 연결 소유권 해제를 모두 확인한 결과다. 같은 문서의 다른 연결이나 다른 Rhino 창은 종료하지 않는다.

Rhino에서 직접 해제하려면 `almonddisconnect`를 사용한다. 처리 중인 작업이나 worker의 종료가 아직 확인되지 않으면 완료 안내를 기다린다. Rhino와 모델은 저장·종료하지 않는다.
Bridge의 `AlmondMCPStart`·`AlmondMCPStop`·`AlmondMCPStatus`는 퇴역 명령이다.

`almondconnect`는 Rhino를 발견 가능하게 만드는 명령이다. Codex 프로그램을 자동 실행하거나 새 채팅에 자동 연결하지는 않는다. 새 시작 도구는 이 명령을 새 Rhino에 자동 전달한다.
Rhino가 없으면 MCP 초기화와 도구 목록은 정상이고 연결 가능한 문서 목록만 비어 있다. 기존 `Almond 시작.cmd`·`RhinoTerminal → almond`로 관리되는 Rhino는 기존 전용 CLI를 사용하거나, 연결을 정상 종료한 뒤 일반 Rhino로 연다.

### 공통 도구를 수정했을 때

이 파일은 설치·사용·개발 참고 문서다. `codex_host.py`의 서버 설명은 초기화 응답에 실린다. `output_contracts.py`는 공통 공개 선언에서 도구 설명과 입출력 schema를 제공한다. 실행 상태에 따른 사유는 각 도구의 응답에서 확인한다.

Codex 직접 연결에서는 `context_01-get_policy` tool, `connect_01-list_up` tool, `connect_02-session` tool, `connect_03-start_session` tool을 연결 ID 없이 호출한다. 나머지 도구는 매번 `connection_id`를 받는다. 생략하면 `connection_id가 지정되지 않았습니다` 오류로 요청이 중단된다. 연결 해제나 MCP 재시작 뒤 보관된 결과를 조회할 때는 `script_03-get_execution` tool 또는 `connect_05-close_session` tool에 원래의 `connection_id`와 `request_id`를 함께 전달한다.

Codex 직접 연결기는 공통 도구 입력에 필요한 `connection_id`를 추가한다. RhinoTerminal은 시작할 때 바인딩한 문서 전용 세션을 사용한다. 외부 연결기는 연결 관리 도구를 추가한다. 카탈로그를 따로 갱신할 필요는 없다.
Python 도구 변경 후 해당 beyond MCP를 정상 종료하고 새로 시작하면 현재 소스의 구현·목록·입력 schema를 읽는다. Terminal은 almond 세션을 정상 종료·재시작한다.
업데이트 뒤에 기존 실행을 다시 조회하려면 원래의 두 ID와 프로젝트 쪽 실행 기록이 모두 필요하다. 연결 ID를 기록하기 전에 만들어진 실행은 업데이트 전에 기존 호스트에서 필요한 결과를 파일로 저장한다.
Rhino만 재시작해도 외부 beyond MCP 프로세스가 살아 있으면 그 메모리는 바뀌지 않는다.
이미 실행 중인 프로세스의 자동 갱신이나 restart 도구는 이번 범위에 포함하지 않는다.
C#/RHP/DLL 수정은 빌드된 실행 파일을 반영한 뒤 Rhino를 정상 종료·재시작해야 한다.

### 동시 연결과 시작 지연

- 클라이언트의 Windows 실행 환경이 독립 프로세스를 허용하지 않으면 새 Rhino 시작을 모델을 열기 전에 거절한다. 이 경우 Rhino를 평소처럼 직접 열고 `almondconnect` → `connect_01-list_up` tool → `connect_02-session` tool로 연결한다. Terminal의 Off가 별도 Rhino를 닫지 않도록 실행 전에 확인하는 제한이며, 기존 Terminal의 자식 종료 규칙은 바꾸지 않는다.

- 여러 beyond stdio adapter가 같은 설치를 사용할 수 있다. 각 Rhino는 한 연결의 소유권을 유지한다. Codex는 각 호출에 지정한 연결 ID로 문서를 찾는다.
  다른 클라이언트가 사용하는 Rhino는 `in_use`로 표시한다. 그 연결을 유지하면서 `connect_03-start_session` tool으로 별도 Rhino를 열 수 있다.
- 같은 데이터 위치를 사용하는 singleton host가 살아 있으면 새 활성 연결은 차단한다. 기존 작업을 정상 마친 뒤 해당 beyond MCP를 재시작해 새 Python 소스를 로드한다. RHP 안내 문구는 일상 업데이트 후 새 Rhino에서 반영된다. 잠금 파일을 삭제하지 않는다.
- Rhino 시작 확인이 늦으면 응답에 표시된 PID의 창과 등록 상태를 확인한다. 같은 `model_path`와 **같은 `request_id`**로 다시 호출하면 같은 프로세스를 재조회한다. 새 ID는 새 Rhino를 여는 별도 요청이다. attach 실패나 결과 불명 오류를 새 ID로 자동 반복하지 않는다.
- 새 Rhino의 시작 요청 기록은 현재 MCP adapter 수명에 한정된다. MCP 재시작 후 모델 작업을 계속하려면 `connect_01-list_up` tool로 남은 Rhino를 확인하고 연결한다. 이전 시작 요청을 자동 재실행하지 않는다.
- 공유 DB 및 같은 연결의 요청 직렬화 잠금 대기는 최대 **10초**다. 대기 초과 호출은 작업을 실행하지 않으며, 기존 실행 중인 작업과 소유권을 유지한다. 실제 모델링 실행시간 제한과 연결 종료 시 native 완료 대기는 별도다. 대기 초과 뒤 수정을 자동 반복하지 않는다.
- Windows 사용자 세션의 named pipe를 사용한다. 이 진입점은 stdio만 지원하며 원격 URL, SSE/HTTP 서버를 제공하지 않는다.
- timeout은 rollback이 아니다. 결과 불명인 수정은 자동 반복하지 않는다.

### 기존 설치 전환

일상 폴더 `C:\TOOL\Rhino\mcp\almond-mcp`의 직접 연결 주소와 복구 기록을 새 위치로 옮기는 배포에 한 번 적용한다.

1. 현재 사용하는 설정에서 `[mcp_servers.rhino]`와 이전 등록 `[mcp_servers.almond_cos]`의 `args`를 확인한다. 다른 stdio 클라이언트는 연결에 쓰는 항목의 `args`를 확인한다. 주소가 이미 현행이어도 기록은 이전 위치에 있을 수 있다. 업데이트 전에 일상 폴더의 `src/*/data/` 아래에서 `execution-locators`와 `session-closes`를 각각 찾아 어느 위치에 기록이 있는지 확인한다. 데이터 위치를 따로 지정한 설치는 그 경로도 확인한다.
2. 새 작업을 시작하지 않고 진행 중인 실행·저장·종료의 결과를 기존 클라이언트에서 확인한다. **연결을 해제하기 전에** 기존 클라이언트에서 보관할 실행의 `request_id`를 지정해 `script_03-get_execution` tool로 결과를 조회한다. 결과가 여러 페이지면 끝까지 조회하고, 필요한 결과 본문을 연결별 임시 폴더 밖에 JSON 파일로 저장해 열어 본다. 전환 뒤 재조회할 기록의 `connection_id`와 `request_id`도 보관한다. 현재 연결을 정상 해제하고 MCP 클라이언트를 종료한다. 해당 host·worker·종료 guard가 끝났는지 확인한 뒤 Rhino를 정상 종료한다. 완료가 불명확하거나 프로세스가 남아 있으면 기록 이동과 pull을 보류한다.
3. 전환 커밋을 받을 일상 브랜치에서 `git pull --ff-only`를 실행해 `src/beyond/codex_host.py`가 생겼는지 확인한다. 목적지는 각각 `src/beyond/data/execution-locators`와 `src/beyond/data/session-closes`다. 이전 기본 위치에 기록이 있는 종류만 옮긴다. 원본과 목적지의 절대 경로가 일상 폴더 안에 있는지 확인하고, 양쪽에 기록이 있으면 먼저 요청별 내용을 대조해 충돌을 해결한다. 이동 전후에 상대경로별 파일 수와 해시를 확인한다. 호스트 광고·잠금 등 다른 데이터는 기존 위치에 두고, 별도로 지정한 데이터 위치는 그대로 사용한다.
4. 기존 Codex 설정을 백업한 뒤 `rhino` 등록의 host 인수를 일상 폴더의 `src/beyond/codex_host.py` 절대 경로로 맞춘다. 이전 `almond_cos` 항목을 전환할 경우 양쪽 설정을 비교해 필요한 사용자 설정과 환경 변수를 보존하고, 퇴역 등록만 제거한다. `codex mcp get rhino --json`으로 경로와 옵션을 확인한다. 등록을 저장할 필요가 없는 CLI는 [실행별 설정](#한-번-설정하기)을 사용할 수 있다.
5. Rhino를 시작하기 전에 `./src/rhp/tools/install_runtime.ps1 -VerifyOnly`로 RHP 경로, 현행 명령값, AlmondRhino의 폐기 명령 캐시 두 항목의 잔존 여부를 검사한다. 갱신 또는 제거가 필요하면 Rhino를 닫은 상태에서 `./src/rhp/tools/install_runtime.ps1`을 실행하고 다시 확인한다. 설치 명령은 레지스트리를 백업한 뒤 지정된 폐기 값만 제거하며 다른 명령값을 보존한다.
6. 일상 클라이언트를 다시 로드한다. `execution-locators`에는 실행 기록을 찾는 정보만 있다. 프로젝트에 원본 실행 기록이 남아 있으면 원래의 `connection_id`와 `request_id`로 `script_03-get_execution` tool에서 결과를 다시 조회할 수 있다. 같은 프로젝트에서 새 연결을 시작하면 이전 실행 기록이 정리될 수 있다. 재조회에 실패하면 3단계의 이동 결과를 확인하고, 원본 실행 기록이 이미 정리됐다면 2단계에서 저장한 파일을 연다. 종료 요청은 옮긴 `session-closes` 아래의 `request.json`에서 원래의 요청 ID·연결 ID와 종료 상태를 확인한다. Rhino에서 `almondconnect`로 문서를 표시하고, 실제 사용할 대화의 `connect_01-list_up` tool에서 그 문서가 보이는지 확인한다. [실행 결과 복구 검사](tests/test_execution_contract.py)와 [연결 종료 검사](tests/test_session_contract.py)는 일회용 데이터로 원래 요청의 결과 조회와 연결 종료를 확인한다. 실제로 옮긴 기록은 이 단계의 원래 ID로 확인한다.

### 일반 업데이트

외부 연결과 Rhino를 정상 종료하고 일상 폴더에서 `git pull --ff-only`를 실행한다. Rhino를 시작하고 beyond 클라이언트를 다시 로드한 뒤 해당 문서에 연결한다.

## Dot 클라이언트 사용

`src/dots/dot_client.py`는 `codex_host.py`를 자식 프로세스로 실행한다. 실행할 서버 경로와 세션은 Dot 프로세스가 관리한다.

### Dot 시작과 세션 유지

```powershell
& ./src/engine/.venv/Scripts/python.exe -B -X utf8 -u src/dots/dot_client.py
```

동지의 실행 도구에서는 지속형 터미널(`tty=true`)로 시작하고 반환된 터미널 `session_id`에 후속 입력을 보낸다. 입력은 한 줄 JSON이며 끝에 Enter를 붙인다. 클라이언트는 서버 시작 → initialize → tools/list를 수행한 뒤 `ready`를 출력한다. 초기 출력은 서버 소개·instructions, 도구 이름 목록, 클라이언트 사용법이며 개별 description 전체를 반복하지 않는다.

프로세스를 유지하는 동안 같은 MCP 세션을 사용한다. 터미널의 `session_id`로 실행 도구의 프로세스를 재사용한다. 호출하는 대화에서 `connect_02-session` tool 또는 `connect_03-start_session` tool이 반환한 `connection_id`를 보관한다. 연결이 필요한 후속 호출마다 `arguments.connection_id`에 작업할 문서의 값을 직접 지정한다. 생략하면 `connection_id가 지정되지 않았습니다` 오류로 호출이 중단된다.

Dot에서는 `"connection_id":"$connection_id"`라고 명시하면 이 프로세스에서 마지막으로 연결에 성공한 ID를 사용한다. 실제 ID를 입력하면 해당 연결을 사용한다. 빈 값이나 초기화되지 않은 변수 참조도 같은 오류로 중단된다.

### Dot 명령

각 입력에 선택적인 `id`를 붙이면 응답에 그대로 반환한다.

```json
{"id":"help","op":"help"}
{"id":"names","op":"catalog"}
{"id":"definitions","op":"describe","names":["connect_01-list_up","connect_02-session","context_04-get_project_info"]}
{"id":"available","op":"call","name":"connect_01-list_up","arguments":{}}
```

`describe`는 이름 배열에 해당하는 전체 description, inputSchema와 제공되는 outputSchema·annotations를 원본 그대로 반환한다. 현재 세션 시작 때 받은 catalog를 사용한다. 알려지지 않은 이름이나 잘못된 명령 형식은 서버를 호출하지 않고 오류로 반환한다.

실제 대상 선택은 `connect_01-list_up` tool에서 확인한 정확한 값으로 한다. 아래 값은 설명용 자리표시자다.

```json
{"op":"call","name":"connect_02-session","arguments":{"host_id":"<목록의 host_id>","model_path":"<목록의 model_path>"}}
{"op":"call","name":"context_04-get_project_info","arguments":{"connection_id":"$connection_id","sections":["document"]}}
{"op":"call","name":"connect_04-disconnect","arguments":{"connection_id":"$connection_id"}}
{"op":"shutdown"}
```

`connect_02-session` tool 이후의 호출도 같은 실행 도구 session_id에 입력한다. 다른 클라이언트가 소유한 Rhino를 빼앗거나 잠금 파일을 삭제하지 않는다. 새 Rhino는 자동으로 만들지 않으며 `connect_03-start_session` tool은 명시적인 요청일 때만 호출한다.

실행·종료 결과를 나중에 조회하려면 원래 작업의 `connection_id`와 `request_id`를 함께 보관한다. Dot을 재시작한 뒤에도 두 값을 직접 지정해 보관 결과를 조회한다.

```json
{"op":"call","name":"script_03-get_execution","arguments":{"connection_id":"<기존 연결 ID>","request_id":"<실행 요청 ID>"}}
{"op":"call","name":"connect_05-close_session","arguments":{"connection_id":"<기존 연결 ID>","request_id":"<종료 요청 ID>"}}
```

### Dot 응답과 오류

`call`의 `tool_result`는 MCP 결과를 원형 보존한다. content의 text·image, structuredContent, isError 등을 축약하거나 재해석하지 않는다. `ok=true`는 클라이언트가 응답을 받았다는 뜻이며, 도구의 성공은 `tool_result.isError`와 본문을 함께 확인한다. 이미지는 JSON의 MCP 이미지 블록으로 반환되며 이 CLI가 화면에 렌더링하지는 않는다.

잘못된 입력 뒤에도 클라이언트는 다음 입력을 기다린다. 호출 오류·timeout을 자동 재시도하지 않는다. timeout은 rollback 증거가 아니며 변경 호출을 다시 보내기 전 결과를 확인한다. 요청은 한 번에 하나씩 처리한다.

`shutdown` 또는 정상 EOF는 이 클라이언트가 만든 MCP 연결을 정리한다. Rhino 파일을 저장하거나 Rhino를 종료하지 않는다. 작업이 끝났으면 먼저 `connect_04-disconnect` tool로 연결 해제를 확인한다. 강제 프로세스 종료와 정상 정리를 혼동하지 않는다.

호출 제한 기본값은 600초다. `--timeout`, `--server-python`, `--server-entry`는 명시적으로 변경할 때만 사용한다. 서버 stdout은 MCP 전용이고 클라이언트 stdout은 위 JSON 출력용이다. 터미널 화면의 줄바꿈·ANSI 코드는 전송 JSON 데이터가 아니다.

### Dot 검증

```powershell
& ./data/development/.venv/Scripts/python.exe -B -X utf8 -m pytest -q src/dots/tests
```

실제 Dot CLI와 일회용 MCP 서버 사이에서 도구 목록 페이지, 연결 선택, 이미지와 오류 응답, 시간 초과 시 재전송 여부를 검증한다.
