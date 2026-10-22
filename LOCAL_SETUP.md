# 로컬 환경 구성

모든 명령은 리포 루트에서 실행합니다. 개인 실행 환경은 `src/engine/.venv`이며
`src/mcp/almond_mcp`를 editable로 사용합니다. Engine과 MCP 소스는 분리돼 있습니다.

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

.NET 8 SDK가 필요합니다. PATH의 SDK 또는 `src/rhp/RhinoTerminal/data/sdk`를 사용합니다.

```powershell
./src/rhp/AlmondCOS/build.ps1
./src/rhp/RhinoTerminal/build.ps1 -OutputDirectory plugin-build
```

Bridge는 다음과 같이 빌드합니다. `$dotnet`에는 실제 SDK 실행 파일을 지정합니다.

```powershell
$dotnet = "$PWD/src/rhp/RhinoTerminal/data/sdk/dotnet.exe"
& $dotnet build src/rhp/RhinoAlmondBridge/RhinoAlmondBridge.csproj -c Release -o src/rhp/RhinoAlmondBridge/plugin-build
Copy-Item src/rhp/RhinoAlmondBridge/plugin-build/RhinoAlmondBridge.dll src/rhp/RhinoAlmondBridge/plugin-build/RhinoAlmondBridge.rhp
& ./src/engine/.venv/Scripts/python.exe tools/build_archive_bundle.py src/rhp/RhinoAlmondBridge/plugin-build/archive
```

`Structural_Analysis`와 `Asset_Panel`은 Bridge 프로젝트가 함께 컴파일하는 소스 폴더입니다.
별도 RHP로 나누지 않습니다. 패널은 RHP 옆 `archive`가 필요하므로 RHP만 복사하면 안 됩니다.
RhinoTerminal과 AlmondCOS는 각각 독립 RHP이고, 각 빌드 폴더의 DLL을 함께 유지합니다.

기존 설치된 Undo 패치 bridge는 유지합니다. 위 로컬 bridge 빌드가 자동으로 기존 설치를
교체하지는 않습니다. 등록 경로와 실제 로드된 버전은 별도로 확인해야 합니다.
사용자 제작 RHP의 새 등록 위치는 `src/rhp/AlmondCOS/plugin-build/AlmondCOS.rhp`,
`src/rhp/RhinoTerminal/plugin-build/RhinoTerminal.rhp`입니다. 정상적으로 Rhino를 재시작해 적용합니다.

## 실행

- 외부 실행: `src/engine/Almond 시작.cmd`. 저장된 모델을 선택합니다.
- Rhino 터미널: `RhinoTerminal` → `almond`; 재연결은 `almond resume`.
- COS: `src/cos/cos-plugin.json`의 command/args와 600초 제한을 사용합니다.
  Rhino의 저장된 문서에서 `AlmondCOS`를 실행하고 해당 host/model 연결을 선택합니다.
- 패널: 기존 `Almond`, `AlmondLibrary`, `AlmondStructure`, `AlmondResults` 명령을 유지합니다.
  UI와 계산기는 기존 구조대로 연결되며, solver 기본 실행 정책도 변경하지 않습니다.

AppData 라이브러리와 명시적 환경변수는 유지됩니다. `asset/`은 저장소 원본 자료입니다.
RHP를 체크아웃 경로에서 직접 새로 로드할 경우 라이브러리 탐색 결과가 달라질 수 있으므로
Python과 RHP가 동일한 `RHINO_MCP_*_DIR` 설정을 사용하도록 하고 Rhino를 재시작합니다.
모델 폴더의 `.almond`는 프로젝트 데이터이므로 실행 환경 정리와 별개입니다.

## 검증

```powershell
& ./src/engine/.venv/Scripts/python.exe -m pytest tests/mcp tests/engine
./src/cos/run_tests.ps1
& ./src/engine/.venv/Scripts/python.exe src/engine/verify_library_sources.py
node --test tests/rhp/Asset_Panel/*.test.mjs
```

네이티브와 Terminal host fixture는 `tests/engine/native`,
`tests/rhp/RhinoTerminal/AlmondHostContracts`에 있습니다. Terminal host fixture에는
기존의 빈 테스트용 data 디렉터리를 절대경로 인수로 전달합니다.
실제 Rhino 로딩·패널 조작·배치 결과는 오프라인 테스트와 별도로 검증합니다.

## Git

원본 `LICENSE`, 자산 고지, vendor 라이선스는 보존합니다. SDK·venv·RHP·로컬 설정·검증 산출물은 무시합니다.
이 리포 커밋을 원격에 올린 뒤 상위 Rhino 리포의 gitlink를 갱신합니다.
새 상위 체크아웃에서는 `git submodule update --init --recursive`로 고정 커밋을 받습니다.
