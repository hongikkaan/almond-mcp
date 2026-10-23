# Almond 저장소 구조와 실행 계약

## 목적과 변경 경계

개인 Rhino 작업에 필요한 소스를 한 리포에서 관리하되 Engine과 MCP를 분리한다.
2026-10-22의 경로 정리와 단일 RHP 통합은 파일 위치·패키징·설치 경로를 맞춘 작업이다.
그 작업에서는 구조해석 수식, 자산 배치, UI 동작, MCP 도구, 연결 프로토콜, Undo/Redo의 의미를 바꾸지 않았다.
기존 네임스페이스·Bridge assembly 이름과 GUID·Rhino 명령을 유지하며, 별도 Terminal 플러그인 entry와 GUID는 제거했다.
후속 문서·뷰포트 조회와 C# 결과 반환은 아래 실행 계약에 포함한다. 상세 입력·반환 형식은
[기능 계약](docs/native-observation.md), 실제 확인 범위는 [검증 기록](docs/native-observation-verification.md)을 따른다.

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
| Engine | 외부 실행기, A–J 슬롯, 모델 폴더의 공유 저장소·프로세스 소유권, 연결 수명 | MCP를 호출하고 원본 Rhino bridge handler를 재사용 |
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

## 현재 문서 조회와 실행 결과

기존 모델 작업은 연결의 `almond_project_info`를 확인하고 `get_rhino_context`로
활성 문서의 identity·단위·공차·객체/레이어 수·선택·viewport/camera를 조회한다.
COS 이름은 각각 `almond_cos_project_info`, `almond_cos_get_rhino_context`이며
연결별 `connection_id`를 전달한다. 선택 목록은 기본 50개, 최대 200개로 제한하고
전체 수와 반환 수·잘림 여부를 구분한다.

`get_rhino_viewport_image` / `almond_cos_get_rhino_viewport_image`는 현재 뷰의
실제 MCP ImageContent와 metadata를 반환한다. 폭·높이 입력은 각각 64–2048의 엄격한
정수이며 화면 비율을 유지하고 확대하지 않는다. JPEG 한도는 4 MiB이며
structured metadata에 base64를 중복하지 않는다. 실패하면 이미지 없는 명시적 오류를 반환한다.
두 조회는 문서 binding·UI thread·호출 identity·native 완료 확인을 거치는 고정 경로다.
레이어·기하·Undo 기록을 만들거나 카메라·display mode·clipping·선택을 바꾸지 않는다.

`get_rhino_probe`는 스킬의 outline·resolve-block·sections·vertical-probe·joint-pairs
helper를 Bridge에 컴파일하여 같은 고정 관찰 경로에서 실행한다. 모델 경로를 확인하고
요청·응답을 각각 256 KiB로 제한한다. 별도 C# 소스 조립이나 일반 실행기를 사용하지 않는다.

`execute_rhino_script`는 JSON으로 표현 가능한 C# 반환값을 `result`로 전달한다.
한도는 compact UTF-8 JSON 65,536 bytes와 container 깊이 16이며, 미지원 값·순환 참조·
한도 초과는 `result_error`로 설명한다. 반환 변환 오류로 이미 완료된 수정이 rollback되지는
않으며 자동 재실행하지 않는다. 기존 `List<Guid>`의 `guids`·자동 치수, void/null,
Undo/Redo 동작을 유지하므로 일반 C# 실행을 read-only로 취급하지 않는다.
기본 AIA 레이어 일괄 초기화는 제거했으며, 실제 적용한 재료의 레이어만 생성한다.

MCP 서버와 COS host의 초기 안내는 현황 조회 → 관련 객체 조사 → 수정 후보의 검증 →
원본 교체 순서를 안내한다. 실행 성공·현재 화면·기하의 유효성만으로 과제의 정확성을
인증하지 않는다. COS catalog는 76개, 관리 도구를 포함한 공개 도구는 79개이며
source fingerprint와 schema 검사를 유지한다.

## Scene·Component·계획·모델링 규칙

Scene은 공간의 의도와 맥락이고, Component는 명시적으로 등록한 Rhino group이다.
객체는 최대 하나의 Component에 속하며, Component는 하나 이상의 Scene에 속한다.
일반 group은 자동 등록하지 않는다. block occurrence를 Component group에 포함할 수 있지만
공유 block definition의 내부 객체를 occurrence별 소유 객체로 등록하지 않는다.
일반 객체는 `register_scene_objects`로 Scene에 직접 연결할 수 있어 asset instance 등록이 필요 없다.
Room과 asset instance는 기존 충돌·containment·하중 계산을 위해 보존한다.
`validate_scene_layout`의 통과는 그 legacy asset 검사 범위에 한정하며 Component 기하 검증은 별도다.

객체 identity는 문서 경로와 GUID의 조합이다. DB 사전검사 → native group 수정 → 완전한
객체 snapshot 확인 → DB commit 순서로 등록한다. 캐시 조회는 `live_verified=false`를 명시하고
`sync_design_component`는 완전한 live group 관찰로 장부를 갱신한다. 수동 regroup/복사로
태그와 membership이 다르면 명시적인 수리가 필요하다. timeout은 자동 재실행 허가가 아니다.
Rhino group 자체의 UserString은 Undo로 복원되지 않아 사용하지 않는다. 그룹 내 기존 객체
하나에 내부 `almond:component_record`를 저장하고 `ModifyAttributes`로 갱신한다. 이 기록이
group GUID·이름·Scene 참조를 보관한다. 추가 관리용 객체는 생성하지 않는다.

Phase는 Plan의 조직상 부모다. Plan은 여러 Scene·Component, Step은 Component를 참조한다.
Step의 참조 생략은 Plan 대상을 상속하고 명시적인 빈 목록은 대상 없음이다.
각 Plan 변경은 전체 계획 상태를 immutable revision으로 저장한다. 이전 DB는 현재 상태를
revision 0 baseline으로 남기며 존재하지 않았던 과거 revision은 만들지 않는다.
`expected_revision`으로 오래된 상태의 수정을 거부할 수 있다. 이 기록은 기하 백업이 아니다.

재료 manifest의 `layer_path`가 `M::category::material_id` 등의 계층을 정한다.
`assign_material`과 C#/Python의 `ModelingMaterials.CreateAttributes`가 같은 native 구현을 쓴다.
MCP C# 실행은 실행 범위 안의 객체 생성·직접 material 변경을 모아서 최종 속성 기준으로
레이어를 적용한 뒤 같은 Undo record를 닫는다. 전역 이벤트나 시작 시 문서 전체 변경은 없다.
ByLayer·ByParent 재료는 추측하지 않는다. MCP 밖의 스크립트는 factory를 명시적으로 사용한다.
`modeling_policy.json`/`get_modeling_policy`가 key 목록을 제공하며 이름은 자유롭다.
보통 새 객체에는 material_id와 필요한 floor·construction_detail·typed source만 기록하고,
Component 등록이 component_id를 설정한다. PBR 값은 native material에 유지한다.

Drafting Sheet는 `upsert/get/list/remove/sync_drawing_sheet`로 관리한다. 도면명·도면 종류·
축척 분모·용지 크기·모델 공간 작성 영역과 Scene/Component/Plan 참조를 보관하며 Rhino
Layout GUID와 연결한다. 실제 도면은 모델 공간의 World XY에 작성하고 Layout의 Top detail이
그 영역을 지정 축척으로 보여 준다. 용지와 축척에 들어가지 않는 영역은 생성 전에 거부한다.
도면을 자동 생성하거나 실제 단면 포함 대상을 추측하지 않는다. `list_drawing_sheets(plan_id=...)`로
마무리할 때 목록을 검토한다. 등록 해제는 도면 형상·Layout을 삭제하지 않는다.

상태·관계 다이어그램, 설계 근거와 한계는 [Component 시스템](docs/component-system.md),
실행 예제는 [재료 모델링 지침](skills/rhino-almond/references/modeling-materials.md)을 따른다.

## 실행·빌드 산출물

Python 환경은 `src/engine/.venv`에 새로 만든다. 이전 venv를 복사해서 재사용하지 않는다.
루트 `pyproject.toml`, `.python-version`, `uv.lock`이 패키지와 의존성 기준이다.
package import는 `src/mcp/almond_mcp`를 가리킨다. 서버가 시작될 때 의존성을 다시 설치하지 않는다.

`src/rhp/build.ps1`은 `net8.0-windows` 단일 RHP를
`src/rhp/RhinoAlmondBridge/plugin-runtime`에 빌드한다. 설치된 Rhino SDK를 참조하며
Rhino 8.34 / .NET 8에서 검증했다. Yak의 최소 Rhino 태그는 실제 참조 SDK 버전을 따른다.
RhinoCommon·Rhino.UI·Eto·Grasshopper·GH_IO는 호스트 제공 DLL이므로 패키지에 복사하지 않는다.
Almond.Engine·Porta.Pty·Vanara·Roslyn·Newtonsoft DLL, deps/runtimeconfig JSON,
Terminal 라이선스, `archive`를 RHP와 함께 유지한다. 로드 중인 출력은 빌드가 덮어쓰지 않는다.

Terminal은 assembly 위치에서 `../../../engine`을 찾으므로 출력은 위 깊이의
`RhinoAlmondBridge/plugin-*` 폴더여야 한다. 임의 Yak 설치 위치만으로 개인 Engine 환경이
자동 구성되지는 않는다. 별도 AlmondCOS 출력은 `src/rhp/AlmondCOS/plugin-runtime`이며
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

같은 모델 폴더는 `.almond/scene.sqlite3`와 `.almond/tmp`를 공유하며 각 연결은
자신의 token·session·call 디렉터리를 소유한다. 한 연결이 전체 DB를 소유하지 않는다.
공유 DB 잠금, 연결별 token, 작업 완료 확인, 불확실한 작업 격리는 그대로다.
시간초과를 rollback이나 재실행 허가로 취급하지 않는다.

## 검증 및 정리 기준

실행 명령은 `LOCAL_SETUP.md`에 둔다. 경로 이동과 단일 RHP 통합은 다음 증거로 검증한다.

- source import, fixture·csproj·UI·문서의 상대 참조가 새 위치를 가리킨다.
- 변경 범위에 해당하는 Engine/Terminal 계약 테스트와 패널 web 테스트가 통과한다.
- 단일 Bridge RHP가 빌드되고 실제 Rhino에서 Terminal·자산 배치·해석·Undo/Redo를 확인한다.
- COS는 별도 구성으로 유지한다. 단일 RHP 통합 당시의 COS 제외 범위를 후속 기능 검증 전체에 적용하지 않는다.
- archive의 hash 검증, wheel의 bundled UI/data 포함, 자산 바이트를 확인한다.
- 이전 폴더를 제거한 상태에서도 새 환경이 동작한다.

문서·뷰포트 조회와 결과 반환은 Python content/schema 검증, 기존 Undo를 포함한 native
회귀, 실제 로드한 후보 RHP, 공개 COS stdio 클라이언트의 이미지·계산값 수신으로 확인한다.
각 검증 결과와 미검증 조건은 [관측·반환 검증 기록](docs/native-observation-verification.md)에 둔다.
테스트는 fixture에서 실행하며 실제 Rhino 패널·모델 작업 검증과 구분한다.
이미 존재하던 실패나 외부 도구 부재는 숨기거나 테스트를 완화해서 통과시키지 않는다.

중복 설치·이전 산출물·임시 로그·구현 계획은 필요가 끝나면 정리한다.
현재 테스트 결과는 ignored `data/`에 남길 수 있지만 개인 모델이나 배포물로 취급하지 않는다.
LICENSE, THIRD-PARTY-NOTICES와 vendor/asset 고지는 포함 코드·자산에 필요하므로 유지한다.
SDK·가상환경·RHP·DB·로컬 COS 설정은 `.gitignore`로 제외한다.
