# 재료 레이어와 최소 메타데이터

`list_materials`에서 재료 ID와 `layer_path`를 확인한 뒤 `assign_material`로 명시한 객체에 적용하라. 라이브러리 조회는 Rhino를 변경하지 않는다. 재료를 실제 적용할 때 해당 재료와 `M::...` 부모·말단 레이어만 생성하거나 재사용한다. 전체 재료 목록의 레이어를 미리 만들지 않는다.

재료 manifest의 `layer_path`가 기준이다. 기존 사용자 manifest에 이 필드가 없으면 `M::<category>::<material_id>`를 사용하며 파일을 다시 쓰지 않는다. 예를 들어 `steel-painted-sage`의 기본 경로는 `M::metal::steel-painted-sage`다. 라이브러리 밖의 직접 지정 재료는 정책에 따라 `M::Custom::<정리된 재료 이름>__<재료 GUID 앞부분>`에 연결한다. 이름 변경은 해당 실행에서 재료 테이블 변경으로 처리된 경우 다음 후처리에 반영된다.

## 적용 범위

Almond의 관리된 `execute_rhino_script` 실행은 새 객체·객체의 직접 재료 변경·재료 테이블 변경을 수집한다. 스크립트가 속성을 모두 설정한 뒤, 같은 Undo 범위를 닫기 전에 최종 재료에 맞춰 대상의 레이어를 정리한다. 실패한 실행은 기존 Undo 복구 규칙을 따른다.

이 처리는 해당 실행에 한정된다. Rhino 시작 시 전체 문서를 재분류하거나 전역 이벤트에서 객체를 즉시 수정하지 않는다. `MaterialFromLayer`·`MaterialFromParent`, 참조 문서 객체와 블록 정의 내부 객체는 자동 후처리 대상에서 제외한다. 루트 블록에 재료를 지정해도 내부의 직접 재료를 덮어쓰지 않는다. 외부 Python/C# 코드로 생성할 때는 아래 공통 속성 팩토리를 사용하라.

Rhino 8의 `CreateHeadless`·`OpenHeadless` 문서는 정적 문서 이벤트를 발생시키지 않아 자동 후처리 범위에 포함되지 않는다([이벤트 규약](https://mcneel.github.io/rhinocommon-api-docs/api/RhinoCommon/html/T_Rhino_EventWatcher.htm)). 해당 문서에서는 공통 `CreateAttributes`·`Apply`를 직접 사용해 재료·레이어 정책을 적용한다.

## 객체에 기록하는 값

공개 키와 내부 참조 이름은 `src/mcp/almond_mcp/modeling_policy.json`을 Python과 네이티브 Bridge가 공유한다.

| 논리 필드 | Rhino UserString | 용도 |
|---|---|---|
| `component_id` | `almond:component_id` | 컴포넌트의 안정적 ID. 컴포넌트 등록 기능이 관리한다. |
| `floor` | `almond:floor` | 사용자가 정한 층 표기. 레이어·Z좌표에서 추정하지 않는다. |
| `construction_detail` | `almond:construction_detail` | 읽을 수 있는 상세·구성 설명. |
| `construction_reference` | `almond:construction_reference` | 선택적 `{"kind":"construction_system","id":"..."}` 참조. 알려진 원본 ID만 허용한다. |
| `material_id` | `almond:material_id` | 실제로 적용한 라이브러리 재료의 export 식별자. |

현재 `construction_system` 원본은 구성 시스템과 예비 설계 지침이며 검증된 개별 시공 상세가 아니다. 출처의 이름을 기본 `construction_detail`로 사용하거나 사용자가 설명을 지정할 수 있다. `construction_detail`만 기록하는 경우 출처가 확인됐다고 간주하지 않는다.

새 할당은 PBR 색·metallic·roughness·opacity와 표시 이름을 객체 UserString에 반복하지 않는다. 이 값은 Rhino 재료 자체에 남는다. 기존 사용자 메타데이터와 자산의 출처·라이선스는 지우지 않는다. 기존 `construction_system` 인자는 위 참조로 정규화하며, 명시적으로 전달한 `structural_role`만 호환성을 위해 기존 키를 유지한다.

재료 팩토리의 추가 `metadata`에는 정책의 `material_assignment_keys`에 있는 floor/detail/reference/structural_role 키만 허용한다. 컴포넌트 소유권·그룹·자산 출처 키를 전달하면 문서 변경 전에 거부한다. `source` 속성에 이미 있는 이 값들은 그대로 보존하며, `material_id`는 전용 재료 인자에 따라 내부에서 기록한다.

`apply_render_material=false`는 현재 재료·레이어·재료 식별자를 유지하고 지정한 floor/detail/reference 등만 기록한다. `attach_metadata=false`는 객체 UserString을 변경하지 않는다. 적용 결과에서 `applied_guids`와 실제 속성이 바뀐 `changed_guids`, 두 메타데이터 적용 플래그를 구분하라. `result_error`나 불명확한 결과는 변경 취소를 뜻하지 않으며 자동 재실행하지 않는다.

## 새 형상의 C#/Python 공통 경로

기하 생성 API는 기존 RhinoCommon을 그대로 사용한다. `ModelingMaterials.CreateAttributes`가 선택한 재료의 속성·레이어만 준비한다. 호출자는 Rhino command 또는 자신의 Undo 범위를 소유해야 한다.

```csharp
using System.Collections.Generic;
using RhinoAlmondBridge;

var metadata = new Dictionary<string, string> {
    [ModelingMetadata.Key("floor")] = "1F",
    [ModelingMetadata.Key("construction_detail")] = "현장타설 콘크리트 벽"
};
var attributes = ModelingMaterials.CreateAttributes(doc, "concrete-smooth", metadata);
var id = doc.Objects.AddBrep(brep, attributes);
```

Rhino 안의 Python도 로드된 동일 Bridge를 사용한다.

```python
import clr
clr.AddReference("RhinoAlmondBridge")
from System import String
from System.Collections.Generic import Dictionary
from RhinoAlmondBridge import ModelingMaterials, ModelingMetadata

metadata = Dictionary[String, String]()
metadata[ModelingMetadata.Key("floor")] = "1F"
attributes = ModelingMaterials.CreateAttributes(doc, "concrete-smooth", metadata)
object_id = doc.Objects.AddBrep(brep, attributes)
```

위 코드는 현재 Rhino 문서 `doc`와 생성할 `brep`가 준비된 호출부에 넣는 예다. 문서 단위와 저장 경로를 먼저 확인한다. 기존 속성을 복제해 사용할 때는 `source` 인자를 전달하며 이름·그룹·관련 없는 UserString을 보존한다. 여러 형상마다 새로운 래퍼 도구를 만들 필요는 없다.

기존 객체에는 `assign_material` 또는 같은 네이티브 `ModelingMaterials.Apply`를 사용한다. `assign_material`은 `modeling_materials=1` capability를 먼저 검사하며, 이전 Bridge로 임의 실행을 우회하지 않는다.
