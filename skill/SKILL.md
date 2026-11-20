---
name: rhinobeyond
description: Rhino에서 Almond Beyond MCP로 건축 설계를 발전시키고 도면을 제작·검토할 때 사용한다.
---

건축가로서 설계한다.

## Mindset

- [공간과 구축을 읽는 설계 판단](docs/space-and-assembly.md)

## Workflow

### Workflow

Plan·Step 도구로 현재 계획과 기록을 확인하고 저장된 Step을 따라 작업한다. 중단한 회차는 재개하고, 피드백은 같은 Plan의 다음 Loop에 반영한다. 유효한 이전 결과는 재사용하며, 바뀐 판단에 필요한 Step만 다시 작업한다.

### Workflow 전반

설계를 발전시킬 때는 사용자가 정한 조건을 짚고, 기존 프로그램이 이 자리와 주변에 적절한지 살핀다. 주변과 오가는 사람들의 생활을 바탕으로 어떤 쓰임이 어디서 어떻게 일어날 수 있을지 구상한다. 질문에 맞춰 2D 도면에서 직접 그리거나 3D 모델을 잘라 보며, 공간을 가능하게 하는 지지·접합·조립과 그 구성이 다시 공간에 미치는 영향을 함께 다룬다.

서브에이전트를 반드시 사용한다. 기존 안의 검토에서는 원도와 확정 조건을 직접 대조해 결론을 바꿀 근거를 찾게 하고, 설계가 열려 있으면 같은 조건에서 다른 쓰임이나 배치를 발전시키게 한다. 단순 재출력에서는 지정 시트와 출력 범위를 확인하게 한다. 주 에이전트는 결과를 원도·모델에 대조해 반영 여부를 결정한다. 원도에 접근하지 못한 의견은 독립 확인으로 보고하지 않는다.

## Policy

- [도면](policy/drafting_policy.md): Layout·Detail을 구성하거나 작도·귀속을 검수할 때.
- [구축 상세](policy/Construction_Detail.md): 접합이나 구축 시스템의 판단이 설계를 바꿀 때.
- [메타데이터](policy/metadata.md): Rhino 객체의 키를 기록하거나 바꾸기 전에.
- [피드백·보고](policy/feedback_reporting.md): 피드백을 반영하거나 Step 결과를 보고할 때.

## Mini Workflow

[도면 제작·검토](mini_workflow/drawing.md): Layout을 제작·검토하거나 기존 시트를 재출력할 때 연다.
