# 지형 단면과 수직선 관찰

[AlmondTerrain.cs](../scripts/AlmondTerrain.cs)의 `Sections(doc, q)`와 `VerticalProbe(doc, q)`는 명시한 문서 객체의 실제 Brep/Mesh를 관찰하고 `JObject`를 반환한다. 두 함수는 객체·선택·뷰·레이어를 변경하지 않는다. Brep, Mesh, Extrusion만 지원하며 블록 정의 내부 멤버와 다른 형식은 `objects[].status`에 별도로 보고한다.

모든 좌표·길이·간격·공차는 **현재 Rhino 문서의 model units**다. 반환의 `model_unit_system`을 확인하라. mm로 자동 변환하지 않는다. `tolerance`를 생략하면 `doc.ModelAbsoluteTolerance`를 사용한다.

## 단면 관찰

```csharp
var result = AlmondTerrain.Sections(doc, new JObject {
    ["ids"] = new JArray(terrainId.ToString(), pavingId.ToString()),
    ["axis"] = "Y",
    ["stations"] = new JArray(0.0, 500.0, 1000.0),
    ["sample_points"] = 8
});
```

`axis`에 수직이고 `stations`에 지정한 문서 좌표를 통과하는 평면으로 각 객체를 자른다. 예를 들어 Y/500은 Y=500 평면이다. Brep는 `BrepPlane` 교차 곡선을 공차 내에서 `JoinCurves`하고, Mesh는 `MeshPlane`의 폴리라인을 사용한다. 각 결과는 곡선 수, 닫힘/열림 수, 길이, bbox를 담는다. `sample_points`를 지정하면 검토용 표본점을 제한적으로 반환한다. Brep의 표본점은 곡선 길이 비율에 따른 점이고 Mesh의 표본점은 원래 꼭짓점의 부분집합이다. 이 점들을 원형상의 정확한 폴리라인으로 취급하지 말라.

| 입력 | 의미·한도 |
|---|---|
| `ids` | 중복 없는 현재 문서의 명시적 GUID 1..128개 |
| `axis` | X, Y, Z. 기본 Z |
| `stations` | 단면 위치 1..256개 |
| `sample_points` | 곡선당 표본점 수. 기본 0, 사용 시 2..64 |
| `max_curves_per_section` | 객체·단면별 상세 곡선 수. 기본 32, 최대 256 |
| `max_output_curves` | 전체 상세 곡선 레코드 수. 기본 512, 최대 4,096 |

`BrepPlane`의 false나 결합 실패는 교차 없음으로 단정하지 않고 `unknown`으로 보고한다. 단면의 닫힌 곡선 수는 단면 영역의 구멍/포함 관계나 솔리드의 유효성을 증명하지 않는다.

## 수직선 관찰

```csharp
var result = AlmondTerrain.VerticalProbe(doc, new JObject {
    ["ids"] = new JArray(terrainId.ToString(), pavingId.ToString()),
    ["xy"] = new JArray(new JArray(100.0, 200.0), new JArray(300.0, 400.0)),
    ["z_min"] = -1000.0,
    ["z_max"] = 5000.0
});
```

`xy`에 지정한 각 위치에서 +Z 방향 선분과 객체를 교차시킨다. Brep는 `CurveBrep`, Mesh는 `MeshLine`을 사용한다. Z값을 정렬하고 공차 내 중복 교차를 제거한다. 유효하고 닫혔으며 manifold인 객체만 교차 사이의 중점을 `IsPointInside`로 검사하여 채워진 Z구간을 반환한다. 열린 형상은 교차점만 보고한다. 닫혔어도 nonmanifold인 형상은 교차점을 보존하면서 구간을 `unknown`으로 남긴다. 경계와 겹치는 선분, 경계 공차 내 중점, 커널 실패도 `unknown`이다.

`objects[].closed`와 `interval_classification_supported`를 구분하라. Brep는 `IsManifold`, Mesh는 `IsManifold(false, out oriented, out hasBoundary)`로 검사하며 `manifold`와 검사 방식을 함께 반환한다. Mesh의 false는 **indexed edges** 검사이고 좌표가 일치하는 꼭짓점을 합친 topological 검사가 아니다. `mesh_manifold_topological_test=false`, `mesh_manifold_edge_mode`, `mesh_oriented`, `mesh_has_boundary`는 이 검사 근거를 기록한다. orientation이나 별도의 topological=true 검사를 추가 필터로 적용하지 않는다.

서로 다른 두 닫힌 객체의 채워진 구간이 공차보다 길게 겹치면 `sampled_overlaps`에 해당 XY·객체 ID·Z구간·깊이를 기록한다. 이 값은 **그 표본선에서 관찰된 중복 구간**이다. 결과가 비어 있어도 전체 형상의 비관입·접합·안전성을 선언하지 말라. 곡선/면의 접촉, 표본 사이의 국소 관입, 열린 지형의 위아래 관계는 별도 검토가 필요하다.

| 입력 | 의미·한도 |
|---|---|
| `xy` | 문서 좌표 `[x,y]` 쌍 1..20,000개. 자동 격자 생성 없음 |
| `z_min`, `z_max` | 둘 다 지정하거나 둘 다 생략. 생략 시 대상 bbox의 Z범위 밖으로 여유를 둠 |
| `max_hits_per_object` | 객체·수직선별 고유 교차 수 한도. 기본 128, 최대 2,048. 초과 시 구간 판정 보류 |
| `max_overlaps` | 중복 구간 상세 반환 수. 기본 256, 최대 4,096 |
| `max_overlap_tests` | 정렬된 객체별 채움 구간의 비교 횟수. 기본 20,000, 최대 100,000 |

지정한 Z범위 안에서만 검사한다. `range_clipped`가 true이면 채워진 구간이 검사 범위 끝에 닿는다. 한쪽 표면과 다른 표면의 높이 차이만 필요하면 열린 형상의 `hit_z`를 함께 읽고 어느 표면을 비교하는지 명시하라.

## 비용·누락·반환 해석

공통 옵션 `max_tests`는 객체×표본 호출 수를 제한한다(기본 20,000, 최대 100,000). `max_results`는 객체×표본 결과 수를 제한한다(기본 256, 최대 4,096). `max_output_points`는 단면 표본점 또는 수직선 교차 Z값·채움 구간 끝점의 전체 반환 수를 제한한다(기본 4,096, 최대 16,384). 수직선에서 반환 예산이 모자라면 해당 객체의 구간 판정은 `unknown`으로 보고한다. 별도 `max_overlap_tests`는 두 객체 구간의 비교량을 제한하며 `overlap_interval_comparisons`에 실행량을 반환한다. 각 개별 Rhino 교차 연산의 시간·메모리를 강제로 중단하는 한도는 아니다.

`objects`에서 누락·미지원·유효하지 않은 입력을, `performed_tests`/`unperformed_tests`에서 실행 범위를, `truncated`/`truncation_reasons`에서 출력·계산 제한을 확인하라. 오류나 생략을 0 또는 통과로 해석하지 말라. 결과의 `global_verdict`는 항상 `not_assessed`다. 대규모 대상은 실제 검토 목적에 맞춰 GUID 범위와 표본 위치를 먼저 좁히고 필요한 예산을 지정하라.
