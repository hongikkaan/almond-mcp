# Phase·Plan·Step의 저장·참조 계약

작업 단위의 의미·운영과 도구 입력은 [Rhino Almond 스킬](../../skills/rhino-almond/SKILL.md#phase--task--step)을 따른다. 현재 API의 Plan은 스킬에서 부르는 Task다.

## 대상과 관계

Phase는 Plan의 상위 묶음이고 Plan 안에 Step을 둔다. Plan의 Scene 참조는 맥락, Component 참조는 작업 대상이다. Step도 Component를 지정할 수 있으며, 대상이 Plan의 맥락 Scene에 연결돼 있어야 한다는 제약은 없다.

참조 인자를 생략하면 기존 값을 유지한다. Step의 대상이 `null`이면 Plan 대상을 상속하고, 명시적인 `[]`는 대상 없음이다. 빈 대상을 Plan 전체나 Scene 전체로 확장하지 않는다. `resolve_targets`는 등록 대상을 해석하며 실제 형상 실행과 별개다.

`depends_on`은 참고 관계를 저장하는 JSON 배열이다. 현재 저장소는 자기 참조·순환·미생성 ID를 허용하고 실행 순서나 선행 완료를 강제하지 않는다. 작업 시 Phase에는 Phase, Task에는 Task를 기록하는 기준은 스킬을 따른다. 기존 `scene_id`는 `scene_ids`의 첫 항목과 호환된다.

## 상태와 revision

Plan·Step 상태는 `pending`, `running`, `paused`, `completed`, `failed`, `blocked`다. 작업을 중단·전환·재개할 수 있으며 선행 작업 완료나 뒤 단계 무효화를 강제하지 않는다.

Plan 변경을 commit할 때마다 전체 Plan 상태를 immutable revision으로 저장한다. `expected_revision`으로 오래된 상태의 수정을 거절하며, 관계·상태·참조 변경과 revision 보관은 같은 DB transaction에서 처리한다. revision은 설계 시도 횟수가 아니며 Rhino 형상을 백업하지 않는다. 기존 Plan에는 migration baseline을 남기되 과거 이력을 만들어내지 않는다.

## 파일·작업자료·역조회

Phase와 Scene은 `file_name`을 항상 반환하고 미지정이면 빈 문자열이다. 선택한 Plan의 `artifact_dir`은 프로젝트 `tmp/YYMMDD_name` 아래에 둔다. `artifact_refs`와 Step 입출력 참조는 프로젝트 상대경로다. `set_working_plan`은 폴더를 재사용하고 `rename_artifact_folder`는 현재 참조를 갱신하며 과거 revision을 보존한다.

`get_selection_references`는 선택 객체에서 등록 Component의 조상과 직접·상속된 Plan/Step 참조를 찾는다. 일반 조회는 `include_ids=true`일 때 ID를 포함하며 get 조회는 이미 입력한 대상 ID를 반복하지 않는다.
