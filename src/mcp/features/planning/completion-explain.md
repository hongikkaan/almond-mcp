# Step 자동 완료와 temp 정리

`completion.py`는 `plan_12-update` tool의 새로운 completed 전환 직전에 사용하는 고정 native 연결이다. Step 상태·입력·Loop/revision 검증과 DB 저장은 호출부와 저장소가 담당한다. 이 모듈은 자료의 보존 가치를 판단하거나 보존 대상을 선택·이동하지 않는다.

## completed

<!-- instruction:completed -->
Step에서 사용한 임시자료인 temp 및 모든 하위 레이어·잔여 객체를 삭제했습니다. 완료에 따른 정상 정리 과정입니다. 되돌릴 자료는 Rhino Undo로 복구해 처리한 뒤 Step을 다른 상태로 바꿨다가 completed로 전환하면 다시 정리됩니다. Rhino Undo는 Step의 저장 상태를 되돌리지 않습니다.
<!-- /instruction:completed -->

## not_needed

<!-- instruction:not_needed -->
최상위 temp 계층이 없어 삭제한 레이어·객체가 없습니다. 정리가 필요 없는 상태를 확인했으며 Step 완료 기록을 진행합니다.
<!-- /instruction:not_needed -->

## unsupported

<!-- instruction:unsupported -->
현재 로드된 Bridge는 자동 Step 정리를 지원하지 않습니다(step_completion=2 필요). Step은 미완료로 유지됩니다. 업데이트된 런타임의 설치·실제 로드를 확인한 뒤 완료를 다시 요청하세요.
<!-- /instruction:unsupported -->

## 입력과 완료 계약

- `cleanup(send, model_path)`는 연결된 저장 문서의 최상위 `temp`와 모든 하위 레이어·잔여 객체를 자동 정리한다. 남길 자료·객체는 완료 전 기존 조회·이동 도구로 temp 밖의 다른 레이어에 먼저 옮긴다. 중첩 temp만 선택하는 부분 정리나 임의 위치의 temp 전역 삭제는 제공하지 않는다.
- capability `step_completion=2`를 확인한 뒤 `{type: "step_completion", expected_model_path: model_path}` 요청을 한 번 보낸다.
- 새 completed 전환은 기존 `store.edit_step`의 입력·현재 Loop·선택적 expected_revision 검증 후 native 정리를 실행하고 성공이 확인된 뒤 같은 DB transaction에서 상태·Step 기록·revision을 저장한다. 일반 수정은 기존 계약을 따른다. native 실패·timeout·불명 결과에서 Step은 이전 미완료 상태를 유지하며 자동 재시도하지 않는다.
- native는 UI thread의 문서·편집 상태와 현재 전체 temp 계층을 검증하고 기존 실행기의 Undo/복구 경로로 정리한다. 각 삭제 직전의 live 상태 검사와 외부 객체·레이어 보존 검사를 유지한다. Undo 한 번으로 모든 실패가 원자적으로 복구된다고 보장하지 않는다.
- 잠금·참조·블록 정의/편집·page-space/grip 및 기존 구성요소/Sheet/PlanSection 관계는 현행 native 보호 검사에 따라 차단한다. 활성 구성요소 등록은 영구 그룹 GUID와 현재 객체의 실제 그룹 소속으로 확인하고 각 삭제 직전에도 다시 확인한다. `ps:placement`·`ps:source_layer`·동적 `ps:clip:<id>`와 기존 Drawing registry 및 legacy 출력 관계도 보존한다. 차단된 자료는 검토·보존·해결한 뒤 완료를 요청한다. 일반 User Text 존재를 귀속·삭제 범위의 근거로 쓰지 않는다.
- 삭제 범위는 최상위 temp와 그 하위 계층이다. NamedView·Layout은 레이어 객체처럼 취급하지 않으며 clipping plane에서 유래한 외부 도면도 연동 삭제하지 않는다. 기존 update 보호 관계를 이유로 외부 도면을 수정하거나 삭제하지 않는다.
- 성공 결과는 `cleanup_complete=true`, 양의 정수 `document_serial`, 0 이상의 정수 `deleted_object_count`·`deleted_layer_count`, `mutation_state=applied|not_needed`를 담는다. 불리언·실수는 serial/count로 받지 않는다. not_needed는 두 삭제 수가 모두 0인 경우, applied는 하나 이상의 실제 삭제가 있는 경우다. 안내는 native 호출 전에 읽고 검증해 결과 설명 실패가 정리 수행 근거를 잃게 하지 않는다.
- 실패의 attempted count는 성공한 Delete 호출의 진단 정보일 수 있으며 최종 삭제 완료 수로 취급하지 않는다. 삭제 수가 null이거나 정리 완료를 확정할 수 없으면 미완료·재관찰 안내를 유지한다. native 정리 성공 뒤 DB 기록이 실패하면 실제 정리 결과와 DB 미완료를 구분해 반환한다.

## 반복 완료와 실제 사용

이미 completed인 Step에 같은 상태를 쓰거나 메모·참조를 수정해도 재정리하지 않는다. paused 등 다른 상태로 변경한 뒤 completed로 전환하면 현재 최상위 temp 전체를 다시 정리한다. Rhino Undo로 정리 결과를 복구해도 DB의 Step 상태는 유지된다. 복구한 자료를 처리하고 Step을 다른 상태로 바꿨다가 completed로 전환해야 다시 정리된다.

현재 재료 도구는 기존 속성을 복제해 MaterialIndex/MaterialSource를 갱신하며 레이어를 바꾸지 않는다. temp에서 재료를 적용한 뒤 보존할 객체의 레이어를 이동하는 기존 흐름을 사용한다. 오프라인 대역의 속성·형상 보존 검사는 실제 Rhino의 재료 표시·보존 판단·삭제·Undo 검증을 대신하지 않는다. 오프라인 검사는 일회용 자료와 대역을 사용하며 사용자 파일·기존 DB/snapshot을 변경하지 않는다.
