# Almond 저장소 구조와 실행 계약

## 목적과 변경 경계

개인 Rhino 작업에 필요한 소스를 한 리포에서 관리하되 Engine과 MCP를 분리한다.
이번 정리는 파일 위치·경로 참조·패키징·설치 경로·문서를 맞추고 Bridge와 Terminal을 단일 RHP로 통합하는 작업이다.
구조해석 수식, 자산 배치, UI 동작, MCP 도구, 연결 프로토콜, Undo/Redo의 의미를 바꾸지 않는다.
기존 네임스페이스·Bridge assembly 이름과 GUID·Rhino 명령을 유지한다. 별도 Terminal 플러그인 entry와 GUID는 제거한다.

## 디렉터리

```text
almond-mcp/
├─ src/
│  ├─ engine/                     # 사용자 제작 실행·연결 계층
│  │  ├─ native/                 # Almond.Engine.dll
│  │  ├─ .venv/                  # 재생성 가능한 로컬 Python 환경, Git 제외
│  │  └─ data/                   # 슬롯·개발 fixture, Git 제외
│  ├─ mcp/
│  │  ├─ almond_mcp/             # 원본 Python package 이름 유지
│  │  └─ rhino_bridge.py          # 기존 Python bridge 예제/진입 파일
│  ├─ cos/                       # COS Python host·worker·카탈로그
│  └─ rhp/
│     ├─ RhinoAlmondBridge/       # core·csproj·원본 아이콘·패키지 설정
│     ├─ Structural_Analysis/    # 분석·결과 패널·solver 연결 C#
│     ├─ Asset_Panel/            # 라이브러리·배치·archive C#, shared web/
│     ├─ RhinoTerminal/          # Bridge에 포함되는 터미널 소스·UI·vendor notices
│     └─ AlmondCOS/              # COS Rhino RHP
├─ asset/
│  ├─ capsules/
│  ├─ constructions/             # Constructionfiles, Materialfiles
│  ├─ drawing/                   # DrawingAssetfiles, DrawingRecipes, Draftingfiles
│  ├─ diagram/                   # DiagramAssetfiles
│  ├─ models/                    # GeneratedAssetfiles, IkeaFurniturefiles
│  └─ history/                   # Historyfiles
├─ tests/
│  ├─ engine/                    # Python·slots·native fixture
│  ├─ mcp/                       # MCP/계산/자산/패키징 검증
│  ├─ cos/                       # Python·pipe·host lifecycle fixture
│  └─ rhp/                       # Bridge·패널 web·Terminal fixture
├─ tools/                        # 빌드·데이터 생성·검증 도구
├─ docs/                         # 기능·사용·기술 문서
└─ examples/                     # 사용 예제
```

다운로드한 Grasshopper 라이브러리를 소스에서 사용할 때의 선택 경로는
`asset/grasshopper/Grasshopperfiles`다. 현재 리포에 제3자 예제 원본을 추가하지 않는다.

## 구성요소와 연결

| 구성요소 | 책임 | 의존 관계 |
|---|---|---|
| Engine | 외부 실행기, A–J 슬롯, 모델별 저장소·프로세스 소유권, 연결 수명 | MCP를 호출하고 원본 Rhino bridge handler를 재사용 |
| MCP | 공개 도구, Python 구조해석 계산, 자산 검색·데이터 관리 | 원본 package 이름 `almond_mcp` 유지 |
| COS Python | stdio host/worker, 도구 카탈로그·계약 검사 | 같은 Engine·editable MCP 사용 |
| RhinoAlmondBridge | Rhino 명령·TCP 처리·Undo, 구조해석/자산/Terminal 패널 | 세 feature 폴더의 C#를 하나의 assembly로 컴파일 |
| RhinoTerminal 소스 | Rhino 내부 터미널·almond 연결 | Bridge assembly 안에서 별도 Almond.Engine.dll 사용 |
| AlmondCOS RHP | Rhino 문서 연결과 COS host 탐색·제어 | `src/cos` 및 `src/engine` 사용 |

`Structural_Analysis`, `Asset_Panel`, `RhinoTerminal`은 독립 RHP가 아니다.
Bridge csproj의 Compile 경로로 연결한다. Terminal 명령은 `Commands.cs`에 유지하고,
패널 등록과 종료 시 `StopAll()`은 유일한 Bridge plugin entry가 담당한다.
분석 패널의 Python 계산 코드는 계속 `src/mcp/almond_mcp`에 있다.

에셋과 분석 탭은 HTML·CSS·JS를 공유하므로 웹 파일 전체를 `Asset_Panel/web`에 유지한다.
개발 checkout에서는 MCP가 그 경로를 읽고, wheel에는 기존 `almond_mcp/library_ui`로 포함한다.
RHP의 오프라인 화면은 빌드 도구가 만든 RHP 인접 `archive/ui`를 읽는다.
웹 자산 이동으로 URL route, UI 이벤트, 모델 배치 명령을 바꾸지 않는다.

## 실행·빌드 산출물

Python 환경은 `src/engine/.venv`에 새로 만든다. 이전 venv를 복사해서 재사용하지 않는다.
루트 `pyproject.toml`, `.python-version`, `uv.lock`이 패키지와 의존성 기준이다.
package import는 `src/mcp/almond_mcp`를 가리킨다. 서버가 시작될 때 의존성을 다시 설치하지 않는다.

`src/rhp/build.ps1`은 `net8.0-windows` 단일 RHP를
`src/rhp/RhinoAlmondBridge/plugin-build`에 빌드한다. 설치된 Rhino SDK를 참조하며
Rhino 8.34 / .NET 8에서 검증했다. Yak의 최소 Rhino 태그는 실제 참조 SDK 버전을 따른다.
RhinoCommon·Rhino.UI·Eto·Grasshopper·GH_IO는 호스트 제공 DLL이므로 패키지에 복사하지 않는다.
Almond.Engine·Porta.Pty·Vanara·Roslyn·Newtonsoft DLL, deps/runtimeconfig JSON,
Terminal 라이선스, `archive`를 RHP와 함께 유지한다. 로드 중인 출력은 빌드가 덮어쓰지 않는다.

Terminal은 assembly 위치에서 `../../../engine`을 찾으므로 출력은 위 깊이의
`RhinoAlmondBridge/plugin-*` 폴더여야 한다. 임의 Yak 설치 위치만으로 개인 Engine 환경이
자동 구성되지는 않는다. 별도 AlmondCOS 출력은 `src/rhp/AlmondCOS/plugin-build`이며
COS의 기존 Engine/host 탐색은 유지한다.

Bridge assembly 이름 `RhinoAlmondBridge`, informational version `0.7.0-rc.2`,
plugin GUID `c337dbb8-394a-4593-9c2b-a3d7cfc91893`와 Engine reflection 계약을 유지한다.
Terminal panel GUID `4B3493B2-3421-4BEC-A8C8-F7F1786E8495`, 명령 `RhinoTerminal`,
`RhinoTerminal.*` web resource 이름도 유지한다.

COS discovery는 `src/cos/data/hosts`, 공통 슬롯은 `src/engine/data`를 사용한다.
모델 상태는 이 위치가 아니라 모델 폴더의 `.almond`에 남는다.
등록 경로가 바뀌어도 실행 중 Rhino가 새 assembly를 즉시 로드하는 것은 아니다.

통합본은 기존 Bridge GUID의 등록 경로를 로컬 빌드로 갱신해 설치한다.
별도 Terminal GUID 등록은 백업 후 제거하되 로드된 파일이나 AppData 라이브러리를 덮어쓰지 않는다.
빌드는 등록을 자동 변경하지 않는다. 설치 후 실제 assembly 경로와 Engine/Bridge 라이브러리
경로 일치를 별도로 확인한다. solver의 기존 uvx 또는 `ALMOND_SOLVER_COMMAND` 정책은 유지한다.

## 자산과 데이터 보존

asset 폴더 내부의 기존 라이브러리 이름과 manifest-relative 경로를 유지한다.
wheel의 `almond_mcp/data/<기존 이름>`과 AppData 폴더명도 유지한다.
`RHINO_MCP_*_DIR` 명시 설정이 우선하며, 개인 Engine은 기존 AppData 기본 라이브러리를 사용한다.
저장소 구조 변경으로 사용자 라이브러리·모델·DB를 이동하거나 다시 초기화하지 않는다.

GLB·PNG·도면·계약·vendor 파일의 바이트와 기록된 해시를 보존한다.
`.gitattributes`의 계약 LF, 도면 원본 줄바꿈 보존, vendor/binary 규칙은 새 경로를 따른다.
외부 원본 저장소의 다운로드 URL은 이 리포의 이동 경로로 치환하지 않는다.

공유 DB 잠금, 연결별 token, 작업 완료 확인, 불확실한 작업 격리는 그대로다.
시간초과를 rollback이나 재실행 허가로 취급하지 않는다.

## 검증 및 정리 기준

실행 명령은 `LOCAL_SETUP.md`에 둔다. 경로 이동은 다음 증거로 검증한다.

- source import, fixture·csproj·UI·문서의 상대 참조가 새 위치를 가리킨다.
- 변경 범위에 해당하는 Engine/Terminal 계약 테스트와 패널 web 테스트가 통과한다.
- 단일 Bridge RHP가 빌드되고 실제 Rhino에서 Terminal·자산 배치·해석·Undo/Redo를 확인한다.
- COS는 별도 구성으로 유지하며 이번 통합의 코드 수정·실제 연결 검증에서 제외한다.
- archive의 hash 검증, wheel의 bundled UI/data 포함, 자산 바이트를 확인한다.
- 이전 폴더를 제거한 상태에서도 새 환경이 동작한다.

테스트는 fixture에서 실행하며 실제 Rhino 패널·모델 작업 검증과 구분한다.
이미 존재하던 실패나 외부 도구 부재는 숨기거나 테스트를 완화해서 통과시키지 않는다.

중복 설치·이전 산출물·임시 로그·구현 계획은 필요가 끝나면 정리한다.
현재 테스트 결과는 ignored `data/`에 남길 수 있지만 개인 모델이나 배포물로 취급하지 않는다.
LICENSE, THIRD-PARTY-NOTICES와 vendor/asset 고지는 포함 코드·자산에 필요하므로 유지한다.
SDK·가상환경·RHP·DB·로컬 COS 설정은 `.gitignore`로 제외한다.
