# 기존 5개 Plan 템플릿의 정책 검토

Plan·도구 기준은 `codex/almond-global-policy` 작업의 시작점 `73fb972`에서 읽고 현재 공개 계약과 대조했다. [BASIC의 Plan 흐름](../../../BASIC-INSTRUCTIONS.md#plan-흐름과-판단의-연결)과 새 활동별 정책을 가상의 사용자 상황에 적용했다. 각 시나리오의 Given은 검토용 전제다. 실제 Rhino 호출과 LLM 행위 측정은 수행하지 않았다.

## 모든 Step의 공통 계약

- [`planning/store.py:434–475`](../../../features/planning/store.py#L434)의 5개 템플릿은 총 32 Step이다. 아래 표의 각 행은 바로 앞 행을 선행 Step으로 지정한다. `planning_scopes.template_scope`에 따라 선택된 템플릿을 읽으므로 같은 이름의 기존 사용자 매핑·기존 Plan의 실제 순서는 `plan_05-get` tool의 `request.include_details=true` 또는 `plan_08-list` tool의 `request.target="step"`으로 확인한다.
- [`planning/requests.py:24–35`](../../../features/planning/requests.py#L24)의 `plan_02-create` tool은 `request.target="plan"`, `title`, `goal`, `scope`를 받고 `scope`를 생략하면 `house`다. Phase·Scene·Holon 등록은 맥락과 대상의 근거다. `inspect_05-resolve_targets` tool 응답의 등록 대상은 `holon_ids`로 반환된다. [`planning/store.py:754–780`](../../../features/planning/store.py#L754)의 `inspect_05-resolve_targets` tool은 Plan Holon 대상만 해석하고 선택적 `step_id`는 소속 확인에 쓴다. 반환된 `live_verified=false`와 Scene 문맥만으로 실제 변경 대상을 확정할 수 없다.
- [`runtime/workspace.py:99–117`](../../../runtime/workspace.py#L99)의 `plan_03-execute_looping` tool은 `plan_id, resume, feedback, artifact_name`을 받아 현재 Plan·Loop·revision·Step 기록·이전 Loop·산출물 경로를 반환한다. `next_step_id`는 순서상 처음으로 `completed`가 아닌 Step을 가리킨다. `failed`, `blocked`, `paused`도 포함한다. `resume=true`는 최신 Loop와 상태를 유지한다. 새 Loop는 이전 이력을 보존하며 같은 Step UUID의 상태·입출력을 초기화한다. 기본 순서, 기존 결과 확인 후 재사용, 현재 Loop 경로 사용, 사용자 Plan 완료는 [`runtime/workspace-explain.md`](../../../runtime/workspace-explain.md#L3)의 `policy_reminder`가 이미 다룬다.
- [`tool_guidance.py:6–53, 71–146`](../../../tool_guidance.py#L6)의 실제 가이드는 Loop·작업 선택 응답으로부터 `plan_10-set_working` tool, 재사용 근거 `input_refs.add`, 새 근거 `output_refs.add`, 같은 `loop_no`, 선택적 `expected_revision`을 이어 준다. [`planning/output.py:30–66`](../../../features/planning/output.py#L30)의 `plan_12-update` tool 응답은 적용 여부·부분 실패·새 revision·Step 상태다. [`planning/store.py:710–750`](../../../features/planning/store.py#L710)의 Step 갱신은 존재·현재 Loop·revision·값을 검사하지만 선행 의존 근거나 사용자 승인 여부를 검사하지 않는다. [`planning/requests.py`](../../../features/planning/requests.py)의 Plan 완료 입력에는 사용자 결정이 명시되어 있다. 선택, 저장 성공, 업무의 수행, 기술적 검수, 사용자의 Plan 완료 결정은 각각 따로 판단한다.
- [`BASIC-INSTRUCTIONS.md`](../../../BASIC-INSTRUCTIONS.md)의 모델링·Drafting은 현황·주변·사용·구축 관찰, 화면과 형상·치수 대조, 영향 범위 검수, 사실·해석·미확인 분리를 이미 요구한다. 아래 도구는 각 Step에 실제로 사용할 수 있는 선택지를 매핑했다. 근거 검토는 `reason` Step의 도구 호출 자체가 목표가 아니며, 다른 종류의 Step도 요청과 선행 결과에 따라 적합한 도구를 선택한다. 초기 연결, 정책·프로젝트 조회로 필요한 맥락을 확보한 후 목적에 맞는 Plan의 실제 Step 순서를 따라 수행한다. 활동 정책 조회는 현재 Step에 필요한 판단 기준을 가져오며 현재 과업과 별개의 Plan 생성을 요구하지 않는다. `inspect_02-get_objects` tool로 저장 문서의 명시적 객체를 읽을 때는 `scope="document"`와 `object_ids`를 전달한다. `fields`에서 필요한 `id`, `bounds`, `geometry_crc`, `faces` 등을 선택한다. 캡처 가이드는 보관된 `image_file.path`가 있는 경우에만 그 경로를 기록으로 연결한다. 도구별 입력과 출력·가이드의 문서 예시는 [`tool_description_spec.md`](../../../../../tool_description_spec.md), 출력 스키마는 [`output_contracts.py`](../../../output_contracts.py)에서 확인했다. 가이드가 언급되지 않은 칸은 출력의 근거로 다음 판단을 연결했다.

## house:

[템플릿 정의](../../../features/planning/store.py#L456) · [구법](../../../features/guidance/tools-explain.md) · [구조](../../../features/structure/tools-explain.md) · [Grasshopper](../../../features/grasshopper/tools-explain.md) · [자산](../../../features/assets/tools-explain.md) · [겹침·Holon](../../../features/components/tools-explain.md) · [피난](../../../features/egress/tools-explain.md)

| 순서·Step | 필요한 입력과 활용할 도구 | 얻는 근거와 다음 판단 | 정책 |
|---|---|---|---|
| 1. `programme` (reason) | `context_04-get_project_info` tool의 `sections=["project","document"]`, 해당 Phase/Plan 상세, 사용자 목표, 기존 공간과 보존 조건. 필요한 현황은 `inspect_02-get_objects` tool의 범위·ID·치수 필드와 캡처로 확인. | 문서·단위·기존 파일을 확인하고 배치할 용도·사용자·동선·경간의 요구를 정한다. 프로젝트 응답은 Plan 목록·작업 경로·객체 조회를 안내한다. 모델에서 읽은 용도와 사용자가 정한 요구를 분리한다. | BASIC Plan 흐름, [OB1] |
| 2. `retrieve_structural_logic` (retrieve) | `research_01-get_construction_guidance` tool에 `category, material, structure_type, span_m`, 초기 깊이·구축 참고를 받을 `field_groups=["rules"]`, 필요 시 `include_reference_data`를 사용한다. `grasshopper_01-get_logic` tool에 `logic_id` 또는 `grasshopper_02-list_capsules` tool에서 ID·포트·실행 감사 확인. | `systems[].fits_span`, 초기 깊이·구축 참고, 캡슐 입력 타입·단위·`audited`. 구법 가이드는 선택한 구법의 기록, 캡슐 가이드는 계약·감사를 확인한 실행을 안내한다. 경간 적합은 실제 하중·접합 승인이나 실행 권한을 뜻하지 않는 예비 근거다. | [SM3], [OB1] |
| 3. `generate_structure` (execute) | 합의하거나 위임된 구조 방향과 해석에 필요한 축선·지점 요구. `script_02-run_rhino` tool의 `script`에 대상·변경·반환 근거를 명시한다. 실행 감사와 생성 계약을 모두 갖춘 캡슐이 실제로 있는 경우 `grasshopper_04-run_definition` tool의 `capsule_id, inputs`를 사용할 수 있다. 저장소의 기존 감사 캡슐은 해석용이다. | RhinoCode의 `request_id, completed, result`를 확인하고 시간 초과 시 같은 실행을 조회한다. 캡슐의 베이크는 정의가 결정하며 `baked_guids`가 반환된 경우 가이드는 형상 재관찰을 안내한다. 현재 객체와 구조 모델에 필요한 연결·지점을 확인해 다음 Step의 입력으로 쓴다. | [SM3], [OB1] |
| 4. `validate_structure` (validate) | `analysis_03-list_design_codes` tool에서 기준 ID와 출처를 확인하고, `analysis_04-validate_structure` tool에 현재 `guids`와 과업에 맞는 `structure_type`, `material`, `fixed_supports`, `connections`, `load_kn`, `uls_combination`, `design_code` 등을 적용. | `status`의 `pass/fail/indicative`, `passed`, `results.analysis_method`, `warnings`, `assumptions`, `design_code.unverified`, `worst_member_guids`. 가이드는 필요 시 구조 오버레이 확인. 유효한 해석 범위와 조건을 근거로 공간 작업을 이어간다. 실패·적용 불명확 결과는 구조 가정이나 생성 Step으로 돌아가는 근거다. | [OB1], [OB2] |
| 5. `define_rooms` (execute) | 프로그램과 확인된 구조·채광·접근 조건에서 벽·문·영역 형상을 정한다. 지원되는 기존 Brep 편집은 `model_02-edit_planar_face` tool에 동일 관찰에서 얻은 `object_id`, `face_index`, `expected_geometry_crc`와 `translation`, 전용 범위 밖은 `script_02-run_rhino` tool. | 변경 ID·CRC 또는 실행 결과를 현재 문서에서 확인한다. 면 편집의 `result.object_id`와 `result.geometry_crc`를 사용하며 가이드는 바뀐 형상·CRC 재관찰을 안내한다. 공간에 실제 배치가 가능한 경계와 개구·유효 치수를 자산 검색의 입력으로 전달한다. | [SM1], [SM2] |
| 6. `retrieve_assets` (retrieve) | `asset_11-search` tool에 `category`, `query`, `max_width_mm`, `max_depth_mm`, `max_height_mm` 중 필요한 필터와 `include_ids=true`를 넣고 `asset_04-get` tool에서 자산 ID·치수·모델 준비 상태 조회. | 치수·준비 상태와 사용 가능한 ID. 가이드는 선택 자산 상세 및 준비된 ID로 배치하는 흐름을 제시한다. 검색 크기는 전체 사용 여유·작동 공간을 대신하지 않는다. 적합한 자산이 없으면 공간 의도와 보존 조건을 유지한 대안을 판단한다. | [SM3], [OB1] |
| 7. `place_assets` (execute) | `asset_06-place` tool에 실제 선택한 `asset_id`, 문서 단위 `x`, `y`, `z`, `rotation_degrees`, `scale`. 필요한 경우 공유 정의 변경 가능성과 기존 배치 영향을 확인한다. | `object_guid`, `definition_created`, 해당 시 `definition_refreshed`와 `affected_existing_instances`. 가이드는 객체 관찰과 캡처로 위치·축척 재확인. 배치 성공 뒤 남는 문 작동·동선·사용 관계를 `validate_layout`에서 판단한다. | [SM3], [OB1] |
| 8. `validate_layout` (validate) | `inspect_02-get_objects` tool에 실제 ID·범위와 치수·유효성 필드, `capture_02-inspection` tool에 전체·문·가구 사용 시점, `intersect_01-find` tool에 검사 범위의 `object_ids`와 `include_block`. 피난 검토가 요청 범위이면 실제 측정 근거로 `analysis_01-check_egress` tool의 `plate_bounds_mm`, `exits`, `travel_distances_m` 등을 구성한다. | 이미지·실제 치수, `intersections.number` 또는 `error_code="intersection_count_incomplete"`, 피난의 `checks`와 `warnings`. 겹침 0 가이드는 검사 범위에서 트림 불필요만 의미한다. 피난 가이드는 미달 항목 수정과 갱신한 측정으로 재검토를 안내한다. | [OB1], [OB2] |
| 9. `resolve_collisions` (resolve) | 양의 체적 겹침이 있고 변경이 적합할 때 `intersect_02-resolve` tool에 앞 검사와 같은 `object_ids`, `include_block`으로 리뷰를 시작하고 이미지·`objects[].number`·`review_id`를 대조한다. 선택된 배치 수정은 해당 편집 도구로 한다. | `state="awaiting_choice"`에서 반환하는 이미지와 `objects[].number`를 `review_id`와 대조해 `choice`에 `1`, `2` 또는 `"skip"`을 넘긴다. 블록 구성원의 자동 차집합은 지원하지 않으므로 skip하거나 맡긴 범위의 명시적 블록 편집을 검토한다. `state=completed`의 `skipped_pairs`는 미수정이다. 구조·공간에 영향을 주면 승인 범위에 맞춰 보존/조정하고 관련 검수를 다시 수행한다. | [SM1], [SM2], [FR2] |
| 10. `final_validation` (validate) | 수정 후 실제 문서에서 초기 요구·경계·사용·보존 조건을 재관찰한다. 구조와 하중에 영향을 줬으면 동일 비교 조건과 현재 ID로 구조 재검토, 배치 영향은 다시 관찰·치수 확인. | 현재 모델 근거, 남은 문제, 조건부 판단을 묶어 보고한다. 현재 Step 근거를 기록한다. Plan `completed`는 사용자의 완료 결정 후 별도로 기록한다. | [SM2], [OB3], [FR3] |

### BDD

- **정상** · Given 사용자가 주거의 공간·구조 범위와 보존 대상을 정했다. When `research_01-get_construction_guidance` tool이 `systems[].fits_span=true`인 후보를 제시하고, 구조 축선·지점을 만든 `script_02-run_rhino` tool의 실행이 `completed=true`로 확인되며, 현재 모델을 조회해 얻은 GUID로 `analysis_04-validate_structure` tool이 `status="pass"`를 반환한다. 이어서 배치 객체의 문 작동 여유를 확인하고 `intersect_01-find` tool이 `intersections.number=0`을 반환한다. Then 현재 해석과 공간 확인의 범위를 기록하고 검사한 범위의 trim을 건너뛴다. 목표 달성 근거를 보고한 뒤 사용자의 완료 결정에 따라 Plan 상태를 갱신한다. **기존 판단의 공백** · 구법 후보와 실행 완료를 방을 확정하는 근거로 사용하거나, 겹침 0을 공간 전체 검수로 사용할 수 있었다. **적용** · BASIC Plan 흐름 → [SM3] 구법 후보와 실제 설치 조건 → [OB1], [OB2] 현재 구조·배치·문 개폐의 서로 다른 판정 → [FR3], [FR2] 사용자 결과 확인. **결과** · 정적 walkthrough 통과; Rhino/LLM 행위효과 검증 아님.
- **실패** · Given `analysis_04-validate_structure` tool이 `status="indicative", passed=null`과 구조 가정·경고를 반환했다. When `validate_structure` 다음에 구조에 의존하는 방 경계를 확정할지 판단한다. Then 현재 축선·지점·하중과 설정을 대조하고 필요한 구조 근거부터 다시 확인한다. 구조 전제와 독립적인 프로그램 확인은 계속한다. **기존 판단의 공백** · 도구는 해석 신뢰도를 밝히지만, 뒤의 방 구성에 무엇을 보류할지는 정하지 않는다. **적용** · BASIC Plan 흐름과 [OB1], [OB2]로 해당 결과가 지지하는 결론을 판단하고 [FR2]에 따라 영향받는 결정만 유보한다. **결과** · 정적 walkthrough 통과; Rhino/LLM 행위효과 검증 아님.
- **피드백** · Given 첫 Loop 구조 판정과 배치 근거가 저장되어 있다. When 사용자가 중량 자산 추가와 지지 벽 위치 변경을 결정한다. Then 같은 Plan의 재검토에서 프로그램·구조 전제부터 영향 범위를 확인한다. 이전 근거 중 바뀌지 않은 관계를 재사용하고, 새 지지·하중 조합과 변경된 벽 주변 동선을 다시 검수한다. **기존 판단의 공백** · 새 Loop와 과거 기록의 기술 계약은 있지만 이전 구조 판정이 이번 자산·벽 변경에도 유효한지는 판단하지 않는다. **적용** · BASIC Plan 흐름과 [DE3]으로 바뀐 요구를 앞선 판단에 연결하고 [SM2], [OB3]으로 영향받은 증거를 갱신한다. [FR2]로 새 결정의 범위를 연결한다. **결과** · 정적 walkthrough 통과; Rhino/LLM 행위효과 검증 아님.

## interior:

[템플릿 정의](../../../features/planning/store.py#L468) · [관찰과 뷰](../../../features/context/tools-explain.md) · [자산](../../../features/assets/tools-explain.md) · [겹침](../../../features/components/tools-explain.md)

| 순서·Step | 필요한 입력과 활용할 도구 | 얻는 근거와 다음 판단 | 정책 |
|---|---|---|---|
| 1. `inspect_rooms` (reason) | 해당 저장 문서의 경로·단위, 사용자 지정 방·보존 범위. `inspect_02-get_objects` tool의 현황·경계·치수와 `capture_04-defined_view` tool의 평면/단면 또는 `capture_02-inspection` tool의 주변 맥락을 대조. | 현재 가구·벽·문과 사용 공간을 파악한다. 객체 가이드의 동일 스냅샷 페이지와 캡처의 실제 이미지 범위를 확인한다. 검색할 크기와 작동 여유의 조건을 분리해 기록한다. | [OB1] |
| 2. `retrieve_assets` (retrieve) | `asset_11-search` tool에 실제 사용 요구와 mm 치수, `include_ids=true`. `asset_04-get` tool로 자세한 치수와 준비 상태 확인. | 준비된 선택 ID와 치수·표현 수준을 후보로 전달한다. `source_only`면 3DM 준비·등록이 배치의 기술 선행조건이다. 배치만 요청했으면 준비·등록의 범위 및 소요를 따로 판단한다. | [SM3] |
| 3. `place_assets` (execute) | `asset_06-place` tool의 `asset_id`, `x`, `y`, `z`, `rotation_degrees`, `scale`에 준비된 ID와 배치 값을 입력. 공유 정의/기존 인스턴스를 보존해야 하면 상태를 먼저 파악. | `object_guid`와 정의 영향이 주는 실제 검사 대상. 가이드는 객체·캡처로 위치와 축척을 확인한다. 시간 초과 `requires_reconciliation`이면 실제 인스턴스부터 읽는다. | [SM3], [OB1] |
| 4. `validate_layout` (validate) | 가구와 문·벽·경로가 함께 드러나는 캡처와 `inspect_02-get_objects` tool의 실제 치수. `intersect_01-find` tool의 현행 대상 범위, 블록 포함 여부를 명시. | 검색 적합·배치 응답과 다른 독립 근거인 작동 여유·사용 가능성·겹침. `intersection_count_incomplete`와 제외한 블록을 0개 결과와 구별한다. | [OB1], [OB2] |
| 5. `resolve_collisions` (resolve) | `intersect_02-resolve` tool에 앞 검사와 같은 `object_ids`, `include_block`을 넣어 시작한다. 반환 이미지·`objects[].number`로 판단한 뒤 후속 호출에 같은 `review_id`와 `choice=1/2/"skip"`만 보낸다. 잘라내기보다 이동·재선택이 적합하면 배치 원인 단계로 돌아간다. | 선택 상태, 수정 여부, 건너뛴 쌍. 블록 구성원의 자동 차집합은 지원하지 않으므로 skip하거나 맡긴 범위의 명시적 블록 편집을 검토한다. 도구가 안내하는 트림 외에도 공간·제품 의도와 보존 조건에 맞는 해결을 판단한다. | [SM1], [SM2] |
| 6. `final_validation` (validate) | 현재 가구·벽·문의 형상과 주요 동선·사용 시점을 재관찰. 바뀐 공유 정의가 있으면 영향받는 기존 배치도 확인. | 수정된 배치가 실제로 사용 가능하고 기존 설계가 보존됐는지 근거와 미확인을 보고한다. 사용자가 정한 결과 범위와 Plan 완료 결정을 확인한다. | [SM2], [OB3], [FR3] |

### BDD

- **정상** · Given 사용자가 벽·문을 보존하고 가구만 배치하라고 했다. When 검색에서 준비된 자산 ID를 얻어 `asset_06-place` tool에 넣고, 반환된 `object_guid`로 위치·치수를 확인하며 캡처와 실측에서 문 작동과 동선이 성립한다. Then 가구의 위치와 축척, 문 작동의 증거와 보존 범위를 보고하고 사용자 완료 결정을 적용한다. **기존 판단의 공백** · 배치 가이드가 위치·축척을 재확인하도록 안내하지만 문 작동과 보존 범위까지 완료 기준으로 연결하지는 않는다. **적용** · BASIC Plan 흐름 → [SM1], [SM3] 보존 대상과 배치 범위 → [OB1] 작동 근거 → [FR3] 결과 전달. **결과** · 정적 walkthrough 통과; Rhino/LLM 행위효과 검증 아님.
- **실패** · Given 가구 배치가 `requires_reconciliation=true`로 돌아왔다. When 현재 인스턴스 조회에서 배치가 이미 있음을 확인한 뒤 `intersect_01-find` tool을 기본 `include_block=false`로 실행해 `intersections.number=0`을 얻었지만 주요 가구는 블록이다. Then 같은 가구를 다시 배치하지 않고 그 배치의 현재 ID로 검수를 이어간다. 필요한 블록을 포함해 겹침과 문 작동 여유를 확인하고, 실제 간섭이 발견되면 가구 이동과 벽·문 보존을 기준으로 해결한다. **기존 판단의 공백** · 타임아웃 회수와 0개 결과의 범위는 도구가 명시한다. 이후 필요한 공간 검수의 범위와 수정할 부재는 에이전트가 결정한다. **적용** · [OB2] 검사 제외 범위 → [OB1] 현재 인스턴스와 문 작동 → [SM1], [SM2] 작업 범위와 해결 후 재검수. **결과** · 정적 walkthrough 통과; Rhino/LLM 행위효과 검증 아님.
- **피드백** · Given 가구와 벽의 겹침이 없다는 기록이 남아 있다. When 사용자가 휠체어 통과와 열린 문 상태의 유효 여유를 새로 요청한다. Then 검색 치수·실제 이동 경로·문 작동 범위를 새 요구에 대조해 영향받는 배치와 검수부터 다시 수행한다. 새 기준을 아직 확인하지 못했으면 통과 여부를 미확인으로 보고한다. **기존 판단의 공백** · 저장된 겹침 없음과 변경된 사용 요구 사이의 판정은 어떤 도구 결과에도 들어 있지 않다. **적용** · [DE3] 질문의 조건 변경 → [OB1], [OB2] 근거·적용 기준 → [SM2], [OB3] 영향 Step의 검사 갱신. **결과** · 정적 walkthrough 통과; Rhino/LLM 행위효과 검증 아님.

## structure:

[템플릿 정의](../../../features/planning/store.py#L434) · [검증 DESCRIPTION과 입력](../../../features/structure/tools-explain.md#L3) · [구조 검증 출력](../../../../../tool_description_spec.md#L7461) · [실제 판정 정규화](../../../features/structure/tools.py#L446) · [구법 가이드](../../../features/guidance/tools-explain.md#L10)

| 순서·Step | 필요한 입력과 활용할 도구 | 얻는 근거와 다음 판단 | 정책 |
|---|---|---|---|
| 1. `inspect_existing_structure` (reason) | `context_04-get_project_info` tool로 문서·단위, `inspect_02-get_objects` tool에 구조 객체의 ID·경계·기하와 필요한 범위, `capture_02-inspection` tool에 전체/접합/지점 시점. | 현재 구조와 숨김/잠김을 포함할 범위를 파악하고, 보이는 부재·지지와 가정해야 할 접합·하중 경로를 구분한다. 객체 가이드는 스냅샷 페이지 연결, 캡처 가이드는 증거 기록을 지원한다. | [OB1] |
| 2. `programme` (reason) | 기존 구조 근거, 변경 목적과 사용 하중, 보존 부재·공간·외피의 요구, 설계 단계와 검토 기준. 기준 후보는 `analysis_03-list_design_codes` tool의 `include_ids=true, field_groups=["parameters","source"]`. | 후보 기준·수치·출처, 선택 기준을 검토에 사용하는 가이드. 프로그램의 보존 조건·검토 가정을 정하고 불명확한 실제 지점·하중은 가정으로 기록한다. | [OB1], [FR1] |
| 3. `retrieve_structural_logic` (retrieve) | `research_01-get_construction_guidance` tool의 구조 유형·재료·경간 필터와 상세/출처. 사용하는 경우 `grasshopper_01-get_logic` tool 및 `grasshopper_02-list_capsules` tool의 논리·포트·감사. | 예비 시스템·깊이·하중 참고 및 캡슐 계약. `fits_span`과 추천값은 모델 접합·지점·하중의 분석을 대체하지 않는다. 구법 기록/감사 확인 후 실행 안내는 선택 이후의 절차다. | [SM3], [OB1] |
| 4. `analyze_structure` (validate) | `analysis_04-validate_structure` tool에 기존 구조를 관찰한 `guids`, 재료, 지점·접합·안정성, 하중·조합·기준. 필요한 경우 `detail=true`. | `status`, `results.analysis_method`, `confidence`, `warnings`, `assumptions`, `design_code.unverified`, 지배 부재. 필요 시 `analysis_05-visualize_structure` tool을 사용하되 `reanalyze=false`인 재표시는 새로운 해석 근거가 아니다. | [OB1], [OB2] |
| 5. `develop_structure_or_improvements` (reason) | 분석이 가리키는 지배 부재·가정, 요구와 주변 사용 공간. 필요 시 구조 오버레이·다시 조회한 형상과 단면 정보를 비교. | 계산이 제시한 문제 원인 후보와 실제 모델 조건을 대조한다. 개선안의 비교는 동일하거나 달라진 조건을 밝히고 영향(보 깊이·접합·공간)을 설명한다. 기술적으로 가능한 개선과 사용자가 선택한 변경을 기록한다. | [DE1], [DE2], [FR2] |
| 6. `apply_structure_changes` (execute) | 정한 변경, 최신 부재 ID·CRC·실제 접합 영향. 지원 범위는 `model_02-edit_planar_face` 또는 `model_03-edit_planar_faces` tool, 전용 기능이 없으면 `script_02-run_rhino` tool. | 면 편집 후 바뀐 형상·CRC 재관찰 가이드. 단일 수정은 `result.object_id`와 `result.geometry_crc`, 배치는 `result.items`를 확인한다. 범용 실행은 완료/결과를 확인하고 시간 초과 시 같은 `request_id`를 조회. 변경 ID·형상과 인접 지지를 다시 확인해 재해석에 전달한다. | [SM3], [OB1] |
| 7. `validate_structure` (validate) | 새 모델의 현행 `guids`와 기준 모델의 가정. `analysis_04-validate_structure` tool을 새로 실행하고 필요 시 `analysis_02-export_structural_report` tool에 관리형 상대 `path`와 `limit`. | 변경 후 설정된 검사의 `pass/fail/indicative`. 경고·가정과 비교 가능한 조건을 함께 보고한다. 보고서는 저장 이력을 담으며 최신 모델의 검증·안전 인증·설계 승인을 자동 생성하지 않는다. | [SM2], [OB3], [FR3] |

### BDD

- **정상** · Given 사용자가 처짐을 줄이고 천장고와 기존 지지를 보존하라고 했다. When 초기 해석이 `worst_member_guids`를 제시하고, 선택한 보 단면으로 변경한 모델의 현재 GUID를 같은 하중·지점·기준으로 검토해 `status="pass"`를 얻고, 실제 단면에서 천장고가 확인된다. Then 변경 전후 비교 조건과 천장고 보존의 관찰을 함께 보고한다. **기존 판단의 공백** · 해석과 오버레이가 부재를 지목해도, 목표인 처짐 개선과 공간 보존을 함께 판정할 조건은 정하지 않는다. **적용** · [DE1], [DE2] 비교 항목과 조건 → [SM2], [OB1] 구조와 공간 증거 연결 → [FR3] 검증 범위 보고. **결과** · 정적 walkthrough 통과; Rhino/LLM 행위효과 검증 아님.
- **실패** · Given `analysis_04-validate_structure` tool이 `status="fail"`과 접합/불안정 관련 `warnings`를 냈다. When `analysis_05-visualize_structure` tool을 `reanalyze=false`로 호출한 표시에서 처짐이 작아 보인다. Then 오버레이가 재사용한 계산과 현재 판정의 조건을 대조하고 해당 지점·접합을 다시 관찰한다. 원인을 특정한 뒤 입력을 고치거나 허용된 개선안을 검토한다. **기존 판단의 공백** · 재표시라는 기술적 사실은 DESCRIPTION에 있지만 서로 다른 표현이 충돌할 때 어느 근거를 보완해야 하는지는 명시하지 않는다. **적용** · [OB1], [OB2] 같은 범위·조건인지 확인하고 필요한 근거를 추가 → [FR1] 현장에서 확인할 사항을 먼저 확인. **결과** · 정적 walkthrough 통과; Rhino/LLM 행위효과 검증 아님.
- **피드백** · Given 기존 수정 승인은 한 보에 한정되며 해석에는 `connections="rigid"`를 썼다. When 사용자가 실제 단부가 핀에 가깝다는 자료를 준다. Then 현재 Rhino의 부재와 접합 조건을 대조하고 자료가 변경한 해석 가정을 기록한다. 해당 분석·개선안·검증을 다시 수행하고 실제 접합이나 지점의 형상 변경이 필요하면 기존 작업 범위와 대조한다. **기존 판단의 공백** · 입력의 접합 모드는 자세하지만, 새 자료가 어떤 앞선 판단을 바꾸는지와 기존 승인 범위는 도구에서 판정하지 않는다. **적용** · [DE3], [OB3], [SM2] 분석 조건과 후속 근거 갱신 → [SM3], [FR2] 실제 변경과 승인 범위 판단. **결과** · 정적 walkthrough 통과; Rhino/LLM 행위효과 검증 아님.

## drawing:

[템플릿 정의](../../../features/planning/store.py#L443) · [도면 스타일](../../../features/drawings/tools-explain.md) · [PlanSection](../../../features/modeling/tools-explain.md#L3) · [뷰·Layout](../../../features/context/tools-explain.md#L26) · [실제 결과 검증](../../../features/modeling/plan_section.py#L55)

| 순서·Step | 필요한 입력과 활용할 도구 | 얻는 근거와 다음 판단 | 정책 |
|---|---|---|---|
| 1. `define_drawing_scope` (reason) | 사용자 목적과 전달 형식, 보존할 시트와 비교할 도면, 대상 범위·투영·축척. `drawing_05-list_recipes` tool의 `include_ids=true`, `drawing_02-get_recipe` tool의 ID와 `scales/parameters` 그룹. | 레시피·적용 가능한 축척·표현 규칙과 다음 스타일 적용 안내. 기존 레이아웃 수정과 모델 공간 생성의 대상·산출 목적을 정한다. | [DR1], [FR1] |
| 2. `inspect_existing_drawings` (retrieve) | `inspect_03-get_document_context` tool의 `sections=["named_views","layouts"]`, `capture_04-defined_view` tool의 `target_kind, target`, `inspect_02-get_objects` tool로 기존 도면·원본/클리핑 객체의 ID·관계. | 기존 시트·뷰·대상 식별, 실제 이미지, 원본/도면 사이의 근거. Layout 캡처는 각 Detail 모드를 유지한다. 표시된 평면만으로 원본의 변경 범위를 추정하지 않는다. | [DR1], [OB1] |
| 3. `generate_or_update_drawings` (execute) | `drawing_06-generate_plan_section` tool에 `operation=Create/Update`, 확인한 `clipping_ids`, 필요한 해치·입면 설정, Create이면 필요 시 원점 `points`. 사용자 목적에 맞게 `drawing_01-apply_style` tool에 선택 레시피 ID. | PlanSection은 모델 공간의 산출물과 `drawing_status`와 인라인 `result` 또는 페이지 조회용 `result.result_id`를 돌려준다. 큰 결과는 `drawing_03-get_plan_section_result` tool로 같은 `result_id`와 반환된 `next_offset`을 따라 끝까지 조회한다. 순서대로 연결한 `json_chunk`를 JSON으로 해석해 항목별 결과를 읽는다. 스타일 성공과 `review_preparation.status=not_executed`는 별개다. | [DR2], [OB1] |
| 4. `validate_drawing` (validate) | 실제 생성/갱신 항목의 `results[].clipping_id`와 `results[].status`를 원본 클리핑 범위, Named View 또는 Layout 캡처 및 객체·치수 관찰과 대조. 필요한 경우 레시피의 `review_preparation`과 출력 선 설정을 대조. | 생성 영수증은 해당 실행 시점의 결과다. 현 도면·평면/단면/입면·원본에서 대응과 변경 범위를 확인하고, 시트에서 읽기·누락·치수·선 위계를 판단한다. 일부 성공은 해당 항목에만 귀속한다. | [DR2], [OB3] |
| 5. `prepare_layout_or_export` (execute) | 실제로 요청된 시트/형식과 대상·축척·용지·출력 설정. Layout 확인은 `capture_04-defined_view` tool. 필요한 출력 작업은 지원되는 Rhino 경로로 수행하며 전용이 없을 때 `script_01-run_project_python` tool의 `code`에 관리형 산출물 경로를 사용하는 Rhino 출력 작업을 지정할 수 있다. | 레이아웃 이미지, 또는 요청한 최종 파일과 출력 경로·시트/축척 확인. 공개 `drawing_06-generate_plan_section` tool은 Layout/PDF 출력 도구가 아니다. 별도 범용 PDF 도구/가이드가 이 도구군에 없다. 캡처가 보관되면 Step에 `image_file.path`를 기록한다. 출력 파일까지 요청됐을 때는 파일 자체를 열어 산출 범위·읽기를 확인한다. | [DR3], [OB3], [FR3] |

### BDD

- **정상** · Given 사용자가 특정 모델 기반 단면 2개와 해당 두 시트를 PDF로 달라고 했다. When 두 클리핑 대상의 PlanSection 항목이 완료되고 Layout 캡처에서 표현과 치수가 확인되며 최종 PDF 파일이 생성된다. Then 생성된 모델 공간의 단면, Layout, PDF를 순서대로 확인하고 최종 PDF를 열어 두 시트의 표현과 축척을 대조한다. **기존 판단의 공백** · PlanSection과 Layout 캡처 성공만으로도 다음 Step을 끝냈다고 기록할 수 있고, 최종 파일에서 잃은 내용은 그 성공 응답에 드러나지 않는다. **적용** · [DR1] 모델/생성 단면의 경로 구분 → [DR3], [OB3] 최종 전달물 다시 확인 → [FR3] 대상별 결과와 근거 전달. **결과** · 정적 walkthrough 통과; Rhino/LLM 행위효과 검증 아님.
- **실패** · Given 두 클리핑 대상의 요청이 `drawing_status="partial"`과 페이지 조회용 `result.result_id`를 반환했고 한 시트에 사용자 수동 주석이 있다. When 일부 새 선이 화면에 보인다. Then 같은 `result_id`로 반환된 `next_offset`을 따라 마지막 페이지까지 조회하고 `json_chunk`를 순서대로 연결해 JSON으로 해석한다. 복원한 영수증의 `results[].status`에서 완료·실패 항목을 읽고 현재 도면의 생성 범위와 수동 주석의 역할을 확인한다. 실패한 대상의 재처리 범위를 정하고 보존할 주석과 새 절단의 정합을 다시 검수한다. **기존 판단의 공백** · 부분 완료와 페이지 조회는 이미 계약에 있다. 완료된 다른 시트를 보존하고 새 원본에도 유효한 수동 표현을 식별하는 것은 정책이 보완한다. **적용** · [DR1], [DR2] 원본과 수동 편집의 관계 판단 → [OB1], [OB3] 보관 결과와 현재 도면 비교 → [DR3] 전달 파일 검수. **결과** · 정적 walkthrough 통과; Rhino/LLM 행위효과 검증 아님.
- **피드백** · Given 모델 공간 단면과 기존 Layout을 검수했다. When 사용자가 축척과 Detail 표시를 수정해 달라고 하되 절단 위치는 유지하라고 한다. Then 이전 절단 근거가 여전히 유효하면 재사용한다. 영향받는 Layout·표시·최종 파일을 다시 검수하고 레시피 성공과 `review_preparation.status="not_executed"`를 확인해 아직 보지 않은 인쇄 상태를 미확인으로 남긴다. **기존 판단의 공백** · 스타일 응답의 검토 안내만으로 유지할 모델 근거와 갱신해야 할 출력 근거가 갈리지 않는다. **적용** · [DE3], [OB3] 피드백과 근거 범위 → [DR3] 전달 형식 확인 → [FR2], [FR3] 사용자 유지 결정과 결과 연결. **결과** · 정적 walkthrough 통과; Rhino/LLM 행위효과 검증 아님.

## component:

[템플릿 정의](../../../features/planning/store.py#L450) · [블록·편집 대상 관찰](../../../features/context/tools-explain.md#L14) · [모델링 도구](../../../features/modeling/tools-explain.md) · [Holon과 겹침](../../../features/components/tools-explain.md)

| 순서·Step | 필요한 입력과 활용할 도구 | 얻는 근거와 다음 판단 | 정책 |
|---|---|---|---|
| 1. `inspect_context` (reason) | 대상·역할·인접 접합과 보존 조건. `inspect_05-resolve_targets` tool에 Plan ID가 있으면 등록 대상부터 조회하고, `scene_05-get_holon` tool에 `live=true`로 현 구성원을 확인. `inspect_02-get_objects` tool과 공유 블록인 경우 `inspect_01-analyze_nested_blocks` tool의 `mode="resolve-block"`, `options.path`. | 대상의 현재 GUID·형상·CRC·배치 및 `data.definition_impact`의 `complete`, `occurrences`, `editing_permission`. 블록 분석 가이드는 공유 정의의 영향·제한을 확인하고 편집 진입 뒤 실제 편집 객체 ID를 재조회하도록 안내한다. 등록·뷰의 범위를 실제 작업 객체와 대조한다. | [SM1], [SM3], [OB1] |
| 2. `design` (reason) | 사용자 요구, 기존 부재의 지지·이음·여유, 바뀌어야 할 배치의 범위. 구법 필요 시 현재 시스템 Layer와 `research_01-get_construction_guidance` tool의 자료를 비교. | 변경한 부재의 형상·재료·구성·범위에 대한 선택. 구법 가이드는 선택 이후의 기록을 안내한다. 공유 정의 전체와 단일 배치의 설계 의도가 다르면 어떤 구성을 수정할지 결정한다. | [SM3], [DE1] |
| 3. `model` (execute) | 동일 관찰의 현재 객체 ID·`face_index`·`expected_geometry_crc`와 이동, 잠기지 않은 닫힌 Brep이면서 일반 모델이면 `model_02-edit_planar_face` tool. 공유 정의 범위/BlockEditNew 작업은 현재 편집 문맥과 권한을 확인하고 적합한 Rhino 경로를 사용. | 면 편집의 형상 재조회 가이드, 또는 Rhino 실행의 `request_id`·완료 증거. CRC 거절이나 변경 불확실 상태에선 현재 대상을 다시 확인한다. Holon 등록은 사용자 목적과 실제 구성·소속 요구가 있을 때 `scene_13-upsert_holon` tool로 별도 수행한다. | [SM3], [OB3] |
| 4. `validate` (validate) | 실제 수정 및 영향 배치의 GUID·형상, `geometry_valid`, 필요한 경우 `solid/manifold/volume`, 단면/접합 관찰, 같은 비교 범위의 겹침. 등록 작업이 있었으면 `scene_05-get_holon` tool에 현재 구성원 조회. | 저장된 변경과 의미·접합·주변에 미친 결과의 독립 근거. Geometry CRC/유효성 통과는 물리적 역할의 확인을 대신하지 않는다. 사용자 의도와 영향 범위에 대한 판단을 보고하고 완료 결정을 별도로 기록한다. | [SM2], [OB1], [FR3] |

### BDD

- **정상** · Given 사용자가 여러 공유 배치 중 한 부재만 다르게 하라고 했다. When `inspect_01-analyze_nested_blocks` tool에서 해당 경로의 공유 정의 영향이 드러난다. Then 대상 배치의 정의를 분리해 변경하고 대상의 접합과 다른 배치의 보존을 관찰한다. **기존 판단의 공백** · 기존 BASIC은 필요한 경우 정의 분리를 이미 설명하며 블록 조회의 `editing_permission`과 가이드도 영향의 한계를 명시한다. 새 Plan 연결은 분석 결과에서 변경 Step의 사용자 범위와 보존 검수를 연결하고, 다른 배치의 영향을 기술 가능 여부와 분리해 기록한다. **적용** · BASIC Plan 흐름 → [SM3], [OB1] 변경 전파·접합 확인 → [FR3] 검증한 결과 전달. **결과** · 정적 walkthrough 통과; Rhino/LLM 행위효과 검증 아님.
- **실패** · Given `model_02-edit_planar_face` tool이 같은 관찰에서 얻었던 CRC가 현재 형상과 달라 편집을 거절했다. When 새 관찰에서 대상의 이음 위치도 달라졌음이 확인된다. Then 현재 ID·면·CRC를 다시 확인하고 기존 이동이 여전히 접합과 사용자 요구를 충족하는지 판단한다. 달라진 부재에 기존 이동을 그대로 적용하지 않는다. **기존 판단의 공백** · CRC 계약이 재조회 필요성을 알려주지만 새로운 형상에서 설계 의도가 아직 유효한지는 에이전트가 판단해야 한다. **적용** · [OB3] 이전 관찰의 범위 → [OB1], [SM2] 새 이음 관계 검토 → [FR2] 범위 결정. **결과** · 정적 walkthrough 통과; Rhino/LLM 행위효과 검증 아님.
- **피드백** · Given 단일 배치 수정과 접합 검수가 끝났다. When 사용자가 인접 배치 한 곳에도 적용하고 다른 배치를 보존하라고 했으며 공유 정의 영향은 더 많은 배치에 걸친다. Then 같은 Plan에서 적용 집합을 다시 확정하고 요청 범위에 해당하는 정의/배치만 편집한다. 새 접합과 보존할 기존 배치를 다시 확인한다. **기존 판단의 공백** · 현행 영향 조회는 변경이 전파될 배치를 알려주지만 사용자의 회신이 허용한 범위까지 해석하지 않는다. **적용** · [FR2], [DE3] 새 사용자 범위 → [SM3] 공유 영향 통제 → [OB3] 필요한 검수 갱신. **결과** · 정적 walkthrough 통과; Rhino/LLM 행위효과 검증 아님.

## 정책 범위와 검토 한계

- [BASIC의 Plan 흐름](../../../BASIC-INSTRUCTIONS.md#plan-흐름과-판단의-연결)은 현재 모델과 이전 결과의 유효성을 판단해 다음 Step에 연결한다. 순서, 적용 범위와 승인 여부를 구분한다. 시작·재개 방법, 기록 입력과 revision 검사는 도구 계약을 따른다.
- 겹침 이미지의 번호·결정 핸들, 실행 시간 초과의 조회 키, 면 편집 CRC, PlanSection 결과 페이지, 구조 판정 상태는 도구 계약을 대조했다. 활동별 정책은 응답에 필요한 확인이 생긴 경우 작업 범위와 영향을 판단하는 근거를 보완한다. 다섯 템플릿에서 도구 계약과 정책의 충돌은 확인되지 않았다.
- 임시 화면 변경은 캡처·구조 오버레이 도구 설명과 [관측 계약](../../../rhino/OBSERVATION-SPEC.md)을 따른다. 사용한 관찰 방식이 이후 판단 범위를 바꾸면 [OB1]로 비교 조건을 다시 맞춘다.
- 32개 Step 순서·종류와 15개 시나리오의 정책 적용을 확인했다. 가상의 상태와 ID는 구조 해석 결과, 피난 법규 판정, 파일 출력 성공, Rhino에서의 변경 효과를 입증하지 않는다.

[SM1]: ../policies/spatial_modeling.md#sm1-의미-경계와-변경-경계를-연결한다
[SM2]: ../policies/spatial_modeling.md#sm2-후속-변경으로-달라진-선행-판단을-다시-확인한다
[SM3]: ../policies/spatial_modeling.md#sm3-상세-수준과-변경-전파를-과업에-맞춘다
[OB1]: ../policies/observation.md#ob1-같은-대상을-설명하는-근거끼리-연결한다
[OB2]: ../policies/observation.md#ob2-발견하지-못한-것과-확인한-부재를-구분한다
[OB3]: ../policies/observation.md#ob3-근거의-유효기간을-변경-영향으로-판단한다
[DR1]: ../policies/drawing.md#dr1-무엇이-설계-원본인지-정한다
[DR2]: ../policies/drawing.md#dr2-재생성-전에-수동-편집의-의도를-보존한다
[DR3]: ../policies/drawing.md#dr3-전달-형식에서-판단이-유지되는지-확인한다
[DE1]: ../policies/design_exploration.md#de1-제안을-검토-가능한-차이로-만든다
[DE2]: ../policies/design_exploration.md#de2-비교-조건과-의미를-맞춘다
[DE3]: ../policies/design_exploration.md#de3-피드백이-바꾼-질문을-읽는다
[FR1]: ../policies/feedback_reporting.md#fr1-결정에-필요한-내용을-함께-전달한다
[FR2]: ../policies/feedback_reporting.md#fr2-답변을-해당-제안과-범위에-연결한다
[FR3]: ../policies/feedback_reporting.md#fr3-전달할-결과와-남길-근거를-구분한다
