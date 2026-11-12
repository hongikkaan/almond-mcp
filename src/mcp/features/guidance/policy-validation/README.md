# Plan 흐름 기반 policy 검증

이 문서는 policy 작성·개선의 검토 근거다. 런타임 지침 원본은 [BASIC](../../../BASIC-INSTRUCTIONS.md)과 [활동별 policy](../policies)이며, 검토 시나리오는 `context_01-get_policy` tool의 반환 본문과 standalone wheel에 포함하지 않는다. 저장소·sdist에는 오프라인 검토와 문서 정합성 검사를 위해 보존한다.

## 검토 전제와 범위

Almond MCP의 설계·모델링·도면·검수 작업이 Plan 템플릿에 정해진 Step을 따라 이루어진다는 전제에서 검토한다. 먼저 각 템플릿의 전체 Step 순서를 확인하고, 각 Step에서 사용하는 도구의 DESCRIPTION·입력 schema·출력·Next Step Guide를 연결한다. 개별 도구의 좋은 설명만으로 후속 단계의 판단까지 충족된다고 가정하지 않는다.

실제 원본은 [Plan 생성](../../planning/store.py), [공개 요청 모델](../../planning/requests.py), [공개 출력](../../../output_contracts.py), [후속 안내](../../../tool_guidance.py), 각 기능의 `tools.py`·`tools-explain.md`와 [도구 명세](../../../../../tool_description_spec.md)다. 저장된 Plan은 사용자 scope 매핑과 이전 템플릿을 보존하므로 실제 작업에서는 조회한 Step 목록이 우선한다.

아래 세 문서는 내장 11개 템플릿의 66개 Step을 모두 순서대로 추적하고, 각 템플릿에 정상·실패/미확인·피드백의 Given–When–Then 시나리오를 둔다. ‘실패’는 기술 오류뿐 아니라 근거 부족이나 잘못된 범위 해석도 포함한다. 도구 응답은 현재 계약에서 구성한 가정이며 실측 응답이 아니다.

| 검토 문서 | 템플릿 | Step | 시나리오 |
|---|---|---:|---:|
| [설계·의미 흐름](design-flows.md) | spatial_development, plan_editing, semantic_exploration | 17 | 9 |
| [상세·수정·검수 흐름](execution-flows.md) | construction_detail, model_revision, inspection | 17 | 9 |
| [기존 범용 흐름](legacy-flows.md) | house, interior, structure, drawing, component | 32 | 15 |

## policy에 남긴 판단과 기존 계약의 담당

| 남는 판단 | 원본 | 기존 안내와 다른 점 |
|---|---|---|
| 앞 Step의 근거를 현재 조건에 가져갈 수 있는지, 피드백이 어느 판단을 다시 여는지 | BASIC의 Plan 흐름 | Loop 시작·재개 인자를 다시 설명하지 않고 회차와 재검토 범위를 고르는 기준을 보완 |
| 의미 경계와 물리 변경 범위, 충돌 해결 후 다시 확인할 공간·공유 관계 | spatial_modeling SM1–SM3 | Scene/Holon CRUD·block·trim 동작을 재정의하지 않고 요청과 보존 조건을 다음 변경에 연결 |
| 관찰 기준, 서로 다른 대상·시점·표현의 근거 적합성, 후속 변화에 따른 재검수 | observation OB1–OB3 | 페이지·미지원·timeout 처리법은 도구 계약에 두고 확인 가능한 주장과 다음 판단을 결정 |
| 2D 원본·모델 파생물·주석의 관계, 재생성의 보존 의도, 검수 뒤 Layout/출력의 영향 | drawing DR1–DR3 | PlanSection·캡처의 인자나 반환 필드를 복제하지 않고 전달물의 설계적 일치 판단을 보완 |
| 추상 목표를 공간 차이로 표현하고 비교 조건을 맞추기, 피드백의 전제 변화 | design_exploration DE1–DE3 | 표현 도구 실행법 대신 안을 구상·비교하며 다음 판단에 넘길 내용을 구체화 |
| 질문·그림·조건의 동시 전달, 답변의 적용 범위, 최종 결과·정리 자료의 보존 | feedback_reporting FR1–FR3 | 채널별 전송법이나 Plan 완료 권한을 다시 만들지 않고 사용자에게 전달되는 의미와 근거를 연결 |

재조회·실행 완료 회수·불명확한 수정의 재실행 금지·기하 검사의 지원 범위·Step 기록과 사용자 Plan 완료는 이미 도구/실행기 안내가 담당한다. 시나리오에서 필요하면 사용하되 새 policy가 처음 만든 규칙으로 계산하지 않는다. policy를 읽기 위한 새 Plan이나 매번 받는 승인을 추가하지 않는다.

## 이전 Notion 초안의 재검토

[BASIC 역할 초안](https://app.notion.com/p/412e0a394120816493fcc5b45a8f8afa)과 아래 다섯 초안의 본문을 현재 소스와 대조했다. 연결된 과거 실행 로그를 판단의 기준으로 다시 읽지 않았다. 예전 도구명, 고정 출력 수치, 특정 프로젝트의 기하 조건은 새 policy로 옮기지 않았다.

| 초안 | 이번 처리 |
|---|---|
| [공간 구성·모델링](https://app.notion.com/p/412e0a39412081f1ab8bcd3afb2ef6cc) | BASIC의 건축 요소·group/block 정의를 유지하고, 의미 등록에서 물리 변경으로 넘어가는 범위와 후속 변경 영향에 집중 |
| [관찰·검수](https://app.notion.com/p/412e0a3941208194b4e6c28523e983a1) | 실제 이미지를 읽는 태도는 BASIC에 유지; 표시 모드·복구 호출 규칙은 각 도구에 남기고 근거 결합·유효성 판단을 보완 |
| [도면 작성·관리](https://app.notion.com/p/412e0a39412081e593a2f01694e80230) | PlanSection 수치·호출 계약을 제외하고, 순수 2D/모델 파생물·수동 편집과 최종 Layout/출력 검수를 연결 |
| [설계 구상·시각적 소통](https://app.notion.com/p/412e0a39412081b29f78ebd383073e10) | 활동별 핵심은 유지하되 Plan의 대안 구상·후속 적용·피드백 재검토 연결로 정리 |
| [피드백 요청·최종 보고](https://app.notion.com/p/412e0a39412081cdac5cd01228d8b3b2) | 비교 표현 규칙은 design_exploration에 모으고, 결정에 필요한 자료의 전달·답변 범위·정리의 증거 보존을 담당 |

## 검증 방법과 해석 한계

1. 시나리오에서 다음 Step이 소비할 입력과 근거를 먼저 확인한다. 기존 안내만으로 결정되는 부분과 남는 판단을 구분한다.
2. 새 policy를 적용해 정상 흐름, 잘못된 근거/실패, 피드백의 다음 행동이 일관되는지 정적 walkthrough로 검토한다. 기준 미확인을 임의의 통과값으로 바꾸는 공백을 OB1에 보완하고, FR1의 비교 자료는 해당 결정에 필요한 범위로 한정했다.
3. `test_policy_walkthroughs.py`는 문서의 Step 순서·종류·템플릿 범위를 실제 일회용 저장소에서 생성한 Plan과 대조한다. Planning README의 공개 Step 표도 같은 순서와 대조한다. 이 검사는 문서가 구현에서 이탈하는 것을 잡으며 문장의 설계 효과를 자동 판정하지 않는다.
4. Get Policy 검사는 공개 선택지와 반환 목록·원본 파일·본문·해시·버전, standalone/문서 연결/외부 경로 schema, wheel·sdist 포함을 확인한다. 기존 네 선택값의 반환 구조와 기본값은 유지한다.

정적 walkthrough의 일관성, 오프라인 계약 검사, 실제 Rhino 기능 검증과 에이전트의 설계 판단 개선은 별도의 근거다. 이번 검토는 앞의 두 범위이며 Rhino를 실행하거나 실제 모델을 바꾸지 않는다. 향후 실사용 결과가 다르면 이 시나리오의 가정과 정책 문구를 함께 갱신한다.
