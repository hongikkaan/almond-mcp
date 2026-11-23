# 04b · 검수 Plan의 판단 근거

기존 inspection은 define_criteria → observe → evaluate → report_findings 네 단계다. 벽체·슬래브 접합이 한 화면에 가려지는 사례에서 주변 영향, 근거와 미확인 구간을 새 Plan에 기록할 수 있게 기존 템플릿을 보강한다.

**선행 티켓** 없음

## 구현 경계

기존 scope 및 과거 Plan·Step·사용자 매핑을 보존한다. 새 scope, 특정 첫 뷰 강제, 자동 모델 수정은 제외한다.

## 수용 기준과 오프라인 검증

임시 DB의 공개 생성/조회와 같은 접합 결함 사례로 inspection mini-workflow와 템플릿이 요청하는 판단을 비교한다. 뷰만으로 접합을 볼 수 없으면 미확인으로 남기고 수정 후에는 같은 조건에서 재확인한다.

## 구현 및 검증 결과

검토본은 dev의 `.agents/skills/rhinobeyond/mini_workflow/inspection.md`다. 글로벌 RhinoBeyond 설치본에는 이 문서가 없다. 다음은 같은 벽체·슬래브 접합 사례를 두 방식으로 읽은 결과다.

| 미니워크플로우가 요구하는 판단 | 새 Plan에서 확인한 Step |
|---|---|
| 접합이 만족할 기준과 영향을 받는 주변 관계 | `define_criteria`의 표시 이름으로 검수 범위와 기준을 확인한다. |
| 정면에 가려진 접합의 간격을 판단할 조회 선택 | `observe`에서 관계를 드러내는 뷰나 조회, 필요한 형상·치수를 선택한다. |
| 결함의 위치와 근거, 관측할 수 없었던 구간 구분 | `evaluate`에 북측 접합의 간격을 미확인으로 기록했고, 별도 Step 상세 조회에서 같은 기록을 읽었다. |
| 수정한 경우 원래 문제 조건에서 다시 확인 | `report_findings` 표시 이름에서 같은 조건으로 재확인할 것을 안내한다. |

네 Step의 종류·순서·의존성은 기존 템플릿과 같다. 표시 이름은 새 Plan 생성 때만 저장한다. 기존 Step ID·리비전·사용자 scope 매핑 보존을 검사했다. 이전 형식의 스냅샷 fixture는 당시 코드(`bb46a95^`)가 기록한 대로 Step ID를 표시 이름으로 구성했다.

```powershell
. ./src/mcp/use_offline_environment.ps1 -Development -ScratchDirectory "$PWD/data/t/plan"
& ./data/development/.venv/Scripts/python.exe -B -X utf8 -m pytest -q src/mcp/tests/test_planning_templates.py::test_inspection_plan_exposes_criteria_for_an_occluded_wall_slab_joint
& ./data/development/.venv/Scripts/python.exe -B -X utf8 -m pytest -q src/mcp/tests/test_planning_templates.py
```

변경 전 단일 시험은 첫 Step이 `define_criteria`만 반환해 실패했다. 변경 후 템플릿 검사 22개를 통과했다. [06c의 계획 회귀 검사](03-update.md)에서는 레거시 스냅샷을 포함해 163개를 통과했다. 가림과 간격은 합성 사례다. 승인된 실제 모델에서 두 방식을 각각 수행하고 결함 발견·근거 품질을 비교하는 검수는 남아 있다.
