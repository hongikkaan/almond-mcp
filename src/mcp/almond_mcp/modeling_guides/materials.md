### 템플릿·재료·구축 레이어

`setup_modeling`은 재료 라이브러리의 `manifest.json` 레시피로 Rhino 재료를 등록하고, 구축 시스템에 맞는 레이어·기본 재료·색을 준비한다. 재료 준비는 `operation="materials"`, 레이어 준비는 `operation="layers"`로 실행한다. 재료 ID나 레시피가 필요하면 `list_materials`로 조회한다.

| 도구 | 입력 | 할 수 있는 일 |
|---|---|---|
| `setup_modeling` | `operation="materials"` 또는 `"layers"`; materials에만 선택적 `overwrite` | PBR 재료 일괄 등록 또는 `M::category::system.name::element.role` 레이어·기본 재료·색 준비. |
| `list_materials` | 선택적 `category`, `query` | 재료 ID·이름·PBR 레시피 조회.|
