# tools.py explain

## list_library

<!-- instruction:list_library -->
로컬 색인에서 조회 가능한 Grasshopper 로직 이름을 찾습니다. 반환된 logic_names 항목을 get_logic_by_id에 사용합니다.

반환: total_entries·logic_names를 반환합니다. include_ids=true는 logic_ids, false는 logic_count를 포함합니다.

Args:
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다.
    field_groups: 상세 그룹: ports, definition, source, paths, audit, all입니다. 생략하거나 비우면 요약을 반환합니다. ID는 include_ids로 선택합니다.
<!-- /instruction:list_library -->

## get_logic_by_id

<!-- instruction:get_logic_by_id -->
로컬 Grasshopper 정의에서 탐지한 구성요소·설명과 사이드카 metadata를 조회합니다. 실행 입력의 타입·단위·필수 여부는 metadata.capsule 계약에서 확인합니다.

반환: file_name·components·all_descriptions·metadata를 반환합니다. components는 문자열 탐지 결과이며 metadata.capsule은 실행 계약이 있을 때 포함됩니다.

Args:
    logic_id: 기존 Grasshopper 라이브러리 파일명에서 확장자를 뺀 이름입니다. 알고 있는 ID를 재사용하거나 list_library(include_ids=true)에서 얻습니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다.
    field_groups: 상세 그룹: ports, definition, source, paths, audit, all입니다. 생략하거나 비우면 요약을 반환합니다. ID는 include_ids로 선택합니다.
<!-- /instruction:get_logic_by_id -->

## list_capsules

<!-- instruction:list_capsules -->
기능별 Grasshopper 캡슐과 실행 감사 여부를 조회합니다. audited=true인 캡슐을 실행할 수 있습니다. 최대 50개를 반환합니다.

반환: capsules와 total·offset·limit·next_offset을 반환합니다. ports 그룹은 포트 이름만 포함합니다. 공개 입력에는 추가 페이지 offset이 없습니다.

Args:
    capability: 선택 필터: "analyze", "generate", "form_find", "aggregate".
    audited_only: true이면 run_gh_definition이 실행을 허용하는 캡슐만 나열합니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다.
    field_groups: 상세 그룹: ports, definition, source, paths, audit, all입니다. 생략하거나 비우면 요약을 반환합니다. ID는 include_ids로 선택합니다.
<!-- /instruction:list_capsules -->

## run_gh_definition

<!-- instruction:run_gh_definition -->
실행 감사를 통과한 Grasshopper 캡슐을 Rhino에서 계산합니다. 계약의 단위 그대로 입력하며 정의에 따라 문서에 형상을 베이크할 수 있습니다. 시간 초과 뒤에는 문서와 실행 상태를 확인합니다.

반환: status, ALMOND_OUT_*별 outputs, baked_guids, analysis_method·confidence·warnings·error를 반환합니다. rule_based는 예비 추정입니다.

Args:
    capsule_id: list_capsules에서 얻은 안정적인 캡슐 식별자입니다(예: "karamba_beam_v1").
    inputs: ALMOND_IN_ 포트 이름과 값의 객체입니다. 형상은 {"guids":["객체 GUID"]}, 숫자·정수·문자열·불리언은 JSON 값, 목록은 number[]/integer[]/string[]의 평탄한 배열입니다. 타입·단위·필수 여부는 metadata.capsule.inputs 계약을 따릅니다.
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
