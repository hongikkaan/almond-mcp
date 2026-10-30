# Rhino native 계약

이 모듈은 Rhino 내부 실행·관찰·패널·터미널과 공용 native 연결을 소유한다.
[작업 지침](AGENTS.md)과 [공통 경계](../../SPEC.md)를 함께 따른다.

## 구성과 빌드

| 위치 | 책임 |
|---|---|
| `RhinoAlmondBridge/` | Rhino 패널 명령, native 요청 handler, C# 실행·Undo, 고정 관찰과 plugin entry |
| `Engine/` | 별도 `Almond.Engine.dll`; 연결 identity·공유 lease·native 완료 |
| `RhinoTerminal/` | 터미널·MCP 실행기 연결. 별도 plugin entry 없이 Bridge에 컴파일 |
| `Structural_Analysis/` | 구조해석·결과 패널과 solver 연결; Bridge에 컴파일 |
| `Asset_Panel/` | 라이브러리·배치·archive와 공용 웹 원본; Bridge에 컴파일 |
| `tools/` | 빌드·패키징·설치·실행 파일 검증 도구 |
| `AlmondRhino/` | AlmondRhino 출력 폴더. 구현은 [외부 연결기 모듈](../cos/SPEC.md) 소유 |

Bridge의 유일한 plugin entry가 패널 등록과 Terminal 종료를 담당한다. Engine과
AlmondRhino는 별도 assembly다. Engine은 호스트 프로젝트를 참조하지 않는다. Bridge는
MCP 소유 C# 모델링 코드와 재료 정책을 링크하므로 해당 변경도 빌드 입력이다.

## 실행·관찰

Bridge 로드는 패널과 기존 native handler/helper만 준비한다. 구형 5000번 포트 listener와
`AlmondMCPStart`·`AlmondMCPStop`·`AlmondMCPStatus` 명령은 제거했으며 별칭을 등록하지 않는다.
모델 작업용 transport는 문서·token에 바인딩된 Engine 세션에서만 시작한다. Engine이 확인하는
Bridge의 `_server` 필드·`HandleRequest`와 helper 계약은 유지한다.

문서 identity, UI thread, 요청·완료 envelope, 공유 저장소 lease와 Undo/Redo 계약을
보존한다. 고정 관찰은 geometry·layer·selection·camera·Undo를 바꾸지 않는다.
수정 실행의 반환 오류와 실제 rollback은 구분한다. 입력·출력 한계와 viewport·probe
계약은 [관측 문서](../mcp/rhino/OBSERVATION-SPEC.md)를 따른다.

Terminal과 AlmondRhino는 고정 RHP 출력 위치에서 `../mcp/runtime`에 해당하는 실제 경로를
계산해 사용한다. 개발 워크트리로 일상 Rhino 등록을 변경하지 않는다.

Terminal의 shell·AlmondHost 수명은 패널과 독립적이다. Rhino 시작이나 패널 복원은
실행을 시작하지 않는다. `RhinoTerminal`의 `On`/`Off`는 표시 상태와 무관하게
실행을 제어하고 `PanelToggle`은 표시만 바꾼다. 패널 없는 실행도 출력 소비와
문서 확인을 유지하며, 최근 128 Ki 문자 출력을 보관해 새 패널에 재생한다.
패널 오른쪽 위 almond/resume 버튼은 기존 터미널 입력 경로로 명령과 Enter를 보낸다.
자세한 절차는 [Terminal 사용법](RhinoTerminal/사용법.txt)을 따른다.

## 도면 스타일

`DrawingStyleManager`는 요청한 선종류의 이름까지 확인한다. 없는 이름에 대한
Rhino의 Continuous 반환을 해당 선종류가 존재한다는 근거로 사용하지 않는다.
레시피의 선택적 `linetype_segments`는 유한한 양수 길이와 명시적인 실선/공백으로
정의한다. 요청 내 상충하는 정의와 기존 동일명 패턴 충돌은 Undo·레이어 변경 전에
거절한다. 일치하는 패턴은 재사용하고, 명시 정의가 없는 기존 레시피는 기존 동작을 유지한다.

## 공유 자원과 출력

웹 원본은 `Asset_Panel/web`, wheel 경로는 `almond_mcp/library_ui`, RHP 오프라인
복사본은 `plugin-runtime/archive/ui`다. 원본을 하나로 유지하고 배포 시 복사한다.
모델링 tool·자산 생성 도구는 MCP, RHP 배포 도구는 이 모듈이 소유한다.

Bridge 빌드는 `build.ps1`, AlmondRhino 빌드는 해당 모듈의 스크립트를 사용한다.
출력은 기존 각 `plugin-runtime` 위치를 유지한다. source·RHP·의존 DLL·JSON·archive를
함께 전달하며 Rhino 제공 DLL은 포함하지 않는다. Engine 변경 시 두 출력의 DLL이
같아야 한다. Bridge의 `runtime-manifest.json`은 AlmondRhino 전용 소스를 포함하지 않는다.

## 검사

각 구성요소의 `tests/`에 fixture를 둔다. 패널은 Node tests, Engine은 NativeFixture,
Terminal은 TerminalSmoke·AlmondHostContracts·TerminalControls와 Node 입력 검사, Bridge는 archive host와
[Undo·관측 fixture](RhinoAlmondBridge/tests/script_executor_undo/README.md)를 사용한다.
기본 검사는 Rhino 없이 수행한다. 기능 검증은 사용자가 작업에 연결한 Rhino 파일의
실제 모델·도면에서 수행하며, 테스트만을 위한 별도 Rhino 문서 생성·실행은 지양한다.
기존 fixture의 문서 교체 guard는 유지하고 사용자 작업 파일에 그런 fixture를 실행하지 않는다.
오프라인 통과와 실제 작업 문서의 기능 검증은 구분한다.

Bridge·연결 RHP의 시작 동작과 실제 배포 명령 목록은
[native startup fixture](../../tests/native_startup/README.md)로 검사한다.
일상 worker와 실제 배포 RHP의 라이브러리 캐시는
[library startup fixture](RhinoAlmondBridge/tests/library_paths/README.md)로 비교한다.
managed helper 생성과 Engine 경로 검사만 사용하며 Rhino 프로세스나 문서는 시작하지 않는다.

Rhino의 지연 로드는 `CommandList` 등록에 의존한다. 연결 명령 변경 시 설치 스크립트가
백업 후 새 이름을 등록하고 이 fork에서 제거한 명령 값만 삭제한다. 다른 패널 명령과
플러그인 설정은 보존한다. `-VerifyOnly`는 파일 경로와 명령 캐시를 함께 검사하며
`tests/runtime_registration_tests.ps1`은 실제 설치 스크립트를 가짜 레지스트리에서 실행해
옛 캐시 거절·최초 등록·이전·반복 적용을 검증한다.
