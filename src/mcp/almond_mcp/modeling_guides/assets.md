### 자산 목록·검색

Drawing 자산은 준비된 3DM, Diagram 자산은 도식용 자료다. `assets` 및 `exchange-capture` 주제(`get_modeling_guide`로 조회)은 해당 작업을 할 때만 읽는다.

| 도구| 입력  | 할 수 있는 일  |
| --- | -- | -- |
| `search_asset_repository` | `query`, 선택적 `kind`, `drawing_ready`, `limit` | 통합 자산 후보 검색. |
| `list_drawing_assets`  | 선택적 `category`, `limit`, `offset`| Drawing 자산 목록 조회. |
| `search_drawing_assets`| 검색어·분류·최대 치수 조건  | 크기와 용도에 맞는 Drawing 자산 검색.  |
| `get_drawing_asset` | `asset_id`| 3DM 가용성·측정 치수·메타데이터 조회.|
| `get_asset_drawing` | `asset_id`| 자산의 평면·정면·측면 도면 파일 목록 조회. |
| `list_diagram_assets`  | 선택적 `category`, `limit`, `offset`| Diagram 자산 목록 조회. |
| `search_diagram_assets`| 검색어·분류·최대 치수 조건  | Diagram 자산 검색.|
| `get_diagram_asset` | `asset_id`| Diagram 파일·크기·배치 조건 조회. |
| `get_retrieval_status` | 선택적 `include_ids`  | 자산 색인·검색 기능 상태 조회.  |

# 자산 작업

목록·검색·상세 조회는 SKILL.md의 자산 절을 사용한다. 아래는 등록·배치·생성·교환·발행이 필요할 때 읽는다. 경로는 프로젝트 상대경로를 사용한다.

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
