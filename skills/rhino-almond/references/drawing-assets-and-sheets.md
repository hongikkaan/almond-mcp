# 3DM 자산과 도면 Sheet

## 준비된 자산을 등록하고 쓰기

1. 외부 Almond Asset Converter에서 원본을 보존하며 형상을 정리하고 방향·원점·재료를 검토하라. 등록할 3DM은 mm 단위, Z-up, XY bounding box 중심과 최저 Z가 원점이어야 한다. 등록 도구는 자동 회전하거나 시각 검수를 대신하지 않는다.
2. `register_drawing_asset(source_3dm=<프로젝트 상대 3DM 경로>, asset_id=<안정적인 ID>, name=<이름>)`로 등록하라. category·tags·description·source_url은 필요한 값만 제공한다. 같은 ID를 갱신할 때만 `replace_existing=true`를 사용하라.
3. 성공 응답의 `registration_applied`, `live_index_refreshed`, `model_path`, `package_dir`를 확인하라. 복사한 3DM, plan/front/right DXF·SVG, `dimensions.json`은 같은 ID 아래에 저장된다. DXF는 실물 mm이고 SVG는 기본 1:50·1:100이다. A3에 맞는 경우에만 Sheet SVG도 생긴다.
4. `get_drawing_asset`으로 원본 가용성·측정 치수를, `get_asset_drawing`으로 도면 목록과 `plan_svg_uri`를 조회하라. 파일 무결성·원본 변경 여부는 `audit_asset_drawing(package_dir=...)`로 확인하라. 평면·정면·우측면은 mesh silhouette이며 hidden line·시공 상세·제품 정면 인식이 아니다.
5. `place_drawing_asset(asset_id=..., x=..., y=..., z=..., rotation_degrees=..., scale=1)`로 배치하라. 위치와 반환 bounds는 현재 Rhino 문서 단위이며 scale은 배율이다. 저장된 mm 형상은 문서 단위로 변환되고 재사용 가능한 block으로 들어온다. 일반 실제 크기 배치는 scale=1을 유지하라.

등록은 Mesh·Brep·Extrusion·Surface·SubD·중첩 block의 검증된 형상을 처리한다. 파일은 최대 100 MB, 파생 mesh는 최대 250,000 삼각형이다. 지원하지 않는 객체가 있으면 일부만 등록하지 않고 실패한다. 이름과 분류의 의미·front 방향은 등록 결과로 인증되지 않는다.

동일 ID 갱신은 새 버전 폴더와 manifest 백업을 남긴다. 이전 배치 block과 파일은 유지된다. `registration_applied=false`는 목록 갱신 전 실패이고, `registration_applied=true, live_index_refreshed=false`는 파일·목록 저장 뒤 현재 프로세스 인덱스 갱신이 실패한 상태다. 후자는 재등록하지 말고 재연결해 조회하라. 배치 응답이 불확실하면 실제 문서에서 생성 여부를 확인한 뒤 결정하라.

등록한 MCP 프로세스는 목록을 즉시 다시 읽는다. 다른 실행 중인 MCP 프로세스는 재연결해야 한다. Rhino의 docked Asset Panel은 설치된 배포 archive를 읽으므로 새 로컬 자산을 즉시 표시하지 않는다. 새 자산은 MCP 조회·배치를 사용하라.

custom GLB 파생 도면은 기존 `generate_asset_drawing_views(source_glb=..., input_units="mm" 또는 "m", up_axis="y" 또는 "z")`를 유지한다. 기존 generated 데이터와 하중·resource 읽기 경로도 유지하지만 generated/Meshy 선택·추천·배치 도구는 새 공개 목록에서 사용하지 않는다. Diagram 자산은 별도의 기존 도구를 사용하라.

## 기존 Layout과 도면

도면·Sheet DB 등록·동기화 도구는 제거됐다. 기존 DB 행, Rhino Layout, 도면 파일은 보존되며 등록 장부를 만들기 위해 새 Layout을 생성하지 않는다. 도면 자산 조회는 파일 manifest를 사용하고 프로젝트 DB 색인을 요구하지 않는다.

`get_rhino_viewport_image(view="a")`는 viewport·named view·layout별 이름과 GUID를 반환한다. GUID를 view에 전달하면 화면을 전환하지 않고 PNG를 볼 수 있다. 기본 `scale_percent=50`이며 100은 원본이다. Layout은 용지와 Detail을 캡처한다. 선명도가 더 필요하면 퍼센트를 올린다.

기존 PageSpace의 제목·축척·도면 종류 등 추가 내용은 필요한 범위만 실제 문서에서 관찰한다. Detail 없는 정적 도면의 축척을 이름으로 추정하지 않는다. Layout 생성·편집이나 파일 내보내기는 사용자가 요청한 경우에 수행한다.
