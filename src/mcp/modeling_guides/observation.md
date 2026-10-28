### 조회·화면 도구

기본 조회는 필요한 요약부터 읽고, 도구가 지원하는 `field_groups`로 다음 판단에 필요한 상세만 추가한다. 일반 필드군 조회의 None/[]는 요약이고 `all`은 전체 상세다. ID는 `include_ids=True`, 기술 timestamp는 audit/all로 각각 선택한다. 오류·불완전·완료 불명·native proof는 표시 옵션으로 숨기지 않는다. 이미 프로젝트 정보에서 확인한 문서를 같은 목적으로 다시 조회할 필요는 없다.

도면·유닛의 위치나 작업 시점이 불명확하면 질문 전에 `get_rhino_viewport_image(view="a")`로 기존 Named View·Layout을 먼저 찾는다. 선택한 GUID를 캡처해 표제와 실제 대상·주변 관계를 대조한다. 이름만으로 범위를 확정하거나 조회를 위해 새 Named View를 만들지는 않는다.

| 도구 | 입력 | 할 수 있는 일 |
| ---- | ---- | --- |
| `get_rhino_context`  | 필요한 `sections`: document/selection/viewport/editor/display_modes; 선택적 `selection_limit`, `recursive=false`, `depth=1`, `include_image=false` | 선택·편집 모드/대상·카메라·설치 mode를 관찰하고 필요 시 같은 호출의 PNG 수신. |
| `get_selection_references` | 선택적 `selection_limit`, `limit`, `field_groups`, `include_ids` | 선택 객체에 연결된 ontological_component·Task·Step 역조회. |
| `get_rhino_probe` | 아래의 `probe`와 `options` | 형상·블록을 읽기 전용으로 관찰·측정.  |
| `get_rhino_viewport_image` | 현재 화면은 생략, 목록은 `view="a"`, 지정 뷰는 `view=GUID`; 선택적 `display_mode`, `labels=true`, `depth=1`, `scale_percent=50`, `target_kind`, `target_id` | 뷰 목록 또는 선택한 시점·group·block의 PNG 캡처. |
| `focus_components`| `component_ids` | 해당 ontological_component 선택·격리·확대. 화면 상태가 바뀐다. |

document/selection/viewport 조회에는 compact editor mode·target·stable도 포함된다. `sections=["editor"]`는 provider evidence와 경고를 더 읽고, 모드·대상 unknown은 미확인으로 남긴다. 선택은 기본 nonrecursive이며 필요할 때만 recursive와 depth(1–8)를 늘린다. `include_image=true`는 같은 native 호출의 JSON text 다음에 현재 PNG를 반환하고, 실패한 이미지는 image_error로 남겨 가능한 context를 보존한다.

표시 모드는 `get_rhino_context(sections=["display_modes"], include_ids=true)`의 실제 설치 이름/GUID에서 고른다. Shaded·Dark·CadWhite를 설치 확인 없이 가정하지 않는다. 캡처의 빈 display_mode는 현재 viewport에서 현재 mode를 유지하고 Named View/group/block에서는 Shaded를 사용한다. Named View는 저장 카메라를 별도 viewport에서 렌더링하므로 작업 중 active view를 바꾸지 않는다.

group/block을 볼 때는 `target_kind="group"` 또는 `"block"`과 영속 group GUID/최상위 block instance GUID를 target_id로 지정하고 view는 비운다. 별도 카메라가 대상 bounds를 잡고 주변 형상은 유지한다. 조회 목적의 캡처와 선택·격리·확대를 수행하는 focus_components는 구별한다. Layout은 Detail mode를 유지해 mode override를 거절하며 Detail 라벨 미지원 경고를 반환한다.

labels는 기본 true이고 최상위 group 이름+GUID, block instance GUID, 독립 객체 GUID를 transient pixels로 표시한다. TextDot·객체·속성을 만들지 않으며 JSON의 include_ids와 독립적으로 labels가 제어한다. depth는 1–8, 라벨은 최대 200개다. 잘림 경고가 있으면 대상·깊이를 좁힌다. PNG는 16 메가픽셀·4 MiB 이내이며 초과하면 scale_percent(1–100)를 명시적으로 낮춘다.

`get_rhino_probe`의 옵션은 아래와 같다. 좌표·길이·공차는 현재 문서 단위다. 반환의 `unknown`·미지원·`truncated`는 미확인 범위이며 0이나 통과를 뜻하지 않는다. 범위가 잘리면 대상·표본을 나눠 조회한다.

| probe 값  | options에 넣을 입력  | 알 수 있는 것|
| ----- | ----- | ----- |
| `outline` | `ids` 또는 `path`; 생략 시 `scope`: selected/viewport/document. 선택적 `depth`, `field_groups`, `include_geometry`, `annotations` | 기본 개수·이름 요약. objects/annotations/transforms를 선택해 필요한 상세만 조회. |
| `resolve-block`  | `path=[최상위 GUID, 내부 멤버 GUID, ...]` | 현재 편집 단계에서 선택 가능한 블록 후보. |
| `sections` | `ids`, `axis`: X/Y/Z, `stations`; 선택적 `sample_points` | 지정 좌표의 절단 곡선 수·길이·bbox·표본점. Brep·Mesh·Extrusion 지원.|
| `vertical-probe` | `ids`, `xy=[[x,y],...]`; 선택적 `z_min`, `z_max`는 함께 지정 | 표본 수직선의 교차 Z와 닫힌 형상의 채움·중복 구간. 열린 형상은 교차점만 반환. |
| `joint-pairs` | `pairs=[[GUID_A,GUID_B],...]`; 선택적 `tolerance`, `compare_operations`, `max_pairs` | 유효 닫힌 최상위 Brep·Extrusion 쌍의 교차체적과 선택적 Join/Union 결과. |

outline의 field_groups는 options 안에 두며 summary/objects/annotations/transforms의 비어 있지 않은 배열이다. 일반 조회와 달리 명시 []나 all은 지원하지 않는다. 기존 include_geometry/annotations의 명시 상세 요청도 유지되며, max_items/방문 budget과 truncation을 확인해 IDs·branch path·depth를 좁힌다.
