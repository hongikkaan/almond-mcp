# Almond 연결 경로와 호환 식별자

사용자 용어는 [GLOSSARY](../../GLOSSARY.md)를 따른다. 연결 경로는 요청이 실제로
지나가는 프로그램으로 구분한다. 대화를 Codex에서 열었다는 사실만으로 직접 연결이 되지는 않는다.

| 경로 | 시작·도구 전달 | Python 진입점 | Rhino 연결 | 종료 |
|---|---|---|---|---|
| CoS 경유 연결 | CoS 앱의 등록된 MCP; 원격 호출에는 CoS 터널 필요 | `src/cos/cos_host.py` → `external_host.py` | `list_connections` → `connect` 또는 `start_session`; 매 호출 `connection_id` | `disconnect`, 이후 CoS MCP 종료 |
| Codex 직접 연결 | 같은 Windows 사용자의 로컬 Codex에 등록한 `rhino` MCP | `src/cos/codex_host.py` → `external_host.py` | 같은 외부 연결 계약; CoS 앱·터널을 호출하지 않음 | `disconnect`, 이후 해당 Codex MCP 종료 |
| RhinoTerminal 연결 | `RhinoTerminal On` → `almond` → 문서 전용 Codex의 `rhino_session` MCP | `src/mcp/runtime/terminal_almond.ps1` → `codex.ps1` → `mcp_server.py` | 시작 시 이미 선택한 문서·슬롯·token에 묶임 | Codex `/exit`; 터미널 자체 종료는 `RhinoTerminal Off` |

외부 시작 버튼 `src/mcp/runtime/Almond 시작.cmd`도 문서 전용 Codex를 만드는
기존 관리 세션 경로다. 일반 Codex에 등록하는 `rhino` 외부 연결기와 구분한다.

## 공통 구현과 유지하는 계약

`external_host.py`는 클라이언트별 지연 시작과 연결별 worker 생명주기를 조정한다.
공유 gate·lease·native 완료 정책은 기존 runtime/Engine 계약을 사용한다. 두 외부 진입점은 MCP 서버 식별을 각각
`Almond CoS`, `Almond Codex`로 지정한다. 공통 도구 이름과 입력 schema는 같다.
CoS 등록 command와 출력 디렉터리를 보존하기 위해 파일은 `src/cos`에 유지한다.
이 디렉터리 이름이 CoS 앱 실행 의존성을 뜻하지 않는다.

`AlmondCOS.rhp`·GUID·`AlmondCOS-` pipe·`attachment="cos"`·
`ALMONDCOS_SESSION_TOKEN`·`src/cos/data`는 기존 native 전송의 호환 식별자다.
두 외부 경로가 같은 계약을 사용하며, 명칭 정리 때문에 변경하거나 복제하지 않는다.
RhinoTerminal의 Bridge 전송과 생명주기는 그대로 둔다. 다른 연결의 ID를 재사용하거나
잠금을 제거하지 않는다. timeout은 rollback이 아니다.

설계 용어는 `ontological-component`다. 기존 도구의 `get_design_component` 등 이름과
`component_id`, 저장 메타데이터·DB 키는 API 호환 식별자로 유지한다.
표현 변경을 데이터 이전이나 전체 도구 rename으로 취급하지 않는다.

## 확인 단계

1. **등록**: `client_config.py`가 출력한 command/args가 일상 폴더를 가리키는지 확인한다.
   기존 생성 설정은 백업 후 직접 진입점으로 이전한다. 사용자 수정 설정은 덮어쓰지 않는다.
2. **서버 실행**: 새 MCP 프로세스의 초기화·도구 목록을 확인한다. stdio 검사 통과는
   그 서버의 증거이며 특정 대화에 도구가 전달됐다는 증거가 아니다.
3. **대화 도구 전달**: 실제 작업할 대화에서 `rhino`의 `list_connections`를 호출한다.
   CoS namespace의 호출은 직접 연결 검증에 포함하지 않는다.
4. **실제 Rhino 작업**: 일회용 문서에 연결하여 조회·가역 편집·정상 연결 해제를 검증한다.
   진행 중인 사용자 모델로 시험하지 않는다. 생성 요청이 불명확하면 자동 재실행하지 않는다.

로컬 MCP를 전달하지 않는 원격/위임 실행 환경에서는 3단계가 막힐 수 있다.
그 경우 로컬 Windows Codex 실행 환경으로 작업을 옮기거나 플랫폼의 직접 MCP 전달이
필요하다. 이 저장소의 Python 변경이나 로컬 설정 등록만으로 원격 대화의 도구 목록을
바꿀 수 없다. CoS 터널을 통해 성공한 결과로 이 차단이 해결됐다고 보고하지 않는다.

실제 설치·사용 절차는 [외부 클라이언트 안내](../../src/cos/EXTERNAL_CLIENTS.md)를 따른다.
