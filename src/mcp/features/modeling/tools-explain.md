# tools.py explain

## plan_section

<!-- instruction:plan_section -->
클리핑 평면에서 모델 공간의 단면·해치·입면 도면을 생성하거나 갱신합니다. 부분 완료나 취소 뒤에도 만들어진 도면은 남을 수 있습니다.

Args:
    operation: Create 또는 Update입니다.
    clipping_ids: 확인된 클리핑 평면 GUID의 비어 있지 않은 목록입니다. 중복된 식별자는 한 번만 처리합니다.
    points: Create에서만 사용하는 선택적 매핑입니다. 요청한 클리핑 GUID를 문서 단위의 절대 도면 원점 [x,y] 또는 [x,y,z]에 대응시킵니다. Update에서는 생략합니다.
    hatch: 기존 원본 단면 스타일로 단면 해치를 생성합니다.
    elevation: 클리핑 평면 뒤에 보이는 입면 곡선을 포함합니다.
    small_details: true이면 기존의 작은 상세 보호 모드를 유지합니다.
    near_width: 가장 가까운 입면 객체의 출력 선 두께(mm)입니다. 양수이며 far_width 이상이어야 합니다. 최종 출력에도 유지됩니다.
    far_width: 가장 먼 입면 객체의 출력 선 두께(mm)입니다. 양수이며 near_width 이하여야 합니다. 최종 출력에도 유지됩니다.
    near_dark: 가장 가까운 입면 객체의 출력 농도 백분율입니다. 0..100 범위이며 far_dark 이상이어야 합니다. 최종 출력에도 유지됩니다.
    far_dark: 가장 먼 입면 객체의 출력 농도 백분율입니다. 0..100 범위이며 near_dark 이하여야 합니다. 최종 출력에도 유지됩니다.
    expected_model_path: 런타임이 제공하는 바인딩된 저장 문서 경로입니다. 값을 명시하면 해당 바인딩과 일치해야 합니다.
<!-- /instruction:plan_section -->

## get_plan_section_result

<!-- instruction:get_plan_section_result -->
보관된 PlanSection 실행 결과를 페이지별로 조회합니다.

Args:
    result_id: plan_section.result.result_id에서 얻은 의미를 해석하지 않는 32자 결과 영수증 ID입니다.
    offset: 첫 페이지는 0, 이후에는 같은 결과의 next_offset을 그대로 입력합니다. UTF-16 코드 단위이므로 Python 문자열 길이로 계산하지 않습니다.
    expected_model_path: 바인딩된 저장 문서 경로입니다. 값을 명시하면 런타임 바인딩과 일치해야 합니다.
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
닫힌 Brep의 평면 한 면을 PushPull Extend로 이동합니다. 그룹·블록 편집을 종료한 일반 모델에서 사용합니다.

Args:
    object_id: 연결된 문서의 관찰 결과에서 얻은 현재 잠기지 않은 최상위 닫힌 Brep GUID입니다.
    face_index: expected_geometry_crc와 동일한 형상 관찰 결과에서 얻은 0부터 시작하는 평면 인덱스입니다.
    expected_geometry_crc: 해당 관찰 결과의 형상 CRC입니다. 형상이 변경되었으면 교체 전에 편집을 거부합니다.
    translation: 문서 단위의 유한한 XYZ 숫자 3개입니다. 면 법선 방향 성분이 문서 허용오차를 초과해야 합니다.
    expected_model_path: 일반적으로 생략합니다. 런타임이 연결된 저장 문서를 제공합니다.
<!-- /instruction:edit_planar_face -->

## edit_planar_faces

<!-- instruction:edit_planar_faces -->
서로 다른 닫힌 Brep의 평면을 한 면씩 단일 Undo 기록으로 이동합니다. 그룹·블록 편집을 종료한 일반 모델에서 사용합니다.

Args:
    edits: 서로 다른 Brep에 대한 항목 1..32개이며, 각 항목에는 object_id, face_index, expected_geometry_crc 및 translation이 들어갑니다. 단일 면 도구의 적용 대상 조건이 적용됩니다.
    expected_model_path: 일반적으로 생략합니다. 런타임이 연결된 저장 문서를 제공합니다.
<!-- /instruction:edit_planar_faces -->

## save_rhino_document

<!-- instruction:save_rhino_document -->
연결된 문서 전체를 기존 .3dm 경로에 저장합니다. 사용자에게 영구 저장을 요청받은 경우 사용합니다.
<!-- /instruction:save_rhino_document -->

## setup_modeling

<!-- instruction:setup_modeling -->
정의된 Material과 구축 Layer를 Rhino 문서에 등록·정렬합니다.

Args:
    overwrite: Material과 Layer 모두에 적용되는 필수 불리언입니다. false는 기존 값을 유지하고, 없는 항목을 만들며, 차이를 보고합니다. true는 사전 정의된 속성을 갱신합니다.
<!-- /instruction:setup_modeling -->

## list_materials

<!-- instruction:list_materials -->
라이브러리 PBR 재료와 매핑 정보를 조회합니다.

Args:
    category: 선택 사항인 라이브러리 분류 필터입니다. 비워 두면 모든 분류를 포함합니다.
    query: 자유 텍스트 검색어입니다. 비워 두면 텍스트 필터를 설정하지 않습니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다.
    field_groups: 선택 사항인 상세 그룹: display, physical, metadata, source, paths, audit 또는 all. 생략하거나 비워 두면 요약을 유지하며, include_ids는 식별 정보 포함 여부를 별도로 제어합니다.
<!-- /instruction:list_materials -->

## assign_material

<!-- instruction:assign_material -->
Rhino 객체에 라이브러리 PBR 재료를 적용합니다. 요청한 경우 구법 metadata도 기록합니다.

Args:
    guids: 할당할 현재 Rhino 객체 GUID입니다. 관찰 결과나 생성 결과를 재사용합니다.
    material_id: list_materials(include_ids=true)에서 얻은 라이브러리의 표준 재료 ID입니다.
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
