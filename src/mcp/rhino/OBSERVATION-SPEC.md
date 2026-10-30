# 현재 문서·화면 조회와 C# 결과 반환

프로젝트 정보가 필요하면 `project_info`를 조회한다. 기본 document 항목이 실제 활성 문서를
함께 확인하므로 같은 live 확인을 위해 `get_rhino_context`를 다시 호출하지 않는다. 현재 화면이 판단에 필요할 때
`get_rhino_viewport_image`를 호출한다. beyond·CoS에서도 같은 이름을 사용하고 `connection_id`를 전달한다.

두 조회는 기존 Engine의 문서 binding·UI thread·호출 identity·native 완료 확인을
거친다. 파일 경로를 임의로 골라 다른 모델을 조회하는 기능은 없다.

문서 전용 MCP 서버와 외부 host가 안내하는 BASIC은 필요한 현황 조회, 관련 객체 조사, 수정 후보 검증 후
원본 교체 순서를 전달한다. beyond·CoS 클라이언트도 이 안내를 받는다.

## 현재 상태

```json
{"sections": ["selection"], "selection_limit": 50}
```

`get_rhino_context`는 document/selection/viewport/editor/display_modes 중 요청한 항목을 수집한다.
기본은 document이며 여러 section을 조합할 수 있다. document/selection/viewport에는 작은
editor 요약(mode/target/stable)이 함께 표시된다. 상세 provider 근거·경고는 editor section을
명시할 때만 반환하며 `sections=[]`는 editor를 조사하지 않는다. 일반 ID는 include_ids=true일 때만 반환한다.

| 필드 | 내용 |
|---|---|
| `status` | `success` 또는 명시적 오류 |
| `document` | runtime serial, path, name, units, 절대/각도 공차, modified, 객체/레이어 수 |
| `selection` | 전체 선택 수 `total`, 반환 수 `returned`, `truncated`, 객체별 id/name/layer/type |
| `viewport` | 활성 viewport ID/이름, 원본 픽셀 크기, display mode, projection, camera/target/up/lens |
| `warnings` | 확인하지 못한 값이나 viewport 부재에 관한 설명 |
| `editor` | model/group/block/unknown 모드, 확인된 편집 대상, 전체 문서 저장·정합을 허용하는 stable |
| `display_modes` | 실제 설치된 display mode 이름/GUID, 최대 128개 |

`selection_limit`의 기본값은 50이고 범위는 0–200이다. 0이면 목록을 생략하면서
전체 선택 수는 조회한다. 선택은 recursive=false, depth=1이 기본이며 완전히 선택된 최상위
group과 block instance를 요약한다. 일부만 선택한 group은 개별 객체로 남는다. recursive=true일
때만 depth(1–8)까지 내부를 펼친다. selected_object_count와 요약 entity total을 구분한다.
이 요약은 공개 Python 도구가 native 요청의 selection_entities=true를 명시해 받는다.
기존 native 내부 호출은 기본 raw 객체 GUID 목록을 유지하므로 선택의 Component/Plan 역조회를 깨지 않는다.
객체 수는 정상·숨김·잠금·reference·light를 포함하며
삭제 객체·블록 정의의 내부 객체·grip은 제외한다. 레이어 수는 삭제 레이어를 제외한다.
조회 실패 값을 0이나 빈 문서로 바꾸지 않고 `null`과 경고로 표시한다.

`include_image=true`를 명시하면 같은 native UI 호출에서 현재 화면을 함께 수집하고,
public MCP 응답은 JSON text 다음 PNG가 된다. 기본 false와 document-only 조회는 JSON만 반환한다.
캡처 실패는 image_error로 남기며 이미 얻은 context를 지우지 않는다.

편집 대상은 명령 수나 선택에서 추측하지 않는다. 공용 `EditingContext.Observe`는 공식 plug-in
로드 상태와 실제 편집 provider 상태를 확인한다. 지원 adapter는 정확한 assembly identity/MVID/hash에
제한되며, 다른 버전·전환·대상 불명·UV/block 전용 공간은 unknown 또는 stable=false다.
현재 adapter 범위는 기본 BlockEdit 8.34.26223.11001과 BlockEditNew package 2.1.7이다.
미설치/미로드 provider는 강제로 로드하지 않는다. GroupEdit provider가 원본 영속 GUID를 보관하지
않으면 group_id는 null이고 원본 index/label/count만 표시한다. 새 Rhino/plugin 버전은 검증 없이
normal로 통과하지 않는다. native 명령·Undo/Redo 진행 중에도 전체 문서 저장·정합을 보류한다.

이 경로는 레이어·치수·geometry·Undo record를 생성하지 않는다. 현재 viewport가
보는 모든 객체를 계산하거나 단면·접합·치수의 정확성을 판정하지는 않는다.

## 현재 화면

```json
{"view": "a"}
```

`view="a"`는 `viewports`, `named_views`, `layouts`별로 이름(`name`)과 GUID(`guid`)만
반환한다. 원하는 GUID를 `view`에 넣으면 그 이미지가 나온다. `view`를 생략하면
현재 뷰를 캡처한다. 같은 이름이 있어도 GUID로 대상을 구분한다.

```json
{"view": "목록에서 받은 GUID", "scale_percent": 50}
```

기본 반환은 **PNG MCP image content 한 개**이며 경로·문서·GUID metadata를 반복하지 않는다.
`scale_percent`는 1–100 정수, 기본 75다. 100은 원본 픽셀 크기이고 도면 검수에 사용한다.
75는 가로·세로 각각 75%다. Named View는 저장된 화면 크기(없으면 현재 뷰 크기), Layout은
용지를 96 dpi로 표현한 크기를 100%로 삼는다. Layout은 주변 작업창을 빼고 용지와
그 안의 Detail을 캡처하며, 현재 Layout에서 Detail이 활성화돼 있어도 용지가 대상이다.

Named View는 별도 viewport에서 저장된 카메라를 그리며 기본 mode는 Shaded다.
화면의 활성 뷰 전환·Named View 복원·zoom·selection·Undo 변경을 하지 않는다.
PNG와 base64 모두 메모리에서 처리하므로 임시 이미지 파일을 만들지 않는다.
display_mode에 실제 설치된 이름/GUID를 지정할 수 있고, 빈 값이면 현재 model viewport는
원래 mode, Named View/group/block은 Shaded를 쓴다. 작업 화면 카메라 이동만으로 독립 Named View
캡처를 버리지 않는다. Shaded/Dark/CadWhite가 설치돼 있다고 가정하지 말고 display_modes를 조회한다.
독립 캡처는 표시하지 않는 공식 SDK viewport control에서 raster mode를 그리며 원본 뷰를 추가·활성화하지 않는다.
Raytraced 등 RealtimeDisplayId가 있는 비동기 렌더 모드는 명시적으로 거절한다. 렌더 완료를 기다리는 기능은 없다.

labels=true/depth=1이 기본이다. 최대 200개 entity의 이름/GUID를 transient 픽셀로 그리며 문서
TextDot이나 속성을 만들지 않는다. top group은 group GUID, block은 definition GUID가 아닌
instance GUID로 구분한다. target_kind=group|block과 target_id로 해당 대상을 detached 카메라에서
프레이밍할 수 있으며 주변 형상을 숨기지는 않는다. Layout은 각 Detail의 mode를 유지하므로 mode
override를 거절하고, Detail 라벨 미지원은 경고한다. 라벨이 필요하면 model viewport/Named View를 캡처한다.

`include_usage=true`일 때만 크기와 토큰 추정치를 덧붙인다. 추정식은
`ceil(width/32) × ceil(height/32) × 1.2`를 올림한 예시이며 공급자의 추가 리사이즈를
가정하지 않는다. 클라이언트의 모델·detail 설정을 MCP가 알 수 없으므로 실제 사용량이
아니다. PNG 압축 바이트 수보다 픽셀 크기를 줄이는 것이 이 추정량을 줄인다.
[공식 이미지 비용 안내](https://developers.openai.com/api/docs/guides/images-vision#calculating-costs)를 참고한다.

16 메가픽셀 또는 PNG 4 MiB를 넘으면 축소율을 낮추라는 오류를 반환하며 몰래 추가
축소하지 않는다. 없는 GUID·실패한 캡처·캡처 중 문서/뷰 변경도 이미지 없이 오류로
반환한다. Python에서도 실제 PNG 형식과 크기를 검사한다. 캡처 성공은 형상의 정확성을
증명하지 않는다. 의도적인 카메라 경로와 여러 패스는 `capture_conditioning_pass`를 사용한다.

## 일반 객체 범위·형상과 묶음 캡처

`get_rhino_objects`와 `get_object_intersections`는 `object_observation=1`로 확인한 고정 native 경로다.
조회는 visible/selected/명시 GUID/document 중 정한 top-level 모델 객체를 대상으로 한다.
필터·페이지·기하 상세의 입력은 [도구 설명](../features/context/tools-explain.md)에 둔다.
그룹·블록으로 연산 범위를 자동 확대하지 않고, 그룹의 범위 밖 멤버와 현재 문서 가시 범위를 보고한다.
문서 가시성은 화면 픽셀·frustum·clipping·occlusion 판정과 구분한다.
UserDictionary는 기존 SharedUserDictionary만 읽으며, 사전을 생성하는 원본 getter를 호출하지 않는다.
다중 값 필터는 출력 잘림과 별개로 판정하고 필터 검사 예산 초과는 오류로 보고한다.
응답은 256 KiB를 넘지 않으며 기하 상세의 면·그룹·메타데이터 생략과 페이지를 명시한다.

GUID 교차 검사는 기존 ComponentOperations/SolidIntersections 구현을 재사용한다.
Component 등록 없이 닫힌 Brep/Extrusion에 대해 최대 512객체·64후보쌍을 검사하고,
미지원·미확정·잘린 결과를 무교차로 간주하지 않는다. 접합의 설계 적합성은 별도 판단이다.

`capture_rhino_inspection`은 `inspection_capture=1`을 확인한 뒤 최대 16개 타일을 합성한다.
별도 viewport와 범위 제한 display conduit를 사용하며 live 카메라·선택·가시 상태를 수정하지 않는다.
필터의 culling 실행을 확인하지 못하면 이미지를 반환하지 않는다. 타일별 범위·모드·카메라·오류를
돌려주며 일부 실패는 `complete=false`로 표시한다. 전체 이미지는 16M 픽셀·PNG 4 MiB 이내다.
명시 블록 인스턴스 필터와 group/block 편집 중 캡처는 지원하지 않는다.

## 제한된 평면 면 편집

`edit_planar_face`는 `face_edit=1`과 저장된 대상 문서를 확인하는 고정 native 편집 경로다.
공개 임의 코드 실행의 대체 경로가 아니라, 닫힌 manifold Brep의 평면 면과 인접 평면을
`Brep.PushPullExtend`로 연장하는 고정 연산이다. 대상 GUID·면 index·원본 geometry CRC를 받아
오래된 면 참조를 거절하고, 복제본에서 검사한 뒤 같은 GUID로 교체한다. 속성·그룹과 기존
geometry UserDictionary/UserStrings를 보존하며, 기타 custom geometry UserData는 편집 전에 거절한다.
상자 재생성으로 대신하지 않는다. Undo·완료·불확실한 수정의
재시도 금지는 기존 ScriptExecutor/native receipt 계약을 따른다. 형상 연산 성공이 설계 적합성을 뜻하지 않는다.

## 중첩 블록 분석

`analyze_block_reculviely(mode, options)`는 `outline`, `resolve-block` 두 모드만 제공한다.
입력·옵션 의미는 [조회·화면 지침](../BASIC-INSTRUCTIONS.md#analyze_block_reculviely)을 따른다.
runtime은 연결된 문서의 expected_model_path를 공급하고 외부 연결기는 connection_id를 요구한다.
경로가 현재 문서와 다르면 계산 전에 거절한다.

Python API와 설명은 `features/context`, 컴파일되는 C# handler와 탐색 helper는
그 안의 `native/`가 소유한다. Bridge의 UI thread가 handler를 직접 호출하며
일반 스크립트 실행기·Roslyn·BeginUndoRecord를 거치지 않는다. 형상·속성·레이어·선택·뷰·modified·Undo를 보존한다.
응답은 status, mode, document identity·units·tolerance, data를 담으며 요청·반환은 각각 UTF-8 JSON 262,144 bytes 이내다.

outline은 summary를 기본으로 하며 field_groups로 objects/annotations/transforms를 선택한다.
명시적 include_geometry/annotations 옵션은 상세 조회를 유지한다. 상세 방문도 max_items로
제한하고 visited/max_visits와 잘림 사유를 표시한다. unknown·미지원·잘림을 0이나 통과로 해석하지 않는다.

Python은 `capabilities.block_analysis=1`을 먼저 확인한다. 지원하지 않는 Bridge에는 분석 요청을 보내지 않는다.
Bridge의 알 수 없는 request type도 실행 없이 unsupported_request로 거절한다.
Component 교차체적 계산은 별도 `get_component_intersections` 계약이며 components/native가 소유한다.

## Private Bridge C# recipe에서 계산값 반환

재료·자산·교환·capture의 내부 Bridge recipe는 `public static Run(RhinoDoc doc)`
진입점을 유지한다. JSON으로 표현 가능한 값을 반환하면 응답의 `result`에 들어간다.
아래 반환값 규칙은 이 private 전송에 해당한다. 공개 `execute_rhino_script`의 C#은
RhinoCode statement body이며 `result_json`을 지정한다. 공개 언어·완료·결과 한도는
[RhinoCode 실행 계약](../runtime/RHINOCODE-SPEC.md)을 따른다.

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

지원 값은 문자열/문자/불리언/유한 숫자/Guid, 문자열 키 dictionary, list/1차원 배열,
그리고 C# 익명 객체다. 그 안의 값도 같은 조건을 만족해야 한다. 기하 객체나 임의
클래스를 그대로 넘기지 말고 필요한 수치·ID를 익명 객체에 투영한다. 임의 POCO의
property getter, lazy enumerable, 사용자 JSON converter는 자동 실행하지 않는다.

`result` 자체의 compact JSON을 UTF-8로 계산해 최대 65,536 bytes, 중첩 container는
최대 16개까지 허용한다. 순환 참조·비유한 숫자·미지원 타입·과대 결과는 일부만 잘라
정상 데이터처럼 보내지 않고 `result_error`로 설명한다. 반환 데이터는 응답 생성 전에
분리한 JSON tree이므로 최종 직렬화가 사용자 객체를 다시 탐색하지 않는다.

| 결과 | 의미 |
|---|---|
| `status=success`, `result` | 스크립트가 끝났으며 표현 가능한 계산값을 받음 |
| `status=success`, `result_error` | 스크립트는 끝났으나 반환값을 표현하지 못함. 적용된 변경은 이 이유로 rollback되지 않음 |
| runtime/Undo 오류 | 기존 실행·복구 오류. 성공 데이터처럼 보일 수 있는 새 결과 필드는 제거됨 |
| timeout/완료 미확정 | 기존 Engine의 격리·완료 확인 규칙을 따름. rollback로 간주하거나 자동 재시도하지 않음 |

`List<Guid>` 반환은 기존 `guids` 및 자동 치수 동작을 유지하며 `result`를 추가하지
않는다. `void`와 `null`도 새 결과 필드를 만들지 않는다. `guids`는 스크립트가 선언한
ID이며 전체 변경 내역을 보장하지 않는다. 일반 실행기는 Undo 범위 안에서 임의 코드를
실행하므로, 계산값만 돌려주는 코드여도 read-only 도구로 간주하지 않는다.

## 수정의 판정과 검증

실행 성공, `IsValid`/`IsSolid`, 현재 화면은 각각 다른 근거다. 예를 들어 Boolean
수정에서는 결과 배열이 비어 있지 않은지, 기대 제거량·접합 범위·기준면이 맞는지,
원본의 비대상 부분이 보존되는지 확인한 뒤 Replace/Delete를 적용한다. 검사값을
반환하면 후속 판단을 쉽게 할 수 있지만 검사 조건 자체의 정확성을 보장하지는 않는다.

Python 검증은 실제 MCP content/schema와 위조·누락 이미지/크기 오류를 다룬다.
`src/rhp/RhinoAlmondBridge/tests/script_executor_undo`의 native suite는 기존 Undo 회귀,
반환 제한과 headless 조회를 검사하고, `ObservationTests.RunViewport(doc)`는 호출자가
지정한 실제 문서의 geometry/attributes/layer/view/selection/Undo 상태를 전후 비교한다.
후보 RHP 빌드, 실제 로드 경로, 실제 클라이언트 수신은 각각 별도로 확인해야 한다.
