# 모듈별 개발과 병렬 작업

목표는 서로 다른 워크트리에서 기능을 수정한 뒤 각 변경을 작은 범위로 합치는 것이다.
MCP와 COS를 별도 제품으로 배포하거나 공용 구현을 복제하지 않는다.

## 소유권과 의존 방향

| 소유 모듈 | 구현·검사 위치 | 허용하는 의존 관계 |
|---|---|---|
| MCP | `src/mcp/almond_mcp`, `runtime`, `tools`, `tests` | Python 라이브러리와 Rhino의 기존 전송 계약. COS 구현을 import하지 않는다. |
| COS | `src/cos`의 host/worker·catalog, `rhp`, `tests` | MCP 실행기의 검증·구성 훅, native Engine. MCP 내부 정책을 COS에 복제하지 않는다. |
| Native Engine | `src/rhp/Engine`, 그 안의 `tests` | Rhino·플랫폼 API. 개별 호스트 프로젝트를 참조하지 않는다. |
| Bridge | `src/rhp/RhinoAlmondBridge` 및 자체 `tests` | Engine, MCP 소유 C# 모델링 코드·재료 정책, 아래 패널·Terminal 소스. |
| RhinoTerminal | `src/rhp/RhinoTerminal/src`, `tests` | Engine과 MCP 실행기. 기존처럼 Bridge RHP에 컴파일된다. |
| 패널·구조해석 | `src/rhp/Asset_Panel`, `Structural_Analysis` | 기존 Bridge 계약. 패널 웹 원본은 Python wheel과 RHP archive가 함께 사용한다. |
| 통합 | 루트 `tests`, `src/rhp/tools`의 설치·배포 검사 | 모듈 간 schema·패키징·native 실행 파일의 일치 여부를 검사한다. |

MCP가 소유한 native 모델링 코드는 Bridge에 컴파일되고, 패널 웹 자원은 Python
패키지에 포함된다. 이 공유 자원을 바꾸면 소비자 검사·빌드도 필요하다. 소유권을
나눈다고 모든 기능을 독립 assembly나 독립 배포로 바꾸지는 않는다.

## 각 워크트리에서 작업하기

각 체크아웃에서 `src/mcp/rebuild_environment.ps1`을 실행해 자기 Python 환경을 만든다.
이 명령은 COS 카탈로그를 수정하지 않는다. COS 작업을 시작할 때만
`src/cos/configure.ps1`로 해당 체크아웃의 카탈로그·CoS 설정 JSON을 생성한다.
생성된 JSON은 앱에 자동 등록되지 않는다.

| 변경 예 | 주로 수정하는 범위 | 기본 검사와 추가 반영 |
|---|---|---|
| MCP 도구 내부 계산·검증 | `src/mcp` | `./src/mcp/run_tests.ps1`; COS fingerprint 대상 소스가 바뀌면 카탈로그도 갱신하고 통합 검사 |
| COS 연결·화면·host 동작 | `src/cos` | `./src/cos/run_tests.ps1`; C# 변경 시 자체 `build.ps1`, COS manifest만 기록 |
| Terminal 입력·호스트 동작 | `src/rhp/RhinoTerminal` | 자체 `tests`의 TerminalSmoke·AlmondHostContracts, Bridge 빌드와 Bridge manifest 기록 |
| 공용 native Engine | `src/rhp/Engine` | 자체 NativeFixture, 두 host 검사, 두 RHP 빌드와 DLL 일치 검사 |
| 패널 웹 UI | `src/rhp/Asset_Panel` | 자체 Node tests, Bridge 빌드, 루트 패키징 통합 검사 |

MCP 전체 검사는 `src/mcp/pytest.ini`로 경로가 고정되어 있다. 일부 검사만 실행하려면:

```powershell
./src/mcp/use_offline_environment.ps1
& ./src/engine/.venv/Scripts/python.exe -B -X utf8 -m pytest -c src/mcp/pytest.ini src/mcp/tests/runtime
```

COS의 `run_tests.ps1`은 필요한 .NET fixture를 준비하고 Python host/worker 검사를
수행한다. Native SDK는 설치된 .NET 8을 사용하며 로컬 SDK를 둔 경우 기존
`src/rhp/RhinoTerminal/data/sdk` 위치도 지원한다. SDK 캐시는 소스 의존성이 아니다.

루트에서 실행하는 기본 `pytest`는 통합 검사다. native archive host가 필요한 검사는
`src/rhp/RhinoAlmondBridge/tests/archive_host/ArchiveHost.csproj`를 빌드한 뒤
`ALMOND_ARCHIVE_TEST_HOST`에 그 실행 파일의 절대 경로를 지정한다. 해당 host가 없으면
관련 검사는 건너뛰므로, 이를 native 검증 완료로 보고하지 않는다.

## 빌드 결과와 통합

Bridge는 `src/rhp/build.ps1`, COS는 `src/cos/build.ps1`로 빌드한다. 각 빌드는 자기
staging에서 완료한 뒤 출력 폴더를 교체한다. 등록·Rhino 로드는 수행하지 않는다.

검증 기록도 각 소유 모듈에 있다.

```powershell
# 해당 모듈 빌드 후 자기 기록만 갱신한다.
& ./src/engine/.venv/Scripts/python.exe -B src/rhp/tools/verify_runtime.py --record --component bridge
& ./src/engine/.venv/Scripts/python.exe -B src/rhp/tools/verify_runtime.py --record --component cos
# 합칠 때 두 기록과 공용 DLL 일치 여부를 함께 검사한다.
& ./src/engine/.venv/Scripts/python.exe -B src/rhp/tools/verify_runtime.py
```

Bridge manifest는 COS 소스를 포함하지 않고, COS manifest는 Terminal·패널 소스를
포함하지 않는다. Engine을 바꾸면 두 manifest와 실행 파일을 함께 갱신해야 한다.
공유 공개 schema 변경도 통합 작업이다. 이 경우의 충돌은 정상적인 계약 조정이며,
한쪽 기록을 덮어써서 숨기지 않는다.

## 기존 설치와 호환 경로

| 이전 소유 위치 | 현재 소유 위치 |
|---|---|
| `src/engine`의 Python·CLI 구현 | `src/mcp/runtime` |
| `src/engine/native` | `src/rhp/Engine` |
| `src/rhp/AlmondCOS/src`·빌드 스크립트 | `src/cos/rhp`·`src/cos/build.ps1` |
| 루트 `tests/mcp`, `tests/engine` | `src/mcp/tests`와 그 안의 `runtime` |
| 루트 `tests/cos` | `src/cos/tests` |
| 루트 `tests/rhp` | 각 RHP 구성요소의 `tests` |
| 공용 `src/rhp/runtime-manifest.json` | Bridge와 COS 각각의 `runtime-manifest.json` |

기존 Rhino 등록 파일 `src/rhp/RhinoAlmondBridge/plugin-runtime/RhinoAlmondBridge.rhp`와
`src/rhp/AlmondCOS/plugin-runtime/AlmondCOS.rhp`는 이동하지 않는다. COS 소스는 모였지만
설치 출력은 기존 등록 위치에 배치한다.

기존 CoS의 Python command를 보존하기 위해 `.venv`는 `src/engine/.venv`에 유지한다.
`src/engine`의 예전 시작 버튼·설치 스크립트는 새 소유 모듈로 전달하는 호환 진입점이다.
그곳에 기능 구현을 추가하지 않는다. 각 체크아웃의 환경은 별도로 만들며 공유하지 않는다.

워크트리가 달라도 모델 폴더의 DB·Rhino 등록·슬롯·실행 중 assembly가 자동 격리되지는
않는다. 오프라인 검사는 checkout의 `data/offline`을 사용하고, 실제 Rhino 검증은
일회용 문서에서 수행한다. 일상 설치 갱신·등록·실제 로드는 로컬 개발 완료와 구분한다.
