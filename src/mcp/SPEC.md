# MCP 계약

이 모듈은 공개 MCP 도구, 계산·자산 API, CLI 실행과 연결별 Python runtime을 소유한다.
작업 규칙은 [AGENTS.md](AGENTS.md), 공통 경계는 [루트 SPEC](../../SPEC.md)를 따른다.

## 구성과 의존 관계

- `almond_mcp/`: 배포되는 Python package와 공개 도구·계산·라이브러리 API.
- `runtime/`: CLI 시작·재연결, 모델 binding, A–J 슬롯, 공유 저장소와 native 완료 확인.
- `tools/`: MCP 자산·모델링 자료의 생성·검증 도구.
- `tests/`, `pytest.ini`, `run_tests.ps1`: 모듈 검사. COS import 없이 실행한다.
- `rebuild_environment.ps1`: 이 체크아웃의 환경을 구성하며 COS catalog는 수정하지 않는다.
- `use_offline_environment.ps1`: 현재 셸과 자식에만 로컬 검사 경로를 설정한다.

COS는 runtime의 binding 검증·구성 훅을 사용한다. MCP는 COS 구현을 참조하지 않는다.
Python package 이름은 `almond_mcp`이며 외부 entry point와 도구 schema를 보존한다.
runtime 메타데이터 도구는 `project_info`, COS 내부 완료 조회는 `worker_state`다.
공개 도구 이름에 제품·클라이언트 접두사를 붙이거나 이전 이름의 alias를 남기지 않는다.
전용 CLI가 이 실행에만 주입하는 MCP 서버 키는 `rhino_session`이며 일반 Codex의 전역
`rhino` 등록과 구분한다. 이전에 실행된 프로세스의 식별 호환성은 유지한다.
공유 DB gate와 연결별 요청 직렬화 잠금은 획득을 최대 10초 기다린다. 대기 초과 호출은
operation·native 요청 생성 전 종료하며 소유자의 작업·잠금은 유지한다. 실행 제한과
cleanup·native 완료를 기다리는 시간은 이 10초와 구분한다.
`almond_mcp/rhino`의 C# 모델링 코드와 재료 정책은 MCP 소유지만 Bridge에 컴파일되므로,
변경 시 Bridge 빌드가 필요하다. Python package가 사용하는 웹 원본은
[RHP Asset Panel](../rhp/SPEC.md)의 공유 자원이다.

공개 API 내부 동작이나 schema를 바꾸면 루트 통합 검사를 수행한다. 새 COS/Codex
클라이언트가 현재 소스에서 catalog를 자동 추출한다. 실행 중인 세션은 시작 시 소스
fingerprint를 유지하므로 변경 후 정상 종료·새 시작이 필요하다. 공유 계약을 우회하지 않는다.

공통 오류 반환 필드인 `status`, `message`, 선택적 `error_code`는 `tool_response.py`에서
구성한다. 각 도구의 JSON 문자열·dict·이미지 반환 방식과 변경 적용·정합 필요 상태는
각 호출부가 유지하며, 공통 오류 필드만으로 rollback 여부를 추정하지 않는다.

## 기능별 구현과 소유권

공개 MCP 도구의 실제 구현은 `almond_mcp/features/<기능>/tools.py`에 있다.
기존 `src/mcp/tools/`는 자료 생성·검증 스크립트이므로 공개 도구의 위치와 구분한다.
각 기능의 `register(mcp, context)`는 명시적으로 도구·resource를 등록하고 기존 이름의
함수 dict를 반환한다. `server.py`는 공용 서비스 생성과 정적 factory 조립을 맡는다.
폴더명을 입력받아 SQL이나 모듈을 동적으로 찾거나 실행하지 않는다.

| 폴더 | 분류·성격 | 소유한 구현과 기능 |
|---|---|---|
| [`context`](almond_mcp/features/context) | 관찰·진단 | 모델·화면·프로브와 저장소 상태를 조회한다. runtime의 project_info와 COS 연결관리 도구는 각 호스트에 남는다. |
| [`planning`](almond_mcp/features/planning) | 작업계획 | Phase·Plan·Step, 참조 대상·의존 순서·evidence·immutable revision과 계획 SQL을 소유한다. |
| [`scenes`](almond_mcp/features/scenes) | Scene | 설계 의도와 Scene 장부, 일반 객체의 Scene 참조를 관리한다. |
| [`components`](almond_mcp/features/components) | Component | 등록 group의 소유권·계층·조회·동기화, focus·교차 관찰 및 native snapshot 정합과 SQL을 소유한다. |
| [`placement`](almond_mcp/features/placement) | 배치 | Room·asset instance의 장부와 배치·containment·충돌·하중 검사를 소유한다. Component 전체 기하 검증을 대신하지 않는다. |
| [`guidance`](almond_mcp/features/guidance) | 설계 참고자료 | 시공 지침·유형 서사·상세자료 후보 탐색과 ConstructionLibrary·HistoryLibrary를 소유한다. |
| [`modeling`](almond_mcp/features/modeling) | 모델링·재료 | 실행 도구·모델링 정책·초기 재료 설정·재료 적용과 MaterialLibrary를 소유한다. 공용 native C#·정책 JSON 위치는 유지한다. |
| [`grasshopper`](almond_mcp/features/grasshopper) | Grasshopper | GHX 해석·archetype·감사된 capsule 조회/실행, LibraryIndexer와 capsule 색인 SQL을 소유한다. |
| [`assets`](almond_mcp/features/assets) | 자산 | 자산 탐색·등록·배치·파생 도면·repository, 공개 resource와 비공개 generated-asset helper, 자산 색인 SQL을 소유한다. |
| [`diagrams`](almond_mcp/features/diagrams) | 다이어그램 | 사람·나무·기호 등 벡터/CAD 자산의 조회·검색·메타데이터·배치를 소유한다. 자산 DB와 manifest indexer는 공유한다. |
| [`drawings`](almond_mcp/features/drawings) | 도면·Sheet | recipe 색인·표현 스타일·해치 import와 Sheet/Layout 장부·축척·native 정합 및 SQL을 소유한다. |
| [`structure`](almond_mcp/features/structure) | 구조검토 | 설계 기준·구조검사·시각화·보고서, 관련 계산·하중·study 모듈과 검사 이력 SQL을 소유한다. |
| [`egress`](almond_mcp/features/egress) | 피난검사 | 피난 조건 검사를 소유하고 공용 시공 라이브러리 데이터를 사용한다. |
| [`exchange`](almond_mcp/features/exchange) | 외부교환 | GLB·almond.json 교환, 재료·metadata 복원·배치·실측 비교와 Blender helper를 소유한다. |
| [`capture`](almond_mcp/features/capture) | 캡처 | conditioning pass 캡처와 이미지 처리를 소유한다. |
| [`publishing`](almond_mcp/features/publishing) | 게시 | Chestnut 게시 payload·첨부와 객체 게시 처리를 소유한다. |

### 공개 도구 위치

아래 76개는 package 공개 도구다. runtime의 `project_info`를 포함한 COS 입력 catalog는 77개이며, COS의 연결관리 도구는 별도로 유지한다.

| 기능 | 공개 함수 |
|---|---|
| 관찰·진단 | `get_retrieval_status`, `get_rhino_context`, `get_rhino_probe`, `get_rhino_viewport_image` |
| 작업계획 | `create_generation_phase`, `get_generation_phase`, `list_generation_phases`, `update_generation_phase`, `create_generation_plan`, `get_generation_plan`, `list_generation_plans`, `update_generation_plan`, `list_generation_plan_revisions`, `update_generation_step`, `resolve_generation_targets` |
| Scene | `create_design_scene`, `get_design_scene`, `register_scene_objects`, `get_scene_objects` |
| Component | `upsert_design_component`, `get_design_component`, `list_design_components`, `sync_design_component`, `remove_design_component`, `get_component_intersections`, `focus_components` |
| 배치 | `upsert_design_room`, `register_scene_instance`, `remove_scene_instance`, `remove_design_room`, `validate_scene_layout` |
| 설계 참고자료 | `get_construction_guidance`, `get_typology_narrative`, `search_detail_sources` |
| 모델링·재료 | `get_modeling_policy`, `execute_rhino_script`, `setup_modeling`, `list_materials`, `assign_material` |
| Grasshopper | `list_library`, `get_logic_by_id`, `list_capsules`, `run_gh_definition` |
| 자산 | `list_drawing_assets`, `search_drawing_assets`, `get_drawing_asset`, `register_drawing_asset`, `get_asset_drawing`, `generate_asset_drawing_views`, `audit_asset_drawing`, `place_drawing_asset`, `search_asset_repository` |
| 다이어그램 | `list_diagram_assets`, `search_diagram_assets`, `get_diagram_asset`, `place_diagram_asset` |
| 도면·Sheet | `list_drawing_recipes`, `get_drawing_recipe`, `apply_drawing_style`, `import_drawing_hatch_patterns`, `upsert_drawing_sheet`, `get_drawing_sheet`, `list_drawing_sheets`, `sync_drawing_sheet`, `remove_drawing_sheet` |
| 구조검토 | `validate_structure`, `list_design_codes`, `visualize_structure`, `export_structural_report` |
| 피난검사 | `check_egress` |
| 외부교환 | `export_asset_contract`, `import_asset_contract`, `get_blender_helper_script` |
| 캡처 | `capture_conditioning_pass` |
| 게시 | `publish_objects_to_chestnut`, `publish_to_chestnut` |

### 공용 서비스와 DB 연결

- `feature_context.py`는 서버별 namespace를 조회한다. 도구가 sender·store를 호출할 때 현재 값을 읽으므로 runtime binding과 테스트 대체 주입이 반영된다. 서버 사이에 feature 전역 상태를 공유하지 않는다. `override`는 ContextVar로 호출별 보고서 경로와 sender를 한정하며 종료 시 복원한다.
- `server.py`는 경로·라이브러리 인스턴스·색인 동기화·MCP 조립과 기존 TCP sender를 유지한다. 라이브러리 초기화의 시점·순서는 기존과 같다. `library_index.py`의 `AssetLibraryIndexer`는 drawing·diagram·generated manifest가 공유한다. `paths.py`, `asset_passport.py`와 native 모델링 자원도 공용이다.
- `retrieval_store.AlmondStore`는 8개 feature store를 정적으로 합성하는 기존 진입점이다. `_connect`는 작업별 SQLite 연결을 열고 성공 시 commit, 예외 시 rollback, 끝에 close한다. 기초 schema·migration 호출 순서·공용 revision 기반은 여기에 남고 `store_common.py`는 직렬화·시각·공용 예외 identity를 제공한다.
- `assets`, `grasshopper`, `scenes`, `components`, `placement`, `planning`, `drawings`, `structure`의 `store.py`가 각각 기능의 규칙과 SQL을 소유한다. DB를 기능별로 새로 만들거나 일반 UPSERT 엔진으로 바꾸지 않는다. 한 논리 작업의 검사와 기록은 이전과 같은 연결·transaction에서 실행된다.
- `planning`은 Component reader를 사용한다. `drawings`는 planning 참조 helper와 component의 GUID·모델·native 검증을 사용한다. `scenes`도 component의 객체 소유·관측 helper를 사용한다. `placement`는 Scene·Assets 조회를 사용한다. 이 호출들은 같은 facade의 명시적 메서드이며 폴더를 파싱하지 않는다.
- Component·Sheet는 DB 사전검사 → native 변경 → 완전한 snapshot 확인 → DB 기록의 기존 순서를 지킨다. native 실행 후 DB 오류를 Rhino rollback으로 취급하지 않는다.
- `runtime/compat_almond.py`는 외부교환 helper의 보고서를 작업별 디렉터리로 제한한다. factory context override와 기존 module 함수 adapter를 지원하며 현재 sender의 binding·완료 receipt 검증을 유지한다.

### Python 구현 경로와 검증

Python 호출부는 기능별 실제 구현을 직접 import한다. `almond_mcp` 바로 아래에서
다른 모듈을 연결하던 15개 Python 호환 파일은 제공하지 않는다. 외부 Python 소비자도
아래 기능 경로를 사용해야 하며, MCP 도구 이름·schema·resource URI는 그대로다.

| 실제 Python 경로 | 모듈 |
|---|---|
| `almond_mcp.features.modeling` | `modeling_policy`, `modeling_setup` |
| `almond_mcp.features.grasshopper` | `ghx_parser` |
| `almond_mcp.features.assets` | `drawing_assets`, `drafting`, `asset_repository` |
| `almond_mcp.features.capture` | `conditioning` |
| `almond_mcp.features.exchange` | `exchange` |
| `almond_mcp.features.structure` | `native_structure`, `frame_solver`, `ec3`, `floor_loads`, `asset_loads`, `design_codes`, `structure_study` |

예를 들어 `from almond_mcp.features.assets.drafting import load_triangles`로 가져온다.
GHX parser를 직접 실행할 때는 `python -m almond_mcp.features.grasshopper.ghx_parser`
명령을 사용한다. 정책 JSON과 native C#·웹 원본의 공용 자원 위치는 유지한다.
서버의 기존 함수·클래스 이름도 조립 시 re-export한다. 비공개 generated-asset helper를
새 공개 MCP 도구로 노출하지 않고 기존 resource URI·등록을 유지한다.

각 기능의 직접 검사는 `tests/test_<기능>_feature.py`에서 factory·store를 사용한다.
전체 회귀는 `run_tests.ps1`, 호스트·catalog 검사는 COS runner, 모듈 경계·실제 전체
schema·패키징은 루트 통합 검사를 사용한다. 새 기능 파일을 추가하거나 기존 구현을
바꾸면 자동 catalog와 실제 worker의 일치를 검사한다. COS는 새 클라이언트 시작 시
server와 feature factory의 AST에서 schema를
읽으며 서버/DB를 import하지 않는다. package의 모든 Python 파일 목록과 내용이
fingerprint 대상이므로 이동·추가·삭제도 감지한다.

## 실행·관측 계약

연결마다 token·session·call 디렉터리와 프로세스 identity를 확인한다. 모델 폴더의
DB/tmp는 공유하며 저장소 lease·DB 잠금·native 완료 확인을 유지한다.

`get_rhino_context`, `get_rhino_viewport_image`, `get_rhino_probe`는 고정 관찰 경로다.
조회가 geometry·layer·selection·camera·Undo를 바꾸면 안 된다.
`execute_rhino_script`의 `result_error`는 이미 끝난 수정을 취소하지 않는다.
요청·반환 제한과 미확인 값의 의미는 [관측 계약](../../docs/modeling/native-observation.md)을 따른다.

기존 CoS command를 유지하기 위해 Python 환경은 `../engine/.venv`에 둔다.
구현 위치와 실행 파일 위치는 별개다. 이전 시작 버튼은 호환 스크립트를 거쳐
`runtime/` 실행기를 호출한다. 사용자 모델·DB·라이브러리를 자동 이동하지 않는다.

## Scene·Component·계획

- Scene은 공간의 의도와 맥락이다. 일반 객체를 직접 참조하거나 Component를 포함한다.
- Component는 명시적으로 등록한 Rhino group이다. 일반 group을 자동 등록하지 않는다. 한 객체의 직접 소유자는 최대 하나이고 Component는 하나 이상의 Scene에 속한다.
- 중첩 Component의 부모 group은 하위 객체를 포함하지만 직접 소유권은 자식에 남는다. block occurrence는 포함할 수 있고 공유 block definition 내부를 occurrence별 객체로 소유하지 않는다.
- Rhino group의 UserString 대신 기존 멤버의 `almond:component_record`를 `ModifyAttributes`로 변경해 Undo를 보존한다. 관리용 가짜 객체는 만들지 않는다.
- DB 사전검사 → native 수정 → 완전한 snapshot 확인 → DB commit 순서다. 캐시 조회는 `live_verified=false`, live 조회는 불일치·pending objects를 드러내고 명시적 sync가 장부와 group을 정합시킨다. timeout은 재실행 허가가 아니다.
- Room·asset instance는 기존 충돌·containment·하중 검사에 남는다. `validate_scene_layout`의 통과를 Component 기하 검증으로 해석하지 않는다.
- Phase 아래 Plan, Plan 아래 Step을 둔다. Plan은 여러 Scene·Component, Step은 Component를 참조한다. 참조 생략은 상속, 빈 목록은 대상 없음이다.
- Plan 변경은 immutable revision으로 기록하며 `expected_revision`은 오래된 상태의 수정을 거절한다. 이 기록은 기하 백업이나 자동 실행기가 아니다.

세부 입력·계층·동기화·도면 계약은 [Component 시스템](../../docs/modeling/component-system.md)에 둔다.

## 재료·도면·자산

재료 manifest의 `layer_path`와 `modeling_policy.json`을 기준으로 `assign_material`과 `ModelingMaterials.CreateAttributes`가 같은 native 구현을 사용한다. MCP C# 실행은 추가 객체·직접 재료 변경을 모아 최종 속성으로 레이어를 적용한 뒤 같은 Undo record를 닫는다. 시작 시 전체 문서를 변경하지 않으며 ByLayer·ByParent는 추측하지 않는다. 외부 스크립트는 factory를 명시적으로 사용한다.

새 모델링 metadata는 필요한 material ID·floor·construction detail·typed source에 한정한다. Component 등록이 소유권을 기록하고 PBR 값은 native material에 둔다. 이름은 자유롭게 사용하며 기존 unrelated UserString을 지우지 않는다.

Drawing Sheet는 모델 공간 World XY의 작성 영역을 Rhino Layout의 Top detail로 지정 축척에 연결한다. 영역이 용지·축척에 맞지 않으면 생성 전에 거절한다. 도면 형상이나 단면 대상을 자동 추측하지 않으며 등록 해제는 geometry·Layout 삭제가 아니다.

저장소 `asset/`, wheel `almond_mcp/data/`, AppData 라이브러리의 배치는 다르다. 명시적 `RHINO_MCP_*_DIR`이 우선하며 기존 사용자 파일·manifest 상대 경로·계약/모델 해시를 보존한다. 다운로드한 community model과 원시 생성 파일은 기본 패키지에 포함하지 않는다. 자산·도면 도구와 단위·출처 계약은 [자산 안내](../../docs/assets/assets-and-drawings.md)를 따른다.

## 지침 Markdown 원본

MCP 도구·리소스의 공개 설명과 응답에 덧붙이는 행동 지침은 원래 Python 파일과
같은 폴더의 `<파일 stem>-explain.md`에 둔다. 예를 들어 `features/modeling/tools.py`는
`features/modeling/tools-explain.md`를 읽는다. 각 항목은 `instruction:` HTML 주석으로
경계를 표시하며, 본문과 동적 값의 공백을 보존한다. `almond_mcp/instruction_text.py`가
지침을 읽고 등록 전에 함수 설명에 적용한다. 항목이 없거나 중복되면 명시적으로 실패한다.
입력 검증 조건, 오류 상태·수치 결과, SQL과 실행할 C#/Blender 코드는 지침 원본이 아니다.
기존 `FUNDAMENTAL-INSTRUCTIONS.md`와 `MODEL-CONTEXT-INSTRUCTIONS.md`의 전달 방식은 유지한다.

COS는 모델 서버를 import하지 않고 같은 Markdown에서 도구 설명을 추출한다.
package와 runtime의 지침 Markdown도 세션 source fingerprint에 포함하므로 변경 후에는
해당 Codex/CoS MCP 또는 Terminal almond 세션을 정상 종료하고 새로 시작한다.
Python 지침만 변경했을 때 Rhino RHP 빌드·등록 변경은 필요하지 않다.
