# Codex·외부 MCP 클라이언트 연결

기존 `cos_host.py`는 표준 **stdio MCP 서버**다. COS 앱 없이 Codex CLI·Codex 앱 또는
로컬 stdio MCP 클라이언트가 같은 Python 명령을 직접 실행할 수 있다. Rhino에서는
기존 `AlmondCOS` 명령을 사용한다. 별도 RHP·서버·HTTP 포트를 만들지 않는다.

## 한 번 설정하기

일상 설치 폴더에서 실행한다. 개발 워크트리를 클라이언트나 Rhino에 등록하지 않는다.
Python 환경과 RHP 최초 설치는 [저장소 설치 안내](../../AGENTS.md)를 따른다.

```powershell
Set-Location C:\TOOL\Rhino\mcp\almond-mcp
# 미리 볼 때: 설정을 출력할 뿐 파일이나 연결을 변경하지 않는다.
& ./src/engine/.venv/Scripts/python.exe -B src/cos/client_config.py
# 실제 Codex 등록: 기존 파일 백업 후 almond_cos 항목만 추가한다.
& ./src/engine/.venv/Scripts/python.exe -B src/cos/client_config.py --install-codex "$env:USERPROFILE/.codex/config.toml"
```

다른 `CODEX_HOME`을 쓰는 CLI라면 그 디렉터리의 `config.toml` 경로를 명시한다.
이미 동일한 등록이 있으면 그대로 두고, 다른 `almond_cos` 항목이 있으면 덮어쓰지 않고
중단한다. 기존 모델·reasoning·다른 MCP·승인 설정은 유지한다. 실행 중인 클라이언트는
MCP를 다시 로드하거나 재시작한다. `codex mcp get almond_cos --json`으로 등록 경로를
확인할 수 있지만, 이 명령 자체는 MCP 연결 검증이 아니다.

다른 로컬 클라이언트는 다음 JSON의 `mcpServers.almond_cos`를 등록한다.
도구 호출 제한은 클라이언트 설정에서 **600초**로 지정한다. JSON에는 클라이언트마다
다른 timeout 키를 넣지 않는다. 경로와 필요한 라이브러리 환경 변수만 출력한다.

```powershell
& ./src/engine/.venv/Scripts/python.exe -B src/cos/client_config.py --format json
```

Codex 설정은 Python/host의 절대 경로, UTF-8, 시작 제한 120초·호출 제한 600초,
AppData·TEMP와 명시적인 라이브러리 경로 전달을 포함한다. 표준 입출력은 MCP 전용이다.
[Codex 공식 MCP 명령 안내](https://learn.chatgpt.com/docs/developer-commands#codex-mcp).

## 매번 사용하기

1. 일반 Rhino 8에서 `.3dm`을 열고 저장한 뒤 `AlmondCOS`를 실행한다.
2. 등록된 Codex 앱이나 외부 Codex CLI에서 "Almond 연결 목록을 확인하고 이 문서에
   연결해 줘"라고 요청한다. 클라이언트가 `almond_cos_list_connections`를 호출한다.
3. 목록의 정확한 `host_id`와 `model_path`로 `almond_cos_connect`를 호출한다.
   반환된 `connection_id`를 이후 모든 호출에 사용한다.
4. `almond_cos_project_info`로 문서와 `artifact_dir`를, `almond_cos_get_rhino_context`로
   실제 활성 문서를 확인한 다음 작업한다. 모델링에는 [Rhino Almond skill](../../skills/rhino-almond/SKILL.md)을 따른다.
5. 끝나면 `almond_cos_disconnect`로 해당 연결을 해제한다. 문서 변경 후에는 재연결한다.

`AlmondCOS`는 Rhino를 발견 가능하게 만드는 명령이다. Codex 프로그램을 자동 실행하거나
새 채팅에 자동 연결하지는 않는다. Rhino가 없으면 MCP 초기화와 도구 목록은 정상이고
연결 가능한 문서 목록만 비어 있다. 기존 `Almond 시작.cmd`·`RhinoTerminal → almond`로
관리되는 Rhino는 기존 전용 CLI를 사용하거나, 연결을 정상 종료한 뒤 일반 Rhino로 연다.

## 현재 공유 범위와 제한

- `src/cos/data/host.lock` 때문에 **한 설치 폴더에서 stdio 호스트는 하나만** 실행된다.
  COS 앱·Codex 앱·별도 Codex CLI 중 한 호스트를 사용한다. 연결 해제만으로 호스트 잠금은
  풀리지 않으므로 다른 클라이언트로 바꾸려면 기존 MCP 호스트도 종료/비활성화한다.
  `Lease is in use or not writable`는 이미 실행 중인 호스트 또는 파일 권한을 확인하라는 뜻이다.
  잠금 파일을 삭제하거나 다른 데이터 폴더로 잠금을 우회하지 않는다.
- 한 호스트가 여러 Rhino 문서를 연결할 수 있지만, 각 Rhino는 기존 한 연결의 소유권을
  유지한다. 서로 다른 클라이언트에 COS의 `connection_id`를 복사해 쓸 수 없다.
- 여러 Codex 채팅/프로세스가 각각 MCP 호스트를 시작하면 같은 제약이 적용된다.
  COS와 Codex 동시 공유, 다중 MCP 클라이언트 공유는 별도 broker 설계가 필요하다.
- Windows 사용자 세션의 named pipe를 사용한다. 이 진입점은 stdio만 지원하며 원격 URL,
  SSE/HTTP 서버 또는 클라우드에서 로컬 Rhino에 직접 접근하는 터널이 아니다.
- timeout은 rollback이 아니다. 결과 불명인 수정은 자동 반복하지 않는다.
