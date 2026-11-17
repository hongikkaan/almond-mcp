# tools.py explain

## list_library

<!-- instruction:list_library -->
로컬 Grasshopper 라이브러리에서 색인된 로직 이름을 조회합니다. logic_names의 이름으로 grasshopper_01-get_logic tool에서 상세 내용을 조회할 수 있습니다.

Args:
    include_ids: true: logic_names와 같은 값의 logic_ids 포함.
    field_groups: paths·all: 라이브러리 경로 포함. ports·definition·source·audit은 목록에 상세를 추가하지 않음.
<!-- /instruction:list_library -->

## get_logic_by_id

<!-- instruction:get_logic_by_id -->
색인된 Grasshopper 로직 파일에서 추출한 물리 관련 항목·설명과 제공된 메타데이터를 조회합니다. JSON만 있는 항목은 메타데이터를 반환합니다. 추출 정보는 완전한 구성·연결 관계나 실행 가능성을 보장하지 않습니다.

Args:
    logic_id: 확장자를 뺀 라이브러리 파일명. grasshopper_03-list_library tool의 logic_names 사용 가능.
    include_ids: true: 다른 식별자 포함. 입력 logic_id는 반복되지 않음.
    field_groups: ports, definition, source, paths, audit, all. 제공된 필드에만 적용.
<!-- /instruction:get_logic_by_id -->

## list_capsules

<!-- instruction:list_capsules -->
등록된 Grasshopper 캡슐의 기능과 감사 상태를 조회합니다. 포트와 ID를 확인해 grasshopper_04-run_definition tool의 입력을 준비할 수 있습니다. 감사 상태는 정의 파일의 존재나 실행 성공을 보장하지 않습니다.

Args:
    capability: 기능 필터: analyze, generate, form_find, aggregate. 대소문자 무시.
    audited_only: true: audited로 등록된 캡슐만.
    include_ids: true: capsule_id 포함. all과 별도 지정.
    field_groups: ports, definition, source, paths, audit, all. 생략·빈 배열: 요약.
<!-- /instruction:list_capsules -->

## run_gh_definition

<!-- instruction:run_gh_definition -->
실행 감사를 통과한 Grasshopper 캡슐을 Rhino에서 계산합니다. 정의에 따라 형상을 베이크할 수 있습니다. 모든 출력 포트를 먼저 확인하고 형상 베이크는 하나의 전용 Undo record로 처리합니다. mutation_state는 none·completed·rolled_back·unknown이며 requires_reconciliation=true이면 baked_guids와 현재 문서를 확인하기 전 자동 재시도하지 않습니다.

Args:
    capsule_id: grasshopper_02-list_capsules tool에서 얻은 안정적인 캡슐 식별자입니다(예: "karamba_beam_v1").
    inputs: ALMOND_IN_ 포트 이름과 값의 객체입니다. grasshopper_02-list_capsules tool(field_groups=['ports'])의 input_ports에서 타입·단위·필수 여부를 확인합니다. 형상은 {"guids":["객체 GUID"]}, 숫자·정수·문자열·불리언은 JSON 값, 목록은 number[]/integer[]/string[]의 평탄한 배열입니다.
    seed: 확률적 정의에 사용할 선택적 정수 시드입니다. 결정적인 정의에서는 생략합니다.
    timeout_s: 솔버 시간 한도(초)입니다. 기본값은 60, 최댓값은 600입니다.
<!-- /instruction:run_gh_definition -->

## response-713

<!-- instruction:response-713 -->
Logic '{0}' not found. Use grasshopper_03-list_library tool() to see available IDs.
<!-- /instruction:response-713 -->

## response-714

<!-- instruction:response-714 -->
Unknown capsule_id: {0}. Use grasshopper_02-list_capsules tool() to discover capsules.
<!-- /instruction:response-714 -->

## response-727

<!-- instruction:response-727 -->
{0} declares unsupported type {1!r} in its manifest; fix the capsule sidecar before running it.
<!-- /instruction:response-727 -->
