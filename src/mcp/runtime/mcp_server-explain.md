# mcp_server.py explain

## execute_looping

<!-- instruction:execute_looping -->
Plan의 다음 Loop를 시작하거나 최신 Loop를 재개하여 작업 맥락과 산출물 위치를 준비합니다. Step이나 Rhino 작업을 자동 실행하지 않으며, 에이전트가 다음 기준에 따라 수행·검증·보고합니다.

- 반환된 Step 순서를 기본으로 따르되 실행을 강제하는 조건으로 취급하지 않습니다. 재개 전에는 저장된 기록을 확인하여 이미 수행한 작업, 남은 검증, 아직 전달하지 않은 보고를 구별하고 완료한 Rhino 작업을 반복하지 않습니다.
- Plan과 Step의 상태(pending, running, paused, completed, failed, blocked)는 명시적으로 기록합니다. Step의 수행·검증·보고 진행과 근거는 `update_step`의 상태 및 `input_refs`·`output_refs`로 남기고, Plan의 변경은 `update_plan`으로 기록합니다. 일반 Rhino/Python 호출 자체는 Plan 리비전을 생성하지 않습니다.
- 이전 결과는 현재에도 유효한지 확인한 뒤 재사용합니다. 사용할 이전 파일 경로는 `input_refs`에, 이번 Loop에서 새로 만들거나 수정한 결과 경로는 `output_refs`에 기록합니다.
- Loop에는 별도 업무 상태가 없고, 더 높은 Loop가 시작되면 이전 Loop는 읽기 전용 참고자료입니다. Step 상태는 Plan 상태와 독립적입니다. 모든 Step을 마치거나 회차를 보고했더라도 Plan 완료는 사용자가 결정하며, 그 결정 후에만 Plan 상태를 completed로 기록합니다.
- 회차가 끝나면 목표, 바뀐 내용, 판단을 뒷받침하는 시각 자료, 검증 결과와 남은 선택지를 사용자에게 보고합니다. 질문은 관련 근거와 연결하고 보고는 간결하게 하며, 이미지 수를 고정하지 않습니다.

반환: 현재 loop_no·revision, Step 순서, 이전 회차, 선택한 작업 공간과 artifact_dir를 반환합니다. Loop에는 별도 업무 상태가 없으며 plan_status와 steps[].status를 확인합니다.

Args:
    plan_id: 다음 Loop를 시작하거나 최신 Loop를 재개할 기존 Plan ID입니다. create_plan 또는 list_plans에서 얻은 ID를 사용합니다.
    resume: false이면 첫 호출에서 Loop 1을, 이후 호출에서는 다음 Loop를 시작합니다. true이면 이미 시작된 최신 Loop의 번호와 Step 기록을 유지하며, 시작된 Loop가 없거나 이전 Loop를 재개하려는 경우에는 사용할 수 없습니다. 다음 회차를 시작하려면 앞 회차를 보고한 뒤 false로 호출합니다. 시작 결과가 불확실하면 get_phase_plan_step으로 현재 Loop와 기록을 먼저 확인하고, 확인 없이 false로 재호출하지 않습니다. 변경 없는 재개는 리비전을 추가하지 않습니다.
    feedback: 이번 회차에서 반영할 피드백입니다. 새 회차에서는 기본값이 빈 문자열이며, 재개할 때 빈 문자열은 기존 피드백을 유지합니다. 재개 시 기존 값과 다른 비어 있지 않은 피드백을 주면 같은 Loop의 피드백을 갱신하고 리비전을 추가합니다.
    artifact_name: 최초 Plan 산출물 폴더의 이름이며 경로가 아닙니다. 생략하면 목표에서 이름을 정하고, 날짜 접두사가 없으면 YYMMDD_를 붙입니다. 이미 정해진 Plan 폴더를 이 입력으로 바꾸지 않습니다. 이번 Loop의 모든 산출물은 반환된 artifact_dir(Plan 폴더 아래 01, 02, …)에 저장합니다. 같은 Loop 안에서 덮어쓸 수 있지만 중간 결과를 보존하려면 다른 파일명을 사용합니다. 재사용할 이전 파일을 Plan 루트로 옮기거나 과거 산출물을 자동 삭제하지 않습니다. 다음 Loop 폴더가 이미 있으면 기존 파일을 보존하기 위해 시작을 거부합니다. 리비전은 기록과 참조를 보존하며 덮어쓴 파일 내용이나 Rhino 형상을 복원하지 않습니다.
<!-- /instruction:execute_looping -->

## project_info

<!-- instruction:project_info -->
프로젝트 경로, 등록 파일, 연결된 문서와 현재 산출물 작업 공간을 조회합니다. 문서를 변경하거나 다시 연결한 뒤에는 정보를 갱신합니다.

반환: 요청한 project·document·locations·runtime 섹션과 next_step_guide를 반환합니다. project.files는 등록된 파일 연결 정보, locations.artifact_dir는 현재 작업 공간입니다.

Args:
    sections: 요청할 섹션은 project, document, locations, runtime입니다. 생략하면 project/document/locations가 기본값입니다. project에는 등록된 파일이 포함되며, document는 현재 문서의 속성을 읽습니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다.
    files_limit: project 섹션 내 등록 파일의 페이지 크기입니다. 범위는 1..500입니다.
    files_offset: project 섹션 내 등록 파일의 오프셋입니다. 0부터 시작합니다.
<!-- /instruction:project_info -->

<!-- instruction:get_rhino_execution -->
기존 RhinoCode 요청의 완료 근거, 결과 페이지와 로그를 조회합니다. 실행 상태는 completed와 status로 확인하며 CLI 종료만으로 완료를 판단하지 않습니다.

반환: request_id·completed·status와 결과·로그 페이지를 반환합니다. next_offset 등 반환된 이어읽기 값을 그대로 사용합니다.

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
Plan과 선택한 Step을 이 연결의 산출물 작업 공간으로 지정합니다. 최신 Loop만 선택할 수 있습니다. 다른 연결이 다음 회차를 시작하면 다시 선택해야 파일을 쓸 수 있습니다. 기존 tmp 계열 폴더는 rename_artifact_folder로 먼저 이전합니다.

반환: plan_id·step_id·loop_no·revision, 현재 artifact_dir와 Plan 루트 plan_artifact_dir를 반환합니다.

Args:
    plan_id: list_plans.plans[].plan_id 또는 get_phase_plan_step.id에서 얻은 기존 Plan ID입니다.
    step_id: 선택 사항인 Plan 내 Step ID입니다. 비어 있으면 Step 없이 Plan을 선택합니다. 선택해도 실행하거나 완료하지 않습니다.
    artifact_name: 최초 폴더 이름만 전달하며 절대 경로나 상대 경로는 사용할 수 없습니다. 생략하면 Plan의 goal을 사용합니다. 파일은 .almond/produced/YYMMDD_name 아래에 저장됩니다. 기존 폴더는 재사용합니다.
    loop_no: 선택 사항인 현재 Loop 번호 보호 검사입니다. 이전 또는 알 수 없는 Loop는 쓰기 대상으로 선택할 수 없습니다.
<!-- /instruction:set_working_plan -->

<!-- instruction:rename_artifact_folder -->
Plan 산출물 폴더의 이름이나 위치를 바꾸고 현재 참조를 갱신합니다. 실행된 Loop나 과거 Loop의 파일 참조가 있으면 거부하며, 대상 폴더는 새 경로여야 합니다.

반환: 새 artifact_dir와 previous_artifact_dir를 반환합니다.

Args:
    name: Plan 산출물 폴더의 새 이름입니다. 날짜 접두사는 런타임이 관리합니다. 소유한 폴더를 이동하고 관련된 저장 참조를 갱신합니다.
    plan_id: 선택 사항인 Plan ID입니다. 비어 있으면 현재 선택된 작업 Plan을 사용합니다.
<!-- /instruction:rename_artifact_folder -->

<!-- instruction:execute_project_python -->
선택한 Plan의 산출물 폴더를 작업 디렉터리로 삼아 연결된 Rhino의 Python 3 코드를 실행합니다. Rhino 내장 실행 환경이며 파일 접근은 OS 권한을 따릅니다. 문서 전환과 백그라운드 쓰기를 만들지 않습니다. 시간 초과·불확실한 결과는 get_rhino_execution으로 확인합니다.

반환: request_id·status·completed와 artifact_dir, 확보한 실행 결과를 반환합니다. completed=false이면 같은 요청을 조회합니다.

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
