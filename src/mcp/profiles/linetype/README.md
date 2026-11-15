# 도면 선종 정의

`manifest.json`은 실행 중인 Python 소스의 `profiles/linetype/`에서 매 스타일 적용 시 직접 읽는다. AppData나 `RHINO_MCP_DRAWING_RECIPE_DIR`로 복사하지 않는다. Recipe·PAT 등 다른 자산의 경로는 바꾸지 않는다. wheel에서도 같은 package 상대 경로를 사용한다.

`schema_version: 1`, `linetypes`의 고유한 `name`과 `segments`를 사용한다. 세그먼트는 양의 유한 숫자 `length`(Rhino 문서 길이 단위)와 불리언 `is_solid`이며, 적어도 하나의 실선이 필요하다. 레이어에는 선종 이름을 기록한다. 등록된 이름은 이 자료의 정의를 사용하므로 기존 AppData A4의 inline 복사본을 수정할 필요가 없다. 그 밖의 사용자 선종은 기존 레시피의 명시적 `linetype_segments`를 호환 입력으로 유지한다.

`legacy_name_rules`는 기존 이름 기반 패턴을 보존한다. 이름에 `contains`가 포함되면 해당 segments를 사용하고, 등록되지 않은 다른 이름은 `legacy_default_segments`를 사용한다. 둘 모두 기존 코드의 수치를 옮긴 자료다. Rhino 문서에 동명이 있으면 외부 패턴과 달라도 기존 정의와 index를 보존·재사용한다. 새 이름일 때만 이 자료로 생성한다.

레이어의 `Continuous`, `ByLayer`, `ByParent` 입력은 실제 레이어 패턴 `Continuous`로 처리하며 사용자 선종을 만들지 않는다. 이 예약 이름의 명시적 세그먼트 지정은 허용하지 않는다.

Recipe는 각 목록·상세·적용 호출 전에 새 snapshot을 읽는다. `sample.json`과 `is_sample: true` 파일은 제외한다. JSON/ID 오류·중복 ID가 있으면 기존 정상 snapshot은 유지하지만 호출은 오류를 반환하므로 잘못된 최신 파일을 수정해야 한다. 파일을 작성하는 동안에는 임시 확장자로 저장 후 `.json`으로 교체하는 것이 좋다. 이 갱신은 데이터 로딩이며 실행 중 Python 소스/RHP 교체를 뜻하지 않는다.
