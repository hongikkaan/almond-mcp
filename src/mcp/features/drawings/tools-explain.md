# tools.py explain

## list_drawing_recipes

<!-- instruction:list_drawing_recipes -->
도면 목적·투영 방식에 맞는 스타일 레시피를 조회합니다.

Args:
    include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
    field_groups: 상세 그룹: scales, parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
<!-- /instruction:list_drawing_recipes -->

## get_drawing_recipe

<!-- instruction:get_drawing_recipe -->
도면 스타일 레시피를 조회합니다.

Args:
    recipe_id: drawing_05-list_recipes tool(include_ids=true)에서 얻은 도면 레시피 ID 또는 이미 알고 있는 레시피 ID입니다.
    include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
    field_groups: 상세 그룹: scales, parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
<!-- /instruction:get_drawing_recipe -->

## apply_drawing_style

<!-- instruction:apply_drawing_style -->
도면 스타일 레시피를 Rhino 문서에 적용합니다.

Args:
    recipe_id: drawing_05-list_recipes tool(include_ids=true)에서 얻은 도면 레시피 ID 또는 이미 알고 있는 레시피 ID입니다.
<!-- /instruction:apply_drawing_style -->

## import_drawing_hatch_patterns

<!-- instruction:import_drawing_hatch_patterns -->
등록된 PAT 자산의 해치 정의를 Rhino 문서에 추가합니다.

Args:
    asset_id: 해치 정의를 가져올 PAT 자산 ID입니다. 같은 이름의 해치 정의가 있으면 재사용합니다.
<!-- /instruction:import_drawing_hatch_patterns -->

## response-642

<!-- instruction:response-642 -->
Rhino bridge is unavailable. Start RhinoAlmondBridge first.
<!-- /instruction:response-642 -->

## response-645

<!-- instruction:response-645 -->
Rhino bridge is unavailable. Start RhinoAlmondBridge first.
<!-- /instruction:response-645 -->
