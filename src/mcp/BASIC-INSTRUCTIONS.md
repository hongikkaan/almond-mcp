---
name: rhino-almond
description: "Architectural judgment for developing existing designs with Almond MCP in Rhino."
---

# Rhino Almond

Almond MCP를 사용해 Rhino에서 건축 설계를 사용자와 함께 발전시킨다. 한 프로젝트는 여러 Rhino 문서로 나누어 작업하며, 작업은 현재 활성 라이노 문서만을 대상으로 한다. 작업에 참조가 필요한 Rhino 문서는 attach해 참조한다.

작업을 시작할 때 context_04-get_project_info tool로 프로젝트 정보를 살피고 현재 Plan·Step의 진행 상태와 기존 결정을 확인하며(`plan_`), 설계 질문에 필요한 뷰와 평·단면, 모델과 자료를 선택해(`inspect_`, `drawing_`, `capture_`) 공간을 구상하고 사용자와 논의하며 도면이나 모델링을 develop(`model_`, `script_`)하며, 필요에 따라 재료 지정과 구축의 구체화자료(`research_`)를 활용해 모델링한다. 형상 간섭 확인과 해결은 `intersect_`를 활용한다.

건축 요소를 물리적 구성과 접합의 assembly로도 다루고, 의미 단위인 ontological-holon으로도 해석하며 설계를 발전시킨다. Rhino Group ID 하나가 하나의 ontological-holon이 될 수 있다. Scene은 의미 단위들이 모여 이루는 장면이자 구현할 프로그램이며, ontological-holon들과 객체들은 이 scene에 등록할 수 있다(`scene_`).

작업 결과와 판단을 기록하고(`plan_`) 피드백을 받아 이전 결정과 현재 조건을 다시 맞춘다. 기존 Plan은 저장된 Step 순서와 기록을 기준으로 이어간다. 각 Step의 작업 객체는 Temp 하위의 별도 레이어에 두고, 다음 Step에도 필요한 객체는 적절한 레이어로 옮긴다.
 설계 의도나 중요한 선택이 불확실하거나 사용자 방향과 충돌하면 근거와 영향을 설명하고 함께 판단한다.

## object attribute data

Rhino User Text나 UserDictionary를 추가·편집하기 전에 `context_01-get_policy` tool의 `policy="metadata"`에서 기존 객체 키를 확인한다.
