# tools.py explain

<!-- instruction:list_design_scenes -->
공유 프로젝트 DB에 등록된 Scene 목록을 조회합니다. 파일명을 생략하면 연결된 파일뿐 아니라 프로젝트의 모든 파일을 포함합니다.

result는 scenes, total, limit, offset, truncated를 담은 JSON 문자열입니다. truncated=true이면 같은 필터에서 offset을 limit만큼 늘려 다음 페이지를 조회합니다. Scene 상세는 scene_04-get tool, 현재 Rhino 구성원은 scene_06-get_objects tool로 확인합니다.

Args:
    name: Scene 이름 부분 검색. 대소문자 무관.
    file_name: 확장자를 포함한 정확한 프로젝트 파일명. 생략: 전체 파일.
    limit: 1~200, 기본 50.
    offset: 0부터 시작. 기본 0.
    include_ids: 기본 false. true: scene_id 등 포함.
    field_groups: scope, state, geometry, audit, all. 생략·빈 배열: 요약.
<!-- /instruction:list_design_scenes -->

## create_design_scene

<!-- instruction:create_design_scene -->
설계 영역·프로그램·상황을 나타내는 Scene을 생성합니다.

Args:
    name: 설계 영역 또는 행위/프로그램 맥락을 설명하는 Scene 이름입니다. 비어 있으면 Untitled가 됩니다.
    units: Scene에 기록할 단위입니다. mm, cm, m, in, ft 중 하나를 선택합니다.
    file_name: 이 Scene이 속한 프로젝트 파일명을 문자열로 입력합니다. 폴더는 제외하고, 같은 이름의 파일이 여러 개면 project_file_id로 지정합니다.
    project_file_id: context_04-get_project_info tool(sections=["project"], include_ids=true)에서 얻은 기존 project.files[].project_file_id입니다. file_name과 함께 제공하면 서로 일치해야 합니다.
<!-- /instruction:create_design_scene -->

## get_design_scene

<!-- instruction:get_design_scene -->
Scene의 등록 정보와 Holon·객체 수를 조회합니다. 저장된 요약이며 현재 Rhino 구성원을 실시간 검증하지 않습니다. 객체 수가 null이면 수를 확정할 수 없는 상태입니다. 현재 구성원은 scene_06-get_objects tool로 조회합니다.

result는 scene 또는 오류를 담은 JSON 문자열입니다. include_ids=true여도 입력한 scene_id는 반복 반환하지 않습니다.

Args:
    scene_id: scene_07-list tool(include_ids=true) 또는 기록된 Scene 참조에서 얻은 기존 Scene ID입니다.
    include_ids: 기본 false. scope 등에서 project_file_id 포함.
    field_groups: scope, state, geometry, audit, all. 생략·빈 배열: 요약.
<!-- /instruction:get_design_scene -->

<!-- instruction:update_design_scene -->
Scene의 프로젝트 파일 연결을 변경하거나 해제합니다.

Args:
    scene_id: scene_07-list tool(include_ids=true) 또는 기록된 Scene 참조에서 얻은 기존 Scene ID입니다.
    file_name: 폴더를 포함하지 않는 교체 파일 이름입니다. 선택 사항이며, project_file_id를 생략한 상태에서 빈 문자열을 지정하면 연결을 해제합니다. 생략하면 유지합니다.
    project_file_id: 연결할 기존 프로젝트 파일의 ID입니다. file_name도 입력하면 같은 파일을 가리켜야 합니다.
<!-- /instruction:update_design_scene -->

## get_scene_objects

<!-- instruction:get_scene_objects -->
Scene의 직접 객체와 Holon 구성원을 현재 Rhino 문서에서 조회합니다. Scene에서 제외한 구성원은 목록에 포함되지 않습니다.

result는 objects, total, limit, offset, truncated 및 live_verified 또는 오류를 담은 JSON 문자열입니다. truncated=true이면 같은 조건에서 offset을 limit만큼 늘려 다음 페이지를 조회합니다.

Args:
    scene_id: scene_07-list tool(include_ids=true) 또는 기록된 Scene 참조에서 얻은 기존 Scene ID입니다.
    include_ids: 기본 false. true: 객체 GUID 포함.
    field_groups: scope, state, geometry, audit, all. 생략·빈 배열: 요약.
    limit: 1~200, 기본 50.
    offset: 0부터 시작. 기본 0.
    expected_model_path: 생략: 연결된 문서. 지정 시 연결 문서와 일치해야 함.
<!-- /instruction:get_scene_objects -->


<!-- instruction:add_scene_objects -->
Rhino 객체를 Scene에 포함하거나 해당 Scene에서 제외했던 Holon 구성원을 복원합니다.

Args:
    scene_id: scene_07-list tool(include_ids=true)에서 얻은 기존 Scene ID입니다.
    object_ids: 일반 형상이나 클리핑 평면을 포함하는 객체 GUID 배열로, 최대 4096개 항목을 허용합니다.
    expected_model_path: 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
<!-- /instruction:add_scene_objects -->

<!-- instruction:remove_scene_objects -->
객체를 Scene에서 제외합니다. Rhino 형상과 Holon 그룹은 유지됩니다.

Args:
    scene_id: scene_07-list tool(include_ids=true)에서 얻은 기존 Scene ID입니다.
    object_ids: 일반 형상 또는 클리핑 평면을 포함하는 객체 GUID 배열이며, 최대 4096개 항목을 받습니다.
    expected_model_path: 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
<!-- /instruction:remove_scene_objects -->
