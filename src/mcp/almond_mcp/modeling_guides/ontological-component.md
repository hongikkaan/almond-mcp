### Scene·ontological_component

<a name="sceneontological-componentinstance"></a>

Scene은 행태·프로그램·장면의 맥락이고, ontological_component는 그 장면을 가능하게 하는 건축 요소와 의미의 묶음이다. 등록할 때는 해당 Scene 맥락을 반드시 지정하며 여러 Scene에 참여할 수 있다. Scene에는 의미 단위 밖의 객체도 직접 연결할 수 있다. 기본 모델링은 Scene·ontological_component와 실제 Rhino group/block을 사용한다. 자산 배치용 Almond Instance 대장은 기본 작업에 추가하지 않는다.

#### Scene

Scene은 특정 공간에서 일어나는 **행태·프로그램·장면·가치**다. 파일 전체를 Scene 하나로 치환하지 않는다. Scene의 `file_name`을 필요할 때 조회해 현재 활성 파일과 대조한다. 이 필드는 작업 문서의 안내 정보이며 파일을 이동하거나 문서를 자동 전환하지 않는다.

| 도구 | 입력 | 할 수 있는 일 |
| -- | ----- | --- |
| `list_design_scenes` | 선택적 `name`, `file_name`, `limit=50`, `offset=0`, `field_groups`, `include_ids` | 프로젝트 전체 Scene 이름의 제한된 페이지 조회. |
| `get_design_scene` | `scene_id`, 선택적 `field_groups`, `include_ids` | Scene 요약·개수와 필요한 상세 조회. |
| `create_design_scene` | `name`, 선택적 `units`, `file_name` | Scene 생성. |
| `update_design_scene` | `scene_id`, `file_name` | 기존 Scene의 파일명 기록. |
| `register_scene_objects` | `scene_id`, 최상위 `object_ids`, `mode`: add/remove/replace | ontological_component 없이 객체를 Scene에 직접 연결·해제.|
| `get_scene_objects`| `scene_id`, 선택적 `limit=50`, `offset=0`, `field_groups`, `include_ids` | 직접 연결 객체와 하위 ontological_component 객체의 합집합을 페이지로 조회. |

Scene 이름만 필요하면 `list_design_scenes()`를 사용한다. Plan·live 문서·SQLite 직접 조회 없이 여러 파일과 빈 Scene까지 포함한다. `name`은 대소문자를 구분하지 않는 부분검색이고 `file_name`은 정확한 필터다. 기본 행은 이름만 반환하며 선택용 handle은 `include_ids=true`, 파일명·단위는 `field_groups=["scope"]`, revision은 `["state"]`로 추가한다. 목록과 객체 페이지의 limit은 1–200이며 total·truncated를 확인한다. Scene 삭제 도구는 없고 등록 변경에는 공개 도구를 사용한다.

#### ontological_component

<a name="ontological-component"></a>

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
| `list_design_components`  | 선택적 `scene_id`, `recursive=false`, `field_groups`, `include_ids` | 지정 Scene 또는 연결 문서의 등록 root 목록 조회. |
| `get_design_component` | `component_id`, 선택적 `live=false`, `recursive=false`, `field_groups`, `include_ids` | 저장 요약 또는 현재 group 관찰. 상세와 자손 형상은 명시 요청. |
| `upsert_design_component` | `name`, 직접 소유 `object_ids`, `scene_ids`, 선택적 기존 ID·group GUID·`child_component_ids` | 의미 등록·Scene/자식 관계 변경·일치하는 기존 group 채택. |
| `sync_design_component`| `component_id` 또는 `component_ids` 또는 `scene_id`; 생략은 연결 문서 | 안정된 Rhino 기준으로 선택 범위를 한 번 정합. |
| `remove_design_component` | `component_id` | ontological_component 등록 해제. 형상과 group은 유지. |

등록하려는 사용·행태·역할을 설명하는 Scene을 먼저 선택한다. `scene_ids`에는 기존 Scene을 한 개 이상 지정한다. 이 Scene 귀속은 단순한 API 우회용 값이 아니며, 파일 전체를 의미 없이 Scene으로 만들지 않는다.

등록은 객체 속성 대신 **문서 private registry**에 의미 handle·영속 group GUID·Scene·명시한 semantic 자식 관계를 저장한다. 현재 group의 이름·멤버가 기준이며 객체의 직접 소유 관계는 이 구조에서 계산한다. 기존 group은 현재 이름과 실제 멤버가 일치해야 하고, 같은 구성이 여러 개면 group GUID를 지정한다. upsert는 형상 교체·멤버 복구·기존 group rename 도구가 아니다. 일반 Rhino group 이름을 바꾼 뒤 query/정합으로 반영한다.

등록·Scene 관계 변경·해제의 semantic Undo와 Rhino group-table 동작을 구별한다. 명시 생성한 group의 등록을 Undo하면 원래 객체 membership은 복원되고 의미 등록은 비활성화되며 빈 group-table 항목이 남을 수 있다. 같은 이름의 live group이 있으면 새 생성은 suffix를 붙이지 않고 거절한다. 기존 group rename/delete의 일반 Undo 복구를 약속하거나 등록을 자동 재실행·멤버 복구하지 않는다.

일반 조회는 DB snapshot이다. 수동 편집·Undo/Redo 또는 멤버 교체가 있었으면 한 편집 묶음이 끝난 뒤 영향받은/dirty 등록 범위를 한 번 정합한다. 목록 전체에 `get(live=True) → sync → get`을 반복하지 말고 현재 schema가 제공하는 범위 정합 도구를 사용한다. 이름·색 변경만으로 멤버십 정합을 반복하지 않는다. 기존 정보 수정 시 생략한 인자는 유지되며 `child_component_ids=[]`는 자식 분리다.

목록은 기본적으로 범위의 root만 반환하고 `recursive=true`로 등록 자손을 포함한다. parent가 다른 Scene에 있어도 해당 Scene에 직접 속한 child는 조회 범위에 남는다. 실제 형상이 필요할 때만 `field_groups=["geometry"]`, 관계는 `["references"]`를 요청하며 자손 형상은 recursive도 함께 선택한다. 경로는 연결이 공급하므로 Scene 조회를 위해 model_path를 기억해 반복 입력하지 않는다.

정합 대상 형식은 서로 섞지 않는다. 명시한 parent/Scene 범위는 등록 자손을 포함하고 최대 64개·native 응답 2 MiB를 넘으면 좁힌다. compact 결과의 checked·changed·unavailable·problems를 읽는다. 완전한 범위가 부족하다는 오류는 제시된 parent/required handle로 다음 범위를 명시하며, 불확실한 수정을 재실행하는 근거로 쓰지 않는다. 누락 group은 참조·history를 유지하고, 개별 오류는 관련 없는 정상 등록의 관찰을 막지 않는다.

정합의 형상 기준은 **현재 안정된 Rhino 문서의 group·멤버·block 배치**다. DB와 다르다는 이유로 형상을 재생성하거나 일반 group을 해체하지 않는다. GroupEdit·BlockEdit 등 편집 격리가 활성 또는 불명확하면 모드·대상을 확인하고 안정된 문서 상태가 될 때까지 삭제 판단·정합을 보류한다. 불완전한 관찰은 삭제의 증거가 아니다. 타임아웃·결과 불명확은 rollback이 아니므로 실제 완료 결과를 먼저 확인하며 자동 재시도하지 않는다.

component·Scene·Plan·Phase·재료 key 등 Almond 관리 UserStrings를 개별 객체에 신규 자동 기록하지 않는다. 기존 사용자 속성을 보존하고, 작업에 필요한 일반 layer·Name·재료 속성 편집과 구별한다. 등록 해제는 의미 등록의 제거이고 물리적 group/block 해체와 별개 결정이다.

#### Instance

Almond의 Instance는 **자산을 Scene의 어디에 어떻게 배치했는지 기록한 DB 항목**이다. `instance_id`로 식별하고 자산 `asset_id`, 위치·회전·축척, 선택적 Rhino 객체 `rhino_guid`를 저장한다. Rhino block instance는 실제 모델 안의 블록 배치 객체이므로 서로 다른 개념이다. DB 배치 기록만으로 Rhino 객체가 생성되는 것도 아니다.

Almond Instance와 Room은 기존 자산 배치 검사에 남아 있는 기능이며 현재 기본 작업에서는 사용하지 않는다. Rhino block의 재사용·편집은 아래 Block 항목을 따른다.
