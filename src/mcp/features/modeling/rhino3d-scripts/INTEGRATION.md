# Almond에서 사용하는 Rhino 3D Scripting Skill

이 묶음은 사용자가 설치한 `rhino3d-scripts`의 본문·네 참고자료·MIT LICENSE를
그대로 포함한다. `get_modeling_guide(tool="execute_rhino_script")` 또는
`get_modeling_guide(tool="execute_project_python")`은 이 자료를 같은 guide snapshot으로
반환한다. 개인 skill 폴더나 네트워크 조회는 실행 시 필요하지 않다.

원본: https://github.com/github/awesome-copilot/tree/main/skills/rhino3d-scripts
공식 실행 명세: https://developer.rhino3d.com/guides/scripting/advanced-cli/
포함본: 2026-10-30 사용자 로컬 설치본. upstream 원본과 동일한 revision이라는 뜻은 아니다.

## 이 도구에 적용하는 실행 방식

- 새 코드는 Python 3이 기본이다. `doc`은 연결된 실제 RhinoDoc이며 `scriptcontext.doc`도
  같은 문서다. Python은 JSON 값 `result`, C# statement body는 JSON 문자열 `result_json`에
  결과를 넣는다. `csharp`와 `csharp-script`는 같은 ScriptEditor C# 경로다.
  이전 `class Script { public static ... Run(RhinoDoc doc) }` 공개 실행 형식은 사용하지 않는다.
- 두 공개 도구 모두 공식 RhinoCode → ScriptEditor에서 실행한다. 프로젝트 Python의
  cwd는 선택한 Plan 산출물 폴더, 일반 Rhino 스크립트의 cwd는 프로젝트 루트다.
  `project_root`는 절대경로, `artifact_dir`는 프로젝트 상대경로다. 필요하면
  `os.path.join(project_root, artifact_dir, "result.json")`으로 출력한다.
  `ALMOND_PROJECT_ROOT`, `ALMOND_MODEL_PATH`, `ALMOND_ARTIFACT_DIR`은 실행 중에만 바인딩된다.
- 외부 MCP venv의 Python 패키지가 Rhino Python에 설치되어 있다고 가정하지 않는다.
  누락된 의존성을 자동 설치하지 않는다. RhinoCommon은 Rhino 내장 Python에서 사용한다.
- 실행기는 `list --json`에서 PID·프로세스 시작 시각·저장 문서 경로에 대응하는 exact
  `pipeId`를 선택한다. Almond A–J 슬롯 문자는 RhinoCode instance ID가 아니다.
- 실행 전과 Rhino UI thread 진입 후에 대상 문서를 확인한다. Undo record와 redraw는
  실행기가 관리하고 `finally`에서 cwd·환경·scriptcontext·redraw를 복구한다.
  코드가 추가 Undo record를 만들거나 별도 thread에서 문서를 수정하지 않는다.
- CLI 프로세스 종료는 Rhino 실행 완료가 아니다. `request_id`로 `get_rhino_execution`을
  조회한다. timeout은 대기 한도이며 코드를 종료하거나 반복하지 않는다.
- 스킬의 대화형 선택 예제는 명시 GUID 입력으로 바꿔 사용한다. `rs.GetObject`, `Pause`,
  dialog는 자동 실행에 넣지 않는다. macro에 `!`를 자동 추가하지 않는다. 스킬의 일반
  매크로 권고보다 기존 사용자 명령 보존과 이 연결의 완료 계약을 우선한다.
- 원문에 있는 ScriptEditor의 VBScript 지원 설명은 이 실행기에 적용하지 않는다.
  VBScript는 별도 legacy LoadScript/RunScript 표면이며 공개 RhinoCode 언어로 제공하지 않는다.
  Python `rs.Command`는 한 번에 한 명령을 사용하며 `! ` 조합을 넣지 않는다.
- 문서 공차 `doc.ModelAbsoluteTolerance`, GUID 변환, 실제 Geometry 타입, `Guid.Empty`
  확인은 참고자료를 따른다. 긴 반복은 `Rhino.RhinoApp.EscapeKeyPressed`를 확인한다.
  Boolean 결과의 null/빈 배열/유효닫힘 여부와 체적을 구분하고, 결과 검증 전 원본을
  Replace/Delete하지 않는다. 유효닫힘만으로 중첩 제거를 성공 판정하지 않는다.

## 내부 호출과 공개 도구의 경계

재료·레이어 설정, 자산 배치·교환, 화면 capture의 감사된 C# recipe는 공개 실행 도구를
호출하지 않는다. 이들은 기존 private Bridge 전송·반환값·ManagedFiles 계약을 유지한다.
공개 코드 실행에서 그 경로로 fallback하지 않는다. 고정 조회와 native helper도 그대로다.
이 경계 덕분에 공개 실행 도구 교체가 내부 도구의 `guids`·재료 결과·파일 관리를 바꾸지 않는다.
