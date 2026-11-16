# 도면 스타일 레시피

## A4 평면·단면 스타일 적용

한 층의 평면이나 국소 단면을 1:100 A4 가로 도면으로 검토하는 예다. 한 공간을 상세하게 보려면 1:50, 동과 동 사이 관계를 보려면 1:200을 레시피의 권장 축척으로 참고한다.

1. `drawing_05-list_recipes` tool에 `{"include_ids":true}`를 입력하고 **Architectural Plan and Section A4**의 `recipe_id`를 확인한다.
2. `drawing_02-get_recipe` tool에 다음 인자를 입력한다.

   ```json
   {"recipe_id":"architectural_plan_section_a4_v1","field_groups":["scales","parameters"]}
   ```

   `recommended_scales`, `layers`, `output`을 확인한다. 절단선은 `ALMOND-DRAW::SECTION-CUT`에서 0.35 mm, 보이는 선은 `ALMOND-DRAW::VISIBLE`에서 0.13 mm로 출력한다.
3. 작업할 Rhino 문서에 연결하고 `drawing_01-apply_style` tool에 `{"recipe_id":"architectural_plan_section_a4_v1"}`를 입력한다. 적용은 `ALMOND-DRAW` 아래의 레이어와 그 속성을 생성하거나 갱신한다. 같은 스타일을 다시 적용하면 기존 경로의 레이어에 해당 속성을 적용한다.
4. 실제 도면 선과 Layout을 작업한 뒤 제목, 축척, 가로 A4 용지 크기와 출력선을 확인한다. 투영·축척·용지 설정은 레시피에서 참고할 도면 조건이다. 레이어 적용 이후 Rhino에서 뷰와 Layout을 구성한다. 출력 미리보기가 필요하면 적용 결과의 `review_preparation`을 확인한다.

## 선종류

각 레이어의 `linetype`은 문서에서 사용할 이름이다. 새 선종류는 [선종 매니페스트](../../../src/mcp/profiles/linetype/manifest.json)에 정의된 길이와 실선·공백 설정으로 만든다. 문서에 같은 이름이 이미 있으면 그 패턴과 참조를 유지하므로 레시피를 반복 적용해도 정의가 중복되지 않는다. 매니페스트에서 필요한 정의를 찾을 수 없으면 선종류와 레이어를 변경하기 전에 오류를 반환한다. [선종류 정의 형식](../../../src/mcp/profiles/linetype/README.md)을 참고한다.

## 레시피 검색 경로와 갱신

Python MCP는 시작할 때 다음 순서로 레시피 폴더 하나를 선택한다.

1. `RHINO_MCP_DRAWING_RECIPE_DIR`에 지정한 폴더
2. 저장소에서 실행하는 경우 `asset/drawing/DrawingRecipes`
3. 설치 패키지에서 실행하는 경우 Windows의 `%LOCALAPPDATA%\Almond\DrawingRecipes`. 패키지 기본 레시피는 이 폴더에 같은 파일명의 파일이 없을 때 복사된다.

선택된 폴더 바로 아래의 JSON을 프로세스 시작 시 색인한다. 레시피 파일 추가·수정이나 검색 폴더 변경은 연결을 정상 종료하고 새 MCP 세션에서 확인한다. 사용자 파일을 기본값으로 덮어쓰지 않는다. 기본 패키지에는 A4와 `technical_axon_v1`이 포함된다.

PAT 해치 패턴은 등록된 PAT 자산의 ID로 `drawing_04-import_hatches` tool에서 가져온다.
