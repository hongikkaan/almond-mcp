# tools.py explain

## get_rhino_context

<!-- instruction:get_rhino_context -->
현재 Rhino 문서와 편집 상태, 뷰·디스플레이 모드를 조회합니다.

Args:
    sections: document, viewport, editor, display_modes, named_views, layouts, viewports 중 필요한 항목의 배열입니다. 생략하면 document, named_views, layouts, display_modes를 조회합니다. []는 status와 warnings만 반환합니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다.
    include_editor_details: editor를 요청한 경우에만 provider/command/Undo 근거를 포함합니다.
<!-- /instruction:get_rhino_context -->

## analyze_block_reculviely

<!-- instruction:analyze_block_reculviely -->
중첩 블록 구조와 특정 배치 경로의 공유 정의 영향을 조회합니다.

Args:
    mode: outline은 객체와 중첩 정의를 순회합니다. resolve-block은 명시적인 배치 인스턴스 경로를 해석하고 공유 정의에 미치는 영향을 보고합니다. 경로 해석에는 선택 가능 조건이 필요하지 않으며 편집기 소유 관계를 부여하지도 않습니다. 중첩 정의 구성원은 독립적인 편집 ID가 아닙니다.
    options: outline: ids(루트 GUID 배열) 또는 path(배치 GUID 경로)를 선택합니다. 둘 다 없으면 scope=selected|viewport|document로 범위를 정합니다. depth=0..64, max_items=1..5000, max_bytes=2048..262144이며 기본값은 각각 64, 200, 48000입니다. field_groups는 summary, objects, annotations, transforms 중 선택한 비어 있지 않은 배열입니다. include_geometry/annotations는 상세 포함 여부, annotation_layer는 텍스트 도트의 레이어 필터입니다. resolve-block: 최상위에서 내부 방향의 배치 GUID 1..65개를 path에 입력합니다.
    expected_model_path: 일반적으로 생략합니다. 런타임이 연결된 문서 경로를 제공합니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다.
<!-- /instruction:analyze_block_reculviely -->

## get_defined_viewcapture

<!-- instruction:get_defined_viewcapture -->
저장된 Named View 또는 Layout 용지를 작업 화면 전환 없이 캡처합니다.

Args:
    target_kind: named_view는 저장된 카메라를 사용하며, display_mode가 제공되지 않으면 기본값은 Shaded입니다. layout은 각 Detail의 기존 모드를 유지하며 display_mode 재정의를 허용하지 않습니다.
    target: 기존 이름 또는 ID입니다. 대소문자를 구분하지 않는 이름 일치는 유일해야 합니다.
    scale_percent: 범위는 1..100이며 기본값은 75입니다. 원하는 상한이며, 백분율 캡처는 전달 용량 제한에 맞게 축소될 수 있습니다.
    include_usage: 실제 치수와 설명용 픽셀 기반 토큰 추정치를 포함합니다. 측정된 사용량은 아닙니다.
    display_mode: Named View 전용: 생략하거나 비워 두면 Shaded를 선택하며, 다른 설치된 래스터 모드 이름/ID를 제공할 수도 있습니다. 단면 검토 시 display_modes에서 확인한 뒤 AGENT_Section_Glass를 고려합니다. Layout: 각 Detail의 기존 모드를 유지하려면 생략합니다. 재정의는 거부됩니다.
    labels: 선택 사항인 일시적 엔터티 레이블이며, 기본값은 false입니다.
    depth: 엔터티 레이블 확장 깊이이며, 범위는 1..8입니다.
    width: 선택 사항인 Named View의 픽셀 너비로, 범위는 128..2048입니다. height도 제공하고 scale_percent=100으로 설정합니다. Layout에는 사용하지 않습니다.
    height: 선택 사항인 Named View의 픽셀 높이로, 범위는 128..2048입니다. width도 제공하고 scale_percent=100으로 설정합니다. Layout에는 사용하지 않습니다.
    expected_model_path: 일반적으로 생략합니다. 런타임이 연결된 모델을 제공합니다.
<!-- /instruction:get_defined_viewcapture -->

## get_current_viewcapture

<!-- instruction:get_current_viewcapture -->
현재 모델 화면을 캡처합니다. 대상·격리·디스플레이 옵션을 지정하면 실제 화면에도 적용됩니다.

Args:
    target_ids: 객체, 그룹 또는 Holon ID로 구성된 선택 사항인 비어 있지 않은 문자열 배열입니다. 확인된 객체가 중복되면 한 번만 선택합니다.
    target_kind: object(기본값), group, block(일반 객체 ID) 또는 holon입니다. 허용할 형상 유형이 아니라 ID 이름 공간을 선택합니다.
    isolate: 기본값은 false입니다. true이면 Zoom Selected 전에 실제 Rhino Isolate를 실행합니다. 가시성을 복원하려면 Unisolate를 사용합니다.
    scale_percent: 범위는 1..100이며 기본값은 75입니다. 뷰포트 창 크기가 아니라 이미지 해상도를 변경합니다.
    include_usage: 치수와 설명용 픽셀 기반 토큰 추정치를 포함합니다. 측정된 사용량은 아닙니다.
    display_mode: 선택 사항인 설치된 래스터 모드 이름/ID입니다. 제공하면 실제 모델 뷰포트를 변경합니다.
    labels: 선택 사항인 일시적 레이블이며 기본값은 false입니다. 선택 강조 표시는 Rhino의 기본 표시를 유지합니다.
    depth: 레이블 확장 깊이이며, 범위는 1..8입니다.
    width: 선택 사항인 이미지의 픽셀 너비로, 범위는 128..2048입니다. height도 제공하고 scale_percent=100으로 설정합니다. Rhino 창 크기를 바꾸지는 않습니다.
    height: 선택 사항인 이미지의 픽셀 높이로, 범위는 128..2048입니다. width도 제공하고 scale_percent=100으로 설정합니다. Rhino 창 크기를 바꾸지는 않습니다.
    expected_model_path: 일반적으로 생략합니다. 런타임이 연결된 모델을 제공합니다.
<!-- /instruction:get_current_viewcapture -->
<!-- instruction:get_objects -->
Rhino 객체의 속성·그룹·블록 계층·Brep 면을 관찰합니다.

Args:
    scope: current(기본값)는 화면 밖에 있더라도 표시 상태이고 잠기지 않은 모델 객체를 포함합니다. document는 숨김/잠금 객체도 포함합니다.
    object_ids: document 범위에서만 사용할 수 있는 선택 사항인 서로 다른 최상위 객체 GUID입니다(1..4096개). group_ids와 함께 사용하지 않습니다.
    filters: AND 조건입니다. layer_paths(정확한 전체 경로), object_types(관찰된 Rhino 이름), name_contains(대소문자 구분 없음), user_dictionary(source=attributes|geometry, key, 스칼라 any_of)를 사용할 수 있습니다.
    include_geometry: fields를 생략했을 때 objects 모드에서 형상 상세 정보를 포함합니다. 명시적인 fields가 우선합니다.
    offset: 행 오프셋으로, 범위는 0..100000입니다. 0보다 큰 값에는 첫 페이지의 expected_snapshot이 필요합니다.
    limit: 페이지당 행 수입니다. 범위는 1..200이며 기본값은 50입니다.
    expected_model_path: 일반적으로 생략합니다. 런타임이 연결된 저장 문서를 제공합니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다.
    result_mode: objects(기본값), hierarchy 또는 summary입니다. recursive=true는 hierarchy를 선택하며 summary와 함께 사용할 수 없습니다.
    fields: 선택 사항인 비어 있지 않은 필드 목록입니다. id, name, layer_path, object_type, geometry_kind, geometry_crc, visible, selected, hidden, locked, bounds, groups, user_dictionary, geometry_valid, solid, manifold, volume, faces, face_count를 사용할 수 있습니다. 형상 상세 정보와 faces에는 objects 모드가 필요합니다. summary는 fields를 거부합니다.
    face_offset: 면 페이지 오프셋이며 기본값은 0입니다. 두 번째 이후 면 페이지에는 document 범위의 object_ids와 모든 객체에 대한 expected_geometry_crcs가 필요합니다.
    face_limit: 객체별 페이지의 면 수입니다. 범위는 1..128이며 기본값은 128입니다. 면 옵션에는 objects 모드가 필요합니다.
    expected_geometry_crcs: 요청한 각 객체 GUID를 키로 하는 관찰된 CRC입니다. 면을 페이지 단위로 조회하는 동안 형상이 변경되면 거부합니다.
    group_ids: 어느 scope에서든 사용할 수 있는 선택 사항인 서로 다른 Rhino 그룹 GUID입니다(1..64개). 구성원과 선택한 범위의 교집합을 사용합니다. object_ids와 함께 사용하지 않습니다.
    selected: current에서만 사용하며 기본값은 false입니다. 화면 밖의 선택도 포함하여 적격한 선택 객체로 필터링합니다. inside_window와 함께 사용할 수 없습니다.
    inside_window: current에서만 사용하며 기본값은 false입니다. 활성 뷰포트 경계에 걸친 바운딩 박스를 포함합니다. 클리핑 평면이나 픽셀 가림 검사는 수행하지 않습니다. selected와 함께 사용할 수 없습니다.
    recursive: 그룹과 블록 배치 인스턴스를 계층 구조로 함께 펼칩니다. 기본값은 false입니다.
    depth: 계층 깊이는 1..8이며 루트는 1입니다. 1보다 큰 값에는 recursive=true가 필요합니다.
    expected_snapshot: 첫 페이지에서는 생략합니다. 이후 offset 페이지에는 첫 페이지의 snapshot 토큰을 변경 없이 전달합니다. 스냅샷이 변경되면 이어서 조회하는 요청을 거부합니다.
<!-- /instruction:get_objects -->

<!-- instruction:get_object_intersections -->
닫힌 솔리드 사이에서 부피가 겹치는 객체 쌍을 찾습니다.

Args:
    object_ids: 서로 다른 현재 최상위 Rhino 객체 GUID 1..512개입니다. 내부 페이지 처리를 통해 하나의 범위로 검사합니다.
    include_block: true이면 변환이 적용된 중첩 블록 구성원까지 펼칩니다. 기본값 false는 범위에서 블록을 제외합니다.
<!-- /instruction:get_object_intersections -->

<!-- instruction:capture_rhino_inspection -->
작업 화면을 유지하면서 여러 시점과 객체 범위를 하나의 PNG로 비교합니다.

Args:
    views: 타일 객체 1..16개입니다. direction 기본값은 current이며, 선택지는 current, top, bottom, front, back, left, right, iso_ne, iso_nw, iso_se, iso_sw, below_ne, below_nw, below_se, below_sw입니다. display_mode는 선택 사항인 설치된 이름/GUID(최대 512자)이며, label도 선택 사항(최대 120자)입니다. 선택 사항인 object_ids에는 서로 다른 최상위 GUID 1..512개를 넣습니다. ID를 생략하거나 비워 두면 공통 object_ids가 제공된 경우를 제외하고 문서 가시성을 사용합니다.
    width: 타일의 픽셀 너비로, 범위는 128..2048이며 기본값은 640입니다. 결합 이미지 제한도 적용됩니다.
    height: 타일의 픽셀 높이로, 범위는 128..2048이며 기본값은 480입니다. 결합 이미지 제한도 적용됩니다.
    columns: 선택 사항인 열 개수이며, 범위는 1..뷰 개수입니다. 생략하면 자동 격자를 사용합니다.
    expected_model_path: 일반적으로 생략합니다. 런타임이 연결된 저장 문서를 제공합니다.
    model_view_id: 선택 사항인, 목록에 있는 모델 뷰포트 GUID입니다. Layout/Detail이 활성화된 경우를 포함하여 해당 뷰포트를 활성화하지 않고 사용합니다.
    object_ids: 모든 타일에 공통으로 적용할, 서로 다른 최상위 GUID 1..4096개의 선택 사항인 집합입니다. 비어 있지 않은 타일별 object_ids와 함께 사용하지 않습니다.
<!-- /instruction:capture_rhino_inspection -->
