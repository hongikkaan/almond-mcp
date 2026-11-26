# Almond 연결 경로와 호환 식별자

사용자 용어는 [GLOSSARY](../../../GLOSSARY.md)를 따른다. 연결 경로는 요청이 실제로 지나가는 프로그램으로 구분한다. 대화를 Codex에서 열었다는 사실만으로 직접 연결이 되지는 않는다.

| 사용 경로 | MCP 서버 이름 | 시작·진입점 | Rhino 쪽 플러그인 | 연결 방식 |
|---|---|---|---|---|
| RhinoTerminal | `Almond` | `RhinoTerminal On` → `almond` → `terminal_almond.ps1` → `codex.ps1` → `mcp_server.py` | `RhinoAlmondBridge` | 시작할 때 문서·슬롯·token이 정해짐. 문서 전용 `rhino_session` MCP 사용 |
| 외부 Codex 직접 연결 | `beyond` | 저장된 `rhino` 등록 또는 Codex CLI 실행별 설정 → `src/beyond/codex_host.py` | `AlmondRhino` | `connect_02-session` tool 또는 `connect_03-start_session` tool에서 받은 `connection_id`를 대화가 보관하고 문서 대상 호출마다 전달 |

RhinoTerminal은 Codex `/exit`로 세션을 종료하고 `RhinoTerminal Off`로 터미널을 닫는다.
beyond는 `connect_04-disconnect` tool로 연결을 해제하며 Rhino 문서를 저장하거나 닫지 않는다.
beyond에서 Rhino까지 종료할 때는 연결을 유지한 채 `connect_05-close_session` tool에 종료 시도별 `request_id`와 원래의 `connection_id`를 전달한다. 결과 재조회에도 두 값이 필요하다. 이 도구는 변경·읽기 전용·저장 경로·프로세스와 문서 identity를 확인하고 공식 RhinoCode `_Save`로 기존 파일명에 저장한 뒤 정확한 완료를 기다린다. 동일 문서의 `modified=false` 확인 후 별도 UI 스레드 guard가 문서·worker·binding과 변경 여부를 다시 확인하고 `_-Exit`로 정상 종료한다. 저장 실패·완료 불명확·문서 변경 시 Exit를 보내지 않는다. 저장 여부 선택이나 자동 No 응답, 강제 종료는 없다.

동일 `request_id` 재호출은 보관된 결과 조회이며 저장·종료를 재실행하지 않는다. 요청 ID별 OS 잠금과 대상별 보관 기록은 여러 beyond host 사이의 중복 실행을 막는다. 종료 지연 중에는 기존 worker·native binding·host lease를 유지하며, 정확한 Rhino와 CLI 프로세스 종료를 확인한 뒤 worker를 정상 종료하고 소유권을 해제한다. 호스트 재시작 후에는 기록과 프로세스·lease 근거로 결과만 확인한다. 확실한 미전송은 거부로 정리하고, 불확실한 전송은 완료 근거가 생길 때까지 보관한다. Save의 늦은 완료가 확인돼도 뒤늦게 Exit를 자동 전송하지 않는다.

`connect_04-disconnect` tool 성공 응답의 `pid`·`model_path`는 해제한 대상을 식별하며 후속 안내는 해당 문서에 다시 연결한 뒤 `connect_05-close_session` tool을 쓰도록 한다. 해제가 미확정이면 종료 안내를 성공 응답으로 제공하지 않는다. RhinoTerminal의 `/exit`·`Off`는 기존 문서 전용 세션/터미널 종료 의미를 유지한다.

별도 창의 `src/mcp/runtime/Almond 시작.cmd`도 RhinoTerminal과 같은 문서 전용 세션 방식이다. [문서 전용 Codex 실행](../SPEC.md#문서-전용-codex-실행) · [Dot 클라이언트](../../beyond/SPEC.md#dot-클라이언트-사용)

## 공통 구현과 유지하는 계약

`codex_host.py`는 클라이언트별 지연 시작과 연결별 worker 생명주기를 조정한다.
RhinoTerminal과 beyond의 worker는 `mcp_server.py`에서 `document_session.py`로 진입한다. 문서 세션은 binding과 lease를 확인하고 공통 MCP 서버에 `Workspace`, 문서 전용 도구, 외부 구성 훅을 연결한다. worker가 종료 기록을 남긴 뒤 lease를 반납한다.
공유 gate·lease·native 완료 정책은 기존 runtime/Engine 계약을 사용한다. beyond는 정책 조회·연결 목록·연결·시작을 제외한 모든 도구의 최상위 입력에 `connection_id`를 요구한다. 생략 시 `connection_id가 지정되지 않았습니다`를 반환하고 중단한다. host가 이 인자를 소비하고 worker에는 공통 스키마의 인자만 전달한다.

Rhino 플러그인의 assembly·namespace·출력 폴더는 `AlmondRhino`, 클래스는 `RhinoPlugin`·`RhinoHost`다.
플러그인 GUID는 `39eb74f6-8283-4e43-bf26-f0106d891b75`다.
제어 pipe 접두사는 `AlmondRhino-`, worker 환경 변수 접두사는 `ALMONDRHINO_`다.
외부 세션의 바인딩에는 `attachment="beyond"`를 쓰고 Rhino 호스트 발견 정보는 `src/beyond/data/hosts`에 둔다. host 잠금은 같은 `src/beyond/data` 아래에 둔다.
실행 조회·종료 기록의 기본 위치는 각각 `src/beyond/data/execution-locators`와 `src/beyond/data/session-closes`다. 데이터 위치를 별도로 지정하면 해당 디렉터리의 두 하위 폴더를 사용한다.
RhinoTerminal의 Bridge 전송과 생명주기는 그대로 둔다. 다른 연결의 ID를 재사용하거나 잠금을 제거하지 않는다. timeout은 rollback이 아니다.

도면 레시피는 Python worker에서 읽는다. 체크아웃에서는 런처가 기존 AppData 기본 위치를 전달하거나 경로를 생략하면 [저장소 레시피](../../../asset/drawing/DrawingRecipes/README.md)를 사용한다. 별도로 지정한 레시피 폴더는 우선한다.
그 밖의 일상 worker와 Bridge의 라이브러리 기본 위치는 `%LOCALAPPDATA%\Almond\<라이브러리명>`이다.
`RHINO_MCP_*_DIR`에 명시한 경로가 우선하며, RHP가 있는 저장소의 `asset/` 존재 여부로 일상 라이브러리를 바꾸지 않는다. 오프라인 개발 셸은 저장소 자산을 명시적으로 선택한다.
Bridge는 시작할 때 이 경로를 캐시하므로 worker와 실제 캐시가 다르면 native 요청을 거부한다.
기존 라이브러리를 옮기거나 캐시를 호출 중에 바꾸지 않고, 같은 설정으로 시작한 두 쪽을 비교한다.

Windows 패키지 앱의 AppData 가상화가 감지되면 `desktop_runtime.py`가 허용된 Almond 진입점만 일반 Windows 프로세스에서 다시 시작한다. 외부 직접 연결의 허용 진입점은 `src/beyond/codex_host.py`다. lease·DB·라이브러리 초기화 전에 전환하고 인증된 loopback 연결로 stdio·환경·종료 코드를 전달한다. 실제 worker의 PID와 기존 EOF 종료 절차를 유지하며, 제한된 토큰·AppContainer에서는 전환을 거부한다. stdin을 읽지 않는 라이브러리 HTTP 서버에는 중계 연결 종료를 별도 Windows 이벤트로 전달해 포트를 해제한다. 기존 AppData와 명시적 경로는 이동·병합하지 않고, 전환 실패를 빈 라이브러리로 처리하지 않는다.

설계 용어는 `Ontological_Holon`이다. 공개 도구는 `scene_05-get_holon` tool 등과 `holon_id`·`holon_ids` 계열 키를 사용하며, DB 등록 테이블은 `ontological_holons`다. 기존 ID 값과 Rhino 내부 메타데이터 형식은 유지하고 공개 응답에서 키를 변환한다. 기존 클라이언트는 새 스키마로 다시 연결해야 한다.
표현 변경을 데이터 이전이나 전체 도구 rename으로 취급하지 않는다.

## 확인 단계

1. **설정 확인**. Codex에서 `codex mcp get rhino --json`으로 적용된 `command`와 `args`를 읽는다. [실행별 설정](../../beyond/SPEC.md#한-번-설정하기)을 쓰면 같은 `-c` 인자를 검사에도 전달한다. Python은 일상 폴더의 `src/engine/.venv/Scripts/python.exe`, 호스트는 같은 폴더의 `src/beyond/codex_host.py`여야 한다. 이전 주소나 퇴역 등록이 남아 있으면 [기존 설치 전환](../../beyond/SPEC.md#기존-설치-전환)을 따른다.
2. **서버 실행**: 새 MCP 프로세스의 초기화·도구 목록을 확인한다. stdio 검사 통과는 그 서버의 증거이며 특정 대화에 도구가 전달됐다는 증거가 아니다.
3. **대화 도구 전달**: 실제 작업할 대화에서 `rhino`의 `connect_01-list_up` tool를 호출한다.
4. **실제 Rhino 작업**: 사용자가 연결한 작업 문서의 기존 형상·뷰·Layout에서 기능을 검증한다.
   기본 개발 검증은 Rhino 없이 fixture·가짜 registry·stdio 계약 검사로 수행한다. 실제 로드는 따로 보고한다.

로컬 MCP를 전달하지 않는 원격/위임 실행 환경에서는 3단계가 막힐 수 있다.
그 경우 로컬 Windows Codex 실행 환경으로 작업을 옮기거나 플랫폼의 직접 MCP 전달이 필요하다. 이 저장소의 Python 변경이나 로컬 설정 등록만으로 원격 대화의 도구 목록을 바꿀 수 없다.

실제 설치·사용 절차는 [외부 클라이언트 안내](../../beyond/SPEC.md#codex와-외부-mcp-클라이언트-사용)를 따른다.
