# 부재 쌍의 접촉·관입 관찰

[AlmondJoints.cs](../scripts/AlmondJoints.cs)의 `AlmondJoints.AuditPairs(doc, options)`로 명시한 부재 쌍을 읽기 전용으로 조사하라. 반환형은 `JObject`다. 이 코드는 형상 관찰을 제공하며 구조 접합·시공·방수 적합성을 판정하지 않는다.

## 호출

```csharp
var report = AlmondJoints.AuditPairs(doc, new Newtonsoft.Json.Linq.JObject {
    ["pairs"] = new Newtonsoft.Json.Linq.JArray {
        new Newtonsoft.Json.Linq.JArray(chordId.ToString(), braceId.ToString()) },
    ["compare_operations"] = true
});
```

GUID는 현재 문서의 실제 최상위 객체 ID를 사용하라. `Brep`과 `Extrusion`만 지원한다. 블록 배치, 정의 내부 멤버, 메시, 열린 Brep, 잘못된 형상은 `unsupported_input`으로 반환한다. 블록을 검사하려면 배치 경로와 누적 변환으로 문서 좌표의 검사 대상을 먼저 확보하라. 정의 내부 GUID를 최상위 GUID처럼 전달하지 마라.

| 옵션 | 의미 |
|---|---|
| `pairs` | 서로 다른 두 GUID의 배열을 묶은 비어 있지 않은 배열 |
| `tolerance` | 양의 유한값, **문서 단위**. 기본 `doc.ModelAbsoluteTolerance` |
| `compare_operations` | 복제본에 Join/BooleanUnion을 추가 실행해 결과 개수·valid/solid를 관찰. 기본 false |
| `max_pairs` | 한 번에 평가할 쌍 수. 기본 16, 허용 1–64 |
| `max_bytes` | compact JSON 출력의 UTF-8 바이트 예산. 기본 48,000, 허용 4,096–262,144 |

## 결과 해석

`pairs[i].a`와 `.b`에서 입력의 valid/solid/orientation을 확인하라. 안쪽을 향하는 유효 닫힌 Brep은 **복제본만** 뒤집어 계산하며 `flipped_copy=true`를 남긴다. 원본 형상·속성·선택·뷰를 변경하지 않는다.

`pairs[i].overlap`의 `volume_model_units3`는 문서 단위의 세제곱이다. mm 문서에서는 mm³다.

| `overlap.status` | 뜻 |
|---|---|
| `positive_volume` | BooleanIntersection의 유효 닫힌 결과 또는 아래의 union 체적 보존으로 양의 교차체적을 계산함. `method`로 경로를 구분하라 |
| `zero_volume` | 유효한 닫힌 교차 결과의 0 체적을 관찰함. `method=disjoint_bounding_boxes`이면 bbox 분리 하한이 공차보다 커서 교차 연산 없이 0을 판단함 |
| `unknown` | null 반환, 보완 계산으로도 판정하지 못한 빈 교차 결과, 잘못되거나 열린 교차 결과, 체적 계산 실패, 지원하지 않는 입력 등. 체적은 null |

`bbox_distance_lower_bound`는 바운딩박스 사이 거리에서 구한 **실제 형상 사이 거리의 하한**이다. 0이면 bbox가 겹치거나 닿는다는 뜻일 뿐, 실제 형상의 접촉·관입 증거가 아니다. 실제 표면 간격은 계산하지 않으며 `surface_gap=null`, `surface_gap_status=not_measured`로 표시한다.

`join.result_count`와 `boolean_union.result_count`는 선택 옵션의 관찰값이다. Union 1개나 solid=true만으로 올바른 접합을 선언하지 마라. 체적 0도 맞닿음·완전 분리·허용 오차 내 간격·접합 상세의 적합성을 구분하지 못한다. 작은 체적을 공차 기준으로 임의로 0으로 반올림하지 않는다.

bbox가 겹치는 두 solid의 BooleanIntersection이 빈 배열을 반환해도 체적 0으로 바꾸지 마라. 완전히 포함된 닫힌 solid에서도 교차 결과가 누락될 수 있다. 이 경우에만 유효하고 닫힌 outward BooleanUnion 결과로 `V(A) + V(B) − V(A∪B)`를 별도로 계산한다. 결과가 수치 오차 경계보다 크고 작은 입력의 체적을 오차 범위 내에서 넘지 않을 때 `method=boolean_union_volume_balance`로 반환한다. 입력·union 체적은 `operands_model_units3`, 수치 오차 경계는 `numeric_uncertainty_model_units3`에 기록한다. 이 경계는 mass properties의 적분 오차 추정값과 부동소수점 연산 여유이며 Boolean 공차·모델 정확도까지 보장하지 않는다.

null Intersection은 이 보완 경로를 사용하지 않는다. union 실패·잘못된 결과·불확정 체적·0 또는 음의 체적 보존 결과는 모두 unknown이다. 유한 점 표본으로 전체 포함을 증명하거나 미확정 값을 0으로 바꾸지 않는다.

`truncated=true`이면 `truncation_reason`과 `evaluated_pairs`를 확인하고 남은 쌍만 새로 요청하라. 출력 예산은 완전한 쌍 레코드 단위로 적용되므로 계산한 마지막 레코드가 출력에서 생략될 수 있다. 상세 형상이 복잡하면 쌍 수가 적어도 Boolean 연산 비용이 클 수 있다.
