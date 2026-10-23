# 관측·반환 계약 검증 기록

2026-10-22–23 UTC / 2026-10-23 KST, `codex/native-observation-contracts`. 시작 commit은 `c578115`이다.
이 기록은 구현, 오프라인 검증, 실제 Rhino에서 확인한 증거를 구분한다.

## 완료한 구현

- 기존 C# 실행의 `List<Guid>`/void/Undo를 유지하면서 제한된 JSON `result`와 별도
  `result_error`를 추가했다. 64 KiB UTF-8, container depth 16, 순환/비유한 수치/미지원
  타입을 검사하며, 임의 POCO getter를 실행하지 않는다.
- `get_rhino_context`와 `get_rhino_viewport_image`를 기존 bound native 경로에 추가했다.
  이미지 반환은 실제 MCP ImageContent이며 JPEG decode, 원본/요청/반환 크기를 검사한다.
- 새 세 입력에만 `StrictInt`를 적용했다. 독립 리뷰에서 발견한 FastMCP의 입력 coercion
  문제를 수정했으며, 실제 MCP Client에서 boolean/string/float가 native 호출 전에 거절됨을 검증했다.
- 기존 conditioning 도구의 shot 예시가 노출 description에서 사라지던 docstring을 고쳤다.
- COS catalog를 DB-owning server import 없이 재생성했다. catalog 59개, 관리 도구를
  포함한 공개 COS 도구 62개이며 package/source/schema 검사를 유지한다.

## 실행한 검증

| 검증 | 결과 | 범위/한계 |
|---|---|---|
| 최초 observation/catalog/shared-store pytest | 38 passed, 13 subtests | fake bridge 및 실제 in-process MCP content/schema |
| 기본 pytest 전체 | 402 passed, 102 skipped, 21 subtests | standalone archive host 환경 미설정 등 기존 optional skip 포함. 기존 경고 8개 포함 |
| StrictInt 수정 후 observation/catalog/broker/compat pytest | 53 passed, 5 subtests | 실제 Client의 잘못된 타입 거절 6개 포함 |
| 최종 COS stdio handshake | 1 passed | 62개 도구 노출·schema·오래된 연결 거절 |
| COS 검증 script | Python 41, native 연결 fixture 18, COS lifecycle fixture 6 통과 | 실제 Rhino/model은 사용하지 않는 fixture |
| 통합 후보 RHP | build 성공, 오류 0 | 기존 ResultsPanel.Load 경고 1개. 설치/로드 증거와 별개 |
| native 테스트 DLL | build 성공, 오류 0 | 기존 ViewTable.GetViewList overload 경고 1개 |
| PID 29560 실제 Rhino native suite | Undo/result 40, headless observation 9, viewport 4 통과 | source-linked 고유 fixture. viewport 검사는 해당 단계의 전후 상태 보존을 확인 |
| PID 24468 공개 COS stdio | context·실제 JPEG·C# 계산값·오류 응답·정상 disconnect 통과 | 실제 후보 RHP, Rendered/Perspective model view. 일반 C# 실행은 기존 AIA 레이어 초기화 부수효과 포함 |
| PID 24468 단계별 native 재검증 | Undo/result 40, headless observation 9, viewport 4 통과 | 전체 정확 일치는 false. headless 단계에서 공유 Undo 일련번호만 증가했고 실제 viewport 단계의 전체 상태는 동일 |
| headless Undo 기록 1개 대조 실험 | 통과 | 활성 문서와 headless 문서가 같은 다음 일련번호를 관측함. 나머지 전체 snapshot 필드는 동일 |
| 마지막 소스·바이너리·모델 checkpoint | 11개 모두 최초 bytes/SHA-256과 일치 | 제품 소스 7개, 후보 RHP·Engine·fixture 3개, 디스크의 test.3dm. branch/HEAD도 동일 |
| 변경 diff | whitespace 검사 통과 | 독립 리뷰의 유일한 P2 입력 coercion finding은 위 StrictInt 수정으로 검증 |

제품 후보 출력:

`src/rhp/RhinoAlmondBridge/plugin-observation-20261022/RhinoAlmondBridge.rhp`

native fixture 출력:

`data/native-observation-review/native-tests/AlmondObservationTests20261022.dll`

기존에 로드된 fixture와 혼동하지 않도록 고유 AssemblyName을 사용했다. 속성 보존
검사는 SDK에 없는 ObjectAttributes.DataCRC 대신 지원되는 ToJSON(SerializationOptions)을
사용하며 사용자 데이터도 포함한다. 실제 8.0 참조 assembly로 컴파일을 확인했다.

재실행 명령:

```powershell
& .\src\engine\.venv\Scripts\python.exe -B src/cos/build_catalog.py
& .\src\engine\.venv\Scripts\python.exe -B -m pytest tests/mcp/test_rhino_observation.py tests/cos/test_catalog.py tests/cos/test_broker.py tests/cos/test_compat.py -q
& .\src\cos\run_tests.ps1
& .\src\rhp\build.ps1 -OutputDirectory 'RhinoAlmondBridge\plugin-observation-20261022'
```

빌드 경로가 실제 로드된 뒤에는 같은 경로를 덮어쓰지 않고 새 후보 경로를 사용한다.
로컬 stdout 기록은 `data/native-observation-review`에 있다.

## AlmondCOS 명령 누락과 실제 로드

worker가 read-only로 확인한 명령 누락 원인은 HKCU의 AlmondCOS GUID
`39eb74f6-8283-4e43-bf26-f0106d891b75` 등록이 존재하지 않는 옛
`C:\TOOL\Rhino\mcp\AlmondCOS\plugin-shared-storage-20261020\AlmondCOS.rhp`를 가리키는 것이다.
현재 파일은 `src/rhp/AlmondCOS/plugin-build/AlmondCOS.rhp`에 있고 GUID와 command 정의는 맞다.
레지스트리 키는 `data/native-observation-review/almondcos-before-20261022-29560.reg`에
백업했다. 정상 Install/Load 후 두 명령 `AlmondCOS`/`AlmondCOSDisconnect`, 명령 실행 성공,
연결 광고의 PID/startTicks/protocol 일치를 확인했다. 두 GUID의 HKCU 등록 경로도
실제 후보 Bridge와 현재 COS 출력으로 갱신됐다.

초기 Core/Desktop 조회 이후 일부 worker 도구의 추가 승인 대기가 있었으며 이후
해소됐다. PID 29560의 실제 AppDomain 조회에서 Bridge/Engine/COS 미로드를 먼저
확인한 뒤 후보 Bridge를 정상 로드했다. 활성 문서는 사용자 허용 `test.3dm`, runtime
serial은 268435460이었다. 실제 로드 경로는 위 후보 출력이며 MVID는
`d33baad5-52c3-4c2e-bdc5-60235e20fb89`이다. 등록 명령은 `RhinoTerminal`을 포함한
12개로 확인했다. 근거는 `data/native-observation-review/loaded_plugins_29560_before.json`과
`loaded_plugins_29560_after.json`이다. PlugInManager의 옛 메타데이터만으로 로드 경로를
판정하지 않았다. Bridge 등록 키도 `bridge-before-20261022-29560.reg`에 백업했다.

`almondcos_recovery_29560.json`에서 COS 실제 경로는 `src/rhp/AlmondCOS/plugin-build`,
Engine 실제 경로는 후보 Bridge 옆 `Almond.Engine.dll`이다. COS MVID는
`734eae71-e889-4543-b659-8d5a11f659dd`, Engine MVID는
`e63840dd-2133-4869-b7d1-ea65db408870`이다. 명령 복구 전후 document Modified는
false이며 runtime serial이 유지됐다.

ChatGPT 설정에서 COS Plugins의 app permission은 Allow all actions로 조회됐다.
이번 대화에 전달된 호출 목록에서는 COS Plugins 경유 API를 찾지 못해 그 앱을 통한
직접 호출은 시험하지 않았다. 이는 이 대화의 검증 범위에 관한 기록이며, 사용자의
승인 누락이나 COS Plugins의 설치·연결·작동 불능을 진단한 것이 아니다.
아래 실제 Almond 검증은 Core에서 실행한 표준 COS stdio 클라이언트로 수행했다.
이 검증 경로의 차이와 Rhino의 잘못된 RHP 등록 사이의 인과관계도 단정하지 않는다.

## 실제 연결에서 확인한 라이브러리 환경

공개 COS stdio Client는 62개 도구 노출, PID/문서 선택, 연결 및 project_info를 성공적으로
수행했다. 최초 local runner는 FastMCP의 문자열 결과 포장을 해석하지 못했다.
설치 소스의 `meta.fastmcp.wrap_result` 계약에 맞춰 runner를 수정했고,
그 뒤 실제 문서 조회 응답이 native library guard의 명시적인 오류임을 확인했다.
두 시도 모두 C# 수정 실행 이전에 끝났고 정상 disconnect의 `released=true`를 확인했다.

`native-library-roots-29560.json`에서 기존 Rhino Process의 세 library 환경변수가
모두 비어 있었고, capsule/drawing helper는 저장소 `asset/` 경로를 기억하고 있었다.
Python worker는 `src/engine/library_paths.py`에 따라 AppData를 선택했다.
Windows User scope의 세 변수는 이미 AppData로 설정돼 있었다. 기존 캐시를 바꾸거나
guard를 우회하지 않고, 이 사용자 설정을 새 검증 프로세스의 환경에 전달했다.

새 Rhino PID 24468에서 `live-mcp-bootstrap.json`은 다섯 native library cache가 모두
사용자 설정과 일치함을 확인했다. 같은 후보 Bridge/COS/Engine MVID, `test.3dm`,
document serial 268435458, Modified=false, AlmondCOS 명령 성공도 기록했다.
기존 Rhino PID 29560은 그대로 두었다. 모델을 저장하거나 사용자 환경변수를 다시 쓰지 않았다.

## 실제 공개 COS 실행

사용자가 자유롭게 시험하도록 허용한 리포 루트 `test.3dm`을 사용한다. 다른 파일로
활성 문서가 바뀌면 준비된 runner는 실행을 거절한다.

`data/native-observation-review/live-mcp-report.json`은 2026-10-22 16:21 UTC의
실제 MCP Client → COS host/worker → Engine → 후보 RHP 실행 결과다. 공개 도구는
62개였고, PID 24468과 정확한 모델 경로를 선택한 뒤 아래 결과를 확인했다.

- 문서 조회: serial 268435458, Millimeters, 절대 공차 0.01, 객체 10,121개,
  레이어 41개, 선택 0개. Rendered/Perspective 뷰의 원본 크기는 1238×945였다.
- 이미지: 요청 상한 960×720에서 실제 JPEG 943×720, 97,578 bytes를 받았다.
  MCP content는 text+image이며 metadata에 base64를 중복하지 않았다.
  `live-viewport.jpg`를 직접 열어 모델 화면을 확인했다. SHA-256은
  `8e876ad5e4de2f4df1d182e41707431ad4de4f08e47a549b55d94ed00a304efe`이다.
- 캡처 전후 context는 동일했다. 잘못된 크기 요청은 이미지 없는 오류로 반환됐다.
- C#에서 메모리에만 만든 10×10×10 상자에서 2×12×12 슬래브를 빼는 계산을 했다.
  응답의 `result`는 valid/solid 결과 2개, 기대 체적 800에 실제 800.0000000000008,
  기대 제거 체적 200에 실제 199.9999999999992를 담았고 `result_error`는 없었다.
- 정상 disconnect는 `released=true`, `worker_closed=true`, `rhino_closed=false`였다.

Boolean 형상을 문서에 추가하지 않았지만 일반 C# 실행기는 기존 AIA 레이어 초기화를
수행했다. 실행 뒤 객체 수는 10,121개, 레이어 수는 43개, Modified는 true였다.
따라서 이 전체 실행을 문서 무변경 검증으로 부르지 않는다. 캡처 단계의 보존 검증과
C# 계산값 반환 검증은 각각 위의 근거로 판정한다. 모델 Save는 호출하지 않았다.

## 추가 전체 상태 비교의 진단

PID 29560의 최초 modeless 실행에서는 40+9+4개 검증이 통과했다.
`native-observation-tests-pid29560.json`에 이 결과를 보존했다. 독립 검토 후 local runner의
후처리 예외가 `ok=false`를 보장하도록 수정했고, 전체 suite 전후 snapshot도 추가했다.

먼저 공개 C# 실행으로 suite 전체를 감쌌던 시도는 전후 비교에서 runtime_error가 났다.
`live-native-suite-first-attempt.json`에 남아 있으며 당시 정확한 변경 필드는 기록하지 않았다.
후속 진단 wrapper는 `Newtonsoft.Json.Rhino` 10과 `Newtonsoft.Json` 13의 동일 타입 이름
충돌로 compile_error가 났다. 이 시도는 suite 본체를 실행하지 않았으며
`live-native-suite-report.json`에 보존했다. 제품 컴파일러를 변경하지 않고 원래의
modeless Python 실행기로 돌아가 단계별 JSON leaf 차이를 기록했다.

2026-10-23 01:22–01:23 UTC의 `native-observation-tests-resumed.json` 결과는 다음과 같다.

| 단계 | 회귀 결과 | 활성 문서 snapshot의 변화 |
|---|---|---|
| 별도 headless 문서의 Undo/result | 40/40 통과 | `next_record` 159 → 304 |
| 별도 headless 문서의 observation | 9/9 통과 | `next_record` 304 → 308 |
| 실제 활성 문서의 context/viewport | 4/4 통과 | 변경 필드 0개 |

전체 suite에서 달라진 leaf는 `/next_record` 하나였다. 문서 identity, geometry CRC,
사용자 데이터를 포함한 attributes, selection, layer CRC, view/camera, Modified,
현재 Undo 기록과 나머지 snapshot 필드는 모두 같았다. 전체 정확 일치는 false이므로
원본의 `active_document_preserved=false`와 `ok=false`를 성공으로 다시 쓰지 않았다.
이 실행의 identity 비교는 snapshot을 읽은 문서 참조의 serial/path에 대한 것이다.
runner 종료 시점의 별도 ActiveDoc 일치 조건은 차이가 있을 때 단락 평가되므로
이 기록만으로 그 조건의 통과까지 주장하지 않는다.

`headless-undo-counter-control.json`은 headless 문서 하나의 Undo 기록 하나 안에 임시 점
하나를 추가하는 별도 modeless 대조 실험이다. Begin 직전 활성/headless 문서의 다음
번호가 모두 309였고, 기록 309 안에서 점을 추가한 뒤 모두 310이었다.
활성 문서의 현재 Undo 기록은 계속 0이었다.
headless 문서를 Dispose한 뒤에도 활성 문서의 나머지 전체 snapshot 필드는 같았다.
이 Rhino 프로세스에서 다음 Undo 번호가 문서 사이에 공유됨을 직접 확인했다.

따라서 headless Undo 테스트를 포함한 전체 suite에 다음 번호의 불변까지 요구한
추가 harness 조건은 이 범위에 맞지 않는다. 판정은 53개 회귀 결과, 실제 문서의 조회
단계에서 전체 상태가 같았다는 결과, 위 대조 실험에 근거한다. 제품 코드나 native
조회 테스트의 엄격한 `DocumentState` 비교에서 이 필드를 제거하거나 기준을 완화하지 않았다.
처음 실패한 wrapper에는 필드별 기록이 없으므로 그 시도의 다른 차이 유무까지 추정하지 않는다.

## 마지막 상태와 확인 범위

`data/native-observation-review/final-checkpoint.json`에서 최초 checkpoint의 11개 파일과
bytes/SHA-256이 모두 일치했고 branch/HEAD도 같았다. 디스크의 `test.3dm`은
37,373,345 bytes, SHA-256
`bc09bc64d7bbda4d100cf3cef148a2543dc0c700a74d561978e801281ea7a1ad`로 유지됐다.
Rhino 안의 Modified=true 상태와 디스크 파일의 보존은 별개의 결과다.

대조 실험에서 현재 AppDomain의 Bridge/Engine/COS/fixture 실제 경로와 MVID도 다시
기록했으며 앞선 후보와 일치했다. 로드된 RHP를 덮어쓰거나 Rhino를 강제 종료하지 않았다.
검증의 마지막 네이티브 실행 뒤 명령 입력 상태로 복귀했고, 공개 COS 연결은 각 시도에서
정상 해제했다. 이 검증 기록과 checkpoint는 작업 브랜치의 변경을 커밋하기 전에 확정했다.

실제 공개 MCP 이미지 검증은 Rendered/Perspective model view 하나와 선택 0개 조건이다.
페이지/detail/clipping 조합 전체, 모든 이미지 크기 경계, 실제 자산 배치·구조해석을
이번 새 기능의 실환경 증거로 주장하지 않는다. 이 채팅에서 COS Plugins 앱을 통해
직접 호출하는 경로는 미검증이다. Core에서 실행한 표준 COS stdio 클라이언트의
실제 성공과 구분하며, 이 기록을 COS 전체의 설치·권한·연결 문제로 해석하지 않는다.
이 검증은 실행/관측 계약을 확인하며 통제된 모델링 성능 비교를 대체하지 않는다.
