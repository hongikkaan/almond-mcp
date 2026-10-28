# beyond 외부 연결기 계약

beyond는 Codex 직접·CoS 경유 연결의 공용 외부 연결기다. 이 모듈은 기존 Rhino 연결 플러그인도 소유한다.
[작업 지침](AGENTS.md)과 [공통 경계](../../SPEC.md)를 함께 따른다.

CoS는 `cos_host.py`, Codex·외부 로컬 MCP 클라이언트는 `codex_host.py`를 진입점으로 사용한다.
두 진입점은 `external_host.py`의 같은 stdio 연결기와 worker를 사용한다.
`client_config.py`는 일상 설치의 설정을 생성하고 명시적으로 요청할 때만 Codex 설정에
`rhino` 항목을 추가한다. 이전 `almond_cos` 항목이 이 생성기의 설정과 정확히 같을 때만
원본 백업 후 이름을 이전하고, 수정된 항목이나 중복·충돌은 변경 없이 거절한다.
공개 도구는 `project_info`, `connect`, `start_session` 등 접두사 없는 이름을 사용하고
이전 이름의 alias를 공개하지 않는다. 클라이언트가 붙이는 서버 namespace는 도구 schema와 별개다.
등록·initialize·tools/list는 catalog만 제공하며 broker·worker·
Rhino·모델 DB 연결이나 소유권 잠금을 준비하지 않는다. stdio 통신을 위한 클라이언트별
최소 Python 프로세스는 필요하다. 모델링 준비는 명시적 connect/start_session 호출에서 한다.
사용 방법과 동시 연결 제한은 [외부 클라이언트 안내](EXTERNAL_CLIENTS.md)에 둔다.

Rhino 연결 명령은 `almondconnect`·`almonddisconnect`다. 기존 `AlmondCOS`와
`AlmondCOSDisconnect` 명령/별칭은 등록하지 않는다. RHP 파일명·GUID·등록 경로는 유지한다.
연결 준비 및 상태 안내는 Codex와 CoS 모두에 적용된다. connect는 discovery host를 재사용하고
disconnect는 기존 native drain·worker 종료 확인을 거쳐 연결만 해제한다. Rhino 문서는 유지한다.

## 구성

| 위치 | 책임 |
|---|---|
| `external_host.py`, `cos_worker.py` | 공용 외부 stdio adapter와 Rhino 연결마다 분리된 worker |
| `cos_host.py`, `codex_host.py` | CoS 경유·Codex 직접 연결의 명시적인 진입점과 MCP 서버 식별 |
| `SERVER-DESCRIPTION.md` | 건축설계 용도·연결 관리 도구 4개·연결 및 해제 방법을 담은 공통 소개 |
| `session_start.py` | 명시적 요청으로 새 Rhino를 열고 해당 프로세스의 외부 연결 광고 확인 |
| `detached_process.py` | 새 프로세스를 suspended 상태로 생성하고 모든 Windows Job 밖임을 확인한 뒤 실행 |
| `runtime.py`, `build_catalog.py` | 시작 시 현재 공통 schema 추출, lockfile 버전·source fingerprint·worker schema 검사 |
| `data/tool_catalog.json` | configure/build에서 만드는 Git 추적 제외 개발용 export; 런타임은 읽지 않고 현재 소스에서 schema를 생성함 |
| `binding_watch.py`, `winpipe.py` | 연결 변경 감시와 Windows 제어 채널 |
| `rhp/` | Rhino 내부 almondconnect·almonddisconnect 명령·host 탐색·문서 binding |
| `tests/`, `run_tests.ps1` | Python·native relay·host 수명·pipe·stdio 검사 |
| `build.ps1`, `runtime-manifest.json` | COS RHP 빌드와 소스·실행 파일 검증 기록 |

## 의존·연결 계약

Python worker는 MCP runtime의 기존 `main`, binding 검증·구성 훅과 완료 receipt를
사용한다. 저장소 잠금·native 완료·자산 helper 정책을 COS에 복제하지 않는다.
RHP는 [공용 Engine](../rhp/Engine/AGENTS.md)을 참조한다. Bridge·Terminal의 구현
소스를 COS에 링크하지 않는다.

새 클라이언트의 catalog 생성은 MCP server와 `features/*/tools.py`의 `register` 내부 도구 AST에서
schema만 읽고 DB를 소유하는 MCP server를 import하지 않는다. 같은 이름의 중복
도구는 거절한다. fingerprint는 runtime의 검토된 소스와 MCP package 전체 Python
파일 목록·내용을 포함하여 feature 파일의 추가·삭제·이동도 감지한다. 패키지 버전은
`uv.lock`과 대조한다. 추출 중 소스 변경, 시작한 클라이언트와 worker의 snapshot 불일치,
실제 worker schema 불일치를 검사하며 불일치하면 모델링 요청을 보내지 않는다.
관측 이미지의 직접 `ToolResult`와 context의 정확한 `str | ToolResult` 반환형만 별도로
허용한다. ToolResult 입력형·중첩형·임의 annotation 실행은 허용하지 않는다. context 기본
JSON과 선택한 PNG의 MCP content 계약을 schema 생성 때문에 바꾸지 않는다. context에 한해
기존 `{result: string}` output schema literal을 허용하고 text/structuredContent를 함께 보존한다.
공통 도구 변경 후 수동 catalog 재생성 없이 관련 Codex/CoS MCP를 정상 종료·재시작하면
새 구현과 schema를 읽는다. Terminal은 almond 세션을 새로 시작한다. 이미 시작한
프로세스를 자동 교체하거나 restart 도구를 제공하지 않는다. RHP/DLL 변경은 빌드와
Rhino의 정상 종료·새 시작이 별도로 필요하다.

connection ID와 token·프로세스 identity·저장 문서를 함께 확인한다. 변경된 binding,
미확인 native 결과, 실행 중 작업의 해제·취소에 대한 기존 소유권 규칙을 유지한다.
다른 연결의 DB 접근은 기존 공유 lease·gate를 통과한다.

공유 DB gate와 같은 연결의 요청 직렬화 잠금은 획득을 최대 10초 기다린다. 초과한 대기
호출은 operation/native 요청을 시작하지 않고 종료한다. 실행 중인 소유자의 잠금을 해제하거나
수정을 자동 재시도하지 않는다. 실제 모델링 실행 제한·cleanup·native drain 대기는 이 값과 별개다.

각 adapter는 자신의 connection ID만 처리한다. 활성 제어 연결은 Rhino PID·시작 시각별
독점 파일 lease를 유지한다. 다른 클라이언트의 Rhino는 목록에 `in_use`로 표시하고 그
pipe에 접속하지 않는다. `host.lock`은 활성 연결들이 공유하는 이전 버전 호환 barrier다.
이전 singleton host가 독점 중이면 새 연결을 거절한다. 어떤 잠금 파일도 삭제하지 않는다.
adapter lease 해제는 RHP의 native/slot/token 소유권 해제가 아니다. 미확인 native 작업의
기존 RHP binding은 계속 새 attach를 거절한다.

`start_session`은 저장된 절대 `.3dm` 경로와 request ID를 받는다. 기존
runtime의 모델 경로 검증을 재사용하고 새 Rhino에 `_almondconnect` 명령을 전달한다. 정확히
그 PID·시작 시각의 광고만 기존 connect 경로에 연결한다. A–J 슬롯·DB·native 준비는
기존 RHP Attach와 worker 계약을 사용하며 시작 로직에 복제하지 않는다. 모델을 저장하거나
Rhino를 강제 종료하지 않는다. launch/advertise 실패 후 새 프로세스를 자동 실행하지 않는다.
새 프로세스는 `CREATE_BREAKAWAY_FROM_JOB`으로 생성하고 실행 전 `IsProcessInJob`으로
중첩 Job까지 벗어났는지 확인한다. 분리 불가 시 아직 한 줄도 실행하지 않은 suspended
프로세스만 폐기하고 시작을 거절한다. Terminal의 자식 종료 규칙은 완화하지 않으며
이미 열린 Rhino는 건드리지 않는다. 해당 환경에서는 Rhino를 직접 열고 connect한다.

request ID는 한 adapter 수명 안에서 시작 시도 하나를 가리킨다. startup timeout 뒤 같은
ID로 호출하면 이미 시작한 프로세스만 재조회한다. connect가 실패하면 같은 ID로 attach를
반복하지 않는다. caller 취소 뒤에도 결과를 보존하고, adapter 종료 때는 시작 대기를 취소하고
기존 연결 정리를 수행한다. 열린 Rhino는 남는다. adapter를 재시작한 뒤에는 연결 목록으로
남은 Rhino를 확인해야 한다.

## 빌드·검증·설치

`configure.ps1`은 이 체크아웃의 catalog와 `cos-plugin.json`을 생성한다. CoS 앱
등록은 하지 않는다. 기존 command는 `../engine/.venv/Scripts/python.exe`와 이 폴더의
`cos_host.py`를 사용하므로 소스 재편 뒤에도 그대로 유지된다.

`build.ps1`은 `rhp/AlmondCOS.csproj`를 staging에서 빌드한 뒤 기존 등록 위치인
`../rhp/AlmondCOS/plugin-runtime`에 배치한다. 로드된 파일을 덮어쓰지 않으며
빌드가 Rhino 등록·실제 로드를 의미하지 않는다. plugin GUID·assembly identity는 유지한다.

COS 전용 C# 변경은 COS manifest만 갱신한다. Engine을 변경하면 두 소비자 RHP를
빌드하고 루트 통합 검사로 DLL 일치까지 확인한다. MCP 공개 도구 변경에 따른
자동 schema 추출과 실제 worker의 일치도 통합 검사 대상이다.

## 공통 모델링 안내

외부 host는 `SERVER-DESCRIPTION.md`를 초기화 응답의 `serverInfo.description`과
`instructions` 앞부분에 제공한다. 두 연결 경로의 MCP 표시 이름과 앱 등록용 생성 설정 이름은
`beyond`이며, 기존 `src/cos` 경로·실행 파일·native 식별자는 유지한다.
ChatGPT의 `Chat On Steroids Plugins` 공통 소개는 클라이언트가 관리하므로, 서버 소개를
수정한 것만으로 해당 화면에 표시되었다고 판단하지 않는다.
이어서 MCP package의 시작 안내를 제공한다. `project_info`도 원본 도구
설명을 유지하므로 document의 live 조회와 선택 instructions 항목이 정확히 안내된다.
`get_modeling_guide`는 기존 worker 도구 전달 경로를 사용한다. 연결 후 connection_id가
필요하며 control·binding·receipt 예외를 추가하지 않는다. 텍스트·선택 이미지 content를
그대로 전달한다. bundle Markdown·manifest·PNG도 session source fingerprint에 포함한다.
주제 계약과 갱신 절차는 [MCP SPEC](../mcp/SPEC.md#모델링-안내-전달)을 따른다.
