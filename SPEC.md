# Almond 공통 구조

이 문서는 모듈 사이의 공통 경계와 문서의 진입점만 유지한다.
기능·검사·내부 구조의 현재 계약은 해당 모듈 문서에서 유지한다. 저장소 작업 지침은 [루트 AGENTS.md](AGENTS.md) 한 곳에서 관리한다.

| 모듈 | 책임 | 상세 계약 |
|---|---|---|
| MCP | 모델링 도구·계산·자산 API, CLI와 Python 실행기 | [SPEC](src/mcp/SPEC.md) |
| 외부 연결기·AlmondRhino | beyond 진입점, 외부 host/worker와 AlmondRhino 플러그인 | [SPEC](src/beyond/SPEC.md) |
| RHP | Rhino Bridge·패널·Terminal과 공용 native Engine | [SPEC](src/rhp/SPEC.md) |
| 호환 진입점 | 기존 시작 버튼과 Python 환경 위치 보존 | [설명](src/engine/README.md) |

## 공통 경계

- 외부 연결기는 MCP runtime의 확장 훅과 공용 native Engine을 사용한다. MCP는 외부 연결기 구현을 import하지 않고 native Engine은 개별 호스트를 참조하지 않는다.
- Bridge는 MCP 소유의 C# 모델링·조회 코드와 재료 정책을 컴파일한다. Python 패키지는 RHP 소유의 공용 패널 웹 원본을 포함한다. 공유 원본을 복제하지 않는다.
- 모델 폴더의 `.almond/scene.sqlite3`를 공유한다. Plan 산출물은 프로젝트 `.almond/produced/YYMMDD_name`, 연결별 임시자료는 `.almond/tmp/python/<token>/<operation>`에 둔다. 연결별 token·session·call과 프로세스 identity를 구분하며 잠금·lease·native 완료 확인을 유지한다.
- 객체 identity는 정규화한 모델 경로와 Rhino GUID의 조합이다. timeout은 rollback이나 자동 재실행 허가가 아니다.
- 기존 사용자 변경·모델·DB·라이브러리, 공개 tool schema, plugin identity와 Undo/Redo 계약을 보존한다.
- 모듈 전용 테스트와 검증 기록은 모듈이 소유한다. 루트 `tests/`는 여러 모듈의 계약을 확인한다. 문서에 연결된 RhinoTerminal의 공개 도구 선언은 [임시 모델을 사용하는 stdio 검사](tests/README.md#실행기별-확인-범위)로 검증한다. 워크트리는 실행 중 Rhino와 모델 DB를 자동 격리하지 않는다.

## 소유권과 의존 방향

| 소유 모듈 | 구현·검사 위치 | 허용하는 의존 관계 |
|---|---|---|
| MCP | `src/mcp`의 공용 코드·`features`, `runtime`, `release_validation`, `tests` | Python 라이브러리와 Rhino의 기존 전송 계약. 외부 연결기 구현을 import하지 않는다. |
| 외부 연결기 | `src/beyond`의 host/worker·catalog, `rhp`, `tests` | MCP 실행기의 검증·구성 훅, native Engine. MCP 내부 정책을 외부 연결기에 복제하지 않는다. |
| Native Engine | `src/rhp/Engine`, 그 안의 `tests` | Rhino·플랫폼 API. 개별 호스트 프로젝트를 참조하지 않는다. |
| Bridge | `src/rhp/RhinoAlmondBridge` 및 자체 `tests` | Engine, MCP 소유 C# 모델링·조회 코드와 재료 정책, 아래 패널·Terminal 소스. |
| RhinoTerminal | `src/rhp/RhinoTerminal/src`, `tests` | Engine과 MCP 실행기. 기존처럼 Bridge RHP에 컴파일된다. |
| 패널·구조해석 UI | `src/rhp/Asset_Panel`, `Structural_Analysis` | 기존 Bridge 계약과 MCP 소유 기능 코드. 패널 웹 원본은 Python wheel과 RHP archive가 함께 사용한다. |
| 통합 | 루트 `tests`, `src/rhp/tools`의 설치·배포 검사 | 모듈 간 schema·패키징·native 실행 파일의 일치 여부를 검사한다. |

MCP 도구의 native 구현은 `src/mcp/features/<기능>/native`에 두고 Bridge에 컴파일한다.
연결·실행 호스트와 패널 UI는 RHP에 둔다. 패널 웹 자원은 Python 패키지에 포함된다. 이 공유 자원을 바꾸면 소비자 검사·빌드도 필요하다. 소유권을 나눈다고 모든 기능을 독립 assembly나 독립 배포로 바꾸지는 않는다.

## Python 시작과 실행의 책임

| 경계 | 소유자 | 전달하는 것 |
|---|---|---|
| 도구 선언 | MCP `tool_declarations` | [공개 선언 원본](TOOL-DECLARATIONS-CURRENT.md)에서 생성한 [스키마 데이터](src/mcp/public_contract_data.json)를 문서용 런타임과 beyond가 함께 사용한다. |
| 서버 시작 | MCP `startup` | 명시적 DB·라이브러리 경로와 전송 함수를 받아 한 `ServerApplication`을 만든다. import만으로 저장소를 열지 않는다. |
| 기능 실행 | MCP `features` | 서버별 `FeatureContext`의 의존성을 사용한다. 기능별 SQL·모델링·계산 규칙을 유지한다. |
| 저장소 수명 | MCP `store_database` | SQLite 연결·트랜잭션·초기 스키마·migration 순서를 관리한다. `AlmondStore`는 기능별 저장소의 기존 인터페이스를 제공한다. |
| 작업 경로·전이 | MCP `runtime/workspace`와 planning 저장소 | 파일 이동 intent와 같은 DB transaction의 Loop 전이 receipt로 미완료 전이를 복구한다. 작업 경로를 사용하는 호출은 공유 gate 아래 선택한 snapshot을 재사용한다. |
| 외부 명령 접수 | MCP `runtime/owned_process` | 자식의 정확한 프로세스 identity를 기록하고 부모 승인 후 명령을 시작한다. Python과 Engine이 같은 소유권 근거를 읽으며 프로세스 종료와 native 완료를 별도로 확인한다. |
| 외부 연결 수명 | 외부 연결기 `external_host` | 연결 탐색·선택·attach·detach와 worker 수명. 선택된 연결을 실행 담당자에 전달한다. |
| 외부 호출 수명 | 외부 연결기 `execution_invocation` | 호출 접수·전송 여부·예약·대기·취소와 결과 회수를 관리한다. 실제 완료 판정은 공통 runtime의 journal·receipt·프로세스 근거에 따른다. |
| Rhino 문서 실행 | MCP `runtime`와 `bridge_transport`, 공용 Engine | endpoint 전송과 binding·문서·UI thread·native 완료의 기존 검증을 연결한다. 외부 연결기에서 문서 실행 정책을 복제하지 않는다. |
| Native binding·변경 | Engine `NativeBinding`, `BridgeDispatchContext`, `NativeUndoRecord` | 두 호스트의 binding 발행·무효화·drain, 검증한 문서의 dispatch와 Undo 소유권을 공통화한다. PTY·worker·discovery 수명은 각 호스트가 소유한다. |
| 배포 검증 | RHP `tools/verify_runtime` | 필수 출력 목록·기록된 해시·공유 Engine 일치를 검사한다. 실제 Rhino 로드·모델링 검증은 별도다. |

새 실행 경로는 기존 진입점에서 같은 소유자를 호출한다. 교체된 전역 서버 조립·호출별 함수 교체·중복 선언 추출 구현은 별도 경로로 유지하지 않는다. 데이터 스키마·공개 도구·Rhino 플러그인 identity를 바꾸는 이전은 해당 계약의 별도 변경이다.

## 공통 안내

- [작업 원칙·설치·배포](AGENTS.md)
- [기능별 사용 문서](README.md)
- [공개 선언의 실제 stdio 스냅샷](tests/integration/tool_catalogs.md)

모듈 내부만 변경되는 작업은 이 문서를 수정할 필요가 없다. 공통 의존 방향이나 설치·저장소 계약이 실제로 바뀔 때만 함께 갱신한다.
