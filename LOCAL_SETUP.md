# 로컬 환경 구성

모든 명령은 리포 루트에서 실행합니다. 개인 실행 환경은 `src/engine/.venv`이며
`src/mcp/almond_mcp`를 editable로 사용합니다. Engine과 MCP 소스는 분리돼 있습니다.

## 일상 업데이트

기존 Python 환경과 최초 등록이 완료된 일상 폴더에서는 Rhino를 닫고
`git pull --ff-only`를 실행한 뒤 Rhino를 켜면 됩니다. Bridge/COS RHP와
의존 파일은 `src/rhp/*/plugin-runtime`에 Git으로 함께 배포합니다.
별도 빌드, 바이너리 복사, 매번 등록 변경은 필요하지 않습니다.
다른 위치에 처음 설치할 때만 `tools/install_runtime.ps1`을 실행합니다.
Python 환경의 최초 구성은 아래 설명을 따릅니다.

개발자는 C# 변경 시 아래 빌드 명령으로 고정 runtime 폴더를 갱신하고
`python tools/verify_runtime.py --record`와 `python tools/verify_runtime.py`를
실행한 뒤 소스와 실행 파일을 같은 커밋에 포함해야 합니다.
## Python

```powershell
./src/engine/rebuild_environment.ps1
```

이 환경을 사용하는 host/worker와 관리 중인 Rhino 연결을 종료한 뒤 실행합니다.
Python 3.12.12, `uv.lock`의 local/dev 의존성을 설치하고 source 경로를 검사하며
`src/cos/tool_catalog.json`과 로컬 절대경로의 `src/cos/cos-plugin.json`을 생성합니다.

수동 uv 명령에서는 해당 쉘에서만 환경 경로를 지정합니다.

```powershell
$env:UV_PROJECT_ENVIRONMENT = "$PWD/src/engine/.venv"
uv run --no-sync python -c "import almond_mcp; print(almond_mcp.__file__)"
```

실행 중에는 동기화하지 않습니다. Python 변경은 해당 host/worker 재시작이 필요합니다.
COS 카탈로그의 source fingerprint와 tool schema 검사를 우회하지 않습니다.

## Rhino 플러그인 빌드

.NET 8 SDK와 Windows Rhino 8이 필요합니다. 통합본은 `net8.0-windows`이며
설치된 Rhino 8.34 SDK / Rhino의 .NET 8 runtime에서 검증했습니다.
빌드는 `src/rhp/RhinoTerminal/data/sdk` 또는 PATH의 SDK를 사용하고,
SDK가 없으면 기존 방식대로 검증된 다운로드를 로컬 `data/sdk`에 준비합니다.

```powershell
./src/rhp/build.ps1
```

출력은 `src/rhp/RhinoAlmondBridge/plugin-runtime`입니다. Bridge·Structural_Analysis·
Asset_Panel·RhinoTerminal이 같은 `RhinoAlmondBridge.rhp`에 포함됩니다.
Almond.Engine.dll은 별도 DLL로 유지하며 Porta.Pty/Vanara/Roslyn/Newtonsoft DLL,
deps/runtimeconfig JSON, `licenses`, `archive`를 함께 둡니다.
Rhino가 제공하는 RhinoCommon/Rhino.UI/Eto/Grasshopper/GH_IO DLL은 배포하지 않습니다.

빌드는 새 staging 폴더에서 완료한 뒤 출력을 교체합니다. 출력이 Rhino에 로드돼 있으면
중단하므로 해당 Rhino를 정상 종료한 뒤 빌드합니다. 사용자 문서를 강제로 닫지 않습니다.
Terminal의 `../../../engine` 탐색을 위해 출력은 `RhinoAlmondBridge/plugin-*` 깊이를 유지합니다.

COS는 별도 플러그인입니다. 필요할 때 기존 명령으로 빌드하며 이번 단일 RHP에 포함하지 않습니다.

```powershell
./src/rhp/AlmondCOS/build.ps1
```

통합 설치 경로는 `src/rhp/RhinoAlmondBridge/plugin-runtime/RhinoAlmondBridge.rhp`입니다.
기존 Bridge GUID `c337dbb8-394a-4593-9c2b-a3d7cfc91893`로 등록하고,
이전 Terminal GUID `27D4B9A1-8FAD-421C-B64A-7A213D3B4079`의 중복 등록은 백업 후 제거합니다.
빌드는 등록을 변경하지 않습니다. 정상 Rhino 재시작 후 실제 로드 경로·버전을 확인합니다.
COS의 등록 경로는 `src/rhp/AlmondCOS/plugin-runtime/AlmondCOS.rhp`로 별도 유지합니다.

Yak 확인이 필요하면 다음을 실행합니다. 설치·게시하지 않는 별도 staging 빌드이며,
현재 SDK에서 생성하는 이름은 `almondbridge-0.7.0-rc.2-rh8_34-win.yak`입니다.
Yak만 임의 위치에 설치하면 Terminal이 개인 checkout의 Engine을 자동으로 찾지는 못합니다.

```powershell
./tools/build_yak.ps1 -PythonExecutable "$PWD/src/engine/.venv/Scripts/python.exe" -DotnetExecutable "$PWD/src/rhp/RhinoTerminal/data/sdk/dotnet.exe"
```

## 실행

- 외부 실행: `src/engine/Almond 시작.cmd`. 저장된 모델을 선택합니다.
- Rhino 터미널: `RhinoTerminal` → `almond`; 재연결은 `almond resume`.
- COS: `src/cos/cos-plugin.json`의 command/args와 600초 제한을 사용합니다.
  Rhino의 저장된 문서에서 `AlmondCOS`를 실행하고 해당 host/model 연결을 선택합니다.
- 패널: 기존 `Almond`, `AlmondLibrary`, `AlmondStructure`, `AlmondResults` 명령을 유지합니다.
  UI와 계산기는 기존 구조대로 연결되며, solver 기본 실행 정책도 변경하지 않습니다.

Rhino 8.34에서 떠 있는 Almond 패널이 Structure 전환 후 숨는 현상이 관찰됐습니다.
이 경우 패널을 오른쪽의 기존 Terminal/Layers dock에 함께 두고 사용합니다.
검증에서는 `Panels.PanelDockBar(TerminalGuid)`로 얻은 dock에
`Panels.OpenPanel(dock, AlmondPanelGuid, true)`를 호출해 화면을 복구했습니다.
플러그인의 패널 GUID나 등록 방식은 변경하지 않았습니다.

AppData 라이브러리와 명시적 환경변수는 유지됩니다. `asset/`은 저장소 원본 자료입니다.
RHP를 체크아웃 경로에서 직접 새로 로드할 경우 라이브러리 탐색 결과가 달라질 수 있으므로
Python과 RHP가 동일한 `RHINO_MCP_*_DIR` 설정을 사용하도록 하고 Rhino를 재시작합니다.
모델 폴더의 `.almond`는 프로젝트 데이터이므로 실행 환경 정리와 별개입니다.

## 검증

기본 `pytest`는 MCP와 Engine을 수집합니다. COS는 .NET pipe/lifecycle fixture와
환경변수 준비가 필요하므로 기본 수집에서 제외하고 전용 `src/cos/run_tests.ps1`로 실행합니다.

```powershell
& ./src/engine/.venv/Scripts/python.exe -X utf8 -m pytest tests/mcp tests/engine
./src/cos/run_tests.ps1
& ./src/engine/.venv/Scripts/python.exe src/engine/verify_library_sources.py
node --test (Get-ChildItem tests/rhp/Asset_Panel -Filter *.test.mjs | ForEach-Object FullName)
```

네이티브와 Terminal host fixture는 `tests/engine/native`,
`tests/rhp/RhinoTerminal/AlmondHostContracts`에 있습니다. Terminal host fixture에는
기존의 빈 테스트용 data 디렉터리를 절대경로 인수로 전달합니다.
실제 Rhino 로딩·패널 조작·배치 결과는 오프라인 테스트와 별도로 검증합니다.
단일 RHP 통합 당시의 실제 검증 결과는 [통합 기록](docs/HANDOFF-single-rhp.md),
후속 문서·뷰포트 조회와 C# 결과 반환의 실제 확인 범위는
[관측·반환 검증 기록](docs/native-observation-verification.md)을 참고합니다.

새 조회·반환 계약의 Python 검증은 다음과 같이 실행합니다. Rhino를 직접 변경하는 검증은 아닙니다.

```powershell
& ./src/engine/.venv/Scripts/python.exe -B -X utf8 -m pytest tests/mcp/test_rhino_observation.py tests/cos/test_catalog.py tests/cos/test_broker.py tests/cos/test_compat.py tests/cos/test_transport.py::StdioTests -q
```

위 명령은 .NET pipe fixture가 필요한 `PipeTests`를 포함하지 않습니다. 전체 COS 검증은
앞의 `src/cos/run_tests.ps1`을 사용합니다.

실제 연결에서는 `almond_cos_project_info`로 문서를 확인한 뒤
`almond_cos_get_rhino_context`, 필요할 때 `almond_cos_get_rhino_viewport_image`를 호출합니다.
세 도구 모두 연결의 `connection_id`를 사용합니다. 반환 형식과 C#의 `result_error` 의미는
[기능 계약](docs/native-observation.md)을 따릅니다.
native Undo·조회 fixture의 빌드와 modeless 실행 절차는
[fixture README](tests/rhp/RhinoAlmondBridge/script_executor_undo/README.md)에 있습니다.
실제 로드된 RHP와 충돌하지 않게 새 `RhinoAlmondBridge/plugin-*` 후보 경로를 사용하고,
fixture·빌드 성공과 실제 MCP 클라이언트 수신을 구분합니다.

## Git

원본 `LICENSE`, 자산 고지, vendor 라이선스는 보존합니다. SDK·venv·RHP·로컬 설정·검증 산출물은 무시합니다.
이 리포 커밋을 원격에 올린 뒤 상위 Rhino 리포의 gitlink를 갱신합니다.
새 상위 체크아웃에서는 `git submodule update --init --recursive`로 고정 커밋을 받습니다.

### 워크트리 개발

워크트리는 같은 Git 이력을 공유하는 전체 체크아웃입니다. 분야별 폴더는 작업 책임을
나누는 용도이며, 코드·DB·RHP를 독립 패키지로 나눌 필요는 없습니다.

| 폴더 예시 (`C:\TOOL\Almond-worktrees` 아래) | 브랜치·역할 |
|---|---|
| `main` | `main`; PR 병합 결과 동기화와 통합 검증 |
| `construction-material` | `work/construction-material`; construction·material·관련 자료 |
| `scene-workflow` | `work/scene-workflow`; scene·room·instance·plan·step |
| `skill` | `work/skill`; Rhino Almond 스킬·고정 probe 및 관련 계약 |

asset 작업은 실제 과업이 생길 때 최신 `main`에서 별도 작업 브랜치를 만듭니다.
`server.py`, `retrieval_store.py`의 스키마, Engine/COS, 카탈로그, 공용 패널과 통합 RHP
빌드는 공통 변경 범위입니다. 여러 분야가 같은 파일을 바꾸면 작은 공통 PR을 먼저
병합하고 각 작업 브랜치에서 반영합니다. 분야마다 DB 스키마나 실행 계층을 복제하지 않습니다.

새 과업의 예시는 다음과 같습니다. 기존 워크트리와 겹치지 않는 경로·브랜치를 사용합니다.

```powershell
git -C C:\TOOL\Almond-worktrees\main pull --ff-only
git -C C:\TOOL\Almond-worktrees\main worktree add -b work/asset-catalog C:\TOOL\Almond-worktrees\asset-catalog main
Set-Location C:\TOOL\Almond-worktrees\asset-catalog
./src/engine/rebuild_environment.ps1
```

각 워크트리의 `src/engine/.venv`는 해당 체크아웃에서 새로 설치합니다. venv 복사·공유는
editable import를 다른 브랜치로 연결할 수 있습니다. 재설치 전에는 해당 환경의
host/worker와 관리 중인 Rhino 연결을 종료하며, 기존 실행 경로는 그대로 둡니다.

오프라인 개발용 PowerShell에서 작업할 워크트리로 이동한 뒤 다음을 실행합니다.

```powershell
./tools/use_offline_environment.ps1
& ./src/engine/.venv/Scripts/python.exe -B -X utf8 -m pytest tests/mcp/test_construction.py tests/mcp/test_materials.py tests/mcp/test_retrieval_store.py -q
```

이 설정은 현재 PowerShell과 여기서 시작하는 자식 프로세스에만 적용됩니다.
라이브러리는 해당 워크트리의 `asset/`, 없는 라이브러리는 `data/offline/libraries`,
기본 상태 DB는 `data/offline/state.sqlite3`, 임시 파일은 `data/offline/tmp`를 사용합니다.
개별 테스트가 만든 임시 DB도 같은 임시 폴더를 사용합니다. 다른 워크트리로 이동했다면
그쪽 설정을 다시 실행합니다. 일반 실행으로 돌아갈 때는 새 PowerShell을 엽니다.

환경 설정 자체의 검사는 `./tests/engine/test_offline_environment.ps1`입니다.
서버를 import하기 전에 설정해야 합니다. 이 스크립트는 네트워크 차단기가 아니므로
실제 Rhino 연결 검증은 별도 단계에서 수행합니다. 모델의 `.almond` DB, AppData,
A–J 슬롯과 로드된 RHP는 워크트리를 만든 것만으로 격리되지 않습니다.

작업은 해당 브랜치에 commit/push하고 PR의 base를 `main`으로 지정합니다. PR 병합은
원격 `main`을 갱신하므로 로컬 `main` 워크트리에서 다시 `git pull --ff-only`를 실행합니다.
다음 과업은 갱신된 `main`에서 새 브랜치로 시작합니다. 로컬 `skill`은 기존 작업을
보존하는 브랜치이며 모든 개발의 분기 기준으로 사용하지 않습니다.

### 일상 Rhino/COS 실행 경로는 원래 저장소에 고정

Rhino의 실행 소스는 로드한 RHP 위치에서 결정됩니다. 같은 프로세스의 Bridge·COS·
Engine과 Python은 같은 워크트리를 사용해야 합니다. Git의 PR 병합이나 현재 작업
디렉터리 변경만으로 실행 중인 Rhino가 전환되지는 않습니다.

평소 CoS의 Almond COS 등록은 원래 저장소인 `C:\TOOL\Rhino\mcp\almond-mcp`의
`src/cos/cos-plugin.json`을 사용합니다. 이 실행 경로는 브랜치 이름과 별개입니다.
개발은 작업용 워크트리에서 진행합니다. 개발 결과를 일상 환경에 적용할 때 원래
저장소의 파일을 갱신하고 필요한 빌드·정상 재시작을 거칩니다. 개발할 때마다 일상
CoS 등록을 바꾸지 않습니다.

1. 원래 저장소의 Python 환경·카탈로그를 준비하고 관련 검증을 실행합니다.
2. 원래 저장소에서 `src/rhp/build.ps1 -OutputDirectory 'RhinoAlmondBridge\plugin-<빌드명>'`와
   `src/rhp/AlmondCOS/build.ps1`로 두 플러그인을 빌드합니다. 로드 중인 출력을
   덮어쓰지 않으며, 공통 `Almond.Engine.dll`의 빌드가 일치하는지 확인합니다.
3. 기존 Bridge/COS 레지스트리 키를 백업한 뒤 다음 두 키의 `FileName`만
   원래 저장소의 RHP 절대경로로 설정합니다. GUID와 기존 LoadMode는 유지합니다.

   - `HKCU\Software\McNeel\Rhinoceros\8.0\Plug-ins\c337dbb8-394a-4593-9c2b-a3d7cfc91893\PlugIn`
   - `HKCU\Software\McNeel\Rhinoceros\8.0\Plug-ins\39eb74f6-8283-4e43-bf26-f0106d891b75\PlugIn`

4. 원래 저장소의 `src/cos/cos-plugin.json`에 있는 command/args를 CoS의 Almond COS 등록에
   적용합니다. 이 파일 생성은 CoS 앱에 플러그인을 등록하는 동작이 아닙니다. 목록에
   없다면 CoS의 Plugins에서 사용자 지정 실행 파일로 한 번 등록합니다. 기존 연결은
   완료·detach하고, 같은 문서의 DB·세션 보호를 유지합니다.
5. 새 Rhino 또는 정상 재시작한 Rhino에서 실제 Bridge·COS·Engine 모듈 경로와
   Python worker 경로를 확인합니다. 기존 `RHINO_MCP_*_DIR`를 유지하고 native와
   Python 라이브러리 경로를 대조합니다. 고정 조회·캡처·필요한 기능을 실제 호출합니다.

개발 워크트리의 빌드는 위 레지스트리와 CoS 등록을 변경하지 않습니다. 일상 등록을
개발 브랜치로 돌렸다가 되돌리는 절차를 사용하지 않습니다.

`skills/rhino-almond/scripts/Almond*.cs`는 고정 probe용으로 Bridge에 함께 컴파일됩니다.
이 helper 변경도 RHP 재빌드·로드 검증 대상입니다. 문서만 바꾸는 스킬 작업에는
RHP 재빌드가 필요하지 않습니다.

2026-10-23에는 `skill` 워크트리로 Bridge/COS 등록을 전환하고 별도 Rhino에서
공개 COS 호출까지 검증했습니다. 정확한 경로·검증 범위는
[전환 기록](docs/worktree-probe-verification.md)에 있습니다. 상위 Rhino 리포의
gitlink는 이 실행 경로와 별개이며, 상위에서 진행 중인 다른 작업과 섞어 변경하지 않습니다.
