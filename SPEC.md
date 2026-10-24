# Almond 구조와 데이터 계약

설치·실행·빌드·작업 규칙은 [AGENTS.md](AGENTS.md), 기능별 안내는 [README.md](README.md)를 따른다.

## 코드와 실행 구성

| 위치 | 책임 |
|---|---|
| `src/engine` | 실행기, A–J 슬롯, 문서 연결, 공유 저장소·프로세스 소유권 |
| `src/engine/native` | 별도 `Almond.Engine.dll` |
| `src/mcp/almond_mcp` | Python MCP 서버, 구조해석 계산, 자산·Scene·계획 API |
| `src/cos` | stdio host와 연결별 worker, 도구 카탈로그·계약 검사 |
| `src/rhp/RhinoAlmondBridge` | Rhino 명령, TCP 요청, C# 실행·Undo, 고정 관찰 |
| `src/rhp/Structural_Analysis` | 구조해석·결과 패널과 solver 연결; Bridge에 컴파일 |
| `src/rhp/Asset_Panel` | 라이브러리·배치·archive; 공용 웹 UI 포함 |
| `src/rhp/RhinoTerminal` | Bridge에 컴파일되는 터미널·Engine 연결; 별도 PlugIn entry 없음 |
| `src/rhp/AlmondCOS` | 별도 COS RHP와 host 탐색·문서 연결 |
| `asset` | constructions, drawing, diagram, models, capsules, history 라이브러리 |
| `tests` | engine/mcp/cos/rhp별 fixture와 회귀 검사 |
| `tools`, `docs`, `examples` | 빌드·검증 도구, 기능 문서, 사용 예제 |

MCP package 이름은 `almond_mcp`다. Bridge가 Structural_Analysis·Asset_Panel·RhinoTerminal을 한 assembly로 컴파일하며 Engine과 COS는 별도로 유지한다. Bridge의 유일한 plugin entry가 패널 등록과 Terminal 종료를 담당한다.

웹 원본은 `src/rhp/Asset_Panel/web`, wheel의 경로는 `almond_mcp/library_ui`, RHP의 오프라인 복사본은 `plugin-runtime/archive/ui`다. Python 환경은 루트 `pyproject.toml`·`uv.lock`을 기준으로 `src/engine/.venv`에 구성한다.

## 문서와 실행 identity

모델 폴더별 `.almond/scene.sqlite3`와 `.almond/tmp`는 공유하고 연결별 token·session·call 디렉터리는 분리한다. 객체 identity는 정규화한 모델 경로와 Rhino GUID의 조합이다. 공유 DB 잠금·연결 lease·프로세스 identity·UI thread·native 완료 확인을 거쳐야 한다.

`get_rhino_context`, `get_rhino_viewport_image`, `get_rhino_probe`는 고정 관찰 경로다. 조회를 위해 geometry·layer·selection·camera·Undo를 바꾸지 않는다. `execute_rhino_script`는 수정 실행이며 `result_error`가 이미 끝난 수정을 취소하지 않는다. 요청·반환 제한과 미확인 값의 의미는 [관측 계약](docs/modeling/native-observation.md)을 따른다.

## Scene·Component·계획

- Scene은 공간의 의도와 맥락이다. 일반 객체를 직접 참조하거나 Component를 포함한다.
- Component는 명시적으로 등록한 Rhino group이다. 일반 group을 자동 등록하지 않는다. 한 객체의 직접 소유자는 최대 하나이고 Component는 하나 이상의 Scene에 속한다.
- 중첩 Component의 부모 group은 하위 객체를 포함하지만 직접 소유권은 자식에 남는다. block occurrence는 포함할 수 있고 공유 block definition 내부를 occurrence별 객체로 소유하지 않는다.
- Rhino group의 UserString 대신 기존 멤버의 `almond:component_record`를 `ModifyAttributes`로 변경해 Undo를 보존한다. 관리용 가짜 객체는 만들지 않는다.
- DB 사전검사 → native 수정 → 완전한 snapshot 확인 → DB commit 순서다. 캐시 조회는 `live_verified=false`, live 조회는 불일치·pending objects를 드러내고 명시적 sync가 장부와 group을 정합시킨다. timeout은 재실행 허가가 아니다.
- Room·asset instance는 기존 충돌·containment·하중 검사에 남는다. `validate_scene_layout`의 통과를 Component 기하 검증으로 해석하지 않는다.
- Phase 아래 Plan, Plan 아래 Step을 둔다. Plan은 여러 Scene·Component, Step은 Component를 참조한다. 참조 생략은 상속, 빈 목록은 대상 없음이다.
- Plan 변경은 immutable revision으로 기록하며 `expected_revision`은 오래된 상태의 수정을 거절한다. 이 기록은 기하 백업이나 자동 실행기가 아니다.

세부 입력·계층·동기화·도면 계약은 [Component 시스템](docs/modeling/component-system.md)에 둔다.

## 재료·도면·자산

재료 manifest의 `layer_path`와 `modeling_policy.json`을 기준으로 `assign_material`과 `ModelingMaterials.CreateAttributes`가 같은 native 구현을 사용한다. MCP C# 실행은 추가 객체·직접 재료 변경을 모아 최종 속성으로 레이어를 적용한 뒤 같은 Undo record를 닫는다. 시작 시 전체 문서를 변경하지 않으며 ByLayer·ByParent는 추측하지 않는다. 외부 스크립트는 factory를 명시적으로 사용한다.

새 모델링 metadata는 필요한 material ID·floor·construction detail·typed source에 한정한다. Component 등록이 소유권을 기록하고 PBR 값은 native material에 둔다. 이름은 자유롭게 사용하며 기존 unrelated UserString을 지우지 않는다.

Drawing Sheet는 모델 공간 World XY의 작성 영역을 Rhino Layout의 Top detail로 지정 축척에 연결한다. 영역이 용지·축척에 맞지 않으면 생성 전에 거절한다. 도면 형상이나 단면 대상을 자동 추측하지 않으며 등록 해제는 geometry·Layout 삭제가 아니다.

저장소 `asset/`, wheel `almond_mcp/data/`, AppData 라이브러리의 배치는 다르다. 명시적 `RHINO_MCP_*_DIR`이 우선하며 기존 사용자 파일·manifest 상대 경로·계약/모델 해시를 보존한다. 다운로드한 community model과 원시 생성 파일은 기본 패키지에 포함하지 않는다. 자산·도면 도구와 단위·출처 계약은 [자산 안내](docs/assets/assets-and-drawings.md)를 따른다.
