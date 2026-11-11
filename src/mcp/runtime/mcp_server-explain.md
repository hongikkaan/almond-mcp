# mcp_server.py explain

## execute_looping

<!-- instruction:execute_looping -->
Plan의 작업 회차를 시작하거나 재개합니다. 각 Step은 에이전트가 수행합니다.

Args:
    plan_id: 다음 Loop를 시작하거나 최신 Loop를 재개할 기존 Plan ID입니다. plan_02-create tool 또는 plan_08-list tool에서 얻은 ID를 사용합니다.
    resume: false는 새 회차 시작, true는 최신 회차 재개입니다. 이전 회차의 결과를 보고한 뒤 새 회차를 시작합니다. 시작 결과가 불확실하면 plan_05-get tool의 request에 target='plan'과 plan_id를 넣어 현재 회차를 먼저 확인합니다.
    feedback: 이번 회차에 반영할 피드백입니다. 재개 시 생략하거나 비우면 기존 값을 유지합니다.
    artifact_name: Plan의 최초 산출물 폴더 이름입니다. 생략하면 목표에서 정하며 날짜 접두사 YYMMDD_를 붙입니다. 기존 폴더는 재사용합니다.
<!-- /instruction:execute_looping -->

## project_info

<!-- instruction:project_info -->
프로젝트와 현재 문서의 작업 정보를 조회합니다.

Args:
    sections: 요청할 섹션은 project, document, locations, runtime입니다. 생략하면 project/document/locations가 기본값입니다. project에는 등록된 파일이 포함되며, document는 현재 문서의 속성을 읽습니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다.
    files_limit: project 섹션 내 등록 파일의 페이지 크기입니다. 범위는 1..500입니다.
    files_offset: project 섹션 내 등록 파일의 오프셋입니다. 0부터 시작합니다.
<!-- /instruction:project_info -->

<!-- instruction:get_rhino_execution -->
기존 RhinoCode 요청의 실행 상태·결과·로그를 조회합니다.

Args:
    request_id: 이전에 반환된 실행 request_id입니다. 비워 두면 이 세션의 가장 최근 요청을 선택합니다. 시간 초과 시에는 코드를 다시 제출하지 말고 동일 요청을 조회해야 합니다.
    include_result: true이면 저장된 결과를 포함합니다.
    include_stdout: true이면 캡처된 stdout을 포함합니다. 코드를 다시 실행하지는 않습니다.
    result_fields: 유지할 최상위 결과 필드 이름으로, 선택 사항입니다. 생략하면 결과 필드를 유지합니다.
    offset: 0부터 시작하는 결과 페이지 오프셋(배열 행 또는 문자열 문자 수)입니다. stdout은 바이트 스트림 오프셋을 사용합니다.
    limit: 결과 페이지 크기로, 범위는 1..1000입니다. stdout은 해당 스트림 용량 한도에 따라 독립적으로 제한됩니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다.
    include_diagnostics: true이면 상세 실행 진단을 포함합니다.
<!-- /instruction:get_rhino_execution -->

<!-- instruction:set_working_plan -->
Plan 또는 Step을 산출물 작업 공간으로 선택합니다.

Args:
    plan_id: plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다.
    step_id: 선택할 Step ID입니다. 생략하면 Plan만 선택합니다.
    artifact_name: Plan의 최초 산출물 폴더 이름입니다. 생략하면 목표에서 정하고 날짜 접두사 YYMMDD_를 붙입니다. 기존 폴더는 재사용합니다.
    loop_no: 선택 사항인 현재 Loop 번호 보호 검사입니다. 이전 또는 알 수 없는 Loop는 쓰기 대상으로 선택할 수 없습니다.
<!-- /instruction:set_working_plan -->

<!-- instruction:rename_artifact_folder -->
Plan 산출물 폴더를 옮기거나 이름을 바꾸고 저장된 참조를 갱신합니다. 실행된 회차가 있으면 변경할 수 없습니다.

Args:
    name: Plan 산출물 폴더의 새 이름입니다. 날짜 접두사는 런타임이 관리합니다. 소유한 폴더를 이동하고 관련된 저장 참조를 갱신합니다.
    plan_id: 선택 사항인 Plan ID입니다. 비어 있으면 현재 선택된 작업 Plan을 사용합니다.
<!-- /instruction:rename_artifact_folder -->

<!-- instruction:execute_project_python -->
선택한 Plan의 산출물 폴더를 작업 디렉터리로 삼아 Rhino 내부에서 Python 3 코드를 실행합니다.

Args:
    code: 연결된 Rhino에서 실행할 동기식 Python 3 코드입니다. doc과 scriptcontext.doc은 연결된 문서이며 JSON-safe 결과를 result에 할당합니다. 상대 출력 경로는 선택한 Plan/Loop의 산출물 폴더를 기준으로 합니다.
    timeout_seconds: 1-600의 정수이며 기본값은 60입니다. 대기 시간 제한이며, 실행을 취소하지 않습니다.
<!-- /instruction:execute_project_python -->

## response-90

<!-- instruction:response-90 -->
This Rhino uses the previous storage protocol. Load the new host and reconnect before sharing a DB.
<!-- /instruction:response-90 -->

## response-92

<!-- instruction:response-92 -->
Do not connect this model to another project database.
<!-- /instruction:response-92 -->

## response-96

<!-- instruction:response-96 -->
Connection changed. Exit Codex and reconnect with almond.
<!-- /instruction:response-96 -->
