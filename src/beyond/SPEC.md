# 외부 연결기와 AlmondRhino 계약

beyond는 외부 Codex와 로컬 stdio MCP 클라이언트의 직접 연결을 제공하며 AlmondRhino 플러그인을 소유한다.
[루트 작업 지침](../../AGENTS.md)과 [공통 경계](../../SPEC.md)를 함께 따른다.

직접 연결의 진입점은 `src/beyond/codex_host.py`이며 `external_host.py`의 stdio 연결기와 worker를 사용한다.
`client_config.py`는 기본 실행에서 설정을 출력한다. `--install-codex`는 지정한 Codex 설정 파일에 `rhino`를 등록한다. 같은 일상 설치에서 생성한 이전 주소와 중복 등록은 현행 `rhino` 하나로 합치고, 사용자 설정과 충돌하면 쓰기 전에 중단한다. 기존 파일을 바꿀 때만 원본을 백업하며, 이미 현행 등록이면 재실행해도 파일과 백업이 그대로다. 실행·종료 기록의 이전은 [배포 절차](EXTERNAL_CLIENTS.md#기존-설치-전환)에서 별도로 처리한다.
공개 호출명은 `context_04-get_project_info`, `connect_02-session`, `connect_03-start_session`처럼 `<category>_<NN>-<name>` 형식이며 이전 이름의 alias를 공개하지 않는다. 클라이언트가 붙이는 서버 namespace는 도구 schema와 별개다.
등록·initialize·tools/list는 catalog만 제공하며 broker·worker· Rhino·모델 DB 연결이나 소유권 잠금을 준비하지 않는다. stdio 통신을 위한 클라이언트별 최소 Python 프로세스는 필요하다. 모델링 준비는 명시적 connect_02-session tool/connect_03-start_session tool 호출에서 한다.
사용 방법과 동시 연결 제한은 [외부 클라이언트 안내](EXTERNAL_CLIENTS.md)에 둔다.

Rhino 연결 명령은 `almondconnect`·`almonddisconnect`다. AlmondRhino의 플러그인 GUID는 `39eb74f6-8283-4e43-bf26-f0106d891b75`다.
connect_02-session tool는 discovery host를 재사용하고 connect_04-disconnect tool는 기존 native drain·worker 종료 확인을 거쳐 연결만 해제한다. Rhino 문서는 유지한다.
`connect_05-close_session` tool은 연결된 문서의 변경 여부를 조회하고 공식 RhinoCode `_Save`로 기존 파일명에 저장한다. 저장 완료·동일 문서의 저장 상태를 확인한 뒤 `_-Exit`로 정상 종료한다. 요청 ID별 OS 잠금·보관 결과·대상별 진행 기록으로 재호출과 호스트 재시작의 중복 저장·종료를 막는다. 종료 직전 guard와 실제 프로세스 종료·worker 종료·lease 해제를 구분해 입증한다. 상세 절차는 [연결 계약](../mcp/runtime/CONNECTION-SPEC.md)에 둔다.

## 구성

| 위치 | 책임 |
|---|---|
| `external_host.py`, `external_worker.py` | 공용 외부 stdio adapter와 Rhino 연결마다 분리된 worker |
| `codex_host.py` | Codex와 외부 로컬 MCP 클라이언트의 직접 연결 진입점 |
| `external_host.py`의 서버 설명 | 건축설계·모델링·도면·연결 관리 역할을 담은 공통 소개 |
| `session_start.py` | 명시적 요청으로 새 Rhino를 열고 해당 프로세스의 외부 연결 광고 확인 |
| `execution_invocation.py` | 선택된 연결의 호출 예약·취소·첫 응답 대기·완료 복구. 연결 탐색·attach·detach는 Broker가 소유 |
| `session_close.py`, `session_close_guard.py.txt` | 저장·종료 순서와 보관 결과 조회를 관리한다. 연결 잠금 안에서 `ExecutionInvocations`로 저장을 실행하거나 이전 저장 결과를 회수하고, 종료는 별도 프로세스 근거로 확인한다. |
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

새 클라이언트의 catalog는 [공용 MCP 선언 판독기](../mcp/tool_declarations.py)로 feature와 문서 전용 도구의 schema를 읽는다. 선언 판독기와 실행 서버는 같은 feature 목록을 사용한다. 판독기는 handler나 서버를 import하지 않고 중복 도구명을 거절한다. fingerprint는 runtime의 검토된 소스와 MCP package 전체 Python 파일 목록·내용을 포함하여 feature 파일의 추가·삭제·이동도 감지한다. 패키지 버전은 `uv.lock`과 대조한다. 추출 중 소스 변경, 시작한 클라이언트와 worker의 snapshot 불일치, 실제 worker schema 불일치를 검사하며 불일치하면 모델링 요청을 보내지 않는다.
선언 파일을 처음 읽은 바이트에서 AST와 fingerprint를 함께 구한다. 카탈로그를 완성한 뒤 파일 목록과 내용을 다시 읽어 처음 기록과 대조한다.
관측 이미지의 직접 `ToolResult`와 고정 조회의 정확한 `str | ToolResult` 반환형만 별도로 허용한다. ToolResult 입력형·중첩형·임의 annotation 실행은 허용하지 않는다. context·선택·객체·교차 조회는 기존 `{result: string}` output schema literal을 허용하고 JSON text/structuredContent와 명시적 오류 상태를 함께 보존한다. PNG는 별도 캡처 도구의 MCP image content로 전달하며 schema 생성 때문에 이 계약을 바꾸지 않는다.
공통 도구 변경 후 수동 catalog 재생성 없이 관련 beyond MCP를 정상 종료·재시작하면 새 구현과 schema를 읽는다. Terminal은 almond 세션을 새로 시작한다. 이미 시작한 프로세스를 자동 교체하거나 restart 도구를 제공하지 않는다. RHP/DLL 변경은 빌드와 Rhino의 정상 종료·새 시작이 별도로 필요하다.

연결별 PID·token·문서 binding·worker·잠금은 각 Connection에 유지한다. connect_02-session tool과 connect_03-start_session tool은 해당 연결의 connection_id를 반환한다. 같은 host_id/model_path에 다시 연결하면 활성 연결 ID를 재사용한다. beyond에서 호출자는 ID를 대화별로 보관하고 일반 호출·연결 해제·종료 요청마다 최상위 인자로 전달한다. host는 이 값으로 연결을 찾아 원래 도구 인자를 worker에 전달한다. 요청 접수 시점의 대상을 유지한다.

종료 요청과 script_03-get_execution tool의 보관 결과는 원래 request_id로 재조회한다. beyond는 원래 connection_id도 일치해야 연결 해제나 호스트 재시작 후에 보관된 결과를 읽는다. 실행 request_id를 비우면 지정한 활성 연결의 최근 실행을 읽는다. connection_id 기록이 도입되기 전의 미확정 실행은 기존 host에서 조회한 뒤 업데이트한다.

connection ID와 token·프로세스 identity·저장 문서를 함께 확인한다. 변경된 binding, 미확인 native 결과, 실행 중 작업의 해제·취소에 대한 기존 소유권 규칙을 유지한다.
다른 연결의 DB 접근은 기존 공유 lease·gate를 통과한다.

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

`build_catalog.py`는 개발용 카탈로그를 내보낸다. Python 환경과 RHP 설치는 [루트 설치 절차](../../AGENTS.md#일상-실행과-최초-설치), 외부 클라이언트 설정은 [연결 안내](EXTERNAL_CLIENTS.md#한-번-설정하기)를 따른다.

`build.ps1`은 `rhp/AlmondRhino.csproj`를 staging에서 빌드한 뒤 출력 위치인 `../rhp/AlmondRhino/plugin-runtime`에 배치한다. 로드된 파일을 덮어쓰지 않으며 빌드가 Rhino 등록·실제 로드를 의미하지 않는다. plugin GUID·assembly identity는 유지한다.

AlmondRhino 전용 C# 변경은 이 모듈의 runtime-manifest.json만 갱신한다. 공유 Engine 변경은 두 소비자 RHP를 빌드하고 양쪽 검사 기록과 Engine DLL 일치를 확인한다. 변경별 실행 순서와 worker·카탈로그 공개 계약 검사는 [개발 검사 안내](../../tests/README.md)를 따른다.

## 공통 모델링 안내

외부 host는 `external_host.py`의 서버 설명을 초기화 응답의 `serverInfo.description`과 `instructions` 앞부분에 제공한다. MCP 서버 이름은 `beyond`다.
이어서 기술 참고 자료 조회 방법과 `guide_version`을 전달한다. 연결을 선택하기 전에도 `context_01-get_policy` tool에서 공개 도구 목록과 기술 참고 자료를 읽을 수 있다. 연결을 선택한 뒤 `context_04-get_project_info` tool로 현재 문서와 실제 Worksession 첨부, DB 파일 목록 및 작업 경로를 조회한다.
`context_01-get_policy` tool은 연결 선택 전에도 외부 host에서 읽을 수 있다. Rhino-bound worker와 같은 정책 로더를 사용해 JSON text content와 structured content를 전달한다. `metadata`는 Rhino 객체 키 사전을 반환한다. 카탈로그는 worker와 같은 정책 선택값을 공개하고 개별 도구의 설명 전문을 `tools/list`에 제공한다. 정책 파일·도구 소스·설명 Markdown은 session source fingerprint에 포함한다.
안내 조회 계약과 갱신 절차는 [MCP SPEC](../mcp/SPEC.md#모델링-안내-전달)을 따른다.
