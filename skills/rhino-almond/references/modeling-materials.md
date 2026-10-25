# 재질·구축 레이어와 최소 메타데이터

재질 준비는 `setup_modeling(operation="materials")`로 라이브러리를 한꺼번에 등록하고, 이후 Rhino에 등록된 재질을 사용하라. 재질마다 별도로 등록하거나 적용 전에 매번 목록을 조회할 필요는 없다. MCP로 특정 객체에 재질을 지정할 때는 `assign_material`을 사용하고, 재료 ID나 PBR 레시피 확인이 필요할 때만 `list_materials`를 조회한다. **`assign_material`은 기존 객체의 레이어를 보존한다.** 재질에 따른 자동 레이어 이동이나 실행 후 재분류는 없다.

## 명시적인 준비 작업

`setup_modeling`은 Bridge `modeling_materials=2`를 확인한 뒤 한 Undo 범위에서 아래 작업을 수행한다. 일반 재질 할당이나 스크립트 실행이 이 준비 작업을 자동 호출하지 않는다.

| 호출 | 실제 효과 |
|---|---|
| `setup_modeling(operation="materials", overwrite=...)` | 라이브러리의 읽을 수 있는 이름으로 PBR 재질을 등록한다. 같은 이름의 기존 재질은 `overwrite=true`면 PBR 값을 갱신하고, `false`면 보존한다. 생략하면 Rhino에서 Yes/No를 한 번 선택하며 Cancel은 변경하지 않는다. |
| `setup_modeling(operation="layers")` | 구축 라이브러리에서 `M::category::system.name::element.role` 레이어를 생성·재사용하고 재질·표시색·출력색을 설정한다. 기존 객체는 이동하거나 메타데이터를 기록하지 않는다. `overwrite`는 이 작업에 적용되지 않는다. |

구축 레이어의 기본 재질은 시스템의 첫 `render_material_ids` 레시피다. connection/reinforcement/decking은 galvanized steel, Wood의 subfloor/sheathing은 birch plywood를 쓰는 현재 구현의 기본값이며, manifest가 제공하는 역할별 매핑이라고 간주하지 않는다. 컨테이너 레이어는 회색이다. 기존 레이어의 색·재질도 갱신하므로 사용자가 요청한 준비 범위에서 실행한다. 재질 manifest의 과거 `layer_path`는 객체 레이어 결정에 사용하지 않는다.

**Worksession에서는 재료의 공유 사용처도 보호한다.** 현재 helper는 이름이 같은 참조 RenderMaterial까지 찾을 수 있어 `overwrite=true`가 참조의 메모리 재료를 바꾼 사례가 있다. attached 디스크 파일을 저장하지 않았다는 것만으로 보호를 확인하지 마라. 참조와 동명·공유된 재료를 덮어쓰지 말고 기존 값을 보존하는 준비 경로와 로컬 전용 재료·연결을 확인한다. 안전한 분리를 확인할 수 없는 변경은 해당 범위를 미완료로 남기며 참조 재료를 임의로 고쳐 해결하지 않는다. 재료명·도구 성공 응답과 실제 PBR 채널·레이어 기본 재료 identity·저장 재읽기를 구별한다.

## 단순·상세 표현과 ByLayer

단순 형상은 해당 `M::category::system` 레이어에, 실제로 분리된 상세 부품은 알맞은 `element.role` 하위 레이어에 둔다. 단순 덩어리 한 개를 상세 레이어에 옮긴 것만으로 상세 모델링이 되지는 않는다. 레이어 구조 준비와 상세 형상의 생성·교체·복원은 별개이며, 별도 대체 형상·전환 기능을 구현하지 않았다면 자동 LOD 전환 완료라고 보고하지 않는다.

사용자가 전체 속성 ByLayer를 요청하면 재료·색·선종류·출력색·출력두께·지원되는 단면 속성의 source와 레이어 기본값을 함께 확인한다. `assign_material`의 객체 직접 재료 할당을 ByLayer 완료로 오해하지 않는다. 블록 occurrence의 속성과 정의 내부 ByLayer/ByParent의 실제 표현도 구별한다. 참조·공유 정의의 속성은 허용 범위 밖에서 변경하지 않는다.

재료명·해시로 `Custom::<material>` 같은 레이어를 새로 만들지 않는다. 사진에 남은 기존 레이어는 [원문 사례](component-feedback.md)를 참고하고 실제 객체·블록 정의·숨김·참조 사용처와 현재 로드된 구현을 확인한다. 과거 레이어가 있다는 이유만으로 현재 자동 생성이 계속된다고 단정하거나 사용자 레이어를 일괄 삭제하지 않는다.

## 적용 범위

`assign_material`은 기존의 편집 가능한 객체 GUID를 명시해 재질과 선택한 메타데이터를 적용한다. 참조 객체와 블록 정의 내부 객체는 대상에서 제외된다. 루트 블록의 재질은 내부의 by-parent 형상에 적용되며 내부 객체의 직접 재질을 덮어쓰지 않는다.

Rhino 시작·재질 이름 변경·`execute_rhino_script` 종료 시 재질을 근거로 객체를 재분류하지 않는다. 새 객체는 호출자가 지정한 레이어를 사용한다. 기존 객체에 `assign_material`을 호출하면 기존 MaterialFromLayer/MaterialFromParent 설정도 명시적인 객체 재질로 바뀔 수 있지만 레이어는 유지된다.

외부 Python/C# 코드와 headless 문서에도 자동 재질·레이어 후처리는 없다. 필요한 재질은 아래 공통 속성 팩토리로 명시하고, 레이어는 별도로 지정한다. 수정 호출의 오류·타임아웃은 변경 취소를 뜻하지 않으므로 자동 재실행하지 않는다.

## 객체에 기록하는 값

아래 표는 **현재 구현의 저장 계약**이다. 공개 키와 내부 참조 이름은 `src/mcp/almond_mcp/modeling_policy.json`을 Python과 네이티브 Bridge가 공유한다. 사용자 최신 [피드백 원문](component-feedback.md)의 키 간소화 요구와 아직 다른 부분이 있다. 스킬 지침만으로 기존 소유권 키·`component_record`를 지우거나 이름을 바꾸지 않는다.

| 논리 필드 | Rhino UserString | 용도 |
|---|---|---|
| `component_id` | `almond:component_id` | 컴포넌트의 안정적 ID. 컴포넌트 등록 기능이 관리한다. |
| `floor` | `almond:floor` | 프로젝트 층 기준을 확인해 파악한 층 표기. 빈 값이면 기준 레벨·도면·현재 형상과 대조해 기입한다. Z좌표 하나만으로 확정하지 않으며 다층 부재·근거 부족은 불명확한 범위로 남긴다. |
| `construction_detail` | `almond:construction_detail` | 읽을 수 있는 상세·구성 설명. |
| `construction_reference` | `almond:construction_reference` | 선택적 `{"kind":"construction_system","id":"..."}` 참조. 알려진 원본 ID만 허용한다. |
| `material_id` | `almond:material_id` | 실제로 적용한 라이브러리 재료의 export 식별자. |

현재 `construction_system` 원본은 구성 시스템과 예비 설계 지침이며 검증된 개별 시공 상세가 아니다. 출처의 이름을 기본 `construction_detail`로 사용하거나 사용자가 설명을 지정할 수 있다. `construction_detail`만 기록하는 경우 출처가 확인됐다고 간주하지 않는다.

새 할당은 PBR 색·metallic·roughness·opacity와 표시 이름을 객체 UserString에 반복하지 않는다. 이 값은 Rhino 재료 자체에 남는다. 기존 사용자 메타데이터와 자산의 출처·라이선스는 지우지 않는다. 기존 `construction_system` 인자는 위 참조로 정규화하며, 명시적으로 전달한 `structural_role`만 호환성을 위해 기존 키를 유지한다.

사용자는 `material_id` 제외·`almond` prefix 제거·레이어에서 알 수 있는 `construction_detail` 제외·빈 값이라도 `Scene_id` 포함·`structural_role` 대신 `role`·`type` 검토를 요구했다. 이는 공개 표시와 내부 영속 데이터·API·export의 호환 이행을 함께 다룰 **개발 항목**이다. 현행 API가 계속 쓰는 필드를 이미 제거된 것처럼 설명하거나 임의의 새 키로 중복 기록하지 않는다. `component_record`는 현재 group GUID·이름·Scene·자식 관계의 Undo/저장 복구를 위한 내부 맵이다. Scene은 여러 개일 수 있어 단일 Scene 문자열로 덮어쓰지 않는다. 층 확인과 불필요한 사용자 이름·수동 중복 메타데이터 추가를 줄이는 운영 개선부터 적용한다.

재료 팩토리의 추가 `metadata`에는 정책의 `material_assignment_keys`에 있는 floor/detail/reference/structural_role 키만 허용한다. 컴포넌트 소유권·그룹·자산 출처 키를 전달하면 문서 변경 전에 거부한다. `source` 속성에 이미 있는 이 값들은 그대로 보존하며, `material_id`는 전용 재료 인자에 따라 내부에서 기록한다.

`apply_render_material=false`는 현재 재료·레이어·재료 식별자를 유지하고 지정한 floor/detail/reference 등만 기록한다. `attach_metadata=false`는 객체 UserString을 변경하지 않는다. 적용 결과에서 `applied_guids`와 실제 속성이 바뀐 `changed_guids`, 두 메타데이터 적용 플래그를 구분하라. `result_error`나 불명확한 결과는 변경 취소를 뜻하지 않으며 자동 재실행하지 않는다.

## 새 형상의 C#/Python 공통 경로

기하 생성 API는 기존 RhinoCommon을 그대로 사용한다. `ModelingMaterials.CreateAttributes`의 두 번째 인자는 **material_id 문자열이 아니라 재질 레시피 JSON**이다. `list_materials`의 `materials`에서 선택한 한 재질 객체를 JSON 문자열로 전달한다. MCP가 레시피를 검증·선택하며 네이티브 helper는 라이브러리를 직접 읽지 않는다. 가능하면 기존 객체에는 공개 `assign_material`을 사용한다.

아래 예제는 현재 문서 `doc`와 생성할 `brep`, 선택한 레시피 JSON 문자열 `recipeJson`(Python에서는 `recipe_json`)이 준비된 호출부에 넣는다. `source`가 있으면 속성을 복제해 레이어·이름·그룹·무관한 UserString을 보존하고, 없으면 현재 레이어를 사용한다. 다른 레이어로 생성하려면 반환 속성의 `LayerIndex`를 호출자가 지정한다. 호출자는 Rhino command 또는 자신의 Undo 범위를 소유해야 한다.

```csharp
using System.Collections.Generic;
using RhinoAlmondBridge;

var metadata = new Dictionary<string, string> {
    [ModelingMetadata.Key("floor")] = "1F",
    [ModelingMetadata.Key("construction_detail")] = "현장타설 콘크리트 벽"
};
var attributes = ModelingMaterials.CreateAttributes(doc, recipeJson, metadata);
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
attributes = ModelingMaterials.CreateAttributes(doc, recipe_json, metadata)
object_id = doc.Objects.AddBrep(brep, attributes)
```

문서 단위와 저장 경로를 먼저 확인한다. 같은 이름의 일반 재질은 레거시 `ALMOND::<material_id>` 이름도 호환 재사용한다. 라이브러리 자산의 해시별 레시피는 내부 호출에서 `reuseLegacyMaterial=false`로 정확한 이름만 재사용한다. 자산의 이름·해시를 임의로 바꿔 이 분리를 우회하지 않는다.

기존 객체에는 `assign_material` 또는 같은 네이티브 `ModelingMaterials.Apply`를 사용한다. 네이티브 `Apply`의 두 번째 인자도 레시피 JSON이다. `assign_material`과 `setup_modeling`은 `modeling_materials=2` capability를 먼저 검사하며, 이전 Bridge로 임의 실행을 우회하지 않는다.
