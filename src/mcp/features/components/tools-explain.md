# tools.py explain

## upsert_ontological_holon

<!-- instruction:upsert_ontological_holon -->
물리적 요소와 관계를 Holon으로 등록하거나 갱신합니다.

Args:
    name: 의미적 Holon 이름입니다. 기존 Rhino 그룹에 연결할 때는 해당 그룹의 정확한 이름과 일치해야 합니다.
    object_ids: 등록할 최상위 Rhino 객체 GUID 배열입니다. 각 객체는 하나의 Holon에 속합니다. 생략하면 name과 일치하는 기존 그룹을 사용합니다. []는 child_holon_ids가 있는 부모에만 사용합니다.
    expected_model_path: 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
    scene_ids: Holon이 속할 기존 Scene ID 배열입니다. 새 Holon에는 필수이며, 수정 시 생략하면 유지합니다.
    holon_id: 수정할 기존 Holon ID입니다. 선택 사항이며, 생략하면 등록을 생성합니다.
    rhino_group_id: 기존 Rhino 그룹의 정확한 GUID입니다. 선택 사항이며, 이름의 모호성을 해소하는 데 사용합니다.
    child_holon_ids: 등록된 자식 Holon 목록입니다. 선택 사항이며, []는 기존 자식을 분리하고 생략하면 유지합니다. 자식당 부모는 하나만 허용하고 계층 순환을 금지합니다.
<!-- /instruction:upsert_ontological_holon -->

## get_ontological_holon

<!-- instruction:get_ontological_holon -->
Holon의 등록 정보와 구성원을 조회합니다.

Args:
    holon_id: include_ids=true를 사용한 Holon 조회 또는 이전 등록 결과에서 얻은 등록된 Holon ID입니다.
    live: true이면 현재 Rhino 그룹 구성원 관계와 형상을 읽습니다. false이면 저장된 등록 정보만 읽습니다.
    include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
    recursive: true이면 등록된 하위 Holon을 확장합니다. 이는 의미적 계층이며, 블록 정의 확장이 아닙니다.
    field_groups: 선택 사항인 상세 그룹: references, geometry, scope, audit 또는 all. 생략하거나 비워 두면 요약을 조회합니다.
<!-- /instruction:get_ontological_holon -->

## list_ontological_holons

<!-- instruction:list_ontological_holons -->
등록된 Holon 목록을 조회합니다.

Args:
    expected_model_path: 관리형 세션의 기본값은 연결된 모델입니다. 독립 실행에서 빈 입력을 사용하면 여러 모델의 등록 정보를 나열합니다. 활성 Rhino 문서를 전환하지 않습니다.
    include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
    scene_id: 선택 사항인 등록된 Scene ID 필터입니다. 비어 있으면 Scene으로 필터링하지 않습니다.
    recursive: true이면 등록된 자식 Holon을 포함합니다.
    field_groups: 선택 가능한 세부 그룹은 references, geometry, scope, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다.
<!-- /instruction:list_ontological_holons -->

## sync_ontological_holon

<!-- instruction:sync_ontological_holon -->
Rhino의 현재 구성원을 읽어 Holon 등록 정보를 갱신합니다.

Args:
    holon_id: 단일 대상의 상태 대조 및 정합성 확인에 사용할 등록된 Holon ID입니다. 선택 사항입니다.
    expected_model_path: 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
    rhino_group_id: holon_id와 함께 제공하는 선택 항목으로, 현재 Rhino 그룹 GUID의 일관성을 확인합니다. 이 값만으로 그룹을 선택하거나 연결 대상을 바꾸지 않습니다.
    holon_ids: 명시적 Holon ID 일괄 목록입니다. 선택 사항이며, 단일 Holon/그룹 선택자와 함께 사용하지 않습니다.
    scene_id: 구성원을 갱신할 Scene ID입니다. holon_id, holon_ids, rhino_group_id와 함께 입력하지 않습니다.
<!-- /instruction:sync_ontological_holon -->

## remove_ontological_holon

<!-- instruction:remove_ontological_holon -->
Holon 등록을 해제하고 Rhino 형상과 그룹은 유지합니다.

Args:
    holon_id: 등록을 해제할 Holon ID입니다. 이 Holon을 참조하는 부모 Holon과 Plan의 관계를 먼저 해제합니다.
<!-- /instruction:remove_ontological_holon -->

## resolve_object_intersection

<!-- instruction:resolve_object_intersection -->
겹친 객체 쌍을 이미지로 검토하고 선택한 객체에서 겹친 부분을 제거합니다. 검토 시 실제 카메라와 선택이 바뀝니다.

Args:
    object_ids: 검토 범위를 시작할 서로 다른 현재 최상위 객체 GUID 1..512개입니다. 선택 사항이며, 현재 범위를 이어서 검토하거나 선택을 제출할 때는 생략합니다.
    include_block: 새 검토 범위에 변환이 적용된 중첩 블록 구성원을 포함합니다. 기본값은 false입니다. 블록 정의 편집은 여전히 지원하지 않습니다.
    review_id: 반환된 결정 핸들로, choice와 함께 사용할 때 필수입니다. 화면에 표시된 연산 대상을 식별합니다. 완료되었거나 새 검토로 대체된 핸들로는 변경을 다시 실행할 수 없습니다.
    choice: 1 또는 2는 해당 번호의 객체에서 겹친 부분을 제거합니다. "skip"은 두 객체를 모두 그대로 둡니다. review_id를 제공하고 object_ids는 생략합니다. 확인/계속 진행하려면 choice를 생략합니다.
<!-- /instruction:resolve_object_intersection -->

## focus_holons

<!-- instruction:focus_holons -->
Holon과 하위 Holon의 현재 구성원을 Rhino에서 선택·격리·확대합니다.

Args:
    holon_ids: 현재 유효 구성원으로 해석할 등록된 Holon ID 1..32개입니다. 확인된 최상위 객체는 최대 4096개를 지원합니다. 실제 선택, 격리 및 카메라를 변경합니다.
    expected_model_path: 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
<!-- /instruction:focus_holons -->

## response-566

<!-- instruction:response-566 -->
Load a Bridge with design_components=1 before registering Holons.
<!-- /instruction:response-566 -->

## response-571

<!-- instruction:response-571 -->
Load a Bridge with component_operations=1 before using Holon helpers.
<!-- /instruction:response-571 -->
