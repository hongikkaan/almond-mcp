---
name: rhino-almond
description: "Inspect and edit Rhino architecture with Almond MCP: project context, Phase/Task/Step, Scene/ontological-component, modeling, drafting, and verification."
---

# Rhino Almond

Almond MCP를 사용해 Rhino 건축 모델과 도면을 조사·편집한다. 아래 도구명은 공통 이름이며 연결 방식에 따라 필요한 인자가 다를 수 있다. 실제 호출은 현재 연결의 schema를 따른다.

최초 사용 시 `get_modeling_guide()`로 이 문서 전문과 조회 가능한 도구명을 읽는다. 같은 `guide_version`에서 이미 읽은 지침은 재사용한다.

개별 도구의 사용법이 불확실하면 `get_modeling_guide(tool="assign_material")`처럼 정확한 도구명으로 설명을 조회한다. 이 조회는 해당 도구를 실행하지 않는다. 입력 형식과 기본값은 현재 연결의 schema를 따르고, 작업의 판단 기준과 도구를 사용하는 맥락은 이 문서를 따른다.

## 목차

- [기본 세팅](#기본-세팅)
  - [템플릿·재료·구축 레이어](#템플릿재료구축-레이어)
- [조회 도구](#조회-도구)
- [프로젝트 기본 구조](#프로젝트-기본-구조)
  - [프로젝트·문서·파일](#프로젝트문서파일)
  - [Phase → Task → Step](#phase--task--step)
  - [Scene·ontological-component](#sceneontological-component)
- [모델링](#모델링)
  - [건축물을 모델로 다루기](#건축물을-모델로-다루기)
  - [텍토닉: 재료와 구성, 접합](#텍토닉-재료와-구성-접합)
    - [구축 시스템과 표현 단계](#구축-시스템과-표현-단계)
  - [구성의 발전과 형상 편집](#구성의-발전과-형상-편집)
  - [객체들의 묶음 단위 유형](#객체들의-묶음-단위-유형)
  - [모델링 검수](#모델링-검수)
- [편집 범위의 격리와 내부 조회](#편집-범위의-격리와-내부-조회)
- [Drafting](#drafting)
  - [도면을 공간과 의미로 읽기](#도면을-공간과-의미로-읽기)
  - [설계와 도면의 발전](#설계와-도면의-발전)
  - [도면 생성 툴](#도면-생성-툴)
  - [Layout 생성 및 관리](#layout-생성-및-관리)
  - [도면 표현·출력 검수](#도면-표현출력-검수)
- [구조 검토](#구조-검토)
- [거의 사용하지 않는 기능](#거의-사용하지-않는-기능)

## 기본 세팅

### 템플릿·재료·구축 레이어

재료·구축 레이어를 준비할 때 `setup_modeling(operation="materials", overwrite=false)`로 기존 동명 재료를 유지하며 재료를 등록하고, `setup_modeling(operation="layers")`로 레이어를 생성·재사용한다. 이미 세팅된 문서에서는 필요한 부분만 보완한다.

레이어는 `M::유형::시스템명::요소역할` 구조이며, 시스템·요소 레이어에는 재료와 표시·출력 색이 설정된다. 모델링한 객체를 해당 레이어에 배치하고 재료·색을 ByLayer로 적용한다.

## 조회 도구

MCP의 관찰·캡처로 필요한 정보를 확인하며 computer use를 검증의 우회 수단으로 호출하지 않는다. 형상과 속성, 화면, 현재 편집 상태는 서로 다른 정보를 주므로 이번 판단에 필요한 관찰을 선택한다.

객체 집합은 `get_rhino_objects`로 조회한다. 레이어·형상 유형별 요약으로 범위를 파악하고, `fields`로 ID나 필요한 속성만 받을 수 있다. 면 정보와 교차검사 결과가 나뉘어 반환되면 응답의 후속 조회 정보를 사용한다.

### get_rhino_context: 문서·선택·화면·편집 상태
필요한 `sections`를 함께 요청한다. 기본값은 `["document"]`이며, `project_info`에서 이미 현재 문서를 확인했다면 같은 확인을 반복하지 않는다. 이 조회는 모델을 변경하지 않는다.

| 입력 | 할 수 있는 일 |
| --- | --- |
| `sections`: document, selection, viewport, editor, display_modes | 문서 경로·단위·공차와 객체·레이어 수, 선택 요약, 화면의 카메라·표시 정보 등을 필요한 범위로 조회한다. `editor`는 편집 상태의 근거·경고를, `display_modes`는 설치된 표시 모드를 제공한다. |
| `selection_limit`, `recursive`, `depth` | 선택 객체 요약은 기본 최대 50개, `selection_limit`은 0–200이다. 기본 비재귀 조회는 완전히 선택된 최상위 group·block을 요약하며, `recursive=true`는 `depth=1–8` 범위의 내부 멤버를 펼친다. 일부만 선택된 group은 객체 선택으로 남는다. |
| `include_image`, `include_ids` | 기본은 이미지와 ID를 제외한다. `include_image=true`는 같은 호출에서 현재 화면 PNG를 반환하며 실패 시 `image_error`와 조회 가능한 상태를 반환한다. 후속 작업에 ID가 필요하면 `include_ids=true`를 지정한다. |

document·selection·viewport 조회에도 간략한 편집 모드·대상·안정 상태가 포함된다. 일반 모델 편집 상태가 확인된 경우에만 안정 상태이며, 격리 편집·전환 중이거나 확인할 수 없으면 불안정하다. `unknown`과 `null`은 미확인이므로 선택 상태만으로 편집 대상을 추정하지 않는다. 객체 수나 현재 화면만으로 형상·가시성을 검증할 수는 없다.

### get_selection_references: 선택 객체의 등록 관계

현재 Rhino 선택에서 등록된 ontological-component와 관련 Task·Step의 이름과 ID를 한 번에 역조회한다. 선택 자체는 실시간으로 읽고, 관계는 등록 정보를 기준으로 한다. 직접 지정된 Step 대상과 Task에서 상속된 대상을 구분하며, component의 조상도 포함한다. Scene 맥락만으로 대상 관계를 만들지는 않는다.

`selection_limit`은 조회할 선택 객체 수(기본 50, 1–200), `limit`은 관계 결과 수를 제한한다. 미등록 객체와 선택·Task 결과의 잘림 여부를 확인하고, 결과가 잘렸다면 범위를 나눠 조회한다. 이 도구는 명시적 ID 역조회이므로 ID를 반환한다. 추가 상세는 `field_groups`로 요청한다.

### get_rhino_viewport_image: 화면으로 관찰하기

현재 화면이나 저장된 viewport·Named View·Layout을 활성화하지 않고 PNG로 확인한다. `view="a"`는 이미지 대신 각각의 이름과 GUID 목록을 반환한다. 이름은 중복될 수 있으므로 목록에서 GUID를 골라 `view`에 전달한다.

**Viewport:** `view`를 생략하면 활성 화면을 캡처하고, 목록의 viewport GUID를 지정하면 해당 화면을 캡처한다. 현재 모델 viewport의 표시 모드는 기본적으로 유지한다.

**Named View:** 목록의 GUID를 지정하면 저장된 카메라를 별도 화면에서 렌더링한다. 기본 표시 모드는 Shaded이고, 저장된 픽셀 크기가 없으면 현재 viewport 크기를 사용한다. 보이는 화면의 카메라는 바뀌지 않는다.

**Layout:** 목록의 GUID를 지정하면 Detail을 포함한 용지 영역을 이미지로 확인한다. 활성 화면이 Layout이면 Detail 편집 중에도 용지 영역을 캡처한다. `scale_percent=100`은 용지를 96 dpi로 출력한다. Detail별 표시 모드는 유지되며 표시 모드 변경은 거절하고 Detail 라벨은 지원하지 않는다.

**Group·block:** `view`를 비우고 `target_kind="group"` 또는 `"block"`과 `target_id`를 지정한다. 대상은 각각 영속 group GUID 또는 최상위 block instance GUID이며, block 정의 GUID는 대상이 아니다. 별도 화면에서 대상 범위를 확대하고 주변 형상도 표시한다. 기본 표시 모드는 Shaded다.

도면·유닛의 위치나 작업 시점이 불명확하면 질문 전에 기존 Named View·Layout을 찾고, 선택한 GUID의 이미지에서 표제와 실제 대상·주변 관계를 대조한다. 이름만으로 범위를 확정하거나 조회를 위해 새 Named View를 만들지 않는다.

절단면으로 내부를 확인하려면 실제 clipping plane을 설정한다. 캡처의 `display_mode`는 표시 모드만 바꾸며 모델을 절단하지 않는다.

**공통 옵션:** `display_mode`는 `get_rhino_context(sections=["display_modes"], include_ids=true)`로 설치된 이름 또는 GUID를 확인해 지정한다. Raytraced 같은 실시간 렌더링 모드는 지원하지 않는다. `scale_percent`는 1–100이며 기본 75, 도면 검수에는 100을 사용한다. 픽셀 크기만 조절하며 Layout Detail의 도면 축척은 바꾸지 않는다. 16메가픽셀·4 MiB 제한을 초과하면 자동 축소하지 않고 오류를 반환하므로 비율을 낮춰 다시 요청한다.

`labels=true`가 기본이다. 최상위 group 이름·GUID, block instance 이름·GUID와 group에 속하지 않은 객체 GUID를 이미지에 표시하며 Rhino 객체를 만들지 않는다. 최대 200개이며 `depth=1–8`로 중첩 라벨 범위를 조절한다. 라벨이 잘리면 대상이나 깊이를 좁힌다. `include_usage=true`는 이미지 크기와 참고용 토큰 추정치를 추가하며 실제 사용량은 클라이언트에 따라 다르다.

## 프로젝트 기본 구조

### 프로젝트·문서·파일

같은 폴더의 여러 `.3dm`이 하나의 프로젝트이며 `.almond/scene.sqlite3`를 공유한다. **Rhino 편집 대상은 활성 문서만**이다. Worksession의 attached/reference 문서는 조회만 한다.

프로젝트·현재 파일은 `project_info`로 확인한다. DB 기록은 도구가 저장하고, 작업자료는 Task를 선택하면 `tmp/YYMMDD_작업명`에 관리된다. 관리 도구에는 프로젝트 상대경로를 전달하면 되므로 TEMP나 절대경로를 따로 조립하지 않는다. Rhino 모델의 `.3dm` 저장은 DB 기록과 별개다. 저장 명령 성공, 저장 후 `modified` 표시, 실제 저장본 확인은 구별한다. 표시가 남으면 저장 이후 변경·미확인 상태를 보고하고 표시를 강제로 지우지 않는다.

이미 확인한 문서 상태는 재사용한다. 최초 연결·재연결, 문서 변경의 증거, 프로젝트·경로 맥락의 누락 또는 사용자 요청이 있을 때 필요한 `project_info` sections만 다시 조회한다.

| 도구 | 입력 | 할 수 있는 일 |
| ------- | ----- | ----- |
| `project_info` | 필요한 `sections`: project, document, artifacts, runtime, instructions | 프로젝트 루트·파일명·공유 DB·현재 문서·작업자료 위치 조회. document에 live 확인이 포함된다. |
| `save_rhino_document` | 없음 | 연결된 기존 `.3dm`을 같은 경로에 비대화식 저장. `saved=null`이면 완료 불명이므로 재시도 전에 실제 결과를 확인한다. |
| `rename_artifact_folder` | `name`, 선택적 `plan_id` | 작업자료 폴더와 관련 참조를 함께 변경. |
| `execute_project_python` | `code`, 선택적 `timeout_seconds` | 선택한 작업자료 폴더를 cwd로 하여 RhinoCode Python 3 실행. RhinoCommon과 연결된 doc 사용 가능. |
| `execute_rhino_script`| `script`, 선택적 `language`, `timeout_seconds` | RhinoCode로 형상·속성 편집 또는 계산. 기본 Python 3, Python 2, C# statement body, command 지원. 도구 설명에 내장 rhino3d-scripts 자료가 포함된다. |

### Phase → Task → Step

**Phase는 작업 묶음, Task는 과업, Step은 과업의 단계**다. API에서는 Task를 `Plan`, 그 ID를 `plan_id`라고 한다. 상태는 `pending`, `running`, `paused`, `completed`, `failed`, `blocked`다.

새 지시가 기존 Task의 연속이면 해당 Task를 재사용하고, 다른 과업이면 관련 Task를 선택·생성한다. 부족한 맥락만 조회하며 일회성 조회에는 새 Task를 만들지 않는다. 요청한 실행과 필요한 검수가 끝나면 완료로 판단한다.

Task의 상위 Phase는 `phase_id`로 지정한다. 관련 Task는 `depends_on` 배열에 기록하고, 관련 Phase는 전용 관계 필드가 없으므로 Phase의 `description`에 ID를 적는다. 다른 파일에 속한 항목도 참조할 수 있다. 관계는 참고 정보이며 실행 순서나 자동 완료를 강제하지 않는다.

| 도구 | 입력 | 할 수 있는 일 |
| ----- | ----- | ----- |
| `list_phases` | 선택적 `limit` | 프로젝트의 Phase 목록 조회. |
| `get_phase` | `phase_id`, 선택적 `field_groups`, `include_ids` | Phase 이름·소속 Task 수 조회. 설명은 `description`, 파일명은 `scope` 필드 그룹으로 요청. |
| `create_phase`  | `name`, 선택적 `description`, `file_name`, `project_file_id`, `status` | Phase 생성. |
| `update_phase`  | `phase_id`, 바꿀 `name`, `description`, `file_name`, `project_file_id`, `status` | Phase 정보 수정. |
| `list_plans` | 선택적 `phase_id`, `scene_id`, `status`, `limit` | Phase·Scene·상태로 범위를 좁혀 Task 요약 조회. ID는 `include_ids=true`로 요청한다. |
| `get_plan`| `plan_id`, 선택적 `revision`, `field_groups`, `include_ids` | Task 요약 또는 저장 revision 조회. Step은 `field_groups=["steps"]`, 대상 관계는 `["references"]`, 작업자료는 `["artifacts"]`로 요청한다. 일반 조회의 `field_groups` 생략·`[]`은 요약, `all`은 전체 상세, `audit`은 기술 timestamp다. |
| `set_working_plan` | 선택할 Task의 `plan_id`, 선택적 `step_id`, 최초 폴더 이름 `artifact_name` | 연결에서 Task·Step과 작업자료 폴더를 선택·재사용한다. 이름을 생략하면 Task 목표로 폴더를 정한다. |
| `create_plan`| Task 목표 `goal`, 선택적 `scope`, `phase_id`, 맥락 `scene_id` 또는 `scene_ids`, 편집 대상 `component_ids`, 관련 `depends_on` | Task와 기본 Step 생성. scope는 house, interior, structure, drawing, component. |
| `update_plan`| `plan_id`, 바꿀 목표·참조·상태·`artifact_refs`, `expected_revision` | Task 정보와 상태 수정. 조회한 revision을 전달해 오래된 수정의 충돌을 막는다. |
| `update_step`| `plan_id`, `step_id`, `status`, 선택적 입출력 참조·대상, `expected_revision` | Step의 의미 있는 진행·중단·결과를 기록한다. 대상 `null`은 Task 상속, `[]`는 대상 없음이다. |
| `resolve_targets`  | `plan_id`, 선택적 `step_id` | Task 또는 Step이 가리키는 ontological-component·문서·group 확인. |
| `list_plan_revisions` | `plan_id`, 선택적 `limit` | Task의 저장된 변경 이력 조회. |

파일 관계는 `project_files`의 파일명과 UUID를 사용한다. `list_project_files(include_ids=true)`에서 파일 ID를 조회하고 Scene·Phase의 `project_file_id`에 넣는다. 같은 이름이 여러 개면 ID를 지정한다. `file_name`에는 폴더 없이 `ddd.3dm`처럼 파일명만 넣으며 빈 문자열로 관계를 해제한다. 실제 파일 이동·이름 변경은 수행하지 않는다.

Phase·Task·Step의 상태는 pending, running, completed, failed, blocked, paused 중 선택한다. DB의 `workflow_statuses` 관계로 같은 선택지를 제한한다. scope는 `planning_scopes` 관계이며 기본값 외에 새 이름을 추가할 때 `template_scope`를 house/interior/structure/drawing/component 중 하나로 지정한다. 예: scope=facade, template_scope=component. 이름을 추가해도 실행 권한이나 새로운 모델링 도구가 생기지는 않는다. 장부 시간은 UTC 분 단위이며 revision으로 같은 분 안의 변경 순서를 구분한다.

### Scene·ontological-component

Scene은 행태·프로그램·장면의 맥락이고, ontological-component는 그 장면을 가능하게 하는 건축 요소와 의미의 묶음이다. ontological-component는 여러 Scene에 참여할 수 있다. 개별 객체는 DB에 등록하지 않는다. Scene은 ontological-component를 통해 현재 Rhino 객체를 조회한다.

#### Scene

Scene은 특정 공간에서 일어나는 **행태·프로그램·장면·가치**다. 파일 전체를 Scene 하나로 치환하지 않는다. Scene의 `file_name`을 필요할 때 조회해 현재 활성 파일과 대조한다. 이 필드는 작업 문서의 안내 정보이며 파일을 이동하거나 문서를 자동 전환하지 않는다.

| 도구 | 입력 | 할 수 있는 일 |
| -- | ----- | --- |
| `list_design_scenes` | 선택적 `name` 부분검색, `file_name` 정확한 파일명, `limit`, `offset`, `field_groups`, `include_ids` | 프로젝트 전체 Scene 목록. 기본은 이름만 반환하며 `include_ids=true`로 ID, `field_groups=["scope"]`로 파일명·단위를 추가한다. |
| `get_design_scene` | `scene_id`, 선택적 `field_groups`, `include_ids` | Scene 요약 조회. 파일명·단위는 `scope`, revision은 `state` 필드 그룹으로 요청. |
| `create_design_scene` | `name`, 선택적 `units`, `file_name`, `project_file_id` | Scene 생성. |
| `update_design_scene` | `scene_id`, `file_name` 또는 `project_file_id` | 기존 Scene의 파일 관계 변경. |
| `get_scene_objects`| `scene_id`, 선택적 `limit`, `offset`, `field_groups`, `include_ids`, `expected_model_path` | 현재 Rhino에서 Scene의 ontological-component 멤버를 읽기 전용으로 조회. 개별 객체는 DB에 저장하지 않는다. |

목록과 객체 페이지의 limit은 1–200이다. Scene 삭제 도구는 없으며 등록 정보 변경에는 공개 도구를 사용한다.

#### ontological-component

ontological-component는 **건축 요소와, 그 요소들이 함께 가능하게 하는 사용·행태·구조적 역할을 묶은 의미 단위**다. 무엇을 만들었는지와 그 묶음이 무엇을 가능하게 하는지를 함께 설명할 수 있어야 한다. 객체 종류·재료·거리만으로 경계를 정하지 않는다. 예를 들어 창문 하나를 일률적으로 ontological-component로 등록하는 대신, 바깥 풍경을 보며 머무르는 장소를 만드는 벽·창문 등의 관계를 보고 묶는다.

##### 예시(중요)

###### 1. 마루와 계단참

![마루·계단참·지지 구조·가구의 공간 관계](features/guidance/guides/references/assets/resident-porch.png)

작은 계단참과 마루에서 사람들이 머물고 교류하는 행태가 Scene이다. 그 Scene을 이루는 ontological-component는 다음처럼 **실물 구성과 그것이 가능하게 하는 것**을 함께 갖는다.

| ontological-component | 함께 구성하는 요소와 의미 |
|---|---|
| 마루 위 공간을 지지하는 구조 | 기둥·보 여러 개가 함께 위에서 오는 하중을 지지한다. 기둥마다 따로 등록하지 않는다. |
| 사람들이 걸터앉는 마루·계단참 | 지지 콘크리트와 마루 마감이 함께 단차와 앉을 자리를 만든다. 마루라는 실물이면서 걸터앉을 수 있게 하는 장치다. 공유 바닥슬래브 전체를 포함할 필요는 없다. |
| 마루에서 바둑 두는 가구 묶음 | 방석·낮은 탁자·바둑판·바둑알과 통·시계 등이 함께 앉아서 바둑 두는 행위를 가능하게 하고 유도한다. 가구 하나씩 나누지 않고, 그 행위와 사용 관계로 묶는다. |

###### 2. 지붕과 우수관

![지붕과 우수관](features/guidance/guides/references/assets/roof-drainage.png)

지붕의 의미에는 덮는 역할과 함께 집수·배수가 이어진다. 우수관이 여러 층을 지나거나 기둥 속 콘크리트에 매립돼 있어도 그 역할이 이어지므로 지붕 ontological-component에 포함한다. 지붕 안의 구축 시스템과 우수관 element들은 일반 group으로 나눠 관리할 수 있다. **물리적으로 떨어져 있어도 하나의 역할을 이루면 같은 ontological-component가 될 수 있다.** 두 사례의 [사용자 설명 원문과 사진](features/guidance/guides/references/component-feedback.md)은 별도로 보존한다.

##### 등록·관리 도구

의미 단위를 이루는 객체들을 한 `.3dm`의 Rhino group으로 정의해 ontological-component로 등록한다. 일반 group이 자동으로 ontological-component가 되는 것은 아니다. 내부 구축 시스템·부재는 편집 목적에 따라 일반 group이나 block으로 정리한다.

| 도구 | 입력 | 할 수 있는 일 |
| --- | --- | --- |
| `list_ontological_components`  | 선택적 `scene_id`, `recursive`, `field_groups`, `include_ids` | 지정 Scene 또는 연결 문서의 등록 root 목록 조회. `recursive=true`로 등록 자손도 포함한다. |
| `get_ontological_component` | `component_id`, 선택적 `live`, `recursive`, `field_groups`, `include_ids` | 저장 요약 조회. 실제 group은 `live=true`, 형상은 `field_groups=["geometry"]`로 요청한다. |
| `upsert_ontological_component` | `name`, 직접 소유 `object_ids`, 선택적 `scene_ids`·기존 ID·group GUID·`child_component_ids` | ontological-component 생성·구성 변경·기존 group 채택. 신규 등록에는 Scene이 필요하다. |
| `sync_ontological_component`| `component_id`, `component_ids`, `scene_id` 중 선택; `component_id` 지정 시 선택적 `rhino_group_id`; 대상 생략 시 연결 문서 | 실제 group에 맞춰 선택 범위의 멤버십·등록 정보를 정합. |
| `remove_ontological_component` | `component_id` | ontological-component 등록 해제. 형상과 group은 유지. |

등록은 현재 Rhino group의 이름·멤버를 기준으로 하며, 부모 group이 자손 객체를 포함해도 직접 소유권은 자식에 남는다. 등록 해제와 group/block 해체는 별개다. 등록·구성 변경의 입력과 제약은 해당 도구 설명을 따른다.

실제 편집 상태가 필요하면 DB 요약 대신 live 조회를 사용한다. 수동 편집·멤버 교체·Undo/Redo 뒤에는 group/block 편집을 마치고 문서가 안정됐을 때 영향받은 등록 범위를 한 번 sync하며, 결과의 문제·미확인 항목을 확인한다. 이름·색 변경만으로 멤버십 정합을 반복하지 않는다.

등록과 sync는 형상·멤버십 복구 도구가 아니며, 등록의 Undo도 Rhino group-table의 생성·이름 변경·삭제를 모두 되돌리지는 않는다. 재편·복구는 현재 Rhino 상태와 공개 도구의 지원 범위를 확인해 진행하고, DB나 소유권 UserString을 직접 고쳐 우회하지 않는다.

## 모델링

### 건축물을 모델로 다루기

건축 모델링은 공간을 이루는 물질적 구성을 설계하고 구체화하는 일이다. 모델에서 부재와 재료가 차지하는 부분, 그 사이에 생기는 공간, 공간을 연결하거나 나누는 경계를 함께 읽는다. 형상의 크기·두께·방향·배치는 사람이 머물고 움직이는 방식과 빛·시선·환경을 받아들이는 조건을 만든다. 형상을 수정할 때는 그 변화가 어떤 공간과 사용을 가능하게 하고 무엇을 어렵게 하는지 판단한다.

모델의 요소는 건축물 안에서 서로 역할을 주고받는다. 한 요소가 여러 공간을 형성하거나 다른 요소를 지지할 수 있고, 떨어진 요소들이 하나의 기능을 함께 수행할 수도 있다. 따라서 요소의 이름이나 현재 묶음만으로 역할을 확정하지 않고, 어디에 놓여 무엇과 연결되며 어떤 구성에 참여하는지 해석한다. 과업의 규모에 따라 이 관계를 실내에서 건축물 전체와 주변 환경까지 연결해 이해한다.

Rhino 객체는 이 건축을 표현하는 편집 단위다. 하나의 실물 부재가 여러 객체로 나뉘거나 하나의 객체가 복합적인 구성을 단순화해 나타낼 수 있다. 모델을 읽을 때는 형상이 무엇을 나타내는지와 실제로 어느 정도까지 구체화돼 있는지를 구별한다. 분할된 객체 사이의 경계와 실물의 이음, 모델에 생긴 빈틈과 의도한 공간은 그 의미를 확인해야 구분할 수 있다.

### 텍토닉: 재료와 구성, 접합

텍토닉은 재료의 성질과 부재의 구성·결합이 건축의 공간과 표현을 성립시키는 방식이다. 재료의 물성과 가공 방식, 부재를 만들고 조립하는 순서는 가능한 형상·치수·접합을 제약한다. 요소를 이해할 때는 이 조건 속에서 부재가 무엇을 받치거나 감싸며, 힘과 기능이 다른 요소로 어떻게 이어지는지 읽는다. 실제 역할과 만드는 방식이 부재의 구분과 연결을 판단하는 근거다.

접합부에는 요소 사이의 의존 관계가 드러난다. 연속돼야 할 부분, 힘이나 기능을 넘겨받는 부분, 서로 움직이거나 교체할 수 있도록 분리할 부분은 서로 다른 구성을 요구한다. 맞닿음·겹침·틈은 이 관계를 표현하는 기하 상태이므로, 각각이 재료·시공·사용 조건에 맞는지 판단한다. 모델에서 면이 맞거나 솔리드가 닫혔다는 사실과, 실제로 조립되고 역할을 수행할 수 있다는 판단은 별도의 근거를 갖는다.

공간과 구축은 함께 발전한다. 부재의 위치와 깊이, 재료의 두께, 접합과 지지 방식은 공간의 여유·개방감·경계의 성질을 바꾸고, 원하는 공간은 다시 구성 방식의 선택에 영향을 준다. 현재 설계 단계에서 판단하려는 내용에 맞춰 형상을 구체화한다. 단순화한 표현으로 남긴 구성과 실제 상세를 결정한 부분을 구별하고, 상세를 추가할 때는 전체 구성과의 관계를 이어 간다.

#### 구축 시스템과 표현 단계

구축 레이어에서 유형 레이어는 시스템 미정, 시스템명 레이어는 시스템이 정해진 단순화 표현, 요소역할 하위 레이어는 부재·마감의 상세 표현에 쓴다.

시스템명 레이어의 단순 형상을 상세화할 때는 `get_construction_guidance(query="시스템명", field_groups=["rules"])`로 요소 역할·재료·간격·초기 치수·구성 메모를 조회한다. 검색 결과의 시스템명을 대조하고, 모델의 지지·경계·접합 조건에 맞춰 부재·마감을 구체화해 기존 요소역할 레이어에 배치한다. 접합 상세의 참고 출처가 필요하면 `search_detail_sources`를 사용한다.

함께 조립·편집할 하나의 구축 구성을 group으로 묶는 것을 권장한다.

### 구성의 발전과 형상 편집

사용자의 목표와 기존 모델·도면·피드백을 함께 읽고, 이어 가야 할 설계 의도와 바꿀 수 있는 조건을 파악한다. 기존 구성의 역할을 해석한 뒤 보완할 지점을 찾으며, 특정 요소에 대한 피드백도 그 요소가 참여하는 공간과 구축의 관계 안에서 이해한다.

수정할 객체의 범위는 판단하려는 건축 요소와 변경의 영향에서 정한다. 한 요소가 여러 객체에 걸쳐 있으면 그 전체의 형상과 연결을 이해하고, 주변 요소와의 관계가 문제라면 그 관계를 함께 살핀다. 격리나 분류는 이 판단을 돕는 관찰 방법이다. 과업이 달라졌을 때는 앞서 사용한 작업 구획을 이어 쓰기 전에 이번 판단에 필요한 관계가 그 안에 드러나는지 살핀다.

구성을 고칠 때는 현재 방식으로 의도한 역할이 성립하는지 고찰하고, 필요한 경우 부재의 구성·접합·배치나 공간 조직의 대안을 모색한다. 각 대안이 사용자의 의도, 공간 경험, 구축의 성립에 주는 이점과 제약을 비교한다. 형상을 정돈하는 것으로 해소되는 문제와 구성 방식 자체를 바꿔야 하는 문제를 구별해 사용자가 정한 조건 안에서 발전시킨다. 중요한 설계 선택이 불확실하면 대안의 차이와 영향을 설명한다.

실현할 변화가 정해지면 그에 맞는 형상 연산을 선택한다. 이동·면 편집·절단·결합·재구성은 부재와 공간의 관계를 구현하는 수단이다. 연산으로 경계가 사라지거나 객체가 나뉠 때 실제로 연속시킬 부분과 별도 부재로 남길 부분이 현재 표현 목적에 맞게 유지되는지 판단한다. 바뀐 형상에 맞춰 관련 구성과 속성·묶음도 정합하며, 기존 형상을 활용할지 새로 구성할지는 보존해야 할 내용과 필요한 변화에 따라 정한다.

### 객체들의 묶음 단위 유형

함께 다룰 구성과 변경을 공유할 범위에 따라 group과 block을 선택·조합한다. Group은 개별 객체와 재귀적 묶음을 유지하고, group 자체는 복사본 사이에 변경을 전파하지 않는다. 한 객체가 여러 group에 속할 수 있으므로 중첩과 멤버 중복을 구분한다. Block은 definition을 공유하는 instance의 배치로, 각 배치의 위치·회전·축척은 개별적이고 정의 변경은 공유 배치에 반영된다. 일부 배치의 구성만 달라져야 하면 정의를 분리한다. 중첩 block은 보존되지만 일반 group의 묶음 관계는 block definition 내부에 보존되지 않으며, 바깥 group을 복사해도 내부 block은 정의를 공유한다. 묶음을 전환·해체·재조립할 때는 개별화할 형상과 남길 하위 구성, 변경이 전파될 배치를 구분한다.

#### BlockEditNew에서 편집 범위를 다루기

BlockEditNew에서는 뷰포트에서 선택한 group이나 block instance를 열고, 중첩 구성의 필요한 단계로 들어가 편집한다. Group 편집은 묶음의 구성원들을 다루는 작업이고, block 편집은 선택한 배치를 통해 공유 정의의 내용을 고치는 작업이다. Block을 열었을 때 화면에서 선택 가능한 작업 객체는 저장된 definition 내부 객체와 같은 식별 대상이 아니다. 정의 내부 GUID와 현재 편집 객체의 ID를 구분하고, 편집 진입·완료·재구성 뒤에는 대상을 다시 조회한다. 정의와 배치 변환은 이때 어떤 구성과 위치를 편집하는지 연결하는 근거가 된다.

격리된 부분에서는 부재의 형상과 내부 구성을 읽기 쉽고, 그 부분이 전체에서 맡는 역할은 주변 관계 속에서 판단할 수 있다. 검토할 관계에 맞춰 편집 깊이와 관찰 범위를 선택하고, 부분의 변경이 끝나면 영향을 받는 상위 구성과 공유 배치에서 결과를 확인한다. 중첩 단계 밖의 선택·표시 상태를 임의로 재설정해 현재 편집 맥락을 잃지 않도록 한다. 실제 편집 상태는 `get_rhino_context(sections=["editor"])`, 블록의 중첩 경로와 현재 선택 가능한 블록 후보는 `analyze_block_reculviely`로 확인할 수 있다.

묶음을 별도의 의미 단위(ontological-component)로 등록해 관리하는 경우에는 [등록·관리](#등록관리-도구)의 소유 관계와 정합 계약도 적용한다. 물리적인 묶음의 편집과 의미 등록의 변경은 각각 확인한다.

### 모델링 검수

검수는 바뀐 모델이 해결하려던 설계 문제를 해결했는지, 의도한 공간과 구축을 성립시키는지 판단하는 과정이다. 수정한 형상에서 출발해 그 요소의 역할, 접합과 연속, 영향을 받은 공간과 다른 요소로 판단을 이어 간다. 국소적인 형상 개선이 주변의 사용이나 구성에 새로운 문제를 만들었는지도 살핀다.

무엇을 판단할지에 따라 관찰 방법을 정한다. 전체 배치와 공간 관계, 부재의 연결, 가려진 내부 구성은 필요한 관찰 범위와 시점이 다르다. 판단에 필요한 요소들이 함께 드러나도록 화면을 구성하고 실제 이미지를 읽는다. 격리한 화면이 보여 주는 관계와 제외한 관계를 구분하며, 잘린 요소나 빠진 주변 구성 때문에 판단 근거가 달라지지 않는지 확인한다.

시각적으로 읽은 내용은 그 판단에 필요한 형상과 치수로 대조한다. 부재 전체의 연속성을 판단하려면 그 부재를 이루는 객체들의 관계를, 접합을 판단하려면 맞물리는 요소의 실제 형상과 구성을 확인한다. 수치상 교차·간격이나 객체별 유효성은 해당 질문의 근거로 해석한다. 검사를 통과한 항목만으로 아직 보지 않은 관계까지 성립한다고 확대하지 않는다.

의미 있는 편집 묶음이 끝나면 결과를 사용자의 목표와 보존 조건에 대조하고, 그 결과를 바탕으로 다음 개입을 정한다. 변경으로 판단 범위나 구성에 대한 이해가 달라졌다면 관찰과 설계를 다시 이어 간다.

확인한 사실, 설계 의도에 대한 해석, 가정과 미확인 사항을 구분한다. 실행 성공과 형상의 유효성, 공간·구축의 적합성, 사용자 요청의 완료는 각각의 근거로 판단하며 미검사 범위와 남은 문제를 보고한다.

## 편집 범위의 격리와 내부 조회

### focus_components

`component_ids`에 서로 다른 ontological-component ID를 1–32개 지정하면, 각 component의 현재 멤버와 등록된 자손의 멤버를 선택·격리하고 확대한다. `expected_model_path`는 보통 생략하며 연결된 문서가 자동으로 지정된다.

Rhino의 기존 Isolate/Unisolate 이력을 사용하며 선택·가시성·화면 상태를 변경한다. 이미 숨겨지거나 잠긴 객체와 기존 문서 상태는 Rhino의 격리 기능 조건에 영향을 받는다. 실행 결과가 불확실하면 현재 상태를 확인하고 자동으로 재시도하지 않는다.


### analyze_block_reculviely

중첩 블록 구조와 현재 편집 단계의 블록 후보를 읽기 전용으로 조회한다. `mode="outline"`은 `options`의 `ids` 또는 `path`로 대상을 지정하고, 생략 시 `scope`(selected/viewport/document)로 범위를 고른다. `depth`로 펼칠 깊이를 제한한다. 기본 반환은 작은 요약이며 `field_groups=["objects","transforms"]`, `include_ids=true`로 내부 경로·누적 변환·ID를 추가한다. TextDot 관계는 `annotations` 필드군을 요청한다. `field_groups`는 summary/objects/annotations/transforms 중 비어 있지 않은 배열이며 `[]`·`all`은 지원하지 않는다.

`mode="resolve-block"`은 `options={"path":[최상위_GUID, 내부_멤버_GUID, ...]}`만 받는다. BlockEditNew에서는 부모를 연 뒤 경로를 한 단계씩 늘려 현재 선택 가능한 후보를 확인한다. 내부 GUID와 지금 선택 가능한 ID를 구분하고, 정의 저장·멤버 교체 후에는 다시 조회한다. 반환의 `unknown`·미지원·`truncated`는 미확인 범위다. 잘리면 IDs·path·depth를 좁힌다. 좌표·길이·공차는 현재 문서 단위다.

## Drafting

도면은 건축 요소의 표현이자 공간의 구성과 사용을 구상하고 전달하는 설계 도구다. 도면을 읽을 때는 그려진 형상과 표현을 파악하는 동시에, 그 구성이 만들어 내는 공간과 경험, 사람들이 그 안에서 맺는 관계를 이해한다.

### 도면을 공간과 의미로 읽기

도면의 요소를 독립된 객체나 선의 집합으로만 보지 않는다. 요소들이 함께 형성하는 공간적 관계와 그 관계가 가능하게 하는 사용·행태·경험을 읽는다. 하나의 요소가 여러 공간과 역할에 걸쳐 작용할 수 있음을 고려하고, 물리적으로 떨어진 요소도 하나의 사용이나 역할을 함께 이룰 수 있음을 살핀다.

공간의 의미는 실의 명칭이나 도면 기호만으로 결정되지 않는다. 공간의 구성과 주변 관계를 바탕으로 그곳에서 일어날 수 있는 행태를 구상하고, 그 행태가 공간과 건축 요소에 의해 어떻게 뒷받침되는지 판단한다.

평면·단면·입면은 같은 건축을 서로 다른 관점에서 보여 준다. 하나의 도면에서 읽은 관계를 다른 도면이나 모델과 연결해 이해하고, 확인할 수 없는 사항은 추론의 범위와 함께 구분한다.

#### 행태와 공간 경험

공간을 구상하고 검토할 때 사람이 그곳을 어떻게 경험하고 이용할지 생각한다. 공간의 크기나 형태뿐 아니라 공간 사이의 연결과 전이, 경계와 개방, 이용의 가능성과 제약을 함께 이해한다.

사람의 행태는 고정된 하나의 장면이 아니다. 공간은 이용자와 상황에 따라 다르게 사용될 수 있으며, 그 변화가 공간 구성과 어떤 관계를 맺는지 살핀다. 설계가 어떤 경험을 유도하고 무엇을 선택할 수 있게 하는지, 또는 어떤 이용을 어렵게 하는지 판단한다.

도면에 표현된 행태를 그대로 받아들이는 데 그치지 않고, 실제 공간에서 가능한 관계인지 검토한다. 도면만으로 확인할 수 없는 이용 조건은 필요한 자료와 시점을 통해 보완한다.

#### 공간의 규모와 사회적 관계

도면을 개별 실과 건축 요소에서 시작해 더 넓은 공간적 맥락과 연결해 읽는다. 과업의 규모와 목적에 따라 개인의 생활, 공동체의 관계, 거리와 도시, 사회적 가치까지 건축적 판단의 범위에 포함한다.

사람과 사람, 개인과 공동체, 건축과 주변 환경의 관계가 공간을 통해 어떻게 형성되는지 고찰한다. 공간적 구성과 사회적 가치 사이의 관계를 살피되, 도면만으로 확정할 수 없는 운영이나 사회적 효과는 해석과 제안으로 구분한다.

### 설계와 도면의 발전

도면 작업에서는 사용자의 의도와 설계 방향을 바탕으로 공간을 발전시키고, 그 결과가 도면에 정확하게 반영되도록 한다. 피드백이 특정 요소를 가리키더라도 그것이 놓인 공간과 주변 관계를 함께 이해한다.

평면을 수정하거나 새롭게 구성할 때는 도면상 형상의 변화가 실제 공간의 사용과 경험에 어떤 영향을 주는지 판단한다. 설계 과정에서 발견한 관계와 문제를 도면의 구성에 반영하고, 변경에 따라 함께 달라져야 할 사항을 정합한다.

확인된 조건을 바탕으로 전문적으로 판단하되, 사용자의 의도나 중요한 설계 선택이 불확실하면 그 불확실성과 선택의 영향을 분명히 설명한다.

작업의 목적과 대상, 설계 단계, 사용자의 결정과 조건을 파악한다. 현재 도면과 관련 스케치·피드백을 함께 읽고 공간의 구성과 맥락을 이해한다.

실제 도면 이미지를 보며 공간의 구성과 사용 관계를 검토한다. 그려진 요소가 의도한 공간과 행태를 뒷받침하는지, 도면이 설계의 관계를 정확하게 전달하는지 확인한다.

시각적으로 읽은 내용은 필요한 형상과 치수로 대조한다. 평면에서 확인하기 어려운 사항은 단면·입면·모델을 함께 살피고, 수정한 부분과 그 영향을 받는 공간을 다시 검토한다. 지정된 Named View가 있으면 검수에 활용한다.

도면에서 확인한 사실과 그에 대한 해석, 설계상 가정과 미확인 사항을 구분한다.

벽·문·가구·동선·프로그램 관계를 촘촘히 검토한 과거 과정의 참고 이미지가 필요하면 [Bonsai 평면 개요](features/guidance/guides/Bonsai-FloorPlan-overview.png)를 확인하되, 이를 최신 공간 결정이나 완성 도면 원본으로 사용하지 않는다.

### 도면의 작성과 관리

#### Layout 생성 및 관리

도면 Layout을 구성할 때는 현재 Rhino 문서에 실제 존재하는 Layout·PageSpace·Detail을 조회해 목적·용지·축척에 맞게 재사용하거나 조정할 수 있는지 살핀다. 필요하면 새 Layout과 Detail 뷰를 추가해 작업하고, 불필요해진 Layout은 필요한 도면·주석이 남아 있지 않은지 확인한 뒤 제거한다.

#### 도면 생성 툴

[PlanSection](features/modeling/PlanSection/README.md#에이전트에서-사용)은 clipping plane GUID를 받아 평면·단면의 단면선·해치·가시 입면선을 추출한다. `execute_rhino_script`에서 해당 스크립트의 `run()`을 호출하며, 입력 형식과 호출 예시는 링크를 따른다. 출력은 별도의 도면 레이어에 놓이고 원본 객체·레이어·부모 블록에서 해석한 속성을 적용한다. 해치는 SectionStyle에 채움이 있을 때 생성되며, 입면선의 인쇄 굵기·명암은 깊이에 따라 계산한다.

도면은 clipping plane의 축을 기준으로 WorldXY(Z=0)에 놓이며, 배치 기준점은 clipping plane의 원점에 대응하는 점이다. `Create`의 `points={GUID: [x, y]}`로 그 기준점의 도면상 절대 위치를 문서 단위로 지정한다. `Move`는 기존 도면을 그대로 옮기고, `Update`는 저장된 위치에서 다시 추출하므로 출력에 직접 가한 형상·속성 수정은 교체된다. `PDF`는 clipping의 `Paper`·`Scale`과 원점으로 용지 크기·축척·중심을 정하며, 용지 밖은 잘라낸다.

#### 도면 표현·출력 검수

도면의 용도와 축척에 맞춰 선두께·선종류·해치·문자와 치수의 가독성·잘림을 확인한다. Layout 도면을 검토할 때는 뷰 목록에서 해당 Layout GUID를 골라 용지와 Detail을 캡처하고, 용지 크기와 Detail 축척을 확인한다. 정적 도면의 축척은 이름으로 추정하지 않는다. 파일을 출력했다면 출력본도 열어 확인하고 수정한 부분을 다시 검수한다.

출력 색상과 선두께를 화면에서 검토할 때는 해당 문서의 PrintDisplay와 Model·Layout의 Print colors 적용 상태를 확인하고, 필요한 설정을 적용한다. Layout 캡처 자체는 기존 Detail 축척과 PrintDisplay를 변경하지 않는다. 미리보기의 색상·선두께와 실제 출력 결과는 구분하며, Detail이 없는 정적 PageSpace 도면만으로는 Detail 축척을 입증할 수 없다.

## 구조 검토

명시한 부재·재료·하중·지지 조건으로 구조를 검토한다. 응답의 engine·해석 수준을 확인하며, `rule_based/low` 결과는 FEA 결과와 구분한다.

| 도구 | 입력 | 할 수 있는 일 |
|---|---|---|
| `list_design_codes` | 선택적 `include_ids` | 지원 구조 설계 코드 목록 조회.|
| `validate_structure` | 객체 `guids`, 구조 형식·재료·하중·지지·해석 조건 | 구조 검토 실행·이력 기록. 응답의 engine·해석 수준 확인. |
| `visualize_structure`| 대상·해석 조건, 선택적 표시 설정 | 구조 검토 결과를 Rhino 화면에 표시. |
| `export_structural_report` | 선택적 `path`, `limit`  | 구조 검토 이력 보고서 출력.|
| `check_egress` | `plate_bounds_mm`, `exits`, 용도·층수·피난 조건  | 출구 수·분리·폭·이동거리 검토. |

## 거의 사용하지 않는 기능

### 자산 목록·검색

모델·2D 자산은 공통 목록에서 다루며, 3D 대표 파일은 3DM이다. 생성·입수 경위는 출처 정보로 보존하고 Diagram은 도식용 자료로 구분한다. [준비·등록·배치·교환·외부 발행·카메라 경로 작업](features/guidance/guides/references/asset-workflows.md)은 해당 작업을 할 때 읽는다.

| 도구| 입력  | 할 수 있는 일  |
| --- | --- | --- |
| `search_asset_repository` | `query`, 선택적 `kind`, `drawing_ready`, `limit` | 통합 자산 후보 검색. |
| `list_drawing_assets`  | 선택적 `category`, `limit`, `offset`| 모델·2D 자산 목록 조회. |
| `search_drawing_assets`| 검색어·분류·최대 치수 조건  | 크기와 용도에 맞는 모델·2D 자산 검색.  |
| `get_drawing_asset` | `asset_id`| 3DM 가용성·측정 치수·메타데이터 조회.|
| `get_asset_drawing` | `asset_id`| 자산의 평면·정면·측면 도면 파일 목록 조회. |
| `list_diagram_assets`  | 선택적 `category`, `limit`, `offset`| Diagram 자산 목록 조회. |
| `search_diagram_assets`| 검색어·분류·최대 치수 조건  | Diagram 자산 검색.|
| `get_diagram_asset` | `asset_id`| Diagram 파일·크기·배치 조건 조회. |
| `get_retrieval_status` | 선택적 `include_ids`  | 자산 색인·검색 기능 상태 조회.  |

이름·종류로 후보를 좁힌 뒤 치수는 dimensions, 실제 파일은 paths, 출처·라이선스는 source 등 해당 도구가 지원하는 field_groups로 추가한다. include_ids만 켜서 모든 상세를 받은 것으로 해석하지 않는다. 기존 자산 provenance·라이선스는 보존한다.

### Grasshopper

| 도구| 입력| 할 수 있는 일|
| --- | --- | --- |
| `list_library`| 선택적 `include_ids`| Grasshopper 로직 목록 조회. |
| `get_logic_by_id`| `logic_id` | 로직 원형·설명 조회. |
| `list_capsules`  | 선택적 `capability`, `audited_only=True`  | 실행 가능한 audited capsule과 입출력 port 확인.  |
| `run_gh_definition` | `capsule_id`, port 계약에 맞는 `inputs`, 선택적 `seed`, `timeout_s` | audited capsule 실행. 정의에 따라 Rhino에 bake할 수 있다. |
