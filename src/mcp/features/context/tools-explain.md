# tools.py explain

## get_retrieval_status

<!-- instruction:get_retrieval_status -->
Returns compact diagnostics for the local structured retrieval system.
This is an intrinsically bounded diagnostic: fixed scalar counts/status and configured index names, not asset records.
IDs and GUIDs are omitted by default. Set include_ids=true when needed; supplied target IDs are not repeated.
<!-- /instruction:get_retrieval_status -->

## get_rhino_context

<!-- instruction:get_rhino_context -->
Read selected LIVE Rhino context on the UI thread. sections accepts document,
selection, viewport, editor and display_modes; default is ["document"]. Unrequested sections are not collected.
Document/selection/viewport responses also contain compact editor mode/target/stable
so isolation is immediately visible. Request editor for provider evidence and warnings;
sections=[] skips editor observation for capability-only calls.
editor reports mode (model/group/block/unknown), the known target and stable. Only a
verified normal model is stable; active isolation, transitions and unsupported editor
versions are unstable. Unknown target identity remains null, never inferred from selection.
display_modes lists at most 128 installed mode names/GUIDs. Shaded, Dark and CadWhite
are choices only if actually installed; do not invent aliases for custom modes.

Includes document identity/path, units/tolerances, object/layer counts, a bounded
selection summary and camera/display metadata. This query does not create layers,
geometry, dimensions or an Undo record. Unavailable values are null with warnings.
Counts and the current view are context, not a geometric or visibility validation.
Request only the context needed for the task. project_info already verifies the live
document; do not repeat this call merely to check whether that document is live.

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

Requests and responses are bounded to 256 KiB of UTF-8 JSON. Unknown, unsupported
and truncated observations remain unverified. Requires Bridge block_analysis=1.

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

Omit view to capture the current view. Pass view="a" to list viewports, named_views,
and layouts, with only name and guid for each entry. Then pass the desired GUID as view.
Names need not be unique. Named Views render the saved camera off screen using
Shaded by default; they never replace the visible viewport. Layouts capture the
paper area, including its details, not the surrounding workspace. A current Layout
also captures its paper, even when a detail is active.

scale_percent=100 means the original pixel dimensions; 75 (default) retains 75% of both
dimensions and uses 56.25% of the pixels. Named Views use their saved
pixel size (current viewport size if unavailable); Layout 100% means paper at 96 dpi.
No temporary image file is created. Capture does not change camera, selection or
Undo state, or prove geometric correctness. A failed or oversized image is an error;
lower scale_percent explicitly instead of receiving a silently resized image.

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

읽기 전용으로 일반 모델 객체의 범위·속성·그룹·형상을 조회한다. `scope`는 현재 문서 가시 객체 `visible`(기본값), `selected`, 명시 GUID `ids`, 숨긴 객체를 포함한 `document` 중 선택한다. `object_ids`는 `ids`에서만 1..4096개를 받는다. 그룹이나 블록 내부로 자동 확장하지 않는다. `include_ids=true`면 후속 작업에 쓸 GUID도 반환한다.

`filters` 조건은 AND로 결합한다. `layer_paths`는 전체 레이어 경로 1..64개의 정확한 일치(대소문자 무시), `name_contains`는 이름 부분 문자열(대소문자 무시)이다. `user_dictionary`는 `{source: "attributes" 또는 "geometry", key: 키, any_of: [값들]}` 조건 배열이다. scalar 또는 배열의 원소와 정확히 비교하며 문자열을 임의로 분할하거나 층 정보를 추론하지 않는다. 메타데이터 필터를 건축 요소의 정체성과 동일시하지 않는다.

각 객체에 문서 가시성·선택 여부·bbox·원본 `geometry_crc`·두 UserDictionary·그룹을 반환한다. 그룹의 `members_outside_match_count`와 문서의 `visible_outside_match_count`는 조회 범위 밖의 관계를 드러낸다. `visible`은 Rhino의 문서/레이어 가시성으로, 화면의 픽셀·가림·clipping 결과를 보증하지 않는다.

`include_geometry=true`면 Brep의 유효성·solid·manifold·체적과 최대 128개 면의 index·평면·방향을 추가한다. 면 편집에는 같은 응답의 원본 CRC를 쓴다. `face_edit_supported`는 형상 종류와 기본 조건의 사전 판별이며 실제 편집 성공 보장은 아니다. `offset`/`limit`(1..200), `next_offset`, 각 `truncated` 표시를 확인한다. 응답은 256 KiB, 문서 스캔은 100000개로 제한하며 초과하면 범위를 줄여 조회한다.

<!-- /instruction:get_rhino_objects -->

<!-- instruction:get_object_intersections -->

일반 모델 객체의 명시 GUID 1..512개에 대해 닫힌 Brep/Extrusion의 체적 교차를 읽기 전용으로 검사한다. Component 등록은 필요 없다. `max_pairs`(1..64)는 bbox 후보 중 실제 기하 커널에 전달할 쌍 수다. `include_ids=true`면 원인 객체와 쌍의 GUID를 반환한다.

`complete`, `truncated`, `unsupported_objects`, `unknown_pair_count`를 함께 읽는다. `has_positive_overlap=false`는 전체 대상 검사가 끝나고 양의 체적 교차가 없을 때만 반환하며, 불완전한 무교차 결과는 null이다. 체적 교차가 없다는 결과는 접합·연속성·설계 적합성 판단을 대신하지 않는다. 블록은 펼치지 않고 그룹은 대상에 추가하지 않는다.

<!-- /instruction:get_object_intersections -->

<!-- instruction:capture_rhino_inspection -->

지정한 여러 시점과 객체집합을 하나의 PNG에 담는 읽기 전용 캡처다. `views`는 1..16개 tile로, 각 항목은 `object_ids`(생략하면 현재 문서 가시 범위), `direction`, `display_mode`, `label`을 받는다. 필요하면 `get_rhino_objects`의 필터 결과 GUID를 tile마다 전달한다. 현재 선택·카메라·숨김 상태를 바꾸지 않는다.

`direction`은 `current`, `top`, `bottom`, `front`, `back`, `left`, `right`, `iso_ne`, `iso_nw`, `iso_se`, `iso_sw`, `below_ne`, `below_nw`, `below_se`, `below_sw` 중 선택한다. 필요한 시점만 요청한다. `display_mode` 생략 시 현재 모드를 쓰며, 이름이 중복되면 `get_rhino_context(sections=["display_modes"])`에서 확인한 GUID를 사용한다. 각 tile의 메타데이터와 오류를 읽고 이미지의 실제 범위를 확인한다.

`width`/`height`는 tile 픽셀 크기, `columns`는 배치 열 수다. 합계 16M 픽셀과 PNG 4 MiB를 넘으면 크기나 tile 수를 줄인다. 문서 가시성 기준의 대상 목록은 픽셀에 실제 보이는 모든 객체의 증명이 아니다. 명시 필터에서 블록 인스턴스·블록 내부 객체는 지원하지 않으며 해당 tile 오류로 보고한다. 필터를 생략한 전체 범위에서는 블록을 원래대로 표시한다.

<!-- /instruction:capture_rhino_inspection -->
