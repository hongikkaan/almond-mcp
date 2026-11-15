# Step 자동 완료 흐름

공개 입력·반환은 [계획 도구 계약](README.md#step-완료와-temp-정리)과 [도구 설명](tools-explain.md#update_planning)을 따른다. `StepCompletionFlow`는 다른 상태에서 completed로 바뀌는 요청에 기존 `store.edit_step`의 `_before_complete` hook을 전달한다. 저장소가 모든 입력·Loop/revision을 검증한 뒤 native 정리를 한 번 호출하며, 성공을 확인한 뒤 DB 상태·Step 기록·revision을 commit한다.

별도의 확인 대기·yes/no·pending map·token·receipt·페이지 조회 흐름은 사용하지 않는다. status 생략/null과 다른 상태 수정은 일반 수정이다. 이미 completed인 기록 수정·동일 completed 요청은 재정리하지 않는다. 다른 상태로 바꾼 뒤 completed로 전환하면 현재 최상위 temp와 모든 하위 계층을 다시 정리한다.

native 실패·부분/불명 결과·timeout은 자동 재시도하거나 완료로 기록하지 않는다. 정리 성공 뒤 DB 기록이 실패하면 cleanup 근거·DB 미완료·재관찰 안내를 함께 반환한다. 실제 모델 변경은 DB transaction으로 되돌릴 수 없으며 기존 Undo 복구도 실패할 수 있다. Rhino Undo는 Step 저장 상태를 되돌리지 않는다. 복구한 자료를 처리한 뒤 Step을 다른 상태로 바꿨다가 completed로 전환해 재정리한다.
