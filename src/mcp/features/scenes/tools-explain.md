# tools.py explain

<!-- instruction:list_design_scenes -->
프로젝트에 등록된 Scene 목록을 조회합니다.

Args:
    name: 선택 사항인 대소문자를 구분하지 않는 Scene 이름 필터입니다.
    file_name: 선택 사항인 저장된 프로젝트 파일 이름 필터입니다. 현재 형상을 검증하지는 않습니다.
    limit: 페이지 크기이며, 범위는 1..200입니다.
    offset: 이 페이지의 0부터 시작하는 첫 행 위치입니다. 다음 페이지를 요청할 때는 동일한 필터를 사용합니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다.
    field_groups: 선택 사항인 상세 그룹: scope, state, geometry, audit 또는 all. 생략하거나 비워 두면 요약을 유지하며, include_ids는 식별 정보 포함 여부를 별도로 제어합니다.
<!-- /instruction:list_design_scenes -->

## create_design_scene

<!-- instruction:create_design_scene -->
설계 영역·프로그램·상황을 나타내는 Scene을 생성합니다.

Args:
    name: 설계 영역 또는 행위/프로그램 맥락을 설명하는 Scene 이름입니다. 비어 있으면 Untitled가 됩니다.
    units: Scene 단위 코드: mm, cm, m, in 또는 ft. Rhino 문서 단위를 바꾸지는 않습니다.
    file_name: 폴더를 제외한 프로젝트 파일 이름입니다. 중복 파일 이름을 구분하려면 project_file_id를 사용합니다. 이는 저장된 연결 정보이며, 파일 작업이 아닙니다.
    project_file_id: project_info(sections=["project"], include_ids=true)에서 얻은 기존 project.files[].project_file_id입니다. file_name과 함께 제공하면 서로 일치해야 합니다.
<!-- /instruction:create_design_scene -->

## get_design_scene

<!-- instruction:get_design_scene -->
Scene의 저장된 정보와 등록 요약을 조회합니다.

Args:
    scene_id: list_design_scenes(include_ids=true) 또는 기록된 Scene 참조에서 얻은 기존 Scene ID입니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다.
    field_groups: 선택 사항인 상세 그룹: scope, state, geometry, audit 또는 all. 생략하거나 비워 두면 요약을 유지하며, include_ids는 식별 정보 포함 여부를 별도로 제어합니다.
<!-- /instruction:get_design_scene -->

<!-- instruction:update_design_scene -->
Scene의 프로젝트 파일 연결을 변경하거나 해제합니다.

Args:
    scene_id: list_design_scenes(include_ids=true) 또는 기록된 Scene 참조에서 얻은 기존 Scene ID입니다.
    file_name: 폴더를 포함하지 않는 교체 파일 이름입니다. 선택 사항이며, project_file_id를 생략한 상태에서 빈 문자열을 지정하면 연결을 해제합니다. 생략하면 유지합니다.
    project_file_id: 기존 프로젝트 파일 ID입니다. 선택 사항이며, file_name과 함께 제공하면 서로 일치해야 합니다. 디스크의 파일이 아니라 메타데이터를 변경합니다.
<!-- /instruction:update_design_scene -->

## get_scene_objects

<!-- instruction:get_scene_objects -->
Scene에 포함된 직접 객체와 하위 Holon의 현재 구성원을 조회합니다.

Args:
    scene_id: list_design_scenes(include_ids=true) 또는 기록된 Scene 참조에서 얻은 기존 Scene ID입니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다.
    field_groups: 선택 사항인 상세 그룹: scope, state, geometry, audit 또는 all. 생략하거나 비워 두면 요약을 유지하며, include_ids는 식별 정보 포함 여부를 별도로 제어합니다.
    limit: 현재 상태를 검증한 Scene 객체의 페이지 크기이며, 범위는 1..200입니다.
    offset: 이 페이지의 0부터 시작하는 첫 행 위치입니다. 다음 페이지를 요청할 때는 동일한 필터를 사용합니다.
    expected_model_path: 일반적으로 생략합니다. 관리형 세션이 연결된 저장 Rhino 문서를 제공합니다. 명시한 경로는 이 연결 정보와 일치해야 하며, 문서를 전환하지는 않습니다.
<!-- /instruction:get_scene_objects -->


<!-- instruction:add_scene_objects -->
Rhino 객체를 Scene에 포함하거나 해당 Scene에서 제외했던 Holon 구성원을 복원합니다.

Args:
    scene_id: list_design_scenes(include_ids=true)에서 얻은 기존 Scene ID입니다.
    object_ids: 일반 형상이나 클리핑 평면을 포함하는 객체 GUID 배열로, 최대 4096개 항목을 허용합니다.
    expected_model_path: 일반적으로 생략합니다. 관리형 세션이 연결된 저장 문서를 제공합니다. 명시한 경로는 해당 문서와 일치해야 합니다.
<!-- /instruction:add_scene_objects -->

<!-- instruction:remove_scene_objects -->
객체를 Scene에서 제외합니다. Rhino 형상과 Holon 그룹은 유지됩니다.

Args:
    scene_id: list_design_scenes(include_ids=true)에서 얻은 기존 Scene ID입니다.
    object_ids: 일반 형상 또는 클리핑 평면을 포함하는 객체 GUID 배열이며, 최대 4096개 항목을 받습니다.
    expected_model_path: 보통 생략합니다. 관리형 세션이 연결된 저장 문서를 제공합니다. 경로를 명시하면 해당 문서와 일치해야 합니다.
<!-- /instruction:remove_scene_objects -->
