### 형상 편집·설계 자료

구축 시스템의 구성 요소·재료는 `get_construction_guidance`로 확인한다. 시스템을 하나의 단순 형상으로 표현하면 해당 시스템 레이어에 두고, 실제 부재·마감을 따로 모델링하면 `M::분류::시스템명::요소역할`의 대응 하위 레이어에 둔다. 예를 들어 따로 만든 마감 객체와 구조 객체는 각자의 역할 레이어로 구분한다. 재료명·해시마다 별도 Custom 레이어를 만들지 않는다.

`assign_material`은 지정한 객체의 재료를 바꾸며 레이어는 이동하지 않는다. ByLayer로 표현하려면 객체의 재료·색 source를 ByLayer로 설정하고 해당 레이어의 재료·색을 맞춘다. 개별 재료를 직접 지정하는 방식과 구분해 적용한다. 층 정보는 실제 프로젝트 레벨을 확인해 `floor`에 전달하며 자동 추정되지 않는다. 지원 메타데이터 키는 `get_modeling_policy`에서 확인한다.

| 도구 | 입력 | 할 수 있는 일 |
| ------- | ------- | ----- |
| `execute_rhino_script`| `script` | Rhino 형상·속성을 편집하는 C# 실행. 조회는 앞의 전용 도구를 사용. |
| `get_typology_narrative` | 검색어, 선택적 construction_system·structure_type | 유형·설계 근거의 서술 자료 조회. |
| `search_detail_sources`  | `query` | 구축 상세의 참고 출처 검색. |
| `get_construction_guidance` | 검색어, 선택적 category·material·structure_type·span_m | 구축 시스템·요소·권장 재료와 예비 설계 지침 조회. |
| `get_modeling_policy` | 없음 | 현재 재료·레이어·메타데이터 규칙 조회. |
| `assign_material`  | 객체 `guids`, `material_id`, 선택적 floor·구축 참조·적용 플래그 | 기존 객체에 재료·선택한 메타데이터 적용. 객체 레이어는 유지. |
