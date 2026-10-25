---
name: rhino-almond
description: "Use Almond MCP to inspect, plan, model, register, and verify Rhino architecture. Requires at least one Phase and an actively maintained Plan for each independent task. Read references selectively."
---

# Rhino Almond

Almond MCP는 Rhino 실물 형상, 공간 Scene, 구축·역할·의미의 묶음인 Component, Phase·Plan·Step, 자산·Sheet, 검증을 연결한다. **스크립트 실행 도구로만 취급하지 말고 실제 연결에 노출된 도구와 Bridge capability를 확인한다.**

## 시작과 필수 Phase·Plan

1. COS에서는 `list_connections` → 필요 시 `connect`로 `connection_id`를 얻는다. 저장된 모델을 별도 Rhino에서 시작하라는 요청이면 `start_session`을 사용한다. `project_info`로 모델 binding·`artifact_dir`를, `get_rhino_context`로 **실제 활성 저장 문서·단위·공차·뷰**를 따로 확인한다. COS 호출에는 해당 `connection_id`를 함께 전달한다.
2. **Phase 최소 1개 필수:** `list_generation_phases`로 조회해 적합한 Phase를 재사용한다. 없다면 `create_generation_phase`로 생성한다. 모든 Plan에 해당 `phase_id`를 연결한다. API상 Phase 링크가 선택적이더라도 이 스킬에서는 필수다.
3. **Plan 생성 및 사용 필수:** 새 독립 과업에는 `create_generation_plan(goal, scope, phase_id, ...)`으로 Plan을 만든다. 동일 과업의 연속 작업은 `list_generation_plans`/`get_generation_plan`으로 기존 Plan을 재사용한다. 과거 Plan에 `phase_id`가 없으면 `update_generation_plan`으로 연결한다. 계획만 생성하고 방치하지 않는다.
4. 작업 전 `get_generation_plan`과 `resolve_generation_targets`로 Step·의존성·대상을 읽는다. 단계마다 `update_generation_step`에 실물 결과와 `input_refs`/`output_refs`, 검증 증거를 기록한다. `expected_revision`으로 충돌을 방지한다. Scope별 Step은 고정 템플릿이므로 수행하지 않은 단계를 완료로 꾸미지 않는다. Scene 참조만으로 객체 편집 범위를 늘리지 않는다.
5. 허용된 변경만 수행하고 실제 Rhino·DB·저장·시각 결과를 비교한다. 타임아웃·불명확한 쓰기 응답을 자동 재실행하지 않는다.

Phase·Plan은 진행 조직/검증 기록이며 문서나 공간 자체가 아니다. 상세: [Scene·Component·Phase·Plan](references/components-and-plans.md), [워크플로우](references/workflow.md).

## 데이터 모델과 안전 경계

- **Scene = 특정 공간에서 일어나는 행태·프로그램·장면·가치.** 문서 전체를 Scene 하나로 치환하지 않는다. 같은 문서에 여러 Scene이 있고 Component 하나가 여러 Scene에 참여할 수 있다.
- **Component = 그 장면을 가능하게 하는 구축·역할·의미의 실물 묶음.** 기둥·보가 함께 지지하는 구조, 지지 콘크리트와 목재 마감이 만드는 걸터앉는 마루, 바둑 행위를 가능하게 하는 가구·도구 묶음, 배수관까지 포함하는 지붕처럼 구성한다. 창문·문·기둥 한 개라는 이유로 각각 자동 등록하지 않는다. 반복 형상은 block, 부재·시스템의 선택 묶음은 일반 Rhino group을 활용하고, 모든 하위 group을 Component로 승격하지 않는다. [구성 기준](references/components-and-plans.md#component를-나누는-기준)과 [사용자 설명·사진 원문](references/component-feedback.md)을 먼저 대조한다. 직접 객체 소유자는 하나이고 `object_ids`는 직접 소유 객체, `child_component_ids`는 별도 의미를 가진 직접 자식이다. 수동 group 변경 후 `get_design_component(live=True)`로 대조하고 필요할 때만 `sync_design_component`로 정합한다.
- 편집 대상은 **현재 사용자 승인된 Rhino 문서·해당 .almond 범위**다. Worksession의 **attached/reference 파일은 절대 수정하지 않는다**. 소유 파일·`IsReference`를 확인하고, 무관한 QA 객체·Layout·레이어를 새로 생성하지 않는다.
- **Sheet API ≠ 기존 Layout 메타데이터 전체 목록.** `upsert_drawing_sheet`는 Rhino Layout·detail 생성/갱신용이며 `list_drawing_sheets`는 Almond 등록 Sheet만 반환한다. 기존 PageSpace 도면을 조사·카탈로그화할 때 새 Layout을 생성하지 않는다. [자산·Sheet](references/drawing-assets-and-sheets.md).
- **구축 관계와 실제 관입도 검수한다.** 마감/슬래브·후레싱/벽 등 Component 내부와 인접 요소의 쌓임·접합을 [시각 검수](references/visual-review.md#구축-관계와-중첩)에 따라 확인한다. `get_component_intersections`는 같은 Component 내부 쌍도 검사하지만 block·mesh·상한·`unknown`·`complete=false`·잘림은 무충돌이 아니다. `validate_scene_layout`은 legacy asset-instance AABB 검사다. CRC·ByLayer·소유권 일치만으로 의미 구성·시공성 검수를 완료하지 않는다.

## 참조 지도

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
