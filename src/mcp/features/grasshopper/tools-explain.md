# tools.py explain

## list_library

<!-- instruction:list_library -->
로컬 색인에서 Grasshopper 로직 이름을 찾습니다.

Args:
    include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
    field_groups: 상세 그룹: ports, definition, source, paths, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
<!-- /instruction:list_library -->

## get_logic_by_id

<!-- instruction:get_logic_by_id -->
Grasshopper 정의의 구성과 사용 계약을 조회합니다.

Args:
    logic_id: 기존 Grasshopper 라이브러리 파일명에서 확장자를 뺀 이름입니다. 알고 있는 ID를 재사용하거나 list_library(include_ids=true)에서 얻습니다.
    include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
    field_groups: 상세 그룹: ports, definition, source, paths, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
<!-- /instruction:get_logic_by_id -->

## list_capsules

<!-- instruction:list_capsules -->
사용할 Grasshopper 캡슐을 찾습니다.

Args:
    capability: 선택 필터: "analyze", "generate", "form_find", "aggregate".
    audited_only: true이면 run_gh_definition이 실행을 허용하는 캡슐만 나열합니다.
    include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
    field_groups: 상세 그룹: ports, definition, source, paths, audit, all입니다. 생략하거나 비우면 요약을 반환합니다.
<!-- /instruction:list_capsules -->

## run_gh_definition

<!-- instruction:run_gh_definition -->
실행 감사를 통과한 Grasshopper 캡슐을 Rhino에서 계산합니다. 정의에 따라 형상을 베이크할 수 있습니다.

Args:
    capsule_id: list_capsules에서 얻은 안정적인 캡슐 식별자입니다(예: "karamba_beam_v1").
    inputs: ALMOND_IN_ 포트 이름과 값의 객체입니다. list_capsules(field_groups=['ports'])의 input_ports에서 타입·단위·필수 여부를 확인합니다. 형상은 {"guids":["객체 GUID"]}, 숫자·정수·문자열·불리언은 JSON 값, 목록은 number[]/integer[]/string[]의 평탄한 배열입니다.
    seed: 확률적 정의에 사용할 선택적 정수 시드입니다. 결정적인 정의에서는 생략합니다.
    timeout_s: 솔버 시간 한도(초)입니다. 기본값은 60, 최댓값은 600입니다.
<!-- /instruction:run_gh_definition -->

## response-713

<!-- instruction:response-713 -->
Logic '{0}' not found. Use list_library() to see available IDs.
<!-- /instruction:response-713 -->

## response-714

<!-- instruction:response-714 -->
Unknown capsule_id: {0}. Use list_capsules() to discover capsules.
<!-- /instruction:response-714 -->

## response-727

<!-- instruction:response-727 -->
{0} declares unsupported type {1!r} in its manifest; fix the capsule sidecar before running it.
<!-- /instruction:response-727 -->
