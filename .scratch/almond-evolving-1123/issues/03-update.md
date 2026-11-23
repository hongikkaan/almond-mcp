# 06c · 수정이 저장된 경우와 무변경 구분

동일 제목을 두 번 저장하면 revision은 2로 유지되나 두 결과가 모두 success다. 완전 반영·변경은 updated, 실제 무변경은 no_change, 일부 반영은 partial_success와 issues를 반환한다.

**선행 티켓** 없음

## 구현 경계

plan_12-update의 phase/plan/step 응답과 소비자·완료 안내·공개 계약. DB 전환 및 plan.status는 유지한다.

## 수용 기준과 오프라인 검증

변경·무변경·전체 건너뜀·부분 성공·실패·재완료·복수 갱신을 공개 도구에서 비교한다.

## 구현 및 검증 결과

Phase·Plan·Step의 저장 결과를 조립하는 `update_ack`에서 실제 변경과 항목별 건너뜀을 구분했다. 공개 응답 스키마, 도구 설명, 완료 안내의 소비자, 계획 및 조회 문서를 맞췄다. 관련 공개 선언과 기준 스키마는 통합 담당자가 갱신한다.

| 공개 호출 | 확인한 결과 |
|---|---|
| 같은 Plan 제목을 두 번 저장 | 첫 요청은 `updated`, 두 번째는 `no_change`이며 둘 다 revision 2, Plan 업무 상태는 `pending`이다. |
| 빈 패치 또는 전체 항목 건너뜀 | `changed=false`, `no_change`와 기존 revision을 반환한다. 문제 없는 입력은 빈 `issues`이고 건너뛴 입력은 이유를 돌려준다. |
| 유효 변경과 잘못된 항목을 함께 요청 | 유효 값만 한 번 저장하고 `partial_success` 및 항목별 `issues`를 반환한다. |
| Plan·Step 재완료와 동시 Plan 수정 | 저장된 완료 전이에만 정리 안내·후속 작업을 한 번 실행한다. 완료 상태에서 다른 필드를 변경하면 `updated`, 같은 값만 다시 보내면 `no_change`다. |
| Step 저장 실패 또는 후속 Rhino 정리 실패 | 전자는 원래 데이터와 revision을 유지한다. 후자는 `error`와 `changed=true`, 완료된 Step의 상태와 확인할 후속 작업을 반환한다. Rhino 응답은 오프라인 fixture로 검증했다. |

```powershell
. ./src/mcp/use_offline_environment.ps1 -Development -RequireDotNet -ScratchDirectory "$PWD/data/t/plan"
& ./data/development/.venv/Scripts/python.exe -B -X utf8 -m pytest -q src/mcp/tests/test_planning_templates.py src/mcp/tests/test_planning_updates.py src/mcp/tests/test_planning_crud.py src/mcp/tests/test_step_completion.py src/mcp/tests/test_planning_behavior.py src/mcp/tests/test_looping_revision.py src/mcp/tests/test_plan_links.py src/mcp/tests/test_tool_instruction_flow.py src/mcp/tests/test_planning_details.py
. ./src/mcp/use_offline_environment.ps1 -Development -ScratchDirectory "$PWD/data/t/handoff"
& ./data/development/.venv/Scripts/python.exe -B -X utf8 -m pytest -q tests/integration/test_step_handoff.py
```

변경 전 `test_plan_completion_adds_guidance_only_on_a_saved_transition`의 첫 완료 요청은 `success`를 반환해 실패했다. 최종 모듈 회귀 검사는 163개 통과(21.04초), 별도 stdio worker의 저장·인계 검사는 1개 통과(8.76초)다. 검사 환경은 dev의 .NET SDK 8.0.426과 체크아웃 전용 Python을 사용했다.

별도로 `tests/integration/test_stdio_contract.py::test_cold_direct_full_descriptions_and_basic_scripting_guide`를 실행했다. 기준 커밋 `dbdb6f3`의 선언 문서에도 있는 1225·4138행의 ‘아니다.’를 `test_stdio_contract.py:58`의 정규식이 잡아 공개 호출에 도달하기 전에 실패했다. 선언 문서 중앙 동기화 및 전체 stdio 계약 검사에서 추적한다.
