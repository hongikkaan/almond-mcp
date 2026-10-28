### 구조 검토

명시한 부재·재료·하중·지지 조건으로 구조를 검토한다. 응답의 engine·해석 수준을 확인하며, `rule_based/low` 결과는 FEA 결과와 구분한다.

| 도구 | 입력 | 할 수 있는 일 |
|---|---|---|
| `list_design_codes` | 선택적 `include_ids` | 지원 구조 설계 코드 목록 조회.|
| `validate_structure` | 객체 `guids`, 구조 형식·재료·하중·지지·해석 조건 | 구조 검토 실행·이력 기록. 응답의 engine·해석 수준 확인. |
| `visualize_structure`| 대상·해석 조건, 선택적 표시 설정 | 구조 검토 결과를 Rhino 화면에 표시. |
| `export_structural_report` | 선택적 `path`, `limit`  | 구조 검토 이력 보고서 출력.|
