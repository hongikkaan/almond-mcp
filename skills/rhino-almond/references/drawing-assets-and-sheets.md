# 3DM 자산과 도면 Sheet

## 준비된 자산을 등록하고 쓰기

1. 외부 Almond Asset Converter에서 원본을 보존하며 형상을 정리하고 방향·원점·재료를 검토하라. 등록할 3DM은 mm 단위, Z-up, XY bounding box 중심과 최저 Z가 원점이어야 한다. 등록 도구는 자동 회전하거나 시각 검수를 대신하지 않는다.
2. `register_drawing_asset(source_3dm=<절대 3DM 경로>, asset_id=<안정적인 ID>, name=<이름>)`로 등록하라. category·tags·description·source_url은 필요한 값만 제공한다. 같은 ID를 갱신할 때만 `replace_existing=true`를 사용하라.
3. 성공 응답의 `registration_applied`, `live_index_refreshed`, `model_path`, `package_dir`를 확인하라. 복사한 3DM, plan/front/right DXF·SVG, `dimensions.json`은 같은 ID 아래에 저장된다. DXF는 실물 mm이고 SVG는 기본 1:50·1:100이다. A3에 맞는 경우에만 Sheet SVG도 생긴다.
4. `get_drawing_asset`으로 원본 가용성·측정 치수를, `get_asset_drawing`으로 도면 목록과 `plan_svg_uri`를 조회하라. 파일 무결성·원본 변경 여부는 `audit_asset_drawing(package_dir=...)`로 확인하라. 평면·정면·우측면은 mesh silhouette이며 hidden line·시공 상세·제품 정면 인식이 아니다.
5. `place_drawing_asset(asset_id=..., x=..., y=..., z=..., rotation_degrees=..., scale=1)`로 배치하라. 위치와 반환 bounds는 현재 Rhino 문서 단위이며 scale은 배율이다. 저장된 mm 형상은 문서 단위로 변환되고 재사용 가능한 block으로 들어온다. 일반 실제 크기 배치는 scale=1을 유지하라.

등록은 Mesh·Brep·Extrusion·Surface·SubD·중첩 block의 검증된 형상을 처리한다. 파일은 최대 100 MB, 파생 mesh는 최대 250,000 삼각형이다. 지원하지 않는 객체가 있으면 일부만 등록하지 않고 실패한다. 이름과 분류의 의미·front 방향은 등록 결과로 인증되지 않는다.

동일 ID 갱신은 새 버전 폴더와 manifest 백업을 남긴다. 이전 배치 block과 파일은 유지된다. `registration_applied=false`는 목록 갱신 전 실패이고, `registration_applied=true, live_index_refreshed=false`는 파일·목록 저장 뒤 현재 프로세스 인덱스 갱신이 실패한 상태다. 후자는 재등록하지 말고 재연결해 조회하라. 배치 응답이 불확실하면 실제 문서에서 생성 여부를 확인한 뒤 결정하라.

등록한 MCP 프로세스는 목록을 즉시 다시 읽는다. 다른 실행 중인 MCP 프로세스는 재연결해야 한다. Rhino의 docked Asset Panel은 설치된 배포 archive를 읽으므로 새 로컬 자산을 즉시 표시하지 않는다. 새 자산은 MCP 조회·배치를 사용하라.

custom GLB 파생 도면은 기존 `generate_asset_drawing_views(source_glb=..., input_units="mm" 또는 "m", up_axis="y" 또는 "z")`를 유지한다. 기존 generated 데이터와 하중·resource 읽기 경로도 유지하지만 generated/Meshy 선택·추천·배치 도구는 새 공개 목록에서 사용하지 않는다. Diagram 자산은 별도의 기존 도구를 사용하라.

## Sheet와 기존 Rhino Layout은 같은 목록이 아니다

**현재 Sheet API는 이미 존재하는 모든 Rhino Layout의 메타데이터 카탈로그가 아니다.** `list_drawing_sheets`는 Almond DB에 **등록된 Sheet만** 반환한다. 사용자가 만든 PageSpace 벡터 도면·텍스트·주석이 이미 Layout에 있어도, Sheet로 등록된 적이 없다면 목록에 나타나지 않는다. `sync_drawing_sheet`도 이미 등록된 `sheet_id`에 대한 관찰/동기화이며, 미등록 Layout 전체를 자동 발견하지 않는다.

실사용 검증(2026-10-24): `주민시설.3dm`의 원래 **13개 Layout**(DPRK-101~108, DPRK-201~205)은 정적 PageSpace 곡선·주석 중심이며 Rhino Detail viewport가 없었다. `list_drawing_sheets`는 별도로 생성한 **3개 QA Sheet**만 반환했다. 이 경험을 모든 3DM에 동일하게 적용하지 말고, **기존 Layout 인벤토리**와 **새 Layout/Detail 생성**의 서로 다른 작업으로 구분하라.

- 사용자가 요청한 것이 기존 도면의 **제목·layout GUID·paper·도면 종류·표기된 축척·Scene/Component/Plan 연계 메타데이터 목록**이면 Rhino Layout을 새로 만들거나 도면 선을 생성하지 않는다. 현재 전용 metadata-only catalog/refresh API는 **없다**. 읽기 전용으로 관찰할 수 있는 범위와 필요한 기능 개선을 명시한다.
- 축척은 Detail이 없는 PageSpace 도면에서 자동 측정할 수 없다. 도면에 적힌 축척·작업기록의 축척은 **표기·문서상 출처**로 구분하고, 네이티브 Detail scale 실측이라고 기재하지 않는다.
- `execute_rhino_script`는 조회 코드여도 Undo/후처리가 수반될 수 있다. 기존 Layout 전수조사를 위해 임의 코드를 실행할 때는 사용자의 쓰기·보기 변경 허용 범위를 확인하고, 실행 전후 문서 동일성을 검증한다.

## 새 모델 공간 도면을 Sheet로 등록하기

Sheet 하나는 실제 Rhino Layout 하나와 그 안의 등록된 detail viewport 하나를 가진다. 도면 형상은 모델 공간의 world-XY 영역에 작성하라. `drawing_type`은 도면 성격의 이름이며 3D 형상을 자동 투영하는 명령이 아니다.

`upsert_drawing_sheet`에는 실제 `expected_model_path`, `title`, `drawing_type`, `paper_mm=[폭,높이]`, `scale_denominator`, `model_bounds_mm=[minX,minY,minZ,maxX,maxY,maxZ]`를 제공하라. 축척 1:100은 100이다. XY 폭·깊이는 양수여야 하며 10 mm 종이 여백 안에 해당 축척으로 들어가야 한다. 모델·Layout 단위가 달라도 종이 크기와 도면 범위 입력은 mm다.

Scene·Component·Plan 참조로 관련 도면을 연결하라. 기존 Sheet 갱신은 반환된 `sheet_id`를 사용하고 모델·Layout identity를 바꾸지 마라. 생략한 참조는 유지되고 `[]`는 해제하며 `plan_id=""`는 Plan 연결을 해제한다.

Plan 작업 종료 시 `list_drawing_sheets(plan_id=...)`로 이름·범위·참조를 대조해 중복을 검토하라. `remove_drawing_sheet`는 등록만 해제하고 Layout·detail·도면 형상을 보존한다. 실제 형상 삭제는 이 호출의 효과가 아니다.

Layout 변경은 Rhino Undo로 완전히 복구된다고 가정하지 마라. 응답의 `layout_undo_supported=false`를 확인하라. 실패·타임아웃·수동 수정 뒤에는 `sync_drawing_sheet(expected_model_path=..., sheet_id=...)`로 기존 Layout을 읽고 기록을 맞추며 생성 요청을 무조건 다시 보내지 마라.
