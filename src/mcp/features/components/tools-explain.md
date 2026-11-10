# tools.py explain

## upsert_ontological_holon

<!-- instruction:upsert_ontological_holon -->
물리적 요소와 관계의 역할·동작·구조를 Holon으로 등록하거나 갱신합니다. 직접 객체 소유권은 Holon 하나에 속합니다. 기존 그룹 이름 변경은 거부하며, 불확실한 결과나 Undo 뒤에는 현재 상태를 확인합니다.

반환: status와 holon의 ID·그룹·상태 등 등록 확인 정보를 반환합니다.

Args:
    name: 의미적 Holon 이름입니다. 기존 Rhino 그룹에 연결할 때는 해당 그룹의 정확한 이름과 일치해야 합니다.
    object_ids: 등록할 현재 최상위 Rhino 객체 GUID입니다. 생략하면 이름이 지정된 기존 그룹을 찾아 사용할 수 있습니다. []는 child_holon_ids가 있는 부모에만 유효합니다.
    expected_model_path: 보통 생략합니다. 관리형 세션이 연결된 저장 Rhino 문서를 제공합니다. 경로를 명시하면 해당 연결과 일치해야 하며, 문서를 전환하지는 않습니다.
    scene_ids: 기존 Scene 소속 관계입니다. 새 Holon에는 필수입니다. 생략하면 기존 등록을 유지하며, Scene을 생성하지는 않습니다.
    holon_id: 수정할 기존 Holon ID입니다. 선택 사항이며, 생략하면 등록을 생성합니다.
    rhino_group_id: 기존 Rhino 그룹의 정확한 GUID입니다. 선택 사항이며, 이름의 모호성을 해소하는 데 사용합니다.
    child_holon_ids: 등록된 자식 Holon 목록입니다. 선택 사항이며, []는 기존 자식을 분리하고 생략하면 유지합니다. 자식당 부모는 하나만 허용하고 계층 순환을 금지합니다.
<!-- /instruction:upsert_ontological_holon -->

## get_ontological_holon

<!-- instruction:get_ontological_holon -->
Holon의 등록 요약이나 현재 Rhino 그룹 구성원을 조회합니다. 현재 상태 조회는 안정된 일반 모델에서 수행하며 그룹·블록 편집 중에는 오류를 반환합니다. 등록과 현재 상태의 차이는 응답에 표시합니다.

반환: holon의 저장 요약 또는 현재 구성원 관찰과 불일치 정보를 반환합니다. live_verified 등의 근거 범위를 확인합니다.

Args:
    holon_id: include_ids=true를 사용한 Holon 조회 또는 이전 등록 결과에서 얻은 등록된 Holon ID입니다.
    live: true이면 현재 Rhino 그룹 구성원 관계와 형상을 읽습니다. false이면 저장된 등록 정보만 읽습니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다.
    recursive: true이면 등록된 하위 Holon을 확장합니다. 이는 의미적 계층이며, 블록 정의 확장이 아닙니다.
    field_groups: 선택 사항인 상세 그룹: references, geometry, scope, audit 또는 all. 생략하거나 비워 두면 요약을 유지하며, include_ids는 식별 정보 포함 여부를 별도로 제어합니다.
<!-- /instruction:get_ontological_holon -->

## list_ontological_holons

<!-- instruction:list_ontological_holons -->
문서 또는 Scene 범위의 캐시된 Holon 등록 목록을 조회합니다. 현재 구성원은 get_ontological_holon이나 get_scene_objects로 확인합니다.

반환: holons와 total·live_verified를 반환합니다. 캐시된 등록 목록이므로 현재 구성원 검증은 별도 조회가 필요합니다.

Args:
    expected_model_path: 관리형 세션의 기본값은 연결된 모델입니다. 독립 실행에서 빈 입력을 사용하면 여러 모델의 등록 정보를 나열합니다. 활성 Rhino 문서를 전환하지 않습니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다.
    scene_id: 선택 사항인 등록된 Scene ID 필터입니다. 비어 있으면 Scene으로 필터링하지 않습니다.
    recursive: true이면 등록된 자식 Holon을 포함합니다.
    field_groups: 선택 가능한 세부 그룹은 references, geometry, scope, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별 정보는 include_ids로 별도 제어합니다.
<!-- /instruction:list_ontological_holons -->

## sync_ontological_holon

<!-- instruction:sync_ontological_holon -->
안정된 Rhino 편집 상태에서 현재 Holon 구성원을 읽어 등록 대장을 갱신합니다. 변경 뒤 등록과 현재 상태를 맞출 때 사용합니다.

반환: checked·changed·unavailable·problems와 scene_revisions·live_verified로 동기화 결과를 반환합니다.

Args:
    holon_id: 단일 대상의 상태 대조 및 정합성 확인에 사용할 등록된 Holon ID입니다. 선택 사항입니다.
    expected_model_path: 보통 생략합니다. 관리형 세션이 연결된 저장 Rhino 문서를 제공합니다. 경로를 명시하면 해당 연결과 일치해야 하며, 문서를 전환하지는 않습니다.
    rhino_group_id: holon_id와 함께 제공하는 선택 항목으로, 현재 Rhino 그룹 GUID의 일관성을 확인합니다. 이 값만으로 그룹을 선택하거나 연결 대상을 바꾸지 않습니다.
    holon_ids: 명시적 Holon ID 일괄 목록입니다. 선택 사항이며, 단일 Holon/그룹 선택자와 함께 사용하지 않습니다.
    scene_id: 일괄 상태 대조 및 정합성 확인에 사용할 Scene 범위입니다. 선택 사항이며, 새 Holon을 생성하거나 추론하지 않습니다.
<!-- /instruction:sync_ontological_holon -->

## remove_ontological_holon

<!-- instruction:remove_ontological_holon -->
Holon 등록을 해제하고 Rhino 형상·일반 그룹·객체 속성은 보존합니다. 부모와 Plan 참조를 먼저 해제해야 하며 자식 Holon은 독립된 등록 루트로 남습니다. 결과가 불확실하면 현재 등록 상태를 확인합니다.

반환: status와 해제된 holon 정보를 반환합니다.

Args:
    holon_id: include_ids=true를 지정한 Holon 조회 또는 이전 등록 결과에서 얻은 등록된 Holon ID입니다.
<!-- /instruction:remove_ontological_holon -->

## resolve_object_intersection

<!-- instruction:resolve_object_intersection -->
겹친 객체를 한 쌍씩 이미지로 비교하고 선택한 객체에서 겹친 부분을 제거합니다. 검토 중 실제 선택·카메라가 바뀝니다. 안정된 저장 문서와 래스터 모델 뷰포트가 필요하며, 설계 판단에 따라 명시적으로 대상을 선택합니다. 변경 결과가 불확실하면 진행을 멈추고 관찰합니다.

반환: state와 현재 검토 쌍·이미지 또는 적용 결과, skipped_pairs를 반환합니다. 검토 이미지의 review_id와 choice로 다음 결정을 제출합니다.

Args:
    object_ids: 검토 범위를 시작할 서로 다른 현재 최상위 객체 GUID 1..512개입니다. 선택 사항이며, 현재 범위를 이어서 검토하거나 선택을 제출할 때는 생략합니다.
    include_block: 새 검토 범위에 변환이 적용된 중첩 블록 구성원을 포함합니다. 기본값은 false입니다. 블록 정의 편집은 여전히 지원하지 않습니다.
    review_id: 반환된 결정 핸들로, choice와 함께 사용할 때 필수입니다. 화면에 표시된 연산 대상을 식별합니다. 완료되었거나 새 검토로 대체된 핸들로는 변경을 다시 실행할 수 없습니다.
    choice: 1 또는 2는 해당 번호의 객체에서 겹친 부분을 제거합니다. "skip"은 두 객체를 모두 그대로 둡니다. review_id를 제공하고 object_ids는 생략합니다. 확인/계속 진행하려면 choice를 생략합니다.
<!-- /instruction:resolve_object_intersection -->

## focus_holons

<!-- instruction:focus_holons -->
등록된 Holon과 하위 Holon의 현재 구성원을 Rhino에서 선택·격리·확대합니다. 카메라·선택·가시성이 바뀌며 잠긴 주변 객체는 보일 수 있습니다. 결과가 불확실하면 재실행 전에 화면 상태를 확인합니다.

반환: selected_ids, zoom_selected·isolated와 locked_context_remains_visible, restore_visibility_command 등을 반환합니다.

Args:
    holon_ids: 현재 유효 구성원으로 해석할 등록된 Holon ID 1..32개입니다. 확인된 최상위 객체는 최대 4096개를 지원합니다. 실제 선택, 격리 및 카메라를 변경합니다.
    expected_model_path: 일반적으로 생략합니다. 관리형 세션이 연결된 저장 Rhino 문서를 제공합니다. 명시한 경로는 이 연결 정보와 일치해야 하며, 문서를 전환하지는 않습니다.
<!-- /instruction:focus_holons -->

## response-566

<!-- instruction:response-566 -->
Load a Bridge with design_components=1 before registering Holons.
<!-- /instruction:response-566 -->

## response-571

<!-- instruction:response-571 -->
Load a Bridge with component_operations=1 before using Holon helpers.
<!-- /instruction:response-571 -->
