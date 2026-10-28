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
