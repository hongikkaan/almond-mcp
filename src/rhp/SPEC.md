# Rhino native 계약

이 모듈은 Rhino 내부 실행·관찰·패널·터미널과 공용 native 연결을 소유한다.
[작업 지침](AGENTS.md)과 [공통 경계](../../SPEC.md)를 함께 따른다.

## 구성과 빌드

| 위치 | 책임 |
|---|---|
| `RhinoAlmondBridge/` | Rhino 명령, TCP 요청, C# 실행·Undo, 고정 관찰과 plugin entry |
| `Engine/` | 별도 `Almond.Engine.dll`; 연결 identity·공유 lease·native 완료 |
| `RhinoTerminal/` | 터미널·MCP 실행기 연결. 별도 plugin entry 없이 Bridge에 컴파일 |
| `Structural_Analysis/` | 구조해석·결과 패널과 solver 연결; Bridge에 컴파일 |
| `Asset_Panel/` | 라이브러리·배치·archive와 공용 웹 원본; Bridge에 컴파일 |
| `tools/` | 빌드·패키징·설치·실행 파일 검증 도구 |
| `AlmondCOS/` | 기존 등록을 보존하는 COS 출력 폴더. 구현은 [COS](../cos/SPEC.md) 소유 |

Bridge의 유일한 plugin entry가 패널 등록과 Terminal 종료를 담당한다. Engine과
COS는 별도 assembly다. Engine은 호스트 프로젝트를 참조하지 않는다. Bridge는
MCP 소유 C# 모델링 코드와 재료 정책을 링크하므로 해당 변경도 빌드 입력이다.

## 실행·관찰

문서 identity, UI thread, 요청·완료 envelope, 공유 저장소 lease와 Undo/Redo 계약을
보존한다. 고정 관찰은 geometry·layer·selection·camera·Undo를 바꾸지 않는다.
수정 실행의 반환 오류와 실제 rollback은 구분한다. 입력·출력 한계와 viewport·probe
계약은 [관측 문서](../../docs/modeling/native-observation.md)를 따른다.

Terminal과 COS는 고정 RHP 출력 위치에서 `../mcp/runtime`에 해당하는 실제 경로를
계산해 사용한다. 개발 워크트리로 일상 Rhino 등록을 변경하지 않는다.

## 공유 자원과 출력

웹 원본은 `Asset_Panel/web`, wheel 경로는 `almond_mcp/library_ui`, RHP 오프라인
복사본은 `plugin-runtime/archive/ui`다. 원본을 하나로 유지하고 배포 시 복사한다.
모델링 tool·자산 생성 도구는 MCP, RHP 배포 도구는 이 모듈이 소유한다.

Bridge 빌드는 `build.ps1`, COS 빌드는 해당 모듈의 스크립트를 사용한다.
출력은 기존 각 `plugin-runtime` 위치를 유지한다. source·RHP·의존 DLL·JSON·archive를
함께 전달하며 Rhino 제공 DLL은 포함하지 않는다. Engine 변경 시 두 출력의 DLL이
같아야 한다. Bridge의 `runtime-manifest.json`은 COS 전용 소스를 포함하지 않는다.

## 검사

각 구성요소의 `tests/`에 fixture를 둔다. 패널은 Node tests, Engine은 NativeFixture,
Terminal은 TerminalSmoke·AlmondHostContracts, Bridge는 archive host와
[Undo·관측 fixture](RhinoAlmondBridge/tests/script_executor_undo/README.md)를 사용한다.
실제 Rhino가 필요한 검사는 일회용 문서에서 수행하며 offline 통과와 구분한다.
