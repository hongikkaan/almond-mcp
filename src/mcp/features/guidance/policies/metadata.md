# Rhino 메타데이터

## 키와 저장 범위 확인

- 기존 객체를 편집하기 전에 현재 값과 저장 위치를 확인한다. 객체 속성 User Text는 객체에 붙는 문자열이다. 형상 User Text, 객체·형상 각각의 UserDictionary, 문서 전체의 User Text(`RhinoDoc.Strings`)는 별도 저장소다. 문서 전체에 적용할 정보만 문서 범위에 기록하고, 객체 키 사전을 문서 키 규약으로 사용하지 않는다.
- `inspect_02-get_objects` tool의 `fields=["user_dictionary"]`와 `filters.user_dictionary`는 객체 속성·형상의 UserDictionary를 대상으로 한다. 객체 User Text는 Rhino의 속성 패널에서, 문서 User Text는 문서 속성에서 확인한다. 자동화가 필요하면 `script_02-run_rhino` tool을 통해 해당 저장소만 읽는다.
- 이 정책과 함께 반환되는 `policy`의 `public_object_keys`와 `internal_object_keys`에서 기존 키를 확인한다. 이미 같은 의미의 키가 있으면 기존 기능에 맞는 키와 저장 위치를 재사용한다. 내부 키는 해당 기능에서 관리하므로 일괄 기입하지 않는다. 사용자가 정한 키와 별도 메타데이터는 보존한다.

## 기존 기능으로 기록

- 재료나 구축 의도를 기록할 때는 `model_04-list_materials` tool과 `research_01-get_construction_guidance` tool에서 필요한 ID를 확인한 뒤 `model_01-assign_material` tool의 해당 입력을 사용한다. `floor`는 사용자나 프로젝트가 정한 층 표기를 사용한다. `construction_detail`은 사람이 읽는 구축 설명이고 `construction_reference`는 확인한 시스템 ID를 가리킨다. 구조 역할은 근거가 있는 경우에 지정하고, 재료의 시각 속성은 Rhino 재료에 둔다.
- 구조 해석용 단면이나 단부 조건은 `analysis_04-validate_structure` tool의 설명과 구조 지침을 확인한다. 해석 대상 곡선의 객체 속성 User Text에 단면 `almond:section`(예: `rect 300x640`)이나 단부 조건 `almond:release`(예: `pinned_start`)을 지정할 수 있다. 해석에서 읽는 값이므로 해당 조건을 의도한 경우에만 쓴다.
- 전용 도구가 없는 키를 스크립트로 변경할 때는 저장소와 대상만 지정하고 기존 속성을 보존한다. 변경 후 같은 저장소에서 값을 다시 읽어 확인한다. 새 사용자 키는 허용되며, 기존 키를 자동으로 이름 변경하거나 다른 저장소로 옮기지 않는다.
