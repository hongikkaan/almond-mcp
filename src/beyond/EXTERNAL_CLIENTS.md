# Codex·외부 MCP 클라이언트 연결

Codex 직접 연결은 `src/beyond/codex_host.py`에서 표준 **stdio MCP 서버**인 `external_host.py`를 실행한다.
RhinoTerminal과 beyond의 연결 방식은 [연결 경로 안내](../mcp/runtime/CONNECTION-SPEC.md)를 따른다.

MCP 등록과 클라이언트 시작 시에는 **도구 목록을 제공하는 최소 stdio 프로세스**만 실행된다.
모델링 worker·Rhino·모델 DB 연결은 시작하지 않는다. 사용하는 대화에서 연결 또는 시작 도구를 명시적으로 호출하면 필요한 준비를 한다.

## 한 번 설정하기

일상 설치 폴더에서 실행한다. 개발 워크트리를 클라이언트나 Rhino에 등록하지 않는다.
Python 환경과 RHP 최초 설치는 [저장소 설치 안내](../../AGENTS.md)를 따른다.

```powershell
Set-Location C:\TOOL\Rhino\mcp\almond-mcp
# 미리 볼 때: 설정을 출력할 뿐 파일이나 연결을 변경하지 않는다.
& ./src/engine/.venv/Scripts/python.exe -B src/beyond/client_config.py
# 실제 Codex 등록: rhino 항목을 설치하거나 이전 생성 등록을 전환한다.
& ./src/engine/.venv/Scripts/python.exe -B src/beyond/client_config.py --install-codex "$env:USERPROFILE/.codex/config.toml"
```

다른 `CODEX_HOME`을 쓰는 CLI라면 그 디렉터리의 `config.toml` 경로를 명시한다.
기존 `rhino` 등록의 `args`가 일상 폴더의 `src/beyond/codex_host.py`를 가리키는지 확인한다. 이전 진입점을 쓰는 경우 [기존 설치 전환](#기존-설치-전환)을 먼저 적용한다.
같은 일상 폴더의 자동 생성 등록은 설치 명령이 현재 주소로 갱신한다. 이전 키 `[mcp_servers.almond_cos]`는 `rhino`로 옮기고 생성된 `rhino`와 중복되면 제거한다. 변경 전에 원본 설정을 `config.toml.almond-backup-*`에 백업한다.
설정을 직접 수정했거나 두 항목의 설정이 충돌하면 설치 명령은 변경하지 않고 확인할 항목을 표시한다. 두 항목과 각 `.env`를 비교하고 유지할 직접 연결 설정을 `rhino`에 모은 다음 퇴역 항목과 그 `.env`를 제거한다. 같은 이름을 쓰는 다른 서버는 항목과 하위 테이블의 이름을 바꿔 보존한다.
기존 모델·reasoning·다른 MCP·승인 설정은 유지한다. 실행 중인 클라이언트는 MCP를 다시 로드하거나 재시작한다. `codex mcp get rhino --json`으로 등록 경로를 확인할 수 있지만, 이 명령 자체는 MCP 연결 검증이 아니다.

Codex 직접 연결의 MCP 서버 이름은 `beyond`이며 Rhino 측 플러그인은 `AlmondRhino`다.
Codex의 기존 등록 키 `rhino`와 클라이언트가 붙이는 namespace는 별도로 유지한다.
`external_host.py`의 서버 소개가 초기화 응답의 서버 설명과 안내에 전달된다.

설정 후 **실제로 사용할 Codex 대화에서 등록된 `rhino` MCP의 `connect_01-list_up` tool를 직접 호출**해 확인한다. 터미널에서 별도 MCP 클라이언트를 실행한 결과는 서버 검사일 뿐, 그 대화에 도구가 전달된 증거가 아니다. 도구를 상속하지 않는 위임 실행 환경은 일반 로컬 Codex 대화와 구분한다.

다른 로컬 클라이언트는 다음 JSON의 `mcpServers.rhino`를 등록한다.
도구 호출 제한은 클라이언트 설정에서 **600초**로 지정한다. JSON에는 클라이언트마다 다른 timeout 키를 넣지 않는다. 경로와 필요한 라이브러리 환경 변수만 출력한다.

```powershell
& ./src/engine/.venv/Scripts/python.exe -B src/beyond/client_config.py --format json
```

Codex용 생성 설정은 `[mcp_servers.rhino]`의 `tool_timeout_sec = 240`, 시작 제한 120초, Python/host의 절대 경로, UTF-8과 라이브러리 환경 변수를 포함한다. 실제 등록 대기는 `codex mcp get rhino --json`의 `tool_timeout_sec`로 확인한다. 현행 진입점을 가리키고 그 밖의 설정이 생성값과 일치하는 600초 등록은 명시적 설치 실행으로 240초로 갱신할 수 있다. 직접 지정한 호출 제한을 바꾸려면 해당 Codex 설정에서 수정한 뒤 MCP를 다시 로드한다.
`script_01-run_project_python` tool과 `script_02-run_rhino` tool은 외부 연결에서 첫 완료 대기를 최대 60초로 제한한다. 더 짧은 timeout_seconds는 그대로 사용한다. 실행이 계속되면 pending과 정확한 request_id를 받아 `script_03-get_execution` tool로 같은 ID를 조회한다. 실행 결과를 기다리는 동안 같은 코드를 재실행하지 않는다. 준비·응답 회수가 지연될 때도 현재 실행의 저장 근거가 확인되어야 pending을 반환하며, 근거가 없으면 결과 미확인 오류로 알린다.
[Codex 공식 MCP 명령 안내](https://learn.chatgpt.com/docs/developer-commands#codex-mcp).

도구 호출명은 `context_04-get_project_info`, `connect_03-start_session`, `inspect_03-get_document_context`처럼 `<category>_<NN>-<name>` 형식이다. 이전 이름의 별칭은 제공하지 않는다.
클라이언트가 표시하는 `mcp__rhino__...` 같은 서버 namespace는 클라이언트가 추가한다.
RhinoTerminal·전용 시작기의 CLI 설정은 전역 등록과 충돌하지 않는 `rhino_session`을 사용한다.

## 매번 사용하기

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

## 공통 도구를 수정했을 때

이 파일은 설치·사용·개발 참고 문서이며 MCP의 server description이나 tool description에 주입되지 않는다. `external_host.py`의 서버 설명은 서버 역할로 노출되고, 구현 docstring의 도구 역할 본문은 description, `Args` 항목은 각 inputSchema 필드의 description으로 분리된다. outputSchema는 `output_contracts.py`, 실행 결과의 후속 안내는 `tool_guidance.py`와 각 실행기의 상태별 응답에서 제공한다.

Codex 직접 연결에서는 `context_01-get_policy` tool, `connect_01-list_up` tool, `connect_02-session` tool, `connect_03-start_session` tool을 연결 ID 없이 호출한다. 나머지 도구는 매번 `connection_id`를 받는다. 생략하면 `connection_id가 지정되지 않았습니다` 오류로 요청이 중단된다. 연결 해제나 MCP 재시작 뒤 보관된 결과를 조회할 때는 `script_03-get_execution` tool 또는 `connect_05-close_session` tool에 원래의 `connection_id`와 `request_id`를 함께 전달한다.

Codex 직접 연결기는 공통 도구 입력에 필요한 `connection_id`를 추가한다. RhinoTerminal은 시작할 때 바인딩한 문서 전용 세션을 사용한다. 외부 연결기는 연결 관리 도구를 추가한다. 카탈로그를 따로 갱신할 필요는 없다.
Python 도구 변경 후 해당 beyond MCP를 정상 종료하고 새로 시작하면 현재 소스의 구현·목록·입력 schema를 읽는다. Terminal은 almond 세션을 정상 종료·재시작한다.
업데이트 뒤에 기존 실행을 다시 조회하려면 원래의 두 ID와 프로젝트 쪽 실행 기록이 모두 필요하다. 연결 ID를 기록하기 전에 만들어진 실행은 업데이트 전에 기존 호스트에서 필요한 결과를 파일로 저장한다.
Rhino만 재시작해도 외부 beyond MCP 프로세스가 살아 있으면 그 메모리는 바뀌지 않는다.
이미 실행 중인 프로세스의 자동 갱신이나 restart 도구는 이번 범위에 포함하지 않는다.
C#/RHP/DLL 수정은 빌드된 실행 파일을 반영한 뒤 Rhino를 정상 종료·재시작해야 한다.

## 동시 연결과 시작 지연

- 클라이언트의 Windows 실행 환경이 독립 프로세스를 허용하지 않으면 새 Rhino 시작을 모델을 열기 전에 거절한다. 이 경우 Rhino를 평소처럼 직접 열고 `almondconnect` → `connect_01-list_up` tool → `connect_02-session` tool로 연결한다. Terminal의 Off가 별도 Rhino를 닫지 않도록 실행 전에 확인하는 제한이며, 기존 Terminal의 자식 종료 규칙은 바꾸지 않는다.

- 여러 beyond stdio adapter가 같은 설치를 사용할 수 있다. 각 Rhino는 한 연결의 소유권을 유지한다. Codex는 각 호출에 지정한 연결 ID로 문서를 찾는다.
  다른 클라이언트가 사용하는 Rhino는 `in_use`로 표시한다. 그 연결을 유지하면서 `connect_03-start_session` tool으로 별도 Rhino를 열 수 있다.
- 같은 데이터 위치를 사용하는 singleton host가 살아 있으면 새 활성 연결은 차단한다. 기존 작업을 정상 마친 뒤 해당 beyond MCP를 재시작해 새 Python 소스를 로드한다. RHP 안내 문구는 일상 업데이트 후 새 Rhino에서 반영된다. 잠금 파일을 삭제하지 않는다.
- Rhino 시작 확인이 늦으면 그 창의 알림과 등록 상태를 확인한다. **같은 `request_id`**로 다시 호출하면 같은 프로세스를 재조회한다. 새 ID는 새 Rhino를 여는 별도 요청이다. attach 실패나 결과 불명 오류를 새 ID로 자동 반복하지 않는다. `connect_01-list_up` tool의 `starts`에서 현재 adapter가 시작한 요청·PID·상태를 볼 수 있다.
- 새 Rhino의 시작 요청 기록은 현재 MCP adapter 수명에 한정된다. MCP 재시작 후 모델 작업을 계속하려면 `connect_01-list_up` tool로 남은 Rhino를 확인하고 연결한다. 이전 시작 요청을 자동 재실행하지 않는다.
- 공유 DB 및 같은 연결의 요청 직렬화 잠금 대기는 최대 **10초**다. 대기 초과 호출은 작업을 실행하지 않으며, 기존 실행 중인 작업과 소유권을 유지한다. 실제 모델링 실행시간 제한과 연결 종료 시 native 완료 대기는 별도다. 대기 초과 뒤 수정을 자동 반복하지 않는다.
- Windows 사용자 세션의 named pipe를 사용한다. 이 진입점은 stdio만 지원하며 원격 URL, SSE/HTTP 서버를 제공하지 않는다.
- timeout은 rollback이 아니다. 결과 불명인 수정은 자동 반복하지 않는다.

## 기존 설치 전환

일상 폴더 `C:\TOOL\Rhino\mcp\almond-mcp`의 직접 연결 주소와 복구 기록을 새 위치로 옮기는 배포에 한 번 적용한다.

1. 현재 사용하는 설정에서 `[mcp_servers.rhino]`와 이전 등록 `[mcp_servers.almond_cos]`의 `args`를 확인한다. 다른 stdio 클라이언트는 연결에 쓰는 항목의 `args`를 확인한다. 주소가 이미 현행이어도 기록은 이전 위치에 있을 수 있다. 업데이트 전에 일상 폴더의 `src/*/data/` 아래에서 `execution-locators`와 `session-closes`를 각각 찾아 어느 위치에 기록이 있는지 확인한다. 데이터 위치를 따로 지정한 설치는 그 경로도 확인한다.
2. 새 작업을 시작하지 않고 진행 중인 실행·저장·종료의 결과를 기존 클라이언트에서 확인한다. **연결을 해제하기 전에** 기존 클라이언트에서 보관할 실행의 `request_id`를 지정해 `script_03-get_execution` tool로 결과를 조회한다. 결과가 여러 페이지면 끝까지 조회하고, 필요한 결과 본문을 연결별 임시 폴더 밖에 JSON 파일로 저장해 열어 본다. 전환 뒤 재조회할 기록의 `connection_id`와 `request_id`도 보관한다. 현재 연결을 정상 해제하고 MCP 클라이언트를 종료한다. 해당 host·worker·종료 guard가 끝났는지 확인한 뒤 Rhino를 정상 종료한다. 완료가 불명확하거나 프로세스가 남아 있으면 기록 이동과 pull을 보류한다.
3. 전환 커밋을 받을 일상 브랜치에서 `git pull --ff-only`를 실행해 `src/beyond/codex_host.py`가 생겼는지 확인한다. 목적지는 각각 `src/beyond/data/execution-locators`와 `src/beyond/data/session-closes`다. 이전 기본 위치에 기록이 있는 종류만 옮긴다. 원본과 목적지의 절대 경로가 일상 폴더 안에 있는지 확인하고, 양쪽에 기록이 있으면 먼저 요청별 내용을 대조해 충돌을 해결한다. 이동 전후에 상대경로별 파일 수와 해시를 확인한다. 호스트 광고·잠금 등 다른 데이터는 기존 위치에 두고, 별도로 지정한 데이터 위치는 그대로 사용한다.
4. Codex의 자동 생성 등록은 [설치 명령](#한-번-설정하기)으로 전환한다. 직접 관리하는 등록은 `args`의 host 스크립트 인수를 일상 폴더의 `src/beyond/codex_host.py` 절대 경로로 바꾸고 Python·나머지 인수·작업 폴더·호출 제한·환경 변수와 다른 설정을 보존한다. Codex에서는 `codex mcp get rhino --json`으로 주소와 유지할 설정을 확인한다.
5. Rhino를 시작하기 전에 `./src/rhp/tools/install_runtime.ps1 -VerifyOnly`로 RHP 경로, 현행 명령값, AlmondRhino의 폐기 명령 캐시 두 항목의 잔존 여부를 검사한다. 갱신 또는 제거가 필요하면 Rhino를 닫은 상태에서 `./src/rhp/tools/install_runtime.ps1`을 실행하고 다시 확인한다. 설치 명령은 레지스트리를 백업한 뒤 지정된 폐기 값만 제거하며 다른 명령값을 보존한다.
6. 일상 클라이언트를 다시 로드한다. `execution-locators`에는 실행 기록을 찾는 정보만 있다. 프로젝트에 원본 실행 기록이 남아 있으면 원래의 `connection_id`와 `request_id`로 `script_03-get_execution` tool에서 결과를 다시 조회할 수 있다. 같은 프로젝트에서 새 연결을 시작하면 이전 실행 기록이 정리될 수 있다. 재조회에 실패하면 3단계의 이동 결과를 확인하고, 원본 실행 기록이 이미 정리됐다면 2단계에서 저장한 파일을 연다. 종료 요청은 옮긴 `session-closes` 아래의 `request.json`에서 원래의 요청 ID·연결 ID와 종료 상태를 확인한다. Rhino에서 `almondconnect`로 문서를 표시하고, 실제 사용할 대화의 `connect_01-list_up` tool에서 그 문서가 보이는지 확인한다. 오프라인 검증은 [실행 기록 이전 테스트](tests/test_execution_recovery_identity.py)와 [세션 종료 테스트](tests/test_session_close.py)를 따른다.

## 일반 업데이트

외부 연결과 Rhino를 정상 종료하고 일상 폴더에서 `git pull --ff-only`를 실행한다. Rhino를 시작하고 beyond 클라이언트를 다시 로드한 뒤 해당 문서에 연결한다.
