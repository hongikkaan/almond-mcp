# tools.py explain

## export_asset_contract

<!-- instruction:export_asset_contract -->
Rhino 객체를 GLB와 Almond 자산 계약 파일로 내보냅니다.

Args:
    guids: 기존 객체 관찰, 선택 또는 모델링 결과에서 얻은 현재 Rhino 객체 GUID입니다.
    asset_id: 안정적으로 유지할 ID입니다. 예: "canopy-pavilion-01". 영문자, 숫자, . _ -를 사용합니다.
    name: 사람이 읽을 수 있는 이름입니다. 기본값은 asset_id입니다.
    output_dir: 관리형 세션에서는 선택한 Plan 산출물 폴더에 대한 상대 경로이며, 기본값은 exchange입니다. 독립 실행에서는 대상 폴더이며, 기본값은 <user data dir>/exchange입니다.
<!-- /instruction:export_asset_contract -->

## import_asset_contract

<!-- instruction:import_asset_contract -->
Almond 자산 계약에 따라 GLB를 Rhino 문서로 가져옵니다.

Args:
    contract_path: export_asset_contract 또는 Blender 내보내기가 반환한 계약 경로입니다. 관리형 세션에서는 프로젝트 기준 상대 .almond.json 경로이고, 독립 실행에서는 절대 경로입니다.
    x_mm: 계약 앵커의 X 배치 좌표(밀리미터)입니다. 기본값은 0입니다.
    y_mm: 계약 앵커의 Y 배치 좌표(밀리미터)입니다. 기본값은 0입니다.
    z_mm: 계약 앵커의 Z 배치 좌표(밀리미터)입니다. 기본값은 0입니다.
    rotation_degrees: 월드 Z축 기준 회전입니다.
    layer: 대상 레이어입니다. 없으면 생성합니다.
<!-- /instruction:import_asset_contract -->

## get_blender_helper_script

<!-- instruction:get_blender_helper_script -->
Blender의 선택 형상 내보내기 또는 재료 설정에 사용할 Python 코드를 생성합니다.

Args:
    action: "export" 또는 "materials"입니다.
    asset_id: export에 필요한 값으로, 내보낸 파일에 사용할 안정적인 식별자입니다.
    name: 내보내기 표시 이름입니다. 기본값은 asset_id입니다.
    output_dir: 내보내기 대상 위치입니다. 관리형 세션에서는 선택한 Plan이 필요하며, 해당 산출물 디렉터리 아래의 상대 폴더를 사용합니다. 기본값은 exchange입니다. 독립 실행 호출의 기본값은 사용자 데이터의 exchange 폴더입니다.
    material_id: materials에 필요한, 알고 있는 라이브러리 재료 ID입니다.
    object_names: materials에 필요한 실제 Blender 객체 이름의 비어 있지 않은 목록입니다.
    include_ids: true이면 후속 호출에 사용할 ID를 포함합니다.
    field_groups: 선택 항목은 notes, audit, all입니다. script는 기본 응답에 유지됩니다.
<!-- /instruction:get_blender_helper_script -->

## response-672

<!-- instruction:response-672 -->
If importing into a destination Rhino is intended, pass the returned contract_path to import_asset_contract(contract_path=...) and choose its placement coordinates in mm; exporting alone does not request another import. For Blender, import the returned glb_path there and verify materials/placement; get_blender_helper_script supports export and materials, not import.
<!-- /instruction:response-672 -->

## response-677

<!-- instruction:response-677 -->
Run in Blender, then call import_asset_contract with the printed path.
<!-- /instruction:response-677 -->

## response-679

<!-- instruction:response-679 -->
Unknown material_id: {0}. Call list_materials.
<!-- /instruction:response-679 -->
