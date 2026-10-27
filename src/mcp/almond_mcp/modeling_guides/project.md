## Rhino 편집

Almond MCP로 Rhino 건축 모델을 조회·편집하고 도면을 작성한다. 아래 도구명은 공통 이름이며, COS에서는 연결별 `connection_id`를 함께 전달한다. 인자는 현재 연결에 노출된 schema를 따른다.

### 프로젝트·문서·파일

같은 폴더의 여러 `.3dm`이 하나의 프로젝트이며 `.almond/DB`를 공유한다. **Rhino 편집 대상은 활성 문서만**이다. Worksession의 attached/reference 문서는 조회만 한다.

프로젝트·현재 파일은 `project_info`로 확인한다. DB 기록은 도구가 저장하고, 작업자료는 Task를 선택하면 `tmp/YYMMDD_작업명`에 관리된다. 관리 도구에는 프로젝트 상대경로를 전달하면 되므로 TEMP나 절대경로를 따로 조립하지 않는다. Rhino 모델의 `.3dm` 저장은 DB 기록과 별개다.

같은 문서의 연속 지시는 알고 있는 맥락을 재사용한다. `project_info` 재조회는 첫 연결·재연결, 사용자나 도구가 알려 준 문서 변경, 새 프로젝트·경로 정보 부족, 명시적 조회 요청이 있을 때 필요한 sections로 한정한다. 새 메시지가 왔다는 사실만으로 재조회하지 않는다. `document`가 live 문서를 함께 확인하므로 같은 확인을 위해 `get_rhino_context`를 이어 호출하지 않는다.

일상 편집마다 모델 전체나 DB의 별도 백업을 만들지 않는다. 명시적 요청이나 정해진 마이그레이션 계약이 있을 때만 별도 사본을 만든다. 기존 모델·DB·백업과 관련 없는 사용자 속성은 보존한다.

| 도구 | 입력 | 할 수 있는 일 |
| ------- | ----- | ----- |
| `project_info` | 필요한 `sections`: project, document, artifacts, runtime, instructions | 프로젝트 루트·파일명·공유 DB·현재 문서·작업자료 위치 조회. document에 live 확인이 포함된다. |
| `set_working_plan` | `plan_id`, 선택적 `step_id`, `artifact_name` | Task의 작업자료 폴더 선택·재사용. |
| `rename_artifact_folder` | `name`, 선택적 `plan_id` | 작업자료 폴더와 관련 참조를 함께 변경. |
| `execute_project_python` | `code`, 선택적 `timeout_seconds` | 선택한 작업자료 폴더에서 Python 실행. Rhino 형상 편집용 도구는 아니다. |
