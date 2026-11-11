# tools.py explain

## list_diagram_assets

<!-- instruction:list_diagram_assets -->
사람·나무·기호 등 다이어그램 자산 목록을 조회합니다.

Args:
    category: 라이브러리 분류 필터입니다. 선택 사항이며, 비어 있으면 모든 분류를 포함합니다.
    limit: 한 페이지에 반환할 최대 항목 수입니다.
    offset: 이 페이지의 시작 행을 0부터 세는 값입니다. 다음 페이지를 요청할 때도 같은 필터를 사용합니다.
    include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
    field_groups: 선택 가능한 세부 그룹은 dimensions, drawing, metadata, source, paths, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다.
<!-- /instruction:list_diagram_assets -->

## search_diagram_assets

<!-- instruction:search_diagram_assets -->
조건에 맞는 다이어그램 자산을 검색합니다.

Args:
    query: 자유 텍스트 검색어입니다. 비어 있으면 텍스트 필터를 설정하지 않습니다.
    category: 라이브러리 분류 필터입니다. 선택 사항이며, 비어 있으면 모든 분류를 포함합니다.
    max_width_mm: 측정된 자산 너비의 최댓값이며, 밀리미터 단위입니다. 선택 사항이며, 0은 이 크기 필터를 해제합니다.
    max_depth_mm: 측정된 자산 깊이의 최댓값이며, 밀리미터 단위입니다. 선택 사항이며, 0은 이 크기 필터를 해제합니다.
    max_height_mm: 측정된 자산 높이의 최댓값이며, 밀리미터 단위입니다. 선택 사항이며, 0은 이 크기 필터를 해제합니다.
    limit: 한 페이지에 반환할 최대 항목 수입니다.
    offset: 이 페이지의 시작 행을 0부터 세는 값입니다. 다음 페이지를 요청할 때도 같은 필터를 사용합니다.
    include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
    field_groups: 선택 가능한 세부 그룹은 dimensions, drawing, metadata, source, paths, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다.
<!-- /instruction:search_diagram_assets -->

## get_diagram_asset

<!-- instruction:get_diagram_asset -->
다이어그램 자산의 등록 정보와 사용 가능 상태를 조회합니다.

Args:
    asset_id: include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다.
    include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
    field_groups: 선택 가능한 세부 그룹은 dimensions, drawing, metadata, source, paths, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다.
<!-- /instruction:get_diagram_asset -->

## place_diagram_asset

<!-- instruction:place_diagram_asset -->
SVG·DWG·DXF 다이어그램을 Rhino 문서의 블록 인스턴스로 배치합니다.

Args:
    asset_id: include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다.
    x: 현재 Rhino 문서 단위를 사용하는 배치 X 좌표입니다.
    y: 현재 Rhino 문서 단위를 사용하는 배치 Y 좌표입니다.
    z: 현재 Rhino 문서 단위를 사용하는 배치 Z 좌표입니다.
    rotation_degrees: 월드 Z축을 중심으로 한 회전각이며, 단위는 도입니다.
    scale: 양수인 균일 배치 축척입니다. 1이면 단위 변환 후 자산 크기를 유지합니다.
<!-- /instruction:place_diagram_asset -->
