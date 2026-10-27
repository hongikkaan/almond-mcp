# 자산 검색·배치·도면·출처

Rhino 패널 조작은 [패널 사용법](rhino-archive-quickstart.md), MCP 도구 입력은 [자산 작업 지침](../modeling/guidance/references/asset-workflows.md)을 따른다. 아래는 라이브러리·등록·배치·파생 도면·출처의 계약이다.

## 라이브러리 탐색

Rhino에서는 `Almond` 또는 `AlmondLibraryBrowser`를 연다. Python만으로 탐색하려면 준비된 환경에서 다음 명령을 실행한다.

```powershell
& ./src/engine/.venv/Scripts/python.exe -B -m almond_mcp.cli library --open
```

기본 주소는 `http://127.0.0.1:8767/`, 다른 포트는 `--port 8768`로 지정한다. Ctrl+C로 종료한다. Rhino와 인터넷 없이 로컬 파일을 탐색할 수 있다. 파일이 없는 항목은 사용 불가 상태와 원본 링크를 표시한다.

| 자료 | 저장소 위치 |
|---|---|
| 생성 모델·passport·sidecar·preview | `asset/models/GeneratedAssetfiles` |
| Drawing asset | `asset/drawing/DrawingAssetfiles` |
| 파생 투영 도면 | `asset/drawing/Draftingfiles` |
| 도면 표현 규칙 | `asset/drawing/DrawingRecipes` |

실행 환경의 `RHINO_MCP_*_DIR`이 저장소 경로보다 우선한다. 파일이나 manifest를 변경한 뒤 archive를 다시 시작한다. 검색은 이름·ID·분류·태그·drawing role을 사용하며 즐겨찾기는 브라우저 localStorage에 남는다. HTTP 서버는 loopback에 바인딩하고 Host 검사와 파일 allowlist를 사용한다. 업로드나 임의 파일 탐색 기능은 없다.

- `search_asset_repository(query, kind, drawing_ready, limit)`: 통합 검색.
- `almond://repository/{asset_id}`: 출처·표현·로컬 경로를 포함한 MCP record.
- `/api/catalogue`, `/api/assets/{asset_id}.json`: HTTP 목록과 개별 record. 내보낸 목록은 모델 파일 묶음이 아니다.

## 준비한 3DM 등록·배치

새 Drawing 자산의 원본은 검토·정리한 3DM이다. 정리·방향 판단·시각 검토는 외부 Almond Asset Converter가 담당한다. 등록은 mm·Z-up·바닥 중심 원점을 확인하며 원본 파일을 회전하거나 실제 정면의 적절성을 판정하지 않는다.

`register_drawing_asset`의 native extractor는 복사한 File3dm에서 중첩 블록 변환을 해석하고 지원 형상을 mesh로 추출해 hash·측정 bounds를 확인한다. 미지원 형상이나 불완전한 추출은 발행을 막는다. 같은 asset ID 아래 복사한 3DM, plan/front/right DXF·SVG, `dimensions.json`을 준비하며 기존 GLB 투영 구현을 재사용한다.

라이브러리 쓰기는 OS lock으로 직렬화하고 파일을 확인한 뒤 manifest를 atomic하게 교체한다. 명시적 교체는 이전 version과 manifest backup을 보존한다. 발행 전 실패는 이전 항목을 유지하며, 발행 후 색인 갱신 실패는 `registration_applied=true`로 알린다. 이때 재등록 대신 연결을 새로 해 색인을 읽는다.

`get_asset_drawing`, drawing resource, audit, `place_drawing_asset`은 같은 manifest 항목을 해석한다. 배치는 3DM hash와 문서 단위를 확인하고 원본 revision·단위별 block definition을 재사용한다. 새 원본을 등록해도 기존 배치는 보존한다. 완료 응답 누락만으로 배치를 반복하지 않는다.

등록 결과는 현재 MCP 프로세스와 repository UI에서 보인다. native Asset Panel은 설치된 archive snapshot을 읽으므로 즉시 갱신되지 않는다. 다른 실행 중 MCP 프로세스도 재연결해 라이브러리를 다시 읽어야 한다.

## 기존 GLB·Scene 배치 장부

공개 Generated/Meshy 목록·검색·추천·fit·배치 도구는 종료됐다. 기존 생성 manifest·resource reader·하중 소비자와 GLB 파생 package는 호환을 유지한다. Diagram 자산은 계속 제공한다.

기존 GLB의 passport는 `asset.extras.almond.passport`, `.almond.json` sidecar와 manifest에 있다. 실제 치수·polygon count와 목표값·편차, anchor·footprint·clearance, 재료·생성 기록·미확인 사항을 구분한다. importer가 extras를 잃을 수 있으므로 sidecar와 checksum을 보존한다.

기존 생성 GLB는 mm·Y-up이다. 일반 glTF의 metre 관례와 구분하며 뷰어의 0.001 표시 배율은 다운로드 형상을 바꾸지 않는다. `export_asset_contract`, `import_asset_contract`, `get_blender_helper_script`는 geometry와 sidecar를 함께 교환한다.

`retrieval_store.upsert_room` accepts only six finite
`bounds_mm` values; the `rooms` table has no curve/Brep identity. An assigned
`instance` uses `room.min_z` as its default floor elevation. The
`validate_scene_layout` query runs R-tree instance-AABB collision preflight and
compares each assigned instance AABB with the Room AABB, reporting
`passed_scope=legacy_asset_instances`,
`registered_object_collisions_checked=false` and `live_verified=false`.
An enclosing box or a curved Room reference stored only in metadata does not
support exact curved-boundary containment.

일반 Rhino 객체의 Scene·Component 등록에는 asset instance가 필요 없다. 자산 하중의 기존 소비 경로는 [구조 해석](../structure/structural-validation.md#해석-대상과-자산-하중)에 둔다.

## Layout·Sheet 호환

Sheet DB CRUD/sync와 native 등록 경로는 종료됐다. 기존 Sheet 자료와 Rhino Layout은 보존하며 옛 Sheet 참조는 Component 등록 해제를 막지 않는다. Drawing 자산은 라이브러리 manifest·파일에 등록하고 프로젝트 DB에 복제하지 않는다. Viewport·Named View·Layout 용지는 `get_rhino_viewport_image`로 조회·캡처한다.

## GLB에서 투영 도면 만들기

- `get_asset_drawing(asset_id)`: 미리 생성한 도면 package.
- `generate_asset_drawing_views`: 라이브러리 모델 또는 custom GLB의 plan/front/right 투영.
- `audit_asset_drawing`: 출력 hash와 현재 source geometry를 비교. custom 파일은 현재 경로를 함께 전달한다.

custom GLB 호출 예시:

```json
{
  "source_glb": "C:/Projects/MyProject/custom-bench.glb",
  "input_units": "m",
  "up_axis": "y",
  "scales": [50, 100]
}
```

custom 입력의 단위·방향은 추측하지 않는다. 지원 입력은 embedded float position과 triangle index를 가진 정적·비압축 GLB이며 한도는 100 MB, 250,000 triangles다. animation·skinning·morph·외부 buffer·필수 extension·sparse/normalized accessor는 명시적으로 거절한다.

생성 결과는 새 디렉터리에 기록하며 이전 도면을 덮어쓰지 않는다. 각 축척의 SVG, full-size mm DXF, 용지에 들어가는 A3 landscape SVG sheet를 만든다. 기본 축척은 1:50·1:100이다. 용지에 맞지 않는 view는 임의로 축소하지 않고 경고한다. SVG의 50 mm 보정선을 실제 크기 인쇄로 확인한다. 화면에 맞춘 preview는 인쇄 축척이 아니다.

Y-up 입력은 `(X,-Z,Y)`로 Z-up에 변환하고 front는 +Y 방향, right는 -X 방향으로 본다. 이는 좌표 규칙이며 물체의 실제 정면을 인식한 결과가 아니다. 입력 translation과 원점은 유지한다.

투영 triangle의 합집합에서 외곽을 얻고 0.01 mm precision grid를 사용한다. 30,000 triangles를 넘으면 긴 변 2,044 pixels의 raster contour 경로를 사용한다. 이 경로에서는 작은 구멍·세부가 사라질 수 있다. 단순화 공차는 종이에서 0.05 mm, 모델에서 최대 5 mm이며 각 view가 방법과 한계를 기록한다. 총 오차가 독립적으로 검증됐다고 해석하지 않는다.

결과는 배치·표현용 silhouette다. 내부 visible/hidden edge, 단면, hatch, 벽체 층, 체결부나 성능을 추론하지 않는다. 실제 Rhino 도면 영역·축척·Layout은 기존 Rhino 문서에서 별도로 편집한다.

## 출처와 파생 관계

기존 source resource의 내부 `get_asset_sources(asset_id)` reader는 기록된 생성 근거와 빈틈을 반환한다. `search_detail_sources`는 dataholz·Lignumdata·ARCAT·CADdetails·WikiHouse·LibreCAD 같은 참조 목록을 검색하며 도면 파일을 내려받지는 않는다. 이후 찾은 자료를 기존 모델의 생성 입력이라고 소급 기록하지 않는다.

새 입력·참조에는 제목, 저자/설계자, 발행자, canonical URL, 항목·page·figure, 접근일, revision, 사용 관계와 영향을 받은 asset ID를 기록한다. 보유한 파일은 checksum을 남긴다. `source_references`가 요구하는 terms URL 등 기존 schema 필드는 유지한다. 자료가 없으면 `unknown`·`not_supplied`로 남기며 추측하지 않는다.

생성 기록에는 실제 제출 prompt·settings, provider/model version, task ID, timestamp, 제공된 seed, input/output hash를 보관한다. token·cookie·만료 URL은 넣지 않는다. normalization·회전·축척·retopology는 parent/output hash를 가진 파생 단계다. 단순 brief나 task ID를 실제 API 요청·원본 이미지의 증거로 취급하지 않는다.

`source-register.json`은 `provenance.json`·catalogue·manifest·passport에서 만든 색인이다. 직접 고치지 말고 원본을 수정한 뒤 재생성한다.

```powershell
& ./src/engine/.venv/Scripts/python.exe -B src/mcp/tools/document_generation_sources.py
& ./src/engine/.venv/Scripts/python.exe -B src/mcp/tools/document_generation_sources.py --check
```

`drawing.json`은 source file/geometry hash와 파생 파일 hash를 연결한다. 모델 metadata만 바뀐 경우와 형상이 바뀐 경우를 구분한다. SVG는 출처·축척·방법을 포함하지만 DXF와 교환할 때는 인접 JSON도 보존한다.

유료 생성 도구 `run_meshy_batch.py`는 POST 전에 intent를 기록하고 완료가 불확실한 제출을 자동 재시도하지 않는다. 이미지 검토 후 mesh 단계로 넘어간다. `prepare_organic_meshes.py`는 원본에서 파생 형상을 만들고 `import_organic_batch.py`가 생성 근거·catalogue·passport를 연결한다.
