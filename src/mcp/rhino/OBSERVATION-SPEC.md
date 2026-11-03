# 현재 문서·화면 조회와 C# 결과 반환

프로젝트 정보가 필요하면 `project_info`를 조회한다. project/document 항목이 실제 문서를 한 번 함께 확인하고 project에 연결 문서와의 일치 여부를 제공하므로 같은 live 확인을 위해 `get_rhino_context`를 다시 호출하지 않는다. 현재 화면이 판단에 필요할 때 `get_current_viewcapture`를 호출한다. beyond·CoS에서도 같은 이름을 사용하고 `connection_id`를 전달한다.

두 조회는 기존 Engine의 문서 binding·UI thread·호출 identity·native 완료 확인을 거친다. 파일 경로를 임의로 골라 다른 모델을 조회하는 기능은 없다.

문서 전용 MCP 서버와 외부 host가 안내하는 BASIC은 필요한 현황 조회, 관련 객체 조사, 수정 후보 검증 후 원본 교체 순서를 전달한다. beyond·CoS 클라이언트도 이 안내를 받는다.

## 현재 상태

`get_rhino_context`는 document/viewport/editor/named_views/layouts/display_modes/viewports 중 요청한 항목만 수집한다.
sections를 생략하면 document/named_views/layouts/display_modes와 next_step을 반환한다. next_step은 다른 선택 입력에 관계없이 sections 생략 시에만 표시한다. 명시한 sections에 editor가 없으면 편집 상태를 조사하거나 출력하지 않는다. sections=[]는 status/warnings만 반환한다.

| 필드 | 내용 |
|---|---|
| `status`, `warnings` | 성공/오류와 확인하지 못한 값의 설명 |
| `document` | units, absolute_tolerance, angle_tolerance(라디안), modified, object_count, layer_count |
| `viewport` | 활성 viewport 이름/크기/표시 모드/투영/카메라; ID는 include_ids=true일 때 |
| `editor` | mode/target/stable/warnings; include_editor_details=true일 때 provider·명령·Undo 근거 추가 |
| `named_views`, `layouts` | 이름과 ID, include_ids와 무관하게 ID 유지 |
| `display_modes` | 설치된 이름과 ID, 최대 128개와 초과 경고; ID 항상 유지 |
| `viewports` | 모델 viewport 목록; 선택 조회이며 일반 include_ids 정책 적용 |

문서 파일명·경로는 project_info에서 확인한다. 문서 객체 수는 정상·숨김·잠금·reference·light를 포함하며 삭제 객체·블록 정의 내부·grip은 제외한다. 레이어 수는 삭제 레이어를 제외한다. 실패한 관측은 null과 경고이며 가짜 0/빈 목록으로 바꾸지 않는다. 공개 context는 이미지를 받거나 파일을 쓰지 않는다.

선택 조회는 `get_objects(scope="selected")`로 통합한다. 기본은 문서 객체 목록이며, `result_mode="hierarchy"`로 완전히 선택된 그룹·블록을 요약하고 expand_groups/expand_blocks와 depth로 내부를 펼친다. 부분적으로 선택된 그룹은 개별 객체로 남는다. 문서 객체 수와 계층 occurrence 수는 서로 다르다.

공개 조회는 context_sections>=2를 요구하고 native public_context=true로 요청한다. 기존 내부 native 호출은 문서 identity/capabilities, 필요한 compact editor, raw 선택 GUID 기본값을 유지한다. 이로써 연결 문서 검증과 Holon/Plan 역조회 계약을 보존한다.

편집 대상은 명령 수나 선택에서 추측하지 않는다. 공용 `EditingContext.Observe`는 공식 plug-in 로드 상태와 실제 편집 provider 상태를 확인한다. 지원 adapter는 정확한 assembly identity/MVID/hash에 제한되며, 다른 버전·전환·대상 불명·UV/block 전용 공간은 unknown 또는 stable=false다.
현재 adapter 범위는 기본 BlockEdit 8.34.26223.11001과 BlockEditNew package 2.1.7이다.
미설치/미로드 provider는 강제로 로드하지 않는다. GroupEdit provider가 원본 영속 GUID를 보관하지 않으면 group_id는 null이고 원본 index/label/count만 표시한다. 새 Rhino/plugin 버전은 검증 없이 normal로 통과하지 않는다. native 명령·Undo/Redo 진행 중에도 전체 문서 저장·정합을 보류한다.

이 경로는 레이어·치수·geometry·Undo record를 생성하지 않는다. 현재 viewport가 보는 모든 객체를 계산하거나 단면·접합·치수의 정확성을 판정하지는 않는다.

## 화면 캡처

`get_defined_viewcapture(target_kind="named_view"|"layout", target="이름 또는 ID")`는 지정된 Named View 또는 Layout을 캡처한다. 목록은 get_rhino_context에서 조회한다. 같은 이름이 여러 개이면 오류이며 고유 ID로 구분한다. Named View는 저장된 카메라를 별도 화면에서 그리므로 실제 활성 뷰를 바꾸지 않는다. 기본 표시 모드는 Shaded이며 설치된 이름/ID로 변경할 수 있다.

Layout은 실제 용지와 Detail을 인쇄 색·선 두께로 캡처하고 주변 작업창을 포함하지 않는다. 100%는 용지를 144 dpi로 표현한 크기다. 호출자는 픽셀이나 용지 비율을 계산하지 않는다. Layout의 표시 모드·픽셀 강제 지정은 거절하며 Detail 축척과 문서 PrintDisplay를 바꾸지 않는다. scale_percent는 기본 75의 상한이며 정의된 뷰가 PNG 전달 한도를 넘으면 비율을 줄이고 경고한다. 명시한 Named View 픽셀은 자동 축소하지 않는다.

`get_current_viewcapture()`는 현재 모델 viewport를 그대로 캡처한다. target_ids를 지정하면 실제 선택을 그 대상으로 바꾸고 Zoom Selected를 적용한다. isolate=true는 그 전에 Rhino 기본 Isolate를 실행한다. 실제 화면의 카메라·선택·격리는 캡처 후 유지되며 Unisolate로 native 격리를 해제한다. 잠긴 주변 객체는 Rhino Isolate의 기존 동작대로 남을 수 있다. optional display_mode도 실제 viewport에 적용한다. Layout에서 호출하면 모델 viewport 활성화 또는 정의된 Layout 캡처를 안내한다.

대상은 여러 ID를 받는다. target_kind는 ID의 종류(object/group/block/holon)를 뜻하며 geometry 허용 목록이 아니다. object와 block 경로는 같은 일반 Rhino 객체 식별을 사용하므로 curve/mesh/Brep/block/annotation을 따로 분기하지 않는다. group은 현재 멤버, holon은 현재 effective 멤버를 해석한다. 실제 선택·격리·확대는 기존 Holon focus와 공통 함수를 사용한다. 현재 선택 가능한 model-space 객체와 4096개 focus 한도, 명령·Undo 전환 보호를 유지한다. 숨김·잠금·Layout 객체·블록 정의 내부의 ID는 자동으로 수정하거나 잘못된 위치에서 선택하지 않는다.

캡처는 파일 저장과 화면 변경 결과를 구분한다. 정상 출력은 PNG MCP image와 image_file이며, 실제 화면을 변경한 요청은 view_change와 mutation_applied를 함께 반환한다. 이미지 캡처·검증·저장 실패가 이미 수행한 화면 변경을 되돌리지 않는다. native 완료가 불명확하면 mutation_applied=null/requires_reconciliation=true를 보존하고 자동 재시도하지 않는다. Isolate의 Undo/Unisolate 기록은 Rhino 명령이 관리하며 별도 geometry나 custom 격리 렌더러를 만들지 않는다.

labels는 기본 false이고 선택 시 최대 200개의 임시 pixel label을 그린다. depth는 1–8이다. Layout Detail label은 지원하지 않으며 경고한다. 현재 화면 scale_percent는 1–100, 기본 75다. 명시 width/height는 각 128–2048과 scale_percent=100으로 요청하고 창 크기를 변경하지 않는다. PNG는 16 megapixels/4 MiB 한도다. 선택적 include_usage는 실제 출력 픽셀과 예시 token 추정이며 실제 모델 사용량이 아니다. 새 realtime 표시 모드를 시작하거나 렌더 완료를 기다리지 않는다.

검증된 PNG를 Plan artifact_dir/captures 또는 연결 소유 .almond/tmp/python/<token>/captures에 저장한다. 상대 경로·bytes·SHA256·보존 수명을 반환하며 별도 저장 실패에도 이미지와 화면 변경 근거는 유지한다. 캡처 도구는 MCP readOnlyHint=false, destructiveHint=false다. get_rhino_context와 get_objects는 파일을 쓰지 않는다.

공개 get_rhino_viewport_image와 context의 include_image는 제거됐다. 내부 native 문서 관측과 기존 capture helper는 private 호출 계약을 유지한다. 새 캡처는 view_capture=1 capability와 문서 binding을 검증한다.

## 일반 객체 범위·형상과 묶음 캡처

`get_objects`는 `object_observation>=3`로 확인한 고정 native 경로다. 내부 get_rhino_objects 요청 이름은 유지하고 공개 get_rhino_selection/get_rhino_objects는 제거한다.
조회는 visible/selected/명시 GUID/document/groups 중 정한 top-level 모델 객체를 대상으로 한다. groups는 실제 Rhino group GUID 1–64개를 받아 해당 model-space 멤버의 중복 없는 합집합을 반환한다. 없는 그룹은 오류이며 다른 그룹의 연결 관계를 따라 범위를 확대하지 않는다.
필터·페이지·기하 상세의 입력은 [도구 설명](../features/context/tools-explain.md)에 둔다.
result_mode=objects는 문서 객체, summary는 레이어·유형 수량, hierarchy는 그룹·블록 계층이다. 필터는 top-level 객체에 먼저 적용한다. hierarchy는 expand_groups/expand_blocks(각 기본 false), depth(1–8, 기본 1)로 확장하며 number/parent_number가 페이지를 가로지르는 부모 관계를 보존한다. 그룹 계층은 엄격한 멤버 포함 관계로 판정하며, 겹치는 그룹·동일 멤버 그룹을 임의의 단일 부모에 배치하지 않는다. 명시한 그룹은 필터 후에도 루트로 유지하며 member_count와 matched_member_count를 구분한다.
블록 내부는 root_object_id와 block_path_ids로 구분하고 document_object=false를 표시한다. bounds는 world 좌표, 나머지 metadata는 정의 객체 기준이며 effective occurrence visible/selected는 null이다. 문서 객체의 수정 ID와 혼동하지 않도록 hierarchy에서 geometry/face 상세 입력은 거절한다. 해당 상세는 objects 모드로 조회한다.
children_state는 leaf/collapsed/expanded/depth_limit/cycle을 구분한다. complete는 요청한 깊이에서의 페이지 완전성을 뜻하며 모든 자손 조사 완료를 뜻하지 않는다. 계층 번호는 동일 문서·범위·옵션에서만 유효한 순회 순번이다. 페이지 사이 문서가 변경되면 처음부터 다시 조회한다. 계층은 100000 occurrence 한도를 둔다.
문서 가시성은 화면 픽셀·frustum·clipping·occlusion 판정과 구분한다.
UserDictionary는 기존 SharedUserDictionary만 읽으며, 사전을 생성하는 원본 getter를 호출하지 않는다.
다중 값 필터는 출력 잘림과 별개로 판정하고 필터 검사 예산 초과는 오류로 보고한다.
응답은 256 KiB를 넘지 않으며 기하 상세의 면·그룹·메타데이터 생략과 페이지를 명시한다.
요약은 필터된 전체 집합을 레이어·객체 유형·형상 종류로 집계하며, 선택한 필드만 계산한다.
명시적인 `fields=["id"]`는 기본 ID 생략보다 우선한다. 바깥 페이지는 객체/요약행, 각 객체의 `face_page`는 면 목록의 페이지다. 후속 면 조회는 명시 객체 집합과 원본 CRC를 요구한다.

GUID·Component 교차 검사는 `intersection_queries=1`을 확인하고 components/native의 공통 분석기를 사용한다. 512개 top-level 객체에서 닫힌 Brep·Extrusion·Mesh를 검사하고, 명시된 include_blocks에 따라 중첩 배치를 world-space 복사본으로 해석한다. 최대 2048개 occurrence· 20000개 후보를 허용하며 페이지당 최대 64쌍을 계산한다. Cursor는 문서·형상·범위·공차에 묶인다.
pair handle과 pair_state는 표시·수정의 실행 입력이므로 요약·ID 표시 옵션과 무관하게 보존한다.
미지원·미확정·미검사는 무교차가 아니다. Mesh/Brep 혼합 관찰의 메싱 근사와 페이지별 범위를 명시한다.
두 고정 객체 조회의 명시적 `status=error`는 기존 `{result: JSON 문자열}` schema와 오류 상세를 보존하며 MCP `isError=true`로 반환한다. 정상 페이지의 `unknown`, `complete=false`, cursor는 오류로 대체하지 않는다.

`capture_rhino_inspection`은 `inspection_capture=1`을 확인한 뒤 최대 16개 타일을 합성한다.
별도 viewport와 범위 제한 display conduit를 사용하며 live 카메라·선택·가시 상태를 수정하지 않는다.
필터의 culling 실행을 확인하지 못하면 이미지를 반환하지 않는다. 타일별 범위·모드·카메라·오류를 돌려주며 일부 실패는 `complete=false`로 표시한다. 전체 이미지는 16M 픽셀·PNG 4 MiB 이내다.
기본은 활성 모델뷰를 사용한다. `inspection_model_view=1`에서는 `model_view_id`로 기존 모델뷰를 지정해 활성 Layout·Detail을 바꾸지 않고 모델을 관찰한다. 문서·선택·가시성·Modified와 원본/활성 viewport·ActiveSpace가 전후 일치하지 않으면 이미지를 내보내지 않는다.
기존 tile별 GUID는 512개 한도를 유지한다. `inspection_shared_scope=1`에서는 최상위 `object_ids`에 기존 객체 조회와 같은 상한인 1..4096개를 한 번 전달해 모든 tile에 재사용한다. 공통 `[]`와 공통/개별 집합 혼용은 오류다. 전체 GUID·총수는 `shared_scope`에 한 번 반환하며, 성공 tile의 참조·개수와 요청 집합을 Python에서 대조한다. 요청 256 KiB·메타데이터 512 KiB 한도를 유지한다. 전체/부분 성공 표시는 실제 tile 상태와 일치해야 하며 정상 부분 이미지는 보존한다.
명시 블록 인스턴스 필터와 group/block 편집 중 캡처는 지원하지 않는다.

## 제한된 평면 면 편집

`edit_planar_face`는 `face_edit=1`과 저장된 대상 문서를 확인하는 고정 native 편집 경로다.
공개 임의 코드 실행의 대체 경로가 아니라, 닫힌 manifold Brep의 평면 면과 인접 평면을 `Brep.PushPullExtend`로 연장하는 고정 연산이다. 대상 GUID·면 index·원본 geometry CRC를 받아 오래된 면 참조를 거절하고, 복제본에서 검사한 뒤 같은 GUID로 교체한다. 속성·그룹과 기존 geometry UserDictionary/UserStrings를 보존하며, 기타 custom geometry UserData는 편집 전에 거절한다.
상자 재생성으로 대신하지 않는다. Undo·완료·불확실한 수정의 재시도 금지는 기존 ScriptExecutor/native receipt 계약을 따른다. 형상 연산 성공이 설계 적합성을 뜻하지 않는다.

`edit_planar_faces`는 `face_edit_batch=1`을 확인하고 서로 다른 객체 1..32개의 면을 한 native 호출로 편집한다.
모든 복제본을 준비·검증한 뒤 한 Undo 구간에서 교체한다. 준비 실패는 문서를 바꾸지 않으며, 교체 중 실패는 적용·실패·불명·미시도 항목을 구분하고 중단한다. 단일 Undo는 자동 rollback을 뜻하지 않는다.
동일 객체를 두 번 포함할 수 없으며, 같은 객체의 다음 편집에는 바뀐 면·CRC 관찰이 필요하다.

## 중첩 블록 분석

`analyze_block_reculviely(mode, options)`는 `outline`, `resolve-block` 두 모드만 제공한다.
입력·옵션 의미는 `tools/list`의 해당 도구 설명 전문과 schema를 따른다. 설명 원본은 [context 도구 설명](../features/context/tools-explain.md)에 있다.
runtime은 연결된 문서의 expected_model_path를 공급하고 외부 연결기는 connection_id를 요구한다.
경로가 현재 문서와 다르면 계산 전에 거절한다.

Python API와 설명은 `features/context`, 컴파일되는 C# handler와 탐색 helper는 그 안의 `native/`가 소유한다. Bridge의 UI thread가 handler를 직접 호출하며 일반 스크립트 실행기·Roslyn·BeginUndoRecord를 거치지 않는다. 형상·속성·레이어·선택·뷰·modified·Undo를 보존한다.
응답은 status, mode, document identity·units·tolerance, data를 담으며 요청·반환은 각각 UTF-8 JSON 262,144 bytes 이내다.

outline은 summary를 기본으로 하며 field_groups로 objects/annotations/transforms를 선택한다.
명시적 include_geometry/annotations 옵션은 상세 조회를 유지한다. 상세 방문도 max_items로 제한하고 visited/max_visits와 잘림 사유를 표시한다. unknown·미지원·잘림을 0이나 통과로 해석하지 않는다.

Python은 `capabilities.block_analysis=1`을 먼저 확인한다. 지원하지 않는 Bridge에는 분석 요청을 보내지 않는다.
Bridge의 알 수 없는 request type도 실행 없이 unsupported_request로 거절한다.
Holon의 rhino_group_id는 get_objects(scope="groups", group_ids=[...], include_ids=true)로 실제 문서 객체 GUID를 얻은 뒤 get_object_intersections에 전달한다. 전용 공개 get_holon_intersections는 없으며 공통 교차 계산기는 components/native가 소유한다. 의미 등록의 정합 검사는 Holon 조회 계약으로 남는다.

## Private Bridge C# recipe에서 계산값 반환

재료·자산·교환·capture의 내부 Bridge recipe는 `public static Run(RhinoDoc doc)` 진입점을 유지한다. JSON으로 표현 가능한 값을 반환하면 응답의 `result`에 들어간다.
아래 반환값 규칙은 이 private 전송에 해당한다. 공개 `execute_rhino_script`의 C#은 RhinoCode statement body이며 `result_json`을 지정한다. 공개 언어·완료·결과 한도는 [RhinoCode 실행 계약](../runtime/RHINOCODE-SPEC.md)을 따른다.

```csharp
public class Script
{
    public static object Run(RhinoDoc doc)
    {
        return new {
            name = doc.Name,
            units = doc.ModelUnitSystem.ToString(),
            tolerance = doc.ModelAbsoluteTolerance
        };
    }
}
```

지원 값은 문자열/문자/불리언/유한 숫자/Guid, 문자열 키 dictionary, list/1차원 배열, 그리고 C# 익명 객체다. 그 안의 값도 같은 조건을 만족해야 한다. 기하 객체나 임의 클래스를 그대로 넘기지 말고 필요한 수치·ID를 익명 객체에 투영한다. 임의 POCO의 property getter, lazy enumerable, 사용자 JSON converter는 자동 실행하지 않는다.

`result` 자체의 compact JSON을 UTF-8로 계산해 최대 65,536 bytes, 중첩 container는 최대 16개까지 허용한다. 순환 참조·비유한 숫자·미지원 타입·과대 결과는 일부만 잘라 정상 데이터처럼 보내지 않고 `result_error`로 설명한다. 반환 데이터는 응답 생성 전에 분리한 JSON tree이므로 최종 직렬화가 사용자 객체를 다시 탐색하지 않는다.

| 결과 | 의미 |
|---|---|
| `status=success`, `result` | 스크립트가 끝났으며 표현 가능한 계산값을 받음 |
| `status=success`, `result_error` | 스크립트는 끝났으나 반환값을 표현하지 못함. 적용된 변경은 이 이유로 rollback되지 않음 |
| runtime/Undo 오류 | 기존 실행·복구 오류. 성공 데이터처럼 보일 수 있는 새 결과 필드는 제거됨 |
| timeout/완료 미확정 | 기존 Engine의 격리·완료 확인 규칙을 따름. rollback로 간주하거나 자동 재시도하지 않음 |

`List<Guid>` 반환은 기존 `guids` 및 자동 치수 동작을 유지하며 `result`를 추가하지 않는다. `void`와 `null`도 새 결과 필드를 만들지 않는다. `guids`는 스크립트가 선언한 ID이며 전체 변경 내역을 보장하지 않는다. 일반 실행기는 Undo 범위 안에서 임의 코드를 실행하므로, 계산값만 돌려주는 코드여도 read-only 도구로 간주하지 않는다.

## 수정의 판정과 검증

실행 성공, `IsValid`/`IsSolid`, 현재 화면은 각각 다른 근거다. 예를 들어 Boolean 수정에서는 결과 배열이 비어 있지 않은지, 기대 제거량·접합 범위·기준면이 맞는지, 원본의 비대상 부분이 보존되는지 확인한 뒤 Replace/Delete를 적용한다. 검사값을 반환하면 후속 판단을 쉽게 할 수 있지만 검사 조건 자체의 정확성을 보장하지는 않는다.

현재 오프라인 검사는 실제 MCP content/schema와 읽기 전용 응답 계약을 다룬다. 실제 Rhino의 Undo/Redo, viewport와 geometry/attributes/layer/view/selection 보존에 대한 native 자동 검증은 아직 구성되어 있지 않다. 검증 범위와 실제 문서 보존 원칙은 `src/rhp/RhinoAlmondBridge/tests/script_executor_undo/README.md`를 따른다. 오프라인 통과를 이 항목의 실사용 검증으로 취급하지 않는다.
후보 RHP 빌드, 실제 로드 경로, 실제 클라이언트 수신은 각각 별도로 확인해야 한다.
