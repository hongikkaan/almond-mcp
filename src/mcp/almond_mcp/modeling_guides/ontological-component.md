### Scene·ontological_component

Scene은 행태·프로그램·장면의 맥락이고, ontological_component는 그 장면을 가능하게 하는 건축 요소와 의미의 묶음이다. 등록할 때는 해당 Scene 맥락을 반드시 지정하며 여러 Scene에 참여할 수 있다. Scene에는 의미 단위 밖의 객체도 직접 연결할 수 있다. 기본 모델링은 Scene·ontological_component와 실제 Rhino group/block을 사용한다. 자산 배치용 Almond Instance 대장은 기본 작업에 추가하지 않는다.

#### Scene

Scene은 특정 공간에서 일어나는 **행태·프로그램·장면·가치**다. 파일 전체를 Scene 하나로 치환하지 않는다. Scene의 `file_name`을 필요할 때 조회해 현재 활성 파일과 대조한다. 이 필드는 작업 문서의 안내 정보이며 파일을 이동하거나 문서를 자동 전환하지 않는다.

| 도구 | 입력 | 할 수 있는 일 |
| -- | ----- | --- |
| `get_design_scene` | `scene_id` | Scene의 이름·파일명·연결 정보 조회. |
| `create_design_scene` | `name`, 선택적 `units`, `file_name` | Scene 생성. |
| `update_design_scene` | `scene_id`, `file_name` | 기존 Scene의 파일명 기록. |
| `register_scene_objects` | `scene_id`, 최상위 `object_ids`, `mode`: add/remove/replace | ontological_component 없이 객체를 Scene에 직접 연결·해제.|
| `get_scene_objects`| `scene_id` | 직접 연결 객체와 하위 ontological_component 객체의 합집합 조회. |

현재 전체 Scene 목록·삭제 도구는 없다. 기존 Scene ID는 작업 맥락과 연결 기록에서 찾는다. 등록 정보 변경에는 공개 도구를 사용한다.

#### ontological_component

ontological_component는 **건축 요소와, 그 요소들이 함께 가능하게 하는 사용·행태·구조적 역할을 묶은 의미 단위**다. 무엇을 만들었는지와 그 묶음이 무엇을 가능하게 하는지를 함께 설명할 수 있어야 한다. 객체 종류·재료·거리만으로 경계를 정하지 않는다. 예를 들어 창문 하나를 일률적으로 ontological_component로 등록하는 대신, 바깥 풍경을 보며 머무르는 장소를 만드는 벽·창문 등의 관계를 보고 묶는다.

이렇게 정한 객체들을 한 `.3dm` 안에서 Rhino group으로 정의하고 ontological_component로 등록한다. **일반 group이 자동으로 ontological_component가 되는 것은 아니다.** 그 의미 단위를 구현하는 내부 구축 시스템·부재·element는 일반 group이나 block으로 정리한다. 이 내부 묶음은 조립·반복·선택·편집을 위한 것으로, 그 자체를 별도 ontological_component로 등록할 이유가 되지는 않는다. **ontological_component는 건축 요소와 의미를 함께 정의하고, 내부 group/block은 그 실물의 구축·모델링 구성을 정리한다.**

사례 사진 — 마루·계단참·지지 구조·가구의 공간 관계: `get_modeling_guide(topic="ontological-component-evidence", include_images=true)`.

작은 계단참과 마루에서 사람들이 머물고 교류하는 행태가 Scene이다. 그 Scene을 이루는 ontological_component는 다음처럼 **실물 구성과 그것이 가능하게 하는 것**을 함께 갖는다.

| ontological_component | 함께 구성하는 요소와 의미 |
|---|---|
| 마루 위 공간을 지지하는 구조 | 기둥·보 여러 개가 함께 위에서 오는 하중을 지지한다. 기둥마다 따로 등록하지 않는다. |
| 사람들이 걸터앉는 마루·계단참 | 지지 콘크리트와 마루 마감이 함께 단차와 앉을 자리를 만든다. 마루라는 실물이면서 걸터앉을 수 있게 하는 장치다. 공유 바닥슬래브 전체를 포함할 필요는 없다. |
| 마루에서 바둑 두는 가구 묶음 | 방석·낮은 탁자·바둑판·바둑알과 통·시계 등이 함께 앉아서 바둑 두는 행위를 가능하게 하고 유도한다. 가구 하나씩 나누지 않고, 그 행위와 사용 관계로 묶는다. |

사례 사진 — 지붕과 우수관: `get_modeling_guide(topic="ontological-component-evidence", include_images=true)`.

지붕의 의미에는 덮는 역할과 함께 집수·배수가 이어진다. 우수관이 여러 층을 지나거나 기둥 속 콘크리트에 매립돼 있어도 그 역할이 이어지므로 지붕 ontological_component에 포함한다. 지붕 안의 구축 시스템과 우수관 element들은 일반 group으로 나눠 관리할 수 있다. **물리적으로 떨어져 있어도 하나의 역할을 이루면 같은 ontological_component가 될 수 있다.** 두 사례의 사용자 설명 원문과 사진(`get_modeling_guide(topic="ontological-component-evidence", include_images=true)`)은 별도로 보존한다.

| 도구 | 입력 | 할 수 있는 일 |
| --- | ----- | -- |
| `list_design_components`  | 선택적 `include_ids` | 연결 문서의 등록 ontological_component 목록 조회. |
| `get_design_component` | `component_id`, 선택적 `live=True` | 저장 정보 또는 실제 group·멤버·미등록 후보 조회. |
| `upsert_design_component` | `name`, 직접 소유 `object_ids`, `scene_ids`, 선택적 기존 ID·group GUID·`child_component_ids` | ontological_component 생성·구성 변경·기존 group 채택. |
| `sync_design_component`| `component_id`, 선택적 `rhino_group_id` | 실제 group에 맞춰 멤버십·등록 정보를 정합.  |
| `remove_design_component` | `component_id` | ontological_component 등록 해제. 형상과 group은 유지. |

등록하려는 사용·행태·역할을 설명하는 Scene을 먼저 선택한다. `scene_ids`에는 기존 Scene을 한 개 이상 지정한다. 이 Scene 귀속은 단순한 API 우회용 값이 아니며, 파일 전체를 의미 없이 Scene으로 만들지 않는다.

일반 조회는 DB snapshot이다. 수동 편집·Undo/Redo 또는 멤버 교체가 있었으면 한 편집 묶음이 끝난 뒤 영향받은/dirty 등록 범위를 한 번 정합한다. 목록 전체에 `get(live=True) → sync → get`을 반복하지 말고 현재 schema가 제공하는 범위 정합 도구를 사용한다. 이름·색 변경만으로 멤버십 정합을 반복하지 않는다. 기존 정보 수정 시 생략한 인자는 유지되며 `child_component_ids=[]`는 자식 분리다.

정합의 형상 기준은 **현재 안정된 Rhino 문서의 group·멤버·block 배치**다. DB와 다르다는 이유로 형상을 재생성하거나 일반 group을 해체하지 않는다. GroupEdit·BlockEdit 등 편집 격리가 활성 또는 불명확하면 모드·대상을 확인하고 안정된 문서 상태가 될 때까지 삭제 판단·정합을 보류한다. 불완전한 관찰은 삭제의 증거가 아니다. 타임아웃·결과 불명확은 rollback이 아니므로 실제 완료 결과를 먼저 확인하며 자동 재시도하지 않는다.

component·Scene·Plan·Phase·재료 key 등 Almond 관리 UserStrings를 개별 객체에 신규 자동 기록하지 않는다. 기존 사용자 속성을 보존하고, 작업에 필요한 일반 layer·Name·재료 속성 편집과 구별한다. 등록 해제는 의미 등록의 제거이고 물리적 group/block 해체와 별개 결정이다.

#### Instance

Almond의 Instance는 **자산을 Scene의 어디에 어떻게 배치했는지 기록한 DB 항목**이다. `instance_id`로 식별하고 자산 `asset_id`, 위치·회전·축척, 선택적 Rhino 객체 `rhino_guid`를 저장한다. Rhino block instance는 실제 모델 안의 블록 배치 객체이므로 서로 다른 개념이다. DB 배치 기록만으로 Rhino 객체가 생성되는 것도 아니다.

Almond Instance와 Room은 기존 자산 배치 검사에 남아 있는 기능이며 현재 기본 작업에서는 사용하지 않는다. Rhino block의 재사용·편집은 아래 Block 항목을 따른다.
