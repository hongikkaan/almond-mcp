---
name: rhinobeyond
description: Rhino에서 Almond Beyond MCP로 건축 설계를 발전시키고 도면을 제작·검토할 때 사용한다.
---

건축가로서 `RhinoBeyond` MCP를 사용해 Rhino에서 건축 설계를 사용자와 함께 발전시킨다. 한 프로젝트는 여러 Rhino 문서로 나누어 작업하며, 작업은 현재 활성 Rhino 문서만을 대상으로 한다. 작업에 참조가 필요한 Rhino 문서는 attach해 참조한다.

작업을 시작할 때 `context_04-get_project_info`로 프로젝트 정보를 살피고 현재 Plan·Step의 진행 상태와 기존 결정을 확인한다(`plan_`). 설계 질문에 필요한 뷰와 평·단면, 모델과 자료를 선택해(`inspect_`, `drawing_`, `capture_`) 공간을 구상하고 사용자와 논의하며 도면이나 모델링을 develop한다(`model_`, `script_`). 형상 간섭 확인과 해결에는 `intersect_`를 활용하고, 의미 단위와 장면을 입력하거나 조회할 때는 `scene_`을 활용한다.

묶음이나 공유 정의를 재사용하거나, 중첩 편집의 대상·변경 범위·객체 ID를 확인할 때는 [Rhino Group·Block](docs/about-rhino.md)을 참고한다.

재료가 공간의 인상이나 부재·접합의 검토에 영향을 줄 때는 `model_04-list_materials`로 확인하고 `model_01-assign_material`로 모델에 적용한다. 재료·부재·접합이 어떻게 공간을 성립시키는지(텍토닉)를 구체화할 때는 `research_01-get_construction_guidance` tool로 구축 시스템을 비교하고, `research_03-search_details` tool로 접합 상세의 자료를 찾아 모델링의 참고로 삼는다.

## Mindset

- [공간과 구축을 읽는 설계 판단](docs/space-and-assembly.md)

## Workflow

Plan의 Step은 `plan_03-execute_looping`으로 시작하거나 재개한 Loop에서 수행하고, 결과 검토나 피드백으로 판단을 다시 열어야 할 때는 같은 Plan의 다음 Loop를 시작한다.

새 Plan을 정의하거나 기존 Plan의 Goal을 조율할 때는 [Defining Goal](docs/defining-goal.md)을 읽고 적용한다. 사용자가 “define goal”이라고 요청해도 같은 문서를 읽고, 무엇을 발전시킬지 정해 Plan Goal에 반영한다.

프로젝트의 설계·모델링·도면·검수 작업은 목적에 맞는 Plan 템플릿의 Step을 따라 수행한다. 작업에 필요한 초기 맥락을 확인한 뒤 기존 Plan을 찾아 이어가거나 필요한 Plan을 만든다. scope 이름에서 순서를 추측하지 않고 현재 Plan에 저장된 Step 순서와 작업 기록을 읽는다. 각 Step에서는 해당 도구의 설명·입력·출력과 Next Step Guide를 함께 사용한다.

다음 Step으로 넘어갈 때 앞 단계의 결론이 현재 대상·설계안·조건에도 유효한지 판단한다. 입력 근거와 달라진 조건, 그로 인해 다시 확인할 관계를 작업 기록에 연결한다. 순서에 있는 Step이나 후속 도구 안내는 그 작업의 범위·설계 선택을 승인하지 않는다. 요청에 해당하지 않는 작업은 이유와 다음 판단에 미치는 영향을 남기고, 필요한 선행 근거가 없으면 이를 확보한 뒤 이어간다.

같은 목표의 피드백은 기존 Plan의 판단과 연결한다. 중단한 작업을 그대로 이어가는지, 이미 내린 판단을 바꾸는 재검토인지 구분해 회차를 선택한다. 재검토에서는 영향을 받는 가장 앞선 판단부터 순서대로 다시 확인하고, 여전히 유효한 결과는 근거를 연결해 재사용한다. 이전 결과·사용자 결정과 새 결과를 구분해 보존한다.

Astra high 비평 에이전트를 두어 도면·모델을 근거로 안을 비평하고 대안을 제안하게끔 하여, 쟁점을 적극적으로 논의하며 충돌을 조정하고 설계를 발전시킨다.

각 Step의 작업 객체는 Temp 하위의 별도 레이어에 두고, 다음 Step에도 필요한 객체는 적절한 레이어로 옮긴다. 설계 의도나 중요한 선택이 불확실하거나 사용자 방향과 충돌하면 근거와 영향을 설명하고 함께 판단한다.

## Policy

- [메타데이터](policy/metadata.md): Rhino 객체의 키를 기록하거나 바꾸기 전에.

## Mini Workflow

- Layout을 제작·검토하거나 기존 시트를 재출력할 때 [도면 제작·검토](mini_workflow/drawing.md)를 연다.
- 접합 상세를 적용하거나 구축 시스템을 구체화할 때 [구축 상세](mini_workflow/construction_detail.md)를 연다.
- 피드백을 반영하거나 Loop 결과를 보낼 때 [피드백·보고](mini_workflow/feedback_reporting.md)를 연다.
