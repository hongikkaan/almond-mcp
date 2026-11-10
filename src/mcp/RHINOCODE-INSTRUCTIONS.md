# RhinoCode 실행

`execute_rhino_script`는 선택한 연결의 Rhino ScriptEditor에서 코드를 실행합니다. 해당 Rhino에서 `StartScriptServer`가 켜져 있어야 합니다. `project_info(sections=["runtime"])`의 `rhinocode` 항목으로 사용 가능 여부를 확인합니다.

- `script`에는 실행할 소스를 넣습니다. `language`는 `python`(Python 3), `python2`, `csharp` 또는 `csharp-script`, `command` 중에서 선택합니다. `command`일 때는 Rhino 커맨드 문자열을 넣습니다.
- Rhino의 PID, 포트, 연결 토큰과 문서는 런타임이 연결별로 관리합니다. 소스에 다른 Rhino 프로세스나 문서의 식별자를 복사하지 않습니다.
- 관찰한 문서 단위·공차·객체 ID를 사용합니다. API 작성 참고가 필요하면 `get_policy(policy="rhino_scripting")`, 메타데이터 규칙은 `get_policy(policy="metadata")`로 조회합니다.
- 산출물 파일을 만들기 전에 `set_working_plan`으로 작업 공간을 선택합니다. `execute_project_python`도 연결된 Rhino의 Python 3에서 실행하며 선택한 Plan 산출물 폴더를 작업 디렉터리로 사용합니다. 외부 worker의 가상환경 패키지가 Rhino에도 있다고 가정하지 않습니다.
- 코드와 커맨드는 실제 문서를 변경할 수 있습니다. Undo 범위와 실행 성공이 부분 변경의 롤백이나 저장 완료를 보장하지 않습니다. 저장은 요청된 경우 `save_rhino_document`로 수행합니다.
- 시간 초과·취소 후에는 반환된 `request_id`로 `get_rhino_execution`을 조회하고 문서 상태를 확인합니다. 완료 여부가 불확실한 변경을 자동으로 반복하지 않습니다. 요청 ID는 개별 실행 결과 식별자이므로 연결이 유지돼도 실행마다 달라집니다.
