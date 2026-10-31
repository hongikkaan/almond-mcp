# tools.py explain

## get_retrieval_status

<!-- instruction:get_retrieval_status -->
Returns compact diagnostics for the local structured retrieval system.
This is an intrinsically bounded diagnostic: fixed scalar counts/status and configured index names, not asset records.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
<!-- /instruction:get_retrieval_status -->

## get_rhino_context

<!-- instruction:get_rhino_context -->
Read selected LIVE Rhino context on the UI thread. sections accepts document, selection, viewport, editor and display_modes; default is ["document"]. Unrequested sections are not collected.
Document/selection/viewport responses also contain compact editor mode/target/stable so isolation is immediately visible. Request editor for provider evidence and warnings; sections=[] skips editor observation for capability-only calls.
editor reports mode (model/group/block/unknown), the known target and stable. Only a verified normal model is stable; active isolation, transitions and unsupported editor versions are unstable. Unknown target identity remains null, never inferred from selection.
display_modes lists at most 128 installed mode names/GUIDs. Shaded, Dark and CadWhite are choices only if actually installed; do not invent aliases for custom modes.

Includes document identity/path, units/tolerances, object/layer counts, a bounded selection summary and camera/display metadata. This query does not create layers, geometry, dimensions or an Undo record. Unavailable values are null with warnings.
Counts and the current view are context, not a geometric or visibility validation.
Request only the context needed for the task. project_info already verifies the live document; do not repeat this call merely to check whether that document is live.

Args:
    selection_limit: Maximum selected object summaries, from 0 to 200; total/truncated are still reported.
    recursive: False by default: summarize complete top-level groups and block instances.
        True expands nested members only to depth; partial groups remain object selections.
    depth: 1..8, default 1. IDs are omitted unless include_ids=true.
    include_image: False keeps the JSON-only response. True returns JSON text first and
        the current PNG from the same native UI call. An image_error preserves available
        context when capture fails. Use this when the current viewport is needed visually.
Returns:
    JSON with status, document, selection, viewport and warnings, or an explicit error.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
<!-- /instruction:get_rhino_context -->

## analyze_block_reculviely

<!-- instruction:analyze_block_reculviely -->
Read nested block structure or resolve a block occurrence without modifying the document.

Requests and responses are bounded to 256 KiB of UTF-8 JSON. Unknown, unsupported and truncated observations remain unverified. Requires Bridge block_analysis=1.

Args:
    mode: outline traverses objects and nested definitions; resolve-block finds
        candidates for the current editing context along an explicit occurrence path.
    options: outline accepts ids or path, otherwise scope (selected/viewport/document),
        depth and output budgets. field_groups is a nonempty list of summary, objects,
        annotations and transforms; the default is a compact summary. include_geometry
        and annotations explicitly request their details. Narrow IDs/path/depth after
        truncation; max_items also bounds eligible visits (reason=max_visits).
        resolve-block accepts only path: 1..65 GUIDs from the top-level instance inward.
    expected_model_path: Usually omitted; the runtime supplies the bound document path.
    include_ids: Include IDs when needed; supplied target IDs are not repeated.
Returns:
    JSON with status, mode, document identity/units/tolerance and data, or an explicit error.
<!-- /instruction:analyze_block_reculviely -->

## get_rhino_viewport_image

<!-- instruction:get_rhino_viewport_image -->
Return a Rhino viewport, Named View or Layout as a PNG image, without activating it.

Omit view to capture the current view. Pass view="a" to list viewports, named_views, and layouts, with only name and guid for each entry. Then pass the desired GUID as view.
Names need not be unique. Named Views render the saved camera off screen using Shaded by default; they never replace the visible viewport. Layouts capture the paper area, including its details, not the surrounding workspace. A current Layout also captures its paper, even when a detail is active.

For capture resolution and Layout print appearance, follow [BASIC-INSTRUCTIONS.md](../../BASIC-INSTRUCTIONS.md#get_rhino_viewport_image-화면으로-관찰하기).
No temporary image file is created. Capture does not change camera, selection or Undo state, or prove geometric correctness. A failed or oversized image is an error; lower scale_percent explicitly instead of receiving a silently resized image.

Args:
    view: Empty for current view, "a" for the grouped list, or a listed GUID.
    scale_percent: Integer from 1 to 100; default 75. Use 100 for visual drawing review. Controls pixels, not a Layout Detail's drawing scale.
    include_usage: False returns only an image. True also returns dimensions and an
        illustrative token estimate (32px patches x 1.2, without provider resizing).
        Actual usage depends on the client's model and detail setting, which MCP
        does not supply. PNG compression reduces bytes, not pixel-token counts.
    display_mode: Installed display mode name or GUID. Empty preserves the current
        model viewport mode; Named View/group/block captures default to Shaded. List
        available modes with get_rhino_context(sections=["display_modes"], include_ids=true).
        Realtime rendering modes such as Raytraced are rejected; this tool does not
        wait for asynchronous rendering to finish.
    labels: True by default. Transient pixels show top-level group name/GUID, block
        instance name/GUID and ungrouped object GUID, without creating document objects.
        At most 200 labels; explicit smaller targets/depth narrow a truncated overlay.
    depth: 1..8, default 1; higher values expose nested entity labels.
    target_kind: view (default), group or block. group/block frame target bounds in a
        detached viewport and label that target; surrounding geometry stays visible.
    target_id: Persistent group GUID or block instance GUID for group/block; leave view
        empty. Definition GUIDs are not block instance targets.
    Layouts retain each detail's mode, reject a mode override, and explicitly warn that
        detail labels are unavailable; capture a Named View/model viewport for labels.
Returns:
    One MCP PNG image by default, with text only for explicit warnings/usage, or the grouped name/GUID list for view="a".
    Images are limited to 16 megapixels and 4 MiB. No repeated path or GUID metadata.
<!-- /instruction:get_rhino_viewport_image -->
<!-- instruction:get_rhino_objects -->

읽기 전용으로 일반 모델 객체의 범위·속성·그룹·형상을 조회한다. `scope`는 현재 문서 가시 객체 `visible`(기본값), `selected`, 명시 GUID `ids`, 숨긴 객체를 포함한 `document` 중 선택한다. `object_ids`는 `ids`에서만 1..4096개를 받는다. 그룹이나 블록 내부로 자동 확장하지 않는다.

`result_mode="summary"`는 필터된 집합에서 실제 객체가 있는 레이어·객체 유형·형상 종류별 개수와 가시 수만 반환한다. `objects`(기본값)는 개별 객체를 반환한다. 필요한 정보가 정해져 있으면 `fields`로 골라 받는다. `fields=["id"]`는 별도의 `include_ids` 설정 없이 GUID만 반환하며, `id`, `name`, `layer_path`, `object_type`, `geometry_kind`, `geometry_crc`, `visible`, `selected`, `hidden`, `locked`, `bounds`, `groups`, `user_dictionary`를 조합할 수 있다. 생략하면 기존 기본 정보를 반환하고 GUID는 `include_ids=true`일 때 포함한다. 요약·필드 선택·면 페이지와 유형 필터는 Bridge `object_observation>=2`가 필요하다.

`filters` 조건은 AND로 결합한다. `layer_paths`는 전체 레이어 경로 1..64개의 정확한 일치, `object_types`는 조회된 `object_type` 이름 1..32개, `name_contains`는 이름 부분 문자열이며 대소문자를 구분하지 않는다. `user_dictionary`는 `{source: "attributes" 또는 "geometry", key: 키, any_of: [값들]}` 조건 배열이다. scalar 또는 배열의 원소와 정확히 비교하며 문자열을 임의로 분할하거나 층 정보를 추론하지 않는다. 메타데이터 필터를 건축 요소의 정체성과 동일시하지 않는다.

기본 객체 응답은 문서 가시성·선택 여부·bbox·원본 `geometry_crc`·두 UserDictionary·그룹을 포함한다. 그룹의 `members_outside_match_count`와 문서의 `visible_outside_match_count`는 조회 범위 밖의 관계를 드러낸다. `visible`은 Rhino의 문서/레이어 가시성으로, 화면의 픽셀·가림·clipping 결과를 보증하지 않는다.

`include_geometry=true`면 Brep의 유효성·solid·manifold·체적과 면 정보를 추가한다. 기하 정보도 `fields`의 `geometry_valid`, `solid`, `manifold`, `volume`, `face_count`, `faces`로 선택할 수 있으며 명시한 fields가 우선한다. `faces`에는 원본 ID·CRC와 `face_page`를 함께 반환한다. `face_limit`은 1..128, `face_offset`은 면 시작 위치다. 다음 면 페이지는 `scope="ids"`, 대상 ID들과 이전 `geometry_crc`를 담은 `expected_geometry_crcs={GUID: CRC}`로 요청하며 형상이 바뀌면 거절한다. 면의 `face_edit_supported`는 사전 판별이며 실제 편집 성공 보장은 아니다.

바깥 `offset`/`limit`(1..200), `next_offset`, `complete`는 객체 또는 요약행의 페이지이고, 각 객체의 `face_page`는 그 객체의 면 페이지다. 응답은 256 KiB, 문서 스캔은 100000개로 제한하며 초과하면 범위·필드·페이지 크기를 줄여 조회한다. 가시 범위와 그룹의 범위 밖 관계는 실제로 반환된 필드에 근거해 읽는다.

<!-- /instruction:get_rhino_objects -->

<!-- instruction:get_object_intersections -->

명시 GUID 1..512개의 닫힌 Brep·Extrusion·방향이 정해진 manifold Mesh의 체적 교차를 읽기 전용으로 검사한다. Component 등록은 필요 없다. `max_pairs`(1..64)는 한 페이지의 후보쌍 계산 수다. `include_blocks=true`면 중첩 블록의 배치 변환을 적용한 구성원도 검사하며 정의는 수정하지 않는다. Disjoint Mesh는 문서에서 분해·재결합할 필요가 없다. Brep/Mesh 혼합 쌍은 임시 메싱에 의한 근사임을 결과에 표시한다.

`next_cursor`를 같은 대상과 함께 전달하면 나머지 후보를 이어 검사한다. 형상·범위가 바뀌면 cursor가 거절된다. 페이지 결과를 합쳐 읽고, `pagination_complete`는 후보 열거의 끝, `complete`는 이번 응답만으로 전체 범위가 확인됐는지를 뜻한다. 미지원·판정 불명·미검사는 무교차가 아니다. 각 쌍의 `a.handle`, `b.handle`, `pair_state`는 ID 표시 옵션과 무관하게 반환되며 `show_object_intersection`·`resolve_object_intersection`의 입력으로 쓴다. 그룹은 대상을 자동 추가하지 않는다.

<!-- /instruction:get_object_intersections -->

<!-- instruction:capture_rhino_inspection -->

지정한 여러 시점과 객체집합을 하나의 PNG에 담는 읽기 전용 캡처다. `views`는 1..16개 tile로, 각 항목은 `object_ids`(생략하면 현재 문서 가시 범위), `direction`, `display_mode`, `label`을 받는다. 필요하면 `get_rhino_objects`의 필터 결과 GUID를 tile마다 전달한다. 현재 선택·카메라·숨김 상태를 바꾸지 않는다.

`direction`은 `current`, `top`, `bottom`, `front`, `back`, `left`, `right`, `iso_ne`, `iso_nw`, `iso_se`, `iso_sw`, `below_ne`, `below_nw`, `below_se`, `below_sw` 중 선택한다. 필요한 시점만 요청한다. `display_mode` 생략 시 현재 모드를 쓰며, 이름이 중복되면 `get_rhino_context(sections=["display_modes"])`에서 확인한 GUID를 사용한다. 각 tile의 메타데이터와 오류를 읽고 이미지의 실제 범위를 확인한다.

`width`/`height`는 tile 픽셀 크기, `columns`는 배치 열 수다. 합계 16M 픽셀과 PNG 4 MiB를 넘으면 크기나 tile 수를 줄인다. 문서 가시성 기준의 대상 목록은 픽셀에 실제 보이는 모든 객체의 증명이 아니다. 명시 필터에서 블록 인스턴스·블록 내부 객체는 지원하지 않으며 해당 tile 오류로 보고한다. 필터를 생략한 전체 범위에서는 블록을 원래대로 표시한다.

<!-- /instruction:capture_rhino_inspection -->
