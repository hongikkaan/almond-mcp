# 도면 스타일 레시피

표준 수동 2D 레이어 전체는 `drawing_01-apply_style` tool에 `{}`를 전달해 바로 적용한다. 한 용도만 필요하면 같은 도구의 `layer_path` 선택지에서 고른다. 예를 들어 `{"layer_path":"D::Line::Hidden"}`은 숨은선 레이어와 표준 상위 선 레이어를 준비한다. 작도할 객체의 선종은 ByLayer로 지정한다.

## A4 평면·단면 스타일 적용

한 층의 평면이나 국소 단면을 1:100 A4 가로 도면으로 검토하는 예다. 한 공간을 상세하게 보려면 1:50, 동과 동 사이 관계를 보려면 1:200을 레시피의 권장 축척으로 참고한다.

1. `drawing_05-list_recipes` tool에 `{"include_ids":true}`를 입력하고 **Architectural Plan and Section A4**의 `recipe_id`를 확인한다.
2. `drawing_02-get_recipe` tool에 다음 인자를 입력한다.

   ```json
   {"recipe_id":"architectural_plan_section_a4","field_groups":["scales","parameters"]}
   ```

   `recommended_scales`, `layers`, `output`을 확인한다. 절단선 `Drawing::SECTION`은 0.5 mm, 윤곽선 `Drawing::PROFILE`은 0.35 mm, 보이는 선 `Drawing::elevation`은 0.09 mm다.
3. 작업할 Rhino 문서에 연결하고 `drawing_01-apply_style` tool에 `{"recipe_id":"architectural_plan_section_a4"}`를 입력한다. 이 레시피는 `Drawing` 아래의 A4 전용 레이어와 공통 `D` 레이어를 함께 준비한다. 표준 D 정의가 기존 문서와 충돌하면 변경 전에 중단하며, 충돌한 정의를 교체할 때는 `overwrite=true`를 명시한다.
4. 실제 도면 선과 Layout을 작업한 뒤 제목, 축척, 가로 A4 용지 크기와 출력선을 확인한다. 투영·축척·용지 설정은 레시피에서 참고할 도면 조건이다. 레이어 적용 이후 Rhino에서 뷰와 Layout을 구성한다. A4 스타일을 성공적으로 적용하면 결과의 `review_preparation`에 PrintDisplay 설정 명령이 안내된다. 이 명령은 필요한 경우 별도로 실행한다.

다른 폴더나 스타일을 쓰는 경우에도 목록에 표시된 `recipe_id`를 조회와 적용에 사용할 수 있다. 스타일 적용에서 ID를 생략하면 공통 `standard_d`를 적용한다. 두 기본 레시피는 자체 레이어와 같은 표준 D 레이어를 함께 적용한다. 표준 D의 기존 정의는 `overwrite=true`일 때만 교체한다.

## 새 레시피 작성

아래 예제를 UTF-8 JSON 파일로 저장한다. `recipe_id`는 같은 폴더에서 고유해야 하며 영문·숫자·`.`·`_`·`-`를 사용해 1~80자로 정한다. 스타일을 적용하려면 `layers`에 레이어가 하나 이상 있어야 하고, 각 레이어에 비어 있지 않은 `path`가 필요하다. 하위 레이어 경로의 구분자는 `::`다.

```json
{
  "recipe_id": "project_plan",
  "layers": [
    {"path": "Drawing::ProjectPlan", "plot_weight_mm": 0.18}
  ]
}
```

필요에 따라 `name`, `description`, `projection`, `recommended_scales`, `output`을 추가해 레시피의 용도와 도면 조건을 기록한다. 레이어에는 표시 색 `color`, 출력 색 `plot_color`와 `linetype`을 지정할 수 있다. 색은 RGB 정수 세 개의 배열로 지정한다.

스타일 적용 성공 시 PrintDisplay 설정 명령을 안내하려면 레시피에 `"review_preparation": {"print_display": true}`를 추가한다.

## 선종류

각 레이어의 `linetype`에는 문서에서 사용할 이름만 쓴다. `linetype`을 생략하면 `Continuous`가 적용된다. 새 선종류의 길이와 실선·공백 설정은 [선종 매니페스트](../../../src/mcp/profiles/linetype/manifest.json)에 정의한다. 문서에 같은 이름이 이미 있으면 그 패턴과 참조를 유지하므로 레시피를 반복 적용해도 정의가 중복되지 않는다. 매니페스트에서 필요한 정의를 찾을 수 없으면 선종류와 레이어를 변경하기 전에 오류를 반환한다. [선종류 정의 형식](../../../src/mcp/profiles/linetype/README.md)을 참고한다.

## 레시피 검색 경로와 갱신

Python MCP는 시작할 때 다음 순서로 레시피 폴더 하나를 선택한다.

1. `RHINO_MCP_DRAWING_RECIPE_DIR`에 기존 AppData 기본 위치와 다른 폴더를 지정하면 그 폴더를 사용한다.
2. 저장소에서 실행하면 문서 연결 worker와 독립 서버 모두 `asset/drawing/DrawingRecipes`를 사용한다. 런처가 기존 기본 위치인 `%LOCALAPPDATA%\Almond\DrawingRecipes`를 전달해도 같다.
3. 저장소 레시피 폴더가 없는 설치 패키지는 지정한 폴더 또는 사용자 기본 위치를 사용한다. 독립 서버는 환경변수가 없을 때 패키지 기본 레시피 중 누락된 파일을 사용자 기본 폴더에 복사한다.

선택된 폴더 바로 아래의 JSON을 프로세스 시작 시 색인한다. 레시피 파일 추가·수정이나 검색 폴더 변경은 연결을 정상 종료하고 새 MCP 세션에서 확인한다. 사용자 파일을 기본값으로 덮어쓰지 않는다. 기본 패키지에는 A4와 `technical_axon_v1`이 포함된다.

PAT 해치 패턴은 등록된 PAT 자산의 ID로 `drawing_04-import_hatches` tool에서 가져온다.

## 표준 D

[표준 D 레시피](../../../src/mcp/profiles/drawing/standard_d.json)는 수동 작도의 기본값이며, 나열하거나 별도의 레시피 폴더를 설정하지 않아도 `drawing_01-apply_style`에서 적용된다. `layer_path`로 해당 용도의 레이어를 선택하거나, 생략해 전체를 적용한다. 선택된 하위 레이어에 표준 상위 레이어가 있으면 함께 확인한다. 반환된 레이어에 작도하고 객체 선종은 `ByLayer`로 둔다.

다른 기존 정의가 있으면 기본으로 아무것도 바꾸지 않고 충돌을 반환한다. 같은 정의는 다시 쓰지 않으며, 충돌을 교체하려면 `overwrite: true`를 사용한다. 표준 D 작도와 `D::PlanSection` 자동 출력은 분리한다.
