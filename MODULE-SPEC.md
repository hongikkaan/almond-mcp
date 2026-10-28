# 모듈별 개발과 병렬 작업

목표는 서로 다른 워크트리에서 기능을 수정한 뒤 각 변경을 작은 범위로 합치는 것이다.
MCP와 외부 연결기를 별도 제품으로 배포하거나 공용 구현을 복제하지 않는다.

## 소유권과 의존 방향

| 소유 모듈 | 구현·검사 위치 | 허용하는 의존 관계 |
|---|---|---|
| MCP | `src/mcp`의 공용 코드·`features`, `runtime`, `release_validation`, `tests` | Python 라이브러리와 Rhino의 기존 전송 계약. 외부 연결기 구현을 import하지 않는다. |
| 외부 연결기 | `src/cos`의 host/worker·catalog, `rhp`, `tests` | MCP 실행기의 검증·구성 훅, native Engine. MCP 내부 정책을 외부 연결기에 복제하지 않는다. |
| Native Engine | `src/rhp/Engine`, 그 안의 `tests` | Rhino·플랫폼 API. 개별 호스트 프로젝트를 참조하지 않는다. |
| Bridge | `src/rhp/RhinoAlmondBridge` 및 자체 `tests` | Engine, MCP 소유 C# 모델링 코드·재료 정책, 아래 패널·Terminal 소스. |
| RhinoTerminal | `src/rhp/RhinoTerminal/src`, `tests` | Engine과 MCP 실행기. 기존처럼 Bridge RHP에 컴파일된다. |
| 패널·구조해석 | `src/rhp/Asset_Panel`, `Structural_Analysis` | 기존 Bridge 계약. 패널 웹 원본은 Python wheel과 RHP archive가 함께 사용한다. |
| 통합 | 루트 `tests`, `src/rhp/tools`의 설치·배포 검사 | 모듈 간 schema·패키징·native 실행 파일의 일치 여부를 검사한다. |

MCP가 소유한 native 모델링 코드는 Bridge에 컴파일되고, 패널 웹 자원은 Python
패키지에 포함된다. 이 공유 자원을 바꾸면 소비자 검사·빌드도 필요하다. 소유권을
나눈다고 모든 기능을 독립 assembly나 독립 배포로 바꾸지는 않는다.

## 각 워크트리에서 작업하기

개발·테스트는 사용 중인 Rhino나 MCP 서버를 시작·종료하지 않아도 수행할 수 있어야 한다.
실행 중인 서버의 소스도 보존해야 하면 별도 워크트리를 사용한다. Python 환경만 분리해도
같은 체크아웃의 소스 변경이 기존 호스트의 source fingerprint에 반영되는 점은 달라지지 않는다.

```powershell
./src/mcp/rebuild_environment.ps1 -Development
./src/mcp/run_tests.ps1 -Development
./src/cos/run_tests.ps1 -Development
./tests/run_tests.ps1 -Development
```

`-Development`는 해당 체크아웃의 `data/development/.venv`에 잠긴 의존성을 설치한다.
일상 `src/engine/.venv`, CoS 설정, Rhino 등록 및 실행 중인 호스트를 변경하지 않는다.
대상 개발 환경 자체가 사용 중이면 재구성하지 않는다. 옵션 없는 최초 설치 절차는
일상 환경을 대상으로 하므로 해당 환경의 host/worker 정상 종료가 필요하다.

오프라인 설정은 현재 셸·자식의 라이브러리와 DB/tmp를 `asset/`·`data/offline`으로
지정한다. 실제 모델에 연결하거나 네트워크 전체를 차단하는 기능은 아니다.
일반 실행으로 돌아갈 때는 새 셸을 연다. venv는 체크아웃 간 복사·공유하지 않는다.

| 변경 예 | 검사와 반영 |
|---|---|
| MCP 도구·계산·저장소 | MCP 검사, 공개 schema 변경 시 외부 연결기 및 루트 통합 검사 |
| 외부 연결기 | COS 검사: .NET 대역·소유권·통신 fixture와 Python 검사 |
| Terminal·공용 Engine | 각 native fixture, 영향받는 RHP 빌드 및 manifest 검증 |
| 패널 웹 UI | Node tests, Bridge 빌드, 루트 패키징 통합 검사 |

테스트용 native fixture 빌드는 RHP 교체와 별개이며 Rhino 종료를 요구하지 않는다.
실제 RHP를 교체할 때만 Rhino가 닫혀 있는지 확인한다. 실제 Rhino 검증은 별도 요청 시
일회용 문서로 수행한다. 모듈 검사는 각 모듈의 `tests/`, 공유 계약은 루트 `tests/`에 둔다.

루트 `tests/run_tests.ps1 -Development`는 오프라인 환경을 설정하고
`src/rhp/RhinoAlmondBridge/tests/archive_host/ArchiveHost.csproj`를 빌드한 뒤
`ALMOND_ARCHIVE_TEST_HOST`에 그 실행 파일의 절대 경로를 지정하고 pytest를 실행한다.
빌드 실패나 출력 누락은 검사 실행 전에 오류로 중단한다. Rhino SDK·실제 문서 없이
실행되는 독립 net48 콘솔 fixture이며 RHP 출력이나 등록을 변경하지 않는다.
SDK는 이 체크아웃의 `src/rhp/RhinoTerminal/data/sdk/dotnet.exe`, PATH 순서로 찾는다.
별도 SDK는 `-DotNet <SDK/dotnet.exe>`, pytest 옵션은 `-TestArgs @('-q', '-k', 'archive')`로 지정한다.

직접 pytest를 실행할 때도 선택된 검사에 `archive_host` marker가 있으면 유효한 host 경로가
필수다. host가 없거나 경로가 잘못되면 조용히 제외하지 않고 실행기 사용법을 안내하며 중단한다.
ArchiveHost가 필요 없는 검사만 선택한 경우에는 이 준비 조건을 요구하지 않는다.

## MCP 기능별 워크트리

MCP 내부 기능 소유권과 공용 의존 관계는 [MCP SPEC](src/mcp/SPEC.md#기능별-구현과-소유권)을 따른다.
기능 작업자는 `features/<기능>/`과 해당 기능 검사를 중심으로 작업한다.
새 tool 등록, 공용 schema·서비스, `server.py` 조립, `retrieval_store.py` 합성,
외부 연결기 catalog와 호스트 계약은 통합 담당자와 조율한다. 기능 분리가 공용 계약의
충돌이나 모델 DB 공유를 없애지는 않는다.

현재 기능 분리의 통합 대상은 원격 `SPLIT`이다. 기능 브랜치는 `work/split-<기능>`처럼
별도 이름을 쓰고 PR base를 `SPLIT`으로 지정한다. Windows에서는 `SPLIT`과
`split/<기능>` ref가 경로 대소문자로 충돌하므로 `split/` 접두사를 사용하지 않는다.
일상 폴더는 `main`을 유지하며 SPLIT 통합을 일상 설치 배포로 간주하지 않는다.
SPLIT을 main에 반영하고 일상 설치를 갱신하는 작업은 별도 시작 지시를 따른다.

```powershell
git fetch origin
# 새 작업 예시: 로컬 SPLIT 브랜치를 만들 필요가 없다.
git worktree add -b work/split-example C:/TOOL/Almond-worktrees/split-example origin/SPLIT
```

`origin/SPLIT`은 fetch로 갱신하는 원격 추적 ref다. fetch는 현재 브랜치를 바꾸거나
일상 폴더의 추적 파일을 갱신하지 않는다. 각 기능 checkout에서 자기 환경을 구성하고
기능 검사 후 MCP 전체·외부 연결기 catalog와 영향받는 통합 계약을 검증한다.

## 빌드 결과와 통합

Bridge는 `src/rhp/build.ps1`, AlmondRhino는 `src/cos/build.ps1`로 빌드한다. 각 빌드는 자기
staging에서 완료한 뒤 출력 폴더를 교체한다. 등록·Rhino 로드는 수행하지 않는다.

검증 기록도 각 소유 모듈에 있다.

```powershell
# 해당 모듈 빌드 후 자기 기록만 갱신한다.
& ./src/engine/.venv/Scripts/python.exe -B src/rhp/tools/verify_runtime.py --record --component bridge
& ./src/engine/.venv/Scripts/python.exe -B src/rhp/tools/verify_runtime.py --record --component cos
# 합칠 때 두 기록과 공용 DLL 일치 여부를 함께 검사한다.
& ./src/engine/.venv/Scripts/python.exe -B src/rhp/tools/verify_runtime.py
```

Bridge manifest는 외부 연결기 소스를 포함하지 않고, 외부 연결기 manifest는 Terminal·패널 소스를
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
| 공용 `src/rhp/runtime-manifest.json` | Bridge와 외부 연결기 각각의 `runtime-manifest.json` |

Bridge 출력은 `src/rhp/RhinoAlmondBridge/plugin-runtime/RhinoAlmondBridge.rhp`다.
공용 외부 연결 플러그인은 AlmondCOS에서 AlmondRhino로 이름을 이전했으며, 출력은
`src/rhp/AlmondRhino/plugin-runtime/AlmondRhino.rhp`다. 기존 GUID를 유지하고
`install_runtime.ps1`으로 등록 이름과 경로를 이전한다.

기존 CoS의 Python command를 보존하기 위해 `.venv`는 `src/engine/.venv`에 유지한다.
`src/engine`의 예전 시작 버튼·설치 스크립트는 새 소유 모듈로 전달하는 호환 진입점이다.
그곳에 기능 구현을 추가하지 않는다. 각 체크아웃의 환경은 별도로 만들며 공유하지 않는다.

워크트리가 달라도 모델 폴더의 DB·Rhino 등록·슬롯·실행 중 assembly가 자동 격리되지는
않는다. 오프라인 검사는 checkout의 `data/offline`을 사용하고, 실제 Rhino 검증은
별도 요청이 있을 때만 일회용 문서에서 수행한다. 일상 설치 갱신·등록·실제 로드는 로컬 개발 완료와 구분한다.
