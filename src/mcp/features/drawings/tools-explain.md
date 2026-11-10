# tools.py explain

## list_drawing_recipes

<!-- instruction:list_drawing_recipes -->
목적·투영 방식에 맞는 저장 도면 스타일 레시피를 조회합니다.

반환: total과 recipes를 반환합니다. 후속 적용에 필요한 recipe_id는 include_ids=true로 요청합니다.

Args:
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다.
    field_groups: 상세 그룹: scales, parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다. ID는 include_ids로 선택합니다.
<!-- /instruction:list_drawing_recipes -->

## get_drawing_recipe

<!-- instruction:get_drawing_recipe -->
저장된 도면 레시피의 목적과 선택한 상세 설정을 조회합니다.

반환: recipe에 목적·요약과 선택한 scales·parameters 등 상세 그룹을 반환합니다.

Args:
    recipe_id: list_drawing_recipes(include_ids=true)에서 얻은 도면 레시피 ID 또는 이미 알고 있는 레시피 ID입니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다.
    field_groups: 상세 그룹: scales, parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다. ID는 include_ids로 선택합니다.
<!-- /instruction:get_drawing_recipe -->

## apply_drawing_style

<!-- instruction:apply_drawing_style -->
도면 레시피의 레이어 계층·색상·출력 선 두께·선종류를 Rhino 문서에 적용합니다. 선종류 충돌은 변경 전에 거부합니다. 시간 초과 뒤에는 문서 상태를 확인한 후 재시도합니다.

반환: recipe_id·layers와 review_preparation을 반환합니다. 레이어 적용 결과와 출력 검토 준비 사항을 확인합니다.

Args:
    recipe_id: list_drawing_recipes(include_ids=true)에서 얻은 도면 레시피 ID 또는 이미 알고 있는 레시피 ID입니다.
<!-- /instruction:apply_drawing_style -->

## import_drawing_hatch_patterns

<!-- instruction:import_drawing_hatch_patterns -->
등록된 PAT 도면 자산의 해치 정의를 Rhino 문서에 추가합니다. 같은 이름의 정의는 재사용합니다.

반환: patterns에 새로 추가했거나 기존에 있어 사용 가능한 해치 이름을 반환합니다. message가 신규 수와 사용 가능 수를 구분합니다.

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
