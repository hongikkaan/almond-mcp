# tools.py explain

## list_drawing_recipes

<!-- instruction:list_drawing_recipes -->
도면 목적·투영 방식에 맞는 스타일 레시피를 조회합니다.

Args:
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다.
    field_groups: 상세 그룹: scales, parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다. ID는 include_ids로 선택합니다.
<!-- /instruction:list_drawing_recipes -->

## get_drawing_recipe

<!-- instruction:get_drawing_recipe -->
저장된 도면 레시피의 목적과 설정을 조회합니다.

Args:
    recipe_id: list_drawing_recipes(include_ids=true)에서 얻은 도면 레시피 ID 또는 이미 알고 있는 레시피 ID입니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다.
    field_groups: 상세 그룹: scales, parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다. ID는 include_ids로 선택합니다.
<!-- /instruction:get_drawing_recipe -->

## apply_drawing_style

<!-- instruction:apply_drawing_style -->
도면 레시피의 레이어·색상·출력 선 두께·선종류를 Rhino 문서에 적용합니다.

Args:
    recipe_id: list_drawing_recipes(include_ids=true)에서 얻은 도면 레시피 ID 또는 이미 알고 있는 레시피 ID입니다.
<!-- /instruction:apply_drawing_style -->

## import_drawing_hatch_patterns

<!-- instruction:import_drawing_hatch_patterns -->
등록된 PAT 자산의 해치 정의를 Rhino 문서에 추가합니다. 같은 이름의 정의는 재사용합니다.

Args:
    asset_id: include_ids=true로 조회한 일치하는 목록/검색 결과의 기존 라이브러리 자산 ID 또는 이미 알고 있는 ID입니다.
<!-- /instruction:import_drawing_hatch_patterns -->

## response-642

<!-- instruction:response-642 -->
Rhino bridge is unavailable. Start RhinoAlmondBridge first.
<!-- /instruction:response-642 -->

## response-645

<!-- instruction:response-645 -->
Rhino bridge is unavailable. Start RhinoAlmondBridge first.
<!-- /instruction:response-645 -->
