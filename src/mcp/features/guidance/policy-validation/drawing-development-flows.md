# 2D 설계 발전 흐름

정적 계약 검토이며 실제 Rhino 실행 또는 에이전트 행동 효과 검증이 아니다. 단계별 의미는 [Planning README](../../planning/README.md#drawing_development)를 따른다. 도구 계약의 기존 입력·후속 안내를 재사용하며 drawing·design_exploration·observation·feedback_reporting policy로 판단을 보완한다.

## drawing_development:

| Step | 근거와 판단 |
|---|---|
| 1. `inspect_context` (reason) | `context_04-get_project_info` tool의 project/document 정보와 `plan_05-get` tool의 목표·기존 Step을 읽어 문서·단위·원본·변경 범위를 맞춘다. 결과가 안내한 대상 조회를 이어간다. |
| 2. `inspect_surroundings` (reason) | `inspect_02-get_objects` tool의 scope/filters/fields와 `capture_04-defined_view` tool의 target_kind/target으로 객체·주변 뷰를 읽는다. 페이지가 잘렸으면 나머지를 조회하고 주변 관계를 숨긴 캡처로 전체를 판단하지 않는다. |
| 3. `explore_opportunities` (reason) | 앞 단계의 도면 근거로 설계 질문·가정을 정하고 `plan_12-update` tool의 Step input_refs/output_refs에 연결한다. 부분 반영 issues는 확인하며 도구 호출 성공을 설계 판단의 정답으로 읽지 않는다. |
| 4. `develop_options` (reason) | 같은 범위·축척으로 2D 대안을 비교한다. 필요시 `script_02-run_rhino` tool의 script/language로 맡긴 범위의 스케치를 만들고 `capture_04-defined_view` tool로 읽는다. 실행 미완료는 request_id로 `script_03-get_execution` tool에서 회수한다. 선택 권한에 따라 질문 또는 적용한다. |
| 5. `develop_design_drawings` (execute) | 직접 설계하는 2D 원본은 `script_02-run_rhino` tool로 수정하고 completed·결과를 확인한다. 기존 3D 파생 도면인 경우에만 drawing Update/결과 회수 계약을 적용한다. 순수 2D를 위해 3D 생성을 요구하지 않는다. |
| 6. `resolve_spatial_conflicts` (resolve) | 객체 조회·동일 뷰 캡처와 필요한 읽기 전용 치수 측정으로 공간 충돌 근거를 확인한다. 맡긴 수정은 script 실행·결과 회수 후 같은 대상에서 재확인한다. 선 교차와 사용상의 간섭을 구분한다. |
| 7. `coordinate_drawings` (resolve) | 관련 도면별 `capture_04-defined_view` tool과 객체 조회·측정으로 축선·치수·레벨·개구를 대조한다. 한쪽 갱신만으로 양쪽 정합을 선언하지 않고 필요한 변경과 미확인 관계를 기록한다. |
| 8. `validate_design_relationships` (validate) | 최신 도면·측정과 목표를 대조하고 `plan_12-update` tool로 확인 근거·남은 가정을 기록한다. 캡처가 증명하지 못하는 높이·구조·법규를 검증 완료로 표현하지 않는다. |
| 9. `cleanup_intermediate_artifacts` (validate) | 현재 과업의 임시 표현을 식별하고 허용된 정리만 수행한다. 최신 뷰와 객체를 다시 확인하고 원본·대안 근거를 보존한다. 저장을 맡긴 경우에만 `script_04-save_document` tool의 saved/modified 결과로 저장 여부를 보고한다. |

## Given–When–Then

- 정상: 2D 평면과 단면으로 공간 발전을 요청받았을 때, 원본·주변 조건을 확인하고 동등 조건의 대안을 비교한 뒤 위임된 안을 도면에 적용한다. 공간 충돌과 도면 간 레벨·개구를 정합하고 목표 대비 검수 후 근거를 보존해 정리한다. 3D 모델을 요구하지 않는다.
- 미확인: 평면상 계단 위치가 성립하지만 층고·단면 근거가 없을 때, 높이·통과 여유까지 검증했다고 하지 않는다. 설계 판단에 필요한 단면·레벨 근거를 확보하거나 미확인 한계를 보고한다. 모든 작업에 모든 도면을 강제하지 않는다.
- 피드백: 최종안에 대해 사용자가 진입 방향을 바꾸면, 같은 Plan에서 주변 관계와 대안 판단을 갱신하고 영향을 받은 도면·충돌·관계를 재검수한다. 기존 근거 중 유효한 내용은 재사용하며 승인되지 않은 모델 변경으로 확대하지 않는다.
