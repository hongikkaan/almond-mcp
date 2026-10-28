# 자산 작업

목록·검색·상세 조회는 `assets` 주제의 자산 목록·검색 절을 사용한다. 아래는 등록·배치·생성·교환·발행이 필요할 때 읽는다. 경로는 프로젝트 상대경로를 사용한다.

## 3DM 등록·배치

등록 원본은 **mm, Z-up, XY bbox 중심과 최저 Z가 원점**인 준비된 3DM이다. 객체 정리·방향 확인이 필요하면 almond-asset-converter 스킬을 사용한다. 등록 도구가 원본의 의미나 정면 방향을 판단하지는 않는다.

| 도구 | 입력 | 할 수 있는 일 |
|---|---|---|
| `register_drawing_asset` | `source_3dm`, 안정적 `asset_id`, `name`, 선택적 분류·출처·`replace_existing` | 준비된 3DM과 plan/front/right DXF·SVG·치수를 라이브러리에 등록. 동일 ID 갱신에만 replace_existing=true. |
| `place_drawing_asset` | `asset_id`, 문서 단위 `x/y/z`, 선택적 `rotation_degrees`, `scale` | 3DM을 문서 단위로 변환해 재사용 block으로 배치. 실제 크기는 scale=1. |
| `place_diagram_asset` | `asset_id`, `x/y/z`, 선택적 `rotation_degrees`, `scale` | Diagram 자산 배치. |

등록은 최대 100 MB·파생 Mesh 250,000 삼각형이며 미지원 객체가 있으면 실패한다. 갱신해도 이전 배치 block은 유지된다. `registration_applied=true`, `live_index_refreshed=false`이면 재등록 대신 재연결 후 조회한다. 다른 MCP 프로세스와 docked Asset Panel은 갱신 시점이 다를 수 있다.

## 파생 도면 생성·확인

| 도구 | 입력 | 할 수 있는 일 |
|---|---|---|
| `generate_asset_drawing_views` | `asset_id` 또는 `source_glb`, 명시적 `input_units`, `up_axis`, 선택적 `scales` | GLB의 평면·정면·우측면 파생 도면 생성. |
| `audit_asset_drawing` | `package_dir`, custom GLB는 현재 `source_glb`도 지정 | 도면 파일 무결성과 원본 변경 여부 확인. |

GLB 단위는 mm/m, 위축은 y/z를 명시한다. 파생 뷰는 Mesh silhouette이며 hidden line·시공 상세를 대신하지 않는다. DXF는 실물 mm, 기본 SVG 축척은 1:50·1:100이다.

## 교환·외부 발행

| 도구 | 입력 | 할 수 있는 일 |
|---|---|---|
| `export_asset_contract` | `guids`, `asset_id`, 선택적 `name`, `output_dir` | 선택 객체를 교환 패키지로 출력. |
| `import_asset_contract` | `contract_path`, 선택적 `x_mm/y_mm/z_mm`, 회전·레이어 | 교환 패키지를 Rhino 문서로 가져오기. |
| `get_blender_helper_script` | `action`, 작업에 필요한 자산·객체·재료·출력 인자 | Blender에서 사용할 helper script 조회. 실행과 별개. |
| `publish_to_chestnut` | `guids`, `asset_name`, 선택적 `behavior`, `asset_id` | Rhino 객체를 Chestnut에 발행. |
| `publish_objects_to_chestnut` | `guids`, `asset_name`, 선택적 body_type·collider·질량 | 물리 속성을 지정해 Chestnut에 발행. |

## 카메라 경로 산출물

| 도구 | 입력 | 할 수 있는 일 |
|---|---|---|
| `capture_conditioning_pass` | `shot` JSON, 선택적 `out_dir`, 크기·fps·passes·모드 | live Rhino에서 경로별 RGB·edge·depth 프레임과 카메라 기록 생성. |

shot은 orbit/track/keyframes 형식이며 경로 좌표는 모델 단위다. Wan 용도는 4n+1 프레임을 사용한다. 산출물에는 프레임·동영상·camera.json·깊이 범위·요약이 포함되며 동영상 생성에는 ffmpeg가 필요하다. 캡처 후 카메라 복원 상태를 확인한다.
