# tools.py explain

## get_rhino_context

<!-- instruction:get_rhino_context -->
연결된 Rhino 문서·뷰·편집 상태와 저장된 Named View·Layout·표시 모드를 조회합니다.

- `document`: 단위·공차·변경 여부·객체와 레이어 수
- `viewport` / `viewports`: 활성 화면의 카메라·투영·표시 모드 / 뷰포트 목록
- `editor`: 편집 모드와 안정성
- `named_views` / `layouts` / `display_modes`: 저장된 뷰·용지·표시 모드 목록

**Named View·Layout·표시 모드 목록의 ID**는 `include_ids`와 무관하게 반환됩니다. 화면 이미지 캡처는 `capture_03-current_view` tool을 사용합니다.

Args:
    sections: document, viewport, editor, viewports, named_views, layouts, display_modes 중 선택.
        생략 또는 null은 document, named_views, layouts, display_modes. []는 status와 warnings만.
    include_ids: viewport 등에서 ID 포함. 기본 false.
    include_editor_details: editor 요청 시 공급자·명령·Undo 근거 포함. 기본 false.
<!-- /instruction:get_rhino_context -->

## analyze_block_reculviely

<!-- instruction:analyze_block_reculviely -->
중첩 블록 구조와 특정 배치 경로의 공유 정의 영향을 조회합니다. 읽기 전용입니다.

- outline: 기본적으로 선택된 루트의 요약. ids·path·scope로 대상을 정하고 field_groups로 상세를 선택합니다.
- resolve-block: 루트부터 대상 블록까지의 path로 정의의 공유 배치와 참조·링크 제한을 확인합니다.
- truncated·depth_limited: 조회 범위의 제한. definition_impact의 complete는 영향 범위 계수 완료 여부, occurrences_truncated는 반환 목록의 잘림 여부입니다.
- 정의 내부 ID는 현재 편집 가능한 문서 객체 ID와 다를 수 있습니다. 후속 호출에 ID가 필요하면 include_ids=true를 사용합니다.

Args:
    mode: outline | resolve-block
    options: outline: ids 또는 path. 생략 시 scope=selected(기본)|viewport|document.
        depth 0..64(기본 64), max_items 1..5000(기본 200), max_bytes 2048..262144(기본 48000).
        field_groups: summary(기본), objects, annotations, transforms 중 선택.
        include_geometry, annotations, annotation_layer: 형상·주석 출력 및 TextDot 레이어 필터.
        field_groups 생략 + include_geometry 또는 annotations 지정: legacy 상세 모드.
        resolve-block: path에 최상위부터 목표 블록까지 GUID 1..65개.
    expected_model_path: 생략: 연결 문서. 지정 시 경로 일치 검사.
    include_ids: 기본 false.
<!-- /instruction:analyze_block_reculviely -->

## get_defined_viewcapture

<!-- instruction:get_defined_viewcapture -->
저장된 Named View 또는 Layout 용지를 PNG로 캡처합니다. 이름·ID는 inspect_03-get_document_context tool에서 조회합니다.

Named View는 저장된 카메라를 사용하고, Layout은 용지와 Detail의 기존 표시 모드를 사용합니다. Layout에는 픽셀 크기와 display_mode를 지정할 수 없습니다. 이미지와 image_file 저장 결과는 별개이며, 사용량 추정·경고는 별도 text content로 반환됩니다. Layout Detail 레이블은 지원하지 않습니다.

Args:
    target_kind: named_view | layout.
    target: 기존 이름 또는 ID입니다. 대소문자를 구분하지 않는 이름 일치는 유일해야 합니다.
    scale_percent: 범위는 1..100이며 기본값은 75입니다. 원하는 상한이며, 백분율 캡처는 전달 용량 제한에 맞게 축소될 수 있습니다.
    include_usage: true이면 이미지 크기와 픽셀 기준 토큰 추정치를 포함합니다.
    display_mode: Named View 전용. 기본 Shaded; 설치된 래스터 모드 이름 또는 ID.
    labels: 기본 false. 최대 200개; 주변 레이블이 겹칠 수 있음.
    depth: 레이블 깊이: 1..8, 기본 1.
    width: 선택 사항인 Named View의 픽셀 너비로, 범위는 128..2048입니다. height도 제공하고 scale_percent=100으로 설정합니다. Layout에는 사용하지 않습니다.
    height: 선택 사항인 Named View의 픽셀 높이로, 범위는 128..2048입니다. width도 제공하고 scale_percent=100으로 설정합니다. Layout에는 사용하지 않습니다.
    expected_model_path: 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
<!-- /instruction:get_defined_viewcapture -->

## get_current_viewcapture

<!-- instruction:get_current_viewcapture -->
현재 Rhino 모델 뷰포트를 PNG로 캡처합니다. 대상 지정 시 실제 선택과 카메라가 바뀌며, isolate와 display_mode도 실제 화면 상태를 변경합니다. 격리 해제는 Rhino Unisolate를 사용합니다. 잠긴 주변 객체는 보일 수 있고, 선택·카메라는 별도로 확인해야 합니다.

PNG 이미지 전달과 image_file 저장은 별개입니다. include_usage의 토큰 수는 픽셀 기준 추정치입니다. labels는 주변 객체에도 표시되어 화면을 가릴 수 있습니다.

Args:
    target_ids: 화면에서 선택·확대할 객체, 그룹 또는 Holon의 ID 배열입니다. 생략하면 현재 화면을 사용하며, 입력할 때는 하나 이상의 ID를 지정합니다.
    target_kind: object(기본), group, block, holon. block은 배치 객체 ID; 비기본값은 target_ids 필요.
    isolate: 기본 false. true: target_ids 필수, 확대 전 Isolate.
    scale_percent: 이미지 해상도의 백분율입니다. 1..100 범위이며 기본값은 75입니다.
    include_usage: true이면 이미지 크기와 픽셀 기준 토큰 추정치를 포함합니다.
    display_mode: 선택 사항인 설치된 래스터 모드 이름/ID입니다. 제공하면 실제 모델 뷰포트를 변경합니다.
    labels: 기본 false. 주변 객체에도 최대 200개 표시 가능.
    depth: 레이블 확장 깊이: 1..8, 기본 1.
    width: 이미지의 픽셀 너비입니다. 128..2048 범위이며 height도 입력하고 scale_percent=100으로 지정합니다.
    height: 이미지의 픽셀 높이입니다. 128..2048 범위이며 width도 입력하고 scale_percent=100으로 지정합니다.
    expected_model_path: 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
<!-- /instruction:get_current_viewcapture -->
<!-- instruction:get_objects -->
Rhino 문서의 최상위 모델 객체를 조회합니다. `current`는 표시되고 잠기지 않은 객체(화면 밖 포함), `document`는 숨김·잠금 객체도 포함합니다. 객체·그룹 ID와 메타데이터로 범위를 좁히고 객체, 요약 또는 계층으로 관찰합니다. 그룹은 선택한 범위와 구성원의 교집합입니다. 계층 조회는 그룹·블록 배치를 펼치며 문서 객체와 블록 정의 내부 항목을 구분합니다.

행과 면은 각각 페이지를 나눕니다. 행 후속 조회에는 같은 조건과 첫 응답의 snapshot·next_offset을, 면 후속 조회에는 document 객체 ID와 geometry_crc를 사용합니다. objects/summary의 complete는 전체 행이 첫 단일 응답에 포함되고 편집 상태가 안정적일 때 true입니다. 마지막 페이지는 next_offset=null로 확인합니다. hierarchy의 complete에는 관계 완전성도 반영되며 깊이 제한이 있을 수 있습니다. face_page.complete는 전체 면이 첫 단일 응답에 있을 때 true입니다.

표시 여부는 픽셀 가시성이나 가림 여부를 뜻하지 않습니다.

Args:
    scope: current(기본), document.
    object_ids: document 범위에서만 사용할 수 있는 선택 사항인 서로 다른 최상위 객체 GUID입니다(1..4096개). group_ids와 함께 사용하지 않습니다.
    filters: AND 조건입니다. layer_paths(정확한 전체 경로), object_types(관찰된 Rhino 이름), name_contains(대소문자 구분 없음), user_dictionary(source=attributes|geometry, key, 스칼라 any_of)를 사용할 수 있습니다.
    include_geometry: fields를 생략했을 때 objects 모드에서 형상 상세 정보를 포함합니다. 명시적인 fields가 우선합니다.
    offset: 0..100000. 양수: expected_snapshot 필수.
    limit: 1..200, 기본 50.
    expected_model_path: 생략: 연결 문서. 지정 시 경로 일치 검사.
    include_ids: 기본 false. true: ID 포함.
    result_mode: objects(기본), hierarchy, summary. recursive=true와 summary는 배타.
    fields: 선택 사항인 비어 있지 않은 필드 목록입니다. id, name, layer_path, object_type, geometry_kind, geometry_crc, visible, selected, hidden, locked, bounds, groups, user_dictionary, geometry_valid, solid, manifold, volume, faces, face_count를 사용할 수 있습니다. 형상 상세 정보와 faces에는 objects 모드가 필요합니다. summary는 fields를 거부합니다.
    face_offset: 기본 0. 양수: document object_ids와 각 객체의 expected_geometry_crcs 필수.
    face_limit: 1..128, 기본 128. objects 모드.
    expected_geometry_crcs: 객체 GUID별 CRC. 면 연속 조회 중 형상 변경 시 거부.
    group_ids: 어느 scope에서든 사용할 수 있는 선택 사항인 서로 다른 Rhino 그룹 GUID입니다(1..64개). 구성원과 선택한 범위의 교집합을 사용합니다. object_ids와 함께 사용하지 않습니다.
    selected: current에서만 사용하며 기본값은 false입니다. 화면 밖의 선택도 포함하여 적격한 선택 객체로 필터링합니다. inside_window와 함께 사용할 수 없습니다.
    inside_window: current에서만 사용하며 기본값은 false입니다. 활성 뷰포트 경계에 걸친 바운딩 박스를 포함합니다. 클리핑 평면이나 픽셀 가림 검사는 수행하지 않습니다. selected와 함께 사용할 수 없습니다.
    recursive: 기본 false. true: hierarchy 모드.
    depth: 1..8, 루트=1. 1 초과 시 recursive=true.
    expected_snapshot: 첫 페이지 snapshot. offset > 0에서 필수.
<!-- /instruction:get_objects -->

<!-- instruction:get_object_intersections -->
닫힌 솔리드 사이에서 양의 부피가 겹치는 객체 쌍의 수를 찾습니다. include_block=false면 블록을 검사 범위에서 제외합니다. 0건은 선택된 검사 범위에서의 결과이며 전체 설계 적합성이나 간격을 보장하지 않습니다.

계산할 수 없는 객체·쌍이 있으면 intersection_count_incomplete 오류와 상세를 반환합니다. 접촉만 하는 면도 계산 불완전으로 반환될 수 있습니다. result는 결과 또는 오류를 담은 JSON 문자열입니다.

Args:
    object_ids: 서로 다른 현재 최상위 Rhino 객체 GUID 1..512개입니다. 내부 페이지 처리를 통해 하나의 범위로 검사합니다.
    include_block: true이면 변환이 적용된 중첩 블록 구성원까지 펼칩니다. 기본값 false는 범위에서 블록을 제외합니다.
<!-- /instruction:get_object_intersections -->

<!-- instruction:capture_rhino_inspection -->
작업 화면을 유지하면서 여러 시점과 객체 범위를 하나의 PNG로 비교합니다. 객체 범위는 문서 표시 상태를 기준으로 하며 픽셀 가시성이나 가림을 보장하지 않습니다. 그룹 자동 확장과 블록 배치·정의 필터는 지원하지 않습니다.

일부 타일이 실패해도 status=success일 수 있습니다. 전체 성공 여부는 complete, 개별 결과는 tiles에서 확인합니다. PNG 전달과 image_file 저장은 별개입니다.

Args:
    views: 타일 1..16개. direction: current(기본), top, bottom, front, back, left, right, iso_ne, iso_nw, iso_se, iso_sw, below_ne, below_nw, below_se, below_sw.\n  // display_mode: 설치된 이름/GUID, label: 최대 120자. object_ids: 최상위 GUID 1..512개; 생략·빈 배열은 공통 범위 또는 문서 표시 상태.
    width: 타일의 픽셀 너비로, 범위는 128..2048이며 기본값은 640입니다. 결합 이미지 제한도 적용됩니다.
    height: 타일의 픽셀 높이로, 범위는 128..2048이며 기본값은 480입니다. 결합 이미지 제한도 적용됩니다.
    columns: 선택 사항인 열 개수이며, 범위는 1..뷰 개수입니다. 생략하면 자동 격자를 사용합니다.
    expected_model_path: 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
    model_view_id: 선택 사항인, 목록에 있는 모델 뷰포트 GUID입니다. Layout/Detail이 활성화된 경우를 포함하여 해당 뷰포트를 활성화하지 않고 사용합니다.
    object_ids: 공통 최상위 객체 GUID 1..4096개. 빈 배열 불가; 타일별 object_ids와 배타.
<!-- /instruction:capture_rhino_inspection -->
