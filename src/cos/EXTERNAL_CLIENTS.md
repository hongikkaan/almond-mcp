# Codex·외부 MCP 클라이언트 연결

Codex 직접 연결은 `codex_host.py`, CoS 경유 연결은 기존 `cos_host.py`를 실행한다.
두 진입점은 표준 **stdio MCP 서버**인 `external_host.py`를 공유한다. Codex 직접 연결에는
CoS 앱이나 터널이 필요하지 않다. 기존 CoS 명령·터널과 native 등록은 유지한다.
RhinoTerminal을 포함한 세 경로의 구분은 [연결 경로 안내](../mcp/runtime/CONNECTION-SPEC.md)를 따른다.

MCP 등록과 클라이언트 시작 시에는 **도구 목록을 제공하는 최소 stdio 프로세스**만 실행된다.
모델링 worker·Rhino·모델 DB 연결은 시작하지 않는다. 사용하는 대화에서 연결 또는 시작
도구를 명시적으로 호출하면 필요한 준비를 한다.

## 한 번 설정하기

일상 설치 폴더에서 실행한다. 개발 워크트리를 클라이언트나 Rhino에 등록하지 않는다.
Python 환경과 RHP 최초 설치는 [저장소 설치 안내](../../AGENTS.md)를 따른다.

```powershell
Set-Location C:\TOOL\Rhino\mcp\almond-mcp
# 미리 볼 때: 설정을 출력할 뿐 파일이나 연결을 변경하지 않는다.
& ./src/engine/.venv/Scripts/python.exe -B src/cos/client_config.py
# 실제 Codex 등록: 기존 파일 백업 후 rhino 항목을 추가/이전한다.
& ./src/engine/.venv/Scripts/python.exe -B src/cos/client_config.py --install-codex "$env:USERPROFILE/.codex/config.toml"
```

다른 `CODEX_HOME`을 쓰는 CLI라면 그 디렉터리의 `config.toml` 경로를 명시한다.
이미 동일한 `rhino` 등록이 있으면 그대로 둔다. 이 도구가 이전에 생성한 `cos_host.py` 등록은
백업 후 `codex_host.py` 직접 진입점으로 이전한다. 이전 `almond_cos` 항목도 생성 설정과
정확히 같을 때만 `rhino`로 이름을 이전하여 두 host가 중복 시작되지 않게 한다.
수정된 이전 설정이나 `rhino` 항목과 충돌하면 아무것도 변경하지 않고 중단한다.
기존 모델·reasoning·다른 MCP·승인 설정은 유지한다. 실행 중인 클라이언트는
MCP를 다시 로드하거나 재시작한다. `codex mcp get rhino --json`으로 등록 경로를
확인할 수 있지만, 이 명령 자체는 MCP 연결 검증이 아니다.

Codex 직접 연결의 MCP 서버 이름은 `beyond`, CoS 경유 연결은 `CoS`다.
CoS 앱 등록용 `cos-plugin.json`의 표시 이름도 `CoS`다. 두 경로는 `AlmondRhino` 플러그인을 사용한다.
Codex의 기존 등록 키 `rhino`와 클라이언트가 붙이는 namespace는 별도로 유지한다.
공통 소개는 `SERVER-DESCRIPTION.md`에서 수정하며, `{server_name}`을 각 경로의 이름으로 치환해 초기화 응답의 서버 설명과 첫 안내에 전달한다.

설정 후 **실제로 사용할 Codex 대화에서 등록된 `rhino` MCP의 `list_connections`를 직접
호출**해 확인한다. 터미널에서 별도 MCP 클라이언트를 실행한 결과는 서버 검사일 뿐,
그 대화에 도구가 전달된 증거가 아니다. 도구를 상속하지 않는 위임 실행 환경은 일반
로컬 Codex 대화와 구분한다. 도구가 없을 때 CoS 터널 호출로 대신 성공 처리하지 않는다.

다른 로컬 클라이언트는 다음 JSON의 `mcpServers.rhino`를 등록한다.
도구 호출 제한은 클라이언트 설정에서 **600초**로 지정한다. JSON에는 클라이언트마다
다른 timeout 키를 넣지 않는다. 경로와 필요한 라이브러리 환경 변수만 출력한다.

```powershell
& ./src/engine/.venv/Scripts/python.exe -B src/cos/client_config.py --format json
```

Codex 설정은 Python/host의 절대 경로, UTF-8, 시작 제한 120초·호출 제한 600초,
AppData·TEMP와 명시적인 라이브러리 경로 전달을 포함한다. 표준 입출력은 MCP 전용이다.
[Codex 공식 MCP 명령 안내](https://learn.chatgpt.com/docs/developer-commands#codex-mcp).

도구 자체는 `project_info`, `start_session`, `get_rhino_context`처럼 접두사가 없다.
클라이언트가 표시하는 `mcp__rhino__...` 같은 서버 namespace는 클라이언트가 추가한다.
RhinoTerminal·전용 시작기의 CLI 설정은 전역 등록과 충돌하지 않는 `rhino_session`을 사용한다.
기존 CoS의 표시 이름·터널 namespace는 해당 앱에서 관리하며 이 도구명 변경과 구분한다.

## 매번 사용하기

저장된 모델을 새 Rhino에서 시작하려면:

1. 일반 Codex 대화에서 "`C:\작업\모델.3dm`을 Almond의 새 세션으로 열어 줘"라고 요청한다.
2. Codex가 `start_session`에 절대 `model_path`와 새 `request_id`를 전달한다.
   새 Rhino를 열고 `_almondconnect`를 자동 실행한 뒤 해당 프로세스에만 연결한다. CoS 앱이나
   별도 Codex 창을 열 필요는 없다. 원본 모델을 저장하거나 기존 Rhino를 종료하지 않는다.
3. 프로젝트·문서 정보가 필요하면 반환된 `connection_id`로 `project_info`의 필요한
   sections를 조회한다. 기본 document 항목이 live 확인을 포함한다. 자료를 작성할 때는
   `set_working_plan`으로 Plan의 `artifact_dir`를 선택한다.
4. 끝나면 `disconnect`를 호출한다. Rhino 창은 남으며 저장·종료는 Rhino에서 한다.

새 Rhino는 디스크에 저장된 파일을 연다. 다른 Rhino 창의 저장되지 않은 변경을 복제하지 않는다.
다른 Codex 대화나 CoS에서도 별도 Rhino 세션을 시작할 수 있다. 슬롯 A–J는 기존 Terminal·
CoS 연결과 함께 사용하며 사용 가능한 자리가 있어야 연결된다.

이미 열린 일반 Rhino에 연결하려면:

1. 해당 Rhino 8에서 `.3dm`을 열고 저장한 뒤 `almondconnect`를 실행한다.
2. 등록된 Codex 앱이나 외부 Codex CLI에서 "Almond 연결 목록을 확인하고 이 문서에
   연결해 줘"라고 요청한다. 클라이언트가 `list_connections`를 호출한다.
3. 목록의 정확한 `host_id`와 `model_path`로 `connect`를 호출한다.
   반환된 `connection_id`를 이후 모든 호출에 사용한다.
4. 필요할 때 `project_info`에서 프로젝트·live 문서를 함께 조회한다. 같은 확인을 위해
   `get_rhino_context`를 반복 호출하지 않는다. 자료 작성 전 `set_working_plan`으로
   폴더를 선택하고, 모델링에는 [Rhino 모델링 지침](../mcp/BASIC-INSTRUCTIONS.md)을 따른다.
5. 끝나면 `disconnect`로 해당 연결을 해제한다. 문서 변경 후에는 재연결한다.

Rhino에서 직접 해제하려면 `almonddisconnect`를 사용한다. 처리 중인 작업이나 worker의
종료가 아직 확인되지 않으면 완료 안내를 기다린다. Rhino와 모델은 저장·종료하지 않는다.
기존 `AlmondCOS`·`AlmondCOSDisconnect`와 `AlmondMCPStart`·`AlmondMCPStop`·
`AlmondMCPStatus` 명령은 제거했다. PackageManager에서 다른 패키지를 삭제할 필요는 없다.

이 명령 이름 변경을 처음 적용할 때는 Rhino를 닫은 상태에서 일상 폴더의
`src/rhp/tools/install_runtime.ps1`을 한 번 실행한다. 파일만 갱신하면 Rhino의
지연 로드용 `CommandList`가 옛 이름을 계속 기억할 수 있다. 설치 스크립트는
기존 등록을 백업하고 새 연결 명령 두 개와 제거된 명령 목록을 맞춘다.
`-VerifyOnly`는 경로가 올바르더라도 명령 캐시가 옛 상태이면 실패한다.

`almondconnect`는 Rhino를 발견 가능하게 만드는 명령이다. Codex 프로그램을 자동 실행하거나
새 채팅에 자동 연결하지는 않는다. 새 시작 도구는 이 명령을 새 Rhino에 자동 전달한다.
Rhino가 없으면 MCP 초기화와 도구 목록은 정상이고
연결 가능한 문서 목록만 비어 있다. 기존 `Almond 시작.cmd`·`RhinoTerminal → almond`로
관리되는 Rhino는 기존 전용 CLI를 사용하거나, 연결을 정상 종료한 뒤 일반 Rhino로 연다.

## 공통 도구를 수정했을 때

RhinoTerminal·Codex·CoS는 같은 공통 도구 소스를 사용한다. 외부 연결기는 연결 관리 도구를
추가하고 공통 도구 입력에 `connection_id`를 붙인다. 카탈로그를 따로 갱신할 필요는 없다.
Python 도구 변경 후 해당 Codex/CoS MCP를 정상 종료하고 새로 시작하면 현재 소스의
구현·목록·입력 schema를 읽는다. Terminal은 almond 세션을 정상 종료·재시작한다.
Rhino만 재시작해도 외부 Codex/CoS MCP 프로세스가 살아 있으면 그 메모리는 바뀌지 않는다.
이미 실행 중인 프로세스의 자동 갱신이나 restart 도구는 이번 범위에 포함하지 않는다.
C#/RHP/DLL 수정은 빌드된 실행 파일을 반영한 뒤 Rhino를 정상 종료·재시작해야 한다.

## 동시 연결과 시작 지연

- 클라이언트의 Windows 실행 환경이 독립 프로세스를 허용하지 않으면 새 Rhino 시작을
  모델을 열기 전에 거절한다. 이 경우 Rhino를 평소처럼 직접 열고 `almondconnect` →
  `list_connections` → `connect`로 연결한다. Terminal의 Off가 별도 Rhino를 닫지 않도록
  실행 전에 확인하는 제한이며, 기존 Terminal의 자식 종료 규칙은 바꾸지 않는다.

- 여러 CoS·Codex stdio adapter가 같은 설치를 사용할 수 있다. 각 Rhino는 한 연결의 소유권을
  유지한다. 서로 다른 클라이언트에 외부 연결기의 `connection_id`를 복사해 쓸 수 없다.
  다른 클라이언트가 사용하는 Rhino는 `in_use`로 표시한다. 그 연결을 유지하면서
  `start_session`으로 별도 Rhino를 열 수 있다.
- 업데이트 전에 시작한 singleton host가 살아 있으면 새 활성 연결은 차단한다. 기존 작업을
  정상 마친 뒤 해당 CoS/Codex MCP를 재시작해 새 Python 소스를 로드한다. RHP 안내 문구는
  일상 업데이트 후 새 Rhino에서 반영된다. 잠금 파일을 삭제하지 않는다.
- Rhino 시작 확인이 늦으면 그 창의 알림과 등록 상태를 확인한다. **같은 `request_id`**로 다시
  호출하면 같은 프로세스를 재조회한다. 새 ID는 새 Rhino를 여는 별도 요청이다. attach 실패나
  결과 불명 오류를 새 ID로 자동 반복하지 않는다. `list_connections`의 `starts`에서 현재
  adapter가 시작한 요청·PID·상태를 볼 수 있다.
- request ID 기록은 현재 MCP adapter 수명에 한정된다. MCP를 재시작했다면 먼저
  `list_connections`로 남은 Rhino를 확인하고 연결한다. 이전 ID를 자동 재실행하지 않는다.
- 공유 DB 및 같은 연결의 요청 직렬화 잠금 대기는 최대 **10초**다. 대기 초과 호출은
  작업을 실행하지 않으며, 기존 실행 중인 작업과 소유권을 유지한다. 실제 모델링 실행시간
  제한과 연결 종료 시 native 완료 대기는 별도다. 대기 초과 뒤 수정을 자동 반복하지 않는다.
- Windows 사용자 세션의 named pipe를 사용한다. 이 진입점은 stdio만 지원하며 원격 URL,
  SSE/HTTP 서버를 제공하지 않는다. 기존 CoS가 제공하는 터널 경로는 변경하지 않는다.
- timeout은 rollback이 아니다. 결과 불명인 수정은 자동 반복하지 않는다.

## AlmondRhino 이름 이전

기존 AlmondCOS 플러그인은 같은 GUID를 유지한 AlmondRhino로 이름과 출력 위치를 이전했다.
Rhino가 종료된 상태에서 `src/rhp/tools/install_runtime.ps1`을 실행하면 이전 등록을 백업하고
새 `src/rhp/AlmondRhino/plugin-runtime/AlmondRhino.rhp` 경로와 표시 이름을 등록한다.
Python host/worker도 정상 종료 후 새로 시작해야 새 제어 pipe와 환경 변수 이름을 사용한다.
등록 확인은 `-VerifyOnly`로 수행하며, 실제 Rhino 로드 확인과는 별개다.
