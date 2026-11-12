# 구축 상세·모델 수정·검토 정책 검증

`construction_detail` 5개, `model_revision` 8개, `inspection` 4개 Step을 구현 순서대로 검토했다. 정상·실패·피드백 시나리오 9개는 가정된 도구 응답에서 새 정책이 요구하는 다음 판단을 추적한다. **정적 walkthrough 통과. Rhino 실행과 LLM 행위효과는 검증 범위 밖이다.**

## 공통 도구 연결

| 위치 | 설명·입력 | 출력과 다음 안내 | 정책 적용 |
|---|---|---|---|
| 초기 맥락 | `context_04-get_project_info` tool로 필요한 `sections=["project","document","locations"]`를 읽는다. `context_01-get_policy` tool로 BASIC과 활동에 필요한 정책을 조회한다. | `project.file_path`와 `project.is_bound_document`, 문서 정보, 현재 작업 위치를 대조한다. 프로젝트 안내는 `plan_08-list` tool, `plan_10-set_working` tool, `inspect_02-get_objects` tool로 연결한다. 저장된 대상이 필요하면 `inspect_05-resolve_targets` tool에 `plan_id`와 선택적 `step_id`를 준다. `live_verified=false`인 대상은 `scene_05-get_holon` tool의 `live=true` 또는 실제 객체 조회로 확인한다. | 초기 맥락은 Plan 확인에 필요한 진입이다. BASIC의 「Plan 흐름과 판단의 연결」과 OB1에 따라 실제 문서·범위부터 맞춘다. |
| Plan 확인 | 기존 Plan은 `plan_08-list` tool의 `request.target="plan"`으로 찾는다. 새 Plan이 필요하면 `plan_02-create` tool의 `request.target="plan"`, `title`, `goal`, `scope`를 쓴다. | 생성 응답의 `plan.plan_id`와 `next_step_guide`를 `plan_05-get` tool의 `request.target="plan"`, `include_details=true`로 잇는다. `plan_08-list` tool의 `request.target="step"`도 현재 순서와 `loop_no/revision/read_only`를 반환한다. | scope 이름보다 저장된 Step 순서를 사용한다. 정책별 별도 Plan이나 승인 Step을 만들 필요가 없다. |
| 회차 선택 | `plan_03-execute_looping` tool에 `plan_id`와 필요 시 `resume/feedback`을 준다. | `next_step_id`는 `completed`가 아닌 첫 Step의 ID이며 `previous_loop`, `steps`, `artifact_dir`도 반환한다. `resume=true`는 기존 상태를 보존하고 다른 `feedback`이 있으면 그 텍스트를 갱신한다. `resume=false`는 같은 Plan의 새 회차에서 Step을 `pending`으로 만든다. 안내는 이전 근거 확인과 `plan_10-set_working` tool 선택을 제안한다. | BASIC 및 FR2에 따라 기존 대기가 해소됐으면 이어가고, 이미 한 판단의 전제가 달라졌으면 가장 이른 영향 Step부터 다시 본다. 상태가 새 판단을 대신하지 않는다. |
| 작업·근거 | `plan_10-set_working` tool에 `plan_id`와 해당 `step_id`를 준다. `plan_12-update` tool의 `request.target="step"`에 `plan_id/step_id/loop_no`와 필요한 `input_refs/output_refs` 패치, 선택적 `status/expected_revision`을 준다. | 선택 응답의 `artifact_dir`와 `loop_no/revision`을 사용한다. 저장된 Plan 캡처의 `image_file.path`는 `output_refs.add`에 기록하라는 안내가 있다. 기록 응답의 `changed/issues`와 반환 상태를 확인한다. `partial_success`는 건너뛴 항목이 있을 수 있고 revision 충돌 안내는 현재 Plan 재조회로 잇는다. | 저장 실패나 revision 충돌은 작업 기록의 문제다. 당시 모델 근거를 보존하고 기록 대상·회차를 재확인한다. Rhino 편집을 반복할 이유는 없다. |
| 보고·완료 | Loop 안내에 따라 목표, 변경, 시각 자료, 검증 범위, 남은 선택을 보고한다. 필요할 때 `plan_12-update` tool의 `request.target="plan"`으로 업무 상태를 기록한다. | `status=completed`는 사용자의 완료 결정 뒤에 사용한다는 입력 안내가 있다. 도구 실행 결과와 Plan 업무 상태는 서로 다른 출력이다. | FR3로 검토 결과와 실제 수정·검증 범위를 보여 준다. FR2는 최종 보고마다 승인 질문을 추가하지 않는다. |

[기본 정책](../../../BASIC-INSTRUCTIONS.md), [Planning 도구](../../planning/tools-explain.md), [Plan 입력 계약](../../planning/requests.py), [Plan 출력](../../planning/output.py), [revision 충돌](../../planning/store-explain.md), [Loop 구현](../../planning/looping.py), [작업 공간](../../../runtime/workspace.py), [후속 안내 선택](../../../tool_guidance.py).

## construction_detail:

[등록된 Step](../../planning/store.py#L421-L427). 유형 Layer에서 시작하는 경우와 시스템 Layer가 이미 있는 경우 모두 실제 지지·접합과 자료를 대조한다. 상세 발전 범위는 현재 사용자 요청으로 판단한다.

| Step | 이전 결과를 받아 쓰는 도구와 입력 | 출력·Next Step Guide와 이어지는 정책 판단 |
|---|---|---|
| 1. `inspect_context` (reason) | 요청된 접합부·보존 조건과 연결 문서를 확인한다. `inspect_02-get_objects` tool의 `scope="document"`, `object_ids` 또는 `filters.layer_paths`, `fields`로 객체·Layer·경계·그룹을 읽는다. 주변을 함께 볼 시점을 `capture_02-inspection` tool의 `views`로 구성한다. | 객체 `complete/next_offset/snapshot`과 캡처 `tiles/complete`에서 관찰 범위를 확인한다. 후속 객체 페이지는 `offset=next_offset`, `expected_snapshot=snapshot`으로 연결한다. 저장한 Plan 캡처는 해당 Step에 기록한다. OB1·SM3로 실제 접합 상대와 현재 표현 단계, 보존할 연속 조건을 2로 넘긴다. |
| 2. `review_system` (retrieve) | 유형/시스템, 재료와 현재 모델에서 확인한 경간을 `research_01-get_construction_guidance` tool의 `query/category/material/span_m`에 반영하고 `field_groups=["rules"]`로 치수 경험칙과 구법 참조를 받는다. 외부 출처 후보는 `research_03-search_details` tool의 `query`로 찾고 `field_groups=["all"]`에서 사용 조건을 읽는다. | `systems[].fits_span/depth_guidance/construction_reference`는 후보 근거다. `total=0`의 `hint`는 검색 조건 조정을 안내한다. `sources[].generation_use="candidate_only"`인 출처는 후보 자료다. 검색 성공 시 재료 지정 안내는 기록 방법을 제공한다. SM3·OB1로 실제 지지 방향·접합과 맞는 범위를 확인해 3에 전달한다. |
| 3. `resolve_detail` (reason) | 후보의 실제 차이를 사용·조립·지지·배수 조건에 대조한다. 부족한 관찰은 같은 대상의 `inspect_02-get_objects` tool과 `capture_02-inspection` tool로 보완한다. | 타일 범위와 기하 관측은 서로 비교할 근거다. DE1·DE2로 필요한 만큼만 제안과 비교를 만들고, 사용자 선택이 필요한 주요 차이는 FR1로 전달한다. FR2로 기존 선택과 범위를 연결한다. 경험칙의 통과와 재료 안내만으로 선택을 확정할 수 없다. |
| 4. `model_detail` (execute) | 선택한 상세의 형상과 역할 Layer를 적용한다. 전용 편집으로 처리하기 어려운 기하는 `script_02-run_rhino` tool에 `script/language`를 준다. 재료는 `model_04-list_materials` tool의 `include_ids=true`에서 얻은 ID로 `model_01-assign_material` tool에 `guids/material_id`와 필요 시 `attach_metadata=true`와 `structural_role/construction_reference`를 준다. | 스크립트 `completed=false`와 `request_id`가 있으면 안내에 따라 동일 ID로 `script_03-get_execution` tool을 사용한다. 재료의 `applied_count`와 `changed_guids`의 의미를 구분하고 안내대로 `inspect_02-get_objects` tool로 확인한다. 재료 지정은 객체 Layer를 이동하지 않는다. BASIC·SM3·OB3로 실행 상태와 건축적 근거를 구분해 5로 잇는다. |
| 5. `validate_detail` (validate) | 최신 대상·주변을 `inspect_02-get_objects` tool의 `fields`로 다시 읽고 `capture_02-inspection` tool에서 접합과 주변을 본다. 의도하지 않은 양의 겹침이 검토 항목이면 `intersect_01-find` tool의 `object_ids/include_block`을 그 범위에 맞춘다. | 겹침 0의 안내는 해당 범위의 양의 부피 겹침에 한정한다. OB1–OB3·SM2로 역할 Layer, 맞물림, 지지·조립·배수를 각 근거에 대조하고 FR3로 검증한 내용과 현장·공학 자료가 필요한 사항을 보고한다. |

| 경우 | Given | When | Then 및 정책 매핑 | 기존 안내에서 부족했던 연결 → 새 행동 | 검토 결과 |
|---|---|---|---|---|---|
| 정상 | 사용자가 목구조 지붕과 홈통 접합 상세 및 선택한 시스템을 정했다. | 연구가 `construction_reference`와 경험칙을 주고 스크립트가 완료됐다. 최신 객체와 주변 이미지에서 접합·받침·배수 연결을 확인했다. | SM3로 정해진 상세 수준을 따르고 OB1·OB3로 현 모델의 기하·타일을 대조한다. FR2·FR3로 승인 근거, 적용 결과, 모델에서 확인한 관계와 현장 확인 범위를 기록한다. | 재료 안내와 실행 결과가 각각 후속 도구로 이어졌다. 이제 이미 승인된 범위를 다시 묻지 않고, 해당 위치에서 상세가 성립하는지 검증하고 보고한다. | 정적 통과 |
| 실패 | 유형 Layer만 있으며 접합부 지지 조건이 가려져 있다. | `fits_span=true`와 재료 지정 안내가 나왔으나 필요한 캡처 타일이 실패하여 `complete=false`다. | SM3·OB1·OB2로 후보를 보존하면서 지지 근거를 추가 확보한다. 주요 시스템 선택이 아직 필요하면 DE1·FR1·FR2로 조건과 차이만 제시한다. 그 접합의 적용은 근거와 선택이 충족될 때 진행한다. | 조회 성공·부분 이미지와 상세 적용 사이의 판단이 필요했다. 이제 유효한 조회는 활용하고, 지지 미확인이나 미결정이 걸리는 편집만 보류한다. | 정적 통과 |
| 피드백 | 첫 회차에서 지붕 가장자리 상세를 적용하고 보고했다. | 사용자가 돌출형 대신 매립형 홈통을 요청했다. 재개 시 새 텍스트가 저장되어도 `next_step_id=null`일 수 있다. | BASIC·DE3·OB3·FR2로 변경된 배수·점검 접근성과 상세 선택이 영향을 받는 첫 판단을 찾는다. 같은 Plan의 새 회차에서 유효한 관측은 연결해 재사용하고 영향받은 접합과 적용을 다시 검증한다. | 재개 안내는 상태 보존 방법을 다뤘다. 이제 사용자 피드백을 예전 안의 승인으로 읽지 않고 선택 근거를 갱신한다. 요청이 분명한 매립형 변경에 반복 승인을 요구하지 않는다. | 정적 통과 |

## model_revision:

[등록된 Step](../../planning/store.py#L411-L420)의 8개 Step과 현재 Planning README의 순서를 기준으로 한다.

| Step | 이전 결과를 받아 쓰는 도구와 입력 | 출력·Next Step Guide와 이어지는 정책 판단 |
|---|---|---|
| 1. `inspect_context` (reason) | 연결 파일과 Plan 범위를 맞춘 뒤 `inspect_02-get_objects` tool의 `scope="document"`와 현재 대상·인접 `object_ids`, `fields`를 쓴다. 관련 시점은 `capture_02-inspection` tool로 확보한다. | `objects[].id/layer_path/bounds/groups` 및 페이지 범위를 대조한다. 이미지와 파일 저장 상태를 분리하고 저장 근거를 Step에 연결한다. OB1로 수정 대상과 영향을 비교할 기준 상태를 잡는다. |
| 2. `identify_tectonic_system` (reason) | Layer와 실물 역할을 맞춰 본다. 공유 블록은 `inspect_01-analyze_nested_blocks` tool의 `mode="resolve-block"`과 `options.path`를 쓴다. `research_01-get_construction_guidance` tool은 필요할 때 자료를 보완한다. | 블록 응답 `data`에서 정의와 다른 배치의 영향을 확인한다. 편집에 들어가면 `inspect_02-get_objects` tool로 작업 객체 ID를 다시 확인하라는 안내가 있다. SM3로 실제 변경 전파와 보존 관계를 다음 판단에 연결한다. 이 Step을 상세 발전으로 자동 확장하지 않는다. |
| 3. `diagnose_issue` (reason) | 관측의 대상·시점을 맞추고 필요 시 `intersect_01-find` tool에 최상위 `object_ids`와 `include_block`을 넘긴다. 유효 폭 등 다른 질문은 해당 관계를 실제 측정한다. | `intersections.number`는 양의 부피 겹침 개수다. 미지원·계산 실패는 `unsupported_objects/failed_pairs` 등의 오류 근거가 될 수 있다. OB1·OB2·SM2로 의도한 접합과 불필요한 충돌, 치수 문제를 구분해 원인을 4로 넘긴다. |
| 4. `define_changes` (reason) | 대상·이동량·보존 조건을 정한다. 고정 면 편집이 가능한 경우 `inspect_02-get_objects` tool에 `scope="document"`, `object_ids`와 `fields=["id","faces","geometry_crc"]`를 쓴다. | 안내는 같은 관찰의 ID·`face_index`·CRC를 사용하게 한다. 다음 면 페이지는 `face_offset`과 해당 객체의 `expected_geometry_crcs`를 받는다. SM1·SM3·FR2로 필요한 변경 범위를 확정하고 다른 배치나 지지·접합에 관한 범위를 벗어나는 변경만 논의한다. |
| 5. `apply_changes` (execute) | 일반 모델의 지원 형상은 `model_02-edit_planar_face` tool의 `object_id/face_index/expected_geometry_crc/translation` 또는 `model_03-edit_planar_faces` tool의 `edits`를 쓴다. 일반 경로로 처리하기 어려우면 `script_02-run_rhino` tool에 맞는 코드를 쓴다. | 성공 단일 응답의 `result.edited/result.geometry_crc`, 배치의 `result.complete/result.items/result.mutation_state`와 최상위 오류·불명 상태를 구분한다. 도구 안내는 최신 객체 조회 및 미완료 스크립트의 같은 요청 ID 회수를 다룬다. OB3로 실제 반영된 결과를 기준으로 영향 관측을 다시 정한다. |
| 6. `resolve_collisions` (resolve) | 바뀐 범위에서 `intersect_01-find` tool로 검사한다. 양의 겹침에 비교가 필요하면 `intersect_02-resolve` tool에 앞 검사와 같은 `object_ids`, `include_block`을 전달해 리뷰를 시작한다. | `awaiting_choice`의 `review_id`, 이미지와 `objects[].number`를 읽고 동일 `review_id`와 `choice=1/2/"skip"`으로 응답하라는 안내가 있다. 블록 구성원의 자동 차집합은 지원하지 않으므로 skip하거나 맡긴 범위에서 명시적 블록 편집을 검토한다. `state=completed`와 `skipped_pairs`를 함께 읽는다. SM1·SM2·FR2로 남길 기능과 요청 범위를 판단해 절단 또는 유지를 정한다. 0이면 `intersect_02-resolve` tool을 호출할 이유가 없다. |
| 7. `validate_impacts` (validate) | 실제 적용 후 `inspect_02-get_objects` tool에서 변경·보존 대상의 현재 기하를 읽는다. `capture_02-inspection` tool은 지원되는 타일 범위에 쓰고 블록 인스턴스에 필터가 필요하면 현재 계약에 맞는 시점·블록 조회를 쓴다. | 새 CRC, `geometry_valid/solid/manifold`, 타일 `complete`는 각각 해당 관찰 범위의 결과다. OB1–OB3·SM2·SM3로 문 회전·유효 폭·공유 배치 등 영향을 다시 확인한다. |
| 8. `final_validation` (validate) | 최초 문제와 보존 기준에 최신 근거를 대조한다. 영구 저장 요청이 포함된 경우 `script_04-save_document` tool로 현재 연결 문서를 저장한다. | `saved=true`와 `modified=false`는 저장 상태다. 검증 근거·미해결 범위를 `plan_12-update` tool의 해당 Step·Loop에 연결하고 FR3로 보고한다. 완료 결정은 기존 Plan 계약을 따른다. |

| 경우 | Given | When | Then 및 정책 매핑 | 기존 안내에서 부족했던 연결 → 새 행동 | 검토 결과 |
|---|---|---|---|---|---|
| 정상 | 사용자가 문 위치 조정과 인접 구조·공유 배치 보존을 요청했다. | 공유 영향 조회 뒤 지정 배치만 고치는 방법으로 편집했고, 현재 치수·이미지에서 문 회전과 폭·인접 배치를 확인했다. 검사 범위에서 겹침이 0이다. | SM3·OB1·OB3로 다른 배치 보존을 포함해 비교한다. SM2·OB2로 절단 호출을 생략하고 폭·개폐를 별도로 검증한다. FR3로 변경과 보존 근거를 보고한다. | 0의 도구 안내 자체는 절단이 불필요하다고 했다. 이제 해당 설계 범위에서 주변 사용과 공유 배치가 보존됐는지까지 대조한다. | 정적 통과 |
| 실패 | 여러 객체의 수정이 요청됐고 일부 변경 여부만 확인됐다. | 배치 `result.complete=false/result.mutation_state=partial` 또는 스크립트 `completed=false`가 반환됐다. | 기존 도구 계약대로 배치 항목별 상태와 현재 객체를 대조하거나 동일 스크립트 `request_id`로 조회한다. OB3·SM2로 적용 여부에 따라 영향받은 관측을 갱신하고 확인된 미완료분의 다음 편집을 결정한다. | 부분 배치 재실행 금지와 요청 회수는 기존 계약이었다. 이제 이전 캡처·검증 중 실제 적용 결과 때문에 바뀐 근거까지 선별한다. | 정적 통과 |
| 피드백 | 충돌 리뷰에서 바닥을 절단하는 선택이 제시됐다. | 사용자가 바닥을 유지하고 덕트 경로를 바꾸라고 했다. 기존 `review_id`에는 이전 절단 선택을 제출할 수 있다. | FR2·SM1·SM2로 이전 선택을 제출하지 않는다. BASIC·DE3로 바닥 보존과 덕트 재경로를 최초로 영향받는 판단에 연결해 다시 수행하고, OB3로 사용 범위와 인접 관계를 재검증한다. | 리뷰 안내는 번호를 전달하는 방법만 설명했다. 이제 회신으로 보호 대상이 바뀌었으므로 선택·기하·검사 범위를 갱신한다. | 정적 통과 |

## inspection:

[등록된 Step](../../planning/store.py#L428-L433). 발견한 결함은 검토 결과에 포함한다. 수정 요청이 추가되면 그 요청의 범위에서 수행 여부를 판단한다.

| Step | 이전 결과를 받아 쓰는 도구와 입력 | 출력·Next Step Guide와 이어지는 정책 판단 |
|---|---|---|
| 1. `define_criteria` (reason) | 요청과 `context_04-get_project_info` tool에서 대상 문서를 확인한다. 작업 중인 뷰 정보가 필요하면 `inspect_03-get_document_context` tool에 필요한 `sections`를 넘긴다. | 문서와 Named View/Layout 목록·경고를 얻는다. `sections`를 생략한 문서 조회는 현재 화면 도구를 안내할 수 있다. OB1·OB2로 무엇을 어느 범위와 기준으로 판단할지 정하고 알려지지 않은 기준을 명시한다. |
| 2. `observe` (retrieve) | `inspect_02-get_objects` tool의 `scope/result_mode/fields`와 필요한 필터로 범위를 조회한다. `capture_02-inspection` tool은 `views/model_view_id` 또는 지원되는 범위 필터를, `capture_04-defined_view` tool은 `target_kind/target`을 쓴다. | 객체 페이지 `snapshot/next_offset`과 계층 `children_state`, 타일 `complete/tiles`로 관찰 누락을 확인한다. `scope_unavailable`인 숨김 객체는 `scope="document"` 조회의 구조·치수로 보완할 수 있다. 같은 숨김 객체를 캡처 요청에 다시 넣어도 가시성이 복구되지 않는다. OB1·OB2로 도구마다 실제 포함한 범위를 확인한다. |
| 3. `evaluate` (validate) | 기준별 필요한 자료를 대조한다. 부피 겹침은 `intersect_01-find` tool의 실제 `object_ids/include_block`에서 읽고, 예를 들어 통과 높이에는 해당 위치의 기하 치수를 쓴다. | 0 결과의 안내는 양의 겹침만 설명한다. OB1·OB2로 판정에 필요한 범위가 빠졌는지 확인하고, 검사가 충분하지 않으면 보완하거나 해당 판단을 미확인으로 둔다. |
| 4. `report_findings` (reason) | 관찰 근거, 기준별 결과와 유보, 수정 제안이 있는 경우 그 제안을 전달한다. `plan_12-update` tool은 증거를 해당 Step·Loop에 잇는다. | Loop 안내는 검증 결과와 남은 선택을 보고하게 한다. `changed/issues`는 저장 기록의 상태다. BASIC·FR2·FR3로 보고 결과와 이후 설계 결정·모델 수정 여부를 구분한다. |

| 경우 | Given | When | Then 및 정책 매핑 | 기존 안내에서 부족했던 연결 → 새 행동 | 검토 결과 |
|---|---|---|---|---|---|
| 정상 | 사용자가 문과 복도의 유효 폭만 검토해 달라고 했고 판정 기준을 확인할 수 있다. | 기준과 동일 범위의 이미지·실제 형상 치수에서 미달을 발견했다. | OB1·OB2로 기준과 측정 범위를 함께 밝히고 BASIC·FR3로 미달 결과와 수정 제안을 보고한다. 검토 요청의 범위에서는 수정 명령을 사용하지 않는다. | 기존 도구는 캡처와 치수 근거를 제공했다. 이제 검토 기준과 근거를 대응시키고 미달 발견을 고쳐 달라는 요청으로 확장하지 않는다. | 정적 통과 |
| 실패 | 사용자가 숨은 설비까지 포함한 통과 조건을 확인해 달라고 했다. | `scope="current"`에는 대상이 없고 필요한 타일 하나는 실패했다. 확인된 솔리드 집합에서 겹침 0이 나왔다. | OB1·OB2로 `scope="document"`에서 대상을 먼저 확인한다. 숨김 상태를 유지하며 지원되는 기하 자료로 보완하고, 해당 조건의 근거가 남지 않으면 미확인으로 보고한다. | 도구별 누락·0의 범위는 설명돼 있었다. 이제 개별 도구의 범위를 합쳐 필요한 전체 판정이 가능한지 먼저 판단한다. | 정적 통과 |
| 피드백 | 첫 회차에서 문과 복도의 유효 폭만 보고했다. | 사용자가 상부 덕트 하부 높이를 검토 항목에 추가했다. | BASIC·FR2·OB1·OB3로 같은 Plan의 `define_criteria`부터 추가 범위를 반영한다. 유효 폭 근거는 시점과 조건이 맞으면 재사용하고 상부 자료를 새로 확인한다. FR3로 새 결과를 보고한다. | Loop 안내에는 이력을 읽고 재사용하는 방법이 있었다. 이제 검토 기준을 갱신하고 덕트 수정으로 작업을 넓히지 않는다. | 정적 통과 |

## 중복과 범위 확인

- BASIC은 실제 Plan의 순서를 따르고 활동별 정책을 현재 Step에 연결한다. 초기 맥락 조회는 진입 단계다. 위 경로 어디에도 활동별 별도 Plan, 새 승인 Step, 외부 채널 또는 일률적인 승인 대기가 추가되지 않는다. 중대한 변경·설계 선택의 범위는 현재 요청과 기존 결정으로 판단하며, FR2는 같은 조건의 승인을 재사용한다.
- 지원 형상, 페이지, 타일, 결과 필드, 동일 요청 회수, Plan 완료 조건은 도구 계약에서 가져왔다. SM2는 충돌의 건축적 의미와 변경 뒤 영향 판단을 추가한다. OB1–OB3는 여러 결과가 같은 범위의 근거인지, 변경 뒤에도 유지되는지 판단한다. FR3은 보고 자료에서 실제 변경·검증·남은 선택을 연결한다.
- 세 시나리오의 캡처는 검토 증거다. 도면 작성·갱신·Layout 전달을 별도로 가정하지 않았으므로 DR1–DR3를 필수 경로에 추가하지 않았다.
- 판정 기준이나 실제 관측이 끝내 부족한 경우 결과를 미확인으로 남긴다. 연구 라이브러리의 경험칙은 프로젝트별 시공·공학 검증을 대체하지 않는다. 도구 가용성, Rhino의 실제 상태, 사용자 회신과 실제 실행 결과는 이 검토에서 확인하지 않았다.

[SM 정책](../policies/spatial_modeling.md), [OB 정책](../policies/observation.md), [DR 정책](../policies/drawing.md), [DE 정책](../policies/design_exploration.md), [FR 정책](../policies/feedback_reporting.md), [객체·캡처 도구](../../context/tools-explain.md), [관측 계약](../../../rhino/OBSERVATION-SPEC.md), [타일 가시성 제한](../../context/native/InspectionCapture.cs#L137), [구법 도구](../tools-explain.md), [모델링 도구](../../modeling/tools-explain.md), [겹침 도구](../../components/tools-explain.md), [출력 필드 계약](../../../output_contracts.py), [공개 도구 예시](../../../../../tool_description_spec.md).
