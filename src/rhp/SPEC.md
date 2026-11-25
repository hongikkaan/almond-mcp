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
| `AlmondRhino/` | AlmondRhino 출력 폴더. 구현은 [외부 연결기 모듈](../beyond/SPEC.md) 소유 |

Bridge의 유일한 plugin entry가 패널 등록과 Terminal 종료를 담당한다. Engine과 AlmondRhino는 별도 assembly다. Engine은 호스트 프로젝트를 참조하지 않는다. Bridge는 MCP 소유 `features/<기능>/native`의 C# 도구 구현, `src/mcp/rhino`의 공용 C# 소스와 재료 정책을 빌드 입력으로 사용한다. [GeometryJson.Point](../mcp/rhino/GeometryJson.cs)는 점의 세 좌표를 그대로 배열에 넣는다. 문서 관측에서 유한하지 않은 좌표를 `null`로 표시하는 처리는 `DocumentObservation`에 둔다.

## 실행·관찰

Bridge 로드는 패널과 기존 native handler/helper만 준비한다. 구형 5000번 포트 listener와 `AlmondMCPStart`·`AlmondMCPStop`·`AlmondMCPStatus` 명령은 제거했으며 별칭을 등록하지 않는다.
모델 작업용 transport는 문서·token에 바인딩된 Engine 세션에서만 시작한다. Engine은 고정 plugin GUID에서 `IBridgeProvider`를 찾아 `IBridgeRequestHandler`를 사용한다. private 필드명·정확한 배포 버전 문자열을 실행 계약으로 사용하지 않는다. `BridgeDispatchContext`가 인증한 문서·모델 경로·세션·작업·요청 identity를 전달하며 Bridge는 처리 전후 문서를 확인하고 같은 문서를 기능 구현에 전달한다. 기존 JSON opcode와 payload는 유지한다.

문서 identity, UI thread, 요청·완료 envelope, 공유 저장소 lease와 Undo/Redo 계약을 보존한다. 고정 관찰은 geometry·layer·selection·camera·Undo를 바꾸지 않는다.
수정 실행의 반환 오류와 실제 rollback은 구분한다. 입력·출력 한계와 viewport·probe 계약은 [관측 문서](../mcp/rhino/OBSERVATION-SPEC.md)를 따른다.

`NativeBinding`이 두 호스트의 공통 binding 구성·소유자 확인 발행·무효화·문서 identity·native drain 이후 worker gate를 잡은 locator/lease 해제를 소유한다. Terminal의 PTY와 AlmondRhino의 discovery·worker·slot 수명은 각 호스트가 소유한다. 다른 token의 ready/locator 기록은 덮어쓰거나 삭제하지 않는다.

Terminal과 AlmondRhino는 모델 경로를 표시하고 비교할 때 Engine의 `SessionFiles.Canonical`과 `SessionFiles.Same`을 사용한다. 각 호스트는 연결할 문서의 저장 상태와 문서 식별번호를 확인한다.
두 호스트는 공용 `RuntimeEnvironment`로 고정 RHP 출력 위치에서 `../mcp/runtime`에 해당하는 실제 경로를 계산해 사용한다. 개발 워크트리로 일상 Rhino 등록을 변경하지 않는다.

Terminal의 shell·AlmondHost 수명은 패널과 독립적이다. Rhino 시작이나 패널 복원은 실행을 시작하지 않는다. `RhinoTerminal`의 `On`/`Off`는 표시 상태와 무관하게 실행을 제어하고 `PanelToggle`은 표시만 바꾼다. 패널 없는 실행도 출력 소비와 문서 확인을 유지하며, 최근 128 Ki 문자 출력을 보관해 새 패널에 재생한다.
패널 오른쪽 위 almond/resume 버튼은 기존 터미널 입력 경로로 명령과 Enter를 보낸다.
자세한 절차는 [Terminal 사용법](RhinoTerminal/사용법.txt)을 따른다.

## 문서 변경과 비동기 결과

`NativeUndoRecord`는 ScriptExecutor의 기존 Undo 소유권·빈 record purge·복구 후 Redo 정리를 공유한다. 도면 스타일과 GH 형상 출력은 변경 전에 전용 record를 확보한다. 모든 GH 출력 포트 존재를 베이크 전에 확인한다. 응답의 `mutation_state`는 `none`, `completed`, `rolled_back`, `unknown`이며 `requires_reconciliation`이 참이면 자동 재시도 대신 실제 문서와 반환된 GUID를 확인한다. Rhino 명령이 소유한 배치 Undo는 기존 command 경로에 남긴다.

패널의 대기 중 작업은 요청 문서를 다시 확인한다. 비동기 해석 결과 적용과 결과 객체 선택은 현재 문서 serial·경로·단위·허용오차·객체 형상/속성 fingerprint가 원 요청과 같아야 한다. overlay는 그 문서에서만 그려지며 다른 문서의 기존 결과를 재사용하지 않는다. 해제된 패널의 비동기 응답은 적용하지 않는다.

## 도면 스타일

`DrawingStyleManager`는 요청한 선종류의 이름까지 확인한다. 없는 이름에 대한 Rhino의 Continuous 반환을 해당 선종류가 존재한다는 근거로 사용하지 않는다.
문서에 같은 이름의 선종류가 있으면 기존 인덱스를 레이어에 적용한다. 이미 연결된 도면의 선종 정의와 참조를 유지한다.
레이어는 선종류의 이름을 지정한다. Python MCP는 패키지에 포함된 `profiles/linetype/manifest.json` 경로를 native 요청에 전달한다. 문서에 없는 이름이 필요할 때만 해당 파일을 읽는다. 새 정의의 각 세그먼트에는 유한한 양수 길이와 명시적인 실선/공백 여부가 필요하다. 필요한 파일을 읽을 수 없거나 정의가 누락 또는 유효하지 않으면 Undo 시작 전에 오류를 반환한다.

## 공유 자원과 출력

라이브러리 조회의 Python 위치는 Terminal 클래스가 아니라 `RuntimeEnvironment`에서 해석한다. native archive는 drawing snapshot의 선택적 `sha256`을 실제 제공할 바이트에 대조한다.

웹 원본은 `Asset_Panel/web`, wheel 경로는 `almond_mcp/library_ui`, RHP 오프라인 복사본은 `plugin-runtime/archive/ui`다. 원본을 하나로 유지하고 배포 시 복사한다.
모델링 tool·자산 생성 도구는 MCP, RHP 배포 도구는 이 모듈이 소유한다.

Bridge 빌드는 `build.ps1`, AlmondRhino 빌드는 해당 모듈의 스크립트를 사용한다.
출력은 기존 각 `plugin-runtime` 위치를 유지한다. source·RHP·의존 DLL·JSON·archive를 함께 전달하며 Rhino 제공 DLL은 포함하지 않는다. Engine 변경 시 두 출력의 DLL이 같아야 한다. Bridge의 `runtime-manifest.json`은 AlmondRhino 전용 소스를 포함하지 않는다.

`tools/verify_runtime.py`의 기록과 검증은 같은 필수 산출물 규칙을 사용한다. RHP·Engine과 Bridge의 필수 라이선스가 manifest에 포함되고 실제 바이트가 일치해야 한다. 배포 결과와 네이티브 소스, 빌드 스크립트, archive 생성 코드와 배포 자산·라이선스의 해시 및 양쪽 Engine 일치도 확인한다. 기록되지 않은 추가 파일은 허용한다. 검증 범위는 체크아웃에서 관리하는 입력과 출력이다.

Bridge 일상 빌드와 Yak 빌드는 같은 컴파일·archive·라이선스 단계를 사용한다. Yak staging은 런타임 의존 파일만 복사하고 Rhino 제공 SDK와 원본 Bridge DLL·PDB를 배포하지 않는다. Python 패키지 버전의 원본은 `src/mcp/__init__.py`다. Hatch는 이 버전을 쓰고, MSBuild와 Yak는 Bridge용 SemVer 표기로 변환한다. 예를 들어 `0.7.0rc2`는 `0.7.0-rc.2`가 된다. AlmondRhino와 Engine은 각 프로젝트의 버전을 유지한다. 문서 전용 시작기를 포함한 native 연결은 Engine의 Bridge provider 계약으로 호환성을 검증한다.

## 검사

각 구성요소의 `tests/`에 fixture를 둔다. 패널의 Node 검사는 자산 배치와 결과 선택을, Engine의 NativeFixture는 세션 identity·공유 잠금·완료 확인을, Terminal의 AlmondHostContracts는 소유권 해제를 검사한다. Bridge의 archive host는 오프라인 GLB 디코더 검사를 지원한다. 실행 방법과 범위는 [native 검사 안내](tests/README.md), Undo·관측의 현재 상태는 [별도 안내](RhinoAlmondBridge/tests/script_executor_undo/README.md)를 따른다.
개발 검사는 [오프라인 검사 기준](../../tests/README.md)에 따라 Rhino·RhinoCore와 사용자 작업 파일을 사용하지 않는다. Rhino에서만 확인 가능한 동작은 검증 범위 밖으로 기록한다.

현재 오프라인 fixture는 Bridge·연결 RHP의 실제 시작, 배포 명령 목록, 일상 worker와 배포 RHP의 라이브러리 캐시 일치를 검증하지 않는다. managed helper 검사는 Rhino 프로세스를 실행하거나 연결하지 않는다.

Rhino의 지연 로드는 `LoadMode`와 `CommandList` 등록에 의존한다. 설치 스크립트는 바꿀 값을 계획하고 기존 키를 내보낸 다음 경로·로드 모드·명령을 적용한다. 명령 캐시에서는 등록 목록에 지정한 폐기 값만 제거한다. 쓰기나 최종 검증에 실패하면 이 실행이 수정한 값만 원복하며 이미 바뀐 다른 값은 보존한다. `-VerifyOnly`는 경로, 이름, DWORD 로드 모드, 현행 명령값과 폐기 값의 잔존 여부를 검사한다. 오프라인 테스트는 대역 레지스트리로 반복 적용, 쓰기 실패 복구와 사용자 값 보존을 검증한다.
