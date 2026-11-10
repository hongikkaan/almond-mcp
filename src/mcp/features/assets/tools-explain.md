# tools.py explain

## list_drawing_assets

<!-- instruction:list_drawing_assets -->
변환 대기 원본을 포함한 모델·2D 자산 목록을 조회합니다. 사람·나무·기호 등 다이어그램은 list_diagram_assets로 조회합니다.

반환: assets와 total·offset·limit·truncated를 반환합니다. source_only는 변환 대기 상태이며 배치 가능한 3DM과 구분합니다.

Args:
    category: 라이브러리 분류 필터입니다. 선택 사항이며, 비어 있으면 모든 분류를 포함합니다.
    limit: 이 응답에서 반환할 최대 행 수입니다. 페이지를 전체 결과로 간주하기 전에 total과 페이지 처리 필드를 확인합니다.
    offset: 이 페이지의 시작 행을 0부터 세는 값입니다. 다음 페이지를 요청할 때도 같은 필터를 사용합니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다.
    field_groups: 선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별 정보는 include_ids로 별도 제어합니다.
<!-- /instruction:list_drawing_assets -->

## search_drawing_assets

<!-- instruction:search_drawing_assets -->
텍스트·분류·측정 치수로 모델·2D 자산을 검색합니다. 변환 대기 원본도 포함되므로 반환된 준비 상태를 확인합니다. 다이어그램은 search_diagram_assets로 검색합니다.

반환: assets와 total·offset·limit·truncated를 반환합니다. asset_id는 include_ids=true로 요청합니다. 변환 대기 항목의 next_tool·next_step을 확인합니다.

Args:
    query: 자유 텍스트 검색어입니다. 비어 있으면 텍스트 필터를 설정하지 않습니다.
    category: 라이브러리 분류 필터입니다. 선택 사항이며, 비어 있으면 모든 분류를 포함합니다.
    max_width_mm: 측정된 자산 너비의 최댓값이며, 밀리미터 단위입니다. 선택 사항이며, 0은 이 크기 필터를 해제합니다.
    max_depth_mm: 측정된 자산 깊이의 최댓값이며, 밀리미터 단위입니다. 선택 사항이며, 0은 이 크기 필터를 해제합니다.
    max_height_mm: 측정된 자산 높이의 최댓값이며, 밀리미터 단위입니다. 선택 사항이며, 0은 이 크기 필터를 해제합니다.
    limit: 이 응답에서 반환할 최대 행 수입니다. 페이지를 전체 결과로 간주하기 전에 total과 페이지 처리 필드를 확인합니다.
    offset: 이 페이지의 시작 행을 0부터 세는 값입니다. 다음 페이지를 요청할 때도 같은 필터를 사용합니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다.
    field_groups: 선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별 정보는 include_ids로 별도 제어합니다.
<!-- /instruction:search_drawing_assets -->

## get_drawing_asset

<!-- instruction:get_drawing_asset -->
모델·2D 자산의 파일 사용 가능 여부, 출처, 변환·갱신 상태를 조회합니다.

반환: asset의 요약·파일 상태와 요청한 상세 그룹을 반환합니다. 입력 asset_id는 응답에 반복되지 않을 수 있습니다.

Args:
    asset_id: include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다.
    field_groups: 선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별 정보는 include_ids로 별도 제어합니다.
<!-- /instruction:get_drawing_asset -->

## prepare_drawing_asset

<!-- instruction:prepare_drawing_asset -->
원본 사본을 검사하고 명시적 편집과 이미지 검토를 거쳐 등록용 3DM을 준비합니다. 기본 조립 구조·레이어·재질·원점은 보존합니다. 검토 확인은 실제 이미지와 파일 해시에 연결하며, 불확실한 실행은 status 단계에서 확인합니다.

반환: state·ready_for_registration·job_dir·next_stage와 검토 근거를 반환합니다. ready일 때 source_3dm을 등록에 사용할 수 있습니다. running/unconfirmed/failed는 상태와 error를 확인합니다.

Args:
    stage: inspect, normalize, verify 또는 status입니다. inspect는 작업을 생성하고, 이후 단계는 job_dir를 재사용합니다. status는 저장된 근거만 다시 읽습니다. 네이티브 작업을 실행하거나, 나중에 완료되었다는 이유로 확인되지 않은 작업의 단계를 올리지 않습니다.
    source_file: inspect에 사용할 원본 모델입니다. 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. 원본 바이트는 변경하지 않고 유지합니다.
    job_dir: 이전에 반환된 준비 작업의 job_dir입니다. 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. normalize, verify, status에 필수입니다.
    input_units: OBJ/STL/PLY/OFF/GLB/glTF의 명시적 원본 단위로 mm, cm, m, in 또는 ft를 지정합니다. 측정한 원본 단위를 사용합니다. 이후 단계에서는 생략하며, 3DM은 내장된 단위를 보존합니다.
    review: 검토 결과 객체입니다. normalize: {vision_reviewed:true, inspected_sha256:"확인한 해시", rotation_degrees_xyz:[x,y,z], translation:[x,y,z], remove:[{object_id:"ID",reason:"사유"}]}. 생략한 변환은 유지하며 translation은 원본 단위입니다. 최종 이미지를 본 뒤 verify: {vision_reviewed:true, final_sha256:"확인한 해시", name:"이름", asset_id:"ID"}. 첫 verify로 최종 이미지를 만든 후 검토 확인을 제출합니다.
    field_groups: 선택 가능한 값은 summary, parts, previews, provenance 또는 all입니다. 생략하면 미리 보기 경로를 포함하고, []이면 간략한 결과를 유지합니다. 페이지 처리는 parts에 적용됩니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다.
    offset: 이 페이지의 시작 행을 0부터 세는 값입니다. 다음 페이지를 요청할 때도 같은 필터를 사용합니다.
    limit: 부품 목록의 페이지 크기이며, 범위는 1..200입니다.
<!-- /instruction:prepare_drawing_asset -->

## register_drawing_asset

<!-- instruction:register_drawing_asset -->
준비한 3DM을 측정 치수와 평면·정면·우측면 도면이 있는 라이브러리 자산으로 게시합니다. 기존 자산 교체는 연결 인스턴스에 영향을 줄 수 있습니다. 게시 후 오류에서는 registration_applied를 확인하고 불확실하면 등록 상태부터 대조합니다.

반환: registration_applied, 자산·파일 경로와 live_index_refreshed를 반환합니다. 적용 여부가 null이고 requires_reconciliation이면 기존 등록과 파일을 확인합니다.

Args:
    source_3dm: 검토한 3DM 원본입니다. 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. preparation_job을 사용할 때는 해당 작업 응답의 source_3dm을 사용합니다.
    asset_id: 검토한 자산에 사용할 새 고정 라이브러리 식별자입니다.
    name: 사람이 읽을 수 있는 자산 이름입니다.
    category: 새 자산의 라이브러리 분류입니다.
    tags: 선택 사항인 설명용 검색 태그입니다.
    description: 선택 사항인 자산 설명입니다.
    source_url: 출처 이력으로 보존할 원래 원본 URL입니다. 선택 사항입니다.
    replace_existing: true이면 이 ID를 가진 기존 자산을 명시적으로 교체합니다. false이면 교체를 거부합니다.
    preparation_job: 완료된 준비 작업의 job_dir입니다. 선택 사항이며, 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. 검토를 거치는 다중 형식 변환 절차에는 필수입니다.
<!-- /instruction:register_drawing_asset -->

## get_asset_drawing

<!-- instruction:get_asset_drawing -->
등록 모델의 저장 도면 매니페스트·뷰 URI 또는 기존 시범 패키지를 조회합니다. 원본과의 일치 여부는 audit_asset_drawing으로 확인합니다.

반환: plan_svg_uri 등 저장 뷰 URI와 manifest를 반환합니다.

Args:
    asset_id: include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다.
    field_groups: 선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별 정보는 include_ids로 별도 제어합니다.
<!-- /instruction:get_asset_drawing -->

## generate_asset_drawing_views

<!-- instruction:generate_asset_drawing_views -->
등록 3DM 또는 지정 GLB에서 평면·정면·우측면 실루엣의 새 도면 패키지를 만듭니다. 기존 등록 도면의 저장된 변경을 반영하려면 refresh_asset을 사용합니다.

반환: 새 package_dir와 manifest를 반환합니다. 도면은 실루엣이며 제품의 정면 방향·시공 상세는 별도로 검토합니다.

Args:
    asset_id: 라이브러리 자산 ID입니다. 선택 사항이며, 이 값 또는 source_glb 중 하나를 제공합니다.
    source_glb: 사용자 지정 정적 GLB 원본입니다. 관리형 세션에서는 프로젝트 상대 경로, 독립 실행에서는 절대 경로를 사용합니다. 이 값 또는 asset_id 중 하나를 제공합니다.
    input_units: 사용자 지정 GLB 원본 단위로 mm 또는 m을 사용합니다. source_glb를 제공할 때 필수입니다.
    up_axis: 원본의 위쪽 축으로 y 또는 z를 사용합니다. 기본값은 y입니다.
    scales: 도면 축척의 분모 목록입니다. 선택 사항이며, 생략하면 [50, 100]을 사용합니다.
    source_references: source_id/title/url/publisher/locator/accessed_on/relationship/used_for/terms_url을 포함하는 참조 객체입니다. 선택 사항이며, 출처 이력이 정확성을 보증하지는 않습니다.
<!-- /instruction:generate_asset_drawing_views -->

## audit_asset_drawing

<!-- instruction:audit_asset_drawing -->
저장 도면 패키지의 파일 해시와 확인 가능한 원본의 변경 여부를 검사합니다.

반환: checked_files와 failures, source_geometry로 파일 무결성과 확인 가능한 원본 일치 여부를 반환합니다.

Args:
    package_dir: 이전 생성/조회 결과의 도면 패키지 디렉터리입니다. 관리형 Almond 세션에서는 프로젝트 상대 경로를 사용하며, 독립 실행 라이브러리 호출에서는 절대 경로가 필요합니다.
    source_glb: 원본 변경으로 오래된 상태가 되었는지 확인할 현재 원본 GLB입니다. 선택 사항이며, 동일한 관리형/독립 실행 경로 규칙을 사용합니다. 라이브러리에서 원본을 확인할 수 있으면 생략합니다.
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
모델·2D 자산을 Rhino 문서에 배치합니다. 3DM은 원본에 연결된 블록으로 삽입하며 공유 정의 갱신이 기존 인스턴스에 영향을 줄 수 있습니다. 불확실한 실패나 시간 초과 뒤에는 문서를 확인한 후 재시도합니다.

반환: asset_id·object_guid·definition_created를 반환합니다. object_guid는 삽입한 최상위 블록의 관찰에 사용합니다.

Args:
    asset_id: include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다.
    x: 현재 Rhino 문서 단위를 사용하는 배치 X 좌표입니다.
    y: 현재 Rhino 문서 단위를 사용하는 배치 Y 좌표입니다.
    z: 현재 Rhino 문서 단위를 사용하는 배치 Z 좌표입니다.
    rotation_degrees: 월드 Z축을 중심으로 한 회전각이며, 단위는 도입니다.
    scale: 양수인 균일 배치 축척입니다. 1이면 단위 변환 후 자산 크기를 유지합니다.
<!-- /instruction:place_drawing_asset -->

## search_asset_repository

<!-- instruction:search_asset_repository -->
모델·2D 요소 아카이브를 검색합니다. 도면 준비가 완료된 후보로 필터링할 수 있으며, 비-3DM 원본은 변환·등록 후 배치합니다.

반환: total과 assets를 반환합니다. 결과 ID는 include_ids=true로 요청하고 변환 안내 next_tool·next_step을 확인합니다.

Args:
    query: 자유 텍스트 검색어입니다. 비어 있으면 텍스트 필터를 설정하지 않습니다.
    kind: 저장소 유형 필터로 all, element 또는 model을 사용합니다.
    drawing_ready: true이면 도면 데이터가 준비된 자산으로 제한합니다.
    limit: 간략 목록에 포함할 최대 자산 수이며, 1..100 범위로 제한됩니다. 반환된 assets의 길이를 total과 비교합니다. 이 도구에는 offset/has_more 필드가 없습니다.
    include_ids: true이면 후속 호출에 필요한 ID를 포함합니다. 상세 항목은 field_groups로 별도 선택합니다.
    field_groups: 선택 가능한 세부 그룹은 dimensions, source, paths, drawing, metadata, audit 또는 all입니다. 생략하거나 비워 두면 요약을 유지합니다. 식별 정보는 include_ids로 별도 제어합니다.
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
편집 후 저장된 등록 3DM을 다시 측정하고 저장 도면을 재생성합니다. 원본 경로는 유지됩니다. Rhino 문서 저장과 기존 연결 인스턴스 갱신은 별도로 수행합니다. 게시가 적용되었거나 결과가 불확실하면 재실행 전에 등록 상태를 확인합니다.

반환: registration_applied·source_path_preserved·live_index_refreshed와 갱신 파일 경로를 반환합니다. registration_applied=true이면 색인 갱신 오류가 있어도 게시가 적용된 상태입니다.

Args:
    asset_id: include_ids=true를 지정한 해당 목록/검색 결과에서 얻은 기존 라이브러리 자산 ID 또는 이전부터 알고 있는 ID입니다.
<!-- /instruction:refresh_asset -->
