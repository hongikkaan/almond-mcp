# mcp_server.py explain

## execute_looping

<!-- instruction:execute_looping -->
Plan의 새 작업 회차를 시작하거나 최신 회차를 재개합니다. Step 실행은 에이전트가 직접 수행합니다.

새 회차는 Step을 pending으로 시작하며 이전 회차의 상태와 참조는 previous_loop에 반환합니다. resume=true는 기존 회차를 유지하며, 피드백을 생략하거나 비우면 기존 피드백을 유지합니다. 실행된 회차가 없으면 재개할 수 없습니다. next_step_id는 미완료 첫 Step이며 없으면 null입니다.

Args:
    plan_id: 다음 Loop를 시작하거나 최신 Loop를 재개할 기존 Plan ID입니다. plan_02-create tool 또는 plan_08-list tool에서 얻은 ID를 사용합니다.
    resume: 기본 false: 새 회차. true: 최신 회차 재개.
    feedback: 재개 시 생략·빈 문자열은 기존 값 유지.
    artifact_name: 최초 산출물 폴더명. 생략 시 목표 기반, YYMMDD_ 접두사. 기존 폴더 재사용.
<!-- /instruction:execute_looping -->

## project_info

<!-- instruction:project_info -->
연결된 Rhino 문서와 프로젝트의 작업 정보를 조회합니다. 작업을 시작하거나 이어갈 때 현재 문서, 등록 파일과 작업 공간을 확인하는 데 사용합니다.

`sections`로 필요한 정보를 선택합니다. project는 프로젝트 경로·현재 문서와 연결 모델의 일치 여부·DB 등록 파일, document는 현재 문서의 단위·허용오차·객체 수 등, named_views·layouts는 저장된 뷰·Layout 전체 목록, layers는 전체 레이어의 들여쓰기 불릿 트리, worksession은 활성 모델을 제외한 첨부 경로 목록, locations는 선택된 작업 공간과 공유 DB, runtime은 연결 실행 환경입니다. sections를 생략하면 runtime을 제외한 모든 섹션을 조회합니다. 필요한 현재 문서 정보는 inspect_03-get_document_context tool과 공통 수집기로 한 번 읽습니다. 문서의 개별 값을 읽지 못하면 해당 값은 null이며 warnings에 사유가 나옵니다.

`project.files`는 실제 Worksession 첨부 목록과 구분되는 DB 등록 프로젝트 문서 목록입니다. 각 행의 filename과 description으로 자료를 고르고 Rhino에서 Worksession에 attach하여 참조할 수 있습니다. 기존 file_name은 filename과 같은 값입니다. 등록은 실제 첨부 상태나 디스크 존재를 보증하지 않습니다. 등록 파일 목록이 잘리면 `files_page`의 offset과 limit을 더해 `files_offset`으로 다음 페이지를 조회합니다. 파일 ID 등 후속 작업에 필요한 식별자는 `include_ids=true`로 포함하며 Named View·Layout ID는 항상 반환합니다. 프로젝트 내부 경로는 project_root 기준 상대경로로 반환됩니다.

`worksession.attachments`는 Rhino API가 보고한 전체 첨부의 filename과 path입니다. 활성 모델과 중복 경로는 제외하고 동명이어도 경로가 다르면 유지합니다. 같은 드라이브의 path는 프로젝트 기준 상대경로이며 외부 경로에는 ../가 포함될 수 있습니다. 다른 드라이브·UNC처럼 상대경로를 만들 수 없으면 절대경로를 보존합니다. 이는 참조의 식별 정보이며 관리 산출물 경로 입력과는 구분합니다. 빈 배열은 첨부 없음이며 조회 실패나 유효하지 않은 경로가 섞인 경우 worksession 전체가 null이고 warnings에 사유가 나옵니다. 형식 검사는 금지 문자·제어문자·절대경로와 파일명 구성을 확인하며 파일시스템 전체 유효성을 보증하지 않습니다. 이 목록은 실제 로드 성공이나 최신 상태를 보증하지 않습니다. 첨부 목록에는 필터·페이지 제한을 적용하지 않습니다.

Args:
    sections: project, document, named_views, layouts, layers, worksession, locations, runtime. 기본은 runtime을 제외한 모든 섹션.
    include_ids: 기본 false.
    files_limit: 등록 파일 페이지 크기: 정수 1~500, 기본 50.
    files_offset: 등록 파일의 시작 위치: 0 이상의 정수, 기본 0.
<!-- /instruction:project_info -->

<!-- instruction:get_rhino_execution -->
이전에 요청한 RhinoCode 실행의 상태와 보관된 결과·로그를 조회합니다. **코드를 다시 실행하지 않습니다.** request_id를 생략하면 현재 연결의 가장 최근 실행을 조회하며, beyond·CoS에서는 ID를 지정해 원래 실행 연결을 찾습니다. 연결이 끝난 뒤에도 해당 실행 기록이 남아 있으면 조회할 수 있습니다.

결과의 배열이나 문자열은 페이지로 조회할 수 있습니다. 로그는 별도의 바이트 오프셋을 사용합니다.

Args:
    request_id: 이전에 반환된 실행 request_id입니다. 비워 두면 현재 연결의 가장 최근 요청을 읽습니다. beyond·CoS는 지정한 ID의 원래 실행 연결을 찾습니다. 시간 초과 시에는 같은 ID로 결과를 조회합니다.
    include_result: 기본 true.
    include_stdout: stdout·stderr와 CLI 로그 포함 여부. 기본 false.
    result_fields: 객체 결과의 최상위 키 또는 객체 배열의 행에서 남길 키.
    offset: 결과는 배열 항목 또는 문자열 문자, 로그는 바이트 단위. 기본 0.
    limit: 결과 페이지 크기. 1~1000, 기본 100. 로그는 별도 크기 제한 적용.
    include_ids: 결과의 식별자 포함 여부. 기본 true.
    include_diagnostics: 기본 false.
<!-- /instruction:get_rhino_execution -->

<!-- instruction:set_working_plan -->
현재 연결에서 Plan과 선택적인 Step을 산출물 작업 대상으로 선택합니다. 선택 자체는 **작업 실행이나 Plan·Step 상태 변경이 아닙니다.**

최초 선택은 Plan 산출물 경로를 정하며 revision이 증가할 수 있습니다. 이후에는 같은 Plan의 경로를 재사용합니다. Loop 시작 전 `artifact_dir`은 Plan 루트, 시작 후에는 현재 Loop의 번호 폴더입니다. 반환된 `loop_no`와 `revision`은 선택 시점의 값입니다.

Args:
    plan_id: plan_08-list tool에 request.target=plan으로 조회한 plans[].plan_id 또는 plan_05-get tool의 id에서 얻은 기존 Plan ID입니다.
    step_id: 생략 시 Plan만 선택.
    artifact_name: 최초 폴더명. 생략 시 목표에서 정하고 YYMMDD_ 접두사를 붙임. 기존 폴더와 다른 이름은 거부.
    loop_no: 현재 Loop 보호 값. 생략·null은 현재 Loop. 이전·존재하지 않는 Loop 선택 불가.
<!-- /instruction:set_working_plan -->

<!-- instruction:rename_artifact_folder -->
Plan의 산출물 폴더 이름을 바꾸고 현재 Plan·Step의 저장 경로 참조를 갱신합니다. 먼저 plan_10-set_working tool으로 산출물 폴더를 지정해야 합니다.

Loop 실행 이후 또는 다른 Plan의 과거 Loop가 참조하는 폴더는 실제 이름을 변경할 수 없습니다. 같은 이름 요청은 변경 없이 성공하며, 대상 폴더가 이미 존재하거나 다른 Plan에 속하면 실패합니다. 기존 revision은 유지됩니다.

Args:
    name: 폴더명 하나. YYMMDD_가 없으면 현재 날짜 추가. 경로·Windows 금지 문자 불가.
    plan_id: 생략 또는 빈 문자열: 현재 선택된 Plan.
<!-- /instruction:rename_artifact_folder -->

<!-- instruction:execute_project_python -->
연결된 Rhino 문서에서 Python 3 코드를 실행합니다. Rhino 형상을 생성·편집하거나 산출물 파일을 만들 때 사용하며, 선택된 Plan·Loop의 산출물 폴더가 작업 디렉터리가 됩니다.

실행하려면 **유효하고 쓰기 가능한 작업 공간**이 선택되어 있어야 합니다. 선택된 작업 공간이 없다면 `plan_10-set_working` tool으로 선택하세요. 기존 선택은 재사용할 수 있습니다.

코드는 실제 문서를 변경할 수 있으며 실행 완료가 문서 저장을 뜻하지는 않습니다. **시간 초과는 실행을 취소하지 않습니다.** 완료 여부가 불확실하면 반환된 `request_id`로 `script_03-get_execution` tool을 조회하고, 변경을 다시 실행하기 전에 문서 상태를 확인하세요. 오류가 발생해도 부분 변경이 롤백되었다고 가정하지 마세요.

Args:
    code: 비어 있지 않은 동기식 Python 3 코드. doc·scriptcontext.doc은 연결된 문서이며, 반환할 JSON 호환 값은 result에 할당합니다. 상대 경로는 선택된 산출물 폴더 기준입니다.
    timeout_seconds: 1~600초의 정수, 기본 60초.
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
