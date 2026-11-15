# tools.py explain

## list_drawing_assets

<!-- instruction:list_drawing_assets -->
모델·2D 자산 목록과 사용 준비 상태를 조회합니다. 원본만 있는 자산은 바로 배치할 3DM이 아닐 수 있습니다. 상세 조회에 필요한 ID는 include_ids=true로 포함합니다.

페이지 결과에 next_offset은 없으며, truncated=true면 같은 필터로 offset에 반환된 자산 수를 더해 이어 읽습니다. result는 목록 또는 오류를 담은 JSON 문자열입니다.

Args:
    category: 라이브러리 분류 필터입니다. 선택 사항이며, 비어 있으면 모든 분류를 포함합니다.
    limit: 한 페이지에 반환할 최대 항목 수입니다.
    offset: 이 페이지의 시작 행을 0부터 세는 값입니다. 다음 페이지를 요청할 때도 같은 필터를 사용합니다.
    include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
    field_groups: 선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다.
<!-- /instruction:list_drawing_assets -->

## search_drawing_assets

<!-- instruction:search_drawing_assets -->
모델·2D 자산을 검색어, 분류와 최대 치수로 검색합니다. 여러 검색어 중 하나 이상 일치하면 포함하고, 일치 단어가 많은 순으로 표시합니다. 결과에는 파일·모델·도면 상태와 페이지 정보가 포함됩니다.

최대 치수 필터는 등록 치수를 비교하며, 해당 치수가 없는 자산도 포함될 수 있습니다. 상세 정보는 include_ids=true로 얻은 ID를 asset_04-get tool에 전달합니다. result는 검색 결과 또는 오류를 담은 JSON 문자열입니다.

Args:
    query: 이름·설명·제품·분류·태그 등 부분 일치. 대소문자 무시.
    category: 분류의 정확한 값. 대소문자 무시, 빈 값은 전체.
    max_width_mm: 너비 상한(mm). 양수일 때 적용.
    max_depth_mm: 깊이 상한(mm). 양수일 때 적용.
    max_height_mm: 높이 상한(mm). 양수일 때 적용.
    limit: 페이지 크기: 기본 10, 1..100.
    offset: 0부터 시작. truncated=true면 같은 조건의 offset에 반환 건수를 더해 이어 조회.
    include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
    field_groups: 선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다.
<!-- /instruction:search_drawing_assets -->

## get_drawing_asset

<!-- instruction:get_drawing_asset -->
모델·2D 자산의 등록 정보와 사용 가능 상태를 조회합니다. paths로 원본·모델 경로를 확인할 수 있습니다. result는 자산 정보 또는 오류를 담은 JSON 문자열입니다.

Args:
    asset_id: include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다.
    include_ids: ID 포함 옵션. 조회한 asset_id는 응답에 반복되지 않을 수 있습니다.
    field_groups: 선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다.
<!-- /instruction:get_drawing_asset -->

## prepare_drawing_asset

<!-- instruction:prepare_drawing_asset -->
원본 사본을 검사·편집·시각 검토해 등록용 3DM을 준비합니다. inspect로 job을 만들고, 필요하면 normalize로 수정한 뒤 verify합니다. 수정이 필요 없으면 normalize를 건너뛰고 verify할 수 있습니다.

첫 verify는 최종 미리보기와 해시를 생성합니다. 이를 검토한 뒤 같은 해시·이름·ID를 넣어 다시 verify하면 등록 준비 상태가 됩니다. ready_for_registration은 호출자의 해시 연계 검토 확인이며 형상 적합성을 자동 판정했다는 뜻은 아닙니다. 관리형 source_file은 프로젝트 내부 경로여야 합니다.

Args:
    stage: inspect, normalize, verify 또는 status입니다. inspect는 작업을 생성하고, 이후 단계는 job_dir를 재사용합니다. status는 저장된 근거만 다시 읽습니다. 네이티브 작업을 실행하거나, 나중에 완료되었다는 이유로 확인되지 않은 작업의 단계를 올리지 않습니다.
    source_file: inspect에 사용할 원본 모델입니다. 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. 원본 바이트는 변경하지 않고 유지합니다.
    job_dir: 이전에 반환된 준비 작업의 job_dir입니다. 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. normalize, verify, status에 필수입니다.
    input_units: OBJ/STL/PLY/OFF/GLB/glTF의 명시적 원본 단위로 mm, cm, m, in 또는 ft를 지정합니다. 측정한 원본 단위를 사용합니다. 이후 단계에서는 생략하며, 3DM은 내장된 단위를 보존합니다.
    review: 검토 결과 객체입니다. normalize: {vision_reviewed:true, inspected_sha256:"확인한 해시", rotation_degrees_xyz:[x,y,z], translation:[x,y,z], remove:[{object_id:"ID",reason:"사유"}]}. 생략한 변환은 유지하며 translation은 원본 단위입니다. 최종 이미지를 본 뒤 verify: {vision_reviewed:true, final_sha256:"확인한 해시", name:"이름", asset_id:"ID"}. 첫 verify로 최종 이미지를 만든 후 검토 확인을 제출합니다.
    field_groups: 선택 가능한 값은 summary, parts, previews, provenance 또는 all입니다. 생략하면 미리 보기 경로를 포함하고, []이면 간략한 결과를 유지합니다. 페이지 처리는 parts에 적용됩니다.
    include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
    offset: 이 페이지의 시작 행을 0부터 세는 값입니다. 다음 페이지를 요청할 때도 같은 필터를 사용합니다.
    limit: 부품 목록의 페이지 크기이며, 범위는 1..200입니다.
<!-- /instruction:prepare_drawing_asset -->

## register_drawing_asset

<!-- instruction:register_drawing_asset -->
준비한 3DM을 모델 라이브러리에 등록하고 치수와 평면·입면 도면 패키지를 생성합니다. 생성 도면은 투영 실루엣으로 내부 가시선·숨은선이나 구성 레이어를 표현하지 않습니다.

파생 메시가 250,000 삼각형을 넘으면 등록에 실패합니다. asset_07-prepare tool의 준비 완료는 등록 성공을 보장하지 않습니다. 등록 후 asset_04-get tool로 자산 상태를 확인할 수 있습니다.

Args:
    source_3dm: 검토한 3DM 원본입니다. 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. preparation_job을 사용할 때는 해당 작업 응답의 source_3dm을 사용합니다.
    asset_id: 자산 ID. preparation_job 사용 시 검토한 ID와 일치.
    name: preparation_job 사용 시 검토한 이름과 일치.
    category: 새 자산의 라이브러리 분류입니다.
    tags: 선택 사항인 설명용 검색 태그입니다.
    description: 선택 사항인 자산 설명입니다.
    source_url: 출처 이력으로 보존할 원래 원본 URL입니다. 선택 사항입니다.
    replace_existing: true이면 이 ID를 가진 기존 자산을 명시적으로 교체합니다. false이면 교체를 거부합니다.
    preparation_job: 완료된 준비 작업의 job_dir입니다. 선택 사항이며, 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. 검토를 거치는 다중 형식 변환 절차에는 필수입니다.
<!-- /instruction:register_drawing_asset -->

## get_asset_drawing

<!-- instruction:get_asset_drawing -->
등록 자산의 저장 도면 패키지를 조회합니다. manifest에서 도면 파일·축척·치수·출처와 투영 한계를 확인할 수 있습니다. 도면은 자산의 원본 형상을 투영한 것으로 배치 인스턴스의 변환이 적용된 결과는 아닙니다.

Args:
    asset_id: include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다.
    include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
    field_groups: 선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다.
<!-- /instruction:get_asset_drawing -->

## generate_asset_drawing_views

<!-- instruction:generate_asset_drawing_views -->
등록 3DM 또는 사용자 지정 GLB의 메쉬를 평면·정면·우측면 실루엣으로 투영합니다. 실물 크기 mm DXF와 축척 SVG를 생성하며, 세 뷰가 A3 시트 영역에 들어가면 시트 SVG도 생성합니다. 시트가 생략되어도 성공할 수 있습니다.

실루엣에는 단면과 내부 가시선·은선이 없으며 정면은 좌표계 기준입니다. 축척에 따른 단순화나 근사로 작은 형상의 윤곽이 달라질 수 있습니다. 결과는 별도 drawing-runs 패키지에 저장되며 등록 자산의 도면을 갱신하지 않습니다.

Args:
    asset_id: 등록 3DM 자산 ID. source_glb와 택일.
    source_glb: 정적·비압축 삼각형 GLB, 최대 100 MB·250,000 삼각형.
        관리형: 프로젝트 상대 경로 / 독립 실행: 절대 경로.
    input_units: GLB 원본 단위 mm 또는 m. source_glb에 필수.
    up_axis: GLB 위쪽 축 y 또는 z. 기본 y: (X,-Z,Y)로 변환. 등록 3DM에는 미적용.
    scales: 축척 분모 1~4개, 중복 없는 정수 5~1000. 기본 [50, 100].
    source_references: 이 도면에 첨부하는 출처. 원본 모델 생성 이력의 증빙은 아님.
        필수: source_id, title, url, publisher, locator, accessed_on, relationship, used_for, terms_url.
        relationship: background_reading, dimensional_reference, assembly_reference, post_generation_reference.
<!-- /instruction:generate_asset_drawing_views -->

## audit_asset_drawing

<!-- instruction:audit_asset_drawing -->
저장 도면 패키지의 manifest에 기록된 파일 해시와 원본을 비교합니다. 검사 성공은 도면 내용의 적합성이나 manifest의 완전성을 보장하지 않으며, 목록이 비어 있으면 검사 파일 0개로도 성공할 수 있습니다. 원본을 찾지 못하면 파일만 검사하고 원본 비교는 생략합니다.

Args:
    package_dir: 생성/조회 결과의 package_dir를 그대로 입력합니다. 관리형 세션은 프로젝트 안의 패키지와 설정된 도면 라이브러리·drawing-runs의 패키지를 검사합니다. 독립 실행에서는 절대 경로가 필요합니다.
    source_glb: 원본 변경으로 오래된 상태가 되었는지 확인할 현재 원본 GLB입니다. 선택 사항이며, 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. 라이브러리에서 원본을 확인할 수 있으면 생략합니다.
<!-- /instruction:audit_asset_drawing -->

## asset_catalogue_resource

<!-- instruction:asset_catalogue_resource -->
Compact catalogue; retrieve individual passports/previews on demand.
<!-- /instruction:asset_catalogue_resource -->

## asset_preview_resource

<!-- instruction:asset_preview_resource -->
Existing Blender preview for a known catalogue id.
<!-- /instruction:asset_preview_resource -->

## place_drawing_asset

<!-- instruction:place_drawing_asset -->
모델·2D 자산을 Rhino 문서에 블록으로 배치합니다. 3DM은 원본에 연결된 블록이며 같은 정의를 사용하는 배치에 정의 갱신이 반영됩니다. 결과는 성공 또는 오류를 담은 JSON 문자열입니다.

Args:
    asset_id: include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다.
    x: 원본 기준점의 월드 X 좌표. 문서 단위, 기본 0.
    y: 원본 기준점의 월드 Y 좌표. 문서 단위, 기본 0.
    z: 원본 기준점의 월드 Z 좌표. 문서 단위, 기본 0.
    rotation_degrees: 월드 Z축 기준 회전각(도). 기본 0.
    scale: 균일 배치 축척. 기본 1, 0 초과 100 이하.
<!-- /instruction:place_drawing_asset -->

## search_asset_repository

<!-- instruction:search_asset_repository -->
모델·2D 요소 아카이브를 검색하고 후보의 사용 가능 상태를 확인합니다. 결과는 전체 매치 수와 limit개까지의 후보이며 이어지는 페이지는 없습니다. 잘린 경우 검색어나 유형으로 범위를 좁힐 수 있습니다.

원본만 있는 자산은 즉시 배치 가능한 상태가 아닐 수 있습니다. 상세 정보와 경로는 후보 ID로 asset_04-get tool에서 조회합니다.

Args:
    query: 이름·ID·분류·variant·재료 ID·태그·역할 검색. 대소문자 무시, 공백으로 구분한 모든 단어 포함.
    kind: all(기본), element 또는 model.
    drawing_ready: true이면 도면 데이터가 준비된 자산으로 제한합니다.
    limit: 반환 개수: 기본 20, 1..100으로 보정.
    include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
    field_groups: dimensions, source, paths, drawing, metadata, audit 또는 all. 검색 결과에 있는 필드만 표시.
<!-- /instruction:search_asset_repository -->

## repository_asset_resource

<!-- instruction:repository_asset_resource -->
Unified object metadata, source evidence, representations and local files.
<!-- /instruction:repository_asset_resource -->

## response-399

<!-- instruction:response-399 -->
Placed geometry deviates from catalogue dimensions beyond tolerance; inspect the source model (see manifest match note).
<!-- /instruction:response-399 -->

## response-400

<!-- instruction:response-400 -->
Load a Bridge with drawing_asset_extract=2 before registering or refreshing a 3DM asset
<!-- /instruction:response-400 -->

## response-403

<!-- instruction:response-403 -->
Library has no passport; upgrade the asset pack.
<!-- /instruction:response-403 -->

## response-404

<!-- instruction:response-404 -->
Source register missing; update the asset pack
<!-- /instruction:response-404 -->

## response-406

<!-- instruction:response-406 -->
No bundled drawing for this asset; generate views on demand
<!-- /instruction:response-406 -->

## response-409

<!-- instruction:response-409 -->
This asset ID belongs to the separate Diagram collection
<!-- /instruction:response-409 -->

## response-410

<!-- instruction:response-410 -->
Asset files and manifest were published. Reconnect to refresh the index; do not repeat registration: {0}
<!-- /instruction:response-410 -->

## response-411

<!-- instruction:response-411 -->
Choose exactly one asset_id or source_glb
<!-- /instruction:response-411 -->

## response-417

<!-- instruction:response-417 -->
Model file missing for {0}; run almond-mcp fetch-assets to download it.
<!-- /instruction:response-417 -->

## response-419

<!-- instruction:response-419 -->
Inspect the placed geometry and relevant Rhino views before concluding the placement is correct.
<!-- /instruction:response-419 -->

## response-423

<!-- instruction:response-423 -->
Rhino drawing-asset import timed out; inspect the model before retrying.
<!-- /instruction:response-423 -->

## response-424

<!-- instruction:response-424 -->
Rhino bridge is unavailable. Start RhinoAlmondBridge first.
<!-- /instruction:response-424 -->

## refresh_asset

<!-- instruction:refresh_asset -->
편집·저장된 등록 3DM을 다시 측정하고 평면·입면 도면을 새 리비전으로 발행합니다. 원본 경로와 이전 도면은 유지됩니다. 도면은 메쉬 투영 실루엣으로 내부 가시선·은선이나 구성 레이어를 표현하지 않습니다.

열린 Rhino 문서의 연결 블록을 갱신하거나 저장하지 않습니다. 공유 블록 정의를 별도로 갱신하면 기존 인스턴스에도 반영되지만, 배치 당시 메타데이터는 자동 갱신되지 않습니다.

Args:
    asset_id: 등록 3DM 모델 자산 ID.
<!-- /instruction:refresh_asset -->
