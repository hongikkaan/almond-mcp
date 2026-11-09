# dot 전용 Almond MCP 클라이언트

`dot_client.py`는 기존 `codex_host.py`를 자식 프로세스로 실행하는 별도 MCP 클라이언트다. 기존 서버 코드, Codex MCP 등록, CoS 설정은 수정하지 않는다.

## 시작과 세션 유지

```powershell
& ./src/engine/.venv/Scripts/python.exe -B -X utf8 -u src/dots/dot_client.py
```

동지의 실행 도구에서는 지속형 터미널(`tty=true`)로 시작하고 반환된 터미널 `session_id`에 후속 입력을 보낸다. 입력은 한 줄 JSON이며 끝에 Enter를 붙인다. 클라이언트는 서버 시작 → initialize → tools/list를 수행한 뒤 `ready`를 출력한다. 초기 출력은 서버 소개·instructions, 도구 이름 목록, 클라이언트 사용법이며 개별 description 전체를 반복하지 않는다.

프로세스를 유지하는 동안 같은 MCP 세션과 connection_id를 사용한다. 터미널 session_id는 실행 도구의 핸들이고 Rhino connection_id와는 다르다. 실행 환경·터미널이 종료되면 이 세션도 종료된다. 영구 백그라운드 서비스나 재접속 복구 기능은 아니다. 새 클라이언트에 이전 connection_id를 넘겨 재사용하지 않는다.

## 명령

각 입력에 선택적인 `id`를 붙이면 응답에 그대로 반환한다.

```json
{"id":"help","op":"help"}
{"id":"names","op":"catalog"}
{"id":"definitions","op":"describe","names":["list_connections","connect","project_info"]}
{"id":"available","op":"call","name":"list_connections","arguments":{}}
```

`describe`는 이름 배열에 해당하는 전체 description, inputSchema와 제공되는 outputSchema·annotations를 원본 그대로 반환한다. 현재 세션 시작 때 받은 catalog를 사용한다. 알려지지 않은 이름이나 잘못된 명령 형식은 서버를 호출하지 않고 오류로 반환한다.

실제 대상 선택은 `list_connections`에서 확인한 정확한 값으로 한다. 아래 값은 설명용 자리표시자다.

```json
{"op":"call","name":"connect","arguments":{"host_id":"<목록의 host_id>","model_path":"<목록의 model_path>"}}
{"op":"call","name":"project_info","arguments":{"connection_id":"<connect 결과의 ID>","sections":["document"]}}
{"op":"call","name":"disconnect","arguments":{"connection_id":"<같은 ID>"}}
{"op":"shutdown"}
```

`connect` 이후의 호출도 같은 실행 도구 session_id에 입력한다. 다른 클라이언트가 소유한 Rhino를 빼앗거나 잠금 파일을 삭제하지 않는다. 새 Rhino는 자동으로 만들지 않으며 `start_session`은 명시적인 요청일 때만 호출한다.

## 응답과 오류

`call`의 `tool_result`는 MCP 결과를 원형 보존한다. content의 text·image, structuredContent, isError 등을 축약하거나 재해석하지 않는다. `ok=true`는 클라이언트가 응답을 받았다는 뜻이며, 도구의 성공은 `tool_result.isError`와 본문을 함께 확인한다. 이미지는 JSON의 MCP 이미지 블록으로 반환되며 이 CLI가 화면에 렌더링하지는 않는다.

잘못된 입력 뒤에도 클라이언트는 다음 입력을 기다린다. 호출 오류·timeout을 자동 재시도하지 않는다. timeout은 rollback 증거가 아니며 변경 호출을 다시 보내기 전 결과를 확인한다. 요청은 한 번에 하나씩 처리한다.

`shutdown` 또는 정상 EOF는 이 클라이언트가 만든 MCP 연결을 정리한다. Rhino 파일을 저장하거나 Rhino를 종료하지 않는다. 작업이 끝났으면 먼저 `disconnect`로 연결 해제를 확인한다. 강제 프로세스 종료와 정상 정리를 혼동하지 않는다.

호출 제한 기본값은 600초다. `--timeout`, `--server-python`, `--server-entry`는 명시적으로 변경할 때만 사용한다. 서버 stdout은 MCP 전용이고 클라이언트 stdout은 위 JSON 출력용이다. 터미널 화면의 줄바꿈·ANSI 코드는 전송 JSON 데이터가 아니다.

## 검증

```powershell
& ./data/development/.venv/Scripts/python.exe -B -X utf8 -m unittest discover -s src/dots/tests -p 'test_*.py' -v
```

기존 도구의 이름 변경이나 instruction 재배분은 이 클라이언트와 별도 작업이다.
