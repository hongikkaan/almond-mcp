# 설계와 의미 Plan의 정책 검토

공간 발전 9개, 평면 편집 4개, 의미 탐색 4개 Step을 생성 코드 순서대로 읽었다. 현재 진행 중인 Plan에는 저장된 Step 순서를 적용한다. 아래 도구는 각 판단에 필요한 증거를 얻는 경로이며 모든 호출을 일괄 실행하는 목록이 아니다. 예시의 반환값은 공개 계약에 맞춰 구성했다. [템플릿 생성 코드](../../planning/store.py#L388) · [도구 스키마 고정본](../../../../../tests/integration/tool_schemas.json) · [출력 계약](../../../output_contracts.py) · [결과별 후속 안내 구현](../../../tool_guidance.py) · [공개 도구 예시](../../../../../tool_description_spec.md)

각 시나리오의 **정적 walkthrough 통과**는 문서와 도구 계약을 순서대로 적용해 기대 판단에 도달했다는 뜻이다. 실제 Rhino 관찰·변경·저장, 정책 적용 전후 LLM 행동 비교, 사용자 피드백은 이번 검토에서 확인하지 않았다.

적용 기준은 [BASIC Plan 흐름](../../../BASIC-INSTRUCTIONS.md#plan-흐름과-판단의-연결), [공간 모델링 SM1–SM3](../policies/spatial_modeling.md), [관찰 OB1–OB3](../policies/observation.md), [도면 DR1–DR3](../policies/drawing.md), [설계 탐색 DE1–DE3](../policies/design_exploration.md), [피드백과 보고 FR1–FR3](../policies/feedback_reporting.md)이다.

## 세 흐름에 공통인 연결

| 시점 | 도구 설명과 입력 → 출력 → 후속 안내 | 다음 판단 |
| --- | --- | --- |
| 문서와 과업 파악 | `context_04-get_project_info` tool의 `sections=["project","document"]`와 필요시 `include_ids=true` → `project.is_bound_document`, 등록 파일, 현재 문서 속성 → Plan 목록·작업 공간·객체 조회 안내. | 초기 조회로 사용자가 요청한 문서와 목적을 확인한다. 활성 과업의 Plan을 찾아 이어가고 필요한 경우 목적에 맞는 scope로 만든다. |
| Step 흐름 확인 | `plan_02-create` tool의 `request.target="plan"`, `title`, `goal`, `scope` 및 관련 참조 → `plan.plan_id` → 상세에서 생성 Step 확인 안내. `plan_08-list` tool의 `request.target="step"`, `plan_id` → 순서, `loop_no`, `revision`, `truncated` → `plan_05-get` tool에서 같은 스냅샷의 Step 상세 조회 안내. | 저장된 순서와 이전 결론을 읽는다. 상세의 `read_only`와 `input_refs`·`output_refs`를 확인해 과거 관찰과 현재 변경을 연결한다. |
| 피드백과 재개 | `plan_03-execute_looping` tool의 `plan_id`, `resume`, `feedback` → `loop_no`, `next_step_id`, `previous_loop`, 현재 `steps`와 `artifact_dir` → 미완료 Step 선택, 증거 기록, 회차 보고 안내. | 같은 Plan에서 단순 중단은 현재 회차로, 이미 내린 판단에 영향을 주는 피드백은 기존 결과를 보존할 후속 회차로 연결한다. 새 회차는 정의 순서를 유지하며 유효한 앞 단계의 근거를 다시 쓸 수 있다. 시작 결과가 불명확하면 현재 회차를 읽어 확인한다. |
| 증거 기록과 결과 보고 | `plan_10-set_working` tool에 `plan_id`, 현재 `step_id`, `loop_no` → `artifact_dir`, `revision` → 저장 파일을 Step 근거로 기록하라는 안내. `plan_12-update` tool의 `request.target="step"`, 같은 Plan·Step·Loop, 선택적 `expected_revision`, `input_refs`·`output_refs` 패치 → `status`, `changed`, `issues` → 성공 시 다음에 할 Step을 정한 경우 선택, 부분 적용 시 건너뛴 항목 확인 안내. | Step 선택은 실행과 별개다. 부분 적용 또는 무변경은 실제 남은 근거를 조회한다. 적용 결과와 검수 결과를 기록한다. Plan 완료 결정은 기존 사용자 결정 규칙을 따른다. |

BASIC은 사용자 요구대로 현재 과업의 Plan Step 순서를 적용한다. 연결, 정책 및 프로젝트 초기 조회는 그 흐름을 파악하는 진입이다. 활동별 policy는 해당 Step의 기준을 제공한다. 하나의 Step에서 여러 policy를 함께 읽어도 별도 Plan이나 추가 승인 없이 이미 맡긴 작업을 계속할 수 있다. 변경 또는 결정의 권한은 사용자 요청에 있으며, Plan 순서와 도구 결과는 기술적 다음 행동을 안내한다. [Planning 도구 계약](../../planning/README.md) · [고정 관찰·캡처 계약](../../../rhino/OBSERVATION-SPEC.md)

## spatial_development:

| Step | 도구 설명과 입력 → 출력 → 후속 안내 | 새 정책에서 이어지는 판단 |
| --- | --- | --- |
| 1. `inspect_context` (reason) | `context_04-get_project_info` tool로 문서·프로젝트를 확인한다. `plan_05-get` tool의 `request.target="plan"`, `plan_id`, `include_details=true` → 목표·대상·이전 기록 → 수행할 Step을 정한 뒤 선택 안내. `inspect_05-resolve_targets` tool의 `plan_id`, 선택적 `step_id` → 저장된 `holon_ids`와 `live_verified=false` → 대상이 있으면 live Holon 조회 안내. | **OB1·SM1** 현재 문서, 대상 Scene, 사용자 보존 조건을 맞춘다. 저장된 대상 집합을 실제 형상과 대조할 범위를 세운다. |
| 2. `inspect_surroundings` (reason) | `inspect_02-get_objects` tool의 `scope="document"`와 필요한 `object_ids` 또는 `group_ids`, `fields` → `objects`, `snapshot`, `next_offset`, `complete` → 다음 페이지에 같은 조건과 `expected_snapshot` 유지 안내. `capture_02-inspection` tool의 `views`, 필요시 공통 `object_ids` → `tiles`, `complete`, 이미지와 파일 정보 → Plan에 저장한 완전한 이미지는 Step 근거 연결 안내. | **OB1·OB2** 전체와 집중 관찰을 대조해 화면에서 빠진 주변과 실제 부재를 구분한다. 대안의 동선·지지·경계에 필요한 관찰을 보강한다. |
| 3. `Explore_opportunities` (reason) | `research_02-get_typology_narrative` tool의 `query`, `construction_system` → `entries` → 관련 구법 비교 안내. `research_01-get_construction_guidance` tool의 `query`, `category`, `span_m`, 필요한 `field_groups` → `systems`, 제공되는 경간 적합성과 참고 자료 → 선택된 구법의 재료 적용 경로 안내. | **DE1·SM3** ‘더 열린 진입’ 같은 목표를 어느 경계와 사용 관계가 달라져야 하는지로 풀고, 자료의 권장값은 위치와 설계 단계에 맞춰 참고한다. |
| 4. `develop_options` (reason) | `capture_02-inspection` tool의 `views`로 비교에 필요한 현황 관찰을 확보한다. `plan_12-update` tool의 Step 근거 패치 → `changed`·`issues` → 다음 Step을 정하면 선택 안내. | **DE1·DE2·FR1·FR2** 공통 조건에서 안별 차이·보존 조건을 보여 준다. 스케치로 판단 가능하면 상세화 비용을 줄인다. 위임된 선택은 진행하고, 사용자의 결정이 필요한 범위만 근거를 갖춰 묻는다. |
| 5. `develop_model_and_drawings` (execute) | `model_02-edit_planar_face` tool의 `object_id`, `face_index`, `expected_geometry_crc`, `translation` → 변경 결과 → `inspect_02-get_objects` tool로 변경 형상·CRC 재확인 안내. 그 외 편집은 필요한 경우 `script_02-run_rhino` tool의 `script`, `language` → `completed`, `request_id`, 결과 및 해당하는 변경 상태 → 대기 종료 시 `script_03-get_execution` tool로 같은 요청 조회 안내. 파생 도면이 범위에 있으면 `drawing_06-generate_plan_section` tool의 `operation`, `clipping_ids` → `drawing_status`와 결과. 큰 결과의 `result.result_id`는 `drawing_03-get_plan_section_result` tool로 읽고 반환된 `next_offset`을 따라 끝까지 조회한다. 순서대로 연결한 `json_chunk`를 JSON으로 해석해 항목별 결과를 읽는다. | **SM1·SM3·DR1·DR2·OB3** 위임된 변경을 정확한 원본에 적용한다. 대상과 공유 영향, 도면의 원본과 수동 편집을 식별하고 결과에서 후속 검사의 객체·시점을 정한다. |
| 6. `resolve_collisions` (resolve) | `intersect_01-find` tool의 `object_ids`, `include_block` → 범위 내 `intersections.number` → 0이면 별도 설계·여유 조건의 확인 범위 설명. `intersect_02-resolve` tool에 앞 검사와 같은 `object_ids`, `include_block`으로 시작 → 비교 이미지와 메타데이터 `state="awaiting_choice"`, `review_id`, `objects[].number` → 해당 `review_id`에 `choice=1/2` 또는 `"skip"`을 내는 안내. 블록 구성원은 리뷰만 지원하며 자동 차집합은 지원하지 않으므로 skip하거나 맡긴 범위에서 명시적 블록 편집을 검토한다. 처리 결과의 `skipped_pairs`와 앞서 적용한 변경도 확인한다. | **SM1·SM2·OB2** 표시 번호를 구조 관계와 맞춘다. 의도된 접합은 유지하고 불필요한 충돌은 맡긴 범위에서 해결한다. 미확정 접합은 필요한 관찰을 보강한다. |
| 7. `check_tectonic_consistency` (resolve) | `inspect_02-get_objects` tool의 `scope`, `object_ids`, `fields`에서 필요한 형상·레이어·경계·그룹을 확인한다. 구조 검토가 범위에 있으면 `analysis_04-validate_structure` tool의 `guids`와 구조·하중 조건 → `status`, `passed`, `warnings`, `assumptions` → 문제 부재 시각화 안내. | **SM2·SM3·OB3** 충돌 해결로 달라진 지지, 접합과 연속 조건을 재확인한다. 범위와 설계 단계에 맞춰 단순 표현으로 남길 상세와 확인할 관계를 고른다. |
| 8. `validate_relationships` (validate) | `capture_02-inspection` tool은 모델 관찰을, `capture_04-defined_view` tool의 `target_kind`, `target`은 실제 도면 이미지를 반환한다. `inspect_02-get_objects` tool로 필요한 수치 근거를 확인한다. 피난 사전 검토가 범위에 있으면 `analysis_01-check_egress` tool의 `plate_bounds_mm`, `exits`와 필요한 실측 입력 → `passed`, `checks`, `warnings`, `source_note` → 미달 시 측정 갱신 및 재검토 안내. | **OB1·OB2·OB3·DR3** 현재 안의 통행·지지·도면 표현은 각 주장에 맞는 근거로 확인한다. 피난 계산은 입력한 측정과 도구가 제시한 기준 범위에서 해석한다. |
| 9. `cleanup_intermediate_artifacts` (validate) | `plan_05-get` tool의 현재·이전 상세에서 `artifact_refs` 및 Step refs를 확인한다. `plan_10-set_working` tool은 현재 `artifact_dir`과 기록 경로를 안내한다. 모델 임시 객체는 `inspect_02-get_objects` tool로 현재 ID와 관련 대상을 확인한다. 영구 저장 요청 시 `script_04-save_document` tool의 `saved`, `modified`를 확인한다. | **FR3·OB3** 현재 과업의 불필요한 항목을 식별하고 앞 회차 비교·결정·검증 근거를 보존한다. 정리가 전달물과 참조를 바꾸면 그 영향 범위를 다시 확인하고 사용자에게 결과를 연결한다. |

[관측·충돌·형상 편집](../../../rhino/OBSERVATION-SPEC.md) · [모델링·도면 설명](../../modeling/tools-explain.md) · [실행 결과·저장 근거](../../../runtime/RHINOCODE-SPEC.md)

| 사용자 시나리오 | Given / When | 적용 전 부족했던 판단 → Then | 검토 결과 |
| --- | --- | --- | --- |
| 정상 · 출입구와 지지를 유지한 계단·마루 개선 | 사용자가 배치 변경을 맡기고 원래 출입구와 지지 보존을 요구했다. 문서·객체가 일치하고 같은 조건으로 비교한 안을 적용한 뒤 양의 겹침 0이 반환됐다. | 겹침 검사만으로는 계단 사용과 지지의 결론이 부족했다. **OB2·SM2·DR3**에 따라 통로·계단 여유, 접합, 도면 표현을 현재 결과에서 각각 확인한다. **FR3·OB3**에 따라 시험 조각 중 쓸모가 끝난 것만 정리하고 남긴 근거·최종 결과를 연결한다. | 정적 walkthrough 통과 |
| 실패 · 지지 부재를 가리킨 trim 선택 | 기존 비교에서 `awaiting_choice`와 번호가 왔다. 그 번호가 지지 부재일 수 있고, 뒤이어 인접 객체를 수정한 스크립트도 대기 시간에 최종 결과가 도착하지 않았다. | 비교 번호만으로 대상의 역할과 현재 상태를 판단할 수 없었다. **OB1·OB3**으로 재실행 전에 같은 `request_id`의 결과와 현재 형상을 대조하고 바뀐 범위의 비교를 다시 확보한다. **SM1·SM2**로 지지 역할을 확인한 뒤 유지·제거를 결정한다. 선택이 필요한 경우 **FR1·FR2**로 영향과 미확인을 담아 그 결정만 요청한다. | 정적 walkthrough 통과 |
| 피드백 · 마루는 유지하고 계단 방향 변경 | 첫 회차 결과를 보고한 뒤 사용자가 새 방향을 지정했다. 앞선 대안의 동선·지지·도면 전제가 달라졌다. | 이전 완료 상태는 새 방향에서 어떤 검증이 필요한지 정해 주지 않았다. **DE3·OB3**으로 같은 Plan의 후속 회차에서 기존 현황과 마루의 보존을 확인하고 바뀐 전제부터 순서대로 대안과 영향을 다시 판정한다. **SM2·DR2·FR3**으로 지지·도면을 갱신하고 이전 비교를 남긴다. 같은 결정을 명료화하는 답변이면 **FR2**에 따라 이미 받은 승인을 재사용한다. | 정적 walkthrough 통과 |

## plan_editing:

| Step | 도구 설명과 입력 → 출력 → 후속 안내 | 새 정책에서 이어지는 판단 |
| --- | --- | --- |
| 1. `inspect_plan` (reason) | `context_04-get_project_info` tool로 문서와 단위를 확인한다. `inspect_03-get_document_context` tool의 `sections=["layouts","named_views"]` → 해당 이름·ID와 경고. `capture_04-defined_view` tool의 `target_kind`, `target` → 이미지 및 `image_file` → Plan에 보관할 경우 Step 근거 연결 안내. `inspect_02-get_objects` tool의 `scope`, `filters`, `fields` → 관찰된 객체와 페이지 범위. | **DR1·OB1** 지정 화면과 편집 원본을 연결한다. 직접 편집하는 2D, 모델에서 생성된 도면, Layout Detail과 주석의 역할을 읽는다. |
| 2. `define_changes` (reason) | `plan_12-update` tool의 `request.target="step"`, `input_refs`·`output_refs` 패치 → 실제 변경과 `issues` → 다음 Step 선택 또는 건너뛴 근거 확인 안내. | **DR1·DR2·DE1** 사용자 스케치와 현 도면에 근거해 벽·문·해치·치수가 표현하는 관계를 구체화한다. 편집할 원본과 함께 갱신할 표현, 보존할 수동 작업을 정한다. |
| 3. `edit_plan` (execute) | 2D 원본 직접 편집에는 필요시 `script_02-run_rhino` tool의 `script`, `language` → `completed`, `request_id`, 결과 → 필요시 `script_03-get_execution` tool로 회수 안내. 파생 도면에는 `drawing_06-generate_plan_section` tool의 `operation="Update"`, `clipping_ids` → `drawing_status`와 결과. 부분 완료·취소에도 객체가 남을 수 있어 `result.result_id`가 있으면 `drawing_03-get_plan_section_result` tool로 읽는다. 위 공간 발전의 5번 Step과 같이 반환된 `next_offset`을 따라 마지막 페이지까지 조회하고 `json_chunk`를 순서대로 연결해 JSON으로 해석한다. 스타일 작업이 범위에 있으면 `drawing_01-apply_style` tool의 `recipe_id` → 결과와 `review_preparation`이 있는 경우 출력 검토 안내. | **DR1·DR2·OB3** 맡긴 범위의 원본을 수정한다. 재생성 뒤 남은 보정의 의도와 실제 적용 상태를 확인하고 필요한 표현만 연동한다. |
| 4. `validate_plan` (validate) | `capture_04-defined_view` tool로 같은 Layout·Named View를 다시 캡처하고 `inspect_02-get_objects` tool의 `fields`로 확인 가능한 객체 위치·경계·레이어를 대조한다. 치수값 자체가 필요하면 `script_02-run_rhino` tool에 읽기 전용 측정 `script`를 전달해 결과를 현재 객체에 연결한다. 저장을 맡긴 경우 `script_04-save_document` tool의 `saved`, `modified`를 읽는다. | **DR3·OB1·OB2·FR3** 바뀐 위치와 유지한 공간, 표기·축척·잘림·선 위계를 실제 전달 형식에서 점검한다. PNG가 보여 주지 못한 인쇄 속성과 저장 여부는 각각의 확인 범위로 남긴다. |

[도면 생성·회수 설명](../../modeling/tools-explain.md) · [도면 스타일 설명](../../drawings/tools-explain.md) · [Layout 캡처 관찰 범위](../../../rhino/OBSERVATION-SPEC.md#화면-캡처)

| 사용자 시나리오 | Given / When | 적용 전 부족했던 판단 → Then | 검토 결과 |
| --- | --- | --- | --- |
| 정상 · 기존 평면의 문과 주변 표현 조정 | 사용자가 지정 Layout의 문 위치를 옮기고 기존 복도 폭을 보존하라고 맡겼다. 직접 편집할 2D 원본과 Detail을 구분했고, 변경 뒤 같은 Layout과 수치에서 새 위치·벽선·해치·유효 폭이 일치했다. | 편집 성공만으로 원본과 전달 표현의 정합을 판단할 수 없었다. **DR1·OB1·DR3**으로 원본과 표현을 맞춰 확인하고 **FR3**으로 결과와 확인 범위를 보고한다. 전체 문서 저장은 사용자 요청과 저장 확인에 연결한다. | 정적 walkthrough 통과 |
| 실패 · 부분 갱신 뒤 PNG만 정상 | 파생 도면 Update가 일부 처리된 뒤 중단됐으나 Layout PNG는 저장됐다. 현재 도면에서 바뀐 선은 보이지만 모델 원본과 일부 치수의 관계는 확인되지 않는다. | PNG 상태만으로 어떤 변경이 반영됐는지 알 수 없었다. **DR1·DR2·OB3**으로 원본과 수동 편집을 식별하고, 보관된 결과가 있으면 현재 도면과 대조해 적용·미적용·미확정을 가른다. **DR3**으로 필요한 갱신만 마친 뒤 실제 전달 표현을 다시 본다. | 정적 walkthrough 통과 |
| 피드백 · 문 위치 유지, 표기만 교정 | 사용자가 이전 위치 변경안을 검토한 뒤 현 위치를 유지하고 모델과 일치하도록 표기만 수정하라고 했다. 앞 회차 캡처는 위치 변경안의 것이다. | ‘수정’이라는 회신만으로 원본과 변경 범위를 알 수 없었다. **FR2·DE3·OB3**으로 피드백이 가리킨 안과 현 위치를 구분하고 기존 Plan에서 바뀐 판단으로 돌아간다. **DR1·DR3**으로 현재 위치와 치수를 대조해 표기만 적용하고 같은 Layout에서 다시 확인한다. | 정적 walkthrough 통과 |

## semantic_exploration:

| Step | 도구 설명과 입력 → 출력 → 후속 안내 | 새 정책에서 이어지는 판단 |
| --- | --- | --- |
| 1. `inspect_context` (reason) | `context_04-get_project_info` tool로 문서와 파일을 확인한다. `scene_07-list` tool의 `file_name`, `include_ids`, `offset` → `scenes`, `total`, `truncated` → 선택한 Scene 상세 조회 안내. `scene_04-get` tool의 `scene_id` → 등록 정보 → 현재 구성원 조회 안내. | **OB1·DE2** 모델 파일, 등록된 Scene, 해석할 행태·사용 조건을 연결한다. 해당 경계와 관계를 확인할 관찰 범위를 정한다. |
| 2. `inspect_surroundings` (reason) | `scene_06-get_objects` tool의 `scene_id`, `include_ids`, `expected_model_path`, `limit`·`offset` → `objects`, `total`, `truncated`, `live_verified`, `model_path` → 잘렸으면 같은 필터로 다음 페이지 조회. 합집합에서 Holon 구성의 근거가 필요하면 `scene_05-get_holon` tool의 `holon_id`, `live=true`, `recursive=true`, 필요시 `include_ids`·`field_groups` → 직접/확장 Holon 근거. `capture_02-inspection` tool로 주변 범위와 집중 관찰을 비교한다. | **OB1·OB2·SM1** 구성원 합집합과 live Holon을 대조하고, 합집합만으로 출처가 모호한 중복 객체의 직접 등록 여부는 미확인으로 남긴다. 화면 가시성과 실제 공간 관계를 함께 읽어 누락된 범위를 보강한다. |
| 3. `interpret_spatial_context` (reason) | 역할·행태를 근거로 해석한다. 요청에 등록이 포함된 경우 `scene_02-create` tool의 `name`, `units`, `file_name` 또는 `project_file_id` → `scene.scene_id` → 구성원 추가 경로 안내. `scene_13-upsert_holon` tool의 `name`, `scene_ids`, 필요한 `object_ids`·`rhino_group_id`·`child_holon_ids` → Holon 등록 결과 → live Holon 확인 안내. `scene_01-add_objects` tool의 `scene_id`, `object_ids` → `failed_indices`, `already_present_indices` → 현재 Scene 멤버십 조회 안내. | **SM1·DE1·DE2·FR2** 포함·제외가 장면의 역할과 연속을 설명하는지 검토한다. 맡긴 의미 등록은 실행 후 live 결과를 대조한다. 탐색에서 나온 후보는 사용자 요청의 범위대로 제안으로 전달한다. 형상 편집은 그 행위가 맡긴 범위에 있는지 따로 판단한다. |
| 4. `report_findings` (reason) | `capture_02-inspection` tool의 `views` → 작업 화면을 유지한 이미지와 범위. 실제 격리가 필요한 경우 `capture_03-current_view` tool의 `target_ids`, `target_kind`, `isolate=true` → 이미지 결과와 별도의 `view_change`·`mutation_applied` → 보관할 Plan 이미지의 Step 기록 안내. `plan_12-update` tool로 관찰과 판단 근거를 남긴다. | **FR1·FR3·OB1·OB2** 포함·제외 이유와 전체·집중 이미지를 연결하고, 의미 해석과 확인한 멤버십, 아직 검증하지 못한 공간 관계를 밝힌다. 실제 격리는 관측 계약에 따라 복원하고 그 상태를 확인한다. |

[Scene 도구 설명](../../scenes/tools-explain.md) · [현재 Scene 구성원 구현](../../scenes/store.py#L146) · [Holon 설명](../../components/tools-explain.md) · [관찰과 의미 등록 계약](../../components/SPEC.md) · [격리·이미지 상태 계약](../../../rhino/OBSERVATION-SPEC.md#화면-캡처)

| 사용자 시나리오 | Given / When | 적용 전 부족했던 판단 → Then | 검토 결과 |
| --- | --- | --- | --- |
| 정상 · 마루와 계단참의 장면을 등록 | 사용자가 두 구성의 관계를 읽고 합의한 경계만 등록하라고 했다. 실제 문서와 Scene이 일치했고, 주변·live 구성에서 지지와 앉는 행위가 가능한 범위를 식별했다. 등록 뒤 재조회도 기대 집합과 일치했다. | 등록 성공은 사용 관계나 형상 변경의 근거가 아니었다. **SM1·OB1·FR3**으로 이미 맡긴 등록을 진행하고, 확인된 구성·행태 해석·실통행 미검증을 따로 설명한다. 승인 질문을 다시 붙이지 않는다. | 정적 walkthrough 통과 |
| 실패 · 일부 Scene 페이지와 격리 화면 | 집중 화면에 주변 부재가 보이지 않고, Scene 첫 페이지는 `truncated=true`이며 검사 캡처는 `complete=false`를 반환했다. 가려진 부재는 의미 경계를 바꿀 수 있다. | 지금 보이지 않는 것과 현재 범위에 없는 것을 가를 근거가 없었다. **OB1·OB2·SM1**으로 동일 조건의 나머지 페이지와 주변 live 관찰을 보강한다. 실제 Isolate가 적용된 경우 그 상태와 복원을 관측 계약에 따라 확인하고 경계 판정이 남아 있으면 **FR3**으로 알린다. | 정적 walkthrough 통과 |
| 피드백 · 한쪽 진입에서 두 번째 진입까지 검토 | 첫 진입만 포함한 경계 후보를 보고했고, 사용자가 두 번째 진입도 같이 봐 달라고 했다. 두 번째 진입의 관찰과 등록 요청은 아직 없다. | 요청이 기존 경계의 승인인지 새 해석 조건인지 구분해야 했다. **FR2·DE3·OB1**으로 기존 Plan에서 관찰 범위를 넓히고 포함·제외를 다시 판단한다. **SM1**로 이번 요청이 위임한 범위를 읽고 새 의미 경계를 제안한다. 기존 제안 근거는 보존한다. | 정적 walkthrough 통과 |
