# tools.py explain

## plan_section

<!-- instruction:plan_section -->
클리핑 평면의 방향·깊이·참여 대상을 기준으로 활성 모델에서 단면선과 선택적인 해치·입면선을 계산해 모델 공간에 생성하거나 갱신합니다. 같은 클리핑의 기존 생성 도면이 교체되며 수동 편집이 사라질 수 있습니다. 부분 완료나 취소 뒤에도 결과가 남을 수 있습니다.

Args:
    operation: Create: 생성 또는 기존 도면 교체. Update: 기존 도면 재생성.
    clipping_ids: 클리핑 평면 GUID 목록. 비어 있을 수 없으며 중복은 한 번만 처리.
    points: Create만: 클리핑 GUID별 절대 도면 원점 [x,y] 또는 [x,y,z], 문서 단위.
    hatch: 해치 생성 허용. 원본 단면 스타일의 채움과 형상 조건을 따름. 기본 true.
    elevation: 입면선 포함. 기본 true.
    small_details: 작은 상세 보호 여부. 기본 true.
    near_width: 가까운 입면선 출력 두께(mm). 기본 0.09, 양수이며 far_width 이상.
    far_width: 먼 입면선 출력 두께(mm). 기본 0.04, 양수이며 near_width 이하.
    near_dark: 가까운 입면선 출력 농도 0..100%. 기본 80, far_dark 이상.
    far_dark: 먼 입면선 출력 농도 0..100%. 기본 45, near_dark 이하.
    expected_model_path: 생략: 연결된 저장 문서 경로. 지정: 일치 여부 확인.
<!-- /instruction:plan_section -->

## get_plan_section_result

<!-- instruction:get_plan_section_result -->
drawing_06-generate_plan_section tool의 큰 결과를 영수증으로 조회합니다. 같은 result_id의 json_chunk를 next_offset이 null일 때까지 이어 붙여 JSON으로 해석합니다. 저장된 실행 결과이며 현재 형상을 재관찰하지 않습니다. 결과는 같은 Bridge 프로세스·문서에서 최대 1시간 보관되지만 개수·용량 제한이나 재시작으로 더 일찍 사라질 수 있습니다.

Args:
    result_id: drawing_06-generate_plan_section tool의 result.result_id.
    offset: 첫 페이지 기본 0, 이후 반환된 next_offset 사용. UTF-16 코드 단위.
    expected_model_path: 생략: 연결된 저장 문서 경로. 지정: 일치 여부 확인.
<!-- /instruction:get_plan_section_result -->

## execute_rhino_script

<!-- instruction:execute_rhino_script -->
연결된 RhinoCode에서 모델링·편집·측정 코드를 실행합니다. 전용 도구로 처리하기 어려운 작업에 사용합니다.

Args:
    script: 동기식 Python 소스, C# 문장 본문 또는 명령 매크로입니다. Python은 JSON-safe 값을 result에, C#은 결과 JSON을 result_json에 할당합니다. doc은 연결된 문서입니다. command는 !·Pause·대화상자 없이 끝나는 매크로를 입력합니다.
    language: python(기본값 Python 3), python2, csharp, csharp-script 또는 command입니다. 모든 모드는 공식 RhinoCode를 사용합니다.
    timeout_seconds: 1-600의 정수이며 기본값은 60입니다. 대기 시간만 제한합니다. 시간 초과 후에는 동일한 요청을 조회합니다.
<!-- /instruction:execute_rhino_script -->

## edit_planar_face

<!-- instruction:edit_planar_face -->
닫힌 Brep의 평면 한 면을 PushPull Extend로 이동합니다. 그룹·블록 편집을 종료한 일반 모델에서 사용합니다. 현재 객체의 면 번호와 geometry_crc를 같은 관찰에서 얻어 입력합니다.

result는 편집 결과 또는 오류를 담은 JSON 문자열입니다. 오류 응답에 mutation_state가 항상 포함되지는 않습니다.

Args:
    object_id: 연결된 문서의 관찰 결과에서 얻은 현재 잠기지 않은 최상위 닫힌 Brep GUID입니다.
    face_index: expected_geometry_crc와 동일한 형상 관찰 결과에서 얻은 0부터 시작하는 평면 인덱스입니다.
    expected_geometry_crc: 해당 관찰 결과의 형상 CRC입니다. 형상이 변경되었으면 교체 전에 편집을 거부합니다.
    translation: 문서 단위의 유한한 XYZ 숫자 3개입니다. 면 법선 방향 성분이 문서 허용오차를 초과해야 합니다.
    expected_model_path: 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
<!-- /instruction:edit_planar_face -->

## edit_planar_faces

<!-- instruction:edit_planar_faces -->
서로 다른 닫힌 Brep의 평면을 한 면씩 단일 Undo 기록으로 이동합니다. 그룹·블록 편집을 종료한 일반 모델에서 사용합니다. 각 객체의 면 번호와 CRC는 같은 형상 관찰에서 얻습니다.

result는 배치 결과 또는 오류를 담은 JSON 문자열입니다. 준비 단계에서 한 항목이 거부되면 객체 교체를 시작하지 않습니다. 처리 상태와 항목별 결과는 mutation_state와 items에서 확인합니다.

Args:
    edits: 서로 다른 Brep에 대한 항목 1..32개이며, 각 항목에는 object_id, face_index, expected_geometry_crc 및 translation이 들어갑니다. 단일 면 도구의 적용 대상 조건이 적용됩니다.
    expected_model_path: 생략하면 현재 연결의 저장 문서 경로를 자동 적용합니다. 명시하면 그 경로와 일치하는지 확인합니다.
<!-- /instruction:edit_planar_faces -->

## save_rhino_document

<!-- instruction:save_rhino_document -->
연결된 문서 전체를 기존 .3dm 경로에 저장합니다. 사용자에게 영구 저장을 요청받은 경우 사용합니다.
<!-- /instruction:save_rhino_document -->

## setup_modeling

<!-- instruction:setup_modeling -->
라이브러리의 표준 재료와 구축 시스템별 레이어를 연결된 Rhino 문서에 설정합니다. 재료를 등록하고 `M` 아래 분류·시스템·부재 역할별 레이어와 색·재료를 구성합니다.

- **`overwrite=false`**: 없는 항목 생성, 기존 속성 유지 및 차이 보고.
- **`overwrite=true`**: 없는 항목 생성, 기존 항목의 사전 정의 속성 갱신.

반환 JSON의 `applied=true`는 기준과의 차이·오류가 없는 상태를 뜻합니다. 차이나 오류가 남으면 `incomplete`이며, 이 경우에도 일부 항목이 이미 생성·변경됐을 수 있습니다.

객체별 재료 지정에는 `model_04-list_materials`와 `model_01-assign_material`을 사용합니다.

Args:
    overwrite: Material과 Layer 모두에 적용되는 필수 불리언입니다. false는 기존 값을 유지하고, 없는 항목을 만들며, 차이를 보고합니다. true는 사전 정의된 속성을 갱신합니다.
<!-- /instruction:setup_modeling -->

## list_materials

<!-- instruction:list_materials -->
라이브러리 재료를 이름·설명·태그 또는 분류로 찾습니다. 결과는 Rhino 문서에 이미 적용된 재료 목록이 아닙니다. 적용에 필요한 material_id는 include_ids=true로 조회합니다. result는 재료 목록 또는 오류를 담은 JSON 문자열입니다.

Args:
    category: 분류 정확히 일치. 대소문자 구분; 생략 시 전체.
    query: 이름·설명·태그 검색. 대소문자 구분 없음.
    include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
    field_groups: 선택 사항인 상세 그룹: display, physical, metadata, source, paths, audit 또는 all. 생략하거나 비워 두면 요약을 조회합니다.
<!-- /instruction:list_materials -->

## assign_material

<!-- instruction:assign_material -->
Rhino 객체에 라이브러리 재료와 선택적인 구축 메타데이터를 적용합니다. 렌더 재료는 객체에 직접 지정되며 레이어는 바뀌지 않습니다. 중복 GUID는 하나로 처리합니다.

반환 result는 적용 결과 또는 오류를 담은 JSON 문자열입니다. 실제 렌더 재료와 사용자 문자열은 Rhino 객체 속성에서 확인할 수 있습니다. inspect_02의 user_dictionary는 이 사용자 문자열과 같은 항목이 아닙니다.

Args:
    guids: 할당할 현재 Rhino 객체 GUID입니다. 관찰 결과나 생성 결과를 재사용합니다.
    material_id: model_04-list_materials tool(include_ids=true)에서 얻은 라이브러리의 표준 재료 ID입니다.
    apply_render_material: true이면 지정된 객체에 표준 렌더 재료를 적용합니다.
    attach_metadata: true이면 Almond 재료/구축 메타데이터를 부착합니다. false이면 요청한 렌더 재료만 적용합니다.
    structural_role: 선택 사항인 구조 역할 메타데이터이며, attach_metadata와 함께 사용합니다.
    construction_system: 알려진 구축 시스템 ID입니다. attach_metadata=true일 때 사용합니다. construction_reference를 함께 지정하면 같은 시스템이어야 합니다.
    floor: 선택 사항인 층 레이블 메타데이터이며, attach_metadata와 함께 사용합니다.
    construction_detail: 선택 사항인 구축 상세 설명이며, attach_metadata와 함께 사용합니다.
    construction_reference: {"kind":"construction_system","id":"확인한 system_id"} 형식의 출처 참조입니다. attach_metadata=true일 때 사용합니다. construction_system도 지정하면 같은 시스템이어야 합니다.
<!-- /instruction:assign_material -->

## response-750

<!-- instruction:response-750 -->
Setup ran but its result is unavailable. Inspect Rhino before retrying.
<!-- /instruction:response-750 -->

## response-754

<!-- instruction:response-754 -->
Material assignment ran but its result could not be returned. Inspect Rhino before retrying.
<!-- /instruction:response-754 -->

## response-755

<!-- instruction:response-755 -->
Material assignment returned no valid applied-object result. Inspect Rhino before retrying.
<!-- /instruction:response-755 -->
