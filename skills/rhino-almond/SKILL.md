---
name: rhino-almond
description: "Use Almond MCP to inspect, plan, model, register, and verify Rhino architecture. Requires at least one Phase and an actively maintained Plan for each independent task. Read references selectively."
---

# Rhino Almond

Almond MCP는 Rhino 실물 형상, 공간 Scene, 구축·역할·의미의 묶음인 Component, Phase·Plan·Step, 자산·Layout, 검증을 연결한다. **스크립트 실행 도구로만 취급하지 말고 실제 연결에 노출된 도구와 Bridge capability를 확인한다.**

## 시작과 필수 Phase·Plan

1. 프로젝트·현재 문서 정보가 필요할 때 `project_info`에서 필요한 sections만 조회한다. 기본 document 항목이 실제 열린 문서를 같은 호출에서 확인하므로 live 확인을 위해 `get_rhino_context`를 추가 호출하지 않는다. 매 과업마다 시작 확인 두 도구를 반복하는 절차는 없다. 선택·카메라 정보가 필요할 때만 `get_rhino_context(sections=["selection"] 또는 ["viewport"])`를 쓴다.
2. **Phase 최소 1개 필수:** 기존 Phase를 재사용하거나 생성한다. ID가 필요하면 `list_phases(include_ids=True)`를 쓴다. Phase의 `file_name`은 미기입 시 빈 문자열인 기록값이며 파일을 이동하지 않는다.
3. **Plan 생성 및 사용 필수:** 새 독립 과업은 `create_plan`으로, 재개는 `list_plans(include_ids=True)`/`get_plan`으로 기존 Plan을 재사용한다. `depends_on`에는 다른 Phase의 Plan이나 Phase ID도 배열로 자유롭게 기록한다. 관련성 기록이며 선행 완료·실행 순서 조건이 아니다.
4. `set_working_plan(plan_id, step_id)`으로 작업자료 폴더를 선택·재사용한다. worker는 상대경로만 전달한다. Python은 `execute_project_python`, Rhino C#은 `RhinoAlmondBridge.ManagedFiles.Input/Output`을 쓴다. 폴더는 `tmp/YYMMDD_작업명`이며 `rename_artifact_folder`로 바꿀 수 있다. 유용한 자료는 Plan의 `artifact_refs`와 Step의 `input_refs`/`output_refs`에 기록한다.
5. **작업 중단·전환·재개는 정상이다.** 필요하면 Plan·Step을 `paused`로 기록하고 다른 작업을 한다. 미수행 Step을 completed로 꾸미거나 모든 작업을 선형적으로 끝내려 하지 않는다. `expected_revision`으로 기록 충돌을 막고, 사용자 승인 범위의 실제 결과·검증 근거를 기록한다. Scene 참조만으로 편집 범위를 늘리거나 불명확한 쓰기를 자동 재시도하지 않는다.

Phase·Plan은 진행 조직/검증 기록이며 문서나 공간 자체가 아니다. 상세: [Scene·Component·Phase·Plan](references/components-and-plans.md), [워크플로우](references/workflow.md).

## 데이터 모델과 안전 경계

- **Scene = 특정 공간에서 일어나는 행태·프로그램·장면·가치.** 문서 전체를 Scene 하나로 치환하지 않는다. 같은 문서에 여러 Scene이 있고 Component 하나가 여러 Scene에 참여할 수 있다.
- **Component = 그 장면을 가능하게 하는 구축·역할·의미의 실물 묶음.** 기둥·보가 함께 지지하는 구조, 지지 콘크리트와 목재 마감이 만드는 걸터앉는 마루, 바둑 행위를 가능하게 하는 가구·도구 묶음, 배수관까지 포함하는 지붕처럼 구성한다. 창문·문·기둥 한 개라는 이유로 각각 자동 등록하지 않는다. 반복 형상은 block, 부재·시스템의 선택 묶음은 일반 Rhino group을 활용하고, 모든 하위 group을 Component로 승격하지 않는다. [구성 기준](references/components-and-plans.md#component를-나누는-기준)과 [사용자 설명·사진 원문](references/component-feedback.md)을 먼저 대조한다. 직접 객체 소유자는 하나이고 `object_ids`는 직접 소유 객체, `child_component_ids`는 별도 의미를 가진 직접 자식이다. 수동 group 변경 후 `get_design_component(live=True)`로 대조하고 필요할 때만 `sync_design_component`로 정합한다.
- 편집 대상은 **현재 사용자 승인된 Rhino 문서·해당 .almond 범위**다. Worksession의 **attached/reference 파일은 절대 수정하지 않는다**. 소유 파일·`IsReference`를 확인하고, 무관한 QA 객체·Layout·레이어를 새로 생성하지 않는다.
- **도면·Sheet DB 등록 기능은 제거됐다.** 기존 Layout과 도면 파일은 유지된다. 뷰 목록·캡처는 `get_rhino_viewport_image(view="a")`와 반환 GUID를 사용한다. 등록 장부를 만들기 위해 Layout을 생성하지 않는다.

- **구축 관계와 실제 관입도 검수한다.** 마감/슬래브·후레싱/벽 등 Component 내부와 인접 요소의 쌓임·접합을 [시각 검수](references/visual-review.md#구축-관계와-중첩)에 따라 확인한다. `get_component_intersections`는 같은 Component 내부 쌍도 검사하지만 block·mesh·상한·`unknown`·`complete=false`·잘림은 무충돌이 아니다. `validate_scene_layout`은 legacy asset-instance AABB 검사다. CRC·ByLayer·소유권 일치만으로 의미 구성·시공성 검수를 완료하지 않는다.

## 참조 지도

아래 도구 선택표는 순차 작업표가 아니다. 현재 과업의 Phase·Plan 기록을 재사용하면서, Scene·재료 등 필요한 조회와 이번 과업의 도구만 골라 사용한다.

| 목적 | 참조 |
|---|---|
| 공개 MCP 도구·입출력·지원 범위 | [도구 선택](references/tool-map.md) |
| Scene·Component 계층, Phase·Plan·revision | [Scene·Component·계획](references/components-and-plans.md) |
| 등록 3DM·파생 도면, Sheet와 기존 Layout 차이 | [자산·Sheet](references/drawing-assets-and-sheets.md) |
| 작업·변경·오류·검증 근거 | [워크플로우](references/workflow.md) |
| viewport·clipping·평면·단면 검수 | [시각 검수](references/visual-review.md) |
| 고정 probe·C# 실행·Undo/반환 한계 | [Probe](references/probe-tools.md) |
| 블록·TextDot / 지형 / 접합 | [블록](references/blocks-and-notes.md) · [지형](references/terrain-probes.md) · [접합](references/joint-probes.md) |
| 재료·메타데이터·레이어 | [재료](references/modeling-materials.md) |

## 검증과 보고

모델 검수는 [시각 검수](references/visual-review.md)의 필수 순서를 지킨다. 실제 눈높이 Perspective의 여러 위치·Named View·복수 Display Mode를 먼저 확인하고, 실제 clipping 평면·종횡단면을 이어서 검토한 뒤 수치 결과와 대조한다. `get_rhino_viewport_image`의 **실제 이미지**를 열어야 한다. 이 도구는 뷰·clipping을 설정하지 않으므로 PageSpace와 ModelSpace/Detail, 카메라를 구분하고 캡처 성공만으로 절단을 검증했다고 하지 않는다. 1000 mm 간격 종·횡·Z **전면검수는 사용자 지시가 있을 때만** 수행한다.

설계 논의·크리틱·고찰에는 사용자가 금지하지 않았고 도구가 지원하면 읽기 전용 독립 검토를 수행한다. Rhino·DB 변경 권한은 주 담당자에만 둔다. 의사결정·질문·장애·최종 결과 위주로 보고하고 사용자가 정한 Slack 채널·스레드·멘션을 준수한다. **완료 근거, `unknown`/미지원 사항, Plan의 최신 단계 상태**를 구분한다.
