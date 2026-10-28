### Grasshopper

| 도구| 입력| 할 수 있는 일|
| --- | --- | --- |
| `list_library`| 선택적 `include_ids`| Grasshopper 로직 목록 조회. |
| `get_logic_by_id`| `logic_id` | 로직 원형·설명 조회. |
| `list_capsules`  | 선택적 `capability`, `audited_only=True`  | 실행 가능한 audited capsule과 입출력 port 확인.  |
| `run_gh_definition` | `capsule_id`, port 계약에 맞는 `inputs`, 선택적 `seed`, `timeout_s` | audited capsule 실행. 정의에 따라 Rhino에 bake할 수 있다. |
