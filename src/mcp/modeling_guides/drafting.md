### 도면 표현

기존 Layout·PageSpace·Detail을 기준으로 필요한 도면을 편집한다. Sheet DB 등록 기능은 현재 제공하지 않는다.

2D 곡선이 재귀 Explode로 선분이 됐다면 같은 실물·표현 역할의 연속 선분을 식별하고 Join 필요성을 판단한다. 문서 공차·끝점·열림/닫힘·분기·중복을 확인하고, 결과의 곡선 수·형태와 비대상 선 보존을 대조한다. 근접한 선 전체를 일괄 Join하거나 개폐 궤적을 문짝 윤곽에 섞지 않는다. 전용 Join 도구는 없으므로 현재 일반 스크립트의 변경 경로를 사용하고 결과를 확인한다.

| 도구| 입력 | 할 수 있는 일|
| --- | ---- |  |
| `list_drawing_recipes` | 선택적 `include_ids` | 도면 표현 recipe 목록 조회. |
| `get_drawing_recipe`| `recipe_id` | recipe의 레이어·색·선종류·출력두께 조회.|
| `apply_drawing_style`  | `recipe_id` | recipe에 따른 Rhino 도면 레이어·출력 속성 적용. |
| `import_drawing_hatch_patterns` | `asset_id`  | 선택한 해치 패턴을 문서로 가져오기.  |

### 도면 검수

뷰 목록에서 Layout GUID를 골라 용지와 Detail을 캡처한다. 용지 크기·축척·선두께·선종류·해치·문자와 치수의 가독성·잘림을 확인한다. 정적 도면의 축척은 이름으로 추정하지 않는다. 파일을 출력했다면 출력본도 열어 확인하고 수정한 부분을 다시 검수한다.
