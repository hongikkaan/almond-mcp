# Rhino native 계약

이 모듈은 Rhino 내부 실행·관찰·패널·터미널과 공용 native 연결을 소유한다.
[루트 작업 지침](../../AGENTS.md)과 [공통 경계](../../SPEC.md)를 함께 따른다.

## 구성과 빌드

| 위치 | 책임 |
|---|---|
| `RhinoAlmondBridge/` | native 요청 전달, C# 실행·Undo와 plugin entry |
| `Engine/` | 별도 `Almond.Engine.dll`; 연결 identity·공유 lease·native 완료 |
| `RhinoTerminal/` | 터미널·MCP 실행기 연결. 별도 plugin entry 없이 Bridge에 컴파일 |
| `Structural_Analysis/` | 구조해석 작업·결과 표시 UI; Bridge에 컴파일 |
| `Asset_Panel/` | 라이브러리 패널·마우스 배치·archive와 공용 웹 원본; Bridge에 컴파일 |
| `tools/` | 빌드·패키징·설치·실행 파일 검증 도구 |
| `AlmondRhino/` | AlmondRhino 출력 폴더. 구현은 [외부 연결기 모듈](../cos/SPEC.md) 소유 |

Bridge의 유일한 plugin entry가 패널 등록과 Terminal 종료를 담당한다. Engine과 AlmondRhino는 별도 assembly다. Engine은 호스트 프로젝트를 참조하지 않는다. Bridge는 MCP 소유 `features/<기능>/native`의 C# 도구 구현과 재료 정책을 링크하므로 해당 변경도 빌드 입력이다.

## 실행·관찰

Bridge 로드는 패널과 기존 native handler/helper만 준비한다. 구형 5000번 포트 listener와 `AlmondMCPStart`·`AlmondMCPStop`·`AlmondMCPStatus` 명령은 제거했으며 별칭을 등록하지 않는다.
모델 작업용 transport는 문서·token에 바인딩된 Engine 세션에서만 시작한다. Engine이 확인하는 Bridge의 `_server` 필드·`HandleRequest`와 helper 계약은 유지한다.

문서 identity, UI thread, 요청·완료 envelope, 공유 저장소 lease와 Undo/Redo 계약을 보존한다. 고정 관찰은 geometry·layer·selection·camera·Undo를 바꾸지 않는다.
수정 실행의 반환 오류와 실제 rollback은 구분한다. 입력·출력 한계와 viewport·probe 계약은 [관측 문서](../mcp/rhino/OBSERVATION-SPEC.md)를 따른다.

Terminal과 AlmondRhino는 고정 RHP 출력 위치에서 `../mcp/runtime`에 해당하는 실제 경로를 계산해 사용한다. 개발 워크트리로 일상 Rhino 등록을 변경하지 않는다.

Terminal의 shell·AlmondHost 수명은 패널과 독립적이다. Rhino 시작이나 패널 복원은 실행을 시작하지 않는다. `RhinoTerminal`의 `On`/`Off`는 표시 상태와 무관하게 실행을 제어하고 `PanelToggle`은 표시만 바꾼다. 패널 없는 실행도 출력 소비와 문서 확인을 유지하며, 최근 128 Ki 문자 출력을 보관해 새 패널에 재생한다.
패널 오른쪽 위 almond/resume 버튼은 기존 터미널 입력 경로로 명령과 Enter를 보낸다.
자세한 절차는 [Terminal 사용법](RhinoTerminal/사용법.txt)을 따른다.

## 도면 스타일

`DrawingStyleManager`는 요청한 선종류의 이름까지 확인한다. 없는 이름에 대한 Rhino의 Continuous 반환을 해당 선종류가 존재한다는 근거로 사용하지 않는다.
문서에 같은 이름의 선종류가 있으면 기존 인덱스를 레이어에 적용한다. 이미 연결된 도면의 선종 정의와 참조를 유지한다.
레이어는 선종류의 이름을 지정한다. Python MCP는 패키지에 포함된 `profiles/linetype/manifest.json` 경로를 native 요청에 전달한다. 문서에 없는 이름이 필요할 때만 해당 파일을 읽는다. 새 정의의 각 세그먼트에는 유한한 양수 길이와 명시적인 실선/공백 여부가 필요하다. 필요한 파일을 읽을 수 없거나 정의가 누락 또는 유효하지 않으면 Undo 시작 전에 오류를 반환한다.

## 공유 자원과 출력

웹 원본은 `Asset_Panel/web`, wheel 경로는 `almond_mcp/library_ui`, RHP 오프라인 복사본은 `plugin-runtime/archive/ui`다. 원본을 하나로 유지하고 배포 시 복사한다.
모델링 tool·자산 생성 도구는 MCP, RHP 배포 도구는 이 모듈이 소유한다.

Bridge 빌드는 `build.ps1`, AlmondRhino 빌드는 해당 모듈의 스크립트를 사용한다.
출력은 기존 각 `plugin-runtime` 위치를 유지한다. source·RHP·의존 DLL·JSON·archive를 함께 전달하며 Rhino 제공 DLL은 포함하지 않는다. Engine 변경 시 두 출력의 DLL이 같아야 한다. Bridge의 `runtime-manifest.json`은 AlmondRhino 전용 소스를 포함하지 않는다.

`tools/verify_runtime.py`의 기록과 검증은 같은 필수 산출물 규칙을 사용한다. RHP·Engine과 Bridge의 필수 라이선스가 manifest에 포함되고 실제 바이트가 일치해야 한다. 빈 출력 목록이나 필수 항목 누락을 성공으로 처리하지 않는다. 기록된 나머지 파일과 소스의 해시·소스 목록·양쪽 Engine 일치도 확인한다. 기록되지 않은 추가 파일을 일괄 금지하지 않으며, 이 검사는 모든 빌드 입력의 완전성이나 실제 Rhino 로드를 보증하지 않는다.

## 검사

각 구성요소의 `tests/`에 fixture를 둔다. 패널의 Node 검사는 자산 배치와 결과 선택을, Engine의 NativeFixture는 세션 identity·공유 잠금·완료 확인을, Terminal의 AlmondHostContracts는 소유권 해제를 검사한다. Bridge의 archive host는 오프라인 GLB 디코더 검사를 지원한다. 실행 방법과 범위는 [native 검사 안내](tests/README.md), Undo·관측의 현재 상태는 [별도 안내](RhinoAlmondBridge/tests/script_executor_undo/README.md)를 따른다.
개발 검사는 [오프라인 검사 기준](../../tests/README.md)에 따라 Rhino·RhinoCore와 사용자 작업 파일을 사용하지 않는다. Rhino에서만 확인 가능한 동작은 검증 범위 밖으로 기록한다.

현재 오프라인 fixture는 Bridge·연결 RHP의 실제 시작, 배포 명령 목록, 일상 worker와 배포 RHP의 라이브러리 캐시 일치를 검증하지 않는다. managed helper 검사는 Rhino 프로세스를 실행하거나 연결하지 않는다.

Rhino의 지연 로드는 `CommandList` 등록에 의존한다. 연결 명령 변경 시 설치 스크립트가 백업 후 새 이름을 등록하고 이 fork에서 제거한 명령 값만 삭제한다. 다른 패널 명령과 플러그인 설정은 보존한다. `-VerifyOnly`는 파일 경로와 명령 캐시를 함께 검사한다. 등록 이전·반복 적용의 가짜 레지스트리 자동 검사는 현재 없다.
