# tools.py explain

## list_drawing_recipes

<!-- instruction:list_drawing_recipes -->
사용 가능한 도면 스타일 레시피의 요약을 조회합니다. 상세 조회에 사용할 recipe_id는 include_ids=true로 포함합니다. next_step_guide는 drawing_01-apply_style tool을 사용한 스타일 적용을 안내하며 요약에서도 반환합니다. 호출마다 레시피 파일을 다시 읽고 작성 틀 sample.json은 제외합니다. result는 목록 또는 오류를 담은 JSON 문자열입니다.

Args:
    include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
    field_groups: 상세 그룹: scales, parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
<!-- /instruction:list_drawing_recipes -->

## get_drawing_recipe

<!-- instruction:get_drawing_recipe -->
지정한 도면 스타일 레시피의 투영·축척·레이어·출력 설정을 조회합니다. 조회만으로 문서 스타일이 적용되지 않으며, next_step_guide에 따라 같은 recipe_id로 drawing_01-apply_style tool을 호출합니다. 안내는 상세 그룹·ID 표시 여부와 무관하게 반환합니다. result는 레시피 또는 오류를 담은 JSON 문자열입니다.

Args:
    recipe_id: drawing_05-list_recipes tool(include_ids=true)에서 얻은 도면 레시피 ID 또는 이미 알고 있는 레시피 ID입니다.
    include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
    field_groups: 상세 그룹: scales, parameters, source, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
<!-- /instruction:get_drawing_recipe -->

## apply_drawing_style

<!-- instruction:apply_drawing_style -->
도면 레시피의 레이어 계층과 색·출력색·출력 선 두께·선종류를 Rhino 문서에 생성하거나 갱신합니다. 같은 경로의 기존 레이어에도 적용됩니다. 선종 기본 정의는 실행 소스의 profiles/linetype/manifest.json에서 직접 읽으며, 문서에 동명 선종이 있으면 패턴이 달라도 기존 정의를 보존·재사용합니다. 레이어 선종의 ByLayer·ByParent 입력은 Continuous로 처리합니다. 레시피의 투영·축척·용지 설정으로 도면이나 Layout을 만들지는 않습니다.

Args:
    recipe_id: drawing_05-list_recipes tool 또는 drawing_02-get_recipe tool의 레시피 ID. 생략: technical_axon_v1.
<!-- /instruction:apply_drawing_style -->

## import_drawing_hatch_patterns

<!-- instruction:import_drawing_hatch_patterns -->
등록된 PAT 자산의 해치 패턴 정의를 Rhino 문서에 가져옵니다. 같은 이름이 이미 있으면 기존 정의를 재사용합니다. 도면에 해치 객체를 배치하지는 않습니다.

Args:
    asset_id: 등록된 PAT 도면 자산 ID.
<!-- /instruction:import_drawing_hatch_patterns -->

## response-642

<!-- instruction:response-642 -->
Rhino bridge is unavailable. Start RhinoAlmondBridge first.
<!-- /instruction:response-642 -->

## response-645

<!-- instruction:response-645 -->
Rhino bridge is unavailable. Start RhinoAlmondBridge first.
<!-- /instruction:response-645 -->
