### 조회·화면 도구

ID가 필요한 조회에는 `include_ids=True`를 사용한다. 이미 프로젝트 정보에서 확인한 문서를 같은 목적으로 다시 조회할 필요는 없다.

도면·유닛의 위치나 작업 시점이 불명확하면 질문 전에 `get_rhino_viewport_image(view="a")`로 기존 Named View·Layout을 먼저 찾는다. 선택한 GUID를 캡처해 표제와 실제 대상·주변 관계를 대조한다. 이름만으로 범위를 확정하거나 조회를 위해 새 Named View를 만들지는 않는다.

| 도구 | 입력 | 할 수 있는 일 |
| ---- | ---- | --- |
| `get_rhino_context`  | `sections=["selection"]` 또는 `["viewport"]`, 선택적 `selection_limit` | 현재 선택 객체 또는 카메라·화면 정보 조회.|
| `get_selection_references` | 선택적 `selection_limit`, `limit` | 선택 객체에 연결된 ontological-component·Task·Step 역조회. |
| `get_rhino_probe` | 아래의 `probe`와 `options` | 형상·블록을 읽기 전용으로 관찰·측정.  |
| `get_rhino_viewport_image` | 현재 화면은 생략, 목록은 `view="a"`, 지정 뷰는 `view=GUID`; 선택적 `scale_percent` | viewport·Named View·Layout 목록 또는 PNG 캡처. 기본 크기 50%. |
| `focus_components`| `component_ids` | 해당 ontological-component 선택·격리·확대. 화면 상태가 바뀐다. |

`get_rhino_probe`의 옵션은 아래와 같다. 좌표·길이·공차는 현재 문서 단위다. 반환의 `unknown`·미지원·`truncated`는 미확인 범위이며 0이나 통과를 뜻하지 않는다. 범위가 잘리면 대상·표본을 나눠 조회한다.

| probe 값  | options에 넣을 입력  | 알 수 있는 것|
| ----- | ----- | ----- |
| `outline` | `ids` 또는 `path`; 생략 시 `scope`: selected/viewport/document. 선택적 `depth`, `include_geometry`, `annotations` | 객체·중첩 블록 경로·누적 변환·TextDot 주석과 동명 대상. |
| `resolve-block`  | `path=[최상위 GUID, 내부 멤버 GUID, ...]` | 현재 편집 단계에서 선택 가능한 블록 후보. |
| `sections` | `ids`, `axis`: X/Y/Z, `stations`; 선택적 `sample_points` | 지정 좌표의 절단 곡선 수·길이·bbox·표본점. Brep·Mesh·Extrusion 지원.|
| `vertical-probe` | `ids`, `xy=[[x,y],...]`; 선택적 `z_min`, `z_max`는 함께 지정 | 표본 수직선의 교차 Z와 닫힌 형상의 채움·중복 구간. 열린 형상은 교차점만 반환. |
| `joint-pairs` | `pairs=[[GUID_A,GUID_B],...]`; 선택적 `tolerance`, `compare_operations`, `max_pairs` | 유효 닫힌 최상위 Brep·Extrusion 쌍의 교차체적과 선택적 Join/Union 결과. |
