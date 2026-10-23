# 블록과 주석

[AlmondSpatial.cs](../scripts/AlmondSpatial.cs)는 블록과 주석을 읽는 C# 함수 모음이다. 선택·형상·공유 정의를 변경하지 않는다.

## 함수

| 함수 | 반환 |
|---|---|
| `Outline(doc, options)` | 블록 배치·주석·동명 대상의 flat records를 담은 JObject |
| `ResolveBlock(doc, path)` | 현재 선택 가능한 블록 후보의 ID, 이름, definition, 누적 transform과 매칭 기준 |
| `PathObject(doc, path, out parent)` | 지정 경로의 RhinoObject와 그 객체가 속한 부모의 누적 transform |

Outline 예시에서 rootId는 실제 문서 루트 GUID다.

```csharp
var outline = AlmondSpatial.Outline(doc, new Newtonsoft.Json.Linq.JObject {
    ["ids"] = new Newtonsoft.Json.Linq.JArray(rootId.ToString()),
    ["depth"] = 1,
    ["annotations"] = false
});
```

| Outline 옵션 | 의미·기본값 |
|---|---|
| ids | 문서 또는 현재 편집 단계의 루트 GUID 배열 |
| path | [root, child, ...] 한 가지 지정. ids와 함께 사용할 수 없음 |
| scope | ids/path가 없을 때 selected(기본), viewport, document |
| depth | 최대 깊이 0..64, 기본 64. 0은 지정 루트/가지만 반환 |
| include_geometry | 일반 말단의 ID/type/layer/name 포함, 기본 false. geometry dump가 아님 |
| annotations | TextDot과 같은 owner의 동명 대상 포함, 기본 true |
| annotation_layer | 주석 레이어와 하위 레이어 필터. 생략하면 모든 TextDot |
| max_items / max_bytes | 기본 200 records / 48,000 UTF-8 bytes |

viewport는 루트의 가시성과 frustum bbox 범위이며 픽셀 단위 가시성은 아니다. document에는 숨김·잠김 루트도 포함된다. hidden/locked 필드는 개별 멤버의 상태다.

## 반환 데이터와 주석 연결

| record kind / 필드 | 의미 |
|---|---|
| occurrence | instance 이름·definition 이름/ID, path와 누적 transform |
| path | 문서 루트 GUID → 정의 내부 직접 멤버 GUID. 내부 GUID가 현재 선택 가능한 ID라는 뜻은 아님 |
| definition_to_world / geometry_to_world | 정의 좌표→문서 좌표의 4×4 행렬, row-major 16개 값 |
| owner | DOCUMENT 또는 definition ID별 한 번의 직접 멤버 타입 요약 |
| note | owner, TextDot ID·Name·text·point_local. 긴 text는 512자로 제한되며 text_limited 표시 |
| note_target | 같은 owner의 직접 멤버 중 주석과 동일한 비어 있지 않은 Name을 가진 대상 |
| truncated / reason / depth_limited | 레코드·용량·순환·깊이 제한으로 생략된 데이터 표시 |

TextDot끼리 또는 이름 없는 주석과 무명 객체 전체를 연결하지 않는다. 주석은 정의별 한 번만 출력한다. 해당 배치의 주석 좌표는 definition_to_world × [x,y,z,1]로 계산한다. 누적 변환은 **parent transform × InstanceXform**이며 회전·미러·비균일 스케일을 포함한다. 모든 record는 같은 출력 예산을 사용한다.

## BlockEditNew에서 후보 사용

1. Outline의 path에서 루트 GUID 하나만 담은 배열로 ResolveBlock을 호출한다. 반환된 ID를 선택해 _BlockEditNew로 진입한다.
2. 의도한 부모가 열린 상태에서 path의 앞 두 개, 앞 세 개처럼 경로를 늘려 ResolveBlock을 다시 호출한다. definition ID와 누적 transform이 맞는 편집 가능한 후보가 정확히 하나여야 한다.
3. 진입 뒤 실제 편집 객체의 ID를 다시 조회한다. 정의 내부의 과거 member ID와 현재 편집 객체 ID는 구분한다.
4. _BlockSave 또는 _BlockCancel로 한 단계씩 복귀한다. 정의 저장·멤버 교체·배치 변경 뒤에는 관련 path와 ID를 갱신한다.

멤버 GUID는 저장 과정에서 다시 부여될 수 있다. 루트 배치 GUID가 유지돼도 내부 ID·기하 참조·이전 검사 결과가 그대로 유효하다고 가정하지 마라. 기존 semantic ID가 있다면 실제 정의·경로와 대조해 재식별하고, 영향받은 Almond 등록과 검증도 갱신하라. semantic ID의 존재나 자동 연결을 가정하지 마라.

한 항목 path는 정확한 루트 ID를 사용한다. 중첩 매칭은 **editor owner를 증명하지 않으며** editor_owner_verified=false를 반환한다. 같은 정의·transform의 별도 배치가 잘못된 편집 단계에서도 후보로 잡힐 수 있으므로, 의도한 부모 편집 상태를 확인한 뒤 후보를 사용한다. 후보가 0개 또는 복수이면 예외가 발생한다.

BlockEditNew/BlockSave/BlockCancel과 BlockLockHideOutside는 설치된 사용자 명령의 실제 옵션을 따른다. 표준 BlockEdit와 같은 동작이라고 가정하지 않는다. $TempBlockEditUserData$, $block-instance-original-object-id$ 등의 내부 키는 읽는 힌트이며 직접 변경하지 않는다.

중첩 대상 검수에는 isolate + Zoom Selected 확대와 BlockLockHideOutside 인접 관계 캡처를 함께 전달하라. 캡처 전후 편집·가시성 상태를 확인하고, [시각 검수](visual-review.md)에 따라 실제 이미지 내용을 검토하라.

공유 정의를 저장하면 그 정의를 참조하는 다른 배치에도 반영된다. 영향 범위에는 숨김 배치와 다른 정의 내부의 참조도 포함된다. group은 선택 묶음으로, 블록 정의의 재귀와는 구별한다.
