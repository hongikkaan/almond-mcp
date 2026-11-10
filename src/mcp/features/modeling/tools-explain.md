# tools.py explain

## plan_section

<!-- instruction:plan_section -->
클리핑 평면에서 모델 공간의 단면·해치·입면 도면을 생성하거나 갱신합니다. Create는 해당 도면을 생성·교체하고 Update는 저장된 배치의 도면을 갱신합니다. 부분 완료·취소·시간 초과 뒤에도 생성된 도면은 남을 수 있으므로 결과 복구는 get_plan_section_result로 수행합니다.

반환: status·drawing_status와 result를 반환합니다. partial/cancelled이면 이미 생성된 도면이 남을 수 있습니다. result_id와 next_offset이 있으면 get_plan_section_result로 이어 읽습니다.

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
같은 문서 인스턴스에 보관된 PlanSection 실행 결과를 페이지별로 복구합니다. 만료·누락된 결과는 오류로 반환하며 결과 복구를 위해 도면을 재생성하지 않습니다.

반환: json_chunk와 offset·next_offset·total_characters·result_sha256을 반환합니다. 청크를 순서대로 합친 뒤 JSON을 읽습니다.

Args:
    result_id: plan_section.result.result_id에서 얻은 의미를 해석하지 않는 32자 결과 영수증 ID입니다.
    offset: 첫 페이지는 0, 이후에는 같은 결과의 next_offset을 그대로 입력합니다. UTF-16 코드 단위이므로 Python 문자열 길이로 계산하지 않습니다.
    expected_model_path: 바인딩된 저장 문서 경로입니다. 값을 명시하면 런타임 바인딩과 일치해야 합니다.
<!-- /instruction:get_plan_section_result -->

## execute_rhino_script

<!-- instruction:execute_rhino_script -->
전용 도구로 처리하기 어려운 모델링·편집·측정 코드를 연결된 RhinoCode에서 실행합니다. 문서 전환과 백그라운드 쓰기를 만들지 않습니다. 시간 초과·불확실한 결과는 재실행하지 말고 get_rhino_execution으로 확인합니다. 지침은 get_policy의 rhino_scripting과 rhinocode로 조회합니다.

반환: request_id·status·completed와 result를 반환합니다. 결과가 페이지화되거나 실행이 끝나지 않았으면 get_rhino_execution으로 이어서 읽습니다.

Args:
    script: 동기식 Python 소스, C# 문장 본문 또는 명령 매크로입니다. Python은 JSON-safe 값을 result에, C#은 결과 JSON을 result_json에 할당합니다. doc은 연결된 문서입니다. command는 !·Pause·대화상자 없이 끝나는 매크로를 입력합니다.
    language: python(기본값 Python 3), python2, csharp, csharp-script 또는 command입니다. 모든 모드는 공식 RhinoCode를 사용합니다.
    timeout_seconds: 1-600의 정수이며 기본값은 60입니다. 대기 시간만 제한합니다. 시간 초과 후에는 동일한 요청을 조회합니다.
<!-- /instruction:execute_rhino_script -->

## edit_planar_face

<!-- instruction:edit_planar_face -->
최상위 닫힌 Brep의 평면 한 면을 PushPull Extend로 이동합니다. 대상과 인접 면은 평면이고 객체는 잠금 해제 상태여야 하며 그룹·블록 편집을 종료한 뒤 사용합니다. 불확실한 실행은 재호출 전에 관찰합니다.

반환: status와 result에 변경 객체·관찰값·보존 결과를 반환합니다. 적용 여부가 불확실하면 새 관찰로 확인합니다.

Args:
    object_id: 연결된 문서의 관찰 결과에서 얻은 현재 잠기지 않은 최상위 닫힌 Brep GUID입니다.
    face_index: expected_geometry_crc와 동일한 형상 관찰 결과에서 얻은 0부터 시작하는 평면 인덱스입니다.
    expected_geometry_crc: 해당 관찰 결과의 형상 CRC입니다. 형상이 변경되었으면 교체 전에 편집을 거부합니다.
    translation: 문서 단위의 유한한 XYZ 숫자 3개입니다. 면 법선 방향 성분이 문서 허용오차를 초과해야 합니다.
    expected_model_path: 일반적으로 생략합니다. 런타임이 연결된 저장 문서를 제공합니다.
<!-- /instruction:edit_planar_face -->

## edit_planar_faces

<!-- instruction:edit_planar_faces -->
서로 다른 닫힌 Brep에서 평면 한 면씩을 단일 호출·Undo 기록으로 이동합니다. 단일 면 편집의 대상 조건을 따릅니다. 교체 중 실패하면 일부 변경이 남으므로 배치 전체를 자동 재실행하지 않습니다.

반환: status와 result에 배치 적용·실패 항목을 반환합니다. 일부 적용된 배치는 남은 대상만 새 관찰 후 처리합니다.

Args:
    edits: 서로 다른 Brep에 대한 항목 1..32개이며, 각 항목에는 object_id, face_index, expected_geometry_crc 및 translation이 들어갑니다. 단일 면 도구의 적용 대상 조건이 적용됩니다.
    expected_model_path: 일반적으로 생략합니다. 런타임이 연결된 저장 문서를 제공합니다.
<!-- /instruction:edit_planar_faces -->

## save_rhino_document

<!-- instruction:save_rhino_document -->
사용자가 영구 저장을 요청한 연결 문서 전체를 기존 .3dm 경로에 저장합니다. 다른 작업의 변경도 포함되므로 미확정 편집과 그룹·블록 편집을 먼저 정리합니다. 확인되지 않은 저장은 재실행 전에 상태를 대조합니다.

반환: status·saved·modified로 저장 및 문서 변경 상태를 반환합니다.

<!-- /instruction:save_rhino_document -->

## setup_modeling

<!-- instruction:setup_modeling -->
정의된 Material과 구축 Layer를 Rhino 문서에 등록·정렬합니다. 객체의 기존 레이어·ByLayer 설정·metadata는 유지합니다. incomplete나 오류이면 이미 변경된 항목을 응답에서 확인합니다.

반환: status와 applied를 반환합니다. incomplete이면 항목별 성공·실패와 보존 결과를 확인합니다.

Args:
    overwrite: Material과 Layer 모두에 적용되는 필수 불리언입니다. false는 기존 값을 유지하고, 없는 항목을 만들며, 차이를 보고합니다. true는 사전 정의된 속성을 갱신합니다.
<!-- /instruction:setup_modeling -->

## list_materials

<!-- instruction:list_materials -->
이름·용도에 맞는 라이브러리 PBR 재료와 매핑 정보를 조회합니다.

반환: materials와 total을 반환합니다. 후속 할당에 필요한 재료 ID는 include_ids=true로 요청합니다.

Args:
    category: 선택 사항인 라이브러리 분류 필터입니다. 비워 두면 모든 분류를 포함합니다.
    query: 자유 텍스트 검색어입니다. 비워 두면 텍스트 필터를 설정하지 않습니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다.
    field_groups: 선택 사항인 상세 그룹: display, physical, metadata, source, paths, audit 또는 all. 생략하거나 비워 두면 요약을 유지하며, include_ids는 식별 정보 포함 여부를 별도로 제어합니다.
<!-- /instruction:list_materials -->

## assign_material

<!-- instruction:assign_material -->
Rhino 객체에 라이브러리 PBR 재료를 적용합니다. 기존 레이어는 유지하고 metadata는 요청한 항목만 추가합니다. 응답에서 부분 적용과 확인되지 않은 결과를 구분합니다.

반환: requested_count·applied_count, 재료 적용·metadata 첨부 여부와 대상 정보를 반환합니다. 부분 적용과 실패 항목을 확인합니다.

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
