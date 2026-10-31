# MCP 계약

이 모듈은 공개 MCP 도구, 계산·자산 API, CLI 실행과 연결별 Python runtime을 소유한다.
작업 규칙은 [AGENTS.md](AGENTS.md), 공통 경계는 [루트 SPEC](../../SPEC.md)를 따른다.

## 구성과 의존 관계

- `./`: Python package의 소스와 공개 도구·계산·라이브러리 API.
- `runtime/`: CLI 시작·재연결, 모델 binding, A–J 슬롯, 공유 저장소와 native 완료 확인.
- `BASIC-INSTRUCTIONS.md`, `*-explain.md`: 기본 작업 지침과 도구별 설명 원본. `features/guidance/guides/`는 연결된 참고자료, `release_validation/`은 배포 검증을 소유한다.
- `tests/`, `pytest.ini`, `run_tests.ps1`: 모듈 검사. COS import 없이 실행한다.
- `rebuild_environment.ps1`: 이 체크아웃의 환경을 구성하며 COS catalog는 수정하지 않는다.
- `use_offline_environment.ps1`: 현재 셸과 자식에만 로컬 검사 경로를 설정한다.

COS는 runtime의 binding 검증·구성 훅을 사용한다. MCP는 COS 구현을 참조하지 않는다.
Python package 이름은 `almond_mcp`이며 외부 entry point와 도구 schema를 보존한다.
소스는 이 폴더에 직접 둔다. editable 설치는 `almond_mcp.py`가 이곳의 `__init__.py`를 package로 로드하며, wheel은 빌드 경로 매핑으로 `almond_mcp/`에 담는다.
이 진입 파일은 wheel에 포함하지 않는다.
runtime 메타데이터 도구는 `project_info`, COS 내부 완료 조회는 `worker_state`다.
공개 도구 이름에 제품·클라이언트 접두사를 붙이거나 이전 이름의 alias를 남기지 않는다.
전용 CLI가 이 실행에만 주입하는 MCP 서버 키는 `rhino_session`이며 일반 Codex의 전역 `rhino` 등록과 구분한다. 이전에 실행된 프로세스의 식별 호환성은 유지한다.
RhinoTerminal은 `codex.ps1 -RhinoTerminal`로 시작하며 새 대화·resume·exec에 실행별 `features.apps=false`, `features.plugins=false`를 전달한다. `mcp list`에 나타나지 않고 실행 중 추가되는 Apps(CoS 포함)와 플러그인 MCP의 등록 경로를 끈다. 일반 개인 스킬은 유지되며 플러그인 소속 스킬은 제외된다. 이 옵션은 별도 창의 전용 시작기나 일반 Codex에는 적용하지 않고, 전역·프로젝트 설정과 인증 파일도 수정하지 않는다.
설정 목록 검사는 MCP 연결·도구 탐색·실제 호출 검증과 별개다. Codex TUI 자체가 추가하는 도구는 Apps·플러그인과 별도 경로이므로 설정 목록만으로 `rhino_session` 외 모든 도구의 부재를 보장하지 않는다. 실행기 회귀 검사는 `tests/runtime/test_terminal_launch.ps1`에서 실제 설치 CLI의 설정 해석을 사용하고 Rhino 관측만 대역으로 수행한다. 이 스크립트 변경만으로 RHP 빌드·등록은 필요하지 않으며, 배포된 변경은 RhinoTerminal의 기존 Codex를 `/exit`한 뒤 `almond` 또는 `almond resume`으로 다시 시작할 때 적용된다.
공유 DB gate와 연결별 요청 직렬화 잠금은 획득을 최대 10초 기다린다. 대기 초과 호출은 operation·native 요청 생성 전 종료하며 소유자의 작업·잠금은 유지한다. 실행 제한과 cleanup·native 완료를 기다리는 시간은 이 10초와 구분한다.
`features/<기능>/native`의 C# 도구 구현과 `rhino`의 공통 모델링 코드·재료 정책은 MCP 소유지만 Bridge에 컴파일되므로, 변경 시 Bridge 빌드가 필요하다. Python package가 사용하는 웹 원본은 [RHP Asset Panel](../rhp/SPEC.md)의 공유 자원이다.

공개 API 내부 동작이나 schema를 바꾸면 루트 통합 검사를 수행한다. 새 COS/Codex 클라이언트가 현재 소스에서 catalog를 자동 추출한다. 실행 중인 세션은 시작 시 소스 fingerprint를 유지하므로 변경 후 정상 종료·새 시작이 필요하다. 공유 계약을 우회하지 않는다.

공통 오류 반환 필드인 `status`, `message`, 선택적 `error_code`는 `tool_response.py`에서 구성한다. 각 도구의 JSON 문자열·dict·이미지 반환 방식과 변경 적용·정합 필요 상태는 각 호출부가 유지하며, 공통 오류 필드만으로 rollback 여부를 추정하지 않는다.

## 기능별 구현과 소유권

공개 MCP 도구의 실제 구현은 `features/<기능>/tools.py`에 있다.
배포 검증은 `release_validation/`, 기본·도구별 안내 조회는 `modeling_guidance.py`에 둔다.
자산 생성·변환·출처 기록은 `features/assets/generation/`, 구조해석 검증은 `features/structure/validation/`, 시공 기준 문서 생성은 `features/guidance/`가 소유한다.
이 개발 스크립트들은 공개 MCP 도구 등록 코드와 구분한다.
각 기능의 `register(mcp, context)`는 명시적으로 도구·resource를 등록하고 기존 이름의 함수 dict를 반환한다. `server.py`는 공용 서비스 생성과 정적 factory 조립을 맡는다.
폴더명을 입력받아 SQL이나 모듈을 동적으로 찾거나 실행하지 않는다.

| 폴더 | 분류·성격 | 소유한 구현과 기능 |
|---|---|---|
| [`context`](features/context) | 관찰·진단 | 모델·화면·프로브와 저장소 상태를 조회한다. runtime의 project_info와 COS 연결관리 도구는 각 호스트에 남는다. |
| [`planning`](features/planning) | 작업계획 | Phase·Plan·Step, 참조 대상·자유 관계·evidence·immutable revision과 계획 SQL을 소유한다. |
| [`scenes`](features/scenes) | Scene | 설계 의도와 Scene 장부, 일반 객체의 Scene 참조를 관리한다. |
| [`components`](features/components) | Component | 등록 group의 소유권·계층·조회·동기화, focus·교차 관찰 및 native snapshot 정합과 SQL을 소유한다. |
| [`guidance`](features/guidance) | 설계 참고자료 | 시공 지침·유형 서사·상세자료 후보 탐색과 ConstructionLibrary·HistoryLibrary를 소유한다. |
| [`modeling`](features/modeling) | 모델링·재료 | 실행 도구·모델링 정책·초기 재료 설정·재료 적용과 MaterialLibrary를 소유한다. 공용 native C#·정책 JSON 위치는 유지한다. |
| [`grasshopper`](features/grasshopper) | Grasshopper | GHX 해석·archetype·감사된 capsule 조회/실행, LibraryIndexer와 capsule 색인 SQL을 소유한다. |
| [`assets`](features/assets) | 자산 | 자산 탐색·등록·배치·파생 도면·repository, 공개 resource와 비공개 generated-asset helper, 자산 색인 SQL을 소유한다. |
| [`diagrams`](features/diagrams) | 다이어그램 | 사람·나무·기호 등 벡터/CAD 자산의 조회·검색·메타데이터·배치를 소유한다. 자산 DB와 manifest indexer는 공유한다. |
| [`drawings`](features/drawings) | 도면·Sheet | recipe 색인·표현 스타일·해치 import와 기존 Sheet 자료 보존용 migration을 소유한다. 새 Sheet DB 등록은 제공하지 않는다. |
| [`structure`](features/structure) | 구조검토 | 설계 기준·구조검사·시각화·보고서, 관련 계산·하중·study 모듈과 검사 이력 SQL을 소유한다. |
| [`egress`](features/egress) | 피난검사 | 피난 조건 검사를 소유하고 공용 시공 라이브러리 데이터를 사용한다. |
| [`exchange`](features/exchange) | 외부교환 | GLB·almond.json 교환, 재료·metadata 복원·배치·실측 비교와 Blender helper를 소유한다. |
| [`capture`](features/capture) | 캡처 | conditioning pass 캡처와 이미지 처리를 소유한다. |
| [`publishing`](features/publishing) | 게시 | Chestnut 게시 payload·첨부와 객체 게시 처리를 소유한다. |

### 공개 도구 위치

아래 76개는 package 공개 도구다. runtime의 `project_info`, `set_working_plan`, `rename_artifact_folder`, `execute_project_python`, `get_rhino_execution`을 포함한 입력 catalog는 81개다. 외부 host는 연결관리 도구 4개를 추가해 실제 클라이언트에 85개를 노출한다. 수치는 현재 소스에서 생성한 catalog를 기준으로 한다.

| 기능 | 공개 함수 |
|---|---|
| 관찰·진단 | `get_retrieval_status`, `get_rhino_context`, `analyze_block_reculviely`, `get_rhino_viewport_image`, `get_rhino_objects`, `get_object_intersections`, `capture_rhino_inspection` |
| 작업계획 | `create_phase`, `get_phase`, `list_phases`, `update_phase`, `create_plan`, `get_plan`, `list_plans`, `update_plan`, `list_plan_revisions`, `update_step`, `resolve_targets`, `get_selection_references` |
| Scene | `create_design_scene`, `update_design_scene`, `get_design_scene`, `list_design_scenes`, `get_scene_objects` |
| Component | `upsert_ontological_component`, `get_ontological_component`, `list_ontological_components`, `sync_ontological_component`, `remove_ontological_component`, `get_component_intersections`, `focus_components` |
| 설계 참고자료 | `get_modeling_guide`, `get_construction_guidance`, `get_typology_narrative`, `search_detail_sources` |
| 모델링·재료 | `get_modeling_policy`, `execute_rhino_script`, `save_rhino_document`, `edit_planar_face`, `setup_modeling`, `list_materials`, `assign_material` |
| Grasshopper | `list_library`, `get_logic_by_id`, `list_capsules`, `run_gh_definition` |
| 자산 | `list_drawing_assets`, `search_drawing_assets`, `get_drawing_asset`, `prepare_drawing_asset`, `register_drawing_asset`, `get_asset_drawing`, `generate_asset_drawing_views`, `audit_asset_drawing`, `place_drawing_asset`, `search_asset_repository` |
| 다이어그램 | `list_diagram_assets`, `search_diagram_assets`, `get_diagram_asset`, `place_diagram_asset` |
| 도면·Sheet | `list_drawing_recipes`, `get_drawing_recipe`, `apply_drawing_style`, `import_drawing_hatch_patterns` |
| 구조검토 | `validate_structure`, `list_design_codes`, `visualize_structure`, `export_structural_report` |
| 피난검사 | `check_egress` |
| 외부교환 | `export_asset_contract`, `import_asset_contract`, `get_blender_helper_script` |
| 캡처 | `capture_conditioning_pass` |
| 게시 | `publish_objects_to_chestnut`, `publish_to_chestnut` |

### 공용 서비스와 DB 연결

- `feature_context.py`는 서버별 namespace를 조회한다. 도구가 sender·store를 호출할 때 현재 값을 읽으므로 runtime binding과 테스트 대체 주입이 반영된다. 서버 사이에 feature 전역 상태를 공유하지 않는다. `override`는 ContextVar로 호출별 보고서 경로와 sender를 한정하며 종료 시 복원한다.
- `server.py`는 경로·라이브러리 인스턴스·색인 동기화·MCP 조립과 기존 TCP sender를 유지한다. 라이브러리 초기화의 시점·순서는 기존과 같다. `features/assets/library_index.py`의 `AssetLibraryIndexer`는 drawing·diagram·generated manifest가 공유한다. `paths.py`, `features/assets/asset_passport.py`와 native 모델링 자원도 공용이다.
- `retrieval_store.AlmondStore`는 8개 feature store를 정적으로 합성하는 기존 진입점이다. `_connect`는 작업별 SQLite 연결을 열고 성공 시 commit, 예외 시 rollback, 끝에 close한다. 기초 schema·migration 호출 순서·공용 revision 기반은 여기에 남고 `store_common.py`는 직렬화·시각·공용 예외 identity를 제공한다.
- `assets`, `grasshopper`, `scenes`, `components`, `planning`, `drawings`, `structure`의 `store.py`가 각각 기능의 규칙과 SQL을 소유한다. DB를 기능별로 새로 만들거나 일반 UPSERT 엔진으로 바꾸지 않는다. 한 논리 작업의 검사와 기록은 이전과 같은 연결·transaction에서 실행된다.
- `planning`은 Component reader를 사용한다. `drawings`의 기존 Sheet 연결 자료는 보존하되 Component·Scene 해제를 막는 제약은 제거한다. `scenes`도 component의 객체 소유·관측 helper를 사용한다. 이 호출들은 같은 facade의 명시적 메서드이며 폴더를 파싱하지 않는다.
- Component는 DB 사전검사 → native 변경 → 완전한 snapshot 확인 → DB 기록의 기존 순서를 지킨다. native 실행 후 DB 오류를 Rhino rollback으로 취급하지 않는다.
- `runtime/compat_almond.py`는 외부교환 helper의 보고서를 작업별 디렉터리로 제한한다. factory context override와 기존 module 함수 adapter를 지원하며 현재 sender의 binding·완료 receipt 검증을 유지한다.

### Python 구현 경로와 검증

Python 호출부는 기능별 실제 구현을 직접 import한다. `almond_mcp` 바로 아래에서 다른 모듈을 연결하던 15개 Python 호환 파일은 제공하지 않는다. 외부 Python 소비자도 아래 기능 경로를 사용해야 하며, MCP 도구 이름·schema·resource URI는 그대로다.

| 실제 Python 경로 | 모듈 |
|---|---|
| `almond_mcp.features.modeling` | `modeling_policy`, `modeling_setup` |
| `almond_mcp.features.grasshopper` | `ghx_parser` |
| `almond_mcp.features.assets` | `drawing_assets`, `drafting`, `asset_repository` |
| `almond_mcp.features.capture` | `conditioning` |
| `almond_mcp.features.exchange` | `exchange` |
| `almond_mcp.features.structure` | `native_structure`, `frame_solver`, `ec3`, `floor_loads`, `asset_loads`, `design_codes`, `structure_study` |

예를 들어 `from almond_mcp.features.assets.drafting import load_triangles`로 가져온다.
GHX parser를 직접 실행할 때는 `python -m almond_mcp.features.grasshopper.ghx_parser` 명령을 사용한다. 정책 JSON과 native C#·웹 원본의 공용 자원 위치는 유지한다.
서버의 기존 함수·클래스 이름도 조립 시 re-export한다. 비공개 generated-asset helper를 새 공개 MCP 도구로 노출하지 않고 기존 resource URI·등록을 유지한다.

모듈 검사는 `tests/test_readonly_contracts.py`와 `tests/runtime/`에서 읽기 전용 응답·공유 저장소·환경 분리를 확인한다. 실제 stdio와 외부 연결기 사이의 도구 설명·schema 계약은 루트 `tests/integration/test_stdio_contract.py`가 검사한다. 이 범위는 모든 모델링·계산 기능 또는 실제 Rhino의 Undo/Redo 검증을 대신하지 않는다.
전체 회귀는 `run_tests.ps1`, 호스트·catalog 검사는 COS runner, 모듈 경계·실제 전체 schema·패키징은 루트 통합 검사를 사용한다. 새 기능 파일을 추가하거나 기존 구현을 바꾸면 자동 catalog와 실제 worker의 일치를 검사한다. COS는 새 클라이언트 시작 시 server와 feature factory의 AST에서 schema를 읽으며 서버/DB를 import하지 않는다. package의 모든 Python 파일 목록과 내용이 fingerprint 대상이므로 이동·추가·삭제도 감지한다.

## 실행·관측 계약

연결마다 token·session·call 디렉터리와 프로세스 identity를 확인한다. 모델 폴더의 DB/tmp는 공유하며 저장소 lease·DB 잠금·native 완료 확인을 유지한다.

`get_rhino_context`, `get_rhino_viewport_image`, `analyze_block_reculviely`, `get_rhino_objects`, `get_object_intersections`, `capture_rhino_inspection`은 고정 관찰 경로다.
조회가 geometry·layer·selection·camera·Undo를 바꾸면 안 된다.
`execute_rhino_script`의 `result_error`는 이미 끝난 수정을 취소하지 않는다.
공개 코드 실행은 `execute_rhino_script`와 `execute_project_python` 모두 공식 RhinoCode를 사용한다. Python 3이 기본이며 private Bridge recipe와는 별도 경로다.
내장 스킬·언어·산출물 폴더·완료 조회는 [RhinoCode 실행 계약](runtime/RHINOCODE-SPEC.md)을 따른다.
요청·반환 제한과 미확인 값의 의미는 [관측 계약](rhino/OBSERVATION-SPEC.md)을 따른다.

기존 CoS command를 유지하기 위해 Python 환경은 `../engine/.venv`에 둔다.
구현 위치와 실행 파일 위치는 별개다. 이전 시작 버튼은 호환 스크립트를 거쳐 `runtime/` 실행기를 호출한다. 사용자 모델·라이브러리를 자동 이동하지 않는다.
기존 확장자 없는 `DB`는 아래의 DB 파일명 이전 조건을 충족할 때만 같은 폴더의 `scene.sqlite3`로 바꾼다.

## Scene·Component·계획

Scene·Component의 의미와 작업 방식은 [Rhino 모델링 지침](BASIC-INSTRUCTIONS.md#sceneontological-component)을 따른다. 구현 계약은 [Component 등록·계층·동기화](features/components/SPEC.md)와 [계획 저장·참조](#계획-저장참조)에 둔다. 기존 Room·asset instance 검사의 범위는 [자산 안내](features/assets/SPEC.md#기존-glbscene-배치-장부)에 둔다.

`list_design_scenes`는 Plan이나 live 문서 조회 없이 프로젝트 전체 Scene 이름의 제한된 페이지를 제공한다. Component 목록은 `scene_id`로 범위를 정하고 기본 root/선택적 recursive를 지원한다. `sync_ontological_component`는 기존 단건 호출과 함께 component_ids·Scene·bound 문서 범위를 지원하며 대상 형식을 혼합하지 않는다.

Component는 `component_registry=2`의 문서 private registry를 사용하며 객체에 관리 속성을 새로 기록하지 않는다. 실제 group 이름·멤버가 기준이고 upsert는 기존 group rename·membership 복구를 수행하지 않는다. semantic Undo와 group-table 생성·이름·삭제의 경계는 Component 계약을 따른다.

### 계획 저장·참조

Phase는 Plan의 상위 묶음이고 Plan 안에 Step을 둔다. Plan의 Scene 참조는 맥락, Component 참조는 작업 대상이다. Step도 Component를 지정할 수 있으며, 대상이 Plan의 맥락 Scene에 연결돼 있어야 한다는 제약은 없다.

참조 인자를 생략하면 기존 값을 유지한다. Step의 대상이 `null`이면 Plan 대상을 상속하고, 명시적인 `[]`는 대상 없음이다. 빈 대상을 Plan 전체나 Scene 전체로 확장하지 않는다. `resolve_targets`는 등록 대상을 해석하며 실제 형상 실행과 별개다.

`depends_on`은 참고 관계를 저장하는 JSON 배열이다. 현재 저장소는 자기 참조·순환·미생성 ID를 허용하고 실행 순서나 선행 완료를 강제하지 않는다. 사용자 작업 단위와 도구 사용 기준은 BASIC-INSTRUCTIONS.md를 따른다. 기존 `scene_id`는 `scene_ids`의 첫 항목과 호환된다.

#### 상태와 revision

Phase·Plan·Step 상태는 `pending`, `running`, `paused`, `completed`, `failed`, `blocked`다. 작업을 중단·전환·재개할 수 있으며 선행 작업 완료나 뒤 단계 무효화를 강제하지 않는다.

Plan 변경을 commit할 때마다 전체 Plan 상태를 immutable revision으로 저장한다. `expected_revision`으로 오래된 상태의 수정을 거절하며, 관계·상태·참조 변경과 revision 보관은 같은 DB transaction에서 처리한다. revision은 설계 시도 횟수가 아니며 Rhino 형상을 백업하지 않는다. 기존 Plan에는 migration baseline을 남기되 과거 이력을 만들어내지 않는다.

상태는 `workflow_statuses`를 참조하는 외래 키로 제한한다. scope는 `planning_scopes(scope, template_scope)`를 참조하며 사용자가 추가한 scope는 기존 템플릿 하나를 선택한다. 관계없는 문자열은 SQL에서도 거부한다. 타임스탬프는 UTC 분 단위로 기록하고 revision은 정수로 순서를 보존한다.

#### 파일·작업자료·역조회

Phase와 Scene의 `project_file_id`는 `project_files(file_id, file_name)`을 참조한다. `file_name`은 파일 관계에서 읽어 반환하며 미지정이면 빈 문자열이다. `list_project_files`로 파일명과 선택 가능한 ID를 조회한다. 선택한 Plan의 `artifact_dir`은 프로젝트 `tmp/YYMMDD_name` 아래에 둔다. `artifact_refs`와 Step 입출력 참조는 프로젝트 상대경로다. `set_working_plan`은 폴더를 재사용하고 `rename_artifact_folder`는 현재 참조를 갱신하며 과거 revision을 보존한다.

`get_selection_references`는 선택 객체에서 등록 Component의 조상과 직접·상속된 Plan/Step 참조를 찾는다. 일반 조회는 `include_ids=true`일 때 ID를 포함하며 get 조회는 이미 입력한 대상 ID를 반복하지 않는다.

## 재료·도면·자산

재료 등록·구축 레이어 준비·객체 재료 적용은 MCP가 recipe를 해석하고 공통 native 구현을 호출한다. `assign_material`은 객체 레이어를 유지한다. 세부 recipe·레이어·메타데이터 계약은 [구법 안내](features/guidance/construction-guide.md#재료구축-레이어-구현), 종료된 Sheet 등록과 기존 Layout 보존은 [자산 안내](features/assets/SPEC.md#layoutsheet-호환)를 따른다.

저장소 `asset/`, wheel `almond_mcp/data/`, AppData 라이브러리의 배치는 다르다. 명시적 `RHINO_MCP_*_DIR`이 우선하며 기존 사용자 파일·manifest 상대 경로·계약/모델 해시를 보존한다. 다운로드한 community model과 원시 생성 파일은 기본 패키지에 포함하지 않는다. 자산·도면 도구와 단위·출처 계약은 [자산 안내](features/assets/SPEC.md)를 따른다.

## 지침 Markdown 원본

MCP 도구·리소스의 공개 설명과 응답에 덧붙이는 행동 지침은 원래 Python 파일과 같은 폴더의 `<파일 stem>-explain.md`에 둔다. 예를 들어 `features/modeling/tools.py`는 `features/modeling/tools-explain.md`를 읽는다. 각 항목은 `instruction:` HTML 주석으로 경계를 표시하며, 본문과 동적 값의 공백을 보존한다. `instruction_text.py`가 지침을 읽고 등록 전에 함수 설명에 적용한다. 항목이 없거나 중복되면 명시적으로 실패한다.
입력 검증 조건, 오류 상태·수치 결과, SQL과 실행할 C#/Blender 코드는 지침 원본이 아니다.
기본 작업 지침은 `BASIC-INSTRUCTIONS.md`에 둔다.

COS는 모델 서버를 import하지 않고 같은 Markdown에서 도구 설명을 추출한다.
package와 runtime의 지침 Markdown도 세션 source fingerprint에 포함하므로 변경 후에는 해당 Codex/CoS MCP 또는 Terminal almond 세션을 정상 종료하고 새로 시작한다.
Python 지침만 변경했을 때 Rhino RHP 빌드·등록 변경은 필요하지 않다.

## 조회와 작업자료 계약

`project_info`는 project/document/artifacts를 기본 조회하며 document에서 live 확인을 함께 한다.
`sections`로 runtime/instructions를 포함해 필요한 정보만 고른다. `get_rhino_context`도 document/selection/viewport/editor/display_modes에서 필요한 section을 수집한다. 일반 context에는 compact editor mode·target·stable을 함께 제공하고 명시 editor는 evidence를 추가한다.
선택은 recursive=false·depth=1이 기본이며 include_image=true일 때만 같은 native 호출의 JSON text+현재 PNG를 반환한다. 캡처는 표시모드·transient labels·깊이·view/group/block 대상을 선택하고 Named View는 active view와 별개로 렌더링한다. 상세 한도·오류는 관측 계약을 따른다.
일반 조회는 include_ids=false이고 입력으로 확정된 get 대상 ID는 반복 출력하지 않는다.
필드군을 지원하는 조회는 기본 summary에 필요한 field_groups만 추가하며 IDs와 audit는 독립이다.
오류·불완전·native 완료/proof는 요약으로 숨기지 않는다.

`save_rhino_document()`는 인자 없이 연결된 기존 `.3dm` 전체를 같은 경로에 비대화식 저장한다.
저장되지 않은 문서·readonly·binding 불일치·활성/불명 editor는 쓰기 전에 거절한다.
확인 결과는 saved=true와 실제 modified boolean이고, 결과 불명은 saved=null 및 requires_reconciliation=true다. SaveAs·명령/Enter·자동 재시도·완료 보호 해제는 제공하지 않는다.

Plan depends_on은 다른 Phase의 Plan/Phase ID도 자유롭게 담는 배열이다. 실행 순서·존재·순환 검사를 강제하지 않는다. Step은 paused 상태를 포함하고 중단·전환·재개가 정상 흐름이다.
Phase와 Scene은 미입력 시에도 file_name=""를 보존한다.

ALMOND_PROJECT_ROOT를 런타임이 설정하고 managed 도구가 상대경로를 적용한다.
Plan별 tmp/YYMMDD_name 폴더는 재사용하며 rename_artifact_folder는 현재 참조도 갱신한다.
Python은 별도 호출 scratch와 수명이 제한된 프로세스 트리에서 실행하고 임시 스크립트 파일을 만들지 않는다. 산출물은 선택한 Plan 폴더, 호출 scratch는 `.almond/tmp/python/<token>/<operation>`이다.
로컬 조회는 scratch 폴더를 만들지 않는다. Native 요청은 Bridge 소유권 검증에 필요한 폴더를 전송 직전에 생성하고 완료 확인 후 회수한다. 결과가 불명확한 파일 쓰기는 별도 소유 기록으로 다른 연결의 쓰기·폴더 이름 변경을 차단한다. Worker 재시작이나 Plan 완료로 이 기록을 지우지 않는다.

공유 DB 파일명은 `.almond/scene.sqlite3`다. 기존 확장자 없는 `DB`의 checkpoint·close 뒤 이름을 바꾸며, 다른 worker가 사용 중이거나 두 이름·sidecar가 충돌하면 원본을 보존하고 이전을 중단한다.
호출마다 DB 사본을 만들지 않는다. 종료된 `.sessions` 정리는 프로세스·잠금·native 완료를 기준으로 하며 Plan/Step 상태와 무관하다. 고정 공유 잠금 파일은 삭제하지 않는다.

구형 `.almond/tmp/calls/<token>`에는 작업 보고서·모델·DB 백업이 섞여 있을 수 있다.
파일이 남은 구형 호출 폴더와 세션 locator는 자동 정리에서 제외한다. 기존 프로젝트를 정리할 때는 파일과 DB의 현재 자료 참조를 대조해 보존 자료를 `tmp/YYMMDD_name`으로 옮기고 현재 참조도 함께 갱신한다. 당시 경로를 포함한 과거 revision과 미완료 작업 상태는 유지한다. 이전 완료 후 빈 구형 호출 폴더는 종료된 연결 정리에서 회수한다. 새 scratch와 구형 작업자료를 혼동하지 않는다.

## 모델링 안내 전달

최초 `get_modeling_guide()`는 `BASIC-INSTRUCTIONS.md` 전문과 공통 도구명 목록을 반환한다. `get_modeling_guide(tool="assign_material")`은 해당 공개 도구의 `*-explain.md` 원문을 반환하며 그 도구를 실행하지 않는다. `project_info`의 instructions section도 같은 BASIC을 반환한다.
문서 전용 MCP는 initialize.instructions에 공통 안내를 넣지 않는다. Codex Code Mode가 이 필드를 모든 도구 설명에 반복해서 붙이므로, 최초 BASIC 조회 안내는 `get_modeling_guide`의 짧은 설명에만 둔다. tools/list에는 각 도구의 첫 문장과 호출에 필요한 입력·출력 schema를 제공하고, 상세 절차와 guide_version은 명시적인 안내 조회 응답으로 전달한다. 외부 연결기의 연결 안내와는 별도 계약이다.

reader는 BASIC·등록 도구 소스·설명 원문의 정규화 SHA-256으로 `guide_version`을 계산한다. snapshot 수집 중 변경은 거절하고 외부 source fingerprint·worker schema 검사를 유지한다. 토픽 맵·토픽별 조회·이미지 첨부 인자는 제공하지 않는다. 조회 인자는 정확한 공개 도구명인 tool 하나다. 알 수 없는 이름·파일 경로·URL은 거절하며 조회가 해당 도구를 실행하지 않는다. 공개 도구명은 features/*/tools.py와 runtime/mcp_server.py의 등록 정의에서 정적으로 수집하고 내부 helper는 제외한다. 응답은 status·guide_version·text·source_refs를 가진 JSON text 한 개이며 기본 응답에는 tools, 도구 응답에는 tool_name을 추가한다. source_refs는 패키지 상대 경로와 정규화 SHA-256이다.

reader는 모델·작업 DB·사용자 산출물을 읽거나 수정하지 않는다. 연결된 호출은 기존 binding·공유 잠금·operation receipt를 거치며 외부 연결기에서는 connection_id가 필요하다. BASIC의 참고자료는 직접 링크로 읽고 별도 가이드 payload를 생성하지 않는다. runtime을 포함한 체크아웃은 runtime 도구 설명도 수집하며, runtime이 제외된 standalone wheel은 설치된 공통 도구만 수집한다. 안내 검사는 원문 일치·이름 목록·버전·변경 감지와 cold stdio 초기화, runtime 없는 배포 레이아웃의 서버 초기화를 확인한다.

문서·도구 설명 변경은 해당 Python/MCP 세션을 정상 종료하고 새로 시작해야 적용된다. Python 안내 변경만으로 RHP 빌드나 Rhino 재시작을 요구하지 않는다.

## Public query and write responses

See [QUERY_OUTPUT.md](QUERY_OUTPUT.md) for summary defaults, explicit field groups, independent ID/audit selection, compact write acknowledgements and project-wide Scene discovery.


## 프로필 원본과 도구 설명 표시

- 내장 원본은 `profiles/eurocode.json`, `profiles/construction_system/manifest.json`, `profiles/material/manifest.json`이다. 재료·구조 시스템 로더는 각 폴더의 `manifest.json`을 읽는다. 설계 기준 검색은 `profiles` 바로 아래 JSON만 읽으므로 하위 manifest와 섞이지 않는다.
- 명시적인 `RHINO_MCP_*_DIR`, `ALMOND_DESIGN_CODE_DIR` 및 일상 실행의 AppData 경로와 기존 파일은 보존한다. 개발 체크아웃과 오프라인 환경만 새 원본 위치를 사용한다. wheel은 `profiles`의 원본을 포함하고 최초 배치 시 기존 AppData `Materialfiles`, `Constructionfiles` 폴더로 누락된 파일만 복사한다.
- `features/assets/asset_passport.py`와 `library_index.py`는 자산 전용 구현이다. 서버·CLI·생성기·배포 도구는 이 위치를 직접 가져온다.
- MCP 도구 목록에는 설명의 첫 문장만 표시한다. 상세 사용법은 인접한 `*-explain.md`에 유지하고 명시적으로 조회한다. Args의 인자별 의미는 입력 schema에 반영하며 입출력 형식은 함수 타입·등록 schema를 따른다. 전체 작업 지침은 도구 설명에 자동 삽입하지 않는다.
- 외부 연결기는 프로필 JSON도 source fingerprint에 포함한다. 프로필이나 설명을 바꾼 뒤에는 해당 클라이언트/세션을 정상 종료하고 새로 시작한다.

## 공개 component 이름과 기존 데이터 호환

room·scene instance 관리 및 AABB 충돌 검사인 validate_scene_layout은 공개 API로 제공하지 않는다. Scene 조회도 rooms/instances 항목을 반환하지 않는다. 구조 하중은 실제 Rhino 자산 배치만 사용하며 scene_id 장부 인자는 제거한다. 기존 DB의 rooms/instances 및 revision 기록은 삭제하거나 변환하지 않고 보존한다.

공개 API는 upsert/get/list/sync/remove_ontological_component(s) 이름을 사용하며 design_component 도구 별칭은 제공하지 않는다. 기존 Bridge와 통신하는 내부 design_component request/capability 태그는 호환을 위해 유지한다. 이는 공개 도구 이름이 아니며 DB·Undo·native 계약을 변경하지 않는다.
